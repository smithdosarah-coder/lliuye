/**
 * CustomerDrawer 本地 UI 态 —— 只管"当前打开哪个客户"。
 *
 * 不持久化（刷新自然关闭）。不与红区 customer-store 合并：后者管客户实体，
 * 本 store 管"抽屉是否开着"—— 是两码事。
 */
"use client";

import { create } from "zustand";

interface DrawerState {
  openId: string | null;
  open: (id: string) => void;
  close: () => void;
}

export const useCustomerDrawerStore = create<DrawerState>((set) => ({
  openId: null,
  open: (id) => set({ openId: id }),
  close: () => set({ openId: null }),
}));
