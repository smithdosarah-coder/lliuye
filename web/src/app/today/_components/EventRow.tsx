"use client";

/**
 * EventRow · EventTimeline 单行
 *
 * 布局：[MM:SS] [agent 徽章] [文案 + 客户 pill] — mono 时间左缩进, 行色取 --t-<agent>。
 * 老于 10 分钟的条目加 `--faded` class 降低对比度。
 */

import Link from "next/link";

import { useCustomerStore } from "@/lib/store";
import type { AgentEvent } from "@/lib/store";

import { AGENT_LABEL, EVENT_TEXT } from "./event-text";

const FADE_AFTER_MS = 10 * 60_000;

function formatEventTime(iso: string, now: Date): string {
  const d = new Date(iso);
  const diff = now.getTime() - d.getTime();
  if (diff < 60_000) return "刚刚";
  if (diff < FADE_AFTER_MS) return `${Math.floor(diff / 60_000)} 分前`;
  if (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  ) {
    const hh = String(d.getHours()).padStart(2, "0");
    const mm = String(d.getMinutes()).padStart(2, "0");
    return `${hh}:${mm}`;
  }
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${mo}-${day}`;
}

function agentRouteOf(agent: AgentEvent["agent"]): string {
  // event.agent ∈ AgentId，与 /archive/<agent> 路由同名
  return agent;
}

export interface EventRowProps {
  event: AgentEvent;
  customerName?: string;
  now: Date;
}

export function EventRow({ event, customerName, now }: EventRowProps) {
  const focus = useCustomerStore((s) => s.focus);
  const faded =
    now.getTime() - new Date(event.createdAt).getTime() > FADE_AFTER_MS;
  const text = EVENT_TEXT[event.type] ?? event.type;
  const timeLabel = formatEventTime(event.createdAt, now);

  const customerLink = event.customerId && customerName ? (
    <Link
      href={`/archive/${agentRouteOf(event.agent)}?customer=${event.customerId}`}
      onClick={() => focus(event.customerId!)}
      className="event-row__cust"
    >
      {customerName}
    </Link>
  ) : null;

  return (
    <li
      className={`event-row agent-${event.agent}${faded ? " event-row--faded" : ""}`}
    >
      <span className="event-row__time">{timeLabel}</span>
      <span className="event-row__badge">{AGENT_LABEL[event.agent]}</span>
      <span className="event-row__text">
        <span>{text}</span>
        {customerLink}
      </span>
    </li>
  );
}
