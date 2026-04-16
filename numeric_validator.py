# -*- coding: utf-8 -*-
"""
NumericValidator — 数字白名单兜底守卫

治本思路:
  LLM 在长段落里重输数字时必然出错(10010→1010、%和pct混用、存货/应收搞错)。
  靠 prompt 要求"不得幻觉"无法根治。
  这里从 FinancialIndicators + truth_data 构建确定性白名单,
  对生成文本做正则抽取+上下文语义匹配,发现不一致时返回可定位的错误清单,
  上层可据此做小范围重写(只改错句,不整段重写)。

设计要点:
  1. 覆盖银行最在意的 20 个核心数字;不追求全量校验。
  2. 用上下文窗口(左 22 字 + 右 4 字)判断语义 tag 和年份/时点。
  3. 数字容差 0.5% 以内视为一致(允许"10010.0 vs 10010"),
     10 倍级差异一定抓出来。
  4. 输出 {context, tag, year, actual, expected, unit} 清单,
     上层可据此生成修正指令。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


# ------------------------------------------------------------
# 语义 tag 别名表(中文口径 → tag)
# ------------------------------------------------------------
# 每个 tag 给多个别名,按窗口里出现的关键词定位。
# 按"关键度"排序,长的优先匹配以避免 "净利润" 混入 "利润"
TAG_ALIASES: dict[str, list[str]] = {
    # 规模
    "revenue":             ["营业收入", "主营业务收入", "营业总收入", "营收"],
    "net_profit":          ["净利润"],
    "total_assets":        ["总资产", "资产总计", "资产合计"],
    "total_liabilities":   ["总负债", "负债合计", "负债总额"],
    "total_equity":        ["所有者权益", "股东权益", "净资产"],
    # 盈利
    "gross_margin":        ["毛利率"],
    "net_margin":          ["净利率"],
    "operating_margin":    ["营业利润率"],
    # 偿债
    "debt_to_asset_ratio": ["资产负债率"],
    "current_ratio":       ["流动比率"],
    "quick_ratio":         ["速动比率"],
    # 营运
    "ar_turnover_days":    ["应收账款周转天数", "应收周转天数"],
    "inv_turnover_days":   ["存货周转天数"],
    # 现金流
    "operating_cf_net":    ["经营活动净现金流", "经营活动产生的现金流量净额",
                            "经营性净现金流", "经营性现金流净额",
                            "经营活动现金流净额", "经营现金流净额"],
    "ocf_to_net_income":   ["经营现金流/净利润", "经营现金流比净利润"],
    "cash_recv_to_rev":    ["销售商品收现/营收", "销售收现/营收"],
    # BS 关键科目
    "monetary_funds":      ["货币资金"],
    "accounts_receivable": ["应收账款"],
    "other_receivables":   ["其他应收款"],
    "inventory":           ["存货"],
    "short_term_borrow":   ["短期借款"],
    "long_term_borrow":    ["长期借款"],
    "accounts_payable":    ["应付账款"],
    "other_payables":      ["其他应付款"],
    "paid_in_capital":     ["实收资本"],
}


# tag → 白名单里 FinancialIndicators 的字段名 或 raw_statements BS 科目名
TAG_FROM_INDICATOR: dict[str, str] = {
    "revenue":             "revenue",
    "net_profit":          "net_profit",
    "total_assets":        "total_assets",
    "total_liabilities":   "total_liabilities",
    "total_equity":        "total_equity",
    "gross_margin":        "gross_margin",
    "net_margin":          "net_margin",
    "operating_margin":    "operating_margin",
    "debt_to_asset_ratio": "debt_to_asset_ratio",
    "current_ratio":       "current_ratio",
    "quick_ratio":         "quick_ratio",
    "ar_turnover_days":    "ar_turnover_days",
    "inv_turnover_days":   "inventory_turnover_days",
}

TAG_FROM_BS: dict[str, str] = {
    "monetary_funds":      "货币资金",
    "accounts_receivable": "应收账款",
    "other_receivables":   "其他应收款",
    "inventory":           "存货",
    "short_term_borrow":   "短期借款",
    "long_term_borrow":    "长期借款",
    "accounts_payable":    "应付账款",
    "other_payables":      "其他应付款",
    "paid_in_capital":     "实收资本",
}


# ------------------------------------------------------------
# 白名单条目
# ------------------------------------------------------------
@dataclass
class WhitelistEntry:
    tag: str
    current: Optional[float]        # 当期值(已换算为 LLM 正文常用单位)
    previous: Optional[float]       # 上期/年初值
    unit: str                       # 万元/%/倍/天
    current_label: str              # 如 "2025末"
    previous_label: str             # 如 "2024末"

    def expected_for(self, time_hint: str) -> Optional[float]:
        """根据上下文年份/时点 hint 返回期望值。"""
        if not time_hint:
            # 默认当期
            return self.current
        # "较年初" 本身仍指当期(期末值),年初是对比参考
        if any(k in time_hint for k in (
                "当期", "报告期", "当年", "本期", "最新", "末")):
            return self.current
        if any(k in time_hint for k in (
                "上年", "去年", "上期", "前期")):
            return self.previous
        # 精确年份匹配
        if self.current_label and self.current_label[:4] in time_hint:
            return self.current
        if self.previous_label and self.previous_label[:4] in time_hint:
            return self.previous
        return self.current  # 默认当期


# ------------------------------------------------------------
# 构建白名单
# ------------------------------------------------------------
def build_whitelist(financial_indicators) -> dict[str, WhitelistEntry]:
    """从 FinancialIndicators 对象构建白名单。

    注意: FinancialIndicators 中金额类 PeriodValue.current 单位为"元",
    format 时除以 10000 显示万元。此处白名单统一换算为"万元"。
    """
    wl: dict[str, WhitelistEntry] = {}
    if financial_indicators is None:
        return wl

    # 从 FinancialIndicators 直接字段取
    for tag, field_name in TAG_FROM_INDICATOR.items():
        pv = getattr(financial_indicators, field_name, None)
        if pv is None:
            continue
        unit = getattr(pv, "unit", "")
        cur = getattr(pv, "current", None)
        prev = getattr(pv, "previous", None)
        # 金额类以 "万元" 口径存储
        if unit == "万元":
            cur = cur / 10000 if cur is not None else None
            prev = prev / 10000 if prev is not None else None
        wl[tag] = WhitelistEntry(
            tag=tag,
            current=cur, previous=prev,
            unit=unit,
            current_label=getattr(pv, "current_label", ""),
            previous_label=getattr(pv, "previous_label", ""),
        )

    # 从 raw_statements BS 取关键科目
    stmts = getattr(financial_indicators, "raw_statements", None)
    if stmts is not None:
        bs = getattr(stmts, "balance_sheet", {}) or {}
        for tag, subj in TAG_FROM_BS.items():
            pv = bs.get(subj)
            if pv is None:
                continue
            cur = getattr(pv, "current", None)
            prev = getattr(pv, "previous", None)
            cur = cur / 10000 if cur is not None else None
            prev = prev / 10000 if prev is not None else None
            wl[tag] = WhitelistEntry(
                tag=tag,
                current=cur, previous=prev,
                unit="万元",
                current_label=getattr(pv, "current_label", ""),
                previous_label=getattr(pv, "previous_label", ""),
            )

    # 现金流(单值,无 previous)
    ocf = getattr(financial_indicators, "operating_cf_net", None)
    if ocf is not None:
        wl["operating_cf_net"] = WhitelistEntry(
            tag="operating_cf_net",
            current=ocf / 10000, previous=None,
            unit="万元", current_label="", previous_label="",
        )
    ocf_ni = getattr(financial_indicators, "ocf_to_net_income", None)
    if ocf_ni is not None:
        wl["ocf_to_net_income"] = WhitelistEntry(
            tag="ocf_to_net_income",
            current=ocf_ni, previous=None,
            unit="倍", current_label="", previous_label="",
        )

    return wl


# ------------------------------------------------------------
# 文本抽取
# ------------------------------------------------------------
# 数字 + 单位 正则
_NUM_UNIT_RE = re.compile(
    r"(-?\d[\d,]*(?:\.\d+)?)\s*(万元|亿元|%|个百分点|pct|倍|天)"
)


def _to_float(num_str: str) -> Optional[float]:
    try:
        return float(num_str.replace(",", ""))
    except (ValueError, TypeError):
        return None


def _unit_normalize(val: float, unit: str) -> tuple[float, str]:
    """把 亿元→万元,pct/个百分点→% 等对齐到白名单单位。"""
    if unit == "亿元":
        return val * 10000, "万元"
    if unit in ("pct", "个百分点"):
        return val, "%"
    return val, unit


_SENT_STOP = ("。", "；", ";", "\n", ":", ":")


def _tail_prefix(text: str, num_start: int, max_back: int = 40) -> str:
    """取数字左侧真正修饰它的语境 prefix:
    - 最远回溯 max_back 字
    - 遇到句号/分号/换行截断
    - 若 prefix 中仍含有其他『数字+单位』组合,从最后一个组合之后重新开始
      (说明 alias 已被前一个数字"消耗"了)
    """
    left = max(0, num_start - max_back)
    for i in range(num_start - 1, left - 1, -1):
        if text[i] in _SENT_STOP:
            left = i + 1
            break
    prefix = text[left:num_start]
    last = None
    for nm in _NUM_UNIT_RE.finditer(prefix):
        last = nm
    if last is not None:
        prefix = prefix[last.end():]
    return prefix


def _match_tag(text: str, num_start: int) -> Optional[str]:
    """在数字左侧 prefix 中按别名长度降序匹配 tag。"""
    prefix = _tail_prefix(text, num_start)
    if not prefix:
        return None
    best_tag = None
    best_len = 0
    for tag, aliases in TAG_ALIASES.items():
        for alias in aliases:
            if alias in prefix and len(alias) > best_len:
                best_tag = tag
                best_len = len(alias)
    return best_tag


def _extract_time_hint(context: str) -> str:
    """提取时点 hint(年份字串或时点关键词)。"""
    hints = []
    # 年份
    for m in re.finditer(r"20\d{2}\s*年?", context):
        hints.append(m.group(0))
    # 关键词
    for kw in ("年初", "上年", "去年", "上期", "当期", "报告期",
               "当年", "本期", "最新", "末"):
        if kw in context:
            hints.append(kw)
    return " ".join(hints)


def _values_close(actual: float, expected: float, unit: str) -> bool:
    """判断数字是否在容差内。"""
    if expected == 0:
        return abs(actual) < 0.01
    # 比率/百分比:绝对差 < 0.5 个百分点
    if unit in ("%", "个百分点", "pct"):
        return abs(actual - expected) < 0.5
    # 倍/天:相对差 < 5% 或绝对差 < 1
    if unit in ("倍", "天"):
        return (abs(actual - expected) / max(abs(expected), 1)) < 0.05
    # 金额:相对差 < 0.5%
    return (abs(actual - expected) / abs(expected)) < 0.005


@dataclass
class Inconsistency:
    tag: str
    context: str
    actual: float
    expected: float
    unit: str
    time_hint: str
    start: int
    end: int

    def describe(self) -> str:
        return (f"『{self.context}』中 {self.tag} 写作 {self.actual}{self.unit},"
                f"但权威值为 {self.expected}{self.unit}")


def find_inconsistencies(
    text: str,
    whitelist: dict[str, WhitelistEntry],
    window_left: int = 22,
    window_right: int = 4,
) -> list[Inconsistency]:
    """扫描文本,返回所有可定位且不一致的数字条目。"""
    if not text or not whitelist:
        return []

    errors: list[Inconsistency] = []
    for m in _NUM_UNIT_RE.finditer(text):
        num_str, unit = m.group(1), m.group(2)
        val = _to_float(num_str)
        if val is None:
            continue
        norm_val, norm_unit = _unit_normalize(val, unit)

        start = max(0, m.start() - window_left)
        end = min(len(text), m.end() + window_right)
        context = text[start:end]

        tag = _match_tag(text, m.start())
        if tag is None:
            continue
        entry = whitelist.get(tag)
        if entry is None:
            continue

        # 单位不匹配直接跳(避免误报,例如%和万元)
        if entry.unit != norm_unit:
            continue

        time_hint = _extract_time_hint(context)
        expected = entry.expected_for(time_hint)
        if expected is None:
            continue

        if not _values_close(norm_val, expected, entry.unit):
            errors.append(Inconsistency(
                tag=tag,
                context=context.strip(),
                actual=norm_val,
                expected=expected,
                unit=entry.unit,
                time_hint=time_hint,
                start=m.start(),
                end=m.end(),
            ))

    return errors


# ------------------------------------------------------------
# 自测
# ------------------------------------------------------------
if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    # 构造一个假白名单
    wl = {
        "revenue": WhitelistEntry(
            tag="revenue", current=10010.0, previous=8712.0,
            unit="万元", current_label="2025末", previous_label="2024末"),
        "net_profit": WhitelistEntry(
            tag="net_profit", current=494.0, previous=329.0,
            unit="万元", current_label="2025末", previous_label="2024末"),
        "debt_to_asset_ratio": WhitelistEntry(
            tag="debt_to_asset_ratio", current=42.5, previous=50.2,
            unit="%", current_label="2025末", previous_label="2024末"),
    }

    tests = [
        # 应被抓的:有 alias 前缀
        "2025年营业收入1010万元",                # 应报
        "当年净利润为4940万元",                   # 应报
        "资产负债率52.5%",                       # 应报 (实际 42.5)
        # 不应误报
        "2025年营业收入10010万元,同比增长14.9%", # 不应报 (值对)
        "资产负债率42.5%,较年初下降7.7个百分点", # 只该检查42.5,7.7不匹配
        "2024年营业收入8712万元",                 # 不应报 (previous 值)
        "客户A贡献收入1116万元",                 # 不应报 (无 alias 精确匹配 revenue)
    ]
    for t in tests:
        errs = find_inconsistencies(t, wl)
        status = f"OK" if not errs else f"ERR x{len(errs)}"
        print(f"[{status}] {t}")
        for e in errs:
            print(f"    → {e.describe()}")
