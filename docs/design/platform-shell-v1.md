# Platform Shell v1 · 实装规范

**设计源**：`design_mockups/shell.html`（2771 行，2026-04-18 lock）
**规范状态**：v1 · 2026-04-19 落盘（主 CLI 从 mockup 翻译而来）
**落地目标**：Stage 2 frontend CLI 按此文件实装 tsx
**更新权责**：主 CLI 唯一可写

---

## 一、信息架构（4 view 模型）

| view | 路径 | 定位 | 主 mockup 锚点 |
|---|---|---|---|
| **今日** Today | `/today` | 个人 dashboard · 三模块预览（消息/进行中/任务） | shell.html L1882-2240 |
| **对话** Dispatch | `/dispatch` | Slack 风 IM · 频道制 · `@` 提及 · 任务内联 | shell.html L2241-2366 |
| **AI 助手** Archive | `/archive` · `/archive/[agent]` | 6 Agent 工作区入口 · 每 Agent 独立 session 与历史 | shell.html L2367-2450 |
| **任务** Warroom | `/warroom` | 看板视图 · 拖拽换列 · AI Bench 重排 | shell.html L2451-end |

**左抽屉（Desk · 共享）**：固定左侧 collapse 面板，4 节：我的客户 / 进行中 / 最近 / 新建。不随 view 切换消失，用于工作上下文。

**顶栏（Masthead · 共享）**：Logo "乾策 Studio" + 4 tab + 右侧 persona（王哲 · 客户经理 · 华东 · 时间）。

**人设优先**：顶栏不挂 Agent 切换；Agent 是 Archive view 内部的 tiles。

## 二、路由地图

```
/                    → 301 /today
/today               → TodayView
/dispatch            → DispatchView (+ ?channel=xxx 深链)
/archive             → ArchiveIndex (6 Agent tiles)
/archive/[agent]     → AgentWorkspace (复用现有 /credit /channel 等内容)
/warroom             → WarroomView (+ ?task=xxx 深链)
/auth/*              → 登录/切换（Stage 6，暂留 stub）
```

**迁移策略**：现有 `/credit` `/channel` `/alert` `/compliance` `/report` `/riskctrl` 6 个路由 → 重定向到 `/archive/[agent]`；内部组件（ScoreRadar/PipelineRail/Card/VerdictBadge/ChatTagInput）全部复用，只换壳。

## 三、设计 token（源 `design_mockups/tokens.css` + shell.html L11-117）

### 3.1 主题

4 套 `data-theme`：

| 主题 | key | 定位 | 主色关键 |
|---|---|---|---|
| **Canvas** | `canvas`（default） | 米黄 → 橙红 → 深墨绿 渐变，暖色偏 editorial | `--g4: #D4653F` `--g7: #163025` |
| **Matcha** | `matcha` | 米杏 → 抹茶绿 → 墨绿 渐变，清雅 | `--g4: #5E8A57` `--g5: #355F41` |
| **Dusk** | `dusk` | 粉白 → 玫瑰粉 → 紫黑 渐变，暮色 | `--g4: #B14774` `--g5: #76284E` |
| **Crimson** | `crimson` | 米色 → 赭红 → 黑 剧场 | `--g4: #6E1911` `--accent: #D5321E` |

每主题提供 `--g0..--g7` 8 档渐变 + `--accent` + `--ink` + `--chalk` + `--safe`。

**切换逻辑**：`localStorage.theme` 持久化，顶栏右侧齿轮点击切换。

### 3.2 字体栈

```css
--display: "Funnel Display", "Noto Sans SC", system-ui, sans-serif;
--sans:    "Instrument Sans", "Noto Sans SC", system-ui, sans-serif;
--italic:  "Instrument Serif", "Noto Serif SC", Georgia, serif;
--mono:    "JetBrains Mono", ui-monospace, monospace;
--cjk:     "Noto Sans SC", system-ui, sans-serif;
--cjkserif:"Noto Serif SC", Georgia, serif;
```

**银行私有化场景**：Stage 6 前必须把 Google Fonts 迁到自托管（`web/public/fonts/`），避免外联。Stage 2 允许临时用 CDN。

### 3.3 透明度滑块

`color-mix(in srgb, var(--ink) N%, transparent)` 生成 `--ink-04..--ink-80` 10 档 + `--ch-08..--ch-96` 22 档。**浏览器兼容**：`color-mix()` 需 Chrome 111+ / Edge 111+ / Safari 16.4+。工行/农行内网 IE/旧 Edge 路线待产品决策。

### 3.4 圆角

`--r-md: 18px` `--r-lg: 26px`——全局统一，不得局部覆写。

## 四、数据契约需求

### 4.1 Stage 2 可用 mock 的端点（前端先走本地 fixture）

```
GET  /api/presence         当前 persona + 华东分行 session
GET  /api/desk/customers   左抽屉 "我的客户" 列表
GET  /api/desk/in-flight   左抽屉 "进行中" · Agent 运行态（%进度 + ETA）
GET  /api/desk/recent      左抽屉 "最近" · 人 / 频道 / 政策混合流
GET  /api/today/summary    今日 hero 统计（管道 / 队列 / 风险）
GET  /api/today/feed       消息预览（5-8 条）
GET  /api/today/in-flight  进行中预览（3-4 条）
GET  /api/today/tasks      任务预览（3-4 条）
GET  /api/dispatch/channels  频道列表 + 未读数
GET  /api/dispatch/messages?channel=xxx
POST /api/dispatch/send
GET  /api/warroom/tasks
POST /api/warroom/move     {task_id, to_column}
```

### 4.2 Stage 2 只出 stub，Stage 3+ 接后端

- Stage 2 frontend 用 `web/src/lib/mock/*.ts` 提供 hard-coded JSON
- Stage 3 逐端点切到真后端（在 `agent_*/api.py` 对应目录下新增 `desk.py` `dispatch.py` `warroom.py`）
- Stage 3 起，Agent 的 in-flight % 进度要从各 Agent 的 job queue 汇聚（现有 SSE 事件流复用）

### 4.3 禁止项

- ❌ 不动 `shared/` 或 `docs/contracts/` 的任何现有契约（红区，A-004 § 〇 仍生效）
- ❌ 不改 6 个现有 Agent 的 handoff schema（Agent3 已按 ReportJSON 定，不回头）
- ❌ Stage 2 不做登录/RBAC（Stage 6 专项）

## 五、Stage 2 · AppShell 实装清单（给 frontend CLI）

### 5.1 新增 tsx 文件

```
web/src/app/tokens.css                 # 从 design_mockups/tokens.css 迁移 + 4 主题
web/src/app/globals.css                # 接入 tokens.css，保留现有 body reset
web/src/components/shell/AppShell.tsx  # 壳（Desk drawer + Masthead + Stage）
web/src/components/shell/Desk.tsx      # 左抽屉 4 节
web/src/components/shell/Masthead.tsx  # 顶栏 logo + 4 tab + persona
web/src/components/shell/ThemeSwitch.tsx  # 4 主题切换 + localStorage
web/src/app/today/page.tsx             # Today view（hero + 3 preview card）
web/src/app/dispatch/page.tsx          # Dispatch view stub（channel list + message stream）
web/src/app/archive/page.tsx           # Archive index（6 agent tiles）
web/src/app/warroom/page.tsx           # Warroom stub（kanban）
web/src/lib/mock/desk.ts               # mock fixture
web/src/lib/mock/today.ts
web/src/lib/mock/dispatch.ts
web/src/lib/mock/warroom.ts
```

### 5.2 旧文件动作

```
web/src/components/layout/AppShell.tsx  # 保留但不再被 root layout 引用
web/src/app/layout.tsx                  # 换挂 shell/AppShell
web/src/app/page.tsx                    # redirect → /today
web/src/lib/agents.ts                   # 保留 AGENTS 常量，供 Archive tiles 用
```

现有 `/credit /channel /alert /compliance /report /riskctrl` 6 个路由**不动**——通过 middleware 重定向到 `/archive/[agent]`，内部页面照跑。

### 5.3 冒烟 DoD（Stage 2 收敛条件）

```bash
cd web && npm run dev
# http://localhost:3000 → 301 → /today
# 切换 4 主题 localStorage 持久化
# /today 渲染 hero + 3 preview card（数据走 mock）
# /dispatch /archive /warroom 各自空壳渲染（loading / empty state 过关）
# /archive/credit 等旧路由仍可访问（重定向生效）
# 1440px / 900px viewport 分别与 shell-board-1440.png / shell-today-900.png 视觉匹配
```

### 5.4 红区边界

- ❌ 不碰 `shared/` `docs/contracts/` `agent_*/` Python 代码
- ❌ 不动现有 6 个 Agent 页面内的业务逻辑（只迁路由，不改组件）
- ❌ 不引入 shadcn / Radix（现有自建组件库风格一致，保持）
- ✅ 只在 `web/src/components/shell/` + `web/src/app/(4 view)/` + `web/src/lib/mock/` 写代码

## 六、Stage 3 及后续阶段预览

| Stage | 范围 | 依赖 |
|---|---|---|
| **3** | Agent 迁入 `/archive/[agent]` · 现有 6 页复用 | Stage 2 AppShell 落地 |
| **4** | `/dispatch` 真后端（in-memory store） | Stage 3 Agent 正常跑 |
| **5** | `/warroom` 真后端 + `/today` live 汇聚 | Stage 4 dispatch ready |
| **6** | `/auth` + RBAC + 字体自托管 | Stage 5 + 产品拍板 |

## 七、规范变更流程

- 发现 mockup 与 spec 不一致 → 以 mockup 为准
- 发现 spec 缺信息 → 主 CLI 补 spec · 不在 onboarding 里临时决策
- `docs/contracts/` 红区变更 → 仍走 shared-change-protocol v1.1 RFC
