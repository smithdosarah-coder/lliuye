"use client";

/**
 * PanelPinHandle · 气泡钉选抓手
 *
 * 放在任意 `.rpt-panel`（或 position:relative 的气泡容器）内，绝对定位到
 * 右上角。用户只能从这个抓手发起 drag，不是整块 panel —— 这样可以保留
 * panel 内部的 resize handle / 子元素点击 / 输入框等原生交互，不冲突。
 *
 * 拖到右侧 PanelCanvas → 序列化为 PANEL_PIN_MIME payload → pin 成缩略图。
 * 拖到其它位置（shell-views 中央）→ AppShell onDragOver 允许，onDrop noop。
 *
 * 设计取舍：
 *   - 不对整 panel 加 draggable=true（会吃掉内部拖拽/选择/resize）
 *   - 不用 CSS ::before pseudo（无法真正 draggable）
 *   - 不用全局 dragstart delegation（无法 scope 到抓手）
 *   → 用真实 DOM 节点 + dragstart handler 最稳
 */

import type { CSSProperties, DragEvent } from "react";
import {
  PANEL_PIN_MIME,
  type PanelPinPayload,
} from "@/lib/store/panel-canvas-store";
import {
  CARD_PIN_MIME,
  type CardPinPayload,
} from "@/lib/store/whiteboard-store";

export interface PanelPinHandleProps {
  /** 全局唯一 pin id —— 约定 `${agentKey}:${panelKey}`，同源重复 drop 会被 store 去重。 */
  id: string;
  /** 主标题（e.g. "营销优先级雷达"）。 */
  title: string;
  subtitle?: string;
  /** 6 Agent 功能色 CSS var 名（如 "--t-channel"）。 */
  accentVar?: string;
  /** workspace 层 agent key（用于点击缩略回跳）。 */
  agentKey?: string;
  /** 回跳 href（默认 workspace 根路由）。 */
  href?: string;
  /** 1-2 行摘要，显示在缩略图卡片下方。 */
  blurb?: string;
}

export function PanelPinHandle(props: PanelPinHandleProps) {
  function onDragStart(e: DragEvent<HTMLButtonElement>) {
    const payload: PanelPinPayload = {
      id: props.id,
      kind: "panel",
      title: props.title,
      subtitle: props.subtitle,
      accentVar: props.accentVar,
      agentKey: props.agentKey,
      href: props.href,
      blurb: props.blurb,
    };
    // 白板语义映射：panel 气泡落到 .rpt-panel:ticket 的字符条形态，href
    // 兜底到 workspace 根路由（白板项点击需要有目的地）。
    const cardPayload: CardPinPayload = {
      id: `panel:${props.id}`,
      kind: "ticket",
      title: props.title,
      subtitle: props.subtitle ?? props.blurb ?? "面板",
      href: props.href ?? "#",
      accentVar: props.accentVar,
    };
    try {
      e.dataTransfer.setData(PANEL_PIN_MIME, JSON.stringify(payload));
      e.dataTransfer.setData(CARD_PIN_MIME, JSON.stringify(cardPayload));
      e.dataTransfer.setData("text/plain", props.title);
      e.dataTransfer.effectAllowed = "copy";
    } catch {
      /* setData 在某些受限沙盒下抛错，吞掉即可 */
    }
  }

  const style: CSSProperties = props.accentVar
    ? ({ "--pp-grip-accent": `var(${props.accentVar})` } as CSSProperties)
    : {};

  return (
    <button
      type="button"
      className="pp-grip"
      style={style}
      draggable
      onDragStart={onDragStart}
      aria-label={`拖拽以固定到画布 · ${props.title}`}
      title="拖到右侧画布 · 保留为缩略图"
    >
      <span className="pp-grip-dots" aria-hidden>
        ⋮⋮
      </span>
      <span className="pp-grip-lbl" aria-hidden>
        钉
      </span>
    </button>
  );
}
