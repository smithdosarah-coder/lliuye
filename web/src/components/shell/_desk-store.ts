/**
 * Desk 本地私有 store — 只管 UI 态，不跨 worktree 共享。
 *
 * 不进红区 (`lib/store/*`)：pinned 集合是用户个人偏好，不影响 Customer 实体；
 * 评审若认为应升入共享 customer-store 再走 Q-NNN 流程。
 *
 * 命名约定：`_` 前缀 + `-store` 后缀，区别于共享 store。
 */
"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type DeskFilter = "all" | "owned" | "shared";

interface DeskState {
  pinned: string[]; // Customer.id[]
  query: string; // 搜索关键字（非持久化 — 刷新即清）
  filter: DeskFilter;
  togglePin: (id: string) => void;
  isPinned: (id: string) => boolean;
  setQuery: (q: string) => void;
  setFilter: (f: DeskFilter) => void;
}

export const useDeskStore = create<DeskState>()(
  persist(
    (set, get) => ({
      pinned: [],
      query: "",
      filter: "all",
      togglePin: (id) =>
        set((s) => ({
          pinned: s.pinned.includes(id)
            ? s.pinned.filter((x) => x !== id)
            : [id, ...s.pinned].slice(0, 12),
        })),
      isPinned: (id) => get().pinned.includes(id),
      setQuery: (q) => set({ query: q }),
      setFilter: (f) => set({ filter: f }),
    }),
    {
      name: "platform.desk.v1",
      // filter 持久；query 每次刷新清空
      partialize: (s) => ({ pinned: s.pinned, filter: s.filter }),
    },
  ),
);
