/**
 * IM WebSocket client (Stage D.2F · onboarding W-D2F-A3).
 *
 * 按 docs/contracts/im-protocol.md §4:
 *   URL: ws://.../ws/im?token=<jwt>
 *   inbound  (client → server): subscribe / typing / ack_read / resync
 *   outbound (server → client): system / ack / message / typing / agent_progress
 *                               / agent_output / error / resync
 *
 * 重连策略 (§4.3): exponential backoff 1s → 2s → 4s → 8s → 16s → cap 30s · 上 attempts 0
 * 心跳: 30s 发 typing-self (轻量 keepalive · backend 60s timeout 内安全 buffer)
 *
 * 不依赖第三方 ws lib · 浏览器 WebSocket API · 仅 client (use client 标记)。
 */
"use client";

import { getImToken } from "@/lib/api/im";

export type WsInboundEvent = {
  type: "subscribe" | "typing" | "ack_read" | "resync";
  thread_id: string;
  up_to?: string;
  since?: string;
};

export type WsOutboundEvent = {
  type:
    | "system"
    | "ack"
    | "message"
    | "typing"
    | "agent_progress"
    | "agent_output"
    | "error"
    | "resync";
  thread_id?: string;
  message?: unknown;
  messages?: unknown[];
  user_id?: string;
  stage?: string;
  pct?: number;
  code?: string;
  ack_for?: string;
  [k: string]: unknown;
};

export type ImWsClientOptions = {
  /** WS base URL · 默认走相对路径 · 走当前 origin */
  baseUrl?: string;
  /** override token getter */
  getToken?: () => string;
  /** 收到 outbound event 回调 · null 静默 */
  onEvent?: (evt: WsOutboundEvent) => void;
  /** 连接状态回调 · 用于 UI 显示状态 */
  onStateChange?: (state: ImWsState) => void;
  /** 心跳间隔 ms · 默认 30000 (backend 60s timeout) */
  heartbeatMs?: number;
  /** max backoff ms · 默认 30000 */
  maxBackoffMs?: number;
  /** 自动重连 · 默认 true */
  autoReconnect?: boolean;
};

export type ImWsState = "idle" | "connecting" | "open" | "closed" | "error";


function inferWsUrl(baseUrl?: string): string {
  if (baseUrl && baseUrl.startsWith("ws")) return baseUrl;
  if (baseUrl) {
    return baseUrl.replace(/^http/, "ws");
  }
  if (typeof window === "undefined") return "ws://127.0.0.1:8000";
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}`;
}


export class ImWebSocketClient {
  private ws: WebSocket | null = null;
  private opts: Required<Omit<ImWsClientOptions, "baseUrl" | "getToken" | "onEvent" | "onStateChange">> &
    Pick<ImWsClientOptions, "baseUrl" | "getToken" | "onEvent" | "onStateChange">;
  private state: ImWsState = "idle";
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private subscribedThreadIds = new Set<string>();
  private explicitlyClosed = false;

  constructor(opts: ImWsClientOptions = {}) {
    this.opts = {
      heartbeatMs: opts.heartbeatMs ?? 30_000,
      maxBackoffMs: opts.maxBackoffMs ?? 30_000,
      autoReconnect: opts.autoReconnect ?? true,
      baseUrl: opts.baseUrl,
      getToken: opts.getToken,
      onEvent: opts.onEvent,
      onStateChange: opts.onStateChange,
    };
  }

  getState(): ImWsState {
    return this.state;
  }

  private setState(s: ImWsState) {
    this.state = s;
    this.opts.onStateChange?.(s);
  }

  /** 显式打开连接 · 已 open 直接 noop · explicit close → 重新置 false */
  connect(): void {
    if (typeof window === "undefined") return; // SSR safe
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }
    this.explicitlyClosed = false;
    this.setState("connecting");
    const token = (this.opts.getToken ?? getImToken)();
    const url = `${inferWsUrl(this.opts.baseUrl)}/ws/im?token=${encodeURIComponent(token)}`;

    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
    } catch (e) {
      this.setState("error");
      this.scheduleReconnect();
      return;
    }
    this.ws = ws;

    ws.onopen = () => {
      this.setState("open");
      this.reconnectAttempts = 0;
      this.startHeartbeat();
      // re-subscribe 历史 thread (per protocol §4.3 重连恢复)
      for (const tid of this.subscribedThreadIds) {
        this._sendRaw({ type: "subscribe", thread_id: tid });
      }
    };

    ws.onmessage = (ev) => {
      let parsed: WsOutboundEvent | null = null;
      try {
        parsed = JSON.parse(typeof ev.data === "string" ? ev.data : "{}");
      } catch {
        parsed = null;
      }
      if (!parsed || typeof parsed !== "object") return;
      this.opts.onEvent?.(parsed);
    };

    ws.onerror = () => {
      this.setState("error");
    };

    ws.onclose = () => {
      this.stopHeartbeat();
      this.setState("closed");
      if (!this.explicitlyClosed && this.opts.autoReconnect) {
        this.scheduleReconnect();
      }
    };
  }

  /** 主动关闭 · 不重连 */
  close(): void {
    this.explicitlyClosed = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.stopHeartbeat();
    if (this.ws && this.ws.readyState !== WebSocket.CLOSED) {
      try {
        this.ws.close();
      } catch {
        /* ignore */
      }
    }
    this.ws = null;
    this.setState("closed");
  }

  subscribe(threadId: string): void {
    if (!threadId) return;
    this.subscribedThreadIds.add(threadId);
    if (this.state === "open") {
      this._sendRaw({ type: "subscribe", thread_id: threadId });
    }
  }

  unsubscribe(threadId: string): void {
    this.subscribedThreadIds.delete(threadId);
  }

  /** 发 typing event (轻量 · 不持久) · 调用者负责 debounce */
  sendTyping(threadId: string): void {
    if (this.state !== "open") return;
    this._sendRaw({ type: "typing", thread_id: threadId });
  }

  /** 发 ack_read · message_id cursor */
  sendAckRead(threadId: string, upTo: string): void {
    if (this.state !== "open") return;
    this._sendRaw({ type: "ack_read", thread_id: threadId, up_to: upTo });
  }

  /** 重连后 · 拉 cursor 之后的消息 (resync inbound · backend 推 resync outbound) */
  sendResync(threadId: string, since: string): void {
    if (this.state !== "open") return;
    this._sendRaw({ type: "resync", thread_id: threadId, since });
  }

  private _sendRaw(payload: WsInboundEvent): void {
    try {
      this.ws?.send(JSON.stringify(payload));
    } catch {
      /* ws 已断 · 等 onclose 触发重连 */
    }
  }

  private scheduleReconnect(): void {
    if (this.explicitlyClosed) return;
    if (this.reconnectTimer) return;
    const attempt = this.reconnectAttempts;
    const delay = Math.min(2 ** attempt * 1000, this.opts.maxBackoffMs);
    this.reconnectAttempts = attempt + 1;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      // 用 typing 当 keepalive · backend 任 type 都重置 idle 计数
      // 但 typing 需要有效 thread_id · 取第一个 subscribed
      const tid = this.subscribedThreadIds.values().next().value;
      if (tid) {
        this._sendRaw({ type: "typing", thread_id: tid });
      } else {
        // 无 subscribed thread · 发 ping-equivalent (backend 拒识但不闭)
        try {
          this.ws?.send("{}");
        } catch {
          /* ignore */
        }
      }
    }, this.opts.heartbeatMs);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /** Reconnect attempts (test 用) */
  get _attempts(): number {
    return this.reconnectAttempts;
  }
}


/** 单例 · dispatch view + archive ConversationPanel 共享 */
let _singleton: ImWebSocketClient | null = null;

export function getImWsClient(opts?: ImWsClientOptions): ImWebSocketClient {
  if (!_singleton) {
    _singleton = new ImWebSocketClient(opts);
  }
  return _singleton;
}

export function resetImWsClient(): void {
  _singleton?.close();
  _singleton = null;
}
