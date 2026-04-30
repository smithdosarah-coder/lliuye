/**
 * Platform-shell v2 shared types
 *
 * RED ZONE: 修改字段需走 RFC（docs/arch/platform-contracts.md §改动流程）
 * 允许在 domain 内扩展自有类型（如 dispatch/types.ts），不允许 inline 改本文件。
 */

export type AgentId =
  | "report" // Agent6
  | "credit" // Agent3
  | "channel" // Agent1
  | "alert" // Agent4
  | "compliance" // Agent5
  | "riskctrl"; // Agent2

export const AGENT_IDS: readonly AgentId[] = [
  "report",
  "credit",
  "channel",
  "alert",
  "compliance",
  "riskctrl",
] as const;

export type Role =
  | "rm" // 客户经理
  | "credit_officer" // 审贷员
  | "compliance_officer" // 合规官
  | "risk_manager" // 风险经理
  | "admin";

export interface User {
  id: string;
  name: string;
  role: Role;
  team: string; // 华东 / 总部风险管理部 / ...
  avatar?: string; // emoji or initial
}

export type CustomerStage =
  | "lead" // 线索
  | "intake" // 材料采集中
  | "report" // 报告撰写中
  | "credit" // 授信审批中
  | "monitoring" // 贷后监控
  | "alert" // 预警中
  | "closed"; // 结清/拒绝

export interface Customer {
  id: string;
  name: string; // 全称
  shortName?: string; // 俗称 / abbr
  industry?: string; // 制造业 / 批发零售 / ...
  region?: string; // 长三角 / 珠三角 / ...
  tags: string[];
  amount?: number; // 授信金额（万元），未决用 undefined
  stage: CustomerStage;
  assignedTo: string; // User.id
  sharedWith: string[]; // User.id[]，协同人员
  lastActivityAt: string; // ISO
  createdAt: string;
}

/**
 * Agent 事件 — 所有 Agent workspace 完成关键步骤时 publish 到 event-bus。
 * 消费者：today 聚合、dispatch IM 流、warroom 看板、audit log。
 */
export type AgentEventType =
  | "report.completed" // Agent6 报告完成
  | "report.drafted" // Agent6 草稿保存
  | "credit.decided" // Agent3 授信决定
  | "credit.redline_hit" // Agent3 红线命中
  | "channel.lookalike_picked" // Agent1 相似企业选中
  | "alert.raised" // Agent4 预警触发
  | "alert.handled" // Agent4 预警处置
  | "compliance.conflict_found" // Agent5 合规冲突
  | "riskctrl.dsl_deployed" // Agent2 规则上线
  | "handoff.requested" // 跨 Agent handoff
  | "handoff.accepted"
  | "comment.added"; // IM 留言

export interface AgentEvent {
  id: string;
  type: AgentEventType;
  agent: AgentId;
  customerId?: string;
  actor: string; // User.id
  payload: Record<string, unknown>;
  createdAt: string; // ISO
  /** 相关联的 handoff / ticket id，跨 Agent 追踪用 */
  correlationId?: string;
}

/**
 * Handoff ticket — 一个 Agent 完成工作后交给下一个 Agent。
 * 生命周期：requested → accepted → completed。
 * 看板（warroom）基于 ticket 展示 4 列 kanban。
 */
export type HandoffStatus =
  | "requested"
  | "accepted"
  | "in_progress"
  | "completed"
  | "rejected";

export interface HandoffTicket {
  id: string;
  fromAgent: AgentId;
  toAgent: AgentId;
  customerId: string;
  reason: string; // 简短描述
  payload: Record<string, unknown>; // 上游产出（ReportJSON / ScoreJSON / ...）
  status: HandoffStatus;
  requestedBy: string; // User.id
  assignedTo?: string; // User.id
  createdAt: string;
  updatedAt: string;
  /** 追溯到触发 handoff 的 AgentEvent.id */
  triggerEventId?: string;
}

/**
 * IM 消息 — dispatch view 的基本单元。
 * Thread = 一个客户 / 一个 handoff 的连续对话。
 */
export interface ImMessage {
  id: string;
  threadId: string; // 一般是 customerId 或 ticketId
  from: string; // User.id | "system" | AgentId
  kind:
    | "text"
    | "system_event"
    | "handoff_card"
    | "file"
    | "agent_output"
    | "pin_ref"; // Stage D.2F · additive · Q-037 precedent · 与 backend insert_message kind 集合一致 (im-protocol §5.3)
  content: string; // 文本正文 or JSON 序列化
  refs?: {
    eventId?: string;
    ticketId?: string;
    fileUrl?: string;
    /** Stage D.2F additive · pin_ref kind 用 · 画布 → composer drop 形成的缩略图卡 */
    agentId?: string;
    href?: string;
    fullText?: string;
    thumbDataUrl?: string;
    /** Stage D.2F additive · agent_output kind 用 · 跨 agent run 引用 */
    agentRunId?: string;
  };
  createdAt: string;
}

export interface ImThread {
  id: string;
  title: string;
  customerId?: string;
  participants: string[]; // User.id[]
  lastMessageAt: string;
  unreadCount: number;
  /** "group" = 含 agent 的协作群；"dm" = 客户经理 ↔ 同事的纯人际私聊。
   *  仅用于 ThreadList 视觉分类，不影响后端契约。Optional 兼容旧数据。 */
  kind?: "group" | "dm";
}

/**
 * Permission action — RBAC 判定的细粒度动作。
 */
export type PermissionAction =
  | { kind: "agent.access"; agent: AgentId }
  | { kind: "handoff.create"; from: AgentId; to: AgentId }
  | { kind: "handoff.accept"; agent: AgentId }
  | { kind: "customer.assign" }
  | { kind: "audit.view" };
