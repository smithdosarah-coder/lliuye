"use client";

import { byUserId } from "@/lib/store";
import type { ImMessage } from "@/lib/store";

import { agentMeta, isAgentId } from "./agent-meta";
import { formatTimestamp } from "./time";

export function MessageBubble({ message }: { message: ImMessage }) {
  const author = resolveAuthor(message.from);
  return (
    <article className={`dpx-msg ${author.kind}`}>
      <span
        className="dpx-msg-avatar"
        style={author.tint ? { backgroundColor: author.tint } : undefined}
      >
        {author.glyph}
      </span>
      <div className="dpx-msg-body">
        <header className="dpx-msg-meta">
          <span className="nm">{author.name}</span>
          <span className="role">{author.role}</span>
          <span className="ts">{formatTimestamp(message.createdAt)}</span>
        </header>
        <div className="dpx-msg-text">{message.content}</div>
      </div>
    </article>
  );
}

type AuthorView = {
  kind: "user" | "agent" | "system";
  name: string;
  role: string;
  glyph: string;
  tint?: string;
};

function resolveAuthor(from: string): AuthorView {
  if (from === "system") {
    return { kind: "system", name: "系统", role: "platform", glyph: "·" };
  }
  if (isAgentId(from)) {
    const meta = agentMeta(from);
    return {
      kind: "agent",
      name: meta.name,
      role: meta.role,
      glyph: meta.glyph,
      tint: meta.tint,
    };
  }
  const u = byUserId(from);
  if (!u) {
    return { kind: "user", name: from, role: "未知", glyph: "?" };
  }
  return {
    kind: "user",
    name: u.name,
    role: u.team,
    glyph: u.avatar ?? u.name.slice(0, 1),
  };
}
