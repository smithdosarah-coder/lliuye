/**
 * Panel Layout store — 自由拖排（free-panels）模式下的位置/尺寸/层级。
 *
 * 开关：`body[data-free-panels="true"]` 时，每个 .rpt-panel 可被拖动、拉伸、
 *       点击置顶、双击 head 回位。默认不开（UI toggle 暂未引入 · identity
 *       说「用 localStorage key 或 body dataset 调试即可」）。
 *
 * Key 约定：`${agentKey}::${panelIndex}`（由 FreePanelLayer 统一分配到
 *           .rpt-panel[data-panel-id]）。跨刷新靠 persist 恢复。
 *
 * 持久化：localStorage `platform.panel-layout.v1`。与 whiteboard / panel-canvas
 *         的 key 空间独立不冲突（前缀 `platform.panel-layout`，与 identity
 *         要求的 `panel-layout/` 前缀一致）。
 */
"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface PanelBox {
  /** 绝对定位左/上（px，相对定位父容器）。 */
  x: number;
  y: number;
  /** 拉伸后 width/height（px，未改过则 undefined = 走 CSS 初始 min-*）。 */
  w?: number;
  h?: number;
  /** 置顶层级。用户点击任一 panel → zTop+1。 */
  z: number;
}

interface PanelLayoutState {
  /** `${agentKey}::${panelId}` → PanelBox。 */
  panels: Record<string, PanelBox>;
  /** 全局递增 z 计数；赋给被点击 panel 的 z 后自增。 */
  zTop: number;
  setPos: (key: string, x: number, y: number) => void;
  setSize: (key: string, w: number, h: number) => void;
  bringToFront: (key: string) => void;
  reset: (key: string) => void;
  /** 删除某 agent 所有 entries（前缀 `${agent}::`）· 画布模式下关画布时调用。 */
  clearAgent: (agent: string) => void;
  resetAll: () => void;
}

export const usePanelLayoutStore = create<PanelLayoutState>()(
  persist(
    (set, get) => ({
      panels: {},
      zTop: 10,
      setPos: (key, x, y) => {
        const cur = get().panels[key];
        set({
          panels: {
            ...get().panels,
            [key]: { x, y, w: cur?.w, h: cur?.h, z: cur?.z ?? 10 },
          },
        });
      },
      setSize: (key, w, h) => {
        const cur = get().panels[key];
        set({
          panels: {
            ...get().panels,
            [key]: {
              x: cur?.x ?? 0,
              y: cur?.y ?? 0,
              w,
              h,
              z: cur?.z ?? 10,
            },
          },
        });
      },
      bringToFront: (key) => {
        const zTop = get().zTop + 1;
        const cur = get().panels[key];
        set({
          zTop,
          panels: {
            ...get().panels,
            [key]: { x: cur?.x ?? 0, y: cur?.y ?? 0, w: cur?.w, h: cur?.h, z: zTop },
          },
        });
      },
      reset: (key) => {
        const next = { ...get().panels };
        delete next[key];
        set({ panels: next });
      },
      clearAgent: (agent) => {
        const prefix = `${agent}::`;
        const next: Record<string, PanelBox> = {};
        for (const [k, v] of Object.entries(get().panels)) {
          if (!k.startsWith(prefix)) next[k] = v;
        }
        set({ panels: next });
      },
      resetAll: () => set({ panels: {}, zTop: 10 }),
    }),
    {
      name: "platform.panel-layout.v1",
      partialize: (s) => ({ panels: s.panels, zTop: s.zTop }),
    },
  ),
);
