"use client";

/**
 * HighlightCard — 把正文里的 claim 用浅色块包起来,hover 弹 mini popover。
 *
 * 数据源: EvidenceContext · 按 refId 反查 EvidenceItem。
 *
 * 降级(Task B 硬指标):
 *   - refId 在 evidence_trail 里找不到 → 退回 <span>{children}</span>,不报错,不编造高亮。
 */

import { useMemo, useRef, useState, useCallback, type ReactNode } from "react";
import { useEvidence } from "./EvidenceContext";
import { isLowConfidence, UNFILLED_MARKER_TEXT } from "./types";
import { parseClaims } from "./claimParser";
import { UnfilledMarker } from "./UnfilledMarker";

export interface HighlightCardProps {
  refId: string;
  children: ReactNode;
}

export function HighlightCard({ refId, children }: HighlightCardProps) {
  const ctx = useEvidence();
  const item = useMemo(() => ctx.getByRefId(refId), [ctx, refId]);
  const [hovering, setHovering] = useState(false);
  const hoverTimer = useRef<number | null>(null);

  const openPop = useCallback(() => {
    if (hoverTimer.current !== null) {
      window.clearTimeout(hoverTimer.current);
      hoverTimer.current = null;
    }
    setHovering(true);
  }, []);
  const closePop = useCallback(() => {
    if (hoverTimer.current !== null) window.clearTimeout(hoverTimer.current);
    // 延迟关闭,让鼠标能从 mark 移到 popover 上不丢
    hoverTimer.current = window.setTimeout(() => setHovering(false), 120);
  }, []);

  if (!item) {
    // 降级:后端契约漂移或 ref_id 丢失 → 普通 span,不报错,不编造高亮。
    return <span data-ref-missing={refId}>{children}</span>;
  }

  const low = isLowConfidence(item);
  const pct = Math.round(item.confidence * 100);

  return (
    <mark
      className="ev-highlight"
      data-ref-id={refId}
      data-low-confidence={low ? "true" : "false"}
      onMouseEnter={openPop}
      onMouseLeave={closePop}
      onFocus={openPop}
      onBlur={closePop}
      tabIndex={0}
    >
      {children}
      <span className="ev-highlight-dot" aria-hidden />
      {hovering && (
        <span className="ev-highlight-mini" role="tooltip">
          <span className="ev-highlight-mini-source" title={item.source}>
            {item.source}
          </span>
          <span className="ev-highlight-mini-bar" aria-label={`置信度 ${pct}%`}>
            <span
              className="ev-highlight-mini-bar-fill"
              style={{ width: `${Math.max(4, pct)}%` }}
            />
          </span>
          <span className="ev-highlight-mini-num">{pct}%</span>
        </span>
      )}
    </mark>
  );
}

/**
 * ClaimText — 便捷包装,接受纯文本 + 自动切 [ref:xxx]...[/ref] 锚点。
 *
 * 测试注入:
 *   - 若 `window.__CLAIM_TEST_TEXT__` 有值,优先用它作为 text(只首次渲染生效)。
 *     生产 / 真 SSE 情景不设置此变量,直接用传入 prop。
 */
export interface ClaimTextProps {
  text: string;
  className?: string;
  as?: "p" | "div" | "span";
}

declare global {
  interface Window {
    __CLAIM_TEST_TEXT__?: string;
  }
}

import { useEffect } from "react";

export function ClaimText({ text, className, as = "p" }: ClaimTextProps) {
  const [resolved, setResolved] = useState<string>(text);
  useEffect(() => {
    if (typeof window !== "undefined" && typeof window.__CLAIM_TEST_TEXT__ === "string") {
      setResolved(window.__CLAIM_TEST_TEXT__);
    } else {
      setResolved(text);
    }
  }, [text]);

  const tokens = useMemo(() => parseClaims(resolved), [resolved]);

  const rendered: ReactNode[] = [];
  tokens.forEach((t, i) => {
    if (t.kind === "ref") {
      rendered.push(
        <HighlightCard key={`r-${i}-${t.refId}`} refId={t.refId}>
          {t.content}
        </HighlightCard>
      );
      return;
    }
    // text token · 拆分字面值 "未能自动填写" 为 <UnfilledMarker inline>
    if (!t.content.includes(UNFILLED_MARKER_TEXT)) {
      rendered.push(<span key={`t-${i}`}>{t.content}</span>);
      return;
    }
    const parts = t.content.split(UNFILLED_MARKER_TEXT);
    parts.forEach((seg, j) => {
      if (seg) rendered.push(<span key={`t-${i}-${j}`}>{seg}</span>);
      if (j < parts.length - 1) {
        rendered.push(
          <UnfilledMarker
            key={`u-${i}-${j}`}
            fieldName={`inline_${i}_${j}`}
            reason="qc_blocked"
            inline
          />
        );
      }
    });
  });

  // 无锚点 + 无 token → 直接返回原文(防守)
  const content = rendered.length > 0 ? rendered : resolved;

  if (as === "span") return <span className={className}>{content}</span>;
  if (as === "div") return <div className={className}>{content}</div>;
  return <p className={className}>{content}</p>;
}
