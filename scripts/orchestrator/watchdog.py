"""Mesh watchdog daemon - tick every N seconds, detect stuck worktrees, emit jsonl events.

Usage:
    py scripts/orchestrator/watchdog.py [--interval 60] [--once]

Behavior (per tick):
  - Load mesh, walk every worktree.
  - Compute head_sha + commit_age_seconds.
  - Cache HEAD sha across ticks: skip last_commit_with_signal if HEAD unchanged.
  - Stuck detection (mark only, do NOT auto-recover):
      * worker + age > 1h + HEAD unchanged since last tick -> stuck:idle-1h
      * worker + age > 3d                                  -> stuck:abandoned-3d
      * head_sha unreachable                               -> stuck:git-unreachable
  - Append events to docs/handoff/watchdog-events.jsonl (one JSON per line).
  - Persist last-tick state to docs/handoff/.watchdog-state.json so restart resumes.

v1 = detect + log. Recovery is a separate module's job.
"""
from __future__ import annotations

import argparse
import json
import signal as _pysignal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# sys.path hack: scripts/ on path so `from orchestrator.lib import ...` resolves
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.lib import git_helpers, mesh  # noqa: E402
from orchestrator import scoreboard  # noqa: E402  (used for mesh-status.json render)


# ---- thresholds (seconds) ---------------------------------------------------
# These constants remain as the legacy defaults; mesh.json `thresholds` block
# (Y2) overrides them per project. Tag names ("stuck:idle-1h" / "stuck:abandoned-3d")
# are preserved for consumer stability — the "1h"/"3d" suffix is semantic
# ("looks idle" / "looks abandoned"), not a literal reading of the threshold.
IDLE_THRESHOLD = 3600          # 1 hour (legacy default)
ABANDONED_THRESHOLD = 86400 * 3  # 3 days (legacy default)


def detect_stuck(
    worktree: mesh.Worktree,
    head_sha: Optional[str],
    age: Optional[int],
    prev_sha: Optional[str],
    *,
    idle_threshold: int = IDLE_THRESHOLD,
    abandoned_threshold: int = ABANDONED_THRESHOLD,
    unreachable_subtype: Optional[str] = None,
) -> Optional[str]:
    """Pure stuck-classification function. Returns event tag or None.

    Args:
        worktree: the worktree under inspection
        head_sha: current HEAD sha, or None if git unreachable
        age: commit_age_seconds, or None
        prev_sha: HEAD sha recorded last tick, or None on first sight
        idle_threshold: seconds of silence before a worker is flagged idle
            (kwarg-only; defaults to IDLE_THRESHOLD)
        abandoned_threshold: seconds before a worker is flagged abandoned
            (kwarg-only; defaults to ABANDONED_THRESHOLD)
        unreachable_subtype: when ``head_sha is None``, the caller may
            supply a finer-grained category from
            ``git_helpers.diagnose_unreachable`` — one of
            'path-missing', 'perm-denied', 'binary-missing', 'unreachable'
            — which becomes ``stuck:git-<subtype>``. Legacy callers passing
            None still get the umbrella ``stuck:git-unreachable`` tag.

    Returns:
        "stuck:git-unreachable" | "stuck:git-path-missing" |
        "stuck:git-perm-denied" | "stuck:git-binary-missing" |
        "stuck:abandoned-3d" | "stuck:idle-1h" | None
    """
    # git unreachable trumps everything (could be a deleted/corrupt worktree)
    if head_sha is None:
        if unreachable_subtype and unreachable_subtype != "unreachable":
            return f"stuck:git-{unreachable_subtype}"
        return "stuck:git-unreachable"

    # only workers can be stuck; orchestrator is meant to idle
    if worktree.role != "worker":
        return None

    if age is None:
        return None

    # abandoned takes priority over idle (longer threshold = stronger signal)
    if age > abandoned_threshold:
        return "stuck:abandoned-3d"

    # idle-1h requires both age AND no movement since last tick
    if age > idle_threshold and prev_sha is not None and prev_sha == head_sha:
        return "stuck:idle-1h"

    return None


# ---- daemon plumbing --------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _events_path(mesh_obj: mesh.Mesh) -> Path:
    """Resolve docs/handoff/watchdog-events.jsonl relative to mesh.json location."""
    # walk up from cwd same way mesh.load does, then anchor to docs/handoff/
    cur = Path.cwd().resolve()
    for _ in range(20):
        candidate = cur / "docs" / "handoff"
        if (candidate / "mesh.json").exists():
            return candidate / "watchdog-events.jsonl"
        if cur.parent == cur:
            break
        cur = cur.parent
    # fallback: alongside cwd
    return Path("docs/handoff/watchdog-events.jsonl").resolve()


def _state_path(events_path: Path) -> Path:
    return events_path.parent / ".watchdog-state.json"


def _append_event(events_path: Path, payload: Dict[str, Any]) -> None:
    events_path.parent.mkdir(parents=True, exist_ok=True)
    # one JSON per line, NO pretty-print (keeps jsonl parseable)
    with events_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _load_state(state_path: Path) -> Dict[str, Dict[str, Any]]:
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(state_path: Path, state: Dict[str, Dict[str, Any]]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_mesh_status(
    events_path: Path,
    m: mesh.Mesh,
    state: Optional[Dict[str, Dict[str, Any]]] = None,
) -> None:
    """Refresh docs/handoff/mesh-status.json with stuck_event from watchdog state.

    Failures are non-fatal (log to stderr, daemon keeps running).
    """
    target = events_path.parent / "mesh-status.json"
    try:
        stuck_state = {}
        if state:
            for name, info in state.items():
                ev = info.get("last_event") if isinstance(info, dict) else None
                if isinstance(ev, str) and ev.startswith("stuck:"):
                    stuck_state[name] = ev
        target.write_text(
            scoreboard.render_json_payload(m, stuck_state=stuck_state),
            encoding="utf-8",
        )
    except Exception as e:  # noqa: BLE001
        print(f"[watchdog] WARN: mesh-status write failed: {e}", file=sys.stderr)


def run_tick(
    tick: int,
    events_path: Path,
    state: Dict[str, Dict[str, Any]],
    m: Optional[mesh.Mesh] = None,
) -> Dict[str, Dict[str, Any]]:
    """Run one watchdog tick. Mutates+returns state. Optionally accepts pre-loaded mesh."""
    if m is None:
        m = mesh.load()
    ts = _now_iso()

    # Pull per-mesh thresholds, falling back to module defaults (Y2).
    idle_th = int(m.thresholds.get("idle_seconds", IDLE_THRESHOLD))
    abandoned_th = int(m.thresholds.get("abandoned_seconds", ABANDONED_THRESHOLD))

    for w in m.worktrees:
        prev = state.get(w.name, {})
        prev_sha = prev.get("head_sha")
        prev_status = prev.get("last_event")

        sha = git_helpers.head_sha(w.path)
        age = git_helpers.commit_age_seconds(w.path) if sha else None
        unreachable_subtype = (
            git_helpers.diagnose_unreachable(w.path) if sha is None else None
        )

        # cache: if HEAD unchanged, skip the heavier last_commit_with_signal call
        # (tick still proceeds; we just don't re-parse the log)
        if sha is not None and sha == prev_sha:
            details = "head-unchanged-since-last-tick"
        else:
            details = "head-changed-or-first-sight"

        event_tag = detect_stuck(
            w, sha, age, prev_sha,
            idle_threshold=idle_th,
            abandoned_threshold=abandoned_th,
            unreachable_subtype=unreachable_subtype,
        )
        is_status_change = False
        if event_tag is None:
            # only emit "fresh" when status flipped from a stuck state
            if prev_status and prev_status.startswith("stuck:"):
                event_tag = "fresh"
                is_status_change = True
            else:
                event_tag = "fresh"
        elif event_tag != prev_status:
            is_status_change = True

        # always write per-worktree event for the tick (audit trail)
        _append_event(events_path, {
            "ts": ts,
            "tick": tick,
            "worktree": w.name,
            "role": w.role,
            "event": event_tag,
            "head_sha": sha,
            "age_seconds": age,
            "details": details + (";status-change" if is_status_change else ""),
        })

        state[w.name] = {
            "head_sha": sha,
            "age_seconds": age,
            "last_tick": tick,
            "last_event": event_tag,
            "last_seen_ts": ts,
        }

    return state


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Mesh watchdog daemon")
    parser.add_argument("--interval", type=int, default=60, help="tick interval seconds")
    parser.add_argument("--once", action="store_true", help="run one tick then exit")
    args = parser.parse_args(argv)

    m = mesh.load()
    events_path = _events_path(m)
    state_path = _state_path(events_path)
    state = _load_state(state_path)

    _append_event(events_path, {
        "ts": _now_iso(),
        "event": "watchdog-started",
        "interval": args.interval,
        "worktree_count": len(m.worktrees),
        "once": args.once,
    })

    stop = {"flag": False}

    def _handle_sigint(_signum, _frame):  # noqa: ANN001
        stop["flag"] = True

    try:
        _pysignal.signal(_pysignal.SIGINT, _handle_sigint)
    except (ValueError, OSError):
        # not in main thread or platform refuses; Ctrl+C will still raise KeyboardInterrupt
        pass

    tick = 0
    try:
        while not stop["flag"]:
            tick += 1
            m_tick = mesh.load()
            state = run_tick(tick, events_path, state, m=m_tick)
            _save_state(state_path, state)
            _write_mesh_status(events_path, m_tick, state=state)
            if args.once:
                break
            # interruptible sleep: many short naps so Ctrl+C lands quickly
            slept = 0
            while slept < args.interval and not stop["flag"]:
                time.sleep(min(1, args.interval - slept))
                slept += 1
    except KeyboardInterrupt:
        stop["flag"] = True
    finally:
        _append_event(events_path, {
            "ts": _now_iso(),
            "event": "watchdog-stopped",
            "ticks_completed": tick,
        })

    return 0


if __name__ == "__main__":
    sys.exit(main())
