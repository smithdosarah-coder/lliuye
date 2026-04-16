"""
IndustryBenchmark — 行业基准区间数据层

向财务分析段注入"同行业典型区间"作为参照系,让 LLM 做归因对比有依据。
数据来源:公开行业研报、国家统计局行业数据、上市公司年报中位数。

当前覆盖:
  I65 软件和信息技术服务业(中锐网络所在行业)
扩展方式:添加新的 IndustryKey 即可。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MetricRange:
    """一个指标的行业区间(低位-高位),以及超出区间的典型归因方向。"""
    low: float
    high: float
    unit: str  # "%" 或 "天" 或 "倍"
    direction_high_cause: str = ""  # 高于区间的常见原因
    direction_low_cause: str = ""   # 低于区间的常见原因


@dataclass
class IndustryBenchmark:
    code: str       # 国标行业代码(如 I65)
    name: str       # 行业名称
    metrics: dict[str, MetricRange] = field(default_factory=dict)

    def format_for_prompt(self) -> str:
        """格式化为 prompt 参照系。"""
        lines = []
        lines.append(f"【行业基准参照({self.code} {self.name}典型区间)】")
        lines.append("(来源:公开研报/上市公司年报中位数;用于对比归因,不是硬指标)")
        for name, r in self.metrics.items():
            line = f"  {name}: {r.low}~{r.high}{r.unit}"
            if r.direction_high_cause:
                line += f"  ├高于上限常因:{r.direction_high_cause}"
            if r.direction_low_cause:
                line += f"  └低于下限常因:{r.direction_low_cause}"
            lines.append(line)
        lines.append("")
        lines.append("归因模板(LLM 撰写财务段时使用):")
        lines.append("  若指标超出行业区间,须在财务分析中明确标注")
        lines.append("  例:『应收周转天数271天,显著高于软件信息业90-180天典型区间,主要由于项目验收周期较长+政府客户回款账期较长』")
        return "\n".join(lines)


# ------------------------------------------------------------------
# 数据定义
# ------------------------------------------------------------------

SOFTWARE_IT_I65 = IndustryBenchmark(
    code="I65",
    name="软件和信息技术服务业",
    metrics={
        "应收账款周转天数": MetricRange(
            low=90, high=180, unit="天",
            direction_high_cause="项目制验收周期长/政府及大B客户账期长/在手订单回款滞后",
            direction_low_cause="以个人/小B客户为主且预收款模式",
        ),
        "存货周转天数": MetricRange(
            low=30, high=90, unit="天",
            direction_high_cause="定制化项目未验收沉淀为存货/硬件集成类业务备货周期长",
            direction_low_cause="纯SaaS/订阅业务几乎无库存",
        ),
        "毛利率": MetricRange(
            low=30, high=50, unit="%",
            direction_high_cause="自研软件/SaaS为主,边际成本低",
            direction_low_cause="硬件集成占比高/低价竞标/人力成本刚性上升",
        ),
        "净利率": MetricRange(
            low=5, high=15, unit="%",
            direction_high_cause="规模效应显著+研发资本化比例高",
            direction_low_cause="研发投入占比高/费用率上升/坏账计提大",
        ),
        "资产负债率": MetricRange(
            low=30, high=55, unit="%",
            direction_high_cause="项目垫资需要+银行授信使用率高",
            direction_low_cause="实收资本雄厚或上市募资到位",
        ),
        "流动比率": MetricRange(
            low=1.5, high=2.5, unit="倍",
            direction_low_cause="应收应付期限错配/短期借款集中",
        ),
        "速动比率": MetricRange(
            low=1.2, high=2.0, unit="倍",
            direction_low_cause="存货占流动资产比重偏高",
        ),
    },
)


# ------------------------------------------------------------------
# 对外 API
# ------------------------------------------------------------------

def get_benchmark(industry_hint: str = "软件") -> Optional[IndustryBenchmark]:
    """根据行业关键词返回对应基准。目前只覆盖 I65。"""
    if not industry_hint:
        return SOFTWARE_IT_I65
    hint = industry_hint.lower()
    it_kws = ("软件", "信息", "科技", "网络", "it", "computer", "tech", "digital", "智慧", "数字")
    if any(k in hint.lower() or k in hint for k in it_kws):
        return SOFTWARE_IT_I65
    return None


if __name__ == "__main__":
    bm = get_benchmark("软件信息")
    print(bm.format_for_prompt())
