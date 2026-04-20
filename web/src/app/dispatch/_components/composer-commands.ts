/**
 * Composer 快捷命令注册表 + 解析器
 *
 * 命令在 SlashMenu 提示，由 ComposerBar 调用。
 * /run agent6 cust_zrgs   → 调起 Agent workspace
 * /handoff <recipeId>      → 在当前 thread 插入 handoff_card 占位
 * /assign <userId>         → 在当前 thread 插入 system_event（assigned）
 * /clear                   → 清空当前 thread 消息
 */
import type { AgentId, CustomerStage } from "@/lib/store";

export type SlashCommandKey = "run" | "handoff" | "assign" | "clear";

export interface SlashCommandDef {
  key: SlashCommandKey;
  label: string;
  hint: string;
  template: string;
  example: string;
}

export const SLASH_COMMANDS: SlashCommandDef[] = [
  {
    key: "run",
    label: "/run",
    hint: "调起一个 Agent workspace",
    template: "/run ",
    example: "/run agent6 cust_zrgs",
  },
  {
    key: "handoff",
    label: "/handoff",
    hint: "向下一个 Agent 发交接",
    template: "/handoff ",
    example: "/handoff report_to_credit",
  },
  {
    key: "assign",
    label: "/assign",
    hint: "把对话指给某人",
    template: "/assign ",
    example: "/assign u_lihua",
  },
  {
    key: "clear",
    label: "/clear",
    hint: "清空当前对话（仅本地）",
    template: "/clear",
    example: "/clear",
  },
];

/** 把用户输入的 agent 别名（agent6 / report）规范成 AgentId */
const AGENT_ALIAS_TO_ID: Record<string, AgentId> = {
  agent1: "channel",
  agent2: "riskctrl",
  agent3: "credit",
  agent4: "alert",
  agent5: "compli",
  agent6: "report",
  channel: "channel",
  riskctrl: "riskctrl",
  credit: "credit",
  alert: "alert",
  compli: "compli",
  report: "report",
};

export const resolveAgentAlias = (raw: string): AgentId | null =>
  AGENT_ALIAS_TO_ID[raw.trim().toLowerCase()] ?? null;

/** 客户阶段 → 默认 Agent，给 comment.added 事件的 agent 字段托底 */
export const stageToAgent = (stage: CustomerStage | undefined): AgentId => {
  switch (stage) {
    case "lead":
    case "intake":
      return "channel";
    case "report":
      return "report";
    case "credit":
      return "credit";
    case "alert":
    case "monitoring":
      return "alert";
    case "closed":
      return "compli";
    default:
      return "report";
  }
};

export interface ParsedSlash {
  cmd: SlashCommandKey | "unknown";
  raw: string;
  args: string[];
}

export const parseSlash = (input: string): ParsedSlash | null => {
  const trimmed = input.trim();
  if (!trimmed.startsWith("/")) return null;
  const parts = trimmed.slice(1).split(/\s+/).filter(Boolean);
  const head = parts[0]?.toLowerCase();
  if (!head) return { cmd: "unknown", raw: trimmed, args: [] };
  const known = SLASH_COMMANDS.find((c) => c.key === head);
  return {
    cmd: known ? known.key : "unknown",
    raw: trimmed,
    args: parts.slice(1),
  };
};
