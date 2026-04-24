"use client";

/**
 * UnfilledMarker — 后端 QC Blocker 拦截的字段 / 证据不足的字段 → 显式渲染"未能自动填写"。
 *
 * CLAUDE.md §12 硬红线:字段填不了就标"未能自动填写",绝不 fallback 成 "0" / "" / "-"。
 * 比编一个看起来对的数字更有价值。
 *
 * 两种用法:
 *   A) 字段级 — workspace render 字段时 check `useEvidence().isUnfilled(fieldName)`,命中则挂 <UnfilledMarker>
 *   B) 正文级 — 后端正文里的字面值 "未能自动填写" 由 MarkedText 自动替换为组件(带 hover tooltip)
 */

import { useEvidence } from "./EvidenceContext";
import { UNFILLED_MARKER_TEXT, type UnfilledReason } from "./types";
import "./unfilled.css";

export interface UnfilledMarkerProps {
  fieldName: string;
  reason?: UnfilledReason;
  /** 可选 · 显式标签文案覆盖(默认"未能自动填写") */
  label?: string;
  /** 可选 · 供字段内嵌时紧凑渲染(无字段名前缀) */
  inline?: boolean;
}

const REASON_TIP: Record<UnfilledReason, string> = {
  qc_blocked: "QC 拦截",
  no_evidence: "证据不足",
  conflict: "证据冲突",
  unknown: "未能自动填写",
};

export function UnfilledMarker({
  fieldName,
  reason = "unknown",
  label = UNFILLED_MARKER_TEXT,
  inline = false,
}: UnfilledMarkerProps) {
  const tooltip = REASON_TIP[reason] ?? REASON_TIP.unknown;
  const className = `ev-unfilled${inline ? " ev-unfilled--inline" : ""}`;
  const commonProps = {
    className,
    "data-field-name": fieldName,
    "data-reason": reason,
    "aria-label": `${fieldName}: ${label}`,
    title: `${label} · ${tooltip}`,
  };
  const body = (
    <>
      <span className="ev-unfilled-bar" aria-hidden />
      <span className="ev-unfilled-label">{label}</span>
      <span className="ev-unfilled-help" aria-hidden>?</span>
    </>
  );
  if (inline) return <span {...commonProps}>{body}</span>;
  return <div {...commonProps}>{body}</div>;
}

/**
 * 字段级便捷包装 — 若 fieldName 在 unfilled_fields 中命中则渲染 Marker,否则渲染 children。
 *
 * 使用场景: workspace 在渲染单个字段值时套一层,自动根据 context 决定渲染"值"还是"未能自动填写"。
 */
export interface UnfilledGuardProps {
  fieldName: string;
  reason?: UnfilledReason;
  children: React.ReactNode;
}

export function UnfilledGuard({ fieldName, reason, children }: UnfilledGuardProps) {
  const { isUnfilled } = useEvidence();
  if (isUnfilled(fieldName)) {
    return <UnfilledMarker fieldName={fieldName} reason={reason ?? "qc_blocked"} inline />;
  }
  return <>{children}</>;
}

/**
 * UnfilledFields — 把 EvidenceContext 里全部 unfilled_fields 渲染成一排 <UnfilledMarker>。
 *
 * 给 workspace 底部 "未能自动填写的字段" 区块用。若 unfilledFields 为空 → 不渲染。
 */
export interface UnfilledFieldsProps {
  label?: string;
  reason?: UnfilledReason;
}

export function UnfilledFields({
  label = "未能自动填写的字段",
  reason = "qc_blocked",
}: UnfilledFieldsProps) {
  const { unfilledFields, getUnfilledReason } = useEvidence();
  if (unfilledFields.length === 0) return null;
  return (
    <section className="ev-unfilled-list" aria-label={label}>
      <span className="ev-unfilled-list-label">{label}</span>
      {unfilledFields.map((f) => (
        <UnfilledMarker
          key={f}
          fieldName={f}
          reason={getUnfilledReason(f) ?? reason}
        />
      ))}
    </section>
  );
}

/**
 * 正文级替换 — 把 text 里的字面值 "未能自动填写" 全部替换成 <UnfilledMarker inline>。
 * 给 ClaimText 或任意 markdown-ish 正文复用。
 */
export function splitUnfilledLiteral(text: string): Array<
  { kind: "text"; content: string } | { kind: "unfilled"; index: number }
> {
  if (!text || !text.includes(UNFILLED_MARKER_TEXT)) {
    return [{ kind: "text", content: text ?? "" }];
  }
  const out: Array<{ kind: "text"; content: string } | { kind: "unfilled"; index: number }> = [];
  const parts = text.split(UNFILLED_MARKER_TEXT);
  parts.forEach((part, i) => {
    if (part) out.push({ kind: "text", content: part });
    if (i < parts.length - 1) out.push({ kind: "unfilled", index: i });
  });
  return out;
}
