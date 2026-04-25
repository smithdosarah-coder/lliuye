# Phase 3-Final · 轨 4 · 前端整合（7 frozen branch 融合）Onboarding

**状态**：Phase 3-Final GO（**Wave 2 起 · 等 Wave 1 三轨合流后再 dispatch**）
**发布日期**：2026-04-25
**Signal 入口**：`PHASE-3-FINAL-T4-ACK`
**前置**：Wave 1（轨 1 agent6 + 轨 2 agent3 + 轨 3 agent1-cherry）全 APPROVED merged 到 chore/l0-infra · commit `4f2132e ORCHESTRATOR-HANDOFF-PHASE-3-FINAL-PLANNED` + Q-032
**参照决策**：`docs/handoff/decisions-log.md` Q-031（7 前端 branch 冻结 · 已被 Q-032 推翻）/ Q-032（Phase 3-F 8 轨规划） + `docs/handoff/session-2026-04-25-phase-3-final-handoff.md` §3 + §4.4 + `docs/scorecard/dod-current-status-2026-04-24.md`
**强制 spec**：`CLAUDE.md` §7 platform shell v2 + `docs/design/platform-shell-v2.md` + `design_mockups/rm-assistant-final-2026-04-19.html`（视觉 1:1 复刻源 · sha256 25155e74...）
**worker 建议**：新建 worktree `code-frontend-integration`（fork from `chore/l0-infra` · 新分支 `feat/frontend-integration` · Codex 辅助大批量 tsx 脏活 · 决策走 Claude）
**Final Signal**：`READY-FOR-FRONTEND-INTEGRATION-REVIEW`
**中间 signal 链**：`FRONTEND-INTEGRATION-ACK` → `FE-STAGE-1-SHELL-BASE-DONE` → `FE-STAGE-2-AGENT-WORKSPACE-DONE` → `FE-STAGE-3-DISPATCH-IM-DONE` → `FE-STAGE-4-HERO-POLISH-DONE` → `FE-STAGE-5-SMOKE-DONE` → `READY-FOR-FRONTEND-INTEGRATION-REVIEW`

---

## 1. 背景与目标

### 1.1 7 frozen branch 现状

mesh.json `frozen_branches_no_worktree[]` 共 7 条，全部是 Q-031 时代"做一半"的关键产出（Q-032 推翻"冻结"决策 · 全部激活）：

| branch | 形态 | main 当前缺件 | REVIEW 状态 |
|---|---|---|---|
| `feat/shell-free-drag` | PanelCanvas.tsx + Whiteboard.tsx 组件本体 + PANEL_PIN drop zone + MessagePinHandle 双 MIME | 组件 0 命中 main · store 都在 | 未 REVIEW |
| `feat/canvas-mode-toggle` | CanvasModeToggle 组件 + ⌘⇧F hotkey + localStorage 持久化 + panel-layout-store clearAgent action | CanvasModeToggle 组件 0 命中 main | 未 REVIEW |
| `feat/alert-codex-fusion` | AlertWorkspace Codex 融合 6 step（pin + queue + heat bars + CTA 5 步 + 左栏扫描范围/知识库/监测源 + ConversationPanel） | AlertWorkspace 751 行 · 无 queue-heat / 无 CTA 5 步 / 无左栏 drop zone | **REVIEW-READY**（直接合 · 不再 worker 自审）|
| `feat/compliance-codex-fusion` | ComplianceWorkspace Codex 融合 6 step（mock + shell drop zone + matrix drawer 左右对照 + 底部修订意见栏 + pin） | ComplianceWorkspace 757 行 · 无 matrix drawer / 无 advice bar | **REVIEW-READY** |
| `feat/credit-mock-endpoint` | `/api/credit/mock-session` corp/small/retail 三板块 | 0 命中 main | 未 REVIEW |
| `feat/chat-wechat-style` | ConversationPanel 类微信气泡 + dispatch 左侧线程分群组/私聊 + demo pickReply + typing dot | ConversationPanel 浅 · dispatch 群组/私聊分段缺 | 未 REVIEW |
| `feat/agent-workspaces-v2` | 5 agent archive hero redesign（riskctrl KS×AUC / compliance policy ticker / alert traffic light / credit dashboard / report pipeline）· net -126 行 replace | RiskctrlWorkspace 976 行 · 36 处 KS/AUC 匹配但 hero band 形态非 v2 | 未 REVIEW |

### 1.2 解 DoD 条目（参照 handoff §1.3 + §3.1）

- **L1-3 核心可视化 4 条全解**：Agent4 红黄绿盘（alert-codex）· Agent5 政策矩阵（compliance-codex）· Agent2 KS 图表（agent-workspaces-v2）· Agent3 雷达 / dashboard（credit-mock-endpoint + agent-workspaces-v2）
- **L1-3 shell 交互基础**：PanelCanvas / Whiteboard / CanvasModeToggle / Desk drawer 本体齐
- **L1-3 dispatch IM 完整化**：ConversationPanel 微信气泡 + 线程分群组
- **Agent1 信号时间线**：本轨 7 branch 不含 · 由轨 7 docs-compliance 兜底新写

L1-3 score 当前 60% → 本轨贡献后 ~85%（剩余 15% 由轨 7 收尾）。

### 1.3 硬边界

**只动**：`web/src/components/shell/` + `web/src/app/archive/{alert,compliance,credit,channel,report,riskctrl}/_components/*Workspace.tsx` + `web/src/app/dispatch/_components/*` + `web/src/lib/store/panel-layout-store.ts`（**仅 clearAgent action 扩展 · 任何其他 store 改动走 RFC**） + `web/src/app/api/credit/mock-session/route.ts`（新建）+ `web/tests/*.spec.ts`（既有 spec 验证 · 不删）+ `docs/screens/frontend-integration/`（截屏产物）

**不动**：
- 后端 `agent_*/` / `shared/` / `api_server.py` / `v16_*.py` / `evaluation/`
- 红区 `financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py`
- legacy 顶层 6 页 `web/src/app/{channel,credit,alert,compliance,report,riskctrl}/page.tsx`（路由收敛是单独 task · 见 CLAUDE.md §7 路由拓扑红线）
- `web/src/lib/store/*` 除 panel-layout-store.clearAgent 外其余 store

### 1.4 §7 spec 强制对齐

CLAUDE.md §7 platform shell v2 spec 明文 · 任何偏离立即 REJECT-V2：

- **4 view canon**：`/today` / `/dispatch` / `/archive` + `/archive/[agent]` 动态路由 / `/warroom`
- **4 主题**：Canvas（默认 米黄→橙红→墨绿）/ Matcha（抹茶）/ Dusk（暮粉桃花）/ Ink（水墨 · 替换 v1 Letterpress 黑红）
- **6 Agent functional color**：`--t-report` 棕赭 / `--t-alert` 赭红 / `--t-compli` 墨绿 / `--t-credit` 青蓝 / `--t-riskctrl` 绛紫 / `--t-channel` 青绿
- **Float-badge SVG**：落日(Canvas) / 禅圆 enso(Matcha) / 桃花(Dusk) / 太极(Ink)
- **字体栈**：Funnel Display / Instrument Sans/Serif / Noto Sans/Serif SC / JetBrains Mono
- **圆角**：`--r-md: 18px` / `--r-lg: 26px`
- **动画**：bodyBreath 22s / drift 38s / breathe 8.5s / glyph-rise stagger / rise / card-rise / bar-in / case-in / bar-flow / wait-slide / blip
- **Desk hover-from-edge**：< 22px 触发 + pin/Esc/⌘K
- **live clock**：20s tick

任何引入 Letterpress / crimson / 老 `--color-brass` / `--color-ink` / `ink-brush-hr` 老 tokens → **立即 REJECT**。

---

## 2. Task 清单

### Task A · Stage 1 · shell 基础组件（Day 1-2）

**目标**：把 PanelCanvas + Whiteboard + CanvasModeToggle 三个组件本体合到 main，shell 交互基础齐。

**步骤**：
1. `git worktree add ../code-frontend-integration -b feat/frontend-integration chore/l0-infra`
2. cherry-pick 或 merge `feat/shell-free-drag` → 引入 `web/src/components/shell/PanelCanvas.tsx` + `Whiteboard.tsx` + PANEL_PIN drop zone + MessagePinHandle 双 MIME
3. cherry-pick 或 merge `feat/canvas-mode-toggle` → 引入 `web/src/components/shell/CanvasModeToggle.tsx` + ⌘⇧F hotkey hook + localStorage 持久化 + `panel-layout-store.ts` clearAgent action 扩展
4. 编译闸门：`cd web && npx tsc --noEmit && npm run build`（**0 error**）
5. 跨 view 手测：4 view 切 · CanvasModeToggle 可见 + 触发 + ⌘⇧F 工作

**约束**：
- 两 branch 可并行 cherry-pick · 组件本体冲突概率低
- panel-layout-store 改动**仅限 clearAgent action 添加** · 其他 store 触动立即停 + RFC
- 不动 §7 spec 任何 token / 主题

**完成信号**：`Signal: FE-STAGE-1-SHELL-BASE-DONE`

---

### Task B · Stage 2 · agent workspace Codex 融合（Day 3-5）

**目标**：合 alert / compliance / credit 三 workspace 的 Codex 融合 + mock 端点 + 严格保 Batch 2 EvidenceTrail。

**步骤**：
1. cherry-pick / merge `feat/alert-codex-fusion`（**REVIEW-READY · 直接合 · 但仍需解 EvidenceTrail 兼容**）
   - AlertWorkspace 扩 queue + heat bars + CTA 5 步进度 + 左栏扫描范围/知识库上传/监测源 + ConversationPanel + pin
2. cherry-pick / merge `feat/compliance-codex-fusion`（**REVIEW-READY**）
   - ComplianceWorkspace 扩 mock + shell drop zone + matrix drawer 左右对照纸 + 底部修订意见栏 + pin
3. cherry-pick / merge `feat/credit-mock-endpoint`
   - 新建 `web/src/app/api/credit/mock-session/route.ts` corp/small/retail 三板块
   - CreditWorkspace 消费 mock-session 端点
3a. **agent3 RiskRadar 补 (Q-033 backlog · 2026-04-25 加)**：
   - 来源：原 commit `596283f feat(agent_credit): L1-3 RiskRadar thin wrapper` from
     `feat/agent3-productize` pre-rebase tip (= `6c5820a`)
   - 内容：`web/src/app/credit/components/RiskRadar.tsx` (48 行) + `web/src/app/credit/page.tsx` (6 行 wiring)
   - 注意：原 SHA 596283f 已被 agent3 P3F rebase 时 auto-dropped empty (web/ 红线触发) ·
     但内容应被本轨 Stage 2 吸收 · 用 `git show 596283f` 取 patch 应用
   - 路径迁移：原文件在 `web/src/app/credit/` (legacy 路由) · 本轨需改路由到
     `web/src/app/archive/credit/_components/RiskRadar.tsx` (canon `/archive/[agent]` 路径)
   - 解 DoD: L1-3 Agent3 RiskRadar (合本轨后 closes Q-033 follow-up)
   - 测试：新增 `web/tests/risk-radar.spec.ts` 验渲染 + 4 维度入参
4. **每 rebase 必须保留 Batch 2 EvidenceTrail 挂载**：
   - `<EvidenceTrail>` 在 6 个 `/archive/*/_components/*Workspace.tsx` 的挂载点不能丢
   - 冲突时**双方共存**：保留 EvidenceTrail + 吸收 Codex 融合新功能
5. spec 校验：`web/tests/evidence-trail.spec.ts` + `highlight-card.spec.ts` + `unfilled-marker.spec.ts` 全绿
6. 编译闸门：`cd web && npx tsc --noEmit && npm run build`

**约束**：
- alert + compliance 已 REVIEW-READY · merge 用 `git merge --no-ff` 保留历史
- credit-mock-endpoint 未 REVIEW · worker 自审 + diff 对齐 §7 spec
- EvidenceTrail 挂载点**任何丢失即 REJECT-V2**

**完成信号**：`Signal: FE-STAGE-2-AGENT-WORKSPACE-DONE`

---

### Task C · Stage 3 · dispatch IM 扩展（Day 6）

**目标**：合 chat-wechat-style · ConversationPanel 微信气泡 + dispatch 左侧线程分群组。

**步骤**：
1. cherry-pick / merge `feat/chat-wechat-style`
   - ConversationPanel 类微信气泡（输出气泡 + typing dot + pickReply 假聊天）
   - dispatch 左侧线程分群组 / 私聊
2. 与 Stage 2 结果叠加（alert / compliance 已 import ConversationPanel）· 可能存在 prop drift · 解冲突保 Stage 2 + Stage 3 双方
3. 编译闸门 + 跨 view 手测

**约束**：
- dispatch 路由 `/dispatch` canon 不变 · 不引入新顶层路由
- 假聊天 demo pickReply 留 dev mode flag · 生产模式不挂

**完成信号**：`Signal: FE-STAGE-3-DISPATCH-IM-DONE`

---

### Task D · Stage 4 · 视觉 polish（Day 7）

**目标**：合 agent-workspaces-v2 · 5 agent hero band redesign。**最后合 · 因为它是 net -126 行 replace 型 · 合早了会被 Stage 1-3 覆盖**。

**步骤**：
1. cherry-pick / merge `feat/agent-workspaces-v2`
   - riskctrl KS×AUC hero / compliance policy ticker / alert traffic light / credit dashboard / report pipeline
2. **关键决策点**：v2 hero band 与 Batch 2 EvidenceTrail + Stage 2 Codex 融合可能不兼容
   - **兼容**：直接 merge
   - **不兼容**：降级到 cherry-pick 单 agent 部分（保 Codex 融合不被 hero 覆盖）· final body 写明降级理由
3. 编译闸门 + 跨 view 手测 + EvidenceTrail spec 全绿

**约束**：
- v2 hero 不能引入 Letterpress / crimson 老色
- riskctrl KS×AUC hero 解 L1-3 Agent2 KS 图表 DoD · 必合
- 视觉与 mockup `rm-assistant-final-2026-04-19.html` 1:1 对齐

**完成信号**：`Signal: FE-STAGE-4-HERO-POLISH-DONE`

---

### Task E · Stage 5 · 跨 browser smoke + 截屏（Day 8）

**目标**：跨 browser 验证 4 主题 × 4 view 全通 · 截屏留证。

**步骤**：
1. **手测矩阵**：
   - browser：Chrome 111+ + Edge 111+（银行内网兼容主线）
   - 主题：Canvas / Matcha / Dusk / Ink 4 套
   - view：/today / /dispatch / /archive（含 6 agent tile 跳转） / /warroom
   - 总计 2 browser × 4 主题 × 4 view = **32 个屏幕**
2. **截屏留证**：每个屏幕一张 PNG · 落 `docs/screens/frontend-integration/{browser}/{theme}/{view}.png`
3. 跑全量 web/tests/*.spec.ts · 期望 0 fail
4. 跑 `cd web && npm run build` · 0 error / 0 warning

**约束**：
- 截屏分辨率 ≥ 1440×900 · 全屏（含 Masthead + Desk + Float-badge）
- 主题切换走右下 Float-badge 4 按钮 · 不走 dev tools / localStorage 直改
- 失败截屏立即 Q-NNN askout · 不修无证据 bug

**完成信号**：`Signal: FE-STAGE-5-SMOKE-DONE` → 紧接 `Signal: READY-FOR-FRONTEND-INTEGRATION-REVIEW`

---

## 3. 验收硬指标（T4-1 ~ T4-15 · 15 项）

| # | 指标 | 阈值 | 判定 |
|---|---|---|---|
| T4-1 | 7 branch 全 rebase 或显式 SKIP | final body 列出 7 branch 处理结果（merge SHA / cherry-pick / SKIP 决策 + 1 句理由） | 看 body |
| T4-2 | 编译闸门每 stage 后 0 error | `cd web && npx tsc --noEmit` 5 次 + `npm run build` 5 次全绿 | exit 0 |
| T4-3 | Batch 2 EvidenceTrail spec 全绿 | `web/tests/{evidence-trail,highlight-card,unfilled-marker}.spec.ts` 全过 | playwright exit 0 |
| T4-4 | §7 spec 全守 | 4 主题 token / Masthead 4 tab / Float-badge 4 SVG / Desk hover<22px / live clock 20s · grep + 视觉验证 | grep + 截屏 |
| T4-5 | legacy 顶层 6 页 0 改动 | `git diff origin/chore/l0-infra...HEAD --name-only \| grep -E "web/src/app/(channel\|credit\|alert\|compliance\|report\|riskctrl)/page.tsx"` 为空 | git diff |
| T4-6 | canon /archive/[agent] 修改限于 _components | `git diff --name-only \| grep "web/src/app/archive"` 全部在 `_components/` 下 | git diff |
| T4-7 | 视觉 1:1 复刻 mockup | 截屏与 `design_mockups/rm-assistant-final-2026-04-19.html` 视觉对照（Float-badge / 圆角 / 字体栈 / 4 主题色） | 视觉 review |
| T4-8 | 5 stage signal trailer 齐 | STAGE-1/2/3/4/5 + READY 共 6 段 single-line trailer | git log grep |
| T4-9 | 红区 0 漂移 | `web/src/lib/store/*` 仅 panel-layout-store.clearAgent 改动 · `financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py` 0 改动 | git diff |
| T4-10 | shell 三组件存在 | `ls web/src/components/shell/{PanelCanvas,Whiteboard,CanvasModeToggle}.tsx` 全有 | ls |
| T4-11 | /api/credit/mock-session 端点存在 | `ls web/src/app/api/credit/mock-session/route.ts` | ls |
| T4-12 | AlertWorkspace queue-heat + CTA 5 步可见 | grep `queue-heat`/`CTA 5` in `AlertWorkspace.tsx` + 截屏验证 | grep + 视觉 |
| T4-13 | ComplianceWorkspace matrix drawer 可见 | grep `matrix-drawer` in `ComplianceWorkspace.tsx` + 截屏 | grep + 视觉 |
| T4-14 | ConversationPanel 微信气泡 + dispatch 群组分段 | grep `bubble`/`thread-group` + 视觉 | grep + 视觉 |
| T4-15 | 跨 browser 截屏 32 张 | `ls docs/screens/frontend-integration/{chrome,edge}/{canvas,matcha,dusk,ink}/{today,dispatch,archive,warroom}.png` 全 32 张 | ls |

---

## 4. 红线

### ❌ 不动

- ❌ **legacy 顶层 6 页**（路由收敛单独 task · 全链路扫查后再动 · 详见 CLAUDE.md §7）
- ❌ **后端**（`agent_*/` / `shared/` / `api_server.py` / `v16_*.py` / `evaluation/`）
- ❌ **红区**：`financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py` / `web/src/lib/store/*`（除 panel-layout-store.clearAgent 扩展外）
- ❌ **Letterpress 老色 / crimson / 老 tokens**（`--color-brass` / `--color-ink` / `ink-brush-hr`）
- ❌ **Stage 顺序乱跳**（必须 1 → 2 → 3 → 4 → 5 · 每 stage 编译闸门通过才进下一 stage）
- ❌ **不 git push**（主 CLI 统一合流）
- ❌ **不删测试 spec**（既有 evidence-trail / highlight-card / unfilled-marker 必须全绿）

### ✅ 必做

- ✅ 新 worktree `code-frontend-integration` fork from `chore/l0-infra` · 新分支 `feat/frontend-integration`
- ✅ Codex 辅助大批量 tsx 改动（cherry-pick 冲突解 / spec 同步） · **决策（合不合 / 兼容判断 / hero polish 选择）走 Claude 主力**
- ✅ 每 stage 独立 commit · trailer 单行 Signal
- ✅ Batch 2 EvidenceTrail 挂载点硬保 · 任何丢失立即 REJECT-V2
- ✅ Final body 含：7 branch 处理结果 + 5 stage SHA + 32 张截屏路径 + 解 DoD 条目自检 + 红区漂移自检
- ✅ 冲突 > 4 文件 / spec fail / 视觉偏 §7 → Q-NNN askout · 不硬解

---

## 5. 工期

- Stage 1 · 2 天
- Stage 2 · 3 天（Codex 融合 3 branch · EvidenceTrail 兼容是主要工作）
- Stage 3 · 1 天
- Stage 4 · 1 天（最终 polish · 兼容判断耗时）
- Stage 5 · 1 天（跨 browser 截屏 32 张）
- 合计 **7-8 天**
- **允许 REJECT-V2 一轮返工**（Stage 2 EvidenceTrail 兼容 / Stage 4 v2 hero 互斥 / Stage 5 跨 browser fail 三类典型返工）
