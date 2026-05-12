# -*- coding: utf-8 -*-
"""liuye_service.tests.test_outbox — OutboxWorker retry + dead-letter + idempotency.

Per W1-backend brief §5 DoD + ``liuye_service/CLAUDE.md`` §11 (file 18) +
v3 §5.x + ``deploy/liuye-outbox.service`` systemd unit.

Test surfaces:

1. ``_is_dead_letter`` boundary · retry_count > max_retry triggers
2. backoff schedule · ``_backoff_for_retry(n)`` returns correct seconds
3. ``process_entry`` success path · ledger write OK → unlink outbox file
4. ``process_entry`` failure path · increment retry + reschedule
5. dead-letter graduation · ``retry_count > max_retry`` moves to dead-letter
6. idempotency_key dedup · same key processed twice in one run → 1 ledger call
7. corrupt JSON handling · move straight to dead-letter
8. envelope payload preservation · re-write keeps the original fields

All sqlite + filesystem effects are confined to ``tmp_path`` fixtures.
We monkeypatch ``shared.decision_ledger.record_decision`` so the tests
don't touch the production ledger sqlite file.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from liuye_service.workers.outbox_retry import (
    DEFAULT_BACKOFF_SEC,
    DEFAULT_MAX_RETRY,
    DEFAULT_SCAN_INTERVAL_SEC,
    OutboxWorker,
    _parse_backoff_csv,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_outbox(tmp_path: Path) -> tuple[Path, Path]:
    """Provide isolated outbox + dead-letter dirs for one test."""
    outbox = tmp_path / "outbox"
    dead = tmp_path / "dead-letter"
    outbox.mkdir(parents=True, exist_ok=True)
    dead.mkdir(parents=True, exist_ok=True)
    return outbox, dead


@pytest.fixture
def envelope_factory() -> Any:
    """Return a callable that builds a minimal outbox envelope."""

    def _make(
        decision_id: str = "dec_test_001",
        *,
        retry_count: int = 0,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return {
            "decision_id": decision_id,
            "agent_id": "credit",
            "endpoint": "/api/liuye/sessions",
            "input_payload": {"applied_product": "CORP_CREDIT"},
            "output_payload": {"verdict": "PASS"},
            "evidence_chain": {"trace_id": "trace_test"},
            "jurisdiction": "HQ",
            "retention_class": "standard",
            "subject_name": None,
            "subject_id": None,
            "parent_turn_id": None,
            "retry_count": retry_count,
            "idempotency_key": idempotency_key or decision_id,
        }

    return _make


def _write_envelope(outbox: Path, envelope: dict[str, Any]) -> Path:
    """Drop an envelope JSON onto the outbox dir · return the path."""
    target = outbox / f"{envelope['decision_id']}.json"
    target.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


# ---------------------------------------------------------------------------
# 1. _is_dead_letter boundary
# ---------------------------------------------------------------------------


def test_is_dead_letter_boundary() -> None:
    """``retry_count > max_retry`` is the graduation threshold."""
    w = OutboxWorker(max_retry=5)
    assert not w._is_dead_letter(0)
    assert not w._is_dead_letter(5)  # exactly max_retry · still alive
    assert w._is_dead_letter(6)      # one more failure · graduate
    assert w._is_dead_letter(99)


def test_is_dead_letter_with_custom_max_retry() -> None:
    """``max_retry`` is configurable · graduation tracks it."""
    w = OutboxWorker(max_retry=3)
    assert not w._is_dead_letter(3)
    assert w._is_dead_letter(4)


# ---------------------------------------------------------------------------
# 2. Backoff schedule
# ---------------------------------------------------------------------------


def test_backoff_schedule_v3_spec_locked() -> None:
    """``DEFAULT_BACKOFF_SEC`` matches v3 §5.x · 60 / 120 / 240 / 480 / 960."""
    assert DEFAULT_BACKOFF_SEC == (60, 120, 240, 480, 960)


def test_backoff_for_retry_index() -> None:
    """``_backoff_for_retry(n)`` returns the n-th backoff (1-based)."""
    w = OutboxWorker()
    assert w._backoff_for_retry(1) == 60
    assert w._backoff_for_retry(2) == 120
    assert w._backoff_for_retry(3) == 240
    assert w._backoff_for_retry(4) == 480
    assert w._backoff_for_retry(5) == 960


def test_backoff_for_retry_clamps_at_last() -> None:
    """Beyond the last backoff entry · cap at the final value (defensive)."""
    w = OutboxWorker()
    assert w._backoff_for_retry(10) == 960
    assert w._backoff_for_retry(99) == 960


def test_backoff_for_retry_handles_zero_one_off() -> None:
    """``_backoff_for_retry(0)`` clamps to first (idx 0 protects from negative)."""
    w = OutboxWorker()
    assert w._backoff_for_retry(0) == 60


def test_parse_backoff_csv_valid() -> None:
    assert _parse_backoff_csv("60,120,240") == (60, 120, 240)


def test_parse_backoff_csv_missing_falls_back() -> None:
    assert _parse_backoff_csv(None) == DEFAULT_BACKOFF_SEC
    assert _parse_backoff_csv("") == DEFAULT_BACKOFF_SEC


def test_parse_backoff_csv_malformed_falls_back() -> None:
    assert _parse_backoff_csv("bogus,values") == DEFAULT_BACKOFF_SEC


# ---------------------------------------------------------------------------
# 3. process_entry success path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_entry_success_unlinks(
    tmp_outbox: tuple[Path, Path],
    envelope_factory: Any,
) -> None:
    outbox, dead = tmp_outbox
    env = envelope_factory("dec_ok_001")
    path = _write_envelope(outbox, env)
    worker = OutboxWorker(outbox_dir=outbox, deadletter_dir=dead)

    with patch(
        "liuye_service.workers.outbox_retry.record_decision",
        return_value="dec_ok_001",
    ) as mocked:
        ok = await worker.process_entry(path)

    assert ok is True
    assert not path.exists(), "successful retry must unlink the outbox file"
    # Forwarded all the kwargs from the envelope.
    mocked.assert_called_once()
    kwargs = mocked.call_args.kwargs
    assert kwargs["decision_id"] == "dec_ok_001"
    assert kwargs["agent_id"] == "credit"
    assert kwargs["retention_class"] == "standard"
    assert kwargs["parent_turn_id"] is None


# ---------------------------------------------------------------------------
# 4. process_entry failure path · increment + reschedule
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_entry_failure_reschedules(
    tmp_outbox: tuple[Path, Path],
    envelope_factory: Any,
) -> None:
    outbox, dead = tmp_outbox
    env = envelope_factory("dec_fail_001")
    path = _write_envelope(outbox, env)
    worker = OutboxWorker(outbox_dir=outbox, deadletter_dir=dead)

    # record_decision raises · we count this as a failure.
    with patch(
        "liuye_service.workers.outbox_retry.record_decision",
        side_effect=RuntimeError("sqlite locked"),
    ):
        ok = await worker.process_entry(path)

    assert ok is False
    # File still on disk · reschedule recorded.
    assert path.exists()
    new_env = json.loads(path.read_text(encoding="utf-8"))
    assert new_env["retry_count"] == 1
    assert "next_attempt_at" in new_env
    assert "last_attempt_at" in new_env
    # idempotency_key preserved across the rewrite.
    assert new_env["idempotency_key"] == env["idempotency_key"]


# ---------------------------------------------------------------------------
# 5. Dead-letter graduation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dead_letter_after_max_retry(
    tmp_outbox: tuple[Path, Path],
    envelope_factory: Any,
) -> None:
    """Envelope already at retry_count=5 fails again → moves to dead-letter."""
    outbox, dead = tmp_outbox
    env = envelope_factory("dec_dead_001", retry_count=5)
    path = _write_envelope(outbox, env)
    worker = OutboxWorker(outbox_dir=outbox, deadletter_dir=dead)

    with patch(
        "liuye_service.workers.outbox_retry.record_decision",
        side_effect=RuntimeError("still failing"),
    ):
        ok = await worker.process_entry(path)

    assert ok is False
    assert not path.exists(), "graduated entry must leave the outbox"
    dead_file = dead / "dec_dead_001.json"
    assert dead_file.exists(), "dead-letter file must be created"
    payload = json.loads(dead_file.read_text(encoding="utf-8"))
    assert payload.get("_dead_letter", {}).get("reason") == "max_retry_exceeded"


@pytest.mark.asyncio
async def test_dead_letter_skips_attempt_for_already_max(
    tmp_outbox: tuple[Path, Path],
    envelope_factory: Any,
) -> None:
    """Entry whose retry_count already exceeds max_retry graduates without a write attempt."""
    outbox, dead = tmp_outbox
    env = envelope_factory("dec_skip_001", retry_count=10)
    path = _write_envelope(outbox, env)
    worker = OutboxWorker(outbox_dir=outbox, deadletter_dir=dead)

    with patch(
        "liuye_service.workers.outbox_retry.record_decision",
    ) as mocked:
        ok = await worker.process_entry(path)

    assert ok is False
    mocked.assert_not_called()
    assert (dead / "dec_skip_001.json").exists()


# ---------------------------------------------------------------------------
# 6. idempotency_key dedup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_idempotency_key_blocks_double_attempt_in_one_run(
    tmp_outbox: tuple[Path, Path],
    envelope_factory: Any,
) -> None:
    """The same idempotency_key processed twice in one run → 1 ledger call."""
    outbox, dead = tmp_outbox
    env = envelope_factory("dec_idem_001", idempotency_key="idem_shared")
    path = _write_envelope(outbox, env)
    worker = OutboxWorker(outbox_dir=outbox, deadletter_dir=dead)

    with patch(
        "liuye_service.workers.outbox_retry.record_decision",
        return_value="dec_idem_001",
    ) as mocked:
        # First call · success path · file unlinked.
        await worker.process_entry(path)
        # Manually re-create the envelope · second call should skip.
        _write_envelope(outbox, env)
        await worker.process_entry(path)

    # Only the FIRST process_entry called record_decision.
    assert mocked.call_count == 1, (
        f"idempotency_key reuse must not trigger a second ledger write · "
        f"got {mocked.call_count} calls"
    )


# ---------------------------------------------------------------------------
# 7. Corrupt JSON handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_corrupt_json_moves_to_dead_letter(
    tmp_outbox: tuple[Path, Path],
) -> None:
    outbox, dead = tmp_outbox
    bad_path = outbox / "dec_corrupt_001.json"
    bad_path.write_text("{this is not valid json", encoding="utf-8")
    worker = OutboxWorker(outbox_dir=outbox, deadletter_dir=dead)

    with patch(
        "liuye_service.workers.outbox_retry.record_decision",
    ) as mocked:
        ok = await worker.process_entry(bad_path)

    assert ok is False
    mocked.assert_not_called()
    assert not bad_path.exists()
    assert (dead / "dec_corrupt_001.json").exists()


# ---------------------------------------------------------------------------
# 8. Cadence gate · next_attempt_at in the future blocks retry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_future_next_attempt_at_blocks_retry(
    tmp_outbox: tuple[Path, Path],
    envelope_factory: Any,
) -> None:
    """An envelope with future ``next_attempt_at`` is skipped this pass."""
    outbox, dead = tmp_outbox
    env = envelope_factory("dec_future_001")
    # 1 hour in the future
    from datetime import datetime, timedelta, timezone
    env["next_attempt_at"] = (
        datetime.now(timezone.utc) + timedelta(hours=1)
    ).isoformat(timespec="seconds")
    env["retry_count"] = 1
    path = _write_envelope(outbox, env)
    worker = OutboxWorker(outbox_dir=outbox, deadletter_dir=dead)

    with patch(
        "liuye_service.workers.outbox_retry.record_decision",
    ) as mocked:
        ok = await worker.process_entry(path)

    assert ok is False
    mocked.assert_not_called()
    assert path.exists(), "future-scheduled entry must stay in outbox"


# ---------------------------------------------------------------------------
# 9. run loop · stop signal exits cleanly within one scan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_loop_stops_on_signal(
    tmp_outbox: tuple[Path, Path],
) -> None:
    """``worker.stop()`` flips the event · run() returns promptly."""
    outbox, dead = tmp_outbox
    worker = OutboxWorker(
        outbox_dir=outbox, deadletter_dir=dead,
        scan_interval_sec=0.01,  # tight loop for the test
    )
    # Schedule stop after one scan tick.
    async def _stop_soon() -> None:
        await asyncio.sleep(0.02)
        worker.stop()

    asyncio.create_task(_stop_soon())
    # Should return without hanging.
    await asyncio.wait_for(worker.run(), timeout=2.0)


# ---------------------------------------------------------------------------
# 10. from_env honours systemd unit defaults
# ---------------------------------------------------------------------------


def test_from_env_defaults() -> None:
    w = OutboxWorker.from_env(env={})
    assert w.max_retry == DEFAULT_MAX_RETRY
    assert w.backoff_sec == DEFAULT_BACKOFF_SEC
    assert w.scan_interval_sec == DEFAULT_SCAN_INTERVAL_SEC


def test_from_env_overrides() -> None:
    """systemd Environment= values override defaults."""
    env = {
        "LIUYE_OUTBOX_MAX_RETRY": "3",
        "LIUYE_OUTBOX_BACKOFF_SEC": "10,20,30",
        "LIUYE_OUTBOX_SCAN_SEC": "5",
    }
    w = OutboxWorker.from_env(env=env)
    assert w.max_retry == 3
    assert w.backoff_sec == (10, 20, 30)
    assert w.scan_interval_sec == 5.0


def test_from_env_invalid_max_retry_falls_back() -> None:
    env = {"LIUYE_OUTBOX_MAX_RETRY": "not-a-number"}
    w = OutboxWorker.from_env(env=env)
    assert w.max_retry == DEFAULT_MAX_RETRY
