# 产品就绪度 grounded 真辩论报告 · 2026-05-07

> **PM 命题**: 评估当前产品 (排版/前端 API/后端实用性) 是否达 "实打实能跑" 标准
> **PM 要求**: Claude + Codex 都真去看代码 (前端 + 后端 + UI) → 三轮辩论 → 写报告
> **辩论方式**: 双方独立思考 → 互看方案 → discuss 差异 (= 1 轮) · × 3
> **基础**: 6 Explore agent 并行 audit + Codex 抽样 grep · 严格 grounded · 不基于 abstract

---

# 0. Audit Base · 6 Explore Agent 真 grounded 数据

## 0.1 后端 6 Agent api.py

| Agent | LLM caller | audit | session | D1 | D2 | D4 | force_mock |
|---|---|---|---|---|---|---|---|
| Agent1 channel | ✅ shared/llm_caller | finally hook | 内存 + TTL | ✅ | ✅ | ✅ | False |
| Agent3 credit | ❌ **直 OpenAI client** | finally hook | 内存 + TTL 30min | ✅ | ❌ | ✅ | False |
| Agent4 alert | ✅ shared/llm_caller | finally hook | **本地 JSON** | ✅ | ✅ | ✅ | False |
| Agent5 compliance | ✅ shared/llm_caller | **@decorator (bug #11)** | **本地 JSON** | ✅ | ❌ | ✅ | False |
| Agent6 report | ✅ shared/llm_caller | finally hook + sync log | 内存 + TTL | ✅ | ❌ | ✅ | False |
| Agent2 riskctrl | ✅ shared/llm_caller | **@decorator (bug #11)** | 无 | ✅ | ❌ | ✅ | False |

## 0.2 shared/ 核心 infra

- llm_caller: **Production-ready** · 9 file 用 · PIPL fallback chain (DeepSeek + DashScope)
- decision_ledger: **Production-ready** · sqlite + PII hash + 4 retention · 4 agent caller
- audit_service: **Production-ready** · 双层 sqlite + encrypt 可选 · silent-fail **是设计意图** (decorator catch · API 仍抛业务)
- shared/prompts/contract.py: **SKELETON · 全 _PENDING_A1_SPEC · 0 agent 调** (8 段 SSOT 完全没用)

## 0.3 前端 web/src/lib

- API client 完整 · 6 agent + auth + im 全有 client (channel/auth/im/alert/compliance/riskctrl/report .ts)
- LiveFailError + AuthApiError 标准化 · 不 silent
- 无 runtime schema 校验 (zod 没用)
- **Cache/Dedup/Abort: 0 实现** · SSE 无 abort · 僵尸连接风险
- auth-store 无 persist · 刷页 0.5s 闪屏

## 0.4 前端 web/src/app + 6 workspace

- 6 workspace 4-Gate state 协议一致
- CSS 三栏 grid 各自不同 · `.rpt-grid` CSS 已补 (注释是历史 · 需 E2E verify)
- Hero 命名不统一 (HeroSection / PrimaryProfileHero / ChannelHero / ReportHero / RiskHero)

## 0.5 CSS · UI 视觉

- tokens.css 4 主题完整 · shell.css 100% var(--*)
- 6 workspace CSS: 全 token (Report 423 var · Channel 407 · Alert 459 · Compliance 478 · Credit 445 · Riskctrl 182)
- **CustomerListClient 31 处 inline · PersonalFinancePanel 22 处 · DecisionPanel 18 处** = 71 处
- 圆角 token 缺 (workspace hardcode 8/12/999 · shell 用 --r-md)
- customer page inline 无 z-index · 与 PanelCanvas (z-44) 视觉重叠风险

## 0.6 6 Agent prompt (严格 grep)

- **8 段 SSOT 0 注入** (grep `contract.assemble` = 0 matches)
- Evidence 时效约束 0/6 agent prompt (grep `evidence_date` 0 / `last.*month` 0 / `freshness` 0)
- Agent6 仅 `_EVIDENCE_SYSTEM_PROMPT` 3 阶段半实装
- 其他 5 agent: hardcode string · 无 helper 接入

---

# Round 1 真辩论 (grounded)

## 1.1 Claude R1 lock (独立 · 看 6 Explore audit)

**Production blocker 6 件**:
1. 8 段 SSOT 0 注入 (银行合规无防线)
2. D2 freshness 4/6 没硬约束 (Agent3/5/6/2 prompt 无时效)
3. Agent3 LLM 没迁 shared/llm_caller (PIPL/audit/fallback 断层)
4. customer page 71 处 inline + 无 z-index (与 PanelCanvas 重叠风险)
5. 前端 0 cache/dedup/abort (SSE 僵尸连接)
6. auth-store 无 persist (刷页 0.5s 闪屏)

**修正 abstract R1 5 处误判**:
- ❌ "audit silent fail" → silent-fail 是**设计**不是事故
- ❌ "前端 API 散" → 6 agent + auth + im 全有 client · 仅 customer page 3 component 直 fetch
- ❌ ".rpt-grid 全坏" → CSS 已补 · 需 E2E verify
- ❌ "session_store 全内存" → Agent4/5 有 JSON 持久化
- ❌ "ai_decision mock" 概括 → 5/6 真接 LLM · Agent3 例外

## 1.2 Codex R1 lock (独立 · 抽样 grep)

**Production blocker** (6 件几乎一致 + 1 件):
- Prompt SSOT 是 #1 blocker (相同)
- D2 freshness 不闭环 (相同)
- Agent3 LLM 绕 shared/llm_caller (相同)
- 前端 runtime schema (zod) 缺 (Claude 没单列)
- SSE abort/dedup 缺 (相同)
- UI grid 塌陷需 E2E verify (相同 · 谨慎不可全凭注释)

**修正 abstract 5 处** (跟 Claude 重合):
- 后端 LLM infra 不是 "大面积未完成" · 已接近 production core
- "SSOT 已统一" 必推翻 (contract 文件存在 ≠ 生效)
- 前端不只 "美化债" · runtime schema/abort/dedup 是可靠性债
- UI grid 不可全凭注释定罪 · 需 E2E

**Critical gap "看起来 X 实际 Y"**:
1. 看起来有 contract · 实际 prompt 没 contract
2. 看起来有证据链 · 实际 freshness 不闭环
3. 看起来 TS 完整 · 实际运行时 payload 不受控

## 1.3 R1 互看 + Discuss

**双方共识**: 6 件 production blocker · 5 处 abstract 修正

**Claude 加 (Codex 没单列)**:
- customer page z-index 风险 (PM 之前反馈"气泡碰撞" 真原因)
- auth hydrate 闪屏

**Codex 加 (Claude 没单列)**:
- silent-fail 分级 taxonomy (user-facing/audit-facing/metrics-facing)
- E2E SSE 断连测试必跑 (静态 grep 不足)
- .next 构建产物是否吃到最新 CSS (需 verify)

**R2 各独立想 4 件**: 8 段 SSOT 落地 / D2 freshness prompt 文本 / silent-fail taxonomy 具体行为 / customer inline 抢救 plan

---

# Round 2 真辩论 (grounded)

## 2.1 Claude R2 (独立)

1. **8 段 SSOT 落地**: 先填 [safety][evidence-first][**output-schema**] · helper `build_system_prompt(agent_id, strict=True)` · 6 agent 调统一 helper · pytest assert pending=0
2. **D2 freshness prompt**: system 加 "evidence 必带 evidence_date · stale 不入核心" · user prompt 每 evidence 附 date 字段
3. **silent-fail taxonomy**: user-facing (banner) / audit-facing (sqlite 必落) / metrics-facing (本地 stderr OK)
4. **customer inline 抢救**: 71 处 inline → 3 个 .v-customer-* class · CSS 用 --ink/--chalk/--r-md token

## 2.2 Codex R2 (独立)

1. **8 段 SSOT 落地**: 先填 [safety][evidence-first][**agent-role**] · runtime check + tests (Python 不能 compile-time) · `tests/shared/test_prompts_contract.py` 扫 marker
2. **D2 freshness prompt**: 给具体文本 (`【证据新鲜度硬约束】当前运行日期 {run_date} · 每条 evidence 必带 evidence_date · stale 仅作背景 · 全 stale 降级"材料不足"`)
3. **silent-fail taxonomy**: 同 Claude 三级 + 具体行为 (audit-facing 必含 fallback_reason/source/evidence_date/freshness_score · metrics-facing 计数器 + span tag)
4. **customer inline 抢救**: 目标不是 0 inline · 是迁**静态视觉样式** · 保留 dynamic (width: ${pct}% / Recharts) · 加 lint/rg gate 防回退

## 2.3 R2 互看 + Discuss

**共识** (3/4):
- D2 freshness: Codex 给具体文本 · Claude 接受
- silent-fail taxonomy: 三级一致 + Codex 加具体行为
- customer inline: Codex "仅迁静态 + lint gate" 比 Claude "全迁 0 inline" 更 nuanced · Claude 接受

**1 处分歧**: 8 段 SSOT 第 3 段先填
- Claude: **output-schema** (直接影响 LLM 输出可解析)
- Codex: **agent-role** (6 agent 共用 + role 清晰后 schema 跟着)

**R3 各独立想 1 件 + 验收标准**

---

# Round 3 真辩论 (grounded · final)

## 3.1 R3 议题

1. R2 残余分歧: agent-role vs output-schema 谁先填
2. Tier 0 + Tier 1 验收标准

## 3.2 Codex R3 final

**Codex 接受 Claude output-schema** ✅:
> "R3 目标是先把系统从'能跑'推到'可判定正确'. agent-role 重要 · 但偏行为边界. output-schema 直接决定 6 agent 输出是否可解析/可合并/可审计. 没 schema · role 再清晰也留不可执行歧义."

**Tier 0 验收 (3 个 pytest)**:
1. `tests/test_ssot_prompts.py` · 断言 8 段 SSOT 存在 + 前 3 段 = safety/evidence-first/output-schema
2. `tests/test_freshness_prompt.py` · 输入过期/缺日期 evidence · 断言 D2 prompt 要求标注 freshness 风险 · 不允许静默通过
3. `tests/test_silent_fail.py` · 模拟 tool 返空/异常 · 断言同时产生 user-visible fallback + audit event + metrics counter

**Tier 1 验收 (3 个 pytest)**:
1. `tests/test_agent_output_contract.py` · 6 agent fixture 输出全部通过统一 schema 校验 · 非法/缺字段失败
2. `tests/test_inline_static_migration.py` · 静态 inline 已迁 · lint gate 对新增 inline 报错
3. `tests/test_end_to_end_auditability.py` · 跑一条完整 credit-report flow · 断言每个关键结论有 evidence id + freshness + agent source

**R4 不需要**: R3 已只剩排序分歧 · 接受 output-schema 后可直进执行 · R4 只消耗决策时间.

---

# 综合 verdict (grounded · 双方共识)

## A · 当前产品状态 (基于真 audit)

| 层 | 评级 | 关键 fact |
|---|---|---|
| 后端 LLM infra | **A-** | 5/6 真接 shared/llm_caller · ledger/audit production-ready · 仅 Agent3 遗留 |
| Phase C 模块 | **B+** | 12 模块 production-grade · 但 D2 应用率 2/6 · contract.py SKELETON |
| 前端 API client | **B** | 6 agent + auth + im 全有 client · 但 customer page 3 component 直 fetch · 0 cache/abort |
| 前端 UI/CSS | **B-** | 6 workspace 全 token · customer page 71 处 inline · 圆角混乱 |
| Prompt SSOT | **D** | 8 段 SSOT 0 注入 · 6 agent hardcode · evidence 时效约束 0 prompt |
| **总体** | **C+** | Demo + 部分 production-grade · 闭环不通 · 离 "实打实能跑" 还差 1-2 周 |

## B · Production Blocker 6 件 (双方 grounded 共识)

1. 8 段 SSOT 注入 (#1 critical · 银行合规底线)
2. D2 freshness 6 agent prompt 硬约束
3. Agent3 LLM 迁 shared/llm_caller
4. customer page 71 处 inline → CSS class (含 z-index 修)
5. 前端 zod runtime + AbortController + dedup
6. auth-store persist + hydrate guard

## C · ROI 排序 (grounded)

| # | 项 | 工期 | 验收 |
|---|---|---|---|
| 1 | contract.py 实装 [safety][evidence-first][output-schema] 3 段 + 6 agent 强制 | 1-2d | test_ssot_prompts.py |
| 2 | D2 freshness 6 agent prompt 硬约束 | 1d | test_freshness_prompt.py |
| 3 | Agent3 LLM 迁 shared/llm_caller | 0.5d | test_agent_output_contract.py |
| 4 | silent-fail 分级 (user/audit/metrics) | 0.5d | test_silent_fail.py |
| 5 | customer page 71 处 inline 整改 | 1d | test_inline_static_migration.py |
| 6 | 前端 zod + AbortController + auth persist | 1-2d | runtime contract |
| 7 | E2E SSE 断连 + .next CSS verify | 0.5d | playwright spec |

**Total**: ~6-8d (单 CLI sequential) · ~3-4d (并行)

## D · Critical Gap (Codex grounded · "看起来 X 实际 Y")

1. 看起来有 contract · **实际 prompt 没 contract** (contract.py SKELETON)
2. 看起来有证据链 · **实际 freshness 不闭环** (4/6 prompt 无时效)
3. 看起来 TS 完整 · **实际运行时 payload 不受控** (无 zod)
4. (Claude 加) 看起来 client 完整 · **实际新 component 仍直 fetch** (3 customer page)
5. (Claude 加) 看起来 audit OK · **实际 Agent5/2 latency 失真** (bug #11)

## E · PM 必拍 5 件

1. **Tier 0 顺序**: 接受 R3 共识 (safety + evidence-first + output-schema) · 还是改 (e.g. agent-role 优先)?
2. **Agent3 LLM 迁** 是否 Tier 1 内强制完成 · 还是允许后做?
3. **customer page inline 抢救**: 全迁 vs 仅静态迁 · PM 拍
4. **审计 Agent5/2 bug #11 修复优先级**: 现 audit 数据失真 · 何时修?
5. **E2E SSE 断连测试**: 是否进 CI gate 阻断 ship?

## F · 与之前 abstract 报告区别

| 之前 (abstract) | 现 (grounded) |
|---|---|
| "audit silent fail" 概括 | silent-fail 是设计意图 + Agent5/2 真 bug #11 latency 失真 |
| "前端 API 散乱无 client" | 6 agent + auth + im 全有 client · 仅 customer page 3 直 fetch |
| ".rpt-grid 全坏" | CSS 已补 · 需 E2E verify (谨慎) |
| "session_store 全内存" | Agent4/5 本地 JSON 持久化 · 1/3/6 内存 |
| "ai_decision mock" 概括 | 5/6 真接 LLM · 仅 Agent3 例外 |
| "前端只是美化债" | 实际是可靠性债 (zod + abort + dedup) |

---

**Source**: 6 Explore agent 真 audit + Codex 抽样 grep + Claude × Codex 真辩论 R1+R2+R3 全 converged
**Build**: 严格 grounded · 不基于 abstract
**File**: `docs/reset/product-readiness-grounded-2026-05-07.md`
**Signal**: PRODUCT-READINESS-GROUNDED-2026-05-07
