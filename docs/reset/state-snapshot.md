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

## 2026-04-29 (本批次 4) · worker-A7 PRD drift table v1 ready (pre-PM 拍板)

### What happened
- worker-A7 (feat/phase-a7-prd · 复用 work-A3-prd worktree) resume + rebase chore/l0-infra 拿 A1+A2 V2 (3752d98 + 2bfc5ad)
- 读 4 关键 context: RESET_MASTER + phase-a-charter + prd-evidence-frozen 70% + conflict-register-v1 + codex draft A7-prd + agent-naming-ssot v1.0
- 扩展 `docs/audit/prd-evidence-frozen.md` 99 → 206 行:
  - 修 Section 2 Agent4/Agent5 关于"无 F-XXX"过时声明 (实 F-020~F-027 + F-049/F-055 已建)
  - 加 Section 4 · per-agent drift table 5 列 (Original Intent / Current State / KRR / Evidence / Owner+Deadline+Acceptance) · 6 agent each (4.1-4.6) + 4.7 coverage summary
  - 加 Section 5 · PM 裁决候选清单 (10 G-XX 一行 · 8 🟢 默认追认 + 2 🟡 必拍归属) + 5.1 批量 GO 路径 + 5.2 飞书双写流程
  - 加 Section 6 · 0 新 PRD-level gap (10 G-XX 已穷举)

### Triggered by
- A7 onboarding §1.1 (PRD 取证 + drift table + master/sub PRD)
- PM 指令 "继续 PRD draft + drift table"

### State change (delta)
- prd-evidence-frozen.md: 70% (Section 1+2+3 list) → 100% drift table v1 (Section 1-6 全覆盖 5 列)
- worker-A7 状态: §0 worktree resume → §1.1 drift table 完 · 等 PM 拍板 cycle
- Phase A 硬线 #7 进度 (master+6 sub PRD): 0% → 30% (drift ready · master/sub 待 PM 拍板后写)

### 风险预警
- G-05/G-06 codex draft 反对纯 PRD 越界占用 A6 schema · A7 已标 🟡 PM 拍板归属项 · 不自决
- G-08 事件订阅工程量大 · A7 建议 Phase B-3 推延 · 但 PRD 触发源是 Agent5/Agent4 边界本质 · PM 必拍
- G-09 业务单号粒度 待主 CLI 跑 ComplianceWorkspace F-026 真路径验后决 · A7 不能盲拍

### Next
- worker-A7 commit drift table 扩展 (no signal yet · pre-PM cycle)
- 通知 PM: drift table ready · §5.1 批量 GO + §5.2 双 🟡 归属拍板
- PM 拍板 (signal: `WORKER-A7-PRD-DRIFT-PM-RULED`) → A7 进 master + 6 sub-PRD draft + 飞书双写 → signal: `WORKER-A7-PRD-MASTER-DONE`
- §1.2 legacy_gradio 全栈隔离 + §1.3 active rule 回写 与 PRD draft 并行 (autonomous · 不阻 PM)

---

## 2026-04-29 (本批次 5) · worker-A7 legacy_gradio 全栈隔离 (Block B 完)

### What happened
- worker-A7 落地 PM 拍板 #4 "legacy_gradio 物理保留 + 全栈隔离" (5 件):
  1. `legacy_gradio/__init__.py` 新建 · `ALLOW_LEGACY_GRADIO=1` 才允许 import · 默认抛 `ImportError`
  2. `pyproject.toml` 4 处加 exclude: `pytest.norecursedirs` / `ruff.extend-exclude` / `coverage.omit` / `mypy.exclude`
  3. CLAUDE.md §16 新增章节 "Archived: legacy_gradio (备用 · 全栈隔离)" · 含隔离方式 5 件 + emergency 解锁 + 真删条件 + v15 vs v16 对比表
  4. CLAUDE.md §2 line 12 改 "如需 fallback 演示从 archive 恢复" → "全栈隔离 · 详 §16"
  5. RESET_MASTER_PLAN.md §6 红线区加"不读 legacy_gradio/" 红线 (worker / Codex / 任何 Agent 不读不引)

### Triggered by
- A7 onboarding §1.2 (PM 拍板 #4 第 4 件 · per phase-a-charter 加项)
- Block B autonomous · 不阻 PM 拍板 cycle (与 Block A drift table 并行)

### State change (delta)
- legacy_gradio: physical 保留 · 但所有工具链 (pytest/ruff/coverage/mypy) 不再扫 · 主线代码 import 抛 ImportError
- CLAUDE.md: §15 末 → §16 新增 (CLAUDE.md 总章数 15 → 16)
- worker-A7 状态: drift table v1 ready (Block A 等 PM) → +Block B 完 (pending Block B commit)

### Next
- Commit Block B (5 件合 1 commit · Signal: `WORKER-A7-LEGACY-GRADIO-ISOLATED`)
- 进 Block A.0: 3 active rule 回写 CLAUDE.md (Q-040 MAX_ROWS / Q-041 candidate metadata 4 字段 / PIPL fallback chain)
- 进 Block A.1-A.7: master + 6 sub-PRD draft + 飞书双写

---

(下次更新模板)

## YYYY-MM-DD · <事件>

### Worker 状态变更

### 决策变更

### 风险预警
