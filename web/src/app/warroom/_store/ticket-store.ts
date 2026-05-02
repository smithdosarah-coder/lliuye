/**
 * Warroom ticket store —— /warroom kanban 本地 state。
 *
 * 数据源：
 * 1) event-bus `handoff.requested` 订阅（workspace 发起）
 * 2) 看板内用户操作（drag / Accept / Reject / Reassign）
 *
 * 持久化：localStorage `platform.warroom.tickets.v1`，刷新保留。
 * 订阅注册：`subscribeHandoffRequested()` 在 warroom page mount 时调一次，StrictMode 双调安全。
 *
 * 不改 lib/store/*（红区）：本文件与 lib/store 的关系是「消费 + 写入自己的 ticket 副本」。
 * 需要 event-bus / catalog / customer 元数据时走 import @/lib/store 的只读 API。
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

import {
  buildTicketSkeleton,
  findRecipeById,
  publishEvent,
  useCustomerStore,
  useEventBus,
  type AgentEvent,
  type AgentId,
  type HandoffStatus,
  type HandoffTicket,
} from "@/lib/store";

/** 看板可见的 4 列（`rejected` 不在 kanban 呈现，留在 store 里供 audit / drawer） */
export const KANBAN_STATUSES: readonly HandoffStatus[] = [
  "requested",
  "accepted",
  "in_progress",
  "completed",
] as const;

export type KanbanStatus = (typeof KANBAN_STATUSES)[number];

export interface ColumnConfig {
  status: KanbanStatus;
  label: string;
  done?: boolean;
}

export const COLUMNS: ColumnConfig[] = [
  { status: "requested", label: "待受理" },
  { status: "accepted", label: "已受理" },
  { status: "in_progress", label: "进行中" },
  { status: "completed", label: "已完成", done: true },
];

export interface TicketFilters {
  customerId?: string;
  assignedTo?: string;
  requestedBy?: string;
  fromAgent?: AgentId;
  toAgent?: AgentId;
  priority?: "normal" | "urgent";
  scope?: "mine" | "all";
  currentUserId?: string;
}

const genId = () =>
  `tkt_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;

const nowIso = () => new Date().toISOString();

/** First-run seed —— 让 kanban 首次加载不为空，便于 demo 观察。
 *  用户清空后不会重填（persist 以 localStorage 是否存在为准）。 */
const seed = (): HandoffTicket[] => [
  {
    id: "tkt_seed_1",
    fromAgent: "report",
    toAgent: "credit",
    customerId: "cust_zrgs",
    reason: "报告定稿 → 交审贷官出授信决策",
    payload: { reportId: "rpt_zrgs_20260420", finalized: true },
    status: "requested",
    requestedBy: "u_wangzhe",
    assignedTo: "u_lihua",
    createdAt: "2026-04-20T09:15:00+08:00",
    updatedAt: "2026-04-20T09:15:00+08:00",
  },
  {
    id: "tkt_seed_2",
    fromAgent: "channel",
    toAgent: "report",
    customerId: "cust_haiyuan",
    reason: "锁定 look-alike 候选客户后，发起尽调报告",
    payload: { candidateId: "cand_haiyuan_01" },
    status: "accepted",
    requestedBy: "u_wangzhe",
    assignedTo: "u_wangzhe",
    createdAt: "2026-04-20T08:40:00+08:00",
    updatedAt: "2026-04-20T08:55:00+08:00",
  },
  {
    id: "tkt_seed_3",
    fromAgent: "alert",
    toAgent: "compliance",
    customerId: "cust_yunrong",
    reason: "预警命中 → 合规官复核",
    payload: { alertId: "alt_yunrong_7", severity: "yellow" },
    status: "in_progress",
    requestedBy: "u_chenkai",
    assignedTo: "u_zhoumin",
    createdAt: "2026-04-20T07:30:00+08:00",
    updatedAt: "2026-04-20T08:10:00+08:00",
  },
  {
    id: "tkt_seed_4",
    fromAgent: "credit",
    toAgent: "report",
    customerId: "cust_dingchuan",
    reason: "授信打回 → 审贷意见回写报告",
    payload: { reportId: "rpt_dingchuan_0417", issues: ["财报 P.24 披露不全"] },
    status: "completed",
    requestedBy: "u_lihua",
    assignedTo: "u_wangzhe",
    createdAt: "2026-04-18T15:20:00+08:00",
    updatedAt: "2026-04-19T11:45:00+08:00",
  },
];

interface TicketStoreState {
  tickets: HandoffTicket[];
  /** 上次订阅的清理函数，避免 StrictMode 双订阅 */
  _unsubscribe: (() => void) | null;

  add: (ticket: Omit<HandoffTicket, "id" | "createdAt" | "updatedAt">) => HandoffTicket;
  /** 从事件 / recipeId 直接创建（event-bus listener 用这个路径） */
  addFromRequest: (args: {
    recipeId: string;
    customerId: string;
    requestedBy: string;
    assignedTo?: string;
    event?: AgentEvent;
  }) => HandoffTicket | null;

  updateStatus: (
    id: string,
    nextStatus: HandoffStatus,
    opts?: { actor?: string; publish?: boolean; reason?: string },
  ) => void;
  reassign: (id: string, assignedTo: string, actor?: string) => void;
  archive: (id: string) => void;
  /** 测试 / 手动清空 */
  reset: () => void;

  byStatus: (status: HandoffStatus) => HandoffTicket[];
  byId: (id: string) => HandoffTicket | undefined;
  filtered: (filters: TicketFilters) => HandoffTicket[];

  /** warroom page mount 时调。返回 cleanup，React effect 直接 return 它。 */
  subscribeHandoffRequested: () => () => void;
}

export const useTicketStore = create<TicketStoreState>()(
  persist(
    (set, get) => ({
      tickets: seed(),
      _unsubscribe: null,

      add: (partial) => {
        const ticket: HandoffTicket = {
          ...partial,
          id: genId(),
          createdAt: nowIso(),
          updatedAt: nowIso(),
        };
        set((s) => ({ tickets: [ticket, ...s.tickets] }));
        return ticket;
      },

      addFromRequest: ({ recipeId, customerId, requestedBy, assignedTo, event }) => {
        const recipe = findRecipeById(recipeId);
        if (!recipe) {
          console.warn(`[warroom] addFromRequest: unknown recipeId=${recipeId}`);
          return null;
        }
        const skeleton = buildTicketSkeleton(recipe, {
          customerId,
          requestedBy,
          assignedTo,
          event,
        });
        return get().add(skeleton);
      },

      updateStatus: (id, nextStatus, opts) => {
        const prev = get().tickets.find((t) => t.id === id);
        if (!prev || prev.status === nextStatus) return;
        set((s) => ({
          tickets: s.tickets.map((t) =>
            t.id === id
              ? { ...t, status: nextStatus, updatedAt: nowIso() }
              : t,
          ),
        }));
        if (opts?.publish !== false) {
          const eventType = statusToEventType(nextStatus);
          if (eventType) {
            publishEvent({
              type: eventType,
              agent: prev.toAgent,
              customerId: prev.customerId,
              actor: opts?.actor ?? prev.assignedTo ?? prev.requestedBy,
              payload: {
                ticketId: id,
                fromAgent: prev.fromAgent,
                toAgent: prev.toAgent,
                reason: opts?.reason,
              },
              correlationId: id,
            });
          }
        }
      },

      reassign: (id, assignedTo, actor) => {
        const prev = get().tickets.find((t) => t.id === id);
        if (!prev || prev.assignedTo === assignedTo) return;
        set((s) => ({
          tickets: s.tickets.map((t) =>
            t.id === id ? { ...t, assignedTo, updatedAt: nowIso() } : t,
          ),
        }));
        publishEvent({
          type: "comment.added",
          agent: prev.toAgent,
          customerId: prev.customerId,
          actor: actor ?? prev.requestedBy,
          payload: {
            ticketId: id,
            action: "reassign",
            prevAssignee: prev.assignedTo,
            nextAssignee: assignedTo,
          },
          correlationId: id,
        });
      },

      archive: (id) =>
        set((s) => ({ tickets: s.tickets.filter((t) => t.id !== id) })),

      reset: () => set({ tickets: [] }),

      byStatus: (status) => get().tickets.filter((t) => t.status === status),
      byId: (id) => get().tickets.find((t) => t.id === id),

      filtered: (filters) => {
        const { customerId, assignedTo, requestedBy, fromAgent, toAgent, priority, scope, currentUserId } = filters;
        return get().tickets.filter((t) => {
          if (customerId && t.customerId !== customerId) return false;
          if (assignedTo && t.assignedTo !== assignedTo) return false;
          if (requestedBy && t.requestedBy !== requestedBy) return false;
          if (fromAgent && t.fromAgent !== fromAgent) return false;
          if (toAgent && t.toAgent !== toAgent) return false;
          if (priority) {
            const p = inferPriority(t);
            if (p !== priority) return false;
          }
          if (scope === "mine" && currentUserId) {
            if (t.assignedTo !== currentUserId && t.requestedBy !== currentUserId)
              return false;
          }
          return true;
        });
      },

      subscribeHandoffRequested: () => {
        const existing = get()._unsubscribe;
        if (existing) existing();
        const unsub = useEventBus.getState().subscribeTo("handoff.requested", (e) => {
          const payload = e.payload ?? {};
          const recipeId = typeof payload.recipeId === "string" ? payload.recipeId : null;
          const customerId = e.customerId ?? (typeof payload.customerId === "string" ? payload.customerId : null);
          if (!recipeId || !customerId) return;
          get().addFromRequest({
            recipeId,
            customerId,
            requestedBy: e.actor,
            assignedTo: typeof payload.assignedTo === "string" ? payload.assignedTo : undefined,
            event: e,
          });
        });
        set({ _unsubscribe: unsub });
        return () => {
          unsub();
          if (get()._unsubscribe === unsub) set({ _unsubscribe: null });
        };
      },
    }),
    {
      name: "platform.warroom.tickets.v1",
      partialize: (s) => ({ tickets: s.tickets }),
    },
  ),
);

/** status → 对应 AgentEvent 类型。仅对 accepted / completed 映射；其他状态不发事件。 */
function statusToEventType(status: HandoffStatus) {
  if (status === "accepted") return "handoff.accepted" as const;
  return null;
}

/** 从 recipe + payload 推断 priority —— catalog 里 recipe.priority 存在时用；否则默认 normal。
 *  live ticket 无法直接读 recipe（id 不存）时，用 reason 中关键字兜底。 */
export function inferPriority(ticket: HandoffTicket): "normal" | "urgent" {
  if (ticket.reason.includes("预警") || ticket.reason.includes("打回")) return "urgent";
  return "normal";
}

/** 便捷：读 customer meta，避免组件重复接 store。 */
export function useCustomerForTicket(ticket: HandoffTicket | null | undefined) {
  return useCustomerStore((s) => (ticket ? s.byId(ticket.customerId) : undefined));
}
