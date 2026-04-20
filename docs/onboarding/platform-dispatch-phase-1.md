# platform-dispatch (IM/Slack 风) Phase 1 Onboarding

**状态**：APPROVED
**发布日期**：2026-04-20
**Signal 入口**：`PHASE-1-BATCH-1-DISPATCHED`
**前置**：
- Stage 1.0 contracts 已落地（commit c99a277）
- 共享 store：`web/src/lib/store/*`（只读）
- 契约文档：`docs/arch/platform-contracts.md`

---

## 你是谁

你是 **platform-dispatch** worker CLI，负责把 `/dispatch` 路由从当前 13 行骨架改造成**可用的 Slack 风 IM 视图**。产品用户是客户经理 / 审贷官 / 合规官 / 风险经理 —— 他们围绕"客户"开对话线程，AI Agent 是线程里的自动参与者。

---

## 本批次任务

### ✅ Task A — ThreadList 左栏 + MessageStream 中栏

**目标**：3 栏布局（ThreadList 左 280px / MessageStream 中 flex / InspectorPanel 右 320px），ThreadList 显示按客户聚合的线程。

**模块路径**：
- 新建：`web/src/app/dispatch/_components/{ThreadList,MessageStream,InspectorPanel,MessageBubble,SystemEventCard,HandoffCard}.tsx`
- 新建：`web/src/app/dispatch/_store/dispatch-store.ts`（thread + message 本地 zustand store，种子 mock 数据）
- 修改：`web/src/app/dispatch/page.tsx`（13 行骨架 → 3 栏 layout）
- 消费：`@/lib/store`（useCustomerStore / useEventBus / useAuthStore / byUserId）

**指标/验证**：
- 打开 `/dispatch` 看到 5 个 thread（与 customer-store 5 个客户对应）
- 点击 thread → 右侧切 inspector，中间刷消息流
- thread unreadCount 正确 decrement

**工作量**：M（1.5 天）
**完成信号**：`Signal: DISPATCH-THREE-PANE-DONE`

---

### ✅ Task B — ComposerBar + 快捷命令 `/run`

**目标**：底部输入框支持 `/run agent6 cust_zrgs` 语法，直接触发对应 Agent workspace；普通文本走 IM 留言。

**模块路径**：
- 新建：`web/src/app/dispatch/_components/{ComposerBar,SlashMenu}.tsx`
- 修改：`web/src/app/dispatch/_store/dispatch-store.ts`（addMessage 动作）
- 消费：`@/lib/store`（publishEvent 发 `comment.added`）

**指标/验证**：
- 输入 `/` 弹 4 条命令（run / handoff / assign / clear）
- `/run agent6 cust_zrgs` 发一条 system_event 到当前 thread + 跳转 `/archive/report?customer=cust_zrgs`
- 回车发纯文本消息；消息出现在 stream + publish event

**工作量**：M（1 天）
**完成信号**：`Signal: DISPATCH-COMPOSER-DONE`

---

### ✅ Task C — 事件桥 + Handoff 卡片

**目标**：订阅 event-bus 里的 Agent 事件（report.completed / credit.decided / alert.raised），自动插入到对应客户的 thread 作为 system_event；handoff 事件渲染为可操作的 HandoffCard。

**模块路径**：
- 修改：`web/src/app/dispatch/_store/dispatch-store.ts`（useEffect 里订阅 event-bus，注入消息）
- 修改：`_components/HandoffCard.tsx`（accept / reject 按钮，发 handoff.accepted event）

**指标/验证**：
- 手动 `publishEvent({ type: "report.completed", agent: "report", customerId: "cust_zrgs", ... })` → dispatch 里对应 thread 立即多一条 system_event
- handoff 卡片点"接手"→ publish handoff.accepted + 客户 stage 前进

**工作量**：S（半天）
**完成信号**：`Signal: DISPATCH-EVENT-BRIDGE-DONE`

---

## 完成后

所有 Task 做完：`Signal: READY-FOR-PLATFORM-DISPATCH-REVIEW`

---

## 红线

- ❌ 不改 `web/src/lib/store/*`（红区，走 RFC）
- ❌ 不改 `web/src/components/shell/*`（AppShell 归 CLI-4 + 主 CLI）
- ❌ 不动 `web/src/app/warroom/` / `/today/` / `/customer/` / `/login/`（其他 worker 的地盘）
- ❌ 不碰 `web/src/app/archive/` / `web/src/components/workspace/*`（现有 Agent workspace）
- ✅ `web/src/app/dispatch/` 及其子目录你全权负责
- ✅ 可以 read 其他 worker 文件，但只读

---

## 设计参考

视觉 1:1 对齐 `design_mockups/rm-assistant-final-2026-04-19.html`（2026-04-19 lock）的 shell 主题；Slack / Lark / Microsoft Teams 的 IM 3 栏布局为信息架构参考，但**配色走本项目 data-theme 主题（默认 Canvas），不要搞 Slack 紫或 Teams 蓝**。

---

## ACK 协议

1. Resume 后看到本文件 → commit 一条空/文档 commit，trailer `Signal: PHASE-1-BATCH-1-ACK`
2. 按 Task A → B → C 顺序推进，每 Task 独立 commit 带对应 `-DONE` signal
3. 全 Task 完成 → `READY-FOR-PLATFORM-DISPATCH-REVIEW`

**维护者**：主 CLI
**下次更新触发**：主 CLI 验收后 APPROVE 或 REJECT
