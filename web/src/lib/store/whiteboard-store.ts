/**
 * Whiteboard store — 左侧白板（pinboard）状态。
 *
 * 定位：平台 shell 级 UI 偏好（与 Desk 抽屉并列），保存用户拖拽上来的
 * 功能卡（archive agent tile / warroom ticket / 未来可扩 dispatch thread
 * 等）。不是客户/工单实体的红区 state，是用户个人桌面。
 *
 * 持久化：localStorage `platform.whiteboard.v1`。刷新保留，换用户不互通
 * （按键 key 空间共用，跨用户 demo 场景由调用方负责清理）。
 *
 * 命名约定：`-store` 后缀，与 _desk-store 的私有 UI store 平级，但因为
 * 涉及跨 view（archive / warroom）生产、多路消费，放 `lib/store/` 下便
 * 于从 workspace 组件直接 import（而不是私有 shell 组件目录）。
 */
"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

/** 一个白板 pin 的数据结构 —— 最小可视化所需，不冗余原实体。 */
export type WhiteboardPinKind = "agent" | "ticket" | "customer";

export interface WhiteboardPin {
  /** 跨 kind 唯一 —— 约定 `${kind}:${originId}` 由调用方组装。 */
  id: string;
  kind: WhiteboardPinKind;
  title: string;
  subtitle: string;
  /** 点击跳转的目标路径。 */
  href: string;
  /** 6 Agent 功能色 CSS var 名（如 `--t-channel`），用于左侧 rail 着色；可空。 */
  accentVar?: string;
  /** ISO 时间，用于按 pin 先后排序（新在前）。 */
  pinnedAt: string;
}

interface WhiteboardState {
  pins: WhiteboardPin[];
  open: boolean;
  /** 去重：已有同 id 则 noop。新 pin 插最前。 */
  pin: (item: Omit<WhiteboardPin, "pinnedAt"> & { pinnedAt?: string }) => void;
  unpin: (id: string) => void;
  toggle: () => void;
  setOpen: (b: boolean) => void;
  clear: () => void;
}

export const useWhiteboardStore = create<WhiteboardState>()(
  persist(
    (set, get) => ({
      pins: [],
      open: false,
      pin: (item) => {
        const existing = get().pins;
        if (existing.some((p) => p.id === item.id)) return; // dedupe noop
        const next: WhiteboardPin = {
          ...item,
          pinnedAt: item.pinnedAt ?? new Date().toISOString(),
        };
        set({ pins: [next, ...existing].slice(0, 48) });
      },
      unpin: (id) => set((s) => ({ pins: s.pins.filter((p) => p.id !== id) })),
      toggle: () => set((s) => ({ open: !s.open })),
      setOpen: (b) => set({ open: b }),
      clear: () => set({ pins: [] }),
    }),
    {
      name: "platform.whiteboard.v1",
      // open 状态不持久（刷新默认收起，避免挡新访客）；pins 持久。
      partialize: (s) => ({ pins: s.pins }),
    },
  ),
);

/** MIME 常量，AppShell / tile / ticket 共用。 */
export const CARD_PIN_MIME = "application/x-card-pin";

/** 拖拽 payload —— 不带 pinnedAt（store 自己打时间戳）。 */
export type CardPinPayload = Omit<WhiteboardPin, "pinnedAt">;
