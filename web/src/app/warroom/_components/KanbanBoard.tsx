"use client";

import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import { useEffect, useMemo, useState } from "react";

import { useTicketStore, COLUMNS, type KanbanStatus } from "../_store/ticket-store";
import { FilterBar } from "./FilterBar";
import { StatusColumn } from "./StatusColumn";
import { TicketDrawer } from "./TicketDrawer";
import { useWarroomFilters } from "./useWarroomFilters";

/** @dnd-kit DndContext 包 4 列 · 订阅 event-bus · 弹 Drawer · 接 FilterBar。 */
export function KanbanBoard() {
  const updateStatus = useTicketStore((s) => s.updateStatus);
  const subscribe = useTicketStore((s) => s.subscribeHandoffRequested);
  const filteredFn = useTicketStore((s) => s.filtered);
  const tickets = useTicketStore((s) => s.tickets);

  const { filters } = useWarroomFilters();

  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => {
    return subscribe();
  }, [subscribe]);

  const visible = useMemo(() => filteredFn(filters), [filteredFn, filters, tickets]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor),
  );

  const handleDragEnd = (e: DragEndEvent) => {
    const ticketId = String(e.active.id);
    const overStatus = e.over?.data?.current?.status as KanbanStatus | undefined;
    if (!overStatus) return;
    updateStatus(ticketId, overStatus);
  };

  return (
    <>
      <FilterBar visibleCount={visible.length} />
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <div className="kanban">
          {COLUMNS.map((col) => (
            <StatusColumn
              key={col.status}
              column={col}
              tickets={visible.filter((t) => t.status === col.status)}
              onOpenTicket={setOpenId}
            />
          ))}
        </div>
      </DndContext>
      <TicketDrawer ticketId={openId} onClose={() => setOpenId(null)} />
    </>
  );
}
