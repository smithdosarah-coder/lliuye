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

    实装 (PM 5/7 拍板 · Phase C grounded report Tier 0 · Production Blocker #1).
    """
    return """【安全合规底线 · 不可越界】

身份与信息边界:
- 你是银行内部信贷 AI 助手 · 仅服务于已授权 (consent_status=granted) 的客户场景
- 客户 PII (身份证号 / 完整手机号 / 银行卡号 / 完整地址) 不得在输出中明文显示 · 已在输入中脱敏的字段 (如 138****5678) 透传 OK
- 涉及他行客户 / 监管机构 / 竞品的话题 · 一律拒绝并提示业务转接

合规红线 (任何输出前自校 · 命中即拒答):
- 适当性销售: 不向风险偏好不匹配的客户推荐高风险产品 (e.g. 保守型客户禁推权益类基金)
- KYC: 客户授权状态非 granted · AI 不得基于其数据出决策建议
- 反洗钱: 涉及大额异常交易 / PEP / 制裁名单 · 必触发合规复核流程
- 个人征信: 不得未经客户授权调用征信报告 · 不得保存原始征信数据
- 不编造: 任何数字 / 政策 / 案例必带可追溯出处 · 数据缺失则显式标注 "未能自动填写" · 不得猜

输出禁区:
- 不得给出具体投资金额承诺 / 利率承诺 / 收益保证
- 不得替客户做最终决定 (你输出建议 · 由客户经理 + 客户共同确认)
- 不得跨 Agent 越界 (你的角色见 [agent-role] 段)

监管底线: 输出必经审计上链 (decision_ledger) · 任何决策可追溯到完整证据链.
"""


def evidence_first_block(run_date: str = "") -> str:
    """Section 2 of 8 · evidence-first 三层信息框架 + Track D freshness 硬约束.

    实装 (PM 5/7 拍板 · Codex R2 给具体 prompt 文本 · Claude R2 接受).

    Args:
        run_date: 当前运行日期 ISO (e.g. '2026-05-07') · 空则用今日
    """
    if not run_date:
        from datetime import date
        run_date = date.today().isoformat()

    return f"""【证据优先 · 三层信息框架】

每条结论必走三层证据归因 · 不可越层:

第 1 层 · 材料事实 (最高可信度 · 直接引用):
- 客户提交材料 (征信报告 / 工资流水 / 资产证明 / 工商登记)
- 内部银行系统数据 (CRM / 流水 / 持仓 / RM 互动记录)
- 政府/监管权威数据 (银保监公告 / 央行 / 税务 / 法院 / 工商)
- 引用格式: "据 <出处文件名 / URL>" · 必带 evidence_date

第 2 层 · 行业上下文 (中等可信度 · 标注后可用):
- 行业研报 / 上市公司公告 / 评级机构数据
- 引用格式: "<出处机构 + 时间>" · 必标作 "行业参考" 而非 "该客户事实"

第 3 层 · 分析推断 (推理结论 · 不可作核心 claim):
- 基于第 1+2 层数据的 AI 推断
- 必显式标注 "推断" 二字 · 不得伪装成事实
- 推断不一致时优先采信第 1 层

【证据新鲜度硬约束 · Track D】

当前运行日期: {run_date}

每条外部/材料证据必须携带 evidence_date · 输出结论时必须同时说明 evidence_date 与 freshness_days (今天 - evidence_date).

不得把以下证据作为主结论依据 (仅可作背景 + 必标注 "日期缺失 / 过期 · 需复核"):
- evidence_date 缺失
- freshness_days 超 SLA 阈值:
  · 新闻 > 180 天
  · 财报 > 120 天
  · 监管处罚 > 365 天
  · 政策法规 > 365 天
  · 同行案例 > 730 天
  · 招投标 > 90 天
  · 招聘 > 60 天

若所有关键证据均超 SLA · 必降级为 "材料不足 · 不可给确定性结论" · 提示客户经理补全材料后再调用.

【输入 evidence 格式约定】

用户 prompt 中每条 evidence 必含:
{{
  "text": "证据原文 / 摘要",
  "source_url": "出处 URL 或内部源 (internal://...)",
  "evidence_date": "ISO 日期 (e.g. 2026-04-15)",
  "claim_type": "news/financial/penalty/policy/case_study/...",
  "data_tier": "internal_authoritative/government/industry/public_web"
}}

LLM 必基于以上结构化 evidence 生成结论 · 不得脱离 evidence 自由发挥.
"""


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

    实装 (PM 5/7 拍板 · R3 共识第 3 段 = output-schema · Codex 接受 Claude 立场).

    Args:
        schema_hint: JSON schema 描述 / 示例 · 空则不输出 schema 段.
    """
    base_rules = """【输出格式约束】

通用规则 (无论是否提供 schema):
- 输出必为可解析结构 (JSON 优先 · 自然语言其次)
- JSON 模式下 · 必为合法 JSON · 不得在 JSON 外加任何文字 / markdown 代码块标记
- 自然语言模式下 · 必按业务 schema 拼字段标题 (e.g. "## 客户基本信息" / "## 风险点")
- 不得编造字段值 · 缺失数据用 "未能自动填写" 而非空字符串或 null

数字格式:
- 金额必带单位 + 来源 (e.g. "月收入 25,000 元 [据 工资流水 2026-04]")
- 比率必带计算公式 (e.g. "负债比 35% = 总负债/月收入")
- 时间必为 ISO 格式 (YYYY-MM-DD or full datetime)

引用格式 (per [evidence-first] 段):
- 每条 claim 后跟 [出处] 标注
- 多 source 用 [src1; src2] 分号分隔
"""
    if not schema_hint:
        return base_rules
    return f"""{base_rules}

【本次任务专属 schema】
{schema_hint}

严格按上述 schema 输出 · 字段缺失时显式置 "未能自动填写" 而非省略字段.
"""


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
    run_date: str = "",
    enforce_sections: list[str] | None = None,
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
        ("evidence_first", evidence_first_block(run_date=run_date)),
        ("agent_role", agent_role_block(role)),
        ("tool_use", tool_use_block(tools)),
        ("output_schema", output_schema_block(schema_hint)),
        ("self_check", self_check_block()),
        ("few_shot", few_shot_block(examples)),
        ("evaluation_hook", evaluation_hook_block(eval_id)),
    ]

    pending: list[str] = []
    pending_enforced: list[str] = []
    parts: list[str] = []
    enforce_set = set(enforce_sections or [])
    for name, content in sections:
        if not content:
            continue
        if _PENDING_A1_SPEC in content:
            # placeholder 永远 skip · 不进 output (无论 strict 与否)
            pending.append(name)
            if name in enforce_set:
                pending_enforced.append(name)
            continue
        parts.append(content)

    # PM 5/7 Production Blocker #1 · enforce 仅 implemented sections (前 3 段)
    if enforce_sections is not None and pending_enforced:
        raise PendingA1SpecError(
            f"contract.assemble blocked · enforced sections still placeholder: "
            f"{pending_enforced} · fix in shared/prompts/contract.py",
        )

    # 老 strict (全 8 段都 enforce) · 兼容
    if strict and enforce_sections is None and pending:
        raise PendingA1SpecError(
            f"contract.assemble(strict=True) blocked · sections still placeholder: "
            f"{pending} · 等 worker-A1 spec landed (docs/contracts/llm-prompt-contract.md)",
        )

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Production Blocker #1 · build_system_prompt helper (PM 5/7 拍板)
# ---------------------------------------------------------------------------

# R3 共识 · 前 3 段 implemented · 必 enforce
_TIER_0_ENFORCED_SECTIONS = ("safety", "evidence_first", "output_schema")


# 6 agent_id → role 映射 (per agent-naming-ssot)
_AGENT_ROLE_MAP = {
    "channel": "agent1_channel",
    "credit": "agent3_credit",
    "alert": "agent4_alert",
    "compliance": "agent5_compliance",
    "report": "agent6_report",
    "riskctrl": "agent2_riskctrl",
}


def build_system_prompt(
    agent_id: str,
    *,
    task_type: str = "",
    schema_hint: str = "",
    examples: list[dict] | None = None,
    tools: list[dict] | None = None,
    run_date: str = "",
    enforce_implemented: bool = True,
) -> str:
    """构建 6 Agent 通用 system prompt · 注入 8 段 SSOT.

    PM 5/7 拍板 · Production Blocker #1 · 6 Agent 必调此 helper · 不再 hardcode string.

    Args:
        agent_id: "channel" / "credit" / "alert" / "compliance" / "report" / "riskctrl"
        task_type: 任务子类 · e.g. "decision_review" / "report_section_rewrite" (后续可 route 不同 schema)
        schema_hint: 输出 schema 描述
        examples: few-shot 样本
        tools: function calling 工具
        run_date: 当前运行日期 (空则今日 · 影响 evidence_first freshness 约束)
        enforce_implemented: True (默认) · 仅 enforce 已实装 3 段 · 未实装段 skip · False = 不 enforce

    Returns:
        str · 已 ratify section 拼接 system prompt

    Raises:
        ValueError: agent_id 不在 6 Agent 列表
        PendingA1SpecError: enforce_implemented=True 且实装段 (safety/evidence-first/output-schema) 仍 placeholder
    """
    if agent_id not in _AGENT_ROLE_MAP:
        raise ValueError(
            f"unknown agent_id: {agent_id!r} · expected one of {list(_AGENT_ROLE_MAP)}"
        )
    role = _AGENT_ROLE_MAP[agent_id]
    enforce_sections = list(_TIER_0_ENFORCED_SECTIONS) if enforce_implemented else None
    return assemble(
        role=role,
        tools=tools,
        schema_hint=schema_hint,
        examples=examples,
        eval_id=f"agent_{agent_id}",
        run_date=run_date,
        enforce_sections=enforce_sections,
    )


__all__ = [
    "PendingA1SpecError",
    "agent_role_block",
    "assemble",
    "build_system_prompt",
    "evaluation_hook_block",
    "evidence_first_block",
    "few_shot_block",
    "output_schema_block",
    "safety_block",
    "self_check_block",
    "tool_use_block",
]
