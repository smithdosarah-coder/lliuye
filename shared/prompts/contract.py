# -*- coding: utf-8 -*-
"""shared.prompts.contract — 8 段 LLM prompt template (M7 of 9).

Phase A worker-A2 · 2026-04-29 · skeleton.

**Status: PENDING worker-A1 spec**

  本模块是 docs/contracts/llm-prompt-contract.md (worker-A1 deliverable) 的 Python
  实装. A1 worker 与本 worker 并行 · 本模块先建骨架 + 占位 marker · A1 spec
  ratify 后再 fill 8 段实际 prompt 文本.

  PM 拍板 5 (RESET_MASTER_PLAN.md §4) · "命名 SSOT 词典 8 列" 同期 · contract.py
  consume A1 8 段 spec.

  当前所有 *_block() 函数返回 _PENDING_A1_SPEC marker · assemble() 拼接 8 段时
  跳过 marker · 返回空 prompt body (caller 必须显式 override 各 block · OR 等
  A1 spec landed).

8 段 (per onboarding A2-shared-infra.md §1 表 row 3):
  1. safety              · PIPL / 银保监合规底线 / 不输出 PII / 不编造
  2. evidence-first      · 三层信息框架 (材料事实 / 行业上下文 / 分析推断)
  3. agent-role          · 6 agent 各自角色 + 业务边界
  4. tool-use            · 工具调用规范 (function calling schema · 何时调)
  5. output-schema       · 输出格式约束 (JSON schema / 自然语言结构)
  6. self-check          · 自审 checklist (数字溯源 / 占位符 / 矛盾)
  7. few-shot            · 反馈飞轮历史样本注入 (data/feedback/extracted/)
  8. evaluation-hook     · 与 evaluation/agent_*.yaml metric 对齐的内部 hook

API (skeleton stable · 实现待 A1):
  safety_block()                                  · → str
  evidence_first_block()                          · → str
  agent_role_block(role: str)                     · → str
  tool_use_block(tools: list[dict] | None = None) · → str
  output_schema_block(schema_hint: str = "")      · → str
  self_check_block()                              · → str
  few_shot_block(examples: list[dict] | None = None, max_n: int = 3) · → str
  evaluation_hook_block(eval_id: str = "")        · → str
  assemble(role: str, tools=None, schema_hint="", examples=None, eval_id="",
           strict=False) · → str
       strict=True 时若任一 section 仍是 _PENDING_A1_SPEC 抛 PendingA1SpecError.

Migration path (A4 worker 后续迁 · 6 agent 后续走 contract.assemble):
  · root prompts.py:AGENT_SYSTEM_PROMPT     → contract.assemble(role="agent6_report")
  · agent_channel/prompts.py:PITCH_GEN_SYSTEM → contract.assemble(role="agent1_channel_pitch")
  · agent_alert/prompts.py:SYSTEM_RISK_SCAN  → contract.assemble(role="agent4_alert_scan")
  · 同理 6 agent 全部 prompts.py
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Sentinel + Error
# ---------------------------------------------------------------------------

# Marker · A1 spec 落地前 · 各 *_block() 默认返回此值
_PENDING_A1_SPEC: str = "[PENDING worker-A1 spec · docs/contracts/llm-prompt-contract.md]"


class PendingA1SpecError(RuntimeError):
    """assemble(strict=True) 时 · 任一 section 仍是 placeholder · 显式抛.

    A4 worker 在迁 agent prompts 时若已切到本 contract · 应 strict=True 防回退.
    """


# ---------------------------------------------------------------------------
# 8 段 (skeleton)
# ---------------------------------------------------------------------------


def safety_block() -> str:
    """Section 1 of 8 · safety / PIPL / 银保监合规底线 / 不输出 PII / 不编造.

    Source-of-truth (待 A1 ratify):
      · CLAUDE.md §3.1 反模式 · 红线
      · docs/reset/north-star.md §3 修正方向
      · docs/contracts/llm-prompt-contract.md §1 (worker-A1 起草)

    Returns:
        str · A1 spec landed 前返 _PENDING_A1_SPEC marker.
    """
    # TODO(worker-A1): docs/contracts/llm-prompt-contract.md §1 ratify 后 fill
    return _PENDING_A1_SPEC


def evidence_first_block() -> str:
    """Section 2 of 8 · evidence-first 三层信息框架.

    Source-of-truth:
      · CLAUDE.md §3.3 Evidence-First Protocol
      · root prompts.py:_DATA_CITATION_RULES (现有 evidence-first 实装 · 仅 Agent6)
      · docs/contracts/llm-prompt-contract.md §2 (worker-A1 起草)

    Returns:
        str · A1 spec landed 前返 _PENDING_A1_SPEC marker.
    """
    # TODO(worker-A1): 三层信息框架 (材料事实 / 行业上下文 / 分析推断) ratify 后 fill
    return _PENDING_A1_SPEC


def agent_role_block(role: str) -> str:
    """Section 3 of 8 · agent-role 角色定义 + 业务边界.

    Args:
        role:  agent 标识 · e.g. "agent6_report" / "agent1_channel_pitch" /
               "agent4_alert_scan" / ... (与 8-列 SSOT 词典对齐 · worker-A1 spec)

    Source-of-truth:
      · CLAUDE.md §4 6 Agent 功能边界
      · docs/contracts/agent-naming-ssot.md (worker-A1 deliverable · 8 列 · agent_id 列)
      · docs/contracts/llm-prompt-contract.md §3 (worker-A1 起草)

    Returns:
        str · A1 spec landed 前返 _PENDING_A1_SPEC marker (含 role 标记便于 debug).
    """
    # TODO(worker-A1): 8 列 SSOT 词典 ratify 后按 role 取角色描述
    return f"{_PENDING_A1_SPEC} (role={role!r})"


def tool_use_block(tools: list[dict] | None = None) -> str:
    """Section 4 of 8 · tool-use function calling 规范.

    Args:
        tools:  list[dict] · OpenAI tool schema · 空则不输出 tool 段.

    Source-of-truth:
      · llm.LLMClient.chat tools kwarg 现有 OpenAI function calling
      · docs/contracts/llm-prompt-contract.md §4 (worker-A1 起草)

    Returns:
        str · A1 spec landed 前返 _PENDING_A1_SPEC marker · tools 空时返空串.
    """
    if not tools:
        return ""
    # TODO(worker-A1): 工具调用规范 (何时调 / 何时不调 / 参数校验) ratify 后 fill
    return _PENDING_A1_SPEC


def output_schema_block(schema_hint: str = "") -> str:
    """Section 5 of 8 · output-schema 输出格式约束.

    Args:
        schema_hint:  JSON schema 描述 / 示例 · 空则不输出 schema 段.

    Source-of-truth:
      · shared/llm_caller/prompts.py:with_json_schema_hint (现有 string utility)
      · docs/contracts/llm-prompt-contract.md §5 (worker-A1 起草)

    Returns:
        str · A1 spec landed 前返 _PENDING_A1_SPEC marker · schema_hint 空时返空串.
    """
    if not schema_hint:
        return ""
    # TODO(worker-A1): JSON schema 注入 + non-supports_json_mode provider 兜底规范
    return _PENDING_A1_SPEC


def self_check_block() -> str:
    """Section 6 of 8 · self-check 自审 checklist.

    Source-of-truth:
      · root prompts.py:SELF_REFLECT_PROMPT (现有 Agent6 自审 · 6 项 checklist)
      · CLAUDE.md §3.3 三阶段 (证据 / 撰写 / 自审)
      · docs/contracts/llm-prompt-contract.md §6 (worker-A1 起草)

    Returns:
        str · A1 spec landed 前返 _PENDING_A1_SPEC marker.
    """
    # TODO(worker-A1): 跨 6 agent 通用的 self-check 6 项 ratify 后 fill
    return _PENDING_A1_SPEC


def few_shot_block(
    examples: list[dict] | None = None,
    max_n: int = 3,
) -> str:
    """Section 7 of 8 · few-shot 反馈飞轮历史样本.

    Args:
        examples:  list[dict] · {input, output, reason?} 形态 · 空则不输出 few-shot 段.
        max_n:     最多注入条数

    Source-of-truth:
      · root prompts.py:get_feedback_fewshot_block (Agent6 现有 fewshot 注入)
      · agent_channel/prompts.py:render_fewshot_block (Agent1 现有 fewshot 注入)
      · CLAUDE.md §6 数据飞轮 第 4 环
      · docs/contracts/llm-prompt-contract.md §7 (worker-A1 起草)

    Returns:
        str · A1 spec landed 前返 _PENDING_A1_SPEC marker · examples 空时返空串.
    """
    if not examples:
        return ""
    # TODO(worker-A1): 跨 6 agent 通用 few-shot 注入格式 ratify 后 fill
    return _PENDING_A1_SPEC


def evaluation_hook_block(eval_id: str = "") -> str:
    """Section 8 of 8 · evaluation-hook 与 evaluation/agent_*.yaml 对齐.

    Args:
        eval_id:  evaluation/agent_*.yaml id · e.g. "agent6_report" · 空不输出.

    Source-of-truth:
      · evaluation/*.yaml metric 名集合 (field_completeness / evidence_rate /
         hallucination_rate / tool_success_rate / task_completion_rate)
      · CLAUDE.md §5 评估框架双轨制
      · docs/contracts/llm-prompt-contract.md §8 (worker-A1 起草)

    Returns:
        str · A1 spec landed 前返 _PENDING_A1_SPEC marker · eval_id 空时返空串.
    """
    if not eval_id:
        return ""
    # TODO(worker-A1): evaluation runner 跑分前 prompt 内提示自校 · ratify 后 fill
    return _PENDING_A1_SPEC


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def assemble(
    *,
    role: str,
    tools: list[dict] | None = None,
    schema_hint: str = "",
    examples: list[dict] | None = None,
    eval_id: str = "",
    strict: bool = False,
) -> str:
    """组合 8 段为最终 system prompt.

    Args:
        role:        agent_role_block 的 role kwarg
        tools:       tool_use_block 的 tools
        schema_hint: output_schema_block 的 schema_hint
        examples:    few_shot_block 的 examples
        eval_id:     evaluation_hook_block 的 eval_id
        strict:      行为模式 (V2 fix issue 4):
                      · False (默认): placeholder section 静默 skip · 仅返 ratified 内容
                      · True: placeholder 仍 skip · 但有任一 placeholder 时抛
                        PendingA1SpecError · 防 A4 worker 在 A1 spec 未 landed 时
                        误用本 module 注入空 prompt

    Returns:
        str · 已 ratify section \\n\\n 拼接 · 空段 / placeholder 段全 skip.
        当前所有 8 段都是 placeholder · A1 spec landed 前 strict=False 默认返 "".

    Raises:
        PendingA1SpecError: strict=True 且任一启用 section 仍 placeholder · 显式
            阻止 A4 worker 接入空 prompt.
    """
    sections: list[tuple[str, str]] = [
        ("safety", safety_block()),
        ("evidence_first", evidence_first_block()),
        ("agent_role", agent_role_block(role)),
        ("tool_use", tool_use_block(tools)),
        ("output_schema", output_schema_block(schema_hint)),
        ("self_check", self_check_block()),
        ("few_shot", few_shot_block(examples)),
        ("evaluation_hook", evaluation_hook_block(eval_id)),
    ]

    pending: list[str] = []
    parts: list[str] = []
    for name, content in sections:
        if not content:
            continue
        if _PENDING_A1_SPEC in content:
            # V2 fix issue 4 · placeholder 永远 skip · 不进 output (无论 strict 与否)
            pending.append(name)
            continue
        parts.append(content)

    if strict and pending:
        raise PendingA1SpecError(
            f"contract.assemble(strict=True) blocked · sections still placeholder: "
            f"{pending} · 等 worker-A1 spec landed (docs/contracts/llm-prompt-contract.md)",
        )

    return "\n\n".join(parts)


__all__ = [
    "PendingA1SpecError",
    "agent_role_block",
    "assemble",
    "evaluation_hook_block",
    "evidence_first_block",
    "few_shot_block",
    "output_schema_block",
    "safety_block",
    "self_check_block",
    "tool_use_block",
]
