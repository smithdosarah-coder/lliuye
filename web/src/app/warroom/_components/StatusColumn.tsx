"use client";

import { useDroppable } from "@dnd-kit/core";

import type { HandoffTicket } from "@/lib/store";
import { COLUMNS } from "../_store/ticket-store";
import { EmptyColumn } from "./EmptyColumn";
import { TicketCard } from "./TicketCard";

type Column = (typeof COLUMNS)[number];

/** `.kcol` 单列 · 复用 views.css 既有样式 + dnd-kit droppable */
export function StatusColumn({
  column,
  tickets,
  onOpenTicket,
}: {
  column: Column;
  tickets: HandoffTicket[];
  onOpenTicket: (id: string) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({
    id: column.status,
    data: { status: column.status },
  });

  const cls = [
    "kcol",
    column.done ? "done" : "",
    isOver ? "kcol--over" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const countPad = String(tickets.length).padStart(2, "0");

  return (
    <section ref={setNodeRef} className={cls} data-status={column.status}>
      <div className="khd">
        <span className="t">
          {column.label} <em>· {countPad}</em>
        </span>
        <span className="n">{countPad}</span>
      </div>
      <div className="kbody">
        {tickets.length === 0 ? (
          <EmptyColumn />
        ) : (
          tickets.map((t, i) => (
            <TicketCard key={t.id} ticket={t} idx={i} onOpen={onOpenTicket} />
          ))
        )}
      </div>
    </section>
  );
}
