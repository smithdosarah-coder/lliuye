"use client";

/**
 * /archive/credit · Agent 03 BENCH · 对话式授信决策 workspace
 * 2026-04-22 v3 · Codex 融合重设计：
 *   顶栏 AGENT eyebrow + 模式 tabs（对公/普惠/对私）
 *   Primary Profile Hero · 企业 chips + 综合分圆环 + CTA "生成授信辅助" + 4 维 mini metrics
 *   左栏 · 资料上传 (materials) + 资料库接口 (dataSources) + 案件概要 + 近期
 *   中栏 · 对话 + CreditComposer（不动）
 *   右栏 · 决策看板 tabs (radar / limit / cases)
 *   底栏 · 证据链（正向/提醒/缺失） | 生成流程（pipeline）
 *
 * 壳类：.v-archive--canon[data-agent="credit"] → --agent = var(--t-credit) 青蓝
 * 所有 .rpt-panel 挂 PanelPinHandle · 所有消息挂 MessagePinHandle（拖到白板/画布）
 */

import { useEffect, useRef, useState, type CSSProperties } from "react";
import {
  ClaimText,
  EvidenceProvider,
  EvidenceTrail,
  UnfilledFields,
} from "@/components/evidence";
import { CREDIT_EVIDENCE } from "@/components/evidence/fixtures";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";
import { MessagePinHandle } from "@/components/shell/MessagePinHandle";
import { PanelPinHandle } from "@/components/shell/PanelPinHandle";
import { CustomerSelector } from "@/components/shared/CustomerSelector";
import { RiskRadar, type RiskRadarSegment } from "./RiskRadar";
import {
  CREDIT_GLOBAL_STATS,
  CREDIT_MODE_LABEL,
  CREDIT_SESSIONS,
  type CaseRecall,
  type ConversationMessage,
  type CreditMode,
  type CreditProfile,
  type CreditRadarDim,
  type CreditQuery,
  type CreditRecentSession,
  type CreditSession,
  type DataSourcesPanel,
  type EvidenceItem,
  type EvidencesPanel,
  type GenerateStep,
  type LimitSuggestion,
  type MaterialsPanel as MaterialsPanelData,
  type RedLine,
  type CreditPipelineStep,
} from "@/lib/mock/agent-credit-session";

type OutputTab = "radar" | "limit" | "cases";

const DECISION_LABEL: Record<string, string> = {
  approved: "通过",
  "approved-cut": "打折批",
  rejected: "拒",
  pending: "待决",
};

const AGENT_KEY = "credit";
const AGENT_HREF = "/archive/credit";
const AGENT_ACCENT = "--t-credit";

/* W-CF-A2 · 2026-04-28 · stage_tab 命名与 backend 对齐 (per agent-credit-spec §1 + W-C2-A2 backend v4.0)
   内部 CreditMode keys 不变 (mock data map 不动 · 现 testid/Tabbar UI 不破)
   onboarding 字面 testid 用 "corporate" / "small_business" / "retail" mapping. */
const MODE_TO_STAGE_TAB: Record<CreditMode, "corporate" | "small_business" | "retail"> = {
  corp: "corporate",
  small: "small_business",
  retail: "retail",
};

const STAGE_TAB_DESCRIPTION: Record<CreditMode, string> = {
  corp: "对公授信 · 50-5000 万 · 4 维评分 + 30 红线",
  small: "普惠 / 小微 · 10-500 万 · 抵押权重高 · 阈值放宽 5 分",
  retail: "对私 / 零售 · 5-500 万 · FICO 式 800/760/700/680 评级",
};

export default function CreditWorkspace() {
  const [mode, setMode] = useState<CreditMode>("corp");
  const [tab, setTab] = useState<OutputTab>("radar");
  const session = CREDIT_SESSIONS[mode];

  // CTA 生成授信辅助 · 动态进度条状态（纯前端 mock · 5 步 450ms）
  const [progress, setProgress] = useState<{
    running: boolean;
    step: number;
    pct: number;
    label: string;
  }>({
    running: false,
    step: -1,
    pct: 100,
    label: "已完成综合判断",
  });
  const timerRef = useRef<number | null>(null);
  /* 2026-04-23 · credit 也统一空态 · startGenerate 最后一步触发 · 数据显现 */
  const [scanned, setScanned] = useState(false);

  /* W-CF-A2 · 2026-04-28 · empty-state-design-protocol v1.0 落地
     started default false · 仅渲染 Hero + 3 CTA + skeleton + status pill
     mock data 不 default load · 用户主动选 dropdown / submit 才 start */
  const [started, setStarted] = useState(false);
  const [liveAdvice, setLiveAdvice] = useState<Record<string, unknown> | null>(null);
  const [decisionId, setDecisionId] = useState<string | null>(null);
  const [decisionRunning, setDecisionRunning] = useState(false);
  const [decisionError, setDecisionError] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current !== null) {
        window.clearInterval(timerRef.current);
      }
    };
  }, []);

  /* 起授信决策 · POST /api/credit/decision SSE · 收 advice + decision_id
     mock=true 兼容无 LLM key 环境 (curl-friendly · spec test 也走 mock 避真 LLM 依赖) */
  async function runDecision(opts: { mockMode: boolean }) {
    if (decisionRunning) return;
    setStarted(true);
    setDecisionRunning(true);
    setDecisionError(null);
    setLiveAdvice(null);
    setDecisionId(null);
    try {
      const apiBase =
        (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE) || "";
      const stageTab = MODE_TO_STAGE_TAB[mode];
      // preset_name 默认用 mode 的第一个预置 (后续 Stage 可让用户在 Drawer 选)
      const presetByMode: Record<CreditMode, string> = {
        corp: "dingsheng_trade",
        small: "dingsheng_trade",
        retail: "zhangsan_restaurant",
      };
      const res = await fetch(`${apiBase}/api/credit/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          stage_tab: stageTab,
          mock: opts.mockMode,
          preset_name: opts.mockMode ? null : presetByMode[mode],
        }),
      });
      if (!res.ok || !res.body) {
        throw new Error(`HTTP ${res.status}`);
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const blocks = buf.split("\n\n");
        buf = blocks.pop() ?? "";
        for (const block of blocks) {
          const dataLine = block.split("\n").find((l) => l.startsWith("data:"));
          if (!dataLine) continue;
          try {
            const evt = JSON.parse(dataLine.slice(5).trim()) as {
              event?: string;
              stage?: string;
              decision_id?: string;
              payload?: Record<string, unknown>;
              message?: string;
            };
            if (evt.event === "stage" && evt.stage === "advising_done" && evt.payload) {
              setLiveAdvice(evt.payload);
              setScanned(true);
            }
            if (evt.event === "decision_cached" && evt.decision_id) {
              setDecisionId(evt.decision_id);
            }
            if (evt.event === "error") {
              setDecisionError(String(evt.message ?? "decision SSE error"));
            }
          } catch {
            /* skip malformed line */
          }
        }
      }
    } catch (err) {
      setDecisionError(err instanceof Error ? err.message : String(err));
    } finally {
      setDecisionRunning(false);
    }
  }

  /* tertiary CTA · 选历史 (示例) session · setStarted=true 但不调 backend · 看 mock UI */
  function selectHistoricalDemo() {
    setStarted(true);
    setScanned(true);
    setLiveAdvice(null);
    setDecisionId(null);
    setDecisionError(null);
  }

  function startGenerate() {
    if (progress.running) return;
    if (timerRef.current !== null) window.clearInterval(timerRef.current);
    const steps = session.generateSteps;
    setProgress({ running: true, step: 0, pct: 0, label: steps[0].label });
    let i = 0;
    timerRef.current = window.setInterval(() => {
      const s = steps[i];
      setProgress({
        running: i < steps.length - 1,
        step: i,
        pct: s.pct,
        label: s.label,
      });
      if (i === steps.length - 1) {
        if (timerRef.current !== null) window.clearInterval(timerRef.current);
        timerRef.current = null;
        /* 最后一步触发 · 数据 fade-in 显现 */
        setScanned(true);
      }
      i += 1;
    }, 450);
  }

  /* W-CF-A2 · empty-state v1.0 路径
     started=false → 渲染 EmptyState (Hero + 3 CTA + skeleton + status pill · 不渲染 mock data)
     started=true  → 渲染现有完整 workspace (4 panel + EvidenceTrail + RiskRadar 等) */
  /* B-banner · workspace 顶部统一错误条 · started 与 !started 两分支共用 */
  const creditTopBanner = decisionError ? (
    <div
      role="alert"
      data-testid="credit-error-banner"
      className="credit-error-banner"
    >
      <span className="credit-error-banner__icon" aria-hidden>⚠</span>
      <span className="credit-error-banner__text">
        <b>决策操作失败</b>
        <span className="credit-error-banner__detail">{decisionError}</span>
      </span>
      <button
        type="button"
        className="credit-error-banner__retry"
        onClick={() => runDecision({ mockMode: false })}
      >
        重试
      </button>
      <button
        type="button"
        className="credit-error-banner__dismiss"
        onClick={() => setDecisionError(null)}
        aria-label="关闭错误提示"
      >
        ×
      </button>
    </div>
  ) : null;

  if (!started) {
    return (
      <EvidenceProvider
        items={CREDIT_EVIDENCE.items}
        unfilledFields={CREDIT_EVIDENCE.unfilledFields}
      >
        <div
          className="rpt-workspace credit-empty-root"
          data-credit-mode={mode}
          data-scanned="no"
          data-credit-started="no"
        >
          {creditTopBanner}
          <CreditEmptyState
            mode={mode}
            onModeChange={setMode}
            onPrimary={() => runDecision({ mockMode: false })}
            onSecondary={() => runDecision({ mockMode: true })}
            onTertiary={selectHistoricalDemo}
            decisionRunning={decisionRunning}
            decisionError={decisionError}
          />
        </div>
      </EvidenceProvider>
    );
  }

  return (
    <EvidenceProvider
      items={CREDIT_EVIDENCE.items}
      unfilledFields={CREDIT_EVIDENCE.unfilledFields}
    >
    <div
      className="rpt-workspace"
      data-credit-mode={mode}
      data-credit-started="yes"
      data-scanned={scanned ? "yes" : "no"}
    >
      {creditTopBanner}
      <TopBar
        mode={mode}
        onModeChange={setMode}
        sessionsCount={CREDIT_GLOBAL_STATS.weeklyProcessed}
      />

      <PrimaryProfileHero
        profile={session.profile}
        objective={session.objective}
        stage={session.stage}
        updated={session.updated}
        decision={session.decision}
        overallScore={session.overallScore}
        radar={session.radar}
        limit={session.limit}
        redLines={session.redLines}
        qcCounts={session.qcCounts}
        progress={progress}
        onGenerate={startGenerate}
      />

      <DashboardBand
        radar={session.radar}
        overall={session.overallScore}
        limit={session.limit}
        redLines={session.redLines}
      />

      <div className="rpt-grid">
        <aside className="rpt-col rpt-col--left">
          <QueryPanel q={session.query} />
          <MaterialsPanel data={session.materials} />
          <DataSourcesPanel data={session.dataSources} />
          <RecentPanel recent={session.recentSessions} />
        </aside>

        <section className="rpt-col rpt-col--mid">
          <ConversationPanel msgs={session.conversation} />
        </section>

        <section className="rpt-col rpt-col--right">
          <OutputPanel
            tab={tab}
            onTabChange={setTab}
            radar={session.radar}
            overall={session.overallScore}
            limit={session.limit}
            redLines={session.redLines}
            cases={session.cases}
          />
        </section>
      </div>

      <BottomBar
        evidences={session.evidences}
        pipeline={session.pipeline}
        generateSteps={session.generateSteps}
        progress={progress}
      />
      {/* W-CF-A2 · 决策完成 advice + Word 导出 (live SSE 路径) */}
      <CreditDecisionAdvicePanel
        liveAdvice={liveAdvice}
        decisionId={decisionId}
        decisionRunning={decisionRunning}
        decisionError={decisionError}
        stageTab={MODE_TO_STAGE_TAB[mode]}
      />
      <section className="ev-claim-summary" aria-label="Evidence-grounded 分析结论">
        <span className="ev-claim-summary-label">分析结论 · Evidence-grounded</span>
        <ClaimText text={CREDIT_EVIDENCE.summary} />
      </section>
      <UnfilledFields />
      <RiskRadarPreview mode={mode} session={session} />
      <EvidenceTrail agentTone="credit" />
    </div>
    </EvidenceProvider>
  );
}

/* ─────────── Q-033 · RiskRadar Preview · L1-3 ─────────── */
/* 596283f wrapper · 复用 ScoreRadar · 与既有 session.radar (CreditRadarDim) 并存 ·
   提供四维 segment 派发 (corp/sme: 财务/行业/经营/担保 · retail: 还款能力/还款
   意愿/稳定性/担保)，从 session.radar 抽 score 拼 ScoringPayload-shape 子集 ·
   仅可视 demo · 不替代既有 RadarChart。 */
function RiskRadarPreview({
  mode,
  session,
}: {
  mode: CreditMode;
  session: CreditSession;
}) {
  const segment: RiskRadarSegment =
    mode === "corp" ? "corporate" : mode === "small" ? "sme" : "retail";
  const corpKeys = [
    "financial_score",
    "industry_score",
    "operational_score",
    "guarantee_score",
  ] as const;
  const retailKeys = [
    "repayment_capacity",
    "repayment_willingness",
    "stability",
    "collateral",
  ] as const;
  const radarByKey: Record<string, number> = {};
  for (const dim of session.radar) {
    radarByKey[dim.key] = dim.score;
  }
  const flat = {
    financial_score: radarByKey["fin"],
    industry_score: radarByKey["ind"] ?? radarByKey["ops"],
    operational_score: radarByKey["ops"],
    guarantee_score: radarByKey["guar"],
  };
  const cat = {
    repayment_capacity: radarByKey["repay"] ?? radarByKey["fin"],
    repayment_willingness: radarByKey["will"] ?? radarByKey["comp"],
    stability: radarByKey["stab"] ?? radarByKey["ops"],
    collateral: radarByKey["coll"] ?? radarByKey["guar"],
  };
  const scoring = segment === "corporate" ? flat : { category_scores: cat };
  return (
    <section
      className="rpt-panel risk-radar-preview"
      aria-label="L1-3 RiskRadar (Q-033)"
      data-testid="risk-radar-preview"
    >
      <header className="risk-radar-preview-head">
        <span className="risk-radar-preview-eyebrow">L1-3 · 四维风险雷达</span>
        <span className="risk-radar-preview-segment">segment: {segment}</span>
      </header>
      <RiskRadar scoring={scoring} segment={segment} />
    </section>
  );
}

/* ─────────── TopBar · AGENT eyebrow + 模式 tabs ─────────── */

function TopBar({
  mode,
  onModeChange,
  sessionsCount,
}: {
  mode: CreditMode;
  onModeChange: (m: CreditMode) => void;
  sessionsCount: string;
}) {
  return (
    <div className="credit-topbar">
      <div className="credit-topbar__left">
        <span className="credit-topbar__badge" aria-hidden>
          ✦
        </span>
        <span className="credit-topbar__agent">AGENT · 03 · BENCH</span>
        <span className="credit-topbar__sep">·</span>
        <span className="credit-topbar__view">授信决策辅助</span>
      </div>
      <div className="credit-topbar__mode" role="tablist" aria-label="分析模式">
        <span className="credit-topbar__mode-lbl">模式</span>
        {(["corp", "small", "retail"] as CreditMode[]).map((k) => (
          <button
            key={k}
            type="button"
            role="tab"
            aria-selected={mode === k}
            className="credit-topbar__mode-btn"
            data-active={mode === k ? "yes" : "no"}
            onClick={() => onModeChange(k)}
          >
            {CREDIT_MODE_LABEL[k]}
          </button>
        ))}
      </div>
      <div className="credit-topbar__right">
        <span className="credit-topbar__stat-n">{sessionsCount}</span>
        <span className="credit-topbar__stat-l">本周已决</span>
      </div>
    </div>
  );
}

/* ─────────────── v2 Hero Band · 四维评分仪表盘 ─────────────── */
/* Stage 4 · b6f9ef9 patch · DashboardBand 4 圆环 (综合评分 / 建议额度 /
   建议期限 / 红线检查) + 4 维权重 chip · tone 色阶走 --safe / --t-report /
   --t-alert · CSS .credit-band-* 已在 main credit-workspace.css。 */

function DashboardBand(p: {
  radar: CreditRadarDim[];
  overall: number;
  limit: LimitSuggestion;
  redLines: RedLine[];
}) {
  const dims = p.radar;
  const overall = p.overall;
  const cutPct = Math.round((p.limit.suggested / p.limit.applied) * 100);
  const redFail = p.redLines.filter((r) => r.status === "fail").length;
  const redWarn = p.redLines.filter((r) => r.status === "warn").length;

  const cards = [
    {
      key: "overall",
      label: "综合评分",
      value: overall,
      unit: "分",
      caption: "综合 4 维 × 权重",
      detail: overall >= 75 ? "绿区" : overall >= 60 ? "关注区" : "红区",
      pct: overall,
      tone: overall >= 75 ? "good" : overall >= 60 ? "warn" : "bad",
    },
    {
      key: "limit",
      label: "建议额度",
      value: p.limit.suggested,
      unit: "万",
      caption: `申请 ${p.limit.applied} 万`,
      detail: cutPct < 100 ? `打折 ${cutPct}%` : "足额批",
      pct: Math.min(cutPct, 100),
      tone: cutPct >= 90 ? "good" : cutPct >= 70 ? "warn" : "bad",
    },
    {
      key: "tenor",
      label: "建议期限",
      value: p.limit.tenorMonths,
      unit: "月",
      caption: `利率 ${(p.limit.rateBps / 100).toFixed(2)}%`,
      detail: `区间 ${p.limit.tenorRange[0]}–${p.limit.tenorRange[1]} 月`,
      pct: Math.round((p.limit.tenorMonths / p.limit.tenorRange[1]) * 100),
      tone: "neutral",
    },
    {
      key: "red",
      label: "红线检查",
      value: p.redLines.length - redFail - redWarn,
      unit: `/ ${p.redLines.length}`,
      caption: `${redFail} 触发 · ${redWarn} 预警`,
      detail: redFail === 0 ? "无阻断" : "阻断",
      pct: Math.round(
        ((p.redLines.length - redFail - redWarn) / Math.max(p.redLines.length, 1)) * 100,
      ),
      tone: redFail === 0 ? "good" : "bad",
    },
  ] as const;

  return (
    <section className="rpt-panel credit-band" aria-label="四维评分仪表盘">
      <div className="credit-band-head">
        <span className="eyebrow">DASHBOARD · 四维评分 × 额度 × 红线</span>
        <div className="dims">
          {dims.map((d) => (
            <span key={d.key} className="dim" title={d.note}>
              <span className="k">{d.label}</span>
              <span className="v">{d.score}</span>
              <span className="w">× {Math.round(d.weight * 100)}%</span>
            </span>
          ))}
        </div>
      </div>
      <ol className="credit-band-list">
        {cards.map((c) => (
          <li key={c.key} className="credit-band-card" data-tone={c.tone}>
            <div className="credit-band-dial" aria-hidden>
              <svg width="64" height="64" viewBox="0 0 64 64">
                <circle cx="32" cy="32" r="26" className="track" />
                <circle
                  cx="32"
                  cy="32"
                  r="26"
                  className="fill"
                  strokeDasharray={`${(c.pct / 100) * 163.36} 163.36`}
                  transform="rotate(-90 32 32)"
                />
              </svg>
              <div className="credit-band-val">
                <span className="num">{c.value}</span>
                <span className="unit">{c.unit}</span>
              </div>
            </div>
            <div className="credit-band-body">
              <div className="lbl">{c.label}</div>
              <div className="caption">{c.caption}</div>
              <div className="detail">{c.detail}</div>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

/* ─────────── Primary Profile Hero ───────────
   融合 Codex 的 hero + 我们的 DashboardBand：
   - 左 · chips + tagline + 4 维 mini metrics
   - 右 · 综合分圆环 + decision + CTA + 进度条 */

function PrimaryProfileHero(p: {
  profile: CreditProfile;
  objective: string;
  stage: string;
  updated: string;
  decision: "approved" | "approved-cut" | "rejected" | "pending";
  overallScore: number;
  radar: CreditRadarDim[];
  limit: LimitSuggestion;
  redLines: RedLine[];
  qcCounts: { block: number; warn: number; info: number };
  progress: { running: boolean; step: number; pct: number; label: string };
  onGenerate: () => void;
}) {
  const redFail = p.redLines.filter((r) => r.status === "fail").length;
  const redWarn = p.redLines.filter((r) => r.status === "warn").length;

  return (
    <header className="credit-hero" data-decision={p.decision}>
      <PanelPinHandle
        id={`credit:hero:${p.objective}`}
        title={`授信画像 · 综合 ${p.overallScore}`}
        subtitle={`${DECISION_LABEL[p.decision]} · ${p.stage}`}
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb={p.profile.tagline}
      />

      <div className="credit-hero__body">
        <div className="credit-hero__left">
          {/* 2026-04-23 · demo 客户选择器 · 替代硬编 objective · 演示不同客户 */}
          <CustomerSelector className="credit-hero__customer" />
          <h1 className="credit-hero__title credit-hero__title--mini">{p.objective}</h1>
          <div className="credit-hero__chips">
            {p.profile.chips.map((c) => (
              <span key={c} className="credit-hero__chip">
                {c}
              </span>
            ))}
          </div>
          <p className="credit-hero__tagline">{p.profile.tagline}</p>
          <dl className="credit-hero__metrics">
            {p.radar.map((d) => (
              <div key={d.key} className="credit-hero__metric">
                <dt>{d.label}</dt>
                <dd>
                  <span className="credit-hero__metric-v">{d.score}</span>
                  <span className="credit-hero__metric-w">× {Math.round(d.weight * 100)}%</span>
                </dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="credit-hero__right">
          <ScoreRing score={p.overallScore} decision={p.decision} />
          <div className="credit-hero__decision">
            <span className="credit-hero__decision-txt">{DECISION_LABEL[p.decision]}</span>
            <span className="credit-hero__decision-sub">{p.stage}</span>
          </div>
          <div className="credit-hero__qc">
            <span className="credit-hero__qc-chip" data-tone="block">
              {p.qcCounts.block} 阻
            </span>
            <span className="credit-hero__qc-chip" data-tone="warn">
              {p.qcCounts.warn + redWarn} 警
            </span>
            <span className="credit-hero__qc-chip" data-tone="info">
              {p.qcCounts.info} 提
            </span>
          </div>
          <button
            type="button"
            className="credit-hero__cta"
            onClick={p.onGenerate}
            disabled={p.progress.running}
          >
            {p.progress.running ? "生成中…" : "生成授信辅助"}
          </button>
          <div className="credit-hero__progress" aria-hidden={!p.progress.step && !p.progress.running}>
            <div className="credit-hero__progress-label">{p.progress.label}</div>
            <div className="credit-hero__progress-track">
              <div
                className="credit-hero__progress-fill"
                style={{ width: `${p.progress.pct}%` } as CSSProperties}
              />
            </div>
          </div>
          <div className="credit-hero__red-summary">
            红线 · {p.redLines.length - redFail - redWarn}/{p.redLines.length} 过
            {redWarn > 0 ? <span className="credit-hero__red-warn"> · {redWarn} 警</span> : null}
            {redFail > 0 ? <span className="credit-hero__red-fail"> · {redFail} 阻</span> : null}
          </div>
        </div>
      </div>
    </header>
  );
}

function ScoreRing({
  score,
  decision,
}: {
  score: number;
  decision: "approved" | "approved-cut" | "rejected" | "pending";
}) {
  const tone =
    decision === "approved" || score >= 85
      ? "good"
      : decision === "rejected" || score < 60
      ? "bad"
      : "warn";
  const circ = 2 * Math.PI * 42; // r=42
  const dash = (score / 100) * circ;
  return (
    <div className="credit-hero__ring" data-tone={tone}>
      <svg width="120" height="120" viewBox="0 0 100 100" aria-hidden>
        <circle cx="50" cy="50" r="42" className="credit-hero__ring-track" />
        <circle
          cx="50"
          cy="50"
          r="42"
          className="credit-hero__ring-fill"
          strokeDasharray={`${dash} ${circ}`}
          transform="rotate(-90 50 50)"
        />
      </svg>
      <div className="credit-hero__ring-val">
        <span className="credit-hero__ring-num">{score}</span>
        <span className="credit-hero__ring-unit">综合</span>
      </div>
    </div>
  );
}

/* ─────────── LEFT · 案件概要（压缩） ─────────── */

function QueryPanel({ q }: { q: CreditQuery }) {
  const kv: Array<[string, string]> = [
    ["客户", q.customer],
    ["产品", q.product],
    ["申请", `${q.applyAmount} / ${q.applyTenor}`],
    ["用途", q.purpose],
    ["行业", q.industry],
  ];
  return (
    <div className="rpt-panel cr-q">
      <PanelPinHandle
        id={`credit:query:${q.id}`}
        title={`案件概要 · ${q.customer}`}
        subtitle={`${q.product} · ${q.applyAmount}`}
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb={`${q.purpose} · ${q.industry}`}
      />
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">案件概要</div>
        <div className="rpt-panel__updated">更新 {q.updated}</div>
      </div>
      <div className="rpt-panel__body">
        <dl className="cr-q__dl">
          {kv.map(([k, v]) => (
            <div key={k} className="cr-q__row">
              <dt>{k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}

/* ─────────── LEFT · 资料上传与解析（新） ─────────── */

function MaterialsPanel({ data }: { data: MaterialsPanelData }) {
  return (
    <div className="rpt-panel cr-mat">
      <PanelPinHandle
        id={`credit:materials:${data.completeness}`}
        title={`资料完整度 ${data.completeness}%`}
        subtitle={data.missing || "无缺失"}
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb={`${data.files.length} 份资料 · ${data.missing || "全部到位"}`}
      />
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">资料与解析</div>
        <div className="rpt-panel__counter">{data.completeness}%</div>
      </div>
      <div className="rpt-panel__body">
        <div className="cr-mat__summary">
          <div className="cr-mat__completeness" data-level={data.completeness >= 85 ? "good" : data.completeness >= 70 ? "warn" : "bad"}>
            <span className="cr-mat__num">{data.completeness}</span>
            <span className="cr-mat__pct">%</span>
          </div>
          <div className="cr-mat__meta">
            <div className="cr-mat__meta-lbl">完整度</div>
            <div className="cr-mat__meta-missing">{data.missing || "全部到位"}</div>
          </div>
        </div>
        <label className="cr-mat__drop">
          <span className="cr-mat__drop-ic" aria-hidden>
            +
          </span>
          <span className="cr-mat__drop-txt">上传客户资料</span>
          <span className="cr-mat__drop-hint">财报 · 流水 · 执照 · 担保 · 征信</span>
          <input type="file" multiple hidden aria-label="上传客户资料" />
        </label>
        <ul className="cr-mat__list">
          {data.files.map((f) => (
            <li key={f.id} className="cr-mat__item" data-status={f.status}>
              <span className="cr-mat__ic">{f.icon}</span>
              <div className="cr-mat__body">
                <div className="cr-mat__name">{f.name}</div>
                <div className="cr-mat__note">{f.note}</div>
              </div>
              <span className="cr-mat__chip" data-status={f.status}>
                {f.status === "done" ? "完成" : f.status === "warn" ? "复核" : "待交"}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/* ─────────── LEFT · 资料库接口（新） ─────────── */

function DataSourcesPanel({ data }: { data: DataSourcesPanel }) {
  return (
    <div className="rpt-panel cr-src">
      <PanelPinHandle
        id={`credit:sources`}
        title={`资料库接口 · ${data.summary}`}
        subtitle={`更新 ${data.updated}`}
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb={`${data.sources.length} 个数据源 · ${data.sources.filter((s) => s.status === "online").length} 在线`}
      />
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">资料库接口</div>
        <div className="rpt-panel__counter">{data.summary}</div>
      </div>
      <div className="rpt-panel__body">
        <div className="cr-src__updated">更新 {data.updated}</div>
        <ul className="cr-src__list">
          {data.sources.map((s) => (
            <li key={s.id} className="cr-src__item" data-status={s.status}>
              <span className="cr-src__dot" aria-hidden />
              <div className="cr-src__body">
                <div className="cr-src__name">{s.name}</div>
                <div className="cr-src__desc">{s.desc}</div>
              </div>
              <span className="cr-src__chip" data-status={s.status}>
                {s.status === "online" ? "在线" : s.status === "warn" ? "预警" : "离线"}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/* ─────────── LEFT · 近期（压缩） ─────────── */

function RecentPanel({ recent }: { recent: CreditRecentSession[] }) {
  return (
    <div className="rpt-panel cr-rc">
      <PanelPinHandle
        id={`credit:recent`}
        title={`近期 · ${recent.length} 条`}
        subtitle="跨三板块"
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb={`最近 ${recent[0]?.customer ?? "—"} ${recent[0]?.decision ?? ""}`}
      />
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">近期</div>
        <div className="rpt-panel__counter">{recent.length}</div>
      </div>
      <div className="rpt-panel__body">
        <ul className="cr-rc__list">
          {recent.slice(0, 5).map((r) => (
            <li key={r.id} className="cr-rc__item">
              <div className="cr-rc__head">
                <div className="cr-rc__name">{r.customer}</div>
                <span className="cr-rc__chip" data-decision={r.decision}>
                  {DECISION_LABEL[r.decision]}
                </span>
              </div>
              <div className="cr-rc__meta">
                <span>{r.product}</span>
                <span>{r.amount}</span>
                <span className="cr-rc__time">{r.updated}</span>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/* ─────────── MID · 对话面板 ─────────── */

function ConversationPanel({ msgs }: { msgs: ConversationMessage[] }) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [msgs.length]);

  return (
    <div className="rpt-panel rpt-panel--conv rpt-panel--conv-docked">
      <PanelPinHandle
        id={`credit:conversation`}
        title="审贷对话流"
        subtitle="BENCH · 推理"
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb={`${msgs.length} 条消息 · 最后 ${msgs[msgs.length - 1]?.at ?? ""}`}
      />
      <div className="rpt-conv" ref={scrollRef}>
        {msgs.map((m) => (
          <ConversationMsg key={m.id} m={m} />
        ))}
      </div>
      <CreditComposer />
    </div>
  );
}

function ConversationMsg({ m }: { m: ConversationMessage }) {
  const short = truncate(m.content, 42);
  const speaker = speakerOf(m);

  if (m.kind === "system-event") {
    return (
      <div className="rpt-msg rpt-msg--sys">
        <MessagePinHandle
          id={`credit:msg:${m.id}`}
          title={short}
          subtitle={`${speaker} · ${m.at}`}
          accentVar={AGENT_ACCENT}
          agentKey={AGENT_KEY}
          href={AGENT_HREF}
          fullText={m.content}
        />
        <span className="rpt-msg__dot" aria-hidden>
          ◈
        </span>
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
          id={`credit:msg:${m.id}`}
          title={short}
          subtitle={`${speaker} · ${m.at}`}
          accentVar={AGENT_ACCENT}
          agentKey={AGENT_KEY}
          href={AGENT_HREF}
          fullText={m.content}
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
        <MessagePinHandle
          id={`credit:msg:${m.id}`}
          title={short}
          subtitle={`BENCH · ${m.at}`}
          accentVar={AGENT_ACCENT}
          agentKey={AGENT_KEY}
          href={AGENT_HREF}
          fullText={m.content}
        />
        <div className="rpt-msg__head">
          <span className="rpt-msg__who">BENCH · 推理</span>
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
  const who = m.kind === "ai-question" ? "BENCH · 问" : "BENCH";
  return (
    <div className="rpt-msg rpt-msg--ai" data-q={m.kind === "ai-question" ? "yes" : "no"}>
      <MessagePinHandle
        id={`credit:msg:${m.id}`}
        title={short}
        subtitle={`BENCH · ${m.at}`}
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        fullText={m.content}
      />
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

function speakerOf(m: ConversationMessage): string {
  if (m.kind === "user-reply") return "我";
  if (m.kind === "user-command") return "指令";
  if (m.kind === "system-event") return "系统";
  if (m.kind === "ai-thinking") return "BENCH 推理";
  if (m.kind === "ai-question") return "BENCH 问";
  return "BENCH";
}

function truncate(s: string, n: number): string {
  const flat = s.replace(/\s+/g, " ").trim();
  return flat.length > n ? `${flat.slice(0, n - 1)}…` : flat;
}

function CreditComposer() {
  const [value, setValue] = useState("");
  const hints = ["深看财务", "补担保方案", "对比案例 C-1", "触发放款条件", "生成决议草稿"];
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
        placeholder="对 BENCH 提问 / 给指令：深看维度、对比案例、调额度、下决议…"
        rows={3}
      />
      <div className="rpt-composer__foot">
        <span className="rpt-composer__hint-txt">Enter 发 · Shift+Enter 换行 · /lock 锁结论</span>
        <button type="button" className="rpt-composer__send" disabled={!value.trim()}>
          发送
        </button>
      </div>
    </div>
  );
}

/* ─────────── RIGHT · OutputPanel 3 tabs ─────────── */

function OutputPanel(p: {
  tab: OutputTab;
  onTabChange: (t: OutputTab) => void;
  radar: CreditRadarDim[];
  overall: number;
  limit: LimitSuggestion;
  redLines: RedLine[];
  cases: CaseRecall[];
}) {
  return (
    <div className="rpt-panel cr-out">
      <PanelPinHandle
        id={`credit:output:${p.tab}`}
        title={`决策看板 · ${p.tab === "radar" ? "四维雷达" : p.tab === "limit" ? "额度建议" : "相似案例"}`}
        subtitle={`综合 ${p.overall}`}
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb={`${p.radar.length} 维 · ${p.redLines.length} 条红线 · ${p.cases.length} 个案例`}
      />
      <div className="rpt-panel__head cr-out__head">
        <div className="rpt-panel__eyebrow">决策看板</div>
        <div className="cr-out__tabs" role="tablist">
          <TabBtn active={p.tab === "radar"} onClick={() => p.onTabChange("radar")}>
            四维
          </TabBtn>
          <TabBtn active={p.tab === "limit"} onClick={() => p.onTabChange("limit")}>
            额度
          </TabBtn>
          <TabBtn active={p.tab === "cases"} onClick={() => p.onTabChange("cases")}>
            案例
          </TabBtn>
        </div>
      </div>
      <div className="rpt-panel__body cr-out__body">
        {p.tab === "radar" ? <RadarView radar={p.radar} overall={p.overall} /> : null}
        {p.tab === "limit" ? <LimitView limit={p.limit} redLines={p.redLines} /> : null}
        {p.tab === "cases" ? <CasesView cases={p.cases} /> : null}
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
    <button
      type="button"
      className="cr-out__tab"
      data-active={active ? "yes" : "no"}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function RadarView({ radar, overall }: { radar: CreditRadarDim[]; overall: number }) {
  const data = radar.map((d) => ({ dim: d.label, score: d.score }));
  return (
    <div className="cr-rd">
      <div className="cr-rd__kpi">
        <div className="cr-rd__score">
          <span className="cr-rd__score-num">{overall}</span>
          <span className="cr-rd__score-unit">综合分</span>
        </div>
        <div className="cr-rd__score-note">100 分制 · 加权合成（财 30/经 30/合 25/担 15）</div>
      </div>
      <div className="cr-rd__chart">
        <ResponsiveContainer width="100%" height={240}>
          <RadarChart data={data} outerRadius="72%">
            <PolarGrid stroke="color-mix(in srgb, var(--ink) 15%, transparent)" />
            <PolarAngleAxis
              dataKey="dim"
              tick={{ fill: "var(--ink)", fontSize: 12, fontFamily: "var(--cjk)" }}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 100]}
              tick={{ fill: "color-mix(in srgb, var(--ink) 55%, transparent)", fontSize: 10 }}
              stroke="color-mix(in srgb, var(--ink) 20%, transparent)"
            />
            <Radar
              name="评分"
              dataKey="score"
              stroke="var(--agent)"
              fill="var(--agent)"
              fillOpacity={0.2}
              strokeWidth={1.8}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <ul className="cr-rd__list">
        {radar.map((d) => (
          <li key={d.key} className="cr-rd__item">
            <div className="cr-rd__head">
              <span className="cr-rd__lbl">{d.label}</span>
              <span className="cr-rd__sc">{d.score}</span>
              <span className="cr-rd__w">权 {Math.round(d.weight * 100)}%</span>
            </div>
            <div className="cr-rd__bar">
              <div
                className="cr-rd__bar-fill"
                style={{ width: `${d.score}%` } as CSSProperties}
              />
            </div>
            <div className="cr-rd__note">{d.note}</div>
            <div className="cr-rd__tags">
              {d.tags.map((t) => (
                <span key={t} className="cr-rd__tag">
                  {t}
                </span>
              ))}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function LimitView({ limit, redLines }: { limit: LimitSuggestion; redLines: RedLine[] }) {
  const amountPct = ((limit.suggested - limit.floor) / (limit.ceiling - limit.floor)) * 100;
  const tenorPct =
    ((limit.tenorMonths - limit.tenorRange[0]) /
      (limit.tenorRange[1] - limit.tenorRange[0])) *
    100;
  const ratePct =
    ((limit.rateBps - limit.rateRange[0]) / (limit.rateRange[1] - limit.rateRange[0])) * 100;

  return (
    <div className="cr-lm">
      <div className="cr-lm__summary">
        <div className="cr-lm__kpi">
          <span className="cr-lm__kpi-num">{limit.suggested}</span>
          <span className="cr-lm__kpi-unit">万</span>
        </div>
        <div className="cr-lm__kpi-sub">
          建议额度 · 申请 {limit.applied} 万 · Δ {limit.suggested - limit.applied} 万
        </div>
      </div>

      <Gauge
        label="额度"
        unit="万"
        min={limit.floor}
        max={limit.ceiling}
        value={limit.suggested}
        pct={amountPct}
        applied={limit.applied}
      />
      <Gauge
        label="期限"
        unit="月"
        min={limit.tenorRange[0]}
        max={limit.tenorRange[1]}
        value={limit.tenorMonths}
        pct={tenorPct}
      />
      <Gauge
        label="利率"
        unit="bps"
        min={limit.rateRange[0]}
        max={limit.rateRange[1]}
        value={limit.rateBps}
        pct={ratePct}
        prefix="LPR+"
      />

      <div className="cr-lm__rationale">
        <div className="cr-lm__section-ttl">建议理由</div>
        <ul>
          {limit.rationale.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      </div>

      <div className="cr-lm__redlines">
        <div className="cr-lm__section-ttl">红线 · {redLines.length} 项</div>
        <ul className="cr-lm__rl-list">
          {redLines.map((r) => (
            <li key={r.id} className="cr-lm__rl" data-status={r.status}>
              <span className="cr-lm__rl-mark" aria-hidden>
                {r.status === "pass" ? "✓" : r.status === "warn" ? "!" : "✕"}
              </span>
              <div className="cr-lm__rl-body">
                <div className="cr-lm__rl-rule">{r.rule}</div>
                <div className="cr-lm__rl-detail">{r.detail}</div>
                <div className="cr-lm__rl-cite">出处 · {r.citation}</div>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function Gauge(p: {
  label: string;
  unit: string;
  min: number;
  max: number;
  value: number;
  pct: number;
  applied?: number;
  prefix?: string;
}) {
  const appliedPct =
    p.applied !== undefined ? ((p.applied - p.min) / (p.max - p.min)) * 100 : null;
  return (
    <div className="cr-lm__g">
      <div className="cr-lm__g-head">
        <span className="cr-lm__g-lbl">{p.label}</span>
        <span className="cr-lm__g-val">
          {p.prefix ?? ""}
          {p.value} {p.unit}
        </span>
      </div>
      <div className="cr-lm__g-track">
        <div
          className="cr-lm__g-fill"
          style={{ width: `${p.pct}%` } as CSSProperties}
        />
        <div
          className="cr-lm__g-dot"
          style={{ left: `calc(${p.pct}% - 6px)` } as CSSProperties}
        />
        {appliedPct !== null ? (
          <div
            className="cr-lm__g-applied"
            title={`申请值 ${p.applied}`}
            style={{ left: `${appliedPct}%` } as CSSProperties}
          />
        ) : null}
      </div>
      <div className="cr-lm__g-scale">
        <span>
          {p.prefix ?? ""}
          {p.min}
        </span>
        <span>
          {p.prefix ?? ""}
          {p.max}
        </span>
      </div>
    </div>
  );
}

function CasesView({ cases }: { cases: CaseRecall[] }) {
  return (
    <div className="cr-cs">
      <div className="cr-cs__ttl">相似案例召回 · {cases.length} 条（相似度 ≥ 0.75）</div>
      <ul className="cr-cs__list">
        {cases.map((c) => (
          <li key={c.id} className="cr-cs__item" data-decision={c.decision}>
            <div className="cr-cs__head">
              <div className="cr-cs__name">{c.name}</div>
              <span className="cr-cs__chip">{DECISION_LABEL[c.decision]}</span>
            </div>
            <div className="cr-cs__meta">
              <span className="cr-cs__sim">相似度 {(c.similarity * 100).toFixed(0)}%</span>
              <span className="cr-cs__sep">·</span>
              <span>申请 {c.amount}</span>
            </div>
            <div className="cr-cs__note">{c.note}</div>
            <div className="cr-cs__tags">
              {c.tags.map((t) => (
                <span key={t} className="cr-cs__tag">
                  {t}
                </span>
              ))}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ─────────── BOTTOM · 证据链 | 生成流程 ─────────── */

function BottomBar(p: {
  evidences: EvidencesPanel;
  pipeline: CreditPipelineStep[];
  generateSteps: GenerateStep[];
  progress: { running: boolean; step: number; pct: number; label: string };
}) {
  return (
    <div className="credit-bottom">
      <EvidenceLane evidences={p.evidences} />
      <PipelineLane
        pipeline={p.pipeline}
        generateSteps={p.generateSteps}
        progress={p.progress}
      />
    </div>
  );
}

function EvidenceLane({ evidences }: { evidences: EvidencesPanel }) {
  const counts = {
    positive: evidences.positive.length,
    warnings: evidences.warnings.length,
    missing: evidences.missing.length,
  };
  const total = counts.positive + counts.warnings + counts.missing;
  return (
    <section className="rpt-panel credit-evi">
      <PanelPinHandle
        id={`credit:evidence`}
        title={`证据链 · ${total} 条`}
        subtitle={`正 ${counts.positive} · 警 ${counts.warnings} · 缺 ${counts.missing}`}
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb="评分细则回指到资料/规则/外部接口"
      />
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">评分细则 · 证据链</div>
        <div className="rpt-panel__counter">{total} 条</div>
      </div>
      <div className="rpt-panel__body credit-evi__body">
        <EvidenceGroup label="正向" items={evidences.positive} tone="positive" />
        <EvidenceGroup label="提醒" items={evidences.warnings} tone="warning" />
        <EvidenceGroup label="缺失" items={evidences.missing} tone="missing" />
      </div>
    </section>
  );
}

function EvidenceGroup({
  label,
  items,
  tone,
}: {
  label: string;
  items: EvidenceItem[];
  tone: "positive" | "warning" | "missing";
}) {
  return (
    <div className="credit-evi__group" data-tone={tone}>
      <div className="credit-evi__group-head">
        <span className="credit-evi__group-lbl">{label}</span>
        <span className="credit-evi__group-n">{items.length}</span>
      </div>
      {items.length === 0 ? (
        <div className="credit-evi__empty">— 无</div>
      ) : (
        <ul className="credit-evi__list">
          {items.map((ev) => (
            <li key={ev.id} className="credit-evi__item">
              <span className="credit-evi__ic" aria-hidden>
                {ev.icon}
              </span>
              <div className="credit-evi__main">
                <div className="credit-evi__title">{ev.title}</div>
                <div className="credit-evi__detail">{ev.detail}</div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function PipelineLane({
  pipeline,
  generateSteps,
  progress,
}: {
  pipeline: CreditPipelineStep[];
  generateSteps: GenerateStep[];
  progress: { running: boolean; step: number; pct: number; label: string };
}) {
  return (
    <section className="rpt-panel credit-pipe">
      <PanelPinHandle
        id={`credit:pipeline`}
        title={`生成流程 · ${pipeline.filter((s) => s.status === "done").length}/${pipeline.length}`}
        subtitle="资料 → 评分 → 红线 → 案例 → 决议"
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb={progress.label}
      />
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">生成流程状态</div>
        <div className="rpt-panel__counter">
          {pipeline.filter((s) => s.status === "done").length}/{pipeline.length}
        </div>
      </div>
      <div className="rpt-panel__body credit-pipe__body">
        <div className="credit-pipe__live">
          <div className="credit-pipe__live-label">{progress.label}</div>
          <div className="credit-pipe__live-track">
            <div
              className="credit-pipe__live-fill"
              style={{ width: `${progress.pct}%` } as CSSProperties}
            />
          </div>
          <div className="credit-pipe__live-steps">
            {generateSteps.map((s, i) => (
              <span
                key={s.label}
                className="credit-pipe__live-chip"
                data-active={progress.step >= i ? "yes" : "no"}
              >
                {String(i + 1).padStart(2, "0")} {s.label.replace(/中…$|中$/g, "")}
              </span>
            ))}
          </div>
        </div>
        <ol className="credit-pipe__list">
          {pipeline.map((s, i) => (
            <li key={s.id} className="credit-pipe__item" data-status={s.status}>
              <span className="credit-pipe__idx">{String(i + 1).padStart(2, "0")}</span>
              <div className="credit-pipe__body-txt">
                <div className="credit-pipe__lbl">{s.label}</div>
                {s.note ? <div className="credit-pipe__note">{s.note}</div> : null}
              </div>
              <span className="credit-pipe__mark" aria-hidden>
                {s.status === "done" ? "✓" : s.status === "active" ? "●" : "○"}
              </span>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

/* ─────────── CreditEmptyState · W-CF-A2 · 2026-04-28 ───────────
   empty-state-design-protocol v1.0 落地:
     §2.1 场景 Hero (一句话 problem statement)
     §2.2 主 CTA 3 入口分级 (primary 显著 / secondary 次要 / tertiary 灰色 (示例))
     §2.3 Panel 区空骨架 (灰底 placeholder · 不显示模拟数字)
     §2.4 状态透明 status pill
     §2.5 demo 显式标 (示例) tag
   §3 状态机 started default false · 用户主动 trigger 才 setStarted(true)
   §6 Credit 改造: 主 CTA = 选材料 (来自 Agent6 handoff) + 起决策
*/

function CreditEmptyState(p: {
  mode: CreditMode;
  onModeChange: (m: CreditMode) => void;
  onPrimary: () => void;       // 起决策 (真接 backend SSE)
  onSecondary: () => void;     // 起决策 (mock=true · 无 LLM key 演示)
  onTertiary: () => void;      // 选历史 (示例) session
  decisionRunning: boolean;
  decisionError: string | null;
}) {
  const stageTab = MODE_TO_STAGE_TAB[p.mode];
  const stageDesc = STAGE_TAB_DESCRIPTION[p.mode];
  return (
    <div className="credit-empty" data-testid="credit-empty-skeleton">
      {/* Stage tabs · 与 backend stage_tab 命名对齐 */}
      <div
        className="credit-empty__tabs"
        role="tablist"
        aria-label="授信板块切换"
      >
        <span className="credit-empty__tabs-lbl">板块</span>
        {(["corp", "small", "retail"] as CreditMode[]).map((k) => (
          <button
            key={k}
            type="button"
            role="tab"
            aria-selected={p.mode === k}
            data-testid={`credit-stage-tab-${MODE_TO_STAGE_TAB[k]}`}
            className="credit-empty__tab"
            data-active={p.mode === k ? "yes" : "no"}
            onClick={() => p.onModeChange(k)}
          >
            {CREDIT_MODE_LABEL[k]}
          </button>
        ))}
      </div>

      {/* §2.1 Hero · 一句话 problem statement */}
      <header className="credit-empty__hero">
        <div className="credit-empty__hero-eyebrow">AGENT · 03 · BENCH · 授信决策辅助</div>
        <h1 className="credit-empty__hero-title">
          授信决策辅助 · 4 维评分 + 红线 + 案例 + 决策建议书
        </h1>
        <p className="credit-empty__hero-sub">
          当前板块: <strong>{CREDIT_MODE_LABEL[p.mode]}</strong> · {stageDesc}
        </p>
      </header>

      {/* §2.2 主 CTA · 3 入口分级 */}
      <section className="credit-empty__cta-row" aria-label="3 CTA 分级">
        <button
          type="button"
          className="credit-empty__cta credit-empty__cta--primary"
          data-testid="credit-decision-cta"
          data-cta="primary"
          onClick={p.onPrimary}
          disabled={p.decisionRunning}
        >
          <span className="credit-empty__cta-rank">主操作</span>
          <span className="credit-empty__cta-title">
            {p.decisionRunning ? "决策中…" : "选材料 + 起决策"}
          </span>
          <span className="credit-empty__cta-sub">
            从 Agent6 handoff 拉报告 · 真接 LLM SSE
          </span>
        </button>
        <button
          type="button"
          className="credit-empty__cta credit-empty__cta--secondary"
          data-testid="credit-decision-cta-secondary"
          data-cta="secondary"
          onClick={p.onSecondary}
          disabled={p.decisionRunning}
        >
          <span className="credit-empty__cta-rank">次操作</span>
          <span className="credit-empty__cta-title">演示模式起决策</span>
          <span className="credit-empty__cta-sub">
            无 LLM key 也能看流程 · backend mock=true
          </span>
        </button>
        <button
          type="button"
          className="credit-empty__cta credit-empty__cta--tertiary"
          data-testid="credit-history-tertiary"
          data-cta="tertiary"
          onClick={p.onTertiary}
        >
          <span className="credit-empty__cta-rank credit-empty__cta-rank--demo">
            历史 (示例)
          </span>
          <span className="credit-empty__cta-title">看示例案例</span>
          <span className="credit-empty__cta-sub">
            {CREDIT_MODE_LABEL[p.mode]} · 培训演示用 · 切真实输入随时返回
          </span>
        </button>
      </section>

      {/* §2.3 Panel 空骨架 · 不显示模拟数字 · 仅说明文字 */}
      <section
        className="credit-empty__skeleton"
        aria-label="授信决策面板 · 空骨架"
        data-testid="credit-empty-skeleton-panels"
      >
        <div className="credit-empty__skel-row">
          <div className="credit-empty__skel-card" data-skel="radar">
            <div className="credit-empty__skel-lbl">4 维评分雷达</div>
            <div className="credit-empty__skel-hint">起决策后此处显示综合分 + 雷达图</div>
          </div>
          <div className="credit-empty__skel-card" data-skel="redlines">
            <div className="credit-empty__skel-lbl" data-testid="credit-redlines-list">
              红线检查
            </div>
            <div className="credit-empty__skel-hint">命中红线显示在这里 (硬/软分级)</div>
          </div>
          <div className="credit-empty__skel-card" data-skel="cases">
            <div className="credit-empty__skel-lbl">相似案例 Top5</div>
            <div className="credit-empty__skel-hint">案例召回结果显示在这里</div>
          </div>
        </div>
        <div className="credit-empty__skel-row">
          <div className="credit-empty__skel-card credit-empty__skel-card--wide" data-skel="advice">
            <div className="credit-empty__skel-lbl">决策建议书 · LLM 自然语言</div>
            <div className="credit-empty__skel-hint">
              起决策完成后显示决策结论 / 额度 / 期限 / 利率 / 红线解释 +{" "}
              <button
                type="button"
                className="credit-empty__skel-export"
                data-testid="credit-export-docx-btn"
                disabled
                aria-disabled
              >
                导出 .docx (待决策完成启用)
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* §2.4 status pill · 服务健康 + LLM 预算 + 历史 hint */}
      <footer
        className="credit-empty__status"
        data-testid="credit-empty-status-pill"
        aria-label="状态透明"
      >
        <span className="credit-empty__status-item" data-tone="ok">
          ◉ 服务正常
        </span>
        <span className="credit-empty__status-item">
          板块: <code>{stageTab}</code>
        </span>
        <span className="credit-empty__status-item credit-empty__status-item--demo">
          {p.decisionRunning ? "授信流式中…" : "等待主操作"}
        </span>
        {p.decisionError ? (
          <span
            className="credit-empty__status-item credit-empty__status-item--err"
            role="alert"
          >
            ⚠ {p.decisionError}
          </span>
        ) : null}
      </footer>
    </div>
  );
}

/* ─────────── CreditDecisionAdvicePanel · W-CF-A2 · 2026-04-28 ───────────
   决策完成 (live SSE advising_done event) 后渲染 LLM 决策建议 + 红线 +
   Word 导出 button. decision_id 命中 → POST /api/credit/export_docx 下载 .docx.
   liveAdvice=null 时不渲 (避免与 mock data band 重叠). */

function CreditDecisionAdvicePanel(p: {
  liveAdvice: Record<string, unknown> | null;
  decisionId: string | null;
  decisionRunning: boolean;
  decisionError: string | null;
  stageTab: "corporate" | "small_business" | "retail";
}) {
  if (!p.liveAdvice && !p.decisionRunning && !p.decisionError) return null;

  const advice = (p.liveAdvice ?? {}) as Record<string, unknown>;
  const decision = String(advice.decision ?? "");
  const composite = advice.composite_score;
  const grade = String(advice.risk_grade ?? "");
  const amount = advice.approved_amount;
  const term = advice.approved_term_months;
  const rate = advice.interest_rate;
  const benchmark = String(advice.rate_benchmark ?? "");
  const reason = String(advice.decision_reason ?? "");
  const conditions = Array.isArray(advice.conditions) ? (advice.conditions as string[]) : [];

  async function downloadDocx() {
    if (!p.decisionId && !p.liveAdvice) return;
    const apiBase =
      (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE) || "";
    const body = p.decisionId
      ? { decision_id: p.decisionId }
      : { advice: { ...advice, segment: "corporate", subject_name: String(advice.subject_name ?? "授信主体") } };
    try {
      const res = await fetch(`${apiBase}/api/credit/export_docx`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `授信决策建议书_${p.stageTab}_${Date.now()}.docx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("[credit] export_docx failed:", err);
    }
  }

  return (
    <section
      className="rpt-panel credit-advice-live"
      aria-label="决策建议 · LLM 实时生成"
      data-testid="credit-decision-advice-live"
    >
      <header className="credit-advice-live__head">
        <span className="credit-advice-live__eyebrow">
          DECISION · {p.stageTab.toUpperCase()}
          {p.decisionRunning ? " · 流式中…" : ""}
        </span>
        {p.decisionError ? (
          <span className="credit-advice-live__err" role="alert">
            ⚠ {p.decisionError}
          </span>
        ) : null}
      </header>
      {p.liveAdvice ? (
        <div className="credit-advice-live__body">
          <div className="credit-advice-live__verdict">
            <span className="credit-advice-live__verdict-lbl">{decision || "—"}</span>
            {grade ? (
              <span className="credit-advice-live__verdict-grade">{grade}</span>
            ) : null}
            {typeof composite === "number" ? (
              <span className="credit-advice-live__verdict-score">{composite} 分</span>
            ) : null}
          </div>
          <dl className="credit-advice-live__meta">
            {typeof amount === "number" ? (
              <div>
                <dt>建议额度</dt>
                <dd>{amount} 万</dd>
              </div>
            ) : null}
            {typeof term === "number" ? (
              <div>
                <dt>建议期限</dt>
                <dd>{term} 个月</dd>
              </div>
            ) : null}
            {typeof rate === "number" ? (
              <div>
                <dt>利率</dt>
                <dd>
                  {(rate * 100).toFixed(2)}%
                  {benchmark ? <span className="bench"> ({benchmark})</span> : null}
                </dd>
              </div>
            ) : null}
          </dl>
          {reason ? (
            <p className="credit-advice-live__reason">{reason}</p>
          ) : null}
          {conditions.length > 0 ? (
            <div className="credit-advice-live__cond">
              <span className="lbl">附加条件</span>
              <ul>
                {conditions.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <button
            type="button"
            className="credit-advice-live__export"
            data-testid="credit-export-docx-btn"
            onClick={downloadDocx}
            disabled={!p.decisionId && !p.liveAdvice}
          >
            导出决策建议书 (.docx)
          </button>
        </div>
      ) : p.decisionRunning ? (
        <div className="credit-advice-live__loading">LLM 决策流式生成中…</div>
      ) : null}
    </section>
  );
}
