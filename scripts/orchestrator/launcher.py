"""Launcher · register a new worktree into mesh.json + scaffold AGENT_IDENTITY.md.

Usage:

    py scripts/orchestrator/launcher.py register <name> \
        --path <abs-path> --branch <branch> --role <orchestrator|worker> \
        [--description "..."] [--onboarding "docs/onboarding/<name>-phase-1.md"]

Behavior:

  1. Read docs/handoff/mesh.json (located via lib.mesh path-walk).
  2. Append a worktree entry. Reject duplicate names (exit 1).
  3. Update `last_updated` to today's ISO date.
  4. Write mesh.json back, preserving indent=2 + key order.
  5. Scaffold `<path>/AGENT_IDENTITY.md` from template. If the file already
     exists, skip + warn (do not overwrite the user's local WIP).

The mesh-mutation logic lives in `add_worktree()` so tests can exercise it
without touching a real mesh.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from datetime import date
from pathlib import Path
from typing import Optional

# scripts/orchestrator/launcher.py -> add scripts/ to sys.path so `orchestrator.lib` imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.lib import mesh as mesh_lib  # noqa: E402


VALID_ROLES = ("orchestrator", "worker")


# ---------- mesh.json mutation (pure / testable) ----------

def add_worktree(
    mesh_path: Path,
    name: str,
    *,
    path: str,
    branch: str,
    role: str,
    description: str = "",
    onboarding: Optional[str] = None,
    today: Optional[str] = None,
) -> None:
    """Append a worktree entry to mesh.json in place.

    Raises ValueError on duplicate name or invalid role. Preserves the existing
    indent=2 formatting and top-level key order.
    """
    if role not in VALID_ROLES:
        raise ValueError(f"invalid role {role!r}; must be one of {VALID_ROLES}")

    p = Path(mesh_path)
    if not p.exists():
        raise FileNotFoundError(f"mesh.json not found at {p}")

    # object_pairs_hook=OrderedDict preserves top-level key order on round-trip.
    raw = json.loads(p.read_text(encoding="utf-8"), object_pairs_hook=OrderedDict)

    existing_names = {w["name"] for w in raw.get("worktrees", [])}
    if name in existing_names:
        raise ValueError(f"worktree {name!r} already exists in mesh.json")

    entry: "OrderedDict[str, str]" = OrderedDict()
    entry["name"] = name
    entry["path"] = path
    entry["branch"] = branch
    entry["role"] = role
    entry["description"] = description
    if onboarding:
        entry["onboarding"] = onboarding

    raw["worktrees"].append(entry)
    raw["last_updated"] = today or date.today().isoformat()

    # Trailing newline matches existing file convention.
    p.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------- AGENT_IDENTITY.md scaffolding ----------

IDENTITY_TEMPLATE = """# 我是谁
- 角色：{role}
- Worktree：{worktree}
- 分支：{branch}
- Upstream remote：{upstream}
- 职责：<TODO 用户填>

## Resume 必读清单
1. CLAUDE.md
2. docs/handoff/mesh.json
3. docs/handoff/decisions-log.md
4. docs/contracts/shared-change-protocol.md
5. docs/contracts/decision-log-protocol.md
{onboarding_line}
{git_log_line}

## 当前批次任务
<TODO 用户填>
EXPECTED_NEXT_SIGNAL: <TODO>

## 红线（自己也守）
✅ commit trailer 带 Signal: XXX
❌ 不在主 CLI 分支上动代码
❌ 不绕 decisions-log 直接批示
❌ 改红区不走 RFC
"""


def render_identity(
    *,
    role: str,
    worktree: str,
    branch: str,
    upstream: str,
    onboarding: Optional[str] = None,
) -> str:
    """Render the AGENT_IDENTITY.md body. Onboarding is optional list item 6."""
    if onboarding:
        onboarding_line = f"6. {onboarding}"
        git_log_line = "7. git log --format='%h %s' -20"
    else:
        onboarding_line = "6. git log --format='%h %s' -20"
        git_log_line = ""

    body = IDENTITY_TEMPLATE.format(
        role=role,
        worktree=worktree,
        branch=branch,
        upstream=upstream,
        onboarding_line=onboarding_line,
        git_log_line=git_log_line,
    )
    # Collapse the empty trailing list line if no onboarding was given.
    return body.replace("\n\n\n", "\n\n")


def scaffold_identity(
    worktree_dir: Path,
    *,
    role: str,
    branch: str,
    upstream: str,
    onboarding: Optional[str] = None,
) -> tuple[Path, bool]:
    """Write AGENT_IDENTITY.md into worktree_dir.

    Returns (target_path, written). `written=False` means the file already
    existed and was left untouched.
    """
    wt = Path(worktree_dir)
    target = wt / "AGENT_IDENTITY.md"
    if target.exists():
        return target, False

    body = render_identity(
        role=role,
        worktree=str(wt).replace("\\", "/"),
        branch=branch,
        upstream=upstream,
        onboarding=onboarding,
    )
    wt.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return target, True


# ---------- CLI ----------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="launcher.py",
        description="Register a new worktree into mesh.json + scaffold AGENT_IDENTITY.md.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    reg = sub.add_parser("register", help="Register a new worktree.")
    reg.add_argument("name", help="Short worktree name (must be unique in mesh.json).")
    reg.add_argument("--path", required=True, help="Absolute filesystem path of the worktree.")
    reg.add_argument("--branch", required=True, help="Git branch this worktree tracks.")
    reg.add_argument("--role", required=True, choices=VALID_ROLES, help="Role of the CLI in this worktree.")
    reg.add_argument("--description", default="", help="One-line description.")
    reg.add_argument("--onboarding", default=None, help="Onboarding doc path (optional).")
    return p


def cmd_register(args: argparse.Namespace) -> int:
    mesh_path = mesh_lib._find_mesh_json()
    upstream_remote = mesh_lib.load(mesh_path).upstream_remote

    try:
        add_worktree(
            mesh_path,
            args.name,
            path=args.path,
            branch=args.branch,
            role=args.role,
            description=args.description,
            onboarding=args.onboarding,
        )
    except ValueError as e:
        sys.stderr.write(f"launcher: {e}\n")
        return 1

    target, written = scaffold_identity(
        Path(args.path),
        role=args.role,
        branch=args.branch,
        upstream=upstream_remote,
        onboarding=args.onboarding,
    )

    print(f"[launcher] registered worktree {args.name!r} in {mesh_path}")
    if written:
        print(f"[launcher] scaffolded AGENT_IDENTITY at {target}")
    else:
        sys.stderr.write(
            f"[launcher] warning: {target} already exists; left untouched\n"
        )
    return 0


def main(argv: list[str]) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "register":
        return cmd_register(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
