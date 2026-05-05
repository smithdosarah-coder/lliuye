# -*- coding: utf-8 -*-
"""agent_riskctrl.dsl_field_dict — DSL 字段字典 (BE6.1).

每个 DSL rule field 的 datatype + 单位 + 允许值范围 + 别名 ·
解决三个真痛点 (per docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md BE6 +
风险经理痛 1.4.1+2):

  1. **DSL 写完不知道好不好** — 业务方看不懂"debt_ratio > 0.8" 是 80% 还是 0.8 倍
     · 字段字典给单位 + 业务名 + 允许值范围 · DSL gen 时 LLM prompt 注入
     · backtest 输出业务可读 ("负债率 > 80%")

  2. **单位混乱** — loans.csv 同时有 `loan_amount_wan` (万元) / `rate_pct` (%)
     / `monthly_income_cny` (元) / `debt_ratio` (倍数 0-1) 四种单位
     · 字段字典锁定每字段语义 · 配合 unit_normalizer (BE6.2) 自动归一

  3. **取值越界** — debt_ratio=2.5 (250%) 是数据脏 OR 业务真实 (高杠杆地产) ·
     字段字典给 hard_min/hard_max (合理上下界) + soft_min/soft_max (常见区间) ·
     超 hard 范围 reject DSL · 在 [hard, soft) 之间 warn

依据:
  - CLAUDE.md §3.1 (确定性计算 · 字段语义 Python 锁定 · 不让 LLM 现场猜)
  - CLAUDE.md §3.5 (反 5 原则 · 字段字典 mock 真实形态 · 不预填答案)
  - data/mock/agent2-samples/loans.csv 28 字段真实形态锚定

Public surface:
  - ``FIELD_DICT``: dict[field_name → FieldSpec]
  - ``FieldSpec`` dataclass
  - ``get_field_spec(name) -> FieldSpec | None`` (含别名 lookup)
  - ``validate_value(field, value) -> ValidationResult``
  - ``format_for_business(field, value) -> str`` (业务可读 e.g. "负债率 80%")
"""
from __future__ import annotations

from dataclasses import dataclass, field as _dc_field
from typing import Any


# ---------------------------------------------------------------------------
# Datatype enum (str-ish · 跨 worker 不引 enum dep)
# ---------------------------------------------------------------------------

DTYPE_INT = "int"
DTYPE_FLOAT = "float"
DTYPE_RATIO = "ratio"        # 0-1 倍数 (e.g. debt_ratio=0.74)
DTYPE_PERCENT = "percent"    # 百分比 (e.g. rate_pct=6.61 表 6.61%)
DTYPE_AMOUNT_CNY = "amount_cny"      # 元
DTYPE_AMOUNT_WAN = "amount_wan"      # 万元
DTYPE_AMOUNT_YI = "amount_yi"        # 亿
DTYPE_BPS = "bps"            # 基点 (1bps = 0.01%)
DTYPE_CATEGORICAL = "categorical"
DTYPE_DAYS = "days"
DTYPE_MONTHS = "months"
DTYPE_YEARS = "years"


# ---------------------------------------------------------------------------
# FieldSpec dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldSpec:
    """单字段元数据 · 不可变 (frozen) 防止 runtime 修改."""

    name: str                     # 规范字段名 (与 CSV column 一致)
    business_name: str            # 业务可读名 (中文 · 给业务方看)
    dtype: str                    # 见 DTYPE_* 常量
    unit: str                     # 单位 string (业务可读 · e.g. "%" "元" "万元")
    description: str = ""         # 业务释义
    aliases: tuple[str, ...] = ()  # 同义字段名 (中文/英文别名)

    # 允许值范围 (None = 无约束)
    hard_min: float | None = None  # 物理下界 (越界 reject DSL)
    hard_max: float | None = None
    soft_min: float | None = None  # 业务常见下界 (越界 warn)
    soft_max: float | None = None

    # 类别字段允许值 (categorical 字段必填)
    allowed_values: tuple[str, ...] = ()

    # 业务方向 (越大越好 / 越小越好 / N/A) · LLM prompt + champion/challenger 推荐用
    business_direction: str = "neutral"  # "higher_better" | "lower_better" | "neutral"


# ---------------------------------------------------------------------------
# FIELD_DICT · 28 字段对应 data/mock/agent2-samples/loans.csv
# ---------------------------------------------------------------------------

FIELD_DICT: dict[str, FieldSpec] = {
    # === 申请人画像 ===
    "applicant_age": FieldSpec(
        name="applicant_age", business_name="申请人年龄",
        dtype=DTYPE_YEARS, unit="岁",
        description="授信申请主体年龄 (个人/法人代表)",
        aliases=("age", "申请人年龄", "年龄"),
        hard_min=18, hard_max=100, soft_min=22, soft_max=70,
    ),
    "marriage": FieldSpec(
        name="marriage", business_name="婚姻状况",
        dtype=DTYPE_CATEGORICAL, unit="",
        aliases=("婚姻", "婚姻状况"),
        allowed_values=("未婚", "已婚", "离异", "丧偶"),
    ),
    "education": FieldSpec(
        name="education", business_name="学历",
        dtype=DTYPE_CATEGORICAL, unit="",
        aliases=("学历",),
        allowed_values=("高中及以下", "大专", "本科", "硕士", "博士"),
    ),
    "job_tenure_months": FieldSpec(
        name="job_tenure_months", business_name="在职月数",
        dtype=DTYPE_MONTHS, unit="月",
        aliases=("在职时长", "工龄"),
        hard_min=0, hard_max=600, soft_min=6, soft_max=360,
    ),
    "monthly_income_cny": FieldSpec(
        name="monthly_income_cny", business_name="月收入",
        dtype=DTYPE_AMOUNT_CNY, unit="元",
        aliases=("月收入", "monthly_income"),
        hard_min=0, hard_max=10_000_000, soft_min=2000, soft_max=200_000,
        business_direction="higher_better",
    ),
    # === 企业画像 ===
    "company_age_years": FieldSpec(
        name="company_age_years", business_name="经营年限",
        dtype=DTYPE_YEARS, unit="年",
        aliases=("经营年限", "成立年限", "company_age"),
        hard_min=0, hard_max=200, soft_min=0.5, soft_max=80,
        business_direction="higher_better",
    ),
    "industry_l1": FieldSpec(
        name="industry_l1", business_name="行业大类",
        dtype=DTYPE_CATEGORICAL, unit="",
        aliases=("行业", "industry"),
        allowed_values=(
            "制造业", "建筑业", "批发零售", "交通运输", "信息技术",
            "金融业", "房地产业", "住宿餐饮", "农林牧渔", "其他",
        ),
    ),
    "scale": FieldSpec(
        name="scale", business_name="企业规模",
        dtype=DTYPE_CATEGORICAL, unit="",
        aliases=("规模", "company_scale"),
        allowed_values=("微型", "小型", "中型", "大型"),
    ),
    "region": FieldSpec(
        name="region", business_name="所属地域",
        dtype=DTYPE_CATEGORICAL, unit="",
        aliases=("地域", "区域"),
        allowed_values=("华东", "华南", "华北", "华中", "东北", "西南", "西北"),
    ),
    # === 财务比率 (统一用 ratio 倍数 · 0-1 区间) ===
    "current_ratio": FieldSpec(
        name="current_ratio", business_name="流动比率",
        dtype=DTYPE_FLOAT, unit="倍",
        description="流动资产 / 流动负债 · 短期偿债能力",
        aliases=("流动比率",),
        hard_min=0, hard_max=100, soft_min=0.5, soft_max=10,
        business_direction="higher_better",
    ),
    "debt_ratio": FieldSpec(
        name="debt_ratio", business_name="资产负债率",
        dtype=DTYPE_RATIO, unit="(0-1 倍)",
        description="总负债 / 总资产 · 0.74 表 74%",
        aliases=("负债率", "资产负债率"),
        hard_min=0, hard_max=5, soft_min=0.1, soft_max=0.9,
        business_direction="lower_better",
    ),
    "roe": FieldSpec(
        name="roe", business_name="净资产收益率",
        dtype=DTYPE_PERCENT, unit="%",
        description="ROE = 净利润 / 净资产 · 9.11 表 9.11%",
        aliases=("ROE", "净资产收益率"),
        hard_min=-100, hard_max=200, soft_min=-30, soft_max=80,
        business_direction="higher_better",
    ),
    "revenue_yoy": FieldSpec(
        name="revenue_yoy", business_name="营收同比增速",
        dtype=DTYPE_PERCENT, unit="%",
        aliases=("营收增速", "营收同比"),
        hard_min=-100, hard_max=1000, soft_min=-50, soft_max=300,
        business_direction="higher_better",
    ),
    "net_margin": FieldSpec(
        name="net_margin", business_name="净利率",
        dtype=DTYPE_PERCENT, unit="%",
        aliases=("净利率", "净利润率"),
        hard_min=-100, hard_max=100, soft_min=-30, soft_max=60,
        business_direction="higher_better",
    ),
    # === 贷款属性 ===
    "loan_amount_wan": FieldSpec(
        name="loan_amount_wan", business_name="贷款金额",
        dtype=DTYPE_AMOUNT_WAN, unit="万元",
        description="贷款本金 · 单位万元 · 313.98 表 313.98 万元",
        aliases=("贷款金额", "loan_amount", "金额"),
        hard_min=0, hard_max=1_000_000, soft_min=1, soft_max=100_000,
    ),
    "term_months": FieldSpec(
        name="term_months", business_name="贷款期限",
        dtype=DTYPE_MONTHS, unit="月",
        aliases=("期限", "loan_term"),
        hard_min=1, hard_max=360, soft_min=3, soft_max=120,
    ),
    "rate_pct": FieldSpec(
        name="rate_pct", business_name="利率",
        dtype=DTYPE_PERCENT, unit="%",
        description="年化利率 · 6.61 表 6.61%",
        aliases=("利率", "rate", "年化利率"),
        hard_min=0, hard_max=36, soft_min=2, soft_max=24,
        business_direction="lower_better",
    ),
    "collateral_type": FieldSpec(
        name="collateral_type", business_name="担保方式",
        dtype=DTYPE_CATEGORICAL, unit="",
        aliases=("担保", "担保方式"),
        allowed_values=("信用", "保证", "抵押", "质押", "组合"),
    ),
    "purpose": FieldSpec(
        name="purpose", business_name="贷款用途",
        dtype=DTYPE_CATEGORICAL, unit="",
        aliases=("用途",),
        allowed_values=(
            "经营周转", "原材料采购", "设备购置", "固定资产投资",
            "技术研发", "其他",
        ),
    ),
    # === 征信信号 ===
    "credit_score": FieldSpec(
        name="credit_score", business_name="征信分",
        dtype=DTYPE_INT, unit="分",
        aliases=("征信分", "credit"),
        hard_min=300, hard_max=900, soft_min=500, soft_max=850,
        business_direction="higher_better",
    ),
    "past_overdue_count_1y": FieldSpec(
        name="past_overdue_count_1y", business_name="近1年逾期次数",
        dtype=DTYPE_INT, unit="次",
        aliases=("逾期次数", "近1年逾期"),
        hard_min=0, hard_max=200, soft_min=0, soft_max=12,
        business_direction="lower_better",
    ),
    "current_overdue_count": FieldSpec(
        name="current_overdue_count", business_name="当前逾期笔数",
        dtype=DTYPE_INT, unit="笔",
        aliases=("当前逾期",),
        hard_min=0, hard_max=50, soft_min=0, soft_max=3,
        business_direction="lower_better",
    ),
    "guarantee_times_1y": FieldSpec(
        name="guarantee_times_1y", business_name="近1年对外担保次数",
        dtype=DTYPE_INT, unit="次",
        aliases=("对外担保",),
        hard_min=0, hard_max=200, soft_min=0, soft_max=10,
        business_direction="lower_better",
    ),
    "query_times_3m": FieldSpec(
        name="query_times_3m", business_name="近3月征信查询次数",
        dtype=DTYPE_INT, unit="次",
        aliases=("征信查询次数", "近3月查询"),
        hard_min=0, hard_max=200, soft_min=0, soft_max=15,
        business_direction="lower_better",
    ),
    # === 流水信号 ===
    "bank_balance_stddev_3m": FieldSpec(
        name="bank_balance_stddev_3m", business_name="近3月银行余额标准差",
        dtype=DTYPE_FLOAT, unit="(归一化)",
        description="流水波动度 · 越大越异常",
        aliases=("流水波动",),
        hard_min=0, hard_max=100,
        business_direction="lower_better",
    ),
    "large_debit_count_1m": FieldSpec(
        name="large_debit_count_1m", business_name="近1月大额支出笔数",
        dtype=DTYPE_INT, unit="笔",
        aliases=("大额支出",),
        hard_min=0, hard_max=1000, soft_min=0, soft_max=20,
        business_direction="lower_better",
    ),
    "cross_province_count_1m": FieldSpec(
        name="cross_province_count_1m", business_name="近1月跨省交易笔数",
        dtype=DTYPE_INT, unit="笔",
        aliases=("跨省交易",),
        hard_min=0, hard_max=1000, soft_min=0, soft_max=30,
        business_direction="lower_better",
    ),
    # === 标签 ===
    "days_past_due": FieldSpec(
        name="days_past_due", business_name="逾期天数",
        dtype=DTYPE_DAYS, unit="天",
        description="bad_threshold 默认 30 (>30 视坏账) · backtest label 列",
        aliases=("逾期天数",),
        hard_min=0, hard_max=10000,
    ),
}


# ---------------------------------------------------------------------------
# 别名 lookup index (build once at import)
# ---------------------------------------------------------------------------

_ALIAS_INDEX: dict[str, str] = {}
for _spec in FIELD_DICT.values():
    _ALIAS_INDEX[_spec.name.lower()] = _spec.name
    for _alias in _spec.aliases:
        _ALIAS_INDEX[_alias.lower()] = _spec.name


def get_field_spec(name: str) -> FieldSpec | None:
    """按规范名 OR 别名查 FieldSpec · 大小写不敏感.

    Returns:
        FieldSpec or None (字段未注册)
    """
    if not name:
        return None
    canonical = _ALIAS_INDEX.get(name.strip().lower())
    if canonical is None:
        return None
    return FIELD_DICT.get(canonical)


# ---------------------------------------------------------------------------
# 取值校验
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """单值校验结果."""
    valid: bool                  # hard 范围内 + 类型对齐
    warning: bool = False        # soft 范围外但 hard 内 (业务异常但不阻断)
    field: str = ""
    raw_value: Any = None
    message: str = ""
    details: dict = _dc_field(default_factory=dict)


def validate_value(field_name: str, value: Any) -> ValidationResult:
    """校验某字段的取值是否合理.

    Decision tree:
      字段未注册        → invalid + msg "未注册字段"
      categorical 越界  → invalid
      数值越 hard 界    → invalid (DSL gen 阻断)
      数值越 soft 界    → valid + warning (业务异常 banner)
      其他              → valid

    Args:
        field_name: 字段名 (规范 or 别名)
        value: 取值

    Returns:
        ValidationResult
    """
    spec = get_field_spec(field_name)
    if spec is None:
        return ValidationResult(
            valid=False, field=field_name, raw_value=value,
            message=f"字段 '{field_name}' 未在 FIELD_DICT 注册 · DSL 拒绝",
        )

    # categorical
    if spec.dtype == DTYPE_CATEGORICAL:
        if not spec.allowed_values:
            return ValidationResult(
                valid=True, field=spec.name, raw_value=value,
                message=f"{spec.business_name}: 无 allowed_values 约束 · 透传",
            )
        if str(value).strip() not in spec.allowed_values:
            return ValidationResult(
                valid=False, field=spec.name, raw_value=value,
                message=(
                    f"{spec.business_name} 值 '{value}' 不在允许枚举内: "
                    f"{spec.allowed_values}"
                ),
                details={"allowed_values": list(spec.allowed_values)},
            )
        return ValidationResult(
            valid=True, field=spec.name, raw_value=value,
            message=f"{spec.business_name}: '{value}' OK",
        )

    # numeric
    try:
        num_value = float(value)
    except (TypeError, ValueError):
        return ValidationResult(
            valid=False, field=spec.name, raw_value=value,
            message=f"{spec.business_name} 值 '{value}' 不能转数值",
        )

    if spec.hard_min is not None and num_value < spec.hard_min:
        return ValidationResult(
            valid=False, field=spec.name, raw_value=value,
            message=(
                f"{spec.business_name}={num_value} 低于 hard_min "
                f"{spec.hard_min} · DSL 拒绝"
            ),
            details={"hard_min": spec.hard_min},
        )
    if spec.hard_max is not None and num_value > spec.hard_max:
        return ValidationResult(
            valid=False, field=spec.name, raw_value=value,
            message=(
                f"{spec.business_name}={num_value} 高于 hard_max "
                f"{spec.hard_max} · DSL 拒绝"
            ),
            details={"hard_max": spec.hard_max},
        )

    # soft warn
    warning = False
    msg = f"{spec.business_name}={num_value}{spec.unit} OK"
    if spec.soft_min is not None and num_value < spec.soft_min:
        warning = True
        msg = (
            f"{spec.business_name}={num_value}{spec.unit} 低于业务常见下界 "
            f"{spec.soft_min} · 警告"
        )
    elif spec.soft_max is not None and num_value > spec.soft_max:
        warning = True
        msg = (
            f"{spec.business_name}={num_value}{spec.unit} 高于业务常见上界 "
            f"{spec.soft_max} · 警告"
        )

    return ValidationResult(
        valid=True, warning=warning, field=spec.name, raw_value=value,
        message=msg,
    )


# ---------------------------------------------------------------------------
# 业务可读格式化 (给业务方看的字符串)
# ---------------------------------------------------------------------------


def format_for_business(field_name: str, value: Any) -> str:
    """把 (field, value) 渲染成业务方可读 string.

    Examples:
        format_for_business("debt_ratio", 0.74)         → "资产负债率 74%"
        format_for_business("rate_pct", 6.61)           → "利率 6.61%"
        format_for_business("loan_amount_wan", 313.98)  → "贷款金额 313.98 万元"
        format_for_business("monthly_income_cny", 19031) → "月收入 19,031 元"

    未注册字段 fallback "<field>=<value>" · 不抛错.
    """
    spec = get_field_spec(field_name)
    if spec is None:
        return f"{field_name}={value}"

    if spec.dtype == DTYPE_CATEGORICAL:
        return f"{spec.business_name} {value}"

    try:
        num = float(value)
    except (TypeError, ValueError):
        return f"{spec.business_name} {value}"

    if spec.dtype == DTYPE_RATIO:
        # 0.74 → 74%
        return f"{spec.business_name} {num * 100:.0f}%"
    if spec.dtype == DTYPE_PERCENT:
        return f"{spec.business_name} {num:.2f}%"
    if spec.dtype == DTYPE_AMOUNT_CNY:
        return f"{spec.business_name} {num:,.0f} 元"
    if spec.dtype == DTYPE_AMOUNT_WAN:
        return f"{spec.business_name} {num:,.2f} 万元"
    if spec.dtype == DTYPE_AMOUNT_YI:
        return f"{spec.business_name} {num:,.2f} 亿元"
    if spec.dtype == DTYPE_BPS:
        return f"{spec.business_name} {num:.0f} bps"
    if spec.dtype in (DTYPE_DAYS, DTYPE_MONTHS, DTYPE_YEARS, DTYPE_INT):
        return f"{spec.business_name} {num:,.0f}{spec.unit}"
    return f"{spec.business_name} {num}{spec.unit}"


# ---------------------------------------------------------------------------
# Prompt fragment (供 DSL gen LLM prompt 注入)
# ---------------------------------------------------------------------------


def format_field_dict_for_prompt(fields: list[str] | None = None) -> str:
    """生成给 LLM 的字段说明 markdown · DSL gen prompt 注入用.

    Args:
        fields: 限定输出字段子集 · None = 全部

    Returns:
        markdown · 每字段 1 行 (name | 业务名 | dtype | unit | 范围)
    """
    target = fields or list(FIELD_DICT.keys())
    lines = ["| 字段 | 业务含义 | 类型 | 单位 | 取值范围 |", "|---|---|---|---|---|"]
    for name in target:
        spec = FIELD_DICT.get(name)
        if spec is None:
            continue
        if spec.dtype == DTYPE_CATEGORICAL:
            range_str = " / ".join(spec.allowed_values) if spec.allowed_values else "(任意)"
        else:
            parts = []
            if spec.hard_min is not None or spec.hard_max is not None:
                parts.append(f"硬: [{spec.hard_min}, {spec.hard_max}]")
            if spec.soft_min is not None or spec.soft_max is not None:
                parts.append(f"常见: [{spec.soft_min}, {spec.soft_max}]")
            range_str = " · ".join(parts) if parts else "(无约束)"
        lines.append(
            f"| `{spec.name}` | {spec.business_name} | "
            f"{spec.dtype} | {spec.unit or '-'} | {range_str} |"
        )
    return "\n".join(lines)


__all__ = [
    "ALLOWED_DTYPES",
    "DTYPE_AMOUNT_CNY",
    "DTYPE_AMOUNT_WAN",
    "DTYPE_AMOUNT_YI",
    "DTYPE_BPS",
    "DTYPE_CATEGORICAL",
    "DTYPE_DAYS",
    "DTYPE_FLOAT",
    "DTYPE_INT",
    "DTYPE_MONTHS",
    "DTYPE_PERCENT",
    "DTYPE_RATIO",
    "DTYPE_YEARS",
    "FIELD_DICT",
    "FieldSpec",
    "ValidationResult",
    "format_field_dict_for_prompt",
    "format_for_business",
    "get_field_spec",
    "validate_value",
]


ALLOWED_DTYPES: frozenset[str] = frozenset({
    DTYPE_INT, DTYPE_FLOAT, DTYPE_RATIO, DTYPE_PERCENT,
    DTYPE_AMOUNT_CNY, DTYPE_AMOUNT_WAN, DTYPE_AMOUNT_YI, DTYPE_BPS,
    DTYPE_CATEGORICAL, DTYPE_DAYS, DTYPE_MONTHS, DTYPE_YEARS,
})
