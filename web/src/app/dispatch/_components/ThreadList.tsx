"use client";

import { useCustomerStore } from "@/lib/store";
import type { ImThread } from "@/lib/store";

import { useDispatchStore } from "../_store/dispatch-store";
import { formatTimestamp } from "./time";

/* Step 3 · 2026-04-22 CLI-C
   左侧线程列表分两段：GROUPS（含 agent 协作群） + DIRECT（同事私聊）
   旧数据 thread.kind 缺省视作 group，保持渐进。 */
export function ThreadList() {
  const threads = useDispatchStore((s) => s.threads);
  const currentId = useDispatchStore((s) => s.currentThreadId);
  const select = useDispatchStore((s) => s.selectThread);
  const sorted = [...threads].sort(
    (a, b) => +new Date(b.lastMessageAt) - +new Date(a.lastMessageAt),
  );
  const groups = sorted.filter((t) => (t.kind ?? "group") === "group");
  const dms = sorted.filter((t) => t.kind === "dm");

  return (
    <aside className="dpx-list">
      <header className="dpx-list-head">
        <span className="dpx-eyebrow">DISPATCH</span>
        <em>共 {threads.length} 个对话</em>
      </header>
      <div className="dpx-list-body">
        <ThreadSection
          label="GROUPS · 群组"
          count={groups.length}
          threads={groups}
          currentId={currentId}
          onSelect={select}
        />
        {dms.length > 0 && (
          <>
            <hr className="dpx-list-sep" aria-hidden />
            <ThreadSection
              label="DIRECT · 私聊"
              count={dms.length}
              threads={dms}
              currentId={currentId}
              onSelect={select}
            />
          </>
        )}
      </div>
    </aside>
  );
}

function ThreadSection({
  label,
  count,
  threads,
  currentId,
  onSelect,
}: {
  label: string;
  count: number;
  threads: ImThread[];
  currentId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <section className="dpx-list-section">
      <header className="dpx-list-section-head">
        <span className="lbl">{label}</span>
        <span className="num">{count}</span>
      </header>
      {threads.map((t) => (
        <ThreadRow
          key={t.id}
          thread={t}
          active={t.id === currentId}
          onSelect={() => onSelect(t.id)}
        />
      ))}
    </section>
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
  const isDm = thread.kind === "dm";
  const subtitle = customer
    ? `${customer.industry ?? "—"} · ${customer.region ?? "—"}`
    : isDm
      ? "私聊"
      : "未分配客户";
  /* dm 用 title 首字 + 中性灰底；group 沿用 customer.stage 染色。 */
  const avatarChar = customer?.shortName?.[0] ?? thread.title[0] ?? "·";
  const avatarStage = isDm ? "dm" : (customer?.stage ?? "lead");
  return (
    <button
      type="button"
      className={`dpx-row${active ? " on" : ""}`}
      onClick={onSelect}
    >
      <span className={`dpx-row-avatar stage-${avatarStage}`}>{avatarChar}</span>
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
