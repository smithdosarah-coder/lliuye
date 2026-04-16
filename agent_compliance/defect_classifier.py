# -*- coding: utf-8 -*-
"""Agent5 合规巡检 - 缺陷分级

对不合规项进行严重度分级，并生成整改计划。
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .compliance_checker import CheckItem


class Defect(BaseModel):
    """单条缺陷"""
    defect_id: str = Field(default="", description="缺陷编号，如 DEF-001")
    description: str = Field(default="", description="缺陷描述")
    severity: str = Field(default="minor", description="严重度: critical/major/minor")
    category: str = Field(default="", description="缺陷类别")
    recommendation: str = Field(default="", description="整改建议")
    deadline: str = Field(default="", description="建议整改期限")


# 严重度判定标准
SEVERITY_CRITERIA = {
    "critical": "违反监管强制要求（mandatory），可能导致监管处罚、行政罚款或业务资质风险",
    "major": "违反监管推荐做法（recommended），影响业务合规性和内控有效性",
    "minor": "流程优化建议（optional或partial），不影响基本合规但存在改进空间",
}

# 整改期限参考
DEADLINE_MAP = {
    "critical": "立即整改，15个工作日内完成",
    "major": "30个工作日内完成整改",
    "minor": "下一季度内完成优化",
}


def classify_defects(failed_items: list[CheckItem]) -> list[Defect]:
    """对不合规项进行缺陷分级。

    分级逻辑：
    - fail 状态项 → 根据要求描述中是否包含强制性关键词判定 critical/major
    - partial 状态项 → minor

    Args:
        failed_items: status 为 fail 或 partial 的 CheckItem 列表

    Returns:
        list[Defect]: 按严重度排序的缺陷列表（critical > major > minor）
    """
    defects: list[Defect] = []
    severity_order = {"critical": 0, "major": 1, "minor": 2}

    for i, item in enumerate(failed_items):
        defect_id = f"DEF-{i + 1:03d}"

        if item.status == "partial":
            severity = "minor"
        elif _is_mandatory_violation(item):
            severity = "critical"
        else:
            severity = "major"

        defects.append(Defect(
            defect_id=defect_id,
            description=item.gap_description or f"要求 {item.req_id} 未达标: {item.requirement}",
            severity=severity,
            category=_infer_category(item),
            recommendation=_generate_recommendation(item, severity),
            deadline=DEADLINE_MAP.get(severity, "60个工作日内完成"),
        ))

    # 按严重度排序
    defects.sort(key=lambda d: severity_order.get(d.severity, 99))
    return defects


def _is_mandatory_violation(item: CheckItem) -> bool:
    """判断是否违反强制性要求。"""
    text = (item.requirement + " " + item.gap_description).lower()
    mandatory_keywords = [
        "必须", "应当", "强制", "mandatory", "不得", "禁止",
        "处罚", "罚款", "违规", "监管要求", "法律规定",
    ]
    return any(kw in text for kw in mandatory_keywords)


def _infer_category(item: CheckItem) -> str:
    """从检查项内容推断缺陷类别。"""
    text = item.requirement + " " + item.gap_description
    category_keywords = {
        "信息披露": ["披露", "公示", "报告", "报送"],
        "风险管理": ["风险", "风控", "限额", "准备金"],
        "客户保护": ["客户", "消费者", "权益", "投诉", "隐私"],
        "反洗钱": ["反洗钱", "可疑交易", "身份识别", "KYC"],
        "贷后管理": ["贷后", "催收", "逾期", "不良"],
        "资本充足": ["资本", "充足率", "拨备"],
        "内控合规": ["内控", "审计", "合规", "制度"],
    }
    for cat, keywords in category_keywords.items():
        if any(kw in text for kw in keywords):
            return cat
    return "其他"


def _generate_recommendation(item: CheckItem, severity: str) -> str:
    """为缺陷生成基础整改建议。"""
    if severity == "critical":
        return f"立即启动整改：针对「{item.requirement[:30]}」建立专项整改方案，明确责任人和时间节点，整改完成后报合规部门复核。"
    elif severity == "major":
        return f"制定整改计划：完善「{item.requirement[:30]}」相关的制度流程和操作规范，安排培训确保执行到位。"
    else:
        return f"持续优化：改进「{item.requirement[:30]}」相关操作流程，提升合规管理精细化水平。"


def generate_improvement_plan(defects: list[Defect]) -> str:
    """基于缺陷列表生成整改计划摘要。

    Args:
        defects: 已分级的缺陷列表

    Returns:
        str: Markdown格式的整改计划
    """
    if not defects:
        return "未发现合规缺陷，无需整改。"

    critical = [d for d in defects if d.severity == "critical"]
    major = [d for d in defects if d.severity == "major"]
    minor = [d for d in defects if d.severity == "minor"]

    SEVERITY_ICON = {"critical": "\U0001f534", "major": "\U0001f7e0", "minor": "\U0001f7e1"}
    SEVERITY_CN = {"critical": "严重", "major": "重要", "minor": "一般"}

    lines = [
        "## 整改计划",
        "",
        f"共发现 **{len(defects)}** 项缺陷："
        f"严重 {len(critical)} 项、重要 {len(major)} 项、一般 {len(minor)} 项",
        "",
    ]

    # 分阶段整改
    if critical:
        lines.append("### 第一阶段：紧急整改（15个工作日内）")
        lines.append("")
        for d in critical:
            lines.append(f"- {SEVERITY_ICON['critical']} **{d.defect_id}** {d.description[:60]}")
            lines.append(f"  - 建议: {d.recommendation}")
        lines.append("")

    if major:
        lines.append("### 第二阶段：重点整改（30个工作日内）")
        lines.append("")
        for d in major:
            lines.append(f"- {SEVERITY_ICON['major']} **{d.defect_id}** {d.description[:60]}")
            lines.append(f"  - 建议: {d.recommendation}")
        lines.append("")

    if minor:
        lines.append("### 第三阶段：持续优化（下一季度内）")
        lines.append("")
        for d in minor:
            lines.append(f"- {SEVERITY_ICON['minor']} **{d.defect_id}** {d.description[:60]}")
            lines.append(f"  - 建议: {d.recommendation}")
        lines.append("")

    return "\n".join(lines)
