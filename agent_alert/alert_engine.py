# -*- coding: utf-8 -*-
"""Agent4 贷中风险预警 - 预警引擎

红/黄/绿三级信号灯系统，基于规则的风险预警识别。
风险类别：财务恶化、法律诉讼、经营异常、行业风险、关联风险。
"""

from __future__ import annotations

import re
from typing import Any, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pydantic 模型
# ---------------------------------------------------------------------------

class AlertSignal(BaseModel):
    """单条预警信号"""
    signal_id: str = ""
    category: str = ""          # 财务恶化/法律诉讼/经营异常/行业风险/关联风险
    level: str = "green"        # red / yellow / green
    description: str = ""
    evidence: str = ""          # 触发该信号的具体数据证据
    trigger_date: str = ""


class AlertReport(BaseModel):
    """预警报告"""
    company_name: str = ""
    overall_level: str = "green"   # red / yellow / green
    signals: list[AlertSignal] = Field(default_factory=list)
    summary: str = ""
    # Phase 1 Task C · trigger_reasons: 结构推断而非关键词黑名单
    # 枚举：external_signal / internal_rule / cross_hit
    # 推断规则在 agent_alert/cross_matcher.py::_infer_trigger_reasons
    # 文档：docs/design/alert-trigger-reasons-taxonomy.md
    trigger_reasons: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 预定义风险指标和阈值
# ---------------------------------------------------------------------------

ALERT_RULES: list[dict] = [
    # --- 财务恶化 ---
    {
        "signal_id": "FIN-001", "category": "财务恶化",
        "name": "营收大幅下降", "check": "_check_revenue_decline",
        "thresholds": {"red": 30, "yellow": 10},
        "desc_tpl": "营业收入同比下降{value:.1f}%",
    },
    {
        "signal_id": "FIN-002", "category": "财务恶化",
        "name": "连续亏损", "check": "_check_continuous_loss",
        "thresholds": {},
        "desc_tpl": "企业存在亏损情况",
    },
    {
        "signal_id": "FIN-003", "category": "财务恶化",
        "name": "资产负债率过高", "check": "_check_debt_ratio",
        "thresholds": {"red": 80, "yellow": 70},
        "desc_tpl": "资产负债率为{value:.1f}%",
    },
    {
        "signal_id": "FIN-004", "category": "财务恶化",
        "name": "流动比率不足", "check": "_check_current_ratio",
        "thresholds": {"red": 1.0, "yellow": 1.5},
        "desc_tpl": "流动比率为{value:.2f}",
    },
    # --- 法律诉讼 ---
    {
        "signal_id": "LAW-001", "category": "法律诉讼",
        "name": "涉诉风险", "check": "_check_litigation",
        "thresholds": {},
        "desc_tpl": "企业存在涉诉记录",
    },
    {
        "signal_id": "LAW-002", "category": "法律诉讼",
        "name": "行政处罚", "check": "_check_admin_penalty",
        "thresholds": {},
        "desc_tpl": "企业受到行政处罚",
    },
    # --- 经营异常 ---
    {
        "signal_id": "BIZ-001", "category": "经营异常",
        "name": "工商信息变更", "check": "_check_business_change",
        "thresholds": {},
        "desc_tpl": "企业近期存在工商变更",
    },
    {
        "signal_id": "BIZ-002", "category": "经营异常",
        "name": "实控人变更", "check": "_check_controller_change",
        "thresholds": {},
        "desc_tpl": "企业实际控制人发生变更",
    },
    # --- 行业风险 ---
    {
        "signal_id": "IND-001", "category": "行业风险",
        "name": "行业风险信号", "check": "_check_industry_risk",
        "thresholds": {},
        "desc_tpl": "行业层面存在风险信号",
    },
    # --- 关联风险 ---
    {
        "signal_id": "REL-001", "category": "关联风险",
        "name": "负面舆情", "check": "_check_negative_news",
        "thresholds": {},
        "desc_tpl": "发现企业负面舆情信息",
    },
    {
        "signal_id": "REL-002", "category": "关联风险",
        "name": "关联企业风险", "check": "_check_affiliate_risk",
        "thresholds": {},
        "desc_tpl": "关联企业存在风险信号",
    },
]


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _safe_float(val: Any) -> Optional[float]:
    """安全地将值转换为浮点数"""
    if val is None:
        return None
    s = str(val).strip().replace(",", "").replace("%", "")
    s = s.replace("万元", "").replace("万", "").replace("亿元", "").replace("亿", "")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _extract_number(text: str, pattern: str) -> Optional[float]:
    """从文本中按正则提取数值"""
    m = re.search(pattern, text or "")
    if m:
        return _safe_float(m.group(1))
    return None


def get_level_emoji(level: str) -> str:
    """red->🔴, yellow->🟡, green->🟢"""
    return {"red": "🔴", "yellow": "🟡", "green": "🟢"}.get(level.lower(), "⚪")


# ---------------------------------------------------------------------------
# 各项检查函数
# ---------------------------------------------------------------------------

def _check_revenue_decline(data: dict, search_text: str = "") -> Optional[AlertSignal]:
    """营收下降检查：>30%红灯，>10%黄灯"""
    text = str(data)
    decline = _extract_number(text, r"营[业收]收入.*?(?:下降|减少|降幅)[：:]*\s*([\d.]+)\s*%?")
    if decline is not None:
        level = "red" if decline > 30 else ("yellow" if decline > 10 else "green")
        if level != "green":
            return AlertSignal(
                signal_id="FIN-001", category="财务恶化", level=level,
                description=f"营业收入同比下降{decline:.1f}%，{'经营状况严重恶化' if level == 'red' else '需关注经营趋势'}",
                evidence=f"营收降幅{decline:.1f}%，{'超过30%红线' if level == 'red' else '超过10%关注线'}",
            )
    return None


def _check_continuous_loss(data: dict, search_text: str = "") -> Optional[AlertSignal]:
    """连续亏损检查"""
    text = str(data)
    if re.search(r"连续.*亏损|持续亏损|净利润为负", text):
        return AlertSignal(
            signal_id="FIN-002", category="财务恶化", level="red",
            description="企业存在连续亏损情况，盈利能力严重恶化",
            evidence="材料中存在连续亏损相关描述",
        )
    facts = data.get("facts", {}) or {}
    profit = facts.get("profit_latest") or ""
    val = _safe_float(profit)
    if val is not None and val < 0:
        return AlertSignal(
            signal_id="FIN-002", category="财务恶化", level="yellow",
            description=f"企业当期净利润为{profit}，存在亏损",
            evidence=f"净利润数据：{profit}",
        )
    return None


def _check_debt_ratio(data: dict, search_text: str = "") -> Optional[AlertSignal]:
    """资产负债率检查：>80%红灯，>70%黄灯"""
    text = str(data)
    ratio = _extract_number(text, r"资产负债率[：:]*\s*([\d.]+)\s*%?")
    if ratio is None:
        facts = data.get("facts", {}) or {}
        fs = facts.get("financial_summary") or {}
        ratio = _safe_float(fs.get("debt_ratio") or fs.get("资产负债率"))
    if ratio is not None:
        if ratio > 80:
            return AlertSignal(
                signal_id="FIN-003", category="财务恶化", level="red",
                description=f"资产负债率{ratio:.1f}%，超过80%警戒线，偿债压力极大",
                evidence=f"资产负债率={ratio:.1f}%，阈值：红灯>80%",
            )
        elif ratio > 70:
            return AlertSignal(
                signal_id="FIN-003", category="财务恶化", level="yellow",
                description=f"资产负债率{ratio:.1f}%，接近80%警戒线，需关注偿债能力",
                evidence=f"资产负债率={ratio:.1f}%，阈值：黄灯>70%",
            )
    return None


def _check_current_ratio(data: dict, search_text: str = "") -> Optional[AlertSignal]:
    """流动比率检查：<1红灯，<1.5黄灯"""
    text = str(data)
    ratio = _extract_number(text, r"流动比率[：:]*\s*([\d.]+)")
    if ratio is None:
        facts = data.get("facts", {}) or {}
        fs = facts.get("financial_summary") or {}
        ratio = _safe_float(fs.get("current_ratio") or fs.get("流动比率"))
    if ratio is not None:
        if ratio < 1.0:
            return AlertSignal(
                signal_id="FIN-004", category="财务恶化", level="red",
                description=f"流动比率{ratio:.2f}，低于1.0，短期偿债能力严重不足",
                evidence=f"流动比率={ratio:.2f}，阈值：红灯<1.0",
            )
        elif ratio < 1.5:
            return AlertSignal(
                signal_id="FIN-004", category="财务恶化", level="yellow",
                description=f"流动比率{ratio:.2f}，低于1.5，短期偿债能力偏弱",
                evidence=f"流动比率={ratio:.2f}，阈值：黄灯<1.5",
            )
    return None


def _check_litigation(data: dict, search_text: str = "") -> Optional[AlertSignal]:
    """涉诉信息检查"""
    facts = data.get("facts", {}) or {}
    risk_signals = str(facts.get("risk_signals", ""))
    negative_info = str(facts.get("negative_info", ""))
    combined = risk_signals + " " + negative_info + " " + search_text
    if re.search(r"涉诉|被告|诉讼|仲裁|执行|失信被执行", combined):
        is_severe = bool(re.search(r"失信被执行|重大诉讼|标的.*?[千万亿]", combined))
        level = "red" if is_severe else "yellow"
        snippet = combined.strip()[:120]
        return AlertSignal(
            signal_id="LAW-001", category="法律诉讼", level=level,
            description=f"企业存在{'重大' if is_severe else ''}涉诉记录，{'需立即关注' if is_severe else '需持续跟踪'}",
            evidence=f"涉诉关键信息：{snippet}",
        )
    return None


def _check_admin_penalty(data: dict, search_text: str = "") -> Optional[AlertSignal]:
    """行政处罚检查"""
    combined = str(data) + " " + search_text
    if re.search(r"行政处罚|罚款|责令整改|警告处分|监管处罚", combined):
        is_severe = bool(re.search(r"罚款.*?[百千万]|吊销|暂停|取消资质", combined))
        level = "red" if is_severe else "yellow"
        return AlertSignal(
            signal_id="LAW-002", category="法律诉讼", level=level,
            description=f"企业受到行政处罚，{'处罚力度较大' if is_severe else '需关注合规情况'}",
            evidence=f"在材料或舆情中发现行政处罚相关信息",
        )
    return None


def _check_business_change(data: dict, search_text: str = "") -> Optional[AlertSignal]:
    """工商信息变更检查"""
    text = str(data) + " " + search_text
    if re.search(r"工商变更|经营范围变更|注册地址变更|法人变更", text):
        return AlertSignal(
            signal_id="BIZ-001", category="经营异常", level="yellow",
            description="企业近期存在工商变更记录，需关注变更原因及影响",
            evidence="材料中发现工商变更相关信息",
        )
    return None


def _check_controller_change(data: dict, search_text: str = "") -> Optional[AlertSignal]:
    """实控人变更检查"""
    text = str(data) + " " + search_text
    if re.search(r"实控人变更|实际控制人变更|股权转让|控股权转移", text):
        return AlertSignal(
            signal_id="BIZ-002", category="经营异常", level="red",
            description="企业实际控制人发生变更，需重新评估企业经营稳定性",
            evidence="材料中发现实控人/股权变更相关信息",
        )
    return None


def _check_industry_risk(data: dict, search_text: str = "") -> Optional[AlertSignal]:
    """行业风险检查"""
    combined = str(data.get("facts", {}).get("industry", "")) + " " + search_text
    risk_kw = ["行业下行", "产能过剩", "政策收紧", "行业整顿", "行业监管",
               "市场萎缩", "行业风险", "景气度下降"]
    found = [kw for kw in risk_kw if kw in combined]
    if found:
        return AlertSignal(
            signal_id="IND-001", category="行业风险", level="yellow",
            description=f"行业层面存在风险信号：{'、'.join(found[:3])}",
            evidence=f"发现行业风险关键词：{'、'.join(found)}",
        )
    return None


def _check_negative_news(data: dict, search_text: str = "") -> Optional[AlertSignal]:
    """负面舆情检查"""
    combined = search_text + " " + str(data.get("facts", {}).get("negative_info", ""))
    if not combined.strip():
        return None
    neg_kw = ["违规", "处罚", "罚款", "暴雷", "跑路", "欠薪", "裁员", "倒闭",
              "违法", "立案", "调查", "监管", "警告", "整改"]
    found = [kw for kw in neg_kw if kw in combined]
    if found:
        is_severe = any(k in combined for k in ["暴雷", "跑路", "立案", "倒闭"])
        level = "red" if is_severe else "yellow"
        return AlertSignal(
            signal_id="REL-001", category="关联风险", level=level,
            description=f"发现负面舆情：{'、'.join(found[:5])}，{'事态严重需立即关注' if is_severe else '需持续跟踪'}",
            evidence=f"舆情关键词命中：{'、'.join(found)}",
        )
    return None


def _check_affiliate_risk(data: dict, search_text: str = "") -> Optional[AlertSignal]:
    """关联企业风险检查"""
    combined = str(data) + " " + search_text
    if re.search(r"关联企业.*?(?:风险|出险|违约|诉讼)|担保圈.*?风险|股权质押.*?(?:冻结|拍卖)", combined):
        return AlertSignal(
            signal_id="REL-002", category="关联风险", level="yellow",
            description="关联企业或担保圈存在风险信号，需评估风险传导可能性",
            evidence="材料或舆情中发现关联风险信息",
        )
    return None


# 检查函数映射表
_CHECK_FUNCS = {
    "_check_revenue_decline": _check_revenue_decline,
    "_check_continuous_loss": _check_continuous_loss,
    "_check_debt_ratio": _check_debt_ratio,
    "_check_current_ratio": _check_current_ratio,
    "_check_litigation": _check_litigation,
    "_check_admin_penalty": _check_admin_penalty,
    "_check_business_change": _check_business_change,
    "_check_controller_change": _check_controller_change,
    "_check_industry_risk": _check_industry_risk,
    "_check_negative_news": _check_negative_news,
    "_check_affiliate_risk": _check_affiliate_risk,
}


# ---------------------------------------------------------------------------
# 核心引擎
# ---------------------------------------------------------------------------

def evaluate_alerts(data: dict, profile=None, search_text: str = "") -> AlertReport:
    """基于数据评估预警等级，返回 AlertReport

    Args:
        data: 企业数据（kb 格式或原始数据字典）
        profile: 可选的 EnterpriseProfile
        search_text: 舆情搜索结果文本
    """
    company_name = ""
    if profile and hasattr(profile, "company_name"):
        company_name = profile.company_name
    if not company_name:
        facts = data.get("facts", {}) or {}
        company_name = facts.get("company_name", "未知企业")

    triggered: list[AlertSignal] = []
    for rule in ALERT_RULES:
        func_name = rule["check"]
        func = _CHECK_FUNCS.get(func_name)
        if func is None:
            continue
        try:
            result = func(data=data, search_text=search_text)
            if result is not None:
                triggered.append(result)
        except (RuntimeError, ValueError, TypeError, KeyError, AttributeError, IndexError):
            continue

    # 聚合信号：any红->红, any黄->黄, else绿
    levels = {s.level.lower() for s in triggered}
    if "red" in levels:
        overall = "red"
    elif "yellow" in levels:
        overall = "yellow"
    else:
        overall = "green"

    # 生成摘要
    if not triggered:
        summary = f"{company_name}各项监控指标正常，未触发预警规则，建议维持常规监控。"
    else:
        red_count = sum(1 for s in triggered if s.level == "red")
        yellow_count = sum(1 for s in triggered if s.level == "yellow")
        categories = list({s.category for s in triggered})
        summary = (
            f"{company_name}触发{len(triggered)}项预警信号"
            f"（红灯{red_count}项、黄灯{yellow_count}项），"
            f"涉及{'、'.join(categories)}，"
            f"综合预警等级为{get_level_emoji(overall)} {overall.upper()}。"
        )

    return AlertReport(
        company_name=company_name,
        overall_level=overall,
        signals=triggered,
        summary=summary,
    )
