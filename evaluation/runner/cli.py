# -*- coding: utf-8 -*-
"""
evaluation.runner.cli — 命令行入口

用法:
  python -m evaluation.runner --agent report --artifacts outputs/普惠申报书_骨架型_v16.docx
  python -m evaluation.runner --all
  python -m evaluation.runner --all --gate                # CI gate · blocker_threshold 阻断
  python -m evaluation.runner --agent report --compare-baseline
  python -m evaluation.runner --agent report --artifacts outputs/ --out /tmp/eval.json

退出码 (Sprint 2 决策 3 · per-metric 4-state):
  0 = 全部 metric status=PASS (≥ 0.95 × baseline_target) · 安全发布 (绿)
  1 = 任一 PARTIAL (0.80-0.95 × baseline_target) 或 FAIL (< 0.80) · 默认阻断 · 需 PM 评审豁免 (黄/橙)
  2 = adapter 未实现或其他异常 · 修代码后重跑 (灰)
  3 = blocker_threshold 命中 (仅 --gate 触发 · 不可豁免) · 必回滚 prompt (红)

发布闸门语义 (per BE10 + Codex V2 + Sprint 2 决策 3):
  * 退出码 0 才算"自动放行"
  * 1 / 2 / 3 都阻断 · 强度递增 (1 可豁免 / 2 必修 / 3 不可豁免)
  * SKIP metric (value=None / 缺 baseline_target) 不算 fail · 但纳入 PARTIAL 风险 hint
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
    gate: bool = False,
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
    if result.blockers:
        print(f"    [BLOCKERS] {', '.join(result.blockers)}", file=sys.stderr)
    if result.failed_metrics:
        print(f"    [FAIL]     {', '.join(result.failed_metrics)}", file=sys.stderr)
    if result.partial_metrics:
        print(f"    [PARTIAL]  {', '.join(result.partial_metrics)}", file=sys.stderr)
    if collected is not None:
        collected.append(json.loads(result.model_dump_json()))
    if gate and result.any_blocker:
        return 3  # CI 阻断 (Phase B BE10)
    # Sprint 2 决策 3 · per-metric status 驱动 exit
    if result.failed_metrics or result.partial_metrics:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m evaluation.runner",
        description="Cross-agent evaluation runner (Phase A + HOLDING H-A).",
    )
    parser.add_argument("--agent", help="channel | riskctrl | credit | alert | compliance | report")
    parser.add_argument("--artifacts", nargs="*", default=[], help="待评估产出物路径")
    parser.add_argument("--all", action="store_true", help="跑所有已注册 adapter")
    parser.add_argument("--compare-baseline", action="store_true")
    parser.add_argument(
        "--gate",
        action="store_true",
        help="blocker_threshold 触发时退出码 3 (CI 阻断发布 · Phase B BE10)",
    )
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
            sub_rc = _run_one(
                agent_id, [], args.compare_baseline, collected, gate=args.gate,
            )
            rc_final = max(rc_final, sub_rc)
    elif args.agent:
        rc_final = _run_one(
            args.agent, args.artifacts, args.compare_baseline, collected,
            gate=args.gate,
        )
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
