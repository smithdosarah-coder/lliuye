/**
 * PanelCanvas store — 右侧画布。
 *
 * 与 Whiteboard（左侧 pinboard）并列但语义不同：
 *   - Whiteboard 钉的是 **entity**（agent tile / ticket / customer），行状罗列。
 *   - PanelCanvas 钉的是 **panel 本身**（RadarPanel / CandidatesPanel 等气泡），
 *     以缩略图（thumbnail）形式保留视觉快照。
 *
 * 为什么不合进 whiteboard-store：
 *   1. 用户明确指定「右侧画布」——左右语义独立可见
 *   2. 渲染方式不同：白板 = 文本列，画布 = 缩略图网格
 *   3. 生命周期不同：panel 钉选与当前 workspace 耦合（快照时刻的视觉），
 *      entity pin 是跨 view 的纯导航锚
 *
 * 持久化：localStorage `platform.panel-canvas.v1`。刷新保留 pins，不保留 open。
 */
"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

/** 目前仅一种 kind，预留扩展（未来可能加 "chart" / "doc" snapshot）。 */
export type PanelPinKind = "panel";

/** 画布 3 区 (visual-v3/P3 · 2026-04-23 · plan L119)：
 *   insight  · 固定洞察 · 置顶持久 · 复盘参考
 *   analysis · 当前分析 · 默认新 pin 去这里 · 工作中的快照
 *   action   · 建议动作 · 准备执行的事项
 */
export type PanelZone = "insight" | "analysis" | "action";

export const DEFAULT_ZONE: PanelZone = "analysis";

export interface PanelPin {
  /** 跨 workspace 唯一，约定 `${agentKey}:${panelKey}:${Date.now()}` 由 drop 源组装。 */
  id: string;
  kind: PanelPinKind;
  /** 主标题（e.g. "营销优先级雷达"）。 */
  title: string;
  /** 副标题（e.g. "获客 · 厦门瑞鼎"），可空。 */
  subtitle?: string;
  /** 6 Agent 功能色 CSS var 名（如 `--t-channel`），缩略图左条着色。 */
  accentVar?: string;
  /** 源 workspace 的 agent key（channel / credit / ...），用于点击跳回。 */
  agentKey?: string;
  /** 点击缩略图跳回的目标路径（通常是 workspace 根路由 + query hash）。 */
  href?: string;
  /** 简短内容摘要 1-2 行（不是完整 snapshot，避免 storage 膨胀）。 */
  blurb?: string;
  /** 画布分区 · 默认 analysis（plan P3a）· 由 drag-between-zones 调整 */
  zone?: PanelZone;
  /** ISO 时间，按钉选顺序排序（新在前）。 */
  pinnedAt: string;
}

interface PanelCanvasState {
  pins: PanelPin[];
  open: boolean;
  pin: (item: Omit<PanelPin, "pinnedAt"> & { pinnedAt?: string }) => void;
  unpin: (id: string) => void;
  /** 改 pin 所在 zone（P3c drag-between-zones 消费） */
  setZone: (id: string, zone: PanelZone) => void;
  toggle: () => void;
  setOpen: (b: boolean) => void;
  clear: () => void;
}

export const usePanelCanvasStore = create<PanelCanvasState>()(
  persist(
    (set, get) => ({
      pins: [],
      open: false,
      pin: (item) => {
        const existing = get().pins;
        if (existing.some((p) => p.id === item.id)) return;
        const next: PanelPin = {
          ...item,
          /* 2026-04-23 P3a · 老 payload 无 zone 字段兜底 analysis（当前分析） */
          zone: item.zone ?? DEFAULT_ZONE,
          pinnedAt: item.pinnedAt ?? new Date().toISOString(),
        };
        set({ pins: [next, ...existing].slice(0, 36) });
      },
      unpin: (id) => set((s) => ({ pins: s.pins.filter((p) => p.id !== id) })),
      setZone: (id, zone) =>
        set((s) => ({
          pins: s.pins.map((p) => (p.id === id ? { ...p, zone } : p)),
        })),
      toggle: () => set((s) => ({ open: !s.open })),
      setOpen: (b) => set({ open: b }),
      clear: () => set({ pins: [] }),
    }),
    {
      name: "platform.panel-canvas.v1",
      partialize: (s) => ({ pins: s.pins }),
    },
  ),
);

/** 拖拽 MIME 常量 —— panel 气泡作 drag source 时用。 */
export const PANEL_PIN_MIME = "application/x-panel-pin";

/** drag payload 结构（store 侧自己打 pinnedAt）。 */
export type PanelPinPayload = Omit<PanelPin, "pinnedAt">;
