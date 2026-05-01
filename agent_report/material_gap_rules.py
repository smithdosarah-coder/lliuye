# -*- coding: utf-8 -*-
"""agent_report.material_gap_rules — Sprint 1 BE3 静态规则配置.

JSON-serializable dict 配置 · 不含逻辑 · material_gap.build_graph 消费.

锁定来源:
  - material id 取自 material_kb.py 14 KB 维度命名 (basic_info / shareholders /
    controller / business / upstream_top5 / downstream_top5 / affiliates /
    financing / credit_history / risk_info / r_and_d / orders / bank_flows /
    tax_data) · 不漂移
  - section id 取自 v16_runner._CHAPTER_HEADINGS 4 章锚点
    (chapter_1_background / chapter_2_operation / chapter_3_finance /
    chapter_4_conclusion) · 与 mock_v16_stream done.sections 同 shape
  - scoring_dimension id 取自 agent_credit/scoring_model_corporate.py:79-84
    DEFAULT_WEIGHTS (Sprint 1 = current code IDs · 不 wait BE2 future ·
    per Codex 插入点 1 V2 战术修 Q1):
      financial (35%) / industry (15%) / operational (25%) / guarantee (25%)
    BE2 ratify 后 fix-forward 拆分 (e.g. operational → operation_stability +
    management_quality)

公式:
  impact_magnitude = (affected_fields_count / SECTION_FIELD_COUNT[section]) *
                     SECTION_TO_DIM_WEIGHTS[section][dim] * 100
  四舍五入 int 0-100 (公式 placeholder · Phase C / worker-B7 baseline 校准)

详 docs/contracts/agent-report-material-gap.md v1.0 V2 §2 + §3.
"""
from __future__ import annotations

# ============================================================================
# Material → Section 映射 (provides edge)
# 每 material 影响哪些 section 的哪些字段 · severity blocking/advisory
# ============================================================================

# shape: {material_id: [(section_id, severity, [affected_fields])]}
MATERIAL_TO_SECTION_RULES: dict[str, list[tuple[str, str, list[str]]]] = {
    "basic_info": [
        ("chapter_1_background", "blocking",
         ["company_name", "uscc", "registered_capital", "founded", "legal_rep", "industry"]),
    ],
    "shareholders": [
        ("chapter_1_background", "blocking",
         ["shareholder_structure", "ownership_distribution"]),
    ],
    "controller": [
        ("chapter_1_background", "advisory",
         ["actual_controller", "controller_credit_history"]),
    ],
    "r_and_d": [
        ("chapter_1_background", "advisory",
         ["patents", "rd_investment", "innovation_capability"]),
    ],
    "business": [
        ("chapter_2_operation", "blocking",
         ["main_business", "revenue_breakdown_by_product", "competitive_advantage"]),
    ],
    "upstream_top5": [
        ("chapter_2_operation", "blocking",
         ["supplier_concentration", "supply_chain_stability"]),
    ],
    "downstream_top5": [
        ("chapter_2_operation", "blocking",
         ["customer_concentration", "buyer_diversity"]),
    ],
    "orders": [
        ("chapter_2_operation", "advisory",
         ["pipeline_orders", "order_book_visibility"]),
    ],
    "affiliates": [
        ("chapter_2_operation", "advisory",
         ["related_party_tx", "group_structure"]),
    ],
    "financing": [
        ("chapter_3_finance", "blocking",
         ["debt_structure", "existing_credit", "refinancing_risk"]),
    ],
    "bank_flows": [
        ("chapter_3_finance", "blocking",
         ["cashflow_quality", "monthly_inflow_volatility"]),
    ],
    "tax_data": [
        ("chapter_3_finance", "advisory",
         ["tax_compliance", "tax_revenue_consistency"]),
    ],
    "credit_history": [
        ("chapter_3_finance", "advisory",
         ["historical_credit_performance", "overdue_records"]),
    ],
    "risk_info": [
        ("chapter_4_conclusion", "advisory",
         ["litigation_records", "esg_signals", "regulatory_alerts"]),
    ],
}


# ============================================================================
# Section → ScoringDimension 权重 (affects edge)
# 每 section 对每 scoring_dim 的总贡献权重 (0.0-1.0)
# Sprint 1 = current code IDs (per Codex V2 Q1) · 4 dim:
#   financial (35%) / industry (15%) / operational (25%) / guarantee (25%)
# ============================================================================

SECTION_TO_DIM_WEIGHTS: dict[str, dict[str, float]] = {
    "chapter_1_background": {
        "operational": 0.4,   # 公司基本面 + 股东 + 实控人 → 经营评分主要素
        "industry":    0.3,   # 行业属性 + 注册资本规模
    },
    "chapter_2_operation": {
        "operational": 0.6,   # 经营情况是 operational 主战场
        "industry":    0.4,   # 行业景气度直接体现
    },
    "chapter_3_finance": {
        "financial":   0.8,   # 财务分析是 financial 主战场
        "guarantee":   0.5,   # 流水反映还款能力 + 现金流覆盖担保
    },
    "chapter_4_conclusion": {
        # Agent3 决策回写区 · 不直接产 magnitude · 由 Agent3 综合判断
        # 留 dict 不为空 · 防 build_graph 边查询 KeyError
    },
}


# ============================================================================
# Section 总字段数 (用于 impact_magnitude 计算分母)
# ============================================================================

SECTION_FIELD_COUNT: dict[str, int] = {
    "chapter_1_background": 12,
    "chapter_2_operation": 15,
    "chapter_3_finance": 18,
    "chapter_4_conclusion": 0,  # Agent3 区 · 不参与 magnitude 计算
}


# ============================================================================
# 中文显示名 (前端 PreviewPanel / MaterialPanel hydrate 用)
# ============================================================================

MATERIAL_NAMES: dict[str, str] = {
    "basic_info":      "企业基本信息",
    "shareholders":    "股东结构清单",
    "controller":      "实际控制人信息",
    "r_and_d":         "研发投入与专利",
    "business":        "主营业务说明",
    "upstream_top5":   "前五大供应商",
    "downstream_top5": "前五大客户",
    "orders":          "在手订单清单",
    "affiliates":      "关联企业清单",
    "financing":       "现有融资明细",
    "bank_flows":      "银行流水（12 个月）",
    "tax_data":        "纳税申报表",
    "credit_history":  "历史授信记录",
    "risk_info":       "诉讼与征信记录",
}

SECTION_NAMES: dict[str, str] = {
    "chapter_1_background": "一、企业背景",
    "chapter_2_operation":  "二、经营情况",
    "chapter_3_finance":    "三、财务分析",
    "chapter_4_conclusion": "四、审批意见",
}

SCORING_DIM_NAMES: dict[str, str] = {
    "financial":   "财务情况",
    "industry":    "行业情况",
    "operational": "经营情况",
    "guarantee":   "担保情况",
}


# ============================================================================
# Schema version (graph_version 与 contract doc align)
# ============================================================================

GRAPH_VERSION = "1.0"


# ============================================================================
# Helpers (查询封装 · build_graph 调)
# ============================================================================

def get_material_name(material_id: str) -> str:
    """material_id → 中文显示名 · 未知 id 返 id 本身 (不抛)."""
    return MATERIAL_NAMES.get(material_id, material_id)


def get_section_name(section_id: str) -> str:
    return SECTION_NAMES.get(section_id, section_id)


def get_scoring_dim_name(dim_id: str) -> str:
    return SCORING_DIM_NAMES.get(dim_id, dim_id)


def get_section_field_count(section_id: str) -> int:
    """未知 section 返 0 · 让 magnitude 计算自然降为 0 (不参与)."""
    return SECTION_FIELD_COUNT.get(section_id, 0)


def get_section_dim_weight(section_id: str, dim_id: str) -> float:
    """未知 section/dim 返 0.0 · magnitude 自然降为 0."""
    return SECTION_TO_DIM_WEIGHTS.get(section_id, {}).get(dim_id, 0.0)


def get_material_provides(material_id: str) -> list[tuple[str, str, list[str]]]:
    """material_id → list of (section_id, severity, affected_fields)."""
    return MATERIAL_TO_SECTION_RULES.get(material_id, [])
