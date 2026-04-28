/**
 * IM REST client (Stage D.2F · onboarding W-D2F-A3).
 *
 * 按 docs/contracts/im-protocol.md §3.2:
 *   GET    /api/im/threads
 *   GET    /api/im/threads/{tid}/messages?before=&limit=
 *   POST   /api/im/threads
 *   POST   /api/im/threads/{tid}/read
 *   POST   /api/im/messages
 *
 * 所有调用走 Authorization: Bearer <token> · token 由 getImToken() 解析:
 *   1. 优先 cookie "auth_token" (D.1 worker A2 设置)
 *   2. 退 localStorage "im_token"
 *   3. fallback "demo-u_wangzhe" (demo · 单 user 路径 · 与 backend auth.py shim 对齐)
 *
 * NB: 后端兼容 ?token=<jwt> query 参数 · WebSocket 客户端用 query · REST 用 header。
 */
"use client";

import type { ImMessage, ImThread } from "@/lib/store";

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "").replace(/\/$/, "");

function url(path: string): string {
  return `${API_BASE}${path}`;
}

/** 取 IM token · 优先 cookie · 次 localStorage · fallback demo. */
export function getImToken(): string {
  if (typeof window === "undefined") return "demo-u_wangzhe";
  // cookie auth_token (D.1 worker A2 设)
  const cookies = document.cookie.split(";").map((c) => c.trim());
  for (const c of cookies) {
    if (c.startsWith("auth_token=")) {
      const v = c.slice("auth_token=".length);
      if (v) return decodeURIComponent(v);
    }
  }
  // localStorage 备选
  try {
    const v = window.localStorage?.getItem("im_token");
    if (v) return v;
  } catch {
    /* 无 localStorage 权限 · 忽略 */
  }
  // fallback demo (本批 D.2F 与 D.1F merge 顺序无关 · 演示能跑)
  return "demo-u_wangzhe";
}

function authHeaders(): HeadersInit {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${getImToken()}`,
  };
}

export class ImApiError extends Error {
  status: number;
  code?: string;
  constructor(message: string, status: number, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function parseError(resp: Response): Promise<ImApiError> {
  let code: string | undefined;
  let msg = `HTTP ${resp.status}`;
  try {
    const body = await resp.json();
    const err = body?.detail?.error;
    if (err?.code) code = err.code;
    if (err?.message) msg = err.message;
  } catch {
    /* 非 JSON · ignore */
  }
  return new ImApiError(msg, resp.status, code);
}

/* ── Thread ────────────────────────────────────────────── */

export type BackendThread = {
  id: string;
  title: string;
  customer_id?: string | null;
  kind: "group" | "dm";
  participants: string[];
  last_message_at: string;
  unread_count: number;
  created_at: string;
};

function backendThreadToIm(t: BackendThread): ImThread {
  return {
    id: t.id,
    title: t.title,
    customerId: t.customer_id ?? undefined,
    participants: t.participants ?? [],
    lastMessageAt: t.last_message_at,
    unreadCount: t.unread_count ?? 0,
    kind: t.kind ?? "group",
  };
}

export async function listThreads(): Promise<ImThread[]> {
  const resp = await fetch(url("/api/im/threads"), {
    headers: authHeaders(),
    credentials: "include",
  });
  if (!resp.ok) throw await parseError(resp);
  const body = await resp.json();
  const items: BackendThread[] = body?.threads ?? [];
  return items.map(backendThreadToIm);
}

export async function createThread(req: {
  title: string;
  kind: "group" | "dm";
  participants: string[];
  customerId?: string;
}): Promise<ImThread> {
  const resp = await fetch(url("/api/im/threads"), {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify({
      title: req.title,
      kind: req.kind,
      participants: req.participants,
      customer_id: req.customerId,
    }),
  });
  if (!resp.ok) throw await parseError(resp);
  return backendThreadToIm(await resp.json());
}

export async function markThreadRead(threadId: string): Promise<void> {
  const resp = await fetch(url(`/api/im/threads/${encodeURIComponent(threadId)}/read`), {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
  });
  if (!resp.ok) throw await parseError(resp);
}

/* ── Message ─────────────────────────────────────────────── */

export type BackendMessage = {
  id: string;
  thread_id: string;
  from_id: string;
  kind:
    | "text"
    | "system_event"
    | "handoff_card"
    | "file"
    | "agent_output"
    | "pin_ref";
  content: string;
  refs?: Record<string, unknown> | null;
  created_at: string;
};

function backendMsgToIm(m: BackendMessage): ImMessage {
  return {
    id: m.id,
    threadId: m.thread_id,
    from: m.from_id,
    kind: m.kind,
    content: m.content,
    refs: (m.refs ?? undefined) as ImMessage["refs"],
    createdAt: m.created_at,
  };
}

export async function listMessages(
  threadId: string,
  opts: { before?: string; limit?: number } = {},
): Promise<ImMessage[]> {
  const qs = new URLSearchParams();
  if (opts.before) qs.set("before", opts.before);
  if (opts.limit) qs.set("limit", String(opts.limit));
  const path = `/api/im/threads/${encodeURIComponent(threadId)}/messages${
    qs.size ? `?${qs.toString()}` : ""
  }`;
  const resp = await fetch(url(path), {
    headers: authHeaders(),
    credentials: "include",
  });
  if (!resp.ok) throw await parseError(resp);
  const body = await resp.json();
  const items: BackendMessage[] = body?.messages ?? [];
  return items.map(backendMsgToIm);
}

export async function sendMessage(req: {
  threadId: string;
  content: string;
  kind?: ImMessage["kind"];
  refs?: ImMessage["refs"];
  targetAgent?: string;
}): Promise<ImMessage> {
  const resp = await fetch(url("/api/im/messages"), {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify({
      thread_id: req.threadId,
      content: req.content,
      kind: req.kind ?? "text",
      refs: req.refs,
      target_agent: req.targetAgent,
    }),
  });
  if (!resp.ok) throw await parseError(resp);
  const body = await resp.json();
  const msg: BackendMessage = body?.message;
  if (!msg) {
    throw new ImApiError("send response missing message", resp.status);
  }
  return backendMsgToIm(msg);
}

/* ── Helpers exported for consumers ──────────────────────── */

export const __for_tests = {
  backendThreadToIm,
  backendMsgToIm,
};
