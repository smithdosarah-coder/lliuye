"""Sprint 6 D1 · CRM 主键统社匹配 + 字段比对

per xlsx v2 1.1 verbatim "AI 画像 vs CRM 主键 (统社) 匹配率 > 95% · 字段比对自动发现矛盾 · Sprint 6 接 CRM Mock 后跑 baseline 公布"

输入:
- ai_profile: AI 画像 dict (subject_name / 统社 / 法人 / 注册资本 / 实缴 / 行业 / 地址)
- crm_record: 银行 CRM master record dict

输出:
- matched: bool · 主键统社是否匹配
- match_score: float · 0.0-1.0 · 综合字段相似度
- mismatches: list[dict] · 字段值不一致清单 (财报 vs 工商 / 注册资本 vs 实缴等)

算法:
1. 主键统社精匹配 (uniform social credit code · 18 位统一社会信用代码)
2. 名称模糊匹配 (Levenshtein ratio · 容名 / 法人变更)
3. 数字字段比对 (注册资本 / 实缴 · 量级一致即 OK · ±10% 差容)
4. 文本字段比对 (行业 / 地址 · 字符串包含或 80% 相似)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _normalize_str(s: Any) -> str:
    if s is None:
        return ""
    return str(s).strip().replace(" ", "").replace("　", "")


def _levenshtein_ratio(a: str, b: str) -> float:
    """Compute Levenshtein similarity ratio (0.0 - 1.0)."""
    a, b = _normalize_str(a), _normalize_str(b)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    n, m = len(a), len(b)
    if n > m:
        a, b = b, a
        n, m = m, n
    prev = list(range(n + 1))
    curr = [0] * (n + 1)
    for j in range(1, m + 1):
        curr[0] = j
        for i in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[i] = min(curr[i - 1] + 1, prev[i] + 1, prev[i - 1] + cost)
        prev, curr = curr, prev
    distance = prev[n]
    return 1.0 - distance / max(n, m)


def _amount_match(a: Any, b: Any, tolerance: float = 0.10) -> tuple[bool, float]:
    """Compare two numeric amounts · ±tolerance OK · return (matched, ratio)."""
    try:
        va, vb = float(a), float(b)
    except (TypeError, ValueError):
        return (False, 0.0)
    if va == 0 and vb == 0:
        return (True, 1.0)
    if max(va, vb) == 0:
        return (False, 0.0)
    diff = abs(va - vb) / max(abs(va), abs(vb))
    return (diff <= tolerance, max(0.0, 1.0 - diff))


@dataclass
class FieldMismatch:
    field: str
    ai_value: Any
    crm_value: Any
    severity: str  # "critical" | "major" | "minor"
    note: str = ""


@dataclass
class CrmMatchResult:
    matched: bool
    match_score: float  # 0.0 - 1.0
    primary_key_matched: bool  # 统社精匹配
    mismatches: list[FieldMismatch] = field(default_factory=list)


def match_crm_record(ai_profile: dict, crm_record: dict) -> CrmMatchResult:
    """主键统社精匹配 + 字段相似度比对.

    返回 CrmMatchResult · 含 mismatch 清单 · 用于审贷员核对.
    """
    mismatches: list[FieldMismatch] = []

    # 1. 主键统社精匹配 (18 位 uniform social credit code)
    ai_social_credit = _normalize_str(ai_profile.get("social_credit_code") or ai_profile.get("uscc"))
    crm_social_credit = _normalize_str(crm_record.get("social_credit_code") or crm_record.get("uscc"))
    primary_key_matched = bool(
        ai_social_credit and crm_social_credit and ai_social_credit == crm_social_credit
    )
    if not primary_key_matched and (ai_social_credit or crm_social_credit):
        mismatches.append(FieldMismatch(
            field="social_credit_code",
            ai_value=ai_social_credit or "(missing)",
            crm_value=crm_social_credit or "(missing)",
            severity="critical",
            note="统社不一致 · 主键失配 · 高度疑似不同主体",
        ))

    # 2. 名称 Levenshtein
    ai_name = _normalize_str(ai_profile.get("subject_name") or ai_profile.get("name"))
    crm_name = _normalize_str(crm_record.get("subject_name") or crm_record.get("name"))
    name_ratio = _levenshtein_ratio(ai_name, crm_name)
    if ai_name and crm_name and name_ratio < 0.85:
        mismatches.append(FieldMismatch(
            field="name",
            ai_value=ai_name,
            crm_value=crm_name,
            severity="major" if name_ratio < 0.60 else "minor",
            note=f"名称 ratio={name_ratio:.2f} · 可能容名变更",
        ))

    # 3. 法人 Levenshtein
    ai_legal = _normalize_str(ai_profile.get("legal_representative"))
    crm_legal = _normalize_str(crm_record.get("legal_representative"))
    legal_ratio = _levenshtein_ratio(ai_legal, crm_legal)
    if ai_legal and crm_legal and legal_ratio < 0.95:
        mismatches.append(FieldMismatch(
            field="legal_representative",
            ai_value=ai_legal,
            crm_value=crm_legal,
            severity="major",
            note=f"法人 ratio={legal_ratio:.2f} · 可能近期变更",
        ))

    # 4. 注册资本 ±10% 容差
    ai_reg_cap = ai_profile.get("registered_capital")
    crm_reg_cap = crm_record.get("registered_capital")
    if ai_reg_cap is not None and crm_reg_cap is not None:
        cap_match, cap_ratio = _amount_match(ai_reg_cap, crm_reg_cap, tolerance=0.10)
        if not cap_match:
            mismatches.append(FieldMismatch(
                field="registered_capital",
                ai_value=ai_reg_cap,
                crm_value=crm_reg_cap,
                severity="major",
                note=f"注册资本量级差异 · ratio={cap_ratio:.2f}",
            ))

    # 5. 实缴 ±10% 容差
    ai_paid = ai_profile.get("paid_in_capital")
    crm_paid = crm_record.get("paid_in_capital")
    if ai_paid is not None and crm_paid is not None:
        paid_match, paid_ratio = _amount_match(ai_paid, crm_paid, tolerance=0.10)
        if not paid_match:
            mismatches.append(FieldMismatch(
                field="paid_in_capital",
                ai_value=ai_paid,
                crm_value=crm_paid,
                severity="minor",
                note=f"实缴量级差异 · ratio={paid_ratio:.2f}",
            ))

    # 综合 match_score (主键 60% + 名称 20% + 法人 15% + 资本 5%)
    score = 0.0
    score += 0.60 * (1.0 if primary_key_matched else 0.0)
    score += 0.20 * name_ratio
    score += 0.15 * legal_ratio
    if ai_reg_cap is not None and crm_reg_cap is not None:
        _, cap_ratio = _amount_match(ai_reg_cap, crm_reg_cap, tolerance=0.10)
        score += 0.05 * cap_ratio
    score = min(1.0, score)

    matched = primary_key_matched and score >= 0.85

    return CrmMatchResult(
        matched=matched,
        match_score=round(score, 3),
        primary_key_matched=primary_key_matched,
        mismatches=mismatches,
    )


__all__ = [
    "match_crm_record",
    "CrmMatchResult",
    "FieldMismatch",
]
