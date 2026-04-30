"use client";

import {
  byUserId,
  publishEvent,
  useAuthStore,
  useCustomerStore,
} from "@/lib/store";
import type { AgentId, CustomerStage, ImMessage } from "@/lib/store";
import { findRecipeById } from "@/lib/store";

import { useDispatchStore } from "../_store/dispatch-store";
import { agentMeta } from "./agent-meta";
import { decodeHandoff } from "./handoff-payload";
import { encodeHandoff } from "./handoff-payload";
import { formatTimestamp } from "./time";

const FALLBACK_USER_ID = "u_wangzhe";

const AGENT_TO_STAGE: Record<AgentId, CustomerStage> = {
  channel: "lead",
  report: "report",
  credit: "credit",
  alert: "alert",
  compliance: "monitoring",
  riskctrl: "monitoring",
};

export function HandoffCard({ message }: { message: ImMessage }) {
  const payload = decodeHandoff(message.content);
  const recipe = payload.recipeId ? findRecipeById(payload.recipeId) : undefined;
  const fromAgent = payload.fromAgent ?? recipe?.fromAgent;
  const toAgent = payload.toAgent ?? recipe?.toAgent;
  const reason = payload.reason ?? recipe?.trigger ?? "请求交接";

  const updateMessage = useDispatchStore((s) => s.updateMessage);
  const appendSystemEvent = useDispatchStore((s) => s.appendSystemEvent);
  const advanceStage = useCustomerStore((s) => s.advanceStage);
  const currentUser = useAuthStore((s) => s.currentUser);
  const actorId = currentUser?.id ?? FALLBACK_USER_ID;

  const status = payload.status ?? "pending";

  const fromMeta = fromAgent ? agentMeta(fromAgent) : null;
  const toMeta = toAgent ? agentMeta(toAgent) : null;

  function persist(next: HandoffStatus) {
    updateMessage(message.threadId, message.id, {
      content: encodeHandoff({ ...payload, status: next }),
    });
  }

  function handleAccept() {
    persist("accepted");
    if (payload.customerId && toAgent) {
      advanceStage(payload.customerId, AGENT_TO_STAGE[toAgent]);
    }
    publishEvent({
      type: "handoff.accepted",
      agent: toAgent ?? "report",
      customerId: payload.customerId,
      actor: actorId,
      payload: {
        recipeId: payload.recipeId,
        ticketId: payload.ticketId,
        source: "dispatch.local",
      },
      correlationId: payload.ticketId,
    });
    const actorName = byUserId(actorId)?.name ?? "用户";
    appendSystemEvent(message.threadId, {
      from: toAgent ?? "report",
      content: `${actorName} 接手了 ${toMeta?.name ?? toAgent ?? "下一个 Agent"}（${payload.recipeId ?? "—"}）。`,
    });
  }

  function handleReject() {
    persist("rejected");
    appendSystemEvent(message.threadId, {
      from: "system",
      content: `已拒绝交接（${payload.recipeId ?? "—"}）。`,
    });
  }

  return (
    <article className={`dpx-handoff ${status}`}>
      <header>
        <span className="dpx-handoff-tag">
          交接卡片
          {fromMeta && toMeta && (
            <em>
              {" · "}
              {fromMeta.name} → {toMeta.name}
            </em>
          )}
        </span>
        <span className="ts">{formatTimestamp(message.createdAt)}</span>
      </header>
      <div className="dpx-handoff-body">{reason}</div>
      <footer className="dpx-handoff-actions">
        {status === "pending" ? (
          <>
            <button type="button" className="ghost" onClick={handleReject}>
              退回
            </button>
            <button type="button" className="primary" onClick={handleAccept}>
              接手
            </button>
          </>
        ) : (
          <span className="dpx-handoff-state">
            {status === "accepted" ? "已接手 · 客户阶段已推进" : "已退回"}
          </span>
        )}
      </footer>
    </article>
  );
}

type HandoffStatus = "pending" | "accepted" | "rejected";
