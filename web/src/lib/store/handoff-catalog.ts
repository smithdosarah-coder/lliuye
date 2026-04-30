/**
 * Handoff catalog —— 预定义的 Agent → Agent 交接配方。
 *
 * 每个 Agent workspace 根据 current customer + catalog 渲染 "下一步发给…" 的 action 按钮。
 * 选中 recipe → 创建 HandoffTicket → publish handoff.requested 事件 → 进 warroom kanban。
 *
 * 新增 / 修改 recipe 走 RFC（docs/arch/platform-contracts.md §改动流程）。
 */
import type { AgentEvent, AgentId, HandoffTicket } from "./types";

export interface HandoffRecipe {
  id: string;
  fromAgent: AgentId;
  toAgent: AgentId;
  /** 触发场景 —— UI 按钮文案，不做逻辑判定 */
  trigger: string;
  /** 按钮文案（12 字以内） */
  label: string;
  /** hover / 确认对话里的详细说明 */
  description: string;
  /** 从触发事件生成 ticket payload 的函数；如果没有关联事件，取 customerId 即可 */
  buildPayload?: (event?: AgentEvent) => Record<string, unknown>;
  /** 触发事件类型白名单（可选，UI 可据此决定是否高亮推荐） */
  triggerEventTypes?: string[];
  /** 预期紧急度 */
  priority?: "normal" | "urgent";
}

export const HANDOFF_CATALOG: HandoffRecipe[] = [
  {
    id: "channel_to_report",
    fromAgent: "channel",
    toAgent: "report",
    trigger: "锁定 look-alike 候选客户后，发起尽调报告",
    label: "转报告助手",
    description: "把 Agent1 挑中的候选企业清单带入 Agent6，自动新建尽调报告草稿。",
    triggerEventTypes: ["channel.lookalike_picked"],
    priority: "normal",
    buildPayload: (e) => ({ candidateId: e?.payload?.candidateId }),
  },
  {
    id: "report_to_credit",
    fromAgent: "report",
    toAgent: "credit",
    trigger: "报告定稿 → 交审贷官出授信决策",
    label: "送审贷会",
    description:
      "ReportJSON 完整 + QC 通过后，携带证据链进入 Agent3 四维评分 + 授信建议。",
    triggerEventTypes: ["report.completed"],
    priority: "normal",
    buildPayload: (e) => ({
      reportId: e?.payload?.reportId,
      finalized: true,
    }),
  },
  {
    id: "credit_to_report",
    fromAgent: "credit",
    toAgent: "report",
    trigger: "授信打回 → 审贷意见回写报告",
    label: "退回补件",
    description: "把 Agent3 的异议 / 缺陷项回写到 Agent6 报告对应段落，自动打补件提醒。",
    triggerEventTypes: ["credit.decided"],
    priority: "urgent",
    buildPayload: (e) => ({
      reportId: e?.payload?.reportId,
      issues: e?.payload?.issues ?? [],
    }),
  },
  {
    id: "alert_to_compliance",
    fromAgent: "alert",
    toAgent: "compliance",
    trigger: "预警命中 → 合规官复核",
    label: "合规复核",
    description: "Agent4 红/黄预警命中后交 Agent5 合规冲突检查，输出处置建议。",
    triggerEventTypes: ["alert.raised"],
    priority: "urgent",
    buildPayload: (e) => ({
      alertId: e?.payload?.alertId,
      severity: e?.payload?.severity,
    }),
  },
  {
    id: "alert_to_credit",
    fromAgent: "alert",
    toAgent: "credit",
    trigger: "预警触发额度调整建议",
    label: "申请调整额度",
    description: "预警命中后触发 Agent3 重新打分，输出额度缩减 / 提前收回建议。",
    triggerEventTypes: ["alert.raised"],
    priority: "urgent",
    buildPayload: (e) => ({ alertId: e?.payload?.alertId }),
  },
  {
    id: "compliance_to_report",
    fromAgent: "compliance",
    toAgent: "report",
    trigger: "合规冲突 → 报告补章节",
    label: "回写合规意见",
    description: "Agent5 发现制度冲突后，自动在 Agent6 报告对应段落插入合规提示 + 源政策引用。",
    triggerEventTypes: ["compliance.conflict_found"],
    priority: "normal",
    buildPayload: (e) => ({ conflictId: e?.payload?.conflictId }),
  },
];

export const findRecipes = (fromAgent: AgentId): HandoffRecipe[] =>
  HANDOFF_CATALOG.filter((r) => r.fromAgent === fromAgent);

export const findRecipeById = (id: string): HandoffRecipe | undefined =>
  HANDOFF_CATALOG.find((r) => r.id === id);

/**
 * 从 recipe + 事件构造一个 Ticket（不含 id / 时间戳 —— 由 ticket store 填）。
 */
export const buildTicketSkeleton = (
  recipe: HandoffRecipe,
  ctx: {
    customerId: string;
    requestedBy: string;
    assignedTo?: string;
    event?: AgentEvent;
  },
): Omit<HandoffTicket, "id" | "createdAt" | "updatedAt"> => ({
  fromAgent: recipe.fromAgent,
  toAgent: recipe.toAgent,
  customerId: ctx.customerId,
  reason: recipe.trigger,
  payload: recipe.buildPayload?.(ctx.event) ?? {},
  status: "requested",
  requestedBy: ctx.requestedBy,
  assignedTo: ctx.assignedTo,
  triggerEventId: ctx.event?.id,
});
