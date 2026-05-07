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


# ---------------------------------------------------------------------------
# Test 6 · PB#2 守则 3 · prompt 行数 ≤ 220 上限 (per pb2-prompt-governance.md §1)
# ---------------------------------------------------------------------------
class TestPromptLineLimit:
    """6 Agent helper 输出行数必 ≤ 220 · 防 prompt 膨胀重蹈卡兹克 600 行覆辙."""

    PROMPT_LINE_HARD_CAP = 220

    def test_six_agents_within_220_line_cap(self):
        """每 agent helper 输出 ≤ 220 行 · per Codex 守则 3."""
        from shared.prompts.agent_helpers import BUILDERS

        for agent_id, builder in BUILDERS.items():
            prompt = builder()
            line_count = len(prompt.splitlines())
            assert line_count <= self.PROMPT_LINE_HARD_CAP, (
                f"{agent_id} prompt {line_count} 行 > {self.PROMPT_LINE_HARD_CAP} 上限 · "
                f"违反 Codex 守则 3 · 必拆 SSOT 段并删重复约束"
            )

    def test_prompt_with_schema_hint_within_cap(self):
        """schema_hint 注入后仍 ≤ 220 (常规业务 schema 长度)."""
        from shared.prompts.agent_helpers import BUILDERS

        sample_schema = '{"decision": "通过/拒绝/补件", "amount_cny": "数值", "rationale": "解释文字"}'
        for agent_id, builder in BUILDERS.items():
            prompt = builder(schema_hint=sample_schema)
            line_count = len(prompt.splitlines())
            assert line_count <= self.PROMPT_LINE_HARD_CAP, (
                f"{agent_id} with schema_hint {line_count} 行 > {self.PROMPT_LINE_HARD_CAP}"
            )


# ---------------------------------------------------------------------------
# Test 7 · PB#2 守则 1 + 4 · prompt 不含可代码化的"阈值/权重/决策树"
# ---------------------------------------------------------------------------
class TestNoOversteppingPatterns:
    """SSOT helper 输出不应含"如果 A 则 X 否则 Y"决策树 / 具体阈值数字 (这些必在代码)."""

    def test_no_multi_condition_decision_tree(self):
        """守则 4: prompt 不应有"if A then B else if C then D"多条件决策树."""
        from shared.prompts.agent_helpers import build_credit_ssot_prompt

        p = build_credit_ssot_prompt()
        # 决策树措辞示例 (在代码做的事 · 不应进 prompt)
        forbidden_patterns = [
            "如果 A 则",
            "若分数 > 80 则通过",
            "评分 ≥ 750 自动批",
        ]
        for pattern in forbidden_patterns:
            assert pattern not in p, f"prompt 不应含决策树 '{pattern}' (守则 4)"

    def test_no_hardcoded_threshold_in_prompt(self):
        """守则 2: prompt 不应有具体业务阈值 (这些必由 user prompt 输入)."""
        from shared.prompts.agent_helpers import build_credit_ssot_prompt

        p = build_credit_ssot_prompt()
        # 业务阈值数字 (假阴性是 freshness SLA 阈值 · 不算违反 · 那是数据时效不是业务)
        # freshness SLA 是允许的: "新闻 > 180 天" 是 evidence-first 段定义
        # 业务阈值 (e.g. "余额 > 100 万拒绝") 不应在 prompt
        forbidden_business_thresholds = [
            "余额 > 100 万",
            "授信额度 ≤ 500 万",
            "FICO < 600",
        ]
        for pattern in forbidden_business_thresholds:
            assert pattern not in p, f"业务阈值 '{pattern}' 不应在 prompt (守则 2)"


# ---------------------------------------------------------------------------
# Test 8 · PB#2 freshness 语义 fail mode
# ---------------------------------------------------------------------------
class TestFreshnessSemantics:
    """D2 freshness 硬约束语义验证 · 防 PB#2 后退化."""

    def test_freshness_sla_thresholds_present(self):
        """6 Agent prompt 都必含 SLA 阈值 (新闻 180d / 财报 120d / 处罚 365d)."""
        from shared.prompts.agent_helpers import BUILDERS

        for agent_id, builder in BUILDERS.items():
            p = builder()
            assert "180" in p, f"{agent_id} prompt 缺 新闻 SLA 180d"
            assert "120" in p, f"{agent_id} prompt 缺 财报 SLA 120d"
            assert "365" in p, f"{agent_id} prompt 缺 处罚 SLA 365d"

    def test_stale_evidence_degradation_clause(self):
        """所有 agent prompt 都必有"全 stale → 材料不足"降级条款."""
        from shared.prompts.agent_helpers import BUILDERS

        for agent_id, builder in BUILDERS.items():
            p = builder()
            assert "材料不足" in p, f"{agent_id} prompt 缺降级条款"
            assert "降级" in p or "不可给确定性结论" in p, f"{agent_id} prompt 缺降级语义"

    def test_evidence_must_carry_date_field(self):
        """evidence 输入 schema 必含 evidence_date 必填字段."""
        from shared.prompts.agent_helpers import build_alert_ssot_prompt

        p = build_alert_ssot_prompt()
        assert "evidence_date" in p
        assert "ISO 日期" in p or "ISO" in p


# ---------------------------------------------------------------------------
# Test 9 · PB#2 6 agent schema_hint 集成 (per task_type 集成)
# ---------------------------------------------------------------------------
class TestPB2SchemaHintIntegration:
    """PB#2 真接入后 · 6 agent 各自 task_type 应能注入业务 schema."""

    AGENT_TASK_SCHEMA_FIXTURES = [
        ("channel", "profile_extract", "IdealProfile 12 维 JSON"),
        ("credit", "corporate_decision_explain", "决策解释 markdown · 5 节"),
        ("alert", "disposition", "处置建议 80-150 字 · 含立即/一周内/持续关注"),
        ("compliance", "compliance_check", "ComplianceReport pydantic JSON"),
        ("report", "section_generation", "报告章节文本"),
        ("riskctrl", "rule_parse", '{"rules": [{"rule_id", "conditions"}]}'),
    ]

    def test_each_agent_accepts_schema_hint_per_task_type(self):
        """每 agent 每 task_type 都能接受 schema_hint 并 inject 到 output."""
        from shared.prompts.agent_helpers import build_ssot_prompt

        for agent_id, task_type, schema in self.AGENT_TASK_SCHEMA_FIXTURES:
            p = build_ssot_prompt(agent_id, task_type=task_type, schema_hint=schema)
            assert schema in p, f"{agent_id}/{task_type} schema_hint 未 inject"
            assert "本次任务专属 schema" in p, f"{agent_id}/{task_type} schema marker 缺"


# ---------------------------------------------------------------------------
# Test 10 · helper 输入校验
# ---------------------------------------------------------------------------
class TestHelperInputValidation:
    """守则 5: helper 输入参数校验 · 失败 raise · 不静默通过."""

    def test_invalid_agent_id_raises(self):
        from shared.prompts.agent_helpers import build_ssot_prompt
        with pytest.raises(ValueError):
            build_ssot_prompt("nonexistent_agent")

    def test_empty_agent_id_raises(self):
        from shared.prompts.agent_helpers import build_ssot_prompt
        with pytest.raises(ValueError):
            build_ssot_prompt("")


if __name__ == "__main__":
    import sys
    pytest.main([__file__, "-v"] + sys.argv[1:])
