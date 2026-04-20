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

## Phase 1 Batch 1 · 完工记录（2026-04-20）

| 步骤 | Commit | Signal |
| --- | --- | --- |
| ACK | `35aea64` | `PHASE-1-BATCH-1-ACK` |
| Task A · 3 栏 + dispatch-store | `7c2fc83` | `DISPATCH-THREE-PANE-DONE` |
| Task B · ComposerBar + /run | `ca7c72c` | `DISPATCH-COMPOSER-DONE` |
| Task C · event-bus 桥 + HandoffCard | `7de7eff` | `DISPATCH-EVENT-BRIDGE-DONE` |
| Fix · zustand EMPTY sentinel | `ba708e1` | — |
| Batch roll-up | `8424f8d` | `READY-FOR-PLATFORM-DISPATCH-REVIEW`（旧） |
| 本次 READY 重发（GO-2） | 本 commit | `READY-FOR-PLATFORM-DISPATCH-REVIEW` |

（上述 commit sha 基于 rebase onto `upstream/chore/l0-infra` 之后；rebase 前旧 sha 已弃。）

### 浏览器冒烟（localhost:3000/dispatch）

- ThreadList 5 行（中锐工商 / 云融科技 / 鼎川精密 / 海元供应链 / 同信新材料），与 customer-store 5 个 seed 对齐，unread badge 显示正确。
- 点 thread → `customer-store.focus(customerId)` 触发，中栏 meta 刷新（CREDIT LINE / PARTICIPANTS），右栏 Inspector 展示客户档案 + 负责人 + 协同 + 标签。
- `/handoff report_to_credit` → 发 `handoff.requested`（`payload.source="dispatch.local"` 防桥回环） + 在当前 thread 插入 pending HandoffCard；点"接手" → `customer-store.advanceStage("cust_zrgs","credit")` 推进，stream 头部 stage 从"报告撰写"切"授信审批"，右栏 Inspector 同步刷新，system_event 记 `王哲 接手了 Agent3 授信`。
- EventBridge 订阅 11 类 Agent 事件（含 `report.completed` / `credit.decided` / `alert.raised` / `handoff.requested/accepted` 等），非 `dispatch.local` 来源事件自动落对应 thread。
- 控制台 0 error / 0 warning。

### 红线守住

- `web/src/lib/store/**`（5 份 store + event-bus + handoff-catalog）未动。
- `web/src/components/shell/**`（AppShell / Desk / ThemeSwitch）未动。
- 其他 worker view 路径（`/today` / `/archive` / `/warroom` / `/customer` / `/login`）未动。
- 所有视图状态落在 `web/src/app/dispatch/_components/**` + `web/src/app/dispatch/_store/**`。
- HandoffCard 结构化 payload 以 JSON 放进 `ImMessage.content`（avoid contract bump）。跨 store 写入仅发生在 user 显式动作（点 thread → focus，点"接手" → advanceStage）。

### Legacy-theme purge 合规（rebase 自查）

基于 `f004a1d LEGACY-THEME-PURGED`：

- 未引入 `crimson` / `Letterpress` / `ink-seal` / `InkSeal` 任何标识符。
- `dispatch-im.css` 字体栈复查：`--mono` 仅包裹 Latin/数字（timestamps / unread / `<kbd>/`），所有 Chinese field names 走 `--cjk`；原 4 处 CJK-in-mono eyebrow（ThreadList / InspectorPanel / MessageStream meta / SlashMenu head）已转为 Latin eyebrow（`DISPATCH` / `CUSTOMER` / `CREDIT LINE` / `PARTICIPANTS` / `COMMANDS · TYPE TO FILTER`），遵循 mockup `BOOK · RECENT · CREATE` 惯例。
- 主题切换器 Canvas / Matcha / Dusk / Ink 四套正常生效，无 Letterpress 残留。

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
