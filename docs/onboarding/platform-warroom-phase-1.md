# platform-warroom (任务看板) Phase 1 Onboarding

**状态**：APPROVED
**发布日期**：2026-04-20
**Signal 入口**：`PHASE-1-BATCH-1-DISPATCHED`
**前置**：
- Stage 1.0 contracts 已落地（commit c99a277）
- 共享 store：`web/src/lib/store/*`（只读）
- 契约文档：`docs/arch/platform-contracts.md`

---

## 你是谁

你是 **platform-warroom** worker CLI，负责把 `/warroom` 路由从静态 mock（45 行）改造成**可用的 4 列 kanban**：Requested → Accepted → In Progress → Completed。卡片 = `HandoffTicket`，从 Agent 工作流（event-bus）自动汇入。

---

## 本批次任务

### ✅ Task A — TicketStore + kanban 基础布局

**目标**：实现 ticket 本地 store（zustand，持久化），4 列 kanban 拖拽改 status；mount 时订阅 event-bus 的 `handoff.requested` 事件自动创建 ticket。

**模块路径**：
- 新建：`web/src/app/warroom/_store/ticket-store.ts`（列表 + CRUD + persist）
- 新建：`web/src/app/warroom/_components/{StatusColumn,TicketCard,TicketDrawer,EmptyColumn}.tsx`
- 修改：`web/src/app/warroom/page.tsx`（换 layout）
- 消费：`@/lib/store`（useCustomerStore / useEventBus / HANDOFF_CATALOG / byUserId）

**指标/验证**：
- 访问 `/warroom` 看到 4 列，空态提示"暂无 ticket"
- 手动 `publishEvent({ type: "handoff.requested", ..., payload: { recipeId: "report_to_credit" } })` → ticket 进 Requested 列
- 拖到 Accepted 列 → status 更新 + publish `handoff.accepted`

**工作量**：M（1.5 天）
**完成信号**：`Signal: WARROOM-KANBAN-DONE`

---

### ✅ Task B — TicketDrawer 详情 + 操作链

**目标**：点击 ticket 打开右侧 Drawer，显示 customer 卡 + recipe 描述 + payload JSON + 来源 event + 操作按钮（Accept / Reject / Reassign / Archive）。

**模块路径**：
- 修改：`web/src/app/warroom/_components/TicketDrawer.tsx`
- 消费：`findRecipeById` / `byUserId` / `useCustomerStore.byId`

**指标/验证**：
- 点 ticket → Drawer 滑入
- Accept 按钮触发 customer advanceStage + publish accepted 事件
- Reject 需填 reason（≤140 字）

**工作量**：S（半天）
**完成信号**：`Signal: WARROOM-DRAWER-DONE`

---

### ✅ Task C — 过滤 / 排序 / 负责人视图

**目标**：顶栏 FilterBar：按客户 / 按负责人 / 按 fromAgent / 按 toAgent / 按 priority 过滤；"我的任务"默认视图（currentUser = assignedTo）。

**模块路径**：
- 新建：`web/src/app/warroom/_components/FilterBar.tsx`
- 修改：`_store/ticket-store.ts`（selector 加 filter 参数）

**指标/验证**：
- 切 persona（切到 u_lihua）→ kanban 只剩指派给 u_lihua 的 ticket
- "我的任务"和"全部"Tab 可切
- URL query 同步（`?assignee=u_lihua&priority=urgent`）

**工作量**：S（半天）
**完成信号**：`Signal: WARROOM-FILTERS-DONE`

---

## 完成后

全 Task 完成：`Signal: READY-FOR-PLATFORM-WARROOM-REVIEW`

---

## 红线

- ❌ 不改 `web/src/lib/store/*`（红区，走 RFC）
- ❌ 不改 `web/src/components/shell/*`
- ❌ 不动 `web/src/app/dispatch/` / `/today/` / `/customer/` / `/login/`
- ❌ 不改 `HANDOFF_CATALOG`（红区）——只 read
- ✅ `web/src/app/warroom/` 及其子目录你全权负责

---

## 设计参考

Linear / Jira / Trello 的 kanban 交互，但视觉要对齐本项目 `design_mockups/rm-assistant-final-2026-04-19.html`（Canvas 主题；按钮 / 卡片圆角 `--r-md: 18px` / `--r-lg: 26px`；不要用蓝紫撞色）。拖拽库优先用 `@dnd-kit/core`（如未装 →  Task A 里先加到 deps）。

---

## ACK 协议

1. Resume 后 commit `Signal: PHASE-1-BATCH-1-ACK`
2. Task A → B → C 顺序，每 Task 独立 commit
3. 全 Task 完成 → `READY-FOR-PLATFORM-WARROOM-REVIEW`

**维护者**：主 CLI
