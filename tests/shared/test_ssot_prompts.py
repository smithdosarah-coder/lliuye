"""tests/shared/test_ssot_prompts.py · PB#1 Step 4 验收 (PM 5/7 拍板)

per Phase C grounded report Tier 0+1 验收标准 (Codex R3 final):

验收硬规:
- 6 Agent build_*_ssot_prompt() 全跑通
- 输出含 4 关键 marker (安全合规底线 · 三层信息框架 · 证据新鲜度硬约束 · 输出格式约束)
- output_schema 段含 schema_hint 时附加 · 不含时退化通用规则
- run_date 动态注入 (今日 ISO)
- enforce_implemented=True 不抛 (3 段都已实装)
- 不在 6 列表的 agent_id raise ValueError
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Test 1 · 6 agent build 全跑通
# ---------------------------------------------------------------------------
class TestSSotPromptsAllAgents:
    """6 Agent build_*_ssot_prompt 都返非空 + 含 4 关键段."""

    def test_six_agents_build_ok(self):
        from shared.prompts.agent_helpers import BUILDERS

        for agent_id, builder in BUILDERS.items():
            prompt = builder()
            assert isinstance(prompt, str), f"{agent_id} prompt 非 str"
            assert len(prompt) > 1000, f"{agent_id} prompt 太短 ({len(prompt)})"

    def test_safety_block_present(self):
        from shared.prompts.agent_helpers import build_credit_ssot_prompt
        p = build_credit_ssot_prompt()
        assert "安全合规底线" in p
        assert "PIPL" in p or "合规红线" in p
        assert "适当性销售" in p
        assert "不编造" in p

    def test_evidence_first_block_present(self):
        from shared.prompts.agent_helpers import build_credit_ssot_prompt
        p = build_credit_ssot_prompt()
        assert "三层信息框架" in p
        assert "材料事实" in p
        assert "行业上下文" in p
        assert "分析推断" in p

    def test_evidence_freshness_hard_constraint(self):
        """Track D · D2 freshness 硬约束 · per Codex R2 给文本."""
        from shared.prompts.agent_helpers import build_alert_ssot_prompt
        p = build_alert_ssot_prompt()
        assert "证据新鲜度硬约束" in p
        assert "evidence_date" in p
        assert "新闻 > 180" in p or "180 天" in p
        assert "材料不足" in p

    def test_output_schema_block_present(self):
        from shared.prompts.agent_helpers import build_report_ssot_prompt
        p = build_report_ssot_prompt(schema_hint='{"decision": "..."}')
        assert "输出格式约束" in p
        assert "JSON" in p or "json" in p
        assert "未能自动填写" in p


# ---------------------------------------------------------------------------
# Test 2 · run_date 动态
# ---------------------------------------------------------------------------
class TestRunDate:
    def test_run_date_default_today(self):
        """默认 run_date = 今日."""
        from datetime import date
        from shared.prompts.agent_helpers import build_credit_ssot_prompt

        p = build_credit_ssot_prompt()
        today = date.today().isoformat()
        assert today in p, f"今日 {today} 应在 prompt"

    def test_run_date_explicit(self):
        from shared.prompts.agent_helpers import build_credit_ssot_prompt
        p = build_credit_ssot_prompt(run_date="2026-01-15")
        assert "2026-01-15" in p


# ---------------------------------------------------------------------------
# Test 3 · enforce + agent_id 校验
# ---------------------------------------------------------------------------
class TestEnforceAndValidation:
    def test_enforce_implemented_passes(self):
        """3 段实装 (safety / evidence-first / output-schema) · enforce 不抛."""
        from shared.prompts.agent_helpers import build_credit_ssot_prompt
        # 默认 enforce_implemented=True · 不抛
        p = build_credit_ssot_prompt()
        assert isinstance(p, str)

    def test_unknown_agent_id_raises(self):
        from shared.prompts.agent_helpers import build_ssot_prompt
        with pytest.raises(ValueError, match="unknown agent_id"):
            build_ssot_prompt("unknown_agent")

    def test_six_canonical_agents(self):
        """6 个 canonical agent_id."""
        from shared.prompts.agent_helpers import BUILDERS
        assert set(BUILDERS) == {
            "channel", "credit", "alert", "compliance", "report", "riskctrl",
        }


# ---------------------------------------------------------------------------
# Test 4 · schema_hint 注入
# ---------------------------------------------------------------------------
class TestSchemaHint:
    def test_no_schema_hint_short_output_block(self):
        from shared.prompts.agent_helpers import build_credit_ssot_prompt
        p = build_credit_ssot_prompt()
        # 通用规则 必在
        assert "JSON 优先" in p

    def test_with_schema_hint_appended(self):
        from shared.prompts.agent_helpers import build_credit_ssot_prompt
        custom_schema = '{"approval": "通过/拒绝/补件", "amount_cny": "数值"}'
        p = build_credit_ssot_prompt(schema_hint=custom_schema)
        assert custom_schema in p
        assert "本次任务专属 schema" in p


# ---------------------------------------------------------------------------
# Test 5 · contract.assemble pending sections (后 5 段 placeholder · skip OK)
# ---------------------------------------------------------------------------
class TestPendingSections:
    def test_implemented_sections_in_output(self):
        """后 5 段 (agent-role/tool-use/self-check/few-shot/eval-hook) 仍 placeholder · 必 skip · 不进 output."""
        from shared.prompts.agent_helpers import build_credit_ssot_prompt
        p = build_credit_ssot_prompt()
        # placeholder marker 不应 在 output 中
        assert "_PENDING_A1_SPEC" not in p
        assert "[PENDING worker-A1 spec" not in p

    def test_pending_section_not_blocking_when_not_enforced(self):
        """enforce_implemented=False 时 · 全 8 段 placeholder 都 skip · 不抛."""
        from shared.prompts.agent_helpers import build_credit_ssot_prompt
        p = build_credit_ssot_prompt(enforce_implemented=False)
        # 仍包含已实装 3 段
        assert "安全合规底线" in p
        assert "三层信息框架" in p


if __name__ == "__main__":
    import sys
    pytest.main([__file__, "-v"] + sys.argv[1:])
