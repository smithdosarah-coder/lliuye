/**
 * IM REST client (Stage D.2F · onboarding W-D2F-A3 · W-FIX2-A2-im-cookie-auth).
 *
 * 按 docs/contracts/im-protocol.md §3.2:
 *   GET    /api/im/threads
 *   GET    /api/im/threads/{tid}/messages?before=&limit=
 *   POST   /api/im/threads
 *   POST   /api/im/threads/{tid}/read
 *   POST   /api/im/messages
 *
 * Auth (W-FIX2-A2 · 2026-04-29 · bug #8 修):
 *   - 真 user: backend D.1 设 `zhongan_auth` httpOnly cookie · JS 不可读 ·
 *     所有 fetch 加 `credentials: "include"` 让 browser 自动带 cookie · 后端
 *     `_resolve_im_user` 优先吃 cookie 走 D.1 jwt_util.verify。
 *   - demo / e2e: 仍带 `Authorization: Bearer demo-u_<id>` · backend fallback 接受
 *     这条 path · 不影响真 user (backend cookie 优先成功后即返)。
 *
 * 历史 bug: 之前 `getImToken()` 读 cookie "auth_token" · 但 D.1 真 cookie 名
 * `zhongan_auth` (httpOnly 且 JS 不可读) · 导致 token 全 fall to demo · 真 user
 * 触发 401。修复后 frontend 不再 reach for cookie · 全权交 browser auto-include。
 */
"use client";

import type { ImMessage, ImThread } from "@/lib/store";

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "").replace(/\/$/, "");

function url(path: string): string {
  return `${API_BASE}${path}`;
}

/**
 * Demo / e2e fallback token · 真 user 走 cookie path · 此 token 仅 backend
 * Authorization Bearer fallback 用 (无 cookie / cookie 失效场景)。
 *
 * 不再读 `document.cookie` · 因 D.1 zhongan_auth 是 httpOnly · JS 不可读 ·
 * 之前读 `auth_token` 是错的 cookie 名 · resolve 全 fall to demo。
 */
export function getImToken(): string {
  if (typeof window === "undefined") return "demo-u_wangzhe";
  // localStorage 备选 (e2e 测试可注 token · 不依赖真 cookie)
  try {
    const v = window.localStorage?.getItem("im_token");
    if (v) return v;
  } catch {
    /* 无 localStorage 权限 · 忽略 */
  }
  return "demo-u_wangzhe";
}

/**
 * Auth headers + credentials option (browser 自动带 zhongan_auth cookie · 真 user
 * path) · Bearer 头作为 demo / e2e fallback path · backend 优先吃 cookie 后再读
 * Authorization。
 */
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

/* ── LLM single-turn (legacy /api/im/send) ───────────────── */

export type LlmTurnRequest = {
  message: string;
  threadId?: string;
  customerId?: string;
  targetAgent?: string;
  /** AbortSignal 让 caller 取消; helper 自身已加 30s timeout 兜底 */
  signal?: AbortSignal;
};

export type LlmTurnResponse = {
  reply: string;
  agent: string;
  target_agent?: string;
  thread_id?: string;
};

const LLM_TURN_TIMEOUT_MS = 30_000;

/**
 * /api/im/send 单 turn LLM 调用 · 显式错误 throw ImApiError (非 silent fallback)。
 * 内置 30s timeout (DeepSeek 慢响应保护) · caller 可额外传 AbortSignal。
 */
export async function sendLlmTurn(req: LlmTurnRequest): Promise<LlmTurnResponse> {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), LLM_TURN_TIMEOUT_MS);
  if (req.signal) {
    req.signal.addEventListener("abort", () => ctl.abort(), { once: true });
  }
  try {
    const resp = await fetch(url("/api/im/send"), {
      method: "POST",
      headers: authHeaders(),
      credentials: "include",
      signal: ctl.signal,
      body: JSON.stringify({
        message: req.message,
        thread_id: req.threadId ?? "",
        customer_id: req.customerId ?? "",
        target_agent: req.targetAgent ?? "",
      }),
    });
    if (!resp.ok) throw await parseError(resp);
    return (await resp.json()) as LlmTurnResponse;
  } catch (e) {
    if (e instanceof ImApiError) throw e;
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new ImApiError("AI 响应超时 (>30s) · 请重发或稍后再试", 0, "timeout");
    }
    throw new ImApiError(
      e instanceof Error ? e.message : "AI 网络异常",
      0,
      "network",
    );
  } finally {
    clearTimeout(timer);
  }
}

/* ── Helpers exported for consumers ──────────────────────── */

export const __for_tests = {
  backendThreadToIm,
  backendMsgToIm,
};
