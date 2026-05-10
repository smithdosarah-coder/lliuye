# -*- coding: utf-8 -*-
"""Phase B.2 (PM 2026-05-10) §9 evidence drawer 真 wire guard tests.

硬规 (per dispatch §不可 GO):
  - fixtures.ts 任何 import = REJECT
  - grep CHANNEL_EVIDENCE 0 命中 (active import 0 命中 · 注释/历史可保留)
  - live 数据触发 (sessionData.signals → EvidenceItem)

Phase B.2 落实路径:
  - ChannelWorkspace.tsx 不 import CHANNEL_EVIDENCE
  - EvidenceProvider items 从 sessionData.signals 派生 (useMemo)
  - fixtures.ts CHANNEL_EVIDENCE export 退化为空 list (无消费者 · 留 export 给 grep 工具友好)
"""
from __future__ import annotations

from pathlib import Path


CHANNEL_WORKSPACE = (
    Path(__file__).resolve().parents[2]
    / "web" / "src" / "app" / "archive" / "channel"
    / "_components" / "ChannelWorkspace.tsx"
)
FIXTURES = (
    Path(__file__).resolve().parents[2]
    / "web" / "src" / "components" / "evidence" / "fixtures.ts"
)


def test_channel_workspace_no_fixtures_import():
    """ChannelWorkspace 不 import CHANNEL_EVIDENCE / 任何 fixtures.ts export."""
    src = CHANNEL_WORKSPACE.read_text(encoding="utf-8")
    # active import 模式 (顶层 import) · 注释/docstring 不算
    import_lines = [l for l in src.split("\n") if l.strip().startswith("import ")]
    for line in import_lines:
        assert "CHANNEL_EVIDENCE" not in line, (
            f"Phase B.2 §9 · ChannelWorkspace 禁 import CHANNEL_EVIDENCE: {line.strip()}"
        )
        assert "evidence/fixtures" not in line, (
            f"Phase B.2 §9 · ChannelWorkspace 禁 import evidence/fixtures: {line.strip()}"
        )


def test_channel_workspace_uses_live_evidence_items():
    """ChannelWorkspace EvidenceProvider items 必从 live 数据派生 · 不空数组硬编."""
    src = CHANNEL_WORKSPACE.read_text(encoding="utf-8")
    # 验 useMemo 派生 liveEvidenceItems · 走 sessionData.signals
    assert "liveEvidenceItems" in src, (
        "Phase B.2 §9 · 必有 liveEvidenceItems useMemo · live 数据派生 EvidenceItem"
    )
    assert "sessionData.signals" in src, (
        "Phase B.2 §9 · liveEvidenceItems 必从 sessionData.signals 派生"
    )
    # EvidenceProvider 调用 items={liveEvidenceItems}
    assert "items={liveEvidenceItems}" in src, (
        "Phase B.2 §9 · EvidenceProvider items prop 必 wire liveEvidenceItems"
    )


def test_fixtures_channel_evidence_is_empty_no_hardcoded_summary():
    """fixtures.ts CHANNEL_EVIDENCE 必空 (无 "福鼎明辉" / 假 ref_id 残留)."""
    src = FIXTURES.read_text(encoding="utf-8")
    # 锁 CHANNEL_EVIDENCE block · 不允许硬编案例
    block_start = src.find("export const CHANNEL_EVIDENCE")
    assert block_start > 0, "CHANNEL_EVIDENCE export 应仍存在 (兼容 grep · 留空 list)"
    block_end = src.find("export const ", block_start + 1)
    if block_end < 0:
        block_end = len(src)
    block = src[block_start:block_end]
    # 历史 fixture 含 "福鼎明辉" / "F5189" / "地铁配件" / "ch_ev_*" hardcoded · 必删
    bad_tokens = ["福鼎明辉", "F5189", "地铁配件订单", "ch_ev_uscc_001", "ch_ev_tax_003"]
    for tok in bad_tokens:
        assert tok not in block, (
            f"Phase B.2 §9 · CHANNEL_EVIDENCE 内 hardcoded 假证据 残留: {tok!r}"
        )
    # items: [] 空 list (允许多行格式)
    assert "items: []" in block.replace(" ", "").replace("\n", "") or "items:[]" in block.replace(
        " ", ""
    ), (
        f"Phase B.2 §9 · CHANNEL_EVIDENCE.items 必空 list · 当前: {block[:200]!r}"
    )
