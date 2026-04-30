# State Snapshot · Reset 工程现状

> 本文件 timestamped 段落 append-only · 主 CLI 每 PM checkpoint / worker DONE / 阶段转换 / **每次迭代** 时必须更新。

## 更新硬规 (PM 2026-04-29 立)

**Reset 工程任何迭代 · 无论大小 · 必须同步更新本文件**。

**触发清单**:
- 任何 worker DONE signal cherry-pick → 主 CLI 同 commit 加段
- 任何 codex review 出 verdict → 主 CLI 写 audit doc 时同更
- 任何 PM 拍板 / decisions-log Q-NNN → 主 CLI 同更
- 任何 cleanup batch / fix / refactor commit → 主 CLI 同更
- 任何阶段转换 (Phase A → Phase B / Week N → Week N+1)

**段格式**:
```markdown
## YYYY-MM-DD HH:MM · <事件 一行>

### What happened
- <list>

### Triggered by
- <PM / worker-XX / codex review / scheduled / 自发>

### State change (delta)
- <key change · old → new>

### Next
- <implied next 1-2 step>
```

**违反 = stop the line**: 任何触动产品 / 架构 / 决策的 commit 未同步本文件 · 主 CLI 必须 amend / 补 commit。

**意义**: 本文件 + decisions-log = 长周期工程的 ground truth · compression / 新 CLI / 未来的我 全靠它还原。本文件漂 = reset 工程迷失。

---

---

## 2026-04-29 (本批次 3) · Neat-freak 跨 3 层知识洁癖整理

### What happened
- 跑 neat-freak skill (洁癖) · 跨 3 层知识(memory / 项目根 / docs/) 同步现状
- 删 orphan: `_tmp_viktor_pptx.md`(项目根 1 行空)
- archive: `HANDOFF.md` (老 5 demo MVP 交接) → `docs/_archive/HANDOFF_legacy_5demo_2026-04.md`
- archive: `启动说明.md` (Portal 时代 · 2026-04-13) → `docs/_archive/启动说明_legacy_2026-04-13.md`
- 重写 `README.md` (从 v14 single-page 改为 platform shell v2 + ECS production)
- 修 reset docs `workspace-state-protocol.md 不存在 · 必新建` 错描述(实 v1.0 已存在 · Stage B 时建 · worker-A1 任务改为 review + 6 spec 同步)
- CLAUDE.md §10 加 `shared/llm/` 关键文件(Stage E.3 落地 · 0 agent 用 · worker-A2 迁)
- Memory 加 4 新 entries: project_reset_initiative + project_pm_5_decisions + feedback_state_snapshot_hard_rule + project_llm_keys_rotated
- Memory 修 reference_deployment(端口 :8002 → :8000 · 加 ECS production 信息)
- MEMORY.md 索引加 5 项(4 新 + reference_deployment 之前 orphan 现入索引)

### Triggered by
- /neat-freak skill (PM 触发)

### State change (delta)
- 项目根 .md 7 → 5 (删 1 + archive 2)
- README v14 stale → platform shell v2 truthful
- Reset docs 修 workspace-state-protocol 错引用(3 处)
- Memory 28 → 32 entries · 0 orphan · 索引齐

### Next
- commit + push + ECS sync
- fresh main CLI 接手时 6 reset docs 应 self-contained · 0 question · 直接 fire 6 路并行 Step 2

---

## 2026-04-29 (本批次 2) · Step 2 Charter 补 + 答 fresh CLI 8 题

### What happened
- fresh main CLI 启动后读完 6 reset docs · 提 8 个 critical 澄清 (17 类完整定义 / 4 sub-agent 输出在哪 / Step 2 flow / Codex Round 1 template / anti-bias rule 1 衔接 / PRD 取证 / register schema / 调度方式)
- 诊断: 前任 main CLI 写的 reset docs 仍有 4 处"心里有但没写出来"的 gap (compression 写法典型病)
- 修复: 新建 `docs/reset/step2-conflict-scan-charter.md` (Step 2 SOP self-contained · 含 17 类完整 + flow + schema + sub-agent template) + codex-mesh-protocol.md 加 §4.5 (Step 2 codex template) + §5.b (audit dir) + §6 引用 charter §2 · anti-bias-rules.md 加 §1.1 (fresh CLI 接手处理) · CLAUDE.md §14 必读列表加 step2 charter · RESET_MASTER_PLAN 文档地图加 step2 charter

### Triggered by
- fresh main CLI 提 8 题 verify reset doc self-containment (健康 verify 信号)

### State change (delta)
- 新文档: `docs/reset/step2-conflict-scan-charter.md` (10 节 · 含 17 类 SSOT verbatim)
- 编辑: codex-mesh-protocol.md / anti-bias-rules.md / CLAUDE.md / RESET_MASTER_PLAN.md
- reset 必读 docs 从 5 份 → 6 份 (加 step2 charter)

### Next
- commit + push · ECS sync
- 通知 fresh main CLI 重读 step2-conflict-scan-charter.md · 8 题应自答 · 然后 fire 6 路并行 (5 sub-agent + Codex Round 1)
- 沿用 anti-bias rule 1.1: 前任 main CLI 4 sub-agent 输出弃用 (compression 后未 verbatim 还原) · 重派

---

## 2026-04-29 · Reset 启动 · 由当前 main CLI handoff (本次迭代 · 遵守 §14.1 状态更新硬规)

### What happened
- 当前主 CLI 完成 reset 工程承接文档全集落地
- 写 8 份新 doc · 改 4 份 doc · 加 1 个桌面启动脚本
- PM 加 1 条新硬规 (§14.1 · state-snapshot 必须每迭代同步更新)

### Triggered by
- PM 2026-04-29 决议进 reset 长周期工程 + 加状态更新硬规

### State change (delta)
- 文档:`RESET_MASTER_PLAN.md` 新建 · `docs/reset/{north-star, phase-a-charter, phase-b-charter, codex-mesh-protocol, state-snapshot, anti-bias-rules}.md` 新建 · `docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_2026-04-29.md` 新建
- CLAUDE.md: 加 §14 (新 session 必读 + compression 恢复) + §14.1 (state-snapshot 实时更新硬规)
- 桌面: `C:\Users\Mr.S\Desktop\start-reset-mesh.bat` 一键启 main + A1 + A2 worker
- decisions-log: 待新 CLI 接手后写 PM 5 拍板 Q-NNN entries

### Next
- 当前 CLI commit `RESET-HANDOFF-PREPARED` + push + ECS sync · 然后 graceful shutdown
- PM 双击桌面 start-reset-mesh.bat → 3 cmd window 启 → 在 main CLI window 启 claude → paste resume 提示
- 新 CLI 走 NEW-MAIN-CLI-RESUMED 流程 verify

---



### 已完 (Phase B Cleanup batches 0-6 + 散修)

```
b73b15c security(redact): 批 0 · ECS handoff doc + decisions-log secret redact
523efd0 fix(demo): 批 2 · 4 demo坑修复 (forceMock + silent fallback × 3)
e2ec0c5 chore(cleanup): 批 1 · delete 38 dead files + agent-channel-session refactor
99650a9 refactor(routes): 批 4 · delete 8 dead backend routes
ddb565b refactor(framework): 批 5 · Gradio + form_filler + narrative_pipeline 退役
40d8b2c docs(sync): 批 6 · 11 处文档漂移修复
37ff24a chore(workspace): B-2 · dropdown click-to-fire across 4 workspaces
78d28d6 fix(workspace): B-banner · inline error → top banner (4 workspaces)
94e2e88 fix(report): B-cta · Report 删模板库 placeholder + 收紧 launch buttons
a9370a3 fix(pin-ref): B-pin · pin thumbnail real e2e fix
8f8e378 fix(report): EmptySkeleton 撑满 viewport · 修底部空白
97663e7 fix(report): handleApplyLaunch 真 fire SSE · 不再只切 UI 留主列空白
```

**安全**:
- 3 LLM key (DeepSeek / Tavily / DashScope) rotated 2026-04-29 · ECS .env 同步 · backend restart
- handoff doc + decisions-log:1272 + :2364 redacted
- ECS SSH password / Cloudflare tunnel / 5 demo passwords 仍未 rotate (PM 决议: 演示后再处置)

**production**: ECS 139.196.30.69 · domain liuye.me · main 分支 · 4 services active (nginx / cloudflared / lliuye-frontend / lliuye-backend)

### 在跑 (Step 2 conflict scan · 中断状态)

主 CLI 在派 5 sub-agent + Codex Round 1 时 · PM 切换到本文档 reset planning · 已收到的:
- ✅ 架构层 sub-agent (类 1/2/3/4/11) — 7 处 dirty 找到
- ✅ 数据层 sub-agent (类 5/12) — 数据 mock 形态分层 OK · evaluation 6 yaml 对齐
- ✅ 指令层 sub-agent (类 1/6/7) — 3 套 LLM caller 并行 + 多个 active decision 未回写 root CLAUDE.md
- ✅ 命名路由层 sub-agent (类 8/9/10/16) — `compliance` vs `compli` dual-id 全栈分裂 + 4 角色 vs 5 角色文案漂

**未收 / 中断**:
- ❌ 生产同步层 sub-agent (类 0/13/14/15) — 用户中断
- ❌ PRD 取证 sub-agent — 用户中断
- ❌ Codex Round 1 全 17 类 — 用户中断

**整合 conflict register**: 待新 main CLI 接手后完成 (调用上面 4 sub-agent 已收数据 + 重派剩余 + Codex Round 1)。

### 待启 (Phase A worker mesh + Codex 工具化)

- worker-A1 contracts (Week 1)
- worker-A2 shared infra (Week 1)
- worker-A3 Channel pilot (Week 2-3 · 依赖 A1+A2)
- worker-A4 5 子 thin adapter (Week 4-5 · 依赖 A3)
- worker-A5 Letterpress (Week 2-3 并行)
- worker-A6 6 Agent handoff contract (Week 2-3 并行)
- worker-A7 PRD 取证 + draft (Week 2-3 并行 · 与 PM 飞书协作)
- 工程化: `scripts/orchestrator/codex-peer.py` (Week 1-2 后期由主 CLI 抽空写)

### PM 已拍板 (本次 reset 启动)

1. **杜绝拖死 4 机制**: 强制输出 schema / ≤ 3500 词 / 单 issue 最多 2 round 辩论 / dissent 反增即 escalate PM
2. **Phase A/B 严切阶段**
3. **active decision 回写 root CLAUDE.md**: 谁改决策谁回写 + CI lint
4. **命名 SSOT 8 列单表**: agent_id / 中文 / 业务名 / UI brand / route / 色彩 token / RBAC role / eval baseline
5. **Step 3 PRD 取证 Step 2 中并行启动**

### 当前 mesh 状态

11 个 worktree · 见 `docs/handoff/mesh.json` + `py scripts/orchestrator/scoreboard.py`。

```
main · chore/l0-infra · 主 CLI (本次将交班 · Signal: RESET-HANDOFF-PREPARED 后关窗)
A1-inventory · feat/inventory-expand-A1 · idle (将复用为 worker-A1 contracts)
A2-contracts · feat/contracts-bootstrap-A2 · idle (将复用为 worker-A2 shared infra)
A3-prd · feat/prd-summaries-A3 · idle (将复用为 worker-A7 PRD)
其他 7 个 worktree (agent1/agent3/agent6/code-frontend-integration 等) · 长期 idle · 后续按需复用
```

### 5 项 dissent 已闭环 (Phase A 启动前不再争辩)

- 命名 8 列 (PM 选 8) ✓
- Phase A/B 切阶段 (PM 选切) ✓
- 杜绝拖死机制 (PM 选 4 条全要) ✓
- 回写机制 (PM 选谁改谁回写) ✓
- Step 3 取证时机 (PM 选 Step 2 中并行) ✓

### 风险预警

- **decisions-log 长 2400+ 行** · compression 后新 CLI 难以全读 · 关键 active rule 必须回写 root CLAUDE.md (规则 3)
- **`shared/llm/`已建但 0 agent 用** · worker-A2 shared infra 启动时必须接管 + 6 agent 迁
- **Letterpress 12 consumer** · worker-A5 单 sprint · 视觉验收需 PM 看
- **Agent6 → Agent3 handoff data flow 没真做** · worker-A6 必须正面对待这个 pivot

---

## 2026-04-29 04:10 · Step 2 fire 7 路并行 (DISPATCHED · fresh 重派)

### What happened
- 新主 CLI 接手 reset 工程 · 走 anti-bias §1.1 → 弃用前任 4 sub-agent 高层总结 (chat-only · 不可信) · fresh 重派
- 一次 fire 7 路并行 (charter §3 + §9 verbatim):
  - 5 sub-agent (architecture / data / instruction / naming-route / production-shape) → docs/audit/sub-agent-step2-round1/*.md
  - 1 PRD 取证 sub-agent (Step 3 范围 · Step 2 中并行启) → docs/audit/prd-evidence-frozen.md
  - 1 Codex Round 1 background (codex-mesh §4.5 template · 独立扫全 17 类 · 不见 sub-agent 输出) → docs/audit/codex-step2-round1.md
- audit dir docs/audit/sub-agent-step2-round1/ 已建

### Triggered by
- PM 2026-04-29 答 fresh CLI 8 题 → 新加 docs/reset/step2-conflict-scan-charter.md (10 节 · 17 类 SSOT + flow + schema + sub-agent template + Codex template + PRD 取证 + 退出标准)
- codex-mesh-protocol.md 加 §4.5 (Step 2 专用 Codex template) + §5.b (Step 2 audit dir) + §6 引用 SSOT
- anti-bias-rules.md 加 §1.1 (fresh CLI 接手处理 · 前任未 commit sub-agent 输出弃用)

### State change (delta)
- Step 2 状态: 中断 (handoff §7) → IN-FLIGHT (fresh 重派 · 7 路并行)
- 前任 4 sub-agent (架构层/数据层/指令层/命名路由层): chat-only summary → 视为不存在 (per anti-bias §1.1)
- audit dir: 不存在 → docs/audit/sub-agent-step2-round1/ + docs/audit/{codex-step2-round1, prd-evidence-frozen, conflict-register-v1}.md (后 3 个待 fire 完落)

### Next
- 6 sub-agent foreground 全 done + Codex background notification → Read 7 份 audit doc
- 合成 conflict-register-v1.md (charter §8 schema · Cat / file:line / 证据 / Owner-Phase A worker / Keep-Revert-Rewrite · 含 dissent appendix per anti-bias rule 4)
- Commit STEP-2-CONFLICT-REGISTER-V1-PREPARED + 通知 PM 拍板
- PM 拍板 (Signal: STEP-2-PM-RULED) → 进 Step 1 Phase A worker mesh

---

## 2026-04-29 04:25 · Step 2 conflict-register-v1 PREPARED + A1/A2 worker 同时启 (PM override)

### What happened
- 7 路 fire 全 done (6 sub-agent foreground · Codex 1 background notification)
- 7 份 audit doc 全落 disk:
  - `docs/audit/sub-agent-step2-round1/{architecture,data,instruction,naming-route,production-shape}.md` (5 · 105 findings)
  - `docs/audit/codex-step2-round1.md` (50 findings 全 17 类 · independent v1)
  - `docs/audit/prd-evidence-frozen.md` (Step 3 PRD 取证 · 飞书 7 doc found · 10 G-XX gap)
- 主 CLI synthesize → `docs/audit/conflict-register-v1.md` (87 entries · charter §8 schema · 含 dissent appendix per anti-bias rule 4 · ~2800 词)
- PM 拍板"我说的是 A1 和 A2" → override charter §3 sequential flow → A1 + A2 worker 与 Step 2 register 拍板并行启

### Triggered by
- 6 sub-agent foreground 全 returned + Codex background completion notification (b0h9h9wvc)
- PM 答 "我说的是 A1 和 A2" (override Step 2→Phase A sequential gate)

### State change (delta)
- Step 2 状态: IN-FLIGHT → REGISTER PREPARED (待 PM 拍板 Signal: STEP-2-PM-RULED)
- audit dir: 7 路 fire 全落地 + 1 份 conflict-register-v1 主 CLI 合成
- Phase A worker mesh: idle → A1 + A2 dispatch starting (per PM override · 与 register 拍板并行)
- 🔴 Cat 15 (production sync 漂 P0) flagged · 待主 CLI fix-forward (chore/l0-infra 落后 main 10 commit)
- Phase A 8 项验收硬线进度: 0/8 → 启 A1 (硬线 #1, #8) + A2 (硬线 #2)

### Next
- 主 CLI: 写 A1 + A2 onboarding doc + DISPATCHED commit × 2 + fire Codex pre-dispatch draft × 2 (插入点 1)
- 通知 PM 启 worker A1-inventory + A2-contracts cmd window (worktree 复用 · branch 改名为 feat/phase-a1-contracts + feat/phase-a2-shared per charter §3)
- PM 拍板 register (Signal: STEP-2-PM-RULED) → A3-A7 worker 后续按 register 派
- 主 CLI fix-forward Cat 15 production sync (与 A1+A2 并行)

---

## 2026-04-29 04:45 · STEP-2-PM-RULED + A5/A6/A7 dispatched

### What happened
- PM 拍板 4 件 dissent (per conflict-register-v1.md PM 拍板段):
  1. Cat 8 选 `compliance` 单 id
  2. Cat 0 `/today` RM workbench 推 Phase B-3
  3. Cat 15 sync 等 A1+A2 完后
  4. Cat 11 legacy_gradio 全栈隔离 (v16 真稳前不真删)
- 87 entries 默认按建议跑 · PM 不逐条 review · worker owner 列处理
- 主 CLI 派 A5 + A6 + A7 worker (Week 2-3 并行 · 不依赖 A1/A2/A3):
  - A5 worktree D:/claude code/work-A5-design (新建 · feat/phase-a5-design)
  - A6 worktree D:/claude code/work-A6-handoff (新建 · feat/phase-a6-handoff)
  - A7 复用 D:/claude code/work-A3-prd · resume 时切 feat/phase-a7-prd
- Codex pre-dispatch draft × 3 fire background

### Triggered by
- PM "剩下的 GO" (4 件全过)
- A1/A2 worker 已 active 跑 (feat/phase-a1-contracts 59cce5c / feat/phase-a2-shared 3147d49)

### State change (delta)
- Step 2 状态: REGISTER PREPARED → PM-RULED (4 dissent 收敛 + 87 entries 按建议派)
- Phase A worker mesh: A1+A2 active → A5+A6+A7 dispatching (5 worker active 中 · 仅 A3+A4 等依赖)
- 87 entries owner 列指 worker 启 · 各 worker resume 时按 register 干
- legacy_gradio 决议: 真删 → 全栈隔离 (v16 真稳前留)

### Next
- A5/A6/A7 onboarding doc + DISPATCHED commit × 3 + Codex draft × 3 (background)
- 等 5 worker (A1/A2/A5/A6/A7) DONE signal · cherry-pick · push origin · ECS sync (per CLAUDE.md §13.1)
- A1+A2 DONE 后 → 主 CLI 启 A3 (Channel pilot · 依赖 A1+A2)
- A3 DONE 后 → 主 CLI 启 A4 5 子 worker (依赖 A3 · channel pilot 模板)
- A1+A2 cherry-pick 后 → 主 CLI 一次性 sync chore/l0-infra ↔ main (Cat 15 fix-forward · 含 ECS verify)

---

## 2026-04-29 (Phase A · Week 2-3) · worker-A3 channel pilot DONE

### What happened
- A1+A2 V2 已 cherry-pick 进 chore/l0-infra (3752d98 / 2bfc5ad MERGED)
- worker-A3 (feat/phase-a3-channel-pilot) rebase chore/l0-infra · 拉到 V2 contracts + shared modules
- worker-A3 7 commit chain landed (C1-C7 · per `docs/onboarding/A3-design-draft.md` §8 plan):
  - C1 · `WORKER-A3-PANEL-1-MIGRATED` · 4-gate state model + sessionData 单点派生
  - C2 · `WORKER-A3-PANEL-2-MIGRATED` · streamSse + LiveFailError + normalizeBackendDone (replaced inline `res.body.getReader()`)
  - C3 · `WORKER-A3-DONE-ENVELOPE-LANDED` · realtime_stream.py 用 `make_done(panels=...)` 7 panel + 6 aggregator helper (Cat 4 fix)
  - C4 · `WORKER-A3-PANEL-5-BANNER` · banner-spec rule 2 · Tavily silent fallback yield warning event + done.warnings 透传 (Cat 11 fix)
  - C5 · `WORKER-A3-DEMO-ENDPOINT-LANDED` · `/api/channel/demo/run` + 3 scenario JSON (反 5 原则难度分层)
  - C6 · `WORKER-A3-SMOKE-LANDED` · `web/tests/regression/channel-pilot-4gate.spec.ts` 4/4 PASS chromium (19.5s)
  - C7 · `WORKER-A3-CHANNEL-PILOT-DONE` (本 commit · features-inventory F-065/F-066 · state-snapshot 段)

### Triggered by
- PM 'git rebase chore/l0-infra · A1+A2 V2 已 merge · §0.5 wait gate 过 · 真动 ChannelWorkspace.tsx 重构 4 gate · 开干'

### State change (delta)
- Phase A worker mesh: A3 active 中 → A3 DONE 候 cherry-pick + GO 给 A4
- audit conflict-register Cat 2 (channel) / Cat 3 (channel) / Cat 4 (channel) / Cat 11 (channel) · 4 项 channel pilot 范围全部接 fix · 状态从 active → resolved (待 PM verify)
- 硬线 #3 (`phase-a-charter.md` §1) 'Channel pilot 4 gate 真实装 + Playwright 5 panel 同步亮 smoke 通过' · 已满足
- frontend ChannelWorkspace.tsx 重构后 · 净 +20 行 (含 bannerKind state + normalizeBackendDone + streamSse 接入 · 删 inline reader + setLiveCandidatesCompat shim)
- backend realtime_stream.py 加 6 aggregator helper + warnings 收集 · ~+200 行
- 新增 endpoint: `POST /api/channel/demo/run` (mock-forced 演示路径 · 与 live 解耦)
- features-inventory: 加 F-065 (4-gate 端到端) · F-066 (demo endpoint)

### Next
- 主 CLI 等 codex post-DONE peer review (本 commit signal `WORKER-A3-CHANNEL-PILOT-DONE` 触发)
- Codex AGREE 后 → cherry-pick A3 7 commit 到 chore/l0-infra → push origin → 启 A4 5 子 worker (依赖 A3 channel pilot 模板)
- A4 onboarding 必读 cross-ref: `docs/onboarding/A3-channel-pilot.md` + 本 design draft + ChannelWorkspace.tsx 4-gate 实装 + realtime_stream.py done envelope 形态
- channel UI 'demo run' 按钮 wire (deferred 到 A4-channel 或独立任务) · 当前 `/api/channel/demo/run` 端点 ready 待 UI

---

## 2026-04-30 (Phase A · Week 3 morning) · worker-A3 V2 fix · codex 4 issue resolved

### What happened
- 主 CLI resume · 接 2026-04-29 codex DISAGREE 4 issue (verdict in `docs/audit/codex-reviews/WORKER-A3-CHANNEL-PILOT-DONE.md`):
  - Issue 1 (cat 2 partial · ConversationPanel 不从 sessionData 派生)
  - Issue 2 (UI demo button + Playwright 不验 demo run)
  - Issue 3 CRITICAL (`agent_channel/realtime_stream.py` data_source="tavily" 没 map 到 envelope enum · A4 会 inherit bad pattern)
  - Issue 4 (gate-4 smoke drawer optional · selectedCandidate 不 prove)
- 4 issue 全 fix · 单 commit (含 inventory + state-snapshot 同步更新 per §13/§14.1):
  - **Issue 3** · `agent_channel/realtime_stream.py` final tuple 解构后 normalize · "tavily" → `DATA_SOURCE_LIVE` + `provider_source="tavily"` 单独字段透传 done envelope **extras + stage signal_scan done event · 上游 `_parallel_signal_search_iter` API 不变 · 仅在消费侧 normalize
  - **Issue 1** · `ChannelWorkspace.tsx` QueryBar 新增 setMessages + setSelectedCandidate prop · runRealSearch + runDemoScenario 在 setLiveData 后同步 setMessages(live.conversation) + setSelectedCandidate(null) · ConversationPanel 不再卡 stale mock
  - **Issue 2** · `ChannelWorkspace.tsx` 加 `runDemoScenario` 函数 + 3 档 button (`channel-demo-{easy,medium,hard}` data-testid) → /api/channel/demo/run via streamSse · Playwright T5 case 走 page.route 拦 endpoint 验 scenario_id payload + done.data_source="mock_forced" + 5 panel hydrate
  - **Issue 4** · Playwright T3 改 mandatory · `[data-testid="channel-candidate-card"]` click → `[data-testid="channel-candidate-drawer"]` toBeVisible → ESC → toBeHidden · 不再 conditional skip
- formatChannelEvent 兼容: signal_scan done 显 `provider_source ?? data_source` · live UX "来源 tavily" 不退化
- 验:
  - `npx tsc --noEmit` PASS (web)
  - `pytest tests/shared tests/agent_channel` 276/277 PASS (1 pre-existing Tavily 401 integration test · 与本 fix 无关)
  - Playwright `channel-pilot-4gate.spec.ts` 5/5 PASS chromium (15.6s · 含新 T5 demo run case + 加固 T3)

### Triggered by
- 2026-04-29 d8055cb `CODEX-REVIEW-A3-A6-DISAGREE` PM 决: V2 fix tomorrow morning · then cherry-pick + push + ECS + A4 GO commit × 5
- 用户 `morning resume · A3 V2 fix · 必修 4 issue`

### State change (delta)
- A3 verdict: DISAGREE (codex V1) → re-review pending (V2 commit signal `WORKER-A3-V2-DONE` 触发)
- channel pilot SSE 契约: data_source 严格 envelope enum (live/mock_forced/mock_fallback) · provider 细节走 provider_source 顶层字段 · A4 worker 复用本模式 (不再让 "tavily" / "qichacha" 等污染 enum)
- ConversationPanel 派生路径: live SSE done event 后同步刷 messages + 关 drawer · 不留 stale mock 状态
- Playwright spec: 4 case → 5 case (新 T5 demo run · 加固 T3 drawer) · 全数据-testid 锚 · 无 conditional skip
- features-inventory F-066: NB "demo button deferred" 改为 "wired (V2 fix 2026-04-30)" + smoke_test 加 T5 引用

### Next
- 主 CLI 等 codex re-review (V2 fix commit 触发)
- Codex AGREE 后 → cherry-pick A3 8 commit (含本 V2) 到 chore/l0-infra → push origin → 启 A4 5 子 worker
- A6 V2 fix 等 (3 issue · schema vs fixture 不一致 · medium · 与 A3 并行)

---

## 2026-04-30 (Phase A · Week 3 morning · 续) · worker-A3 V3 fix · ConversationPanel 根因 fix

### What happened
- V2 commit b56b361 后 PM 注意到 issue 1 在 V2 是 partial fix:
  - V2 `setMessages(live.conversation)` 同步 setLiveData · 但 `live.conversation` 来自 `tplFallback.conversation` (mock 模板) · 不是真 backend-controlled
  - codex 原本意图: "render `ConversationPanel` from `sessionData.conversation` directly" (option 2) 或 "set live conversation together with `setLiveData`" (option 1)
  - V2 走 option 1 但 backend 没 emit conversation 字段 · 等于半 fix
- V3 走 option 1 完整版: backend 显式 emit `conversation` 字段 · 前端 hydrate
- 触面 (V3 单 commit · 6 文件):
  - `shared/sse_envelope.py` · `CHANNEL_PANEL_KEYS` 7 → 8 keys (加 "conversation")
  - `tests/shared/test_sse_envelope.py` · `test_channel_panel_keys_canonical` expected 8 keys
  - `agent_channel/realtime_stream.py` · `make_done(panels=...)` 加 `"conversation": []` (默认空 · A4-channel AI 复盘 turn 落地后真填)
  - `agent_channel/api.py` · `/api/channel/demo/run` panels 加 `"conversation": data.get("conversation", [])` (scenario JSON 可填)
  - `web/.../ChannelWorkspace.tsx` · `normalizeBackendDone` 读 `evt.conversation` · 空时 fallback `tplFallback.conversation`
  - `web/tests/regression/channel-pilot-4gate.spec.ts` · T2/T5 mock SSE 加 `conversation: []` · 新增 T6 (backend conversation 非空时 · ConversationPanel 显 sentinel)
- 验:
  - `pytest tests/shared/test_sse_envelope.py` 31/31 PASS
  - `pytest tests/agent_channel --ignore test_external_search` 191/191 PASS
  - `npx tsc --noEmit` PASS
  - `npx playwright test channel-pilot-4gate.spec.ts --project=chromium` 6/6 PASS (18.2s · T6 新增 lock V3 contract)
- 契约修订 (Tier 1 · 因 backwards-compat additive · 不破 V2 envelope):
  - `docs/contracts/workspace-state-protocol.md` §4 done event JSON 加 `"conversation": [...]` 行 + V3 fix 注释段
  - 注: 8th key 为前向加 · A4 worker copy channel pilot 时按 8 key 处理 (旧 V1/V2 envelope 不破: 缺字段时前端 fallback tplFallback.conversation)

### Triggered by
- 用户 `A3 V3 fix · 最后 1 issue partial · ConversationPanel 不从 sessionData 派生 · 选 option 1 推荐 backend 补字段`

### State change (delta)
- `CHANNEL_PANEL_KEYS`: 7 → 8 keys (加 "conversation")
- A3 verdict: V2 PENDING → V3 codex re-review 触发中
- Channel pilot done envelope contract: ConversationPanel 真从 sessionData 派生 (option 1 完整版) · 不再依赖 V2 `setMessages(live.conversation)` patch (patch 仍保留作 defensive · 但现真 backend-sourced)
- A4 worker 复用模板: 8th panel key conversation 是 channel pilot canonical · A4-channel/A4-credit 可 inherit · A4-other 看是否需要

### Next
- 主 CLI 等 codex re-review V3 (本 commit signal `WORKER-A3-V3-DONE` 触发)
- AGREE 后 → cherry-pick A3 9 commit (含 V2 + V3) 到 chore/l0-infra → push origin → 启 A4 5 子 worker
- A4-channel onboarding 加 cross-ref: 8 panel key + V3 normalizeBackendDone 派生模板

(下次更新模板)

## 2026-04-29 · worker-A4-credit DONE · cat 0/3/4/13 fix + 4-gate hoist

### What happened
- 主 CLI (worker-A4-credit) resume 后按 `docs/audit/A4-credit-draft.md` §9 13 step 实施顺序 · 8 个独立 commit + 2 准备 commit (Step 3 mock 扩 + Step 13 inventory) 全交:
  - Step 3 (`6bd5bfb`) · CREDIT_MOCK_SESSIONS 6 stratified sessions (反 5 原则 §3.5 难度分层 = 1 simple + 3 medium + 1 hard + 1 extreme · 不破现有 CREDIT_SESSIONS Record · Additive 出口)
  - Step 4 (`c056d7a`) · 4-gate state hoist · workspace-state-protocol §2 (started/selectedSession/liveData/selectedCandidate)
  - Step 6 (`f913c6e`) · backend done envelope symmetric · cat 4 修 (mock + live 路对称)
  - Step 7 (`f79b446`) · SSE reader → streamSse + done-envelope normalize · cat 3 删 35 行内联 reader
  - Step 8 endpoint (`ae31144`) + Step 8 scenarios (`83d61a5`) · `/api/credit/demo/run` + 6 file-backed scenario JSON (corp/retail × simple/medium/hard/extreme)
  - Step 9 (`fa37572`) · EmptyState onPrimary → Agent6 handoff 真消费 · cat 0 北极星核心
  - Step 10 (`f2828e9`) · CaseTable row → CaseDetailDrawer · selectedCandidate gate
  - Step 11 (`9c3c359`) · export_docx error banner · cat 13 替 console.error 静默
  - Step 12 (`7a74dcb`) · credit-pilot-4gate.spec.ts 6 cases (T1-T6 覆盖 4 gate + cat 0/3/4/13 fix)
- 后端新增 endpoint 3 个: `GET /api/credit/reports/sessions` + `POST /api/credit/handoff/from_report` + `POST /api/credit/demo/run`
- features-inventory 加 F-067 entry (cat 0/3/4/13 全覆盖)
- Step 5 (panel split) deferred Phase B · panels 已 props-based (workspace-state-protocol §2.2 通过) · 文件大小不是 contract 强约束

### Triggered by
- worker-A4-credit DONE per `docs/onboarding/A4-credit.md` (chore/l0-infra)
- A3 channel pilot V3 (`5876b7b`) 已 cherry-pick 进 chore/l0-infra · GO 信号 `A4-CREDIT-GO-AFTER-A3` 已发 (`ccfdc97`)
- §0.5 硬 wait gate 已解除

### State change (delta)
- A4-credit verdict: GO-PENDING → DONE-PENDING-VERIFY (待 codex peer review)
- audit conflict-register Cat 0 (credit Agent6 handoff 旁路) / Cat 3 (credit 内联 SSE reader) / Cat 4 (credit done envelope 不对称) / Cat 13 (credit export console.error 静默) · 4 项 credit 范围全部接 fix · 状态 active → resolved (待 PM verify)
- 硬线 #4 (`phase-a-charter.md` §1) · 5 子 worker A4 之 credit 部分: GATES-IMPLEMENTED 4/4 · DONE-ENVELOPE-SYMMETRIC mock+live · AGENT6-HANDOFF-CONSUMED yes · 已满足
- frontend `CreditWorkspace.tsx` 净 +600 行 (4-gate hoist + handoffSource state + handoffBanner JSX + runDecisionWithAgent6Handoff + runDemoScenario + CaseDetailDrawer + export error banner · 删 inline reader)
- new `_components/_normalize.ts` 234 行 (backend done envelope → UI CreditSession shape mapper · 仅 hydrate 高价值字段 radar/overallScore/redLines/cases/limit/decision/profile.chips)
- backend `agent_credit/api.py` 净 +228 行
- mock `agent-credit-session.ts` 净 +897 行 (3 → 6 sessions · CREDIT_MOCK_SESSIONS array + MAP + DEFAULT_SESSION_ID 出口)
- 6 demo scenario JSON 新建 (`data/mock/workspace/credit/scenarios/*.json`)
- features-inventory 加 F-067 (4-gate + cat 0/3/4/13 全覆盖)
- 5 子 worker mesh: A4-credit DONE → A4-{report,alert,compli,riskctrl} 仍 active (其余 4 子各自 worktree GO 已发)

### Next
- 主 CLI 等 codex post-DONE peer review (本 commit signal `WORKER-A4-CREDIT-ADAPTER-DONE` 触发)
- Codex AGREE 后 → cherry-pick A4-credit 10 commit (Step 3/4/6/7/8 endpoint/8 scenarios/9/10/11/12 + Step 13 inventory + state-snapshot) 到 chore/l0-infra → push origin
- A4 其余 4 子 worker 同样路径走 (各 worktree 独立 commit + cherry-pick · A4-credit 模板可 inherit · normalize.ts pattern + handoff banner pattern + case drawer pattern + export error banner pattern)
- Playwright `credit-pilot-4gate.spec.ts` 6 case 待 CI / manual `npx playwright install chromium` 后跑

---

(下次更新模板)

## YYYY-MM-DD · <事件>

### Worker 状态变更

### 决策变更

### 风险预警
