# Frontend Shell · Phase 1 Onboarding（Stage 2）

**对应 worktree**：`D:\claude code\demo-frontend`（`feat/platform-shell`）
**发布日期**：2026-04-19
**spec 源**：`docs/design/platform-shell-v1.md`
**mockup 源**：`design_mockups/shell.html` + `tokens.css`
**前置**：已读 `AGENT_IDENTITY.md` + `CLAUDE.md` §7

---

## 任务摘要

把 `design_mockups/shell.html` 的 4 view 壳翻译成 Next.js 16 tsx，替换现有 `web/` 的 6 路由 grid 入口，但**不动现有 6 个 Agent 页面的业务实现**——只迁挂载点。

**不做 productize**：Stage 2 只出壳 + 空 view 骨架 + 主题切换 + mock fixture；真后端对接在 Stage 3+。

---

## Task A · 迁移 token 层（0.5 天）

### 目标
把 `design_mockups/tokens.css` + `shell.html` L11-117 的 4 主题变量系统搬进 `web/src/app/tokens.css`，覆盖 `globals.css`。

### DoD
- [ ] 新建 `web/src/app/tokens.css`，包含 4 组 `[data-theme="canvas|matcha|dusk|crimson"]` + `:root`（canvas 默认）
- [ ] 所有 `--g0..--g7`、`--accent`、`--ink`、`--chalk`、`--safe`、字体栈、`--r-md/lg` 齐全
- [ ] `--ink-XX` / `--ch-XX` 透明度档位完整迁移（shell.html L37-67 共 32 档）
- [ ] `globals.css` 顶部 `@import './tokens.css';`
- [ ] `<html>` 默认 `data-theme="canvas"`
- [ ] 现有 6 个页面不崩（视觉可以变，但不能 run-time error）

### 冒烟
```bash
cd web && npm run dev
# 访问 http://localhost:3000/credit 页面不报错
# devtools 查 :root 能看到 --g4 等变量
```

---

## Task B · AppShell 骨架（1 天）

### 目标
新建 `web/src/components/shell/` 下四个组件，渲染完整壳（左抽屉 + 顶栏 + stage 内容区）。

### DoD
- [ ] `AppShell.tsx` —— 接收 `children`，组装 Desk + Masthead + stage
- [ ] `Desk.tsx` —— 左抽屉 4 节：我的客户 / 进行中 / 最近 / 新建（数据从 `lib/mock/desk.ts`）
- [ ] `Masthead.tsx` —— logo "乾策 Studio" + 4 tab + persona（王哲 · 客户经理 · 华东 · 时间）
- [ ] `ThemeSwitch.tsx` —— 4 主题切换按钮组，`localStorage.theme` 持久化
- [ ] `app/layout.tsx` 挂载 `<AppShell>{children}</AppShell>`
- [ ] 原 `web/src/components/layout/AppShell.tsx` 删除或注释标记弃用（以本次新 shell 为准）

### mockup 锚点
- Desk：shell.html L1735-1831
- Masthead：shell.html L1860-1878
- 布局框架：L119-1730 的 CSS 是参考，**允许重构成 tailwind utilities 或 CSS Module**，但 token 必须走 CSS 变量

### 冒烟
```bash
cd web && npm run dev
# 访问 / → 自动 301 → /today
# 4 主题切换生效，刷新后主题保持
# 左抽屉可见、顶栏可见、persona 显示 "王哲"
```

---

## Task C · 4 View 骨架 + 路由迁移（1 天）

### 目标
建立 4 view 页面 + mock 数据 + 现有 6 路由重定向。

### DoD
- [ ] `app/today/page.tsx` —— Hero + eyebrow + 3 preview card（消息 / 进行中 / 任务），数据走 `lib/mock/today.ts`
- [ ] `app/dispatch/page.tsx` —— 频道列表 + 空 chat stream（不做 IM 逻辑，只渲染 mock 消息）
- [ ] `app/archive/page.tsx` —— 6 Agent tiles，点击进入 `/archive/[agent]`
- [ ] `app/archive/[agent]/page.tsx` —— 动态路由，目前直接 import 现有 `/credit /channel /alert /compliance /report /riskctrl` 的 page 组件
- [ ] `app/warroom/page.tsx` —— 看板 stub（3 列静态卡片）
- [ ] `app/page.tsx` —— `redirect('/today')`
- [ ] 现有 6 路由通过 middleware 或各自 page.tsx 内部 redirect 到 `/archive/[agent]`（保留 URL 可访问，但 canonical 是 `/archive`）
- [ ] 4 个 `lib/mock/*.ts` fixture 齐全（desk / today / dispatch / warroom）

### 不做
- ❌ 真后端对接（Stage 3 再做）
- ❌ IM 真消息发送（Stage 4）
- ❌ 任务看板拖拽（Stage 5）
- ❌ 登录 / 鉴权（Stage 6）

### 冒烟（Stage 2 final DoD）
```bash
cd web && npm run dev
# 1. / → /today 渲染完整 hero + 3 卡片
# 2. 点顶栏"对话"→ /dispatch 渲染频道列表
# 3. 点"AI 助手"→ /archive 6 个 tile
# 4. 点某 tile → /archive/credit（现有 credit 页面内容正常渲染）
# 5. 直接访问 /credit → redirect 到 /archive/credit（或同屏等价）
# 6. 4 主题切换全部生效（4 个 view 都变色）
# 7. 1440px viewport 目测接近 shell-board-1440.png / shell-today-1440.png
```

---

## 红区边界再强调

本次 Stage 2 **禁止**：
- ❌ 碰 `shared/` `docs/contracts/` `agent_*/`
- ❌ 改 6 个现有 Agent 页面的业务 component（ScoreRadar / PipelineRail / Card / VerdictBadge / ChatTagInput 等）
- ❌ 引入 shadcn / Radix / Ant Design（现有自建组件保持）
- ❌ 动 `api_server.py` 或任何后端路由
- ❌ 改 `docs/design/platform-shell-v1.md`（发现问题 → 写 Q-NNN 进 decisions-log）

允许：
- ✅ `web/src/app/**` 新增路由
- ✅ `web/src/components/shell/**` 新组件
- ✅ `web/src/lib/mock/**` fixture
- ✅ `web/src/app/tokens.css` + `globals.css` 扩展

---

## Commit / Signal 协议

**硬规则**（从本批次起）：

- **R-A · 冒烟必实测**：commit message 写的 `npm run dev` / `npm test` 等命令，必须在当前工作树实测通过再入 commit
- **R-B · 单 commit 单 Signal**：一个 commit 只能带一个 `Signal: XXX` trailer
- **R-C · cherry-pick 要改 Signal**：跨分支复制代码时，主 CLI 侧 commit 用新 Signal（不保留 worker 的原 Signal）

### 本次里程碑 Signal

| 时点 | Signal | 含义 |
|---|---|---|
| 读完 onboarding + identity | `FRONTEND-PHASE-1-ACK` | 确认收到任务 |
| Task A 收敛 | `TASK-A-TOKENS-MIGRATED` | token 层完成 |
| Task B 收敛 | `TASK-B-APPSHELL-READY` | 壳可跑 |
| Task C 收敛 | `TASK-C-VIEWS-SCAFFOLDED` | 4 view 挂好 |
| Stage 2 全绿 | `FRONTEND-STAGE-2-READY-FOR-REVIEW` | 等主 CLI review |
| Review 后收工 | `WINDOW-CLOSED-CLEAN` | 工作树干净，关窗 |

---

## 关键文件速查

- 读：`design_mockups/shell.html` + `design_mockups/tokens.css`
- 读：`docs/design/platform-shell-v1.md`（唯一 spec）
- 读：现有 `web/src/lib/agents.ts`（6 Agent 定义，复用 Archive tiles）
- 读：现有 `web/src/components/layout/AppShell.tsx`（老壳，本次替换）
- 写：`web/src/app/tokens.css`（新）
- 写：`web/src/components/shell/*.tsx`（新）
- 写：`web/src/app/{today,dispatch,archive,warroom}/page.tsx`（新）
- 写：`web/src/lib/mock/*.ts`（新）

---

## ACK 协议

读完本文件 + `AGENT_IDENTITY.md` + spec → `git commit --allow-empty -m "ack(frontend): Stage 2 onboarding absorbed" -m "" -m "Signal: FRONTEND-PHASE-1-ACK"`

随后按 Task A → B → C 顺序推进，每 task 收敛都 commit 一次。
