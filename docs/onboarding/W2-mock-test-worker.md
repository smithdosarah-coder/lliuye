# W2 Mock-Test Worker · Onboarding Brief

> **worker 代号**: `claude-W2-mock-test`
> **任务**: W2 Phase 1 端到端 demo path · 扩 demo-path step 4-9 (full 9 step 70s) + 5 应急 dry-run spec + 3 彩排基线 (live/mock/hybrid) + 3 PermissionRequest fixture + step 级耗时 ±20% gate (11 文件 · 全新)
> **依据**: `_temp/w2-plan.md` §3.3 + v3 spec §6.3 (demo path 70s 9 step) + 附录 C (3 fallback + hard gate + checklist · line 940-1014) + 老仓 root `CLAUDE.md` §3.5 (mock 5 原则) + §3.5.1 (第 6/7 原则)
> **估时**: ~8-10 工时 (W2 D6 ~ D10 · 10-14 sub-agent 棒 30-45 min/棒)
> **版本**: v1.0 (W2 brief writer 写 · 2026-05-12)

---

## 1. 身份 + 起手

**你是**: W2 mock-test worker · 3 worker 并行第三棒 · 你的输出 = W2 demo path 端到端 verification gate + 彩排基线 + 5 应急 dry-run.

**依赖**:
- W1 mock-test 11/11 DONE (3 demo fixture + 3 mock SSE :8001/:8002/:8003 + 2 contract spec + 2 Playwright smoke + migration spec · `tests/` 全 ship · Chromium 1223 binary 已装)
- W1 contract 14/14 DONE (5 schema + Zod + 5 fixture · 复用 `tests/contract/payload-shape.spec.ts` 验 W2 新 fixture)
- W2 backend 同 W2 并行 (你跑 spec 时其 live mode 真接 backend / 失败走 mock fallback)
- W2 frontend 同 W2 并行 (你 Playwright 跑它的真渲组件 · 验 11 event UI 真渲)

**第一件事 (开工前必做)**:
1. 读 `D:\claude code\_temp\w2-plan.md` (W2 plan 全 · 8 章 + 12 必修 + D6-D10 + 5 risk)
2. 读 `D:\claude code\credit_report_agent_work\docs\onboarding\W1-mock-test-worker.md` (W1 brief 模板源)
3. 读 `D:\claude code\credit_report_agent_work\docs\handoff\W1-mock-test-progress.md` (W1 mock-test 5 棒累积 gotcha · 重点第 5 棒 sign-off)
4. 读 `D:\claude code\_temp\liuye-final-spec-v3.md` §6.3 (demo path 70s 9 step · 含并发优化 R10) + 附录 C (3 fallback + demo hard gate + 现场 checklist · line 940-1032) + §2.1 (11 event)
5. 读 老仓 root `CLAUDE.md` §3.5 (5 原则 mock) + §3.5.1 (第 6 原则 evidence_date + 4 Tier + freshness SLA + 第 7 原则 PM Feedback → Regression 闭环)
6. 读 `credit_matrix_next/CLAUDE.md` + `liuye_service/CLAUDE.md` (你 Playwright 跑前端 · live mode 接后端)
7. **读 `docs/onboarding/W1-worker-handoff-protocol.md` §2 + §5** · W2 沿用 · 你不是 8-10h 单 session · 是接力赛 · 每 30 min 必 checkpoint + 写 `docs/handoff/W2-mock-test-progress.md`
8. 写 "我理解 W2 mock-test scope" 一段 (≤ 200 字) 给 main session verify · 没漂再开干

## 2. 输入文件清单

| 文件 | 用途 | 必读章节 |
|---|---|---|
| `_temp/w2-plan.md` | W2 plan SSOT | §3.3 W2-mock-test scope + §5 risk + §6 DoD |
| `docs/onboarding/W1-mock-test-worker.md` | W1 brief 模板源 | 全 (你的 brief 是它的 W2 延伸) |
| `docs/handoff/W1-mock-test-progress.md` | W1 mock-test 5 棒累积 gotcha | 第 5 棒 (Playwright + migration + tests/package.json 入库 · 决策 1-6) |
| `_temp/liuye-final-spec-v3.md` | v3 spec | §6.3 (demo path 70s 9 step + 并发优化 R10) + 附录 C (3 fallback + hard gate + checklist) + §2.1 (11 event) |
| 老仓 root `CLAUDE.md` | 全局工程纪律 | §3.5 (5 原则 mock) + §3.5.1 (第 6/7 原则) |
| `credit_matrix_next/CLAUDE.md` | 前端 scoped | §8 IME + §9 a11y · Playwright 跑它 |
| `liuye_service/CLAUDE.md` | BFF scoped | §3 SSE adapter 11 event + §4 Cowork/Managed |
| `docs/contracts/liuye-architecture.md` | Tier 1 SSOT | 全 |
| `shared/contracts/liuye/schemas/*.json` | 5 协议 (验 fixture 用) | artifact.schema.json 主 |
| W1 5 fixture (`tests/fixtures/*.json` + `shared/contracts/liuye/fixtures/*.json`) | 复用基础 + 3 新 permission fixture 套同样模式 | 全 |

## 3. W2 file checklist (11 文件 · 全新)

```
credit_report_agent_work/tests/e2e/playwright/demo-path-step4-9.spec.ts         (扩 W1 step1-3 → 完整 9 step · 70s 预算 · ±20% gate)
credit_report_agent_work/tests/e2e/playwright/fallback-tavily-quota.spec.ts     (LIUYE_DEMO_MODE=mock 切换 · channel mock fallback)
credit_report_agent_work/tests/e2e/playwright/fallback-ledger-silent-fail.spec.ts (ledger 写失败 outbox enqueue + UI 显「已提交 · 上链中」乐观更新)
credit_report_agent_work/tests/e2e/playwright/rehearsal-live.spec.ts            (live 彩排 · 3 adapter 全 live · Tavily + DeepSeek + sqlite 真路径)
credit_report_agent_work/tests/e2e/playwright/rehearsal-mock.spec.ts            (mock 彩排 · 3 mock SSE + DEMO_MODE=1)
credit_report_agent_work/tests/e2e/playwright/rehearsal-hybrid.spec.ts          (hybrid 彩排 · channel mock + credit/report live · 边界验)
credit_report_agent_work/tests/perf/step-budget.ts                              (step 级耗时 utility · ±20% gate · _temp/w2-rehearsal-baseline.json 输出)
credit_report_agent_work/tests/fixtures/permission_request_a3_new.json          (A3-NEW Decision submit · medium · 客户经理 idempotency_key)
credit_report_agent_work/tests/fixtures/permission_request_le05_sign.json       (LE-05 签字 · high · reason_required=true · 合规官)
credit_report_agent_work/tests/fixtures/permission_request_kb_upload.json       (KB upload · medium · idempotency_key)
credit_report_agent_work/_temp/w2-rehearsal-baseline.json                       (3 彩排 step 级耗时 JSON 基线 · 主 session ack 时入库)
```

## 4. 关键纪律

### 4.1 9 step demo path 70s 时间预算 (v3 §6.3 + 附录 C.1)

W1 mock-test 第 5 棒已实做 step 1-3 (静默首页 / 点 chip / F-066 Channel SSE) · W2 扩 step 4-9:

| step | 动作 | 预算 | hard gate (±20%) | 关键测试点 |
|---|---|---|---|---|
| 1 | F-007 静默首页加载 | 3s | 2.4-3.6s | bootstrap GET (cached) · W1 已实做 |
| 2 | 点「🔍 找合适企业」chip | 1s | 0.8-1.2s | client only · W1 已实做 |
| 3 | F-066 Channel SSE ranked 5 候选 | 15s | 12-18s | Tavily + LLM rerank · W1 已实做 |
| 4 | A1-NEW-1 IdealProfile 12 维抽取 | 10s | 8-12s | LLM call · 12 维 progressive section |
| 5 | 拖 artifact 到 composer 生成 reference chip | 2s | 1.6-2.4s | client only · drag-drop |
| 6 | F-067-handoff Credit SSE | 15s | 12-18s | LLM + tool chain · parent_tool_call_id 透传 |
| 7 | F-053 progressive radar + 4 row 评分 | 10s | 8-12s | tail of step 6 SSE · 大字 92 + 4 small badge |
| 8 | A3-NEW confirm modal「提交并上链」 | 5s | 4-6s | ledger 写入 + idempotency_key · PermissionRequest medium |
| 9 | LE-01 trace modal 弹审计链 | 5s | 4-6s | trace GET · decision → tool_call → artifact → evidence |
| **总** | | **66s** | **≤ 79.2s** | **预算 +20% 80s · 留 70s buffer 4s · 客户走访 ≤ 70s** |

**并发优化 (R10)**:
- step 6 → step 7 提前切换 (turn.started 后) · 不等 turn.completed
- step 7 → step 8 hover preview (chunk_assembly=streaming 时 disabled · final 后 enable)

### 4.2 step 级耗时 utility (`tests/perf/step-budget.ts`)

```typescript
import {test, expect} from '@playwright/test';

export const STEP_BUDGETS = {
  step1: 3000,
  step2: 1000,
  step3: 15000,
  step4: 10000,
  step5: 2000,
  step6: 15000,
  step7: 10000,
  step8: 5000,
  step9: 5000,
} as const;

export async function withBudget(name: keyof typeof STEP_BUDGETS, fn: () => Promise<void>) {
  const budget = STEP_BUDGETS[name];
  const hardLimit = budget * 1.2;  // ±20% gate
  const start = Date.now();
  await test.step(name, fn);
  const elapsed = Date.now() - start;
  console.log(`[step-budget] ${name}: ${elapsed}ms / budget ${budget}ms (utilization ${(elapsed/budget*100).toFixed(1)}%)`);
  expect(elapsed).toBeLessThanOrEqual(hardLimit);
  return elapsed;
}

export async function saveBaseline(spec: string, perStep: Record<string, number>) {
  const totalElapsed = Object.values(perStep).reduce((a, b) => a + b, 0);
  const baseline = {
    spec,
    timestamp: new Date().toISOString(),
    perStep,
    totalElapsed,
    totalBudget: Object.values(STEP_BUDGETS).reduce((a, b) => a + b, 0),
    utilization: (totalElapsed / Object.values(STEP_BUDGETS).reduce((a, b) => a + b, 0)) * 100,
  };
  // append to _temp/w2-rehearsal-baseline.json
  const fs = await import('fs');
  const path = '../../_temp/w2-rehearsal-baseline.json';
  const existing = fs.existsSync(path) ? JSON.parse(fs.readFileSync(path, 'utf-8')) : [];
  existing.push(baseline);
  fs.writeFileSync(path, JSON.stringify(existing, null, 2));
}
```

### 4.3 3 彩排 spec (附录 C.3 hard gate)

W2 必跑 3 次完整路径彩排 (live / mock / hybrid 各 1 次):

**(1) `rehearsal-mock.spec.ts`** (D9 跑 · 走通是 W2 sign-off 硬线):
- env: `LIUYE_DEMO_MODE=1` (DEMO_MODE on) · 3 mock SSE :8001/:8002/:8003 起
- 跑完整 9 step · 各 step 用 `withBudget` 包 · saveBaseline 写 `_temp/w2-rehearsal-baseline.json`
- 预期: 总耗时 < 70s · 各 step ±20% 内 · 9 step 全 PASS

**(2) `rehearsal-hybrid.spec.ts`** (D10 跑 · perfect-check fix #2 · per-adapter URL 覆写):
- env: `LIUYE_DEMO_MODE=0` + `LIUYE_BACKEND_CHANNEL_URL=http://localhost:8001` (channel 走 mock SSE :8001 · 复用 W1 mock-test fixture replay) + `LIUYE_BACKEND_CREDIT_URL` / `LIUYE_BACKEND_REPORT_URL` 留空 fallback `LIUYE_BACKEND_BASE_URL=http://localhost:8000` (credit/report live 真 backend uvicorn :8000) · 见 W2-backend §4.1 `_resolve_backend_url` helper
- 验 mock + live 混用边界 (channel mock fallback 走 fixture · credit/report live 真接 LLM)
- 预期: 总耗时 < 70s + 4s buffer (live LLM 慢一点) · channel mock 提示 chip 显「Demo 模式」

**(3) `rehearsal-live.spec.ts`** (D10 跑):
- env: `LIUYE_DEMO_MODE=0` · 3 adapter 全 live · Tavily + DeepSeek + sqlite ledger 真路径 · 真 backend uvicorn :8000
- 预期: 总耗时 < 70s + 4s buffer · 5 应急流程不触 (sanity check live 健康)
- skipIf backend health probe 失败 (`isBackendAlive()` per W1 mock-test pattern)

### 4.4 5 应急 dry-run spec (W2 跑 2 · W3-W4 跑 3)

W2 D8 必写 + 跑:

**(1) `fallback-tavily-quota.spec.ts`** (附录 C.2.1):
- 模拟 Tavily 返 429 / quota 耗尽 (mock backend response)
- 验: `LIUYE_DEMO_MODE=mock` 自动切换 · channel adapter 走 fixture · UI 显 chip 「Demo 模式」灰 badge
- 后续 step 4-9 不受影响 (channel 给 candidate · credit / report 真接)

**(2) `fallback-ledger-silent-fail.spec.ts`** (附录 C.2.3):
- 模拟 ledger sqlite write fail (mock `sqlite3.OperationalError`)
- 验: silent-fail · decision flow 不破 · event 进 `data/liuye/outbox/` · outbox worker 60s 重试 5 次
- UI confirm modal 显「已提交 · 上链中」乐观更新 (不显失败)
- 端到端: A3-NEW Decision submit medium PermissionRequest → grant → ledger fail → outbox enqueue → confirm modal 乐观显 → 不阻断 step 9 LE-01 trace

**W3-W4 跑剩 3** (留 brief 不写):
- (3) F-053 LLM provider fallback chain (`withRetry max=1 backoff=2s` + `FallbackTriggeredError`)
- (4) SSE adapter conversion failed (`SSE_ADAPTER_FAILED fallback_available=true` + snapshot 重拉)
- (5) network offline cached snapshot (本地 IndexedDB 显最近 snapshot)

### 4.5 3 PermissionRequest fixture (W2 backend live test 复用)

**`permission_request_a3_new.json`** (medium · A3-NEW Decision submit):
```json
{
  "id": "pr_a3_new_001",
  "request_id": "pr_a3_new_001",
  "risk_tier": "medium",
  "action": "credit_decision_submit",
  "idempotency_key": "<uuid4>",
  "required_persona": ["reviewer"],
  "rule_source": "policy.ledger_write",
  "scope": "once",
  "explanation": "本次决策将写入 decision_ledger · 用于审贷会留底 · 不可撤销",
  "consequences": ["写入 ledger jurisdiction=HQ retention=standard 5y", "通知审贷员二次确认"]
}
```

**`permission_request_le05_sign.json`** (high · LE-05 签字 · reason_required):
```json
{
  "id": "pr_le05_001",
  "request_id": "pr_le05_001",
  "risk_tier": "high",
  "action": "ledger_review_signature",
  "idempotency_key": "<uuid4>",
  "required_persona": ["compliance_officer"],
  "reason_required": true,
  "rule_source": "policy.rbac",
  "scope": "once",
  "explanation": "合规官签字将固化 decision · 签字后 24 小时内可申诉 · 之后冻结",
  "consequences": ["LedgerReviewEvent append-only", "签字事件存档 5 年", "向监管报告 (jurisdiction=银)"]
}
```

**`permission_request_kb_upload.json`** (medium · KB upload):
```json
{
  "id": "pr_kb_upload_001",
  "request_id": "pr_kb_upload_001",
  "risk_tier": "medium",
  "action": "kb_doc_upload",
  "idempotency_key": "<uuid4>",
  "required_persona": ["rm", "reviewer"],
  "rule_source": "policy.pipl",
  "scope": "once",
  "explanation": "上传文档进 KB · tier 自动分级 · 跨境数据 (overseas) 需 PIPL 合规审计",
  "consequences": ["KBDoc 入库 (content_hash sha256)", "PIPL audit log 写入 region 字段"]
}
```

**硬规** (W1 mock-test 5 原则沿用 + 第 6 原则):
- 严格遵守 `shared/contracts/liuye/schemas/liuye_chat_event.schema.json` PermissionRequestEventPayload 4 必填 + 7 optional
- idempotency_key 留 `<uuid4>` placeholder · spec 跑时真生成
- 不发明字段 · 不改 schema

### 4.6 5 原则 + 第 6 原则沿用 (W1)

- 盲测 / 难度分层 / 真实锚定 / 脱敏 / 环境边界 (W1 已 PASS · W2 沿用)
- 第 6 原则 evidence_date + data_tier + freshness SLA (W1 fixture 已含 · W2 不动)
- 第 7 原则 PM Feedback → Regression 闭环 (W2 彩排基线 JSON 入库 · main session 比对 3 baseline · 漂移 >±20% 触发 PM 介入)

### 4.7 Playwright config 沿用 + 加 webServer 协调

W1 mock-test 第 5 棒 `tests/e2e/playwright/playwright.config.ts` 已实做 (Chromium 1.60 · headless 默认 · baseURL :3210 · workers=1).

**W2 加固**:
- `webServer` block 仍 disabled (per W1 第 5 棒决策 #3 · 避免端口冲突)
- 但 W2 加 `globalSetup.ts` (新文件 · per W2 plan §5.3 mitigation):
  - 跑 spec 前 probe :3210 (frontend) + :8001/:8002/:8003 (mock SSE) + :8000 (backend optional · live 模式才需要)
  - 任一不通 = 视情况 skip (mock 彩排只需 :3210 + :8001-3 · live 彩排需 + :8000)

### 4.8 不准做 / 别越界

- ❌ 不准发明 fixture 字段 (字段来自 5 schema · 不一致找 contract worker 对齐 · 不自改)
- ❌ 不准 import `agent_*` 内部模块 (跨边界)
- ❌ 不准跳过 5 原则 + 第 6 原则验证
- ❌ 不准 mock SSE server 用 liuye 11 event (用老 v1.0 · adapter 在 backend · W1 第 3 棒已实做 · W2 不动)
- ❌ 不准 fixture evidence 缺 `evidence_date` / `data_tier` (第 6 原则硬线)
- ❌ 不准跳过 step ±20% hard gate (附录 C.3 verbatim)
- ❌ 不准 W2 跑 5 应急 dry-run 全 5 (W2 跑 2 · W3-W4 跑 3 · per W2 plan §6 必修 #12)

## 5. 输出 DoD (Definition of Done)

- ✓ 11 文件全 Write 完成 · path 与 §3 1:1 一致
- ✓ `demo-path-step4-9.spec.ts` 跑通 (9 step 完整 · 各 step ±20% gate 全过 · 真消费 SSE 真渲组件)
- ✓ `fallback-tavily-quota.spec.ts` + `fallback-ledger-silent-fail.spec.ts` 跑通 (2 应急 dry-run · backend + frontend 全栈 round trip)
- ✓ 3 彩排 spec 跑通 (`rehearsal-mock.spec.ts` D9 mock · `rehearsal-hybrid.spec.ts` + `rehearsal-live.spec.ts` D10)
- ✓ step 级耗时 utility 跑通 + baseline JSON 输出 (`_temp/w2-rehearsal-baseline.json` 3 baseline 入库)
- ✓ 3 PermissionRequest fixture 通过 `payload-shape.spec.ts` (W1 contract spec 复用 · 验 PermissionRequestEventPayload schema)
- ✓ 9 step demo path 总耗时 < 70s (mock 彩排) / < 74s (hybrid · live · LLM 慢) · 各 step ±20% 内
- ✓ commit trailer 含 `MOCK-TEST-W2-DELIVERED: 11/11` + `PLAYWRIGHT-PASS: 6/6` + `STEP-BUDGET: all-within-20%` + `REHEARSAL: 3/3 (mock+hybrid+live)` + `EMERGENCY-DRY-RUN: 2/5` + `5原则-PASS: ok (沿用 W1)` + `第6原则-PASS: ok (沿用 W1)`
- ✓ codex independent review 通过 (root §3.7.4 protocol v2)

## 6. W2 末 sign-off 流程

1. **PR 创建**: `feat/liuye-W2-mock-test` 分支 → PR to `main` · title `[W2-mock-test] demo-path 9 step + 5 应急 dry-run 2/5 + 3 彩排基线 (live/mock/hybrid)`
2. **codex review** (root §3.7.4):
   ```
   codex exec -c 'model_reasoning_effort="medium"' \
     --search \
     "Review W2 mock-test worker PR. Check 1) 9 step demo path Playwright spec 真消费 SSE 真渲 (extends W1 step1-3) 2) 5 应急 dry-run 2/5 (Tavily quota + ledger silent-fail · W3-W4 跑剩 3) 3) 3 彩排 spec (live/mock/hybrid) + step 级耗时 ±20% gate 4) 3 PermissionRequest fixture (medium A3-NEW / high LE-05 reason_required / medium KB upload) 5) baseline JSON 入库 (_temp/w2-rehearsal-baseline.json) 6) 沿用 W1 5 原则 + 第 6 原则. Verdict: GO / NO-GO."
   ```
3. **commit trailer** (root §13.5):
   ```
   MOCK-TEST-W2-DELIVERED: 11/11
   PLAYWRIGHT-PASS: 6/6
   STEP-BUDGET: all-within-20%
   REHEARSAL: 3/3 (mock+hybrid+live)
   EMERGENCY-DRY-RUN: 2/5
   5原则-PASS: ok (沿用 W1)
   第6原则-PASS: ok (沿用 W1)
   REVIEW-MODE: codex
   REASONING-EFFORT: medium
   ELAPSED: <min>
   ```
4. **PM ack**: PM 业务专家 review (root §3.5.1 第 7 原则) + 看 baseline JSON · ack 后 W3 才能用 fixture 跑客户走访彩排 W5-W6

## 7. 估时 + 风险点 (file-level)

| 文件 | 估时 | 风险点 |
|---|---|---|
| `demo-path-step4-9.spec.ts` | 2.5h | 9 step 完整 · step 4 (12 维 progressive) + step 6 (Credit handoff parent_tool_call_id) + step 8 (PermissionRequest medium modal) 真渲断言 · 各 step ±20% gate |
| `fallback-tavily-quota.spec.ts` + `fallback-ledger-silent-fail.spec.ts` | 1.5h | mock backend response (Tavily 429 / sqlite OperationalError) · UI 显「Demo 模式」/「已提交·上链中」断言 |
| `rehearsal-mock.spec.ts` | 1h | DEMO_MODE=1 全栈 + 3 mock SSE 起 + 9 step 跑 · saveBaseline JSON 写 |
| `rehearsal-hybrid.spec.ts` + `rehearsal-live.spec.ts` | 1.5h | 混用边界 (channel mock + credit/report live) · live 模式 backend health probe · skipIf 优雅降级 |
| `tests/perf/step-budget.ts` | 0.5h | `test.step` API + `Date.now()` 差值精度 · saveBaseline JSON 文件 atomic write |
| 3 PermissionRequest fixture | 0.5h | PermissionRequestEventPayload schema 4 必填 + 7 optional · idempotency_key placeholder · risk_tier 准确分级 |
| `_temp/w2-rehearsal-baseline.json` (空 + header) | 0.1h | JSON array 起手 · 主 session ack 时 D9-D10 实际 baseline append |

**风险 mitigation**:
- D6 第一件事: 验 W1 mock-test 基础 OK (`cd tests && npm ci && playwright install chromium && npm run smoke:all` 验 W1 11/11 仍 PASS · 不破)
- step 级耗时 utility: 先单 spec 跑 (`rehearsal-mock.spec.ts`) · 验 saveBaseline JSON 写入正常 · 再扩 6 spec
- 9 step 完整 spec: 写完 step 4 → 跑通 → 再写 step 5 → 增量 commit · 不一口气写 6 step 后才跑
- live 彩排: D10 才跑 · 前置 W2 backend live mode + W2 frontend 真渲全 PASS · 任一不到 = skip live 走 mock baseline

## 8. 不准做 / 别越界

- ❌ 不准发明 fixture 字段 / 改 schema (找 contract worker 对齐 · W1 schema 已 lock)
- ❌ 不准 mock SSE server 改 11 event (用老 v1.0 · adapter 在 backend · W1 已 ship)
- ❌ 不准跳过 5 原则 + 第 6 原则 + 第 7 原则 闭环
- ❌ 不准跳过 step ±20% hard gate
- ❌ 不准 W2 跑 5 应急 dry-run 全 5 (W2 跑 2 · W3-W4 跑 3)
- ❌ 不准跳过 codex review
- ❌ 不准动 W1 已 ship 文件 (3 fixture / 3 mock SSE / 2 contract spec / 2 Playwright smoke / migration spec / playwright.config.ts / tests/package.json) · 任何改动走 W2 backend / frontend / contract worker scope · 不在 mock-test 改

## 9. 引用 SSOT

| Tier | 文件 |
|---|---|
| 1 | `docs/contracts/liuye-architecture.md` |
| 1 | `_temp/liuye-final-spec-v3.md` (§6.3 + 附录 C + §2.1) |
| 1 | `docs/contracts/sse-envelope.md` v1.0 (mock SSE server 形态源 · W1 已实做) |
| 2 | 老仓 root `CLAUDE.md` (§3.5 5 原则 + §3.5.1 第 6/7 原则) |
| 3 | `credit_matrix_next/CLAUDE.md` (frontend scoped · Playwright 跑它) |
| 3 | `liuye_service/CLAUDE.md` (BFF scoped · live SSE 源) |
| 4 | W1-mock-test-worker brief (模板源) |
| 4 | **本文件** (W2-mock-test brief) |
| 5 | `docs/handoff/W1-mock-test-progress.md` (W1 5 棒累积 gotcha · 重点第 5 棒决策) |
| 5 | `_temp/w2-plan.md` §3.3 (W2-mock-test scope SSOT) |
| 上游 input | W1 contract 14/14 DONE · W1 mock-test 11/11 DONE · W2 backend 同 W2 并行 (live mode 真接源) · W2 frontend 同 W2 并行 (真渲组件 selector 验) |
