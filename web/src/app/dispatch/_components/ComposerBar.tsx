"use client";

import { useRouter } from "next/navigation";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type DragEvent,
  type FormEvent,
  type KeyboardEvent,
} from "react";

import { sendMessage as sendMessageRest } from "@/lib/api/im";
import { getImWsClient } from "@/lib/im/websocket";
import {
  byUserId,
  publishEvent,
  useAuthStore,
  useCustomerStore,
  type ImMessage,
} from "@/lib/store";
import {
  CARD_PIN_MIME,
  type CardPinPayload,
} from "@/lib/store/whiteboard-store";
import {
  PANEL_PIN_MIME,
  type PanelPinPayload,
} from "@/lib/store/panel-canvas-store";
import { PIN_THUMB_MIME } from "@/components/shell/pin-thumb";

import { findRecipeById } from "@/lib/store";

import { useDispatchStore } from "../_store/dispatch-store";
import { agentMeta } from "./agent-meta";
import {
  parseSlash,
  resolveAgentAlias,
  SLASH_COMMANDS,
  stageToAgent,
  type SlashCommandDef,
} from "./composer-commands";
import { encodeHandoff } from "./handoff-payload";
import { filterCommands, SlashMenu } from "./SlashMenu";

const FALLBACK_USER_ID = "u_wangzhe";

/** W-FIX · 拖拽 payload safeParse · 解析失败返 null · 调用方走 fallback */
function safeParse<T>(raw: string): T | null {
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function ComposerBar() {
  const router = useRouter();
  const thread = useDispatchStore((s) =>
    s.threads.find((t) => t.id === s.currentThreadId),
  );
  const customer = useCustomerStore((s) =>
    thread?.customerId ? s.byId(thread.customerId) : undefined,
  );
  const addMessage = useDispatchStore((s) => s.addMessage);
  const appendSystemEvent = useDispatchStore((s) => s.appendSystemEvent);
  const clearThread = useDispatchStore((s) => s.clearThread);
  const liveMode = useDispatchStore((s) => s.liveMode);
  const setSendFailError = useDispatchStore((s) => s.setSendFailError);
  const currentUser = useAuthStore((s) => s.currentUser);

  /* Stage D.2F · typing debounce · 1s 内同 thread 只 emit 一次 typing */
  const lastTypingAtRef = useRef<{ tid: string; at: number } | null>(null);
  function maybeEmitTyping(tid: string) {
    if (liveMode === "seed") return;
    const now = Date.now();
    const last = lastTypingAtRef.current;
    if (last && last.tid === tid && now - last.at < 1000) return;
    lastTypingAtRef.current = { tid, at: now };
    try {
      getImWsClient().sendTyping(tid);
    } catch {
      /* ws 未连 · 忽略 */
    }
  }

  /* Stage D.2F · effect 在每次 thread 切换 reset typing 节流 */
  const threadIdSnap = thread?.id ?? "";
  useEffect(() => {
    lastTypingAtRef.current = null;
  }, [threadIdSnap]);

  const actorId = currentUser?.id ?? FALLBACK_USER_ID;
  const actor = byUserId(actorId);

  const [text, setText] = useState("");
  const [highlight, setHighlight] = useState(0);
  const [statusLine, setStatusLine] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  const showMenu = text.startsWith("/");
  const filtered = useMemo(() => filterCommands(text), [text]);

  if (!thread) {
    return (
      <div className="dpx-composer dpx-composer-disabled">
        选中一个对话以发送消息。
      </div>
    );
  }

  function pickCommand(cmd: SlashCommandDef) {
    setText(cmd.template);
    setHighlight(0);
    inputRef.current?.focus();
  }

  function flash(msg: string) {
    setStatusLine(msg);
    window.setTimeout(() => setStatusLine(null), 3500);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (showMenu && filtered.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setHighlight((h) => (h + 1) % filtered.length);
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setHighlight((h) => (h - 1 + filtered.length) % filtered.length);
        return;
      }
      if (e.key === "Tab") {
        e.preventDefault();
        pickCommand(filtered[highlight]);
        return;
      }
    }
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleSubmit();
    }
  }

  function handleSubmit(e?: FormEvent) {
    e?.preventDefault();
    const value = text.trim();
    if (!value || !thread) return;

    const slash = parseSlash(value);
    if (slash) {
      runCommand(slash.cmd, slash.args, value);
      setText("");
      return;
    }

    const msg = addMessage(thread.id, {
      from: actorId,
      kind: "text",
      content: value,
    });
    publishEvent({
      type: "comment.added",
      agent: stageToAgent(customer?.stage),
      customerId: thread.customerId,
      actor: actorId,
      payload: { messageId: msg.id, threadId: thread.id, text: value },
    });
    setText("");

    /* W-FIX · 2026-04-28 · live-fallback-banner-spec §1 规则 1
       · 持久化到后端 · 失败必显式 banner (禁止 silent fallback)
       · seed mode (无 backend) → skip · 本地 optimistic 即可 */
    if (liveMode !== "seed" && thread) {
      void sendMessageRest({
        threadId: thread.id,
        content: value,
        kind: "text",
      })
        .then(() => {
          setSendFailError(null);
        })
        .catch((err: unknown) => {
          // 失败 → 触发顶部 banner · 用户可点击 [重试]
          const isError = err instanceof Error;
          const status = (err as { status?: number })?.status;
          setSendFailError({
            message: isError ? err.message : "发消息失败 · 网络异常",
            code: typeof status === "number" ? status : undefined,
          });
        });
    }

    /* #5 + @agent 路由 · 2026-04-27 · IM 真接 DeepSeek + 解析 @智能体 名 */
    const AT_PATTERN =
      /@(报告|授信|获客|预警|合规|风控|agent6|agent3|agent1|agent4|agent5|agent2|report|credit|channel|alert|compli|compliance|riskctrl)/i;
    const AGENT_NAME_TO_ID: Record<string, string> = {
      报告: "report", agent6: "report", report: "report",
      授信: "credit", agent3: "credit", credit: "credit",
      获客: "channel", agent1: "channel", channel: "channel",
      预警: "alert", agent4: "alert", alert: "alert",
      合规: "compli", agent5: "compli", compli: "compli", compliance: "compli",
      风控: "riskctrl", agent2: "riskctrl", riskctrl: "riskctrl",
    };
    const atMatch = value.match(AT_PATTERN);
    const targetAgent = atMatch
      ? AGENT_NAME_TO_ID[atMatch[1].toLowerCase()] ?? ""
      : "";

    const apiBase =
      (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE) ||
      "";
    fetch(`${apiBase}/api/im/send`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include", // W-FIX2-A2 · 让 browser 带 zhongan_auth cookie
      body: JSON.stringify({
        message: value,
        thread_id: thread.id,
        customer_id: thread.customerId ?? "",
        target_agent: targetAgent,
      }),
    })
      .then((r) =>
        r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)),
      )
      .then((data: { reply: string; agent: string; thread_id: string }) => {
        const reply = (data.reply || "").trim();
        if (!reply) return;
        addMessage(thread.id, {
          from: data.agent || "agent_report",
          kind: "text",
          content: reply,
        });
      })
      .catch((err) => {
        console.warn("[ComposerBar] IM send failed · silent fallback:", err);
      });
  }

  function runCommand(cmd: string, args: string[], raw: string) {
    if (!thread) return;
    const fallbackCustomerId = thread.customerId;
    switch (cmd) {
      case "run": {
        const aliasArg = args[0];
        const customerArg = args[1] ?? fallbackCustomerId;
        const agentId = aliasArg ? resolveAgentAlias(aliasArg) : null;
        if (!agentId) {
          flash(`未识别 Agent：${aliasArg ?? "(空)"}。试试 agent6 / report`);
          return;
        }
        if (!customerArg) {
          flash("缺少客户参数，例：/run agent6 cust_zrgs");
          return;
        }
        const meta = agentMeta(agentId);
        appendSystemEvent(thread.id, {
          from: agentId,
          kind: "system_event",
          content: `${actor?.name ?? "用户"} 通过 /run 调起 ${meta.name}（客户 ${customerArg}）`,
        });
        publishEvent({
          type: "handoff.requested",
          agent: agentId,
          customerId: customerArg,
          actor: actorId,
          payload: { source: "dispatch.local", raw, kind: "run" },
        });
        router.push(`/archive/${agentId}?customer=${encodeURIComponent(customerArg)}`);
        return;
      }
      case "handoff": {
        const recipeId = args[0] ?? "report_to_credit";
        const recipe = findRecipeById(recipeId);
        const ticketId = `ticket_${recipeId}_${Date.now().toString(36)}`;
        addMessage(thread.id, {
          from: actorId,
          kind: "handoff_card",
          content: encodeHandoff({
            status: "pending",
            recipeId,
            fromAgent: recipe?.fromAgent,
            toAgent: recipe?.toAgent,
            customerId: fallbackCustomerId,
            reason: recipe?.trigger ?? `请求交接 · recipe=${recipeId}`,
            ticketId,
            source: "dispatch.local",
          }),
          refs: { ticketId },
        });
        publishEvent({
          type: "handoff.requested",
          agent: recipe?.toAgent ?? stageToAgent(customer?.stage),
          customerId: fallbackCustomerId,
          actor: actorId,
          payload: { recipeId, source: "dispatch.local", ticketId },
          correlationId: ticketId,
        });
        flash(`已发出交接请求 · ${recipe?.label ?? recipeId}`);
        return;
      }
      case "assign": {
        const targetId = args[0];
        const target = targetId ? byUserId(targetId) : undefined;
        if (!target) {
          flash(`未找到用户 ${targetId ?? "(空)"}，例：/assign u_lihua`);
          return;
        }
        appendSystemEvent(thread.id, {
          from: "system",
          kind: "system_event",
          content: `${actor?.name ?? "用户"} 把这条对话指给了 ${target.name}（${target.team}）`,
        });
        return;
      }
      case "clear": {
        clearThread(thread.id);
        flash("对话已清空（仅本地，不影响审计日志）");
        return;
      }
      default:
        flash(`未知命令：${raw}。可用：/run /handoff /assign /clear`);
    }
  }

  /* #3 · 2026-04-27 · 画布 / 白板拖到 composer 显示 thumbnail marker · 不显示 url 链接
     dragOver: 接受 PANEL_PIN_MIME / CARD_PIN_MIME · drop: 解 payload + setText 加 reference marker
     minimal: setText "📎 ${title}" · 不 url · 后续可扩 message kind="agent_output" 渲染缩略卡 */
  function handleDragOver(e: DragEvent<HTMLFormElement>) {
    if (
      e.dataTransfer.types.includes(PANEL_PIN_MIME) ||
      e.dataTransfer.types.includes(CARD_PIN_MIME)
    ) {
      e.preventDefault();
      e.dataTransfer.dropEffect = "copy";
    }
  }

  function handleDrop(e: DragEvent<HTMLFormElement>) {
    const panelRaw = e.dataTransfer.getData(PANEL_PIN_MIME);
    const cardRaw = e.dataTransfer.getData(CARD_PIN_MIME);
    if (!panelRaw && !cardRaw) return;
    e.preventDefault();
    let title = "";
    let subtitle: string | undefined;
    let kind: "panel" | "card" = "panel";
    if (panelRaw) {
      try {
        const p = JSON.parse(panelRaw) as PanelPinPayload;
        title = p.title;
        subtitle = p.subtitle;
        kind = "panel";
      } catch {
        return;
      }
    } else if (cardRaw) {
      try {
        const c = JSON.parse(cardRaw) as CardPinPayload;
        title = c.title;
        subtitle = c.subtitle;
        kind = "card";
      } catch {
        return;
      }
    }
    if (!title || !thread) return;
    /* W-FIX · 2026-04-28 · live-fallback-banner-spec §2 规则 4 + F-008
       拖柄 → 立即创建 kind="pin_ref" message · MessageBubble 渲缩略图
       · NOT setText 文本 marker (此前 #3 fallback 已停用 · 改为标准 IM message) */
    const panelPayload = panelRaw ? safeParse<PanelPinPayload>(panelRaw) : null;
    const cardPayload = !panelPayload && cardRaw ? safeParse<CardPinPayload>(cardRaw) : null;
    const refsPayload: NonNullable<ImMessage["refs"]> = {};
    // PanelPinPayload 有 agentKey · CardPinPayload 无 (per pin types 定义)
    const agentKey = panelPayload?.agentKey ?? "";
    const href = panelPayload?.href ?? cardPayload?.href ?? "";
    // fullText 用 PanelPin.blurb (摘要) 或 fallback subtitle/title
    const fullText = panelPayload?.blurb ?? subtitle ?? title;
    // pin-thumb · PanelPinHandle / MessagePinHandle 在 dragstart 时同步生成 SVG data URL
    // · 无论原 DOM 是否有图，drop 处永远拿得到一张缩略图，不再 fallback ◈ 图标
    const thumbDataUrl = e.dataTransfer.getData(PIN_THUMB_MIME);
    if (agentKey) refsPayload.agentId = agentKey;
    if (href) refsPayload.href = href;
    if (fullText) refsPayload.fullText = fullText;
    if (thumbDataUrl) refsPayload.thumbDataUrl = thumbDataUrl;

    const threadId = thread.id;
    const pinMsg = addMessage(threadId, {
      from: actorId,
      kind: "pin_ref",
      content: title,
      refs: refsPayload,
    });

    if (liveMode !== "seed") {
      void sendMessageRest({
        threadId,
        content: title,
        kind: "pin_ref",
        refs: refsPayload,
      })
        .then(() => setSendFailError(null))
        .catch((err: unknown) => {
          const status = (err as { status?: number })?.status;
          setSendFailError({
            message: err instanceof Error ? err.message : "拖拽 ref 发送失败",
            code: typeof status === "number" ? status : undefined,
          });
        });
    }
    void pinMsg;
    inputRef.current?.focus();
  }

  return (
    <form
      className="dpx-composer"
      onSubmit={handleSubmit}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {showMenu && (
        <SlashMenu
          query={text}
          highlightIndex={Math.min(highlight, Math.max(0, filtered.length - 1))}
          onPick={pickCommand}
          onHover={setHighlight}
        />
      )}
      {statusLine && <div className="dpx-composer-flash">{statusLine}</div>}
      <div className="dpx-composer-row">
        <span className="dpx-composer-actor">
          {actor?.avatar ?? "?"}
          <em>{actor?.name ?? actorId}</em>
        </span>
        <textarea
          ref={inputRef}
          className="dpx-composer-input"
          placeholder={`在「${thread.title}」留言，或输入 / 调用命令`}
          value={text}
          rows={1}
          onChange={(e) => {
            setText(e.target.value);
            if (thread) maybeEmitTyping(thread.id);
            setHighlight(0);
          }}
          onKeyDown={handleKeyDown}
        />
        <button type="submit" className="dpx-composer-send" disabled={!text.trim()}>
          发送
        </button>
      </div>
      <div className="dpx-composer-foot">
        <span className="hint">
          回车发送 · Shift + 回车换行 · 输入 <kbd>/</kbd> 看快捷命令（共 {SLASH_COMMANDS.length}）
        </span>
      </div>
    </form>
  );
}
