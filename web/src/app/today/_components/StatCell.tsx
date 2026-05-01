"use client";

/**
 * StatCell · MorningBrief 内部统计格（蜂腰/Hero-meta 风）
 * 视觉对齐 mockup `.hero-meta .kv.big` — label + 大字 + 单位
 * - Task A · platform-today
 *
 * F1 (V4 plan · Phase B-1) · vnum span 加 .num className · 接 Tabular Figures
 * (font-variant-numeric: tabular-nums lining-nums) · 数字等宽避免抖动。
 */

import type { ReactNode } from "react";

export interface StatCellProps {
  label: string;
  value: ReactNode;
  unit?: string;
  hint?: string;
}

export function StatCell({ label, value, unit, hint }: StatCellProps) {
  return (
    <span className="kv big" title={hint}>
      <span className="k">{label}</span>
      <span className="v">
        <span className="vnum num">{value}</span>
        {unit ? <span className="vunit">{unit}</span> : null}
      </span>
    </span>
  );
}
