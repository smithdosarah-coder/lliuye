# PB#2 Prompt Governance · Codex 7 守则 + LLM 越权 4 判定 + 不可照搬 3 条

> **Tier**: 1 (per CLAUDE.md §15 · 红区 · RFC 改)
> **Authority**: PM 2026-05-06 ratify · 双 AI 真辩论 R1+R2 收敛 (Claude opus-4-7 + Codex gpt-5.3-codex)
> **Source**: 卡兹克《AIHOT》《能用脚本就别用 Agent》两文借鉴 + 6 Agent 信贷智能体落地校正
> **Worker scope**: PB#2 worker (D2 freshness 6 Agent prompt 真应用) **必读** · 任何向 6 Agent prompt 加规则的 worker 必读
> **状态**: ACTIVE

---

## 0. Why this contract exists

PB#2 任务 = 把 `shared/prompts/contract.py` 8 段 SSOT 真应用到 6 Agent · 替代 hardcode `SYSTEM_*` 常量。卡兹克《AIHOT》文章 verbatim 教训: prompt 涨到 600 行后 "规则越多模型泛化越差 · 越加规则越笨"。本 contract 是 PB#2 ship 前的安全网 · 防 PB#2 落地走上"600 行 prompt"覆辙。

---

## 1. Codex 7 守则 (verbatim · 加规则进 prompt 必查)

PB#2 注入 SSOT 时 + 任何后续向 prompt 加规则的 worker 必逐条 check:

| # | 守则 | 落地动作 |
|---|---|---|
| 1 | **Prompt 只保留**: 任务定义 / 输入 schema / 输出 schema / 拒答边界 / 证据引用格式 | 其他一律拒入 prompt |
| 2 | **任何"阈值/权重/排序/最终判定"一律移到 Python** | LLM 不下结论 · 不算最终分 · 不判通过/阻断 |
| 3 | **每个 Agent prompt 上限 ≤ 220 行** | 超限必须拆为 SSOT 段并删重复约束 · 不允许"再加 50 行就好"思维 |
| 4 | **禁止在 prompt 里写"多条件优先级决策树"** | 改为代码后处理 · 决策树是 deterministic 计算 · 不该让 LLM 现场判 |
| 5 | **输出强制结构化** (JSON schema / zod) | 失败即重试或降级 · 不让模型自由发挥 · 不允许"模型大概率会按格式来" |
| 6 | **每次加 prompt 规则必须配 1 条失败样例** | 无样例不加规则 · 失败样例进 `data/eval/real_scenario_cases.jsonl` 作回归 |
| 7 | **同义规则合并** | 一条"证据链格式规则"替代多条措辞约束 · 不允许"5 条相似规则各自描述同一约束" |

**违反任意条 = review 阻断 · merge 阻断**。

---

## 2. LLM 越权 4 条判定 (命中任一即越权 · audit 必标)

PB#2 worker 在为每个 agent build SSOT prompt 时 · **必同时审计现有 LLM call site** 是否越权。命中任一即标 `LLM-OVERSTEP: <agent>:<file>:<line>` · 进 PB#2 commit body。

| # | 越权场景 | 治标 (短期 fix-forward) | 治本 (Phase D) |
|---|---|---|---|
| 1 | LLM 直接输出/覆盖**最终授信结论 / 阈值判定 / 合规放行决定** | 加代码 wrapper 把 LLM 输出转成"维度分" · 阈值代码判 | 决策权代码化 · LLM 只打分不下结论 |
| 2 | LLM **决定权重 / 排序规则 / 风险等级映射表** | 把权重/映射表写到 yaml 或 Python const · LLM 输出维度分 + 代码加权 | 配置外部化 · 阈值/权重单独 verison control |
| 3 | LLM 在**无证据 ID / 无可追溯来源**下产出关键字段 | QC gate 阻断 · 标"未能自动填写" (per §3.3 Evidence-First) | Evidence-First 协议强化 · evidence_date 必带 |
| 4 | LLM 输出**未经代码校验**即进入对客 / 对审计结果 | 加代码 校验层 (zod/pydantic) · 不通过 reject + 降级 | 全栈 schema 化 (per §3.5.1 #6 D4) |

---

## 3. 不可照搬 3 条 (内容精选场景 → 金融高合规场景)

卡兹克场景是自媒体内容精选 (失败成本 = 用户少看一篇文章) · 我们是金融银行高合规 (失败成本 = 监管处罚 / 错贷)。**以下 3 条必叠加上位约束 · 不允许直接 copy AIHOT 模式**:

| # | AIHOT 模式 | 金融场景叠加约束 |
|---|---|---|
| 1 | "上百次数值回测调阈值" | **政策刚性约束优先于效果指标** · 监管硬规 (e.g. 对私单笔上限 / 行业禁入名单) **不能被效果指标 override** · 即使回测显示 KS 更高 |
| 2 | "cheap 模型预筛过滤掉 50% 信息" | **监管必查项必白名单强制直通** · cheap 模型不能过滤掉 KYC/AML/反洗钱关键字段 · 即使 cheap 判定"不相关" |
| 3 | "0-LLM AI 日报 1 秒生成" | **对客报告仍需合规模板 + 审计留痕** · 即使流程 0-LLM · 模板版本 + 数据快照 hash + 生成时间戳必入 `decision_ledger` |

---

## 4. PB#2 落地 checklist (worker 必跑)

PB#2 worker 在为每个 agent (channel / credit / alert / compliance / report / riskctrl) build SSOT prompt 时 · 逐条:

- [ ] **prompt 行数审计** — 注入 SSOT 后 system prompt 总行数 ≤ 220 行 · 超限拆 SSOT 段
- [ ] **守则 1 检查** — prompt 内无"阈值/权重/排序"等可代码化逻辑 · 全部移到 Python
- [ ] **守则 4 检查** — 无 "if A then X else if B then Y" 多条件决策树
- [ ] **守则 5 检查** — 输出 schema 已用 pydantic / zod / jsonschema 强制 · 失败有 reject 路径
- [ ] **守则 6 检查** — 本次 PB#2 加的 SSOT 段 8 段每段都有对应 fail case (写到 `tests/shared/test_ssot_prompts.py`)
- [ ] **越权 audit** — 用 越权 4 条扫该 agent 现 LLM call site · 发现的 `LLM-OVERSTEP` 列 commit body
- [ ] **不可照搬 3 条** — 该 agent 是否触及 (compliance / credit 极易触 #1 #2 · report 极易触 #3) · 触及必加上位约束代码

---

## 5. 修改路径 (RFC)

本 contract 改动需:
- PM `Authorized-By` trailer
- 同 commit 加 decisions-log Q-NNN entry
- 同 commit update `docs/reset/state-snapshot.md`

---

## 6. References

- CLAUDE.md §3.1 (确定性 vs 概率性 · 现行二分 · Phase D 三层升级前的 SSOT)
- CLAUDE.md §3.3 (Evidence-First Protocol)
- CLAUDE.md §3.5.1 (#6 数据时效 + #7 业务专家 review)
- CLAUDE.md §3.7 (active runtime rules · 本 contract 落地后此处加 §3.7.6 简述 + 指本 doc)
- `shared/prompts/contract.py` (8 段 SSOT skeleton · PB#1 实装 3 段)
- `shared/prompts/agent_helpers.py` (6 agent BUILDERS)
- `tests/shared/test_ssot_prompts.py` (PB#1 14/14 PASS · PB#2 必扩 fail case 测试)
- 卡兹克《AIHOT》(2026-05-06) `https://mp.weixin.qq.com/s/r6CE2U3Y0-pU05wF3_PuTQ`
- 卡兹克《能用脚本就别用 Agent》(2026-03-17) `https://mp.weixin.qq.com/s/GAZ45bXuSyk793JbnTg__g`
- decisions-log Q-053 (2026-05-06 · PB#2 governance ratify)

---

**Authored**: 主 CLI · 2026-05-06 · 双 AI 真辩论 R1+R2 收敛后 ratify
**Signal**: `PB2-PROMPT-GOVERNANCE-RATIFY-2026-05-06`
