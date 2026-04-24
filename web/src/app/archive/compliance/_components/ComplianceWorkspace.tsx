"use client";

/**
 * /archive/compliance · Agent 05 LEDGER · 对话式合规扫描 workspace（canon 横向套 2026-04-21 H5）
 * 左：query + policies + docs + pipeline + recent /
 * 中：对话 + ComplianceComposer /
 * 右：冲突矩阵（doc × clause）· 扫描漏斗 · 政策 timeline 三切换
 * 壳类：.v-archive--canon[data-agent="compliance"] → --agent = var(--t-compli) 墨绿
 */

import { Fragment, useEffect, useRef, useState, type CSSProperties } from "react";
import { ScanCTA } from "@/components/shared/ScanCTA";
import { CustomerSelector } from "@/components/shared/CustomerSelector";
import { EvidenceProvider, EvidenceTrail } from "@/components/evidence";
import { COMPLIANCE_EVIDENCE } from "@/components/evidence/fixtures";
import {
  COMPLIANCE_GLOBAL_STATS,
  COMPLIANCE_SESSION,
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
} from "@/lib/mock/agent-compliance-session";

type OutputTab = "matrix" | "funnel" | "timeline";

export default function ComplianceWorkspace() {
  const session = COMPLIANCE_SESSION;
  const [tab, setTab] = useState<OutputTab>("matrix");
  /* 2026-04-23 · demo 初始态 · 未扫描时数据模糊 · ScanCTA onDone 解锁 */
  const [scanned, setScanned] = useState(false);

  return (
    <EvidenceProvider
      items={COMPLIANCE_EVIDENCE.items}
      unfilledFields={COMPLIANCE_EVIDENCE.unfilledFields}
    >
    <div className="rpt-workspace" data-scanned={scanned ? "yes" : "no"}>
      <HeroSection
        weeklyProcessed={COMPLIANCE_GLOBAL_STATS.weeklyProcessed}
        conflictRate={COMPLIANCE_GLOBAL_STATS.conflictRate}
        avgDuration={COMPLIANCE_GLOBAL_STATS.avgDuration}
        objective={session.objective}
        stage={session.stage}
        updated={session.updated}
        qcCounts={session.qcCounts}
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
          <ScanCTA
            label="政策核查"
            tone="compli"
            onDone={() => setScanned(true)}
            steps={[
              { label: "抓取最新政策 · 3 渠道", pct: 18 },
              { label: "解析政策条款 · 实体抽取", pct: 42 },
              { label: "比对业务矩阵 · 逐条扫", pct: 66 },
              { label: "违规判定 · 缺陷分类", pct: 86 },
              { label: "生成冲突清单 · 完成", pct: 100 },
            ]}
          />
          <ConversationPanel msgs={session.conversation}>
            <ComplianceComposer />
          </ConversationPanel>
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
          />
        </section>
      </div>
      <EvidenceTrail agentTone="compliance" />
    </div>
    </EvidenceProvider>
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
      {/* 2026-04-23 · 业务逻辑: compliance 是政策事件驱动 · 批量比对内部制度 · 不选客户
          输入是政策源 + 制度库 · 触发"政策核查"即可 · CustomerSelector 不适用 */}
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
  return (
    <div className="rpt-panel cp-pol">
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
  return (
    <div className="rpt-panel cp-doc">
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
  return (
    <div className="rpt-panel cp-pl">
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">扫描流水</div>
        <div className="rpt-panel__counter">
          {steps.filter((s) => s.status === "done").length}/{steps.length}
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

function ConversationPanel({
  msgs,
  children,
}: {
  msgs: ConversationMessage[];
  children?: React.ReactNode;
}) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [msgs.length]);

  return (
    <div className="rpt-panel rpt-panel--conv rpt-panel--conv-docked">
      <div className="rpt-conv" ref={scrollRef}>
        {msgs.map((m) => (
          <ConversationMsg key={m.id} m={m} />
        ))}
      </div>
      {children}
    </div>
  );
}

function ConversationMsg({ m }: { m: ConversationMessage }) {
  if (m.kind === "system-event") {
    return (
      <div className="rpt-msg rpt-msg--sys">
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
}) {
  return (
    <div className="rpt-panel cp-out">
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
          <MatrixView matrix={p.matrix} docs={p.docs} clauses={p.clauses} conflicts={p.conflicts} />
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
}: {
  matrix: MatrixCell[];
  docs: InternalDoc[];
  clauses: { id: string; label: string }[];
  conflicts: Conflict[];
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
        <div className="cp-mx__detail" data-severity={selCell.severity}>
          <div className="cp-mx__d-head">
            <span className="cp-mx__d-doc">{selDoc?.title}</span>
            <span className="cp-mx__d-sep">·</span>
            <span className="cp-mx__d-cl">{selClause?.label}</span>
          </div>
          <div className="cp-mx__d-note">
            {selCell.note ?? "通过 · 无需整改"}
          </div>
          {selConflict ? (
            <>
              <div className="cp-mx__d-row">
                <span className="cp-mx__d-lbl">出处</span>
                <span className="cp-mx__d-val">{selConflict.cite}</span>
              </div>
              <div className="cp-mx__d-row">
                <span className="cp-mx__d-lbl">整改建议</span>
                <span className="cp-mx__d-val">{selConflict.advice}</span>
              </div>
            </>
          ) : null}
        </div>
      ) : (
        <div className="cp-mx__hint">点击矩阵单元格查看冲突详情与整改建议</div>
      )}
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
