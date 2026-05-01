# 主 CLI + Codex 后端方案辩论 R1 · 主 CLI 独立草案

> 痛点驱动 · 不凭印象 · 不套 best practice · 不套竞品
> 2026-05-01 · PM 严要求"深度考虑产品到底解决了什么痛点的角度去设计后端"

## 0. 我自审 (诚实 · v2 charter 错在哪)

PM 看穿 v2 charter 8 项后端 deep work ~17% evidence + 83% 印象。我承认:
- "Agent1 embedding look-alike" — embedding 是**手段不是目的** · RM 真痛是"找的候选不准 + 没追踪是否真转化"
- "Agent3 真 ML (logistic/GBDT)" — ML 是**手段不是目的** · 审贷员真痛是"AI 评分理由不够说服信贷委员会"
- "Agent6 cross-section coherence" — 凭印象推审贷员"应该想要" · 没真问审贷员
- "Agent5 政策 RSS auto-ingest" — 凭印象推合规官"应该想要时效" · 没真扫 agent_compliance backend 看现状

**Fix**: R1 重新基于 4 角色真痛 (我作为产品 PM + 银行场景接触判断 · evidence 见 §1)。

## 1. 4 角色真痛清单

### 1.1 RM 客户经理 (主用户 · 80% 时间)

**痛 1.1.1**: 信息散在 Excel + 微信 + CRM + 报告 · 每天接触数十客户 · 没有"谁该今天联系 · 联系什么"的智能提示
**痛 1.1.2**: 找新客户 (look-alike) 不准 · 现 Agent1 用 Tavily 外搜 · 没接内源已成交客户库 (per F-005 NEVER CORRECTLY DELIVERED)
**痛 1.1.3**: 没追踪 conversion (RM 选了候选 · 实际转化率多少 · 哪些信号高转化 · 全没数据)
**痛 1.1.4**: KPI 不可见 (客户活跃度 + 转化率 + AUM 增量 · 现产品没追踪)

### 1.2 审贷员 (final decision maker)

**痛 1.2.1**: AI 评分"看不到理由" · 不接受黑盒推荐 · 要看支撑数据 + 同业对标 (现 Agent3 是 LLM 评分 · evidence 是 fixture per Codex R1 v2 Bug 2)
**痛 1.2.2**: 大量重复决策 (普惠贷款 90% 是 standard case · 但每单都全人工审) · 想要"AI 高置信预审 + 我只看异常"
**痛 1.2.3**: 报告各章节数据不一致 (e.g. 营收章说 5 千万 · 经营章说 1 亿) · 没有 cross-section sanity check (现 v16 单 section 独立)
**痛 1.2.4**: 委员会要求"同业对标" (本企业 vs 同行业平均) · 现 Agent3 没

### 1.3 合规官

**痛 1.3.1**: 政策更新跟不上 (银保监一年多次新政) · 现 Agent5 KB 估计要手 paste 政策原文 · 没真接央行/银保监 RSS
**痛 1.3.2**: 合规审查重复 (同类型贷款都问同样问题 · 90% 标准化) · 想要"AI 自动检 + 我只看冲突"
**痛 1.3.3**: 合规告警是静态卡 · 没"阻断/忽略/升级"actionable (per Gemini R2 v2 决断 6)
**痛 1.3.4**: 合规历史趋势 (季度/年度合规事件统计) · 现产品没

### 1.4 风险经理

**痛 1.4.1**: 写 DSL 难 · 要懂 Python + 业务 · Agent2 LLM 协助生成 · 但**写完不知道好不好** (回测要快 + 业务指标看得懂)
**痛 1.4.2**: KS/AUC 业务方看不懂 · 要"通过率 + 坏账率 + 利润影响"业务指标 (per Gemini R2 v2 决断 7 大白话结论)
**痛 1.4.3**: 跨客户模式发现 (e.g. ≥ 3 客户共同信号) · 现 Agent4 一个个看 · 没 batch analytics
**痛 1.4.4**: 预警 SLA · 风险事件追踪 · 现产品没

## 2. v2 Charter 8 项重评 (诚实 · evidence 强度排)

| v2 # | Action | 真痛对应 | Evidence 强度 | R1 verdict |
|---|---|---|---|---|
| 1 | Agent3 真 ML | 痛 1.2.1 (评分理由说服力) — 但 ML 不是答案 (evidence 链才是) | ⚠️ 30% | **改 scope**: 不要 ML · 改 "Agent3 evidence 链强化 (ReportJSON 字段引用 + 同业对标 fixture)" |
| 2 | Agent6 cross-section coherence | 痛 1.2.3 (报告章节不一致) | ✅ 90% | **保留** |
| 3 | Agent4 batch analytics | 痛 1.4.3 (跨客户模式) | ✅ 80% | **保留** |
| 4 | Agent5 政策 RSS auto-ingest | 痛 1.3.1 (政策时效) | ✅ 70% (要 audit Agent5 现状) | **保留** |
| 5 | Agent1 embedding look-alike | 痛 1.1.2 (look-alike 不准) — embedding 是手段 | ⚠️ 30% | **改 scope**: 不要 embedding · 改 "Agent1 内源客户库 + conversion tracking" (痛 1.1.3) |
| 6 | Agent2 ML rule mining | 痛 1.4.1 (DSL 写完不知道好不好) — ML 不是答案 | ⚠️ 20% | **撤**: 改 "Agent2 业务指标双轨 (KS/AUC + 通过率/坏账率/利润影响)" (痛 1.4.2) |
| 7 | 数据飞轮真 production | enabler · 不是直接痛 | 50% | **保留** (worker-B1 必做) |
| 8 | 多租户基础 | toB 销售 IT 决策者痛 (能买的基础) | ✅ 80% (per worker-B2 spec) | **保留** (worker-B2 必做) |

## 3. R1 主 CLI 后端 deep work 清单 (痛点驱动 · 8 项)

按 4 角色 + 真痛对应 (不再凭印象):

### 必做 P0 (痛点强 · evidence ≥ 70%)

1. **Agent6 cross-section coherence + historical comparison** (痛 1.2.3) · 2 周
   - 现状: v16 pipeline 单 section 独立 (每章 LLM 单独生成)
   - 改: 加全局 sanity check (营收 vs 经营 vs 现金流 互一致) + historical 对比 (同行业历史报告异常值标注)
2. **Agent4 batch analytics + alert clustering** (痛 1.4.3) · 2 周
   - 现状: 一个个客户独立预警
   - 改: 跨客户聚合 (≥ 3 客户共同信号 · per handoff schema §6.4) + alert clustering 同类合并
3. **Agent5 政策 RSS + conflict matrix auto** (痛 1.3.1 + 1.3.2) · 1.5 周 (待 Codex R1 audit Agent5 现状)
   - 现状: KB scan + LLM 解读 (估计 · 待 audit)
   - 改: 央行/银保监 RSS 自动 ingest + 新政策触发 conflict matrix 自动重扫
4. **Agent3 evidence 链强化 + 同业对标** (痛 1.2.1 + 1.2.4) · 2 周
   - 现状: LLM 评分 + Evidence-First 三阶段 · 但 evidence 是 fixture (Codex Bug 2)
   - 改: 评分理由真接 ReportJSON 字段引用 (file:line) + 同业对标 fixture (行业平均/中位数)
5. **Agent2 业务指标双轨** (痛 1.4.2) · 1 周
   - 现状: backtest 出 KS/AUC (业务方看不懂)
   - 改: 加 plainBusinessMetrics (通过率/坏账率/利润影响估算) + 双轨展示

### 必做 P0 (enabler)

6. **数据飞轮真 production** (worker-B1) · 3 周
   - per Codex R2 v2 加补 C14 baseline gate · 真做 RM 反馈 → auto evaluation → A/B test framework
7. **多租户基础** (worker-B2) · 3-4 周
   - per worker-B2 spec · 真做 isolation + audit per tenant + usage metering

### 改 scope (RM 真痛 · 但 v2 凭印象用错手段)

8. **Agent1 内源客户库 + conversion tracking** (痛 1.1.2 + 1.1.3) · 1.5 周
   - 现状: Tavily 外搜 (不准 · F-005 broken)
   - 改: 内源已成交客户库 (`customer/`) + similarity 4 维度 explainable (industry/geo/scale/已成交) + RM 选候选后追踪 conversion (落 `data/feedback/conversion.jsonl`)

### 撤 (v2 凭印象 · 不是真痛)

- ❌ "Agent3 真 ML" (审贷员痛是 evidence · 不是 ML) → 改 v2 #1
- ❌ "Agent1 embedding look-alike" (embedding 是手段) → 改 v2 #5
- ❌ "Agent2 ML rule mining" (DSL 痛是业务指标 · 不是 ML 协助) → 改 v2 #6

**总**: 8 项 (必做 P0 7 项 + 改 scope 1 项 + 撤 3 项) · 总 ~14 周 (含并行 ~10-11 周 wall-clock)

## 4. 个人画像 POC 加哪 (R1 verdict)

POC 评价标准表 4 维度 (toC 零售财富业务):
- 客户画像 35% (CRM 整合 + 隐性标签 + 需求预测)
- 产品适配 25% (推荐 + 合规校验 + 知识库)
- 经营策略 20% (话术 + 任务拆解 KPI)
- 技术性能 20%

**现 6 Agent 覆盖度**:

| 维度 | Agent1 (toB look-alike) | Agent3 (授信决策) | 新 Agent7 (CRO 客户运营) |
|---|---|---|---|
| 客户画像 | ❌ (找新客户 · 不画像老客户) | ⚠️ (评分需要画像 · 但 scope 是授信决策) | ✅ (整合 CRM + 标签 + 预测 · 直接 fit) |
| 产品适配 | ❌ (找企业 · 不推产品) | ❌ (是授信不是销售) | ✅ (产品推荐 + 合规校验) |
| 经营策略 | ❌ | ❌ | ✅ (话术 + KPI) |

**主 CLI R1 verdict**: **新建 Agent7 客户运营 / 财富顾问 (CRO)** · 不挤进 Agent1/Agent3:

理由:
- POC 4 维度跟 Agent1 (找新企业) 和 Agent3 (授信决策) **scope 完全不同** — 强塞会破 6 Agent 边界 (per CLAUDE.md §4 不可跨界)
- 银行 toC 零售客户运营是大市场 (财富/理财/保险) · 单独 Agent 商业化更清晰
- Agent7 用户 = 个人 RM (零售客户经理) · 跟 Agent1 (公司 RM 找企业) 是不同角色

风险:
- 破 PM 之前 ratify 6 Agent 矩阵 (变 7 Agent · 大动)
- 6 Agent → 7 Agent 涉及命名 SSOT 改 + RBAC 加 + 前端加 archive workspace + handoff schema 加新链路 (大量 connective tissue)

**折中** (PM 反硬改 · 如果不想破 6 Agent):
- Agent7 作为 **Phase C** 加 (Phase B 不动 6 Agent · Phase B 后看 POC POC 实际拿单情况再决定)
- Phase B 期间用 worker-B2 商业化 doc 占位 (POC 评价标准表作为 Phase C charter input)

## 5. 主 CLI R1 verdict (≤ 200 字)

后端 deep work 8 项 (痛点驱动 · 不凭印象 · 撤 3 项 v2 凭印象 · 改 1 项 scope · 加 1 项 evidence 链强化):
- 4 项 Agent backend 真业务能力 (Agent6 cross-section + Agent4 batch + Agent5 政策 RSS + Agent3 evidence 链)
- 1 项 Agent2 业务指标双轨 (大白话结论)
- 1 项 Agent1 内源 + conversion tracking
- 2 项 enabler (数据飞轮真 production + 多租户基础)

总 ~14 周 (~10-11 周 wall-clock 并行)

个人画像 POC = 新建 **Agent7 CRO** (客户运营 · toC 零售) · Phase C 加 (Phase B 不破 6 Agent)。

待 Codex R1 backend audit 出 → R2 互检 → R3 综合给 PM。
