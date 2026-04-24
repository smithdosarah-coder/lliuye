"""End-to-end integration tests for the orchestrator pipeline.

Uses real subprocess-driven git fixtures instead of mocks so we actually
exercise the git CLI contract (our historical bug surface — Windows encoding,
worktree path quoting, log parsing).

Skipped if ``git`` is not on PATH.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent.parent))

from orchestrator import launcher, recovery, scoreboard, watchdog  # noqa: E402
from orchestrator.lib import mesh as mesh_lib  # noqa: E402


pytestmark = pytest.mark.skipif(
    shutil.which("git") is None,
    reason="integration tests require git on PATH",
)


# ---------- git fixtures -----------------------------------------------------

def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        check=check,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    # -b main requires git 2.28+; older installs may fall back to whatever
    # init.defaultBranch resolves to. The rest of the test is branch-agnostic.
    subprocess.run(
        ["git", "init", "-b", "main", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Mesh Integration Test")
    _git(path, "config", "commit.gpgsign", "false")


def _commit(repo: Path, msg: str, filename: str = "note.md") -> None:
    (repo / filename).write_text("content " + msg[:20], encoding="utf-8")
    _git(repo, "add", filename)
    # -m is passed verbatim; the body (with Signal trailer) survives.
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", msg],
        check=True,
        capture_output=True,
        text=True,
    )


def _write_mesh_json(root: Path, worktrees: list) -> Path:
    docs = root / "docs" / "handoff"
    docs.mkdir(parents=True, exist_ok=True)
    payload = {
        "project": "integration-test",
        "project_id": "integration-test",
        "description": "fixture",
        "schema_version": 1,
        "protocol_version": "1.1",
        "worktrees": worktrees,
        "upstream_remote": str(root).replace("\\", "/"),
        "decisions_log": "docs/handoff/decisions-log.md",
        "onboarding_dir": "docs/onboarding/",
        "contracts_dir": "docs/contracts/",
        "arch_contracts": "docs/arch/platform-contracts.md",
        "last_updated": "2026-04-24",
    }
    mesh_path = docs / "mesh.json"
    mesh_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return mesh_path


# ---------- end-to-end cases -------------------------------------------------

def test_signal_commit_flows_through_scoreboard_and_watchdog():
    """commit carrying Signal → scoreboard sees it → watchdog marks fresh."""
    with tempfile.TemporaryDirectory() as td_str:
        td = Path(td_str)
        wt = td / "wt1"
        _init_repo(wt)
        _commit(
            wt,
            "feat: smoke\n\nDoes a thing.\n\nSignal: REVIEW-READY\n",
        )

        mesh_path = _write_mesh_json(
            td,
            [
                {
                    "name": "wt1",
                    "path": str(wt).replace("\\", "/"),
                    "branch": "main",
                    "role": "worker",
                }
            ],
        )

        m = mesh_lib.load(mesh_path)
        assert len(m.worktrees) == 1

        records = scoreboard.collect_all(m)
        assert len(records) == 1
        rec = records[0]
        assert rec.last_signal == "REVIEW-READY", f"got {rec.last_signal!r}"
        assert rec.head_sha is not None
        assert rec.last_signal_age_seconds is not None and rec.last_signal_age_seconds >= 0
        assert rec.status == "fresh", f"fresh commit should be fresh, got {rec.status!r}"

        # Watchdog: feed the mesh directly (skip cwd walking for portability).
        events_path = td / "docs" / "handoff" / "watchdog-events.jsonl"
        state = watchdog.run_tick(
            tick=1,
            events_path=events_path,
            state={},
            m=m,
        )
        assert state["wt1"]["last_event"] == "fresh", state

        # Recovery --all-stuck should find nothing when no state file exists yet.
        stuck = recovery._read_stuck_names(
            td / "docs" / "handoff" / ".watchdog-state.json"
        )
        assert stuck == []


def test_launcher_register_makes_new_worktree_visible_to_scoreboard():
    """launcher.add_worktree → mesh reload → scoreboard sees the extra row."""
    with tempfile.TemporaryDirectory() as td_str:
        td = Path(td_str)

        # Seed with just the orchestrator so we can register a worker later.
        main_wt = td / "main"
        _init_repo(main_wt)
        _commit(main_wt, "init\n\nSignal: MESH-INIT")

        mesh_path = _write_mesh_json(
            td,
            [
                {
                    "name": "main",
                    "path": str(main_wt).replace("\\", "/"),
                    "branch": "main",
                    "role": "orchestrator",
                }
            ],
        )
        assert len(mesh_lib.load(mesh_path).worktrees) == 1

        # Register a second worktree + scaffold its identity file.
        worker_wt = td / "worker-a"
        _init_repo(worker_wt)
        _commit(worker_wt, "kickoff\n\nSignal: MESH-REGISTRY-UPDATED")

        launcher.add_worktree(
            mesh_path,
            "worker-a",
            path=str(worker_wt).replace("\\", "/"),
            branch="main",
            role="worker",
            description="integration-test worker",
            today="2026-04-24",
        )
        target, written = launcher.scaffold_identity(
            worker_wt,
            role="worker",
            branch="main",
            upstream=str(td).replace("\\", "/"),
            onboarding="docs/onboarding/worker-a-phase-1.md",
        )
        assert written is True
        assert target.exists()

        # Reload + verify scoreboard row count + signal propagation.
        m2 = mesh_lib.load(mesh_path)
        names = sorted(w.name for w in m2.worktrees)
        assert names == ["main", "worker-a"]

        records = scoreboard.collect_all(m2)
        by_name = {r.name: r for r in records}
        assert by_name["main"].last_signal == "MESH-INIT"
        assert by_name["worker-a"].last_signal == "MESH-REGISTRY-UPDATED"

        # Raw JSON payload should also include the new worktree.
        raw = json.loads(scoreboard.render_json_payload(m2))
        assert raw["project_id"] == "integration-test"
        assert raw["worktree_count"] == 2
        registered = [w["name"] for w in raw["worktrees"]]
        assert "worker-a" in registered
