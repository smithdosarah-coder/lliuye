"use client";

/**
 * EvidencePopover — 点击条目弹出原文片段 + 出处链接。
 *
 * 交互:
 *   - open 由父组件控制(trail 负责开关)
 *   - 点 backdrop / Esc 关闭
 *   - source 是 pdf 时 href 带 #page=N
 */

import { useEffect, useRef } from "react";
import type { EvidenceItem } from "./types";
import { buildSourceHref, isLowConfidence, isPdfSource } from "./types";

export interface EvidencePopoverProps {
  item: EvidenceItem;
  open: boolean;
  onClose(): void;
}

export function EvidencePopover({ item, open, onClose }: EvidencePopoverProps) {
  const popRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    function onClick(e: MouseEvent) {
      const target = e.target as Node | null;
      if (popRef.current && target && !popRef.current.contains(target)) {
        onClose();
      }
    }
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onClick);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousedown", onClick);
    };
  }, [open, onClose]);

  if (!open) return null;

  const href = buildSourceHref(item);
  const low = isLowConfidence(item);
  const pct = Math.round(item.confidence * 100);

  return (
    <div
      ref={popRef}
      className="ev-popover"
      role="dialog"
      aria-label={`证据 · ${item.source}`}
      data-low-confidence={low ? "true" : "false"}
    >
      <div className="ev-popover-head">
        <span className="ev-popover-source" title={item.source}>
          {item.source}
        </span>
        <span className="ev-popover-confidence" aria-label={`置信度 ${pct}%`}>
          <span className="ev-popover-confbar">
            <span
              className="ev-popover-confbar-fill"
              style={{ width: `${Math.max(4, pct)}%` }}
            />
          </span>
          <span className="ev-popover-confnum">{pct}%</span>
        </span>
      </div>
      <blockquote className="ev-popover-snippet">{item.snippet}</blockquote>
      <div className="ev-popover-meta">
        {typeof item.meta?.page === "number" && (
          <span className="ev-popover-meta-chip">第 {item.meta.page} 页</span>
        )}
        {item.meta?.paragraph_id && (
          <span className="ev-popover-meta-chip">§ {item.meta.paragraph_id}</span>
        )}
        {item.meta?.year && (
          <span className="ev-popover-meta-chip">{String(item.meta.year)}</span>
        )}
        {item.meta?.entity && (
          <span className="ev-popover-meta-chip">{String(item.meta.entity)}</span>
        )}
      </div>
      <div className="ev-popover-foot">
        <code className="ev-popover-refid">ref:{item.ref_id}</code>
        {href ? (
          <a
            className="ev-popover-link"
            href={href}
            target={isPdfSource(item.source) ? "_blank" : undefined}
            rel="noopener noreferrer"
          >
            打开出处 →
          </a>
        ) : (
          <span className="ev-popover-link ev-popover-link--disabled" aria-disabled>
            无可跳转链接
          </span>
        )}
      </div>
    </div>
  );
}
