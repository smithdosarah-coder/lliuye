"use client";

import type { ImMessage } from "@/lib/store";

import { formatTimestamp } from "./time";

/**
 * Task A 占位：渲染 handoff_card kind 消息为只读卡片。
 * Task C 会接入 accept / reject 按钮 + handoff.accepted event。
 */
export function HandoffCard({ message }: { message: ImMessage }) {
  return (
    <article className="dpx-handoff pending">
      <header>
        <span className="dpx-handoff-tag">交接卡片</span>
        <span className="ts">{formatTimestamp(message.createdAt)}</span>
      </header>
      <div className="dpx-handoff-body">{message.content}</div>
      <footer className="dpx-handoff-actions">
        <button type="button" disabled className="ghost">
          接手（待 Task C 接入）
        </button>
      </footer>
    </article>
  );
}
