"use client";

/**
 * TicketDrawer —— 右侧滑入的 ticket 详情抽屉。
 *
 * Task A 仅渲染基础内容（客户 + recipe + payload + 来源 event + Archive 按钮）。
 * 完整 Accept / Reject / Reassign 操作链在 Task B 补。
 */
import { useEffect } from "react";

import {
  byUserId,
  findRecipeById,
  useCustomerStore,
  useEventBus,
} from "@/lib/store";
import { useTicketStore } from "../_store/ticket-store";

const AGENT_CN: Record<string, string> = {
  report: "报告助手",
  credit: "授信决策",
  channel: "获客雷达",
  alert: "贷中预警",
  compli: "合规巡查",
  riskctrl: "风控策略",
};

function findSourceEvent(eventId: string | undefined) {
  if (!eventId) return undefined;
  return useEventBus.getState().history.find((e) => e.id === eventId);
}

export function TicketDrawer({
  ticketId,
  onClose,
}: {
  ticketId: string | null;
  onClose: () => void;
}) {
  const ticket = useTicketStore((s) => (ticketId ? s.byId(ticketId) : undefined));
  const customer = useCustomerStore((s) => (ticket ? s.byId(ticket.customerId) : undefined));
  const archive = useTicketStore((s) => s.archive);

  // Esc 关闭
  useEffect(() => {
    if (!ticketId) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [ticketId, onClose]);

  const open = Boolean(ticket);

  if (!ticket) {
    return (
      <aside
        className={`tkt-drawer${open ? " tkt-drawer--open" : ""}`}
        aria-hidden={!open}
      />
    );
  }

  const recipe = findRecipeById(
    // ticket 没存 recipeId —— 用 fromAgent+toAgent 反查第一个匹配项，作 fallback。
    ticket.triggerEventId ?? "",
  );
  const sourceEvent = findSourceEvent(ticket.triggerEventId);
  const requestedBy = byUserId(ticket.requestedBy);
  const assignedTo = ticket.assignedTo ? byUserId(ticket.assignedTo) : undefined;

  return (
    <>
      <div className="tkt-drawer-scrim" onClick={onClose} />
      <aside
        className="tkt-drawer tkt-drawer--open"
        role="dialog"
        aria-label="Ticket 详情"
      >
        <header className="tkt-dr-hd">
          <div className="tkt-dr-hd-meta">
            <span className="tkt-dr-chip">
              {AGENT_CN[ticket.fromAgent]} → {AGENT_CN[ticket.toAgent]}
            </span>
            <span className="tkt-dr-status" data-s={ticket.status}>
              {statusLabel(ticket.status)}
            </span>
          </div>
          <button className="tkt-dr-close" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </header>

        <section className="tkt-dr-sec">
          <h3 className="tkt-dr-h3">客户</h3>
          <div className="tkt-dr-cust">
            <div className="tkt-dr-cust-name">{customer?.name ?? ticket.customerId}</div>
            <div className="tkt-dr-cust-meta">
              {customer?.industry ?? "行业 —"} · {customer?.region ?? "区域 —"}
              {customer?.amount ? ` · 授信 ${customer.amount} 万` : ""}
            </div>
            {customer?.tags?.length ? (
              <div className="tkt-dr-tags">
                {customer.tags.map((t) => (
                  <span key={t} className="tkt-dr-tag">
                    {t}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        </section>

        <section className="tkt-dr-sec">
          <h3 className="tkt-dr-h3">交接说明</h3>
          <p className="tkt-dr-reason">{ticket.reason}</p>
          {recipe?.description ? (
            <p className="tkt-dr-desc">{recipe.description}</p>
          ) : null}
        </section>

        <section className="tkt-dr-sec">
          <h3 className="tkt-dr-h3">Payload</h3>
          <pre className="tkt-dr-json">
            {JSON.stringify(ticket.payload ?? {}, null, 2)}
          </pre>
        </section>

        <section className="tkt-dr-sec">
          <h3 className="tkt-dr-h3">参与人</h3>
          <ul className="tkt-dr-roster">
            <li>
              <span className="tkt-dr-role">发起</span>
              <span>{requestedBy?.name ?? ticket.requestedBy} · {requestedBy?.team ?? "—"}</span>
            </li>
            <li>
              <span className="tkt-dr-role">处理</span>
              <span>{assignedTo?.name ?? "待指派"}{assignedTo ? ` · ${assignedTo.team}` : ""}</span>
            </li>
          </ul>
        </section>

        {sourceEvent ? (
          <section className="tkt-dr-sec">
            <h3 className="tkt-dr-h3">来源事件</h3>
            <div className="tkt-dr-evt">
              <code>{sourceEvent.type}</code>
              <span className="tkt-dr-evt-time">{formatTime(sourceEvent.createdAt)}</span>
            </div>
          </section>
        ) : null}

        <footer className="tkt-dr-ft">
          <button
            className="tkt-dr-btn tkt-dr-btn--ghost"
            onClick={() => {
              archive(ticket.id);
              onClose();
            }}
          >
            归档
          </button>
          <span className="tkt-dr-ft-hint">完整 Accept / Reject / Reassign 在 Task B</span>
        </footer>
      </aside>
    </>
  );
}

function statusLabel(s: string) {
  switch (s) {
    case "requested": return "待受理";
    case "accepted": return "已受理";
    case "in_progress": return "进行中";
    case "completed": return "已完成";
    case "rejected": return "已拒绝";
    default: return s;
  }
}

function formatTime(iso: string) {
  try {
    const d = new Date(iso);
    return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  } catch {
    return iso;
  }
}
