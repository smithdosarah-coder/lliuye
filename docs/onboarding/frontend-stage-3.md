# Frontend Platform Shell · Stage 3 Onboarding

**对应 worktree**：`D:\claude code\demo-frontend`（分支 `feat/platform-shell`）
**发布日期**：2026-04-19
**spec 源**：`docs/design/platform-shell-v1.md`（主 CLI 唯一可写）
**mockup 源**：`design_mockups/shell.html` + `design_mockups/tokens.css`
**前置 review**：`docs/review/frontend-stage-2-review.md`（Stage 2 APPROVED）
**前置 decision**：`docs/handoff/decisions-log.md` Q-010/A-010（placeholder 三阻理由）· Q-011/A-011（字体策略）
**前置 HEAD**：worker 侧 `b2b48fe` · 主 CLI 侧 `5e9d511`

---

## 任务摘要

Stage 2 已把 4 view 壳（today / dispatch / archive / warroom）+ 4 主题渐变 + Desk + Masthead 挂好；但 `/archive/[agent]` 是 placeholder（"STAGE 2 · WORKSPACE PLACEHOLDER"），6 个老页面 `/credit /channel /alert /compliance /report /riskctrl` 通过 `next.config.ts` 307 redirect 到同路径，**事实离线**。

**Stage 3 唯一任务**：把老 6 页的业务主体抽离成 workspace component，塞进 `/archive/[agent]`，让客户看到的不再是 Coming Soon，而是原 agent 的真实业务界面——但必须解掉 Q-010/A-010 明示的三个阻点。

**不做 productize**：不加新功能、不重新设计 UX、不动 shell 组件、不改 token 源、不动后端。只做"搬 + 解耦 + 色系迁移 + 导航修正"。

---

## 范围 & 不做什么

### 范围（ONLY）

- `web/src/components/workspace/<agent>Workspace.tsx` × 6 新建，从 `app/<agent>/page.tsx` 抽业务主体
- `app/archive/[agent]/page.tsx` 从 placeholder 改为按 `params.agent` 动态渲染对应 workspace
- workspace 组件内 legacy token（`--color-paper/ink/brass/line/ember/sage/chalk` 全家桶）迁到新 token（`--g0..--g7 / --ink / --chalk / --accent / --safe`）
- 老页 `usePathname` 驱动的高亮在 `/archive/[agent]` 下重新定位——或改走 `params.agent`，或走 workspace 内部状态

### 不做

- ❌ 不改 shell 4 view（today/dispatch/archive/warroom）任何 JSX
- ❌ 不动 `web/src/app/tokens.css`（token 源唯一写：主 CLI）
- ❌ 不改 `web/src/components/shell/**`（Desk/Masthead/AppShell/ThemeSwitch）
- ❌ 不动 `docs/design/platform-shell-v1.md`（spec 唯一写：主 CLI）
- ❌ 不改 `next.config.ts` 6 老路由 redirect（Stage 2 已定）
- ❌ 不重新设计 agent UX（尊重老页面交互，先搬再说）
- ❌ 不引入 shadcn / Radix / Ant Design
- ❌ 不动 `shared/` / `docs/contracts/` / `api_server.py` / `agent_*/`

### 风险坦白（B 计划，onboarding 只写不做）

Stage 2→3 过渡期"老页面离线"已经在跑（6 路 307 → placeholder）。若 Stage 3 落地前有客户 demo 暴露：
- **B 计划 1**：回退 `next.config.ts` 的 6 条 redirect（git revert 对应 commit），老页面直接恢复可达
- **B 计划 2**：把老页面挪到 `/archive-legacy/<agent>/`，新壳里加一条紧急导航
- **Stage 3 期间不触发 B 计划**——优先闷头做完。若主 CLI 告知临时 demo，worker 执行 B 计划 1 并抛 `Signal: EMERGENCY-LEGACY-RESTORE`

---

## 前置条件

- [x] Stage 2 APPROVED @ worker `b2b48fe` / 主 CLI `5e9d511`（`docs/review/frontend-stage-2-review.md` Update 段）
- [x] 4 主题 token 层在 `web/src/app/tokens.css`（`--g0..--g7` + `--ink/chalk/accent/safe`）
- [x] Next.js 16 + Tailwind v4 + 4 主题壳全部就位
- [x] `next.config.ts` 6 路由 307 redirect 配置完成
- [x] Q-010/A-010 已落地，三阻点（`"use client"` / legacy ink token / `usePathname` 错位）本次 Stage 3 必须全部解

---

## Task 清单（4 Task · 建议 4-6 工时）

### Task A · workspace component 抽离（6 agent × 1 组件 · 预计 2 工时）

#### goal

为每个 agent 建一个 workspace component，从 `app/<agent>/page.tsx` 迁业务主体。去掉 `"use client"` 顶部声明、去掉老顶栏 JSX（Agent1 的 eyebrow/h1/description header block 可以保留，但不要再渲染自己的 `<header>` 作为页面级导航）、保留所有数据消费逻辑（hooks / api / fixture）。

**Server component 优先**；实在需要交互的部分（比如 Agent3 `CreditDecisionPage` 里 `useState`/`useEffect`/SSE `streamDecision`）下沉成**小粒度**子组件，子组件带 `"use client"`，workspace 本身尽可能 server——至少不再有"整页都 client"的无脑包法。

#### touch

- 新建目录 `web/src/components/workspace/`
- 新建 6 文件：
  - `ReportWorkspace.tsx` ← `app/report/page.tsx`
  - `ChannelWorkspace.tsx` ← `app/channel/page.tsx`
  - `CreditWorkspace.tsx` ← `app/credit/page.tsx`
  - `RiskctrlWorkspace.tsx` ← `app/riskctrl/page.tsx`
  - `AlertWorkspace.tsx` ← `app/alert/page.tsx`
  - `ComplianceWorkspace.tsx` ← `app/compliance/page.tsx`
- 老 6 个 `app/<agent>/page.tsx` **不动**（它们还被 307 redirect 牵住，删了 Next.js 会 404 掉 redirect 源；等 Stage 3 收敛后再清）

#### deliverables

- 6 个 workspace 组件，每个 export default 一个函数组件，接受可选 `params?: { agent: string }` 以便 Task D 复用
- 老页面的 import 图（Card / PipelineRail / ScoreRadar / VerdictBadge / ChatTagInput / FileDrop 等）保持引用路径不变（`@/components/viz/...` `@/components/ui/...`），**不新增**任何 shell 以外的组件库
- 交互密集组件（如 credit 的 SegmentedControl + streamDecision 状态机）按需拆 2-3 个子 client component，文件名遵循 `web/src/components/workspace/<agent>/<PartName>.tsx`（子文件夹内聚）

#### DoD（必测 evidence）

- [ ] `ls web/src/components/workspace/ | wc -l` = 6（或 6 + 子文件夹数）
- [ ] `grep -rn "use client" web/src/components/workspace/ | wc -l` = 仅子交互组件，workspace 主文件**0 匹配**
- [ ] `grep -rn "export default" web/src/components/workspace/*.tsx | wc -l` = 6
- [ ] `cd web && npx tsc --noEmit` = 0 err
- [ ] workspace 组件内不得出现 `<header>` 作为页面顶栏（老页的 page header JSX 清掉或降级为 section eyebrow）

#### Signal

- commit message 末尾 trailer `Signal: FRONTEND-STAGE-3-TASK-A-DONE`
- commit 完成停下等主 CLI GO 再进 Task B

---

### Task B · archive/[agent] 挂业务组件（预计 1 工时）

#### goal

把 `app/archive/[agent]/page.tsx` 从 placeholder 改为按 `params.agent` 动态渲染对应 workspace。`generateStaticParams` 已有 6 项保留不动。

#### touch

- 仅改 `web/src/app/archive/[agent]/page.tsx`
- 保留文件顶部 eyebrow（`A01 · CHANNEL` 之类）+ h1 + lede（来自 `AGENTS` 常量），作为 workspace 之上的身份标识——壳不能完全丢
- 把 "STAGE 2 · WORKSPACE PLACEHOLDER" 整块 tile 删掉
- 按 `agent` switch 到对应 workspace component

#### deliverables

- `archive/[agent]/page.tsx` 新版本
- 推荐用 `dynamic` import + map 表消除 switch-case 噪声（非硬性要求），示例：

  ```tsx
  const WORKSPACES: Record<AgentKey, ComponentType> = {
    report: dynamic(() => import("@/components/workspace/ReportWorkspace")),
    channel: dynamic(() => import("@/components/workspace/ChannelWorkspace")),
    // ...6 项
  };
  ```

- 保留 `notFound()` 在非法 agent key 时触发

#### DoD（必测 evidence）

- [ ] `cd web && npm run dev` 启动后 6 条 curl 全部**不返回** "Coming Soon"：
  ```bash
  for a in report channel credit riskctrl alert compliance; do
    curl -s http://127.0.0.1:3000/archive/$a | grep -c "STAGE 2 · WORKSPACE PLACEHOLDER"
  done
  # 期望全部输出 0
  ```
- [ ] 同上 6 路 HTTP 200，HTML body 含各自 agent 的业务主元素（如 `/archive/credit` 含 "四维风险画像" 或 "授信决策"；`/archive/channel` 含 "候选企业" 等）
- [ ] `npx tsc --noEmit` = 0 err
- [ ] `/archive` index 页（6 tiles）点击跳转功能不坏

#### Signal

- commit trailer `Signal: FRONTEND-STAGE-3-TASK-B-DONE`
- 停下等 GO

---

### Task C · 色系迁移（legacy token → platform-shell token · 预计 2 工时）

#### goal

workspace 组件里遗留 412 处 legacy color token 全部迁到新 token。新 token 在 `web/src/app/tokens.css` 已定义，映射规则见下表。

#### touch

- 仅改 `web/src/components/workspace/**`（含子文件夹子组件）
- **不改** `web/src/app/globals.css`（legacy token 定义保留，兼容其他地方可能的残留引用）
- **不改** `web/src/app/tokens.css`（红区）

#### 映射表（法定）

| legacy token | → 新 token | 说明 |
|---|---|---|
| `--color-paper` | `var(--g0)` | 背景最浅底 |
| `--color-paper-raised` | `var(--g1)` | 卡片面 |
| `--color-paper-sunken` | `color-mix(in srgb, var(--ink) 4%, transparent)` 或 `var(--ink-04)` | 下沉面 |
| `--color-ink` | `var(--ink)` | 主文字 |
| `--color-ink-soft` | `var(--ink-80)` | 次文字 |
| `--color-ink-muted` | `var(--ink-48)` | 弱文字 |
| `--color-brass` | `var(--accent)` | 强调色（主题自适配） |
| `--color-brass-dim` | `color-mix(in srgb, var(--accent) 70%, var(--ink))` | 暗金 |
| `--color-brass-glow` | `color-mix(in srgb, var(--accent) 30%, var(--chalk))` | 亮金 |
| `--color-ember` | `var(--accent)` 或 `#c8463a` 字面保留（**强语义红**，若上下文表达"danger"则保留字面值，不走主题） | 需逐处判断 |
| `--color-ember-dim` | 同上 | |
| `--color-sage` | `var(--safe)` | OK 绿 |
| `--color-sage-dim` | `color-mix(in srgb, var(--safe) 70%, var(--ink))` | 暗绿 |
| `--color-line` | `var(--ink-12)` 或 `color-mix(in srgb, var(--ink) 12%, transparent)` | 分割线 |
| `--color-line-strong` | `var(--ink-24)` | 粗分割线 |
| `--color-overlay` | `var(--ink-04)` | 遮罩 |
| `--color-amber` | `var(--accent)`（主题化）或保字面 `#d49b2f`（warning 语义） | 需逐处判断 |

**语义保留例外**：`--color-ember`（红线 / 错误）和 `--color-amber`（warning）在 verdict badge / red-line panel / error banner 等"告警/危险"语义位置，**允许保留字面色值**（`#c8463a` / `#d49b2f`），不强制走主题变量——因为 4 主题里危险红不应变成暮粉或抹茶绿。工具性语义 > 主题美学。

阴影类 `--shadow-sm/md/lg` 保留不动（tokens.css 未重新定义，`globals.css` 的 legacy 定义继续生效）。

#### deliverables

- 6 个 workspace 文件（及子文件）的 legacy token 引用全部迁完
- `--color-ember` / `--color-amber` 保字面处加行注释 `/* semantic danger; kept literal across themes */`（给 review 留痕）

#### DoD（必测 evidence）

- [ ] `grep -rn "color-paper\|color-ink\|color-brass\|color-line\|color-sage" web/src/components/workspace/ | wc -l` = 0
- [ ] `grep -rn "var(--g[0-7])\|var(--ink)\|var(--chalk)\|var(--accent)\|var(--safe)" web/src/components/workspace/ | wc -l` > 50（证明实际在用）
- [ ] `grep -rn "color-ember\|color-amber" web/src/components/workspace/` 每处都有 `semantic danger` 或 `semantic warning` 注释
- [ ] `npx tsc --noEmit` = 0 err
- [ ] `npm run dev` 后切换 4 主题（canvas/matcha/dusk/crimson），`/archive/credit` 能看到主题变化（强调色跟着变），且红线面板的红色**不变**

#### Signal

- commit trailer `Signal: FRONTEND-STAGE-3-TASK-C-DONE`
- 停下等 GO

---

### Task D · 导航与高亮修正（预计 1 工时）

#### goal

解掉 Q-010/A-010 的第三阻：`usePathname` 在老页面里被用来做"当前 agent 高亮"或"tab active"——到了 `/archive/[agent]` 下语义错位（pathname 是 `/archive/credit`，老逻辑可能比对 `/credit`）。

改用 `params.agent`（Task B 透传）或 workspace 内部 `useState` 持有 active 子 tab。不要保留老顶栏任何残留（已在 Task A 清，这里复核）。

#### touch

- workspace 组件内 `usePathname()` 调用全部审查；如果用途是"判定当前 agent"，改接 `params.agent`；如果用途是"子路由 active"（如老 riskctrl 内部 tab），改 internal state 或 `searchParams`
- 复核 Task A 顶栏清理——workspace 内不得存在渲染 `nav` / `header[role=navigation]` / 全宽顶栏条的 JSX
- archive shell（Masthead）是唯一顶栏，workspace 只能渲染**内容区**

#### deliverables

- `grep` 证据见 DoD
- 任何 active 状态的权威源从"URL pathname" 迁到"params 或 local state"

#### DoD（必测 evidence）

- [ ] `grep -rn "usePathname" web/src/components/workspace/` = 0 （或仅限子组件做细粒度 sub-route，且 comment 解释）
- [ ] `/archive/<agent>` 下人眼过一遍（pyplaywright 可选）：无双层顶栏、无侧栏撞 Desk、主题切换 4 套渐变都不破
- [ ] 每个 agent 页面原交互（按钮点击、表单、SSE 流）**不坏**——冒烟只跑 1 个 agent（推荐 credit，因其 SSE 最复杂）
- [ ] `npx tsc --noEmit` = 0 err

#### Signal

- commit trailer `Signal: FRONTEND-STAGE-3-TASK-D-DONE`
- 停下等 GO

---

## 红区 & 硬规则

### 红区（零触碰）

| 路径 | 说明 |
|---|---|
| `web/src/components/shell/**` | 壳唯一写：主 CLI |
| `web/src/app/globals.css` | legacy token 定义保留，不删不改 |
| `web/src/app/tokens.css` | token 源唯一写：主 CLI |
| `web/src/app/shell.css` / `views.css` | shell/view 样式源 |
| `docs/design/platform-shell-v1.md` | spec 唯一写：主 CLI |
| `docs/handoff/decisions-log.md` | Q/A 记录唯一写：主 CLI |
| `docs/contracts/**` | 契约红区 |
| `next.config.ts` | 6 路 redirect 不改 |
| `shared/**` / `agent_*/` / `api_server.py` | Python 后端红区 |

### 硬规则（从 A-006 起继承）

- **R-A · smoke-must-test**：commit message 声称的冒烟命令必须在**提交分支当前 HEAD** 实测通过再入 commit。违规 → review 自动 CONDITIONAL
- **R-B · 一 commit 一 Signal**：单 commit 只带一条 `Signal: XXX` trailer。`git log --format='%b' HEAD` 自检
- **R-C · cherry-pick 改 trailer**：本 Stage 3 worker 侧无 cherry-pick 需求，略过

### Signal await semantics（来自 A-010 Follow-up）

每 Task 完成后带 trailer `FRONTEND-STAGE-3-TASK-{A|B|C|D}-DONE` commit，**停下**等主 CLI 明示 GO（信号：主 CLI 在 mesh 看板或 decisions-log 里回 `GO-TASK-X+1`）。不得连跑 4 Task。目的：过程中可发现 spec 偏差及时修，不等 final review 才发现累积问题。

---

## Signal 流程

| 时点 | Signal | 含义 |
|---|---|---|
| 读完 onboarding + AGENT_IDENTITY | `FRONTEND-STAGE-3-ACK` | 确认 |
| Task A 收敛 | `FRONTEND-STAGE-3-TASK-A-DONE` | 6 workspace 建成 |
| Task B 收敛 | `FRONTEND-STAGE-3-TASK-B-DONE` | archive 挂载 |
| Task C 收敛 | `FRONTEND-STAGE-3-TASK-C-DONE` | 色系迁完 |
| Task D 收敛 | `FRONTEND-STAGE-3-TASK-D-DONE` | 导航修正 |
| 全绿 | `FRONTEND-STAGE-3-READY-FOR-REVIEW` | 等主 CLI 终审 |
| Review 后收工 | `WINDOW-CLOSED-CLEAN` | 工作树干净 |

### 冲突 / 决策

- 用 `Signal: NEED-DECISION Q-NNN` 中止，Q-NNN 从**下一个可用编号**起
- **当前已用到 Q-011**（A-011 字体策略）。Stage 3 worker 起 Q 前必须 `git fetch && tail -100 docs/handoff/decisions-log.md` 拿最大号 +1
- 与后端 agent1 Phase 1 **共享编号空间**（本仓库 `docs/handoff/decisions-log.md` 是跨 agent 单源）
- 预期冲突点：
  - Q-012 候选：Task C 映射表 `--color-ember` 的"语义保留"边界是否足够清晰
  - Q-013 候选：Task D 若某 agent 页面有**真 sub-route**（如 riskctrl 内部多 tab），迁移策略是否走 `?tab=xxx` search param

---

## 视觉 / 体验基线

### 不倒退（硬约束）

- Stage 2 已过的 4 主题切换在所有 workspace 依然生效（强调色、渐变、字体栈）
- Desk / Masthead / ThemeSwitch 不动一像素
- `/today /dispatch /warroom` 三个 view 不受本 Stage 影响
- 老路由 307 redirect 继续生效

### 可接受的妥协

- 老 agent 页 UX **原样呈现**，不重新设计交互——只做"搬 + 解耦 + 色系"
- 老页的局部布局（grid-cols-12、max-w-1400 等 Tailwind utilities）可以保留
- 子组件若为达成 DoD A 的"主组件非 client"目标而拆出，拆后行数/结构合理即可，不追求极致优化

### 不允许

- ❌ 回退到 legacy ink 主题 / 全局切换主题
- ❌ 保留老顶栏 JSX（page 级 `<header>`）
- ❌ workspace 套另一层 AppShell 或 Masthead（双层壳）
- ❌ 在 workspace 里直接 import shell 组件（`@/components/shell/*`）做 workaround
- ❌ 为了搬代码而删业务功能——功能等价是底线

---

## 时限 & 节奏

- 建议 4-6 工时一窗跑完（4 Task 各 1-2 工时）
- 每 Task 完成停一下等 GO，主 CLI 侧响应 SLA 约 10-30 分钟
- 若单个 Task 预计超 3 小时，先抛 `Signal: NEED-DECISION Q-NNN` 同步情况

---

## 关键文件速查

### 读

- `docs/review/frontend-stage-2-review.md` — Stage 2 APPROVED（Update 段是 Stage 3 入口锚）
- `docs/handoff/decisions-log.md` — Q-010/A-010（三阻理由）· Q-011/A-011（字体）
- `docs/design/platform-shell-v1.md` — spec（§三 token · §五 红区）
- `CLAUDE.md` 第 7 节 — 前端设计系统硬规则
- `design_mockups/shell.html` + `design_mockups/tokens.css` — 不一致时以 mockup 为准
- 老 6 页：`web/src/app/{report,channel,credit,riskctrl,alert,compliance}/page.tsx`

### 写

- `web/src/components/workspace/<Agent>Workspace.tsx` × 6 — 本 Stage 新建
- `web/src/components/workspace/<agent>/*.tsx` — 子交互组件（按需）
- `web/src/app/archive/[agent]/page.tsx` — 本 Stage 改写（不新增）

### 禁写

见上"红区"表；另外**不删**老 `app/<agent>/page.tsx`——它们是 307 redirect 的源端，删了会变 404。

---

## ACK 协议

读完本文件 + `AGENT_IDENTITY.md` + `docs/review/frontend-stage-2-review.md` + decisions-log Q-010/Q-011 后：

```bash
git commit --allow-empty \
  -m "ack(frontend): Stage 3 onboarding absorbed" \
  -m "" \
  -m "Signal: FRONTEND-STAGE-3-ACK"
```

随后按 Task A → B → C → D 顺序推进。每 Task 一 commit 一 Signal，停下等主 CLI GO。全部完成抛 `FRONTEND-STAGE-3-READY-FOR-REVIEW`。
