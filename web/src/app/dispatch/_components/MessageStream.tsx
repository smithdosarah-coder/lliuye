"use client";

import { useEffect, useRef, useState } from "react";

import { byUserId, useCustomerStore } from "@/lib/store";
import type { ImMessage } from "@/lib/store";
import { listMessages, markThreadRead } from "@/lib/api/im";

import { useDispatchStore } from "../_store/dispatch-store";
import { ComposerBar } from "./ComposerBar";
import { HandoffCard } from "./HandoffCard";
import { MessageBubble } from "./MessageBubble";
import { SystemEventCard } from "./SystemEventCard";

const EMPTY_MESSAGES: ImMessage[] = [];
const EMPTY_TYPING: Record<string, number> = {};

export function MessageStream() {
  const currentId = useDispatchStore((s) => s.currentThreadId);
  const thread = useDispatchStore((s) =>
    s.threads.find((t) => t.id === s.currentThreadId),
  );
  const rawMessages = useDispatchStore((s) =>
    s.currentThreadId ? s.messages[s.currentThreadId] : undefined,
  );
  const messages = rawMessages ?? EMPTY_MESSAGES;
  const customer = useCustomerStore((s) =>
    thread?.customerId ? s.byId(thread.customerId) : undefined,
  );
  const liveMode = useDispatchStore((s) => s.liveMode);
  const wsState = useDispatchStore((s) => s.wsState);
  const wsFailSince = useDispatchStore((s) => s.wsFailSince);
  const sendFailError = useDispatchStore((s) => s.sendFailError);
  const setSendFailError = useDispatchStore((s) => s.setSendFailError);
  const typingPresence = useDispatchStore((s) =>
    s.currentThreadId ? s.typingByThread[s.currentThreadId] ?? EMPTY_TYPING : EMPTY_TYPING,
  );
  const setThreadMessages = useDispatchStore((s) => s.setThreadMessages);

  const tailRef = useRef<HTMLDivElement | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    tailRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, currentId]);

  /* Stage D.2F · 切 thread 时 mark read (不阻塞 UI · 失败 silent · seed mode skip) */
  useEffect(() => {
    if (!currentId) return;
    if (liveMode === "seed") return;
    void markThreadRead(currentId).catch(() => {
      /* ignore · UI 已经 selectThread reset unread */
    });
  }, [currentId, liveMode]);

  async function handleHistoryLoad() {
    if (!currentId || historyLoading) return;
    setHistoryLoading(true);
    try {
      const more = await listMessages(currentId, { limit: 200 });
      setThreadMessages(currentId, more);
    } catch {
      /* fallback: 保留 seed messages */
    } finally {
      setHistoryLoading(false);
    }
  }

  const typingUsers = Object.keys(typingPresence ?? {});

  if (!thread) {
    return (
      <section className="dpx-stream empty">
        <div className="dpx-empty">
          <span className="dpx-empty-glyph">⌘</span>
          <p>左侧选一个对话开始协作。</p>
          <p className="dpx-empty-hint">
            每个对话围绕一位客户，AI 助手会在事件发生时自动留言。
          </p>
        </div>
        <ComposerBar />
      </section>
    );
  }

  return (
    <section className="dpx-stream" data-live-mode={liveMode} data-ws-state={wsState}>
      {/* W-FIX · 2026-04-28 · live-fallback-banner-spec §1 规则 1 + onboarding §Acceptance */}
      <ImBanners
        sendFailError={sendFailError}
        clearSendFail={() => setSendFailError(null)}
        wsState={wsState}
        wsFailSince={wsFailSince}
      />
      <header className="dpx-stream-head">
        <div className="dpx-stream-title">
          <h2>{customer?.name ?? thread.title}</h2>
          <span className="dpx-stream-stage">{stageLabel(customer?.stage)}</span>
        </div>
        <div className="dpx-stream-meta">
          {customer?.amount && (
            <span>
              <em>CREDIT LINE</em>
              <b>{customer.amount.toLocaleString()} 万</b>
            </span>
          )}
          <span>
            <em>PARTICIPANTS</em>
            <b>{thread.participants.length}</b>
          </span>
          <span
            className="dpx-stream-ws"
            data-state={wsState}
            data-testid="im-ws-state"
            title={`live mode · ${liveMode}`}
          >
            <em>WS</em>
            <b>{wsState}</b>
          </span>
          <button
            type="button"
            className="dpx-stream-history-load"
            onClick={handleHistoryLoad}
            disabled={historyLoading}
            data-testid="im-thread-history-load"
            data-loading={historyLoading ? "yes" : "no"}
            title="重新拉取历史消息"
          >
            {historyLoading ? "拉取中…" : "加载历史"}
          </button>
        </div>
      </header>
      <div className="dpx-stream-body">
        {messages.length === 0 && (
          <div className="dpx-empty inline">
            <p>这个线程还没有留言，发出第一条吧。</p>
          </div>
        )}
        {messages.map((m) => {
          if (m.kind === "system_event") {
            return <SystemEventCard key={m.id} message={m} />;
          }
          if (m.kind === "handoff_card") {
            return <HandoffCard key={m.id} message={m} />;
          }
          return <MessageBubble key={m.id} message={m} />;
        })}
        <div ref={tailRef} />
      </div>
      {typingUsers.length > 0 ? (
        <div
          className="dpx-stream-typing"
          role="status"
          aria-live="polite"
          data-testid="im-typing-indicator"
        >
          <span className="dpx-stream-typing-dots" aria-hidden>
            <em />
            <em />
            <em />
          </span>
          <span className="dpx-stream-typing-text">
            {formatTypingUsers(typingUsers)}
          </span>
        </div>
      ) : null}
      <ComposerBar />
    </section>
  );
}

/* W-FIX · 2026-04-28 · live-fallback-banner-spec banners
   - sendFailError → 顶部 banner 显错 + [重试 dismiss]
   - wsFailSince 持续 ≥ 30s → "IM 实时连接断开" banner */

const WS_FAIL_THRESHOLD_MS = 30_000;

function ImBanners(p: {
  sendFailError: { message: string; code?: number; ts: number } | null;
  clearSendFail: () => void;
  wsState: string;
  wsFailSince: number | null;
}) {
  const [now, setNow] = useState(() => Date.now());
  // wsFailSince 存在时 · 启动 1s tick · 持续比对 30s threshold
  useEffect(() => {
    if (p.wsState === "open" || p.wsFailSince === null) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [p.wsState, p.wsFailSince]);

  const wsFailing =
    p.wsState !== "open" &&
    p.wsFailSince !== null &&
    now - p.wsFailSince >= WS_FAIL_THRESHOLD_MS;

  if (!p.sendFailError && !wsFailing) return null;

  return (
    <div className="dpx-stream-banners" aria-live="polite">
      {p.sendFailError ? (
        <div
          className="dpx-banner dpx-banner--err"
          role="alert"
          data-testid="im-send-fail-banner"
        >
          <span className="dpx-banner__icon" aria-hidden>⚠️</span>
          <span className="dpx-banner__text">
            发消息失败
            {p.sendFailError.code ? ` (${p.sendFailError.code})` : ""} ·{" "}
            {p.sendFailError.message}
          </span>
          <button
            type="button"
            className="dpx-banner__dismiss"
            data-testid="im-send-fail-dismiss"
            onClick={p.clearSendFail}
          >
            知道了
          </button>
        </div>
      ) : null}
      {wsFailing ? (
        <div
          className="dpx-banner dpx-banner--warn"
          role="status"
          data-testid="im-ws-fail-banner"
        >
          <span className="dpx-banner__icon" aria-hidden>⚠️</span>
          <span className="dpx-banner__text">
            IM 实时连接断开 (state: <code>{p.wsState}</code>) · 自动重连中
          </span>
        </div>
      ) : null}
    </div>
  );
}

/* Stage D.2F · 「李华 + 周敏 正在输入…」 / 「2 人正在输入…」 */
function formatTypingUsers(userIds: string[]): string {
  if (userIds.length === 0) return "";
  if (userIds.length === 1) {
    const u = byUserId(userIds[0]);
    return `${u?.name ?? userIds[0]} 正在输入…`;
  }
  if (userIds.length === 2) {
    const a = byUserId(userIds[0]);
    const b = byUserId(userIds[1]);
    return `${a?.name ?? userIds[0]} + ${b?.name ?? userIds[1]} 正在输入…`;
  }
  return `${userIds.length} 人正在输入…`;
}

function stageLabel(stage: string | undefined): string {
  switch (stage) {
    case "lead":
      return "线索";
    case "intake":
      return "材料采集";
    case "report":
      return "报告撰写";
    case "credit":
      return "授信审批";
    case "monitoring":
      return "贷后监控";
    case "alert":
      return "预警跟进";
    case "closed":
      return "已结清";
    default:
      return "未分阶段";
  }
}
