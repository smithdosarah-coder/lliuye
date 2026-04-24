# -*- coding: utf-8 -*-
"""Agent4 runtime dump — 跑一次 CustomerScanner 把 HitList 序列化成
adapter 消费 schema，落盘到 evaluation/manual/4_<date>.yaml。

对齐 phase0_scan_sample.json 的 schema：
  whitelist_entity_ids: list[str]
  customers: [
    {entity_id, name, grade, evidence[], scan_time_ms, status}
  ]
  tool_calls: {total, success}

与 Phase 0 合成 fixture 的差别：
  - 来源：真 AlertKnowledgeBase + CustomerScanner.scan（非人工拍分布）
  - evidence：HitItem.evidences 实际回填（含 external/internal route + source/url）
  - scan_time_ms：逐家 match_customer 计时
  - tool_calls：MockSearchProvider 的 court_records + news 调用计数

运行：
  py -m agent_alert.runtime_dump --out evaluation/manual/4_20260419.yaml
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any

import yaml

from shared.kb_scan.models import RiskLevel
from shared.kb_scan.search_provider import build_search_provider

from .cross_matcher import CrossMatcher
from .customer_scanner import CustomerScanner
from .knowledge_base import AlertKnowledgeBase


REPO_ROOT = Path(__file__).resolve().parent.parent


class _ToolCallCounter:
    """薄包一层 SearchProvider，只为统计 court_records + news 调用次数。
    成功 = 返回 list (不抛异常)。
    """

    def __init__(self, inner):
        self.inner = inner
        self.total = 0
        self.success = 0

    def _wrap(self, name: str):
        fn = getattr(self.inner, name)

        def _call(*args, **kwargs):
            self.total += 1
            try:
                result = fn(*args, **kwargs)
                if isinstance(result, list):
                    self.success += 1
                return result
            except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError):
                return []

        return _call

    def __getattr__(self, name):
        base = getattr(self.inner, name)
        if name in ("search_court_records", "search_news"):
            return self._wrap(name)
        return base


def _git_head() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True, timeout=5,
        )
        return r.stdout.strip()
    except (OSError, subprocess.SubprocessError, ValueError):
        return "unknown"


def _serialize_hit(hit, scan_time_ms: float) -> dict[str, Any]:
    grade = hit.level.value if isinstance(hit.level, RiskLevel) else str(hit.level)
    evidence = [
        {
            "type": "external"
            if ev.source and ("搜索" in ev.source or "舆情" in ev.source
                              or "裁判" in ev.source or "标签" in ev.source)
            else "internal",
            "signal": ev.snippet[:80] if ev.snippet else "",
            "source": ev.source,
            "url": ev.url or "",
        }
        for ev in (hit.evidences or [])
    ]
    trigger_reasons = (hit.extras or {}).get("trigger_reasons", [])
    return {
        "entity_id": hit.target.target_id,
        "name": hit.target.payload.get("company_name", ""),
        "grade": grade,
        "trigger_reasons": trigger_reasons,
        "evidence": evidence,
        "scan_time_ms": round(scan_time_ms, 2),
        "status": "completed",
    }


def dump(out_path: Path) -> dict[str, Any]:
    kb = AlertKnowledgeBase.from_scenario()
    inner_provider = build_search_provider(demo_mode=True)
    provider = _ToolCallCounter(inner_provider)
    matcher = CrossMatcher(provider)
    scanner = CustomerScanner(kb=kb, search_provider=provider, matcher=matcher)

    customers = scanner._resolve_customers()
    whitelist = [c.company_id or c.company_name for c in customers]

    rows: list[dict[str, Any]] = []
    rules = kb.rules
    for profile in customers:
        t0 = time.perf_counter()
        try:
            hit = matcher.match_customer(profile, rules)
            dt_ms = (time.perf_counter() - t0) * 1000.0
            rows.append(_serialize_hit(hit, dt_ms))
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError) as e:
            dt_ms = (time.perf_counter() - t0) * 1000.0
            rows.append({
                "entity_id": profile.company_id or profile.company_name,
                "name": profile.company_name,
                "grade": "green",
                "evidence": [],
                "scan_time_ms": round(dt_ms, 2),
                "status": f"failed:{type(e).__name__}",
            })

    payload = {
        "version": "runtime-v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": {
            "agent": "alert",
            "git_commit": _git_head(),
            "kb_scenario": "demo_data/agent_alert",
            "search_provider": "MockSearchProvider (demo_mode=True)",
        },
        "whitelist_entity_ids": whitelist,
        "customers": rows,
        "tool_calls": {
            "total": provider.total,
            "success": provider.success,
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)
    return payload


def main():
    ap = argparse.ArgumentParser(prog="python -m agent_alert.runtime_dump")
    ap.add_argument(
        "--out",
        default="evaluation/manual/4_20260419.yaml",
        help="output yaml path relative to repo root",
    )
    args = ap.parse_args()
    out = (REPO_ROOT / args.out) if not Path(args.out).is_absolute() else Path(args.out)
    payload = dump(out)
    n = len(payload["customers"])
    grades = {g: sum(1 for c in payload["customers"] if c["grade"] == g)
              for g in ("red", "yellow", "green")}
    tc = payload["tool_calls"]
    print(f"wrote {out}")
    print(f"customers={n}  grades={grades}  tool_calls={tc}")


if __name__ == "__main__":
    main()
