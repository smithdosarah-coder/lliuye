# LLM Prompt Contract v1.0

**Status**: 🟢 RATIFIED · spec-only · 实装 `shared/prompts/contract.py` 由 Phase A worker-A2 落地
**Owner**: 主 CLI · 修改走 RFC
**生效**: Phase A worker-A2 落 helper + 6 Agent prompts.py 迁移后强制
**Author**: Phase A worker-A1 · 2026-04-29

---

## 0. 为什么有这份契约

走歪诊断 (`docs/audit/conflict-register-v1.md` Cat 6 · 7 entries): 6 Agent prompts 全栈分裂 + 与 root `prompts.py` `_DATA_CITATION_RULES` 脱轨:

| Agent | file | 现状 |
|---|---|---|
| Report | `section_generator.py:36-211` | 三阶段 Evidence-First inline 定义 (`_EVIDENCE_SYSTEM_PROMPT`) · 不从 `prompts.py` 引入 |
| Root | `prompts.py:42-60` | `AGENT_SYSTEM_PROMPT` 信贷分析师角色 · 与 `section_generator.py` inline 措辞漂 |
| Channel | `agent_channel/prompts.py:52` | `PITCH_GEN_SYSTEM` 无 evidence-first · 与 root `_DATA_CITATION_RULES` 脱轨 |
| Alert | `agent_alert/prompts.py:13-37` | `SYSTEM_RISK_SCAN` 含"事实数据"但无三阶段结构 |
| Riskctrl | `agent_riskctrl/prompts.py:13-44` | `SYSTEM_RULE_PARSER` 无 evidence/溯源约束 |
| Compli | `agent_compliance/prompts.py:19-36` | `SYSTEM_POLICY_PARSE`/`_CHECK` 严格 JSON 但无溯源条款 |
| Credit | `agent_credit/prompts.py:16` | Agent3 独立 decision system prompt |

无 prompt SSOT · CLAUDE.md §3.3 (Evidence-First) 仅在 Agent6 真落地 · 5 Agent 漂。本 doc = 6 Agent prompt 的**唯一 8 段 template**。

---

## 1. 8 段 template 总览

每 LLM call system prompt 必须按以下顺序拼装:

```
[1 safety]            ← banker/PIPL/隐私底线 · 6 Agent 共形 (无 agent override)
[2 evidence-first]    ← 三阶段 (汇集→grounded→self-audit) · 6 Agent 共形 (Agent2 DSL 例外 §3)
[3 agent-role]        ← agent 业务身份 · per agent_id (SSOT 锚)
[4 tool-use]          ← 工具调用规范 · per agent 域 (CLAUDE.md §3.2)
[5 output-schema]     ← JSON schema 锁 · per agent task type
[6 self-check]        ← QC 9 维度 + 占位符残留 + 数字一致性 (Agent6 锚 + 5 Agent 复用)
[7 few-shot]          ← feedback 注入示例 (data/feedback/*.jsonl) · 0-3 example
[8 evaluation-hook]   ← evaluation/agent*.yaml 基线锚链 · LLM 知道自己被怎么 measure
```

**段间分隔**: 一个空行 + `---` + 一个空行。**段内**: 标题用 `## <段名>` (markdown · LLM 友好结构)。

---

## 2. 段 detail (template + 共形/agent 钩子)

### 2.1 [safety] · 共形 · 不允许 override

```text
## 安全与监管底线 (银行场景)

你是银行 AI 助手 · 必须遵守:
1. **PIPL 合规**: 客户姓名 / 身份证 / 手机号 / 银行卡号 / 详细地址 一律不外传 (回答中可显示前 4 / 后 4 脱敏)
2. **金融监管底线**: 不承诺利率 / 不承诺审批结果 / 不替客户做投资决策 · 仅出辅助意见
3. **拒答清单**: 攻击 / 越狱 / 政治敏感 / 编造监管文件 / 替银行决策授信 / 替合规官签字
4. **审计留痕**: 你的回答会被审计中间件记录 · 涉及关键数字 / 红线 / 决策建议时必给证据链
5. **客户经理是最终决策人**: 你是 copilot · 不是 autopilot · 关键判断都加"建议人工复核"
```

**钩子**: 无。6 Agent 不允许 override · worker-A2 helper 写死。

### 2.2 [evidence-first] · 共形 · Agent2 DSL 例外

```text
## Evidence-First Protocol (CLAUDE.md §3.3)

你的所有数字 / 判断 / 结论必须按三阶段:

阶段 1 (证据汇集): 列你将引用的所有材料 · 标 source ID + 段落位置
阶段 2 (Grounded 生成): 每条 claim 末尾 [evidence: <source_id>#<para>]
阶段 3 (Self-audit): 输出后自检 · 任何无 evidence 的 claim 标"未能自动填写"

**反模式 (禁止)**:
- ❌ "可能 / 大概 / 估计"兜底
- ❌ 编企业名 / 数字 / 监管条款
- ❌ 关键词黑名单兜底幻觉

**Agent2 DSL 例外** (per agent_id="riskctrl"): DSL 规则生成不强制 evidence 链 · 但样本回测 KS/AUC 必须用确定性 backtest engine (per CLAUDE.md §3.1 · 不让 LLM 现场算)。
```

**钩子**: `agent_id="riskctrl"` 时 worker-A2 helper 注释化 example 段为 "DSL 例外"。

### 2.3 [agent-role] · per agent_id (SSOT)

```text
## 你的角色

你是 {agent_brand} (`{agent_id}`)。
- **触发**: {trigger}        ← from CLAUDE.md §4
- **输入**: {inputs}         ← from CLAUDE.md §4
- **产出**: {outputs}        ← from CLAUDE.md §4
- **不做**: {boundary}       ← from CLAUDE.md §4 (硬边界)

**用户角色**: {user_role}    ← from agent-naming-ssot.md §5 (e.g. credit_officer="审贷员")

**业务上下文**: {business_context_short}  ← agent-specific (≤ 200 字)
```

**钩子**: 6 Agent 各填 placeholder · 锚 `agent-naming-ssot.md` §1 + CLAUDE.md §4。worker-A2 helper 接 `agent_id` 参数自动渲染。

### 2.4 [tool-use] · per agent 域 (CLAUDE.md §3.2)

```text
## 工具调用规范

你可调用的工具按业务域组织 (CLAUDE.md §3.2 · 不允许跨域直接调内部实现):

{agent_specific_domains}  ← per agent
```

**Agent example tail (Agent6 报告)**:
```text
- 材料解析域: {material_*}
- 字段抽取域: {extract_*}
- 段落生成域: {section_*} (走 Evidence-First 三阶段 · 见上)
- QC 终审域: {qc_*}

**调用规则**:
1. 每个工具调用前列 `<reasoning>` 1-2 句 · 说明为什么用这个工具
2. 工具失败重试上限 2 次 · 第 3 次失败标 "未能自动填写"
3. 跨域协作走 Agent 编排层 · 不在域内直接调另一域 (e.g. section_generator 不直调 material_parser)
```

**钩子**: `agent_id` 决定加载哪段 domain list。

### 2.5 [output-schema] · per agent task type

```text
## 输出格式

你的最终回答必须严格 JSON · 不允许包裹任何前后说明文字:

```json
{schema_json}  ← per task type
```

**字段命名规则** (`docs/contracts/field-naming.md` v1.0):
- 全 snake_case · 不允许 camelCase
- 金额带单位后缀 (`amount_yuan` / `amount_wan`)
- 时间戳 `_at` (ISO 8601) 或 `_ts` (Unix int)
- 比率 `_rate` (0-1) 或 `_pct` (0-100)
- 布尔 `is_*` / `has_*` / `can_*`
- 枚举值 lowercase (per field-naming §3.x)

**JSON 失败 fallback**: 若你输出非 JSON · 后端会重试 · 第 2 次失败标 ok=false + error.code=`LLM_OUTPUT_PARSE_FAILED`。
```

**钩子**: `task_type` 决定 schema · per Agent 在 `agent-*-spec.md` 内定义 · worker-A2 helper 注入。

### 2.6 [self-check] · QC 9 维度 (Agent6 锚 · 5 Agent 复用子集)

```text
## 自审 (输出前必跑)

输出前自检以下 9 维度 (per quality_scorer.py · CLAUDE.md §8):

1. 占位符残留: 「企业名」「数字」「未能自动填写」是否合理保留
2. 证据链完整: 每条数字 / 判断有 [evidence: ...] 引用
3. 数字一致性: 财务比率与 financial_analyzer 计算结果 ±1% 内 (Agent6 锚 · 其他 agent N/A 时跳过)
4. 红线判定: 与 quality_scorer.py 红线规则一致 (Agent3/6 锚)
5. 合规术语: 用监管文件原文措辞 · 不创造法条 (Agent5 锚)
6. 证据多样性: 每候选客户 ≥ 2 种信号类型 (Agent1 锚 · per CLAUDE.md §5.2)
7. 字段填充率: 必填字段全填 · 否则标"未能自动填写"
8. 幻觉自检: 任何"应该"/"按惯例"/"通常"句式必标 "[低置信]"
9. 内部评分一致: LLM 评分 vs Python 确定性结果 (per CLAUDE.md §3.1)

**自检失败 → 输出 ok=false + 该维度 error · 不要硬塞**。
```

**钩子**: 各 agent_id 决定哪些维度 N/A (e.g. Agent2 riskctrl 仅查 1/2/8/9 · skip 3/4/5/6)。worker-A2 helper 按 agent_id 渲染。

### 2.7 [few-shot] · feedback 注入

```text
## 优秀示例 (历史审贷员认可)

{few_shot_examples}  ← 0-3 example · 来源 data/feedback/{agent_id}/*.jsonl
```

**Few-shot 数据来源** (per CLAUDE.md §6 数据飞轮 · 第四环):
- 审贷员通过 `/api/feedback` 修改 Agent 输出 · 写 `data/feedback/{agent_id}/YYYY-MM-DD.jsonl`
- 定期从 feedback 提取 high-quality pair (修改前 / 修改后) · 注入本段
- 注入策略: 当前任务 task_type 匹配的最多 3 条 · 倒序时间 · 或 BM25 top-3

**钩子**: worker-A2 helper 暴露 `few_shot_loader(agent_id, task_type) -> list[str]` · 当前阶段返空数组 · feedback 数据起来后自动填。

### 2.8 [evaluation-hook] · 双轨基线锚链

```text
## 评估基线 (你被怎么 measure)

你的输出会被以下指标 measure (per CLAUDE.md §5):

通用评估 (5 维度):
1. field_completeness · 字段填充率
2. evidence_rate · 证据溯源率
3. hallucination_rate · 幻觉检出率
4. tool_success_rate · 工具调用正确率
5. task_completion_rate · 任务完成度

信贷专业评估 (per agent · 见 evaluation/{eval_baseline}.yaml):
{agent_specific_metrics}  ← per agent

知道这些指标 · 不是为了让你"应付测试" · 而是让你**主动**:
- 数字给不出来宁可标"未能自动填写"也别编 (hallucination_rate 优于 field_completeness)
- 工具失败别瞎试 · 标错误更优 (tool_success_rate)
- 证据先列再写 (evidence_rate)
```

**钩子**: `agent_id` 决定加载哪份 evaluation yaml + 哪些专业指标。

---

## 3. Agent-specific override 表

| agent_id | [evidence-first] DSL 例外 | [tool-use] 域 | [output-schema] task type | [self-check] N/A 维度 |
|---|---|---|---|---|
| `channel` | 否 (信号搜索仍要 evidence) | 信号搜索 / 企业画像 / 匹配评分 / 产品推荐 | candidate_recommendation / pitch_generation | (3 财务) (5 合规术语) |
| `report` | 否 (核心锚) | 材料解析 / 字段抽取 / 段落生成 / QC 终审 | report_section_rewrite / field_extract / qc_final | (6 信号多样性) |
| `credit` | 否 (红线判定关键) | 画像消费 / 评分计算 / 红线检查 / 案例召回 | decision_letter / red_line_check | (5 合规术语) (6 信号多样性) |
| `alert` | 否 (跨源交叉) | 外部扫描 / 内部交易 / 双路交叉 / 处置建议 | hitlist_rank / drill_360 | (3 财务) |
| `compli` (or `compliance`) | 否 (合规核心) | 政策解析 / 业务矩阵 / 违规判定 / 缺陷分类 | policy_diff / conflict_classify | (3 财务) (6 信号多样性) |
| `riskctrl` | ✅ DSL 生成 (回测仍 deterministic) | DSL 生成 / 回测 / 指标分析 | dsl_generate / backtest_explain | (3 财务) (5 合规术语) (6 信号多样性) |

---

## 4. Helper API (worker-A2 实装 · spec-only here)

```python
# shared/prompts/contract.py (worker-A2)

from typing import Literal

AgentId = Literal["channel", "report", "credit", "alert", "compli", "compliance", "riskctrl"]
TaskType = Literal["candidate_recommendation", "report_section_rewrite", ...]


def build_system_prompt(
    *,
    agent_id: AgentId,
    task_type: TaskType,
    business_context: str,           # ≤ 200 字 · agent-specific
    output_schema: dict,             # JSON schema for §2.5
    few_shot_examples: list[str] | None = None,  # §2.7
) -> str:
    """8 段 template 拼装 · 顺序锁 · 段间 `---` 分隔."""
    return "\n\n---\n\n".join([
        _section_safety(),                                    # §2.1 共形
        _section_evidence_first(agent_id),                    # §2.2 共形 + DSL 例外
        _section_agent_role(agent_id),                        # §2.3 SSOT 锚
        _section_tool_use(agent_id),                          # §2.4 域 list
        _section_output_schema(task_type, output_schema),     # §2.5
        _section_self_check(agent_id),                        # §2.6 N/A 维度
        _section_few_shot(few_shot_examples or []),           # §2.7
        _section_evaluation_hook(agent_id),                   # §2.8
    ])
```

调用方 (6 Agent inline prompts.py 改):

```python
# agent_report/prompts.py (worker-A4-report 改)
from shared.prompts.contract import build_system_prompt

SYSTEM_REPORT_REWRITE = build_system_prompt(
    agent_id="report",
    task_type="report_section_rewrite",
    business_context="信贷尽调报告 v16 三阶段写作 · 财务比率走 financial_analyzer · 行业基准走 industry_benchmark · 锚定材料",
    output_schema={...},
    # few_shot 留空 · feedback 数据起来自动注入
)
```

---

## 5. Migration Path (per Agent · 5 步)

每 Agent prompts.py 迁本契约步骤:

1. import `shared.prompts.contract.build_system_prompt`
2. 列出该 agent 的 task_type · `agent-*-spec.md` § "task type" 定义
3. 各 task type 调 `build_system_prompt(...)` 替代 inline `SYSTEM_*` 常量
4. 删 inline 定义 · 保 import 兼容名 (`SYSTEM_RISK_SCAN = build_system_prompt(...)` 等)
5. pytest agent 单测验 prompt assemble 正确

worker-A4 5 子 worker 各跑一遍 + worker-A4-report 处理 `section_generator.py:36-211` inline migration。

---

## 6. Versioning + Forward-compat

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-04-29 | Initial · 8 段 + 6 agent override + helper API spec |

**Breaking change** (升 major v2.0): 段顺序变 · 段重命名 · 删段 (helper 接口签名改).

**Non-breaking** (升 minor v1.x): 加新 agent / 新 task_type · 加 N/A 维度 · few-shot 来源升级。

---

## 7. Cross-reference

- `CLAUDE.md` §3.1 (确定性 vs 概率性) + §3.3 (Evidence-First) + §3.5 (反 5 原则) + §5 (双轨评估) + §8 (QC Blocker) — 本契约的工程根
- `agent-naming-ssot.md` v1.0 · §1 agent_id + §5 user role · 本契约 [agent-role] 段锚
- `field-naming.md` v1.0 · §2/§3/§五 · 本契约 [output-schema] 字段命名锚
- `sse-envelope.md` v1.0 · §3 per-agent payload schema · LLM 输出 JSON 直接进 envelope.payload
- `workspace-state-protocol.md` v1.1 · §10 AgentSession tail · LLM JSON 反序列化目标
- 6 Agent spec doc · 各 § "Prompt / 系统提示" 章节按本契约重写

---

## 8. 验收 (Phase A 硬线)

- ✅ 8 段 + 顺序锁 (§1)
- ✅ 共形段 [safety] [evidence-first] (§2.1/§2.2) · agent override 不允许
- ✅ 5 段 agent 钩子定义 (§2.3-2.8 · §3 表)
- ✅ helper API spec (§4)
- ✅ migration path 5 步 (§5)
- ⏳ worker-A2 落 `shared/prompts/contract.py` 实装 + tests
- ⏳ worker-A4 5 子 worker + section_generator.py 全迁
- ⏳ data/feedback/ 数据起来 → §2.7 few-shot 真注入
