"use client";

import { useEffect } from "react";

import { useEventBus } from "@/lib/store";
import type { AgentEvent, AgentEventType } from "@/lib/store";

import {
  findThreadByCustomerId,
  useDispatchStore,
} from "../_store/dispatch-store";
import { agentMeta } from "./agent-meta";
import { encodeHandoff } from "./handoff-payload";

/**
 * 把 lib/store/event-bus 的 Agent 事件桥接成 dispatch view 内的消息。
 *
 * - report.completed / credit.decided / alert.raised 等 → system_event
 * - handoff.requested → 一张 pending 的 HandoffCard（仅当事件来源不是 dispatch 自身）
 * - handoff.accepted → system_event "X 接手了 Y"
 * - 跳过：comment.added (composer 自己已 addMessage) + 任何 payload.source 以 "dispatch." 开头的事件
 *
 * 不持久化 —— 刷新即清空（与 event-bus 一致；真实审计走后端）。
 */
const BRIDGE_TYPES: AgentEventType[] = [
  "report.completed",
  "report.drafted",
  "credit.decided",
  "credit.redline_hit",
  "channel.lookalike_picked",
  "alert.raised",
  "alert.handled",
  "compli.conflict_found",
  "riskctrl.dsl_deployed",
  "handoff.requested",
  "handoff.accepted",
];

export function EventBridge() {
  useEffect(() => {
    const unsub = useEventBus.getState().subscribeTo(BRIDGE_TYPES, (event) => {
      handleEvent(event);
    });
    return unsub;
  }, []);
  return null;
}

function handleEvent(event: AgentEvent) {
  if (isLocalSource(event)) return;
  if (!event.customerId) return;
  const thread = findThreadByCustomerId(event.customerId);
  if (!thread) return;
  const dispatch = useDispatchStore.getState();

  if (event.type === "handoff.requested") {
    const payload = event.payload as Record<string, unknown>;
    dispatch.addMessage(thread.id, {
      from: event.agent,
      kind: "handoff_card",
      content: encodeHandoff({
        status: "pending",
        recipeId: typeof payload?.recipeId === "string" ? payload.recipeId : undefined,
        toAgent: event.agent,
        customerId: event.customerId,
        reason:
          typeof payload?.reason === "string"
            ? payload.reason
            : `${agentMeta(event.agent).name} 请求交接`,
        ticketId:
          typeof payload?.ticketId === "string" ? payload.ticketId : event.id,
      }),
      refs: { eventId: event.id },
    });
    return;
  }

  dispatch.appendSystemEvent(thread.id, {
    from: event.agent,
    content: humanize(event),
    refs: { eventId: event.id },
  });
}

function isLocalSource(event: AgentEvent): boolean {
  const src = (event.payload as { source?: unknown })?.source;
  return typeof src === "string" && src.startsWith("dispatch.");
}

function humanize(event: AgentEvent): string {
  const meta = agentMeta(event.agent);
  const payload = event.payload as Record<string, unknown>;
  switch (event.type) {
    case "report.completed":
      return `${meta.name} · 报告完成${payload?.reportId ? `（${payload.reportId}）` : ""}。`;
    case "report.drafted":
      return `${meta.name} · 报告草稿已保存${payload?.section ? `（${payload.section}）` : ""}。`;
    case "credit.decided":
      return `${meta.name} · 授信决策已出${payload?.amount ? `，建议额度 ${payload.amount}` : ""}。`;
    case "credit.redline_hit":
      return `${meta.name} · 红线命中${payload?.rule ? `：${payload.rule}` : ""}。`;
    case "channel.lookalike_picked":
      return `${meta.name} · 已锁定 look-alike 候选${payload?.count ? `（${payload.count} 家）` : ""}。`;
    case "alert.raised":
      return `${meta.name} · 预警触发${payload?.severity ? `（${payload.severity}）` : ""}：${payload?.reason ?? "—"}`;
    case "alert.handled":
      return `${meta.name} · 预警已处置${payload?.disposition ? `（${payload.disposition}）` : ""}。`;
    case "compli.conflict_found":
      return `${meta.name} · 合规冲突${payload?.policy ? `：${payload.policy}` : ""}。`;
    case "riskctrl.dsl_deployed":
      return `${meta.name} · DSL 规则上线${payload?.ruleId ? `（${payload.ruleId}）` : ""}。`;
    case "handoff.accepted":
      return `${meta.name} · 已接手交接${payload?.recipeId ? `（${payload.recipeId}）` : ""}。`;
    default:
      return `${meta.name} · ${event.type}`;
  }
}
