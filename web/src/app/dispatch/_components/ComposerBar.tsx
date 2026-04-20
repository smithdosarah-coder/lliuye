"use client";

import { useRouter } from "next/navigation";
import {
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";

import {
  byUserId,
  publishEvent,
  useAuthStore,
  useCustomerStore,
} from "@/lib/store";

import { useDispatchStore } from "../_store/dispatch-store";
import { agentMeta } from "./agent-meta";
import {
  parseSlash,
  resolveAgentAlias,
  SLASH_COMMANDS,
  stageToAgent,
  type SlashCommandDef,
} from "./composer-commands";
import { filterCommands, SlashMenu } from "./SlashMenu";

const FALLBACK_USER_ID = "u_wangzhe";

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
  const currentUser = useAuthStore((s) => s.currentUser);

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
          payload: { source: "dispatch.run", raw },
        });
        router.push(`/archive/${agentId}?customer=${encodeURIComponent(customerArg)}`);
        return;
      }
      case "handoff": {
        const recipeId = args[0] ?? "report_to_credit";
        addMessage(thread.id, {
          from: actorId,
          kind: "handoff_card",
          content: `请求交接 · recipe=${recipeId} · 客户 ${fallbackCustomerId ?? "—"}`,
          refs: { ticketId: `ticket_${recipeId}_${Date.now().toString(36)}` },
        });
        publishEvent({
          type: "handoff.requested",
          agent: stageToAgent(customer?.stage),
          customerId: fallbackCustomerId,
          actor: actorId,
          payload: { recipeId, source: "dispatch.handoff" },
        });
        flash(`已发出交接请求 · ${recipeId}`);
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

  return (
    <form className="dpx-composer" onSubmit={handleSubmit}>
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
