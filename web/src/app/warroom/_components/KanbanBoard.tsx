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
import { useEffect, useState } from "react";

import { useTicketStore, COLUMNS, type KanbanStatus } from "../_store/ticket-store";
import { StatusColumn } from "./StatusColumn";
import { TicketDrawer } from "./TicketDrawer";

/** @dnd-kit DndContext 包 4 列 · 订阅 event-bus · 弹 Drawer。
 *  Task A 只实现拖拽 + 抽屉基础。Task B 填 Drawer 操作链，Task C 加 FilterBar。 */
export function KanbanBoard() {
  const tickets = useTicketStore((s) => s.tickets);
  const updateStatus = useTicketStore((s) => s.updateStatus);
  const subscribe = useTicketStore((s) => s.subscribeHandoffRequested);

  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => {
    return subscribe();
  }, [subscribe]);

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
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <div className="kanban">
          {COLUMNS.map((col) => (
            <StatusColumn
              key={col.status}
              column={col}
              tickets={tickets.filter((t) => t.status === col.status)}
              onOpenTicket={setOpenId}
            />
          ))}
        </div>
      </DndContext>
      <TicketDrawer ticketId={openId} onClose={() => setOpenId(null)} />
    </>
  );
}
