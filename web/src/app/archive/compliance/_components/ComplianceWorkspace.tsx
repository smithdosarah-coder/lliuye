"use client";

/**
 * /archive/compliance · Agent 05 LEDGER · 对话式合规扫描 workspace（canon 横向套 2026-04-21 H5）
 * 左：query + policies + docs + pipeline + recent /
 * 中：对话 + ComplianceComposer /
 * 右：冲突矩阵（doc × clause）· 扫描漏斗 · 政策 timeline 三切换
 * 壳类：.v-archive--canon[data-agent="compliance"] → --agent = var(--t-compli) 墨绿
 */

import { Fragment, useEffect, useRef, useState, type CSSProperties } from "react";
import {
  COMPLIANCE_GLOBAL_STATS,
  COMPLIANCE_SESSION,
  type CellDetail,
  type ClauseMapRow,
  type ComplianceQuery,
  type ComplianceRecentSession,
  type Conflict,
  type ConversationMessage,
  type FunnelStage,
  type InternalDoc,
  type MatrixCell,
  type PipelineStep,
  type PolicyRef,
  type PolicyTimelineItem,
  type PolicyUpload,
  type RevisionAdvice,
} from "@/lib/mock/agent-compliance-session";
import { PanelPinHandle } from "@/components/shell/PanelPinHandle";
import { MessagePinHandle } from "@/components/shell/MessagePinHandle";
import {
  ClaimText,
  EvidenceProvider,
  EvidenceTrail,
  UnfilledFields,
} from "@/components/evidence";
import { COMPLIANCE_EVIDENCE } from "@/components/evidence/fixtures";

/** 截断消息文本作 pin title · 尾部加 …（与 channel 同构） */
function msgTitle(raw: string): string {
  const flat = raw.replace(/\s+/g, " ").trim();
  return flat.length > 42 ? `${flat.slice(0, 40)}…` : flat;
}

function msgPinProps(msg: ConversationMessage, speaker: string) {
  return {
    id: `compliance:msg:${msg.id}`,
    title: msgTitle(msg.content),
    subtitle: `${speaker} · ${msg.at}`,
    accentVar: "--t-compli",
    agentKey: "compliance",
    href: "/archive/compliance",
    fullText: msg.content,
  };
}

type OutputTab = "matrix" | "funnel" | "timeline";

export default function ComplianceWorkspace() {
  const session = COMPLIANCE_SESSION;
  const [tab, setTab] = useState<OutputTab>("matrix");

  return (
    <EvidenceProvider
      items={COMPLIANCE_EVIDENCE.items}
      unfilledFields={COMPLIANCE_EVIDENCE.unfilledFields}
    >
    <div className="rpt-workspace">
      <HeroSection
        weeklyProcessed={COMPLIANCE_GLOBAL_STATS.weeklyProcessed}
        conflictRate={COMPLIANCE_GLOBAL_STATS.conflictRate}
        avgDuration={COMPLIANCE_GLOBAL_STATS.avgDuration}
        objective={session.objective}
        stage={session.stage}
        updated={session.updated}
        qcCounts={session.qcCounts}
      />

      <UploadRail
        innerUploads={session.innerPolicyUploads}
        outerUploads={session.outerPolicyUploads}
      />

      <PolicyTicker
        policies={session.policies}
        timeline={session.timeline}
        conflicts={session.conflicts}
      />

      <div className="rpt-grid">
        <aside className="rpt-col rpt-col--left">
          <QueryPanel q={session.query} />
          <PoliciesPanel policies={session.policies} />
          <DocsPanel docs={session.docs} />
          <PipelinePanel steps={session.pipeline} />
          <RecentPanel recent={session.recentSessions} />
        </aside>

        <section className="rpt-col rpt-col--mid">
          <ConversationPanel msgs={session.conversation} />
          <ComplianceComposer />
        </section>

        <section className="rpt-col rpt-col--right">
          <OutputPanel
            tab={tab}
            onTabChange={setTab}
            matrix={session.matrix}
            docs={session.docs}
            clauses={session.clauses}
            conflicts={session.conflicts}
            funnel={session.funnel}
            timeline={session.timeline}
            cellDetails={session.cellDetails}
          />
        </section>
      </div>

      <RevisionPanel advices={session.revisionAdvices} />

      <section className="ev-claim-summary" aria-label="Evidence-grounded 分析结论">
        <span className="ev-claim-summary-label">分析结论 · Evidence-grounded</span>
        <ClaimText text={COMPLIANCE_EVIDENCE.summary} />
      </section>
      <UnfilledFields />
      <EvidenceTrail agentTone="compliance" />
    </div>
    </EvidenceProvider>
  );
}

/* ────────────────────── UPLOAD RAIL · Codex 融合头部 ────────────────────── */

const COMPARE_STEPS: { label: string; pct: number }[] = [
  { label: "解析行内政策 · 匹配版本", pct: 22 },
  { label: "解析外部政策 · 抽取条款", pct: 46 },
  { label: "映射条款关系 · 对齐字段", pct: 70 },
  { label: "识别冲突与差异 · 生成建议", pct: 92 },
  { label: "比对完成 · 可查看对照纸", pct: 100 },
];

function UploadRail(p: {
  innerUploads: PolicyUpload[];
  outerUploads: PolicyUpload[];
}) {
  const [running, setRunning] = useState(false);
  const [stepIdx, setStepIdx] = useState<number>(-1); // -1 = 未开始；4 = 完成
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  function startCompare() {
    if (running) return;
    setRunning(true);
    setStepIdx(0);
    let i = 0;
    timerRef.current = setInterval(() => {
      i += 1;
      if (i >= COMPARE_STEPS.length) {
        setStepIdx(COMPARE_STEPS.length - 1);
        setRunning(false);
        if (timerRef.current) clearInterval(timerRef.current);
      } else {
        setStepIdx(i);
      }
    }, 520);
  }

  const done = stepIdx === COMPARE_STEPS.length - 1 && !running;
  const pct = stepIdx >= 0 ? COMPARE_STEPS[stepIdx].pct : 0;
  const flowText =
    stepIdx < 0
      ? "点击按钮开始新一轮政策比对"
      : COMPARE_STEPS[stepIdx].label;

  return (
    <section className="rpt-panel compliance-upload" aria-label="政策上传与比对">
      <PanelPinHandle
        id="compliance:upload-rail"
        title="政策上传与比对"
        subtitle="行内 + 外部 · CTA 启动 5 步比对"
        accentVar="--t-compli"
        agentKey="compliance"
        href="/archive/compliance"
        blurb={`行内 ${p.innerUploads.length} 份 · 外部 ${p.outerUploads.length} 份 · 点击「开始政策比对」`}
      />
      <div className="compliance-upload-head">
        <div>
          <div className="compliance-upload-eyebrow">POLICY INSPECTION DESK</div>
          <h3 className="compliance-upload-title">上传政策材料 · 启动条款对比</h3>
          <p className="compliance-upload-sub">
            同时维护行内口径与外部监管口径，版本可追溯；点击"开始政策比对"触发 5 步异步流程。
          </p>
        </div>
        <div className="compliance-upload-cta">
          <button
            type="button"
            className="compliance-upload-btn"
            onClick={startCompare}
            disabled={running}
            data-state={running ? "running" : done ? "done" : "idle"}
          >
            {running ? "比对中…" : done ? "重新比对" : "开始政策比对"}
          </button>
          <div className="compliance-upload-btn-sub">
            {done ? "已完成 · 可在矩阵 tab 查看对照" : "Cmd/Ctrl ↵ 触发"}
          </div>
        </div>
      </div>

      <div className="compliance-upload-zones">
        <DropZoneCard
          title="行内政策"
          hint="制度文档 · 审批办法 · 业务细则"
          uploads={p.innerUploads}
          side="inner"
        />
        <DropZoneCard
          title="外部政策"
          hint="监管规定 · 通知 · 指引 · 公开规范"
          uploads={p.outerUploads}
          side="outer"
        />
      </div>

      <div className="compliance-upload-flow" data-running={running ? "yes" : "no"}>
        <div className="compliance-upload-flow-head">
          <span className="compliance-upload-flow-label">比对流程</span>
          <span className="compliance-upload-flow-text">{flowText}</span>
        </div>
        <div className="compliance-upload-prog" aria-hidden>
          <div
            className="compliance-upload-prog-bar"
            style={{ width: `${pct}%` } as CSSProperties}
          />
        </div>
        <ol className="compliance-upload-steps">
          {COMPARE_STEPS.map((s, i) => {
            const state =
              i < stepIdx ? "done" : i === stepIdx ? (running || i === COMPARE_STEPS.length - 1 ? (running ? "active" : "done") : "active") : "pending";
            return (
              <li key={s.label} className="compliance-upload-step" data-state={state}>
                <span className="compliance-upload-step-idx">{String(i + 1).padStart(2, "0")}</span>
                <span className="compliance-upload-step-label">{s.label}</span>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}

function DropZoneCard(p: {
  title: string;
  hint: string;
  uploads: PolicyUpload[];
  side: "inner" | "outer";
}) {
  const count = p.uploads.length;
  return (
    <div className="compliance-drop-card" data-side={p.side}>
      <div className="compliance-drop-head">
        <div className="compliance-drop-title">{p.title}</div>
        <span className="compliance-drop-count">{count} 份</span>
      </div>
      <label className="compliance-drop-zone">
        <span className="compliance-drop-plus" aria-hidden>＋</span>
        <span className="compliance-drop-label">拖拽文件到此处 · 或点击选择</span>
        <span className="compliance-drop-hint">{p.hint}</span>
        <input type="file" multiple hidden aria-label={`上传${p.title}`} />
      </label>
      <ul className="compliance-drop-list">
        {p.uploads.slice(0, 3).map((u) => (
          <li key={u.id} className="compliance-drop-item" data-status={u.status}>
            <span className="compliance-drop-item-ico" aria-hidden>
              {u.status === "synced" ? "✓" : u.status === "parsing" ? "◐" : "◌"}
            </span>
            <div className="compliance-drop-item-body">
              <div className="compliance-drop-item-name">{u.name}</div>
              <div className="compliance-drop-item-meta">
                {u.version} · {u.size}
              </div>
            </div>
            <span className="compliance-drop-item-status">
              {u.status === "synced" ? "已同步" : u.status === "parsing" ? "解析中" : "待处理"}
            </span>
          </li>
        ))}
        {count > 3 ? (
          <li className="compliance-drop-more">+ {count - 3} 份更早版本</li>
        ) : null}
      </ul>
    </div>
  );
}

/* ────────────────────── HERO ────────────────────── */

function HeroSection(p: {
  weeklyProcessed: string;
  conflictRate: string;
  avgDuration: string;
  objective: string;
  stage: string;
  updated: string;
  qcCounts: { block: number; warn: number; info: number };
}) {
  return (
    <header className="rpt-hero">
      <div className="rpt-hero__eyebrow">
        <span className="rpt-hero__badge" aria-hidden>§</span>
        <span>AGENT · 05 · LEDGER</span>
        <span className="rpt-hero__sep">·</span>
        <span>合规扫描引擎</span>
      </div>
      <h1 className="rpt-hero__title">{p.objective}</h1>
      <p className="rpt-hero__sub">{p.stage} · {p.updated}</p>
      <dl className="rpt-hero__stats">
        <div className="rpt-hero__stat">
          <dt>本周已扫</dt>
          <dd>{p.weeklyProcessed}</dd>
        </div>
        <div className="rpt-hero__stat">
          <dt>冲突占比</dt>
          <dd>{p.conflictRate}</dd>
        </div>
        <div className="rpt-hero__stat">
          <dt>平均耗时</dt>
          <dd>{p.avgDuration}</dd>
        </div>
        <div className="rpt-hero__stat">
          <dt>质检</dt>
          <dd className="rpt-hero__qc">
            <span className="rpt-hero__qc-chip" data-tone="block">{p.qcCounts.block}</span>
            <span className="rpt-hero__qc-chip" data-tone="warn">{p.qcCounts.warn}</span>
            <span className="rpt-hero__qc-chip" data-tone="info">{p.qcCounts.info}</span>
          </dd>
        </div>
      </dl>
    </header>
  );
}

/* ─────────── v2 Hero Ticker · 政策事件时间线顶带（最新 3 条） ─────────── */

function PolicyTicker(p: {
  policies: PolicyRef[];
  timeline: PolicyTimelineItem[];
  conflicts: Conflict[];
}) {
  const latest = p.policies.slice(0, 3);
  const totalBlock = p.conflicts.filter((c) => c.severity === "block").length;
  const totalWarn = p.conflicts.filter((c) => c.severity === "warn").length;
  const tlHead = p.timeline[0];

  const SEV_CH: Record<PolicyRef["severity"], string> = {
    high: "高",
    mid: "中",
    low: "低",
  };
  const SCAN_CH: Record<PolicyRef["scanStatus"], string> = {
    done: "扫描完成",
    scanning: "扫描中",
    pending: "待扫",
  };

  return (
    <section className="rpt-panel compliance-ticker" aria-label="政策事件时间线">
      <PanelPinHandle
        id="compliance:policy-ticker"
        title="政策 Ticker"
        subtitle="最新 3 条政策 · 发布/扫描状态"
        accentVar="--t-compli"
        agentKey="compliance"
        href="/archive/compliance"
        blurb={`冲突 ${totalBlock} 阻断 · ${totalWarn} 警告 · 最新 ${tlHead?.date ?? "—"}`}
      />
      <div className="compliance-ticker-head">
        <span className="eyebrow">POLICY TICKER · 最新政策 3 条</span>
        <span className="meta">
          最新事件 {tlHead ? `· ${tlHead.date} ${tlHead.title}` : "—"} · 冲突
          <b className="b-bad"> {totalBlock} 阻断</b> · <b className="b-warn">{totalWarn} 警告</b>
        </span>
      </div>
      <ol className="compliance-ticker-list">
        {latest.map((pol, i) => (
          <li
            key={pol.id}
            className="compliance-ticker-item"
            data-sev={pol.severity}
            data-scan={pol.scanStatus}
          >
            <div className="compliance-ticker-rail" aria-hidden>
              <span className="dot" />
              {i < latest.length - 1 && <span className="line" />}
            </div>
            <div className="compliance-ticker-card">
              <div className="compliance-ticker-meta">
                <span className="date">{pol.date}</span>
                <span className="issuer">{pol.issuer}</span>
                <span className="sev-chip" data-sev={pol.severity}>
                  {SEV_CH[pol.severity]}
                </span>
                <span className="scan-chip" data-scan={pol.scanStatus}>
                  {SCAN_CH[pol.scanStatus]}
                </span>
              </div>
              <div className="compliance-ticker-title">{pol.title}</div>
              <div className="compliance-ticker-foot">
                <span className="conf">
                  冲突 <b>{pol.conflicts}</b>
                </span>
                {pol.conflicts > 0 ? (
                  <span className="act">已排出待处置清单</span>
                ) : (
                  <span className="act muted">无冲突</span>
                )}
              </div>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

/* ────────────────────── LEFT ────────────────────── */

function QueryPanel({ q }: { q: ComplianceQuery }) {
  return (
    <div className="rpt-panel cp-q">
      <PanelPinHandle
        id="compliance:query"
        title="新规概要"
        subtitle={q.policyCode}
        accentVar="--t-compli"
        agentKey="compliance"
        href="/archive/compliance"
        blurb={`${q.policyTitle} · ${q.clauseCount} 条 · 生效 ${q.effectiveDate}`}
      />
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">新规概要</div>
        <div className="rpt-panel__updated">更新 {q.updated}</div>
      </div>
      <div className="rpt-panel__body">
        <div className="cp-q__ttl">{q.policyTitle}</div>
        <div className="cp-q__code">{q.policyCode}</div>
        <dl className="cp-q__dl">
          <div className="cp-q__row">
            <dt>发布</dt>
            <dd>{q.issuer} · {q.issueDate}</dd>
          </div>
          <div className="cp-q__row">
            <dt>生效</dt>
            <dd><span className="cp-q__effect">{q.effectiveDate}</span></dd>
          </div>
          <div className="cp-q__row">
            <dt>条款</dt>
            <dd><span className="cp-q__count">{q.clauseCount}</span> 条</dd>
          </div>
          <div className="cp-q__row">
            <dt>适用</dt>
            <dd>{q.scope}</dd>
          </div>
        </dl>
      </div>
    </div>
  );
}

function PoliciesPanel({ policies }: { policies: PolicyRef[] }) {
  const totalConflicts = policies.reduce((n, p) => n + p.conflicts, 0);
  return (
    <div className="rpt-panel cp-pol">
      <PanelPinHandle
        id="compliance:policies"
        title="近期政策"
        subtitle={`${policies.length} 份 · 冲突合计 ${totalConflicts}`}
        accentVar="--t-compli"
        agentKey="compliance"
        href="/archive/compliance"
        blurb={`最新：${policies[0]?.title ?? "—"}`}
      />
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">近期政策</div>
        <div className="rpt-panel__counter">{policies.length}</div>
      </div>
      <div className="rpt-panel__body">
        <ul className="cp-pol__list">
          {policies.map((p) => (
            <li key={p.id} className="cp-pol__item" data-severity={p.severity} data-status={p.scanStatus}>
              <div className="cp-pol__head">
                <div className="cp-pol__title">{p.title}</div>
                <span className="cp-pol__conflicts">
                  {p.scanStatus === "scanning" ? "扫描中" : `冲突 ${p.conflicts}`}
                </span>
              </div>
              <div className="cp-pol__meta">
                <span>{p.issuer}</span>
                <span className="cp-pol__sep">·</span>
                <span className="cp-pol__date">{p.date}</span>
                <span className="cp-pol__sev" data-severity={p.severity}>
                  {p.severity === "high" ? "高" : p.severity === "mid" ? "中" : "低"}
                </span>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function DocsPanel({ docs }: { docs: InternalDoc[] }) {
  const avgCov = Math.round(docs.reduce((n, d) => n + d.coverage, 0) / (docs.length || 1));
  return (
    <div className="rpt-panel cp-doc">
      <PanelPinHandle
        id="compliance:docs"
        title="内部制度"
        subtitle={`${docs.length} 份 · 覆盖均值 ${avgCov}%`}
        accentVar="--t-compli"
        agentKey="compliance"
        href="/archive/compliance"
        blurb="行内条款 / 办法 / 规程 / 标准 全量清单"
      />
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">内部制度</div>
        <div className="rpt-panel__counter">{docs.length}</div>
      </div>
      <div className="rpt-panel__body">
        <ul className="cp-doc__list">
          {docs.map((d) => (
            <li key={d.id} className="cp-doc__item">
              <div className="cp-doc__head">
                <span className="cp-doc__code">{d.id.toUpperCase()}</span>
                <div className="cp-doc__title">{d.title}</div>
              </div>
              <div className="cp-doc__meta">
                <span className="cp-doc__type">{d.type}</span>
                <span className="cp-doc__rev">{d.lastRev}</span>
                <span className="cp-doc__cov" data-cov={d.coverage >= 90 ? "high" : d.coverage >= 80 ? "mid" : "low"}>
                  覆盖 {d.coverage}%
                </span>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function PipelinePanel({ steps }: { steps: PipelineStep[] }) {
  const done = steps.filter((s) => s.status === "done").length;
  return (
    <div className="rpt-panel cp-pl">
      <PanelPinHandle
        id="compliance:pipeline"
        title="扫描流水"
        subtitle={`${done}/${steps.length} 步完成`}
        accentVar="--t-compli"
        agentKey="compliance"
        href="/archive/compliance"
        blurb={`活跃：${steps.find((s) => s.status === "active")?.label ?? "已全部完成"}`}
      />
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">扫描流水</div>
        <div className="rpt-panel__counter">
          {done}/{steps.length}
        </div>
      </div>
      <div className="rpt-panel__body">
        <ol className="cp-pl__list">
          {steps.map((s, i) => (
            <li key={s.id} className="cp-pl__item" data-status={s.status}>
              <span className="cp-pl__idx">{String(i + 1).padStart(2, "0")}</span>
              <div className="cp-pl__body">
                <div className="cp-pl__label">{s.label}</div>
                {s.note ? <div className="cp-pl__note">{s.note}</div> : null}
              </div>
              <span className="cp-pl__mark" aria-hidden>
                {s.status === "done" ? "✓" : s.status === "active" ? "●" : "○"}
              </span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

function RecentPanel({ recent }: { recent: ComplianceRecentSession[] }) {
  return (
    <div className="rpt-panel cp-rc">
      <PanelPinHandle
        id="compliance:recent"
        title="近期扫描"
        subtitle={`${recent.length} 次会话`}
        accentVar="--t-compli"
        agentKey="compliance"
        href="/archive/compliance"
        blurb={`最近：${recent[0]?.policy ?? "—"} · 冲突 ${recent[0]?.conflicts ?? 0}`}
      />
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">近期</div>
        <div className="rpt-panel__counter">{recent.length}</div>
      </div>
      <div className="rpt-panel__body">
        <ul className="cp-rc__list">
          {recent.map((r) => (
            <li key={r.id} className="cp-rc__item">
              <div className="cp-rc__head">
                <div className="cp-rc__name">{r.policy}</div>
              </div>
              <div className="cp-rc__meta">
                <span className="cp-rc__conf">冲突 {r.conflicts}</span>
                <span className="cp-rc__res">已处置 {r.resolved}</span>
                <span className="cp-rc__time">{r.updated}</span>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/* ────────────────────── MID ────────────────────── */

function ConversationPanel({ msgs }: { msgs: ConversationMessage[] }) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [msgs.length]);

  const blurb = `${msgs.length} 条对话 · LEDGER ↔ 合规办`;

  return (
    <section className="rpt-panel rpt-panel--conv cp-conv">
      <PanelPinHandle
        id="compliance:conversation"
        title="合规对话"
        subtitle={`${msgs.length} 条消息`}
        accentVar="--t-compli"
        agentKey="compliance"
        href="/archive/compliance"
        blurb={blurb}
      />
      <div className="rpt-conv" ref={scrollRef}>
        {msgs.map((m) => (
          <ConversationMsg key={m.id} m={m} />
        ))}
      </div>
    </section>
  );
}

function ConversationMsg({ m }: { m: ConversationMessage }) {
  if (m.kind === "system-event") {
    return (
      <div className="rpt-msg rpt-msg--sys">
        <MessagePinHandle {...msgPinProps(m, "系统事件")} />
        <span className="rpt-msg__dot" aria-hidden>◈</span>
        <span className="rpt-msg__sys-txt">{m.content}</span>
        <span className="rpt-msg__at">{m.at}</span>
      </div>
    );
  }
  if (m.kind === "user-reply" || m.kind === "user-command") {
    const isCmd = m.kind === "user-command";
    return (
      <div className="rpt-msg rpt-msg--user" data-cmd={isCmd ? "yes" : "no"}>
        <MessagePinHandle
          {...msgPinProps(m, isCmd ? "合规办 · /command" : "合规办 · 王哲")}
        />
        <div className="rpt-msg__head">
          <span className="rpt-msg__who">{isCmd ? "指令" : "我"}</span>
          <span className="rpt-msg__at">{m.at}</span>
        </div>
        <div className="rpt-msg__body">{m.content}</div>
      </div>
    );
  }
  if (m.kind === "ai-thinking") {
    return (
      <div className="rpt-msg rpt-msg--ai rpt-msg--thinking">
        <MessagePinHandle {...msgPinProps(m, "LEDGER · 推理")} />
        <div className="rpt-msg__head">
          <span className="rpt-msg__who">LEDGER · 推理</span>
          <span className="rpt-msg__at">{m.at}</span>
        </div>
        <div className="rpt-msg__body">{m.content}</div>
        {m.thinking?.steps?.length ? (
          <details className="rpt-think" open>
            <summary className="rpt-think__sum">推理过程 · {m.thinking.steps.length} 步</summary>
            <ol className="rpt-think__list">
              {m.thinking.steps.map((s, i) => (
                <li key={i} className="rpt-think__item">
                  <div className="rpt-think__lbl">
                    <span className="rpt-think__idx">{String(i + 1).padStart(2, "0")}</span>
                    {s.label}
                  </div>
                  {s.evidences?.length ? (
                    <ul className="rpt-think__ev">
                      {s.evidences.map((e, j) => (
                        <li key={j}>{e}</li>
                      ))}
                    </ul>
                  ) : null}
                </li>
              ))}
            </ol>
          </details>
        ) : null}
      </div>
    );
  }
  const who = m.kind === "ai-question" ? "LEDGER · 问" : "LEDGER";
  return (
    <div className="rpt-msg rpt-msg--ai" data-q={m.kind === "ai-question" ? "yes" : "no"}>
      <MessagePinHandle {...msgPinProps(m, who)} />
      <div className="rpt-msg__head">
        <span className="rpt-msg__who">{who}</span>
        <span className="rpt-msg__at">{m.at}</span>
        {m.fieldRef ? <span className="rpt-msg__ref">{m.fieldRef}</span> : null}
      </div>
      <div className="rpt-msg__body">{m.content}</div>
      {m.sectionDiff ? (
        <div className="rpt-msg__diff">
          <span className="rpt-msg__diff-anchor">{m.sectionDiff.sectionAnchor}</span>
          <span className="rpt-msg__diff-after">{m.sectionDiff.after}</span>
        </div>
      ) : null}
    </div>
  );
}

function ComplianceComposer() {
  const [value, setValue] = useState("");
  const hints = ["看严重档", "按制度拆", "改造成本", "派工单", "导出整改清单"];
  return (
    <div className="rpt-composer">
      <div className="rpt-composer__hints">
        {hints.map((h) => (
          <button
            key={h}
            type="button"
            className="rpt-composer__hint"
            onClick={() => setValue((v) => (v ? v + " / " + h : h))}
          >
            {h}
          </button>
        ))}
      </div>
      <textarea
        className="rpt-composer__ta"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="对 LEDGER 提问 / 给指令：看严重冲突、拆改造成本、派工单…"
        rows={3}
      />
      <div className="rpt-composer__foot">
        <span className="rpt-composer__hint-txt">Enter 发 · Shift+Enter 换行 · /dispatch 派工单</span>
        <button type="button" className="rpt-composer__send" disabled={!value.trim()}>
          发送
        </button>
      </div>
    </div>
  );
}

/* ────────────────────── RIGHT · OUTPUT ────────────────────── */

function OutputPanel(p: {
  tab: OutputTab;
  onTabChange: (t: OutputTab) => void;
  matrix: MatrixCell[];
  docs: InternalDoc[];
  clauses: { id: string; label: string }[];
  conflicts: Conflict[];
  funnel: FunnelStage[];
  timeline: PolicyTimelineItem[];
  cellDetails: Record<string, CellDetail>;
}) {
  const blurb = `矩阵 / 漏斗 / Timeline · ${p.conflicts.length} 条冲突 · ${p.docs.length} 份制度`;
  return (
    <div className="rpt-panel cp-out">
      <PanelPinHandle
        id="compliance:output"
        title="合规看板"
        subtitle={`tab · ${p.tab}`}
        accentVar="--t-compli"
        agentKey="compliance"
        href="/archive/compliance"
        blurb={blurb}
      />
      <div className="rpt-panel__head cp-out__head">
        <div className="rpt-panel__eyebrow">合规看板</div>
        <div className="cp-out__tabs" role="tablist">
          <TabBtn active={p.tab === "matrix"} onClick={() => p.onTabChange("matrix")}>矩阵</TabBtn>
          <TabBtn active={p.tab === "funnel"} onClick={() => p.onTabChange("funnel")}>漏斗</TabBtn>
          <TabBtn active={p.tab === "timeline"} onClick={() => p.onTabChange("timeline")}>Timeline</TabBtn>
        </div>
      </div>
      <div className="rpt-panel__body cp-out__body">
        {p.tab === "matrix" ? (
          <MatrixView
            matrix={p.matrix}
            docs={p.docs}
            clauses={p.clauses}
            conflicts={p.conflicts}
            cellDetails={p.cellDetails}
          />
        ) : null}
        {p.tab === "funnel" ? <FunnelView funnel={p.funnel} conflicts={p.conflicts} /> : null}
        {p.tab === "timeline" ? <TimelineView timeline={p.timeline} /> : null}
      </div>
    </div>
  );
}

function TabBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button type="button" className="cp-out__tab" data-active={active ? "yes" : "no"} onClick={onClick}>
      {children}
    </button>
  );
}

/* ── 冲突矩阵 ── */

function MatrixView({
  matrix,
  docs,
  clauses,
  conflicts,
  cellDetails,
}: {
  matrix: MatrixCell[];
  docs: InternalDoc[];
  clauses: { id: string; label: string }[];
  conflicts: Conflict[];
  cellDetails: Record<string, CellDetail>;
}) {
  const [sel, setSel] = useState<{ docId: string; clauseId: string } | null>(null);
  const lookup = new Map<string, MatrixCell>();
  matrix.forEach((c) => lookup.set(`${c.docId}-${c.clauseId}`, c));

  const selCell = sel ? lookup.get(`${sel.docId}-${sel.clauseId}`) : null;
  const selDoc = sel ? docs.find((d) => d.id === sel.docId) : null;
  const selClause = sel ? clauses.find((c) => c.id === sel.clauseId) : null;
  const selConflict = sel
    ? conflicts.find(
        (cf) =>
          cf.docId === sel.docId &&
          cf.clauseLabel === clauses.find((c) => c.id === sel.clauseId)?.label
      )
    : null;

  return (
    <div className="cp-mx">
      <div className="cp-mx__legend">
        <span className="cp-mx__leg" data-severity="block">严重</span>
        <span className="cp-mx__leg" data-severity="warn">警告</span>
        <span className="cp-mx__leg" data-severity="info">提示</span>
        <span className="cp-mx__leg" data-severity="pass">通过</span>
      </div>

      <div className="cp-mx__wrap">
        <div
          className="cp-mx__grid"
          style={{
            gridTemplateColumns: `120px repeat(${docs.length}, 1fr)`,
          } as CSSProperties}
        >
          <div className="cp-mx__corner" />
          {docs.map((d) => (
            <div key={d.id} className="cp-mx__col-head" title={d.title}>
              <span className="cp-mx__col-id">{d.id.toUpperCase()}</span>
              <span className="cp-mx__col-name">{d.title}</span>
            </div>
          ))}
          {clauses.map((cl) => (
            <Fragment key={cl.id}>
              <div className="cp-mx__row-head">{cl.label}</div>
              {docs.map((d) => {
                const cell = lookup.get(`${d.id}-${cl.id}`);
                const active = sel?.docId === d.id && sel?.clauseId === cl.id;
                return (
                  <button
                    key={`${cl.id}-${d.id}`}
                    type="button"
                    className="cp-mx__cell"
                    data-severity={cell?.severity ?? "pass"}
                    data-active={active ? "yes" : "no"}
                    onClick={() => setSel({ docId: d.id, clauseId: cl.id })}
                    title={cell?.note ?? "通过"}
                  >
                    {cell?.severity === "block" ? "✕" : cell?.severity === "warn" ? "!" : cell?.severity === "info" ? "i" : "✓"}
                  </button>
                );
              })}
            </Fragment>
          ))}
        </div>
      </div>

      {sel && selCell ? (
        <CellDrawer
          cell={selCell}
          doc={selDoc}
          clause={selClause}
          conflict={selConflict}
          detail={cellDetails[`${sel.docId}-${sel.clauseId}`]}
        />
      ) : (
        <div className="cp-mx__hint">点击矩阵单元格 · 下方展开左右对照纸 + 条款映射</div>
      )}
    </div>
  );
}

/* ── 矩阵 drawer · 左右对照"纸" + 条款映射表 ── */

function CellDrawer({
  cell,
  doc,
  clause,
  conflict,
  detail,
}: {
  cell: MatrixCell;
  doc: InternalDoc | null | undefined;
  clause: { id: string; label: string } | null | undefined;
  conflict: Conflict | null | undefined;
  detail: CellDetail | undefined;
}) {
  const sevLabel =
    cell.severity === "block"
      ? "强冲突"
      : cell.severity === "warn"
      ? "口径差异"
      : cell.severity === "info"
      ? "提示"
      : "通过";

  return (
    <div className="cp-drawer" data-severity={cell.severity}>
      <div className="cp-drawer__head">
        <span className="cp-drawer__sev" data-severity={cell.severity}>
          {sevLabel}
        </span>
        <span className="cp-drawer__doc">{doc?.title}</span>
        <span className="cp-drawer__sep">·</span>
        <span className="cp-drawer__cl">{clause?.label}</span>
      </div>

      {cell.note ? (
        <div className="cp-drawer__note">{cell.note}</div>
      ) : null}

      {detail ? (
        <>
          <div className="cp-drawer__papers">
            <article className="cp-paper" data-side="inner">
              <div className="cp-paper__tag">行内政策条款</div>
              <div className="cp-paper__meta">{detail.paper.innerDocVersion}</div>
              <div
                className="cp-paper__body"
                dangerouslySetInnerHTML={{ __html: detail.paper.innerHtml }}
              />
            </article>
            <article className="cp-paper" data-side="outer">
              <div className="cp-paper__tag">外部政策条款</div>
              <div className="cp-paper__meta">{detail.paper.outerDocVersion}</div>
              <div
                className="cp-paper__body"
                dangerouslySetInnerHTML={{ __html: detail.paper.outerHtml }}
              />
            </article>
          </div>

          <div className="cp-mapping">
            <div className="cp-mapping__title">条款映射</div>
            <div className="cp-mapping__list">
              {detail.clauseMapping.map((row, i) => (
                <ClauseMapRowItem key={i} row={row} />
              ))}
            </div>
          </div>
        </>
      ) : (
        <div className="cp-drawer__empty">
          {cell.severity === "pass"
            ? "此单元格通过 · 无差异 · 无需整改"
            : "此单元格暂无对照原文 · 详情补齐中"}
        </div>
      )}

      {conflict ? (
        <div className="cp-drawer__advice">
          <div className="cp-drawer__advice-head">
            <span className="cp-drawer__advice-tag">整改建议</span>
            <span className="cp-drawer__advice-cite">{conflict.cite}</span>
          </div>
          <div className="cp-drawer__advice-body">{conflict.advice}</div>
        </div>
      ) : null}
    </div>
  );
}

function ClauseMapRowItem({ row }: { row: ClauseMapRow }) {
  const DIFF_LABEL: Record<ClauseMapRow["diff"], string> = {
    bad: "冲突",
    warn: "差异",
    info: "提示",
  };
  return (
    <div className="cp-mapping__row" data-diff={row.diff}>
      <span className="cp-mapping__field">{row.field}</span>
      <span className="cp-mapping__inner">{row.inner}</span>
      <span className="cp-mapping__arrow" aria-hidden>→</span>
      <span className="cp-mapping__outer">{row.outer}</span>
      <span className="cp-mapping__diff" data-diff={row.diff}>
        {DIFF_LABEL[row.diff]}
      </span>
    </div>
  );
}

/* ── 扫描漏斗 ── */

function FunnelView({ funnel, conflicts }: { funnel: FunnelStage[]; conflicts: Conflict[] }) {
  const max = Math.max(...funnel.map((s) => s.count));
  return (
    <div className="cp-fn">
      <ul className="cp-fn__list">
        {funnel.map((s, i) => {
          const w = (s.count / max) * 100;
          return (
            <li key={s.key} className="cp-fn__item" data-stage={s.key}>
              <div className="cp-fn__bar" style={{ width: `${w}%` } as CSSProperties}>
                <span className="cp-fn__count">{s.count}</span>
                <span className="cp-fn__lbl">{s.label}</span>
              </div>
              {s.sub ? <div className="cp-fn__sub">{s.sub}</div> : null}
            </li>
          );
        })}
      </ul>

      <div className="cp-fn__ttl">严重冲突明细 · block {conflicts.filter((c) => c.severity === "block").length} 条</div>
      <ul className="cp-fn__cf-list">
        {conflicts.filter((c) => c.severity === "block").map((c) => (
          <li key={c.id} className="cp-fn__cf" data-severity={c.severity}>
            <div className="cp-fn__cf-head">
              <span className="cp-fn__cf-mark" aria-hidden>✕</span>
              <div className="cp-fn__cf-cl">{c.clauseLabel}</div>
              <span className="cp-fn__cf-doc">{c.docTitle}</span>
            </div>
            <div className="cp-fn__cf-find">{c.finding}</div>
            <div className="cp-fn__cf-cite">出处 · {c.cite}</div>
            <div className="cp-fn__cf-adv">整改 · {c.advice}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ── 政策 timeline ── */

function TimelineView({ timeline }: { timeline: PolicyTimelineItem[] }) {
  return (
    <div className="cp-tl">
      <ol className="cp-tl__list">
        {timeline.map((t) => (
          <li key={t.id} className="cp-tl__item" data-kind={t.kind}>
            <div className="cp-tl__dot" aria-hidden />
            <div className="cp-tl__body">
              <div className="cp-tl__head">
                <span className="cp-tl__date">{t.date}</span>
                <span className="cp-tl__kind" data-kind={t.kind}>
                  {TL_KIND_LABEL[t.kind]}
                </span>
              </div>
              <div className="cp-tl__ttl">{t.title}</div>
              <div className="cp-tl__issuer">{t.issuer}</div>
              {t.note ? <div className="cp-tl__note">{t.note}</div> : null}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

const TL_KIND_LABEL: Record<string, string> = {
  issued: "发布",
  effective: "生效",
  scanned: "扫描完成",
  resolved: "整改完成",
};

/* ────────────────────── REVISION PANEL · 底部修订意见 ────────────────────── */

const KIND_LABEL: Record<RevisionAdvice["kind"], string> = {
  fix: "改",
  add: "补",
  strengthen: "强",
};
const KIND_SUB: Record<RevisionAdvice["kind"], string> = {
  fix: "冲突条款需调整",
  add: "缺失条款需新增",
  strengthen: "措辞需强化",
};

function RevisionPanel({ advices }: { advices: RevisionAdvice[] }) {
  if (!advices.length) return null;

  const groups: Record<RevisionAdvice["kind"], RevisionAdvice[]> = {
    fix: [],
    add: [],
    strengthen: [],
  };
  advices.forEach((a) => groups[a.kind].push(a));

  return (
    <section className="rpt-panel compliance-bottom-revise" aria-label="修订意见">
      <PanelPinHandle
        id="compliance:revision"
        title="修订意见"
        subtitle={`改 ${groups.fix.length} · 补 ${groups.add.length} · 强 ${groups.strengthen.length}`}
        accentVar="--t-compli"
        agentKey="compliance"
        href="/archive/compliance"
        blurb="改/补/强 三类建议 · 可派工单进入修订流程"
      />
      <div className="compliance-revise-head">
        <div>
          <div className="compliance-revise-eyebrow">REVISION ADVICES · 改 / 补 / 强</div>
          <h3 className="compliance-revise-title">修订意见与审阅说明</h3>
          <p className="compliance-revise-sub">
            不仅提示冲突，还给出可直接进入修订流程的建议语句；合规办可将任一条派成工单。
          </p>
        </div>
        <div className="compliance-revise-count">
          <span data-kind="fix">改 <b>{groups.fix.length}</b></span>
          <span data-kind="add">补 <b>{groups.add.length}</b></span>
          <span data-kind="strengthen">强 <b>{groups.strengthen.length}</b></span>
        </div>
      </div>

      <div className="compliance-revise-grid">
        {(["fix", "add", "strengthen"] as const).map((kind) => (
          <div key={kind} className="compliance-revise-col" data-kind={kind}>
            <div className="compliance-revise-col-head">
              <span className="compliance-revise-chip" data-kind={kind}>
                {KIND_LABEL[kind]}
              </span>
              <span className="compliance-revise-col-ttl">{KIND_SUB[kind]}</span>
              <span className="compliance-revise-col-count">{groups[kind].length}</span>
            </div>
            <ul className="compliance-revise-list">
              {groups[kind].map((a) => (
                <li key={a.id} className="compliance-revise-item">
                  <div className="compliance-revise-item-head">
                    <span className="compliance-revise-item-title">{a.title}</span>
                    {a.due ? (
                      <span className="compliance-revise-item-due">截止 {a.due}</span>
                    ) : null}
                  </div>
                  <div className="compliance-revise-item-body">{a.body}</div>
                  {a.docTitle ? (
                    <div className="compliance-revise-item-doc">对应制度 · {a.docTitle}</div>
                  ) : null}
                </li>
              ))}
              {!groups[kind].length ? (
                <li className="compliance-revise-empty">
                  暂无此类建议
                </li>
              ) : null}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}
