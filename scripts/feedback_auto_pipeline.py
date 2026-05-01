# -*- coding: utf-8 -*-
"""Phase B Sprint 2 决策 2 · few-shot 自动 pipeline · 替换 PoC hardcode.

链路:
  data/feedback/*.jsonl (last 30 days)
    ↓ filter (rating>=4 + len>=100 + has_diff + within 30d · AND)
    ↓ per-agent top 10 by created_at desc
    ↓ similarity dedup > 0.85 (shared.similarity)
    ↓ PII redact (复用 agent_credit.prompts._redact_value)
  candidates payload → write data/fewshot/<agent>-candidates.json
    ↓ scripts/inject_fewshot_to_prompts.py --auto
  agent_*/prompts.py FEW_SHOT_EXAMPLES 替换 (marker 块覆盖)

红线 (per dispatch):
  - LIUYE_FEWSHOT_POC_ENABLED 默认 off (build_system_prompt 仍 gated · 注入也无副作用)
  - PII redaction 必复用 _redact_pii / _redact_value (不另写)

Cron 触发:
  ops/cron-fewshot-rotate.sh · 每周日 2am · git commit signal FEW-SHOT-ROTATED-WEEKLY

CLI:
  py scripts/feedback_auto_pipeline.py                 # 全 agent · 30 天窗
  py scripts/feedback_auto_pipeline.py --agent credit  # 单 agent
  py scripts/feedback_auto_pipeline.py --window-days 14
  py scripts/feedback_auto_pipeline.py --dry-run       # 不写 candidates / 不 inject
  py scripts/feedback_auto_pipeline.py --no-inject     # 写 candidates 但不调 inject

Exit code:
  0 全 agent 成功 (含 0 example · 视作 noop 成功)
  1 部分 agent inject 失败
  2 fixture / 配置错误
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

logger = logging.getLogger("feedback_auto_pipeline")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

FEEDBACK_DIR = PROJECT_ROOT / "data" / "feedback"
FEWSHOT_DIR = PROJECT_ROOT / "data" / "fewshot"
ALLOWED_AGENTS = {"channel", "credit", "alert", "compliance", "report", "riskctrl"}

# 决策 2 阈值
MIN_RATING = 4
MIN_FEEDBACK_LEN = 100  # correction_reason + correction values 合并字符数
TOP_N_PER_AGENT = 10
DEDUP_THRESHOLD = 0.85
DEFAULT_WINDOW_DAYS = 30


def _has_diff(rec: dict) -> bool:
    """audit_modify 类: original_output 与 user_correction 真有差 · 不是 thumbs-up."""
    orig = rec.get("original_output") or {}
    corr = rec.get("user_correction") or {}
    if not isinstance(orig, dict) or not isinstance(corr, dict):
        return False
    if not corr:
        return False
    for k, v in corr.items():
        if orig.get(k) != v:
            return True
    return False


def _feedback_length(rec: dict) -> int:
    """决策 2 · correction_reason + correction values 合并字符数."""
    reason = str(rec.get("correction_reason") or "")
    corr = rec.get("user_correction") or {}
    if isinstance(corr, dict):
        corr_str = json.dumps(corr, ensure_ascii=False)
    else:
        corr_str = str(corr)
    return len(reason) + len(corr_str)


def _parse_ts(rec: dict) -> datetime | None:
    ts = rec.get("timestamp")
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _passes_quality(rec: dict, *, window_start: date) -> bool:
    """决策 2 高质量 4 必要条件 (AND)."""
    rating = rec.get("rating")
    if not isinstance(rating, int) or rating < MIN_RATING:
        return False
    if _feedback_length(rec) < MIN_FEEDBACK_LEN:
        return False
    if not _has_diff(rec):
        return False
    ts = _parse_ts(rec)
    if ts is None or ts.date() < window_start:
        return False
    return True


def _scan_feedback(
    feedback_dir: Path, *, agent: str | None, window_days: int,
) -> list[dict]:
    if not feedback_dir.exists():
        return []
    cutoff = date.today() - timedelta(days=window_days)
    out: list[dict] = []
    for path in sorted(feedback_dir.glob("*.jsonl")):
        try:
            file_date = datetime.strptime(path.stem, "%Y-%m-%d").date()
        except ValueError:
            continue
        if file_date < cutoff:
            continue
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if agent and rec.get("agent") != agent:
                        continue
                    out.append(rec)
        except OSError:
            continue
    return out


def _dedup_by_similarity(records: list[dict], threshold: float) -> list[dict]:
    """O(N^2) · N 是 per-agent · 30 天 PoC 数百级足够 · 大数据时换 minhash."""
    from shared.similarity import is_duplicate
    kept: list[dict] = []
    for rec in records:
        rec_payload = {
            "reason": rec.get("correction_reason"),
            "correction": rec.get("user_correction"),
        }
        is_dup = False
        for k in kept:
            k_payload = {
                "reason": k.get("correction_reason"),
                "correction": k.get("user_correction"),
            }
            if is_duplicate(rec_payload, k_payload, threshold=threshold):
                is_dup = True
                break
        if not is_dup:
            kept.append(rec)
    return kept


def _build_examples(records: list[dict]) -> list[dict]:
    """转 records → candidates schema · 复用 agent_credit._redact_value 防 PII 漏出.

    红线: 必走 _redact_value (per Sprint 1 V2 PII 回归)
    """
    from agent_credit.prompts import _redact_pii, _redact_value
    examples: list[dict] = []
    for rec in records:
        reason = _redact_pii(str(rec.get("correction_reason") or "").strip())
        sample_input = _redact_value(rec.get("original_output") or {})
        preferred = _redact_value(rec.get("user_correction") or {})
        if not reason or not preferred:
            continue
        diff_keys = [
            k for k in preferred.keys()
            if isinstance(preferred, dict) and preferred.get(k) != (sample_input or {}).get(k)
        ][:5]
        diff_summary = "; ".join(
            f"{k}: {(sample_input or {}).get(k)} → {preferred.get(k)}"
            for k in diff_keys
        )
        examples.append({
            "cluster_id": f"auto-{rec.get('session_id', 'noid')}",
            "count": 1,
            "rating": rec.get("rating"),
            "reason": reason,
            "sample_input": sample_input,
            "preferred_output": preferred,
            "diff_summary": _redact_pii(diff_summary),
            "first_seen": rec.get("timestamp", ""),
            "last_seen": rec.get("timestamp", ""),
            "source": "auto-pipeline",
        })
    return examples


def aggregate_for_agent(
    records: list[dict],
    *,
    window_days: int,
    top_n: int = TOP_N_PER_AGENT,
    dedup_threshold: float = DEDUP_THRESHOLD,
) -> list[dict]:
    cutoff = date.today() - timedelta(days=window_days)
    quality = [r for r in records if _passes_quality(r, window_start=cutoff)]
    quality.sort(key=lambda r: r.get("timestamp") or "", reverse=True)
    deduped = _dedup_by_similarity(quality, dedup_threshold)
    return _build_examples(deduped[:top_n])


def write_candidates(out_dir: Path, agent: str, examples: list[dict]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{agent}-candidates.json"
    payload = {
        "agent": agent,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "schema_version": 2,  # bumped from 1 (manual SOP) to 2 (auto pipeline)
        "source": "auto-pipeline",
        "examples": examples,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def call_inject(agent: str, fewshot_dir: Path) -> int:
    """call inject script as subprocess · returncode 0/1 propagate."""
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "inject_fewshot_to_prompts.py"),
        "--agent", agent,
        "--fewshot-dir", str(fewshot_dir),
    ]
    proc = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        logger.error("inject %s failed: %s", agent, proc.stderr)
    else:
        logger.info("inject %s: %s", agent, proc.stdout.strip().splitlines()[-1] if proc.stdout else "ok")
    return proc.returncode


def run_pipeline(
    *,
    agents: list[str],
    feedback_dir: Path = FEEDBACK_DIR,
    fewshot_dir: Path = FEWSHOT_DIR,
    window_days: int = DEFAULT_WINDOW_DAYS,
    dry_run: bool = False,
    no_inject: bool = False,
) -> int:
    rc_final = 0
    for agent in agents:
        records = _scan_feedback(feedback_dir, agent=agent, window_days=window_days)
        examples = aggregate_for_agent(records, window_days=window_days)
        logger.info(
            "[%s] scanned=%d quality_dedup=%d window_days=%d",
            agent, len(records), len(examples), window_days,
        )
        if dry_run:
            continue
        if not examples:
            logger.info("[%s] 0 example · skip inject (PoC hardcode 不动)", agent)
            continue
        path = write_candidates(fewshot_dir, agent, examples)
        logger.info("[%s] wrote %s (%d example)", agent, path, len(examples))
        if no_inject:
            continue
        rc = call_inject(agent, fewshot_dir)
        if rc != 0:
            rc_final = max(rc_final, 1)
    return rc_final


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--agent", choices=sorted(ALLOWED_AGENTS), default=None)
    parser.add_argument("--window-days", type=int, default=DEFAULT_WINDOW_DAYS)
    parser.add_argument("--feedback-dir", default=str(FEEDBACK_DIR))
    parser.add_argument("--fewshot-dir", default=str(FEWSHOT_DIR))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-inject", action="store_true")
    args = parser.parse_args(argv)

    if args.window_days <= 0:
        logger.error("--window-days must be > 0")
        return 2

    agents = [args.agent] if args.agent else sorted(ALLOWED_AGENTS)
    return run_pipeline(
        agents=agents,
        feedback_dir=Path(args.feedback_dir),
        fewshot_dir=Path(args.fewshot_dir),
        window_days=args.window_days,
        dry_run=args.dry_run,
        no_inject=args.no_inject,
    )


if __name__ == "__main__":
    sys.exit(main())
