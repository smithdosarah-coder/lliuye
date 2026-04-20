"use client";

import { useCustomerStore } from "@/lib/store";
import type { ImThread } from "@/lib/store";

import { useDispatchStore } from "../_store/dispatch-store";
import { formatTimestamp } from "./time";

export function ThreadList() {
  const threads = useDispatchStore((s) => s.threads);
  const currentId = useDispatchStore((s) => s.currentThreadId);
  const select = useDispatchStore((s) => s.selectThread);
  const sorted = [...threads].sort(
    (a, b) => +new Date(b.lastMessageAt) - +new Date(a.lastMessageAt),
  );

  return (
    <aside className="dpx-list">
      <header className="dpx-list-head">
        <span className="dpx-eyebrow">DISPATCH</span>
        <em>共 {threads.length} 个对话</em>
      </header>
      <div className="dpx-list-body">
        {sorted.map((t) => (
          <ThreadRow
            key={t.id}
            thread={t}
            active={t.id === currentId}
            onSelect={() => select(t.id)}
          />
        ))}
      </div>
    </aside>
  );
}

function ThreadRow({
  thread,
  active,
  onSelect,
}: {
  thread: ImThread;
  active: boolean;
  onSelect: () => void;
}) {
  const customer = useCustomerStore((s) =>
    thread.customerId ? s.byId(thread.customerId) : undefined,
  );
  const subtitle = customer
    ? `${customer.industry ?? "—"} · ${customer.region ?? "—"}`
    : "未分配客户";
  return (
    <button
      type="button"
      className={`dpx-row${active ? " on" : ""}`}
      onClick={onSelect}
    >
      <span className={`dpx-row-avatar stage-${customer?.stage ?? "lead"}`}>
        {customer?.shortName?.[0] ?? "·"}
      </span>
      <span className="dpx-row-body">
        <span className="dpx-row-title">
          <span className="nm">{customer?.shortName ?? thread.title}</span>
          <span className="ts">{formatTimestamp(thread.lastMessageAt)}</span>
        </span>
        <span className="dpx-row-sub">{subtitle}</span>
      </span>
      {thread.unreadCount > 0 && (
        <span className="dpx-row-badge">{thread.unreadCount}</span>
      )}
    </button>
  );
}
