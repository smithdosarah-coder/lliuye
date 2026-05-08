# -*- coding: utf-8 -*-
"""企业实体归一 resolver.

设计 (per CLAUDE.md §3.1 确定性 vs 概率性):
- USCC validate / normalize_company_name = 确定性 (Python 规则)
- LLM fuzzy match = 概率性 (走 shared.llm_caller · PIPL fallback chain)

EntityKey 定义:
- USCC 优先 (18 位 · 唯一锚点 · 100% 准)
- 缺 USCC 时 fallback name_normalized (规则化清洗后的名字)
- LLM fuzzy match 仅在 name 高度相似但不完全相等时调用 (e.g. "海康威视" vs "杭州海康威视数字技术股份有限公司")
"""
from __future__ import annotations

import re
from dataclasses import dataclass


# 中国统一社会信用代码 18 位 · 1 注册管理部门 + 1 机构类别 + 6 行政区划 + 9 主体识别 + 1 校验
_USCC_RE = re.compile(r"^[0-9A-HJ-NP-RTUW-Y]{18}$")

# 公司后缀 · normalize 时去除 (但保留 main 名字)
_COMPANY_SUFFIXES = [
    "股份有限公司",
    "有限责任公司",
    "有限公司",
    "集团公司",
    "集团",
    "公司",
    "合作社",
    "分公司",
    "(集团)",
    "（集团）",
]

# 地名前缀 · normalize 时去除 (e.g. "上海海潮" / "杭州海康威视" 的"上海"/"杭州")
_PROVINCE_PREFIXES = [
    "北京", "上海", "广州", "深圳", "杭州", "苏州", "南京", "武汉", "成都",
    "重庆", "天津", "西安", "青岛", "大连", "厦门", "宁波", "无锡", "佛山",
    "中国", "上海市", "北京市",
]

# 中文标点 · normalize 时去除
_PUNCT_RE = re.compile(r"[（）\(\)·\-_\s　]+")


@dataclass(frozen=True)
class EntityKey:
    """实体唯一 key · 多源去重时按 key 比较."""

    uscc: str = ""  # 18 位 USCC · 优先
    name_normalized: str = ""  # 规则化清洗后的名字 · USCC 缺时兜底
    confidence: float = 1.0  # 0.0-1.0 · USCC 命中=1.0 · LLM fuzzy=0.6-0.9 · 仅 name=0.5

    @property
    def is_uscc_anchored(self) -> bool:
        """True = 用 USCC 作主键 (高可信)."""
        return bool(self.uscc)

    def __hash__(self) -> int:
        return hash(self.uscc) if self.uscc else hash(self.name_normalized)

    def matches(self, other: "EntityKey") -> bool:
        """同一实体判断 · USCC 优先 · 否则 name 完全相等.

        谨慎 rule: USCC anchored 状态必须一致 (一边有 USCC 一边没 → 不算 match · 宁可重复也不假合并).
        """
        if bool(self.uscc) != bool(other.uscc):
            return False
        if self.uscc and other.uscc:
            return self.uscc == other.uscc
        if self.name_normalized and other.name_normalized:
            return self.name_normalized == other.name_normalized
        return False


def validate_uscc(uscc: str) -> bool:
    """18 位 USCC 格式校验 (不算校验码 · 仅格式).

    真校验码算法 (GB 32100-2015) 后续 step 加 · 当前 PoC 仅长度 + 字符集.
    """
    if not uscc or not isinstance(uscc, str):
        return False
    return bool(_USCC_RE.match(uscc.strip().upper()))


def normalize_company_name(name: str) -> str:
    """规则化清洗公司名 · 去后缀 / 去地名前缀 / 去标点.

    例:
    - "(上海)海潮工业软件有限公司" → "海潮工业软件"
    - "杭州海康威视数字技术股份有限公司" → "海康威视数字技术"
    - "海康威视" → "海康威视" (无变化)

    用于 USCC 缺失时的 fallback 主键 · 也用于 LLM fuzzy match 前的预处理.
    """
    if not name or not isinstance(name, str):
        return ""

    s = name.strip()

    # 1. 去标点 (括号/中点/连字符/空格)
    s = _PUNCT_RE.sub("", s)

    # 2. 去地名前缀
    for prefix in _PROVINCE_PREFIXES:
        if s.startswith(prefix):
            s = s[len(prefix):]
            break

    # 3. 去公司后缀 (反复匹配 · 防 "集团有限公司" 一次只去一个 · 从长到短)
    changed = True
    while changed:
        changed = False
        for suffix in sorted(_COMPANY_SUFFIXES, key=len, reverse=True):
            if s.endswith(suffix):
                s = s[: -len(suffix)]
                changed = True
                break

    return s.strip()


def resolve_entity(name: str = "", uscc: str = "") -> EntityKey:
    """主入口 · 输入 name + 可选 uscc · 输出标准化 EntityKey.

    优先级:
    1. USCC 合法 → 用 USCC + name_normalized · confidence=1.0
    2. USCC 缺/非法 + name 有 → 用 name_normalized · confidence=0.5
    3. 都缺 → 空 EntityKey · confidence=0.0

    LLM fuzzy match (step 2.3 加 · 当前 PoC 不调用):
    - 当多个 candidate 的 name_normalized 高度相似但不相等时
    - 走 shared.llm_caller · PIPL fallback chain
    """
    name_norm = normalize_company_name(name)

    if validate_uscc(uscc):
        return EntityKey(
            uscc=uscc.strip().upper(),
            name_normalized=name_norm,
            confidence=1.0,
        )

    if name_norm:
        return EntityKey(
            uscc="",
            name_normalized=name_norm,
            confidence=0.5,
        )

    return EntityKey(uscc="", name_normalized="", confidence=0.0)
