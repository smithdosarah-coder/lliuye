/**
 * Dispatch view 本地 store —— 5 个 thread + 每 thread 的消息流。
 *
 * 边界：
 * - 单 view 私有，文件名前缀 `_store/` 表明非 lib/store 共享契约（contracts §FAQ）
 * - 写入：用户在 dispatch UI 内的动作（点 thread / 发消息）
 * - 读取：仅 dispatch view 内组件
 * - 与 lib/store 的协作：selectThread → 调 customer-store.focus；addMessage → 可选 publish event-bus（在 ComposerBar 决定）
 *
 * Task C 会扩 useEffect 订阅 event-bus 自动注入 system_event。
 */
"use client";

import { create } from "zustand";

import { useCustomerStore } from "@/lib/store";
import type { ImMessage, ImThread } from "@/lib/store";

const ISO_NOW = "2026-04-20T09:30:00+08:00";

const seedThreads: ImThread[] = [
  /* === GROUPS · 含 agent 的协作群 ============================ */
  {
    id: "thr_zrgs",
    title: "中锐工商 · 尽调与授信",
    customerId: "cust_zrgs",
    participants: ["u_wangzhe", "u_lihua"],
    lastMessageAt: "2026-04-20T09:18:00+08:00",
    unreadCount: 2,
    kind: "group",
  },
  {
    id: "thr_dingchuan",
    title: "鼎川精密 · 续贷复核",
    customerId: "cust_dingchuan",
    participants: ["u_wangzhe", "u_lihua"],
    lastMessageAt: "2026-04-20T08:52:00+08:00",
    unreadCount: 1,
    kind: "group",
  },
  {
    id: "thr_yunrong",
    title: "云融科技 · 黄色预警跟进",
    customerId: "cust_yunrong",
    participants: ["u_wangzhe", "u_chenkai"],
    lastMessageAt: "2026-04-20T09:02:00+08:00",
    unreadCount: 3,
    kind: "group",
  },
  {
    id: "thr_haiyuan",
    title: "海元供应链 · look-alike 沟通",
    customerId: "cust_haiyuan",
    participants: ["u_wangzhe"],
    lastMessageAt: "2026-04-20T07:46:00+08:00",
    unreadCount: 0,
    kind: "group",
  },
  {
    id: "thr_tongxin",
    title: "同信新材料 · 合规复核",
    customerId: "cust_tongxin",
    participants: ["u_wangzhe", "u_zhoumin"],
    lastMessageAt: "2026-04-19T17:24:00+08:00",
    unreadCount: 0,
    kind: "group",
  },

  /* === DIRECT · 客户经理 ↔ 同事的纯人际私聊（无 agent，无 customer） == */
  {
    id: "dm_lihua",
    title: "李华 · 授信审贷",
    participants: ["u_wangzhe", "u_lihua"],
    lastMessageAt: "2026-04-20T09:25:00+08:00",
    unreadCount: 1,
    kind: "dm",
  },
  {
    id: "dm_chenkai",
    title: "陈凯 · 风险经理",
    participants: ["u_wangzhe", "u_chenkai"],
    lastMessageAt: "2026-04-20T08:40:00+08:00",
    unreadCount: 0,
    kind: "dm",
  },
  {
    id: "dm_zhoumin",
    title: "周敏 · 合规官",
    participants: ["u_wangzhe", "u_zhoumin"],
    lastMessageAt: "2026-04-19T18:10:00+08:00",
    unreadCount: 0,
    kind: "dm",
  },
];

const seedMessages: Record<string, ImMessage[]> = {
  thr_zrgs: [
    {
      id: "msg_zrgs_1",
      threadId: "thr_zrgs",
      from: "u_wangzhe",
      kind: "text",
      content: "中锐这单材料补全了，麻烦 Agent6 先把尽调报告草稿出一版，下午要上会。",
      createdAt: "2026-04-20T08:40:00+08:00",
    },
    {
      id: "msg_zrgs_2",
      threadId: "thr_zrgs",
      from: "report",
      kind: "system_event",
      content: "Agent6 报告 v7.23 — 已完成 7 / 12 章节，待补：合作机构、对外担保、模型卡。",
      refs: { eventId: "evt_seed_report_progress" },
      createdAt: "2026-04-20T09:05:00+08:00",
    },
    {
      id: "msg_zrgs_3",
      threadId: "thr_zrgs",
      from: "u_lihua",
      kind: "text",
      content: "草稿出来后直接 @我，授信侧我先看四维评分。",
      createdAt: "2026-04-20T09:18:00+08:00",
    },
  ],
  thr_dingchuan: [
    {
      id: "msg_dc_1",
      threadId: "thr_dingchuan",
      from: "credit",
      kind: "system_event",
      content: "Agent3 四维评分完成 · 综合 78 / 100，建议授信 3000 万 / 12 个月。",
      refs: { eventId: "evt_seed_credit_done" },
      createdAt: "2026-04-19T17:30:00+08:00",
    },
    {
      id: "msg_dc_2",
      threadId: "thr_dingchuan",
      from: "u_lihua",
      kind: "text",
      content: "续贷条款基本沿用，建议加一条供应链集中度复核。",
      createdAt: "2026-04-20T08:52:00+08:00",
    },
  ],
  thr_yunrong: [
    {
      id: "msg_yr_1",
      threadId: "thr_yunrong",
      from: "alert",
      kind: "system_event",
      content: "Agent4 预警 · 黄色：核心客户应收账款集中度 → 35%（阈值 30%）。",
      refs: { eventId: "evt_seed_alert" },
      createdAt: "2026-04-20T08:45:00+08:00",
    },
    {
      id: "msg_yr_2",
      threadId: "thr_yunrong",
      from: "u_chenkai",
      kind: "text",
      content: "建议把这单转合规复核，看是否触政策红线。",
      createdAt: "2026-04-20T09:02:00+08:00",
    },
  ],
  thr_haiyuan: [
    {
      id: "msg_hy_1",
      threadId: "thr_haiyuan",
      from: "channel",
      kind: "system_event",
      content: "Agent1 找到 12 家相似企业 · 信号匹配度 ≥ 0.72。",
      refs: { eventId: "evt_seed_channel" },
      createdAt: "2026-04-20T07:30:00+08:00",
    },
    {
      id: "msg_hy_2",
      threadId: "thr_haiyuan",
      from: "u_wangzhe",
      kind: "text",
      content: "把第 3、5、7 三家挑出来，先约线下拜访。",
      createdAt: "2026-04-20T07:46:00+08:00",
    },
  ],
  thr_tongxin: [
    {
      id: "msg_tx_1",
      threadId: "thr_tongxin",
      from: "compli",
      kind: "system_event",
      content: "Agent5 合规复核完成 · 无新增冲突点，沿用 Q1 制度版本。",
      refs: { eventId: "evt_seed_compli" },
      createdAt: "2026-04-19T17:24:00+08:00",
    },
  ],
  /* === DM seeds === */
  dm_lihua: [
    {
      id: "msg_dm_lh_1",
      threadId: "dm_lihua",
      from: "u_lihua",
      kind: "text",
      content: "下午上会顺序你定一下，我这边四维评分都看完了。",
      createdAt: "2026-04-20T09:20:00+08:00",
    },
    {
      id: "msg_dm_lh_2",
      threadId: "dm_lihua",
      from: "u_wangzhe",
      kind: "text",
      content: "中锐先讲，鼎川续贷放第二个，云融预警最后留时间讨论。",
      createdAt: "2026-04-20T09:25:00+08:00",
    },
  ],
  dm_chenkai: [
    {
      id: "msg_dm_ck_1",
      threadId: "dm_chenkai",
      from: "u_wangzhe",
      kind: "text",
      content: "云融那单 Agent4 黄色预警，你看转合规复核合不合适？",
      createdAt: "2026-04-20T08:35:00+08:00",
    },
    {
      id: "msg_dm_ck_2",
      threadId: "dm_chenkai",
      from: "u_chenkai",
      kind: "text",
      content: "可以转，先在 dispatch 里 @周敏 一下，我同步把贷后清单更进去。",
      createdAt: "2026-04-20T08:40:00+08:00",
    },
  ],
  dm_zhoumin: [
    {
      id: "msg_dm_zm_1",
      threadId: "dm_zhoumin",
      from: "u_zhoumin",
      kind: "text",
      content: "Q1 制度版本已经在合规库里同步完了，新单一律走 v2026Q1。",
      createdAt: "2026-04-19T18:10:00+08:00",
    },
  ],
};

/** Stage D.2F · live mode flags + typing presence (per im-protocol §4.1). */
export type LiveMode = "seed" | "live" | "live_with_seed_fallback";

interface DispatchState {
  threads: ImThread[];
  messages: Record<string, ImMessage[]>;
  currentThreadId: string | null;
  /** Stage D.2F · "seed" 默认 · API fetch 成功后切 "live" · 失败保 "live_with_seed_fallback" */
  liveMode: LiveMode;
  /** Stage D.2F · WS 连接状态 (用于 UI status pill) */
  wsState: "idle" | "connecting" | "open" | "closed" | "error";
  /** Stage D.2F · per-thread { user_id: expire_ts } typing indicator */
  typingByThread: Record<string, Record<string, number>>;
  selectThread: (id: string | null) => void;
  addMessage: (threadId: string, partial: Omit<ImMessage, "id" | "threadId" | "createdAt">) => ImMessage;
  appendSystemEvent: (
    threadId: string,
    msg: Omit<ImMessage, "id" | "threadId" | "createdAt" | "kind"> & { kind?: ImMessage["kind"] },
  ) => ImMessage;
  clearThread: (threadId: string) => void;
  updateMessage: (
    threadId: string,
    messageId: string,
    patch: Partial<Pick<ImMessage, "content" | "refs">>,
  ) => void;

  /** Stage D.2F · 真后端推过来的消息 · 不重复插（按 id 去重） */
  ingestRemoteMessage: (msg: ImMessage) => void;
  /** Stage D.2F · API fetch 成功后批量替 thread list */
  setRemoteThreads: (threads: ImThread[]) => void;
  /** Stage D.2F · API fetch 历史消息 → 替 thread.messages */
  setThreadMessages: (threadId: string, msgs: ImMessage[]) => void;
  /** Stage D.2F · WebSocket typing 来 / 自维护 typing 用户表 (3s expire) */
  noteTyping: (threadId: string, userId: string) => void;
  /** Stage D.2F · 清过期的 typing presence (3s 后) */
  pruneTyping: () => void;
  /** Stage D.2F · 设 liveMode + wsState · UI 用 */
  setLiveMode: (mode: LiveMode) => void;
  setWsState: (state: DispatchState["wsState"]) => void;
}

const genMsgId = () =>
  `msg_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;

void ISO_NOW; // referenced by seed timestamps; keep symbol for future dynamic clock

/** Stage D.2F · typing presence 过期时间 (per im-protocol §4.1 typing event 短暂) */
const TYPING_EXPIRE_MS = 3_000;

export const useDispatchStore = create<DispatchState>((set, get) => ({
  threads: seedThreads,
  messages: seedMessages,
  currentThreadId: null,
  liveMode: "seed",
  wsState: "idle",
  typingByThread: {},
  selectThread: (id) => {
    set((s) => ({
      currentThreadId: id,
      threads: id
        ? s.threads.map((t) => (t.id === id ? { ...t, unreadCount: 0 } : t))
        : s.threads,
    }));
    if (!id) return;
    const thread = get().threads.find((t) => t.id === id);
    if (thread?.customerId) {
      // 用户点击 thread 是显式动作 → 触发 customer focus（contracts §customer-store）
      useCustomerStore.getState().focus(thread.customerId);
    }
  },
  addMessage: (threadId, partial) => {
    const msg: ImMessage = {
      id: genMsgId(),
      threadId,
      createdAt: new Date().toISOString(),
      ...partial,
    };
    set((s) => ({
      messages: {
        ...s.messages,
        [threadId]: [...(s.messages[threadId] ?? []), msg],
      },
      threads: s.threads.map((t) =>
        t.id === threadId
          ? { ...t, lastMessageAt: msg.createdAt }
          : t,
      ),
    }));
    return msg;
  },
  appendSystemEvent: (threadId, partial) => {
    return get().addMessage(threadId, {
      from: partial.from,
      kind: partial.kind ?? "system_event",
      content: partial.content,
      refs: partial.refs,
    });
  },
  clearThread: (threadId) =>
    set((s) => ({
      messages: { ...s.messages, [threadId]: [] },
    })),
  updateMessage: (threadId, messageId, patch) =>
    set((s) => ({
      messages: {
        ...s.messages,
        [threadId]: (s.messages[threadId] ?? []).map((m) =>
          m.id === messageId ? { ...m, ...patch } : m,
        ),
      },
    })),

  /** Stage D.2F · WebSocket 推消息进 store · 按 id 去重 (post-send 自己已 ingest 过) */
  ingestRemoteMessage: (msg) => {
    if (!msg || !msg.threadId) return;
    set((s) => {
      const existing = s.messages[msg.threadId] ?? [];
      if (existing.some((m) => m.id === msg.id)) return s; // dedup
      return {
        messages: {
          ...s.messages,
          [msg.threadId]: [...existing, msg],
        },
        threads: s.threads.map((t) =>
          t.id === msg.threadId
            ? {
                ...t,
                lastMessageAt: msg.createdAt,
                unreadCount:
                  s.currentThreadId === msg.threadId
                    ? 0
                    : (t.unreadCount ?? 0) + (msg.kind === "system_event" ? 0 : 1),
              }
            : t,
        ),
      };
    });
  },

  /** Stage D.2F · API fetch 成功后替 thread list (保留 currentThreadId 选中态) */
  setRemoteThreads: (next) => {
    set((s) => {
      const stillExists = s.currentThreadId
        ? next.some((t) => t.id === s.currentThreadId)
        : false;
      return {
        threads: next,
        currentThreadId: stillExists ? s.currentThreadId : s.currentThreadId,
      };
    });
  },

  /** Stage D.2F · 替单 thread 的 messages 列 (历史消息 / resync) */
  setThreadMessages: (threadId, msgs) => {
    if (!threadId) return;
    set((s) => ({
      messages: { ...s.messages, [threadId]: [...msgs] },
    }));
  },

  /** Stage D.2F · 收 typing event · 记 user_id + expire_ts */
  noteTyping: (threadId, userId) => {
    if (!threadId || !userId) return;
    const expireAt = Date.now() + TYPING_EXPIRE_MS;
    set((s) => {
      const cur = s.typingByThread[threadId] ?? {};
      return {
        typingByThread: {
          ...s.typingByThread,
          [threadId]: { ...cur, [userId]: expireAt },
        },
      };
    });
  },

  /** Stage D.2F · 清过期 typing entry (UI useEffect 周期调用) */
  pruneTyping: () => {
    const now = Date.now();
    set((s) => {
      const next: Record<string, Record<string, number>> = {};
      let changed = false;
      for (const [tid, presence] of Object.entries(s.typingByThread)) {
        const filtered: Record<string, number> = {};
        for (const [uid, exp] of Object.entries(presence)) {
          if (exp > now) {
            filtered[uid] = exp;
          } else {
            changed = true;
          }
        }
        if (Object.keys(filtered).length > 0) {
          next[tid] = filtered;
        } else if (presence && Object.keys(presence).length > 0) {
          changed = true;
        }
      }
      return changed ? { typingByThread: next } : s;
    });
  },

  setLiveMode: (mode) => set({ liveMode: mode }),
  setWsState: (state) => set({ wsState: state }),
}));

/** 通过 customerId 反查 thread（事件桥用） */
export const findThreadByCustomerId = (customerId: string): ImThread | undefined =>
  useDispatchStore.getState().threads.find((t) => t.customerId === customerId);
