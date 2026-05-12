# W2-mock-test Progress (append-only)

> 接力 sub-agent 必读 · main session 监控源 · sub-agent checkpoint 每次 append 一段

<!-- 第一棒 sub-agent 在此 append 第一段 -->

## 2026-05-12 · scope-verify (第 1 棒) · claude-W2-mock-test

### What I did (sub-agent · 起手 7 件事)

1. 读 `_temp/w2-plan.md` 全文 (W2 plan SSOT · 306 行 · §1 scope + §2 12 必修 + §3.3 W2-mock-test 11 文件 scope + §3.4 W2-contract 不需 rationale + §4 D6-D10 5 工作日 + §5 3 risk + §6 12 DoD + §7 SSOT + §8 final rationale)
2. 读 `_temp/liuye-final-spec-v3.md` §6.3 (line 587-612 · demo path 70s 9 step + 并发优化 R10 · step 6→7 提前切 / step 7→8 hover preview chunked) + 附录 C (line 940-1014 · C.1 70s 9 step 时间预算表 + C.2.1 Tavily quota mock + C.2.2 LLM withRetry + C.2.3 ledger silent-fail outbox + C.3 hard gate 3 彩排 ±20% + 5 应急 dry-run ≥ 2) + §2 协议 (PermissionRequestEventPayload 字段 verbatim)
3. 读 老仓 root `D:\claude code\credit_report_agent_work\CLAUDE.md` §3.5 (5 原则 mock · 盲测/难度分层/真实锚定/脱敏/环境边界 · 6 Agent 数据归属表) + §3.5.1 (第 6 原则 evidence_date + 4 Tier + freshness SLA + 第 7 原则 PM Feedback → Regression 闭环) + §3.7.2 (Q-041 4 字段硬线: industry/geo/scale/similarity · 缺字段 = regression)
4. 读 `credit_matrix_next/CLAUDE.md` (Tier 3 前端 scoped · §4 selector EMPTY sentinel 硬验 · §8 IME guard · §9 a11y · Playwright 跑它 dev port 3210) + `liuye_service/CLAUDE.md` (Tier 3 BFF scoped · §3 SSE adapter 唯一兼容层 · §11 18 文件交付清单 · mock 形态源 · 注: §3 仍标 "10 event" stale · v3 spec + PM 2026-05-11 ratify 已纠正为 11 event 含 permission.request control-layer · permissions.py 直接 emit · 不走 sse_v1_to_liuye.py adapter)
5. 读 W1-contract 输出 5 schema (artifact 5 type + ArtifactPatch chunked 3 字段 / liuye_chat_event 11 event + TurnErrorPayload + PermissionRequestEventPayload / tool_call 8 status + ProgressMessage 5 status / kb_doc tier 1-4 + content_hash sha256 / evidence_ref freshness 3 enum + data_tier 1-4) + Zod inputSchemas + 5 fixture (shared/contracts/liuye/fixtures/* · 含 evidence_ref array 形态) + `docs/contracts/liuye-sse-event-matrix.md` v1.1 (11 event verbatim · PermissionRequestEventPayload 完整 payload 形态 = request_id + risk_tier + action + idempotency_key + required_persona? + disabled_reason? + reason_required? + rule_source? + scope? + explanation? + consequences? · 是我 3 PermissionRequest fixture 形态源)
6. 读 `docs/handoff/W1-mock-test-progress.md` 全文 5 棒累积 (棒 1 scope-verify · 棒 2 2 demo fixture · 棒 3 1 fixture + 3 mock SSE · 棒 4 2 contract spec + .gitignore · 棒 5 2 Playwright + 1 migration + tests/package.json 入库 · 关键 gotcha: Playwright 1.60 binary 1223 / dev port 3210 / tests/ 独立 npm pkg / 字体三路兜底 / IME 模拟限制 / selector EMPTY sentinel 当前 page.tsx 不消费 store · 真断言留 W2-W4 messages-shell 接入后 / Chromium binary ~112MB 跨 dev 重新拉)
7. 读 `docs/onboarding/W1-worker-handoff-protocol.md` §2 (30 min checkpoint 硬规) + §5 (5 字段 trailer + progress append-only 模板 · W2 沿用 · 仅替 W1- → W2-)

### 我理解 W2 mock-test scope (≤ 200 字)

我是 4 worker 并行第四棒 W2-mock-test · 估 8-10 工时 / 10-14 sub-agent 棒 30-45 min/棒 · 输出 = W2 demo path 端到端 verification gate + 彩排基线 + 5 应急 dry-run (W2 跑 2 + W3-W4 跑 3) + 3 PermissionRequest fixture. 11 文件全新 (不动 W1 已 ship): 1 demo-path-step4-9.spec.ts (扩 W1 step 1-3 至完整 9 step 70s · 步级 ±20% gate · 真消费 SSE 真渲组件) + 2 应急 spec (fallback-tavily-quota · fallback-ledger-silent-fail) + 3 彩排 spec (rehearsal-mock D9 · rehearsal-hybrid D10 per-adapter URL · rehearsal-live D10) + 1 step-budget.ts utility (saveBaseline JSON 写 _temp/w2-rehearsal-baseline.json) + 3 PermissionRequest fixture (a3_new medium · le05_sign high reason_required · kb_upload medium) + 1 baseline JSON 入库. 沿用 W1 5 原则 + 第 6 原则 + 老 v1.0 7 event mock SSE (不发 liuye 11 event · adapter 在 BFF). fixture SSOT 仍走 tests/fixtures/ 不双副本.

### PM ratify Q2 + W2 perfect-check fix #2 必跟

- **Q2 ratify (W1 PM 2026-05-11)**: 11 event 含 permission.request 是 control-plane (`permissions.py::emit_permission_request` 直接 emit · 不经 `adapters/sse_v1_to_liuye.py`) · 我 mock SSE server 仍走老 v1.0 7 event (W1 第 3 棒已实做 · profile_loaded / stage / stream / tool_call / tool_result / done / error) · 不发 liuye 11 event · 不动 W1
- **W2 perfect-check fix #2**: rehearsal-hybrid.spec.ts env per-adapter URL · channel mock fallback 走 `LIUYE_BACKEND_CHANNEL_URL=http://localhost:8001` (mock SSE :8001 复用 W1) + credit/report live fallback `LIUYE_BACKEND_BASE_URL=http://localhost:8000` (`LIUYE_BACKEND_CREDIT_URL` / `LIUYE_BACKEND_REPORT_URL` 留空) · W2-backend §4.1 `_resolve_backend_url(agent_id)` helper 走 `os.environ.get(f'LIUYE_BACKEND_{agent_id.upper()}_URL') or self.backend_url`

### 内部矛盾 / 漂移 (3 个 · 不阻塞但要主 session 知会)

1. **`liuye_service/CLAUDE.md` §3 仍标 "10 event" stale** (复述 W1-mock-test 棒 1 既已识别): v3 spec 主体 + PM 2026-05-11 ratify + `liuye-sse-event-matrix.md` v1.1 均已纠正为 11 event (加 permission.request control-plane) · backend scoped CLAUDE.md 表格仍写 "10 event 映射" 仅列 10 行 · 待主 CLI 后续在合适 sprint 补丁同步 · W2 不动它 (Tier 3 scoped · 修文档走 RFC) · W2-backend 棒可能也独立踩
2. **W1 progress 第 3 棒提到 v16 5 stage vs `v16_pipeline.py` 3 step (classifier/generator/QC) 漂移**: W1-mock-test 已确认 5 stage_label 是展示层 SSOT (per v3 §6.3 demo path 派生) · 不是后端实际 pipeline step · W2 mock-test demo-path-step4-9 step 4 (A1-NEW-1 IdealProfile 12 维) + step 6 (F-067-handoff Credit) + step 7 (F-053 progressive radar + 4 row 评分) 不直接消费 v16 5 stage_label · 走 turn.progress event stage_label 中文外显 + key 进 tooltip (per v3 §4 必修 #27 + #46) · 不动 W1 fixture (report_v16_PARTIAL.json 已含 5 stage 完整 stage_log)
3. **W2-backend §4.1 `_resolve_backend_url` helper 实做细节** vs **W2 plan §3.1 backend file checklist**: brief 给的 helper 实做行 `os.environ.get(f'LIUYE_BACKEND_{agent_id.upper()}_URL') or self.backend_url` 是 Python · W2-backend worker (并行第二棒) 负责落地 · W2-mock-test (我) 通过 Playwright `process.env` 覆写传给 frontend dev server / backend uvicorn `spawn` env · 我 rehearsal-hybrid.spec.ts 走 `test.use({...})` 或 `process.env.LIUYE_BACKEND_CHANNEL_URL='http://localhost:8001'` (Node 写入) + Playwright fork 子进程时 inherit env · 验 backend `/api/channel/run` 真接 :8001 mock SSE · 不验 `_resolve_backend_url` 本身 (那是 backend pytest scope)

### File checklist 状态 (11 文件 + 1 baseline JSON · 12 path 全 W2-mock-test scope)

- [ ] tests/e2e/playwright/demo-path-step4-9.spec.ts (第 2-4 棒 · 6 step 完整 · 主 fixture 最复杂)
- [ ] tests/e2e/playwright/fallback-tavily-quota.spec.ts (第 5-6 棒 · 附录 C.2.1)
- [ ] tests/e2e/playwright/fallback-ledger-silent-fail.spec.ts (第 6-7 棒 · 附录 C.2.3 · UI 显「已提交·上链中」乐观更新)
- [ ] tests/e2e/playwright/rehearsal-live.spec.ts (第 9-10 棒 · D10 · 3 adapter 全 live · skipIf backend health 失败)
- [ ] tests/e2e/playwright/rehearsal-mock.spec.ts (第 8 棒 · D9 · 9 step + saveBaseline · 走通是 W2 sign-off 硬线)
- [ ] tests/e2e/playwright/rehearsal-hybrid.spec.ts (第 9 棒 · D10 · per-adapter URL · channel mock + credit/report live)
- [ ] tests/perf/step-budget.ts (第 2 棒 · withBudget + saveBaseline + STEP_BUDGETS 9 step 常量 · ±20% gate)
- [ ] tests/fixtures/permission_request_a3_new.json (第 3 棒 · medium · A3-NEW Decision submit · idempotency_key uuid placeholder)
- [ ] tests/fixtures/permission_request_le05_sign.json (第 3 棒 · high · LE-05 签字 · reason_required=true · compliance_officer)
- [ ] tests/fixtures/permission_request_kb_upload.json (第 3 棒 · medium · KB upload · pipl region overseas 触发场景)
- [ ] _temp/w2-rehearsal-baseline.json (第 8 棒 · JSON array 起手 · D9-D10 实际 baseline append)

### Next 棒 (第 2 棒 · 30-45 min) 预计交付

- `tests/e2e/playwright/demo-path-step4-9.spec.ts` 主 fixture (step 4 IdealProfile 12 维 + step 5 拖 artifact + step 6 Credit handoff + step 7 progressive radar · 4 step) · 用 W1 demo-path-step1-3.spec.ts 同样模式扩 (test.step + Date.now() 差值 + budget 断言) + `tests/perf/step-budget.ts` withBudget utility 起手 (STEP_BUDGETS 9 step 常量 + ±20% hardLimit + saveBaseline append `_temp/w2-rehearsal-baseline.json`)
- 估 30-45 min · step-budget.ts 是公用 utility 必先起 · 之后 6 step demo-path spec 复用同一 withBudget(name, fn) 调用模式 · 主难点 = mock SSE :8002 (credit) + :8003 (report) 真起 + W1 frontend 接 useLiuyeBridge hook 后才能验真 SSE consumer 渲组件 (但 W2-frontend 同 W2 并行 · 我跑 spec 时 frontend skeleton 仍 W1 状态 · step 4-7 真渲断言留 W2-frontend 棒接 11 event UI 后 spec 可强断言 · 当前用 console.log + isMockSseAlive() probe + step-budget 时间断言三路替代)
- 不写 fixture (第 3 棒) · 不写应急 spec (第 5-7 棒) · 聚焦 demo path 核心 6 step 扩展

### Blocker
- 无

### ELAPSED min: ~32 (起手 7 件事 · 写 progress + scope verify segment + commit 准备)
### Commit SHA: (本 commit · git log 下一行)
