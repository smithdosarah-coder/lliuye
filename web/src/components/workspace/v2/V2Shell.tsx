"use client";

/**
 * V2Shell — shared scaffolding for 6 mockup-v2 agent workspaces.
 * Source of truth: design_mockups/stage5/mockup-v2/{report,channel,credit,alert,compli,riskctrl}.html
 * All class names match the mockup 1:1 so mockup-v2.css (scoped under .ws-v2) applies.
 *
 * W2 builds DOM structure + controlled prop surface.
 * W1 wires data via props (messages, sseEvents, sections, etc.).
 */

import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";
import clsx from "clsx";

export type AgentKey = "report" | "channel" | "credit" | "alert" | "compli" | "riskctrl";

const AGENT_META: Record<AgentKey, { zh: string; en: string; label: string }> = {
  report:   { zh: "信贷报告", en: "Report",   label: "Credit Report Drafter" },
  channel:  { zh: "获客",     en: "Channel",  label: "Lookalike Acquisition" },
  credit:   { zh: "授信",     en: "Credit",   label: "Credit Decision Copilot" },
  alert:    { zh: "预警",     en: "Alert",    label: "Portfolio Sentinel" },
  compli:   { zh: "合规",     en: "Compli",   label: "Policy Conflict Finder" },
  riskctrl: { zh: "风控",     en: "RiskCtrl", label: "Policy DSL Studio" },
};

// Map legacy AgentKey from lib/agents ("compliance") to v2 key ("compli")
export function toV2Key(legacy: string): AgentKey {
  if (legacy === "compliance") return "compli";
  return legacy as AgentKey;
}

export type HeroProps = {
  eyebrowText: string;
  eyebrowAccent?: string;
  heroTitle: ReactNode;
  heroSub: ReactNode;
};

export type StageFlow = {
  n: string;
  nm: string;
  en: string;
  sub: ReactNode;
  state?: "done" | "live" | "";
};

export type TplItem = {
  key: string;
  name: string;
  tag: string;
  meta: string;
  spec: string;
  on?: boolean;
};

export type ApHead = {
  zh: string;          // 信贷报告 · 生成
  en: string;          // Credit Report Drafter
  ver: string;         // v7.23
  metas: Array<{ k: string; v: ReactNode; state?: "ok" | "warn" }>;
  health: string;      // LLM 在线 · DeepSeek
  cta?: { label: string; arrow?: string };
};

export type IntakeCell =
  | { kind: "drop"; title: string; sub: string; btn: string }
  | { kind: "opt"; k: string; v: ReactNode; on?: boolean; toggle?: boolean };

export type V2ShellProps = {
  agent: AgentKey;
  hero: HeroProps;
  apHead: ApHead;
  cap: { cn: string; em: string; k: string };
  stages: StageFlow[];
  tplTitle: { lbl: string; hint: ReactNode; k: string };
  tpls: TplItem[];
  intake: IntakeCell[];
  chatSlot: ReactNode;
  docSlot: ReactNode;
  auditSlot: ReactNode;
  /**
   * Optional demo run-state hook. When set, propagates `data-run` onto .ws-v2 so
   * scoped CSS can collapse/expand audit-strip and style intake feedback.
   * Existing 5 agents omit this — they continue rendering as before.
   */
  runState?: "idle" | "running" | "done";
};

export function V2Shell(props: V2ShellProps) {
  const { agent, hero, apHead, cap, stages, tplTitle, tpls, intake, runState } = props;
  const accentStyle: CSSProperties = {
    ["--t-accent" as string]: `var(--t-${agent})`,
  };

  return (
    <div className={clsx("ws-v2", `v-${agent}`)} data-run={runState ?? undefined}>
      {/* Hero · eyebrow + h1 + sub */}
      <div className="eyebrow">
        <span className="hot-dot" />
        <span>{hero.eyebrowText}</span>
        <span className="sep" />
        {hero.eyebrowAccent ? <em>{hero.eyebrowAccent}</em> : null}
      </div>
      <h1 className="hero-h1">{hero.heroTitle}</h1>
      <p className="hero-sub">{hero.heroSub}</p>

      {/* agent switch bar */}
      <div className="agent-bar">
        <Link href="/archive" className="back">
          <span className="a">←</span>
          <span>回到助手目录</span>
        </Link>
        <div className="ab-list">
          {(Object.keys(AGENT_META) as AgentKey[]).map((k) => (
            <Link
              key={k}
              href={`/archive/${k === "compli" ? "compliance" : k}`}
              className={clsx("ab", `t-${k}`, k === agent && "on")}
            >
              <span className="dot-agent" />
              <span>{AGENT_META[k].zh}</span>
              <em>{AGENT_META[k].en}</em>
            </Link>
          ))}
        </div>
      </div>

      <div className="router" data-view={`a/${agent}`}>
        <div className={`view v-${agent}`}>
          <section className={clsx("ap", `a-${agent}`)} style={accentStyle}>
            {/* ap-head */}
            <header className="ap-head">
              <div className="id">
                <div className="nm">
                  <span className="cn">{apHead.zh}</span>
                  <em>{apHead.en}</em>
                  <span className="ver">{apHead.ver}</span>
                </div>
                <div className="meta">
                  {apHead.metas.map((m, i) => (
                    <span key={i} className="mt">
                      <span className="k">{m.k}</span>
                      <span className={clsx("v", m.state)}>{m.v}</span>
                    </span>
                  ))}
                  <span className="health">
                    <span className="hp" />
                    {apHead.health}
                  </span>
                </div>
              </div>
              {apHead.cta ? (
                <button className="cta" type="button">
                  <span>{apHead.cta.label}</span>
                  <span className="a">{apHead.cta.arrow ?? "↗"}</span>
                </button>
              ) : null}
            </header>

            {/* cap */}
            <div className="cap">
              <div className="t">
                <span className="cn">{cap.cn}</span> <em>{cap.em}</em>
              </div>
              <div className="k">{cap.k}</div>
            </div>

            {/* stage-flow */}
            <div className="stage-flow">
              {stages.map((s, i) => (
                <div key={i} className={clsx("stg", s.state)}>
                  <div className="hd">
                    <span className="n">{s.n}</span>
                    <span className="nm">{s.nm}</span>
                    <em>{s.en}</em>
                  </div>
                  <div className="dot" />
                  <div className="sub">{s.sub}</div>
                </div>
              ))}
            </div>

            {/* tpl-strip */}
            <div className="tpl-strip">
              <div className="tpl-hd">
                <span className="lbl">{tplTitle.lbl}</span>
                <span className="hint">{tplTitle.hint}</span>
                <span className="k">{tplTitle.k}</span>
              </div>
              <div className="tpl-row">
                {tpls.map((t) => (
                  <button
                    key={t.key}
                    type="button"
                    className={clsx("tpl", t.on && "on")}
                    data-tpl={t.key}
                  >
                    <div className="tp-hd">
                      <span className="tp-nm">{t.name}</span>
                      <span className="tp-tag">{t.tag}</span>
                    </div>
                    <div className="tp-meta">{t.meta}</div>
                    <div className="tp-spec">{t.spec}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* intake-strip */}
            <div className="intake-strip">
              {intake.map((c, i) => {
                if (c.kind === "drop") {
                  return (
                    <div key={i} className="slot">
                      <span className="ic">↑</span>
                      <span className="text">
                        <span className="t">{c.title}</span>
                        <span className="s">{c.sub}</span>
                      </span>
                      <button type="button" className="pick">{c.btn}</button>
                    </div>
                  );
                }
                return (
                  <div key={i} className={clsx("cell-opt", c.on && "on")}>
                    <span className="k">{c.k}</span>
                    <span className="v">
                      {c.toggle ? <span className="tog" /> : null}
                      {c.v} {c.toggle ? null : <span className="chev">▾</span>}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* main-board */}
            <div className="main-board">
              <div className="chat-col">{props.chatSlot}</div>
              <div className="doc-col">{props.docSlot}</div>
            </div>

            {/* audit-strip */}
            <div className="audit-strip">{props.auditSlot}</div>
          </section>
        </div>
      </div>
    </div>
  );
}

/* ─── Sub-components for common slot fragments ─── */

export type ChatMessage = {
  side?: "agent" | "user";
  agentName?: string;
  sig: string;                // R. / 王.
  nameZh: string;             // 信贷报告·生成 / 王哲
  nameEn: string;             // Report / 华东客户经理
  ts: string;
  ref?: string;
  body: ReactNode;
  spineColor?: string;        // css var or color; defaults to current agent accent
};

export function ChatBlk({
  title,
  subTitle,
  kBadge,
  messages,
  seeds,
  placeholder,
}: {
  title: ReactNode;
  subTitle?: ReactNode;
  kBadge?: ReactNode;
  messages: ChatMessage[];
  seeds?: Array<{ q: string; body: ReactNode }>;
  placeholder?: string;
}) {
  return (
    <div className="blk">
      <div className="blk-hd">
        <div className="t">
          {title}
          {subTitle ? <em> {subTitle}</em> : null}
        </div>
        {kBadge ? <div className="k">{kBadge}</div> : null}
      </div>

      <div className="chat-thread">
        {messages.map((m, i) => {
          const isUser = m.side === "user";
          const spineVar = m.spineColor ?? "var(--t-accent)";
          const msgStyle: CSSProperties | undefined = isUser
            ? undefined
            : { ["--spine" as string]: spineVar };
          return (
            <div key={i} className={clsx("msg", isUser && "user")} style={msgStyle}>
              <div className="bd-hd">
                <span className="who">
                  <span className="sig">{m.sig}</span> {m.nameZh} <em>{m.nameEn}</em>
                </span>
                <span className="ts">{m.ts}</span>
                {m.ref ? <span className="ref">{m.ref}</span> : null}
              </div>
              <div className="tx">{m.body}</div>
            </div>
          );
        })}
      </div>

      {seeds && seeds.length ? (
        <div className="ask">
          {seeds.map((s, i) => (
            <button key={i} type="button" className="ask-seed">
              <span className="q">{s.q}</span>
              {s.body}
            </button>
          ))}
          <div className="ask-input">
            <input type="text" placeholder={placeholder ?? "继续追问…"} />
            <button type="button" className="attach" title="带材料">＋</button>
            <button type="button" className="send">↗</button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export type TraceLine = {
  ts: string;
  stgTag: string;           // ev · 01 / gn · 2.1 / au · 3
  tx: ReactNode;
  stage: "ev" | "gn" | "au";
  typing?: boolean;
};

export function SseBlk({ title, kBadge, lines }: { title: ReactNode; kBadge?: ReactNode; lines: TraceLine[] }) {
  return (
    <div className="blk">
      <div className="blk-hd">
        <div className="t">{title}</div>
        {kBadge ? <div className="k">{kBadge}</div> : null}
      </div>
      <div className="sse-mini">
        {lines.map((l, i) => (
          <div key={i} className={clsx("trace-line", `s-${l.stage}`)}>
            <span className="ts">{l.ts}</span>
            <span className="stg-tag">{l.stgTag}</span>
            <span className="tx">
              {l.tx}
              {l.typing ? <span className="trace-typing" /> : null}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export type DocSection = {
  n: string;
  name: string;
  en: string;
  state?: "ok" | "live" | "warn" | "pend";
  stateText: string;
  body: ReactNode;
  flag?: "live" | "pending";
};

export function DocWrap({
  docTitle,
  docSubtitle,
  metrics,
  sections,
}: {
  docTitle: ReactNode;
  docSubtitle?: ReactNode;
  metrics: ReactNode[];
  sections: DocSection[];
}) {
  return (
    <div className="doc-wrap">
      <div className="doc-head">
        <div className="doc-t">
          <span className="cn">{docTitle}</span>
          {docSubtitle ? <em>{docSubtitle}</em> : null}
        </div>
        <div className="doc-meta">
          {metrics.map((m, i) => (
            <span key={i}>
              {i > 0 ? <span className="sep">·</span> : null}
              <span>{m}</span>
            </span>
          ))}
        </div>
      </div>
      <div className="doc-body">
        {sections.map((s, i) => (
          <div key={i} className={clsx("sec", s.flag)}>
            <div className="sec-h">
              <span className="sec-n">{s.n}</span>
              <span className="sec-nm">{s.name}</span>
              <em>{s.en}</em>
              <span className={clsx("sec-st", s.state)}>{s.stateText}</span>
            </div>
            <div className="sec-body">{s.body}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export type QcMetric = { k: string; v: string; p: string; hot?: boolean };

export function AuditStrip({
  verdict,
  coverage,
  unfilled,
  qc,
}: {
  verdict: {
    k: string;
    v: ReactNode;
    tip: ReactNode;
    ctas: Array<{ label: string; primary?: boolean }>;
  };
  coverage: Array<{ k: string; v: ReactNode; hot?: boolean }>;
  unfilled: { k: string; items: ReactNode };
  qc: QcMetric[];
}) {
  return (
    <>
      <div className="verdict">
        <div className="k">{verdict.k}</div>
        <div className="v">{verdict.v}</div>
        <div className="tip">{verdict.tip}</div>
        <div className="cta-row">
          {verdict.ctas.map((c, i) => (
            <button key={i} type="button" className={clsx("ct", c.primary && "primary")}>
              {c.label}
            </button>
          ))}
        </div>
      </div>

      <div className="cov-col">
        <div className="cov-row">
          {coverage.map((m, i) => (
            <div key={i} className="m">
              <div className="k">{m.k}</div>
              <div className={clsx("v", m.hot && "hot")}>{m.v}</div>
            </div>
          ))}
        </div>
        <div className="unfilled">
          <span className="k">{unfilled.k}</span>
          {unfilled.items}
        </div>
      </div>

      <div className="qc-grid">
        {qc.map((q, i) => (
          <div key={i} className="qc">
            <span className="k">{q.k}</span>
            <span className={clsx("v", q.hot && "hot")}>
              {q.v}
              <span className="b" style={{ ["--p" as string]: q.p }} />
            </span>
          </div>
        ))}
      </div>
    </>
  );
}
