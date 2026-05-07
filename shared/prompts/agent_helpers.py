"""Per-agent SSOT prompt builder helpers

per Phase C grounded report Production Blocker #1 Step 3 (PM 5/7 拍板):

设计:
- 6 Agent 调统一 helper 注入 8 段 SSOT
- 每 helper 透传到 contract.build_system_prompt(agent_id=...)
- 向下兼容: 6 Agent 现有 hardcode SYSTEM_* 常量保留 · 新 LLM call site 用此 helper
- 命名 _ssot_prompt 避免 name conflict (agent_alert 已有 build_alert_system_prompt)

使用 (e.g. agent_credit/decision_engine.py):
    from shared.prompts.agent_helpers import build_credit_ssot_prompt

    system_prompt = build_credit_ssot_prompt(
        task_type="decision_review",
        schema_hint='{"decision": "通过/拒绝/补件", "amount": ...}',
    )
    # → 含 [safety][evidence-first 含 freshness][output-schema] 3 段实装

Migration path:
- Sprint 6 LLM 真接入时 · 6 Agent LLM caller 改用此 helper
- 老 hardcode SYSTEM_* 常量逐个 deprecate
"""
from __future__ import annotations

from shared.prompts.contract import build_system_prompt as _build


def build_channel_ssot_prompt(**kwargs) -> str:
    """Agent1 channel · 客户洞察 / look-alike / 个人画像."""
    return _build("channel", **kwargs)


def build_credit_ssot_prompt(**kwargs) -> str:
    """Agent3 credit · 授信决策 / 红线 / 案例对比."""
    return _build("credit", **kwargs)


def build_alert_ssot_prompt(**kwargs) -> str:
    """Agent4 alert · 贷后预警 / 红/黄/绿信号灯."""
    return _build("alert", **kwargs)


def build_compliance_ssot_prompt(**kwargs) -> str:
    """Agent5 compliance · 合规扫描 / 政策矩阵 / 违规判定."""
    return _build("compliance", **kwargs)


def build_report_ssot_prompt(**kwargs) -> str:
    """Agent6 report · 客户洞察报告 / v16 主管线."""
    return _build("report", **kwargs)


def build_riskctrl_ssot_prompt(**kwargs) -> str:
    """Agent2 riskctrl · DSL 生成 / 回测 / 双轨指标."""
    return _build("riskctrl", **kwargs)


# 6 helper 集中导出 · 单一 import
BUILDERS = {
    "channel": build_channel_ssot_prompt,
    "credit": build_credit_ssot_prompt,
    "alert": build_alert_ssot_prompt,
    "compliance": build_compliance_ssot_prompt,
    "report": build_report_ssot_prompt,
    "riskctrl": build_riskctrl_ssot_prompt,
}


def build_ssot_prompt(agent_id: str, **kwargs) -> str:
    """通用入口 · agent_id 6 选 1 · 透传 kwargs 到 contract.build_system_prompt."""
    if agent_id not in BUILDERS:
        raise ValueError(
            f"unknown agent_id: {agent_id!r} · expected one of {list(BUILDERS)}"
        )
    return BUILDERS[agent_id](**kwargs)


__all__ = [
    "BUILDERS",
    "build_alert_ssot_prompt",
    "build_channel_ssot_prompt",
    "build_compliance_ssot_prompt",
    "build_credit_ssot_prompt",
    "build_report_ssot_prompt",
    "build_riskctrl_ssot_prompt",
    "build_ssot_prompt",
]
