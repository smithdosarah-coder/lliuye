"""agent_credit.reason_codes — 标准理由码字典加载 + Top-5 推导。

字典位于 docs/reason_codes/agent3-{corporate,retail}.yaml。severity 严格遵守
field-naming v1.0：red / yellow / green。

推导流程（derive_top_reason_codes）：
1. 对每条 rule_hit，尝试按 `rule_id → code` 的 RULE_TO_CODE 映射直接命中；未命中
   时按 severity 回退到一个泛化码（默认红线泛码）。
2. 再按 features 里的定量指标触发阈值型码（DTI、负债率、在贷户数等）。
3. 按决策路径（decision）对 decision_hint 命中度加分，最后按 severity 权重
   （red=3 / yellow=2 / green=1）+ 命中度排序，取 Top-5。
4. 每条输出 `{code, title, severity, evidence_path, description}`，
   evidence_path 已解析为 features_snapshot 里的真实值（若能查到）。
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CODES_DIR = Path(__file__).resolve().parent.parent / "docs" / "reason_codes"

# rule_engine v2 mock rule_id（小写）→ 标准理由码。未命中的 rule 走 severity 回退码。
# DEMO 阶段：规则库 30/20 条的精确映射由后续迭代补齐，当前覆盖已知高频条目。
CORPORATE_RULE_CODE_MAP: dict[str, str] = {
    "corp_rl_001": "R_CORP_CUSTOMER_CONCENTRATION",
}

RETAIL_RULE_CODE_MAP: dict[str, str] = {
    "retail_rl_001": "R_RET_OVERDUE_SEVERE",
}

SEVERITY_WEIGHT = {"red": 3, "yellow": 2, "green": 1}


@dataclass
class ReasonCode:
    code: str
    title: str
    severity: str
    decision_hint: list[str]
    evidence_path: str = ""
    threshold: float | None = None
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "title": self.title,
            "severity": self.severity,
            "decision_hint": list(self.decision_hint),
            "evidence_path": self.evidence_path,
            "threshold": self.threshold,
            "description": self.description,
        }


@lru_cache(maxsize=4)
def load_codes(segment: str) -> dict[str, ReasonCode]:
    seg = _normalize_segment(segment)
    path = CODES_DIR / f"agent3-{seg}.yaml"
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out: dict[str, ReasonCode] = {}
    for item in raw.get("codes", []):
        try:
            code = ReasonCode(
                code=item["code"],
                title=item["title"],
                severity=item.get("severity", "green"),
                decision_hint=item.get("decision_hint", []) or [],
                evidence_path=item.get("evidence_path", ""),
                threshold=item.get("threshold"),
                description=item.get("description", ""),
            )
            out[code.code] = code
        except KeyError:
            continue
    return out


def _normalize_segment(segment: str) -> str:
    return "retail" if segment in ("retail", "sme") else "corporate"


def _lookup_evidence(features: dict, dot_path: str) -> Any:
    """从 features_snapshot 读取 dot-path；未命中返回 None。"""
    if not dot_path or not features:
        return None
    # features 已是扁平 dot-path（extractor 产出就是扁平），直接命中
    if dot_path in features:
        return features[dot_path]
    # 退化：尝试按 dict 树路径解析
    cur: Any = features
    for part in dot_path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def derive_top_reason_codes(
    segment: str,
    decision: str,
    rule_hits: Iterable[Any],
    features: dict,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    """推导 Top-N 标准理由码。

    Args:
        segment: corporate | retail | sme
        decision: 批准 / 有条件批准 / 拒绝
        rule_hits: list of RedLineHit (需有 rule_id, severity 属性)
        features: DecisionAdvice.features_snapshot（flatten dot-path）
        top_n: 截断上限，默认 5
    """
    seg = _normalize_segment(segment)
    codes = load_codes(seg)
    if not codes:
        return []
    rule_map = CORPORATE_RULE_CODE_MAP if seg == "corporate" else RETAIL_RULE_CODE_MAP

    picked: dict[str, dict[str, Any]] = {}

    # 1) rule_hits 优先
    for h in rule_hits or []:
        rid = getattr(h, "rule_id", "") or ""
        sev = getattr(h, "severity", "green") or "green"
        code_id = rule_map.get(rid)
        if code_id and code_id in codes:
            picked.setdefault(code_id, _pack(codes[code_id], features, matched_by="rule", rule=h))
            continue
        # 回退：按 severity 取一个默认泛码
        fallback = _severity_fallback(seg, sev)
        if fallback and fallback in codes:
            picked.setdefault(fallback, _pack(codes[fallback], features, matched_by="severity", rule=h))

    # 2) features 阈值型
    for code in codes.values():
        if code.code in picked:
            continue
        if not _feature_matches(code, features, decision):
            continue
        picked[code.code] = _pack(code, features, matched_by="feature")

    # 3) 若条数不足 top_n，按 decision_hint 命中度补 green/yellow 码
    if len(picked) < top_n:
        for code in codes.values():
            if code.code in picked:
                continue
            if decision in (code.decision_hint or []):
                picked[code.code] = _pack(code, features, matched_by="decision_hint")
            if len(picked) >= top_n:
                break

    # 排序：matched_by 优先级 (rule > feature > severity > decision_hint) + severity 权重
    priority = {"rule": 4, "feature": 3, "severity": 2, "decision_hint": 1}
    ranked = sorted(
        picked.values(),
        key=lambda x: (
            priority.get(x.get("matched_by", ""), 0),
            SEVERITY_WEIGHT.get(x.get("severity", "green"), 0),
        ),
        reverse=True,
    )
    return ranked[:top_n]


def _feature_matches(code: ReasonCode, features: dict, decision: str) -> bool:
    """定量阈值型码触发判断。只覆盖常见几种字段。"""
    if not code.evidence_path or code.threshold is None:
        return False
    val = _lookup_evidence(features, code.evidence_path)
    if val is None or not isinstance(val, (int, float)):
        return False
    thr = code.threshold
    # red：越大越坏（debt_ratio、dti、util、query_count、loans_count）→ val >= thr
    # green：越大越好（scoring.*、months_paid、years_in_job）→ val >= thr
    # yellow：介于两档，仍使用 val >= thr 口径（绿色阈值一般是好码下限）
    if code.severity == "red":
        return val >= thr
    if code.severity == "yellow":
        # yellow 阈值下限；但不能超过同组 red 阈值（由人工维护 YAML 保证）
        return val >= thr
    if code.severity == "green":
        # green 码要求指标达到阈值；但若值是比率且方向是「越小越好」（如 ltv），用 <=
        if code.evidence_path.endswith("ltv"):
            return val <= thr
        return val >= thr
    return False


def _severity_fallback(seg: str, severity: str) -> str | None:
    if seg == "corporate":
        return {
            "red": "R_CORP_OVERDUE_MATERIAL",
            "yellow": "R_CORP_CASHFLOW_TIGHT",
            "green": "R_CORP_FINANCIAL_STRONG",
        }.get(severity)
    return {
        "red": "R_RET_OVERDUE_SEVERE",
        "yellow": "R_RET_DTI_HIGH",
        "green": "R_RET_CREDIT_CLEAN",
    }.get(severity)


def _pack(code: ReasonCode, features: dict, matched_by: str, rule: Any = None) -> dict[str, Any]:
    evidence_value = _lookup_evidence(features, code.evidence_path)
    packed = code.to_dict()
    packed["matched_by"] = matched_by
    packed["evidence_value"] = _jsonable(evidence_value)
    if rule is not None:
        packed["rule_id"] = getattr(rule, "rule_id", "")
        packed["actual_value"] = _jsonable(getattr(rule, "actual_value", None))
    return packed


def _jsonable(v: Any) -> Any:
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    try:
        return str(v)
    except (TypeError, ValueError):
        return None
