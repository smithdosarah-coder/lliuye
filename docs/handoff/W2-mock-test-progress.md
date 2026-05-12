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

