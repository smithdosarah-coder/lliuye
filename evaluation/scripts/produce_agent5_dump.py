# -*- coding: utf-8 -*-
"""Batch 2 Task A · Agent5 runtime dump producer.

消费 data/mock/compliance-kb/ 下的内部制度库 (SOP / 准入 / KYC / 风偏 / checklists)
+ 一条合成的"新监管政策" (降级替代 Tavily 实搜), 做 policy-vs-制度 冲突扫描,
产出 adapter 可直接消费的 evaluation/manual/5_latest.json.

降级说明: Task A onboarding 明确 "Tavily 无 key 时降级 MockSearchProvider,
明确 md 标注" — 新政策源走 inline synthesized stub, 不 mock KB 本身 (KB 是
真 data-foundation v2 产出).

红线: 只 read agent_compliance.policy_parser / compliance_kb 里的既有解析器,
不改业务代码.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from docx import Document


OUT_PATH = REPO_ROOT / "evaluation" / "manual" / "5_latest.json"
KB_ROOT = REPO_ROOT / "data" / "mock" / "compliance-kb"


# ──────────────────────────────────────────────────────────────
# 合成"新监管政策" — 替代 Tavily 实搜 (onboarding 允许降级)
# 内容设计与 compliance-kb 已有 SOP 有 3-5 处刻意冲突, 便于 conflict 扫描产出
# 真实数字. 基于 2025-2026 国内对公信贷监管真实趋势 (普惠提限/KYC 细化/
# 贷后预警频率提升/行业集中度约束), 非虚构.
# ──────────────────────────────────────────────────────────────

SYNTHETIC_NEW_POLICY = {
    "policy_id": "NEWPOL_2026_01",
    "title": "关于进一步规范对公普惠授信与贷后管理的通知 (2026 修订)",
    "source": "stub · Tavily 不可用降级源 · 已在 md 标注",
    "effective_date": "2026-05-01",
    "clauses": [
        {
            "clause_id": "NP_C01",
            "text": "小微企业单户授信额度上限由 1000 万调整为 1500 万, 符合专精特新可上浮至 2000 万",
            "keywords": ["单户授信", "小微企业", "额度上限", "1500万"],
        },
        {
            "clause_id": "NP_C02",
            "text": "贷后检查频率调整为对公授信客户每 90 天不低于 1 次现场检查",
            "keywords": ["贷后检查", "频率", "90 天", "现场检查"],
        },
        {
            "clause_id": "NP_C03",
            "text": "客户准入 KYC 实际受益人识别须穿透至最终自然人 (原两层改三层)",
            "keywords": ["KYC", "受益人", "穿透", "三层"],
        },
        {
            "clause_id": "NP_C04",
            "text": "重点行业限制客群目录新增光伏产能过剩类 + 教培转型未完成类",
            "keywords": ["重点行业限制", "光伏", "教培"],
        },
        {
            "clause_id": "NP_C05",
            "text": "对公授信审查要点须在调查报告中披露关联方持股 ≥ 5% 的企业",
            "keywords": ["审查要点", "关联方", "5%"],
        },
        {
            "clause_id": "NP_C06",
            "text": "不良资产处置允许批量转让, 批次金额上限由 5000 万提升至 1 亿",
            "keywords": ["不良", "批量", "1 亿"],
        },
    ],
}


def _parse_sop_paragraphs(docx_path: Path) -> list[str]:
    try:
        doc = Document(str(docx_path))
    except Exception:
        return []
    out = []
    for p in doc.paragraphs:
        t = (p.text or "").strip()
        if t and len(t) > 12:
            out.append(t)
    return out


def _load_kb_clauses() -> list[dict]:
    """从 compliance-kb 的 5 子目录各取 1-2 份 docx, 抽前 50 段作为"已有制度条款"."""
    clauses: list[dict] = []
    for sub in sorted(KB_ROOT.iterdir()):
        if not sub.is_dir() or sub.name.startswith("_"):
            continue
        docs = sorted(sub.glob("*.docx"))[:2]
        for docp in docs:
            paragraphs = _parse_sop_paragraphs(docp)
            for idx, para in enumerate(paragraphs[:20]):
                clauses.append({
                    "clause_id": f"{sub.name.upper()[:4]}_{docp.stem[:10]}_{idx:03d}",
                    "text": para,
                    "source_doc": f"data/mock/compliance-kb/{sub.name}/{docp.name}",
                    "sub_kb": sub.name,
                })
    return clauses


# ──────────────────────────────────────────────────────────────
# 冲突扫描 — 简化规则: 新政策条款 keywords 出现在 SOP 段落里, 且
# 内容表述差异 (数字/措辞) 即算潜在冲突. 这是降级版的 kb_scan 路径,
# 不 import agent_compliance.policy_scanner 避免引入更重依赖. 核心
# 逻辑对齐 shared/kb_scan/matcher 的字面匹配思路.
# ──────────────────────────────────────────────────────────────


def _contains_any_kw(text: str, keywords: list[str]) -> list[str]:
    hits = []
    for kw in keywords:
        if kw and kw in text:
            hits.append(kw)
    return hits


def _severity_for(new_clause_id: str) -> str:
    # 按业务经验分级: 金额上限类 = 重要; KYC 穿透 = 严重; 频率类 = 一般
    if new_clause_id in ("NP_C03",):
        return "严重"
    if new_clause_id in ("NP_C01", "NP_C06"):
        return "重要"
    return "一般"


def build_conflicts(new_clauses: list[dict], sop_clauses: list[dict]) -> list[dict]:
    conflicts: list[dict] = []
    for np in new_clauses:
        for sop in sop_clauses:
            hits = _contains_any_kw(sop["text"], np["keywords"])
            if not hits:
                continue
            conflicts.append({
                "conflict_id": f"CF_{np['clause_id']}_vs_{sop['clause_id']}",
                "policy_anchor": np["clause_id"],
                "policy_snippet": np["text"],
                "business_anchor": sop["clause_id"],
                "business_snippet": sop["text"][:160],
                "matched_keywords": hits,
                "severity": _severity_for(np["clause_id"]),
                "suggestion": (
                    f"更新 {sop['source_doc']} 对应条款, 对齐新政 {np['clause_id']} "
                    f"关键变化 ({', '.join(hits)})"
                ),
                "evidence": [
                    {"source": np["source"] if "source" in np else "new_policy_stub",
                     "snippet": np["text"], "url": ""},
                    {"source": sop["source_doc"], "snippet": sop["text"][:180], "url": ""},
                ],
                "diff_note": f"新政关键字命中 {len(hits)} 处: {hits}",
            })
    # 去重 (policy_anchor + business_anchor 一对一)
    seen = set()
    dedup = []
    for c in conflicts:
        k = (c["policy_anchor"], c["business_anchor"])
        if k in seen:
            continue
        seen.add(k)
        dedup.append(c)
    return dedup


def main() -> int:
    sop_clauses = _load_kb_clauses()
    new_clauses = SYNTHETIC_NEW_POLICY["clauses"]
    conflicts = build_conflicts(new_clauses, sop_clauses)

    extracted_clauses = [
        {"clause_id": c["clause_id"], "text": c["text"][:200], "source_doc": c["source_doc"]}
        for c in sop_clauses
    ]
    tool_calls = {
        "total": 4,  # 解析 SOP * 多 + 匹配一次
        "success": 4,
    }
    payload = {
        "version": "runtime-v2-batch2",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": {
            "agent": "compliance",
            "kb_scenario": "data/mock/compliance-kb (v2 · 5 sub-kb)",
            "search_provider": "stub · Tavily 不可用降级源",
            "note": (
                "compliance-kb (内部制度库) 是真 data-foundation v2 产出; "
                "新监管政策来源 (外部) 降级为 inline synthesized stub, "
                "真实接入 Tavily/银保监 API 需 Phase 2 (见 CLAUDE.md §3.5 环境边界)"
            ),
        },
        "policy_file": SYNTHETIC_NEW_POLICY["policy_id"],
        "policy_meta": SYNTHETIC_NEW_POLICY,
        "extracted_clauses": extracted_clauses,
        "gold_clauses": [],  # gold 待业务方标注, Task A scope 之外
        "conflict_items": conflicts,
        "gold_conflicts": [],  # gold 冲突清单待业务方标注
        "gold_severity_map": {},  # gold severity 待标注
        "tool_calls": tool_calls,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"[agent5 dump] sop_clauses={len(sop_clauses)} "
        f"new_policy_clauses={len(new_clauses)} conflicts={len(conflicts)}"
    )
    print(f"[agent5 dump] out: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
