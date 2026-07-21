# -*- coding: utf-8 -*-
"""V16 placeholder render-smoke 端到端测试 · Codex R2 R2.2 防御.

为什么这个测试存在 (背景 · Codex R2 抓的最高优先级):
  - lint exit 0 只证明 byte-level diff 无 leak · 不证明 rendered docx 干净
  - 用户看的是 rendered docx · 如果 client_metadata 缺 key · placeholder 会以
    `{{KEY}}` 字面残留 或 整段被 keep 成"未能自动填写"残缺 · 这就是 dogfooding fail
  - 第三次 dogfooding 之前 · 必须有 render-smoke 防御层 · 跑生成→extract→断言全链路

测试范围 (8 个 fixture):
  - 5 个 DP00X sample (data/mock/deep-pillar/DP00X/client_metadata.json · flat dict)
  - 3 个 corp scenarios (data/mock/workspace/credit/scenarios/corp-*.json ·
    client_metadata 嵌在外层 dict)
  - 模板固定用 samples/经纬测绘_对公成稿A.docx (已 placeholder 化的对公模板)

实现策略 (不依赖 LLM):
  1. extract_elements 从 docx 抽全量 element
  2. 对每个含 {{KEY}} 的 element · 跑 placeholder_replace handler (REPLACE/PLACEHOLDER)
     · 不跑 REWRITE/FILL handler (那些需 LLM)
  3. 收集 rendered 文本 · 断言 3 件事:
     a) 无旧客户字面 (经纬数字科技 / 郑志煌 / 5000万元 / 3375万元 等)
     b) 无裸 placeholder · 允许白名单 key (例如部分 fixture 没有母公司)
     c) 新客户名能命中 rendered 文本

约束:
  - 不调 DeepSeek/LLM · 纯确定性 handler 路径
  - 不动现有代码 · 只新加本文件
  - 8 case 各自必 PASS · 或 fail 时明确报缺什么 key / 漏什么 placeholder
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

# repo 根入 sys.path · 允许 import v16 模块 (tests/integration/ 在两层下)
REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from v16_generator import Classification, Materials  # noqa: E402
from v16_op_handlers import placeholder_replace  # noqa: E402
from v16_step1_extract import extract_elements  # noqa: E402


# ─────────────────────────────────────────────────────────────
# Fixtures · 8 个 client_metadata 来源
# ─────────────────────────────────────────────────────────────

# DP00X 是 flat dict (整个 json 就是 client_metadata)
# corp scenarios 是 nested (client_metadata 在外层 dict 的一个 key)
FIXTURES = [
    # DP00X sample
    ("DP001_龙峰精工", REPO / "data/mock/deep-pillar/DP001_龙峰精工/client_metadata.json"),
    ("DP002_蓝汀家电", REPO / "data/mock/deep-pillar/DP002_蓝汀家电/client_metadata.json"),
    ("DP003_宸星家装", REPO / "data/mock/deep-pillar/DP003_宸星家装/client_metadata.json"),
    ("DP004_汇德建材", REPO / "data/mock/deep-pillar/DP004_汇德建材/client_metadata.json"),
    ("DP005_星胤实业", REPO / "data/mock/deep-pillar/DP005_星胤实业/client_metadata.json"),
    # Corp scenarios (nested client_metadata)
    ("corp-dingsheng-001", REPO / "data/mock/workspace/credit/scenarios/corp-dingsheng-001.json"),
    ("corp-ruiheng-002", REPO / "data/mock/workspace/credit/scenarios/corp-ruiheng-002.json"),
    ("corp-zhongrui-003", REPO / "data/mock/workspace/credit/scenarios/corp-zhongrui-003.json"),
]

TEMPLATE_DOCX = REPO / "samples" / "经纬测绘_对公成稿A.docx"

# Placeholder 正则 (与 v16_op_handlers._PLACEHOLDER_KEY_RE 一致)
PLACEHOLDER_RE = re.compile(r"\{\{([A-Z][A-Z0-9_]{1,40})\}\}")

# 旧客户字面词清单 (从 samples/经纬测绘_对公成稿A.metadata.json original_client 拉)
# 这些是模板 placeholder 化前的真实客户文字 · 替换后绝对不应出现
# 2026-05-21 P1 fix · 移除纯数字串 (5000万元 / 3375万元 / 3000万元)
#   - 数字字符串太宽 · DP005 CREDIT_PERIOD="一年(项目贷展期3000万元另议)" 是合法业务表达
#   - 改用专名 (郑志煌 / 福建省招标采购集团 / 195,000.00万元 注册资本) 唯一识别旧客户
OLD_CLIENT_LITERALS = [
    "福建经纬数字科技信息有限公司",
    "经纬数字科技",
    "郑志煌",  # 经纬法人 · 专名 · 不会跟其他客户重叠
    "福建省招标采购集团",  # 经纬母公司 · 专名前缀
    "招标股份",
    "招标采购集团",
    "兴业资产管理有限公司",
    "兴业国信资产管理",
    "195,000.00万元",  # 兴业注册资本特定字符串 · 不会跟 DP00X 重叠
]

# 白名单 — 允许 pending 残留的 placeholder key
# (DP00X / corp scenarios 不一定都有母公司 / 集团 / 关联方 · 这些 key 没填属于业务正常)
PENDING_WHITELIST = {
    "CLIENT_PARENT_FULL_NAME",
    "CLIENT_GROUP_FULL_NAME",
    "CLIENT_PARENT_SHORT_NAME",
    "CLIENT_GROUP_SHORT_NAME",
    "CLIENT_LONG_CORE_NAME",
    "RELATED_PARTY_1_FULL_NAME",
    "RELATED_PARTY_2_FULL_NAME",
}


def _load_client_metadata(metadata_path: Path) -> tuple[dict, str | None]:
    """加载 fixture 的 client_metadata · 返回 (metadata, new_client_name).

    支持 3 种 fixture 格式 (2026-05-21 C 档第 1 步 升级):
      a) 3 section nested (Phase C 后): {client_metadata: {...}, credit_terms: {...}, material_facts: {...}}
         → merge 成 flat dict 供 placeholder_replace 消费
      b) 旧 nested (corp scenarios 旧格式): {client_metadata: {全 45 key}}
      c) 旧 flat (DP00X 旧格式): {schema_version: ..., CLIENT_FULL_NAME: ..., ...}

    placeholder_replace handler (v16_op_handlers._lookup_metadata_value) 同时支持 flat dict
    和 nested · 这里 merge 后传 flat 是为了兼容 handler 的 alias_map fallback (需要 flat 顶层 key).
    """
    raw = json.loads(metadata_path.read_text(encoding="utf-8"))

    # 检测 3 section nested 结构 (Phase C 后的格式)
    has_three_section = (
        isinstance(raw.get("client_metadata"), dict)
        and isinstance(raw.get("credit_terms"), dict)
        and isinstance(raw.get("material_facts"), dict)
    )

    if has_three_section:
        # a) 3 section nested → merge to flat dict (保留 _sections 子结构给 handler 二级查找)
        merged: dict = {}
        for section in ("material_facts", "credit_terms", "client_metadata"):
            sub = raw.get(section)
            if isinstance(sub, dict):
                merged.update(sub)
        merged["_sections"] = {
            s: dict(raw.get(s, {})) for s in ("client_metadata", "credit_terms", "material_facts")
        }
        client_metadata = merged
        new_client_name = (
            merged.get("CLIENT_FULL_NAME")
            or raw.get("profile", {}).get("company_name")
        )
    elif "client_metadata" in raw and isinstance(raw["client_metadata"], dict):
        # b) 旧 nested · corp scenario 格式
        client_metadata = raw["client_metadata"]
        new_client_name = (
            client_metadata.get("CLIENT_FULL_NAME")
            or raw.get("profile", {}).get("company_name")
        )
    else:
        # c) 旧 flat · DP00X 格式
        client_metadata = raw
        new_client_name = client_metadata.get("CLIENT_FULL_NAME")
    return client_metadata, new_client_name


def _make_classification(loc: str) -> Classification:
    return Classification(
        location=loc,
        op="REPLACE",
        label="PLACEHOLDER",
        confidence=1.0,
        justification="render-smoke · deterministic placeholder pre-pass",
    )


# ─────────────────────────────────────────────────────────────
# Main render-smoke test
# ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("name,metadata_path", FIXTURES, ids=[f[0] for f in FIXTURES])
def test_render_smoke_no_old_client_no_naked_placeholder(name, metadata_path):
    """对每个 fixture 跑 placeholder_replace pipeline · 断言无旧客户字面 + 无裸 {{KEY}}.

    断言:
      a) 无旧客户字面 (经纬 / 兴业 / 5000万元 等)
      b) 无裸 placeholder · 允许 PENDING_WHITELIST 内的 key
      c) 新客户名命中 rendered 文本
    """
    # 0. fixture 文件存在
    assert metadata_path.exists(), f"fixture missing: {metadata_path}"
    assert TEMPLATE_DOCX.exists(), f"template docx missing: {TEMPLATE_DOCX}"

    # 1. 加载 client_metadata
    client_metadata, new_client_name = _load_client_metadata(metadata_path)
    assert client_metadata, f"{name} client_metadata is empty"

    # 2. 抽 element
    elements = extract_elements(TEMPLATE_DOCX)
    assert elements, f"extract_elements returned empty for {TEMPLATE_DOCX}"

    # 3. 构造 Materials (handler 只读 client_metadata)
    mats = Materials(client_metadata=client_metadata)

    # 4. 跑 placeholder_replace pipeline
    #    模拟 v16_generator deterministic regex pre-pass + handler dispatch
    rendered_texts: list[str] = []
    pending_locations: list[tuple[str, str]] = []  # (location, reason)
    for e in elements:
        text = e.text or ""
        if PLACEHOLDER_RE.search(text):
            cls = _make_classification(e.location)
            result = placeholder_replace(e, cls, mats)
            # handler 返回 action=fill 时用 new_text · 否则 (keep/全 miss) 原文
            if result.action == "fill" and result.new_text:
                rendered_texts.append(result.new_text)
            else:
                rendered_texts.append(text)
            if result.pending_tag:
                tags = result.pending_tag if isinstance(result.pending_tag, list) else [result.pending_tag]
                pending_locations.extend(
                    (e.location, tag.get("reason", "")) for tag in tags
                )
        else:
            rendered_texts.append(text)

    full_text = "\n".join(rendered_texts)

    # ─── 断言 a: 无旧客户字面 ───
    leaked_old = [kw for kw in OLD_CLIENT_LITERALS if kw in full_text]
    assert not leaked_old, (
        f"[{name}] render still contains old client literals: {leaked_old}\n"
        f"提示: 模板 placeholderize 不完整 · 或 client_metadata 把旧值再次写回"
    )

    # ─── 断言 b: 无裸 placeholder (白名单外) ───
    naked = PLACEHOLDER_RE.findall(full_text)
    leaked_naked = sorted(set(k for k in naked if k not in PENDING_WHITELIST))
    if leaked_naked:
        # 收集每个 leak key 在 metadata 里是否存在 · 帮 user 决策"补 key" vs "改白名单"
        leak_diag = []
        for k in leaked_naked:
            in_meta = k in client_metadata
            in_meta_lower = k.lower() in client_metadata
            leak_diag.append(f"{k} (in_metadata={in_meta} · lower={in_meta_lower})")
        assert False, (
            f"[{name}] leaked naked placeholders (白名单外): {leaked_naked}\n"
            f"诊断: {leak_diag}\n"
            f"决策: 给 client_metadata 补这些 key · 或加入 PENDING_WHITELIST (业务允许 pending)"
        )

    # ─── 断言 c: 新客户名命中 ───
    assert new_client_name, f"{name} fixture 未提供 CLIENT_FULL_NAME / company_name"
    assert new_client_name in full_text, (
        f"[{name}] new client name {new_client_name!r} not in rendered text\n"
        f"提示: placeholder_replace 未把 {{{{CLIENT_FULL_NAME}}}} 替换为 metadata 实值 · "
        f"检查 metadata['CLIENT_FULL_NAME'] = {client_metadata.get('CLIENT_FULL_NAME')!r}"
    )


# ─────────────────────────────────────────────────────────────
# Sanity check · 模板本身确实是 placeholder 化的 (前置条件)
# ─────────────────────────────────────────────────────────────


def test_template_is_placeholderized():
    """前置条件 · 模板 docx 必须含 ≥10 个 {{KEY}} placeholder · 否则不是治本 Phase 2 产物."""
    assert TEMPLATE_DOCX.exists(), f"template missing: {TEMPLATE_DOCX}"
    elements = extract_elements(TEMPLATE_DOCX)
    total_placeholders = 0
    unique_keys: set[str] = set()
    for e in elements:
        for m in PLACEHOLDER_RE.finditer(e.text or ""):
            total_placeholders += 1
            unique_keys.add(m.group(1))
    assert total_placeholders >= 10, (
        f"template {TEMPLATE_DOCX.name} 只有 {total_placeholders} 个 placeholder · "
        f"看起来未 placeholderize · render-smoke 失去意义"
    )
    assert "CLIENT_FULL_NAME" in unique_keys, (
        f"template 必须含 CLIENT_FULL_NAME placeholder · got: {sorted(unique_keys)}"
    )
