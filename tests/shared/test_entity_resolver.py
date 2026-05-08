# -*- coding: utf-8 -*-
"""shared.entity_resolver 单测.

PM 2026-05-07 ALL IN step 2.2 · codex R1 第 1 关键洞察 · 实体归一基础设施.
"""
from __future__ import annotations

import pytest

from shared.entity_resolver import (
    EntityKey,
    normalize_company_name,
    resolve_entity,
    validate_uscc,
)


class TestUsccValidation:
    """18 位 USCC 格式校验."""

    def test_valid_uscc(self):
        # 真实 USCC 示例 (网上公开 · 海康威视)
        assert validate_uscc("91330185711315925G")

    def test_valid_uscc_lowercase(self):
        # 字母大小写 · 应不区分
        assert validate_uscc("91330185711315925g")

    def test_invalid_uscc_too_short(self):
        assert not validate_uscc("91330185")

    def test_invalid_uscc_too_long(self):
        assert not validate_uscc("91330185711315925G123")

    def test_invalid_uscc_with_special_chars(self):
        assert not validate_uscc("9133-0185711315925G")

    def test_empty_uscc(self):
        assert not validate_uscc("")
        assert not validate_uscc(None)


class TestNormalizeCompanyName:
    """公司名规则化清洗."""

    def test_remove_company_suffix(self):
        assert normalize_company_name("海潮工业软件有限公司") == "海潮工业软件"
        assert normalize_company_name("阿里巴巴集团") == "阿里巴巴"
        assert normalize_company_name("腾讯控股有限责任公司") == "腾讯控股"

    def test_remove_province_prefix(self):
        # 杭州 + 海康威视数字技术 + 股份有限公司 → 海康威视数字技术
        assert normalize_company_name("杭州海康威视数字技术股份有限公司") == "海康威视数字技术"

    def test_remove_punct(self):
        # 标点 / 括号 / 中点 / 空格全去
        assert normalize_company_name("海康·威视 (集团) 有限公司") == "海康威视"

    def test_no_change_for_pure_name(self):
        # 已 normalize 的名字不变
        assert normalize_company_name("海康威视") == "海康威视"

    def test_empty_name(self):
        assert normalize_company_name("") == ""
        assert normalize_company_name(None) == ""


class TestResolveEntity:
    """主入口 · USCC 优先 · name fallback."""

    def test_uscc_anchored(self):
        """合法 USCC → confidence=1.0 · is_uscc_anchored=True."""
        e = resolve_entity(name="杭州海康威视股份有限公司", uscc="91330185711315925G")
        assert e.uscc == "91330185711315925G"
        assert e.name_normalized == "海康威视"
        assert e.confidence == 1.0
        assert e.is_uscc_anchored

    def test_name_only_fallback(self):
        """USCC 缺 → 用 name_normalized · confidence=0.5."""
        e = resolve_entity(name="海康威视股份有限公司")
        assert e.uscc == ""
        assert e.name_normalized == "海康威视"
        assert e.confidence == 0.5
        assert not e.is_uscc_anchored

    def test_invalid_uscc_fallback_to_name(self):
        """USCC 非法 → 退化到 name fallback."""
        e = resolve_entity(name="海康威视有限公司", uscc="invalid")
        assert e.uscc == ""
        assert e.name_normalized == "海康威视"
        assert e.confidence == 0.5

    def test_empty_input(self):
        """都空 → empty EntityKey · confidence=0.0."""
        e = resolve_entity()
        assert e.uscc == ""
        assert e.name_normalized == ""
        assert e.confidence == 0.0


class TestEntityKeyMatching:
    """同一实体判断 (多源去重核心)."""

    def test_same_uscc_matches(self):
        """USCC 相同 → 同一实体 (即使名字不一样)."""
        e1 = resolve_entity(name="海康威视", uscc="91330185711315925G")
        e2 = resolve_entity(name="杭州海康威视数字技术股份有限公司", uscc="91330185711315925G")
        assert e1.matches(e2)

    def test_same_name_normalized_matches(self):
        """都没 USCC · name_normalized 相同 → 同一实体 (兜底主键)."""
        e1 = resolve_entity(name="海康威视有限公司")
        e2 = resolve_entity(name="(杭州)海康威视股份有限公司")
        assert e1.matches(e2)

    def test_different_uscc_not_match(self):
        """USCC 不同 → 不同实体 (即使名字相似)."""
        e1 = resolve_entity(name="海康威视", uscc="91330185711315925G")
        e2 = resolve_entity(name="海康威视", uscc="91110108800049528K")
        assert not e1.matches(e2)

    def test_uscc_anchored_vs_name_only_not_match(self):
        """一边有 USCC 一边没 · 即使 name 一样 · 不算 match (谨慎)."""
        e1 = resolve_entity(name="海康威视", uscc="91330185711315925G")
        e2 = resolve_entity(name="海康威视")
        # USCC 缺 → 仅按 name_normalized 比 · USCC anchored 走 USCC 比 · 两边规则不同 → 不算 match
        # (谨慎: 真生产宁可重复也不假合并)
        assert not e1.matches(e2)


class TestEntityKeyHash:
    """EntityKey hashable · 可作 dict key / set element."""

    def test_uscc_anchored_hash_unique(self):
        e1 = EntityKey(uscc="91330185711315925G", name_normalized="海康威视")
        e2 = EntityKey(uscc="91330185711315925G", name_normalized="不同 name")
        assert hash(e1) == hash(e2)

    def test_name_only_hash_unique(self):
        e1 = EntityKey(uscc="", name_normalized="海康威视")
        e2 = EntityKey(uscc="", name_normalized="海康威视")
        assert hash(e1) == hash(e2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
