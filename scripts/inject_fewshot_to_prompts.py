# -*- coding: utf-8 -*-
"""数据飞轮第 4 环 · Step 2 —— 把 PM 审过的 few-shot candidates 注入 prompts.py。

用 magic marker 块包围注入内容，多次跑幂等（覆盖 marker 之间的内容）。
支持 --dry-run 预览 + --revert 抹除整块。

Usage:
    py scripts/inject_fewshot_to_prompts.py                      # 全 agent 注入
    py scripts/inject_fewshot_to_prompts.py --agent credit       # 只注入 Agent3
    py scripts/inject_fewshot_to_prompts.py --dry-run            # 预览
    py scripts/inject_fewshot_to_prompts.py --revert             # 抹除注入块，回到原 prompts.py
    py scripts/inject_fewshot_to_prompts.py --agent credit --revert

与 feedback_to_fewshot.py 的衔接：
    1. 周一跑 feedback_to_fewshot.py 生成 data/fewshot/*-candidates.json
    2. PM review 每个 candidate → 删掉不想用的 example，整理 preferred_output
    3. 跑本脚本注入到 agent_*/prompts.py
    4. 下一次 Agent 调 LLM 就能拿到新 few-shot
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("inject_fewshot")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FEWSHOT_DIR = PROJECT_ROOT / "data" / "fewshot"

ALLOWED_AGENTS = {"channel", "credit", "alert", "compliance", "report", "riskctrl"}

BEGIN_MARK = "# >>> FEW_SHOT_EXAMPLES · auto-injected · do not edit inside >>>"
END_MARK = "# <<< FEW_SHOT_EXAMPLES · auto-injected · do not edit inside <<<"


def _agent_prompts_path(agent: str) -> Path:
    # riskctrl → agent_riskctrl / credit → agent_credit / ...
    return PROJECT_ROOT / f"agent_{agent}" / "prompts.py"


def _render_block(agent: str, examples: list[dict]) -> str:
    """渲染 FEW_SHOT_EXAMPLES 常量 Python 源码块。"""
    header = (
        f"{BEGIN_MARK}\n"
        f"# generated_at: {datetime.now().isoformat(timespec='seconds')}\n"
        f"# agent: {agent}\n"
        f"# count: {len(examples)}\n"
        f"# source: data/fewshot/{agent}-candidates.json\n"
    )
    body = "FEW_SHOT_EXAMPLES = " + json.dumps(
        examples, ensure_ascii=False, indent=2, sort_keys=False,
    ) + "\n"
    return header + body + END_MARK + "\n"


def _strip_existing_block(source: str) -> str:
    begin = source.find(BEGIN_MARK)
    if begin < 0:
        return source
    end_idx = source.find(END_MARK, begin)
    if end_idx < 0:
        logger.warning("found BEGIN marker without END marker, refusing to strip")
        return source
    end_line_end = source.find("\n", end_idx + len(END_MARK))
    if end_line_end < 0:
        end_line_end = len(source)
    else:
        end_line_end += 1
    pre = source[:begin].rstrip("\n")
    post = source[end_line_end:].lstrip("\n")
    pieces = []
    if pre:
        pieces.append(pre + "\n")
    if post:
        pieces.append(post)
    return "".join(pieces) or "\n"


def inject_for_agent(
    agent: str,
    *,
    dry_run: bool = False,
    revert: bool = False,
    fewshot_dir: Path = FEWSHOT_DIR,
) -> str:
    """对单 agent 执行注入或回滚。返回 'injected' | 'reverted' | 'skipped'。"""
    prompts_path = _agent_prompts_path(agent)
    if not prompts_path.exists():
        logger.warning("%s: prompts.py not found (%s)", agent, prompts_path)
        return "skipped"

    src = prompts_path.read_text(encoding="utf-8")

    if revert:
        new_src = _strip_existing_block(src)
        if new_src == src:
            logger.info("%s: no marker block, nothing to revert", agent)
            return "skipped"
        if dry_run:
            logger.info("%s: [dry-run] would revert (strip marker block)", agent)
        else:
            prompts_path.write_text(new_src, encoding="utf-8")
            logger.info("%s: reverted", agent)
        return "reverted"

    cand_path = fewshot_dir / f"{agent}-candidates.json"
    if not cand_path.exists():
        logger.warning("%s: candidates not found (%s) — 先跑 feedback_to_fewshot.py",
                       agent, cand_path)
        return "skipped"

    payload = json.loads(cand_path.read_text(encoding="utf-8"))
    examples = payload.get("examples", [])
    if not examples:
        logger.info("%s: 0 example in candidates — skip", agent)
        return "skipped"

    stripped = _strip_existing_block(src)
    block = _render_block(agent, examples)

    # 放到文件末尾（最稳妥；prompts 常量平级加一个即可）
    if stripped.endswith("\n"):
        new_src = stripped + "\n\n" + block
    else:
        new_src = stripped + "\n\n\n" + block

    if dry_run:
        logger.info("%s: [dry-run] would inject %d example (block size=%d chars)",
                    agent, len(examples), len(block))
        return "injected"

    prompts_path.write_text(new_src, encoding="utf-8")
    try:
        display = prompts_path.relative_to(PROJECT_ROOT)
    except ValueError:
        display = prompts_path
    logger.info("%s: injected %d example(s) → %s", agent, len(examples), display)
    return "injected"


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--agent", choices=sorted(ALLOWED_AGENTS), default=None,
                        help="只处理该 agent，默认全部")
    parser.add_argument("--dry-run", action="store_true", help="预览，不写盘")
    parser.add_argument("--revert", action="store_true",
                        help="抹除注入块（对应 --agent 或全部）")
    parser.add_argument("--fewshot-dir", default=str(FEWSHOT_DIR))
    args = parser.parse_args(argv)

    agents = [args.agent] if args.agent else sorted(ALLOWED_AGENTS)
    results: dict[str, str] = {}
    for agent in agents:
        results[agent] = inject_for_agent(
            agent,
            dry_run=args.dry_run,
            revert=args.revert,
            fewshot_dir=Path(args.fewshot_dir),
        )
    counts = {"injected": 0, "reverted": 0, "skipped": 0}
    for r in results.values():
        counts[r] = counts.get(r, 0) + 1
    logger.info("summary: %s", counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
