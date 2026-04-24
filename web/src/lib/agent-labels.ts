/**
 * Agent key → 展示名映射
 *
 * PanelCanvas 缩略卡 eyebrow / 白板字符条 / 未来所有"回跳到对应 agent"的
 * UI 锚点统一走这里，避免散落硬编。key 与路由 segment + agentKey 对齐。
 */

export const AGENT_LABELS: Record<string, string> = {
  channel: "获客 · Agent1",
  report: "报告 · Agent6",
  credit: "授信 · Agent3",
  alert: "预警 · Agent4",
  compliance: "合规 · Agent5",
  riskctrl: "风控 · Agent2",
};

export function agentLabel(key?: string): string {
  if (!key) return "SNAPSHOT";
  return AGENT_LABELS[key] ?? key.toUpperCase();
}
