/**
 * AgentKey ↔ AgentId 映射
 *
 * `AgentKey`（前端 6 agent tile / route · lib/agents.ts）与 `AgentId`
 * （共享 store 契约 · lib/store/types.ts）绝大多数同值，仅
 * `"compliance"` → `"compli"`。把映射集中在这里避免散落。
 */
import type { AgentKey } from "@/lib/agents";
import type { AgentId } from "@/lib/store/types";

export const AGENT_KEY_TO_ID: Record<AgentKey, AgentId> = {
  report: "report",
  credit: "credit",
  channel: "channel",
  alert: "alert",
  compliance: "compli",
  riskctrl: "riskctrl",
};
