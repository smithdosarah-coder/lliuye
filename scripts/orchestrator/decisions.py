"""decisions.py · CLI for searching docs/handoff/decisions-log.md.

The decisions log is an append-only markdown stream of ``## [Q-NNN]`` questions
from worker CLIs paired with ``### [A-NNN]`` answers from the orchestrator
(see ``protocols/decision-log-protocol.md``). This tool makes the stream
queryable without hand-scrolling.

CLI usage::

    py scripts/orchestrator/decisions.py find Q-023
    py scripts/orchestrator/decisions.py list
    py scripts/orchestrator/decisions.py list --unresolved

Entries are located relative to the mesh's ``decisions_log`` path from
mesh.json. Override the file via ``--log <path>``.

Exit codes::

    0  one or more entries printed
    1  query matched no entries
    2  usage error
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# scripts/orchestrator/decisions.py -> add scripts/ so `orchestrator.lib` imports.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.lib import mesh as mesh_lib  # noqa: E402


Q_HEADER_RE = re.compile(r"^##\s+\[(Q-\d+)\](.*)$")
A_HEADER_RE = re.compile(r"^###\s+\[(A-\d+)\](.*)$")


@dataclass
class Entry:
    id: str           # "Q-023" or "A-023"
    kind: str         # "Q" or "A"
    number: int       # 23
    title: str        # header text after the id, trimmed
    body: str         # lines that follow this header up to the next header or EOF
    line: int         # 1-based line number where the header appears


def parse_log(text: str) -> List[Entry]:
    """Parse the decisions-log markdown into a flat list of Q/A entries."""
    lines = text.splitlines()
    entries: List[Entry] = []
    current: Optional[Entry] = None
    buffer: List[str] = []

    def flush():
        nonlocal current, buffer
        if current is not None:
            current.body = "\n".join(buffer).rstrip()
            entries.append(current)
        current = None
        buffer = []

    for idx, raw in enumerate(lines, start=1):
        m_q = Q_HEADER_RE.match(raw)
        m_a = A_HEADER_RE.match(raw) if not m_q else None
        if m_q or m_a:
            flush()
            m = m_q or m_a
            kind = "Q" if m_q else "A"
            entry_id = m.group(1)
            number = int(entry_id.split("-", 1)[1])
            title = m.group(2).strip().lstrip(":·—-").strip()
            current = Entry(
                id=entry_id,
                kind=kind,
                number=number,
                title=title,
                body="",
                line=idx,
            )
            continue
        if current is not None:
            buffer.append(raw)

    flush()
    return entries


def _default_log_path() -> Path:
    """Resolve the live decisions-log.md via mesh.json."""
    mesh_path = mesh_lib._find_mesh_json()
    m = mesh_lib.load(mesh_path)
    # decisions_log in mesh.json is relative to the project root (mesh.json is at
    # <root>/docs/handoff/mesh.json, so project root = mesh_path.parent.parent).
    project_root = mesh_path.parent.parent
    return project_root / m.decisions_log


def find_entries(entries: List[Entry], entry_id: str) -> List[Entry]:
    """Return all entries matching an id like 'Q-023' or 'A-023'.

    If the caller gave 'Q-023', the matching answer 'A-023' (if any) is
    appended so a single call prints the whole conversation.
    """
    entry_id = entry_id.upper()
    if not re.fullmatch(r"[QA]-\d+", entry_id):
        return []
    matched = [e for e in entries if e.id == entry_id]
    if not matched:
        return []
    # Pair the Q with any A of the same number, regardless of order.
    number = matched[0].number
    pair = [e for e in entries if e.number == number and e.id != entry_id]
    return matched + pair


def unresolved(entries: List[Entry]) -> List[Entry]:
    """Return all Q entries that have no matching A entry in the log."""
    a_numbers = {e.number for e in entries if e.kind == "A"}
    return [e for e in entries if e.kind == "Q" and e.number not in a_numbers]


def _render(entry: Entry) -> str:
    header = "## [" if entry.kind == "Q" else "### ["
    return f"{header}{entry.id}] {entry.title}\n{entry.body}\n"


# ---------- CLI --------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="decisions.py",
        description="Search the decisions-log for Q/A entries.",
    )
    p.add_argument(
        "--log",
        type=Path,
        default=None,
        help="Override path to decisions-log.md (default: resolved via mesh.json).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    find = sub.add_parser("find", help="Print one Q/A pair by id (e.g. Q-023).")
    find.add_argument("entry_id", help="Entry id: Q-NNN or A-NNN")

    lst = sub.add_parser("list", help="List all Q/A entries.")
    lst.add_argument(
        "--unresolved",
        action="store_true",
        help="Show only Q entries that lack a matching A.",
    )
    return p


def cmd_find(entries: List[Entry], entry_id: str) -> int:
    hits = find_entries(entries, entry_id)
    if not hits:
        sys.stderr.write(f"decisions: no entry matching {entry_id!r}\n")
        return 1
    for e in hits:
        sys.stdout.write(_render(e) + "\n")
    return 0


def cmd_list(entries: List[Entry], unresolved_only: bool) -> int:
    subset = unresolved(entries) if unresolved_only else entries
    if not subset:
        kind = "unresolved Q" if unresolved_only else "Q/A"
        sys.stdout.write(f"decisions: no {kind} entries found\n")
        return 1
    for e in subset:
        title = e.title or "(no title)"
        sys.stdout.write(f"{e.id}  L{e.line:>5}  {title}\n")
    return 0


def main(argv: List[str]) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    log_path = args.log or _default_log_path()
    if not log_path.is_file():
        sys.stderr.write(f"decisions: log file not found: {log_path}\n")
        return 2
    entries = parse_log(log_path.read_text(encoding="utf-8"))

    if args.cmd == "find":
        return cmd_find(entries, args.entry_id)
    if args.cmd == "list":
        return cmd_list(entries, args.unresolved)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
