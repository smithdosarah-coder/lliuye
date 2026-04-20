/**
 * 事件类型 → 中文文案映射 · 供 PriorityQueue / EventTimeline 共用
 */
import type { AgentEventType, AgentId } from "@/lib/store";

export const EVENT_TEXT: Record<AgentEventType, string> = {
  "report.completed": "报告生成完成",
  "report.drafted": "报告草稿已保存",
  "credit.decided": "授信决定已出",
  "credit.redline_hit": "命中红线",
  "channel.lookalike_picked": "已选中 look-alike",
  "alert.raised": "触发预警",
  "alert.handled": "预警已处置",
  "compli.conflict_found": "合规冲突待判",
  "riskctrl.dsl_deployed": "风控规则上线",
  "handoff.requested": "发起 handoff",
  "handoff.accepted": "接收 handoff",
  "comment.added": "新留言",
};

export const AGENT_LABEL: Record<AgentId, string> = {
  report: "报告",
  credit: "授信",
  channel: "获客",
  alert: "预警",
  compli: "合规",
  riskctrl: "风控",
};
