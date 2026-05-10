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

import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react";
// Phase B.1.3 hotfix (PM 2026-05-10) · revert ModePill 双控 · PM 真意是上传 sample 跑真后端
import { DataSourceBadge } from "@/components/shared/DataSourceBadge";
import { useAuthStore } from "@/lib/store/auth-store";
import { type DataSourceKind, normalizeDataSource } from "@/lib/api/_data-source";
import { usePinDrop, type PinDropPayload } from "@/components/composer/use-pin-drop";
import { EvidenceProvider } from "@/components/evidence";

/* Phase B.1 fix #4 · 删 fixtures 假证据 · EvidenceProvider 用 EMPTY array
   · 旧 CREDIT_EVIDENCE.items / unfilledFields = mock 演示数据 · 反 KT §3.6 红线 #3 无证据 claim
   · 真 evidence 数据 backend done envelope.data_sources + dataSources panel 直接消费 · 不靠 fixtures 兜底 */
const EMPTY_EVIDENCE_ITEMS: never[] = [];
const EMPTY_UNFILLED_FIELDS: never[] = [];
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";
import { ActionGate } from "@/components/shell/AuthGate";
import { MessagePinHandle } from "@/components/shell/MessagePinHandle";
import { PanelPinHandle } from "@/components/shell/PanelPinHandle";
import { CustomerSelector } from "@/components/shared/CustomerSelector";
import { LiveFailError, liveFailBannerText, streamSse } from "@/lib/api/_live";
import { normalizeCreditDone } from "./_normalize";
import {
  CREDIT_GLOBAL_STATS,
  CREDIT_MODE_LABEL,
  type CaseRecall,
  type ConversationMessage,
  type CreditMode,
  type CreditProfile,
  type CreditRadarDim,
  type CreditQuery,
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

/* ALL IN Phase B step 2 · per channel 模板 (de79725 EMPTY_SESSION pattern):
   sessionData fallback 用空对象 · 不再 fallback CREDIT_MOCK_SESSIONS_MAP (47 分 D 级假分根因)
   panel 内 .find/.map/.reduce 安全 render · 无虚构企业 · 反 KT §3.6 红线 #1 假 live + #2 假分 */
const EMPTY_SESSION: CreditSession = {
  id: "empty",
  mode: "corp",
  objective: "",
  stage: "",
  updated: "",
  profile: { chips: [], tagline: "" },
  query: {
    id: "",
    customer: "",
    customerCode: "",
    product: "对公经营贷",
    applyAmount: "",
    applyTenor: "",
    purpose: "",
    industry: "",
    updated: "",
  },
  pipeline: [],
  radar: [],
  overallScore: 0,
  decision: "pending",
  limit: {
    applied: 0,
    suggested: 0,
    floor: 0,
    ceiling: 0,
    tenorMonths: 0,
    tenorRange: [0, 0],
    rateBps: 0,
    rateRange: [0, 0],
    rationale: [],
  },
  redLines: [],
  cases: [],
  conversation: [],
  qcCounts: { block: 0, warn: 0, info: 0 },
  recentSessions: [],
  materials: { completeness: 0, missing: "", files: [] },
  dataSources: { summary: "", updated: "", sources: [] },
  evidences: { positive: [], warnings: [], missing: [] },
  /* generateSteps · UI 动画 5 步 · 与数据无关 · ALL IN 后改为"等待 / 处理中"措辞反映真实路径 */
  generateSteps: [
    { label: "等待 Agent6 报告 handoff", pct: 22 },
    { label: "拉取 ReportJSON · 注入企业画像", pct: 48 },
    { label: "LLM 评分 · 红线检查 · 案例召回", pct: 76 },
    { label: "决策建议生成中", pct: 96 },
    { label: "综合判断完成", pct: 100 },
  ],
};

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

/* Phase B.2 (PM 2026-05-10 真意 reframe) · 内置 sample 映射
   · /api/credit/demo/run 真后端跑 · 输入来自 demo_data/agent_credit/<sample_id>.json (v4 ReportJSON shape)
   · small_business 共用对公 sample (ALL IN Phase B 无小微专属 sample · 后端 _STAGE_TO_SEGMENT 对公评分模型兼容) */
const MODE_TO_SAMPLE_ID: Record<CreditMode, string> = {
  corp: "corp_dingsheng_trade",
  small: "corp_dingsheng_trade",
  retail: "retail_lisi_education",
};

/* Phase B.2 主活 B · sample 显示名 (CTA 副标题用 · 让用户明确点了会跑哪个 sample) */
const SAMPLE_DISPLAY_NAME: Record<CreditMode, string> = {
  corp: "鼎盛商贸 (对公 · 建材批发 · 关联交易高)",
  small: "鼎盛商贸 (小微复用对公 · 抵押权重提升)",
  retail: "李四 (对私 · 教育行业 · FICO 式)",
};

/* Phase B.2 主活 B (PM 2026-05-10 真意 reframe) · 输入形态切换
   · "real": 真实数据 · 从 Agent6 报告起决策 (handoff archive · LLM 真跑)
   · "demo": 演示数据 · 一键加载内置 sample (corp/retail · LLM 真跑 · 输入是 sample)
   · 两形态共点: 后端 LLM/scoring/rule/case/ledger 全真 · 区别仅"输入来源"
   · 不是 ModePill (那是切假数据 · 已 revert) · 是显式输入来源 toggle */
type CreditInputMode = "real" | "demo";

const STAGE_TAB_DESCRIPTION: Record<CreditMode, string> = {
  corp: "对公授信 · 50-5000 万 · 4 维评分 + 30 红线",
  small: "普惠 / 小微 · 10-500 万 · 抵押权重高 · 阈值放宽 5 分",
  retail: "对私 / 零售 · 5-500 万 · FICO 式 800/760/700/680 评级",
};

export default function CreditWorkspace() {
  /* ALL IN Phase B · workspace-state-protocol §2 · 3 gate state model (selectedSession 删 · 历史 session 已下架)
     (1) started · (2) liveData · (3) selectedCandidate · 加 mode 独立 state (3 板块 stage_tab tab 切换)
     sessionData = liveData ?? EMPTY_SESSION · panel 单点派生 · 不 fallback mock */
  const [started, setStarted] = useState<boolean>(false);
  const [mode, setModeState] = useState<CreditMode>("corp");
  const [liveData, setLiveData] = useState<CreditSession | null>(null);
  /* 件 #2 · data_source SSOT 真消费 (per Q-054 risk #1) · ALL IN 默认 "live" (单一真路径)
     · LiveFailError → "mock_fallback" 降级标 (trust model 一级 · 非 silent fallback 假数据) */
  const [currentDataSource, setCurrentDataSource] = useState<DataSourceKind>("live");
  const [selectedCandidate, setSelectedCandidate] = useState<string | null>(null);

  /* Phase B.2 主活 B · 输入形态 toggle · 真实 default (per onboarding B2) · demo 选了显内置 sample CTA */
  const [inputMode, setInputMode] = useState<CreditInputMode>("real");

  /* Phase B.1.3 (PM 2026-05-10) · revert ModePill 双控 · 错设计 · 演示=上传sample真后端 */

  /* ALL IN Phase B · sessionData 不 fallback mock · 改 EMPTY_SESSION (per channel 模板 de79725)
     panel 内 .find/.map/.reduce 安全 render · 无虚构企业 · 反 KT §3.6 红线 #1 + #2 */
  const sessionData: CreditSession = liveData ?? EMPTY_SESSION;

  /* alias · minimize churn through 1800 lines */
  const session = sessionData;

  /* ALL IN Phase B step 6 · setMode 干净切换 3 板块 (corp/small/retail)
     · 切板块后所有 per-entity 状态全清 (live / drawer / error / handoff banner)
     · per-entity 评分维度 (radar 4 axis dict) 由 _normalize.RADAR_AXIS_LABEL 派生:
       - corp/small_business: financial / industry / operational / guarantee
       - retail: ability / willingness / stability / collateral (FICO 式)
     · 用户切板块后必须点 CTA 重新起决策 · 不靠 mock data 自动派生 */
  const setMode = useCallback((newMode: CreditMode) => {
    setModeState(newMode);
    setLiveData(null);
    setSelectedCandidate(null);
    setDecisionError(null);
    setHandoffSource(null);
  }, []);

  /* ESC 关 case detail drawer (Step 10 · selectedCandidate gate) */
  useEffect(() => {
    if (!selectedCandidate) return;
    function onKey(e: globalThis.KeyboardEvent) {
      if (e.key === "Escape") setSelectedCandidate(null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedCandidate]);

  /* 派生 selected case data · 从 sessionData.cases 找 (live or mock 单源) */
  const selectedCandidateData: CaseRecall | null = selectedCandidate
    ? sessionData.cases.find((c) => c.id === selectedCandidate) ?? null
    : null;

  const [tab, setTab] = useState<OutputTab>("radar");

  // CTA 生成授信辅助 · 动态进度条状态（纯前端 mock · 5 步 450ms · UI 动画 · 与 4 gate 不冲突）
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
  /* PB#5 · AbortController · SSE 防僵尸连接 · 3 SSE callsite 共用 (sequential · 不并发) */
  const abortRef = useRef<AbortController | null>(null);
  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);
  /* 2026-04-23 · credit 也统一空态 · startGenerate 最后一步触发 · 数据显现 */
  const [scanned, setScanned] = useState(false);

  /* runDecision SSE 状态 · Step 7 streamSse 收编后会进一步精简 */
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

  /* ALL IN Phase B step 3 · runDecision (preset fallback) 删除
     · 旧路径 mock=true / preset_name=presetByMode 都是 mock 残留 · 不再保留
     · 真路径单一: runDecisionWithAgent6Handoff (Agent6 → ReportJSON → /decision live SSE)
     · retry button 也走 runDecisionWithAgent6Handoff · 反 KT §3.6 红线 #1 假 live */

  /* primary CTA · Cat 0 北极星核心: Agent6 handoff → 注入 enterprise_profile → 起决策
     Step 9 · 2026-04-29 worker-A4-credit · per agent-handoff-schemas §2 + spec §3 触发源 2
     Phase A: 先拉 /api/credit/reports/sessions list · 取首条 (UI picker 留 Phase B)
     Phase B: 弹 modal 让 RM 在 N 个完成报告中挑选 */
  const [handoffSource, setHandoffSource] = useState<{
    sessionId: string;
    reportId: string;
    companyName: string;
    industry: string | null;
    generatedAt: string;
    stageTab: "corporate" | "small_business" | "retail";
  } | null>(null);

  async function runDecisionWithAgent6Handoff() {
    if (decisionRunning) return;
    setDecisionError(null);
    const apiBase =
      (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE) || "";
    try {
      // 1. 拉 Agent6 已完成报告 list (Phase A: demo_data fixtures · Phase B: 真 archive)
      const listRes = await fetch(`${apiBase}/api/credit/reports/sessions?status=done`);
      if (!listRes.ok) throw new Error(`HTTP ${listRes.status}`);
      const listData = (await listRes.json()) as {
        sessions: Array<{
          session_id: string; report_id: string; company_name: string;
          segment: string; industry: string | null; generated_at: string;
        }>;
        count: number;
      };
      if (listData.count === 0) {
        setDecisionError("无可用 Agent6 报告 · 请先在 /archive/report 完成尽调或选演示模式");
        return;
      }
      // Phase A: 按当前 mode 自动 match · 否则取首条
      const segmentForMode: Record<CreditMode, string> = {
        corp: "corporate", small: "corporate", retail: "retail",
      };
      const targetSeg = segmentForMode[mode];
      const picked = listData.sessions.find((s) => s.segment === targetSeg)
                  ?? listData.sessions[0];

      // 2. 拉 ReportJSON
      const handoffRes = await fetch(`${apiBase}/api/credit/handoff/from_report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: picked.session_id }),
      });
      if (!handoffRes.ok) throw new Error(`handoff HTTP ${handoffRes.status}`);
      const handoff = (await handoffRes.json()) as {
        session_id: string;
        report_id: string;
        company_name: string;
        industry: string | null;
        generated_at: string;
        enterprise_profile: Record<string, unknown>;
        ready_for_decision: boolean;
        warning: string | null;
      };

      // 3. 设 banner state · 起决策
      const stageTab = MODE_TO_STAGE_TAB[mode];
      setHandoffSource({
        sessionId: handoff.session_id,
        reportId: handoff.report_id,
        companyName: handoff.company_name,
        industry: handoff.industry,
        generatedAt: handoff.generated_at,
        stageTab,
      });
      if (handoff.warning) {
        setDecisionError(`⚠️ ${handoff.warning}`);
      }

      // 4. 真起决策 · enterprise_profile 注入 body.report_json
      setStarted(true);
      setDecisionRunning(true);
      setLiveAdvice(null);
      setDecisionId(null);
      const fallbackSession = sessionData;
      abortRef.current?.abort();
      const ac = new AbortController();
      abortRef.current = ac;
      try {
        await streamSse(
          `${apiBase}/api/credit/decision`,
          {
            stage_tab: stageTab,
            mock: false,
            report_json: handoff.enterprise_profile,
          },
          (sseEvt) => {
            if (ac.signal.aborted) return;
            const data = sseEvt.data as {
              event?: string; stage?: string; decision_id?: string;
              payload?: Record<string, unknown>; message?: string;
            };
            if (sseEvt.type === "stage" && data.stage === "advising_done" && data.payload) {
              setLiveAdvice(data.payload);
              setScanned(true);
            }
            if (sseEvt.type === "decision_cached" && data.decision_id) {
              setDecisionId(data.decision_id);
            }
            if (sseEvt.type === "done") {
              setLiveData(normalizeCreditDone(
                data as Record<string, unknown>,
                fallbackSession,
              ));
              setSelectedCandidate(null);
              setScanned(true);
              /* ALL IN Phase B step 3 · data_source SSOT · live 成功标 */
              const rawDs = (data as Record<string, unknown>).data_source;
              setCurrentDataSource(rawDs ? normalizeDataSource(rawDs) : "live");
            }
          },
          { signal: ac.signal },
        );
      } catch (e) {
        if (e instanceof DOMException && e.name === "AbortError") return;
        throw e;
      } finally {
        if (!ac.signal.aborted) setDecisionRunning(false);
      }
    } catch (err) {
      const msg = err instanceof LiveFailError
        ? liveFailBannerText(err, "Credit handoff/from_report")
        : err instanceof Error ? err.message : String(err);
      setDecisionError(msg);
      /* ALL IN Phase B step 3 · live 失败 → trust model 一级降级标 (per Q-054 risk #1) */
      setCurrentDataSource("mock_fallback");
      setDecisionRunning(false);
    }
  }

  /* Phase B.2 (PM 2026-05-10 真意 reframe) · 一键运行示例 · 调 /api/credit/demo/run 真后端跑
     · 旧 (B.1.5 hotfix): body { stage_tab } · 后端 yield fixture · setCurrentDataSource("mock_forced")
     · 新 (B.2): body { sample_id } · 后端真调 LLM/scoring/rule/case/ledger · setCurrentDataSource("live")
     · 演示 = 上传 sample 跑真后端 · 不是切假数据 (per docs/onboarding/B2-phase-b2-dispatch.md)
     · LLM fail / API key 缺 → LiveFailError → trust model 一级降级标 mock_fallback (banner 显 · 不 silent) */
  async function runDemoSample() {
    if (decisionRunning) return;
    setDecisionError(null);
    const apiBase =
      (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE) || "";
    setStarted(true);
    setDecisionRunning(true);
    setLiveAdvice(null);
    setDecisionId(null);
    const fallbackSession = sessionData;
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    try {
      await streamSse(
        `${apiBase}/api/credit/demo/run`,
        { sample_id: MODE_TO_SAMPLE_ID[mode] },
        (sseEvt) => {
          if (ac.signal.aborted) return;
          const data = sseEvt.data as Record<string, unknown>;
          if (sseEvt.type === "done") {
            setLiveData(normalizeCreditDone(data, fallbackSession));
            setSelectedCandidate(null);
            setScanned(true);
            /* Phase B.2 · 真后端跑 = live (LLM/scoring/rule/case/ledger 全真) · 输入是内置 sample 但结果真 */
            setCurrentDataSource("live");
          }
        },
        { signal: ac.signal },
      );
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      const msg = e instanceof LiveFailError
        ? liveFailBannerText(e, "Credit demo/run")
        : e instanceof Error ? e.message : String(e);
      setDecisionError(msg);
      setCurrentDataSource("mock_fallback");
    } finally {
      if (!ac.signal.aborted) setDecisionRunning(false);
    }
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
  /* Step 9 · Cat 0 北极星 · handoff source banner (Agent6 → Agent3 真消费证据) */
  const handoffBanner = handoffSource ? (
    <div
      role="status"
      data-testid="credit-handoff-banner"
      className="credit-handoff-banner"
    >
      <span className="credit-handoff-banner__icon" aria-hidden>📋</span>
      <span className="credit-handoff-banner__text">
        已从 <b>Agent6</b> 加载 <b>{handoffSource.companyName}</b>
        {handoffSource.industry ? <span> · {handoffSource.industry}</span> : null}
        {handoffSource.generatedAt ? <span> · 生成于 {handoffSource.generatedAt}</span> : null}
        {" · 板块 "}
        <code data-testid="credit-handoff-stage-tab">{handoffSource.stageTab}</code>
      </span>
      <button
        type="button"
        className="credit-handoff-banner__dismiss"
        onClick={() => setHandoffSource(null)}
        aria-label="关闭 handoff 提示"
      >
        ×
      </button>
    </div>
  ) : null;

  /* B-banner · workspace 顶部统一错误条 · started 与 !started 两分支共用
     · Phase B.2 step 4 主活 C: retry 按 inputMode 路由 (real → handoff · demo → demoSample)
     · 避免 demo 模式失败后 retry 跳真 handoff 路径 (input 形态错位) */
  const creditTopBanner = decisionError ? (
    <div
      role="alert"
      data-testid="credit-error-banner"
      className="credit-error-banner"
    >
      <span className="credit-error-banner__icon" aria-hidden>⚠</span>
      <span className="credit-error-banner__text">
        <b>{inputMode === "demo" ? "演示运行失败" : "决策操作失败"}</b>
        <span className="credit-error-banner__detail">{decisionError}</span>
      </span>
      <button
        type="button"
        className="credit-error-banner__retry"
        data-testid="credit-error-retry"
        onClick={() => {
          setDecisionError(null);
          if (inputMode === "demo") {
            runDemoSample();
          } else {
            runDecisionWithAgent6Handoff();
          }
        }}
      >
        重试 {inputMode === "demo" ? "(演示)" : "(真实)"}
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
        items={EMPTY_EVIDENCE_ITEMS}
        unfilledFields={EMPTY_UNFILLED_FIELDS}
      >
        <div
          className="rpt-workspace credit-empty-root"
          data-credit-mode={mode}
          data-scanned="no"
          data-credit-started="no"
        >
          {handoffBanner}
      {creditTopBanner}
          <CreditEmptyState
            mode={mode}
            onModeChange={setMode}
            inputMode={inputMode}
            onInputModeChange={setInputMode}
            onPrimary={() => runDecisionWithAgent6Handoff()}
            onRunDemo={() => runDemoSample()}
            decisionRunning={decisionRunning}
            decisionError={decisionError}
          />
        </div>
      </EvidenceProvider>
    );
  }

  return (
    <EvidenceProvider
      items={EMPTY_EVIDENCE_ITEMS}
      unfilledFields={EMPTY_UNFILLED_FIELDS}
    >
    <div
      className="rpt-workspace"
      data-credit-mode={mode}
      data-credit-started="yes"
      data-scanned={scanned ? "yes" : "no"}
    >
      {handoffBanner}
      {creditTopBanner}
      {/* Phase B.2 step 4 主活 C · weeklyProcessed mock "63" 假 stat → placeholder
         · 反不可 GO 条件 #7 (评分都一样 假分残留) + 红线 #2 假分
         · 真路径 = 接 backend metrics endpoint (跨 agent stats SSOT · 不在本 worker 域)
         · ALL IN Phase B 暂留 "—" placeholder · 不显假"63" 误导客户经理 */}
      <TopBar
        mode={mode}
        onModeChange={setMode}
        sessionsCount="—"
      />
      {/* Phase B.1.3 · DataSourceBadge SSOT trust 标记保留 · ModePill 双控删
         · Phase B.2 step 4 主活 C · inline style → CSS class (per CLAUDE.md "203 inline_style 重灾区") */}
      <div className="credit-data-source-wrap">
        <DataSourceBadge kind={currentDataSource} testId="credit-data-source-badge" size="sm" />
      </div>

      {/* Phase B.2 step 7 · 信息密度 · started=true && !liveData && !running && !error 时
         显示 idle hint (空白引导提示) · 大空白填示例 · 反 PM 截图痛点 #2 "大面积空白"
         · 不重叠 creditTopBanner (decisionError 显另一 banner) · 不阻 5 panel 渲染骨架 */}
      {!liveData && !decisionRunning && !decisionError ? (
        <div
          className="credit-idle-hint"
          role="status"
          data-testid="credit-idle-hint"
          aria-label="等待决策结果"
        >
          <span className="credit-idle-hint__icon" aria-hidden>📋</span>
          <span className="credit-idle-hint__text">
            <b>等待决策结果</b>
            <span className="credit-idle-hint__detail">
              决策完成后此处显示 4 维评分 · 红线明细 · 相似案例 · 决策建议书 (live LLM)
            </span>
          </span>
          <button
            type="button"
            className="credit-idle-hint__back"
            data-testid="credit-idle-hint-back"
            onClick={() => {
              setStarted(false);
              abortRef.current?.abort();
            }}
          >
            重选形态
          </button>
        </div>
      ) : null}

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
          {/* ALL IN Phase B step 1 cleanup (per channel 模板 de79725 + 1c6aa34):
              - DELETE QueryPanel (PRD verbatim "Agent3 输入 = Agent6 ReportJSON · 不需 query")
              - KEEP MaterialsPanel + DataSourcesPanel (PRD "多源补充")
              - DELETE RecentPanel (历史 session mock UI · ALL IN 真路径走 Agent6 handoff) */}
          <MaterialsPanel data={session.materials} />
          <DataSourcesPanel data={session.dataSources} />
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
            onSelectCase={setSelectedCandidate}
          />
        </section>
      </div>

      <BottomBar
        evidences={session.evidences}
        pipeline={session.pipeline}
        generateSteps={session.generateSteps}
        progress={progress}
      />
      {/* W-CF-A2 · 决策完成 advice + Word 导出 (live SSE 路径)
          Sprint 4 D1 cleanup (per Codex R3 critical · PM 报"无意义/重复"):
          - DELETE ev-claim-summary (重复 OutputPanel evidence)
          - DELETE UnfilledFields (跨 Agent 全局贴片 · 不是 PRD Dashboard 主线)
          - DELETE RiskRadarPreview (注释 verbatim "仅可视 demo · 不替代既有 RadarChart" · 第 3 处 radar 重叠)
          - DELETE EvidenceTrail (跨 Agent 全局贴片) */}
      <CreditDecisionAdvicePanel
        liveAdvice={liveAdvice}
        decisionId={decisionId}
        decisionRunning={decisionRunning}
        decisionError={decisionError}
        stageTab={MODE_TO_STAGE_TAB[mode]}
      />
      {/* Step 10 · selectedCandidate gate · case detail drawer (workspace-state-protocol §2 #4) */}
      {selectedCandidateData ? (
        <CaseDetailDrawer
          caseRow={selectedCandidateData}
          onClose={() => setSelectedCandidate(null)}
        />
      ) : null}
    </div>
    </EvidenceProvider>
  );
}

/* RiskRadarPreview deleted · Sprint 4 D1 cleanup
   · 注释 verbatim "仅可视 demo · 不替代既有 RadarChart" 自认是第 3 处 radar 重叠
   · 与 DashboardBand + OutputPanel radar Tab 重复 · per PRD v2.0 "1 Dashboard + 1 卡片" 仅保 OutputPanel radar */

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
        {/* Sprint 4 D1 Atomic 3 (per Codex R1 critical fix · 4/14 PRD verbatim "1 Dashboard"):
            DELETE radar dims mini list (与 OutputPanel radar tab 重复 · DashboardBand 4 cards 已含 overall) */}
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
          {/* Sprint 4 D1 Atomic 3 (per Codex R1 critical · PM 报"重复"):
              DELETE radar mini metrics in Hero left col (与 OutputPanel radar tab + DashboardBand 重复)
              保留 chips + tagline (banker 上下文) + 右 ScoreRing (唯一 focal point) */}
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
          {/*
           * Phase B Sprint 3 sub-PR 2 V2-FIX (2026-05-05 · per Codex review critical 2):
           * "生成授信辅助" = credit.invoke action · ActionGate row-level gate ·
           * RM credit.read-only → fallback 显仅查看 badge · 不可发起 (per Q-052 #8 收窄)
           * credit_officer / risk_manager / admin → 真 button · 可调
           */}
          <ActionGate
            agent="credit"
            action="invoke"
            fallback={
              <span
                className="credit-hero__cta credit-hero__cta--readonly"
                data-testid="credit-invoke-readonly"
                aria-disabled="true"
                role="note"
              >
                仅查看 · 无 invoke 权限 (联系审贷员)
              </span>
            }
          >
            <button
              type="button"
              className="credit-hero__cta"
              onClick={p.onGenerate}
              disabled={p.progress.running}
            >
              {p.progress.running ? "生成中…" : "生成授信辅助"}
            </button>
          </ActionGate>
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

/* ─────────── LEFT · RecentPanel 已删 (ALL IN Phase B step 1 · 历史 session mock UI 残留) ─────────── */

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
  // pin-drop · 拖钉到 composer · 插入 `@引用:<title> ` · 不再让 textarea 吞 URL
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
  onSelectCase?: (id: string) => void;
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
        {p.tab === "cases" ? <CasesView cases={p.cases} onSelect={p.onSelectCase} /> : null}
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

function CasesView({
  cases,
  onSelect,
}: {
  cases: CaseRecall[];
  onSelect?: (id: string) => void;
}) {
  return (
    <div className="cr-cs">
      <div className="cr-cs__ttl">相似案例召回 · {cases.length} 条（相似度 ≥ 0.75）</div>
      <ul className="cr-cs__list">
        {cases.map((c) => (
          <li
            key={c.id}
            className="cr-cs__item"
            data-decision={c.decision}
            data-testid="credit-case-row"
            data-case-id={c.id}
            role={onSelect ? "button" : undefined}
            tabIndex={onSelect ? 0 : -1}
            onClick={onSelect ? () => onSelect(c.id) : undefined}
            onKeyDown={onSelect ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelect(c.id);
              }
            } : undefined}
          >
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

/* CaseDetailDrawer · Step 10 · selectedCandidate gate (workspace-state-protocol §2 #4)
   ESC 关 (parent useEffect) · click backdrop 关 · A11y dialog */
function CaseDetailDrawer({
  caseRow,
  onClose,
}: {
  caseRow: CaseRecall;
  onClose: () => void;
}) {
  return (
    <div
      className="credit-case-drawer__backdrop"
      data-testid="credit-case-drawer-backdrop"
      onClick={onClose}
    >
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={`案例详情 · ${caseRow.name}`}
        data-testid="credit-case-drawer"
        data-case-id={caseRow.id}
        data-decision={caseRow.decision}
        className="credit-case-drawer"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="credit-case-drawer__hdr">
          <h3 className="credit-case-drawer__name">{caseRow.name}</h3>
          <span className="credit-case-drawer__decision-chip">
            {DECISION_LABEL[caseRow.decision]}
          </span>
          <button
            type="button"
            onClick={onClose}
            aria-label="关闭"
            className="credit-case-drawer__close"
            data-testid="credit-case-drawer-close"
          >
            ×
          </button>
        </header>
        <section className="credit-case-drawer__body">
          <dl className="credit-case-drawer__dl">
            <dt>相似度</dt>
            <dd>
              <span className="credit-case-drawer__sim">
                {(caseRow.similarity * 100).toFixed(0)}%
              </span>
            </dd>
            <dt>申请额度</dt>
            <dd>{caseRow.amount}</dd>
            <dt>决议</dt>
            <dd data-testid="credit-case-drawer-decision">
              {DECISION_LABEL[caseRow.decision]}
            </dd>
            <dt>说明</dt>
            <dd className="credit-case-drawer__note">{caseRow.note}</dd>
            {caseRow.tags.length > 0 ? (
              <>
                <dt>标签</dt>
                <dd>
                  {caseRow.tags.map((t) => (
                    <span key={t} className="credit-case-drawer__tag">{t}</span>
                  ))}
                </dd>
              </>
            ) : null}
          </dl>
        </section>
        <footer className="credit-case-drawer__ftr">
          <span className="credit-case-drawer__hint">ESC / 点背景 关闭</span>
        </footer>
      </aside>
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
  inputMode: CreditInputMode;       // Phase B.2 · "real" | "demo"
  onInputModeChange: (im: CreditInputMode) => void;
  onPrimary: () => void;       // 起决策 (真接 backend SSE · cat 0 北极星 · Agent6 handoff)
  onRunDemo?: () => void;      // Phase B.2 · 一键运行示例 · sample 跑 (真后端 LLM)
  decisionRunning: boolean;
  decisionError: string | null;
}) {
  const stageTab = MODE_TO_STAGE_TAB[p.mode];
  const stageDesc = STAGE_TAB_DESCRIPTION[p.mode];
  const sampleName = SAMPLE_DISPLAY_NAME[p.mode];
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

      {/* Phase B.2 主活 B (PM 2026-05-10 真意 reframe) · 输入形态切换 toggle
         · 真实 default (从 Agent6 真产物起决策) / 演示 (内置 sample · 真后端跑)
         · 共点: 后端 LLM/scoring/rule/case/ledger 全真 · 区别仅"输入来源"
         · 不是 ModePill (切假数据 · 已 revert) · 是显式输入形态 toggle */}
      <div
        className="credit-empty__input-mode"
        role="tablist"
        aria-label="输入形态切换"
        data-testid="credit-input-mode-toggle"
      >
        <span className="credit-empty__input-mode-lbl">形态</span>
        <button
          type="button"
          role="tab"
          aria-selected={p.inputMode === "real"}
          className="credit-empty__input-mode-tab"
          data-active={p.inputMode === "real" ? "yes" : "no"}
          data-testid="credit-input-mode-real"
          onClick={() => p.onInputModeChange("real")}
          disabled={p.decisionRunning}
        >
          真实数据
          <span className="credit-empty__input-mode-sub">从 Agent6 报告起决策</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={p.inputMode === "demo"}
          className="credit-empty__input-mode-tab"
          data-active={p.inputMode === "demo" ? "yes" : "no"}
          data-testid="credit-input-mode-demo"
          onClick={() => p.onInputModeChange("demo")}
          disabled={p.decisionRunning || !p.onRunDemo}
        >
          演示数据
          <span className="credit-empty__input-mode-sub">内置 sample · 真后端跑</span>
        </button>
      </div>

      {/* Phase B.2 · CTA 按 inputMode 条件渲染 (单 CTA · 不再并列双按钮 · 减少认知负担) */}
      <section className="credit-empty__cta-row" aria-label="主 CTA">
        {p.inputMode === "real" ? (
          <button
            type="button"
            className="credit-empty__cta credit-empty__cta--primary"
            data-testid="credit-decision-cta"
            data-cta="primary"
            onClick={p.onPrimary}
            disabled={p.decisionRunning}
          >
            <span className="credit-empty__cta-rank">真实数据 · 主操作</span>
            <span className="credit-empty__cta-title">
              {p.decisionRunning ? "决策中…" : "从 Agent6 报告起决策"}
            </span>
            <span className="credit-empty__cta-sub">
              选已完成尽调报告 · 自动注入企业画像 · LLM SSE 决策 (cat 0 北极星)
            </span>
          </button>
        ) : (
          <button
            type="button"
            className="credit-empty__cta credit-empty__cta--primary"
            data-testid="credit-demo-cta"
            data-cta="demo"
            onClick={p.onRunDemo}
            disabled={p.decisionRunning || !p.onRunDemo}
          >
            <span className="credit-empty__cta-rank">演示数据 · 内置 sample</span>
            <span className="credit-empty__cta-title">
              {p.decisionRunning ? "运行中…" : `一键运行 · ${sampleName}`}
            </span>
            <span className="credit-empty__cta-sub">
              加载内置 ReportJSON · 真后端 LLM/评分/红线/案例/ledger 全真跑 · 演示 ≠ 假数据
            </span>
          </button>
        )}
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
  /* Step 11 · 2026-04-29 worker-A4-credit · 替 console.error 静默 (cat 13)
     export_docx 失败 → banner 显式 + retry/dismiss · banner 文案区分 4xx/5xx/network */
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportRunning, setExportRunning] = useState(false);

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
    setExportError(null);
    setExportRunning(true);
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
      if (!res.ok) {
        // 解 backend 4xx/5xx detail (per agent_credit/api.py error envelope)
        const text = await res.text().catch(() => "");
        let msg = `HTTP ${res.status}`;
        try {
          const parsed = JSON.parse(text) as { detail?: { error?: { code?: string; message?: string } } };
          if (parsed.detail?.error?.message) {
            msg = `${parsed.detail.error.code ?? `HTTP ${res.status}`}: ${parsed.detail.error.message}`;
          }
        } catch {
          if (text) msg = `${msg} · ${text.slice(0, 120)}`;
        }
        throw new Error(msg);
      }
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
      // 替原 console.error 静默 (cat 13) · banner 显式 + 用户可 retry/dismiss
      setExportError(err instanceof Error ? err.message : String(err));
    } finally {
      setExportRunning(false);
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
          <div className="credit-advice-live__actions">
            <button
              type="button"
              className="credit-advice-live__export"
              data-testid="credit-export-docx-btn"
              onClick={downloadDocx}
              disabled={(!p.decisionId && !p.liveAdvice) || exportRunning}
            >
              {exportRunning ? "导出中…" : "导出决策建议书 (.docx)"}
            </button>
            {/* Sprint 4 D1 Atomic 4 · Agent6 回写 CTA (per PRD v2.0 verbatim:
                "Agent3 的决策意见反过来可回写到 Agent6 报告的审批意见章节"
                Codex R3 critical fix 指引: production 缺此 CTA · 必加) */}
            <button
              type="button"
              className="credit-advice-live__writeback"
              data-testid="credit-writeback-agent6-btn"
              onClick={() => {
                // TODO Sprint 4 D2: wire to /api/report/writeback_decision endpoint
                // 现 placeholder · 用户视角验证 CTA 显示位置正确
                // ref: PRD_授信决策辅助智能体_v2.0.md "Agent3 决策回写 Agent6"
                alert("回写 Agent6 审批意见 · Sprint 4 D2 接 endpoint (现 placeholder)");
              }}
              disabled={!p.decisionId && !p.liveAdvice}
              title="回写 Agent6 报告的审批意见章节"
            >
              ↩ 回写 Agent6 报告
            </button>
          </div>
          {/* Step 11 · cat 13 fix · export 失败 banner (替 console.error 静默) */}
          {exportError ? (
            <div
              role="alert"
              data-testid="credit-export-error-banner"
              className="credit-advice-live__export-err"
            >
              <span className="credit-advice-live__export-err-icon" aria-hidden>⚠</span>
              <span className="credit-advice-live__export-err-text">
                <b>导出失败</b>
                <span className="credit-advice-live__export-err-detail">{exportError}</span>
              </span>
              <button
                type="button"
                className="credit-advice-live__export-err-retry"
                onClick={downloadDocx}
                data-testid="credit-export-retry"
              >
                重试
              </button>
              <button
                type="button"
                className="credit-advice-live__export-err-dismiss"
                onClick={() => setExportError(null)}
                aria-label="关闭导出错误提示"
                data-testid="credit-export-dismiss"
              >
                ×
              </button>
            </div>
          ) : null}
        </div>
      ) : p.decisionRunning ? (
        <div className="credit-advice-live__loading">LLM 决策流式生成中…</div>
      ) : null}
    </section>
  );
}
