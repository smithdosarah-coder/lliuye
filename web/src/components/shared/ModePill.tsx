"use client";

/**
 * ModePill · MOCK / LIVE 数据源 visible badge
 *
 * PM bug #4 P2 fix · 5 workspace 一致性 · 用户视觉看清当前数据源
 * (compliance Sprint 4 D3 已加 inline · channel/credit/alert/report/riskctrl 用此 component)
 */

interface ModePillProps {
  isLive: boolean;
  testId?: string;
  size?: "sm" | "md";
}

export function ModePill({ isLive, testId = "mode-pill", size = "md" }: ModePillProps) {
  const fontSize = size === "sm" ? 11 : 12;
  return (
    <div
      data-testid={testId}
      data-mode={isLive ? "live" : "mock"}
      title={isLive ? "LIVE · 真后端 SSE 数据" : "MOCK · 演示数据 · 不联后端"}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        padding: size === "sm" ? "2px 8px" : "4px 10px",
        borderRadius: 12,
        fontSize,
        fontFamily: "var(--mono)",
        fontWeight: 500,
        letterSpacing: ".05em",
        background: isLive
          ? "color-mix(in srgb, var(--accent) 14%, transparent)"
          : "color-mix(in srgb, var(--ink-14) 50%, transparent)",
        color: isLive ? "var(--accent)" : "var(--ink-65)",
        border: `1px solid ${isLive ? "var(--accent)" : "var(--ink-14)"}`,
      }}
    >
      <span aria-hidden>{isLive ? "●" : "○"}</span>
      <span>{isLive ? "LIVE 真接" : "MOCK 演示"}</span>
    </div>
  );
}
