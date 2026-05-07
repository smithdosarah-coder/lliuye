# HANDOFF · TO NEXT MAIN CLI · 2026-05-07 (Phase C Production Hardening)

> **PM 指令**: 这个 window 太久 · 重启新主 CLI · 100% 承接当前任务. 新窗口第一句 paste:
> **「读 AGENT_IDENTITY.md 和里面列的所有文件 · resume 状态后等我指令。」**

---

## 0. 一句话定位

**当前阶段**: Phase C 产品就绪度提升 · 把"看起来能演"改成"实打实能跑产品"
**最新 commit**: `d936dad` (PB#1 全 ship · 8 段 SSOT 注入完整)
**production**: `https://liuye.me/login` · 4 主题 + 6 Agent + 5 角色 RBAC 全 live
**评级**: C+ (per `docs/reset/product-readiness-grounded-2026-05-07.md`)

---

## 1. 必读 (按顺序 · ~15 min)

1. **`CLAUDE.md`** (项目规范 · 自动加载) — §3.5.1 加 #6 数据时效双轨规则 · §13.1 改完即部署 · §15 SSOT 优先级
2. **`docs/reset/product-readiness-grounded-2026-05-07.md`** ⭐ — 本次 grounded 真辩论 11 节 (Claude+Codex R1+R2+R3 · 6 Explore audit) · 含修正 5 处 abstract 误判 · Top 1 risk · ROI · PM 必拍 5 件
3. **`docs/reset/phase-c-charter-2026-05-06.md`** — Phase C 4 Track 19 件 charter (Week 1-4 全 ship · ABCD)
4. **`docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_2026-05-02.md`** — 上一次 handoff · Q-047 视觉冻结 · 5 跑偏 root cause 硬规
5. **`docs/handoff/decisions-log.md` tail -80** — 最近 PM 拍板

---

## 2. 今晚累计 ship (~4h · 6 commits)

| Commit | What | Status |
|---|---|---|
| `0664a87` | **Tier 0** · ai_decision honest (`mock-v1.0` → `rule-fallback-no-llm`) + API envelope mode/degraded/reason + production fail-fast startup | ✅ live |
| `1f99bea` | **PB#1 Step 1+2** · `shared/prompts/contract.py` 实装 [safety][evidence-first 含 freshness][output-schema] 3 段 + `build_system_prompt(agent_id, ...)` helper | ✅ live |
| `d936dad` | **PB#1 Step 3+4** · `shared/prompts/agent_helpers.py` 6 agent BUILDERS + `tests/shared/test_ssot_prompts.py` 14/14 PASS | ✅ live |
| 之前更早 (今天 5/7 累计) | Phase C charter + grounded report · PM 6 bug 修 · ModePill toggle · CrossAgentWorkflow 紧凑 · 画布 button archive only | ✅ live |

## 3. 当前 production blocker 状态

| # | 项 | 状态 | 工期 |
|---|---|---|---|
| **PB#1** 8 段 SSOT 注入 | ✅ contract.py 实装 + helper + pytest · **但 6 Agent LLM call site 未真用** | (剩 ~1d 真应用 · 也算 PB#2 范围) |
| **PB#2** D2 freshness 6 Agent prompt 真应用 | ⏳ contract 段已写 · 6 Agent build 入口已建 · 但 6 Agent 现 LLM call 还用 hardcode SYSTEM_* | 1d |
| **PB#3** Agent3 LLM 迁 shared/llm_caller | ⏳ Agent3 是唯一仍用旧 OpenAI client · 5/6 已迁 | 0.5d |
| **PB#4** customer page 71 处 inline → CSS class | ⏳ CustomerListClient 31 + PersonalFinancePanel 22 + DecisionPanel 18 | 1d |
| **PB#5** 前端 zod runtime + AbortController + auth persist | ⏳ TS 类型完整 · 但 runtime payload 不受控 + SSE 僵尸连接 + 刷页闪屏 | 1-2d |

**总剩**: ~3.5-4.5d 单 CLI · ~2-3d 并行

---

## 4. PM 5/7 verbatim 关键指令 + 红线

### 关键拍板
- **目标转**: "目标已经不能放在跑通 demo · 现在的目标是真正可用的产品"
- **辩论真定义** (PM 5/7): 双方独立思考 → 互看方案 → discuss 差异 (= 1 轮) · 重复 3 轮
- **审视必看代码**: PM 5/7 verbatim "你和 codex 都单独看所有代码 · 重新进行三轮辩论"
- **Tier 0 + PB#1 ship 后**: PM "做一个 KT" → 即本 handoff

### 红线 (新主 CLI 必守)
- ❌ **不再自加 UI 没问 PM** (PM 5/7 反馈 "为什么被你改的这么丑 · 你动 UI 设计出方案了吗 · 问过我了吗")
- ❌ **不动视觉** (Q-047 视觉冻结 baseline = phase-b-start-2026-05-01)
- ❌ **不写 abstract 报告假装真辩论** (必基于真 audit · 6 Explore 或类似)
- ❌ 不 scp 改 ECS production file (CLAUDE.md §13)
- ❌ 不绕 PM 拍直接动 UI (CLAUDE.md "方案先行 · 视觉/CSS 类任务额外规则")
- ✅ 改完即部署 (CLAUDE.md §13.1 · 默认 default · 不等 PM 触发)
- ✅ 真双辩论必含: 双方独立 + 互看 + discuss

---

## 5. PM 工作偏好 (per CLAUDE.md global · 必守)

- **不谄媚** · 不夸 PM 想法 · 不开头加"当然可以"
- **默认中文** · 代码/命令/变量名英文
- **结论先行** · verdict 在前 · 不铺垫
- **terse 默认** · 长输出仅 PM 明确要求
- **审计/review/体检类**: 开头 1 句 verdict + 3-5 bullet · 不大段散文
- **多档建议给分级** · 高/中/低 ROI 或 🔴🟡🟢
- **commit 粒度 = TaskCreate 粒度** · 一件即 commit · 不批量

---

## 6. Codex 协作 protocol (Q-043 v2 · 实测)

**最佳实操**:
- ✅ short prompt + low reasoning effort = 健康 (~5-30s 回)
- ❌ medium reasoning + 长 prompt = 易 stuck (今晚 4 次 stuck · 后续避免)

**真双辩论流程** (per PM 5/7 定义):
1. Claude 独立 lock R1 (不告诉 codex 我立场)
2. Fire codex with ONLY 命题 (不暗示 Claude 立场)
3. 收到 codex R1 → 比对差异 → 写 discussion
4. R2/R3 同样 (双方独立 + 互看 + discuss)

---

## 7. 5 个 critical gap "看起来 X 实际 Y" (grounded report)

| # | 看起来 X | 实际 Y | 状态 |
|---|---|---|---|
| 1 | 有 contract | prompt 没 contract | ✅ 已修 (PB#1) |
| 2 | 证据链完整 | freshness 不闭环 (4/6 Agent prompt 无 evidence_date) | 🟡 contract 段已写 · 6 Agent 真应用待 (PB#2) |
| 3 | TS 类型完整 | runtime payload 不受控 (无 zod) | ⏳ PB#5 |
| 4 | client 完整 | 新 component 直 fetch (customer page 3 个) | ⏳ PB#4 |
| 5 | audit OK | Agent5/2 latency 失真 (bug #11 @decorator pattern) | ⏳ 未排 |

---

## 8. 关键文件路径快查

### 报告 + charter
- `docs/reset/product-readiness-grounded-2026-05-07.md` ⭐ 本次 grounded 真辩论
- `docs/reset/phase-c-charter-2026-05-06.md` ⭐ Phase C 4 Track 19 件
- `docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_2026-05-07.md` ⭐ 本 handoff
- `docs/handoff/decisions-log.md` Q/A 历史

### 今晚 ship 关键代码
- `shared/prompts/contract.py` — 8 段 SSOT 实装 [safety][evidence-first][output-schema]
- `shared/prompts/agent_helpers.py` — 6 agent BUILDERS · build_*_ssot_prompt()
- `shared/api_envelope.py` — { ok, data, error, meta } envelope · 4 状态 mode
- `shared/production_check.py` — 启动 fail-fast 5 项 check
- `shared/ai_decision.py` — metadata.model 改 honest "rule-fallback-no-llm"
- `tests/shared/test_ssot_prompts.py` — 14/14 PASS · 锁死 SSOT
- `api_server.py` — 4 critical endpoint 返 envelope · /api/_/health 暴露 startup

### 6 Agent backend
- `agent_channel/api.py` (BE12 personal_insight 真接 LLM)
- `agent_credit/api.py` (旧 OpenAI client · PB#3 待迁)
- `agent_alert/api.py` + `agent_compliance/api.py` (本地 JSON 持久化)
- `agent_report/api.py` (v16 主管线 · session_store 内存)
- `agent_riskctrl/api.py` (DSL · audit @decorator bug #11)

### 前端
- `web/src/lib/api/{channel,auth,im,alert,compliance,riskctrl,report}.ts` — 7 client (LiveFailError standardized · 但无 zod)
- `web/src/lib/store/auth-store.ts` — 无 persist (PB#5 待加 hydrate guard)
- `web/src/app/customer/[id]/_components/{PersonalFinancePanel,DecisionPanel,CustomerListClient}.tsx` — 71 处 inline (PB#4 待整改)
- `web/src/app/today/_components/TodayContent.tsx` — 4 RoleHome + CrossAgentWorkflow (今晚紧凑改)
- `web/src/components/shared/ModePill.tsx` — 6 workspace 一致 + 真 toggle

---

## 9. PM 必拍 5 件 (Tier 0 ship 后 · per grounded report §I)

新主 CLI 第一组动作: 按必读读完 → 跑 git log → 等 PM 拍这 5 件:

1. **下一步执行**: PB#2 (1d · D2 freshness 6 Agent prompt 真应用) · 还是 PB#3 (0.5d · Agent3 LLM 迁) · 还是 PB#4 (1d · customer inline 整改) · 还是 PB#5 (1-2d · 前端 zod+abort+persist)
2. **PB 顺序**: 单 CLI sequential 跑 · 还是 multi-cli-mesh 并行 (charter §13 RACI · ~2-3d 并行)
3. **A1 5 角色分流首页 toC 措辞**: 是否做 (PM 5/7 之前未明确拍 · 现 in_progress task)
4. **A4 AI 输出客户口径**: Sprint 6 LLM 真接后做 (现 mock fallback 跑)
5. **客户走访时机**: 是否近期 · 影响 PB 优先级

---

## 10. Resume 后第一组动作 (新主 CLI 必跑)

```bash
# 1. 看最近 commit
git log --oneline -20

# 2. 看 production HEAD
git log origin/main -1 --oneline

# 3. 看 decisions-log 最近 80 行
tail -80 docs/handoff/decisions-log.md

# 4. 看 mesh status (worker 状态)
py "C:/Users/Mr.S/.claude/skills/multi-cli-mesh/scripts/orchestrator/scoreboard.py" 2>/dev/null || echo "scoreboard 未启 · 单 CLI 模式 OK"

# 5. 跑 SSOT pytest verify
cd "D:/claude code/credit_report_agent_work" && py -m pytest tests/shared/test_ssot_prompts.py -v
```

然后停下汇报理解 · 等用户指令. **样例汇报**:

```
Resume 完成 · KT 100% 承接.

我是: main CLI · 主分支 main · D:/claude code/credit_report_agent_work
最新 commit: d936dad (PB#1 全 ship)
production: https://liuye.me/login · 评级 C+ (grounded report)

今晚累计: Tier 0 (audit/envelope/metadata) + PB#1 (8 段 SSOT 注入 · 14/14 PASS)

剩余 production blocker:
- PB#2 6 Agent 真用 SSOT (1d) ← 我建议接着做
- PB#3 Agent3 LLM 迁 (0.5d)
- PB#4 customer 71 inline 改 (1d)
- PB#5 前端 zod+abort+persist (1-2d)

PM 必拍 5 件 (见 handoff §9):
1. 下一步执行 PB# 哪个?
2. 单跑 vs 并行?
3. A1 RoleHome toC?
4. A4 LLM 真接时机?
5. 客户走访时机?

待你指令。
```

---

## 11. 危险区 / 之前踩过的坑 (新主 CLI 避免)

1. **抽象 audit 不严谨** — 我之前 R1 R2 R3 没真看代码 · 5 处误判 · PM 5/7 反馈 "你们辩论的基础是都详细看过了前端后端的代码吗" · 后用 6 Explore 真 audit 修正
2. **自加 UI 没问 PM** — Sprint 4 D1 Atomic 5 加 CrossAgentWorkflowCard · PM 5/7 verbatim "为什么被你改的这么丑 · 问过我了吗" · 后我紧凑重写 + 承诺"动 UI 必先 3 行 plan 问 PM"
3. **codex bg 长 prompt + medium reasoning stuck** — 4 次 stuck · 改 short + low 即健康
4. **辩论假独立** — 之前我给 codex 我的方案让 codex 反应 · 不是真独立 · PM 5/7 verbatim "我要的是各自独立思考 + 互看 + discuss" · 真辩论必各方独立先 lock
5. **ECS deploy github timeout** — 网络问题非代码 · skip retry · 跨境网络抖动期 (per §13)

---

## 12. ECS 部署 (per CLAUDE.md §13.1 · 改完即部署默认)

```bash
bash scripts/deploy_to_ecs.sh                # 完整 (含 web build · 5-10 min)
bash scripts/deploy_to_ecs.sh --skip-build   # 仅 backend restart (Python 改)
```

---

## 13. 新加 Production Endpoint 完整清单 (Phase C + Tier 0)

### 健康检查 (Tier 0.1 新)

```
GET /api/_/health
  → { mode, ok, checks: [{name, ok, detail}], failures: [...] }
  · 5 项 startup check (llm_caller / LLM key / decision_ledger / audit dir / ledger dir)
```

### 客户画像 (Phase C Track A · A1 · 用 envelope)

```
GET /api/customer/list?rm=RM-王哲
  → envelope { ok, data: { items: [...] }, meta }

GET /api/customer/{id}/profile
  → envelope { ok, data: { customer, history, holdings, ... }, meta }
  · consent != granted → meta.mode=degraded reason="customer-consent-pending"
```

### AI 决策建议 (Phase C Track A · A2 · 用 envelope)

```
POST /api/decision/build
  body: { customer_id, intent }
  → envelope · 现 LLM 未接 · meta.mode=degraded reason="llm-not-wired-rule-fallback"
  → ai_decision metadata.model = "rule-fallback-no-llm" (Tier 0.3 honest)
```

### 人工确认 (Phase C Track A · A3)

```
POST /api/decision/{decision_id}/review
  body: { decision_id, reviewer, action, reason, modified_content }
  · action: accept / modify / reject
  · modify/reject 必带 reason ≥ 5 字符

GET /api/decision/{decision_id}/reviews
  → { decision_id, status, reviews: [...] }
```

### 走访导出 (Phase C Track A · A5)

```
POST /api/decision/{decision_id}/export
  body: { decision_id, format }  // format: docx / pdf
  → 文件流下载
```

### 数据血缘 (Phase C Track B · B2)

```
GET /api/lineage/decision/{decision_id}
  → envelope · 一笔决策的所有字段血缘

GET /api/lineage/field?path=customer.income_monthly
  → envelope · 跨决策的字段血缘 timeline

GET /api/lineage/stats
  → envelope · 全局血缘统计 (by tier + by system)
```

### 业务指标 (Phase C Track C · C1)

```
GET /api/metrics/business?days=30&rm=RM-王哲
  → envelope · 现 review_events 内存 store · meta.mode=degraded reason="metrics-source-in-memory"
  · 5 指标: closure_rate / stuck_distribution / manual_intervention_rate / client_confirm_rate / revenue_after_adoption
```

### Agent3 → Agent6 回写 (Phase C Track A)

```
POST /api/report/v16/inject
  body: { report_id, decision_id, decision_summary, advisor_notes }
  · ledger 上链 + session_store update review_notes + audit log
```

### 6 Agent 现有 endpoint (Phase A/B 累计)

详见 `agent_*/api.py`:
- agent_channel: /api/channel/run · /personal_insight/{id} · /handoff
- agent_credit: /api/credit/decision · /demo/run · /export_docx · /reports/sessions
- agent_alert: /api/alert/scan · /batch_scan · /drill/{id}
- agent_compliance: /api/compliance/policy_scan · /policy_diff · /matrix_check
- agent_report: /api/report/v16/fill · /upload · /refine · /export_docx
- agent_riskctrl: /api/riskctrl/dsl_gen · /backtest · /demo/run

---

## 14. Codex 4 个 stuck task (今晚遗留)

| ID | 任务 | 状态 |
|---|---|---|
| `br38ki3xq` | Sprint 5 batch | 🔴 stuck (medium 长 prompt) |
| `bk4dxldhr` | xlsx feasibility verify | 🔴 stuck |
| `b78aj8iz7` | 7 件 batch verify | 🔴 stuck |
| `b9ageki4b` | 短 codex verify · 早期 stuck | 🔴 stuck |

新主 CLI 不要 wait 这 4 个 · 直接 fire 新 codex (short + low) 即可.

---

**Authored**: Main CLI · 2026-05-07 (commit d936dad close-out)
**File status**: `.gitignore` 已屏蔽 worktree-local 文件
**Signal**: HANDOFF-2026-05-07-PHASE-C-PB1-DONE
