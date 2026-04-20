# Platform Shell v2 · 共享契约

**定位**：本文件是 5 个 platform-* worktree 共用的**红区**。任何跨 CLI 读写 state / event 的代码必须依赖此处定义的类型和 store。

**生效日期**：2026-04-20
**当前 protocol**：v1

---

## 契约文件清单（单一写入方 = 主 CLI）

| 文件 | 角色 | 写入方 | 读取方 |
|---|---|---|---|
| `web/src/lib/store/types.ts` | 共享类型（Customer / AgentEvent / HandoffTicket / ImMessage / User / Role / Permission） | 主 CLI | 所有 worktree |
| `web/src/lib/store/customer-store.ts` | 客户上下文 zustand store | 主 CLI | 所有 view + Agent workspace |
| `web/src/lib/store/event-bus.ts` | 跨 Agent 事件总线 | 主 CLI | Agent workspace（publish） + today/dispatch/warroom（subscribe） |
| `web/src/lib/store/auth-store.ts` | 登录态 + RBAC matrix | 主 CLI + CLI-4 | 所有需要鉴权的入口 |
| `web/src/lib/store/handoff-catalog.ts` | 跨 Agent 交接预设 | 主 CLI | Agent workspace（渲染 action 按钮） + CLI-2 warroom |

**工程约定**：以上文件变更**必须**走 RFC 流程；worker 无权直接改。Worker 自己在 domain 内定义的类型（例如 `web/src/app/dispatch/types.ts`）不受本契约约束。

---

## Worktree 职能分工

| Worktree | 分支 | 拥有的 view / page / feature | 不可碰 |
|---|---|---|---|
| `platform-dispatch` (CLI-1) | `feat/platform-dispatch` | `/dispatch` IM 视图、ThreadList、MessageStream、ComposerBar | AppShell / mockup-v2.css |
| `platform-warroom` (CLI-2) | `feat/platform-warroom` | `/warroom` kanban 视图、TicketCard、StatusColumn、FilterBar | AppShell / 其他 view 的 page.tsx |
| `platform-today` (CLI-3) | `feat/platform-today` | `/today` 聚合视图、MorningBrief、PriorityQueue | AppShell / 其他 view 的 page.tsx |
| `platform-auth` (CLI-4) | `feat/platform-auth` | `/login` 登录页、AppShell 内权限守卫 slot、persona 切换控件 | mockup-v2.css / 其他 view 的 page.tsx |
| `platform-customer` (CLI-5) | `feat/platform-customer` | `/customer/[id]` 客户 360、Desk 的客户列表扩展、客户详情抽屉 | AppShell 主结构 / 其他 view 的 page.tsx |

### 冲突预防

- **AppShell.tsx**：只由 CLI-4 改（加鉴权 guard）+ 主 CLI 改。CLI-5 若需注入客户抽屉入口，走 slot（主 CLI 预留 `<AppShell>` 的 `drawer` prop）
- **mockup-v2.css / platform-shell-v2.css**：additive only —— 加 class 可以，改现有 class 的 style 不行
- **lib/store/\***：单一写入方主 CLI；需要新字段 → 提 RFC
- **lib/store/index.ts**：主 CLI 唯一写入
- **app layout.tsx / shell/\***：CLI-4 可加 `<AuthGate>`，其他不改

### Slot 约定

AppShell 预留 4 个 slot 供 worker 注入（主 CLI 在 Stage 1.1 补）：
- `AppShell.drawer` → 客户详情抽屉（CLI-5）
- `AppShell.authGate` → 未登录拦截（CLI-4）
- `AppShell.notifications` → 事件推送 toast（CLI-1 / CLI-2 共用）
- `AppShell.personaSwitcher` → persona 切换按钮（CLI-4）

---

## Store 使用规范

### customer-store
```ts
import { useCustomerStore } from "@/lib/store";

const current = useCustomerStore((s) => s.currentId);
const focus = useCustomerStore((s) => s.focus);
const customer = useCustomerStore((s) => s.byId(current ?? ""));
```

**只有用户显式动作** 才能调 `focus`（点击 Desk 项、打开客户卡片）。Agent workspace 内部不得在组件 mount 时"顺手"切换 current customer。

### event-bus
```ts
import { publishEvent, useEventBus } from "@/lib/store";

// Agent workspace 完成关键步骤时：
publishEvent({
  type: "report.completed",
  agent: "report",
  customerId: currentId,
  actor: currentUserId,
  payload: { reportId, qcPassed: true },
});

// view 订阅：
useEffect(() => {
  return useEventBus.getState().subscribeTo(
    ["report.completed", "credit.decided"],
    (e) => { ... },
  );
}, []);
```

**不得** 直接操作 `history` 数组；**不得** 在 listener 里再 publish（避免循环）。

### auth-store
```ts
import { useAuthStore } from "@/lib/store";

const can = useAuthStore((s) => s.can);
if (!can({ kind: "agent.access", agent: "credit" })) {
  return <NoPermission />;
}
```

RBAC matrix 统一在 auth-store.ts 内，**不要** 在组件里硬编 role 判定。

### handoff-catalog
```ts
import { findRecipes, buildTicketSkeleton } from "@/lib/store";

const recipes = findRecipes("report");
// 渲染按钮；点击后：
const ticket = buildTicketSkeleton(recipe, {
  customerId,
  requestedBy: user.id,
  event: sourceEvent,
});
// 送 warroom store（CLI-2 提供）
```

---

## 改动流程（RFC）

需要改 `lib/store/*.ts` 字段时：

1. Worker 在 `docs/handoff/decisions-log.md` 追加 `Q-NNN`：说清改什么 / 为什么 / 影响哪些 worktree
2. Commit trailer `Signal: Q-NNN-RAISED`，push
3. 主 CLI 读到后在同文件追加 `A-NNN`：APPROVED / REJECTED / AMENDMENT
4. APPROVED → 主 CLI 改 store 文件，commit `Signal: A-NNN-RESOLVED`
5. 所有 worker rebase 拉取
6. Worker 在各自分支 commit `Signal: A-NNN-ACK` 表明已同步

**禁止**：worker 在自己分支改 store 文件，这会让其他 worker 冲突。

---

## 版本演进

| 版本 | 日期 | 变更 |
|---|---|---|
| v1 | 2026-04-20 | Initial —— 5 store 文件 + RBAC matrix + 6 个 handoff recipe |

下次 bump protocol_version 时（在 `docs/handoff/mesh.json`）必须：
- 所有 worker 收到一条 `PROTOCOL-BUMP-vN` signal
- Worker ACK 之前不得合入新的 commit

---

## FAQ

**Q：我的 view 需要记录"用户最近打开过的 report id"，这算红区吗？**
A：不算。只要不跨 worktree 读写，你自己在 view 本地 zustand store 里存即可，文件名加前缀（如 `lib/store/dispatch-thread-store.ts`）以示非共享。

**Q：可以 import 其他 worker 的组件吗？**
A：可以 import，但不能 **改**。其他 worker 的文件对你是只读的。

**Q：event-bus 的 history 不持久化 —— 如果用户刷新，事件流不就丢了吗？**
A：对。这是刻意的 —— 真实审计流由后端 /api/audit 提供，前端只做实时协调。Demo 期刷新后的"空态"体验也能接受。
