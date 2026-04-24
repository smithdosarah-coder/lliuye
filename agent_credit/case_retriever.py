# -*- coding: utf-8 -*-
"""CaseRetriever — 历史已决案例检索

对公 50 条 / 对私 10 条 Mock 案例。
相似度公式：
  对公 = 行业匹配(0.3) + 营收接近度(0.2) + 综合评分接近度(0.3) + 申请额度接近度(0.2)
  对私 = 档位匹配(0.4) + 抵押物类型(0.2) + 申请额度接近度(0.2) + 职业相似(0.2)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

_MOCK_DIR = Path(__file__).parent / "mock_data"


@dataclass
class CaseMatch:
    case_id: str
    company_name: str
    similarity: float
    features_summary: dict = field(default_factory=dict)
    decision: str = ""
    approved_amount: float = 0
    approved_term_months: int = 0
    interest_rate: float = 0
    decision_reason: str = ""
    hit_red_lines: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _closeness(a: float, b: float, scale: float = 1.0) -> float:
    """相对接近度：1 - |a-b| / (max(|a|,|b|,scale))，裁剪到 [0,1]"""
    try:
        af, bf = float(a), float(b)
    except (TypeError, ValueError):
        return 0.0
    denom = max(abs(af), abs(bf), scale)
    if denom == 0:
        return 1.0
    diff = abs(af - bf) / denom
    return max(0.0, 1.0 - diff)


class CaseRetriever:
    def __init__(self):
        self._cases: dict[str, list[dict]] = {}

    def _load(self, segment: str) -> list[dict]:
        if segment in self._cases:
            return self._cases[segment]
        filename = "corporate_cases.json" if segment == "corporate" else "retail_cases.json"
        path = _MOCK_DIR / filename
        cases: list[dict] = []
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    cases = json.load(fh) or []
            except (OSError, json.JSONDecodeError, ValueError, TypeError):
                cases = []
        self._cases[segment] = cases
        return cases

    def retrieve(self, features: dict, segment: str, top_k: int = 5,
                 scoring_result=None) -> list[CaseMatch]:
        cases = self._load(segment)
        if segment == "corporate":
            target_industry = features.get("meta.industry_code") or features.get("industry.code", "")
            target_revenue = features.get("financial.revenue", 0) or 0
            target_composite = getattr(scoring_result, "composite_score", 0) if scoring_result else 0
            target_amount = features.get("request.amount", 0) or 0

            scored = []
            for c in cases:
                sim_ind = 1.0 if c.get("industry") == target_industry else 0.3
                sim_rev = _closeness(c.get("revenue", 0), target_revenue, scale=10000)
                sim_sco = _closeness(c.get("composite_score", 0), target_composite, scale=30)
                sim_amt = _closeness(c.get("requested_amount", 0), target_amount, scale=200)
                sim = 0.3 * sim_ind + 0.2 * sim_rev + 0.3 * sim_sco + 0.2 * sim_amt
                scored.append((c, sim))
        else:  # retail
            target_grade = getattr(scoring_result, "grade", "") if scoring_result else ""
            target_type = features.get("collateral.type", "")
            has_col = 1 if target_type and target_type != "无" else 0
            target_amount = features.get("request.amount", 0) or 0
            target_occ = features.get("meta.occupation", "")

            scored = []
            for c in cases:
                sim_grade = 1.0 if c.get("grade") == target_grade else 0.3
                sim_col = 1.0 if c.get("has_collateral") == bool(has_col) else 0.3
                sim_amt = _closeness((c.get("requested_amount", 0) or 0) * 10000, target_amount, scale=100000)
                sim_occ = 1.0 if c.get("occupation") == target_occ else 0.4
                sim = 0.4 * sim_grade + 0.2 * sim_col + 0.2 * sim_amt + 0.2 * sim_occ
                scored.append((c, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        matches: list[CaseMatch] = []
        for c, sim in scored[:top_k]:
            name = c.get("company_name") or c.get("name") or c.get("case_id", "")
            summary = {
                "industry": c.get("industry") or c.get("business_type") or "",
                "revenue_or_grade": c.get("revenue") or c.get("grade", ""),
                "composite_score": c.get("composite_score") or c.get("fico_score", ""),
            }
            matches.append(CaseMatch(
                case_id=c.get("case_id", ""),
                company_name=name,
                similarity=round(sim, 3),
                features_summary=summary,
                decision=c.get("decision", ""),
                approved_amount=float(c.get("approved_amount", 0) or 0),
                approved_term_months=int(c.get("approved_term_months", 0) or 0),
                interest_rate=float(c.get("interest_rate", 0) or 0),
                decision_reason=c.get("decision_reason", ""),
                hit_red_lines=list(c.get("hit_red_lines") or []),
            ))
        return matches
