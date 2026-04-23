"""Test launcher.add_worktree + scaffold_identity (no real mesh.json mutation)."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Allow `py scripts/orchestrator/tests/test_launcher.py` from project root.
_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent.parent))  # project_root/scripts

from orchestrator import launcher  # noqa: E402
from orchestrator.lib import identity  # noqa: E402


# ---------- mesh.json shape used in tests ----------

def _fake_mesh_dict() -> dict:
    return {
        "project": "fake_proj",
        "description": "test fixture",
        "protocol_version": "1.1",
        "worktrees": [
            {
                "name": "main",
                "path": "/tmp/fake/main",
                "branch": "chore/l0-infra",
                "role": "orchestrator",
                "description": "fake main",
            },
        ],
        "upstream_remote": "/tmp/fake/main",
        "decisions_log": "docs/handoff/decisions-log.md",
        "onboarding_dir": "docs/onboarding/",
        "contracts_dir": "docs/contracts/",
        "arch_contracts": "docs/arch/platform-contracts.md",
        "last_updated": "2026-01-01",
    }


def _write_fake_mesh(tmp: Path) -> Path:
    p = tmp / "mesh.json"
    p.write_text(json.dumps(_fake_mesh_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


# ---------- add_worktree ----------

def test_add_worktree_appends_entry():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        mesh_path = _write_fake_mesh(tmp)

        launcher.add_worktree(
            mesh_path,
            "agent-x",
            path="/tmp/fake/agent-x",
            branch="feat/agent-x",
            role="worker",
            description="test worker",
            onboarding="docs/onboarding/agent-x-phase-1.md",
            today="2026-04-23",
        )

        raw = json.loads(mesh_path.read_text(encoding="utf-8"))
        names = [w["name"] for w in raw["worktrees"]]
        assert "agent-x" in names, f"new worktree should appear, got {names}"

        entry = next(w for w in raw["worktrees"] if w["name"] == "agent-x")
        assert entry["path"] == "/tmp/fake/agent-x"
        assert entry["branch"] == "feat/agent-x"
        assert entry["role"] == "worker"
        assert entry["description"] == "test worker"
        assert entry["onboarding"] == "docs/onboarding/agent-x-phase-1.md"

        assert raw["last_updated"] == "2026-04-23", "last_updated should be bumped"


def test_add_worktree_rejects_duplicate():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        mesh_path = _write_fake_mesh(tmp)

        try:
            launcher.add_worktree(
                mesh_path,
                "main",  # already exists in fake mesh
                path="/tmp/fake/dup",
                branch="feat/dup",
                role="worker",
            )
        except ValueError as e:
            assert "already exists" in str(e), f"got: {e}"
        else:
            raise AssertionError("expected ValueError on duplicate name")

        # Confirm mesh.json was NOT mutated.
        raw = json.loads(mesh_path.read_text(encoding="utf-8"))
        assert len(raw["worktrees"]) == 1


def test_add_worktree_rejects_bad_role():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        mesh_path = _write_fake_mesh(tmp)

        try:
            launcher.add_worktree(
                mesh_path,
                "agent-y",
                path="/tmp/fake/agent-y",
                branch="feat/agent-y",
                role="overlord",  # invalid
            )
        except ValueError as e:
            assert "invalid role" in str(e)
        else:
            raise AssertionError("expected ValueError on bad role")


def test_add_worktree_preserves_top_level_keys():
    """Round-trip should keep top-level key order stable for clean diffs."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        mesh_path = _write_fake_mesh(tmp)

        launcher.add_worktree(
            mesh_path,
            "agent-z",
            path="/tmp/fake/agent-z",
            branch="feat/agent-z",
            role="worker",
            today="2026-04-23",
        )

        # Re-read raw text, check key order at top level.
        raw_obj = json.loads(mesh_path.read_text(encoding="utf-8"))
        expected_first_keys = [
            "project",
            "description",
            "protocol_version",
            "worktrees",
            "upstream_remote",
        ]
        actual_keys = list(raw_obj.keys())
        for i, k in enumerate(expected_first_keys):
            assert actual_keys[i] == k, (
                f"key order drifted at idx {i}: expected {k}, got {actual_keys[i]}"
            )


# ---------- scaffold_identity ----------

def test_scaffold_identity_writes_template():
    with tempfile.TemporaryDirectory() as td:
        wt = Path(td) / "worktree-x"
        target, written = launcher.scaffold_identity(
            wt,
            role="worker",
            branch="feat/x",
            upstream="/tmp/fake/main",
            onboarding="docs/onboarding/x-phase-1.md",
        )
        assert written is True
        assert target.exists()
        text = target.read_text(encoding="utf-8")

        # Key fields appear
        assert "角色：worker" in text
        assert "分支：feat/x" in text
        assert "Upstream remote：/tmp/fake/main" in text
        # onboarding line
        assert "docs/onboarding/x-phase-1.md" in text
        # standard sections
        assert "Resume 必读清单" in text
        assert "EXPECTED_NEXT_SIGNAL" in text
        assert "红线" in text


def test_scaffold_identity_skips_existing():
    with tempfile.TemporaryDirectory() as td:
        wt = Path(td) / "worktree-y"
        wt.mkdir()
        existing = wt / "AGENT_IDENTITY.md"
        existing.write_text("# pre-existing user content\n", encoding="utf-8")

        target, written = launcher.scaffold_identity(
            wt,
            role="worker",
            branch="feat/y",
            upstream="/tmp/fake/main",
        )
        assert written is False
        # Untouched
        assert existing.read_text(encoding="utf-8") == "# pre-existing user content\n"
        assert target == existing


def test_scaffold_then_identity_load_roundtrip():
    """End-to-end: scaffold a file, then identity.load() pulls fields back out."""
    with tempfile.TemporaryDirectory() as td:
        wt = Path(td) / "worktree-rt"
        launcher.scaffold_identity(
            wt,
            role="worker",
            branch="feat/rt",
            upstream="/tmp/fake/main",
            onboarding="docs/onboarding/rt-phase-1.md",
        )

        loaded = identity.load(wt)
        assert loaded is not None
        assert loaded.role == "worker"
        assert loaded.branch == "feat/rt"
        assert loaded.upstream == "/tmp/fake/main"
        assert loaded.worktree == wt


def test_identity_load_missing_returns_none():
    with tempfile.TemporaryDirectory() as td:
        wt = Path(td) / "empty-wt"
        wt.mkdir()
        assert identity.load(wt) is None


def test_identity_load_grep_with_emphasis():
    """Real-world AGENT_IDENTITY.md uses **bold** + Chinese keys + backticks."""
    with tempfile.TemporaryDirectory() as td:
        wt = Path(td) / "fancy-wt"
        wt.mkdir()
        (wt / "AGENT_IDENTITY.md").write_text(
            "# Header\n"
            "## 我是谁\n"
            "- **角色**：orchestrator (主 CLI)\n"
            "- **分支**：`chore/l0-infra`\n"
            "- **Upstream**：自己即 upstream\n"
            "- **职责**：批示 / 仲裁 / 基建\n",
            encoding="utf-8",
        )

        loaded = identity.load(wt)
        assert loaded is not None
        assert loaded.role == "orchestrator (主 CLI)", f"got {loaded.role!r}"
        assert loaded.branch == "chore/l0-infra", f"got {loaded.branch!r}"
        assert loaded.upstream == "自己即 upstream", f"got {loaded.upstream!r}"
        assert "批示" in (loaded.duty or ""), f"got {loaded.duty!r}"


if __name__ == "__main__":
    tests = [
        test_add_worktree_appends_entry,
        test_add_worktree_rejects_duplicate,
        test_add_worktree_rejects_bad_role,
        test_add_worktree_preserves_top_level_keys,
        test_scaffold_identity_writes_template,
        test_scaffold_identity_skips_existing,
        test_scaffold_then_identity_load_roundtrip,
        test_identity_load_missing_returns_none,
        test_identity_load_grep_with_emphasis,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"[OK] {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"[FAIL] {t.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"[ERROR] {t.__name__}: {type(e).__name__}: {e}")
    if failed:
        print(f"\n[FAIL] {failed}/{len(tests)} launcher tests failed")
        sys.exit(1)
    print(f"\n[ALL PASS] {len(tests)} launcher tests")
