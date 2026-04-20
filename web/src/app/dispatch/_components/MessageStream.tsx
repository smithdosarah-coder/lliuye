"use client";

import { useEffect, useRef } from "react";

import { useCustomerStore } from "@/lib/store";

import { useDispatchStore } from "../_store/dispatch-store";
import { ComposerBar } from "./ComposerBar";
import { HandoffCard } from "./HandoffCard";
import { MessageBubble } from "./MessageBubble";
import { SystemEventCard } from "./SystemEventCard";

export function MessageStream() {
  const currentId = useDispatchStore((s) => s.currentThreadId);
  const thread = useDispatchStore((s) =>
    s.threads.find((t) => t.id === s.currentThreadId),
  );
  const messages = useDispatchStore((s) =>
    s.currentThreadId ? s.messages[s.currentThreadId] ?? [] : [],
  );
  const customer = useCustomerStore((s) =>
    thread?.customerId ? s.byId(thread.customerId) : undefined,
  );
  const tailRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    tailRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, currentId]);

  if (!thread) {
    return (
      <section className="dpx-stream empty">
        <div className="dpx-empty">
          <span className="dpx-empty-glyph">⌘</span>
          <p>左侧选一个对话开始协作。</p>
          <p className="dpx-empty-hint">
            每个对话围绕一位客户，AI 助手会在事件发生时自动留言。
          </p>
        </div>
        <ComposerBar />
      </section>
    );
  }

  return (
    <section className="dpx-stream">
      <header className="dpx-stream-head">
        <div className="dpx-stream-title">
          <h2>{customer?.name ?? thread.title}</h2>
          <span className="dpx-stream-stage">{stageLabel(customer?.stage)}</span>
        </div>
        <div className="dpx-stream-meta">
          {customer?.amount && (
            <span>
              <em>授信额度</em>
              <b>{customer.amount.toLocaleString()} 万</b>
            </span>
          )}
          <span>
            <em>线程参与人</em>
            <b>{thread.participants.length}</b>
          </span>
        </div>
      </header>
      <div className="dpx-stream-body">
        {messages.length === 0 && (
          <div className="dpx-empty inline">
            <p>这个线程还没有留言，发出第一条吧。</p>
          </div>
        )}
        {messages.map((m) => {
          if (m.kind === "system_event") {
            return <SystemEventCard key={m.id} message={m} />;
          }
          if (m.kind === "handoff_card") {
            return <HandoffCard key={m.id} message={m} />;
          }
          return <MessageBubble key={m.id} message={m} />;
        })}
        <div ref={tailRef} />
      </div>
      <ComposerBar />
    </section>
  );
}

function stageLabel(stage: string | undefined): string {
  switch (stage) {
    case "lead":
      return "线索";
    case "intake":
      return "材料采集";
    case "report":
      return "报告撰写";
    case "credit":
      return "授信审批";
    case "monitoring":
      return "贷后监控";
    case "alert":
      return "预警跟进";
    case "closed":
      return "已结清";
    default:
      return "未分阶段";
  }
}
