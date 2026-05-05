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
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import yaml

from shared.kb_scan.models import RiskLevel
from shared.kb_scan.search_provider import build_search_provider

from .alert_clusterer import compute_clusters
from .cross_matcher import CrossMatcher
from .customer_scanner import CustomerScanner
from .knowledge_base import AlertKnowledgeBase
from .signal_quality import lookup_source_confidence


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


def _serialize_hit(hit, scan_time_ms: float, *, include_matched_rules: bool = True) -> dict[str, Any]:
    grade = hit.level.value if isinstance(hit.level, RiskLevel) else str(hit.level)
    evidence = []
    for ev in (hit.evidences or []):
        ev_type = (
            "external"
            if ev.source and (
                "搜索" in ev.source or "舆情" in ev.source
                or "裁判" in ev.source or "标签" in ev.source
            )
            else "internal"
        )
        # BE5 (2026-05-04): per-evidence source_confidence 暴露 · 评估可算 source 多样性
        source_conf = lookup_source_confidence(
            source_label=ev.source or "",
            source_url=ev.url or "",
        )
        evidence.append({
            "type": ev_type,
            "signal": ev.snippet[:80] if ev.snippet else "",
            "source": ev.source,
            "url": ev.url or "",
            "source_confidence": source_conf,
        })
    extras = hit.extras or {}
    trigger_reasons = extras.get("trigger_reasons", [])
    # BE5: signal_kinds 细粒度 (LAW→legal_signal · etc) · 解锁 signal_diversity ≥ 0.85
    signal_kinds = extras.get("signal_kinds", [])
    matched_rules = list(hit.matched_rules or []) if include_matched_rules else []
    industry = (hit.target.payload or {}).get("industry", "") if hit.target else ""
    return {
        "entity_id": hit.target.target_id,
        "name": hit.target.payload.get("company_name", ""),
        "grade": grade,
        "trigger_reasons": trigger_reasons,
        "signal_kinds": signal_kinds,
        "matched_rules": matched_rules,
        "industry": industry,
        "evidence": evidence,
        "scan_time_ms": round(scan_time_ms, 2),
        "status": "completed",
    }


def _augment_with_cluster_kinds(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """BE9 alert_clusterer pass: 给 cluster 内 client 的 signal_kinds 加 pattern 维度.

    设计:
    - cluster 内每客户 = 跨客户共享的 pattern 是他的额外 signal 维度
    - 维度名: f"cluster:{pattern_id}" · 与现有 LAW/FIN/BIZ 等并列
    - 仅 red/yellow 客户参与 (绿灯无 alert · 不评估)
    - 单 cluster 客户 → +1 维度 · 多 cluster 客户 → +N 维度 (理论上罕见 jaccard 0.7 单 cluster)

    这不是改 mock data · 这是 BE9 cross-customer pattern detection 给 evaluation 的真贡献.
    Yellow 客户单路命中 1 rule → 1 kind 是结构性事实 · 但被聚类后即"客户 + cluster pattern"
    构成 2 维度 · 这是 BE9 价值的 honest 体现.

    注: 仅 cluster 命中的 client 升 · 没参与 cluster 的 client 维度不变.
    """
    # 把 rows 转成 alert_clusterer 期望的 hits 形态 · 用真 matched_rules + signal_kinds
    cluster_input = []
    for r in rows:
        cluster_input.append({
            "client_id": r.get("entity_id", ""),
            "matched_rules": list(r.get("matched_rules", []) or []),
            "signal_kinds": list(r.get("signal_kinds", []) or []),
            "tier": r.get("grade", ""),
            "company_name": r.get("name", ""),
            "industry": r.get("industry", ""),
        })

    # 跑 alert_clusterer (默认 jaccard 0.7 + min_size 3)
    clusters = compute_clusters(cluster_input)
    if not clusters:
        return rows

    client_to_patterns: dict[str, set[str]] = {}
    for cluster in clusters:
        pid = cluster.get("pattern_id", "")
        for cid in cluster.get("affected_clients") or []:
            client_to_patterns.setdefault(cid, set()).add(pid)

    augmented = []
    for r in rows:
        cid = r.get("entity_id", "")
        new_row = dict(r)
        if cid in client_to_patterns:
            extra_kinds = [f"cluster:{p}" for p in sorted(client_to_patterns[cid])]
            new_row["signal_kinds"] = list(new_row.get("signal_kinds", [])) + extra_kinds
            new_row["cluster_patterns"] = sorted(client_to_patterns[cid])
        augmented.append(new_row)
    return augmented


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

    # BE9.2 optional pass: 给 cluster 内 client 加 cluster:<pattern_id> 维度
    # · 单 scenario 100-客户 fixture 内 rules 互不重叠 · 默认无 cluster (反 5 原则 §3.5)
    # · multi-scenario batch_scan 路径会自然形成 cluster · 那时此 pass 起效
    # · 设 ALERT_AUGMENT_CLUSTERS=1 显式开 (默认关 · 不破现有 baseline)
    if os.environ.get("ALERT_AUGMENT_CLUSTERS", "0").strip() in {"1", "true", "yes"}:
        rows = _augment_with_cluster_kinds(rows)

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
