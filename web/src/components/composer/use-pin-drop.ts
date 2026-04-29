"use client";

/**
 * use-pin-drop · archive workspace composer 共享拖拽 drop 钩子
 *
 * 治本背景：dispatch ComposerBar 已实现 PANEL_PIN_MIME / CARD_PIN_MIME drop +
 * pin_ref message 创建。5 个 archive workspace 的 inline composer 之前 4 个
 * 没有 drop 处理，textarea 原生 drop 把 text/plain（= 钉源 title 兜底）插入
 * 成 URL 文本（之前的 bug），剩 1 个（Channel）做了 `@引用:<title>` 插入但
 * 各自重复实现。
 *
 * 本钩子统一行为：
 *   1. dragOver 在 `pin/*` MIME 出现时 preventDefault，防 textarea 原生处理；
 *   2. drop 解析 PANEL_PIN_MIME → CARD_PIN_MIME → text/plain（依次降级）
 *      取出 title；
 *   3. 通过 onPin 回调把 title + thumbDataUrl 交给上层 composer 处理（一般
 *      做插入 textarea + 渲染缩略卡 / 添加本地 pin_ref message）。
 *
 * 不强制 archive composer 必须有 message store —— 调用方决定怎么消费。
 */

import { useCallback, useState } from "react";
import type { DragEvent } from "react";
import { CARD_PIN_MIME } from "@/lib/store/whiteboard-store";
import { PANEL_PIN_MIME } from "@/lib/store/panel-canvas-store";
import { PIN_THUMB_MIME } from "@/components/shell/pin-thumb";

export interface PinDropPayload {
  title: string;
  subtitle?: string;
  agentKey?: string;
  href?: string;
  thumbDataUrl: string;
}

export interface PinDropHandlers<E extends HTMLElement = HTMLDivElement> {
  dropHover: boolean;
  onDragEnter: (e: DragEvent<E>) => void;
  onDragOver: (e: DragEvent<E>) => void;
  onDragLeave: (e: DragEvent<E>) => void;
  onDrop: (e: DragEvent<E>) => void;
}

function hasPin<E extends HTMLElement>(e: DragEvent<E>): boolean {
  const ts = Array.from(e.dataTransfer.types);
  return ts.includes(PANEL_PIN_MIME) || ts.includes(CARD_PIN_MIME);
}

export function usePinDrop<E extends HTMLElement = HTMLDivElement>(
  onPin: (payload: PinDropPayload) => void,
): PinDropHandlers<E> {
  const [dropHover, setDropHover] = useState(false);

  const onDragEnter = useCallback((e: DragEvent<E>) => {
    if (!hasPin(e)) return;
    e.preventDefault();
    setDropHover(true);
  }, []);

  const onDragOver = useCallback((e: DragEvent<E>) => {
    if (!hasPin(e)) return;
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = "copy";
    setDropHover(true);
  }, []);

  const onDragLeave = useCallback((e: DragEvent<E>) => {
    const node = e.currentTarget;
    const next = e.relatedTarget as Node | null;
    if (!next || !node.contains(next)) setDropHover(false);
  }, []);

  const onDrop = useCallback(
    (e: DragEvent<E>) => {
      if (!hasPin(e)) return;
      e.preventDefault();
      e.stopPropagation();
      setDropHover(false);
      const rawPanel = e.dataTransfer.getData(PANEL_PIN_MIME);
      const rawCard = e.dataTransfer.getData(CARD_PIN_MIME);
      const thumbDataUrl = e.dataTransfer.getData(PIN_THUMB_MIME) || "";
      let title = "";
      let subtitle: string | undefined;
      let agentKey: string | undefined;
      let href: string | undefined;
      try {
        if (rawPanel) {
          const p = JSON.parse(rawPanel) as {
            title?: string;
            subtitle?: string;
            blurb?: string;
            agentKey?: string;
            href?: string;
          };
          title = p.title ?? "";
          subtitle = p.subtitle ?? p.blurb;
          agentKey = p.agentKey;
          href = p.href;
        } else if (rawCard) {
          const c = JSON.parse(rawCard) as {
            title?: string;
            subtitle?: string;
            href?: string;
          };
          title = c.title ?? "";
          subtitle = c.subtitle;
          href = c.href;
        }
      } catch {
        title = e.dataTransfer.getData("text/plain") || "";
      }
      if (!title) return;
      onPin({ title, subtitle, agentKey, href, thumbDataUrl });
    },
    [onPin],
  );

  return { dropHover, onDragEnter, onDragOver, onDragLeave, onDrop };
}
