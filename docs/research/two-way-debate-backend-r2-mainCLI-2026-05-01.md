# 主 CLI + Codex 后端方案辩论 R2 · 主 CLI 互检 Codex R1

> 主 CLI 看 Codex R1 (b6b152s2w · 全扫 175 .py file:line evidence)
> 2026-05-01 · 痛点驱动 · 不凭印象

## 1. 主 CLI 接受 Codex R1 多少

### 1.1 主 CLI 错的 (诚实承认)

**个人画像 POC 加哪 — 主 CLI Agent7 verdict 错 · 接受 Codex Agent1 子域**

- 主 CLI R1 凭"Agent1 是 toB look-alike · 不 fit toC"印象推 Agent7 (4+ 周新建)
- Codex R1 file:line evidence 反驳: Agent1 已有 `product_recommender.py:2, 25, 108` + 话术 + Top3 推荐 + pitch (`sse_extras.py:540, 592`) — Agent1 早已包含 toC 推荐能力 · 我没真看 backend
- Codex 推 Agent1 子域 `personal_insight` (2.5 周) vs 新建 Agent7 (4+ 周需重复 SSE/mock/导出/审计/权限)
- **主 CLI R2 verdict**: ✅ 接受 Codex · 撤 Agent7 verdict · 改 Agent1 子域

**Agent3 evidence 链表述错 — 接受 Codex decision graph**

- 主 CLI R1: "Agent3 evidence 链强化 + 同业对标" (~泛)
- Codex R1: "decision graph (每结论挂 feature snapshot + rule hit + 阈值 + 来源段落 + 版本)" (具体可执行)
- **主 CLI R2 verdict**: ✅ 接受 Codex 表述 + 加"同业对标 fixture" (主 CLI 提的痛 1.2.4 · Codex 没明提)

**Agent5 政策处理表述泛 — 接受 Codex 政策版本链**

- 主 CLI R1: "政策 RSS auto-ingest + conflict matrix auto" (~泛 · 没具体改啥)
- Codex R1: "policy registry + rule version diff + violation reason schema (字段/原文/置信度/复核原因)" (具体)
- **主 CLI R2 verdict**: ✅ 接受 Codex · 撤"RSS auto-ingest"凭印象 (Codex 没说 RSS · 政策版本链不依赖 RSS · 是 manual+版本管理)

### 1.2 主 CLI 同向 + Codex 表述更具体 · 直接接受

| 主 CLI R1 | Codex R1 (具体) | R2 verdict |
|---|---|---|
| Agent6 cross-section coherence + historical | material gap graph + section impact + handoff Agent3 | ✅ 接 Codex (更聚焦 RM/审贷员 evidence 闭环) · 加"cross-section coherence"作为 sub-feature |
| Agent4 batch analytics + alert clustering | Agent4 信号质量 (freshness + source confidence + scan replay) | ⚠️ **不同方向** · 主 CLI batch analytics 是跨客户聚合 (per handoff schema §6.4) · Codex 是单 alert 信号可信度 — **R2 verdict: 都做** (P0 信号质量 + P1 batch analytics) |
| Agent2 业务指标双轨 (KS/AUC + 通过率/坏账率/利润影响) | Agent2 回测可信度 (champion/challenger + PSI + 分月 + 误杀解释) | ⚠️ Codex 漏"业务指标双轨" · **R2 verdict: 接 Codex 回测可信度 + 加业务指标双轨** (Gemini R2 v2 决断 7 大白话结论的后端实现) |
| Agent1 内源 + conversion tracking | Agent1 候选证据评分 + 数据源状态 | ✅ 接 Codex 候选证据 + 加 conversion tracking (主 CLI 加补 · Codex 漏 · RM 痛 1.1.3) |

### 1.3 Codex 漏的 (主 CLI R2 加补)

**worker-B1 数据飞轮真 production** — Codex backend audit scope 外 (Codex 只扫 6 agent_*/ · 没扫 evaluation/ + scripts/feedback/) · 但 Phase B 必做 (per CLAUDE.md §6 数据飞轮四环 + R2 v2 加补 C14 baseline gate)

**worker-B2 多租户基础** — Codex 没 cover · 但 toB 销售必做 (per worker-B2 spec)

**主 CLI R2 verdict**: 这 2 项保留作为 enabler · Codex 不需 verdict (scope 外)

## 2. R2 后融合方案 (主 CLI 综合 R1 v1 双方)

### Phase B 后端 deep work (P0 · 必做 · 痛点驱动)

| # | Action | 来源 | 工程量 | 真痛 |
|---|---|---|---|---|
| **BE1** | Agent1 候选证据评分 + 数据源状态 + conversion tracking | Codex 1 + 主 CLI 8 | 1.5-2 周 | RM 痛 1.1.2+3 (look-alike 不准 + 没追踪转化) |
| **BE2** | Agent3 decision graph (feature snapshot + rule hit + 阈值 + 来源 + 版本) + 同业对标 fixture | Codex 2 + 主 CLI 4 | 2 周 | 审贷员痛 1.2.1+4 (evidence 链不可复核 + 缺同业对标) |
| **BE3** | Agent6 material gap graph + section impact + handoff Agent3 + cross-section coherence sanity check | Codex 3 + 主 CLI 1 | 1.5-2 周 | RM + 审贷员痛 (材料缺口闭环 + 报告章节不一致) |
| **BE4** | Agent5 policy registry + rule version diff + violation reason schema | Codex 4 + 5 | 2-2.5 周 | 合规官痛 1.3.1+2 (政策版本管理 + 冲突解释签字) |
| **BE5** | Agent4 信号质量 (freshness + source confidence + fallback banner + scan replay) | Codex 8 | 1 周 | 风险经理痛 (Agent4 缺 key 回 mock 信号不可信) |
| **BE6** | Agent2 DSL 上线性 (字段字典 + 单位归一 + 互斥/遮蔽) + 业务指标双轨 (KS/AUC + 通过率/坏账率/利润影响) | Codex 6 + 主 CLI 5 | 2-2.5 周 | 风险经理痛 1.4.1+2 (DSL 写完不知道好不好 + KS/AUC 业务方看不懂) |

### Phase B 后端 deep work (P1 · 推 Phase C OR 与 P0 配套)

| # | Action | 来源 | 工程量 | 真痛 |
|---|---|---|---|---|
| **BE7** | Agent2 回测可信度 (champion/challenger + PSI + 分月指标 + 误杀样本解释) | Codex 7 | 2 周 | 风险经理痛 1.4.1 (回测可信度) |
| **BE8** | Agent4 跨客户 batch analytics + alert clustering (per handoff schema §6.4) | 主 CLI 2 | 2 周 | 风险经理痛 1.4.3 (跨客户模式发现) |

### Phase B enabler (Codex scope 外 · 主 CLI 必加)

| # | Action | 来源 | 工程量 | 真痛 |
|---|---|---|---|---|
| **BE9** | 数据飞轮真 production (RM feedback → auto evaluation → A/B test framework + C14 baseline gate) | 主 CLI 6 + Codex R2 v2 加补 C14 | 3 周 | enabler · 否则 live evidence 接入不可证 Evidence-First |
| **BE10** | 多租户基础 (isolation + audit per tenant + usage metering) | 主 CLI 7 + worker-B2 spec | 3-4 周 | toB 销售 IT 决策者真痛 (能买的基础) |

### Agent7 (个人画像 POC · 主 CLI Agent7 verdict 撤 · 改 Agent1 子域)

| # | Action | 来源 | 工程量 | 真痛 |
|---|---|---|---|---|
| **BE11** | Agent1 `personal_insight` 子域 (画像标签 + 产品适配 + 合规红线 + 触达话术 + PII 脱敏 + latency/抗幻觉) | Codex POC verdict + 主 CLI 接受 | 2.5 周 | toC 零售客户运营 POC (per xlsx 4 维度) |
| **BE12** | POC 跨 Agent 拼 (Agent1 画像/推荐/话术 + Agent5 产品合规校验 + Agent4 触达后预警) | Codex POC 加分项 | 1.5-2 周 | POC 加分 · 但不优先做成重平台 |

## 3. 总工程量

- P0 必做 (BE1-BE6): ~10-12.5 周
- P1 推 Phase C OR 配套 (BE7-BE8): ~4 周
- Enabler (BE9-BE10): ~6-7 周
- Agent7 个人画像 POC (BE11-BE12): ~4-4.5 周

**总 Phase B 后端 deep work**: ~20-25 周 (含并行 ~14-18 周 wall-clock)

加 v4 前端 (5-6 周 含并行) · 总 Phase B 真完整版: **~16-20 周 wall-clock**

## 4. 主 CLI R2 verdict

接受 Codex R1 95% (3 处错诚实承认 + 8 项 6 接受具体表述 + 2 项加补) · Codex 帮我修了 v2 charter 凭印象的洞 (~15% evidence → ~70% evidence)。

加补 4 项 Codex scope 外 (worker-B1 数据飞轮 + worker-B2 多租户 + Agent2 业务指标双轨补 + 跨客户 batch analytics)。

个人画像 POC verdict 改 Agent1 子域 (撤 Agent7 凭印象错)。

待 Codex R2 (b1fauqi55) 出齐 → R3 主 CLI 综合 → 后端方案 v2.1 给 PM。
