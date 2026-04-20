"use client";

import type { ImMessage } from "@/lib/store";

import { agentMeta, isAgentId } from "./agent-meta";
import { formatTimestamp } from "./time";

export function SystemEventCard({ message }: { message: ImMessage }) {
  const meta = isAgentId(message.from)
    ? agentMeta(message.from)
    : { name: "系统", role: "platform", glyph: "·", tint: "var(--ink-48)" };
  return (
    <article
      className="dpx-event"
      style={{ borderLeftColor: meta.tint }}
    >
      <span className="dpx-event-tag" style={{ color: meta.tint }}>
        {meta.glyph} · {meta.name}
      </span>
      <div className="dpx-event-body">{message.content}</div>
      <span className="dpx-event-time">{formatTimestamp(message.createdAt)}</span>
    </article>
  );
}
