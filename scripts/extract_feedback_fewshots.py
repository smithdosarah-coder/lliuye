"""数据飞轮第 4 环：从 data/feedback/*.jsonl 抽取审贷员修改记录，
注入 agent_channel/prompts.py 的 PITCH_FEWSHOT_EXAMPLES 块。

用法：
    py scripts/extract_feedback_fewshots.py --agent channel
    py scripts/extract_feedback_fewshots.py --agent channel --max-n 5 --dry-run

约束：
- 只改 sentinel 块（BEGIN/END AUTO-GENERATED），其他内容一字不动
- agent_channel/prompts.py 非红区，可改；api_server.py 红区不碰
- 幂等：多次运行产出一致（按 timestamp 升序后取末尾 max-n）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SUPPORTED_AGENTS = {
    "channel": PROJECT_ROOT / "agent_channel" / "prompts.py",
}

BEGIN = "# BEGIN AUTO-GENERATED FEW-SHOT EXAMPLES (do not edit manually)"
END = "# END AUTO-GENERATED FEW-SHOT EXAMPLES"
BLOCK_RE = re.compile(
    re.escape(BEGIN) + r".*?" + re.escape(END),
    re.DOTALL,
)


def _load_jsonl_records(feedback_dir: Path, agent_id: str) -> list[dict]:
    records: list[dict] = []
    if not feedback_dir.exists():
        return records
    for jsonl in sorted(feedback_dir.glob("*.jsonl")):
        try:
            for line in jsonl.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("agent") != agent_id:
                    continue
                records.append(rec)
        except OSError:
            continue
    records.sort(key=lambda r: r.get("timestamp", ""))
    return records


def _flatten(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for k in ("pitch", "text", "content", "value"):
            if k in value and isinstance(value[k], str):
                return value[k].strip()
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return ""
    return str(value)


def _to_fewshot(rec: dict) -> dict:
    return {
        "bad": _flatten(rec.get("original_output")),
        "good": _flatten(rec.get("user_correction")),
        "reason": _flatten(rec.get("correction_reason")),
    }


def render_block(examples: list[dict]) -> str:
    """Sentinel-delimited 块：python 可执行。"""
    body_lines = [BEGIN, "PITCH_FEWSHOT_EXAMPLES: list[dict] = ["]
    for ex in examples:
        body_lines.append(
            "    " + json.dumps(ex, ensure_ascii=False) + ","
        )
    body_lines.append("]")
    body_lines.append(END)
    return "\n".join(body_lines)


def extract_and_inject(
    agent_id: str,
    max_n: int = 3,
    feedback_dir: Path | None = None,
    dry_run: bool = False,
) -> dict:
    if agent_id not in SUPPORTED_AGENTS:
        raise ValueError(
            f"agent_id must be one of {sorted(SUPPORTED_AGENTS)}, got {agent_id!r}"
        )
    prompts_path = SUPPORTED_AGENTS[agent_id]
    feedback_dir = feedback_dir or (PROJECT_ROOT / "data" / "feedback")

    records = _load_jsonl_records(feedback_dir, agent_id)
    # 保留末尾 max_n 条（最近的修改权重更高）
    tail = records[-max_n:] if max_n > 0 else records
    examples = [_to_fewshot(r) for r in tail]
    # 丢弃两端均空的占位项
    examples = [e for e in examples if e["bad"] or e["good"]]

    new_block = render_block(examples)
    original = prompts_path.read_text(encoding="utf-8")
    if not BLOCK_RE.search(original):
        raise RuntimeError(
            f"sentinel block not found in {prompts_path} — "
            f"expected {BEGIN!r} ... {END!r}"
        )
    updated = BLOCK_RE.sub(new_block, original, count=1)

    if not dry_run and updated != original:
        prompts_path.write_text(updated, encoding="utf-8")

    return {
        "agent_id": agent_id,
        "feedback_dir": str(feedback_dir),
        "records_total": len(records),
        "examples_injected": len(examples),
        "prompts_path": str(prompts_path),
        "changed": updated != original,
        "dry_run": dry_run,
    }


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract few-shot examples from feedback JSONL → inject prompts.py",
    )
    parser.add_argument(
        "--agent", default="channel",
        help=f"agent id, one of {sorted(SUPPORTED_AGENTS)} (default: channel)",
    )
    parser.add_argument(
        "--max-n", type=int, default=3,
        help="max few-shot examples to inject (default: 3)",
    )
    parser.add_argument(
        "--feedback-dir",
        help="override feedback dir (default: data/feedback)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="preview without writing",
    )
    args = parser.parse_args(argv)

    fb_dir = Path(args.feedback_dir) if args.feedback_dir else None
    summary = extract_and_inject(
        agent_id=args.agent,
        max_n=args.max_n,
        feedback_dir=fb_dir,
        dry_run=args.dry_run,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
