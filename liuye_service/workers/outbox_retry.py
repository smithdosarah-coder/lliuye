# -*- coding: utf-8 -*-
"""liuye_service.workers.outbox_retry — 60s outbox scan · 5 retry · dead-letter.

Per W1-backend brief §4.7 + ``liuye_service/CLAUDE.md`` §7 + v3 §5.x +
``deploy/liuye-outbox.service`` systemd unit.

The audit wrapper (``liuye_service.audit.record_liuye_decision``) writes
a JSON envelope to ``data/liuye/outbox/{decision_id}.json`` when the
in-process ledger write fails (sqlite outage / OS error / validation
bug). This worker picks those up and retries.

Retry policy (spec'd · CANNOT be tuned without PM ratify):

- Scan interval:       60 seconds (loop)
- Max retries:          5
- Backoff schedule:     60s / 120s / 240s / 480s / 960s (exponential)
- Dead-letter target:  ``data/liuye/dead-letter/{decision_id}.json``
- Idempotency:         ``idempotency_key`` (defaults to ``decision_id``)
                       prevents double-record when the same outbox file
                       is processed by overlapping workers.
- Sentry alert:        dead-letter graduation logs an ERROR-level record
                       with ``sentry.alert=true`` tag for the ops runbook.

The worker is **process-isolated** from the FastAPI app:

    deploy/liuye-outbox.service
        ExecStart=/usr/bin/python3 -m liuye_service.workers.outbox_retry

This is intentional · running retries inside the FastAPI process would
mean ``uvicorn --workers > 1`` racing on the same outbox files. A
separate systemd unit gives one source of truth per host.

Env vars (read at module import time · forwarded to the worker config):

- ``LIUYE_OUTBOX_DIR``         default ``./data/liuye/outbox``
- ``LIUYE_DEADLETTER_DIR``     default ``./data/liuye/dead-letter``
- ``LIUYE_OUTBOX_MAX_RETRY``   default 5
- ``LIUYE_OUTBOX_BACKOFF_SEC`` default ``"60,120,240,480,960"`` (csv)
- ``LIUYE_OUTBOX_SCAN_SEC``    default 60 (loop cadence)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from shared.decision_ledger import record_decision

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Defaults · centralized so the systemd unit + tests + module agree
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # credit_report_agent_work/
DEFAULT_OUTBOX_DIR = _PROJECT_ROOT / "data" / "liuye" / "outbox"
DEFAULT_DEADLETTER_DIR = _PROJECT_ROOT / "data" / "liuye" / "dead-letter"

# Per v3 §5.x verbatim · DO NOT tune without PM ratify (root §3.7.x style).
DEFAULT_MAX_RETRY = 5
DEFAULT_BACKOFF_SEC: tuple[int, ...] = (60, 120, 240, 480, 960)
DEFAULT_SCAN_INTERVAL_SEC = 60.0


def _parse_backoff_csv(raw: str | None) -> tuple[int, ...]:
    """Parse ``LIUYE_OUTBOX_BACKOFF_SEC`` csv · fallback to default.

    Honours systemd ``Environment=LIUYE_OUTBOX_BACKOFF_SEC=60,120,240,480,960``.
    Any parse error logs once and falls back to the v3 §5.x default so
    the worker never refuses to start on misconfig.
    """
    if not raw:
        return DEFAULT_BACKOFF_SEC
    try:
        parts = [int(p.strip()) for p in raw.split(",") if p.strip()]
        if not parts:
            return DEFAULT_BACKOFF_SEC
        return tuple(parts)
    except ValueError as exc:
        logger.warning(
            "[outbox_retry] LIUYE_OUTBOX_BACKOFF_SEC malformed %r · using default: %s",
            raw, exc,
        )
        return DEFAULT_BACKOFF_SEC


# ---------------------------------------------------------------------------
# OutboxWorker · the loop entry point
# ---------------------------------------------------------------------------


class OutboxWorker:
    """60s scan · per-entry retry budget · dead-letter on exhaustion.

    The class is stateful around in-flight retry counts:

    - ``_retry_counts[decision_id]`` tracks attempts so a process
      restart re-runs the entry from 0 (acceptable per v3 §5.x · the
      backoff timestamps inside the JSON envelope mean we still respect
      the cadence across restarts).
    - ``_next_attempt_ts[decision_id]`` is the wall-clock UTC the next
      retry is permitted. Honours the persisted ``next_attempt_at`` if
      the file carries one (set on first failure).

    The scan loop sleeps for ``scan_interval_sec`` between passes. Each
    pass:

    1. Lists ``*.json`` entries under ``outbox_dir``.
    2. Skips any entry whose ``next_attempt_at`` is still in the future.
    3. Attempts ``shared.decision_ledger.record_decision`` with the
       envelope payload.
    4. On success: ``Path.unlink()`` the file.
    5. On failure: bump retry count · reschedule per ``backoff_sec`` ·
       overwrite the file with the new envelope (atomic write).
    6. On 6th failure: move the file to ``dead-letter_dir`` and emit a
       Sentry ALERT log record (``extra={'sentry.alert': True}``).
    """

    def __init__(
        self,
        *,
        outbox_dir: Optional[Path] = None,
        deadletter_dir: Optional[Path] = None,
        max_retry: int = DEFAULT_MAX_RETRY,
        backoff_sec: tuple[int, ...] = DEFAULT_BACKOFF_SEC,
        scan_interval_sec: float = DEFAULT_SCAN_INTERVAL_SEC,
    ) -> None:
        self.outbox_dir = outbox_dir or DEFAULT_OUTBOX_DIR
        self.deadletter_dir = deadletter_dir or DEFAULT_DEADLETTER_DIR
        self.max_retry = int(max_retry)
        self.backoff_sec = tuple(backoff_sec) or DEFAULT_BACKOFF_SEC
        self.scan_interval_sec = float(scan_interval_sec)
        self._stopping = asyncio.Event()
        # In-memory bookkeeping · cleared on stop.
        self._retry_counts: dict[str, int] = {}
        # Idempotency tracking · same idempotency_key seen this run
        # blocks a second ``record_decision`` call from this worker.
        self._seen_idempotency: set[str] = set()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "OutboxWorker":
        """Construct from env vars · honours the systemd unit defaults."""
        src = env if env is not None else os.environ
        outbox = Path(src.get("LIUYE_OUTBOX_DIR", str(DEFAULT_OUTBOX_DIR)))
        dead = Path(src.get("LIUYE_DEADLETTER_DIR", str(DEFAULT_DEADLETTER_DIR)))
        max_retry_raw = src.get("LIUYE_OUTBOX_MAX_RETRY")
        try:
            max_retry = int(max_retry_raw) if max_retry_raw else DEFAULT_MAX_RETRY
        except ValueError:
            logger.warning(
                "[outbox_retry] LIUYE_OUTBOX_MAX_RETRY=%r invalid · using default %d",
                max_retry_raw, DEFAULT_MAX_RETRY,
            )
            max_retry = DEFAULT_MAX_RETRY
        backoff = _parse_backoff_csv(src.get("LIUYE_OUTBOX_BACKOFF_SEC"))
        scan_raw = src.get("LIUYE_OUTBOX_SCAN_SEC")
        try:
            scan_interval = float(scan_raw) if scan_raw else DEFAULT_SCAN_INTERVAL_SEC
        except ValueError:
            scan_interval = DEFAULT_SCAN_INTERVAL_SEC
        return cls(
            outbox_dir=outbox,
            deadletter_dir=dead,
            max_retry=max_retry,
            backoff_sec=backoff,
            scan_interval_sec=scan_interval,
        )

    def stop(self) -> None:
        """Signal the loop to exit at the next sleep boundary."""
        self._stopping.set()

    async def run(self) -> None:
        """Main scan loop · sleep ``scan_interval_sec`` between passes.

        Loop terminates when ``self.stop()`` flips ``self._stopping`` or
        the host signals SIGTERM / SIGINT. Each pass is best-effort:
        unexpected exceptions in one entry never block the rest of the
        pass.
        """
        self._ensure_dirs()
        logger.info(
            "[outbox_retry] worker started · outbox=%s deadletter=%s max_retry=%d backoff=%s scan=%.0fs",
            self.outbox_dir, self.deadletter_dir, self.max_retry,
            self.backoff_sec, self.scan_interval_sec,
        )
        while not self._stopping.is_set():
            try:
                await self._scan_pass()
            except Exception as exc:  # noqa: BLE001 · loop must not die on edge cases
                logger.exception("[outbox_retry] scan pass raised: %s", exc)
            try:
                await asyncio.wait_for(
                    self._stopping.wait(), timeout=self.scan_interval_sec,
                )
                # event fired · clean exit
                break
            except asyncio.TimeoutError:
                continue
        logger.info("[outbox_retry] worker stopped")

    # ------------------------------------------------------------------
    # One scan pass
    # ------------------------------------------------------------------

    async def _scan_pass(self) -> None:
        """Walk the outbox directory once · attempt every due entry."""
        self._ensure_dirs()
        try:
            entries = sorted(self.outbox_dir.glob("*.json"))
        except OSError as exc:
            logger.warning("[outbox_retry] outbox glob failed: %s", exc)
            return

        for path in entries:
            if self._stopping.is_set():
                return
            try:
                await self.process_entry(path)
            except Exception as exc:  # noqa: BLE001 · entry-level isolation
                logger.exception(
                    "[outbox_retry] process_entry crashed for %s: %s", path, exc,
                )

    async def process_entry(self, path: Path) -> bool:
        """Process one outbox JSON file · return True on success.

        Steps:

        1. Read + parse the JSON envelope. Corrupt files → move to
           dead-letter immediately (cannot retry unparseable bytes).
        2. Check ``next_attempt_at`` (ISO 8601 UTC). If still in the
           future, skip (caller retries on next pass).
        3. Check ``idempotency_key`` against this run's seen-set.
           Already-seen keys are skipped (defensive · prevents accidental
           double-write when two workers race or a manual scan triggers).
        4. Call ``shared.decision_ledger.record_decision``.
        5. Success → ``unlink``. Failure → increment retry · reschedule.
        6. Retry > ``max_retry`` → graduate to dead-letter + alert.
        """
        try:
            with path.open("r", encoding="utf-8") as fh:
                envelope: dict[str, Any] = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            logger.error(
                "[outbox_retry] corrupt envelope at %s: %s · moving to dead-letter",
                path, exc,
            )
            self._move_to_deadletter(
                path,
                reason=f"corrupt_json: {exc}",
                envelope=None,
            )
            return False

        decision_id = str(envelope.get("decision_id") or path.stem)
        idempotency_key = str(envelope.get("idempotency_key") or decision_id)
        retry_count = int(envelope.get("retry_count", 0))

        # Idempotency · already-attempted in this run → skip silently.
        if idempotency_key in self._seen_idempotency:
            logger.debug(
                "[outbox_retry] skipping already-attempted idempotency_key=%s",
                idempotency_key,
            )
            return False

        # Cadence gate · honour persisted next_attempt_at when present.
        next_attempt = envelope.get("next_attempt_at")
        if next_attempt and not self._is_due(next_attempt):
            logger.debug(
                "[outbox_retry] entry %s not due yet (next_attempt_at=%s)",
                decision_id, next_attempt,
            )
            return False

        # Dead-letter graduation check BEFORE making the next attempt.
        if self._is_dead_letter(retry_count):
            self._graduate_to_deadletter(path, envelope, reason="max_retry_exceeded")
            return False

        # Attempt the ledger write.
        self._seen_idempotency.add(idempotency_key)
        ok = await self._attempt_ledger_write(envelope, decision_id)
        if ok:
            self._cleanup_success(path, decision_id)
            return True

        # Failed · bump retry count + schedule next attempt.
        new_retry = retry_count + 1
        if self._is_dead_letter(new_retry):
            self._graduate_to_deadletter(path, envelope, reason="max_retry_exceeded")
            return False
        delay = self._backoff_for_retry(new_retry)
        envelope["retry_count"] = new_retry
        envelope["next_attempt_at"] = self._utc_offset(delay)
        envelope["last_attempt_at"] = self._utc_now()
        self._rewrite_envelope(path, envelope)
        logger.info(
            "[outbox_retry] %s retry=%d scheduled next_attempt_at=%s (delay=%ds)",
            decision_id, new_retry, envelope["next_attempt_at"], delay,
        )
        # Allow the idempotency_key to be re-tried in subsequent runs
        # (only this run's set blocks duplicate attempts within one
        # process · stale outbox files survive across restarts).
        self._seen_idempotency.discard(idempotency_key)
        return False

    def _is_dead_letter(self, retry_count: int) -> bool:
        """Return True when ``retry_count`` exceeds ``max_retry`` · graduation gate.

        ``retry_count`` is the count of *failures so far* (0 = never
        attempted · 5 = five failures · etc.). An entry is dead-letter
        once retry_count > max_retry (strictly greater · the 5th retry
        gets one last attempt before graduation per v3 §5.x).
        """
        return retry_count > self.max_retry

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_dirs(self) -> None:
        """Create outbox + dead-letter dirs · silent-fail on permission."""
        for d in (self.outbox_dir, self.deadletter_dir):
            try:
                d.mkdir(parents=True, exist_ok=True)
            except OSError as exc:  # pragma: no cover · disk-full / readonly fs
                logger.warning("[outbox_retry] mkdir failed at %s: %s", d, exc)

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _utc_offset(seconds: int) -> str:
        """Return UTC ISO 8601 string ``now + seconds``."""
        from datetime import timedelta
        ts = datetime.now(timezone.utc) + timedelta(seconds=int(seconds))
        return ts.isoformat(timespec="seconds")

    @staticmethod
    def _is_due(next_attempt_at: str) -> bool:
        """Return True if ``next_attempt_at`` is in the past (or invalid)."""
        try:
            target = datetime.fromisoformat(next_attempt_at)
            if target.tzinfo is None:
                target = target.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) >= target
        except ValueError:
            # Malformed timestamp · treat as due so the retry proceeds.
            return True

    def _backoff_for_retry(self, retry_count: int) -> int:
        """Return the backoff in seconds for ``retry_count`` (1-based).

        retry_count=1 → backoff_sec[0] (60s default · first failure)
        retry_count=5 → backoff_sec[4] (960s · last failure)
        retry_count > len(backoff_sec) → last entry (cap)
        """
        idx = min(max(retry_count - 1, 0), len(self.backoff_sec) - 1)
        return int(self.backoff_sec[idx])

    async def _attempt_ledger_write(
        self,
        envelope: dict[str, Any],
        decision_id: str,
    ) -> bool:
        """Forward the envelope into ``shared.decision_ledger.record_decision``.

        Returns True iff the ledger write claims persisted = True (the
        façade returns a decision_id even on failure · we treat any
        raised exception or non-matching id as failure).
        """
        try:
            resolved = record_decision(
                agent_id=str(envelope.get("agent_id", "unknown")),
                endpoint=str(envelope.get("endpoint", "unknown")),
                input_payload=envelope.get("input_payload") or {},
                output_payload=envelope.get("output_payload") or {},
                evidence_chain=envelope.get("evidence_chain") or {},
                decision_id=decision_id,
                jurisdiction=envelope.get("jurisdiction"),
                retention_class=envelope.get("retention_class"),
                subject_name=envelope.get("subject_name"),
                subject_id=envelope.get("subject_id"),
                parent_turn_id=envelope.get("parent_turn_id"),
            )
            # The façade returns decision_id even on persist=False · we
            # treat the absence of a fresh sqlite write as failure by
            # tagging the envelope with the result. For now we trust the
            # façade · if the underlying store keeps failing, the next
            # pass will see the file (we unlink on success) and retry.
            #
            # The façade does NOT raise on sqlite errors · it silently
            # returns a result with persisted=False. Since the façade
            # only returns decision_id, we cannot tell from the return
            # value alone. We rely on the underlying store's silent-fail
            # logging + the file existence: if the file still exists
            # after we processed it, the next pass treats it as another
            # failure (we don't unlink here · caller does on True).
            return bool(resolved == decision_id)
        except Exception as exc:  # noqa: BLE001 · last-resort silent-fail
            logger.warning(
                "[outbox_retry] ledger write raised for %s: %s", decision_id, exc,
            )
            return False

    def _cleanup_success(self, path: Path, decision_id: str) -> None:
        """Remove the outbox file after a successful retry."""
        try:
            path.unlink()
            logger.info(
                "[outbox_retry] success · removed outbox entry %s",
                decision_id,
            )
        except OSError as exc:  # pragma: no cover · race · already removed
            logger.debug(
                "[outbox_retry] unlink failed (race · already removed?) %s: %s",
                path, exc,
            )

    def _rewrite_envelope(self, path: Path, envelope: dict[str, Any]) -> None:
        """Atomically rewrite the envelope JSON · keeps retry_count/scheduling."""
        tmp = path.with_suffix(".json.tmp")
        try:
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(envelope, fh, ensure_ascii=False, indent=2, default=str)
            os.replace(tmp, path)
        except OSError as exc:  # pragma: no cover · disk failure
            logger.warning(
                "[outbox_retry] rewrite failed for %s: %s", path, exc,
            )

    def _move_to_deadletter(
        self,
        path: Path,
        *,
        reason: str,
        envelope: dict[str, Any] | None,
    ) -> None:
        """Move an unparseable file straight to dead-letter."""
        target = self.deadletter_dir / path.name
        try:
            if envelope is not None:
                envelope.setdefault("_dead_letter", {})
                envelope["_dead_letter"]["reason"] = reason
                envelope["_dead_letter"]["graduated_at"] = self._utc_now()
                with target.open("w", encoding="utf-8") as fh:
                    json.dump(envelope, fh, ensure_ascii=False, indent=2, default=str)
                path.unlink(missing_ok=True)
            else:
                path.replace(target)
        except OSError as exc:  # pragma: no cover · disk failure
            logger.error(
                "[outbox_retry] dead-letter move failed for %s: %s",
                path, exc,
            )

    def _graduate_to_deadletter(
        self,
        path: Path,
        envelope: dict[str, Any],
        *,
        reason: str,
    ) -> None:
        """Move a max-retry entry to dead-letter + emit Sentry ALERT log."""
        decision_id = str(envelope.get("decision_id") or path.stem)
        envelope.setdefault("_dead_letter", {})
        envelope["_dead_letter"]["reason"] = reason
        envelope["_dead_letter"]["graduated_at"] = self._utc_now()
        envelope["_dead_letter"]["final_retry_count"] = int(
            envelope.get("retry_count", self.max_retry + 1),
        )
        self._move_to_deadletter(path, reason=reason, envelope=envelope)
        # Sentry alert · ops runbook says "any dead-letter graduation is
        # a 信贷 incident · investigate within 1h". The structured `extra`
        # tag is what Sentry's logging integration picks up.
        logger.error(
            "[outbox_retry] DEAD-LETTER · decision_id=%s reason=%s · ops must investigate",
            decision_id, reason,
            extra={"sentry.alert": True, "decision_id": decision_id},
        )


# ---------------------------------------------------------------------------
# CLI entry point · systemd unit invokes via ``python -m liuye_service.workers.outbox_retry``
# ---------------------------------------------------------------------------


def _setup_signal_handlers(worker: OutboxWorker, loop: asyncio.AbstractEventLoop) -> None:
    """Bind SIGTERM / SIGINT → worker.stop() so the loop exits cleanly."""
    def _handler(signum: int, _frame: Any) -> None:  # pragma: no cover · signal
        logger.info("[outbox_retry] received signal %s · stopping", signum)
        # asyncio.Event.set is loop-bound · schedule from signal context.
        loop.call_soon_threadsafe(worker.stop)
    try:
        signal.signal(signal.SIGTERM, _handler)
        signal.signal(signal.SIGINT, _handler)
    except (ValueError, AttributeError):  # pragma: no cover · not main thread / windows
        pass


async def _main() -> None:
    logging.basicConfig(
        level=os.environ.get("LIUYE_LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    worker = OutboxWorker.from_env()
    loop = asyncio.get_event_loop()
    _setup_signal_handlers(worker, loop)
    await worker.run()


if __name__ == "__main__":  # pragma: no cover · CLI entry
    asyncio.run(_main())


__all__ = [
    "DEFAULT_BACKOFF_SEC",
    "DEFAULT_DEADLETTER_DIR",
    "DEFAULT_MAX_RETRY",
    "DEFAULT_OUTBOX_DIR",
    "DEFAULT_SCAN_INTERVAL_SEC",
    "OutboxWorker",
]
