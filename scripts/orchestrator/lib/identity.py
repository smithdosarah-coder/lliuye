"""Read and parse a worktree's AGENT_IDENTITY.md (the .gitignored local pointer).

Each worktree root carries an `AGENT_IDENTITY.md` that names who the CLI in
that worktree is (role, branch, upstream, duty). The file is intentionally
loose markdown — humans edit it — so we grep fields with permissive regexes
that accept both Chinese and English keys plus optional markdown emphasis
(`**`, `*`).

`load(worktree_path)` returns an `AgentIdentity` dataclass, or `None` when the
worktree has no identity file (which is a legal state — newly registered
worktrees may not have written one yet).

Pure markdown parser. No subprocess, no git calls, no network.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

IDENTITY_FILENAME = "AGENT_IDENTITY.md"


@dataclass
class AgentIdentity:
    role: Optional[str]
    worktree: Path
    branch: Optional[str]
    upstream: Optional[str]
    duty: Optional[str]
    raw_text: str


# Field aliases: each logical field maps to a list of keys we accept in
# the markdown. Keys are matched case-insensitively.
_FIELD_ALIASES = {
    "role": ["角色", "Role"],
    "branch": ["分支", "Branch"],
    "upstream": ["Upstream remote", "Upstream", "upstream"],
    "duty": ["职责", "Duty"],
}


def _grep_field(text: str, keys: list[str]) -> Optional[str]:
    """Grep a single-line field value out of markdown.

    Accepts list-bullet prefixes (`-`, `*`, whitespace) and optional `**`/`*`
    emphasis around the key, and either ASCII `:` or full-width `：` separator.
    """
    for key in keys:
        # `[-*\s]*\**{key}\**[\s:：]+(value)` — multi-line so each markdown line
        # is a candidate.
        pattern = re.compile(
            r"^[-*\s]*\**\s*" + re.escape(key) + r"\s*\**\s*[\s:：]+\s*(.+?)\s*$",
            re.MULTILINE | re.IGNORECASE,
        )
        m = pattern.search(text)
        if m:
            value = m.group(1).strip()
            # Strip trailing markdown emphasis if regex's `.+?` captured it.
            value = value.rstrip("*").strip()
            # Strip surrounding backticks (e.g. `chore/l0-infra`).
            if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
                value = value[1:-1]
            if value:
                return value
    return None


def load(worktree_path: Path | str) -> Optional[AgentIdentity]:
    """Load AGENT_IDENTITY.md from the given worktree root.

    Returns None if the file does not exist (legal: worktree has no identity yet).
    """
    wt = Path(worktree_path)
    identity_file = wt / IDENTITY_FILENAME
    if not identity_file.exists():
        return None

    text = identity_file.read_text(encoding="utf-8", errors="replace")

    return AgentIdentity(
        role=_grep_field(text, _FIELD_ALIASES["role"]),
        worktree=wt,
        branch=_grep_field(text, _FIELD_ALIASES["branch"]),
        upstream=_grep_field(text, _FIELD_ALIASES["upstream"]),
        duty=_grep_field(text, _FIELD_ALIASES["duty"]),
        raw_text=text,
    )
