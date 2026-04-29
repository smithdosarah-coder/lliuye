"use client";

/**
 * RefCardMessage · 拖气泡入对话框后生成的"卡片型消息"。
 *
 * 视觉契约：
 *   - 与常规 .rpt-msg--user 等宽 · 右对齐（用户侧，因为拖动是用户动作）
 *   - 卡片内部：agent eyebrow + title + blurb 预览 + 双按钮（展开 / 跳转）
 *   - 背景 = `--agent` 功能色 6% 浅底 + 1px accent 14% 边（灰区决策 #5）
 *
 * 交互：
 *   - 展开：blurb 全文 inline 展开 · 220ms max-height+opacity（灰区决策 #3）
 *   - 跳转：同 tab router.push（灰区决策 #4）· 不开新 tab
 */

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { ConversationMessage } from "@/lib/mock/agent-channel-sessions";
import { agentLabel } from "@/lib/agent-labels";

export function RefCardMessage({ msg }: { msg: ConversationMessage }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const ref = msg.refPayload;
  if (!ref) return null;

  const speaker = msg.speaker ?? "客户经理";
  const accent = ref.accentVar ? `var(${ref.accentVar})` : "var(--ink)";

  function jump() {
    if (!ref?.href) return;
    router.push(ref.href);
  }

  return (
    <li className="rpt-msg rpt-msg--user rpt-msg--refcard">
      <div
        className="rpt-msg-body rpt-msg-body--user"
        style={{ ["--ref-accent" as string]: accent }}
      >
        <div className="rpt-msg-meta rpt-msg-meta--user">
          <span className="rpt-msg-at">{msg.at}</span>
          <span className="rpt-msg-who">{speaker}</span>
        </div>
        <div className={`rpt-ref-card${open ? " is-open" : ""}`}>
          <div className="rpt-ref-card-eyebrow">
            <span className="rpt-ref-card-dot" aria-hidden />
            {agentLabel(ref.agentKey)} · 引用
          </div>
          <div className="rpt-ref-card-title">{ref.title}</div>
          {/* 默认只看 title · 展开后才展示 subtitle + blurb 完整文，给按钮一个真实作用 */}
          {open && ref.subtitle && (
            <div className="rpt-ref-card-sub">{ref.subtitle}</div>
          )}
          {open && ref.blurb && (
            <div className="rpt-ref-card-blurb is-open">{ref.blurb}</div>
          )}
          <div className="rpt-ref-card-acts">
            <button
              type="button"
              className="rpt-ref-act"
              onClick={() => setOpen((v) => !v)}
              disabled={!ref.blurb && !ref.subtitle}
              aria-pressed={open}
            >
              {open ? "收起" : "展开"}
            </button>
            <button
              type="button"
              className="rpt-ref-act rpt-ref-act--primary"
              onClick={jump}
              disabled={!ref.href}
            >
              跳转
            </button>
          </div>
        </div>
      </div>
      <div className="rpt-msg-avatar rpt-msg-avatar--user" aria-hidden>
        王
      </div>
    </li>
  );
}
