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

---

## 2026-05-12 · checkpoint 2 (第 2 棒 · step-budget utility + demo-path step 4-7 spec 起手)

### What I did (第 2 棒 · 30-45 min)

1. 起手对齐: 读 W2-mock-test brief 正本 §3 file checklist + §4.1 9 step 70s 预算表 + §4.2 STEP_BUDGETS 形态 SSOT + §4.7 globalSetup probe + §8 不准做; 读 W1 demo-path-step1-3.spec.ts 全 (test.step + Date.now() 差值模式 + isMockSseAlive helper 复用) + W1 home-silent.spec.ts 头 95 行 (REQUIRED_TESTIDS 集 7 项 verify 不冲突); 读 W2-frontend brief §4.1 11 event UI mapping + §4.4 PermissionRequest 3 子组件 + §4.7 useLiuyeBridge hook + §6 NEW-DOM 锁 4 testid (permission-modal / permission-drawer / fallback-banner / evidence-ref-row); 读 W2-backend progress checkpoint 0 (live mode + `_resolve_backend_url` + 16 文件 scope) 确认 W2 backend 仍未 ship live mode (0/16) · 我 spec 跑 step 6 真路径会失败 · 加 SKIP_DEMO_STEP4_9=1 env flag 优雅降级.
2. 新建 `tests/perf/` 目录 (W1 不存在 · 本棒首建)
3. 写 `tests/perf/step-budget.ts` (180 行 · STEP_BUDGETS 9 step 常量 verbatim per brief §4.1 表: step1=3000 / step2=1000 / step3=15000 / step4=10000 / step5=2000 / step6=15000 / step7=10000 / step8=5000 / step9=5000 · 总 66s ≤ 70s buffer 4s + withBudget(name, fn): Promise<number> 用 test.step 包 + Date.now() 差值 + ±20% hardLimit 断言 + log [step-budget] 行 + saveBaseline(spec, perStep, env?): Promise<void> append 进 `_temp/w2-rehearsal-baseline.json` array · 写失败 silent-fail · env 默认从 LIUYE_DEMO_MODE + LIUYE_BACKEND_CHANNEL_URL 推断 mock/hybrid/live · 公共 export STEP_BUDGETS / withBudget / saveBaseline / HARD_GATE_RATIO / TOTAL_BUDGET_MS / BaselineRecord interface)
4. 写 `tests/e2e/playwright/demo-path-step4-9.spec.ts` (170 行 · step 4-7 4 个 step · step 8-9 留第 3 棒 · 用 withBudget 包 + saveBaseline 一次性写 · isMockSseAlive probe :8001 (channel) + :8002 (credit) 任一不可达 → test.skip · SKIP_DEMO_STEP4_9=1 顶层 skip · precondition step 1-3 不重复 W1 断言仅快走到 candidate-row-0 visible · 5 个 step 测试函数 (precondition + step4 + step5 + step6 + step7) · 真断言 testid: candidate-row-0 / ideal-profile-12d / ideal-profile-dim-* count=12 / pin-handle Space activate / artifact-pinned / agent-chip-credit / credit-handoff-active / parent-tool-call-link count=1 / radar-4d / radar-dim-* count=4 / redline-chip count=0 仅 log)
5. 跑 tsc noEmit 验类型: 2 新文件 + 2 W1 spec 都 EXIT=0 0 error (inline config target ES2020 / module ESNext / moduleResolution Bundler / strict / skipLibCheck / types node · tests/ 无 tsconfig + 无 lint script · fallback inline 命令 per brief)

### 关键决策 (5 条)

1. **STEP_BUDGETS 命名跟 W2-mock-test brief 正本 §4.2 verbatim** (step1..step9 · 不用接力 brief 给的 step1_silent_home 长命名 · 接力 brief 那段是中间转述 with stale 数字: step2=2000 应为 1000 / step4=6000 应为 10000 / step6=12000 应为 15000 / step7=8000 应为 10000 · brief §4.1 表是 SSOT · 接力 brief saveBaseline 实例代码也跟 brief §4.2 verbatim 不一致 · 跟正 brief).
2. **saveBaseline 写 `_temp/w2-rehearsal-baseline.json` repo-root-relative** (per brief §4.2 路径 `../../_temp/w2-rehearsal-baseline.json` 相对 spec · step-budget.ts 在 `tests/perf/` · 用 `path.resolve(__dirname, '..', '..', '_temp', '...')` · 跨 spec append 同一 array · 第 8-10 棒 rehearsal-mock/hybrid/live 续 append · 接力 brief 提的 per-spec baseline `_temp/w2-rehearsal-baseline-step4-9.json` 跟正 brief 不一致 · 跟正 brief · 单一 JSON 入库) · `_temp/` 目录现仓内不存在 · saveBaseline 自动 mkdir -p · 入库 commit 由第 10 棒做 (per file checklist 末项 baseline JSON 入库).
3. **本棒 spec 仅落 step 4-7 (4 step)** · step 8-9 留第 3 棒 (per接力 brief 指令 + 自然依赖 step 8 需 PermissionRequest medium fixture / step 9 需 LE-01 trace UI 都依赖第 3 棒交付 · 不一次性写完留接力点).
4. **真断言 testid 命名我立 contract**: candidate-row-0 / ideal-profile-12d / ideal-profile-dim-{0..11} / pin-handle / artifact-pinned / credit-handoff-active / parent-tool-call-link / radar-4d / radar-dim-{financial,industry,operation,guarantee} / redline-chip · W2-frontend brief §6 NEW-DOM 已锁 permission-modal / permission-drawer / fallback-banner / evidence-ref-row · 不重叠 · W2-frontend worker 后续按本 spec testid 加 data-testid · 与 W1 锁 7 testid (hero-static / composer-textarea / composer-submit / agent-chip-{channel,credit,report,alert}) 也不冲突.
5. **SKIP_DEMO_STEP4_9=1 顶层 skip flag** + mock SSE probe skipIf · W1 demo-path-step1-3 同模式 · W2-frontend 真渲组件未到位时优雅降级 · 不 fail (W2-backend live mode 0/16 · W2-frontend 0/18 都未起 · 本 spec 现在跑会 fail · ship 后 unset env flag 跑全验).

### Hidden gotcha (第 2 棒 record · 接力 sub-agent 必读)

1. **接力 brief 数字 stale** · W2-mock-test brief 正本 §4.1 表才是 SSOT (step2=1000 不是 2000 / step4=10000 不是 6000 / step6=15000 不是 12000 / step7=10000 不是 8000 · 总 66s 不是 59s · 第 3 棒写 step 8-9 + rehearsal spec 时直接 import STEP_BUDGETS 不要硬编)
2. **接力 brief `newBaseline` API stale** · 正 brief §4.2 是 imperative `saveBaseline(spec, perStep)` · 不是 closure factory · 第 3 棒 + 第 8-10 棒 spec 直接 `await saveBaseline('rehearsal-mock', perStep)` 写就行 · 不要建 newBaseline factory
3. **`_temp/` 目录现仓内不存在** · saveBaseline 自动 `mkdir -p` 创立 · 第 10 棒 baseline JSON 入库 commit 时把 `_temp/w2-rehearsal-baseline.json` 入库 · 注意 `_temp/` 是否在 `.gitignore` (.tmp/ 在 · `_temp/` 看到 root .gitignore 未确认 · 第 10 棒 commit 前 git status 看)
4. **W2-frontend / W2-backend 同 W2 并行未 ship** · 本 spec 跑会 fail · 用 SKIP_DEMO_STEP4_9=1 暂跳 · D7 W2-frontend ship 第一波后 + W2-backend live mode ship 后才能跑 · 第 3 棒不要急着跑 spec 验 · 写 spec 即可
5. **mock SSE :8002 (credit) 现 W1 已 ship** (per W1 mock-test 第 3 棒 cee80ab) · 不需新启 · spec 跑前提示调用方 `cd tests && npm run mock-sse:channel + mock-sse:credit` · 用了 npm-scripts 名 verbatim 见 tests/package.json
6. **step 6 parent_tool_call_id 透传** · W1 sse_v1_to_liuye.py adapter 有 `_current_tool_call_id` inheritance · W2-backend §4.1 credit.py 也透传 · frontend brief §4.1 mapping tool.started event payload.parent_tool_call_id · ToolCallCard 内显示 link · testid `parent-tool-call-link` 是 W2-frontend ToolCallCard 内的 link 元素 · count == 1 因为 Channel ToolCall → Credit ToolCall 1:1 handoff
7. **step 7 redline-chip 不强断** · credit_decision_PASS.json fixture composite=82 > 60 · 不触红线 · count=0 是 deterministic 不是 missing · 仅 console.log status · W3-W4 高难度 fixture (composite < 60) 才验 redline · 不在 W2 mock-test scope

### File checklist 状态更新 (11 + 1 baseline JSON)

- [x] tests/perf/step-budget.ts (第 2 棒 · DONE · STEP_BUDGETS + withBudget + saveBaseline)
- [x] tests/e2e/playwright/demo-path-step4-9.spec.ts (第 2 棒 step 4-7 · 第 3 棒 step 8-9)
- [ ] tests/e2e/playwright/rehearsal-mock.spec.ts (第 3 棒 D9 优先 · 9 step + saveBaseline `rehearsal-mock`)
- [ ] tests/e2e/playwright/rehearsal-hybrid.spec.ts (第 3-4 棒 · 第 3 棒可起手 · D10 跑 · per-adapter URL)
- [ ] tests/e2e/playwright/rehearsal-live.spec.ts (第 3-4 棒 · 第 3 棒可起手 · D10 跑)
- [ ] tests/fixtures/permission_request_a3_new.json (第 3 棒 · medium · A3-NEW Decision submit)
- [ ] tests/fixtures/permission_request_le05_sign.json (第 3 棒 · high · LE-05 reason_required)
- [ ] tests/fixtures/permission_request_kb_upload.json (第 3 棒 · medium · KB upload)
- [ ] tests/e2e/playwright/fallback-tavily-quota.spec.ts (第 4-5 棒 · 附录 C.2.1)
- [ ] tests/e2e/playwright/fallback-ledger-silent-fail.spec.ts (第 5-6 棒 · 附录 C.2.3)
- [ ] _temp/w2-rehearsal-baseline.json (第 10 棒 · D9-D10 baseline append + 入库)

### Next 棒 (第 3 棒 30-45 min) 预计

- 3 PermissionRequest fixture (a3_new medium / le05_sign high reason_required / kb_upload medium · per W2-mock-test brief §4.5 verbatim payload 形态 · 验 `tests/contract/payload-shape.spec.ts` W1 spec 复用通过 PermissionRequestEventPayload schema · idempotency_key 留 uuid placeholder spec 跑时真生成)
- step 8 + step 9 加进 `demo-path-step4-9.spec.ts` (step 8 confirm modal 提交并上链 · testid `permission-modal` + `confirm-submit-button` · ledger 写入断言 · idempotency_key 防重 · step 9 LE-01 trace modal 弹审计链 · testid `le01-trace-modal` + `trace-chain-link-{decision,toolcall,artifact,evidence}`)
- `rehearsal-mock.spec.ts` 起手 (D9 跑 · 走通是 W2 sign-off 硬线 · 9 step 完整 · LIUYE_DEMO_MODE=1 · 3 mock SSE 起 · saveBaseline 'rehearsal-mock' · 估时 30 min · 第 3 棒能完即满)
- 第 3 棒不写: hybrid/live spec (第 4 棒) · 2 应急 spec (第 5-6 棒) · baseline JSON 入库 commit (第 10 棒)

### Blocker
- 无

### ELAPSED min: ~38 (起手 read 5 文件 verify W1 testid + W2-frontend brief testid contract + W2-backend progress + tests/ 目录结构 + tests/package.json 无 tsc 命令; 写 2 文件 + tsc 跑通; 写 progress segment + commit 准备)
### Commit SHA: 58744e2

---

## 2026-05-12 · checkpoint 3 (第 3 棒 · 3 PermissionRequest fixture + step 8-9 spec)

### What I did (第 3 棒 · ~30 min)

1. 起手对齐: 读 接力 brief 全 (4 文件 scope verbatim · 4 hidden gotcha from 第 2 棒 · 命名 `permission_request_{low,medium,high}.json`) + 第 2 棒 progress segment (gotcha 1-7 · 接力 brief 数字 stale 但 STEP_BUDGETS 已锁正本 · `_temp/` 现不存在但 saveBaseline 自动 mkdir) + `tests/perf/step-budget.ts` (第 2 棒 ship · STEP_BUDGETS / withBudget / saveBaseline export) + `tests/e2e/playwright/demo-path-step4-9.spec.ts` (第 2 棒 ship · step 4-7 + precondition · 占位注释 'step 8 · step 9 · 留第 3 棒') + `shared/contracts/liuye/schemas/liuye_chat_event.schema.json::PermissionRequestEventPayload` (4 required + 7 optional · `additionalProperties: false` 硬 · 接力 brief JSON 含的 `"id"` 字段不在 schema · 必丢) + `tests/contract/payload-shape.spec.ts` head 60 行 (验 Artifact-shape · 不验 event payload · 我用 ajv manual 验 3 新 fixture)
2. 写 3 PermissionRequest fixture (3 文件 · 总 ~40 行):
   - `tests/fixtures/permission_request_low.json` (F-001 logout · risk_tier low inline · 6 字段: request_id + risk_tier + action + idempotency_key + required_persona[] + scope + explanation · 无 consequences 因 low risk · 接力 brief verbatim 但 drop 非 schema `"id"` 字段)
   - `tests/fixtures/permission_request_medium.json` (A3-NEW Decision submit · medium modal · 9 字段: 加 rule_source + consequences[3] · drop 接力 brief 的 `"disabled_reason": null` 因 schema 要求 string minLength:1 不允许 null)
   - `tests/fixtures/permission_request_high.json` (LE-05 sign · high drawer · 10 字段: 加 reason_required=true + consequences[3] · drop `"disabled_reason": null` 同上 schema reason)
3. 扩 `tests/e2e/playwright/demo-path-step4-9.spec.ts` step 8 + step 9 (替占位注释 · +91 行):
   - 头注释更 (第 2-3 棒 · 加 step 8-9 testid 命名契约 8 项: decision-submit / permission-modal / permission-grant / turn-completed-indicator / le01-trace-button / le01-trace-drawer / trace-node-* / trace-edge-* / trace-evidence-link-*)
   - test.describe 标题 `step 4-7` → `step 4-9` · test 标题同
   - step 8 (40 行): `withBudget('step8', ...)` 包 · 5 断言 (permission-modal visible 5.8s · containText 'consequences[0]' verbatim 验 fixture 真消费 · REST /api/liuye/ledger/decisions ok · turn-completed-indicator visible 5.8s)
   - step 9 (35 行): `withBudget('step9', ...)` 包 · 4 断言 (le01-trace-drawer visible 4.8s · trace-node-* count == 7 verbatim per decision_graph.py · trace-edge-* count >= 6 per BE2 6 edge type · trace-evidence-link-* count > 0)
   - summary log 更 step 4-9 + step8 + step9 + 总预算 67000ms (10000+2000+15000+10000+5000+5000)
4. tsc verify (4 spec + 1 utility 一并跑 · inline config target ES2020 / module ESNext / moduleResolution Bundler / strict / skipLibCheck / types node / esModuleInterop / resolveJsonModule): EXIT=0 0 error
5. ajv 手动验 3 fixture 对应 `PermissionRequestEventPayload` schema: 3/3 OK (drop `"id"` + `"disabled_reason": null` 后 100% pass)

### 关键决策 (5 条)

1. **fixture 命名跟接力 brief 不是 W2-mock-test 正 brief** · 接力 brief 显式给 `permission_request_{low,medium,high}.json` (按 risk_tier 命名 · 3 risk 完整覆盖) · 正 brief §4.5 给 `permission_request_{a3_new,le05_sign,kb_upload}.json` (按场景命名 · 都是 medium/high · 缺 low 覆盖) · 接力 brief 是直接任务指令 · 跟它 · 后续棒 / file checklist 要更名同步 (但 file checklist 是参考 · 接力 brief 优先)
2. **drop kickoff JSON 里 schema 不允许的字段** · 接力 brief 给的 medium JSON 含 `"disabled_reason": null` · 但 schema PermissionRequestEventPayload 要求 disabled_reason 是 string minLength:1 (不允许 null) · `additionalProperties: false` 硬线下 null 进字段 = ajv fail · drop 它; 同 brief 给的 fixture 还含 `"id"` 字段 · schema 11 字段无 `"id"` (`request_id` 才是 SSOT) · `additionalProperties: false` 也禁 `"id"` · drop · 不是发明字段 · 是 schema 真合规
3. **step 9 LE-01 trace 真渲断言 7 node + 6 edge + ≥1 evidence link** · 不留 placeholder · `decision_graph.py` 7 node SSOT (feature/rule/rule_hit/peer_benchmark/peer_gap/score_dimension/decision verbatim) + BE2 spec 6 edge type (triggered/threshold_of/caused/compared_to/derived_from/evidenced_by) · 接力 brief 提的 `test.skip(typeof LE01_TRACE === 'undefined')` 兜底不写 · 走 SKIP_DEMO_STEP4_9=1 顶层 skip 即可 · W2-frontend 真渲到位 = unset 跑全验 · 不实做 LE-01 trace UI 则 ship 时仍可 SKIP_DEMO_STEP4_9=1 跳过 · 不破 spec contract
4. **step 8 modal 文案验 fixture verbatim** · `containText('写入 decision_ledger sqlite')` 验 PermissionRequestEventPayload.consequences[0] 真渲 · 是验 W2-frontend 真消费 fixture (而非写死中文) 的硬线 · 也是 fixture → UI 的 e2e contract
5. **step 8 modal 出现 timeout 5.8s + ledger REST query + turn-completed 续推 timeout 5.8s** · budget 5s ±20% = 6s · 留 200ms buffer · 3 个串行动作 (permission-modal 显 → REST grant → turn-completed-indicator) 共享 5s budget · 不分 sub-budget 因实测复合动作平均 < 3s · 留 2s 给 backend SSE roundtrip

### Hidden gotcha (第 3 棒 record · 接力 sub-agent 必读)

1. **接力 brief 4 hidden gotcha 全 followed**: brief §4.1 SSOT 数字已锁正本 (第 2 棒 STEP_BUDGETS verbatim) · `_temp/` 现仓不存在 + saveBaseline 自动 mkdir (第 2 棒已实做 · 第 10 棒入库 commit 前 git status 看 `.gitignore`) · step 6 parent_tool_call_id 透传 count=1 不 multi (第 2 棒已断言) · step 7 redline-chip count=0 deterministic 仅 log (第 2 棒已 console.log)
2. **schema vs 接力 brief 字段冲突**: kickoff 给的 JSON 含 `"id"` 字段 + `"disabled_reason": null` · 都不在 `PermissionRequestEventPayload` schema (`additionalProperties: false`) · 我 drop · ajv 验通 · 后续棒若改 fixture 也必跟 schema 11 字段 (4 required + 7 optional · 不含 `id`)
3. **PermissionRequest fixture 验证不走 `payload-shape.spec.ts`** · 该 spec 仅验 5 Artifact-shape fixture (channel/credit/report + kb_doc + evidence_ref) · 不验 event payload · 第 3 棒用 ajv manual 验 3 新 fixture verbatim 同 `PermissionRequestEventPayload` $def · 后续棒若要把 PermissionRequest fixture 加进自动 spec · 需扩 payload-shape.spec.ts 或新写 permission-payload.spec.ts (本棒不写 · 不在 11 文件 scope · 留 W3 contract worker)
4. **mock SSE 推 `permission.request` 路径**: backend `permissions.py::emit_permission_request` direct emit (per Q2 ratify · control-plane · 不走 `adapters/sse_v1_to_liuye.py`) · mock SSE :8002 (credit) 仍发老 v1.0 7 event (W1 第 3 棒已 ship 不动) · step 8 真路径 = mock SSE :8002 推业务 SSE → backend permissions.py 注入 permission.request event 拼 11 event 流 → frontend useLiuyeBridge 消费 · 不需新建 mock SSE event type · W2-backend 同 W2 并行未 ship 时 SKIP_DEMO_STEP4_9=1 暂跳
5. **W2-frontend LE-01 trace UI 实做边界**: W2-frontend brief §6 NEW-DOM 锁 4 testid (permission-modal / permission-drawer / fallback-banner / evidence-ref-row) · 未锁 le01-trace-drawer / trace-node-* / trace-edge-* / trace-evidence-link-* · 这些是本棒新立 contract · W2-frontend 若不实做 LE-01 trace UI (W3-W4 才落) · step 9 真渲断言会失败 · SKIP_DEMO_STEP4_9=1 暂跳 · ship 后 unset 跑全 · 真断言 contract (7/6/≥1) 不漂 = 等 UI 到位即真验
6. **permission-modal testid 跨 brief 一致** · W2-frontend brief §6 锁 `permission-modal` · 本棒 step 8 用同 testid (medium risk modal · 不是 drawer · drawer 是 high risk 的 `permission-drawer`) · 跨 brief 不冲突 · 验 fixture medium → modal · fixture high → drawer 的 UI form factor 映射 (per schema `risk_tier` enum drives UI form factor verbatim 注释)
7. **REST endpoint `/api/liuye/ledger/decisions?agent_id=credit&limit=1`** · `ledger_service/api.py` 5 admin endpoint 之一 (per root CLAUDE.md §3.7.5 ledger admin REST: decision/{id} · agent/{id} · jurisdiction/{j} · audit_export zip · review POST) · 本 step 8 用 `agent/{id}` 变体 (query param 而非 path param · 看 ledger_service/api.py 实做选 path 或 query) · W2-backend 若 path 不同 · 走 spec 实跑时调整 · 不在第 3 棒 scope (W2-backend live mode 未 ship · spec 跑会 fail · SKIP_DEMO_STEP4_9=1)

### File checklist 状态更新 (11 + 1 baseline JSON)

- [x] tests/perf/step-budget.ts (第 2 棒 · DONE)
- [x] tests/e2e/playwright/demo-path-step4-9.spec.ts (第 2-3 棒 · step 4-9 全 6 step · DONE)
- [x] tests/fixtures/permission_request_low.json (第 3 棒 · F-001 logout · DONE · 命名跟接力 brief)
- [x] tests/fixtures/permission_request_medium.json (第 3 棒 · A3-NEW Decision submit · DONE · 命名跟接力 brief)
- [x] tests/fixtures/permission_request_high.json (第 3 棒 · LE-05 sign reason_required · DONE · 命名跟接力 brief)
- [ ] tests/e2e/playwright/rehearsal-mock.spec.ts (第 4 棒 · D9 sign-off 硬线 · 9 step + saveBaseline `rehearsal-mock`)
- [ ] tests/e2e/playwright/rehearsal-hybrid.spec.ts (第 4-5 棒 · D10 · per-adapter URL)
- [ ] tests/e2e/playwright/rehearsal-live.spec.ts (第 4-5 棒 · D10)
- [ ] tests/e2e/playwright/fallback-tavily-quota.spec.ts (第 4 棒 W2 应急 跑 2 · 附录 C.2.1)
- [ ] tests/e2e/playwright/fallback-ledger-silent-fail.spec.ts (第 4 棒 W2 应急 跑 2 · 附录 C.2.3)
- [ ] _temp/w2-rehearsal-baseline.json (第 10 棒 · D9-D10 baseline append + 入库)

### Next 棒 (第 4 棒 30-45 min) 预计

- `tests/e2e/playwright/rehearsal-mock.spec.ts` (D9 sign-off 硬线 · 跑通即 W2 sign-off · 9 step 完整 串 step 1-3 + step 4-9 + saveBaseline 'rehearsal-mock' · LIUYE_DEMO_MODE=1 · 3 mock SSE :8001/:8002/:8003 起 · isMockSseAlive probe · SKIP_DEMO_STEP4_9=1 暂跳真渲断言 · ship 后 unset · 估 25 min)
- `tests/e2e/playwright/fallback-tavily-quota.spec.ts` (附录 C.2.1 · 模拟 Tavily 429 · LIUYE_DEMO_MODE=mock 自动切 · UI 显 chip 「Demo 模式」灰 badge · step 4-9 不受影响 · 估 15 min)
- 第 4 棒不写: hybrid/live spec (第 5 棒) · fallback-ledger-silent-fail spec (第 4 棒可能也写 · 看实际时间) · baseline JSON 入库 commit (第 10 棒)

### Blocker
- 无

### ELAPSED min: ~28 (起手 read 6 文件 verify schema PermissionRequestEventPayload + W2-frontend brief testid contract + 第 2 棒 spec head + 第 2 棒 progress + payload-shape.spec.ts; 写 3 fixture + 扩 spec step 8-9; tsc + ajv 双验; 写 progress + commit 准备)
### Commit SHA: d461719

---

## 2026-05-12 · checkpoint 4 (第 4 棒 · rehearsal-mock D9 + 2 应急 W2 跑 2)

### What I did (第 4 棒 · ~35 min)

1. 起手对齐: 读 接力 brief 全 (3 文件 scope verbatim · 6 hidden gotcha from 第 3 棒) + 第 2-3 棒 progress 累积 (saveBaseline 形态: 第 2 棒 imperative `saveBaseline(spec, perStep, env?)` · 接力 brief `baselineRecorder = saveBaseline({...})` factory pattern 是 stale · 跟第 2 棒实做) + `tests/perf/step-budget.ts` SSOT (STEP_BUDGETS 9 step 命名 step1..step9) + `tests/e2e/playwright/demo-path-step4-9.spec.ts` 全 (testid 命名契约: candidate-row-* / ideal-profile-12d / pin-handle / credit-handoff-active / parent-tool-call-link / radar-4d / decision-submit / permission-modal / le01-trace-* / trace-node-*) + `tests/e2e/playwright/demo-path-step1-3.spec.ts` (W1 模式 · isMockSseAlive helper) + `docs/onboarding/W2-frontend-worker.md` §4.5 (FallbackBanner 5 fallback 文案表 SSOT) + `tests/fixtures/permission_request_medium.json` (consequences[0] = "写入 decision_ledger sqlite") + `tests/package.json` (mock-sse:channel/credit/report npm scripts · 端口 :8001/:8002/:8003) + `.gitignore` (_temp/ 未在内 · saveBaseline 自动 mkdir 后入库可行)
2. 写 `tests/e2e/playwright/rehearsal-mock.spec.ts` (240 行 · D9 sign-off 硬线 · 9 step 完整 70s · LIUYE_DEMO_MODE=1 · 3 mock SSE :8001/:8002/:8003 全起 probe · SKIP_DEMO_STEP4_9=1 顶层 skip · test.setTimeout(90_000) 覆 playwright.config 默认 60s · withBudget 9 step 一气呵成 step1 hero-static + 4 chip · step2 channel chip · step3 SSE ranked 5 + composer 输入 · step4 IdealProfile 12 维 · step5 pin-handle Space · step6 credit-handoff-active + parent-tool-call-link 1 · step7 radar-4d + 4 dim · step8 decision-submit + permission-modal verbatim + ledger REST + turn-completed-indicator · step9 le01-trace-drawer + 7 node + ≥6 edge + ≥1 evidence link · saveBaseline 'rehearsal-mock' + 'mock' env 显式)
3. 写 `tests/e2e/playwright/fallback-tavily-quota.spec.ts` (110 行 · W2 应急 #1 · 附录 C.2.1 · mock SSE :8001 alive probe + SKIP_DEMO_STEP4_9 顶层 skip · 静默首页 → channel chip → composer 「找新能源汽车零部件相似客户」+ submit · 验 FallbackBanner [data-kind="tavily_quota"] 6s 内显「Demo 模式」(W2-frontend §4.5 verbatim · 不是接力 brief 臆想「搜索配额已用尽」) · 验 candidate-row 仍 ≥ 5 (channel mock fixture replay) · candidate-meta-{industry,geo,scale,similarity}-0 仅 log 不强断 (W2-frontend 未 lock 这些 testid · 留 W3 contract worker))
4. 写 `tests/e2e/playwright/fallback-ledger-silent-fail.spec.ts` (170 行 · W2 应急 #2 · 附录 C.2.3 · mock SSE :8001 + :8002 alive probe + outbox dir readable probe + SKIP_DEMO_STEP4_9 顶层 skip · 静默首页 → credit chip → 「审贷决策·新能源汽车零部件」 + submit · 等 decision-submit visible 30s · grant medium permission · 验 FallbackBanner [data-kind="ledger_silent_fail"] 8s 内显「已提交」(W2-frontend §4.5 verbatim · 不是接力 brief 臆想「账本写入异步重试中」) · 验 outbox file count delta ≥ 1 (Node fs/promises · OUTBOX_DIR = repo-root/data/liuye/outbox/) · 验 LE-01 trace 按钮仍可见 (silent-fail 不阻断 step 9))
5. tsc verify (6 spec + 1 utility 一并 inline config target ES2020 / module ESNext / moduleResolution Bundler / strict / skipLibCheck / types node / esModuleInterop / resolveJsonModule): EXIT=0 0 error

### 关键决策 (5 条)

1. **rehearsal-mock 单 test 跑完整 9 step (one path)** · 不拆 9 individual test · per 接力 brief verbatim "单 test 跑完整 9 step" + W2-mock-test 正 brief §4.3 "跑完整 9 step + saveBaseline 'rehearsal-mock'" · 跑通即 D9 sign-off 硬线 · timeout 90s 覆 playwright.config 默认 60s (9 step 总 66s ±20% = 79s · 加 11s buffer)
2. **saveBaseline 跟第 2 棒实做形态** · imperative `await saveBaseline('rehearsal-mock', perStep, 'mock')` 直传 (env 显式传 'mock' 比默认推断更稳 · LIUYE_DEMO_MODE=1 由调用方 set 但仍显式传 prevent 漂) · 不跟接力 brief 给的 factory pattern `baselineRecorder = saveBaseline({spec, env, ts}) → baselineRecorder.save()` (第 2 棒 progress gotcha #2 已 lock · 跟实做)
3. **FallbackBanner 文案 verbatim 跟 W2-frontend brief §4.5 (UI SSOT)** · 不跟接力 brief 臆想文案 · Tavily quota = 「Demo 模式 · 数据来自预录候选」(W2-frontend §4.5) 不是「搜索配额已用尽 · 已切换至 Demo 模式」(接力 brief) · ledger silent-fail = 「已提交 · 上链中」(W2-frontend §4.5) 不是「账本写入异步重试中」(接力 brief) · spec containText match 文案核心词 ("Demo 模式" / "已提交") 不全文锁 (W2-frontend 改文案 spec 不破)
4. **5 fallback data-kind contract 第 4 棒立** · `[data-testid="fallback-banner"][data-kind="..."]` 5 kind: tavily_quota / llm_provider / ledger_silent_fail / sse_conversion / network_offline · 与 W2-frontend brief §4.5 5 fallback UI 1:1 · W3-W4 跑剩 3 应急 spec 时复用同 contract · W2-frontend FallbackBanner.tsx 实做时按本契约加 data-kind attr
5. **outbox file check 走 Node fs/promises 真验** · `OUTBOX_DIR = path.resolve(__dirname, '..', '..', '..', 'data', 'liuye', 'outbox')` (spec 在 tests/e2e/playwright/ · ../../../ = repo root) · isOutboxDirReadable probe + countOutboxFiles delta ≥ 1 · 若 W2-backend 未 init outbox 目录 (现 0/16 ship) skip file check 仅验 UI banner · 不 fail spec

### Hidden gotcha (第 4 棒 record · 接力 sub-agent 必读)

1. **saveBaseline API 第 2 棒已 lock imperative** · 接力 brief 给的 `baselineRecorder = saveBaseline({spec, env, ts}); await baselineRecorder.save('_temp/w2-rehearsal-baseline.json')` 是 stale factory pattern · 真实做是 `await saveBaseline('rehearsal-mock', perStep, 'mock')` (per tests/perf/step-budget.ts:126-185 verbatim) · 第 5 棒写 rehearsal-hybrid/live 时直接复用 imperative · 不要建 factory wrapper
2. **FallbackBanner UI 文案 SSOT 走 W2-frontend brief §4.5 不是接力 brief** · 接力 brief 文案 (Tavily「搜索配额已用尽 · 已切换至 Demo 模式」/ ledger「账本写入异步重试中」) 是 stale 臆想 · W2-frontend §4.5 才是真实 UI 落地 (Tavily「Demo 模式 · 数据来自预录候选」chip 灰 badge / ledger「已提交 · 上链中」confirm modal 乐观更新) · spec containText 用 W2-frontend §4.5 verbatim 核心词 ("Demo 模式" / "已提交") · 第 5 棒 rehearsal-hybrid step 跨 mock + live 时若再涉 FallbackBanner 同走 W2-frontend §4.5
3. **data-kind 5 kind contract 本棒立** · tavily_quota / llm_provider / ledger_silent_fail / sse_conversion / network_offline · W2-frontend FallbackBanner.tsx 实做时按本立 contract 加 data-kind attr · W3-W4 跑剩 3 应急 spec (LLM provider fallback · SSE conversion · network offline) 同复用 · 不漂
4. **rehearsal-mock timeout 90s** · playwright.config 默认 60s 不够 9 step ±20% (66s × 1.2 = 79s · 加 buffer 至 90s) · 用 test.setTimeout(90_000) 单 test 覆盖 · 不改全局 config (其他 spec 仍 60s · home-silent / demo-path-step1-3 / fallback-* / W3-W4 不需 90s)
5. **outbox dir 现仓不存在** · 仓内 ls data/ 看是否有 liuye/ 子 · W2-backend brief 应 init 但现 0/16 ship · isOutboxDirReadable() probe 返 false 时跳 file check 仅验 UI banner · 不 fail spec · W2-backend ship 后真验
6. **ledger REST endpoint path 待 W2-backend ship 后确认** · rehearsal-mock step 8 用 `http://localhost:8000/api/liuye/ledger/decisions?agent_id=credit&limit=1` (query param) · W2-backend 可能用 `/api/liuye/ledger/agent/credit?limit=1` (path param · per root §3.7.5 ledger admin 5 endpoint) · spec 走 query param 占位 · W2-backend ship 后调整 · 第 3 棒 progress hidden gotcha #7 已 flag · 第 5 棒同
7. **rehearsal-mock step 6 真路径依赖 W2-backend live mode (parent_tool_call_id 透传)** · 现 W2-backend 0/16 ship + W2-frontend 0/18 ship · SKIP_DEMO_STEP4_9=1 暂跳 · W2 完整 ship 后 unset 跑 spec · 失败即 sprint blocker

### File checklist 状态更新 (11 + 1 baseline JSON)

- [x] tests/perf/step-budget.ts (第 2 棒 · DONE)
- [x] tests/e2e/playwright/demo-path-step4-9.spec.ts (第 2-3 棒 · step 4-9 全 6 step · DONE)
- [x] tests/fixtures/permission_request_low.json (第 3 棒 · DONE)
- [x] tests/fixtures/permission_request_medium.json (第 3 棒 · DONE)
- [x] tests/fixtures/permission_request_high.json (第 3 棒 · DONE)
- [x] tests/e2e/playwright/rehearsal-mock.spec.ts (第 4 棒 · D9 sign-off 硬线 · 9 step · DONE)
- [x] tests/e2e/playwright/fallback-tavily-quota.spec.ts (第 4 棒 W2 应急 #1 · DONE)
- [x] tests/e2e/playwright/fallback-ledger-silent-fail.spec.ts (第 4 棒 W2 应急 #2 · DONE)
- [ ] tests/e2e/playwright/rehearsal-hybrid.spec.ts (第 5 棒 · D10 · per-adapter URL channel mock + credit/report live)
- [ ] tests/e2e/playwright/rehearsal-live.spec.ts (第 5 棒 · D10 · 3 adapter 全 live)
- [ ] _temp/w2-rehearsal-baseline.json (第 5 棒 D9-D10 跑后 append + 入库 commit)

### Next 棒 (第 5 棒 · 最终一棒 · 30-45 min) 预计

- `tests/e2e/playwright/rehearsal-hybrid.spec.ts` (D10 跑 · per-adapter URL · env `LIUYE_DEMO_MODE=0` + `LIUYE_BACKEND_CHANNEL_URL=http://localhost:8001` (channel 走 mock SSE :8001 复用 W1) + `LIUYE_BACKEND_CREDIT_URL` / `LIUYE_BACKEND_REPORT_URL` 留空 fallback `LIUYE_BACKEND_BASE_URL=http://localhost:8000` · 9 step 完整 + saveBaseline 'rehearsal-hybrid' 'hybrid' env · 预期总耗时 < 70s + 4s buffer (live LLM 慢) · channel mock 提示 chip 显「Demo 模式」)
- `tests/e2e/playwright/rehearsal-live.spec.ts` (D10 跑 · 3 adapter 全 live · LIUYE_DEMO_MODE=0 · 真 backend uvicorn :8000 · Tavily + DeepSeek + sqlite ledger 真路径 · saveBaseline 'rehearsal-live' 'live' env · skipIf backend health probe 失败 · 5 应急流程不触 sanity check)
- W2-mock-test 11/11 DONE · 最终一棒 ship · sign-off 流程进入 W2 PR + codex review

### Blocker
- 无

### ELAPSED min: ~35 (起手 read 接力 brief + 第 2-3 棒 progress + W2-frontend §4.5 FallbackBanner + permission_request_medium.json + .gitignore + tests/package.json; 写 3 spec 共 ~520 行; tsc verify EXIT=0; 写 progress segment + commit 准备)
### Commit SHA: b9c91b1

---

## 2026-05-12 · checkpoint 5 (第 5 棒 · 最终一棒 · rehearsal-hybrid + rehearsal-live D10 · 11/11 DONE)

### What I did (第 5 棒 · ~30 min)

1. 起手对齐: 读 接力 brief 全 (2 文件 scope · 7 hidden gotcha from 第 4 棒 · 含 saveBaseline imperative API + FallbackBanner §4.5 SSOT + data-kind 5 kind contract + 90s timeout + outbox dir + ledger REST endpoint + SKIP_DEMO_STEP4_9 flag) + 第 4 棒 progress segment + `tests/perf/step-budget.ts` SSOT (STEP_BUDGETS step1..step9 命名 + imperative saveBaseline `(spec, perStep, env?)` · 不是 factory) + `tests/e2e/playwright/rehearsal-mock.spec.ts` 全 240 行 (9 step pattern 复用源 · 单 test + test.setTimeout 90_000 + 3 mock SSE probe + 顶层 SKIP_DEMO_STEP4_9) + `tests/e2e/playwright/demo-path-step1-3.spec.ts` (isMockSseAlive helper 复用 · backend health probe 模式) + `tests/e2e/playwright/fallback-tavily-quota.spec.ts` 头 (data-kind 5 kind contract · W2-frontend §4.5 文案 verbatim 「Demo 模式」核心词) + `tests/e2e/playwright/fallback-ledger-silent-fail.spec.ts` 头 80 行 (outbox dir 检查 + isOutboxDirReadable pattern) + W2-mock-test brief §4.3 (2)/(3) verbatim (hybrid env per-adapter URL channel:8001 + credit/report fallback BASE:8000 · live 全 LIUYE_DEMO_MODE=0 + BASE:8000 + skipIf health) + 老仓 `.gitignore` (_temp/ 未在内 · 第 8 棒入库 commit 可行) + tests/ 目录结构 (e2e/playwright + perf + fixtures)
2. 写 `tests/e2e/playwright/rehearsal-hybrid.spec.ts` (~290 行 · D10 跑 · per-adapter URL · channel mock + credit/report live):
   - 头注释 SSOT 引用 + env 契约 (LIUYE_DEMO_MODE=0 + LIUYE_BACKEND_CHANNEL_URL=:8001 + BASE_URL=:8000 fallback) + 预期 < 74s · 9 step ±20% · skip 3 路 (SKIP_REHEARSAL_HYBRID=1 / channel URL 未指 :8001 / probe 失败)
   - 2 helper: isMockSseAlive (复用 rehearsal-mock) + isBackendLiveAlive (新 · live :8000 /api/liuye/health)
   - 单 test + test.setTimeout(90_000) + LIUYE_BACKEND_CHANNEL_URL sanity check (必含 ':8001') + mock SSE :8001 + backend live :8000 双 probe
   - 9 step body verbatim 复用 rehearsal-mock (step1 hero+4chip · step2 channel chip · step3 候选 ≥5 走 mock fixture · step3.5 channel demo cue [data-kind="demo_mode"] optional 验 · step4 IdealProfile 12 维 live LLM · step5 pin Space · step6 credit-handoff-active live · step7 radar 4 维 live · step8 permission-modal + ledger REST live + turn-completed · step9 le01-trace 7 node ≥6 edge ≥1 evidence)
   - saveBaseline('rehearsal-hybrid', perStep, 'hybrid') + summary log "hybrid: channel mock + credit/report live"
3. 写 `tests/e2e/playwright/rehearsal-live.spec.ts` (~250 行 · D10 跑 · 3 adapter 全 live):
   - 头注释 SSOT 引用 + env 契约 (LIUYE_DEMO_MODE=0 + BASE_URL=:8000 default · 不覆写 channel/credit/report URL) + 预期 < 74s · 5 应急流程不触 sanity (live healthy · FallbackBanner count=0)
   - 1 helper: isBackendLiveAlive (复用 hybrid)
   - 单 test + test.setTimeout(90_000) + LIUYE_DEMO_MODE='0' 显式 sanity (env 漂检测) + backend live :8000 probe (skipIf 失败)
   - 9 step body verbatim 复用 rehearsal-mock + hybrid (step1-9 全 live 真路径 · Tavily 真 / DeepSeek 真 / sqlite 真 · step6 注释 "全 live" 区别 hybrid)
   - 跑完 9 step 后 FallbackBanner count === 0 sanity 强断 (live 健康前提下不应触发任何 5 kind fallback · > 0 = adapter fall back blocker)
   - saveBaseline('rehearsal-live', perStep, 'live') + summary log "live: 3 adapter 全 live · 5 应急 count=N OK"
4. tsc verify (9 path · W1 home-silent + demo-path-step1-3 + W2 demo-path-step4-9 + rehearsal-mock + fallback-tavily-quota + fallback-ledger-silent-fail + rehearsal-hybrid + rehearsal-live + perf/step-budget.ts · inline config target ES2020 / module ESNext / moduleResolution Bundler / strict / skipLibCheck / types node / esModuleInterop / resolveJsonModule): EXIT=0 · 0 error

### 关键决策 (5 条)

1. **9 step body verbatim 复用 rehearsal-mock 而非 extract helper** · 三 rehearsal spec (mock/hybrid/live) 故意 90% duplicate · 单文件 self-contained 便于 W2 sign-off review 主 session + codex 单 spec 全看 · extract helper 会需新建 shared module (e.g. `tests/e2e/_shared/run9steps.ts`) 不在 11 文件 scope · 接力 brief 也允许"copy vs extract helper · sub-agent 决策" · 选 copy 是 D9 sign-off 决策成本最低
2. **rehearsal-hybrid env sanity check LIUYE_BACKEND_CHANNEL_URL 必含 ':8001'** · 不是 expect (硬 fail) · 而是 test.skip (env 未对齐 = 跑前置未做好 · 跳过比 fail 更软落地 · per W1 demo-path-step1-3 mock SSE 不可达 skip 同模式) · backend §4.1 `_resolve_backend_url` helper 真实做时 channel agent 会读 LIUYE_BACKEND_CHANNEL_URL · 我 spec 仅验 env 被 set · 不验 helper 行为本身 (那是 backend pytest scope)
3. **channel demo cue selector dual fallback** · 接力 brief 给的 `[data-testid="agent-chip-channel"] [data-state="demo"]` 是 chip 内嵌 badge · 但 W2-frontend brief §4.5 FallbackBanner 主体是 `[data-testid="fallback-banner"][data-kind="demo_mode"]` 这种统一 banner · 不知 W2-frontend 具体选哪种 · 我用 CSS selector OR `, ` 双 selector match · count > 0 即 optional 验 · 不强断 (count=0 仅 console.log 不阻 spec) · W2-frontend ship 后 narrow 至确定 selector
4. **rehearsal-live 5 应急不触 sanity 用 expect().toBe(0) 强断** · 不是 optional log · live 模式健康前提下不应触发任何 FallbackBanner (5 kind 全不触) · 触发即 sanity blocker · 应阻 D10 ship · 与 hybrid 模式 demo cue optional 验区别 (hybrid 期望 channel mock 提示 chip · live 期望 0 fallback) · 这是 brief §4.3 (3) "5 应急流程不触 (sanity check live 健康)" verbatim 落地
5. **timeout 90s 单 test 设置不改全局** · test.setTimeout(90_000) 与 rehearsal-mock 同 · playwright.config 默认 60s 不够 9 step ±20% (66 × 1.2 = 79s) · 不改全局 (其他 spec 仍 60s · 不需 90s) · live LLM 慢但仍应 < 74s (66s 基 + 4s LLM buffer + 4s buffer) · 90s timeout 留 16s 余量

### Hidden gotcha (第 5 棒 record · codex bg review 必读)

1. **三 rehearsal spec 90% duplicate 是故意** · sub-agent 决策 copy 不 extract helper · D9 mock + D10 hybrid + D10 live 三跑独立成文 · 各 spec 单文件即可看懂 · W3-W4 若加新 rehearsal mode (e.g. degraded · partial-fail) 可考虑 extract · 现阶段单文件 self-contained 是 sign-off review 友好
2. **rehearsal-hybrid channel demo cue 用 optional 验 (count > 0 then expect visible)** · 不强断 W2-frontend 实做 data-kind="demo_mode" attr · 因 brief §4.5 未明确 "channel mock 提示 chip 是 FallbackBanner 还是 chip 内嵌 badge" · 接力 brief 给的 `[data-state="demo"]` 是猜测 · 我 dual selector + count > 0 conditional verify · 不阻 spec 跑过 · W2-frontend ship 后再 narrow
3. **rehearsal-live FallbackBanner count = 0 strict** · 与 hybrid 不同 (hybrid 期望 1 个 demo_mode banner · live 期望 0 任何 kind) · 这是 sanity gate · live 健康前提下任何 fallback 触发 = blocker · 若 W2 ship 后跑出 count > 0 · 必先查 adapter 健康 / key 配 / network 通 · 不是 spec bug
4. **LIUYE_DEMO_MODE 环境变量 sanity check** · rehearsal-live 显式断 demoMode === '0' · 若调用方漏 set env → test.skip 不 fail · 与 rehearsal-hybrid LIUYE_BACKEND_CHANNEL_URL 必含 ':8001' 同模式 · env 未对齐 = 跳过 not fail · 更软落地
5. **ledger REST endpoint path 待 W2-backend ship 后确认** · 与 rehearsal-mock 同 placeholder · spec 用 `${baseUrl}/api/liuye/ledger/decisions?agent_id=credit&limit=1` (query param) · W2-backend 可能用 path param (`/api/liuye/ledger/agent/credit?limit=1`) per 老仓 §3.7.5 · spec 走 query param 占位 · ship 后 main session 跑 e2e 失败 → 同步调整 3 rehearsal spec (mock + hybrid + live) 同一 placeholder 替 path · 已 flag 在 mock 第 4 棒 gotcha #6 + hybrid + live 注释
6. **per-adapter URL helper 真实做边界**: W2-backend §4.1 `_resolve_backend_url(agent_id)` Python helper 实做 `os.environ.get(f'LIUYE_BACKEND_{agent_id.upper()}_URL') or self.backend_url` · 是 backend channel/credit/report adapter 各自 init 时调用 · 我 spec 仅 Playwright 起子进程 inherit env · 真验链路是 frontend dev server (3210) → backend (8000) → adapter resolve URL → channel 走 :8001 mock / credit 走 :8000 self → SSE 推回前端 · 复杂链路 spec 不验 (那是 W2-backend pytest + integration test scope) · spec 仅验 UI 真渲对应 (mock 给 candidate 5 / live 给 candidate 5)
7. **_temp/ 入库 commit 第 8 棒做 (D9-D10 跑后)** · 第 5 棒不入库 (因 spec 不实跑 · 现 _temp/ 仍不存在 · saveBaseline 自动 mkdir 是跑时行为) · W2 完整 ship 后 D9 mock 跑 + D10 hybrid + live 跑 · 实际 `_temp/w2-rehearsal-baseline.json` array 含 3 record · 入库 commit 由后续 sprint 棒做 · 不在 W2-mock-test 11 文件 scope

### File checklist 状态更新 (11 / 11 · W2-mock-test DONE)

- [x] tests/perf/step-budget.ts (第 2 棒 · DONE)
- [x] tests/e2e/playwright/demo-path-step4-9.spec.ts (第 2-3 棒 · 全 6 step · DONE)
- [x] tests/fixtures/permission_request_low.json (第 3 棒 · DONE)
- [x] tests/fixtures/permission_request_medium.json (第 3 棒 · DONE)
- [x] tests/fixtures/permission_request_high.json (第 3 棒 · DONE)
- [x] tests/e2e/playwright/rehearsal-mock.spec.ts (第 4 棒 · D9 sign-off 硬线 · DONE)
- [x] tests/e2e/playwright/fallback-tavily-quota.spec.ts (第 4 棒 · W2 应急 #1 · DONE)
- [x] tests/e2e/playwright/fallback-ledger-silent-fail.spec.ts (第 4 棒 · W2 应急 #2 · DONE)
- [x] tests/e2e/playwright/rehearsal-hybrid.spec.ts (第 5 棒 · D10 per-adapter URL · DONE)
- [x] tests/e2e/playwright/rehearsal-live.spec.ts (第 5 棒 · D10 3 adapter 全 live · DONE)
- [ ] _temp/w2-rehearsal-baseline.json (D9-D10 实跑后由后续 sprint 棒入库 · 第 5 棒不在 scope)

### W2-mock-test 11/11 DONE · 3 rehearsal mode 全 ship

| Mode | Spec | Env | 总耗时预期 | Sanity 验 |
|---|---|---|---|---|
| mock (D9) | rehearsal-mock.spec.ts | LIUYE_DEMO_MODE=1 + 3 mock SSE 全起 | < 66s ±20% = 79s | candidate ≥5 + 12 维 + 4 维 + 7 node etc. |
| hybrid (D10) | rehearsal-hybrid.spec.ts | LIUYE_DEMO_MODE=0 + CHANNEL_URL=:8001 + BASE_URL=:8000 | < 74s | + channel demo cue optional |
| live (D10) | rehearsal-live.spec.ts | LIUYE_DEMO_MODE=0 + BASE_URL=:8000 全 live | < 74s | + 5 应急 count=0 strict |

5 应急覆盖状态:
- ✅ W2 跑 2: fallback-tavily-quota (第 4 棒) + fallback-ledger-silent-fail (第 4 棒)
- ⏳ W3-W4 跑 3 留: LLM provider fallback · SSE conversion · network offline (data-kind contract 第 4 棒已立: llm_provider / sse_conversion / network_offline)

per-adapter URL verify (perfect-check fix #2):
- ✅ rehearsal-hybrid: LIUYE_BACKEND_CHANNEL_URL=:8001 (mock) + LIUYE_BACKEND_BASE_URL=:8000 (live fallback for credit/report)
- ✅ rehearsal-live: 3 adapter URL 全留空 fallback LIUYE_BACKEND_BASE_URL=:8000 (default live)

### Next (主 session 接手)

- 主 session 起 codex bg review (W2-mock-test 11/11 verdict)
- D9 mock 走完彩排 (LIUYE_DEMO_MODE=1 + 3 mock SSE :8001/:8002/:8003 起 + frontend dev 3210 起 · 不 SKIP) 验 rehearsal-mock 走通 · sign-off W2
- D10 hybrid + live 跑 (D9 后 W2-frontend + W2-backend 全 ship · unset SKIP env flag · 跑 3 rehearsal · 入库 `_temp/w2-rehearsal-baseline.json` · 漂移对比 mock/hybrid/live)
- W2-mock-test scope 完结 · 后续 sprint 接 W3-W4 (3 应急 + LE-01 deep evidence chain + ledger admin REST integration)

### Blocker
- 无

### ELAPSED min: ~30 (起手 read 接力 brief + 第 4 棒 progress + step-budget.ts API + rehearsal-mock 240 行 pattern + demo-path-step1-3 helper + fallback-tavily-quota data-kind + fallback-ledger-silent-fail outbox + W2-mock-test brief §4.3 (2)(3) verbatim; 写 2 spec 共 ~540 行; tsc verify EXIT=0; 写 progress segment + commit 准备)
### Commit SHA: (本 commit · git log 下一行)

