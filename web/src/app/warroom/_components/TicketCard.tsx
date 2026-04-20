"use client";

import { useDraggable } from "@dnd-kit/core";
import { Fragment, type CSSProperties } from "react";

import type { HandoffTicket } from "@/lib/store";
import { byUserId, useCustomerStore } from "@/lib/store";
import { inferPriority } from "../_store/ticket-store";

const AGENT_CN: Record<string, string> = {
  report: "报告",
  credit: "授信",
  channel: "获客",
  alert: "预警",
  compli: "合规",
  riskctrl: "风控",
};

function formatWhen(iso: string) {
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const min = Math.round(diffMs / 60000);
  if (min < 1) return "刚刚";
  if (min < 60) return `${min} 分钟前`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr} 小时前`;
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${mm}/${dd}`;
}

/** `.kcard` 单卡 · 复用 views.css 既有 .v-warroom .kcard 样式。@dnd-kit draggable。 */
export function TicketCard({
  ticket,
  idx,
  onOpen,
}: {
  ticket: HandoffTicket;
  idx: number;
  onOpen: (id: string) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: ticket.id,
    data: { ticket },
  });

  const customer = useCustomerStore((s) => s.byId(ticket.customerId));
  const assignee = ticket.assignedTo ? byUserId(ticket.assignedTo) : undefined;
  const priority = inferPriority(ticket);
  const pillVariant = priority === "urgent" ? "urg" : "P2";
  const pillLabel = priority === "urgent" ? "加急" : "流转";

  const style: CSSProperties = {
    "--i": idx,
    transform: transform ? `translate3d(${transform.x}px, ${transform.y}px, 0)` : undefined,
    opacity: isDragging ? 0.45 : undefined,
    touchAction: "none",
  } as CSSProperties;

  const titleCustomer = customer?.shortName ?? customer?.name ?? ticket.customerId;
  const flowLabel = `${AGENT_CN[ticket.fromAgent] ?? ticket.fromAgent} → ${AGENT_CN[ticket.toAgent] ?? ticket.toAgent}`;

  return (
    <article
      ref={setNodeRef}
      className="kcard"
      style={style}
      onClick={(e) => {
        if (isDragging) return;
        e.stopPropagation();
        onOpen(ticket.id);
      }}
      {...attributes}
      {...listeners}
    >
      <div className="hd">
        <span className="t">{titleCustomer}</span>
        <span className={`pr ${pillVariant}`}>{pillLabel}</span>
      </div>
      <div className="meta">
        <Fragment>{flowLabel}</Fragment>
        {" · "}
        <span className="cn">{formatWhen(ticket.updatedAt)}</span>
      </div>
      <div className="body">{ticket.reason}</div>
      <div className="ft">
        <span className="who">
          <span className="av">{assignee?.avatar ?? assignee?.name?.[0] ?? "未"}</span>
          {assignee?.name ?? "待指派"}
        </span>
        <span className="go">
          打开 <span>↘</span>
        </span>
      </div>
    </article>
  );
}
