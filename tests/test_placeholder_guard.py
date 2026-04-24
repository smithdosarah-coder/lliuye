# -*- coding: utf-8 -*-
"""shared.qc.placeholder_guard 5-Agent QC blocker 验证 (Task B)

每个非 Agent6 智能体（channel/credit/alert/compliance/riskctrl）暴露的
output_validator.validate_text 必须:
  1. 对干净文本静默通过 (无误报)
  2. 对带占位符的输出抛 PlaceholderViolation (硬阻断)

外加 placeholder_guard 自身覆盖 7 类残留模式 + soft_clean 替换为
"未能自动填写" 标记。
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from shared.qc import (
    PlaceholderViolation,
    assert_clean,
    is_clean,
    mark_unfilled,
    scan,
)


# ---------- placeholder_guard 自身规则覆盖 ----------

@pytest.mark.parametrize("snippet, kind", [
    ("企业名: [待补充], 行业 …", "bracket_zh"),
    ("企业名: {{company_name}} 注册资本 100 万", "mustache"),
    ("评分 {composite_score} / 100", "fstring"),
    ("担保方式: <占位>, 评级 A", "angle_zh"),
    ("营收同比……上升", "ellipsis"),
    ("这是一段话, 暂无, 等候补充", "zh_unfilled"),
])
def test_each_pattern_kind_is_caught(snippet: str, kind: str):
    hits = scan(snippet)
    kinds = {h.kind for h in hits}
    assert kind in kinds, f"missing kind={kind}, got={kinds}, snippet={snippet!r}"


def test_clean_text_passes():
    text = "众智达科技综合评分 78 分, B 级, 建议批准 800 万元、24 个月。"
    assert is_clean(text)
    assert scan(text) == []
    assert_clean(text, agent="probe")  # 不抛


def test_assert_clean_blocks_with_violation():
    with pytest.raises(PlaceholderViolation) as ei:
        assert_clean("企业 [待补充] 评分 {{score}}", agent="probe")
    assert ei.value.agent == "probe"
    assert len(ei.value.hits) >= 2


def test_mark_unfilled_replaces_inline():
    out = mark_unfilled("企业 [待补充] 评分 {{score}}")
    assert "[待补充]" not in out
    assert "{{score}}" not in out
    assert out.count("未能自动填写") == 2


# ---------- 5 Agent uniform validate_text 入口 ----------

AGENT_VALIDATORS = (
    ("agent_channel", "agent_channel.output_validator"),
    ("agent_credit", "agent_credit.output_validator"),
    ("agent_alert", "agent_alert.output_validator"),
    ("agent_compliance", "agent_compliance.output_validator"),
    ("agent_riskctrl", "agent_riskctrl.output_validator"),
)


@pytest.mark.parametrize("agent, modpath", AGENT_VALIDATORS)
def test_agent_validator_blocks_placeholder(agent: str, modpath: str):
    """每个 Agent 的 validate_text 在命中占位符时必须抛 PlaceholderViolation。"""
    import importlib
    mod = importlib.import_module(modpath)
    mock_dirty = (
        f"【{agent} 输出】\n"
        "客户: [待补充]\n"
        "建议额度: {{amount}} 万元\n"
        "处置: <占位>\n"
        "理由: 暂无, 等候补充"
    )
    with pytest.raises(mod.PlaceholderViolation) as ei:
        mod.validate_text(mock_dirty)
    assert ei.value.agent == mod.AGENT
    # 至少 4 类命中 (bracket_zh / mustache / angle_zh / zh_unfilled)
    assert len(ei.value.hits) >= 4


@pytest.mark.parametrize("agent, modpath", AGENT_VALIDATORS)
def test_agent_validator_passes_clean(agent: str, modpath: str):
    """正常输出不应误报。"""
    import importlib
    mod = importlib.import_module(modpath)
    clean = f"【{agent}】 一切正常, 无残留, 评分 92 分。"
    mod.validate_text(clean)  # 不抛
    cleaned, hits = mod.soft_clean({"text": clean, "score": 92})
    assert hits == []
    assert cleaned == {"text": clean, "score": 92}


@pytest.mark.parametrize("agent, modpath", AGENT_VALIDATORS)
def test_agent_soft_clean_marks_dirty_dict(agent: str, modpath: str):
    """soft_clean 在 dict 嵌套结构中替换占位符为标记, 命中类型记录在第二个返回值。"""
    import importlib
    mod = importlib.import_module(modpath)
    payload = {
        "headline": "客户 [待补充] 触发预警",
        "metrics": {"amount": "{{amount}}", "rule": "policy ID-09"},
        "tags": ["normal", "<占位>"],
    }
    cleaned, hits = mod.soft_clean(payload)
    assert hits, "soft_clean 必须报告命中"
    assert "未能自动填写" in cleaned["headline"]
    assert cleaned["metrics"]["amount"] == "未能自动填写"
    assert cleaned["metrics"]["rule"] == "policy ID-09"  # 不误伤
    assert "未能自动填写" in cleaned["tags"][1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
