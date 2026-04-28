/**
 * ImLiveBridge · 纯 side-effect 组件 · 不渲染 JSX (Stage D.2F · onboarding W-D2F-A3).
 *
 * 在 dispatch page 挂一次 · 负责:
 *   1. mount 时 listThreads → setRemoteThreads (失败 keep seed)
 *   2. 连接 WebSocket /ws/im · onEvent 路由到 store action
 *   3. currentThreadId 切换 → ws.subscribe + listMessages → setThreadMessages
 *   4. 定时 pruneTyping (3s expire)
 *   5. unmount 关 ws · cleanup setInterval
 *
 * 与既有 EventBridge 并存 · 后者管 customer / agent event-bus · 本组件管 IM。
 */
"use client";

import { useEffect } from "react";

import { listMessages, listThreads } from "@/lib/api/im";
import { getImWsClient, type WsOutboundEvent } from "@/lib/im/websocket";
import type { ImMessage } from "@/lib/store";

import { useDispatchStore } from "../_store/dispatch-store";


export function ImLiveBridge() {
  const currentThreadId = useDispatchStore((s) => s.currentThreadId);
  const setRemoteThreads = useDispatchStore((s) => s.setRemoteThreads);
  const setThreadMessages = useDispatchStore((s) => s.setThreadMessages);
  const ingestRemoteMessage = useDispatchStore((s) => s.ingestRemoteMessage);
  const noteTyping = useDispatchStore((s) => s.noteTyping);
  const pruneTyping = useDispatchStore((s) => s.pruneTyping);
  const setLiveMode = useDispatchStore((s) => s.setLiveMode);
  const setWsState = useDispatchStore((s) => s.setWsState);

  /* mount once · listThreads + open ws */
  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        const next = await listThreads();
        if (cancelled) return;
        if (next.length > 0) {
          setRemoteThreads(next);
          setLiveMode("live");
        } else {
          setLiveMode("live_with_seed_fallback");
        }
      } catch {
        if (cancelled) return;
        setLiveMode("live_with_seed_fallback");
      }
    }

    void bootstrap();

    const client = getImWsClient({
      onEvent: (evt: WsOutboundEvent) => handleWsEvent(evt),
      onStateChange: (state) => setWsState(state),
    });
    client.connect();

    function handleWsEvent(evt: WsOutboundEvent) {
      if (!evt) return;
      const tid = (evt.thread_id as string | undefined) ?? "";
      if (evt.type === "message" || evt.type === "agent_output") {
        const raw = evt.message as Record<string, unknown> | undefined;
        if (!raw) return;
        const msg: ImMessage = {
          id: String(raw.id ?? ""),
          threadId: String(raw.thread_id ?? tid),
          from: String(raw.from_id ?? ""),
          kind: (raw.kind as ImMessage["kind"]) ?? "text",
          content: String(raw.content ?? ""),
          refs: (raw.refs as ImMessage["refs"]) ?? undefined,
          createdAt: String(raw.created_at ?? ""),
        };
        if (msg.id) ingestRemoteMessage(msg);
        return;
      }
      if (evt.type === "typing" && tid && evt.user_id) {
        noteTyping(tid, String(evt.user_id));
        return;
      }
      if (evt.type === "resync" && tid && Array.isArray(evt.messages)) {
        for (const raw of evt.messages as Array<Record<string, unknown>>) {
          const msg: ImMessage = {
            id: String(raw.id ?? ""),
            threadId: String(raw.thread_id ?? tid),
            from: String(raw.from_id ?? ""),
            kind: (raw.kind as ImMessage["kind"]) ?? "text",
            content: String(raw.content ?? ""),
            refs: (raw.refs as ImMessage["refs"]) ?? undefined,
            createdAt: String(raw.created_at ?? ""),
          };
          if (msg.id) ingestRemoteMessage(msg);
        }
        return;
      }
    }

    const pruneTimer = setInterval(() => pruneTyping(), 1000);

    return () => {
      cancelled = true;
      clearInterval(pruneTimer);
      client.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* currentThreadId 切换 → subscribe + 拉历史 */
  useEffect(() => {
    if (!currentThreadId) return;
    const client = getImWsClient();
    client.subscribe(currentThreadId);

    let cancelled = false;
    async function loadHistory() {
      try {
        const msgs = await listMessages(currentThreadId!, { limit: 100 });
        if (cancelled) return;
        if (msgs.length > 0) {
          setThreadMessages(currentThreadId!, msgs);
        }
      } catch {
        // 失败 keep seed messages · liveMode 已是 fallback
      }
    }
    void loadHistory();

    return () => {
      cancelled = true;
      client.unsubscribe(currentThreadId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentThreadId]);

  return null;
}
