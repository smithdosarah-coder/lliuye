"use client";

/**
 * /archive/alert · Agent 04 TOWER · 对话式贷中预警 workspace（canon 横向套 2026-04-21 H4）
 * 左：query + rules + pipeline + recent / 中：对话 + AlertComposer /
 * 右：分档分布 stacked · 30 天热力 · 触达率 三切换
 * 壳类：.v-archive--canon[data-agent="alert"] → --agent = var(--t-alert) 赭红
 */

import { useEffect, useRef, useState, type CSSProperties, type ChangeEvent } from "react";
import {
  ALERT_GLOBAL_STATS,
  ALERT_SESSION,
  type AlertPipelineStep,
  type AlertRecentSession,
  type AlertRule,
  type ConversationMessage,
  type HeatCell,
  type IndustryDistribution,
  type KnowledgeSource,
  type ReachRate,
  type ScanQueueCase,
  type ScanRangeOption,
  type ScanStep,
  type SignalHeatBar,
  type TopCase,
} from "@/lib/mock/agent-alert-session";
import { PanelPinHandle } from "@/components/shell/PanelPinHandle";
import { MessagePinHandle } from "@/components/shell/MessagePinHandle";
import {
  ClaimText,
  EvidenceProvider,
  EvidenceTrail,
  UnfilledFields,
} from "@/components/evidence";
import { ALERT_EVIDENCE } from "@/components/evidence/fixtures";
import { LiveFailError, runAlertScan } from "@/lib/api/alert";

/** 截断消息内容作 pin title，避免白板/画布过长；尾部加 …。 */
function msgTitle(raw: string): string {
  const flat = raw.replace(/\s+/g, " ").trim();
  return flat.length > 42 ? `${flat.slice(0, 40)}…` : flat;
}

/** 统一消息 PinHandle props 生成（alert agent tint）。 */
function msgPinProps(msg: ConversationMessage, speaker: string) {
  return {
    id: `alert:msg:${msg.id}`,
    title: msgTitle(msg.content),
    subtitle: `${speaker} · ${msg.at}`,
    accentVar: "--t-alert",
    agentKey: "alert",
    href: "/archive/alert",
    fullText: msg.content,
  };
}

/** 面板 PanelPinHandle 一键 factory · 默认 href/agentKey/accentVar */
function panelPin(id: string, title: string, subtitle: string, blurb: string) {
  return {
    id: `alert:${id}`,
    title,
    subtitle,
    accentVar: "--t-alert",
    agentKey: "alert",
    href: "/archive/alert",
    blurb,
  };
}

type OutputTab = "dist" | "heat" | "reach";
type ScanPhase = "before" | "scanning" | "after";

export default function AlertWorkspace() {
  const session = ALERT_SESSION;
  const [tab, setTab] = useState<OutputTab>("dist");
  const [rangeId, setRangeId] = useState<string>(session.scanRange[0]?.id ?? "");

  const [phase, setPhase] = useState<ScanPhase>("before");
  const [stepIdx, setStepIdx] = useState(0);
  const timerRef = useRef<number | null>(null);

  /* Stage Fix W-FIX-A3 · live-fallback-banner-spec v1.0 §2 规则 1
     启动扫描需真接 POST /api/alert/scan SSE · 失败显式 banner · 不 silent swap */
  type LiveFail = {
    endpoint: string;
    label: string;
    status: number;
    message: string;
    bodyExcerpt: string;
  };
  const [liveFail, setLiveFail] = useState<LiveFail | null>(null);
  const [retryHandler, setRetryHandler] = useState<(() => void) | null>(null);
  const [scanSessionId, setScanSessionId] = useState<string>("");

  function clearLiveFail(): void {
    setLiveFail(null);
    setRetryHandler(null);
  }

  function recordLiveFail(label: string, err: unknown, retry: () => void): void {
    if (err instanceof LiveFailError) {
      setLiveFail({
        endpoint: err.endpoint,
        label,
        status: err.status,
        message: err.message,
        bodyExcerpt: err.bodyExcerpt,
      });
    } else {
      setLiveFail({
        endpoint: "(unknown)",
        label,
        status: 0,
        message: err instanceof Error ? err.message : String(err),
        bodyExcerpt: "",
      });
    }
    setRetryHandler(() => retry);
  }

  const steps = session.scanSteps;
  const after = session.scanSnapshotAfter;

  /** paint：phase=after 时切换 source list / hero summary / kb state / queue / heat */
  const currentSources = phase === "after" ? after.sources : session.knowledgeBaseSources;
  const currentQueue = phase === "after" ? after.queue : session.scanQueueCases;
  const currentHeat = phase === "after" ? after.heat : session.signalHeatmap;
  const kbState = phase === "after" ? after.kbState : `${session.knowledgeBaseSources.filter((s) => s.status === "online").length} 项联机中`;
  const currentSummary =
    phase === "after"
      ? after.summary
      : `${session.stage} · 红 ${session.totals.red} / 黄 ${session.totals.yellow} / 绿 ${session.totals.green} · ${session.updated}`;

  useEffect(() => {
    return () => {
      if (timerRef.current != null) window.clearInterval(timerRef.current);
    };
  }, []);

  function startScan() {
    if (phase === "scanning") return;
    setPhase("scanning");
    setStepIdx(0);
    clearLiveFail();
    if (timerRef.current != null) window.clearInterval(timerRef.current);

    /* 视觉 stepIdx 推进 (5 步 · 每 500ms) · 与真后端 SSE 并行 */
    let i = 0;
    timerRef.current = window.setInterval(() => {
      i += 1;
      if (i >= steps.length) {
        if (timerRef.current != null) window.clearInterval(timerRef.current);
        timerRef.current = null;
        setStepIdx(steps.length - 1);
      } else {
        setStepIdx(i);
      }
    }, 500);

    /* Stage Fix · 真接 POST /api/alert/scan SSE · 失败显式 banner */
    void (async () => {
      try {
        const { sessionId } = await runAlertScan({
          scenarioKey: rangeId || "",
          forceMock: true, // demo · production 切 false 真扫
        });
        if (sessionId) setScanSessionId(sessionId);
        setPhase("after");
      } catch (e) {
        recordLiveFail("alert scan", e, () => startScan());
        if (timerRef.current != null) {
          window.clearInterval(timerRef.current);
          timerRef.current = null;
        }
        // failure: 仍切 after · 让 UI 渲染 fallback mock 但带 banner
        // 用户主动 click retry 重试 · 不 silent
        setPhase("after");
      }
    })();
  }

  function resetScan() {
    if (timerRef.current != null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setStepIdx(0);
    setPhase("before");
  }

  return (
    <EvidenceProvider
      items={ALERT_EVIDENCE.items}
      unfilledFields={ALERT_EVIDENCE.unfilledFields}
    >
    <div
      className="rpt-workspace"
      data-testid="alert-workspace"
      data-phase={phase}
      data-scan-session-id={scanSessionId}
    >
      {liveFail ? (
        <div
          className="alert-live-fail-banner"
          role="alert"
          data-testid="alert-live-fail-banner"
          data-status={liveFail.status}
          data-endpoint={liveFail.endpoint}
        >
          <span className="alert-live-fail-banner__icon" aria-hidden>⚠️</span>
          <span className="alert-live-fail-banner__text">
            后端 <b>{liveFail.label}</b> 调用失败 (
            {liveFail.status > 0 ? `HTTP ${liveFail.status}` : "network/SSE"})
            · 当前显 fallback 演示数据 · 切真实路径请重试
            {liveFail.bodyExcerpt ? (
              <span className="alert-live-fail-banner__detail">
                · 详情：{liveFail.bodyExcerpt}
              </span>
            ) : null}
          </span>
          {retryHandler ? (
            <button
              type="button"
              className="alert-live-fail-banner__retry"
              onClick={() => retryHandler()}
              data-testid="alert-live-fail-retry"
            >
              重试
            </button>
          ) : null}
          <button
            type="button"
            className="alert-live-fail-banner__dismiss"
            onClick={clearLiveFail}
            aria-label="关闭横幅"
          >
            ×
          </button>
        </div>
      ) : null}

      <HeroSection
        weeklyProcessed={ALERT_GLOBAL_STATS.weeklyProcessed}
        redRate={ALERT_GLOBAL_STATS.redRate}
        avgDuration={ALERT_GLOBAL_STATS.avgDuration}
        objective={session.objective}
        stage={session.stage}
        updated={session.updated}
        totals={session.totals}
        qcCounts={session.qcCounts}
        phase={phase}
        summary={currentSummary}
        afterDelta={phase === "after" ? after.warnDelta : undefined}
        afterWarn={phase === "after" ? after.warnCount : undefined}
        kbState={kbState}
        onScan={startScan}
        onReset={resetScan}
      />

      <ScanProgressStrip
        phase={phase}
        steps={steps}
        stepIdx={stepIdx}
      />

      <TrafficLightWall
        totals={session.totals}
        rules={session.rules}
        reach={session.reach}
        topCases={session.topCases}
      />

      <ScanQueuePanel queue={currentQueue} phase={phase} />

      <div className="rpt-grid">
        <aside className="rpt-col rpt-col--left">
          <ScanRangePanel
            options={session.scanRange}
            selected={rangeId}
            onSelect={setRangeId}
          />
          <KnowledgeUploadPanel />
          <SourceListPanel sources={currentSources} />
          <RulesPanel rules={session.rules} />
          <PipelinePanel steps={session.pipeline} />
          <RecentPanel recent={session.recentSessions} />
        </aside>

        <section className="rpt-col rpt-col--mid">
          <ConversationPanel msgs={session.conversation} />
          <AlertComposer />
        </section>

        <section className="rpt-col rpt-col--right">
          <OutputPanel
            tab={tab}
            onTabChange={setTab}
            distribution={session.distribution}
            heat={session.heat}
            reach={session.reach}
            topCases={session.topCases}
            totals={session.totals}
          />
        </section>
      </div>

      <SignalHeatmapPanel bars={currentHeat} phase={phase} />

      <section className="ev-claim-summary" aria-label="Evidence-grounded 分析结论">
        <span className="ev-claim-summary-label">分析结论 · Evidence-grounded</span>
        <ClaimText text={ALERT_EVIDENCE.summary} />
      </section>
      <UnfilledFields />
      <EvidenceTrail agentTone="alert" />
    </div>
    </EvidenceProvider>
  );
}

/* eslint-disable @typescript-eslint/no-unused-vars · scanSessionId 暴露给 testid 验 */

/* ────────────────────── HERO ────────────────────── */

function HeroSection(p: {
  weeklyProcessed: string;
  redRate: string;
  avgDuration: string;
  objective: string;
  stage: string;
  updated: string;
  totals: { red: number; yellow: number; green: number };
  qcCounts: { block: number; warn: number; info: number };
  phase: ScanPhase;
  summary: string;
  afterDelta?: string;
  afterWarn?: number;
  kbState: string;
  onScan: () => void;
  onReset: () => void;
}) {
  const isScanning = p.phase === "scanning";
  const isAfter = p.phase === "after";
  const btnLabel = isScanning ? "扫描中…" : isAfter ? "重新扫描" : "启动风险扫描";
  return (
    <header className="rpt-hero al-hero">
      <div className="rpt-hero__eyebrow">
        <span className="rpt-hero__badge" aria-hidden>◉</span>
        <span>AGENT · 04 · TOWER</span>
        <span className="rpt-hero__sep">·</span>
        <span>贷中预警引擎</span>
        <span className="al-hero__kb" data-phase={p.phase}>
          <span className="al-hero__kb-dot" aria-hidden />
          {p.kbState}
        </span>
      </div>
      <h1 className="rpt-hero__title">{p.objective}</h1>
      <p className="rpt-hero__sub">{p.summary}</p>

      <div className="al-hero__row">
        <dl className="rpt-hero__stats al-hero__stats">
          <div className="rpt-hero__stat">
            <dt>本周已扫</dt>
            <dd>{p.weeklyProcessed}</dd>
          </div>
          <div className="rpt-hero__stat">
            <dt>红档占比</dt>
            <dd>{p.redRate}</dd>
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
          {isAfter ? (
            <div className="rpt-hero__stat al-hero__stat--delta">
              <dt>最新扫描</dt>
              <dd>
                <span className="al-hero__delta-num">{p.afterWarn}</span>
                <span className="al-hero__delta-tag">{p.afterDelta}</span>
              </dd>
            </div>
          ) : null}
        </dl>

        <div className="al-hero__cta-wrap">
          <button
            type="button"
            className="al-hero__cta"
            data-phase={p.phase}
            disabled={isScanning}
            onClick={isAfter ? p.onReset : p.onScan}
          >
            <span className="al-hero__cta-ic" aria-hidden>◈</span>
            <span className="al-hero__cta-lbl">{btnLabel}</span>
            {!isScanning ? <kbd className="al-hero__cta-kbd">⌘R</kbd> : null}
          </button>
          <div className="al-hero__cta-hint">
            {isScanning
              ? "扫描进行中 · 约 2.5 秒"
              : isAfter
                ? "已完成扫描 · 点击可回到扫描前基线"
                : "5 步 pipeline · 外链 → 内部 → 流水 → 分级 → 完成"}
          </div>
        </div>
      </div>
    </header>
  );
}

function ScanProgressStrip(p: {
  phase: ScanPhase;
  steps: ScanStep[];
  stepIdx: number;
}) {
  if (p.phase === "before") return null;
  const current = p.steps[Math.min(p.stepIdx, p.steps.length - 1)] ?? p.steps[0];
  return (
    <section
      className="rpt-panel al-prog"
      data-phase={p.phase}
      aria-label="风险扫描进度"
    >
      <PanelPinHandle
        {...panelPin(
          "scan-progress",
          "风险扫描进度",
          p.phase === "scanning" ? "扫描中 · 5 步" : "扫描完成",
          `${current?.text ?? "扫描完成"} · ${current?.pct ?? 100}%`,
        )}
      />
      <div className="al-prog__head">
        <div className="al-prog__eyebrow">SCAN · 扫描流程</div>
        <div className="al-prog__text">
          {current?.text ?? "扫描完成"}
          <span className="al-prog__pct">{current?.pct ?? 100}%</span>
        </div>
      </div>
      <div className="al-prog__bar" aria-hidden>
        <div
          className="al-prog__fill"
          style={{ width: `${current?.pct ?? 100}%` } as CSSProperties}
        />
      </div>
      <ol className="al-prog__steps">
        {p.steps.map((s, i) => (
          <li
            key={s.id}
            className="al-prog__step"
            data-status={
              i < p.stepIdx || p.phase === "after"
                ? "done"
                : i === p.stepIdx
                  ? "active"
                  : "pending"
            }
          >
            <span className="al-prog__step-idx">{String(i + 1).padStart(2, "0")}</span>
            <span className="al-prog__step-lbl">{s.text}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

/* ─────────────── v2 Hero · 红黄绿三灯状态墙 ─────────────── */

function TrafficLightWall(p: {
  totals: { red: number; yellow: number; green: number };
  rules: AlertRule[];
  reach: ReachRate[];
  topCases: TopCase[];
}) {
  const { red, yellow, green } = p.totals;
  const total = red + yellow + green;
  const redCases = p.topCases.filter((c) => c.tier === "red");

  const redReach = p.reach.find((r) => r.tier === "red");
  const ylReach = p.reach.find((r) => r.tier === "yellow");
  const greenReach = p.reach.find((r) => r.tier === "green");

  const activeRules = p.rules.filter((r) => r.enabled).length;

  const lights = [
    {
      tier: "red" as const,
      label: "红档 · 立即处置",
      count: red,
      pct: total ? Math.round((red / total) * 100) : 0,
      caption: redReach ? `触达 ${redReach.reached} / ${redReach.total}` : "—",
      detail: `TOP ${redCases.length} 单 · ${redCases[0]?.customer ?? "—"} ${redCases[0]?.amount ?? ""}`,
      animate: true,
    },
    {
      tier: "yellow" as const,
      label: "黄档 · 重点观察",
      count: yellow,
      pct: total ? Math.round((yellow / total) * 100) : 0,
      caption: ylReach ? `触达 ${ylReach.reached} / ${ylReach.total}` : "—",
      detail: `触达率 ${ylReach ? ylReach.reachedPct.toFixed(1) + "%" : "—"}`,
      animate: false,
    },
    {
      tier: "green" as const,
      label: "绿档 · 常规跟踪",
      count: green,
      pct: total ? Math.round((green / total) * 100) : 0,
      caption: greenReach ? `触达 ${greenReach.reached} / ${greenReach.total}` : "—",
      detail: `平稳 · 下轮扫描 T+7`,
      animate: false,
    },
  ];

  return (
    <section className="rpt-panel alert-wall" aria-label="红黄绿三灯状态墙">
      <PanelPinHandle
        {...panelPin(
          "traffic-wall",
          "红黄绿三灯状态墙",
          `贷中预警 · 命中 ${total.toLocaleString()} 户`,
          `红 ${red} · 黄 ${yellow} · 绿 ${green} · ${activeRules} 条规则活跃`,
        )}
      />
      <div className="alert-wall-head">
        <span className="eyebrow">TRAFFIC · 红黄绿三灯 · 命中 {total.toLocaleString()} 户</span>
        <span className="meta">
          <b>{activeRules}</b> 条规则活跃 · 红档 TOP {redCases.length} 单待处置
        </span>
      </div>
      <ol className="alert-wall-list">
        {lights.map((l) => (
          <li key={l.tier} className="alert-wall-light" data-tier={l.tier} data-animate={l.animate}>
            <div className="alert-wall-bulb" aria-hidden>
              <span className="alert-wall-bulb-inner" />
              <span className="alert-wall-bulb-ring" />
            </div>
            <div className="alert-wall-body">
              <div className="alert-wall-row">
                <span className="lbl">{l.label}</span>
                <span className="pct">{l.pct}%</span>
              </div>
              <div className="alert-wall-count">
                <span className="num">{l.count}</span>
                <span className="unit">户</span>
              </div>
              <div className="alert-wall-bar" aria-hidden>
                <div className="alert-wall-fill" style={{ width: `${l.pct}%` }} />
              </div>
              <div className="alert-wall-caption">{l.caption}</div>
              <div className="alert-wall-detail">{l.detail}</div>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

/* ─── 融合 · 预警客户队列（中栏 hero 下方 sub-panel） ─── */

function ScanQueuePanel(p: { queue: ScanQueueCase[]; phase: ScanPhase }) {
  const red = p.queue.filter((c) => c.tier === "red").length;
  const yel = p.queue.filter((c) => c.tier === "yellow").length;
  return (
    <section className="rpt-panel al-queue" aria-label="预警客户队列">
      <PanelPinHandle
        {...panelPin(
          "scan-queue",
          "预警客户队列",
          `贷中预警 · 红 ${red} · 黄 ${yel}`,
          `按风险等级 desc → 最新命中时间 desc · ${p.queue.length} 户`,
        )}
      />
      <div className="al-queue__head">
        <div className="al-queue__ey">
          <span className="eyebrow">QUEUE · 预警客户队列</span>
          <span className="sub">按风险等级 desc → 最新命中时间 desc 排序</span>
        </div>
        <div className="al-queue__stat">
          <span className="al-queue__chip" data-tier="red">红 {red}</span>
          <span className="al-queue__chip" data-tier="yellow">黄 {yel}</span>
          {p.phase === "after" ? (
            <span className="al-queue__chip" data-tier="delta">
              最新扫描更新
            </span>
          ) : null}
        </div>
      </div>
      <ul className="al-queue__list">
        {p.queue.map((c) => (
          <li key={c.id} className="al-queue__item" data-tier={c.tier}>
            <span className="al-queue__ico" aria-hidden>客</span>
            <div className="al-queue__body">
              <div className="al-queue__name">{c.customer}</div>
              <div className="al-queue__reason">{c.reason}</div>
            </div>
            <div className="al-queue__meta">
              <span className="al-queue__tag" data-tier={c.tier}>
                {c.tier === "red" ? "高风险" : "中风险"}
              </span>
              <span className="al-queue__time">{c.updated}</span>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

/* ─── 融合 · 底部风险信号热区 horizontal bars（Codex #heat） ─── */

function SignalHeatmapPanel(p: { bars: SignalHeatBar[]; phase: ScanPhase }) {
  const max = Math.max(...p.bars.map((b) => b.score), 1);
  const top = p.bars[0];
  return (
    <section className="rpt-panel al-heatbars" aria-label="风险信号热区">
      <PanelPinHandle
        {...panelPin(
          "signal-heatmap",
          "风险信号热区",
          "贷中预警 · 5 信号百分制",
          `最强信号「${top?.label ?? "—"}」${top?.score ?? 0} 分 · ${p.bars.length} 条`,
        )}
      />
      <div className="al-heatbars__head">
        <div>
          <span className="eyebrow">SIGNAL · 风险信号热区</span>
          <div className="sub">
            识别外部链接、内部规则与流水异常在客户池中的聚集位置 · 最强信号「{top?.label ?? "—"}」{top?.score ?? 0} 分
          </div>
        </div>
        {p.phase === "after" ? (
          <span className="al-heatbars__delta">本轮扫描已刷新</span>
        ) : null}
      </div>
      <ul className="al-heatbars__list">
        {p.bars.map((b) => {
          const pct = Math.round((b.score / max) * 100);
          return (
            <li key={b.id} className="al-heatbars__row">
              <div className="al-heatbars__lbl">
                <span className="al-heatbars__name">{b.label}</span>
                {b.desc ? <span className="al-heatbars__desc">{b.desc}</span> : null}
              </div>
              <div className="al-heatbars__bar" aria-hidden>
                <div
                  className="al-heatbars__fill"
                  style={{ width: `${pct}%` } as CSSProperties}
                />
              </div>
              <span className="al-heatbars__score">{b.score}</span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

/* ────────────────────── LEFT ────────────────────── */

function ScanRangePanel(p: {
  options: ScanRangeOption[];
  selected: string;
  onSelect: (id: string) => void;
}) {
  const cur = p.options.find((o) => o.id === p.selected) ?? p.options[0];
  return (
    <div className="rpt-panel al-sr">
      <PanelPinHandle
        {...panelPin(
          "scan-range",
          "扫描范围",
          `贷中预警 · ${cur?.label ?? "全部客户"}`,
          `${cur?.coverage?.toLocaleString() ?? 0} 户 · ${cur?.hint ?? ""}`,
        )}
      />
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">扫描范围</div>
        <div className="rpt-panel__counter">
          {cur?.coverage?.toLocaleString() ?? 0} 户
        </div>
      </div>
      <div className="rpt-panel__body">
        <div className="al-sr__seg" role="tablist">
          {p.options.map((o) => (
            <button
              key={o.id}
              type="button"
              className="al-sr__seg-btn"
              data-active={o.id === p.selected ? "yes" : "no"}
              onClick={() => p.onSelect(o.id)}
            >
              {o.label}
            </button>
          ))}
        </div>
        {cur ? (
          <div className="al-sr__hint">
            本次覆盖 <b>{cur.coverage.toLocaleString()}</b> 户 · {cur.hint}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function KnowledgeUploadPanel() {
  const [count, setCount] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);
  function onChange(e: ChangeEvent<HTMLInputElement>) {
    setCount(e.target.files?.length ?? 0);
  }
  const hint =
    count > 0
      ? `已导入 ${count} 份知识库文件，下一次扫描将纳入规则`
      : "支持 Excel、PDF、名单库、规则文档";
  return (
    <div className="rpt-panel al-up">
      <PanelPinHandle
        {...panelPin(
          "knowledge-upload",
          "知识库上传",
          "贷中预警 · 风险规则/名单",
          count > 0
            ? `已导入 ${count} 份 · 下轮扫描纳入`
            : "支持 Excel / PDF / 名单库 / 规则文档",
        )}
      />
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">知识库上传</div>
        <div className="rpt-panel__counter">{count > 0 ? `+${count}` : "未导入"}</div>
      </div>
      <div className="rpt-panel__body">
        <label
          className="al-up__drop"
          onClick={(e) => {
            e.preventDefault();
            inputRef.current?.click();
          }}
        >
          <div className="al-up__plus" aria-hidden>
            +
          </div>
          <div className="al-up__ttl">上传风险知识库</div>
          <div className="al-up__hint">{hint}</div>
          <input
            ref={inputRef}
            type="file"
            multiple
            className="al-up__input"
            onChange={onChange}
            aria-label="上传风险知识库"
          />
        </label>
        <div className="al-up__thr">
          <span className="al-up__thr-lbl">监测阈值</span>
          <span className="al-up__thr-body">
            外部负面命中 1 次即预警；流水异常连续 2 周升级中高风险
          </span>
        </div>
      </div>
    </div>
  );
}

function SourceListPanel({ sources }: { sources: KnowledgeSource[] }) {
  const online = sources.filter((s) => s.status === "online").length;
  return (
    <div className="rpt-panel al-src">
      <PanelPinHandle
        {...panelPin(
          "source-list",
          "监测源",
          `贷中预警 · ${online}/${sources.length} 在线`,
          sources
            .slice(0, 4)
            .map((s) => s.label)
            .join(" · "),
        )}
      />
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">监测源</div>
        <div className="rpt-panel__counter">
          {online}/{sources.length} 在线
        </div>
      </div>
      <div className="rpt-panel__body">
        <ul className="al-src__list">
          {sources.map((s) => (
            <li key={s.id} className="al-src__item" data-status={s.status}>
              <span className="al-src__ico" aria-hidden>
                源
              </span>
              <div className="al-src__body">
                <div className="al-src__lbl">{s.label}</div>
                <div className="al-src__desc">{s.desc}</div>
              </div>
              <span className="al-src__tag" data-status={s.status}>
                {s.statusLabel}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function RulesPanel({ rules }: { rules: AlertRule[] }) {
  const enabled = rules.filter((r) => r.enabled).length;
  const totalHit = rules.reduce((s, r) => s + (r.enabled ? r.hit : 0), 0);
  return (
    <div className="rpt-panel al-rl">
      <PanelPinHandle
        {...panelPin(
          "rules",
          "扫描规则",
          `贷中预警 · ${enabled}/${rules.length} 启用`,
          `命中 ${totalHit} · 外部 / 内部 / 交叉 三类`,
        )}
      />
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">规则</div>
        <div className="rpt-panel__counter">
          {enabled}/{rules.length} · 命中 {totalHit}
        </div>
      </div>
      <div className="rpt-panel__body">
        <ul className="al-rl__list">
          {rules.map((r) => (
            <li
              key={r.id}
              className="al-rl__item"
              data-cat={r.category}
              data-sev={r.severity}
              data-enabled={r.enabled ? "yes" : "no"}
            >
              <span className="al-rl__code">{r.code}</span>
              <div className="al-rl__body">
                <div className="al-rl__label">{r.label}</div>
                <div className="al-rl__meta">
                  <span className="al-rl__cat">{CAT_LABEL[r.category]}</span>
                  <span className="al-rl__sep">·</span>
                  <span className="al-rl__sev">{SEV_LABEL[r.severity]}</span>
                </div>
              </div>
              <span className="al-rl__hit">{r.enabled ? r.hit : "—"}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

const CAT_LABEL: Record<string, string> = { external: "外部", internal: "内部", cross: "交叉" };
const SEV_LABEL: Record<string, string> = { high: "高危", mid: "中危", low: "低危" };

function PipelinePanel({ steps }: { steps: AlertPipelineStep[] }) {
  const done = steps.filter((s) => s.status === "done").length;
  return (
    <div className="rpt-panel al-pl">
      <PanelPinHandle
        {...panelPin(
          "pipeline",
          "扫描流水",
          `贷中预警 · ${done}/${steps.length} 完成`,
          steps.find((s) => s.status === "active")?.label ?? "流程完成",
        )}
      />
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">扫描流水</div>
        <div className="rpt-panel__counter">
          {steps.filter((s) => s.status === "done").length}/{steps.length}
        </div>
      </div>
      <div className="rpt-panel__body">
        <ol className="al-pl__list">
          {steps.map((s, i) => (
            <li key={s.id} className="al-pl__item" data-status={s.status}>
              <span className="al-pl__idx">{String(i + 1).padStart(2, "0")}</span>
              <div className="al-pl__body">
                <div className="al-pl__label">{s.label}</div>
                {s.note ? <div className="al-pl__note">{s.note}</div> : null}
              </div>
              <span className="al-pl__mark" aria-hidden>
                {s.status === "done" ? "✓" : s.status === "active" ? "●" : "○"}
              </span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

function RecentPanel({ recent }: { recent: AlertRecentSession[] }) {
  return (
    <div className="rpt-panel al-rc al-rc--lite">
      <PanelPinHandle
        {...panelPin(
          "recent",
          "近期扫描",
          `贷中预警 · ${recent.length} 次`,
          recent[0]?.objective ?? "无",
        )}
      />
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">近期</div>
        <div className="rpt-panel__counter">{recent.length}</div>
      </div>
      <div className="rpt-panel__body">
        <ul className="al-rc__list">
          {recent.map((r) => (
            <li key={r.id} className="al-rc__row">
              <span className="al-rc__name">{r.objective}</span>
              <span className="al-rc__red">红 {r.redCount}</span>
              <span className="al-rc__time">{r.updated}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/* ────────────────────── MID ────────────────────── */

function ConversationPanel({ msgs }: { msgs: ConversationMessage[] }) {
  const scrollRef = useRef<HTMLElement | null>(null);
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [msgs.length]);

  const lastAi = [...msgs].reverse().find((m) => m.kind === "ai-response" || m.kind === "ai-question");
  return (
    <section
      className="rpt-panel rpt-panel--conv al-conv rpt-conv"
      ref={scrollRef}
    >
      <PanelPinHandle
        {...panelPin(
          "conversation",
          "预警对话",
          `贷中预警 · ${msgs.length} 条`,
          lastAi ? msgTitle(lastAi.content) : "等待对话开始",
        )}
      />
      {msgs.map((m) => (
        <ConversationMsg key={m.id} m={m} />
      ))}
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
          {...msgPinProps(m, isCmd ? "客户经理 · /command" : "客户经理 · 王哲")}
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
        <MessagePinHandle {...msgPinProps(m, "TOWER · 推理")} />
        <div className="rpt-msg__head">
          <span className="rpt-msg__who">TOWER · 推理</span>
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
  const who = m.kind === "ai-question" ? "TOWER · 问" : "TOWER";
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

function AlertComposer() {
  const [value, setValue] = useState("");
  const hints = ["看 top 红档", "行业切片 · 建材", "升级触达", "下发工单", "对比上周"];
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
        placeholder="对 TOWER 提问 / 给指令：看 top 红档、切行业、升级触达、下发工单…"
        rows={3}
      />
      <div className="rpt-composer__foot">
        <span className="rpt-composer__hint-txt">Enter 发 · Shift+Enter 换行 · /dispatch 下发触达</span>
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
  distribution: IndustryDistribution[];
  heat: HeatCell[];
  reach: ReachRate[];
  topCases: TopCase[];
  totals: { red: number; yellow: number; green: number };
}) {
  const tabLabel = p.tab === "dist" ? "分档分布" : p.tab === "heat" ? "30 天热力" : "触达率";
  return (
    <div className="rpt-panel al-out">
      <PanelPinHandle
        {...panelPin(
          "output",
          "预警看板",
          `贷中预警 · ${tabLabel}`,
          p.tab === "dist"
            ? `行业切片 ${p.distribution.length} 类 · 红 ${p.totals.red}`
            : p.tab === "heat"
              ? `30 天累计 ${p.heat.reduce((s, c) => s + c.count, 0)} 次`
              : `红档触达率 ${p.reach.find((r) => r.tier === "red")?.reachedPct.toFixed(1) ?? "—"}%`,
        )}
      />
      <div className="rpt-panel__head al-out__head">
        <div className="rpt-panel__eyebrow">预警看板</div>
        <div className="al-out__tabs" role="tablist">
          <TabBtn active={p.tab === "dist"} onClick={() => p.onTabChange("dist")}>分档</TabBtn>
          <TabBtn active={p.tab === "heat"} onClick={() => p.onTabChange("heat")}>热力</TabBtn>
          <TabBtn active={p.tab === "reach"} onClick={() => p.onTabChange("reach")}>触达</TabBtn>
        </div>
      </div>
      <div className="rpt-panel__body al-out__body">
        {p.tab === "dist" ? (
          <DistView distribution={p.distribution} totals={p.totals} topCases={p.topCases} />
        ) : null}
        {p.tab === "heat" ? <HeatView heat={p.heat} /> : null}
        {p.tab === "reach" ? <ReachView reach={p.reach} /> : null}
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
    <button type="button" className="al-out__tab" data-active={active ? "yes" : "no"} onClick={onClick}>
      {children}
    </button>
  );
}

/* ── 分档 stacked ── */

function DistView(p: {
  distribution: IndustryDistribution[];
  totals: { red: number; yellow: number; green: number };
  topCases: TopCase[];
}) {
  const maxTotal = Math.max(...p.distribution.map((d) => d.total));
  const tot = p.totals.red + p.totals.yellow + p.totals.green;
  return (
    <div className="al-dv">
      <div className="al-dv__tot">
        <div className="al-dv__tot-head">全池 {tot.toLocaleString()} 户</div>
        <div className="al-dv__tot-bar">
          <div
            className="al-dv__tot-seg al-dv__tot-seg--red"
            style={{ width: `${(p.totals.red / tot) * 100}%` } as CSSProperties}
            title={`红 ${p.totals.red}`}
          />
          <div
            className="al-dv__tot-seg al-dv__tot-seg--yellow"
            style={{ width: `${(p.totals.yellow / tot) * 100}%` } as CSSProperties}
            title={`黄 ${p.totals.yellow}`}
          />
          <div
            className="al-dv__tot-seg al-dv__tot-seg--green"
            style={{ width: `${(p.totals.green / tot) * 100}%` } as CSSProperties}
            title={`绿 ${p.totals.green}`}
          />
        </div>
        <div className="al-dv__tot-legend">
          <span className="al-dv__leg al-dv__leg--red">红 {p.totals.red}</span>
          <span className="al-dv__leg al-dv__leg--yellow">黄 {p.totals.yellow}</span>
          <span className="al-dv__leg al-dv__leg--green">绿 {p.totals.green}</span>
        </div>
      </div>

      <div className="al-dv__ttl">按行业切片</div>
      <ul className="al-dv__list">
        {p.distribution.map((d) => {
          const rp = (d.red / d.total) * 100;
          const yp = (d.yellow / d.total) * 100;
          const gp = (d.green / d.total) * 100;
          const barW = (d.total / maxTotal) * 100;
          return (
            <li key={d.industry} className="al-dv__row">
              <div className="al-dv__lbl">{d.industry}</div>
              <div className="al-dv__bar-wrap" style={{ width: `${barW}%` } as CSSProperties}>
                <div className="al-dv__bar">
                  <div className="al-dv__seg al-dv__seg--red" style={{ width: `${rp}%` } as CSSProperties} />
                  <div className="al-dv__seg al-dv__seg--yellow" style={{ width: `${yp}%` } as CSSProperties} />
                  <div className="al-dv__seg al-dv__seg--green" style={{ width: `${gp}%` } as CSSProperties} />
                </div>
              </div>
              <div className="al-dv__nums">
                <span className="al-dv__num al-dv__num--red">{d.red}</span>
                <span className="al-dv__num al-dv__num--yellow">{d.yellow}</span>
                <span className="al-dv__num al-dv__num--green">{d.green}</span>
              </div>
            </li>
          );
        })}
      </ul>

      <div className="al-dv__ttl">Top 红档</div>
      <ul className="al-dv__tops">
        {p.topCases.filter((c) => c.tier === "red").map((c) => (
          <li key={c.id} className="al-dv__tc">
            <div className="al-dv__tc-head">
              <span className="al-dv__tc-tier" data-tier={c.tier}>红</span>
              <div className="al-dv__tc-name">{c.customer}</div>
              <span className="al-dv__tc-amt">{c.amount}</span>
            </div>
            <ul className="al-dv__tc-trig">
              {c.triggers.map((t, i) => (
                <li key={i}>{t}</li>
              ))}
            </ul>
            <div className="al-dv__tc-adv">处置 · {c.advice}</div>
            <div className="al-dv__tc-time">{c.lastUpdate}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ── 热力日历 ── */

function HeatView({ heat }: { heat: HeatCell[] }) {
  const total = heat.reduce((s, c) => s + c.count, 0);
  const peak = Math.max(...heat.map((c) => c.count));
  return (
    <div className="al-hv">
      <div className="al-hv__kpi">
        <div>
          <span className="al-hv__kpi-num">{total}</span>
          <span className="al-hv__kpi-unit">次</span>
        </div>
        <div className="al-hv__kpi-sub">
          近 30 天累计触发 · 峰值 {peak}/日 · 均值 {(total / heat.length).toFixed(1)}/日
        </div>
      </div>

      <div className="al-hv__grid">
        {heat.map((c) => (
          <div
            key={c.date}
            className="al-hv__cell"
            data-level={c.level}
            title={`${c.date} · ${c.count} 次`}
          >
            <span className="al-hv__cell-n">{c.count}</span>
          </div>
        ))}
      </div>

      <div className="al-hv__legend">
        <span>少</span>
        <span className="al-hv__leg-cell" data-level={0} />
        <span className="al-hv__leg-cell" data-level={1} />
        <span className="al-hv__leg-cell" data-level={2} />
        <span className="al-hv__leg-cell" data-level={3} />
        <span className="al-hv__leg-cell" data-level={4} />
        <span>多</span>
      </div>

      <div className="al-hv__note">
        近一周触发明显抬头（+180%）· 建议：重点关注 4-16 之后命中的 63 户建材/制造业客户
      </div>
    </div>
  );
}

/* ── 触达率 ── */

function ReachView({ reach }: { reach: ReachRate[] }) {
  return (
    <div className="al-rv">
      <ul className="al-rv__list">
        {reach.map((r) => (
          <li key={r.tier} className="al-rv__item" data-tier={r.tier}>
            <div className="al-rv__head">
              <span className="al-rv__tier" data-tier={r.tier}>
                {r.tier === "red" ? "红" : r.tier === "yellow" ? "黄" : "绿"}
              </span>
              <div className="al-rv__lbl">{r.label}</div>
              <span className="al-rv__pct">{r.reachedPct.toFixed(1)}%</span>
            </div>
            <div className="al-rv__bar">
              <div
                className="al-rv__bar-fill"
                data-tier={r.tier}
                style={{ width: `${r.reachedPct}%` } as CSSProperties}
              />
            </div>
            <div className="al-rv__meta">
              已触达 {r.reached.toLocaleString()} / 全量 {r.total.toLocaleString()}
            </div>
            <div className="al-rv__ch">
              <span className="al-rv__ch-item">
                <span className="al-rv__ch-lbl">电话</span>
                <span className="al-rv__ch-num">{r.channels.phone}</span>
              </span>
              <span className="al-rv__ch-item">
                <span className="al-rv__ch-lbl">短信</span>
                <span className="al-rv__ch-num">{r.channels.sms}</span>
              </span>
              <span className="al-rv__ch-item">
                <span className="al-rv__ch-lbl">面访</span>
                <span className="al-rv__ch-num">{r.channels.visit}</span>
              </span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
