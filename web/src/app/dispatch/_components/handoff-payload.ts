/**
 * handoff_card 消息序列化辅助
 *
 * ImMessage.content 是 string；handoff_card 把结构化字段以 JSON 编码到 content，
 * UI 解析后渲染。这避免给共享 ImMessage 加新字段（保 contracts 红区不变）。
 */
import type { AgentId } from "@/lib/store";

export interface HandoffCardPayload {
  status: "pending" | "accepted" | "rejected";
  recipeId?: string;
  fromAgent?: AgentId;
  toAgent?: AgentId;
  customerId?: string;
  reason?: string;
  ticketId?: string;
  source?: string;
}

export const encodeHandoff = (p: HandoffCardPayload): string => JSON.stringify(p);

export const decodeHandoff = (raw: string): HandoffCardPayload => {
  try {
    const parsed = JSON.parse(raw) as Partial<HandoffCardPayload>;
    return {
      status: parsed.status ?? "pending",
      recipeId: parsed.recipeId,
      fromAgent: parsed.fromAgent,
      toAgent: parsed.toAgent,
      customerId: parsed.customerId,
      reason: parsed.reason,
      ticketId: parsed.ticketId,
      source: parsed.source,
    };
  } catch {
    return { status: "pending", reason: raw };
  }
};
