# platform-auth (登录 + RBAC) Phase 1 Onboarding

**状态**：APPROVED
**发布日期**：2026-04-20
**Signal 入口**：`PHASE-1-BATCH-1-DISPATCHED`
**前置**：
- Stage 1.0 contracts 已落地（commit c99a277）
- `web/src/lib/store/auth-store.ts` 已提供 5 demo persona + RBAC matrix（只读消费）

---

## 你是谁

你是 **platform-auth** worker CLI，负责实装登录态 + 权限守卫。Demo 期不接真实 SSO，用 **5 个 persona 一键切换**代替：王哲（RM）/ 李华（审贷官）/ 周敏（合规官）/ 陈凯（风险经理）/ 刘野（admin）。切 persona → 整个 shell 的可见内容 + 可点按钮随角色变化。

---

## 本批次任务

### ✅ Task A — `/login` 登录页

**目标**：未登录状态访问任意路径 → 重定向 `/login`；`/login` 展示 5 个 persona 卡片，点击 → `login(userId)` → 跳 `/today`。

**模块路径**：
- 新建：`web/src/app/login/page.tsx`（5 persona 卡片网格）
- 新建：`web/src/app/login/_components/PersonaCard.tsx`
- 修改：`web/src/components/shell/AppShell.tsx`（加 `<AuthGate>` 包裹 children；未登录 render null / redirect）
- 新建：`web/src/components/shell/AuthGate.tsx`

**指标/验证**：
- 清 localStorage 后访问 `/today` → 自动跳 `/login`
- 点王哲卡片 → 登录并跳 `/today`，masthead 右上 persona 显示"王哲·客户经理·华东"
- 刷新页面保留登录态（auth-store persist）

**工作量**：M（1 天）
**完成信号**：`Signal: AUTH-LOGIN-PAGE-DONE`

---

### ✅ Task B — Persona 切换器 + 退出登录

**目标**：masthead 右上的 persona 块点击打开一个 Popover —— 列出全部 5 persona + "退出登录"。切 persona 直接 login(newId)，不走 logout/login 往返。

**模块路径**：
- 新建：`web/src/components/shell/PersonaSwitcher.tsx`
- 修改：`AppShell.tsx` 注入到 masthead 的右上 slot
- 修改：（如果存在）现有 masthead 里硬编的 "王哲" 文案 → 改为从 `useAuthStore` 读

**指标/验证**：
- 点 persona 弹 Popover，列出 5 人
- 切到李华 → masthead 变"李华·审贷官·华东授信审查部"
- 左抽屉 Desk 的"我的客户"列表也按 assignedTo 过滤
- 按 Esc / 点外部 Popover 关闭

**工作量**：S（半天）
**完成信号**：`Signal: AUTH-PERSONA-SWITCHER-DONE`

---

### ✅ Task C — RBAC 守卫 + 无权限态

**目标**：3 个 Agent workspace（`/archive/report`, `/archive/credit`, `/archive/alert` ...）入口前加 `useAuthStore.can({ kind: "agent.access", agent: "xxx" })` 判定；无权访问 → 渲染 `<NoPermission />` 而不是让业务组件报错。

**模块路径**：
- 新建：`web/src/components/shell/NoPermission.tsx`
- 修改：`web/src/app/archive/[agent]/page.tsx` 或 `web/src/app/archive/[agent]/layout.tsx`（加判定）
- 修改：`web/src/app/archive/page.tsx` 的 6 tile（无权限置灰 + tooltip 解释）

**指标/验证**：
- 切到周敏（合规官）→ 访问 `/archive/channel` 显示 `<NoPermission />`，文案"合规官角色无需获客工具，如需跨岗协作请联系客户经理"
- tile 网格里无权 agent 置灰，hover 显示原因
- 切回王哲 → 恢复全部 6 tile 可点

**工作量**：M（1 天）
**完成信号**：`Signal: AUTH-RBAC-GUARD-DONE`

---

### ✅ Task D — 审计视图入口（仅合规官 + admin）

**目标**：masthead 加一个仅对 `audit.view` 权限开放的入口按钮，点击跳 `/audit`（placeholder 页面，列 event-bus.history 最新 50 条 + 筛选）。

**模块路径**：
- 新建：`web/src/app/audit/page.tsx`（placeholder，读 useEventBus）
- 修改：`AppShell.tsx` / masthead 加条件渲染按钮

**指标/验证**：
- 王哲（RM）看不到审计按钮
- 切周敏（合规官）→ 按钮出现 → 点击看到事件流
- 刘野（admin）也看得到

**工作量**：S（半天）
**完成信号**：`Signal: AUTH-AUDIT-ENTRY-DONE`

---

## 完成后

全 Task 完成：`Signal: READY-FOR-PLATFORM-AUTH-REVIEW`

---

## 红线

- ❌ 不改 `web/src/lib/store/auth-store.ts` 的 `ACCESS` / `HANDOFFS` matrix（走 RFC）
- ❌ 不动 `/dispatch/` / `/warroom/` / `/today/` / `/customer/` 的业务逻辑（但可以在这些页 layout 层加 AuthGate wrapper —— 通过 slot 注入，不直接改 page 本身）
- ✅ `web/src/app/login/` + `web/src/app/audit/` + `web/src/components/shell/{AuthGate,PersonaSwitcher,NoPermission}.tsx` 你全权负责
- ✅ `web/src/components/shell/AppShell.tsx` 可以改，但**每次改都要在 decisions-log 留一条短说明**（"加了 AuthGate wrapper / 注入 PersonaSwitcher slot"），方便其他 worker rebase 时理解

---

## 设计参考

登录页参考 Notion / Linear 的 workspace 选择器（左右排 persona 卡片，不要像银行系统的用户名密码表单）；RBAC 的"无权限"态学 Stripe —— 不是 403 报错，而是温和解释"你的角色不包含这个模块"+ 指引下一步。

---

## ACK 协议

1. Resume 后 commit `Signal: PHASE-1-BATCH-1-ACK`
2. Task A → B → C → D 顺序
3. 全 Task 完成 → `READY-FOR-PLATFORM-AUTH-REVIEW`

**维护者**：主 CLI
