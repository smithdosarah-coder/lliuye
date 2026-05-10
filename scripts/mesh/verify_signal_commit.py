#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Worker signal commit 格式校验 · per docs/contracts/signal-commit-contract.md.

可作 git commit-msg hook 用 (worker worktree 启用):
    cp scripts/mesh/verify_signal_commit.py .git/hooks/commit-msg
    chmod +x .git/hooks/commit-msg

或主 CLI cherry-pick 前手动 verify:
    py scripts/mesh/verify_signal_commit.py <commit-sha>
    py scripts/mesh/verify_signal_commit.py --message-file <path>

退出码:
    0 = 通过 (signal commit 合格 · 或非 signal commit 不验)
    1 = 不合格 (列具体违规)
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from typing import Iterable

# Subject 模板 · per signal-commit-contract §1
_SIGNAL_SUBJECT_RE = re.compile(
    r"^chore\(mesh\): signal worker (?P<agent>[a-z]+) ready for mesh merge ALLIN$"
)
_VALID_AGENTS = {"common", "report", "credit", "alert", "riskctrl", "compliance"}

# Body 必含 5 trailer · per §1
_REQUIRED_TRAILERS = ("Worker:", "Phase:", "Refs:", "Signal:", "Root:")
_VALID_PHASES = {"A", "B", "C"}
_VALID_SIGNALS = {"READY", "BLOCKED", "HOTFIX", "RESUMED"}

# Body 必含 7 段 keyword · per §2
_REQUIRED_BODY_SECTIONS = (
    "完成摘要",
    "改的文件清单",
    "测试 verify",
    "红线自检",
    "依赖合同",
    "base dashboard 行更新",
    "证据",
)


def _read_message(args: argparse.Namespace) -> str:
    if args.message_file:
        with open(args.message_file, encoding="utf-8") as f:
            return f.read()
    if args.commit:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%B", args.commit],
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            print(f"[verify_signal] git log failed: {result.stderr}", file=sys.stderr)
            sys.exit(2)
        return result.stdout or ""
    raise SystemExit("must pass --message-file or commit sha")


def _is_signal_commit(msg: str) -> bool:
    """判断是否 signal commit (subject 含 'signal worker X ready for mesh merge ALLIN')."""
    first_line = msg.split("\n", 1)[0].strip()
    return bool(_SIGNAL_SUBJECT_RE.match(first_line))


def _looks_like_signal_attempt(msg: str) -> bool:
    """启发式 · 主要为 hook 防 typo · 含 'signal worker' + 'mesh' 但不匹配 strict pattern."""
    first_line = msg.split("\n", 1)[0].strip().lower()
    if _SIGNAL_SUBJECT_RE.match(msg.split("\n", 1)[0].strip()):
        return False  # 严格匹配 · 不是 attempt
    return ("signal worker" in first_line or "signal " in first_line) and (
        "mesh" in first_line or "allin" in first_line
    )


def _check_subject(msg: str) -> list[str]:
    """检查 subject 行 · 返违规 list."""
    violations: list[str] = []
    first_line = msg.split("\n", 1)[0].strip()
    m = _SIGNAL_SUBJECT_RE.match(first_line)
    if not m:
        violations.append(
            f"Subject 不符模板 'chore(mesh): signal worker <agent> ready for mesh merge ALLIN'\n  实际: {first_line!r}"
        )
        return violations
    agent = m.group("agent")
    if agent not in _VALID_AGENTS:
        violations.append(
            f"Subject agent 名 {agent!r} 不在白名单 {sorted(_VALID_AGENTS)}"
        )
    return violations


def _check_trailers(msg: str) -> list[str]:
    """检查 5 必含 trailer · 验值."""
    violations: list[str] = []
    body = msg
    found: dict[str, str] = {}
    for line in body.splitlines():
        line = line.strip()
        for trailer in _REQUIRED_TRAILERS:
            if line.startswith(trailer):
                key = trailer.rstrip(":")
                value = line[len(trailer):].strip()
                found[key] = value

    for trailer in _REQUIRED_TRAILERS:
        key = trailer.rstrip(":")
        if key not in found:
            violations.append(f"缺 trailer: {trailer}")

    if "Worker" in found and found["Worker"] not in _VALID_AGENTS:
        violations.append(f"Worker {found['Worker']!r} 不在白名单 {sorted(_VALID_AGENTS)}")
    if "Phase" in found and found["Phase"] not in _VALID_PHASES:
        violations.append(f"Phase {found['Phase']!r} 不在白名单 {sorted(_VALID_PHASES)}")
    if "Signal" in found and found["Signal"] not in _VALID_SIGNALS:
        violations.append(f"Signal {found['Signal']!r} 不在白名单 {sorted(_VALID_SIGNALS)}")
    if "Refs" in found and not found["Refs"].startswith("ALLIN-"):
        violations.append(f"Refs 必以 'ALLIN-' 开头 · 实际 {found['Refs']!r}")
    if "Root" in found:
        root = found["Root"]
        if not re.match(r"^[0-9a-f]{7,40}$", root):
            violations.append(f"Root 必是 git sha (7-40 hex) · 实际 {root!r}")
    return violations


def _check_body_sections(msg: str) -> list[str]:
    """检查 7 段 keyword · 不要求顺序 · 关键字 case-insensitive 子串."""
    violations: list[str] = []
    msg_lc = msg.lower()
    for section in _REQUIRED_BODY_SECTIONS:
        # 中文不分 case · 英文 lowered
        if section.lower() not in msg_lc:
            violations.append(f"Body 缺 7 段之一: {section!r}")
    return violations


def verify(msg: str, *, strict_body: bool = False) -> list[str]:
    """对 commit message 做完整校验 · 返违规 list (空 = 通过).

    Args:
        msg: commit message 全文
        strict_body: True 时 enforce 7 段 keyword (READY signal 必)
    """
    if not _is_signal_commit(msg):
        if _looks_like_signal_attempt(msg):
            # typo · 看起来想 signal 但 subject 不严格匹配 → 报 subject 违规
            return _check_subject(msg)
        return []  # 真非 signal commit · 不验

    violations: list[str] = []
    violations.extend(_check_subject(msg))
    violations.extend(_check_trailers(msg))
    if strict_body:
        violations.extend(_check_body_sections(msg))
    return violations


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("commit", nargs="?", help="git sha")
    parser.add_argument("--message-file", help="path to commit message file (commit-msg hook usage)")
    parser.add_argument("--strict-body", action="store_true", help="enforce 7 段 body keywords")
    args = parser.parse_args(argv)

    msg = _read_message(args)
    violations = verify(msg, strict_body=args.strict_body)

    if violations:
        print("[verify_signal] FAIL · 违规如下:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    if _is_signal_commit(msg):
        print("[verify_signal] OK · signal commit 合格")
    return 0


if __name__ == "__main__":
    sys.exit(main())
