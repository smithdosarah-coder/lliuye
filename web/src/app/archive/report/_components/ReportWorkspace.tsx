"use client";

/**
 * /archive/report · Agent6 报告 (Press) workspace · 三栏对话式
 * 2026-04-21 redesign · 左 模板/材料/时间流 · 中 对话协作 · 右 报告预览
 *
 * P1: shell 骨架 + 5 panel 占位 · 消费 REPORT_SESSION mock (DONE · 53c2b4c)
 * P2: 左栏三块实装 · Template / Material / Timeline (DONE · c71540f)
 * P3: 中栏对话 (6 类 msg + AI thinking 展开) + Composer (DONE · 9d00d71)
 * P4: 右栏预览 · Toolbar / TOC / A4 / Field 3-state / QC inline tooltip / Status bar (本 commit)
 * P5: 接后端 SSE + session API
 *
 * 继承 canon A 章 8 条 primitive
 * Agent tint 注入：.v-archive--canon[data-agent="report"] { --agent: var(--t-report) }
 */

import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent, ChangeEvent } from "react";
import { MessagePinHandle } from "@/components/shell/MessagePinHandle";
import { ScanCTA } from "@/components/shared/ScanCTA";
import { CustomerSelector } from "@/components/shared/CustomerSelector";
import { PanelPinHandle } from "@/components/shell/PanelPinHandle";
import { ClaimText, EvidenceProvider, EvidenceTrail } from "@/components/evidence";
import { REPORT_EVIDENCE } from "@/components/evidence/fixtures";
import {
  REPORT_GLOBAL_STATS,
  REPORT_SESSION,
  type ConversationMessage,
  type PreviewField,
  type PreviewSection,
  type TimelineEvent,
} from "@/lib/mock/agent-report-session";

const AGENT_KEY = "report";
const AGENT_HREF = "/archive/report";
const AGENT_ACCENT = "--t-report";

export function ReportWorkspace() {
  const s = REPORT_SESSION;
  const coverPct = Math.round((s.coverage.filled / s.coverage.total) * 100);
  /* 2026-04-23 · demo 初始态 · 未扫描时数据模糊 · ScanCTA onDone 解锁 */
  const [scanned, setScanned] = useState(false);

  return (
    <EvidenceProvider
      items={REPORT_EVIDENCE.items}
      unfilledFields={REPORT_EVIDENCE.unfilledFields}
    >
      <div data-view="archive-report" data-scanned={scanned ? "yes" : "no"}>
        <ReportHero coverPct={coverPct} />
        <ReportPipelineBand />
        <div className="rpt-body">
          <aside className="rpt-side">
            <TemplatePanel />
            <MaterialPanel />
            <TimelinePanel />
          </aside>
          <main className="rpt-main">
            <ScanCTA
              label="生成报告"
              tone="report"
              onDone={() => setScanned(true)}
              steps={[
                { label: "解析企业材料 · OCR 识别", pct: 18 },
                { label: "字段结构化预填", pct: 42 },
                { label: "段落 Evidence-First 生成", pct: 66 },
                { label: "QC 终审 · 占位符检查", pct: 88 },
                { label: "导出 Word · 完成", pct: 100 },
              ]}
            />
            <ConversationPanel>
              <ReportComposer />
            </ConversationPanel>
          </main>
          <aside className="rpt-aux">
            <PreviewPanel coverPct={coverPct} />
          </aside>
        </div>
        <section className="ev-claim-summary" aria-label="Evidence-grounded 分析结论">
          <span className="ev-claim-summary-label">分析结论 · Evidence-grounded</span>
          <ClaimText text={REPORT_EVIDENCE.summary} />
        </section>
        <EvidenceTrail agentTone="report" />
      </div>
    </EvidenceProvider>
  );
}

/* ── Hero ────────────────────────────────────────────── */

function ReportHero({ coverPct }: { coverPct: number }) {
  const s = REPORT_SESSION;
  return (
    <header className="rpt-hero">
      <div className="rpt-hero-left">
        <div className="rpt-hero-badge" aria-hidden>◧</div>
        <div>
          <div className="rpt-hero-code">AGENT · 06 · PRESS</div>
          <h1 className="rpt-hero-title">
            报告 <em>Report Press.</em>
          </h1>
          <CustomerSelector className="rpt-hero__customer" />
          <div className="rpt-hero-sub">
            {s.clientName} · {s.amount} · {s.stage} · 字段覆盖 {coverPct}%
          </div>
        </div>
      </div>
      <div className="rpt-hero-stats">
        <Stat label="本周处理" value={REPORT_GLOBAL_STATS.weeklyProcessed} />
        <Stat label="成功率" value={REPORT_GLOBAL_STATS.successRate} />
        <Stat label="平均时长" value={REPORT_GLOBAL_STATS.avgDuration} />
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

/* ── Hero Band · 文档解析 4 阶段进度带（v2 差异化） ─── */

function ReportPipelineBand() {
  const s = REPORT_SESSION;
  const matTotal = s.materials.length;
  const matParsed = s.materials.filter((m) => m.parsed).length;
  const matPct = matTotal ? Math.round((matParsed / matTotal) * 100) : 0;

  const fieldPct = s.coverage.total
    ? Math.round((s.coverage.filled / s.coverage.total) * 100)
    : 0;

  const secTotal = s.preview.length;
  const secDone = s.preview.filter((p) => p.status === "ok").length;
  const secRun = s.preview.filter((p) => p.status === "running").length;
  const secPct = secTotal ? Math.round(((secDone + secRun * 0.5) / secTotal) * 100) : 0;

  const qcTotal = s.qcCounts.block + s.qcCounts.warn + s.qcCounts.info;
  const qcPct = s.qcCounts.block === 0 ? (s.qcCounts.warn === 0 ? 100 : 70) : 40;

  const stages = [
    {
      key: "mat",
      label: "原始材料",
      caption: `${matParsed} / ${matTotal} 已解析`,
      detail: matTotal - matParsed === 0 ? "全部就位" : `${matTotal - matParsed} 份待处理`,
      pct: matPct,
      state: matPct === 100 ? "done" : matPct > 0 ? "running" : "pending",
    },
    {
      key: "field",
      label: "字段抽取",
      caption: `${s.coverage.filled} / ${s.coverage.total} 字段`,
      detail: `${s.coverage.marked} 项标未填`,
      pct: fieldPct,
      state: fieldPct >= 90 ? "done" : fieldPct > 0 ? "running" : "pending",
    },
    {
      key: "sec",
      label: "段落生成",
      caption: `${secDone} / ${secTotal} 段完成`,
      detail: secRun > 0 ? `${secRun} 段生成中` : "—",
      pct: secPct,
      state: secPct >= 80 ? "done" : secPct > 0 ? "running" : "pending",
    },
    {
      key: "qc",
      label: "QC 终审",
      caption: `阻断 ${s.qcCounts.block} · 警告 ${s.qcCounts.warn}`,
      detail: `${qcTotal} 条问题`,
      pct: qcPct,
      state: s.qcCounts.block === 0 && s.qcCounts.warn === 0 ? "done" : s.qcCounts.block > 0 ? "pending" : "running",
    },
  ] as const;

  return (
    <section className="rpt-panel report-band" aria-label="报告生成流水线">
      <PanelPinHandle
        id="report:pipeline"
        title="报告生成流水线"
        subtitle={`${matParsed}/${matTotal} 材料 · ${secDone}/${secTotal} 段`}
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb="材料 → 字段 → 段落 → QC"
      />
      <div className="report-band-head">
        <span className="eyebrow">PIPELINE · 材料 → 字段 → 段落 → QC</span>
        <span className="flow">
          <b>{matParsed}</b> 份材料 <span className="arr">→</span>{" "}
          <b>{s.coverage.filled}</b> 字段 <span className="arr">→</span>{" "}
          <b>{secDone}</b> / {secTotal} 段 <span className="arr">→</span>{" "}
          <b>QC {s.qcCounts.block ? "阻断" : "通过"}</b>
        </span>
      </div>
      <ol className="report-band-list">
        {stages.map((st, i) => (
          <li key={st.key} className="report-band-cell" data-state={st.state} data-i={i}>
            <div className="report-band-n">{i + 1}</div>
            <div className="report-band-body">
              <div className="report-band-row">
                <span className="lbl">{st.label}</span>
                <span className="pct">{st.pct}%</span>
              </div>
              <div className="report-band-bar" aria-hidden>
                <div className="report-band-fill" style={{ width: `${st.pct}%` }} />
              </div>
              <div className="report-band-caption">{st.caption}</div>
              <div className="report-band-detail">{st.detail}</div>
            </div>
            {i < stages.length - 1 && <span className="report-band-arrow" aria-hidden>›</span>}
          </li>
        ))}
      </ol>
    </section>
  );
}

/* ── 左栏 · Template ────────────────────────────────── */

function TemplatePanel() {
  const tpl = REPORT_SESSION.template;
  const avail = REPORT_SESSION.availableTemplates;
  const cov = REPORT_SESSION.coverage;
  const pct = Math.round((cov.filled / cov.total) * 100);
  const R = 26;
  const CIRC = 2 * Math.PI * R;
  const FILL = (pct / 100) * CIRC;

  return (
    <section className="rpt-panel rpt-panel--tpl">
      <PanelPinHandle
        id="report:template"
        title={`模板 · ${tpl.name}`}
        subtitle={`覆盖 ${pct}% · ${cov.filled}/${cov.total}`}
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb={`${tpl.version} · ${cov.marked} 项标未填`}
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">TEMPLATE · 模板</div>
          <h3 className="rpt-panel-title">{tpl.name}</h3>
        </div>
        <span className="rpt-panel-meta">{tpl.version}</span>
      </div>
      <div className="rpt-panel-body rpt-tpl-body">
        <div className="rpt-tpl-card">
          <svg
            className="rpt-tpl-ring"
            width="68"
            height="68"
            viewBox="0 0 68 68"
            aria-hidden
          >
            <circle cx="34" cy="34" r={R} className="rpt-tpl-ring-track" />
            <circle
              cx="34"
              cy="34"
              r={R}
              className="rpt-tpl-ring-fill"
              strokeDasharray={`${FILL.toFixed(2)} ${CIRC.toFixed(2)}`}
              transform="rotate(-90 34 34)"
            />
            <text
              x="34"
              y="34"
              className="rpt-tpl-ring-pct"
              textAnchor="middle"
              dominantBaseline="central"
            >
              {pct}%
            </text>
          </svg>
          <div className="rpt-tpl-stats">
            <div>
              <span className="num">{cov.filled}</span>
              <span className="lbl">已填</span>
            </div>
            <div>
              <span className="num">{cov.marked}</span>
              <span className="lbl">标未填</span>
            </div>
            <div>
              <span className="num">{cov.total}</span>
              <span className="lbl">总项</span>
            </div>
          </div>
        </div>
        <div className="rpt-tpl-actions">
          <button className="rpt-btn rpt-btn--ghost" type="button">
            <span aria-hidden>⇪</span>上传模板
          </button>
          <button className="rpt-btn rpt-btn--ghost" type="button">
            <span aria-hidden>▤</span>模板库
          </button>
        </div>
        <div className="rpt-tpl-avail">
          <div className="rpt-tpl-avail-lbl">其他可选</div>
          {avail
            .filter((t) => t.id !== tpl.id)
            .map((t) => (
              <button
                key={t.id}
                className="rpt-tpl-avail-row"
                type="button"
              >
                <span className="name">{t.name}</span>
                <span className="meta">
                  {t.version} · {t.fieldTotal} 项
                </span>
              </button>
            ))}
        </div>
      </div>
    </section>
  );
}

/* ── 左栏 · Material ────────────────────────────────── */

function MaterialPanel() {
  const mats = REPORT_SESSION.materials;
  const parsed = mats.filter((m) => m.parsed).length;
  const pending = mats.length - parsed;
  return (
    <section className="rpt-panel rpt-panel--mat">
      <PanelPinHandle
        id="report:materials"
        title={`材料 · ${mats.length} 份`}
        subtitle={`${parsed} 已解析 · ${pending} 待处理`}
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb="pdf · docx · xlsx · img"
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">MATERIALS · 材料</div>
          <h3 className="rpt-panel-title">
            {mats.length} 份 · {parsed} 已解析
          </h3>
        </div>
        <span className="rpt-panel-meta">{pending} 待处理</span>
      </div>
      <div className="rpt-panel-body rpt-mat-body">
        <button type="button" className="rpt-mat-drop" aria-label="上传材料">
          <span className="rpt-mat-drop-ic" aria-hidden>⇪</span>
          <span className="rpt-mat-drop-lbl">拖拽上传 · 或点击浏览</span>
          <span className="rpt-mat-drop-sub">pdf · docx · xlsx · img ≤ 30 MB</span>
        </button>
        <div className="rpt-mat-grid">
          {mats.map((m) => (
            <article
              key={m.id}
              className={`rpt-mat-card ${m.parsed ? "ok" : "pending"}`}
            >
              <header className="rpt-mat-head">
                <span className="rpt-mat-kind" data-k={m.kind}>
                  {m.kind}
                </span>
                <span
                  className={`rpt-mat-dot ${m.parsed ? "ok" : "pending"}`}
                  aria-hidden
                />
              </header>
              <div className="rpt-mat-name" title={m.name}>
                {m.name}
              </div>
              <div className="rpt-mat-meta">
                {m.pages} 页 · {m.bytes}
              </div>
              <div className="rpt-mat-note">{m.parseNote}</div>
              {m.linkedSections.length > 0 && (
                <div className="rpt-mat-links">
                  {m.linkedSections.map((sc) => (
                    <span key={sc} className="rpt-mat-link">
                      {sc}
                    </span>
                  ))}
                </div>
              )}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ── 左栏 · Timeline ────────────────────────────────── */

const TL_KIND_LABEL: Record<TimelineEvent["kind"], string> = {
  "template.select": "模板",
  "material.upload": "上传",
  "material.parsed": "解析",
  "ai.question": "AI 问",
  "user.reply": "回复",
  "section.done": "段落",
  "qc.run": "QC",
  export: "导出",
};

function TimelinePanel() {
  const evs = REPORT_SESSION.timeline;
  const recent = REPORT_SESSION.recentSessions;
  return (
    <section className="rpt-panel rpt-panel--tl">
      <PanelPinHandle
        id="report:timeline"
        title={`时间流 · ${evs.length} 事件`}
        subtitle="本 session"
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb={evs[0] ? `最新 · ${evs[0].label}` : ""}
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">TIMELINE · 时间流</div>
          <h3 className="rpt-panel-title">
            本 session · {evs.length} 事件
          </h3>
        </div>
        <select
          className="rpt-tl-switch"
          aria-label="切换 session"
          defaultValue={REPORT_SESSION.id}
        >
          {recent.map((r) => (
            <option key={r.id} value={r.id}>
              {r.clientName}
            </option>
          ))}
        </select>
      </div>
      <div className="rpt-panel-body rpt-tl-body">
        <ol className="rpt-tl-list">
          {evs.map((ev) => (
            <li key={ev.id} className="rpt-tl-ev" data-prio={ev.priority}>
              <span className="rpt-tl-bar" aria-hidden />
              <div className="rpt-tl-row">
                <span className="rpt-tl-kind">{TL_KIND_LABEL[ev.kind]}</span>
                <span className="rpt-tl-at">{ev.at}</span>
              </div>
              <div className="rpt-tl-label">{ev.label}</div>
              {ev.detail && <div className="rpt-tl-detail">{ev.detail}</div>}
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

/* ── 中栏 · Conversation (6 kinds) ──────────────────── */

function ConversationPanel({ children }: { children?: React.ReactNode }) {
  const msgs = REPORT_SESSION.conversation;
  const s = REPORT_SESSION;
  return (
    <section className="rpt-panel rpt-panel--conv rpt-panel--conv-docked">
      <PanelPinHandle
        id="report:conversation"
        title="对话协作"
        subtitle={`${s.clientName} · ${msgs.length} 条`}
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb={`覆盖 ${s.coverage.filled}/${s.coverage.total} · 阻断 ${s.qcCounts.block}`}
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">CONVERSATION · 对话协作</div>
          <h3 className="rpt-panel-title">
            {s.clientName} · {msgs.length} 条
          </h3>
        </div>
        <span className="rpt-panel-meta">
          覆盖 {s.coverage.filled} / {s.coverage.total} · 阻断{" "}
          {s.qcCounts.block}
        </span>
      </div>
      <div className="rpt-panel-body rpt-conv-body">
        <ol className="rpt-conv-list">
          {msgs.map((m) => (
            <ConversationItem key={m.id} msg={m} />
          ))}
        </ol>
      </div>
      {children}
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

function truncate(s: string, n: number): string {
  const flat = s.replace(/\s+/g, " ").trim();
  return flat.length > n ? `${flat.slice(0, n - 1)}…` : flat;
}

function msgPinProps(msg: ConversationMessage, speaker: string) {
  return {
    id: `report:msg:${msg.id}`,
    title: truncate(msg.content, 42),
    subtitle: `${speaker} · ${msg.at}`,
    accentVar: AGENT_ACCENT,
    agentKey: AGENT_KEY,
    href: AGENT_HREF,
    fullText: msg.content,
  };
}

function SystemEventMsg({ msg }: { msg: ConversationMessage }) {
  return (
    <li className="rpt-msg rpt-msg--sys">
      <MessagePinHandle {...msgPinProps(msg, "系统")} />
      <span className="rpt-msg-sys-chip">
        <span aria-hidden>◎</span> {msg.content}
      </span>
      <span className="rpt-msg-at">{msg.at}</span>
    </li>
  );
}

function AiQuestionMsg({ msg }: { msg: ConversationMessage }) {
  return (
    <li className="rpt-msg rpt-msg--ai rpt-msg--ask">
      <MessagePinHandle {...msgPinProps(msg, "AI · 问")} />
      <div className="rpt-msg-avatar" aria-hidden>◧</div>
      <div className="rpt-msg-body">
        <div className="rpt-msg-meta">
          <span className="rpt-msg-who">AI · Agent6</span>
          {msg.fieldRef && (
            <span className="rpt-msg-fieldref">{msg.fieldRef}</span>
          )}
          <span className="rpt-msg-at">{msg.at}</span>
        </div>
        <div className="rpt-msg-card rpt-msg-card--ask">
          <span className="rpt-msg-card-ic" aria-hidden>?</span>
          <span className="rpt-msg-card-text">{msg.content}</span>
        </div>
      </div>
    </li>
  );
}

function AiResponseMsg({ msg }: { msg: ConversationMessage }) {
  return (
    <li className="rpt-msg rpt-msg--ai">
      <MessagePinHandle {...msgPinProps(msg, "AI · Agent6")} />
      <div className="rpt-msg-avatar" aria-hidden>◧</div>
      <div className="rpt-msg-body">
        <div className="rpt-msg-meta">
          <span className="rpt-msg-who">AI · Agent6</span>
          {msg.fieldRef && (
            <span className="rpt-msg-fieldref">{msg.fieldRef}</span>
          )}
          <span className="rpt-msg-at">{msg.at}</span>
        </div>
        <div className="rpt-msg-card">
          <div className="rpt-msg-card-text">{msg.content}</div>
          {msg.sectionDiff && (
            <div className="rpt-msg-diff">
              <div className="rpt-msg-diff-lbl">
                回填 {msg.sectionDiff.sectionAnchor}
              </div>
              <div className="rpt-msg-diff-after">
                {msg.sectionDiff.after}
              </div>
            </div>
          )}
        </div>
      </div>
    </li>
  );
}

function AiThinkingMsg({ msg }: { msg: ConversationMessage }) {
  const [open, setOpen] = useState(false);
  const steps = msg.thinking?.steps ?? [];
  return (
    <li className="rpt-msg rpt-msg--ai rpt-msg--thinking">
      <MessagePinHandle {...msgPinProps(msg, "AI · thinking")} />
      <div
        className="rpt-msg-avatar rpt-msg-avatar--thinking"
        aria-hidden
      >
        ◧
      </div>
      <div className="rpt-msg-body">
        <div className="rpt-msg-meta">
          <span className="rpt-msg-who">AI · thinking</span>
          <span className="rpt-msg-at">{msg.at}</span>
        </div>
        <button
          type="button"
          className="rpt-msg-think"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          <span className="rpt-msg-think-text">{msg.content}</span>
          <span className="rpt-msg-think-caret" aria-hidden>
            {open ? "▾" : "▸"}
          </span>
        </button>
        {open && steps.length > 0 && (
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
      </div>
    </li>
  );
}

function UserReplyMsg({ msg }: { msg: ConversationMessage }) {
  return (
    <li className="rpt-msg rpt-msg--user">
      <MessagePinHandle {...msgPinProps(msg, "王哲")} />
      <div className="rpt-msg-body rpt-msg-body--user">
        <div className="rpt-msg-meta rpt-msg-meta--user">
          <span className="rpt-msg-at">{msg.at}</span>
          <span className="rpt-msg-who">客户经理 · 王哲</span>
        </div>
        <div className="rpt-msg-card rpt-msg-card--user">{msg.content}</div>
      </div>
      <div className="rpt-msg-avatar rpt-msg-avatar--user" aria-hidden>
        王
      </div>
    </li>
  );
}

function UserCommandMsg({ msg }: { msg: ConversationMessage }) {
  return (
    <li className="rpt-msg rpt-msg--user rpt-msg--cmd">
      <MessagePinHandle {...msgPinProps(msg, "王哲 · 指令")} />
      <div className="rpt-msg-body rpt-msg-body--user">
        <div className="rpt-msg-meta rpt-msg-meta--user">
          <span className="rpt-msg-at">{msg.at}</span>
          <span className="rpt-msg-who">客户经理 · /command</span>
        </div>
        <div className="rpt-msg-card rpt-msg-card--cmd">
          <code>{msg.content}</code>
        </div>
      </div>
      <div className="rpt-msg-avatar rpt-msg-avatar--user" aria-hidden>
        王
      </div>
    </li>
  );
}

/* ── 中栏 · Composer ────────────────────────────────── */

type ComposerHint = "idle" | "slash" | "mention" | "section";

function ReportComposer() {
  const [value, setValue] = useState("");
  const [hint, setHint] = useState<ComposerHint>("idle");
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 180) + "px";
  }, [value]);

  function handleKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
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
    else if (last === "#") setHint("section");
    else setHint("idle");
  }

  function submit() {
    if (!value.trim()) return;
    setValue("");
    setHint("idle");
  }

  const materialCount = REPORT_SESSION.materials.length;
  const sectionCount = REPORT_SESSION.preview.length;

  return (
    <div className="rpt-composer-slot rpt-composer" data-hint={hint}>
      <div className="rpt-composer-bar">
        <textarea
          ref={taRef}
          className="rpt-composer-ta"
          placeholder="回复 AI 提问 · 输入 / 触发指令 · @ 引用材料 · # 跳章节"
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
          <kbd>⌘↩</kbd>
        </button>
      </div>
      <div className="rpt-composer-hints">
        <span
          className="rpt-composer-hint"
          data-active={hint === "slash"}
        >
          <kbd>/</kbd> 指令 · QC / rewrite / export
        </span>
        <span
          className="rpt-composer-hint"
          data-active={hint === "mention"}
        >
          <kbd>@</kbd> 材料 · {materialCount} 份
        </span>
        <span
          className="rpt-composer-hint"
          data-active={hint === "section"}
        >
          <kbd>#</kbd> 章节 · {sectionCount} §
        </span>
      </div>
    </div>
  );
}

/* ── 右栏 · 预览 (P4) ────────────────────────────────── */

const TOOLBAR_ACTIONS = [
  { key: "word",  glyph: "⇩", label: "Word",  title: "下载 Word (.docx)" },
  { key: "pdf",   glyph: "⇩", label: "PDF",   title: "导出 PDF" },
  { key: "share", glyph: "↗", label: "分享",  title: "生成只读分享链接" },
  { key: "vers",  glyph: "⟳", label: "版本",  title: "版本时光机 · 对比历史稿" },
  { key: "print", glyph: "⎙", label: "打印",  title: "打印预览" },
] as const;

function PreviewPanel({ coverPct }: { coverPct: number }) {
  const s = REPORT_SESSION;
  const sections = s.preview;
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeAnchor, setActiveAnchor] = useState<string>(sections[0]?.anchor ?? "§一");

  function scrollTo(id: string) {
    const root = scrollRef.current;
    if (!root) return;
    const el = root.querySelector<HTMLElement>(`#pv-${id}`);
    if (!el) return;
    const rRect = root.getBoundingClientRect();
    const eRect = el.getBoundingClientRect();
    root.scrollTo({
      top: root.scrollTop + eRect.top - rRect.top - 10,
      behavior: "smooth",
    });
  }

  useEffect(() => {
    const root = scrollRef.current;
    if (!root) return;
    const io = new IntersectionObserver(
      (entries) => {
        const hit = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (!hit) return;
        const id = hit.target.id.replace(/^pv-/, "");
        const sec = sections.find((x) => x.id === id);
        if (sec) setActiveAnchor(sec.anchor);
      },
      { root, rootMargin: "-18% 0px -60% 0px", threshold: [0, 0.4, 0.8] },
    );
    sections.forEach((sec) => {
      const el = root.querySelector(`#pv-${sec.id}`);
      if (el) io.observe(el);
    });
    return () => io.disconnect();
  }, [sections]);

  return (
    <section className="rpt-panel rpt-panel--preview">
      <PanelPinHandle
        id="report:preview"
        title={`报告预览 · ${coverPct}%`}
        subtitle={s.clientName}
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb={`${sections.length} 章节 · ${s.amount}`}
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">PREVIEW · 报告预览</div>
          <h3 className="rpt-panel-title">{s.clientName}</h3>
        </div>
        <div className="rpt-panel-meta">
          <span className="rpt-pv-pct">{coverPct}%</span>
        </div>
      </div>

      <div className="rpt-pv-toolbar" role="toolbar" aria-label="导出 / 分享 / 版本 / 打印">
        {TOOLBAR_ACTIONS.map((a) => (
          <button key={a.key} type="button" className="rpt-pv-btn" title={a.title}>
            <span className="ic" aria-hidden>{a.glyph}</span>
            <span>{a.label}</span>
          </button>
        ))}
      </div>

      <nav className="rpt-pv-toc" aria-label="章节目录">
        {sections.map((sec) => (
          <button
            key={sec.id}
            type="button"
            className={activeAnchor === sec.anchor ? "on" : undefined}
            data-status={sec.status}
            onClick={() => scrollTo(sec.id)}
            title={`${sec.anchor} ${sec.title} · ${sec.filled}/${sec.total}`}
          >
            <span className="a">{sec.anchor}</span>
            <span className="t">{sec.title}</span>
          </button>
        ))}
      </nav>

      <div ref={scrollRef} className="rpt-pv-paper-wrap">
        <article className="rpt-pv-paper" aria-label="A4 报告预览">
          <div className="rpt-pv-paper-head">
            <div className="doc-title">{s.template.name}</div>
            <div className="doc-sub">
              {s.clientName} · 拟授信 {s.amount} · 预览稿 v0.86
            </div>
          </div>
          {sections.map((sec) => (
            <SectionView key={sec.id} section={sec} />
          ))}
          <div className="rpt-pv-paper-foot">
            — 以上为 AI 协作预览稿 · 未经人工终审不得作为正式决策依据 —
          </div>
        </article>
      </div>

      <footer className="rpt-pv-status">
        <span className="pg">页 1/3</span>
        <span className="sep">·</span>
        <span className="cov">
          覆盖 <b>{s.coverage.filled}/{s.coverage.total}</b>
          <span className="pct"> ({coverPct}%)</span>
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

function SectionView({ section }: { section: PreviewSection }) {
  const hasMarked = section.marked > 0;
  return (
    <section id={`pv-${section.id}`} className="rpt-pv-sec" data-status={section.status}>
      <header className="rpt-pv-sec-head">
        <h4 className="rpt-pv-sec-title">
          <span className="rpt-pv-anchor">{section.anchor}</span>
          <span>{section.title}</span>
          <SectionStatusDot status={section.status} />
        </h4>
        <div className="rpt-pv-sec-stats">
          <span className="stat">
            字段 <b>{section.filled}</b>/<b>{section.total}</b>
          </span>
          <span className="sep">·</span>
          <span className="stat">证据 {Math.round(section.evidenceRate * 100)}%</span>
          {hasMarked && (
            <>
              <span className="sep">·</span>
              <span className="stat warn">{section.marked} 项未填</span>
            </>
          )}
        </div>
      </header>
      {section.content && <p className="rpt-pv-sec-content">{section.content}</p>}
      <div className="rpt-pv-fields" role="list">
        {section.fields.map((f) => (
          <FieldChip key={f.id} field={f} />
        ))}
      </div>
    </section>
  );
}

function SectionStatusDot({ status }: { status: PreviewSection["status"] }) {
  const labelMap: Record<PreviewSection["status"], string> = {
    ok: "已定稿",
    "needs-review": "待复核",
    running: "生成中",
    pending: "待处理",
  };
  return (
    <span className="rpt-pv-sec-dot" data-s={status} title={labelMap[status]} aria-label={labelMap[status]} />
  );
}

function FieldChip({ field }: { field: PreviewField }) {
  const qcGlyph = field.qc
    ? field.qc.level === "block"
      ? "!"
      : field.qc.level === "warn"
        ? "△"
        : "i"
    : null;
  return (
    <div className="rpt-pv-fc" data-state={field.state} data-qc={field.qc?.level} role="listitem">
      <div className="rpt-pv-fc-lbl">{field.label}</div>
      <div className="rpt-pv-fc-val">
        {field.state === "unfilled" ? (
          <span className="unfilled">未能自动填写</span>
        ) : (
          <>{field.value ?? "—"}</>
        )}
      </div>
      {field.source && field.source !== "—" && (
        <div className="rpt-pv-fc-src" title={field.source}>
          ← {field.source}
        </div>
      )}
      {field.qc && qcGlyph && (
        <span className="rpt-pv-fc-qc" data-l={field.qc.level} tabIndex={0}>
          <span className="g" aria-hidden>{qcGlyph}</span>
          <span className="tip" role="tooltip">
            <b>{field.qc.level === "block" ? "阻断" : field.qc.level === "warn" ? "警告" : "提示"}</b>
            {" · "}
            {field.qc.detail}
          </span>
        </span>
      )}
    </div>
  );
}
