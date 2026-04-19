# -*- coding: utf-8 -*-
"""Agent6 · 反馈飞轮提取器(第 3→4 环桥)

目的:
  把 data/feedback/YYYY-MM-DD.jsonl 中 agent=="report" 的条目 + data/feedback/bootstrap/6_*.yaml
  汇聚为 data/feedback/extracted/6_YYYYMMDD.yaml,供 prompts.py 的哨兵块消费
  注入 few-shot 示例。符合 CLAUDE.md §6 数据飞轮第 3→4 环闭环,不做 SFT。

DoD: L3-8(反馈飞轮 E2E)
对应 onboarding: docs/onboarding/agent6-phase-2.md Task A

流程:
  1. 加载 bootstrap/ 下所有 6_*.yaml(worker 先过一版)
  2. 扫 data/feedback/*.jsonl,过滤 agent=="report"(六个 Agent 共用一份 JSONL)
  3. 按 (chapter, field_path, correction_summary_hash) 去重
  4. 打分排序:高 priority > 近期 > 章节均衡
  5. 输出 YAML 到 data/feedback/extracted/6_YYYYMMDD.yaml

命令:
  py scripts/feedback_extract_agent6.py
  py scripts/feedback_extract_agent6.py --limit 10 --out custom.yaml

注意:
  - 不触 shared/ 不触 docs/contracts/
  - 不动任何已有模块接口,纯新增脚本
  - 脚本产物仅为 prompts.py 哨兵块消费,原 JSONL 永久保留
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEEDBACK_DIR = PROJECT_ROOT / "data" / "feedback"
BOOTSTRAP_DIR = FEEDBACK_DIR / "bootstrap"
EXTRACTED_DIR = FEEDBACK_DIR / "extracted"

AGENT_NAME = "report"
PRIORITY_WEIGHT = {"high": 3, "medium": 2, "low": 1}


def _ensure_dirs() -> None:
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)


def _stable_hash(payload: Any) -> str:
    try:
        s = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    except Exception:
        s = str(payload)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    return " ".join(text.split()).strip().lower()


def load_bootstrap(bootstrap_dir: Path = BOOTSTRAP_DIR) -> list[dict]:
    """读 bootstrap/6_*.yaml 进内存。worker 先过一版的种子样本。"""
    items: list[dict] = []
    if not bootstrap_dir.is_dir():
        return items
    for p in sorted(bootstrap_dir.glob("6_*.yaml")):
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[warn] failed to parse {p}: {e}", file=sys.stderr)
            continue
        if not isinstance(data, dict):
            continue
        data["_source"] = "bootstrap"
        data["_source_file"] = p.name
        items.append(data)
    return items


def load_feedback_jsonl(
    feedback_dir: Path = FEEDBACK_DIR,
    agent: str = AGENT_NAME,
) -> list[dict]:
    """扫 data/feedback/YYYY-MM-DD.jsonl,过滤 agent=={agent}。"""
    items: list[dict] = []
    if not feedback_dir.is_dir():
        return items
    for p in sorted(feedback_dir.glob("*.jsonl")):
        try:
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("agent") != agent:
                    continue
                rec["_source"] = "audit"
                rec["_source_file"] = p.name
                items.append(rec)
        except Exception as e:
            print(f"[warn] failed to read {p}: {e}", file=sys.stderr)
            continue
    return items


def _derive_dedup_key(item: dict) -> str:
    """按 (scenario+chapter+field_path+corrected_gist) 去重 — 覆盖 bootstrap/audit 两种形态。"""
    scenario = item.get("scenario") or ""
    chapter = item.get("chapter") or item.get("injection_hint", {}).get("target_chapter", "")
    field_path = (
        item.get("field_path")
        or item.get("original_output", {}).get("field_path", "")
        if isinstance(item.get("original_output"), dict)
        else item.get("field_path") or ""
    )
    corrected = item.get("corrected_output") or item.get("user_correction") or ""
    if isinstance(corrected, dict):
        corrected = json.dumps(corrected, sort_keys=True, ensure_ascii=False)
    return _stable_hash({
        "scenario": _normalize_text(str(scenario)),
        "chapter": str(chapter),
        "field_path": _normalize_text(str(field_path)),
        "corrected_gist": _normalize_text(str(corrected))[:200],
    })


def dedup(items: list[dict]) -> list[dict]:
    """去重:相同 (scenario, chapter, field_path, corrected_gist) 仅保留一条(优先 bootstrap)。"""
    by_key: dict[str, dict] = {}
    for it in items:
        k = _derive_dedup_key(it)
        if k not in by_key:
            by_key[k] = it
            continue
        prev = by_key[k]
        # bootstrap 优先于 audit;高 priority 优先
        prev_rank = (
            1 if prev.get("_source") == "bootstrap" else 0,
            PRIORITY_WEIGHT.get(prev.get("injection_hint", {}).get("priority", "medium"), 2),
        )
        cur_rank = (
            1 if it.get("_source") == "bootstrap" else 0,
            PRIORITY_WEIGHT.get(it.get("injection_hint", {}).get("priority", "medium"), 2),
        )
        if cur_rank > prev_rank:
            by_key[k] = it
    return list(by_key.values())


def _score(item: dict) -> tuple[int, int, str]:
    """打分:bootstrap 置顶 → priority → scenario 字母序(稳定)。"""
    is_bootstrap = 1 if item.get("_source") == "bootstrap" else 0
    priority = PRIORITY_WEIGHT.get(
        item.get("injection_hint", {}).get("priority", "medium"), 2
    )
    scenario = item.get("scenario") or "zzz"
    return (is_bootstrap, priority, scenario)


def rank_and_balance(items: list[dict], limit: int = 20) -> list[dict]:
    """章节均衡:单章不超过 limit/4,保证 1/2/3/4 章都有示例。"""
    sorted_items = sorted(items, key=_score, reverse=True)
    per_chapter_cap = max(1, limit // 4)
    counts: dict[str, int] = defaultdict(int)
    picked: list[dict] = []
    for it in sorted_items:
        chap = str(
            it.get("chapter")
            or it.get("injection_hint", {}).get("target_chapter", "other")
        )
        if counts[chap] >= per_chapter_cap:
            continue
        picked.append(it)
        counts[chap] += 1
        if len(picked) >= limit:
            break
    # 若仍不足 limit 且有剩余条目未受章节配额限制,补齐
    if len(picked) < limit:
        seen_ids = {id(x) for x in picked}
        for it in sorted_items:
            if id(it) in seen_ids:
                continue
            picked.append(it)
            if len(picked) >= limit:
                break
    return picked


def _shape_for_prompt(item: dict) -> dict:
    """转换为 prompts.py 哨兵块消费的 shape(稳定字段集)。"""
    hint = item.get("injection_hint") or {}
    return {
        "scenario": item.get("scenario") or "",
        "chapter": item.get("chapter")
        or hint.get("target_chapter", ""),
        "field_path": item.get("field_path") or "",
        "original_output": item.get("original_output") or item.get("original_output", ""),
        "corrected_output": item.get("corrected_output") or item.get("user_correction", ""),
        "correction_reason": item.get("correction_reason") or "",
        "injection_hint": {
            "target_chapter": hint.get("target_chapter"),
            "anchor": hint.get("anchor"),
            "pattern_tags": hint.get("pattern_tags", []),
            "priority": hint.get("priority", "medium"),
        },
        "source": item.get("_source") or "unknown",
        "source_file": item.get("_source_file") or "",
    }


def run(
    limit: int = 20,
    out_path: Path | None = None,
    feedback_dir: Path = FEEDBACK_DIR,
    bootstrap_dir: Path = BOOTSTRAP_DIR,
) -> Path:
    """主流程:加载 → 去重 → 打分 → 章节均衡 → 写 YAML。"""
    _ensure_dirs()
    bootstrap = load_bootstrap(bootstrap_dir)
    audit = load_feedback_jsonl(feedback_dir)
    merged = bootstrap + audit
    deduped = dedup(merged)
    picked = rank_and_balance(deduped, limit=limit)

    date = datetime.now().strftime("%Y%m%d")
    if out_path is None:
        out_path = EXTRACTED_DIR / f"6_{date}.yaml"

    payload = {
        "agent": AGENT_NAME,
        "extracted_at": datetime.now().isoformat(timespec="seconds"),
        "source_counts": {
            "bootstrap": sum(1 for x in bootstrap),
            "audit_jsonl": sum(1 for x in audit),
            "after_dedup": len(deduped),
            "picked": len(picked),
        },
        "items": [_shape_for_prompt(x) for x in picked],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=1000),
        encoding="utf-8",
    )
    print(f"[ok] extracted {len(picked)} items → {out_path}")
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser(description="Agent6 反馈飞轮提取器(3→4 环)")
    ap.add_argument("--limit", type=int, default=20, help="最多选取条目数(章节均衡)")
    ap.add_argument(
        "--out",
        type=str,
        default=None,
        help="自定义输出 YAML 路径;默认 data/feedback/extracted/6_YYYYMMDD.yaml",
    )
    ap.add_argument(
        "--feedback-dir",
        type=str,
        default=str(FEEDBACK_DIR),
        help="feedback 根目录(默认 data/feedback/)",
    )
    args = ap.parse_args()
    out = Path(args.out) if args.out else None
    fbd = Path(args.feedback_dir)
    run(
        limit=args.limit,
        out_path=out,
        feedback_dir=fbd,
        bootstrap_dir=fbd / "bootstrap",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
