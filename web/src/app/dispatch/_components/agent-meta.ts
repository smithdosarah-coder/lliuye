import type { AgentId } from "@/lib/store";
import { AGENT_IDS } from "@/lib/store";

const META: Record<AgentId, { name: string; role: string; glyph: string; tint: string }> = {
  report: { name: "Agent6 报告", role: "材料 → 报告", glyph: "六", tint: "var(--t-report)" },
  credit: { name: "Agent3 授信", role: "评分 / 红线", glyph: "三", tint: "var(--t-credit)" },
  channel: { name: "Agent1 获客", role: "look-alike", glyph: "一", tint: "var(--t-channel)" },
  alert: { name: "Agent4 预警", role: "贷后扫描", glyph: "四", tint: "var(--t-alert)" },
  compliance: { name: "Agent5 合规", role: "政策事件", glyph: "五", tint: "var(--t-compli)" },
  riskctrl: { name: "Agent2 风控", role: "DSL / 回测", glyph: "二", tint: "var(--t-riskctrl)" },
};

export const agentMeta = (id: AgentId) => META[id];

export const isAgentId = (s: string): s is AgentId =>
  (AGENT_IDS as readonly string[]).includes(s);
