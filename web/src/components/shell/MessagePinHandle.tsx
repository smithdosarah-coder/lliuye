"use client";

/**
 * MessagePinHandle · 对话消息钉选抓手
 *
 * 与 PanelPinHandle 同构：放在 .rpt-msg 内绝对定位，hover 浮现。
 * dragstart 双 MIME 写入：
 *   - CARD_PIN_MIME（白板字符条 · kind="ticket"） → Whiteboard drop
 *   - PANEL_PIN_MIME（面板缩略 · kind="panel" · blurb=content 摘要） → PanelCanvas drop
 * 再加 text/plain 兜底给 composer 读取（textarea 原生 drop 会吃 text/plain，
 * composer 的 custom onDrop 优先走 CARD/PANEL，text/plain 只是兜底）。
 *
 * 设计取舍：
 *   - 把 grip 做成独立 button 节点；消息文本本身不 draggable，避免吃选中/复制
 *   - hover 才浮现（见 shell.css .mp-grip & .rpt-msg:hover > .mp-grip）
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

export interface MessagePinHandleProps {
  /** 对话全局唯一 id · 约定 `${agentKey}:msg:${msg.id}`。 */
  id: string;
  /** 主标题（一般取消息内容，已由调用方做短截断）。 */
  title: string;
  /** 副标题（发言人 · 时间戳）。 */
  subtitle: string;
  /** 6 Agent 功能色 var 名。 */
  accentVar?: string;
  /** 回跳用 agentKey（channel / report / ...）。 */
  agentKey?: string;
  /** 回跳 href（默认 workspace 根路由）。 */
  href?: string;
  /** 消息原文完整字串，作为 panel 缩略 blurb / card 副标题兜底。 */
  fullText?: string;
}

export function MessagePinHandle(props: MessagePinHandleProps) {
  function onDragStart(e: DragEvent<HTMLButtonElement>) {
    const panelPayload: PanelPinPayload = {
      id: props.id,
      kind: "panel",
      title: props.title,
      subtitle: props.subtitle,
      accentVar: props.accentVar,
      agentKey: props.agentKey,
      href: props.href,
      blurb: props.fullText ?? props.title,
    };
    const cardPayload: CardPinPayload = {
      id: `msg:${props.id}`,
      kind: "ticket",
      title: props.title,
      subtitle: props.subtitle,
      href: props.href ?? "#",
      accentVar: props.accentVar,
    };
    try {
      e.dataTransfer.setData(PANEL_PIN_MIME, JSON.stringify(panelPayload));
      e.dataTransfer.setData(CARD_PIN_MIME, JSON.stringify(cardPayload));
      e.dataTransfer.setData("text/plain", props.title);
      e.dataTransfer.effectAllowed = "copy";
    } catch {
      /* 受限沙盒吞 */
    }
  }

  const style: CSSProperties = props.accentVar
    ? ({ "--mp-grip-accent": `var(${props.accentVar})` } as CSSProperties)
    : {};

  return (
    <button
      type="button"
      className="mp-grip"
      style={style}
      draggable
      onDragStart={onDragStart}
      aria-label={`拖拽以引用消息 · ${props.title}`}
      title="拖到白板 / 画布 / 输入框"
    >
      <span className="mp-grip-dots" aria-hidden>
        ⋮⋮
      </span>
    </button>
  );
}
