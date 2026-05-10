# -*- coding: utf-8 -*-
"""shared.entity_resolver 单测.

PM 2026-05-07 ALL IN step 2.2 · codex R1 第 1 关键洞察 · 实体归一基础设施.
Phase A common (2026-05-09) 扩 GB 32100 校验码 + make_unique_id (per candidate-identity-contract).
"""
from __future__ import annotations

import pytest

from shared.entity_resolver import (
    EntityKey,
    make_unique_id,
    normalize_company_name,
    resolve_entity,
    validate_uscc,
    validate_uscc_checksum,
    validate_uscc_format,
)


class TestUsccFormat:
    """validate_uscc_format · 仅长度 + 字符集 · 不算校验码."""

    def test_valid_format(self):
        assert validate_uscc_format("91330185711315925G")

    def test_valid_format_lowercase(self):
        assert validate_uscc_format("91330185711315925g")

    def test_too_short(self):
        assert not validate_uscc_format("91330185")

    def test_too_long(self):
        assert not validate_uscc_format("91330185711315925G123")

    def test_special_chars(self):
        assert not validate_uscc_format("9133-0185711315925G")

    def test_empty(self):
        assert not validate_uscc_format("")
        assert not validate_uscc_format(None)

    def test_forbidden_char_I(self):
        # GB 32100 字符集排除 I O S V Z (易混)
        assert not validate_uscc_format("9133018571131592I0")

    def test_forbidden_char_O(self):
        assert not validate_uscc_format("9133018571131592O0")

    def test_forbidden_char_S(self):
        assert not validate_uscc_format("9133018571131592S0")

    def test_forbidden_char_V(self):
        assert not validate_uscc_format("9133018571131592V0")

    def test_forbidden_char_Z(self):
        assert not validate_uscc_format("9133018571131592Z0")


class TestUsccChecksum:
    """validate_uscc_checksum · GB 32100-2015 真校验码."""

    def test_valid_checksum_tencent(self):
        # 腾讯科技 (深圳) 有限公司 · 公开 USCC (NECIPS 可查)
        assert validate_uscc_checksum("91440300708461136T")

    def test_valid_checksum_algorithm_generated(self):
        # 算法生成的合法 USCC (前缀 + 计算 check char)
        assert validate_uscc_checksum("91330000725930080D")
        assert validate_uscc_checksum("91110000100003962Y")

    def test_invalid_checksum_wrong_check_char(self):
        # 改最后一位 → 校验码不对
        assert not validate_uscc_checksum("91440300708461136X")
        assert not validate_uscc_checksum("91330000725930080W")

    def test_invalid_checksum_wrong_data(self):
        # 改中间数据 → 校验码不一致
        assert not validate_uscc_checksum("91440300708461137T")  # 第 17 位改

    def test_format_failure_returns_false(self):
        # 格式不合 → checksum 直接 False
        assert not validate_uscc_checksum("invalid")
        assert not validate_uscc_checksum("")
        assert not validate_uscc_checksum("9133")

    def test_lowercase_normalized(self):
        # 小写应 upper · 校验码不变
        assert validate_uscc_checksum("91440300708461136t")


class TestValidateUsccDispatcher:
    """validate_uscc 顶层 · default 仅格式 · strict=True 启用校验码."""

    def test_default_format_only(self):
        # 默认仅格式 (向下兼容旧调用)
        assert validate_uscc("91330185711315925G")  # 格式合法 · 但校验码可能不对
        assert validate_uscc("91440300708461136T")  # 格式 + 校验码都合法

    def test_strict_requires_checksum(self):
        assert validate_uscc("91440300708461136T", strict=True)
        # 格式合法但校验码不对 → strict=False True · strict=True False
        assert validate_uscc("91330185711315925G", strict=False)
        assert not validate_uscc("91330185711315925G", strict=True)


class TestNormalizeCompanyName:
    """公司名规则化清洗."""

    def test_remove_company_suffix(self):
        assert normalize_company_name("海潮工业软件有限公司") == "海潮工业软件"
        assert normalize_company_name("阿里巴巴集团") == "阿里巴巴"
        assert normalize_company_name("腾讯控股有限责任公司") == "腾讯控股"

    def test_remove_province_prefix(self):
        assert normalize_company_name("杭州海康威视数字技术股份有限公司") == "海康威视数字技术"

    def test_remove_punct(self):
        assert normalize_company_name("海康·威视 (集团) 有限公司") == "海康威视"

    def test_no_change_for_pure_name(self):
        assert normalize_company_name("海康威视") == "海康威视"

    def test_empty_name(self):
        assert normalize_company_name("") == ""
        assert normalize_company_name(None) == ""

    def test_idempotent(self):
        # 多次 normalize 输出稳定
        first = normalize_company_name("(上海) 海潮工业软件有限公司")
        second = normalize_company_name(first)
        assert first == second


class TestResolveEntity:
    """主入口 · USCC 优先 · name fallback."""

    def test_uscc_anchored(self):
        e = resolve_entity(name="杭州海康威视股份有限公司", uscc="91330185711315925G")
        assert e.uscc == "91330185711315925G"
        assert e.name_normalized == "海康威视"
        assert e.confidence == 1.0
        assert e.is_uscc_anchored

    def test_name_only_fallback(self):
        e = resolve_entity(name="海康威视股份有限公司")
        assert e.uscc == ""
        assert e.name_normalized == "海康威视"
        assert e.confidence == 0.5
        assert not e.is_uscc_anchored

    def test_invalid_uscc_fallback_to_name(self):
        e = resolve_entity(name="海康威视有限公司", uscc="invalid")
        assert e.uscc == ""
        assert e.name_normalized == "海康威视"
        assert e.confidence == 0.5

    def test_strict_mode_rejects_bad_checksum(self):
        # strict=True · 格式合法但校验码错 → 退化 name fallback
        e = resolve_entity(
            name="某测试公司有限公司",
            uscc="91330185711315925G",  # 格式合法 · 校验码错
            strict=True,
        )
        assert e.uscc == ""
        assert e.confidence == 0.5

    def test_strict_mode_accepts_real_uscc(self):
        # strict=True · 真 USCC 通过
        e = resolve_entity(
            name="腾讯",
            uscc="91440300708461136T",
            strict=True,
        )
        assert e.uscc == "91440300708461136T"
        assert e.confidence == 1.0

    def test_empty_input(self):
        e = resolve_entity()
        assert e.uscc == ""
        assert e.name_normalized == ""
        assert e.confidence == 0.0


class TestEntityKeyMatching:
    """同一实体判断 (多源去重核心)."""

    def test_same_uscc_matches(self):
        e1 = resolve_entity(name="海康威视", uscc="91330185711315925G")
        e2 = resolve_entity(name="杭州海康威视数字技术股份有限公司", uscc="91330185711315925G")
        assert e1.matches(e2)

    def test_same_name_normalized_matches(self):
        e1 = resolve_entity(name="海康威视有限公司")
        e2 = resolve_entity(name="(杭州)海康威视股份有限公司")
        assert e1.matches(e2)

    def test_different_uscc_not_match(self):
        e1 = resolve_entity(name="海康威视", uscc="91330185711315925G")
        e2 = resolve_entity(name="海康威视", uscc="91110108800049528K")
        assert not e1.matches(e2)

    def test_uscc_anchored_vs_name_only_not_match(self):
        # 谨慎规则: 一边有 USCC 一边没 → 不算 match (宁可重复也不假合并)
        e1 = resolve_entity(name="海康威视", uscc="91330185711315925G")
        e2 = resolve_entity(name="海康威视")
        assert not e1.matches(e2)

    def test_empty_keys_dont_match(self):
        # 空 key 不算 match (避免污染 dedup)
        e1 = EntityKey()
        e2 = EntityKey()
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

    def test_set_dedup_by_key(self):
        # set 去重 · 同 USCC 视作同一 entry
        e1 = EntityKey(uscc="91440300708461136T", name_normalized="腾讯")
        e2 = EntityKey(uscc="91440300708461136T", name_normalized="深圳腾讯")
        assert len({e1, e2}) == 1


class TestMakeUniqueId:
    """make_unique_id · per candidate-identity-contract.md §2."""

    def test_uscc_priority(self):
        # USCC 通过 → uscc_<USCC>
        result = make_unique_id(name="海康威视", uscc="91440300708461136T")
        assert result == "uscc_91440300708461136T"

    def test_uscc_uppercase_normalized(self):
        # 小写 USCC · 应 upper
        result = make_unique_id(name="X", uscc="91440300708461136t")
        assert result == "uscc_91440300708461136T"

    def test_name_md5_when_no_uscc(self):
        # 仅 name → name_<md5前12位>
        result = make_unique_id(name="海康威视")
        assert result.startswith("name_")
        assert len(result) == len("name_") + 12

    def test_name_md5_deterministic(self):
        # 同 name → 同 id (跨 session 稳定)
        a = make_unique_id(name="海康威视股份有限公司")
        b = make_unique_id(name="(杭州) 海康威视股份有限公司")
        # normalize 后 name 相同 → md5 相同
        assert a == b

    def test_idx_fallback(self):
        # 都没 → cand_<idx:03d>
        assert make_unique_id(idx=0) == "cand_000"
        assert make_unique_id(idx=5) == "cand_005"
        assert make_unique_id(idx=999) == "cand_999"

    def test_invalid_uscc_falls_to_name(self):
        # USCC 非法 → name fallback
        result = make_unique_id(name="海康威视", uscc="invalid")
        assert result.startswith("name_")

    def test_strict_uscc_rejects_bad_checksum(self):
        # strict=True · 格式合法但校验码错 → name fallback
        result = make_unique_id(
            name="某公司",
            uscc="91330185711315925G",  # 格式合法 · 校验码错
            strict=True,
        )
        assert result.startswith("name_")

    def test_empty_inputs_uses_idx(self):
        # 空 name + 空 uscc + idx → cand_<idx>
        assert make_unique_id(idx=3) == "cand_003"

    def test_unique_within_list(self):
        # 模拟 5 候选 list · 各自 id unique
        candidates = [
            ("腾讯", "91440300708461136T", 0),
            ("阿里巴巴", "", 1),
            ("", "", 2),
            ("百度", "invalid", 3),
            ("华为", "", 4),
        ]
        ids = [make_unique_id(name=n, uscc=u, idx=i) for n, u, i in candidates]
        assert len(set(ids)) == 5  # 全 unique


class TestCrossSourceDedup:
    """端到端: 多源 candidate 合并去重场景."""

    def test_dedup_three_sources_same_company(self):
        # 同一公司 · 3 源 (gsxt / Tavily / 微信) · 名字略有不同
        gsxt = resolve_entity(
            name="腾讯科技(深圳)有限公司",
            uscc="91440300708461136T",
        )
        tavily = resolve_entity(
            name="深圳腾讯",
            uscc="91440300708461136T",
        )
        wechat = resolve_entity(name="腾讯")  # 仅 name 无 USCC

        # gsxt + tavily 同 USCC → match
        assert gsxt.matches(tavily)
        # wechat 仅 name · 谨慎规则 → 不 match (宁可不合并)
        assert not gsxt.matches(wechat)

    def test_dedup_set_collapses_to_one(self):
        # 用 set 自动去重 · 5 条记录 · 同 USCC
        records = [
            resolve_entity(name=n, uscc="91440300708461136T")
            for n in ["腾讯", "腾讯控股", "腾讯科技", "深圳腾讯", "Tencent"]
        ]
        unique_keys = set(records)
        assert len(unique_keys) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
