/**
 * AgentKey ↔ AgentId 映射
 *
 * Per Q-042.B (PM 拍板 2026-04-29) · agent5 单 id = `compliance` 全栈 ·
 * AgentKey 与 AgentId 现完全同值 · 本映射保留为 identity 以维持 import API
 * 稳定 (consumer code 不需改)。
 */
import type { AgentKey } from "@/lib/agents";
import type { AgentId } from "@/lib/store/types";

export const AGENT_KEY_TO_ID: Record<AgentKey, AgentId> = {
  report: "report",
  credit: "credit",
  channel: "channel",
  alert: "alert",
  compliance: "compliance",
  riskctrl: "riskctrl",
};
