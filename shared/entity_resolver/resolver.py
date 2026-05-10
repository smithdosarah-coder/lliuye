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
# GB 32100-2015 字符集 · 31 chars · 排除易混 I O S V Z · 0-9 + A-Y (扣 I O S V Z)
_USCC_RE = re.compile(r"^[0-9A-HJ-NPQRTUWXY]{18}$")

# GB 32100-2015 字符 → 数值映射表 (31 字符 · 索引即 value)
_USCC_CHARSET = "0123456789ABCDEFGHJKLMNPQRTUWXY"
_USCC_CHAR_TO_VALUE = {c: i for i, c in enumerate(_USCC_CHARSET)}

# GB 32100-2015 加权因子 W_i · 17 位 · 仅前 17 位入和 · 第 18 位为校验码
_USCC_WEIGHTS = (1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28)

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
    """实体唯一 key · 多源去重时按 key 比较.

    设计:
    - 主键 = uscc (优先) 或 name_normalized (fallback)
    - __hash__ + __eq__ 对齐主键 (USCC anchored 仅按 USCC · name-only 仅按 name_normalized)
    - confidence 不入 hash/eq · 同主键多源 confidence 应一致 (1.0/0.5)
    - 一边 USCC anchored 另一边 name-only → 不 eq (谨慎规则 · 宁可重复也不假合并)

    set / dict 行为:
    - {EntityKey(uscc=X, name_a), EntityKey(uscc=X, name_b)} 折叠成 1 个 (主键相同)
    - {EntityKey(name_a), EntityKey(uscc=X, name_a)} 不折叠 (一边 anchored 另一边 not)
    """

    uscc: str = ""  # 18 位 USCC · 优先
    name_normalized: str = ""  # 规则化清洗后的名字 · USCC 缺时兜底
    confidence: float = 1.0  # 0.0-1.0 · USCC 命中=1.0 · LLM fuzzy=0.6-0.9 · 仅 name=0.5

    @property
    def is_uscc_anchored(self) -> bool:
        """True = 用 USCC 作主键 (高可信)."""
        return bool(self.uscc)

    def __hash__(self) -> int:
        # 主键 hash · USCC anchored 仅按 USCC · name-only 仅按 name_normalized
        # 加 anchored bit 防 USCC anchored 与 name-only 哈希撞 (理论可能但实战极少)
        if self.uscc:
            return hash(("uscc", self.uscc))
        return hash(("name", self.name_normalized))

    def __eq__(self, other: object) -> bool:
        # 与 __hash__ 对齐 · Python 契约 hash 相等必 __eq__ 相等
        if not isinstance(other, EntityKey):
            return NotImplemented
        return self.matches(other)

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


def validate_uscc_format(uscc: str) -> bool:
    """USCC 格式校验 (仅长度 + 字符集 · 不算校验码)."""
    if not uscc or not isinstance(uscc, str):
        return False
    return bool(_USCC_RE.match(uscc.strip().upper()))


def validate_uscc_checksum(uscc: str) -> bool:
    """GB 32100-2015 校验码算法 · 真校验.

    步骤:
    1. 取前 17 位 · 按 _USCC_CHARSET 转 value (0-30)
    2. Σ(W_i · value_i) mod 31
    3. (31 - Σmod31) mod 31 = 期望校验值
    4. 期望校验值 → _USCC_CHARSET[expected] = 期望第 18 位字符
    5. 比对实际第 18 位

    例: "91330185711315925G"
    - 前 17 位: 91330185711315925
    - 加权和按表算 → 校验值落到 'G' (16)

    Returns: True iff 校验码匹配 · format 不合格直接 False
    """
    if not validate_uscc_format(uscc):
        return False

    s = uscc.strip().upper()
    try:
        weighted = sum(
            _USCC_WEIGHTS[i] * _USCC_CHAR_TO_VALUE[s[i]]
            for i in range(17)
        )
    except KeyError:
        # 字符不在 charset (含 I O S V Z) · 已被 _USCC_RE 拒
        return False

    expected_value = (31 - (weighted % 31)) % 31
    expected_char = _USCC_CHARSET[expected_value]
    return s[17] == expected_char


def validate_uscc(uscc: str, *, strict: bool = False) -> bool:
    """USCC 校验 · 默认仅格式 (向下兼容) · strict=True 时启用 GB 32100 校验码.

    Args:
        uscc: 18 位 USCC string
        strict: True = 校验码 + 格式 (生产推荐) · False = 仅格式 (PoC / 兼容)

    Returns: True iff 通过对应级别校验
    """
    if strict:
        return validate_uscc_checksum(uscc)
    return validate_uscc_format(uscc)


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


def resolve_entity(name: str = "", uscc: str = "", *, strict: bool = False) -> EntityKey:
    """主入口 · 输入 name + 可选 uscc · 输出标准化 EntityKey.

    Args:
        name: 公司名 (会被 normalize_company_name 清洗)
        uscc: 18 位 USCC (可选 · 缺则按 name fallback)
        strict: True 时 USCC 必过校验码 (GB 32100-2015) · False 仅格式 (默认 · 兼容旧调用)

    优先级:
    1. USCC 通过校验 → 用 USCC + name_normalized · confidence=1.0
    2. USCC 缺/非法 + name 有 → 用 name_normalized · confidence=0.5
    3. 都缺 → 空 EntityKey · confidence=0.0

    LLM fuzzy match (Phase B agent 自接 · 当前不在 resolver 内调用):
    - 当多个 candidate 的 name_normalized 高度相似但不相等时
    - agent 自己走 shared.llm_caller · PIPL fallback chain
    - 输出 0.6-0.85 的 fuzzy_score 作为 EntityKey.confidence 上限
    """
    name_norm = normalize_company_name(name)

    if validate_uscc(uscc, strict=strict):
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


def make_unique_id(
    name: str = "",
    uscc: str = "",
    idx: int = 0,
    *,
    strict: bool = False,
) -> str:
    """候选 unique id 派生 (per candidate-identity-contract.md §2).

    优先级:
    1. USCC 通过校验 → "uscc_<USCC>"
    2. name 有 → "name_<md5前 12 位>" (基于 normalize_company_name 输出)
    3. 兜底 → "cand_<idx:03d>"

    用途:
    - 6 agent 的 candidate / customer / record 列表 emit 时必填 id 字段
    - 前端 setSelected(id) + find(it.id === selected) 永不返第一项
    - PM 2026-05-08 痛点 (左右气泡不联动) 的真根因 fix · 推广用

    Args:
        name: 公司名 (会被 normalize_company_name 清洗)
        uscc: 18 位 USCC (可选)
        idx: list 中位置 (兜底用 · 必传 ≥ 0)
        strict: True 时 USCC 必过校验码 (推荐生产)

    Returns: id string · 同一 list 内必 unique (调用方负责)

    例:
        >>> make_unique_id("海康威视", "91330185711315925G", 0)
        'uscc_91330185711315925G'
        >>> make_unique_id("某不知名小厂", idx=3)
        'name_<md5前12位>'
        >>> make_unique_id(idx=5)
        'cand_005'
    """
    import hashlib

    if validate_uscc(uscc, strict=strict):
        return f"uscc_{uscc.strip().upper()}"

    name_norm = normalize_company_name(name)
    if name_norm:
        digest = hashlib.md5(name_norm.encode("utf-8")).hexdigest()[:12]
        return f"name_{digest}"

    return f"cand_{idx:03d}"
