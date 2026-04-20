# platform-customer (客户 360 + Desk 扩展) Phase 1 Onboarding

**状态**：APPROVED
**发布日期**：2026-04-20
**Signal 入口**：`PHASE-1-BATCH-1-DISPATCHED`
**前置**：
- Stage 1.0 contracts 已落地（commit c99a277）
- `web/src/lib/store/customer-store.ts` 已提供 5 客户 seed（只读消费；允许 focus/upsert/advanceStage，不允许改种子数组逻辑）

---

## 你是谁

你是 **platform-customer** worker CLI，负责把"客户"从散落在各 Agent workspace 的变量升格为**平台一等公民**：
- `/customer/[id]` 客户 360 页（时间线 + 材料清单 + 协同人员 + 每个 Agent 的最新产出）
- Desk 左抽屉的客户列表扩展（搜索、分组、pin、拖拽到 main view）
- 客户详情右抽屉（全局 slot，任何 view 点客户名都能开）

---

## 本批次任务

### ✅ Task A — `/customer/[id]` 客户 360 页

**目标**：路由 `/customer/:id` 显示一个客户的全量视图：
- 顶部 hero：客户名 + 行业 + 地区 + stage + 授信金额 + 标签
- 时间线：该客户相关的 event-bus 事件（useEventBus.recent({ customerId }))
- 6 Agent tile：每个 tile 显示最近一次该 Agent 对本客户的产出（"无"则置灰）
- 协同人员：assignedTo + sharedWith 头像列

**模块路径**：
- 新建：`web/src/app/customer/[id]/page.tsx`
- 新建：`web/src/app/customer/[id]/_components/{CustomerHero,AgentTileStrip,ActivityTimeline,CollaboratorList}.tsx`
- 消费：`@/lib/store`（useCustomerStore / useEventBus / byUserId）

**指标/验证**：
- 访问 `/customer/cust_zrgs` 看到"中锐工商"详情
- 不存在的 id → 404（Next.js notFound()）
- 时间线至少 3 条 event（mount 时 publish 几条 seed）
- 点 Agent tile → 跳 `/archive/{agent}?customer=cust_zrgs`

**工作量**：M（1.5 天）
**完成信号**：`Signal: CUSTOMER-360-DONE`

---

### ✅ Task B — Desk 客户列表增强

**目标**：左抽屉 Desk 现状是静态 mock；升级为动态：
- 顶部 `<input>` 搜索框（按 name / shortName / industry / tag 过滤）
- 分组：置顶（recents 前 3） / 我负责的 / 协同 / 全部
- 每行有 pin 按钮（pin 到置顶组）+ stage 徽章
- 保留现有的 hover-from-edge + ⌘K 交互

**模块路径**：
- 修改：`web/src/components/shell/Desk.tsx`（你的唯一 shell 改动；主 CLI 已知并允许）
- 新建：`web/src/components/shell/DeskCustomerRow.tsx`
- 新建：`web/src/components/shell/DeskSearch.tsx`
- 扩展：`web/src/lib/store/customer-store.ts` 加 `pinned: string[]` 字段 —— **这是红区改动，你必须走 RFC 流程**（见下方"改红区的流程"）

**指标/验证**：
- 搜"中锐" → 只剩 1 条
- 切 persona（u_lihua）→ 列表重新按 assignedTo 过滤
- Pin 一条 → 刷新页面保留

**工作量**：M（1 天）
**完成信号**：`Signal: CUSTOMER-DESK-DONE`

---

### ✅ Task C — CustomerDrawer 全局抽屉 slot

**目标**：AppShell 预留的 `drawer` slot 填充为"点任何客户名 → 右侧滑入 280px drawer 显示迷你客户卡"。Dispatch / Warroom / Today 只要在 JSX 上用 `<CustomerLink customerId={x}>` 就自动触发。

**模块路径**：
- 新建：`web/src/components/shell/CustomerDrawer.tsx`
- 新建：`web/src/components/shared/CustomerLink.tsx`（全局组件，供其他 worker 使用）
- 修改：`AppShell.tsx` 注入 drawer slot（与 CLI-4 协调，两人都要改 AppShell —— 走 decisions-log 对齐）

**指标/验证**：
- dispatch 里点客户名 → drawer 滑入
- drawer 里"打开详情"按钮跳 `/customer/[id]`
- 按 Esc / 点外部关闭

**工作量**：S（半天）
**完成信号**：`Signal: CUSTOMER-DRAWER-DONE`

---

## 改红区的流程（Task B 会用到）

Task B 需要给 `customer-store.ts` 加 `pinned` 字段。这是红区（见 `docs/arch/platform-contracts.md`）。你要这么做：

1. 先写 Task B 的 UI + 本地 state（zustand 私 store `web/src/components/shell/_desk-store.ts` 持久化 pinned 列表）—— 完全不碰共享 store
2. Task A/C 完成后，如果评审觉得 pinned 放共享 store 更合理，再起 Q-NNN 请主 CLI 评估
3. **不要在 Task B 里偷偷改 customer-store.ts**；rebase 时会爆炸

---

## 红线

- ❌ 不改 `web/src/lib/store/types.ts` / `customer-store.ts` 的已有字段（加字段走 RFC，见上）
- ❌ 不动 `/dispatch/` / `/warroom/` / `/today/` / `/login/` / `/audit/` 页
- ❌ 不改 `HANDOFF_CATALOG` / `auth-store` / `event-bus`
- ✅ `web/src/app/customer/` + `web/src/components/shell/{Desk,DeskSearch,DeskCustomerRow,CustomerDrawer}.tsx` + `web/src/components/shared/CustomerLink.tsx` 你全权负责
- ✅ `AppShell.tsx` 仅限注入 drawer slot（见 Task C）；其他结构性改动走 decisions-log 预告

---

## 设计参考

HubSpot CRM 客户 360 / Salesforce Lightning 客户页 / Linear 的 project timeline —— 要点："一屏内看完关键信息，深入钻取另开"。视觉对齐 `rm-assistant-final-2026-04-19.html` Canvas 主题。

---

## ACK 协议

1. Resume 后 commit `Signal: PHASE-1-BATCH-1-ACK`
2. Task A → B → C 顺序（Task B 的 pinned 放本地 store，不碰红区）
3. 全 Task 完成 → `READY-FOR-PLATFORM-CUSTOMER-REVIEW`

**维护者**：主 CLI
