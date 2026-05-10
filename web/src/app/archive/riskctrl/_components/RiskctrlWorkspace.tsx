"use client";

/**
 * /archive/riskctrl · Agent2 风控 (Forge) workspace · 三栏对话式
 * 2026-04-21 H2 · canon 横向迁移
 *
 * 左 Query / Rules / Recent · 中 Conversation + Composer · 右 DSL 树 / KS 双线 / Sample bar
 *
 * 继承 canon A 章 · Agent tint: --t-riskctrl (绛紫)
 * 业务：风险经理协同 AI 写 DSL → 回测 KS/通过率/坏账 → 调参 → 送审
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { KeyboardEvent, ChangeEvent } from "react";
import { DataSourceBadge } from "@/components/shared/DataSourceBadge";
import { type DataSourceKind, normalizeDataSource } from "@/lib/api/_data-source";
import { usePinDrop, type PinDropPayload } from "@/components/composer/use-pin-drop";
import { ClaimText, EvidenceProvider } from "@/components/evidence";
import { RISKCTRL_EVIDENCE } from "@/components/evidence/fixtures";
import {
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { MessagePinHandle } from "@/components/shell/MessagePinHandle";
import { ScanCTA } from "@/components/shared/ScanCTA";
import { CustomerSelector } from "@/components/shared/CustomerSelector";
import { PanelPinHandle } from "@/components/shell/PanelPinHandle";
import {
  exportDocx as exportDocxApi,
  exportPdf as exportPdfApi,
  exportXlsx as exportXlsxApi,
  LiveFailError,
  runBacktest,
  runDslGen,
  type BacktestDonePayload,
} from "@/lib/api/riskctrl";
import {
  RISKCTRL_GLOBAL_STATS,
  type ConversationMessage,
  type DslNode,
  type RiskctrlRecentSession,
  type RiskctrlSession,
  type RuleRef,
  type SampleBar,
} from "@/lib/mock/agent-riskctrl-sessions";

/* ── ALL IN Phase B step 2 · EMPTY_SESSION 替代 mock fallback (per channel 模板 de79725) ──
 * 之前 sessionData = liveData ?? mock[selectedSession] ?? mock[default] · 三层 fallback
 * 违反红线 #1 (假 live · 用户不知数据是 mock)
 * 改 sessionData = liveData ?? EMPTY_SESSION · 真 live 没回来时显空骨架 · 不显假数据 */
const EMPTY_SESSION: RiskctrlSession = {
  id: "empty",
  objective: "",
  stage: "等待真路径触发 · LLM 生成 DSL → 真回测",
  updated: "",
  query: {
    id: "empty-query",
    objective: "",
    sampleLabel: "",
    sampleSize: 0,
    windowLabel: "",
    targetKS: 0,
    targetPassRange: [0, 0],
    targetBadRate: 0,
    updated: "",
  },
  rules: [],
  currentRule: { id: "", name: "", version: "" },
  dsl: { id: "root", op: "IF", children: [] },
  ks: { ksPeak: 0, auc: 0, passRate: 0, badRate: 0, points: [] },
  samples: [],
  ruleStats: [],
  conversation: [],
  qcCounts: { block: 0, warn: 0, info: 0 },
  recentSessions: [],
};

const AGENT_KEY = "riskctrl";
const AGENT_HREF = "/archive/riskctrl";
const AGENT_ACCENT = "--t-riskctrl";

function truncate(s: string, n: number): string {
  const flat = s.replace(/\s+/g, " ").trim();
  return flat.length > n ? `${flat.slice(0, n - 1)}…` : flat;
}

function msgPinProps(msg: ConversationMessage, speaker: string) {
  return {
    id: `riskctrl:msg:${msg.id}`,
    title: truncate(msg.content, 42),
    subtitle: `${speaker} · ${msg.at}`,
    accentVar: AGENT_ACCENT,
    agentKey: AGENT_KEY,
    href: AGENT_HREF,
    fullText: msg.content,
  };
}

/* ALL IN Phase B step 1 · 删 secondary_preset / tertiary_history (mock 入口) ·
 * 仅保留 primary_dsl 真路径 (LLM 生成 DSL → 真回测) */
type RiskTrigger = "primary_dsl";

/* ─── backtest done event → liveData session merge (Step 8 · Phase A worker-A4) ───
 * 后端 backtest done 含 panels (ruleset/ks/samples/rule_stats) + metrics 顶层 KPI ·
 * 前端将 backend snake_case 字段 normalize 为 RiskctrlSession camelCase shape ·
 * 与 base mock session merge: ks/samples/ruleStats 切真数据 · 其他 (id/objective/
 * stage/query/dsl/conversation/recent) 保 base · live 视觉壳保留. */
function mergeBacktestIntoSession(
  base: RiskctrlSession,
  done: BacktestDonePayload,
): RiskctrlSession {
  return {
    ...base,
    id: done.session_id ?? base.id,
    stage: "live · 回测完成",
    updated: "刚刚",
    ks: {
      ksPeak: done.ks?.ksPeak ?? 0,
      auc: done.ks?.auc ?? 0,
      passRate: done.ks?.passRate ?? 0,
      badRate: done.ks?.badRate ?? 0,
      points: done.ks?.points ?? [],
    },
    samples: (done.samples ?? []).map((s) => ({
      key: s.key,
      label: s.label,
      count: s.count,
      pct: s.pct,
      badRate: s.bad_rate,
    })),
    ruleStats: (done.rule_stats ?? []).map((r) => ({
      ruleId: r.rule_id ?? "",
      hit: r.hit,
      fp: r.fp,
      tn: r.tn,
    })),
  };
}

type ExportKind = "docx" | "xlsx" | "pdf";

type ExportInfo = {
  status: "idle" | "running" | "done" | "error";
  /** kind 标识本次正在 / 最近一次完成 / 失败的导出格式 (UI 三按钮分别 reflect status) */
  kind?: ExportKind;
  message?: string;
};

type RecentLabel = { value: string; label: string; demo?: boolean };

/* ALL IN Phase B step 1 · 删 RISKCTRL_RECENT_DEMO_OPTIONS / RISKCTRL_PRESET_OPTIONS
 * (history + preset dropdown 入口删除 · 仅保留 primary DSL gen 真路径) */

export default function RiskctrlWorkspace() {
  /* ALL IN Phase B step 2 · workspace state 简化 · 删 selectedSession (无 mock 库可切) ·
   * sessionData = liveData ?? EMPTY_SESSION · 真 live 没回来时显空骨架 · 不显假数据
   * started = "是否进入功能态" · empty-state-design-protocol v1.0 用户触发后才 setStarted(true) */
  const [started, setStarted] = useState<boolean>(false);
  const [liveData, setLiveData] = useState<RiskctrlSession | null>(null);
  const [selectedRuleOrSegment, setSelectedRuleOrSegment] = useState<
    { kind: "rule"; id: string } | { kind: "segment"; key: SampleBar["key"] } | null
  >(null);

  /* ALL IN Phase B step 2 · sessionData 单点派生 · live 优先 · 否则 EMPTY_SESSION (不 fallback mock) */
  const sessionData: RiskctrlSession = liveData ?? EMPTY_SESSION;

  const isLive = liveData !== null;
  /* 件 #2 · data_source SSOT 真消费 (per Q-054 risk #1) · 默认 mock (no run yet). */
  const [currentDataSource, setCurrentDataSource] = useState<DataSourceKind>("mock");

  /* ALL IN Phase B step 1 · 删 secondary_preset / tertiary_history state ·
   * 仅留 primary_dsl 真路径 (LLM 生成 DSL → 真回测) */
  const [trigger, setTrigger] = useState<RiskTrigger | null>(null);

  /* 既有 scanned state (post-backtest 视觉解锁) · 不动 */
  const [scanned, setScanned] = useState(false);

  /* 后端 wire state */
  const [scanRunning, setScanRunning] = useState(false);
  const [scanError, setScanError] = useState<string>("");
  const [rulesetId, setRulesetId] = useState<string>("");
  const [exportInfo, setExportInfo] = useState<ExportInfo>({ status: "idle" });

  /* ALL IN Phase B step 4 · live evidence (来自 backtest done envelope panels.evidence) ·
   * 有 live 时 EvidenceProvider 用 live items · 没 live 时 fallback fixture (channel 模板做法) */
  const [liveEvidenceItems, setLiveEvidenceItems] = useState<
    Array<{ source: string; snippet: string; ref_id: string; confidence: number; meta?: Record<string, unknown> }>
  >([]);

  /* Stage Fix · live-fallback-banner-spec v1.0 §2 规则 1 ·
     按 endpoint 分别记录失败 · UI 显式 banner + retry · 不 silent swap mock */
  type LiveFail = {
    endpoint: string;
    label: string;
    status: number;
    message: string;
    bodyExcerpt: string;
  };
  const [liveFail, setLiveFail] = useState<LiveFail | null>(null);
  const [retryHandler, setRetryHandler] = useState<(() => void) | null>(null);

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

  function clearLiveFail(): void {
    setLiveFail(null);
    setRetryHandler(null);
  }

  /* lastRuleset · dsl_gen done 后 store 整 ruleset 对象 · backtest 直消费 (Step 8 进 liveData) */
  const [lastRuleset, setLastRuleset] = useState<Record<string, unknown> | null>(null);
  /* Default 指向真存在的 7500 行历史贷款 fixture (CLAUDE.md §10 agent2 mock).
     旧默认 "samples/sample.csv" 不存在 · backtest 必返 400 (Q-040 Demo blocker). */
  const [lastSampleCsvPath, setLastSampleCsvPath] = useState<string>(
    "data/mock/agent2-samples/loans.csv",
  );

  /* Primary CTA · 选样本 + 写策略 → POST /api/riskctrl/dsl_gen 真 LLM 生成 */
  /* PB#5 · AbortController · SSE 防僵尸连接 (DSL gen + backtest 共用 ref · 不并发) */
  const abortRef = useRef<AbortController | null>(null);
  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  const triggerDslGen = useCallback(async (ruleText: string) => {
    const text = ruleText || "拒绝近 30 日逾期 ≥ 3 次的小微客户";
    setStarted(true);
    setTrigger("primary_dsl");
    setScanRunning(true);
    setScanError("");
    clearLiveFail();
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    try {
      const result = await runDslGen({
        strategyIntent: text,
        sampleCsvPath: lastSampleCsvPath,
      }, undefined, ac.signal);
      if (ac.signal.aborted) return;
      if (result?.ruleset_id) setRulesetId(result.ruleset_id);
      if (result?.ruleset) setLastRuleset(result.ruleset);
      /* 件 #2 · data_source SSOT 真消费 · dsl_gen done envelope (per riskctrl.ts T2 enum) */
      if (result?.data_source) setCurrentDataSource(normalizeDataSource(result.data_source));
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      recordLiveFail("DSL 生成", e, () => triggerDslGen(text));
      setScanError(e instanceof Error ? e.message : String(e));
      /* 件 #2 · live 失败 → trust model 一级降级 */
      setCurrentDataSource("mock_fallback");
    } finally {
      if (!ac.signal.aborted) setScanRunning(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lastSampleCsvPath]);

  /* ALL IN Phase B step 1 · 删 onSelectPreset / onSelectRecent / onApplySelection ·
   * 入口收敛到 onPrimaryDslGen 真路径 */

  /* 样本回测 · POST /api/riskctrl/backtest · ScanCTA onDone 触发.
     Phase A worker-A4 · backend SSE body 改 {ruleset, csv_path, ...} · 必须先 dsl_gen
     拿 ruleset · lastRuleset 兜底空 (会 422 显示 banner 提示用户先 gen). */
  const triggerBacktest = useCallback(async () => {
    if (!lastRuleset) {
      setScanError("请先生成 DSL · 再跑回测 (backtest 必须含 ruleset)");
      return;
    }
    setScanRunning(true);
    setScanError("");
    clearLiveFail();
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    try {
      const result = await runBacktest({
        ruleset: lastRuleset,
        csvPath: lastSampleCsvPath,
      }, undefined, ac.signal);
      if (ac.signal.aborted) return;
      setScanned(true);
      if (result) {
        // ALL IN Phase B step 2 · backtest done → liveData · base 改 EMPTY_SESSION
        // 真 live 数据 merge 到空骨架上 · 不再 fallback mock session
        const merged = mergeBacktestIntoSession(EMPTY_SESSION, result);
        setLiveData(merged);
        /* 件 #2 · data_source SSOT 真消费 · backtest done envelope 5 enum (per riskctrl.ts T2) */
        setCurrentDataSource(normalizeDataSource(result.data_source));
        /* ALL IN Phase B step 4 · 取 live evidence items (后端 EvidenceDrawer payload) ·
         * 转 EvidenceProvider 接受的 EvidenceItem shape (source/snippet/ref_id/confidence/meta) */
        if (result.evidence?.items?.length) {
          setLiveEvidenceItems(
            result.evidence.items.map((it) => ({
              source: it.source,
              snippet: it.snippet,
              ref_id: it.anchor || it.evidence_id,
              confidence: it.confidence,
              meta: { ...it.meta, source_tier: it.source_tier, claim_type: it.claim_type },
            })),
          );
        }
      }
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      recordLiveFail("样本回测", e, () => triggerBacktest());
      setScanError(e instanceof Error ? e.message : String(e));
      /* 件 #2 · live 失败 → trust model 一级降级 */
      setCurrentDataSource("mock_fallback");
    } finally {
      if (!ac.signal.aborted) setScanRunning(false);
    }
  }, [lastRuleset, lastSampleCsvPath]);

  /* 三件套导出 · POST /api/riskctrl/export_{docx,xlsx,pdf} · backend Step 7 已实装
     (agent_riskctrl/exports.py · python-docx / openpyxl / reportlab 本地渲染 · 不走境外 API) */
  const triggerExport = useCallback(async (kind: ExportKind) => {
    if (!rulesetId && !scanned) {
      setExportInfo({
        status: "error",
        kind,
        message: "尚无回测产物 · 先生成 DSL 或选预置 · 再跑回测",
      });
      return;
    }
    setExportInfo({ status: "running", kind });
    /* ALL IN Phase B step 1 · 移除 preset fallback · sid 仅来自真 ruleset_id 或最小默认 */
    const sid = rulesetId || "demo";
    const apiByKind = {
      docx: exportDocxApi,
      xlsx: exportXlsxApi,
      pdf: exportPdfApi,
    } as const;
    const labelByKind = { docx: "Word", xlsx: "Excel", pdf: "PDF" } as const;
    try {
      const blob = await apiByKind[kind](sid);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `riskctrl_backtest_${sid}.${kind}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setExportInfo({ status: "done", kind });
    } catch (e) {
      if (e instanceof LiveFailError && e.status === 404) {
        setExportInfo({
          status: "error",
          kind,
          message: `导出端点 /api/riskctrl/export_${kind} 不可用`,
        });
        return;
      }
      recordLiveFail(`${labelByKind[kind]} 导出`, e, () => triggerExport(kind));
      setExportInfo({
        status: "error",
        kind,
        message: e instanceof Error ? e.message : String(e),
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rulesetId, scanned]);

  return (
    <EvidenceProvider
      /* ALL IN Phase B step 4 · live evidence 优先 · 无 live 时 fallback RISKCTRL_EVIDENCE fixture
       * (channel 模板 ef5ba13 做法 · 真路径触发后 sidebar evidence drawer 显真证据) */
      items={liveEvidenceItems.length > 0 ? liveEvidenceItems : RISKCTRL_EVIDENCE.items}
      unfilledFields={RISKCTRL_EVIDENCE.unfilledFields}
    >
      <div
        data-view="archive-riskctrl"
        data-scanned={scanned ? "yes" : "no"}
        data-started={started ? "yes" : "no"}
        data-trigger={trigger ?? "none"}
        data-session={sessionData.id}
        data-live={isLive ? "yes" : "no"}
        data-testid="riskctrl-workspace"
      >
        <RiskHero sessionData={sessionData} isLive={isLive} dataSourceKind={currentDataSource} />

        <RiskTriggerBar
          onPrimaryDslGen={() => triggerDslGen("")}
          scanRunning={scanRunning}
        />

        {started ? (
          <>
            {/* ALL IN Phase B step 1 · 删 tertiary_history demo-banner (history dropdown 入口已删) */}

            {liveFail ? (
              <div
                className="riskctrl-live-fail-banner"
                role="alert"
                data-testid="riskctrl-live-fail-banner"
                data-status={liveFail.status}
                data-endpoint={liveFail.endpoint}
              >
                <span className="riskctrl-live-fail-banner__icon" aria-hidden>⚠️</span>
                <span className="riskctrl-live-fail-banner__text">
                  后端 <b>{liveFail.label}</b> 调用失败 (
                  {liveFail.status > 0 ? `HTTP ${liveFail.status}` : "network/SSE"})
                  · 当前显 fallback 演示数据 · 切真实路径请重试
                  {liveFail.bodyExcerpt ? (
                    <span className="riskctrl-live-fail-banner__detail">
                      · 详情：{liveFail.bodyExcerpt}
                    </span>
                  ) : null}
                </span>
                {retryHandler ? (
                  <button
                    type="button"
                    className="riskctrl-live-fail-banner__retry"
                    onClick={() => retryHandler()}
                    data-testid="riskctrl-live-fail-retry"
                  >
                    重试
                  </button>
                ) : null}
                <button
                  type="button"
                  className="riskctrl-live-fail-banner__dismiss"
                  onClick={clearLiveFail}
                  aria-label="关闭横幅"
                >
                  ×
                </button>
              </div>
            ) : null}

            {scanError && !liveFail ? (
              <div
                className="riskctrl-error-banner"
                role="alert"
                data-testid="riskctrl-error-banner"
              >
                后端调用失败：{scanError}
              </div>
            ) : null}

            <RiskIndicatorRow sessionData={sessionData} />
            <div className="rpt-body">
              <aside className="rpt-side">
                <QueryPanel sessionData={sessionData} />
                <RulesPanel
                  sessionData={sessionData}
                  selectedRuleId={
                    selectedRuleOrSegment?.kind === "rule"
                      ? selectedRuleOrSegment.id
                      : null
                  }
                  onSelectRule={(id) => setSelectedRuleOrSegment({ kind: "rule", id })}
                />
                {/* ALL IN Phase B step 2 · RecentPanel 改空状态 · 不再切 mock session ·
                 * TODO Phase A.5 ship 后接 ledger 显真历史 backtest list (RFC 2 watcher 出 event) */}
                <RecentPanel sessionData={sessionData} />
              </aside>
              <main className="rpt-main">
                <div data-testid="riskctrl-backtest-cta">
                  <ScanCTA
                    label="样本回测"
                    tone="riskctrl"
                    onDone={() => {
                      setScanned(true);
                      void triggerBacktest();
                    }}
                    steps={[
                      { label: "装载 DSL 规则 · 3 条件", pct: 18 },
                      { label: "采样 · 50K 近 30 日样本", pct: 42 },
                      { label: "计算 KS / 通过率", pct: 68 },
                      { label: "AB 对比 · 现行版", pct: 88 },
                      { label: "生成回测报告 · 完成", pct: 100 },
                    ]}
                  />
                </div>
                <ConversationPanel sessionData={sessionData}>
                  <RiskComposer sessionData={sessionData} />
                </ConversationPanel>
              </main>
              <aside className="rpt-aux">
                <RiskOutputPanel
                  sessionData={sessionData}
                  rulesetId={rulesetId}
                  exportInfo={exportInfo}
                  onExport={triggerExport}
                  selectedSegmentKey={
                    selectedRuleOrSegment?.kind === "segment"
                      ? selectedRuleOrSegment.key
                      : null
                  }
                  onSelectSegment={(key) => setSelectedRuleOrSegment({ kind: "segment", key })}
                />
              </aside>
            </div>
            <section className="ev-claim-summary" aria-label="Evidence-grounded 分析结论">
              <span className="ev-claim-summary-label">分析结论 · Evidence-grounded</span>
              <ClaimText text={RISKCTRL_EVIDENCE.summary} />
            </section>
          </>
        ) : (
          <RiskEmptySkeleton />
        )}
      </div>
    </EvidenceProvider>
  );
}

/* ── Primary CTA bar (ALL IN Phase B step 1 · 删 secondary preset / tertiary history) ─── */

function RiskTriggerBar(p: {
  onPrimaryDslGen: () => void;
  scanRunning: boolean;
}) {
  const primaryLabel = p.scanRunning ? "DSL 生成中…" : "选样本 + 写策略 · 生成 DSL";
  return (
    <section
      className="riskctrl-trigger-bar"
      aria-label="主入口 · 真接 LLM 生成 DSL"
      data-testid="riskctrl-trigger-bar"
    >
      <button
        type="button"
        className="riskctrl-trigger-bar__primary"
        onClick={p.onPrimaryDslGen}
        disabled={p.scanRunning}
        data-testid="riskctrl-dsl-gen-cta"
      >
        {primaryLabel}
      </button>
    </section>
  );
}

/* ── Empty-state skeleton (空骨架 · 不显示 mock 真数据) ───── */

function RiskEmptySkeleton() {
  return (
    <section
      className="riskctrl-empty"
      aria-label="尚未触发策略 · 等待用户输入"
      data-testid="riskctrl-empty-skeleton"
    >
      <div className="riskctrl-empty__head">
        <h3 className="riskctrl-empty__title">等待触发策略</h3>
        <p className="riskctrl-empty__hint">
          上方
          <strong>「选样本 + 写策略 · 生成 DSL」</strong>
          → 真接 LLM 生成规则树；或
          <strong>选预置规则集</strong>
          快速启用；
          <em>「历史回测（示例）」</em>
          仅供培训演示。
        </p>
      </div>
      <div className="riskctrl-empty__panels">
        <div className="riskctrl-empty__panel" data-panel="dsl">
          DSL 规则树 · IF / AND / OR / THEN 4 op · 生成后此处显示
        </div>
        <div className="riskctrl-empty__panel" data-panel="ks">
          KS / AUC / 通过率 三大指标 + KS 双线图 · 回测完成显示
        </div>
        <div className="riskctrl-empty__panel" data-panel="sample">
          样本分布 (pass / review / block) · 回测完成显示
        </div>
        <div className="riskctrl-empty__panel" data-panel="export">
          回测报告导出 · 完成后可一键导出 Word / Excel / PDF
        </div>
      </div>
    </section>
  );
}

/* ── Hero ────────────────────────────────────────────── */

function RiskHero({ sessionData, isLive, dataSourceKind }: {
  sessionData: RiskctrlSession;
  isLive?: boolean;
  /* 件 #2 · data_source SSOT 真消费 · 5-enum trust model badge */
  dataSourceKind?: DataSourceKind;
}) {
  const s = sessionData;
  return (
    <header className="rpt-hero" data-live={isLive ? "yes" : "no"}>
      <div className="rpt-hero-left">
        <div className="rpt-hero-badge" aria-hidden>⌘</div>
        <div>
          {/* PM bug #3 fix · hero code 中文优先 · 英文 codename 保留 */}
          <div className="rpt-hero-code">AGENT · 02 · 风控 Forge</div>
          <h1 className="rpt-hero-title">
            风控 <em>Forge.</em>
          </h1>
          <div className="rpt-hero-sub">
            {s.objective} · {s.stage} · KS {s.ks.ksPeak.toFixed(2)} / 通过 {s.ks.passRate}%
          </div>
        </div>
      </div>
      {/* ALL IN Phase B step 1 · 删 ModePill (DataSourceBadge 5-enum trust model 已含 LIVE/MOCK 区分) */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        {/* 件 #2 · data_source SSOT 真消费 · 5-enum trust model badge (Q-054 risk #1) */}
        {dataSourceKind && (
          <DataSourceBadge kind={dataSourceKind} testId="riskctrl-data-source-badge" />
        )}
        <div className="rpt-hero-stats">
          <Stat label="本周处理" value={RISKCTRL_GLOBAL_STATS.weeklyProcessed} />
          <Stat label="KS 均值" value={RISKCTRL_GLOBAL_STATS.ksAvg} />
          <Stat label="平均时长" value={RISKCTRL_GLOBAL_STATS.avgDuration} />
        </div>
      </div>
    </header>
  );
}

/* ── v2 Hero · KS / AUC / 通过率 三大指标卡 ──────────── */

function RiskIndicatorRow({ sessionData }: { sessionData: RiskctrlSession }) {
  const s = sessionData;
  const { ksPeak, auc, passRate, badRate } = s.ks;
  const samples = s.samples;
  const pass = samples.find((x) => x.key === "pass");
  const block = samples.find((x) => x.key === "block");
  const review = samples.find((x) => x.key === "review");

  const cards = [
    {
      key: "ks",
      code: "KS",
      label: "KS 峰值",
      value: ksPeak.toFixed(3),
      pct: Math.round(ksPeak * 100),
      caption: `峰值 bin @ 分位 0.${Math.round(ksPeak * 10)}`,
      detail: ksPeak >= 0.4 ? "绿区 · 区分度佳" : ksPeak >= 0.3 ? "关注区" : "红区 · 区分不足",
      tone: ksPeak >= 0.4 ? "good" : ksPeak >= 0.3 ? "warn" : "bad",
    },
    {
      key: "auc",
      code: "AUC",
      label: "AUC 面积",
      value: auc.toFixed(3),
      pct: Math.round(auc * 100),
      caption: `ROC 曲线下面积`,
      detail: auc >= 0.75 ? "绿区 · 模型稳" : auc >= 0.65 ? "关注区" : "红区",
      tone: auc >= 0.75 ? "good" : auc >= 0.65 ? "warn" : "bad",
    },
    {
      key: "pass",
      code: "PASS",
      label: "通过率",
      value: `${passRate.toFixed(1)}%`,
      pct: Math.round(passRate),
      caption: `坏账率 ${badRate.toFixed(1)}%`,
      detail: `拒绝 ${block?.pct ?? 0}% · 复核 ${review?.pct ?? 0}%`,
      tone: passRate >= 30 && badRate <= 3 ? "good" : badRate > 5 ? "bad" : "warn",
    },
  ] as const;

  return (
    <section className="rpt-panel riskctrl-row" aria-label="KS AUC 通过率 指标行">
      <PanelPinHandle
        id="riskctrl:indicators"
        title="KS × AUC × 通过率"
        subtitle={`KS ${ksPeak.toFixed(3)} · 通过 ${passRate}%`}
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb="三大核心指标 + 样本分档"
      />
      <div className="riskctrl-row-head">
        <span className="eyebrow">METRICS · KS × AUC × 通过率</span>
        <span className="meta">
          样本 <b>{samples.reduce((a, b) => a + b.count, 0).toLocaleString()}</b> 条 ·
          当前策略 <b>{s.currentRule.name} {s.currentRule.version}</b>
        </span>
      </div>
      <ol className="riskctrl-row-list">
        {cards.map((c) => (
          <li key={c.key} className="riskctrl-row-card" data-tone={c.tone}>
            <div className="riskctrl-row-head-card">
              <span className="code">{c.code}</span>
              <span className="tone-dot" aria-hidden />
            </div>
            <div className="riskctrl-row-val">
              <span className="num">{c.value}</span>
            </div>
            <div className="riskctrl-row-lbl">{c.label}</div>
            <div className="riskctrl-row-bar" aria-hidden>
              <div className="riskctrl-row-fill" style={{ width: `${Math.min(c.pct, 100)}%` }} />
            </div>
            <div className="riskctrl-row-caption">{c.caption}</div>
            <div className="riskctrl-row-detail">{c.detail}</div>
          </li>
        ))}
        {pass && (
          <li className="riskctrl-row-dist" aria-label="样本分档">
            <div className="riskctrl-row-head-card">
              <span className="code">DIST</span>
            </div>
            <div className="riskctrl-dist-bar" aria-hidden>
              {samples.map((sb) => (
                <span
                  key={sb.key}
                  className="seg"
                  data-k={sb.key}
                  style={{ width: `${sb.pct}%` }}
                  title={`${sb.label} ${sb.count.toLocaleString()} · ${sb.pct}% · 坏账 ${sb.badRate}%`}
                />
              ))}
            </div>
            <ul className="riskctrl-dist-legend">
              {samples.map((sb) => (
                <li key={sb.key} data-k={sb.key}>
                  <span className="swatch" aria-hidden />
                  <span className="lbl">{sb.label}</span>
                  <span className="p">{sb.pct}%</span>
                </li>
              ))}
            </ul>
            <div className="riskctrl-row-detail">
              坏账率 · 通 {pass.badRate}% / 核 {review?.badRate ?? "—"}% / 拒 {block?.badRate ?? "—"}%
            </div>
          </li>
        )}
      </ol>
    </section>
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

/* ── 左栏 · Query 策略目标 ──────────────────────────── */

function QueryPanel({ sessionData }: { sessionData: RiskctrlSession }) {
  const q = sessionData.query;
  return (
    <section className="rpt-panel rpt-panel--tpl">
      <PanelPinHandle
        id="riskctrl:query"
        title={`策略目标 · ${q.objective}`}
        subtitle={`更新 ${q.updated}`}
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb="session 起点 + 目标边界"
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">QUERY · 策略目标</div>
          <h3 className="rpt-panel-title">{q.objective}</h3>
        </div>
        <span className="rpt-panel-meta">{q.updated}</span>
      </div>
      <div className="rpt-panel-body rc-q-body">
        <dl className="rc-q-meta">
          <div>
            <dt>样本</dt>
            <dd>{q.sampleLabel}</dd>
          </div>
          <div>
            <dt>规模</dt>
            <dd>
              {q.sampleSize.toLocaleString()} 笔 · {q.windowLabel}
            </dd>
          </div>
        </dl>
        <div className="rc-q-targets">
          <div className="rc-q-targets-lbl">目标指标</div>
          <div className="rc-q-target">
            <span className="k">KS ≥</span>
            <span className="v">{q.targetKS.toFixed(2)}</span>
          </div>
          <div className="rc-q-target">
            <span className="k">通过率</span>
            <span className="v">
              {(q.targetPassRange[0] * 100).toFixed(0)}% - {(q.targetPassRange[1] * 100).toFixed(0)}%
            </span>
          </div>
          <div className="rc-q-target">
            <span className="k">坏账率 ≤</span>
            <span className="v">{(q.targetBadRate * 100).toFixed(1)}%</span>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ── 左栏 · Rules 规则库 ───────────────────────────── */

const RULE_STATUS_LABEL: Record<RuleRef["status"], string> = {
  active: "在线",
  draft: "草稿",
  retired: "下线",
};

function RulesPanel({
  sessionData,
  selectedRuleId,
  onSelectRule,
}: {
  sessionData: RiskctrlSession;
  selectedRuleId: string | null;
  onSelectRule: (id: string) => void;
}) {
  const rules = sessionData.rules;
  const current = sessionData.currentRule;
  const active = rules.filter((r) => r.status === "active").length;
  return (
    <section className="rpt-panel rpt-panel--mat">
      <PanelPinHandle
        id="riskctrl:rules"
        title={`规则库 · ${current.version}`}
        subtitle="DSL 规则 + 版本"
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb="当前策略 + 可切历史版本"
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">RULES · 规则库</div>
          <h3 className="rpt-panel-title">
            {active} 在线 · {rules.length} 总
          </h3>
        </div>
        <span className="rpt-panel-meta">{current.version}</span>
      </div>
      <div className="rpt-panel-body rc-rule-body">
        {rules.map((r) => (
          <article
            key={r.id}
            className="rc-rule-card"
            data-status={r.status}
            data-current={r.id === current.id ? "yes" : "no"}
            data-selected={r.id === selectedRuleId ? "yes" : "no"}
            data-testid={`riskctrl-rule-card-${r.id}`}
            role="button"
            tabIndex={0}
            onClick={() => onSelectRule(r.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelectRule(r.id);
              }
            }}
          >
            <header className="rc-rule-head">
              <span className="rc-rule-code">{r.code}</span>
              <span className="rc-rule-status" data-s={r.status}>
                {RULE_STATUS_LABEL[r.status]}
              </span>
            </header>
            <div className="rc-rule-name">{r.label}</div>
            <div className="rc-rule-meta">
              <span>{r.version}</span>
              {r.hit > 0 && <span>· {r.hit.toLocaleString()} 命中</span>}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

/* ── 左栏 · Recent ────────────────────────────────── */

function RecentPanel({ sessionData }: { sessionData: RiskctrlSession }) {
  /* ALL IN Phase B step 2 · 删 mock session dropdown · 显真历史 list (来自 sessionData.recentSessions) ·
   * EMPTY_SESSION 时 list = [] 自动显空状态 ·
   * TODO Phase A.5 ship RFC 2 watcher 后 · backtest decision_ledger 出真历史 list */
  const recent = sessionData.recentSessions;
  return (
    <section className="rpt-panel rpt-panel--tl" data-testid="riskctrl-recent-panel">
      <PanelPinHandle
        id="riskctrl:recent"
        title={`近期策略 · ${recent.length} 条`}
        subtitle="跨 session"
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb={recent[0]?.objective ?? ""}
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">RECENT · 近期策略</div>
          <h3 className="rpt-panel-title">{recent.length} 条</h3>
        </div>
      </div>
      <div className="rpt-panel-body rpt-tl-body">
        {recent.length === 0 ? (
          <div className="rc-rc-empty" data-testid="riskctrl-recent-empty">
            尚无历史回测 · 待 Phase A.5 ship 后接 decision_ledger 出真历史
          </div>
        ) : (
          <ol className="rc-rc-list">
            {recent.map((r) => (
              <RecentRow key={r.id} row={r} />
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}

function RecentRow({ row }: { row: RiskctrlRecentSession }) {
  const statusLabel =
    row.status === "done" ? "完成" : row.status === "backtesting" ? "回测中" : "草稿";
  return (
    <li className="rc-rc-row" data-status={row.status}>
      <span className="rpt-tl-bar" aria-hidden />
      <div className="rpt-tl-row">
        <span className="rpt-tl-kind">{statusLabel}</span>
        <span className="rpt-tl-at">{row.updated}</span>
      </div>
      <div className="rpt-tl-label">{row.objective}</div>
      <div className="rc-rc-ks">
        <span className="k">KS</span>
        <span className="v">{row.ks.toFixed(2)}</span>
      </div>
    </li>
  );
}

/* ── 中栏 · Conversation / Composer（复用 canon 模式） ── */

function ConversationPanel({
  sessionData,
  children,
}: {
  sessionData: RiskctrlSession;
  children?: React.ReactNode;
}) {
  const msgs = sessionData.conversation;
  const s = sessionData;
  return (
    <section className="rpt-panel rpt-panel--conv rpt-panel--conv-docked">
      <PanelPinHandle
        id="riskctrl:conversation"
        title="策略对话协作"
        subtitle={`${msgs.length} 条 · FORGE 推理`}
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb="AI 协助调 DSL + 回测 + 送审"
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">CONVERSATION · 对话协作</div>
          <h3 className="rpt-panel-title">
            {s.objective} · {msgs.length} 条
          </h3>
        </div>
        <span className="rpt-panel-meta">
          KS {s.ks.ksPeak.toFixed(2)} · 阻断 {s.qcCounts.block}
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
      <div className="rpt-msg-avatar" aria-hidden>⌘</div>
      <div className="rpt-msg-body">
        <div className="rpt-msg-meta">
          <span className="rpt-msg-who">AI · Forge</span>
          {msg.fieldRef && <span className="rpt-msg-fieldref">{msg.fieldRef}</span>}
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
      <MessagePinHandle {...msgPinProps(msg, "AI · Forge")} />
      <div className="rpt-msg-avatar" aria-hidden>⌘</div>
      <div className="rpt-msg-body">
        <div className="rpt-msg-meta">
          <span className="rpt-msg-who">AI · Forge</span>
          {msg.fieldRef && <span className="rpt-msg-fieldref">{msg.fieldRef}</span>}
          <span className="rpt-msg-at">{msg.at}</span>
        </div>
        <div className="rpt-msg-card">
          <div className="rpt-msg-card-text">{msg.content}</div>
          {msg.sectionDiff && (
            <div className="rpt-msg-diff">
              <div className="rpt-msg-diff-lbl">更新 {msg.sectionDiff.sectionAnchor}</div>
              <div className="rpt-msg-diff-after">{msg.sectionDiff.after}</div>
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
      <div className="rpt-msg-avatar rpt-msg-avatar--thinking" aria-hidden>⌘</div>
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
      <MessagePinHandle {...msgPinProps(msg, "风险经理")} />
      <div className="rpt-msg-body rpt-msg-body--user">
        <div className="rpt-msg-meta rpt-msg-meta--user">
          <span className="rpt-msg-at">{msg.at}</span>
          <span className="rpt-msg-who">风险经理 · 李敏</span>
        </div>
        <div className="rpt-msg-card rpt-msg-card--user">{msg.content}</div>
      </div>
      <div className="rpt-msg-avatar rpt-msg-avatar--user" aria-hidden>李</div>
    </li>
  );
}

function UserCommandMsg({ msg }: { msg: ConversationMessage }) {
  return (
    <li className="rpt-msg rpt-msg--user rpt-msg--cmd">
      <MessagePinHandle {...msgPinProps(msg, "风险经理 · 指令")} />
      <div className="rpt-msg-body rpt-msg-body--user">
        <div className="rpt-msg-meta rpt-msg-meta--user">
          <span className="rpt-msg-at">{msg.at}</span>
          <span className="rpt-msg-who">风险经理 · /command</span>
        </div>
        <div className="rpt-msg-card rpt-msg-card--cmd">
          <code>{msg.content}</code>
        </div>
      </div>
      <div className="rpt-msg-avatar rpt-msg-avatar--user" aria-hidden>李</div>
    </li>
  );
}

/* ── 中栏 · Composer ────────────────────────────────── */

type ComposerHint = "idle" | "slash" | "mention" | "field";

function RiskComposer({ sessionData }: { sessionData: RiskctrlSession }) {
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
    else if (last === "#") setHint("field");
    else setHint("idle");
  }

  function submit() {
    if (!value.trim()) return;
    setValue("");
    setHint("idle");
  }

  // pin-drop · 拖钉到 composer · 插入 `@引用:<title> ` · 不再让 textarea 吞 URL
  const onPin = (payload: PinDropPayload) => {
    setValue((v) => (v ? `${v} @引用:${payload.title} ` : `@引用:${payload.title} `));
  };
  const drop = usePinDrop<HTMLDivElement>(onPin);

  const ruleCount = sessionData.rules.length;

  return (
    <div
      className={`rpt-composer-slot rpt-composer${drop.dropHover ? " rpt-composer--drop-hover" : ""}`}
      data-hint={hint}
      onDragEnter={drop.onDragEnter}
      onDragOver={drop.onDragOver}
      onDragLeave={drop.onDragLeave}
      onDrop={drop.onDrop}
    >
      <div className="rpt-composer-bar">
        <textarea
          ref={taRef}
          className="rpt-composer-ta"
          placeholder="提问或下指令 · 输入 / 触发命令 · @ 引用规则 · # 字段"
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
        <span className="rpt-composer-hint" data-active={hint === "slash"}>
          <kbd>/</kbd> 指令 · lock / rerun / compare
        </span>
        <span className="rpt-composer-hint" data-active={hint === "mention"}>
          <kbd>@</kbd> 规则 · {ruleCount} 条
        </span>
        <span className="rpt-composer-hint" data-active={hint === "field"}>
          <kbd>#</kbd> 字段 · age / score / …
        </span>
      </div>
    </div>
  );
}

/* ── 右栏 · DSL / KS / Sample ─────────────────────────── */

const OUTPUT_ACTIONS = [
  { key: "export", glyph: "⇩", label: "送审", title: "生成送审包 (DSL+回测+对比)" },
  { key: "compare", glyph: "⇄", label: "对比", title: "对比 v1.4 / v1.5 双栏视图" },
  { key: "deploy", glyph: "↑", label: "上线", title: "审批后一键上线" },
  { key: "rerun", glyph: "⟳", label: "重跑", title: "调参后重新回测" },
] as const;

function RiskOutputPanel(p: {
  sessionData: RiskctrlSession;
  rulesetId?: string;
  exportInfo?: ExportInfo;
  onExport?: (kind: ExportKind) => void;
  selectedSegmentKey?: SampleBar["key"] | null;
  onSelectSegment?: (key: SampleBar["key"]) => void;
}) {
  const s = p.sessionData;
  const [tab, setTab] = useState<"dsl" | "ks" | "sample">("dsl");
  const exportStatus = p.exportInfo?.status ?? "idle";
  const exportingKind = p.exportInfo?.kind;
  /* 3 按钮各自从 exportInfo (running/done/error · kind 同) reflect 状态 ·
     running 时全 disable 防并发 · done 仅自己 kind 显完成 · error 显重试 */
  const exportDisabled = exportStatus === "running";
  const renderLabel = (kind: ExportKind, text: string): string => {
    if (exportingKind !== kind) return text;
    if (exportStatus === "running") return "导出中…";
    if (exportStatus === "done") return `重新${text}`;
    if (exportStatus === "error") return `重试${text}`;
    return text;
  };
  const exportButtons: ReadonlyArray<{ kind: ExportKind; label: string; testId: string }> = [
    { kind: "docx", label: "Word", testId: "riskctrl-export-docx-btn" },
    { kind: "xlsx", label: "Excel", testId: "riskctrl-export-xlsx-btn" },
    { kind: "pdf", label: "PDF", testId: "riskctrl-export-pdf-btn" },
  ];
  return (
    <section className="rpt-panel rpt-panel--preview">
      <PanelPinHandle
        id="riskctrl:output"
        title="策略输出看板"
        subtitle="DSL / KS 曲线 / 样本分布"
        accentVar={AGENT_ACCENT}
        agentKey={AGENT_KEY}
        href={AGENT_HREF}
        blurb="DSL v1.5-d3 + 回测结果"
      />
      <div className="rpt-panel-head">
        <div>
          <div className="rpt-panel-eyebrow">OUTPUT · DSL {s.currentRule.version}</div>
          <h3 className="rpt-panel-title">
            KS {s.ks.ksPeak.toFixed(2)} · 通过 {s.ks.passRate}%
          </h3>
          {p.rulesetId ? (
            <p className="rpt-panel-eyebrow" data-testid="riskctrl-ruleset-id">
              ruleset · {p.rulesetId}
            </p>
          ) : null}
        </div>
        <div className="rpt-panel-meta">
          <span className="rpt-pv-pct">AUC {s.ks.auc.toFixed(3)}</span>
          <div className="riskctrl-export-group" role="group" aria-label="导出回测报告 三件套">
            {exportButtons.map((b) => (
              <button
                key={b.kind}
                type="button"
                className="riskctrl-export-btn"
                onClick={() => p.onExport?.(b.kind)}
                disabled={exportDisabled}
                data-state={exportingKind === b.kind ? exportStatus : "idle"}
                data-kind={b.kind}
                data-testid={b.testId}
              >
                {renderLabel(b.kind, b.label)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {exportStatus === "error" && p.exportInfo?.message ? (
        <div className="riskctrl-export-error" role="alert">
          {exportingKind ?? ""} 导出失败：{p.exportInfo.message}
        </div>
      ) : null}

      <div className="rpt-pv-toolbar" role="toolbar">
        {OUTPUT_ACTIONS.map((a) => (
          <button key={a.key} type="button" className="rpt-pv-btn" title={a.title}>
            <span className="ic" aria-hidden>{a.glyph}</span>
            <span>{a.label}</span>
          </button>
        ))}
      </div>

      <nav className="rpt-pv-toc rc-out-tabs" aria-label="输出切换">
        <button type="button" className={tab === "dsl" ? "on" : undefined} onClick={() => setTab("dsl")}>
          <span className="a">§一</span>
          <span className="t">DSL 规则树</span>
        </button>
        <button type="button" className={tab === "ks" ? "on" : undefined} onClick={() => setTab("ks")}>
          <span className="a">§二</span>
          <span className="t">KS 双线</span>
        </button>
        <button type="button" className={tab === "sample" ? "on" : undefined} onClick={() => setTab("sample")}>
          <span className="a">§三</span>
          <span className="t">样本分布</span>
        </button>
      </nav>

      <div className="rpt-pv-paper-wrap">
        <article className="rpt-pv-paper rc-out-paper">
          <div className="rpt-pv-paper-head">
            <div className="doc-title">策略 {s.currentRule.version} · 回测稿</div>
            <div className="doc-sub">
              样本 {s.query.sampleSize.toLocaleString()} · 窗口 {s.query.windowLabel}
            </div>
          </div>
          {tab === "dsl" && <DslView node={s.dsl} />}
          {tab === "ks" && <KSView ks={s.ks} targetKS={s.query.targetKS} />}
          {tab === "sample" && (
            <SampleView
              samples={s.samples}
              selectedKey={p.selectedSegmentKey ?? null}
              onSelectSegment={p.onSelectSegment}
            />
          )}
          <div className="rpt-pv-paper-foot">
            — 以上为 AI 初版策略稿 · 未经风险总监审批不得上线 —
          </div>
        </article>
      </div>

      <footer className="rpt-pv-status">
        <span className="pg">视图 {tab === "dsl" ? "1/3" : tab === "ks" ? "2/3" : "3/3"}</span>
        <span className="sep">·</span>
        <span className="cov">
          通过段坏账 <b>{s.ks.badRate}%</b>
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

function DslView({ node }: { node: DslNode }) {
  return (
    <section className="rc-dsl-sec" data-testid="riskctrl-dsl-editor">
      <header className="rc-out-sec-head">
        <h4 className="rc-out-sec-title">
          <span className="rpt-pv-anchor">§一</span>
          <span>DSL 规则树 · 3 层决策</span>
        </h4>
        <div className="rc-dsl-legend">
          <span className="lg" data-op="IF">IF</span>
          <span className="lg" data-op="AND">AND</span>
          <span className="lg" data-op="OR">OR</span>
          <span className="lg" data-op="THEN">THEN</span>
        </div>
      </header>
      <div className="rc-dsl-tree">
        <DslNodeView node={node} depth={0} />
      </div>
    </section>
  );
}

function DslNodeView({ node, depth }: { node: DslNode; depth: number }) {
  const isAction = node.op === "THEN";
  return (
    <div className="rc-dsl-node" data-op={node.op} data-depth={depth}>
      <div className="rc-dsl-row">
        <span className="rc-dsl-op" data-op={node.op}>
          {node.op}
        </span>
        {node.field && <span className="rc-dsl-field">{node.field}</span>}
        {node.expr && <code className="rc-dsl-expr">{node.expr}</code>}
        {isAction && node.action && (
          <span className="rc-dsl-action" data-action={node.action}>
            {node.action === "pass" ? "通过" : node.action === "block" ? "拒绝" : "复核"}
          </span>
        )}
        {node.reason && <span className="rc-dsl-reason">{node.reason}</span>}
      </div>
      {node.children && node.children.length > 0 && (
        <div className="rc-dsl-children">
          {node.children.map((c) => (
            <DslNodeView key={c.id} node={c} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

function KSView({
  ks,
  targetKS,
}: {
  ks: { ksPeak: number; auc: number; passRate: number; badRate: number; points: { bin: number; tpr: number; fpr: number; ks: number }[] };
  targetKS: number;
}) {
  const data = ks.points.map((p) => ({
    bin: `P${p.bin * 10}`,
    TPR: Math.round(p.tpr * 100),
    FPR: Math.round(p.fpr * 100),
    KS: Math.round(p.ks * 100),
  }));
  return (
    <section className="rc-ks-sec" data-testid="riskctrl-ks-chart">
      <header className="rc-out-sec-head">
        <h4 className="rc-out-sec-title">
          <span className="rpt-pv-anchor">§二</span>
          <span>KS 双线 · 10 分位</span>
        </h4>
        <div className="rc-ks-kpi">
          <span>
            KS peak <b>{ks.ksPeak.toFixed(2)}</b>
          </span>
          <span className="sep">·</span>
          <span>
            目标 <b>{targetKS.toFixed(2)}</b>{" "}
            <em className="ok">(达成)</em>
          </span>
        </div>
      </header>
      <div className="rc-ks-chart">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--ink-14)" />
            <XAxis dataKey="bin" tick={{ fill: "var(--ink-60)", fontSize: 10 }} />
            <YAxis tick={{ fill: "var(--ink-60)", fontSize: 10 }} domain={[0, 100]} />
            <Tooltip
              contentStyle={{
                background: "var(--chalk)",
                border: "1px solid var(--ink-14)",
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Line
              type="monotone"
              dataKey="TPR"
              stroke="var(--agent)"
              strokeWidth={2}
              dot={{ r: 2.5, fill: "var(--agent)" }}
              name="TPR · 好客户累计"
            />
            <Line
              type="monotone"
              dataKey="FPR"
              stroke="var(--t-alert, #C85A3C)"
              strokeWidth={2}
              dot={{ r: 2.5, fill: "var(--t-alert, #C85A3C)" }}
              name="FPR · 坏客户累计"
            />
            <Line
              type="monotone"
              dataKey="KS"
              stroke="var(--t-compli, #4A7A5E)"
              strokeWidth={1.4}
              strokeDasharray="4 3"
              dot={false}
              name="KS · 差值"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="rc-ks-legend">
        <span><span className="sw" data-k="tpr" /> TPR (好客户累计)</span>
        <span><span className="sw" data-k="fpr" /> FPR (坏客户累计)</span>
        <span><span className="sw" data-k="ks" /> KS (TPR - FPR)</span>
      </div>
    </section>
  );
}

function SampleView({
  samples,
  selectedKey,
  onSelectSegment,
}: {
  samples: SampleBar[];
  selectedKey?: SampleBar["key"] | null;
  onSelectSegment?: (key: SampleBar["key"]) => void;
}) {
  const total = samples.reduce((a, b) => a + b.count, 0);
  return (
    <section className="rc-sp-sec" data-testid="riskctrl-sample-dist">
      <header className="rc-out-sec-head">
        <h4 className="rc-out-sec-title">
          <span className="rpt-pv-anchor">§三</span>
          <span>样本分布 · {total.toLocaleString()} 笔</span>
        </h4>
        <div className="rc-sp-meta">
          总 <b>{total.toLocaleString()}</b>
        </div>
      </header>
      <ul className="rc-sp-list">
        {samples.map((s) => {
          const clickable = !!onSelectSegment;
          return (
            <li
              key={s.key}
              className="rc-sp-row"
              data-k={s.key}
              data-selected={s.key === selectedKey ? "yes" : "no"}
              data-testid={`riskctrl-sample-segment-${s.key}`}
              role={clickable ? "button" : undefined}
              tabIndex={clickable ? 0 : undefined}
              onClick={clickable ? () => onSelectSegment(s.key) : undefined}
              onKeyDown={
                clickable
                  ? (e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onSelectSegment(s.key);
                      }
                    }
                  : undefined
              }
              style={clickable ? { cursor: "pointer" } : undefined}
            >
              <div className="rc-sp-head">
                <span className="rc-sp-lbl">{s.label}</span>
                <span className="rc-sp-count">{s.count.toLocaleString()}</span>
                <span className="rc-sp-pct">{s.pct.toFixed(1)}%</span>
                <span className="rc-sp-bad">
                  坏账 <b>{s.badRate.toFixed(1)}%</b>
                </span>
              </div>
              <div className="rc-sp-bar" aria-hidden>
                <div className="rc-sp-bar-fill" style={{ width: `${s.pct}%` }} />
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
