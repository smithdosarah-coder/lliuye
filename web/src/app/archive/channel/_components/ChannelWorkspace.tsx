"use client";

/**
 * /archive/channel · Agent1 获客 (Scout) workspace · 三栏对话式
 * 2026-04-21 H1 · canon 横向迁移（从 Agent6 ReportWorkspace 复用 shell + 右栏换业务 viz）
 *
 * 左 Query / Signals / Recent · 中 Conversation + Composer · 右 Radar + Funnel + Candidates
 *
 * 继承 canon A 章 8 条 primitive
 * Agent tint 注入：.v-archive--canon[data-agent="channel"] { --agent: var(--t-channel) }  (青绿)
 * 业务：look-alike 获客 —— 标杆画像 → 8 信号扫描 → 相似度打分 → Top N 推荐
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { KeyboardEvent, ChangeEvent, DragEvent } from "react";
import { CARD_PIN_MIME } from "@/lib/store/whiteboard-store";
import { PANEL_PIN_MIME } from "@/lib/store/panel-canvas-store";
import { nextThinkDelayMs, pickReply } from "../_mock/canned-replies";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";
import {
  CHANNEL_GLOBAL_STATS,
  CHANNEL_SESSION,
  type Candidate,
  type ConversationMessage,
  type FunnelStage,
  type RadarDimension,
  type RecentScoutSession,
  type SignalEvent,
  type SignalSource,
} from "@/lib/mock/agent-channel-session";
import { PanelPinHandle } from "@/components/shell/PanelPinHandle";
import { MessagePinHandle } from "@/components/shell/MessagePinHandle";
import {
  ClaimText,
  EvidenceProvider,
  EvidenceTrail,
  UnfilledFields,
} from "@/components/evidence";
import { CHANNEL_EVIDENCE } from "@/components/evidence/fixtures";

/** 截断消息内容作 pin title，避免白板/画布过长；尾部加 …。 */
function msgTitle(raw: string): string {
  const flat = raw.replace(/\s+/g, " ").trim();
  return flat.length > 42 ? `${flat.slice(0, 40)}…` : flat;
}

/** 统一消息 PinHandle props 生成。 */
function msgPinProps(msg: ConversationMessage, speaker: string) {
  return {
    id: `channel:msg:${msg.id}`,
    title: msgTitle(msg.content),
    subtitle: `${speaker} · ${msg.at}`,
    accentVar: "--t-channel",
    agentKey: "channel",
    href: "/archive/channel",
    fullText: msg.content,
  };
}

export default function ChannelWorkspace() {
  const s = CHANNEL_SESSION;
  const topSim = Math.round((s.candidates[0]?.similarity ?? 0) * 100);

  /* F-005 Phase 2 · 2026-04-27 · live candidates state hoist
     QueryBar SSE done → setLive(evt.candidates) · CandidatesPanel 优先 live
     历史 session 下拉 → setLive(null) 切回 CHANNEL_SESSION.candidates mock */
  const [liveCandidates, setLive] = useState<Candidate[] | null>(null);

  /* Step 2 · 2026-04-22 CLI-C
     conversation state hoist 到这里：ConversationPanel 渲染、Composer 提交都走它。
     纯 demo · 不接 API · pickReply 走 _mock/canned-replies.ts 关键词 + round-robin。 */
  const [messages, setMessages] = useState<ConversationMessage[]>(s.conversation);
  const seq = useRef(0);

  const submit = useCallback((raw: string) => {
    const text = raw.trim();
    if (!text) return;
    seq.current += 1;
    const ts = `${Date.now()}-${seq.current}`;
    const isCmd = text.startsWith("/");
    const userMsg: ConversationMessage = {
      id: `u-${ts}`,
      at: "刚刚",
      kind: isCmd ? "user-command" : "user-reply",
      content: text,
    };
    setMessages((prev) => [...prev, userMsg]);

    /* 假聊天 demo pickReply · 仅 dev mode 挂 (per onboarding kickoff Stage 3 #4)
       生产环境此分支被 NODE_ENV 静态替换 tree-shaken · 真接 API 走 SSE 路径。 */
    if (process.env.NODE_ENV !== "development") return;
    const thinkingId = `t-${ts}`;
    const thinkingMsg: ConversationMessage = {
      id: thinkingId,
      at: "刚刚",
      kind: "ai-thinking",
      content: "思考中…",
      thinking: { steps: [] },
    };
    setMessages((prev) => [...prev, thinkingMsg]);
    const delay = nextThinkDelayMs();
    window.setTimeout(() => {
      const reply = pickReply(text);
      const aiMsg: ConversationMessage = {
        id: `a-${ts}`,
        at: "刚刚",
        kind: "ai-response",
        content: reply.content,
        fieldRef: reply.fieldRef,
        sectionDiff: reply.sectionDiff,
      };
      setMessages((prev) =>
        prev.map((m) => (m.id === thinkingId ? aiMsg : m))
      );
    }, delay);
  }, []);

  return (
    <EvidenceProvider
      items={CHANNEL_EVIDENCE.items}
      unfilledFields={CHANNEL_EVIDENCE.unfilledFields}
    >
    <div data-view="archive-channel" className="ch-v2">
      <ChannelHero topSim={topSim} />
      <QueryBar setLive={setLive} />
      <FunnelStrip />
      <div className="ch-cross">
        <div className="ch-canvas">
          <div className="ch-canvas-top">
            <RadarPanel />
            <CandidatesPanel liveCandidates={liveCandidates} />
          </div>
          <ConversationPanel messages={messages} />
        </div>
        <aside className="ch-aside">
          <SignalTimelinePanel />
        </aside>
      </div>
      <ChannelComposer onSubmit={submit} />

      <section className="ev-claim-summary" aria-label="Evidence-grounded 分析结论">
        <span className="ev-claim-summary-label">分析结论 · Evidence-grounded</span>
        <ClaimText text={CHANNEL_EVIDENCE.summary} />
      </section>
      <UnfilledFields />
      <EvidenceTrail agentTone="channel" />
    </div>
    </EvidenceProvider>
  );
}

/* ── Hero ────────────────────────────────────────────── */

function ChannelHero({ topSim }: { topSim: number }) {
  const s = CHANNEL_SESSION;
  return (
    <header className="rpt-hero">
      <div className="rpt-hero-left">
        <div className="rpt-hero-badge" aria-hidden>◈</div>
        <div>
          <div className="rpt-hero-code">AGENT · 01 · SCOUT</div>
          <h1 className="rpt-hero-title">
            获客 <em>Scout.</em>
          </h1>
          <div className="rpt-hero-sub">
            {s.benchmarkName} · {s.candidateCount} 家候选 · {s.stage} · 首推相似度 {topSim}%
          </div>
        </div>
      </div>
      <div className="rpt-hero-stats">
        <Stat label="本周处理" value={CHANNEL_GLOBAL_STATS.weeklyProcessed} />
        <Stat label="命中率" value={CHANNEL_GLOBAL_STATS.hitRate} />
        <Stat label="平均时长" value={CHANNEL_GLOBAL_STATS.avgDuration} />
      </div>
    </header>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rpt-stat">
      <div className="rpt-stat-label">{label}</div>
      <div className="rpt-stat-value">{value}</div>
    </div>
  );
}

/* ── 左栏 · Query 画像 ──────────────────────────────── */

function QueryPanel() {
  const q = CHANNEL_SESSION.query;
  return (
    <section className="rpt-panel rpt-panel--tpl">
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">QUERY · 标杆画像</div>
          <h3 className="rpt-panel-title">{q.benchmark}</h3>
        </div>
        <span className="rpt-panel-meta">{q.updated}</span>
      </div>
      <div className="rpt-panel-body ch-q-body">
        <dl className="ch-q-meta">
          <div>
            <dt>行业</dt>
            <dd>{q.industry}</dd>
          </div>
          <div>
            <dt>地域</dt>
            <dd>{q.geo}</dd>
          </div>
          <div>
            <dt>规模</dt>
            <dd>{q.scaleRange}</dd>
          </div>
        </dl>
        <div className="ch-q-tags-wrap">
          <div className="ch-q-tags-lbl">12 维特征</div>
          <div className="ch-q-tags">
            {q.featureTags.map((t) => (
              <span key={t} className="ch-q-tag">
                {t}
              </span>
            ))}
          </div>
        </div>
        <div className="ch-q-kb">
          <div className="ch-q-kb-lbl">知识库命中</div>
          {q.kbRefs.map((k) => (
            <div key={k.id} className="ch-q-kb-row">
              <span className="name">{k.label}</span>
              <span className="hit">← {k.hitBy}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ── 左栏 · Signals 信号源 ─────────────────────────── */

const SIG_STATUS_LABEL: Record<SignalSource["status"], string> = {
  active: "在线",
  degraded: "降级",
  off: "关",
};

function SignalsPanel() {
  const sigs = CHANNEL_SESSION.signals;
  const active = sigs.filter((x) => x.status === "active").length;
  const totalHits = sigs.reduce((a, b) => a + b.hits, 0);
  return (
    <section className="rpt-panel rpt-panel--mat">
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">SIGNALS · 8 信号源</div>
          <h3 className="rpt-panel-title">
            {active} / {sigs.length} 活跃
          </h3>
        </div>
        <span className="rpt-panel-meta">{totalHits.toLocaleString()} 命中</span>
      </div>
      <div className="rpt-panel-body ch-sig-body">
        {sigs.map((g) => (
          <article
            key={g.id}
            className="ch-sig-card"
            data-status={g.status}
          >
            <header className="ch-sig-head">
              <span className="ch-sig-kind" data-k={g.key}>
                {g.label}
              </span>
              <span className="ch-sig-status" data-s={g.status}>
                {SIG_STATUS_LABEL[g.status]}
              </span>
            </header>
            <div className="ch-sig-stats">
              <div>
                <span className="num">{g.hits.toLocaleString()}</span>
                <span className="lbl">命中</span>
              </div>
              <div>
                <span className="num">{g.coverage}%</span>
                <span className="lbl">覆盖</span>
              </div>
              <div>
                <span className="num">{(g.weight * 100).toFixed(0)}</span>
                <span className="lbl">权重</span>
              </div>
            </div>
            <div className="ch-sig-bar" aria-hidden>
              <div
                className="ch-sig-bar-fill"
                style={{ width: `${g.coverage}%` }}
              />
            </div>
            <div className="ch-sig-meta">
              <span>{g.freq}</span>
              {g.note && <span className="note">· {g.note}</span>}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

/* ── 左栏 · Recent sessions ───────────────────────── */

function RecentPanel() {
  const recent = CHANNEL_SESSION.recentSessions;
  return (
    <section className="rpt-panel rpt-panel--tl">
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">RECENT · 近期扫描</div>
          <h3 className="rpt-panel-title">{recent.length} 条</h3>
        </div>
        <select
          className="rpt-tl-switch"
          aria-label="切换 session"
          defaultValue={CHANNEL_SESSION.id}
        >
          {recent.map((r) => (
            <option key={r.id} value={r.id}>
              {r.benchmark}
            </option>
          ))}
        </select>
      </div>
      <div className="rpt-panel-body rpt-tl-body">
        <ol className="ch-rc-list">
          {recent.map((r) => (
            <RecentRow key={r.id} row={r} />
          ))}
        </ol>
      </div>
    </section>
  );
}

function RecentRow({ row }: { row: RecentScoutSession }) {
  const pct = Math.round(row.progress * 100);
  const isDone = row.progress >= 1;
  return (
    <li className="ch-rc-row" data-done={isDone}>
      <span className="rpt-tl-bar" aria-hidden />
      <div className="rpt-tl-row">
        <span className="rpt-tl-kind">{isDone ? "完成" : "进行中"}</span>
        <span className="rpt-tl-at">{row.updated}</span>
      </div>
      <div className="rpt-tl-label">{row.benchmark}</div>
      <div className="ch-rc-bar" aria-hidden>
        <div className="ch-rc-bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="rpt-tl-detail">
        {row.stage} · {pct}%
      </div>
    </li>
  );
}

/* ── 中栏 · Conversation ────────────────────────────── */

function ConversationPanel({ messages }: { messages: ConversationMessage[] }) {
  const s = CHANNEL_SESSION;
  const blurb = `${messages.length} 条对话 · 候选 ${s.candidateCount} · 阻断 ${s.qcCounts.block}`;
  /* 新消息进来自动滚到底部（Composer 提交后看到自己的话） */
  const bodyRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const el = bodyRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages.length]);
  return (
    <section className="rpt-panel rpt-panel--conv">
      <PanelPinHandle
        id="channel:conversation"
        title="获客对话"
        subtitle={`获客 · ${s.benchmarkName}`}
        accentVar="--t-channel"
        agentKey="channel"
        href="/archive/channel"
        blurb={blurb}
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">CONVERSATION · 对话协作</div>
          <h3 className="rpt-panel-title">
            {s.benchmarkName} · {messages.length} 条
          </h3>
        </div>
        <span className="rpt-panel-meta">
          候选 {s.candidateCount} · 阻断 {s.qcCounts.block}
        </span>
      </div>
      <div ref={bodyRef} className="rpt-panel-body rpt-conv-body">
        <ol className="rpt-conv-list">
          {messages.map((m) => (
            <ConversationItem key={m.id} msg={m} />
          ))}
        </ol>
      </div>
    </section>
  );
}

function ConversationItem({ msg }: { msg: ConversationMessage }) {
  switch (msg.kind) {
    case "system-event":
      return <SystemEventMsg msg={msg} />;
    case "ai-question":
      return <AiQuestionMsg msg={msg} />;
    case "ai-response":
      return <AiResponseMsg msg={msg} />;
    case "ai-thinking":
      return <AiThinkingMsg msg={msg} />;
    case "user-reply":
      return <UserReplyMsg msg={msg} />;
    case "user-command":
      return <UserCommandMsg msg={msg} />;
    default:
      return null;
  }
}

function SystemEventMsg({ msg }: { msg: ConversationMessage }) {
  return (
    <li className="rpt-msg rpt-msg--sys">
      <MessagePinHandle {...msgPinProps(msg, "系统事件")} />
      <span className="rpt-msg-sys-chip">
        <span aria-hidden>◎</span> {msg.content}
      </span>
      <span className="rpt-msg-at">{msg.at}</span>
    </li>
  );
}

function AiQuestionMsg({ msg }: { msg: ConversationMessage }) {
  return (
    <li className="rpt-msg rpt-msg--ai rpt-msg--ask wc-msg wc-msg--ai">
      <MessagePinHandle {...msgPinProps(msg, "AI · Scout")} />
      <div className="wc-msg-avatar wc-msg-avatar--ai" aria-hidden>◈</div>
      <div className="wc-msg-bubble wc-msg-bubble--ai wc-msg-bubble--ask">
        <span className="wc-msg-bubble-ic" aria-hidden>?</span>
        <span className="wc-msg-bubble-text">{msg.content}</span>
      </div>
      <div className="wc-msg-foot wc-msg-foot--ai">
        {msg.fieldRef && <span className="wc-msg-fieldref">{msg.fieldRef}</span>}
        <span className="wc-msg-at">{msg.at}</span>
      </div>
    </li>
  );
}

function AiResponseMsg({ msg }: { msg: ConversationMessage }) {
  return (
    <li className="rpt-msg rpt-msg--ai wc-msg wc-msg--ai">
      <MessagePinHandle {...msgPinProps(msg, "AI · Scout")} />
      <div className="wc-msg-avatar wc-msg-avatar--ai" aria-hidden>◈</div>
      <div className="wc-msg-bubble wc-msg-bubble--ai">
        <div className="wc-msg-bubble-text">{msg.content}</div>
        {msg.sectionDiff && (
          <div className="rpt-msg-diff">
            <div className="rpt-msg-diff-lbl">
              更新 {msg.sectionDiff.sectionAnchor}
            </div>
            <div className="rpt-msg-diff-after">{msg.sectionDiff.after}</div>
          </div>
        )}
      </div>
      <div className="wc-msg-foot wc-msg-foot--ai">
        {msg.fieldRef && <span className="wc-msg-fieldref">{msg.fieldRef}</span>}
        <span className="wc-msg-at">{msg.at}</span>
      </div>
    </li>
  );
}

function AiThinkingMsg({ msg }: { msg: ConversationMessage }) {
  const [open, setOpen] = useState(false);
  const steps = msg.thinking?.steps ?? [];
  /* Step 2 · 当 steps 为空（demo 占位场景）时，展示三点 typing 指示，不渲染折叠按钮。
     已有 mock 数据带 steps 的走原有可折叠 UI。 */
  const isTyping = steps.length === 0;
  return (
    <li className="rpt-msg rpt-msg--ai rpt-msg--thinking wc-msg wc-msg--ai">
      <MessagePinHandle {...msgPinProps(msg, "AI · thinking")} />
      <div className="wc-msg-avatar wc-msg-avatar--ai wc-msg-avatar--thinking" aria-hidden>◈</div>
      <div className="wc-msg-bubble wc-msg-bubble--think">
        {isTyping ? (
          <div
            className="wc-msg-typing"
            role="status"
            aria-live="polite"
            aria-label={msg.content}
          >
            <span /><span /><span />
          </div>
        ) : (
          <>
            <button
              type="button"
              className="wc-msg-think"
              aria-expanded={open}
              onClick={() => setOpen((v) => !v)}
            >
              <span className="wc-msg-think-text">{msg.content}</span>
              <span className="wc-msg-think-caret" aria-hidden>
                {open ? "▾" : "▸"}
              </span>
            </button>
            {open && (
              <ol className="rpt-msg-steps">
                {steps.map((st, i) => (
                  <li key={i} className="rpt-msg-step">
                    <div className="rpt-msg-step-lbl">
                      <span className="rpt-msg-step-n">{i + 1}</span>
                      {st.label}
                    </div>
                    <ul className="rpt-msg-step-evs">
                      {st.evidences.map((e, j) => (
                        <li key={j} className="rpt-msg-step-ev">
                          {e}
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ol>
            )}
          </>
        )}
      </div>
      <div className="wc-msg-foot wc-msg-foot--ai">
        <span className="wc-msg-at">{msg.at}</span>
      </div>
    </li>
  );
}

function UserReplyMsg({ msg }: { msg: ConversationMessage }) {
  return (
    <li className="rpt-msg rpt-msg--user wc-msg wc-msg--user">
      <MessagePinHandle {...msgPinProps(msg, "客户经理 · 王哲")} />
      <div className="wc-msg-bubble wc-msg-bubble--user">{msg.content}</div>
      <div className="wc-msg-avatar wc-msg-avatar--user" aria-hidden>王</div>
      <div className="wc-msg-foot wc-msg-foot--user">
        <span className="wc-msg-at">{msg.at}</span>
      </div>
    </li>
  );
}

function UserCommandMsg({ msg }: { msg: ConversationMessage }) {
  return (
    <li className="rpt-msg rpt-msg--user rpt-msg--cmd wc-msg wc-msg--user">
      <MessagePinHandle {...msgPinProps(msg, "客户经理 · /command")} />
      <div className="wc-msg-bubble wc-msg-bubble--user wc-msg-bubble--cmd">
        <code>{msg.content}</code>
      </div>
      <div className="wc-msg-avatar wc-msg-avatar--user" aria-hidden>王</div>
      <div className="wc-msg-foot wc-msg-foot--user">
        <span className="wc-msg-at">{msg.at}</span>
      </div>
    </li>
  );
}

/* ── 中栏 · Composer ────────────────────────────────── */

type ComposerHint = "idle" | "slash" | "mention" | "industry";

function ChannelComposer({ onSubmit }: { onSubmit: (text: string) => void }) {
  const [value, setValue] = useState("");
  const [hint, setHint] = useState<ComposerHint>("idle");
  const [dropHover, setDropHover] = useState(false);
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 180) + "px";
  }, [value]);

  function handleKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    /* 类微信：纯 Enter 直接发；Shift+Enter 才换行；⌘/Ctrl+Enter 也发（保留快捷键） */
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function handleChange(e: ChangeEvent<HTMLTextAreaElement>) {
    const v = e.target.value;
    setValue(v);
    const last = v.slice(-1);
    if (last === "/") setHint("slash");
    else if (last === "@") setHint("mention");
    else if (last === "#") setHint("industry");
    else setHint("idle");
  }

  function submit() {
    const text = value.trim();
    if (!text) return;
    onSubmit(text);
    setValue("");
    setHint("idle");
  }

  /* ── Drop target：接 PANEL_PIN / CARD_PIN / text/plain ──
     读到 payload 后把 title 以 `@引用:<title> ` 形式插入 textarea 当前光标位
     （无焦点就 append 到末尾）；阻止 textarea 原生 drop 吃掉 text/plain。 */
  function hasPin(e: DragEvent<HTMLDivElement>): boolean {
    const ts = Array.from(e.dataTransfer.types);
    return ts.includes(PANEL_PIN_MIME) || ts.includes(CARD_PIN_MIME);
  }

  function onDragEnter(e: DragEvent<HTMLDivElement>) {
    if (!hasPin(e)) return;
    e.preventDefault();
    setDropHover(true);
  }
  function onDragOver(e: DragEvent<HTMLDivElement>) {
    if (!hasPin(e)) return;
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = "copy";
    if (!dropHover) setDropHover(true);
  }
  function onDragLeave(e: DragEvent<HTMLDivElement>) {
    // 只有真正离开 slot 边界才清（子元素间切换 relatedTarget 仍在内部）
    const node = e.currentTarget;
    const next = e.relatedTarget as Node | null;
    if (!next || !node.contains(next)) setDropHover(false);
  }
  function onDrop(e: DragEvent<HTMLDivElement>) {
    if (!hasPin(e)) return;
    e.preventDefault();
    e.stopPropagation();
    setDropHover(false);
    let title = "";
    const rawPanel = e.dataTransfer.getData(PANEL_PIN_MIME);
    const rawCard = e.dataTransfer.getData(CARD_PIN_MIME);
    try {
      if (rawPanel) title = (JSON.parse(rawPanel) as { title?: string }).title ?? "";
      else if (rawCard) title = (JSON.parse(rawCard) as { title?: string }).title ?? "";
    } catch {
      title = e.dataTransfer.getData("text/plain");
    }
    if (!title) return;
    insertAtCursor(`@引用:${title} `);
  }

  function insertAtCursor(fragment: string) {
    const ta = taRef.current;
    if (!ta) {
      setValue((v) => v + fragment);
      return;
    }
    const start = ta.selectionStart ?? value.length;
    const end = ta.selectionEnd ?? value.length;
    const next = value.slice(0, start) + fragment + value.slice(end);
    setValue(next);
    // 光标移到插入片段之后
    requestAnimationFrame(() => {
      if (!taRef.current) return;
      const pos = start + fragment.length;
      taRef.current.focus();
      taRef.current.setSelectionRange(pos, pos);
    });
  }

  const sigCount = CHANNEL_SESSION.signals.length;
  const tagCount = CHANNEL_SESSION.query.featureTags.length;

  const slotCls = [
    "rpt-composer-slot",
    "rpt-composer",
    dropHover ? "rpt-composer--drop-hover" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      className={slotCls}
      data-hint={hint}
      onDragEnter={onDragEnter}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      <div className="rpt-composer-bar">
        <textarea
          ref={taRef}
          className="rpt-composer-ta"
          placeholder="提问或下指令 · 输入 / 触发命令 · @ 引用信号源 · # 换行业"
          value={value}
          onChange={handleChange}
          onKeyDown={handleKey}
          rows={1}
        />
        <button
          type="button"
          className="rpt-composer-send"
          onClick={submit}
          disabled={!value.trim()}
        >
          <span>发送</span>
          <kbd>↩</kbd>
        </button>
      </div>
      <div className="rpt-composer-hints">
        <span className="rpt-composer-hint" data-active={hint === "slash"}>
          <kbd>/</kbd> 指令 · confirm / expand / exclude
        </span>
        <span className="rpt-composer-hint" data-active={hint === "mention"}>
          <kbd>@</kbd> 信号源 · {sigCount} 个
        </span>
        <span className="rpt-composer-hint" data-active={hint === "industry"}>
          <kbd>#</kbd> 画像特征 · {tagCount} 维
        </span>
      </div>
    </div>
  );
}

/* ── 区域 1 · Query 输入条（顶部全宽） ───────────────── */

type ChannelStreamEvent = {
  event?: string;
  stage?: string;
  status?: string;
  pct?: number;
  message?: string;
  candidates?: unknown[];
  tags?: unknown[];
  count?: number;
  total?: number;
  route?: string;
  routes_done?: number;
  routes_total?: number;
  metrics?: { signalTotal?: number; companiesFound?: number; final?: number };
  data_source?: string;
  [k: string]: unknown;
};

/* F-005 Phase 3 · 2026-04-27 · friendly stream event formatter
   替代 raw JSON dump · 让 user 看人话 (PARSE/SIGNAL_SCAN/AGGREGATE/ENRICH/PITCH/RANK/DONE/ERROR) */
function formatChannelEvent(evt: ChannelStreamEvent): {
  stage: string;
  msg: string;
  pct?: number;
} {
  const baseStage = String(evt.stage ?? evt.event ?? "·").toUpperCase();
  if (evt.event === "stage") {
    const status = evt.status;
    if (evt.stage === "parse") {
      if (status === "running") return { stage: baseStage, msg: "解析用户意图..." };
      if (status === "done") {
        const tags = (evt.tags as unknown[] | undefined) ?? [];
        return { stage: baseStage, msg: `已解析 ${tags.length} 个特征标签` };
      }
    }
    if (evt.stage === "signal_scan") {
      if (status === "running") return { stage: baseStage, msg: "并行扫描 5 路信号源 (中标 / 认可 / 技术 / 增长 / 获奖)..." };
      if (status === "done") {
        const count = evt.count;
        const ds = evt.data_source;
        return { stage: baseStage, msg: `扫描完 · ${count ?? "?"} 条信号 · 来源 ${ds ?? "mock"}` };
      }
    }
    if (evt.stage === "aggregate") {
      if (status === "running") return { stage: baseStage, msg: "实体聚合去重..." };
      if (status === "done") return { stage: baseStage, msg: `聚合完 · ${evt.total ?? "?"} 个实体` };
    }
    if (evt.stage === "enrich") {
      if (status === "running") return { stage: baseStage, msg: "企查查补全工商信息 + 产品匹配..." };
      if (status === "done") return { stage: baseStage, msg: "工商 + 产品匹配完成" };
    }
    if (evt.stage === "pitch") {
      if (status === "running") return { stage: baseStage, msg: "推荐配比生成..." };
      if (status === "done") return { stage: baseStage, msg: "推荐生成完" };
    }
    if (evt.stage === "rank") {
      if (status === "running") return { stage: baseStage, msg: "信号密度排序..." };
      if (status === "done") return { stage: baseStage, msg: "排序完成" };
    }
  }
  if (evt.event === "progress") {
    const route = String(evt.route ?? "?");
    const done = evt.routes_done;
    const total = evt.routes_total;
    return {
      stage: "PROGRESS",
      msg: `${route} · ${done ?? 0}/${total ?? 0}`,
      pct: total ? Math.round(((done ?? 0) / total) * 100) : undefined,
    };
  }
  if (evt.event === "done") {
    const cs = (evt.candidates as unknown[] | undefined) ?? [];
    const m = evt.metrics;
    return { stage: "DONE", msg: `完成 · ${cs.length} 候选 · ${m?.companiesFound ?? "?"} 命中` };
  }
  if (evt.event === "error") {
    return { stage: "ERROR", msg: String(evt.message ?? "AI 解析失败 · 请重试") };
  }
  return { stage: baseStage, msg: String(evt.message ?? "进行中…") };
}

function QueryBar({ setLive }: { setLive: (c: Candidate[] | null) => void }) {
  const q = CHANNEL_SESSION.query;
  const recent = CHANNEL_SESSION.recentSessions;
  /* F-005 · 2026-04-27 双模式实装:
     · 历史 session select onChange → 切到对应 mock CHANNEL_SESSION (现状已是 mock 渲染)
     · 自由 textbox onSubmit → fetch /api/channel/run SSE · 真调 DeepSeek + Tavily */
  const [input, setInput] = useState(
    "找做工业软件的 SaaS 公司 · B 轮后 · 华东 · 年营收 1-3 亿"
  );
  const [streaming, setStreaming] = useState(false);
  const [streamEvents, setStreamEvents] = useState<ChannelStreamEvent[]>([]);
  const [streamError, setStreamError] = useState<string | null>(null);

  async function runRealSearch() {
    if (!input.trim() || streaming) return;
    setStreaming(true);
    setStreamEvents([]);
    setStreamError(null);
    try {
      // prod: 相对 path 走 nginx proxy → :8000 · dev: NEXT_PUBLIC_API_BASE=http://localhost:8000
      const apiBase =
        (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE) ||
        "";
      const res = await fetch(`${apiBase}/api/channel/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: input, mock: false, top_n: 8 }),
      });
      if (!res.ok || !res.body) {
        throw new Error(`HTTP ${res.status}`);
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      // Read SSE 流到 done · 累积 events 给下方 stream panel 渲染
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const blocks = buf.split("\n\n");
        buf = blocks.pop() ?? "";
        for (const block of blocks) {
          const dataLine = block
            .split("\n")
            .find((line) => line.startsWith("data:"));
          if (!dataLine) continue;
          try {
            const evt = JSON.parse(dataLine.slice(5).trim()) as ChannelStreamEvent;
            setStreamEvents((prev) => [...prev, evt]);
            // F-005 Phase 2 · 提取 final candidates 注入 ChannelWorkspace 让 CandidatesPanel 渲染 live
            if (evt.event === "done" && Array.isArray(evt.candidates)) {
              setLive(evt.candidates as unknown as Candidate[]);
            }
          } catch {
            /* skip malformed line */
          }
        }
      }
    } catch (err) {
      setStreamError(err instanceof Error ? err.message : String(err));
    } finally {
      setStreaming(false);
    }
  }

  function onSelectSession() {
    /* 选下拉历史 session = 切回 mock · 清 stream 残留 + setLive(null) */
    setStreamEvents([]);
    setStreamError(null);
    setLive(null);
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      void runRealSearch();
    }
  }

  return (
    <section className="rpt-panel ch-querybar">
      <div className="ch-querybar-head">
        <div>
          <div className="rpt-panel-eyebrow">QUERY · 双模式</div>
          <h3 className="rpt-panel-title ch-querybar-title">
            一句话描述要找的企业 · <em>AI 解析 (textbox)</em> 或选历史 (mock)
          </h3>
        </div>
        <div className="ch-querybar-recent">
          <label>历史 session (mock)</label>
          <select defaultValue={CHANNEL_SESSION.id} onChange={onSelectSession}>
            {recent.map((r) => (
              <option key={r.id} value={r.id}>
                {r.benchmark}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="ch-querybar-body">
        <input
          type="text"
          className="ch-querybar-input"
          placeholder="自然语言描述 · 自由输入 → 真接 /api/channel/run (DeepSeek + Tavily) · 或选下拉看 mock"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={streaming}
        />
        <button
          type="button"
          className="ch-querybar-btn"
          data-testid="scout-search"
          onClick={() => void runRealSearch()}
          disabled={!input.trim() || streaming}
        >
          <span>{streaming ? "AI 解析中…" : "AI 搜索"}</span>
          <span className="kbd">{streaming ? "···" : "⌘↩"}</span>
        </button>
      </div>
      <div className="ch-querybar-tags">
        <span className="lbl">AI 解析的特征 · 12 维 (mock 默认)</span>
        <div className="tags">
          {q.featureTags.map((t) => (
            <span key={t} className="tag">
              {t}
            </span>
          ))}
        </div>
      </div>
      {(streamEvents.length > 0 || streamError) && (
        <div className="ch-querybar-stream" data-testid="scout-live-stream">
          <div className="ch-querybar-stream-head">
            ▶ AI 实时流 · /api/channel/run SSE
          </div>
          {streamError ? (
            <div className="ch-querybar-stream-error">⚠ {streamError}</div>
          ) : (
            <ul className="ch-querybar-stream-list">
              {streamEvents.map((evt, i) => {
                const f = formatChannelEvent(evt);
                return (
                  <li key={i} className="ch-querybar-stream-row">
                    <span className="stage">{f.stage}</span>
                    <span className="msg">{f.msg}</span>
                    {typeof f.pct === "number" && (
                      <span className="pct">{f.pct}%</span>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

/* ── 顶栏 · Funnel 5 阶段横条 ───────────────────────── */

function FunnelStrip() {
  const s = CHANNEL_SESSION;
  const funnel = s.funnel;
  const max = Math.max(...funnel.map((f) => f.count));
  return (
    <section className="rpt-panel ch-funnel-strip">
      <div className="ch-funnel-strip-head">
        <span className="eyebrow">FUNNEL · 5 阶段扫描</span>
        <span className="flow">
          {funnel[0].count.toLocaleString()} <span className="arr">→</span>{" "}
          {funnel[funnel.length - 1].count} <span className="tail">候选</span>
        </span>
      </div>
      <ol className="ch-funnel-strip-list">
        {funnel.map((f, i) => {
          const pct = Math.round((f.count / max) * 100);
          return (
            <li key={f.id} className="ch-funnel-strip-cell" data-i={i}>
              <div className="ch-funnel-strip-n">{i + 1}</div>
              <div className="ch-funnel-strip-lbl">{f.label}</div>
              <div className="ch-funnel-strip-count">{f.count.toLocaleString()}</div>
              <div className="ch-funnel-strip-bar" aria-hidden>
                <div className="ch-funnel-strip-fill" style={{ width: `${pct}%` }} />
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

/* ── 区域 2 左 · Radar 独立面板 ──────────────────────── */

function RadarPanel() {
  const s = CHANNEL_SESSION;
  const top = s.candidates[0];
  return (
    <section className="rpt-panel ch-radar-panel">
      <PanelPinHandle
        id="channel:radar"
        title="营销优先级雷达"
        subtitle={`获客 · ${top?.name ?? "—"}`}
        accentVar="--t-channel"
        agentKey="channel"
        href="/archive/channel"
        blurb={`8 维 P50 对标 · 该企业均分 ${Math.round(
          s.radar.reduce((a, d) => a + d.score, 0) / (s.radar.length || 1),
        )}`}
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">RADAR · 营销优先级 8 维</div>
          <h3 className="rpt-panel-title">{top?.name} · P50 对标</h3>
        </div>
        <span className="rpt-panel-meta">B++ 方案</span>
      </div>
      <div className="rpt-panel-body">
        <RadarView radar={s.radar} />
      </div>
    </section>
  );
}

/* ── 区域 2 右 · 候选企业列表 ────────────────────────── */

function CandidatesPanel({ liveCandidates }: { liveCandidates: Candidate[] | null }) {
  const s = CHANNEL_SESSION;
  /* F-005 Phase 2 · 优先 live (SSE done 真返) · 否则 CHANNEL_SESSION.candidates mock */
  const cs = liveCandidates ?? s.candidates;
  const isLive = liveCandidates !== null;
  return (
    <section className="rpt-panel ch-cand-panel" data-mode={isLive ? "live" : "mock"}>
      <PanelPinHandle
        id="channel:candidates"
        title="候选企业 Top 推荐"
        subtitle={`获客 · 共 ${cs.length} 家${isLive ? " · live" : ""}`}
        accentVar="--t-channel"
        agentKey="channel"
        href="/archive/channel"
        blurb={`Top ${cs.length} · 阈值 ${(s.match.similarity * 100).toFixed(0)}% · 首推 ${cs[0]?.name ?? "—"}`}
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">
            CANDIDATES · Top 推荐{isLive ? " · LIVE" : ""}
          </div>
          <h3 className="rpt-panel-title">
            Top {cs.length} · 共 {isLive ? cs.length : s.candidateCount} 家
          </h3>
        </div>
        <div className="rpt-panel-meta">
          阈值 {(s.match.similarity * 100).toFixed(0)}%
        </div>
      </div>
      <div className="rpt-panel-body">
        <CandidatesView candidates={cs} />
      </div>
    </section>
  );
}

/* ── 右栏 · Radar + Funnel + Candidates ─────────────── */

const OUTPUT_ACTIONS = [
  { key: "export", glyph: "⇩", label: "导出", title: "导出 Top 推荐列表 (.xlsx)" },
  { key: "crm",    glyph: "↗", label: "CRM",  title: "推送到 CRM · 待跟进" },
  { key: "assign", glyph: "☰", label: "分配", title: "分配给客户经理" },
  { key: "rerun",  glyph: "⟳", label: "重扫", title: "调参后重新扫描" },
] as const;

function ScoutOutputPanel() {
  const s = CHANNEL_SESSION;
  const [tab, setTab] = useState<"radar" | "funnel" | "cand">("radar");

  return (
    <section className="rpt-panel rpt-panel--preview">
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">OUTPUT · Scout 推荐</div>
          <h3 className="rpt-panel-title">Top {s.candidates.length} 候选</h3>
        </div>
        <div className="rpt-panel-meta">
          <span className="rpt-pv-pct">{s.candidateCount} 家</span>
        </div>
      </div>

      <div className="rpt-pv-toolbar" role="toolbar" aria-label="导出 / CRM / 分配 / 重扫">
        {OUTPUT_ACTIONS.map((a) => (
          <button key={a.key} type="button" className="rpt-pv-btn" title={a.title}>
            <span className="ic" aria-hidden>{a.glyph}</span>
            <span>{a.label}</span>
          </button>
        ))}
      </div>

      <nav className="rpt-pv-toc ch-out-tabs" aria-label="输出视图切换">
        <button
          type="button"
          className={tab === "radar" ? "on" : undefined}
          onClick={() => setTab("radar")}
        >
          <span className="a">§一</span>
          <span className="t">信号雷达</span>
        </button>
        <button
          type="button"
          className={tab === "funnel" ? "on" : undefined}
          onClick={() => setTab("funnel")}
        >
          <span className="a">§二</span>
          <span className="t">扫描 Funnel</span>
        </button>
        <button
          type="button"
          className={tab === "cand" ? "on" : undefined}
          onClick={() => setTab("cand")}
        >
          <span className="a">§三</span>
          <span className="t">Top 推荐</span>
        </button>
      </nav>

      <div className="rpt-pv-paper-wrap">
        <article className="rpt-pv-paper ch-out-paper" aria-label="Scout 推荐输出">
          <div className="rpt-pv-paper-head">
            <div className="doc-title">Scout · look-alike 推荐</div>
            <div className="doc-sub">
              {s.benchmarkName} · 阈值相似度 {(s.match.similarity * 100).toFixed(0)}% · 预览稿 v1
            </div>
          </div>
          {tab === "radar" && <RadarView radar={s.radar} />}
          {tab === "funnel" && <FunnelView funnel={s.funnel} />}
          {tab === "cand" && <CandidatesView candidates={s.candidates} />}
          <div className="rpt-pv-paper-foot">
            — 以上为 AI 初筛推荐稿 · 未经客户经理复核不得作为外呼名单 —
          </div>
        </article>
      </div>

      <footer className="rpt-pv-status">
        <span className="pg">视图 {tab === "radar" ? "1/3" : tab === "funnel" ? "2/3" : "3/3"}</span>
        <span className="sep">·</span>
        <span className="cov">
          候选 <b>{s.candidates.length}/{s.candidateCount}</b>
        </span>
        <span className="sep">·</span>
        <span className="qc" aria-label="QC 徽章">
          QC
          <span className="qc-chip" data-l="block">● {s.qcCounts.block}</span>
          <span className="qc-chip" data-l="warn">● {s.qcCounts.warn}</span>
          <span className="qc-chip" data-l="info">● {s.qcCounts.info}</span>
        </span>
      </footer>
    </section>
  );
}

const QUADRANT_LABEL: Record<RadarDimension["quadrant"], string> = {
  base: "基本盘",
  bonus: "加分项",
  demand: "需求信号",
  health: "合规健康",
  market: "可营销",
};

function RadarView({ radar }: { radar: RadarDimension[] }) {
  const data = radar.map((d) => ({
    axis: d.axis,
    score: d.score,
    benchmark: d.benchmark,
  }));
  const avgScore = Math.round(radar.reduce((a, b) => a + b.score, 0) / radar.length);
  const avgBench = Math.round(radar.reduce((a, b) => a + b.benchmark, 0) / radar.length);
  const lead = avgScore - avgBench;
  return (
    <section className="ch-rad-sec">
      <header className="ch-out-sec-head">
        <h4 className="ch-out-sec-title">
          <span className="rpt-pv-anchor">§一</span>
          <span>营销优先级 · 8 维评分</span>
        </h4>
        <div className="ch-out-legend">
          <span className="lg" data-k="score">● 该企业</span>
          <span className="lg" data-k="benchmark">○ 行业 P50</span>
        </div>
      </header>
      <div className="ch-rad-chart">
        <ResponsiveContainer width="100%" height={320}>
          <RadarChart data={data} outerRadius="72%">
            <PolarGrid stroke="var(--ink-20)" />
            <PolarAngleAxis dataKey="axis" tick={{ fill: "var(--ink-80)", fontSize: 11 }} />
            <PolarRadiusAxis
              domain={[0, 100]}
              tick={{ fill: "var(--ink-40)", fontSize: 9 }}
              axisLine={false}
            />
            <Radar
              name="行业 P50"
              dataKey="benchmark"
              stroke="var(--ink-48)"
              fill="var(--ink-48)"
              fillOpacity={0.08}
              strokeWidth={1.1}
              strokeDasharray="3 3"
            />
            <Radar
              name="该企业"
              dataKey="score"
              stroke="var(--agent)"
              fill="var(--agent)"
              fillOpacity={0.22}
              strokeWidth={1.8}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <div className="ch-rad-summary">
        <div className="ch-rad-summary-row">
          <span className="lbl">综合得分</span>
          <span className="v main">{avgScore}</span>
          <span className="sep">vs</span>
          <span className="v bench">P50 {avgBench}</span>
          <span className={`ch-rad-lead ${lead >= 0 ? "pos" : "neg"}`}>
            {lead >= 0 ? "+" : ""}{lead}
          </span>
        </div>
      </div>
      <ul className="ch-rad-legend">
        {radar.map((r) => {
          const delta = r.score - r.benchmark;
          return (
            <li key={r.axis} className="ch-rad-row" data-q={r.quadrant} title={r.note}>
              <span className="q-chip" data-q={r.quadrant}>{QUADRANT_LABEL[r.quadrant]}</span>
              <span className="axis">{r.axis}</span>
              <span className="pair">
                <span className="v score">{r.score}</span>
                <span className="sep">/</span>
                <span className="v bench">P50 {r.benchmark}</span>
                <span className={`delta ${delta >= 0 ? "pos" : "neg"}`}>
                  {delta >= 0 ? "+" : ""}{delta}
                </span>
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function FunnelView({ funnel }: { funnel: FunnelStage[] }) {
  const max = Math.max(...funnel.map((f) => f.count));
  return (
    <section className="ch-fn-sec">
      <header className="ch-out-sec-head">
        <h4 className="ch-out-sec-title">
          <span className="rpt-pv-anchor">§二</span>
          <span>5 阶段扫描漏斗</span>
        </h4>
        <div className="ch-out-meta">
          {funnel[0]?.count.toLocaleString()} → {funnel[funnel.length - 1]?.count}
        </div>
      </header>
      <ol className="ch-fn-list">
        {funnel.map((f, i) => {
          const pct = Math.round((f.count / max) * 100);
          const prev = i > 0 ? funnel[i - 1].count : f.count;
          const passRate = i > 0 ? Math.round((f.count / prev) * 100) : 100;
          return (
            <li key={f.id} className="ch-fn-row" data-i={i}>
              <div className="ch-fn-head">
                <span className="ch-fn-n">{i + 1}</span>
                <span className="ch-fn-lbl">{f.label}</span>
                <span className="ch-fn-count">{f.count.toLocaleString()}</span>
                {i > 0 && <span className="ch-fn-pass">透过 {passRate}%</span>}
              </div>
              <div className="ch-fn-bar" aria-hidden>
                <div className="ch-fn-bar-fill" style={{ width: `${pct}%` }} />
              </div>
              {f.detail && <div className="ch-fn-detail">{f.detail}</div>}
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function CandidatesView({ candidates }: { candidates: Candidate[] }) {
  return (
    <section className="ch-cd-sec">
      <header className="ch-out-sec-head">
        <h4 className="ch-out-sec-title">
          <span className="rpt-pv-anchor">§三</span>
          <span>Top {candidates.length} 推荐 · 相似度排序</span>
        </h4>
      </header>
      <ol className="ch-cd-list">
        {candidates.map((c, i) => (
          <CandidateCard key={c.id} rank={i + 1} c={c} />
        ))}
      </ol>
    </section>
  );
}

/* ── 右栏 · Signal Timeline (区域 3) ───────────────── */

const SIG_EVENT_LABEL: Record<SignalEvent["kind"], string> = {
  "biz-change": "工商",
  "bid-win":    "招投标",
  "recruit":    "招聘",
  "fund":       "投融资",
  "policy":     "资质",
  "legal":      "司法",
  "tax":        "纳税",
  "news":       "舆情",
};

function SignalTimelinePanel() {
  const s = CHANNEL_SESSION;
  const [activeId, setActiveId] = useState<string>(
    s.candidates.find((c) => c.timeline?.length)?.id ?? s.candidates[0]?.id ?? ""
  );
  const active = s.candidates.find((c) => c.id === activeId) ?? s.candidates[0];
  const events = active?.timeline ?? [];

  return (
    <section className="rpt-panel rpt-panel--tl ch-tl-panel">
      <PanelPinHandle
        id={`channel:timeline:${active?.id ?? "none"}`}
        title={`信号时间线 · ${active?.name ?? "—"}`}
        subtitle="获客 · 候选信号流"
        accentVar="--t-channel"
        agentKey="channel"
        href="/archive/channel"
        blurb={
          events.length
            ? `${events.length} 条聚合信号 · 最近 ${events[0]?.at ?? ""}`
            : "该候选暂无信号"
        }
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">TIMELINE · 候选信号流</div>
          <h3 className="rpt-panel-title">{active?.name}</h3>
        </div>
        <select
          className="rpt-tl-switch"
          aria-label="切换候选企业"
          value={activeId}
          onChange={(e) => setActiveId(e.target.value)}
        >
          {s.candidates.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
              {c.timeline?.length ? ` · ${c.timeline.length} 事件` : " · 无信号"}
            </option>
          ))}
        </select>
      </div>
      <div className="rpt-panel-body ch-tl-body">
        {events.length === 0 ? (
          <div className="ch-tl-empty">
            <span className="ic" aria-hidden>◌</span>
            <span>该候选暂无聚合信号流 · 将在下轮扫描后补全</span>
          </div>
        ) : (
          <ol className="ch-tl-list">
            {events.map((ev) => (
              <TimelineEvent key={ev.id} ev={ev} />
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}

function TimelineEvent({ ev }: { ev: SignalEvent }) {
  return (
    <li className="ch-tl-row" data-kind={ev.kind} data-sev={ev.severity}>
      <span className="ch-tl-dot" aria-hidden />
      <div className="ch-tl-card">
        <div className="ch-tl-meta">
          <span className="kind" data-kind={ev.kind}>{SIG_EVENT_LABEL[ev.kind]}</span>
          <span className="at">{ev.at}</span>
          <span className="sev" data-sev={ev.severity} aria-hidden>
            {ev.severity === "pos" ? "↑" : ev.severity === "neg" ? "↓" : "·"}
          </span>
        </div>
        <div className="ch-tl-title">{ev.title}</div>
        <div className="ch-tl-detail">{ev.detail}</div>
        <div className="ch-tl-source">
          <span className="ic" aria-hidden>◊</span>
          {ev.source.url ? (
            <a href={ev.source.url} target="_blank" rel="noreferrer">
              {ev.source.label}
            </a>
          ) : (
            <span>{ev.source.label}</span>
          )}
        </div>
      </div>
    </li>
  );
}

function CandidateCard({ rank, c }: { rank: number; c: Candidate }) {
  const simPct = Math.round(c.similarity * 100);
  const hasRisk = c.riskTags.length > 0;
  return (
    <li className="ch-cd-card" data-risk={hasRisk ? "yes" : "no"}>
      <header className="ch-cd-head">
        <div className="ch-cd-rank">#{rank}</div>
        <div className="ch-cd-title">
          <h5 className="ch-cd-name">{c.name}</h5>
          <div className="ch-cd-meta">
            {c.industry} · {c.geo} · {c.scale}
          </div>
        </div>
        <div className="ch-cd-sim">
          <div className="ch-cd-sim-pct">{simPct}%</div>
          <div className="ch-cd-sim-bar" aria-hidden>
            <div className="ch-cd-sim-fill" style={{ width: `${simPct}%` }} />
          </div>
          <div className="ch-cd-sim-lbl">相似度</div>
        </div>
      </header>
      <div className="ch-cd-body">
        <div className="ch-cd-sigs">
          <span className="lbl">命中信号</span>
          {c.signals.map((s) => (
            <span key={s} className="ch-cd-sig">
              {s}
            </span>
          ))}
        </div>
        {hasRisk && (
          <div className="ch-cd-risk">
            <span className="lbl">风险提示</span>
            {c.riskTags.map((r) => (
              <span key={r} className="ch-cd-risk-tag">
                {r}
              </span>
            ))}
          </div>
        )}
        <div className="ch-cd-prod">
          <span className="lbl">建议产品</span>
          {c.products.map((p) => (
            <span key={p} className="ch-cd-prod-tag">
              {p}
            </span>
          ))}
        </div>
        {c.note && <div className="ch-cd-note">{c.note}</div>}
      </div>
    </li>
  );
}
