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
  {
    id: "thr_zrgs",
    title: "中锐工商 · 尽调与授信",
    customerId: "cust_zrgs",
    participants: ["u_wangzhe", "u_lihua"],
    lastMessageAt: "2026-04-20T09:18:00+08:00",
    unreadCount: 2,
  },
  {
    id: "thr_dingchuan",
    title: "鼎川精密 · 续贷复核",
    customerId: "cust_dingchuan",
    participants: ["u_wangzhe", "u_lihua"],
    lastMessageAt: "2026-04-20T08:52:00+08:00",
    unreadCount: 1,
  },
  {
    id: "thr_yunrong",
    title: "云融科技 · 黄色预警跟进",
    customerId: "cust_yunrong",
    participants: ["u_wangzhe", "u_chenkai"],
    lastMessageAt: "2026-04-20T09:02:00+08:00",
    unreadCount: 3,
  },
  {
    id: "thr_haiyuan",
    title: "海元供应链 · look-alike 沟通",
    customerId: "cust_haiyuan",
    participants: ["u_wangzhe"],
    lastMessageAt: "2026-04-20T07:46:00+08:00",
    unreadCount: 0,
  },
  {
    id: "thr_tongxin",
    title: "同信新材料 · 合规复核",
    customerId: "cust_tongxin",
    participants: ["u_wangzhe", "u_zhoumin"],
    lastMessageAt: "2026-04-19T17:24:00+08:00",
    unreadCount: 0,
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
};

interface DispatchState {
  threads: ImThread[];
  messages: Record<string, ImMessage[]>;
  currentThreadId: string | null;
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
}

const genMsgId = () =>
  `msg_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;

void ISO_NOW; // referenced by seed timestamps; keep symbol for future dynamic clock

export const useDispatchStore = create<DispatchState>((set, get) => ({
  threads: seedThreads,
  messages: seedMessages,
  currentThreadId: null,
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
}));

/** 通过 customerId 反查 thread（事件桥用） */
export const findThreadByCustomerId = (customerId: string): ImThread | undefined =>
  useDispatchStore.getState().threads.find((t) => t.customerId === customerId);
