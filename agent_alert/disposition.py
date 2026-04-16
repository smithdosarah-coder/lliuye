# -*- coding: utf-8 -*-
"""Agent4 贷中风险预警 - 处置建议引擎

根据预警结果（AlertReport）生成分级处置方案。
处置模板按风险类别和等级预定义，确保建议可操作。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from .alert_engine import AlertReport, AlertSignal


# ---------------------------------------------------------------------------
# Pydantic 模型
# ---------------------------------------------------------------------------

class DispositionAction(BaseModel):
    """单项处置行动"""
    action_type: str = ""       # 行动类型（如：现场核查、追加担保、上报审批...）
    urgency: str = "持续关注"   # 立即 / 一周内 / 持续关注
    description: str = ""       # 具体行动描述
    responsible: str = ""       # 责任方


class DispositionPlan(BaseModel):
    """处置方案"""
    company_name: str = ""
    actions: list[DispositionAction] = Field(default_factory=list)
    follow_up_date: str = ""    # 下次跟进日期
    notes: str = ""             # 补充说明


# ---------------------------------------------------------------------------
# 处置模板 — 按风险类别和等级预定义
# ---------------------------------------------------------------------------

DISPOSITION_TEMPLATES: dict[str, dict[str, list[dict]]] = {
    "财务恶化": {
        "red": [
            {"action_type": "紧急财务核查", "urgency": "立即",
             "description": "安排现场核查，获取最新财务报表及银行流水，核实财务真实性",
             "responsible": "客户经理"},
            {"action_type": "追加担保评估", "urgency": "立即",
             "description": "评估现有担保物价值，研判是否需要追加担保或压缩授信额度",
             "responsible": "风险管理部"},
            {"action_type": "风险上报", "urgency": "立即",
             "description": "向分行风险管理部提交风险预警报告，启动风险处置预案",
             "responsible": "分行管理层"},
        ],
        "yellow": [
            {"action_type": "财务跟踪", "urgency": "一周内",
             "description": "要求企业提供最新月度财务快报，重点关注现金流和偿债能力变化",
             "responsible": "客户经理"},
            {"action_type": "额度审视", "urgency": "一周内",
             "description": "重新评估授信额度合理性，是否需要调整用信条件",
             "responsible": "风险管理部"},
        ],
    },
    "法律诉讼": {
        "red": [
            {"action_type": "法律风险评估", "urgency": "立即",
             "description": "获取涉诉详情（案号、标的、进展），评估对还款能力的影响",
             "responsible": "法律合规部"},
            {"action_type": "资产保全", "urgency": "立即",
             "description": "评估是否需要申请财产保全或提前收回贷款",
             "responsible": "风险管理部"},
            {"action_type": "风险上报", "urgency": "立即",
             "description": "向分行风险管理部报告涉诉情况，启动应急处置流程",
             "responsible": "分行管理层"},
        ],
        "yellow": [
            {"action_type": "涉诉跟踪", "urgency": "一周内",
             "description": "持续跟踪诉讼进展，评估潜在损失金额",
             "responsible": "法律合规部"},
            {"action_type": "企业沟通", "urgency": "一周内",
             "description": "与企业沟通涉诉情况及应对措施",
             "responsible": "客户经理"},
        ],
    },
    "经营异常": {
        "red": [
            {"action_type": "紧急核查", "urgency": "立即",
             "description": "实地走访企业，核查经营真实状况和实控人变更原因",
             "responsible": "客户经理"},
            {"action_type": "贷后重评", "urgency": "立即",
             "description": "全面重新评估企业信用风险等级",
             "responsible": "风险管理部"},
        ],
        "yellow": [
            {"action_type": "工商变更核查", "urgency": "一周内",
             "description": "核实工商变更原因，评估对企业经营稳定性的影响",
             "responsible": "客户经理"},
        ],
    },
    "行业风险": {
        "red": [
            {"action_type": "行业风险评估", "urgency": "立即",
             "description": "全面评估行业下行对企业的影响程度",
             "responsible": "风险管理部"},
        ],
        "yellow": [
            {"action_type": "行业动态跟踪", "urgency": "持续关注",
             "description": "密切关注行业政策和市场变化，定期更新行业风险评估",
             "responsible": "客户经理"},
        ],
    },
    "关联风险": {
        "red": [
            {"action_type": "关联排查", "urgency": "立即",
             "description": "全面排查关联企业和担保圈风险传导路径",
             "responsible": "风险管理部"},
            {"action_type": "舆情监控升级", "urgency": "立即",
             "description": "将企业纳入舆情重点监控名单，实时跟踪负面信息",
             "responsible": "客户经理"},
        ],
        "yellow": [
            {"action_type": "舆情关注", "urgency": "持续关注",
             "description": "持续关注企业及关联方的舆情变化",
             "responsible": "客户经理"},
        ],
    },
}

# 绿灯通用处置
_GREEN_ACTIONS = [
    DispositionAction(
        action_type="常规监控",
        urgency="持续关注",
        description="维持正常贷后监控频率，按季度进行定期检查",
        responsible="客户经理",
    ),
]


# ---------------------------------------------------------------------------
# 处置方案生成
# ---------------------------------------------------------------------------

def generate_disposition(alert_report: AlertReport) -> DispositionPlan:
    """根据预警报告生成处置方案

    Args:
        alert_report: 预警评估结果

    Returns:
        DispositionPlan 处置方案
    """
    now = datetime.now()
    company = alert_report.company_name
    overall = alert_report.overall_level.lower()

    # 绿灯 — 常规处置
    if overall == "green" or not alert_report.signals:
        return DispositionPlan(
            company_name=company,
            actions=_GREEN_ACTIONS,
            follow_up_date=(now + timedelta(days=90)).strftime("%Y-%m-%d"),
            notes="各项指标正常，维持常规监控，下季度定期复查。",
        )

    # 黄灯/红灯 — 按风险类别匹配处置模板
    actions: list[DispositionAction] = []
    seen_types: set[str] = set()

    for signal in alert_report.signals:
        level = signal.level.lower()
        if level == "green":
            continue
        category = signal.category
        templates = DISPOSITION_TEMPLATES.get(category, {}).get(level, [])
        for tpl in templates:
            # 避免重复添加相同类型的行动
            key = f"{tpl['action_type']}_{tpl['responsible']}"
            if key not in seen_types:
                seen_types.add(key)
                actions.append(DispositionAction(**tpl))

    # 确保至少有基础行动
    if not actions:
        actions.append(DispositionAction(
            action_type="专项核查",
            urgency="一周内" if overall == "yellow" else "立即",
            description=f"针对已触发的预警信号进行专项核查，明确风险程度",
            responsible="客户经理",
        ))

    # 确定跟进日期
    if overall == "red":
        follow_up = (now + timedelta(days=7)).strftime("%Y-%m-%d")
    else:
        follow_up = (now + timedelta(days=30)).strftime("%Y-%m-%d")

    # 生成备注
    red_signals = [s for s in alert_report.signals if s.level == "red"]
    yellow_signals = [s for s in alert_report.signals if s.level == "yellow"]
    notes_parts = []
    if red_signals:
        names = "、".join(s.description[:20] for s in red_signals[:3])
        notes_parts.append(f"红灯项（{len(red_signals)}项）需立即处置：{names}")
    if yellow_signals:
        names = "、".join(s.description[:20] for s in yellow_signals[:3])
        notes_parts.append(f"黄灯项（{len(yellow_signals)}项）需加强跟踪：{names}")
    if overall == "red":
        notes_parts.append("建议上报分行风险管理部门。")

    return DispositionPlan(
        company_name=company,
        actions=actions,
        follow_up_date=follow_up,
        notes="；".join(notes_parts) if notes_parts else "按预警等级执行相应处置措施。",
    )
