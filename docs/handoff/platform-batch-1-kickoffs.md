# Platform Phase 1 Batch 1 · 5 Worker Kickoff Prompts

> **定位**：5 条 GO 指令，每条粘到对应 worker CLI（worker resume 汇报完后）。
> **生效前提**：`9eb3346 feat(mesh/platform): dispatch 5 platform worker worktrees + Phase 1 Batch 1` 已落 main。
> **主 CLI 仲裁**：任何 worker 开 Q-NNN / RFC，主 CLI 回 A-NNN 后 worker 才能继续。

---

## ① platform-dispatch

```
GO。按 onboarding 执行：

1. 先 commit 一条 doc-only commit，trailer:
   Signal: PHASE-1-BATCH-1-ACK
2. 然后按 Task A → B → C 顺序推进：
   - A: 3 栏布局 + dispatch-store（5 thread 对齐 5 客户）→ Signal: DISPATCH-THREE-PANE-DONE
   - B: ComposerBar + /run 快捷命令 → Signal: DISPATCH-COMPOSER-DONE
   - C: event-bus 桥 + HandoffCard → Signal: DISPATCH-EVENT-BRIDGE-DONE
3. 全部完成后 commit:
   Signal: READY-FOR-PLATFORM-DISPATCH-REVIEW

红区守则：不动 lib/store / shell/*, 不动其他 worker 地盘。
需要改红区 → 开 Q-NNN 等主 CLI A-NNN 再动。
每个 Task 完成独立 commit，不攒。
开干。
```

---

## ② platform-warroom

```
GO。按 onboarding 执行：

1. 先 commit doc-only，trailer:
   Signal: PHASE-1-BATCH-1-ACK
2. Task A → B → C 顺序：
   - A: ticket-store + 4 列 kanban + 订阅 handoff.requested → Signal: WARROOM-KANBAN-DONE
   - B: TicketDrawer（Accept/Reject/Reassign/Archive）→ Signal: WARROOM-DRAWER-DONE
   - C: FilterBar（按客户/负责人/agent/priority）+ URL query 同步 → Signal: WARROOM-FILTERS-DONE
3. 全 Task 完成：
   Signal: READY-FOR-PLATFORM-WARROOM-REVIEW

拖拽库建议 @dnd-kit/core（未装就 Task A 先加 deps）。
红区守则同：不改 lib/store / HANDOFF_CATALOG / shell/*, 只读其他 worker。
每 Task 独立 commit。
开干。
```

---

## ③ platform-today

```
GO。按 onboarding 执行：

1. 先 commit doc-only，trailer:
   Signal: PHASE-1-BATCH-1-ACK
2. Task A → B → C 顺序：
   - A: MorningBrief hero + StatCell（30s 刷新）→ Signal: TODAY-BRIEF-DONE
   - B: PriorityQueue（TOP 8 按 stage×lastActivityAt）→ Signal: TODAY-QUEUE-DONE
   - C: EventTimeline（mount publish 3-5 条 seed，实时追加）→ Signal: TODAY-TIMELINE-DONE
3. 全 Task 完成：
   Signal: READY-FOR-PLATFORM-TODAY-REVIEW

AuthGate 由 CLI-4 做，未就绪就先硬编 u_wangzhe 兜底。
允许 import 其他 worker 的 store 但只读。
每 Task 独立 commit。
开干。
```

---

## ④ platform-auth

```
GO。按 onboarding 执行（你是 4 Task，最重）：

1. 先 commit doc-only，trailer:
   Signal: PHASE-1-BATCH-1-ACK
2. Task A → B → C → D 顺序：
   - A: /login 5 persona 卡 + AuthGate 包裹 → Signal: AUTH-LOGIN-PAGE-DONE
   - B: PersonaSwitcher Popover + masthead 读 authStore → Signal: AUTH-PERSONA-SWITCHER-DONE
   - C: RBAC 守卫 + NoPermission 组件 + 6 tile 置灰 → Signal: AUTH-RBAC-GUARD-DONE
   - D: /audit 入口（仅合规官+admin）→ Signal: AUTH-AUDIT-ENTRY-DONE
3. 全 Task 完成：
   Signal: READY-FOR-PLATFORM-AUTH-REVIEW

AppShell 归你 + 主 CLI 改。每次改 AppShell 在 decisions-log 留 ≤3 行说明（加了什么 slot / guard），platform-customer 要 rebase。
RBAC matrix 红区不动，用 can(action) 谓词消费。
每 Task 独立 commit。
开干。
```

---

## ⑤ platform-customer

```
GO。按 onboarding 执行：

1. 先 commit doc-only，trailer:
   Signal: PHASE-1-BATCH-1-ACK
2. Task A → B → C 顺序：
   - A: /customer/[id] 360（hero+timeline+6 tile+collaborator）→ Signal: CUSTOMER-360-DONE
   - B: Desk 增强（搜索+分组+pin）。pinned 放本地 _desk-store，不碰 customer-store 红区 → Signal: CUSTOMER-DESK-DONE
   - C: CustomerDrawer 全局 slot + CustomerLink 组件 → Signal: CUSTOMER-DRAWER-DONE
3. 全 Task 完成：
   Signal: READY-FOR-PLATFORM-CUSTOMER-REVIEW

Task B pinned 字段：严禁直接改 customer-store.ts，先本地 _desk-store 实现，review 时再议是否迁共享。
Task C AppShell drawer slot 与 CLI-4（platform-auth）协调，两人都要碰 AppShell —— 先在 decisions-log 留告示再改，避免 rebase 爆炸。
每 Task 独立 commit。
开干。
```

---

## 新主 CLI 使用说明

1. 用户双击 `C:\Users\Mr.S\Desktop\mesh-credit-agents.bat` 起 5 worker tab
2. 每个 worker tab 粘 "读 AGENT_IDENTITY.md ..." 万能 resume 指令（剪贴板自动填）
3. worker 汇报 "Resume 完成" 后，主 CLI 把本文件对应小节的 GO prompt 粘给用户 / 或指示用户按次序粘贴
4. 进度追踪：`py C:/Users/Mr.S/.claude/skills/multi-cli-mesh/scripts/mesh_status.py`
