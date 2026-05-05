# -*- coding: utf-8 -*-
"""agent_riskctrl.unit_normalizer — 单位归一 (BE6.2).

把人类输入的 '1.5亿' / '80%' / '50bps' / '300万' 自动归一成数值 ·
配合 dsl_field_dict (BE6.1) 的 dtype 决定目标单位:

- DTYPE_AMOUNT_CNY (元):    '1.5亿' → 150000000.0 / '300万' → 3000000.0 / '8000' → 8000.0
- DTYPE_AMOUNT_WAN (万元):  '1.5亿' → 15000.0 / '300万' → 300.0 / '8000' → 0.8
- DTYPE_AMOUNT_YI  (亿):    '1.5亿' → 1.5 / '5000万' → 0.5
- DTYPE_PERCENT (%):        '80%' → 80.0 / '0.8' → 80.0 (auto-scale ratio→percent) / '50bps' → 0.5
- DTYPE_RATIO (0-1):        '80%' → 0.8 / '0.8' → 0.8 / '50bps' → 0.005
- DTYPE_BPS:                '50bps' → 50.0 / '0.5%' → 50.0 / '0.005' → 50.0

设计:
- §3.1 确定性 Python · 不让 LLM 现场猜单位
- 中英文符号容忍: '亿' / 'yi' / '万' / 'wan' / '%' / 'bps' / 'BPS'
- ambiguous 输入 (e.g. '0.8' 给 percent 字段) 用 heuristic + flag warning
- normalize 失败返 None + 详细原因 · 不抛 (DSL gen 容忍部分字段失败)

Public surface:
- ``parse_human_value(s) -> ParsedValue`` · 解析任意 string → (value, source_unit, hint)
- ``normalize_to_dtype(s, dtype) -> NormalizedResult`` · 归一到目标 dtype
- ``normalize_for_field(field_name, value) -> NormalizedResult`` · 配 BE6.1 字段字典自动判 dtype
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from agent_riskctrl.dsl_field_dict import (
    DTYPE_AMOUNT_CNY,
    DTYPE_AMOUNT_WAN,
    DTYPE_AMOUNT_YI,
    DTYPE_BPS,
    DTYPE_PERCENT,
    DTYPE_RATIO,
    get_field_spec,
)


# ---------------------------------------------------------------------------
# Source unit enum
# ---------------------------------------------------------------------------

UNIT_RAW = "raw"            # 无后缀的纯数值
UNIT_PERCENT = "percent"    # 80% / 80pct
UNIT_BPS = "bps"            # 50bps
UNIT_AMOUNT_CNY = "cny"     # 8000元 / 8000 RMB
UNIT_AMOUNT_WAN = "wan"     # 300万 / 300 万元
UNIT_AMOUNT_YI = "yi"       # 1.5亿 / 1.5 yi
UNIT_AMOUNT_QIAN = "qian"   # 5千 (rare)


# ---------------------------------------------------------------------------
# Regex
# ---------------------------------------------------------------------------

# 支持小数 + 千分位逗号 + 中文逗号
_NUM_RE = re.compile(r"-?\d+(?:[,，]\d{3})*(?:\.\d+)?")

_UNIT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"亿\s*元?\b|yi\b|亿$", re.IGNORECASE), UNIT_AMOUNT_YI),
    (re.compile(r"万\s*元?\b|wan\b|万$", re.IGNORECASE), UNIT_AMOUNT_WAN),
    (re.compile(r"千\s*元\b|千$", re.IGNORECASE), UNIT_AMOUNT_QIAN),
    (re.compile(r"rmb|cny|元|人民币", re.IGNORECASE), UNIT_AMOUNT_CNY),
    (re.compile(r"bps|基点", re.IGNORECASE), UNIT_BPS),
    (re.compile(r"%|pct|percent|百分比", re.IGNORECASE), UNIT_PERCENT),
]


# ---------------------------------------------------------------------------
# ParsedValue / NormalizedResult
# ---------------------------------------------------------------------------


@dataclass
class ParsedValue:
    """parse_human_value 输出 · 描述输入字符串的语义."""
    value: float | None       # 数值 (单位前的数字 · 不含转换)
    source_unit: str          # UNIT_*
    raw: str                  # 原始字符串 (trimmed)
    error: str = ""           # 解析失败时填


@dataclass
class NormalizedResult:
    """归一结果."""
    value: float | None       # 归一后数值 (None = 失败)
    target_dtype: str         # DTYPE_*
    source_unit: str          # 解析到的源单位
    raw: str                  # 原始字符串
    warnings: list[str]       # ambiguous 警告 (e.g. '0.8 → 80% 用 ratio→percent 启发式')
    error: str = ""


# ---------------------------------------------------------------------------
# Core parse
# ---------------------------------------------------------------------------


def parse_human_value(text: str | float | int) -> ParsedValue:
    """从人类输入提数值 + 源单位 · 不做单位转换.

    Examples:
        parse('1.5亿')        → (1.5, 'yi')
        parse('300万元')      → (300, 'wan')
        parse('80%')          → (80, 'percent')
        parse('50 bps')       → (50, 'bps')
        parse('19,031 元')    → (19031, 'cny')
        parse('0.74')         → (0.74, 'raw')
        parse(0.74)           → (0.74, 'raw')
        parse('hello')        → (None, 'raw', error='no number')
    """
    if text is None:
        return ParsedValue(value=None, source_unit=UNIT_RAW, raw="", error="empty input")

    if isinstance(text, (int, float)):
        return ParsedValue(value=float(text), source_unit=UNIT_RAW, raw=str(text))

    s = str(text).strip()
    if not s:
        return ParsedValue(value=None, source_unit=UNIT_RAW, raw="", error="empty input")

    # 提数字 (允许中英文千分位)
    m = _NUM_RE.search(s)
    if m is None:
        return ParsedValue(value=None, source_unit=UNIT_RAW, raw=s, error="no number found")
    num_str = m.group(0).replace(",", "").replace("，", "")
    try:
        num = float(num_str)
    except ValueError:
        return ParsedValue(
            value=None, source_unit=UNIT_RAW, raw=s, error=f"cannot parse '{num_str}'",
        )

    # 探单位 (后缀)
    rest = s[m.end():]
    full = s
    for pattern, unit in _UNIT_PATTERNS:
        if pattern.search(rest) or pattern.search(full):
            return ParsedValue(value=num, source_unit=unit, raw=s)

    return ParsedValue(value=num, source_unit=UNIT_RAW, raw=s)


# ---------------------------------------------------------------------------
# Conversion table → CNY base
# ---------------------------------------------------------------------------

# 把任意金额单位换算到 CNY
_AMOUNT_TO_CNY: dict[str, float] = {
    UNIT_AMOUNT_CNY: 1.0,
    UNIT_AMOUNT_WAN: 10_000.0,
    UNIT_AMOUNT_QIAN: 1_000.0,
    UNIT_AMOUNT_YI: 100_000_000.0,
    UNIT_RAW: 1.0,  # 无后缀 amount 字段 · 假设已在目标单位
}


def _amount_to_cny(value: float, source_unit: str) -> float | None:
    factor = _AMOUNT_TO_CNY.get(source_unit)
    if factor is None:
        return None
    return value * factor


def _cny_to_dtype(cny: float, target_dtype: str) -> float:
    if target_dtype == DTYPE_AMOUNT_CNY:
        return cny
    if target_dtype == DTYPE_AMOUNT_WAN:
        return cny / 10_000.0
    if target_dtype == DTYPE_AMOUNT_YI:
        return cny / 100_000_000.0
    raise ValueError(f"_cny_to_dtype 不支持 {target_dtype}")


# ---------------------------------------------------------------------------
# Normalize entry point
# ---------------------------------------------------------------------------


_AMOUNT_DTYPES = frozenset({DTYPE_AMOUNT_CNY, DTYPE_AMOUNT_WAN, DTYPE_AMOUNT_YI})
_PERCENT_LIKE_DTYPES = frozenset({DTYPE_PERCENT, DTYPE_RATIO, DTYPE_BPS})


def normalize_to_dtype(text: str | float | int, target_dtype: str) -> NormalizedResult:
    """把人类输入归一到目标 dtype.

    Heuristics for ambiguous '0.8':
      - target=PERCENT: 0 ≤ x ≤ 1 → ×100 (ratio→percent · warn)
      - target=RATIO:   1 < x ≤ 100 → /100 (percent→ratio · warn)
      - target=BPS:     按 percent 处理 → ×100 (1% = 100bps)

    Returns NormalizedResult · value=None on failure.
    """
    parsed = parse_human_value(text)
    warnings: list[str] = []

    if parsed.value is None:
        return NormalizedResult(
            value=None, target_dtype=target_dtype, source_unit=parsed.source_unit,
            raw=parsed.raw, warnings=warnings, error=parsed.error,
        )

    raw_num = parsed.value
    src = parsed.source_unit

    # === 金额类 ===
    if target_dtype in _AMOUNT_DTYPES:
        if src in _PERCENT_LIKE_DTYPES or src == UNIT_PERCENT or src == UNIT_BPS:
            return NormalizedResult(
                value=None, target_dtype=target_dtype, source_unit=src,
                raw=parsed.raw, warnings=warnings,
                error=f"金额字段不能接受 {src} 输入 ({parsed.raw})",
            )
        cny = _amount_to_cny(raw_num, src)
        if cny is None:
            return NormalizedResult(
                value=None, target_dtype=target_dtype, source_unit=src,
                raw=parsed.raw, warnings=warnings,
                error=f"未知金额单位 {src}",
            )
        # 无后缀输入 → 假设已在目标单位 (e.g. '300' 给 amount_wan 字段视作 300 万元)
        if src == UNIT_RAW:
            warnings.append(
                f"输入 '{parsed.raw}' 无单位后缀 · 视作目标单位 ({target_dtype})"
            )
            value = raw_num
        else:
            value = _cny_to_dtype(cny, target_dtype)
        return NormalizedResult(
            value=value, target_dtype=target_dtype, source_unit=src,
            raw=parsed.raw, warnings=warnings,
        )

    # === 百分比 / ratio / bps ===
    if target_dtype == DTYPE_PERCENT:
        if src == UNIT_BPS:
            value = raw_num / 100.0  # 50bps → 0.5%
            return NormalizedResult(
                value=value, target_dtype=target_dtype, source_unit=src,
                raw=parsed.raw, warnings=warnings,
            )
        if src == UNIT_PERCENT:
            return NormalizedResult(
                value=raw_num, target_dtype=target_dtype, source_unit=src,
                raw=parsed.raw, warnings=warnings,
            )
        if src == UNIT_RAW:
            # ambiguous · 0-1 当 ratio · 否则当 percent
            if 0 <= raw_num <= 1:
                value = raw_num * 100.0
                warnings.append(
                    f"输入 '{parsed.raw}' ∈ [0,1] · 启发式视作 ratio → percent (×100)"
                )
                return NormalizedResult(
                    value=value, target_dtype=target_dtype, source_unit=src,
                    raw=parsed.raw, warnings=warnings,
                )
            return NormalizedResult(
                value=raw_num, target_dtype=target_dtype, source_unit=src,
                raw=parsed.raw, warnings=warnings,
            )
        return NormalizedResult(
            value=None, target_dtype=target_dtype, source_unit=src,
            raw=parsed.raw, warnings=warnings,
            error=f"percent 字段不能接 {src} 输入",
        )

    if target_dtype == DTYPE_RATIO:
        if src == UNIT_BPS:
            value = raw_num / 10000.0  # 50bps → 0.005
            return NormalizedResult(
                value=value, target_dtype=target_dtype, source_unit=src,
                raw=parsed.raw, warnings=warnings,
            )
        if src == UNIT_PERCENT:
            value = raw_num / 100.0  # 80% → 0.8
            return NormalizedResult(
                value=value, target_dtype=target_dtype, source_unit=src,
                raw=parsed.raw, warnings=warnings,
            )
        if src == UNIT_RAW:
            # ambiguous · >1 当 percent · 否则当 ratio
            if 1 < raw_num <= 100:
                value = raw_num / 100.0
                warnings.append(
                    f"输入 '{parsed.raw}' ∈ (1,100] · 启发式视作 percent → ratio (/100)"
                )
                return NormalizedResult(
                    value=value, target_dtype=target_dtype, source_unit=src,
                    raw=parsed.raw, warnings=warnings,
                )
            return NormalizedResult(
                value=raw_num, target_dtype=target_dtype, source_unit=src,
                raw=parsed.raw, warnings=warnings,
            )
        return NormalizedResult(
            value=None, target_dtype=target_dtype, source_unit=src,
            raw=parsed.raw, warnings=warnings,
            error=f"ratio 字段不能接 {src} 输入",
        )

    if target_dtype == DTYPE_BPS:
        if src == UNIT_BPS:
            return NormalizedResult(
                value=raw_num, target_dtype=target_dtype, source_unit=src,
                raw=parsed.raw, warnings=warnings,
            )
        if src == UNIT_PERCENT:
            value = raw_num * 100.0  # 1% = 100bps
            return NormalizedResult(
                value=value, target_dtype=target_dtype, source_unit=src,
                raw=parsed.raw, warnings=warnings,
            )
        if src == UNIT_RAW:
            # ambiguous · ≤ 1 视作 ratio · 否则视作 bps 直透
            if 0 <= raw_num <= 1:
                value = raw_num * 10000.0
                warnings.append(
                    f"输入 '{parsed.raw}' ∈ [0,1] · 启发式视作 ratio → bps (×10000)"
                )
                return NormalizedResult(
                    value=value, target_dtype=target_dtype, source_unit=src,
                    raw=parsed.raw, warnings=warnings,
                )
            return NormalizedResult(
                value=raw_num, target_dtype=target_dtype, source_unit=src,
                raw=parsed.raw, warnings=warnings,
            )
        return NormalizedResult(
            value=None, target_dtype=target_dtype, source_unit=src,
            raw=parsed.raw, warnings=warnings,
            error=f"bps 字段不能接 {src} 输入",
        )

    # === 透传 (int / float / days / months / years / categorical) ===
    if src in (UNIT_PERCENT, UNIT_BPS, UNIT_AMOUNT_CNY, UNIT_AMOUNT_WAN, UNIT_AMOUNT_YI, UNIT_AMOUNT_QIAN):
        warnings.append(
            f"输入 '{parsed.raw}' 含单位 {src} · 但 target {target_dtype} 不需要 · 透传数值"
        )
    return NormalizedResult(
        value=raw_num, target_dtype=target_dtype, source_unit=src,
        raw=parsed.raw, warnings=warnings,
    )


def normalize_for_field(field_name: str, value: str | float | int) -> NormalizedResult:
    """配 BE6.1 字段字典 · 自动判 dtype 后归一.

    Field 未注册 → error filled.
    """
    spec = get_field_spec(field_name)
    if spec is None:
        return NormalizedResult(
            value=None, target_dtype="unknown", source_unit=UNIT_RAW,
            raw=str(value), warnings=[],
            error=f"字段 '{field_name}' 未在 FIELD_DICT 注册",
        )
    return normalize_to_dtype(value, spec.dtype)


__all__ = [
    "NormalizedResult",
    "ParsedValue",
    "UNIT_AMOUNT_CNY",
    "UNIT_AMOUNT_QIAN",
    "UNIT_AMOUNT_WAN",
    "UNIT_AMOUNT_YI",
    "UNIT_BPS",
    "UNIT_PERCENT",
    "UNIT_RAW",
    "normalize_for_field",
    "normalize_to_dtype",
    "parse_human_value",
]
