"""异常/缺失数据处理 · 关键字段缺失时 AI 不硬判

per Phase C charter Track B · B4 · 异常/缺失数据处理 (Codex R3 verbatim "银行客户最怕页面无声失败 / AI 胡说 / 数据半加载"):

设计:
- check_missing_fields(profile, required_fields) → list of missing
- check_anomaly_fields(profile) → 检异常 (e.g. age=200 / debt_ratio=10 / 年龄≥80 但活跃理财)
- safe_decision_envelope(decision, missing, anomaly) → 决策包 wrap missing/anomaly notice
- AI 输出层用 safe_decision_envelope · 缺字段 → 显式 "未能自动填写" + 提示 RM 补录
- UI 降级 → 显式缺失项清单 + 不假装跑通

DP3 PM 拍板 '缺核心证据 block' 与本模块 wire 关系:
- block · 决策完全阻断 (前面 ai_decision 已实现)
- missing fields · 单字段缺失 · 决策仍跑 但显式标注 (B4 责任)
- anomaly fields · 数据反常 · 决策仍跑 但 RM 必看告警 (B4 责任)

使用:
    from shared.data_completeness import check_missing_fields, check_anomaly_fields, safe_decision_envelope

    missing = check_missing_fields(profile, ["income_monthly", "risk_level"])
    anomaly = check_anomaly_fields(profile)
    enveloped = safe_decision_envelope(decision, missing=missing, anomaly=anomaly)
"""
from __future__ import annotations

from typing import Any, Optional


# AI 决策必需字段 (from ai_decision.py mock_reasons_for_profile)
DECISION_CRITICAL_FIELDS = {
    "name", "age", "consent_status", "risk_level", "income_monthly",
    "credit_score", "debt_ratio", "employment_status",
}

# 推荐增强字段 (有的话决策更准 · 缺的话不阻)
DECISION_NICE_TO_HAVE_FIELDS = {
    "occupation", "city", "existing_products", "last_contact_at",
    "relationship_manager_id",
}


def check_missing_fields(
    profile: dict[str, Any],
    required: Optional[set[str]] = None,
    *,
    null_means_missing: bool = True,
) -> list[str]:
    """检缺失字段 · 返字段名列表."""
    if required is None:
        required = DECISION_CRITICAL_FIELDS
    missing: list[str] = []
    for field in required:
        v = profile.get(field)
        if v is None and null_means_missing:
            missing.append(field)
        elif isinstance(v, str) and not v.strip() and null_means_missing:
            missing.append(field)
    return missing


def check_anomaly_fields(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """检数据异常 · 返异常清单 (含字段 + 异常 + severity).

    个人金融场景 · 加 reasonable 范围 check:
    - age: 18-120
    - income_monthly: 0-10000000 (1000万/月顶天)
    - credit_score: 300-900
    - debt_ratio: 0-10 (1000% 顶天 · >10 极反常)
    - existing_products 与 employment_status 矛盾 (退休 + 0 持仓 = 反常 OR student + 高净值 = 反常)
    """
    anomalies: list[dict[str, Any]] = []

    age = profile.get("age")
    if age is not None and (age < 18 or age > 120):
        anomalies.append({
            "field": "age", "value": age, "severity": "critical",
            "note": f"年龄 {age} 超合理范围 (18-120)",
        })

    income = profile.get("income_monthly")
    if income is not None and (income < 0 or income > 10_000_000):
        anomalies.append({
            "field": "income_monthly", "value": income, "severity": "warn",
            "note": f"月收入 {income} 超合理范围 (0-1000万)",
        })

    credit_score = profile.get("credit_score")
    if credit_score is not None and (credit_score < 300 or credit_score > 900):
        anomalies.append({
            "field": "credit_score", "value": credit_score, "severity": "critical",
            "note": f"征信分 {credit_score} 超央行征信中心范围 (300-900)",
        })

    debt_ratio = profile.get("debt_ratio")
    if debt_ratio is not None and (debt_ratio < 0 or debt_ratio > 10):
        anomalies.append({
            "field": "debt_ratio", "value": debt_ratio, "severity": "warn",
            "note": f"负债比 {debt_ratio} 超合理范围 (0-10 · >10 极反常)",
        })

    # 跨字段反常: student + 高额持仓
    employment = profile.get("employment_status")
    income_v = profile.get("income_monthly", 0) or 0
    if employment == "student" and income_v > 50000:
        anomalies.append({
            "field": "employment_status_vs_income", "value": f"student/{income_v}",
            "severity": "warn",
            "note": "学生身份 + 月收入 > 5 万 · 数据反常 · RM 复核",
        })

    # 退休 + 大额负债
    if employment == "retired" and (profile.get("debt_ratio") or 0) > 1.5:
        anomalies.append({
            "field": "employment_status_vs_debt", "value": f"retired/{profile.get('debt_ratio')}",
            "severity": "warn",
            "note": "退休身份 + 负债比 > 150% · 数据反常 · 风险预警",
        })

    return anomalies


def safe_decision_envelope(
    decision: dict[str, Any],
    *,
    missing: Optional[list[str]] = None,
    anomaly: Optional[list[dict]] = None,
) -> dict[str, Any]:
    """包装决策 · 加 missing/anomaly 显式标注 · 不假装跑通.

    Returns:
        包装后的 decision dict · 多字段:
        - data_completeness.missing_fields
        - data_completeness.anomaly_fields
        - data_completeness.has_warnings
        - data_completeness.degraded (是否降级运行)
    """
    missing = missing or []
    anomaly = anomaly or []
    has_critical_anomaly = any(a.get("severity") == "critical" for a in anomaly)
    degraded = bool(missing) or bool(anomaly)

    enveloped = dict(decision)
    enveloped["data_completeness"] = {
        "missing_fields": missing,
        "anomaly_fields": anomaly,
        "has_warnings": degraded,
        "has_critical_anomaly": has_critical_anomaly,
        "degraded": degraded,
        "rm_action_required": (
            "请补录字段或复核数据后再使用 AI 建议" if degraded else None
        ),
    }
    return enveloped


__all__ = [
    "DECISION_CRITICAL_FIELDS",
    "DECISION_NICE_TO_HAVE_FIELDS",
    "check_missing_fields",
    "check_anomaly_fields",
    "safe_decision_envelope",
]
