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
  /** 提供 onToggle 时变 button · 用户可点切 mock/live mode (PM 5/6 反馈 #2) */
  onToggle?: (nextForceMock: boolean) => void;
  /** 当前 forceMock state · onToggle 用 */
  forceMock?: boolean;
}

export function ModePill({
  isLive,
  testId = "mode-pill",
  size = "md",
  onToggle,
  forceMock,
}: ModePillProps) {
  const fontSize = size === "sm" ? 11 : 12;
  const interactive = typeof onToggle === "function";

  const baseStyle: React.CSSProperties = {
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
    cursor: interactive ? "pointer" : "default",
  };

  const tooltipText = interactive
    ? forceMock
      ? "当前 强制 MOCK · 点击切换 · 尝试连真后端"
      : isLive
      ? "当前 LIVE · 真后端 · 点击切换 · 切回演示数据"
      : "当前 MOCK 演示 · 后端未触发 · 点击切换 · 强制锁定 mock"
    : isLive
    ? "LIVE · 真后端 SSE 数据"
    : "MOCK · 演示数据 · 不联后端";

  const labelText = forceMock ? "MOCK 强制" : isLive ? "LIVE 真接" : "MOCK 演示";
  const symbolText = forceMock ? "◇" : isLive ? "●" : "○";

  if (interactive) {
    return (
      <button
        type="button"
        data-testid={testId}
        data-mode={isLive ? "live" : "mock"}
        data-force-mock={forceMock ? "yes" : "no"}
        title={tooltipText}
        onClick={() => onToggle!(!forceMock)}
        style={baseStyle}
      >
        <span aria-hidden>{symbolText}</span>
        <span>{labelText}</span>
      </button>
    );
  }

  return (
    <div
      data-testid={testId}
      data-mode={isLive ? "live" : "mock"}
      title={tooltipText}
      style={baseStyle}
    >
      <span aria-hidden>{symbolText}</span>
      <span>{labelText}</span>
    </div>
  );
}
