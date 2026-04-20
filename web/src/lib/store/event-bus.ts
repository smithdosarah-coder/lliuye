/**
 * Cross-Agent 事件总线
 *
 * 用途：解耦各 Agent workspace 产出 —— workspace 发事件，view（today / dispatch / warroom）订阅，
 *      不做 Agent 之间的直接方法调用。
 *
 * 模式：pub-sub + 环形 history（最近 200 条）。history 不持久化到 localStorage，
 *      因为完整审计日志由后端 /api/audit 提供；本 store 只做前端实时协调。
 */
import { create } from "zustand";

import type { AgentEvent, AgentEventType, AgentId } from "./types";

type Listener = (event: AgentEvent) => void;
type Unsubscribe = () => void;

const HISTORY_CAP = 200;

interface EventBusState {
  history: AgentEvent[];
  listeners: Set<Listener>;
  publish: (event: Omit<AgentEvent, "id" | "createdAt">) => AgentEvent;
  subscribe: (listener: Listener) => Unsubscribe;
  /** 只订阅特定类型 */
  subscribeTo: (
    types: AgentEventType | AgentEventType[],
    listener: Listener,
  ) => Unsubscribe;
  /** 只订阅某个 Agent 发出的事件 */
  subscribeAgent: (agent: AgentId, listener: Listener) => Unsubscribe;
  /** 取最近 N 条（可按 customerId / agent 过滤） */
  recent: (opts?: {
    limit?: number;
    customerId?: string;
    agent?: AgentId;
  }) => AgentEvent[];
  /** 测试用，清空 */
  reset: () => void;
}

const genId = () =>
  `evt_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;

export const useEventBus = create<EventBusState>((set, get) => ({
  history: [],
  listeners: new Set(),
  publish: (partial) => {
    const event: AgentEvent = {
      id: genId(),
      createdAt: new Date().toISOString(),
      ...partial,
    };
    set((s) => ({ history: [event, ...s.history].slice(0, HISTORY_CAP) }));
    for (const l of get().listeners) {
      try {
        l(event);
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn("[event-bus] listener threw:", err);
      }
    }
    return event;
  },
  subscribe: (listener) => {
    get().listeners.add(listener);
    return () => {
      get().listeners.delete(listener);
    };
  },
  subscribeTo: (types, listener) => {
    const set = new Set(Array.isArray(types) ? types : [types]);
    return get().subscribe((e) => {
      if (set.has(e.type)) listener(e);
    });
  },
  subscribeAgent: (agent, listener) =>
    get().subscribe((e) => {
      if (e.agent === agent) listener(e);
    }),
  recent: ({ limit = 50, customerId, agent } = {}) => {
    let list = get().history;
    if (customerId) list = list.filter((e) => e.customerId === customerId);
    if (agent) list = list.filter((e) => e.agent === agent);
    return list.slice(0, limit);
  },
  reset: () => set({ history: [], listeners: new Set() }),
}));

/**
 * 便捷函数 —— workspace 无需引 hook：
 *   import { publishEvent } from "@/lib/store/event-bus";
 *   publishEvent({ type: "report.completed", agent: "report", ... });
 */
export const publishEvent: EventBusState["publish"] = (...args) =>
  useEventBus.getState().publish(...args);
