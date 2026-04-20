# platform-today (今日聚合) Phase 1 Onboarding

**状态**：APPROVED
**发布日期**：2026-04-20
**Signal 入口**：`PHASE-1-BATCH-1-DISPATCHED`
**前置**：
- Stage 1.0 contracts 已落地（commit c99a277）
- 共享 store：`web/src/lib/store/*`（只读）

---

## 你是谁

你是 **platform-today** worker CLI，负责把 `/today` 从 89 行静态页改造成**"今日第一屏"动态聚合**：当前登录用户看到自己今天要处理的客户 / 预警 / 任务 / 事件流，**不是设计稿截图，而是活数据**。

---

## 本批次任务

### ✅ Task A — MorningBrief 顶部摘要

**目标**：顶部一张 hero 卡，显示 "早上好，{name}"、今日节选（"你有 N 个待办 ticket、M 条 alert 要看、K 个客户今天有活动"），数据来自 auth-store + event-bus.recent() + warroom ticket store（如果已 build；未 build 就用 mock fallback）。

**模块路径**：
- 新建：`web/src/app/today/_components/{MorningBrief,StatCell}.tsx`
- 修改：`web/src/app/today/page.tsx`

**指标/验证**：
- 未登录 → 跳 `/login`（CLI-4 提供；未就绪就先用硬编 u_wangzhe）
- 切 persona → 问候语 + 统计数字变化
- 每 30s 刷新一次统计

**工作量**：S（半天）
**完成信号**：`Signal: TODAY-BRIEF-DONE`

---

### ✅ Task B — PriorityQueue 今日客户队列

**目标**：按 stage × lastActivityAt 给客户排序，展示 TOP 8 客户卡（stage 徽章 + 最近事件 1 行 + 快捷操作"打开 workspace"）。

**模块路径**：
- 新建：`web/src/app/today/_components/{PriorityQueue,CustomerRow}.tsx`

**指标/验证**：
- 5 个 seed 客户按优先级展示（alert > credit > report > intake > lead）
- 点击"打开报告"→ `/archive/report?customer=xxx`
- 切 persona（u_lihua）→ 只看自己 assigned / sharedWith 的客户

**工作量**：S（半天）
**完成信号**：`Signal: TODAY-QUEUE-DONE`

---

### ✅ Task C — EventTimeline 近期事件流

**目标**：底部一个 timeline，展示 event-bus.recent({ limit: 20 })，每条一行（时间 + agent 徽章 + 事件文案 + 客户名点击跳转）。

**模块路径**：
- 新建：`web/src/app/today/_components/{EventTimeline,EventRow}.tsx`
- 消费：`useEventBus.subscribe` 实时追加；`publishEvent` 的几条 mock seed（mount 时手动 publish 3-5 条假事件让 timeline 有东西看）

**指标/验证**：
- Timeline 初始 3-5 条 seed 事件
- 在别的 view（warroom / dispatch）触发 publishEvent → today 刷新后多一条
- 事件 >10 分钟旧 → 淡化显示

**工作量**：S（半天）
**完成信号**：`Signal: TODAY-TIMELINE-DONE`

---

## 完成后

全 Task 完成：`Signal: READY-FOR-PLATFORM-TODAY-REVIEW`

---

## 红线

- ❌ 不改 `web/src/lib/store/*`
- ❌ 不改 `web/src/components/shell/*`
- ❌ 不动 `/dispatch/` / `/warroom/` / `/customer/` / `/login/`
- ✅ `web/src/app/today/` 你全权负责
- ✅ 允许从其他 worker 的 store 读（import 路径示例：`@/app/warroom/_store/ticket-store`），但**只 read，不 write**

---

## 设计参考

形似 Linear 的 Today / GitHub Copilot Workspace 的 Inbox / Superhuman 的 Today screen —— 重"读"轻"操作"，打开即看、一眼获取今天状态。视觉对齐 `rm-assistant-final-2026-04-19.html` Canvas 主题。

---

## ACK 协议

1. Resume 后 commit `Signal: PHASE-1-BATCH-1-ACK`
2. Task A → B → C 顺序
3. 全 Task 完成 → `READY-FOR-PLATFORM-TODAY-REVIEW`

**维护者**：主 CLI
