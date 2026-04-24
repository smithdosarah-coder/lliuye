# -*- coding: utf-8 -*-
"""
evaluation.runner.cli — 命令行入口

用法:
  python -m evaluation.runner --agent report --artifacts outputs/普惠申报书_骨架型_v16.docx
  python -m evaluation.runner --all
  python -m evaluation.runner --agent report --compare-baseline
  python -m evaluation.runner --agent report --artifacts outputs/ --out /tmp/eval.json

退出码:
  0 = 全部 PASS
  1 = 至少一个 FAIL / PARTIAL
  2 = adapter 未实现或其他异常
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .registry import get_evaluator, list_registered
from .schemas import EvalRun


def _git_head() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return None


def _run_one(
    agent_id: str,
    artifacts: list[str],
    compare_baseline: bool,
    collected: list[dict] | None = None,
) -> int:
    try:
        evaluator = get_evaluator(agent_id)
    except NotImplementedError as e:
        print(f"[SKIP] {agent_id}: {e}", file=sys.stderr)
        return 2

    run = EvalRun(
        agent_id=agent_id,
        commit=_git_head(),
        artifacts=artifacts,
        compare_baseline=compare_baseline,
    )
    result = evaluator.run(run)
    print(result.summary_table())
    if collected is not None:
        collected.append(json.loads(result.model_dump_json()))
    return 0 if result.verdict == "PASS" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m evaluation.runner",
        description="Cross-agent evaluation runner (Phase A + HOLDING H-A).",
    )
    parser.add_argument("--agent", help="channel | riskctrl | credit | alert | compliance | report")
    parser.add_argument("--artifacts", nargs="*", default=[], help="待评估产出物路径")
    parser.add_argument("--all", action="store_true", help="跑所有已注册 adapter")
    parser.add_argument("--compare-baseline", action="store_true")
    parser.add_argument("--list", action="store_true", help="仅列出已注册 adapter")
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="汇总 JSON 输出路径 (单 agent 写 dict, 多 agent 写 list)",
    )
    args = parser.parse_args(argv)

    if args.list:
        names = list_registered()
        if not names:
            print("(no adapter registered)")
        for n in names:
            print(n)
        return 0

    collected: list[dict] = [] if args.out else []  # 始终收集, 便于 --out 输出
    rc_final = 0

    if args.all:
        for agent_id in list_registered():
            sub_rc = _run_one(agent_id, [], args.compare_baseline, collected)
            rc_final = max(rc_final, sub_rc)
    elif args.agent:
        rc_final = _run_one(args.agent, args.artifacts, args.compare_baseline, collected)
    else:
        parser.error("--agent required (or use --all / --list)")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload: Any = collected if args.all else (collected[0] if collected else {})
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n[out] {out_path}")

    return rc_final


if __name__ == "__main__":
    sys.exit(main())
