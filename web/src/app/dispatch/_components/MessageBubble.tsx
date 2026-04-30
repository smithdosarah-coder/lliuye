"use client";

import { byUserId } from "@/lib/store";
import type { ImMessage } from "@/lib/store";
import { MessagePinHandle } from "@/components/shell/MessagePinHandle";
import { buildPinThumbDataUrl } from "@/components/shell/pin-thumb";

import { agentMeta, isAgentId } from "./agent-meta";
import { formatTimestamp } from "./time";

function truncate(s: string, n: number): string {
  const flat = s.replace(/\s+/g, " ").trim();
  return flat.length > n ? `${flat.slice(0, n - 1)}…` : flat;
}

/* #2 · 2026-04-27 · 复用 archive wc-msg 微信气泡样式 (channel/report 已用此设计 · dispatch 之前用 dpx-msg 老 grid · 不一致)
   author.kind: user/agent/system → wc-msg variant: user/ai/system
   CSS 在 dispatch-im.css (global · archive 已有 .v-archive scope 高 specificity 不冲突) */
const KIND_TO_WC: Record<"user" | "agent" | "system", string> = {
  user: "user",
  agent: "ai",
  system: "system",
};

export function MessageBubble({ message }: { message: ImMessage }) {
  const author = resolveAuthor(message.from);
  const isAgent = isAgentId(message.from);
  const wc = KIND_TO_WC[author.kind];
  return (
    <div className={`wc-msg wc-msg--${wc}`}>
      <div
        className={`wc-msg-avatar wc-msg-avatar--${wc}`}
        style={
          author.tint
            ? { backgroundColor: author.tint, borderColor: author.tint }
            : undefined
        }
        aria-hidden
      >
        {author.glyph}
      </div>
      <div className={`wc-msg-bubble wc-msg-bubble--${wc}`}>
        {message.kind === "pin_ref" ? (
          <PinRefThumbnail message={message} />
        ) : (
          <span className="wc-msg-bubble-text">{message.content}</span>
        )}
      </div>
      <div className={`wc-msg-foot wc-msg-foot--${wc}`}>
        <span className="wc-msg-author-name">{author.name}</span>
        <span className="wc-msg-author-role">{author.role}</span>
        <span className="wc-msg-at">{formatTimestamp(message.createdAt)}</span>
      </div>
      {/* F-008 · 拖柄 hover 浮现 · 拖到画布 = 缩略图卡片 (PANEL_PIN_MIME) */}
      <MessagePinHandle
        id={`dispatch:msg:${message.id}`}
        title={truncate(message.content, 42)}
        subtitle={`${author.name} · ${author.role} · ${formatTimestamp(message.createdAt)}`}
        agentKey={isAgent ? message.from : undefined}
        href="/dispatch"
        fullText={message.content}
      />
    </div>
  );
}

/* Stage D.2F · pin_ref kind · 画布 → composer drop 形成的缩略图卡 (im-protocol §7.2)
   显示 缩略图 + 标题 + agent 标签 · 不显 raw URL · href 用 hover tooltip
   · 治本 fix (W-FIX2-Bpin · 2026-04-29)：drag source 始终带 thumbDataUrl;
     若历史消息无 thumb (老 seed / 兼容)，本地按 title+agent 重生成 SVG · 不再 fallback ◈ */
function PinRefThumbnail({ message }: { message: ImMessage }) {
  const refs = message.refs ?? {};
  const agentId = (refs.agentId as string) ?? "";
  const href = (refs.href as string) ?? "";
  const fullText = (refs.fullText as string) ?? "";
  const thumbFromRefs = (refs.thumbDataUrl as string) ?? "";
  // 老消息无 thumb · 本地重建 (与 drag source 同一 builder · 视觉一致)
  const thumb =
    thumbFromRefs ||
    buildPinThumbDataUrl({
      title: message.content,
      subtitle: fullText && fullText !== message.content ? fullText : undefined,
      accentVar: agentToAccentVar(agentId),
      badge: "钉",
    });
  return (
    <a
      className="wc-msg-pin-ref"
      href={href || "#"}
      title={fullText || message.content}
      data-testid="im-pin-ref-thumbnail"
      data-agent={agentId}
    >
      <img className="wc-msg-pin-ref-thumb" src={thumb} alt="" />
      <span className="wc-msg-pin-ref-body">
        <span className="wc-msg-pin-ref-title">{message.content}</span>
        {agentId ? (
          <span className="wc-msg-pin-ref-tag">{agentId}</span>
        ) : null}
      </span>
    </a>
  );
}

/** agentId → accentVar · 与 platform-shell-v2 §7 6 Agent 功能色对齐 */
function agentToAccentVar(agentId: string): string | undefined {
  switch (agentId) {
    case "report":
    case "agent_report":
      return "--t-report";
    case "alert":
    case "agent_alert":
      return "--t-alert";
    case "compliance":
    case "agent_compliance":
      return "--t-compli";
    case "credit":
    case "agent_credit":
      return "--t-credit";
    case "riskctrl":
    case "agent_riskctrl":
      return "--t-riskctrl";
    case "channel":
    case "agent_channel":
      return "--t-channel";
    default:
      return undefined;
  }
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
