"use client";

import { byUserId } from "@/lib/store";
import type { ImMessage } from "@/lib/store";
import { MessagePinHandle } from "@/components/shell/MessagePinHandle";

import { agentMeta, isAgentId } from "./agent-meta";
import { formatTimestamp } from "./time";

function truncate(s: string, n: number): string {
  const flat = s.replace(/\s+/g, " ").trim();
  return flat.length > n ? `${flat.slice(0, n - 1)}…` : flat;
}

export function MessageBubble({ message }: { message: ImMessage }) {
  const author = resolveAuthor(message.from);
  const isAgent = isAgentId(message.from);
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
      {/* F-008 · 拖柄 hover 浮现 · 拖到画布 = 缩略图卡片 (PANEL_PIN_MIME) · 不是 url 链接 */}
      <MessagePinHandle
        id={`dispatch:msg:${message.id}`}
        title={truncate(message.content, 42)}
        subtitle={`${author.name} · ${author.role} · ${formatTimestamp(message.createdAt)}`}
        agentKey={isAgent ? message.from : undefined}
        href="/dispatch"
        fullText={message.content}
      />
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
