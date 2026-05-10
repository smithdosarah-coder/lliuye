#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""主 CLI cherry-pick worker signal 自动化 · per signal-commit-contract §3.

流程 (per §3 主 CLI cherry-pick 五步):

1. verify worker signal commit 格式 (verify_signal_commit.py)
2. DIFF guard: worker 没改 shared/ + docs/contracts/ (per AGENT_IDENTITY 禁改域)
3. cherry-pick worker 的所有 code commit 入 main (skip signal commit)
4. 报告 cherry-pick 结果 (主 CLI 跑总验收)
5. 主 CLI 写 close-out commit (本脚本不写)

用法:
    py scripts/mesh/cherry_pick_worker.py --worker-branch feat/allin-report --signal-sha <sha>
    py scripts/mesh/cherry_pick_worker.py --worker-branch feat/allin-report --signal-sha <sha> --dry-run

退出码:
    0 = cherry-pick 全成功
    1 = signal 校验失败 / DIFF guard 拦截 / cherry-pick 冲突
    2 = git 调用错误
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Iterable

# Phase A common worker 域 · 不允许其他 worker 改
_FORBIDDEN_PATHS_FOR_AGENTS = (
    "shared/",
    "docs/contracts/",
    ".mesh-launcher/",
)


def _git(args: list[str], *, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        capture_output=capture,
        text=True,
        check=check,
        encoding="utf-8",
        errors="replace",
    )


def _verify_signal(signal_sha: str, *, strict_body: bool) -> bool:
    """调 verify_signal_commit.py 验 signal commit 格式."""
    args = ["py", "scripts/mesh/verify_signal_commit.py", signal_sha]
    if strict_body:
        args.append("--strict-body")
    print(f"[cherry-pick] step 1/5 · verify signal commit {signal_sha[:8]}")
    result = subprocess.run(args, check=False)
    return result.returncode == 0


def _list_worker_commits(worker_branch: str, base_branch: str) -> list[str]:
    """列出 worker 分支独有的 commit (按 oldest first · cherry-pick 顺序)."""
    result = _git([
        "rev-list",
        "--reverse",  # oldest → newest · cherry-pick 顺序
        f"{base_branch}..{worker_branch}",
    ])
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _check_diff_guard(commits: list[str], worker_name: str) -> list[str]:
    """DIFF guard · 验 worker 没改禁区 path · 返违规 list."""
    if worker_name == "common":
        return []  # common worker 拥有 shared/ 写域

    violations: list[str] = []
    for sha in commits:
        result = _git(["show", "--name-only", "--format=", sha])
        for path in result.stdout.splitlines():
            path = path.strip()
            if not path:
                continue
            for forbidden in _FORBIDDEN_PATHS_FOR_AGENTS:
                if path.startswith(forbidden):
                    violations.append(f"{sha[:8]} 改了禁区 {path!r}")
                    break
    return violations


def _is_signal_commit_subject(sha: str) -> bool:
    """判断 commit subject 是否 signal commit (cherry-pick 时 skip)."""
    result = _git(["log", "-1", "--format=%s", sha])
    subject = result.stdout.strip()
    return "signal worker" in subject and "ready for mesh merge ALLIN" in subject


def _cherry_pick(commits: list[str], *, dry_run: bool) -> list[str]:
    """cherry-pick code commits · skip signal commit · 返失败 sha list."""
    failed: list[str] = []
    for sha in commits:
        if _is_signal_commit_subject(sha):
            print(f"[cherry-pick]   skip signal commit {sha[:8]}")
            continue
        if dry_run:
            print(f"[cherry-pick]   [dry-run] would cherry-pick {sha[:8]}")
            continue
        print(f"[cherry-pick]   cherry-pick {sha[:8]}")
        result = _git(["cherry-pick", sha], check=False)
        if result.returncode != 0:
            print(f"[cherry-pick]   ⚠ FAIL {sha[:8]} · {result.stderr.strip()}")
            failed.append(sha)
            # 立即 abort cherry-pick · 不残留半成品
            _git(["cherry-pick", "--abort"], check=False)
            break
    return failed


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker-branch", required=True, help="e.g. feat/allin-report")
    parser.add_argument("--signal-sha", required=True, help="worker fire 的 signal commit sha")
    parser.add_argument("--base-branch", default="main", help="base branch (default main)")
    parser.add_argument("--dry-run", action="store_true", help="不真 cherry-pick · 仅打 plan")
    parser.add_argument(
        "--skip-signal-verify",
        action="store_true",
        help="跳 signal commit verify (调试用 · 慎用)",
    )
    parser.add_argument(
        "--strict-body",
        action="store_true",
        help="enforce 7 段 body keyword (READY signal 推荐)",
    )
    args = parser.parse_args(argv)

    # 解析 worker name (从 branch 推 · feat/allin-report → report)
    worker_name = args.worker_branch.replace("feat/allin-", "").replace("-contracts", "").strip("/").split("/")[-1]
    print(f"[cherry-pick] worker: {worker_name}")
    print(f"[cherry-pick] worker branch: {args.worker_branch}")
    print(f"[cherry-pick] base branch: {args.base_branch}")
    print(f"[cherry-pick] signal sha: {args.signal_sha}")
    print()

    # 1. verify signal commit 格式
    if not args.skip_signal_verify:
        if not _verify_signal(args.signal_sha, strict_body=args.strict_body):
            print("[cherry-pick] ❌ signal commit 校验不过 · abort", file=sys.stderr)
            return 1
    else:
        print("[cherry-pick] step 1/5 · skip signal verify (--skip-signal-verify)")

    # 2. 列 worker 独有 commit
    print(f"[cherry-pick] step 2/5 · 列 worker 独有 commit")
    try:
        commits = _list_worker_commits(args.worker_branch, args.base_branch)
    except subprocess.CalledProcessError as e:
        print(f"[cherry-pick] ❌ git rev-list 失败: {e}", file=sys.stderr)
        return 2
    if not commits:
        print("[cherry-pick] ⚠ worker branch 无独有 commit · skip")
        return 0
    print(f"[cherry-pick]   共 {len(commits)} 个 commit:")
    for sha in commits:
        result = _git(["log", "-1", "--format=%h %s", sha])
        print(f"[cherry-pick]     {result.stdout.strip()}")

    # 3. DIFF guard · agent worker 不能改 shared/ + docs/contracts/
    print(f"[cherry-pick] step 3/5 · DIFF guard (worker {worker_name!r})")
    violations = _check_diff_guard(commits, worker_name)
    if violations:
        print("[cherry-pick] ❌ DIFF guard 拦截 · agent worker 改了禁区:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1
    print("[cherry-pick]   OK")

    # 4. cherry-pick code commits
    print(f"[cherry-pick] step 4/5 · cherry-pick (dry-run={args.dry_run})")
    failed = _cherry_pick(commits, dry_run=args.dry_run)
    if failed:
        print(f"[cherry-pick] ❌ cherry-pick 失败 {len(failed)} 个:", file=sys.stderr)
        for sha in failed:
            print(f"  - {sha[:8]}", file=sys.stderr)
        print("[cherry-pick] 已 git cherry-pick --abort · 工作树干净", file=sys.stderr)
        return 1

    # 5. 主 CLI 责任 (本脚本不写 close-out commit)
    print(f"[cherry-pick] step 5/5 · 主 CLI 责任")
    print(f"[cherry-pick]   - 跑总验收 (pytest 全跑 + Playwright 该 agent spec)")
    print(f"[cherry-pick]   - 写 close-out commit · subject: chore(mesh): WORKER-{worker_name.upper()}-CHERRY-PICK-MERGED · ALLIN")
    print(f"[cherry-pick]   - 更新 lark-base dashboard {worker_name} 行 status: merged")
    print(f"[cherry-pick]   - bash scripts/deploy_to_ecs.sh (改完即部署 per CLAUDE.md §13.1)")
    print()
    print(f"[cherry-pick] ✅ {worker_name} cherry-pick 完成 ({len(commits) - 1} code commits + 1 signal skip)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
