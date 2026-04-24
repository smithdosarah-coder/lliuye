"""Per-worktree git operations: log, last-commit-time, head-sha."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass
class CommitInfo:
    sha: str
    short_sha: str
    timestamp: datetime
    subject: str
    body: str


def run_git(worktree: Path, *args: str, check: bool = True) -> str:
    """Run a git command in the given worktree, return stdout (utf-8 best-effort)."""
    cmd = ["git", "-C", str(worktree), *args]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"git failed in {worktree}: {' '.join(cmd)}\n{result.stderr}"
        )
    return result.stdout


def head_sha(worktree: Path) -> Optional[str]:
    """Get HEAD sha of a worktree, or None if git fails."""
    try:
        return run_git(worktree, "rev-parse", "HEAD").strip()
    except (RuntimeError, FileNotFoundError):
        return None


def diagnose_unreachable(worktree: Path) -> str:
    """Classify *why* ``head_sha`` returned None for this worktree.

    Returns one of (subtype names, without the ``stuck:`` prefix):
        'binary-missing' — ``git`` is not on PATH at all
        'path-missing'   — the worktree directory does not exist
        'perm-denied'    — the directory exists but can't be read
        'unreachable'    — some other reason (corrupt .git dir, locked index,
                           etc.); consumers should treat as legacy umbrella

    Pre-checks are cheap and intentional — resolving cause up front saves a
    round-trip to the git subprocess when the filesystem already has the
    answer.
    """
    if shutil.which("git") is None:
        return "binary-missing"
    try:
        if not Path(worktree).exists():
            return "path-missing"
        if not os.access(worktree, os.R_OK):
            return "perm-denied"
    except OSError:
        return "perm-denied"
    return "unreachable"


def head_subject(worktree: Path) -> Optional[str]:
    """Get HEAD commit subject of a worktree."""
    try:
        return run_git(worktree, "log", "-1", "--format=%s").strip()
    except RuntimeError:
        return None


def commit_age_seconds(worktree: Path) -> Optional[int]:
    """Get seconds since HEAD commit was made."""
    try:
        ts = run_git(worktree, "log", "-1", "--format=%aI").strip()
        if not ts:
            return None
        commit_time = datetime.fromisoformat(ts)
        now = datetime.now(timezone.utc)
        return int((now - commit_time).total_seconds())
    except (RuntimeError, ValueError):
        return None


def last_commit_with_signal(worktree: Path, max_count: int = 50) -> Optional[CommitInfo]:
    """Find the most recent commit that contains 'Signal:' in its message."""
    try:
        log = run_git(
            worktree,
            "log",
            f"-{max_count}",
            "--format=COMMIT_START%n%H%n%h%n%aI%n%s%n%b%nCOMMIT_END",
        )
    except RuntimeError:
        return None

    for chunk in _parse_log_chunks(log):
        if "Signal:" in chunk.body or "Signal:" in chunk.subject:
            return chunk
    return None


def _parse_log_chunks(raw: str) -> List[CommitInfo]:
    """Parse the COMMIT_START/COMMIT_END delimited log output into typed objects."""
    out: List[CommitInfo] = []
    for chunk in raw.split("COMMIT_START\n"):
        if not chunk.strip():
            continue
        chunk = chunk.split("COMMIT_END")[0].strip()
        lines = chunk.split("\n")
        if len(lines) < 4:
            continue
        try:
            sha, short_sha, ts_str, subject = lines[0], lines[1], lines[2], lines[3]
            body = "\n".join(lines[4:]).strip()
            out.append(
                CommitInfo(
                    sha=sha,
                    short_sha=short_sha,
                    timestamp=datetime.fromisoformat(ts_str),
                    subject=subject,
                    body=body,
                )
            )
        except (IndexError, ValueError):
            continue
    return out
