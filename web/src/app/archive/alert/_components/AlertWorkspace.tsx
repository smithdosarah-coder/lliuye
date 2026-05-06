"use client";

/**
 * /archive/alert · Agent 04 TOWER · 4-gate 贷中预警 workspace
 * (worker-A4-alert · 2026-04-29 · post A3-cherry-pick · A3 ChannelWorkspace 模板)
 *
 * 4 gate (workspace-state-protocol §2):
 *   started            user 主动 trigger 才显完整 workspace (W-CF2-A2)
 *   selectedSessionId  mock dropdown 切 session · default sess_baseline_100
 *   liveData           live mode SSE done 注入完整 AlertSession · 优先于 mock
 *   selectedClientId   TopCase 行 click → drill drawer · 走 /api/alert/drill/{client_id}
 *
 * sessionData derive: liveData ?? ALERT_MOCK_SESSIONS_MAP[selectedSessionId] ?? default
 * 5 panel 全消费 sessionData (无 const session 闭包 · workspace-state-protocol §7 step 3).
 *
 * Cat 4 done envelope: SSE done event 含 hit_list + totals + industry_distribution +
 *   signal_heatmap + reach_rate + top_cases + dispositions + kb_state · 通过
 *   normalizeAlertSession 注入 liveData.
 * Cat 5 grade (V2 fix · per A6 schema agent-handoff-schemas.md:421-422):
 *   - frontend canon = `tier` (red/yellow/green)         · 本文件 + agent-alert-sessions.ts
 *   - 后端 export INPUT 接受 risk_level/level/tier       · POST /api/alert/export_docx
 *   - HeatCell.level (热力 0..4) NOT touched             · 与 grade 同名不同义
 * Cat 11 banner: training-mode banner (selectedSessionId != default && !liveData) ·
 *   live-fail banner · scanError banner · export-error banner.
 *
 * 壳类: .v-archive--canon[data-agent="alert"] → --agent = var(--t-alert) 赭红
 */

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ChangeEvent,
} from "react";
import { useAuthStore } from "@/lib/store";
import { ModePill } from "@/components/shared/ModePill";
import { usePinDrop, type PinDropPayload } from "@/components/composer/use-pin-drop";
import {
  ALERT_GLOBAL_STATS,
  ALERT_MOCK_SESSIONS_LIST,
  ALERT_MOCK_SESSIONS_MAP,
  DEFAULT_SESSION_ID,
  type AlertPipelineStep,
  type AlertRecentSession,
  type AlertRule,
  type AlertSession,
  type ConversationMessage,
  type HeatCell,
  type IndustryDistribution,
  type KnowledgeSource,
  type ReachRate,
  type ScanQueueCase,
  type ScanRangeOption,
  type ScanSnapshot,
  type ScanStep,
  type SignalHeatBar,
  type TopCase,
} from "@/lib/mock/agent-alert-sessions";
import { ActionGate } from "@/components/shell/AuthGate";
import { PanelPinHandle } from "@/components/shell/PanelPinHandle";
import { MessagePinHandle } from "@/components/shell/MessagePinHandle";
import { ClaimText, EvidenceProvider } from "@/components/evidence";
import { ALERT_EVIDENCE } from "@/components/evidence/fixtures";
import {
  fetchDrill,
  LiveFailError,
  runAlertScan,
  type AlertDrillResponse,
} from "@/lib/api/alert";

/** 截断消息内容作 pin title。 */
function msgTitle(raw: string): string {
  const flat = raw.replace(/\s+/g, " ").trim();
  return flat.length > 42 ? `${flat.slice(0, 40)}…` : flat;
}

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

type RiskGrade = "red" | "yellow" | "green";

const GRADE_LABEL: Record<RiskGrade, string> = {
  red: "红档 · 立即处置",
  yellow: "黄档 · 重点观察",
  green: "绿档 · 常规跟踪",
};

/**
 * normalizeAlertSession · 把 backend SSE done envelope normalize 成前端 AlertSession.
 *
 * Cat 4 共形 (per docs/audit/A4-alert-draft.md §3 + shared.sse_envelope.make_done):
 *   evt.session_id / evt.totals / evt.hit_list / evt.industry_distribution /
 *   evt.signal_heatmap / evt.reach_rate / evt.top_cases / evt.dispositions /
 *   evt.kb_state / evt.summary / evt.data_source.
 *
 * 兜底 fallback chain: 字段缺 → 用 fallback session 同字段;
 * grade 命名兼容 (V2): backend 可能 risk_level / level / tier / grade 任一 → 统一收敛 frontend canon `tier`.
 *
 * V2 fix issue 2 · 5 panel 全 derive (不只 4 panel):
 *   - scanQueueCases: 从 hit_list.red + hit_list.yellow derive (绿不入队列)
 *   - scanSnapshotAfter.queue: 同上
 *   - scanSnapshotAfter.heat: 直接用 signal_heatmap
 *   - scanSnapshotAfter.summary: payload.summary
 *   - scanSnapshotAfter.warnCount: totals.red (主要红档)
 *   - scanSnapshotAfter.kbState: payload.kb_state
 *   - scanSnapshotAfter.tiers: derive from totals (3 tier count + caption)
 *   - scanSnapshotAfter.signals / sources: 保 fallback (无 backend 等价)
 *
 * 不让 LLM 算: 这里只是 schema 桥接 · 不做业务推断 · 不做幻觉补字段.
 */
function normalizeAlertSession(
  payload: Record<string, unknown>,
  fallback: AlertSession,
): AlertSession {
  const sid = String((payload.session_id as string) ?? fallback.id);
  const totalsIn = (payload.totals as { red?: number; yellow?: number; green?: number } | undefined) ?? null;
  const hitListRaw = (payload.hit_list as Record<string, unknown> | undefined) ?? null;
  const topCasesRaw =
    (payload.top_cases as Array<Record<string, unknown>> | undefined) ??
    (hitListRaw?.hits as Array<Record<string, unknown>> | undefined) ??
    null;

  const totals = totalsIn
    ? { red: totalsIn.red ?? 0, yellow: totalsIn.yellow ?? 0, green: totalsIn.green ?? 0 }
    : fallback.totals;

  // 行 → ScanQueueCase 共形 (issue #2 · 5 panel derive · V2)
  function rowToQueueCase(c: Record<string, unknown>, idx: number): ScanQueueCase | null {
    const t = normGrade(c.risk_level ?? c.tier ?? c.level ?? c.grade);
    if (t === "green") return null;
    const reasons = Array.isArray(c.reasons) ? (c.reasons as string[]) : [];
    const matched = Array.isArray(c.matched_rules) ? (c.matched_rules as string[]) : [];
    const reasonText = (reasons[0] || matched[0] || "命中规则").toString();
    const cid = String(c.client_id ?? c.id ?? c.hit_id ?? `cl-${idx}`);
    return {
      id: String(c.id ?? c.hit_id ?? `sq-${idx}`),
      client_id: cid,
      customer: String(c.customer ?? c.company_name ?? c.name ?? "—"),
      tier: t as "red" | "yellow",
      reason: reasonText,
      updated: String(c.lastUpdate ?? c.last_update ?? c.updated ?? "刚刚"),
    };
  }

  // 红+黄 hit_list 拼成 queue · backend hit_list shape: {red:[], yellow:[], green:[]}
  let queue: ScanQueueCase[] | null = null;
  if (hitListRaw && (Array.isArray(hitListRaw.red) || Array.isArray(hitListRaw.yellow))) {
    const red = (hitListRaw.red as Array<Record<string, unknown>> | undefined) ?? [];
    const yellow = (hitListRaw.yellow as Array<Record<string, unknown>> | undefined) ?? [];
    queue = [
      ...red.map((c, i) => rowToQueueCase(c, i)).filter((q): q is ScanQueueCase => q !== null),
      ...yellow.map((c, i) => rowToQueueCase(c, i + red.length)).filter((q): q is ScanQueueCase => q !== null),
    ];
  } else if (Array.isArray(topCasesRaw)) {
    queue = topCasesRaw
      .map((c, i) => rowToQueueCase(c, i))
      .filter((q): q is ScanQueueCase => q !== null);
  }

  const heat = Array.isArray(payload.signal_heatmap)
    ? (payload.signal_heatmap as SignalHeatBar[])
    : fallback.signalHeatmap;

  const distribution = Array.isArray(payload.industry_distribution)
    ? (payload.industry_distribution as IndustryDistribution[])
    : fallback.distribution;

  const reach = Array.isArray(payload.reach_rate)
    ? (payload.reach_rate as Array<Record<string, unknown>>).map((r) => ({
        tier: normGrade(r.risk_level ?? r.tier ?? r.level ?? r.grade),
        label: String(r.label ?? ""),
        total: Number(r.total ?? 0),
        reached: Number(r.reached ?? 0),
        reachedPct: Number(r.reachedPct ?? r.reached_pct ?? 0),
        channels: (r.channels as ReachRate["channels"]) ?? { phone: 0, sms: 0, visit: 0 },
      }))
    : fallback.reach;

  const topCases = Array.isArray(topCasesRaw)
    ? topCasesRaw.map((c, i) => ({
        id: String(c.id ?? c.hit_id ?? `hit-${i}`),
        client_id: String(c.client_id ?? c.id ?? c.hit_id ?? `cl-${i}`),
        customer: String(c.customer ?? c.company_name ?? c.name ?? "—"),
        amount: String(c.amount ?? c.credit_balance ?? "—"),
        tier: normGrade(c.risk_level ?? c.tier ?? c.level ?? c.grade),
        triggers: Array.isArray(c.triggers)
          ? (c.triggers as string[])
          : Array.isArray(c.matched_rules)
            ? (c.matched_rules as string[])
            : [],
        advice: String(c.advice ?? c.disposition ?? ""),
        lastUpdate: String(c.lastUpdate ?? c.last_update ?? c.updated ?? "刚刚"),
      }))
    : fallback.topCases;

  const summary = String((payload.summary as string) ?? fallback.scanSnapshotAfter.summary);
  const kbState = String((payload.kb_state as string) ?? fallback.scanSnapshotAfter.kbState);

  // V2 issue #2 · scanSnapshotAfter 全 derive (queue / heat / kbState / summary / warnCount / tiers)
  const snapshotAfter: ScanSnapshot = {
    summary,
    warnCount: totals.red,
    warnDelta:
      totals.red >= fallback.totals.red
        ? `较上期 +${totals.red - fallback.totals.red}`
        : `较上期 ${totals.red - fallback.totals.red}`,
    kbState,
    tiers: [
      { tier: "red", count: totals.red, caption: "强信号双路命中" },
      { tier: "yellow", count: totals.yellow, caption: "弱风险组合持续" },
      { tier: "green", count: totals.green, caption: "信号已缓和" },
    ],
    signals: fallback.scanSnapshotAfter.signals,
    queue: queue ?? fallback.scanSnapshotAfter.queue,
    heat,
    sources: fallback.scanSnapshotAfter.sources,
  };

  const norm: AlertSession = {
    ...fallback,
    id: sid,
    objective: String((payload.objective as string) ?? fallback.objective),
    stage: summary || fallback.stage,
    updated: "刚刚",
    totals,
    distribution,
    signalHeatmap: heat,
    reach,
    topCases,
    scanQueueCases: queue ?? fallback.scanQueueCases,
    scanSnapshotAfter: snapshotAfter,
  };
  return norm;
}

function normGrade(v: unknown): RiskGrade {
  const s = String(v ?? "").toLowerCase();
  if (s.includes("red") || s.includes("红")) return "red";
  if (s.includes("yellow") || s.includes("黄")) return "yellow";
  return "green";
}

export default function AlertWorkspace() {
  /* ───────── 4 gate state (workspace-state-protocol §2) ───────── */

  /** Gate 1 · started · W-CF2-A2 · empty-state default false */
  const [started, setStarted] = useState<boolean>(false);

  /** Gate 2 · selectedSessionId · mock dropdown 切 · default = baseline_100 */
  const [selectedSessionId, setSelectedSessionId] = useState<string>(DEFAULT_SESSION_ID);

  /** Gate 3 · liveData · SSE done envelope 注入完整 session · null = mock 优先 */
  const [liveData, setLiveData] = useState<AlertSession | null>(null);

  /** Gate 4 · selectedClientId · TopCase 行 click → drill drawer (用 client_id 与 backend 对齐) */
  const [selectedClientId, setSelectedClientId] = useState<string | null>(null);

  /* ───────── derived sessionData (5 panel 全消费这一个) ───────── */

  const sessionData: AlertSession =
    liveData ??
    ALERT_MOCK_SESSIONS_MAP[selectedSessionId] ??
    ALERT_MOCK_SESSIONS_MAP[DEFAULT_SESSION_ID];

  /* ───────── 视觉 phase / step / range / tab ───────── */

  const [tab, setTab] = useState<OutputTab>("dist");
  const [rangeId, setRangeId] = useState<string>(sessionData.scanRange[0]?.id ?? "");
  const [phase, setPhase] = useState<ScanPhase>("before");
  const [stepIdx, setStepIdx] = useState(0);
  const timerRef = useRef<number | null>(null);

  /* ───────── banner / error states ───────── */

  const [scanError, setScanError] = useState<string | null>(null);

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

  const [exportError, setExportError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  /* ───────── derived UI state ───────── */

  const after = sessionData.scanSnapshotAfter;
  const steps = sessionData.scanSteps;
  const currentSources = phase === "after" ? after.sources : sessionData.knowledgeBaseSources;
  const currentQueue = phase === "after" ? after.queue : sessionData.scanQueueCases;
  const currentHeat = phase === "after" ? after.heat : sessionData.signalHeatmap;
  const kbState =
    phase === "after"
      ? after.kbState
      : `${sessionData.knowledgeBaseSources.filter((s) => s.status === "online").length} 项联机中`;
  const currentSummary =
    phase === "after"
      ? after.summary
      : `${sessionData.stage} · 红 ${sessionData.totals.red} / 黄 ${sessionData.totals.yellow} / 绿 ${sessionData.totals.green} · ${sessionData.updated}`;

  /** training-mode banner · selectedSessionId != default + !liveData (live-fallback-banner-spec §2 规则 2) */
  const showTrainingModeBanner = liveData == null && selectedSessionId !== DEFAULT_SESSION_ID;

  /* ───────── effects ───────── */

  useEffect(() => {
    return () => {
      if (timerRef.current != null) window.clearInterval(timerRef.current);
    };
  }, []);

  /** ESC 关 drill drawer (workspace-state-protocol §7 step 6) */
  useEffect(() => {
    if (!selectedClientId) return;
    function onKey(ev: globalThis.KeyboardEvent) {
      if (ev.key === "Escape") setSelectedClientId(null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedClientId]);

  /* ───────── helpers ───────── */

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

  /** dropdown 切 session · reset 视觉 / live state · 关 drawer (A3 模板段 3) */
  const handleSelectSession = useCallback(
    (id: string) => {
      if (!ALERT_MOCK_SESSIONS_MAP[id]) return;
      setSelectedSessionId(id);
      setLiveData(null);
      setPhase("before");
      setStepIdx(0);
      setTab("dist");
      setSelectedClientId(null);
      const next = ALERT_MOCK_SESSIONS_MAP[id];
      setRangeId(next.scanRange[0]?.id ?? "");
      clearLiveFail();
      setScanError(null);
    },
    [],
  );

  /* ───────── scan workflow ───────── */

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

    /* 真接 POST /api/alert/scan SSE · streamSse helper · 失败 banner */
    void (async () => {
      try {
        const result = await runAlertScan(
          { scenarioKey: rangeId || sessionData.scenario_key || "", forceMock: false },
          (evt) => {
            // stage event 推进 stepIdx (per stage name 映射 · 后端 stage names: kb_load/external_scan/internal_match/cross/summary)
            const evtType = evt.data?.event ?? evt.type;
            if (evtType === "stage") {
              const stage = String(evt.data?.stage ?? "");
              const stageMap: Record<string, number> = {
                kb_load: 0,
                external_scan: 1,
                internal_match: 2,
                cross: 3,
                summary: 4,
              };
              if (stageMap[stage] != null) setStepIdx(stageMap[stage]);
            }
            if (evtType === "done") {
              const live = normalizeAlertSession(evt.data, sessionData);
              setLiveData(live);
            }
          },
        );
        if (result.sessionId) setScanSessionId(result.sessionId);
        setPhase("after");
      } catch (e) {
        recordLiveFail("alert scan", e, () => startScan());
        if (timerRef.current != null) {
          window.clearInterval(timerRef.current);
          timerRef.current = null;
        }
        setPhase("after");
      }
    })();
  }

  function triggerPrimaryScan() {
    setStarted(true);
    setScanError(null);
    startScan();
  }

  function triggerSecondaryScan() {
    setStarted(true);
    setScanError(null);
    startScan();
  }

  /** tertiary · 历史 (示例) · 直接走 mock dropdown 切到 manuf_policy_event (training mode) */
  function triggerTertiaryDemo() {
    setStarted(true);
    setScanError(null);
    handleSelectSession("sess_manuf_policy_event");
    if (timerRef.current != null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setStepIdx(steps.length - 1);
    setPhase("after");
  }

  function resetScan() {
    if (timerRef.current != null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setStepIdx(0);
    setPhase("before");
    setLiveData(null);
  }

  /* ───────── export docx ───────── */

  async function handleExportDocx() {
    if (exporting) return;
    setExporting(true);
    setExportError(null);
    try {
      const cases = sessionData.topCases.map((c) => ({
        customer: c.customer,
        risk_level: c.tier,
        triggers: c.triggers,
        amount: c.amount,
        advice: c.advice,
        last_update: c.lastUpdate,
      }));
      const totals =
        phase === "after"
          ? { red: after.warnCount ?? sessionData.totals.red, yellow: sessionData.totals.yellow, green: sessionData.totals.green }
          : sessionData.totals;
      const res = await fetch("/api/alert/export_docx", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionData.id ?? "",
          summary: currentSummary,
          cases,
          scan_range: sessionData.scanRange.find((r) => r.id === rangeId)?.label ?? "",
          stage: sessionData.stage,
          totals,
        }),
      });
      if (!res.ok) {
        const detail = await res.text().catch(() => "");
        throw new Error(`HTTP ${res.status} ${res.statusText} · ${detail.slice(0, 200)}`);
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `agent4_命中清单_${sessionData.id}.docx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setExportError(msg);
    } finally {
      setExporting(false);
    }
  }

  /* ───────── render: 4 gate root branch ───────── */

  return (
    <EvidenceProvider items={ALERT_EVIDENCE.items} unfilledFields={ALERT_EVIDENCE.unfilledFields}>
      <div
        className="rpt-workspace"
        data-view="archive-alert"
        data-alert-started={started ? "yes" : "no"}
        data-testid="alert-workspace"
        data-phase={phase}
        data-session-id={sessionData.id}
        data-live-mode={liveData ? "yes" : "no"}
        data-scan-session-id={scanSessionId}
      >
        {!started ? (
          <>
            {scanError ? (
              <div className="alert-live-fail-banner" role="alert" data-testid="alert-scan-error-banner">
                <span className="alert-live-fail-banner__icon" aria-hidden>⚠️</span>
                <span className="alert-live-fail-banner__text">
                  <b>客户扫描失败</b>
                  <span className="alert-live-fail-banner__detail">{scanError}</span>
                </span>
                <button type="button" className="alert-live-fail-banner__retry" onClick={triggerPrimaryScan}>
                  重试
                </button>
                <button
                  type="button"
                  className="alert-live-fail-banner__dismiss"
                  onClick={() => setScanError(null)}
                  aria-label="关闭横幅"
                >
                  ×
                </button>
              </div>
            ) : null}
            {/*
             * Phase B Sprint 3 sub-PR 2 V2-FIX (2026-05-05 · per Codex review critical 2):
             * AlertEmptyState 3 CTA (primary scan / secondary / demo) 全是 alert.invoke action ·
             * ActionGate row-level gate · RM alert.read-only → fallback 仅查看 banner ·
             * risk_manager / admin → 真 EmptyState · 可调 (per Q-052 #8 + ACCESS_V2)
             */}
            <ActionGate
              agent="alert"
              action="invoke"
              fallback={
                <div
                  className="alert-empty"
                  data-testid="alert-empty-readonly"
                  role="note"
                  aria-label="读取权限 · 不可发起扫描"
                >
                  <header className="alert-empty__hero">
                    <div className="alert-empty__hero-eyebrow">
                      AGENT · 04 · TOWER · 贷中预警引擎
                    </div>
                    <h1 className="alert-empty__hero-title">
                      贷中风险预警 · 当前角色仅 read 权限
                    </h1>
                    <p className="alert-empty__hero-sub">
                      您可查看历史扫描结果与预警榜单 · 不可发起新扫描 (POST /api/alert/scan)
                      · 联系风险经理 (陈凯) 触发批量扫描
                    </p>
                  </header>
                </div>
              }
            >
              <AlertEmptyState
                onPrimary={triggerPrimaryScan}
                onSecondary={triggerSecondaryScan}
                onTertiary={triggerTertiaryDemo}
                scanRunning={phase === "scanning"}
                scanError={scanError}
              />
            </ActionGate>
          </>
        ) : (
          <>
            {/* training-mode banner · live-fallback-banner-spec §2 规则 2 */}
            {showTrainingModeBanner ? (
              <div
                className="alert-demo-banner"
                role="note"
                aria-label="示例数据 · 培训演示模式"
                data-testid="alert-training-mode-banner"
              >
                <span className="alert-demo-banner__icon" aria-hidden>⚠</span>
                <span className="alert-demo-banner__text">
                  示例数据 (training mode) · 当前看的是「{sessionData.difficulty_label}」
                  · 切真实输入 → 点
                  <button
                    type="button"
                    className="alert-demo-banner__cta"
                    data-testid="alert-training-mode-banner-cta"
                    onClick={() => handleSelectSession(DEFAULT_SESSION_ID)}
                  >
                    回基线场景
                  </button>
                </span>
              </div>
            ) : null}

            {scanError && !liveFail ? (
              <div className="alert-live-fail-banner" role="alert" data-testid="alert-scan-error-banner">
                <span className="alert-live-fail-banner__icon" aria-hidden>⚠️</span>
                <span className="alert-live-fail-banner__text">
                  <b>客户扫描失败</b>
                  <span className="alert-live-fail-banner__detail">{scanError}</span>
                </span>
                <button type="button" className="alert-live-fail-banner__retry" onClick={triggerPrimaryScan}>
                  重试
                </button>
                <button
                  type="button"
                  className="alert-live-fail-banner__dismiss"
                  onClick={() => setScanError(null)}
                  aria-label="关闭横幅"
                >
                  ×
                </button>
              </div>
            ) : null}

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

            {exportError ? (
              <div
                data-testid="alert-export-error-banner"
                role="alert"
                style={{
                  margin: "16px 0",
                  padding: "12px 16px",
                  borderRadius: 12,
                  background: "rgba(192, 0, 0, 0.08)",
                  border: "1px solid rgba(192, 0, 0, 0.32)",
                  color: "var(--ink-strong, #2a1a16)",
                  fontSize: 14,
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  flexWrap: "wrap",
                }}
              >
                <span style={{ fontWeight: 600 }}>命中清单导出失败</span>
                <span style={{ opacity: 0.85, flex: 1 }}>
                  后端 <code>/api/alert/export_docx</code> 错误: {exportError}
                </span>
                <button
                  type="button"
                  data-testid="alert-export-error-retry"
                  onClick={handleExportDocx}
                  disabled={exporting}
                  style={{
                    padding: "6px 12px",
                    borderRadius: 8,
                    border: "1px solid rgba(192, 0, 0, 0.5)",
                    background: "transparent",
                    color: "var(--ink-strong, #2a1a16)",
                    fontSize: 13,
                    cursor: exporting ? "wait" : "pointer",
                  }}
                >
                  {exporting ? "重试中…" : "重试"}
                </button>
                <button
                  type="button"
                  data-testid="alert-export-error-dismiss"
                  onClick={() => setExportError(null)}
                  style={{
                    padding: "6px 10px",
                    borderRadius: 8,
                    border: "1px solid rgba(0,0,0,0.18)",
                    background: "transparent",
                    color: "var(--ink-strong, #2a1a16)",
                    fontSize: 13,
                    cursor: "pointer",
                  }}
                >
                  关闭
                </button>
              </div>
            ) : null}

            <SessionPickerBar
              sessions={ALERT_MOCK_SESSIONS_LIST}
              selectedId={selectedSessionId}
              onSelect={handleSelectSession}
              liveMode={liveData != null}
              currentLabel={sessionData.difficulty_label}
            />

            <HeroSection
              weeklyProcessed={ALERT_GLOBAL_STATS.weeklyProcessed}
              redRate={ALERT_GLOBAL_STATS.redRate}
              avgDuration={ALERT_GLOBAL_STATS.avgDuration}
              objective={sessionData.objective}
              stage={sessionData.stage}
              updated={sessionData.updated}
              totals={sessionData.totals}
              qcCounts={sessionData.qcCounts}
              phase={phase}
              summary={currentSummary}
              afterDelta={phase === "after" ? after.warnDelta : undefined}
              afterWarn={phase === "after" ? after.warnCount : undefined}
              kbState={kbState}
              onScan={startScan}
              onReset={resetScan}
              onExport={handleExportDocx}
              exporting={exporting}
              isLive={liveData != null}
            />

            <ScanProgressStrip phase={phase} steps={steps} stepIdx={stepIdx} />

            <TrafficLightWall
              totals={sessionData.totals}
              rules={sessionData.rules}
              reach={sessionData.reach}
              topCases={sessionData.topCases}
            />

            <ScanQueuePanel queue={currentQueue} phase={phase} />

            <div className="rpt-grid">
              <aside className="rpt-col rpt-col--left">
                <ScanRangePanel
                  options={sessionData.scanRange}
                  selected={rangeId}
                  onSelect={setRangeId}
                />
                <KnowledgeUploadPanel />
                <SourceListPanel sources={currentSources} />
                <RulesPanel rules={sessionData.rules} />
                <PipelinePanel steps={sessionData.pipeline} />
                <RecentPanel recent={sessionData.recentSessions} />
              </aside>

              <section className="rpt-col rpt-col--mid">
                {/* D4 Agent4 minimal · 删 IM (用户路径非聊天 · 是 scan → drill → 处置)
                    保留扫描进度+预览 · 完整 drill 由下方 AlertDrillDrawer 触发 */}
                <div
                  className="alert-mid-summary"
                  role="status"
                  data-testid="alert-mid-placeholder"
                >
                  <span className="alert-mid-summary__label">扫描进度</span>
                  <span className="alert-mid-summary__hint">
                    {sessionData.conversation.length > 0
                      ? `AI 扫描 · ${sessionData.conversation.length} 条进度记录 · 选中客户查看 drill 详情`
                      : "等待扫描启动 · 启动后从下方红/黄/绿榜单选中客户查看处置建议"}
                  </span>
                </div>
              </section>

              <section className="rpt-col rpt-col--right">
                <OutputPanel
                  tab={tab}
                  onTabChange={setTab}
                  distribution={sessionData.distribution}
                  heat={sessionData.heat}
                  reach={sessionData.reach}
                  topCases={sessionData.topCases}
                  totals={sessionData.totals}
                  onSelectClient={setSelectedClientId}
                />
              </section>
            </div>

            <SignalHeatmapPanel bars={currentHeat} phase={phase} />

            <AlertExportPanel
              phase={phase}
              scanError={scanError}
              onSelectClient={setSelectedClientId}
              topCases={sessionData.topCases}
              onExport={handleExportDocx}
              exporting={exporting}
            />

            {selectedClientId ? (
              <AlertDrillDrawer
                clientId={selectedClientId}
                sessionId={liveData ? scanSessionId : ""}
                fallbackTopCase={
                  sessionData.topCases.find((c) => c.client_id === selectedClientId) ?? null
                }
                onClose={() => setSelectedClientId(null)}
              />
            ) : null}

            <section className="ev-claim-summary" aria-label="Evidence-grounded 分析结论">
              <span className="ev-claim-summary-label">分析结论 · Evidence-grounded</span>
              <ClaimText text={ALERT_EVIDENCE.summary} />
            </section>
          </>
        )}
      </div>
    </EvidenceProvider>
  );
}

/* ────────────────────── SESSION PICKER ────────────────────── */

function SessionPickerBar(p: {
  sessions: AlertRecentSession[];
  selectedId: string;
  onSelect: (id: string) => void;
  liveMode: boolean;
  currentLabel: string;
}) {
  return (
    <div className="alert-session-picker" data-testid="alert-session-picker">
      <span className="alert-session-picker__eyebrow">SESSION · 切场景</span>
      <select
        className="alert-session-picker__select"
        data-testid="alert-session-select"
        value={p.selectedId}
        onChange={(e: ChangeEvent<HTMLSelectElement>) => p.onSelect(e.target.value)}
        disabled={p.liveMode}
        aria-label="切扫描场景"
      >
        {p.sessions.map((s) => (
          <option key={s.id} value={s.id}>
            {s.objective} · 池 {s.pool} · 红 {s.redCount}
          </option>
        ))}
      </select>
      <span className="alert-session-picker__hint">
        {p.liveMode ? "Live 模式 · 已锁定 backend session" : `当前 mock · ${p.currentLabel}`}
      </span>
    </div>
  );
}

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
  onExport: () => void;
  exporting: boolean;
  isLive?: boolean;
}) {
  const isScanning = p.phase === "scanning";
  const isAfter = p.phase === "after";
  const btnLabel = isScanning ? "扫描中…" : isAfter ? "重新扫描" : "启动风险扫描";
  return (
    <header className="rpt-hero al-hero">
      <div className="rpt-hero__eyebrow">
        <span className="rpt-hero__badge" aria-hidden>◉</span>
        <span>AGENT · 04 · TOWER · 贷中预警</span>
        <span className="rpt-hero__sep">·</span>
        <span>贷中预警引擎</span>
        <span className="al-hero__kb" data-phase={p.phase}>
          <span className="al-hero__kb-dot" aria-hidden />
          {p.kbState}
        </span>
        {/* PM bug #4 P2 · MOCK/LIVE badge · 5 workspace 一致 */}
        <ModePill isLive={p.isLive ?? false} testId="alert-mode-pill" size="sm" />
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
          {isAfter ? (
            <button
              type="button"
              data-testid="alert-export-docx-cta"
              onClick={p.onExport}
              disabled={p.exporting}
              style={{
                marginTop: 8,
                padding: "8px 14px",
                borderRadius: 10,
                border: "1px solid rgba(0,0,0,0.18)",
                background: "var(--surface-1, rgba(255,255,255,0.85))",
                color: "var(--ink-strong, #2a1a16)",
                fontSize: 13,
                cursor: p.exporting ? "wait" : "pointer",
              }}
            >
              {p.exporting ? "导出中…" : "导出命中清单 (.docx)"}
            </button>
          ) : null}
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

function ScanProgressStrip(p: { phase: ScanPhase; steps: ScanStep[]; stepIdx: number }) {
  if (p.phase === "before") return null;
  const current = p.steps[Math.min(p.stepIdx, p.steps.length - 1)] ?? p.steps[0];
  return (
    <section className="rpt-panel al-prog" data-phase={p.phase} aria-label="风险扫描进度">
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
        <div className="al-prog__fill" style={{ width: `${current?.pct ?? 100}%` } as CSSProperties} />
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
      tier: "red" as RiskGrade,
      label: GRADE_LABEL.red,
      count: red,
      pct: total ? Math.round((red / total) * 100) : 0,
      caption: redReach ? `触达 ${redReach.reached} / ${redReach.total}` : "—",
      detail: `TOP ${redCases.length} 单 · ${redCases[0]?.customer ?? "—"} ${redCases[0]?.amount ?? ""}`,
      animate: true,
    },
    {
      tier: "yellow" as RiskGrade,
      label: GRADE_LABEL.yellow,
      count: yellow,
      pct: total ? Math.round((yellow / total) * 100) : 0,
      caption: ylReach ? `触达 ${ylReach.reached} / ${ylReach.total}` : "—",
      detail: `触达率 ${ylReach ? ylReach.reachedPct.toFixed(1) + "%" : "—"}`,
      animate: false,
    },
    {
      tier: "green" as RiskGrade,
      label: GRADE_LABEL.green,
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
          <li
            key={l.tier}
            className="alert-wall-light"
            data-tier={l.tier}
            data-animate={l.animate}
            data-testid={`alert-traffic-light-${l.tier}`}
          >
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

/* ─── 预警客户队列 ─── */

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
            <span className="al-queue__chip" data-tier="delta">最新扫描更新</span>
          ) : null}
        </div>
      </div>
      <ul className="al-queue__list">
        {p.queue.map((c) => (
          <li
            key={c.id}
            className="al-queue__item"
            data-tier={c.tier}
            data-testid="alert-hitlist-row"
            data-client-id={c.client_id}
          >
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

/* ─── 风险信号热区 ─── */

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
        {p.phase === "after" ? <span className="al-heatbars__delta">本轮扫描已刷新</span> : null}
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
                <div className="al-heatbars__fill" style={{ width: `${pct}%` } as CSSProperties} />
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
        <div className="rpt-panel__counter">{cur?.coverage?.toLocaleString() ?? 0} 户</div>
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
          count > 0 ? `已导入 ${count} 份 · 下轮扫描纳入` : "支持 Excel / PDF / 名单库 / 规则文档",
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
          <div className="al-up__plus" aria-hidden>+</div>
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
          sources.slice(0, 4).map((s) => s.label).join(" · "),
        )}
      />
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">监测源</div>
        <div className="rpt-panel__counter">{online}/{sources.length} 在线</div>
      </div>
      <div className="rpt-panel__body">
        <ul className="al-src__list">
          {sources.map((s) => (
            <li key={s.id} className="al-src__item" data-status={s.status}>
              <span className="al-src__ico" aria-hidden>源</span>
              <div className="al-src__body">
                <div className="al-src__lbl">{s.label}</div>
                <div className="al-src__desc">{s.desc}</div>
              </div>
              <span className="al-src__tag" data-status={s.status}>{s.statusLabel}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

const CAT_LABEL: Record<string, string> = { external: "外部", internal: "内部", cross: "交叉" };
const SEV_LABEL: Record<string, string> = { high: "高危", mid: "中危", low: "低危" };

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
        <div className="rpt-panel__counter">{enabled}/{rules.length} · 命中 {totalHit}</div>
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
        <div className="rpt-panel__counter">{done}/{steps.length}</div>
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
    <section className="rpt-panel rpt-panel--conv al-conv rpt-conv" ref={scrollRef}>
      <PanelPinHandle
        {...panelPin(
          "conversation",
          "预警对话",
          `贷中预警 · ${msgs.length} 条`,
          lastAi ? msgTitle(lastAi.content) : "等待对话开始",
        )}
      />
      {msgs.map((m) => <ConversationMsg key={m.id} m={m} />)}
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
    /* PM bug #3 · P1 · 改 useAuthStore 动态 · 不 hardcode 王哲 */
    const u = useAuthStore.getState().currentUser;
    const userSubtitle = u ? `${u.team} · ${u.name}` : "未登录";
    return (
      <div className="rpt-msg rpt-msg--user" data-cmd={isCmd ? "yes" : "no"}>
        <MessagePinHandle {...msgPinProps(m, isCmd ? `${userSubtitle} · /command` : userSubtitle)} />
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
                      {s.evidences.map((e, j) => <li key={j}>{e}</li>)}
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
  const onPin = (payload: PinDropPayload) => {
    setValue((v) => (v ? `${v} @引用:${payload.title} ` : `@引用:${payload.title} `));
  };
  const drop = usePinDrop<HTMLDivElement>(onPin);
  return (
    <div
      className={`rpt-composer${drop.dropHover ? " rpt-composer--drop-hover" : ""}`}
      onDragEnter={drop.onDragEnter}
      onDragOver={drop.onDragOver}
      onDragLeave={drop.onDragLeave}
      onDrop={drop.onDrop}
    >
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
  onSelectClient: (id: string) => void;
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
          <DistView
            distribution={p.distribution}
            totals={p.totals}
            topCases={p.topCases}
            onSelectClient={p.onSelectClient}
          />
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

function DistView(p: {
  distribution: IndustryDistribution[];
  totals: { red: number; yellow: number; green: number };
  topCases: TopCase[];
  onSelectClient: (id: string) => void;
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
          <li
            key={c.id}
            className="al-dv__tc"
            data-testid="alert-top-case-row"
            data-client-id={c.client_id}
            onClick={() => p.onSelectClient(c.client_id)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") p.onSelectClient(c.client_id);
            }}
            style={{ cursor: "pointer" }}
          >
            <div className="al-dv__tc-head">
              <span className="al-dv__tc-tier" data-tier={c.tier}>红</span>
              <div className="al-dv__tc-name">{c.customer}</div>
              <span className="al-dv__tc-amt">{c.amount}</span>
            </div>
            <ul className="al-dv__tc-trig">
              {c.triggers.map((t, i) => <li key={i}>{t}</li>)}
            </ul>
            <div className="al-dv__tc-adv">处置 · {c.advice}</div>
            <div className="al-dv__tc-time">{c.lastUpdate}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}

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
          <div key={c.date} className="al-hv__cell" data-level={c.level} title={`${c.date} · ${c.count} 次`}>
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

/* ─────────── AlertEmptyState · W-CF2-A2 · 2026-04-28 ─────────── */

function AlertEmptyState(p: {
  onPrimary: () => void;
  onSecondary: () => void;
  onTertiary: () => void;
  scanRunning: boolean;
  scanError: string | null;
}) {
  return (
    <div className="alert-empty" data-testid="alert-empty-skeleton">
      <header className="alert-empty__hero">
        <div className="alert-empty__hero-eyebrow">AGENT · 04 · TOWER · 贷中预警引擎</div>
        <h1 className="alert-empty__hero-title">
          贷中风险预警 · 在贷客户池批量扫描 + 红黄绿分级榜单
        </h1>
        <p className="alert-empty__hero-sub">
          外部信号 (裁判文书 / 工商 / 舆情 / 失信) × 内部规则 (本行制度 / 限额 / 白黑名单)
          双路交叉 · 100 家 ≤ 2 分钟扫完吐分级榜单 + 单客户证据链 + 处置建议
        </p>
      </header>

      <section className="alert-empty__cta-row" aria-label="3 CTA 分级">
        <button
          type="button"
          className="alert-empty__cta alert-empty__cta--primary"
          data-testid="alert-scan-cta"
          data-cta="primary"
          onClick={p.onPrimary}
          disabled={p.scanRunning}
        >
          <span className="alert-empty__cta-rank">主操作</span>
          <span className="alert-empty__cta-title">
            {p.scanRunning ? "扫描中…" : "启动风险扫描"}
          </span>
          <span className="alert-empty__cta-sub">
            POST /api/alert/scan · 在贷客户池规则扫 + 双路交叉
          </span>
        </button>
        <button
          type="button"
          className="alert-empty__cta alert-empty__cta--secondary"
          data-testid="alert-scan-cta-secondary"
          data-cta="secondary"
          onClick={p.onSecondary}
          disabled={p.scanRunning}
        >
          <span className="alert-empty__cta-rank">次操作</span>
          <span className="alert-empty__cta-title">选规则集 + 调阈值</span>
          <span className="alert-empty__cta-sub">
            22 条规则 · 风险偏好 toggle · 阈值 inline edit
          </span>
        </button>
        <button
          type="button"
          className="alert-empty__cta alert-empty__cta--tertiary"
          data-testid="alert-history-tertiary"
          data-cta="tertiary"
          onClick={p.onTertiary}
        >
          <span className="alert-empty__cta-rank alert-empty__cta-rank--demo">
            历史 (示例)
          </span>
          <span className="alert-empty__cta-title">看示例扫描</span>
          <span className="alert-empty__cta-sub">
            微贷组合 100 家 · 培训演示用 · 切真实路径随时返回
          </span>
        </button>
      </section>

      <section
        className="alert-empty__skeleton"
        aria-label="贷中预警面板 · 空骨架"
        data-testid="alert-empty-skeleton-panels"
      >
        <div className="alert-empty__skel-row alert-empty__skel-traffic">
          <div className="alert-empty__skel-card" data-skel="red" data-testid="alert-traffic-light-red">
            <div className="alert-empty__skel-light" data-tier="red" aria-hidden />
            <div className="alert-empty__skel-lbl">红档 · 立即处置</div>
            <div className="alert-empty__skel-hint">扫描完显示户数 + TOP 1 客户</div>
          </div>
          <div className="alert-empty__skel-card" data-skel="yellow" data-testid="alert-traffic-light-yellow">
            <div className="alert-empty__skel-light" data-tier="yellow" aria-hidden />
            <div className="alert-empty__skel-lbl">黄档 · 重点观察</div>
            <div className="alert-empty__skel-hint">扫描完显示户数 + 触达率</div>
          </div>
          <div className="alert-empty__skel-card" data-skel="green" data-testid="alert-traffic-light-green">
            <div className="alert-empty__skel-light" data-tier="green" aria-hidden />
            <div className="alert-empty__skel-lbl">绿档 · 常规跟踪</div>
            <div className="alert-empty__skel-hint">下轮 T+7 自动复扫</div>
          </div>
        </div>
        <div className="alert-empty__skel-row">
          <div className="alert-empty__skel-card alert-empty__skel-card--wide" data-skel="hitlist">
            <div className="alert-empty__skel-lbl">命中榜单 (HitList)</div>
            <div className="alert-empty__skel-hint">
              点击客户 → 右侧 drill drawer 显信号 timeline + 处置建议 ·{" "}
              <button
                type="button"
                className="alert-empty__skel-export"
                data-testid="alert-export-docx-btn"
                disabled
                aria-disabled
              >
                导出榜单 .docx (待扫描完成启用)
              </button>
            </div>
          </div>
        </div>
        <div className="alert-empty__skel-row">
          <div className="alert-empty__skel-card alert-empty__skel-card--wide" data-skel="signalmap">
            <div className="alert-empty__skel-lbl">SignalMap · 30 天信号热力 + 触达率</div>
            <div className="alert-empty__skel-hint">扫描完显示行业 × 信号类型分布</div>
          </div>
        </div>
      </section>

      <footer
        className="alert-empty__status"
        data-testid="alert-empty-status-pill"
        aria-label="状态透明"
      >
        <span className="alert-empty__status-item" data-tone="ok">◉ 服务正常</span>
        <span className="alert-empty__status-item">
          KB 待上传 · 客户名录 / 规则库 / 内部制度
        </span>
        <span className="alert-empty__status-item alert-empty__status-item--demo">
          {p.scanRunning ? "扫描流式中…" : "等待主操作"}
        </span>
        {p.scanError ? (
          <span className="alert-empty__status-item alert-empty__status-item--err" role="alert">
            ⚠ {p.scanError}
          </span>
        ) : null}
      </footer>
    </div>
  );
}

/* ─────────── AlertExportPanel · started=true 路径 ─────────── */

function AlertExportPanel(p: {
  phase: ScanPhase;
  scanError: string | null;
  onSelectClient: (id: string) => void;
  topCases: TopCase[];
  onExport: () => void;
  exporting: boolean;
}) {
  const ready = p.phase === "after";
  return (
    <section
      className="rpt-panel alert-export-bar"
      aria-label="导出 + 详情入口"
      data-testid="alert-export-bar"
    >
      <div className="alert-export-bar__left">
        <span className="alert-export-bar__eyebrow">EXPORT · 榜单与处置</span>
        {p.scanError ? (
          <span className="alert-export-bar__err" role="alert">
            ⚠ {p.scanError}
          </span>
        ) : null}
      </div>
      <div className="alert-export-bar__right">
        {ready && p.topCases[0] ? (
          <button
            type="button"
            className="alert-export-bar__drill"
            data-testid="alert-drill-cta"
            onClick={() => p.onSelectClient(p.topCases[0].client_id)}
          >
            查看 TOP 客户详情
          </button>
        ) : null}
        <button
          type="button"
          className="alert-export-bar__docx"
          data-testid="alert-export-docx-btn"
          onClick={p.onExport}
          disabled={!ready || p.exporting}
        >
          {p.exporting ? "导出中…" : "导出榜单 .docx"}
        </button>
      </div>
    </section>
  );
}

/* ─────────── AlertDrillDrawer · 单客户 drill (走 GET /api/alert/drill/{client_id}) ─────────── */

function AlertDrillDrawer(p: {
  clientId: string;
  sessionId: string;
  fallbackTopCase: TopCase | null;
  onClose: () => void;
}) {
  const [data, setData] = useState<AlertDrillResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setFetchError(null);
    fetchDrill(p.clientId, p.sessionId)
      .then((resp) => {
        if (cancelled) return;
        setData(resp);
      })
      .catch((err) => {
        if (cancelled) return;
        setFetchError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [p.clientId, p.sessionId]);

  function onBackdropClick(ev: React.MouseEvent<HTMLDivElement>) {
    if (ev.target === ev.currentTarget) p.onClose();
  }

  const fb = p.fallbackTopCase;
  const displayName = data?.company_name ?? fb?.customer ?? p.clientId;
  const displayLevel = (data?.level as RiskGrade | undefined) ?? fb?.tier ?? "yellow";
  const triggers = fb?.triggers ?? [];
  const advice = (data?.disposition as { content?: string } | undefined)?.content ?? fb?.advice ?? "";
  const reasons = data?.reasons ?? [];
  const matched = data?.matched_rules ?? [];

  return (
    <div
      className="alert-drill-drawer-backdrop"
      onClick={onBackdropClick}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.32)",
        zIndex: 100,
        display: "flex",
        justifyContent: "flex-end",
      }}
    >
      <aside
        className="alert-drill-drawer"
        role="dialog"
        aria-label="客户详情 drawer"
        data-testid="alert-drill-drawer"
        data-client-id={p.clientId}
        style={{
          width: "min(480px, 90vw)",
          maxWidth: 480,
          height: "100vh",
          background: "var(--surface-1, #fff)",
          padding: 24,
          overflowY: "auto",
          boxShadow: "-12px 0 32px rgba(0,0,0,0.18)",
        }}
      >
        <header className="alert-drill-drawer__head" style={{ display: "flex", justifyContent: "space-between" }}>
          <span className="alert-drill-drawer__eyebrow">DRILL DETAIL</span>
          <button
            type="button"
            className="alert-drill-drawer__close"
            onClick={p.onClose}
            aria-label="关闭详情"
            data-testid="alert-drill-drawer-close"
            style={{ border: "none", background: "transparent", fontSize: 22, cursor: "pointer" }}
          >
            ×
          </button>
        </header>
        <h3 className="alert-drill-drawer__name" style={{ marginTop: 8 }}>{displayName}</h3>
        {loading ? (
          <p className="alert-drill-drawer__empty" data-testid="alert-drill-loading">加载中…</p>
        ) : fetchError ? (
          <div data-testid="alert-drill-fail" role="alert" style={{ color: "rgba(192,0,0,1)" }}>
            ⚠ 加载失败：{fetchError}
          </div>
        ) : (
          <dl className="alert-drill-drawer__meta">
            <div>
              <dt>风险等级</dt>
              <dd data-tier={displayLevel}>{GRADE_LABEL[displayLevel] ?? displayLevel}</dd>
            </div>
            {data?.score != null ? (
              <div>
                <dt>得分</dt>
                <dd>{data.score}</dd>
              </div>
            ) : null}
            {fb?.amount ? (
              <div>
                <dt>授信余额</dt>
                <dd>{fb.amount}</dd>
              </div>
            ) : null}
            {triggers.length > 0 ? (
              <div>
                <dt>触发信号</dt>
                <dd>{triggers.join(" · ")}</dd>
              </div>
            ) : null}
            {matched.length > 0 ? (
              <div>
                <dt>命中规则</dt>
                <dd>{matched.join(" · ")}</dd>
              </div>
            ) : null}
            {reasons.length > 0 ? (
              <div>
                <dt>原因摘要</dt>
                <dd>{reasons.join(" · ")}</dd>
              </div>
            ) : null}
            {advice ? (
              <div>
                <dt>处置建议{data?.disposition_source ? ` (${data.disposition_source})` : ""}</dt>
                <dd>{advice}</dd>
              </div>
            ) : null}
          </dl>
        )}
        <footer className="alert-drill-drawer__foot" style={{ marginTop: 16, fontSize: 12, opacity: 0.6 }}>
          <span>ESC / 点击 backdrop 关闭</span>
        </footer>
      </aside>
    </div>
  );
}
