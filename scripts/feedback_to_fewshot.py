# -*- coding: utf-8 -*-
"""数据飞轮第 4 环 · Step 1 —— 从 feedback JSONL 聚合 few-shot 候选。

CLAUDE.md §6:
  静态知识 → 模型评估 → 动态经验(feedback) → 提示词优化(few-shot)

本脚本读 `data/feedback/*.jsonl`，按 agent 聚合、去重、按 `correction_reason`
归类后，输出 `data/fewshot/<agent>-candidates.json`，供 `inject_fewshot_to_prompts.py`
消费。**PM 在两脚本之间人工 review candidates.json 再 inject**（SOP 见
`docs/runbook/feedback-flywheel.md`）。

Usage:
    py scripts/feedback_to_fewshot.py                           # 全 agent 默认跑
    py scripts/feedback_to_fewshot.py --agent credit            # 单 agent
    py scripts/feedback_to_fewshot.py --since 2026-04-01        # 日期过滤
    py scripts/feedback_to_fewshot.py --top-n 5                 # 每 agent 取前 N 条模式
    py scripts/feedback_to_fewshot.py --min-count 2             # 至少 2 条相似反馈才入选
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("feedback_to_fewshot")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FEEDBACK_DIR = PROJECT_ROOT / "data" / "feedback"
FEWSHOT_DIR = PROJECT_ROOT / "data" / "fewshot"

ALLOWED_AGENTS = {"channel", "credit", "alert", "compliance", "report", "riskctrl"}

# 把 correction_reason 先做简单归一（中文分词级别，避免 "利率偏高" / "利率太高" 分成两类）
_CLUSTER_NORMALIZE = [
    (re.compile(r"[偏|过|太]\s*高"), "偏高"),
    (re.compile(r"[偏|过|太]\s*低"), "偏低"),
    (re.compile(r"\s+"), " "),
]


def _normalize_reason(text: str) -> str:
    t = text.strip()
    for pat, repl in _CLUSTER_NORMALIZE:
        t = pat.sub(repl, t)
    return t.lower()


def _cluster_key(record: dict) -> str:
    """一条 feedback 的聚类键 —— 用归一后的 reason + 修改字段集合共同构成。"""
    reason = _normalize_reason(record.get("correction_reason", ""))
    correction = record.get("user_correction", {}) or {}
    if isinstance(correction, dict):
        fields = sorted(correction.keys())
    else:
        fields = []
    raw = f"{reason}|{','.join(fields)}"
    return raw[:120]


def _load_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.warning("skip malformed line in %s: %s", path.name, e)
    return records


def _parse_since(since: str | None) -> date | None:
    if not since:
        return None
    return datetime.strptime(since, "%Y-%m-%d").date()


def _diff_summary(original: dict, correction: dict, max_chars: int = 160) -> str:
    """产出简短"前→后"对照串，供 few-shot input/output 展示。"""
    if not isinstance(original, dict) or not isinstance(correction, dict):
        return ""
    changed_keys = [k for k in correction.keys() if correction.get(k) != original.get(k)]
    if not changed_keys:
        return ""
    bits = []
    for k in changed_keys[:5]:
        before = str(original.get(k, ""))[:40]
        after = str(correction.get(k, ""))[:40]
        bits.append(f"{k}: {before} → {after}")
    out = "; ".join(bits)
    return out[:max_chars]


def aggregate(
    records: list[dict],
    *,
    top_n: int = 5,
    min_count: int = 2,
) -> dict[str, list[dict]]:
    """按 agent 聚合，再按 cluster_key 归类，返回 {agent: [candidate, ...]}。"""
    per_agent: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))

    for rec in records:
        agent = rec.get("agent")
        if agent not in ALLOWED_AGENTS:
            continue
        key = _cluster_key(rec)
        per_agent[agent][key].append(rec)

    result: dict[str, list[dict]] = {}
    for agent, clusters in per_agent.items():
        candidates: list[dict] = []
        for key, items in sorted(clusters.items(), key=lambda kv: -len(kv[1])):
            if len(items) < min_count:
                continue
            representative = items[0]
            example = {
                "cluster_id": hashlib.sha1(
                    f"{agent}|{key}".encode("utf-8")
                ).hexdigest()[:10],
                "count": len(items),
                "reason": representative.get("correction_reason", ""),
                "sample_input": representative.get("original_output", {}),
                "preferred_output": representative.get("user_correction", {}),
                "diff_summary": _diff_summary(
                    representative.get("original_output", {}),
                    representative.get("user_correction", {}),
                ),
                "first_seen": representative.get("timestamp", ""),
                "last_seen": items[-1].get("timestamp", ""),
            }
            candidates.append(example)
        candidates.sort(key=lambda c: -c["count"])
        result[agent] = candidates[:top_n]
    return result


def scan_feedback(
    feedback_dir: Path = FEEDBACK_DIR,
    *,
    agent: str | None = None,
    since: date | None = None,
) -> list[dict]:
    """扫目录下 `*.jsonl` 文件（按日期命名），过滤 agent / since。"""
    if not feedback_dir.exists():
        logger.warning("feedback dir not found: %s", feedback_dir)
        return []

    records: list[dict] = []
    for path in sorted(feedback_dir.glob("*.jsonl")):
        stem = path.stem
        try:
            file_date = datetime.strptime(stem, "%Y-%m-%d").date()
        except ValueError:
            file_date = None

        if since is not None and file_date is not None and file_date < since:
            continue

        for rec in _load_jsonl(path):
            if agent and rec.get("agent") != agent:
                continue
            records.append(rec)
    return records


def write_candidates(candidates: dict[str, list[dict]], out_dir: Path = FEWSHOT_DIR) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for agent, items in candidates.items():
        if not items:
            continue  # 空聚类不落盘，避免假阳性 candidates 文件
        path = out_dir / f"{agent}-candidates.json"
        payload = {
            "agent": agent,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "schema_version": 1,
            "examples": items,
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--agent", choices=sorted(ALLOWED_AGENTS), default=None,
                        help="仅聚合该 agent，默认全部")
    parser.add_argument("--since", default=None, help="起始日期 YYYY-MM-DD")
    parser.add_argument("--top-n", type=int, default=5, help="每 agent 输出 top N 聚类")
    parser.add_argument("--min-count", type=int, default=2,
                        help="聚类至少含 N 条记录才入选（避免单次偶发）")
    parser.add_argument("--feedback-dir", default=str(FEEDBACK_DIR))
    parser.add_argument("--out-dir", default=str(FEWSHOT_DIR))
    args = parser.parse_args(argv)

    since = _parse_since(args.since)
    records = scan_feedback(Path(args.feedback_dir), agent=args.agent, since=since)
    logger.info("loaded %d feedback records (agent=%s, since=%s)",
                len(records), args.agent or "*", since or "*")

    candidates = aggregate(records, top_n=args.top_n, min_count=args.min_count)
    written = write_candidates(candidates, Path(args.out_dir))

    for path in written:
        agent = path.stem.replace("-candidates", "")
        try:
            display = path.relative_to(PROJECT_ROOT)
        except ValueError:
            display = path
        logger.info("  %-10s → %s (%d examples)",
                    agent, display, len(candidates.get(agent, [])))

    if not written:
        logger.info("no candidates produced (feedback 数量不足或 min-count 过严)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
