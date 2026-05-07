"use client";

/**
 * LiveFallbackBanner · banner-spec v1.0 §2 规则 1+2 共形 banner.
 *
 * 替代 6 workspace 各自 inline 实现 (channel/alert/compliance/report/riskctrl 各写一遍 ·
 * Q-054 件 #2 SSOT 化收敛).
 *
 * 三档 (per banner-spec rule 1+2):
 *   - error  (LiveFailError 红)   live 调用 4xx/5xx/network · 用户必看到原因 + 重试
 *   - warn   (mock_fallback 黄)   后端自动降级 · 用户必感知 trust model 一级降级
 *   - info   (mock/mock_forced 蓝/灰) 用户主动选演示 · 提示当前不是真后端
 *   - null   (live/cached)        无 banner · UI 干净
 *
 * 渲染策略由 caller 决定: 一般 caller pattern:
 *   if (LiveFailError) → tone="error" + retry
 *   else if (kind === "mock_fallback") → tone="warn" (auto)
 *   else if (kind === "mock" || kind === "mock_forced") → tone="info" + 切换真后端按钮
 *   else null
 */
import { type DataSourceKind, dataSourceTone } from "@/lib/api/_data-source";
import type { LiveFailError } from "@/lib/api/_live";

export type LiveFallbackBannerProps = {
  /** 当前 done envelope 的 data_source · null 表示 stream 未完成 (caller 一般传 kind) */
  kind?: DataSourceKind;
  /** LiveFailError 实例 · live 调用失败时必传 · 优先级最高 (覆盖 kind tone). */
  error?: LiveFailError | null;
  /** 后端 stage event 透传的 warning 文案 (per banner-spec rule 2 · backend stage status="warning") */
  streamWarning?: string;
  /** 重试 callback · error/warn tone 时 caller 实现 · 不实现则不显示重试按钮 */
  onRetry?: () => void;
  /** "切换真后端" callback · mock/mock_forced 时 caller 实现 (例: setForceMock(false)) */
  onSwitchToLive?: () => void;
  /** Agent 显示名 · e.g. "Agent1 获客" / "Agent6 报告" · 用于 banner 文案 */
  agentLabel: string;
  testId?: string;
};


export function LiveFallbackBanner({
  kind,
  error,
  streamWarning,
  onRetry,
  onSwitchToLive,
  agentLabel,
  testId = "live-fallback-banner",
}: LiveFallbackBannerProps) {
  /* 优先级: error > stream warning > kind. */
  let tone: "error" | "warn" | "info" | null = null;
  let message = "";

  if (error) {
    tone = "error";
    const code = error.status > 0 ? `HTTP ${error.status}` : "network/SSE";
    message = `⚠️ 后端 ${agentLabel} 调用失败 (${code}) · 当前显 fallback 演示数据`;
  } else if (streamWarning) {
    tone = "warn";
    message = streamWarning;
  } else if (kind === "mock_fallback") {
    tone = "warn";
    message = `⚠️ ${agentLabel} 主路径降级 · 当前显演示数据 · 检查 Tavily / API key / 网络后重试`;
  } else if (kind === "mock_forced") {
    tone = "info";
    message = `示例数据 (DEMO 模式) · 当前不联后端 · 切真实输入运行真后端`;
  } else if (kind === "mock") {
    tone = "info";
    message = `示例数据 (training mode) · 切真实输入 → 真后端`;
  } else {
    return null;
  }

  /* tone-token 映射 · 全走 token (不复活 letterpress/--color-brass) */
  const palette = {
    error: {
      bg: "color-mix(in srgb, var(--t-alert) 14%, transparent)",
      border: "var(--t-alert)",
      fg: "var(--ink-90)",
    },
    warn: {
      bg: "color-mix(in srgb, #f5b400 14%, transparent)",
      border: "#f5b400",
      fg: "var(--ink-90)",
    },
    info: {
      bg: "color-mix(in srgb, var(--ink-14) 36%, transparent)",
      border: "var(--ink-14)",
      fg: "var(--ink-65)",
    },
  } as const;
  const c = palette[tone];

  return (
    <div
      data-testid={testId}
      data-tone={tone}
      data-kind={kind ?? ""}
      role={tone === "error" ? "alert" : "status"}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "8px 14px",
        margin: "0 0 8px 0",
        borderRadius: "var(--r-md, 12px)",
        background: c.bg,
        border: `1px solid ${c.border}`,
        color: c.fg,
        fontSize: 13,
        lineHeight: 1.5,
      }}
    >
      <span style={{ flex: 1 }}>{message}</span>
      {error && error.endpoint && (
        <span
          style={{
            fontFamily: "var(--mono)",
            fontSize: 11,
            opacity: 0.65,
          }}
        >
          {error.endpoint}
        </span>
      )}
      {onSwitchToLive && (tone === "info") && (
        <button
          type="button"
          onClick={onSwitchToLive}
          style={{
            padding: "4px 10px",
            borderRadius: 999,
            background: "var(--accent)",
            color: "var(--paper)",
            border: "none",
            fontSize: 12,
            cursor: "pointer",
          }}
          data-testid={`${testId}-switch-live`}
        >
          切真后端
        </button>
      )}
      {onRetry && (tone === "error" || tone === "warn") && (
        <button
          type="button"
          onClick={onRetry}
          style={{
            padding: "4px 10px",
            borderRadius: 999,
            background: "transparent",
            color: c.border,
            border: `1px solid ${c.border}`,
            fontSize: 12,
            cursor: "pointer",
          }}
          data-testid={`${testId}-retry`}
        >
          重试
        </button>
      )}
    </div>
  );
}
