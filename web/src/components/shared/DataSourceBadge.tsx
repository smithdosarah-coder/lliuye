"use client";

/**
 * DataSourceBadge · 5-enum data_source 显式 trust model 徽章 (Q-054 件 #2 + banner-spec v1.0).
 *
 * 与 ModePill 区别:
 *   - ModePill = 二值 (mock/live) 的"操作切换"控件 (force_mock toggle)
 *   - DataSourceBadge = 5-enum (per shared/sse_envelope canon) 的"结果显示"徽章
 *     · live / cached / mock / mock_forced / mock_fallback 5 路独立色
 *     · 仅显示 · 不可点击 (banner trust model 不允许用户篡改)
 *
 * 颜色 tone 按 _data-source.dataSourceTone:
 *   ok   (live/cached)        → accent 绿
 *   info (mock/mock_forced)   → ink 灰
 *   warn (mock_fallback)      → 黄 (banner-spec rule 1 触发 · 用户必感知)
 */
import {
  type DataSourceKind,
  type DataSourceLabelOptions,
  dataSourceLabel,
  dataSourceProviderHint,
  dataSourceTone,
} from "@/lib/api/_data-source";

export type DataSourceBadgeProps = {
  kind: DataSourceKind;
  /** 提供 provider 时第二行显示具体 source (e.g. "via Tavily") · 给 tooltip 也用 */
  provider?: string;
  /** §3.5.1 #6 数据源 4 Tier · 显示 "Tier N <name>" 副标 (推荐核心理由必带) */
  sourceTier?: 1 | 2 | 3 | 4;
  /** §3.5.1 #6 freshness_days · 显示 "近 N 天" · 仅当 ≥ 0 透出 */
  freshnessDays?: number;
  testId?: string;
  size?: "sm" | "md";
};


export function DataSourceBadge({
  kind,
  provider,
  sourceTier,
  freshnessDays,
  testId = "data-source-badge",
  size = "md",
}: DataSourceBadgeProps) {
  const tone = dataSourceTone(kind);
  const label = dataSourceLabel(kind);
  const opts: DataSourceLabelOptions = { provider, sourceTier, freshnessDays };
  const hint = dataSourceProviderHint(kind, opts);

  /* tone-color tokens · 全 token 走 (不复活 letterpress/--color-brass) */
  const palette: Record<typeof tone, { fg: string; bg: string; border: string; symbol: string }> = {
    ok: {
      fg: "var(--accent)",
      bg: "color-mix(in srgb, var(--accent) 14%, transparent)",
      border: "var(--accent)",
      symbol: "●",
    },
    info: {
      fg: "var(--ink-65)",
      bg: "color-mix(in srgb, var(--ink-14) 50%, transparent)",
      border: "var(--ink-14)",
      symbol: "○",
    },
    warn: {
      fg: "var(--t-alert)",
      bg: "color-mix(in srgb, var(--t-alert) 16%, transparent)",
      border: "var(--t-alert)",
      symbol: "△",
    },
  };
  const c = palette[tone];

  const fontSize = size === "sm" ? 11 : 12;
  const padding = size === "sm" ? "2px 8px" : "4px 10px";

  /* 副标行 · provider / tier · 给 tooltip + 第二行短描述 */
  const subline: string[] = [];
  if (provider) subline.push(`via ${provider}`);
  if (sourceTier !== undefined) subline.push(`Tier ${sourceTier}`);

  return (
    <span
      data-testid={testId}
      data-source={kind}
      data-tone={tone}
      data-provider={provider ?? ""}
      title={hint}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding,
        borderRadius: 12,
        fontSize,
        fontFamily: "var(--mono)",
        fontWeight: 500,
        letterSpacing: ".05em",
        background: c.bg,
        color: c.fg,
        border: `1px solid ${c.border}`,
        whiteSpace: "nowrap",
      }}
    >
      <span aria-hidden>{c.symbol}</span>
      <span>{label}</span>
      {subline.length > 0 && (
        <span
          style={{
            opacity: 0.78,
            fontSize: fontSize - 1,
            paddingLeft: 4,
            borderLeft: `1px solid ${c.border}`,
          }}
        >
          {subline.join(" · ")}
        </span>
      )}
    </span>
  );
}
