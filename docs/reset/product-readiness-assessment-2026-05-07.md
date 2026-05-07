# 产品就绪度评估报告 · 2026-05-07

> **建立**: Claude + Codex 三轮真辩论 (R1+R2+R3 · low reasoning short prompt 模式 · 全 converged · 不需 R4)
> **目标**: 评估现产品离 "实打实能跑产品" 的差距 + 给出可验收 roadmap
> **PM 触发**: "你先和 codex 评估下现在的产品 · 经过至少三轮辩论后 · 给我辩论的过程 · 然后输出一份详细报告"

---

## 1. Executive Summary

**一句话 verdict**: Phase C 19 件后端模块 + 前端真接 endpoint 全部 ship · 但**距离生产就绪还差 3 个 Tier · 总工作量 1-2 周** (单 CLI sequential).

**Top 1 风险** (Codex+Claude 共识): "看似闭环 · 实际不可追责不可恢复".
- 内存 store (重启丢) + mock decision + silent audit · 三者组合 · 客户上线即崩.
- 比 UI 丑更致命: PM demo 还能解释视觉债 · 生产事故解释不了"审批建议怎么来的 · 为什么没记录".

**关键洞察 (Codex R1 击中我盲点)**: 缺**生产就绪开关/模式边界**. 现 live / demo / mock fallback / silent-fail / forced-mock 混在代码注释和调用参数里 · PM 不知道当前页面是真跑 / 降级跑 / 演示跑.

---

## 2. 当前系统真实状态: Demo / Degraded / Production-ready 边界

| 层 | 状态 | Evidence |
|---|---|---|
| **6 Agent backend endpoint** | ✅ Production live | `https://liuye.me/login` · 17+ endpoint mounted |
| **Phase C 19 个 shared 模块** | ✅ Ship + tsc/test pass | shared/{crm_contract, data_tiers, evidence_freshness, recommendation_schema, ai_decision, decision_review, data_lineage, customer_aggregator, business_metrics, walkthrough_export, data_completeness} |
| **数据持久化** | 🔴 内存 + 重启丢 | session_store 进程内 dict + TTL · review_events 内存 · business_metrics 数据源 review_events |
| **AI 决策真接 LLM** | 🔴 Mock fallback | ai_decision metadata `model: "mock-v1.0"` · 没接 shared/llm_caller |
| **数据源 Tier 化执行** | 🟡 模块 ship 但未应用 | D1/D2/D4 ship 但 6 Agent endpoint 没真校验 evidence_date / data_tier |
| **prompt 注入** | 🔴 没改 | Phase A 8 段 SSOT + Track D 时效约束 · 6 Agent prompt 没真用 |
| **审计日志** | 🟡 Silent fail | audit_log 失败 silent · 监管查不到丢失数据 |
| **前端 API client** | 🟡 局部 client + inline fetch 散乱 | channel.ts/auth.ts/im.ts 部分有 · PersonalFinancePanel/DecisionPanel 直 fetch · 错误处理 silent/alert/banner 混 |
| **UI shell-v2 token** | 🟡 部分纳入 | 5/6 workspace 用 · 但 PersonalFinancePanel/DecisionPanel/CustomerListClient/CrossAgentWorkflowCard 用 inline style |

---

## 3. Top Risks (按致命度排序)

### 🔴 Risk 1 · 不可追责 + 不可恢复 (Codex Top 1)
- 内存 session/review/metrics + mock decision + silent audit
- 客户上线即崩 (重启丢) + 决策来源不可信 (mock) + 失败不可见 (silent)
- **修法**: Tier 0 audit 非 silent + Tier 1 sqlite 持久化

### 🟡 Risk 2 · 伪 AI (mock 看起来像生产)
- ai_decision 返 confidence 0.99 / decision_summary 都给 · 但 metadata `mock-v1.0`
- PM/RM 看不到 "这是 LLM grounded 还是规则 fallback"
- **修法**: Tier 0 metadata 改 honest (`rule-fallback-no-llm` / `llm-disabled` / `llm-error-fallback`)

### 🟡 Risk 3 · 模式不透明 (假生产)
- live / demo / mock / forced-mock / silent-fail 散在代码 · 不暴露 UI
- 客户走访被问 "现在是真还是演示" 答不上来
- **修法**: Tier 0 API envelope 加 `mode/degraded/reason` · UI 明示 · 测试 assert (Codex critical gap)

### 🟢 Risk 4 · 视觉债 + 前端 drift (相对 less critical · 但累积成本)
- 我加的新组件 inline style · 不复用 shell-v2
- TS interface 跟 Pydantic schema drift
- **修法**: Tier 2 (3-5d · 不立即承诺日期 · 见 §10 残余分歧)

---

## 4. Tiered Roadmap

### Tier 0 · 立即修 (~2-3h · 高 ROI 信任修复 · 必先做)

按 Codex R2 顺序 (audit 是底座):

| # | 项 | 工期 | 验收标准 |
|---|---|---|---|
| **0.1** audit_log 非 silent | 30 min | audit_log 写失败抛 exception + UI banner · 不再 silent ignore |
| **0.2** API envelope 加 `mode/degraded/reason` | 1h | 4 critical endpoint (decision/customer/lineage/metrics) response 必含 `meta.mode = "production"/"demo"/"mock-fallback"/"degraded"` + `meta.reason` |
| **0.3** ai_decision metadata honest | 30 min | metadata.model 改 `rule-fallback-no-llm` (现 `mock-v1.0`) · UI 显式 "未接 LLM · 规则建议" |

### Tier 1 · 短期 (~1-2d · 持久化 + LLM 真接 · 客户走访前必做)

| # | 项 | 工期 | 验收标准 |
|---|---|---|---|
| **1.1** session_store / review_events / business_metrics → sqlite | 4-6h | 重启不丢 · 跨 worker 共享 · 与现 BE7 ledger 同 sqlite pattern |
| **1.2** ai_decision 真接 shared/llm_caller | 4-6h | DeepSeek 真调 · prompt 注入证据 · LLM 失败 fallback rule + metadata 标 "llm-error-fallback" |
| **1.3** 6 Agent endpoint 真应用 D1/D2/D4 | 8-10h | Tavily 输出每 evidence 必含 evidence_date + tier · 推荐 build 走 build_recommendation_with_validation |

### Tier 2 · 中期 (无日期承诺 · 触发条件: Tier 0+1 完 + PM 拍板客户上线场景)

per Codex R3 verbatim "不承诺日期 · 仅定义触发条件 · 否则 PM 会把 3-5d 当排期承诺":

| # | 项 | 触发条件 |
|---|---|---|
| **2.1** 统一 API client + 错误 envelope | Tier 0 0.2 完 + 第 5 个 component 加时 |
| **2.2** 新组件强制 shell-v2 token | UI 第 N 处 inline style 时 (N ≥ 5) |
| **2.3** prompt 注入 8 段 SSOT + 时效约束 | Tier 1 1.2 LLM 真接后 |

### Tier 1+2 补充 (Codex R2 加 6 件 · 我漏)

| # | 项 | 工期 |
|---|---|---|
| 生产模式启动校验 (fail fast · 缺 LLM/sqlite/audit/env 不启动) | 1-2h |
| 降级策略矩阵 (哪 endpoint 允许 degraded · 哪必 hard fail) | doc 1h |
| operation correlation_id 串链 (audit_log + review + API + LLM call) | 2-3h |
| 最小恢复流程 (sqlite 损坏 / audit 写失败 / LLM 不可用 / agent timeout) | doc 1h |
| 回归测试矩阵 4 类 (normal / degraded / fallback / production-misconfig) | 1d |
| 数据保留 + 隐私边界 (哪字段必脱敏 · 哪不可落盘) | doc + code · 4-6h |

---

## 5. Production Readiness Gates

ship Tier 0 后必满足 (才能宣称 "demo-ready" → "production-ready"):

- [ ] audit_log 写失败必抛 + UI banner (不 silent)
- [ ] 4 critical endpoint 响应必含 `meta.mode/degraded/reason`
- [ ] ai_decision metadata 显式标 mock vs LLM
- [ ] correlation_id 贯穿前端→backend→LLM→输出物
- [ ] 启动校验 fail fast (生产环境缺关键 dep 不启动)
- [ ] 降级策略矩阵 + 隐私边界白纸黑字 (doc)
- [ ] 回归测试矩阵 4 类全过

---

## 6. 用户可见影响 + UI 表达

### Tier 0 ship 后用户看到的变化

| 现状 | Tier 0 后 |
|---|---|
| ModePill 显 LIVE 真接 / MOCK 演示 (我之前误标) | 显 "production / demo / mock-fallback / degraded" 4 状态 (envelope 来源) |
| AI 建议无标 · 看起来都像 LLM | 显 "AI 建议 (规则 fallback · LLM 未启用)" / "AI 建议 (LLM grounded · DeepSeek 6.5s P50)" |
| audit 失败 silent · 用户看不见 | 出 banner: "审计日志写失败 · 决策已生成但未上链 · 联系 admin" |

### Tier 1 ship 后用户看到的变化

| 现状 | Tier 1 后 |
|---|---|
| 重启 production · review history 全丢 | 跨重启保留 · review history 永久 (sqlite + ledger) |
| AI 决策固定 mock 4 条理由 · 不分客户 | LLM grounded · 按 customer profile 真生成 |
| Tavily 抓 10 年前新闻 · 客户经理拿到露馅 | 必有 evidence_date · stale 自动 block · 走访不再露馅 |

---

## 7. 测试与回归计划

按 Codex R2 提的 4 类:

| 类 | 描述 | Tier 0 必覆盖 | Tier 1 必覆盖 |
|---|---|---|---|
| normal | LLM 接 + 持久化 + audit 全 OK | metadata `production` + envelope mode | sqlite 重启读 OK |
| degraded | LLM timeout · sqlite 暂不可达 | envelope `degraded` + reason | fallback rule + metadata 标 `llm-error-fallback` |
| fallback | LLM 完全不可用 (env 缺 key) | metadata `rule-fallback-no-llm` + UI 显式 | sqlite 也走 fallback (内存 + warn) |
| production-misconfig | 缺 env / sqlite path 错 | 启动 fail fast · 不 silent 起来 | 同 |

现已 ship test:
- D6 real_scenarios 10/10 PASS
- D9 6 Agent freshness audit (4 stale catch)
- A6 e2e walkthrough 0.4s
- P3 Playwright 5 角色 walkthrough spec

需加 (Tier 0+1 后):
- audit fail-loud test (强制 audit_log 写失败 · 校验 banner 出)
- envelope mode contract test (production / demo / mock / degraded 4 状态)
- LLM 真调 + fallback test
- sqlite 重启 + cross-worker share test

---

## 8. 上线/回滚/恢复策略

per Codex R2 "最小恢复流程":

### 上线
- shadow mode 第 1 周: AI 建议生成但不 surface RM · 仅审计 + 比对 · RM 走原流程
- partial rollout 第 2-3 周: 5 内部用户 (王哲/李华/周敏/陈凯/刘野) 真用 · 客户走访演示
- production 第 4 周+: 客户银行真用户接入

### 回滚
- ECS 单点 → 备份 sqlite 每日 + 上一版 docker tag 保留 · 30s rollback
- 单 service rollback (frontend/backend 独立) · 不全栈

### 恢复
- sqlite 损坏: 从备份恢复 (≤ 24h 数据) · 业务影响告知客户
- audit 写失败: banner + 恢复后回填 (依赖 correlation_id 串链)
- LLM 不可用: 自动 fallback rule + UI 标 "LLM 暂不可用" · 业务继续 (不阻 ship)
- agent timeout: 30s 超时 + 显式 timeout banner · 不挂起

---

## 9. PM Open Questions (Tier 0 ship 后必拍)

per Codex R3 5 件:

1. **审计日志保留多久 · 谁可查**? (默认: total 5y per BE7 jurisdiction · 但 admin / RM / 监管可查权限不同)
2. **失败恢复目标**: 重跑整个 case · 还是从阶段恢复? (后者需 stage checkpoint · 工程更复杂)
3. **LLM 降级边界**: 降级可接受质量损失到哪里? (规则 fallback 比 LLM 简单 · RM 可接受多少 simplicity)
4. **数据脱敏白名单**: 哪字段必脱敏 (统社/手机/身份证号 必) · 哪可落盘 (姓名/年龄/职业 默认可落)
5. **Tier 1 绑定**: Tier 1 完成是否绑定具体客户 demo 或上线场景? (有则有 deadline · 无则继续 sequential)

---

## 10. Codex+Claude 三轮辩论残余分歧 (透明 PM)

### R1
- Claude R1: 3 大块判断 + 5 致命缺口
- Codex R1: 接受 + fine-tune (排版/前端 API 不是"完全没") + 击中我盲点 "生产就绪开关/模式边界"

### R2
- Claude R2: 接受 codex 5 处 + 反驳"前端 API client 是 low-hanging" (不同意 · 应进 Tier 2)
- Codex R2: 接受 Claude 反驳 + 加 6 件 (启动校验 / 降级矩阵 / correlation_id / 恢复流程 / 回归矩阵 / 隐私边界)

### R3
- Claude R3: 接受 codex 全部
- Codex R3 sign-off: 基本 converged · 不需 R4

### 残余 1 处分歧 (PM 拍)

**Tier 2 是否承诺日期**?
- Claude R2 倾向: "3-5d" 给 PM 排期可见
- Codex R3 倾向: 不承诺日期 · 仅定义触发条件 (避免 PM 把 3-5d 当排期承诺)
- **本报告采用 Codex 立场** (Tier 2 仅触发条件 · 见 §4)
- PM 可推翻: 拍 Tier 2 具体日期 · 或保 codex "触发条件" 立场

---

## 11. 下一步

### 我建议 (PM 默认行动)
1. PM 看本报告 (~10 min)
2. PM 拍板 Tier 0 立即开干 (我自跑 ~2-3h)
3. PM 看 §9 5 件 Open Questions · 拍 1-2 件先 (其他可后续)
4. Tier 0 ship 后: PM 验收 + 决定 Tier 1 顺序 + 是否绑定客户 demo

### 我等 PM 拍 (不再自加 UI · 不再"理解 PM 意图自动 ship")
- Tier 0 三件 (audit 非 silent / envelope / metadata honest) · 3 件可立即开干 · 安全 (后端 + 不动 visual)
- §9 Open Questions 5 件 · PM 必拍

---

**Source**: Claude+Codex R1+R2+R3 三轮真辩论 · 全 converged
**File**: `docs/reset/product-readiness-assessment-2026-05-07.md`
**Signal**: PRODUCT-READINESS-REPORT-2026-05-07
