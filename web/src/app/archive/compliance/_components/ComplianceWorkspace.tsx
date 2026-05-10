"use client";

/**
 * /archive/compliance · Agent 05 LEDGER · 对话式合规扫描 workspace（canon 横向套 2026-04-21 H5）
 * 左：query + policies + docs + pipeline + recent /
 * 中：对话 + ComplianceComposer /
 * 右：冲突矩阵（doc × clause）· 扫描漏斗 · 政策 timeline 三切换
 * 壳类：.v-archive--canon[data-agent="compliance"] → --agent = var(--t-compli) 墨绿
 */

import { Fragment, useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { usePinDrop, type PinDropPayload } from "@/components/composer/use-pin-drop";
import {
  type ComplianceDoneEnvelope,
  exportDocx as exportDocxApi,
  LiveFailError,
  runMatrixCheck,
  runPolicyScan,
} from "@/lib/api/compliance";
import {
  COMPLIANCE_GLOBAL_STATS,
  COMPLIANCE_SESSION,
  type CellDetail,
  type ClauseMapRow,
  type ComplianceQuery,
  type ComplianceRecentSession,
  type ComplianceSession,
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
import { EvidenceProvider } from "@/components/evidence";
import { DataSourceBadge } from "@/components/shared/DataSourceBadge";
import { type DataSourceKind, normalizeDataSource } from "@/lib/api/_data-source";

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

/* workspace-state-protocol §2 · view tab (compliance-only · 衍生 UI state · 不在 4 gate)
   per agent-compli-spec §7.1 + draft §K compliance 三视角无状态污染 */
type ViolationView = "by_violation" | "by_clause" | "by_event";

type TriggerSource = "primary_scan" | "secondary_template";

type ExportInfo = {
  status: "idle" | "running" | "done" | "error";
  message?: string;
};

/* workspace-state-protocol §2 · 3 gate state (ALL IN Phase B step 1-2 · 2026-05-09)
   gate 1 = started · gate 2 = liveData · gate 3 = selectedViolationId
   sessionData = liveOverlay(EMPTY_SESSION, liveData) · 不再 fallback mock 模板 (step 2)
   started=true && liveData=null → 渲染 EMPTY · 5 panel 显空骨架 */
const EMPTY_SESSION: ComplianceSession = {
  id: "EMPTY",
  objective: "",
  stage: "",
  updated: "",
  query: {
    id: "",
    policyTitle: "",
    policyCode: "",
    issuer: "",
    issueDate: "",
    effectiveDate: "",
    clauseCount: 0,
    scope: "",
    updated: "",
  },
  policies: [],
  docs: [],
  pipeline: [],
  matrix: [],
  clauses: [],
  conflicts: [],
  funnel: [],
  timeline: [],
  conversation: [],
  qcCounts: { block: 0, warn: 0, info: 0 },
  recentSessions: [],
  innerPolicyUploads: [],
  outerPolicyUploads: [],
  revisionAdvices: [],
  cellDetails: {},
};

/* normalizeComplianceBackendDone · 把 done envelope (panels.violations / recommendations) overlay 到 EMPTY 基板
   - ALL IN step 2 (2026-05-09): tplFallback 不再当 visual 模板填补 · 仅作 schema 兜底 (留 hero/query/timeline 等 step 4 backend 真填)
   - violations 0 时 conflicts=[] (空骨架渲) · 不复用 tpl 假 conflicts (avoid 假 live · 红线 #1) */
function normalizeComplianceBackendDone(
  env: ComplianceDoneEnvelope | null,
  tplFallback: ComplianceSession,
): ComplianceSession {
  if (!env) return tplFallback;

  const violations = Array.isArray(env.violations) ? env.violations : [];
  const recommendations = Array.isArray(env.recommendations) ? env.recommendations : [];

  /* violations → Conflict shape (id/clauseLabel/docId/docTitle/severity/finding/cite/advice + audit/freshness/client)
     compliance Conflict.severity ∈ {block, warn, info} · 后端 critical → block · major → warn · minor → info
     ALL IN step 4: 消费 v.reason.* (backend ViolationReason 8 字段 + 3 freshness)
     ALL IN step 5: 优先消费 v.id (per candidate-identity-contract v1.1) · fallback v.violation_id */
  const conflicts: Conflict[] = violations.map((v, idx) => {
    const sev = String(v.severity ?? "minor").toLowerCase();
    const mapped: Conflict["severity"] =
      sev === "critical" || sev === "block"
        ? "block"
        : sev === "major" || sev === "warn"
        ? "warn"
        : "info";
    /* reason 是 backend ViolationReason.to_dict() 8 字段 + 3 freshness · 可能为 null (registry 不可用时) */
    const reason = (v.reason ?? null) as Record<string, unknown> | null;
    const reasonGet = (k: string): string => {
      const val = reason?.[k];
      return typeof val === "string" ? val : "";
    };
    const reasonGetNum = (k: string): number | undefined => {
      const val = reason?.[k];
      return typeof val === "number" ? val : undefined;
    };
    const reasonGetBool = (k: string): boolean | undefined => {
      const val = reason?.[k];
      return typeof val === "boolean" ? val : undefined;
    };

    return {
      id: String(v.id ?? v.violation_id ?? `live-vio-${idx + 1}`),
      clauseLabel: String(v.rule_article ?? v.rule_condition ?? "—"),
      docId: String(v.event_id ?? "—"),
      docTitle: String(v.event_type ?? "业务事件"),
      severity: mapped,
      finding: String(v.match_reason ?? v.evidence ?? ""),
      cite: String(v.evidence ?? ""),
      advice:
        ((recommendations.find(
          (r) => String(r.violation_id ?? "") === String(v.violation_id ?? ""),
        )?.text as string) ?? "见修订意见区"),
      // ALL IN step 4 audit fields
      clauseId: reasonGet("clause_id") || undefined,
      policyId: reasonGet("policy_id") || undefined,
      policyVersion: reasonGet("policy_version") || undefined,
      clauseHash: reasonGet("clause_text_hash") || undefined,
      evidenceDate: reasonGet("evidence_date") || undefined,
      retrievedAt: reasonGet("retrieved_at") || undefined,
      freshnessDays: reasonGetNum("freshness_days"),
      stalenessPassed: reasonGetBool("staleness_passed"),
      confidence: reasonGetNum("confidence"),
      reviewReason: reasonGet("review_reason") || undefined,
      // ALL IN step 5 client fields (顶层 v.client / v.client_uscc · backend 已平铺)
      client: typeof v.client === "string" ? v.client : undefined,
      clientUscc: typeof v.client_uscc === "string" ? v.client_uscc : undefined,
    };
  });

  /* recommendations → RevisionAdvice 三类 (改/补/强 → fix/add/strengthen) */
  const KIND_MAP: Record<string, RevisionAdvice["kind"]> = {
    "改": "fix",
    "补": "add",
    "强": "strengthen",
    fix: "fix",
    add: "add",
    strengthen: "strengthen",
  };
  const revisionAdvices: RevisionAdvice[] = recommendations.map((r, idx) => {
    const cat = String(r.category ?? "改");
    const kind = KIND_MAP[cat] ?? "fix";
    const vid = String(r.violation_id ?? "");
    const matched = violations.find((v) => String(v.violation_id ?? "") === vid);
    return {
      id: `live-rev-${idx + 1}`,
      kind,
      title: String(r.title ?? "整改建议"),
      body: String(r.text ?? ""),
      docTitle: matched ? String(matched.rule_article ?? "") : undefined,
    };
  });

  return {
    ...tplFallback,
    id: "live",
    stage: "已扫描",
    conflicts,           // ALL IN step 2: 0 violations → 空数组 · 不复用 tpl 假数据
    revisionAdvices,     // ALL IN step 2: 0 recommendations → 空数组
  };
}

export default function ComplianceWorkspace() {
  const [tab, setTab] = useState<OutputTab>("matrix");

  /* ALL IN Phase B step 1-2 (2026-05-09) · empty-state-design-protocol v1.0 默认 started=false (gate 1) ·
     用户上传 / 起巡检 / 点模板比对 才 setStarted(true) · panel 真数据填入。
     mock UI 全删 · 历史 session dropdown / DEMO 难度 dropdown 已下架 (step 1)。
     sessionData fallback EMPTY_SESSION (step 2) · 5 panel started=true && liveData=null 时显空骨架 · 不假 live。

     workspace-state-protocol §2 · 3 gate state:
       (1) started · (2) liveData · (3) selectedViolationId */
  const [started, setStarted] = useState(false);
  const [liveData, setLiveData] = useState<ComplianceDoneEnvelope | null>(null);
  const [selectedViolationId, setSelectedViolationId] = useState<string | null>(null);
  /* compliance-only · 衍生 UI state */
  const [view, setView] = useState<ViolationView>("by_violation");

  /* sessionData 单点派生 · live 优先 overlay · 否则 EMPTY (ALL IN step 2 · 不 fallback mock) */
  const sessionData: ComplianceSession = useMemo(() => {
    return liveData ? normalizeComplianceBackendDone(liveData, EMPTY_SESSION) : EMPTY_SESSION;
  }, [liveData]);
  const session = sessionData;
  const isLive = liveData !== null;

  const [trigger, setTrigger] = useState<TriggerSource | null>(null);
  const [scanId, setScanId] = useState<string>("");
  const [scanRunning, setScanRunning] = useState(false);
  const [scanError, setScanError] = useState<string>("");
  const [exportInfo, setExportInfo] = useState<ExportInfo>({ status: "idle" });

  /* gate 3 selectedViolationId 派生 conflict 对象 · ViolationDetail + RevisionDraft 联动 */
  const selectedViolation: Conflict | null = useMemo(() => {
    if (!selectedViolationId) return null;
    return sessionData.conflicts.find((c) => c.id === selectedViolationId) ?? null;
  }, [selectedViolationId, sessionData.conflicts]);

  /* ESC 关 ViolationDetail (gate 4 · 与 channel pattern 一致 · 但 compliance 是中栏 panel 非 drawer) */
  useEffect(() => {
    if (!selectedViolationId) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSelectedViolationId(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedViolationId]);

  /* D3 Atomic A · 自动选首条 high-severity violation when started · 一次性 ref guard · 防覆盖用户切换 */
  const hasAutoSelectedViolationRef = useRef(false);
  /* PB#5 · AbortController · 组件卸载/重新触发 abort SSE · 防僵尸连接 */
  const abortRef = useRef<AbortController | null>(null);
  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);
  useEffect(() => {
    if (!started) return;
    if (selectedViolationId) return;
    if (hasAutoSelectedViolationRef.current) return;
    const conflicts = sessionData.conflicts;
    if (!conflicts || conflicts.length === 0) return;
    const sorted = [...conflicts].sort(
      (a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity],
    );
    if (sorted[0]?.id) {
      setSelectedViolationId(sorted[0].id);
      hasAutoSelectedViolationRef.current = true;
    }
  }, [started, selectedViolationId, sessionData.conflicts]);

  /* Stage Fix W-FIX2-A3 · live-fallback-banner-spec v1.0 §2 规则 1 ·
     按 endpoint 分别记录失败 · UI 显式 banner + retry · 不 silent swap mock.
     bug #5 根因: primary CTA 之前 hardcode `force_mock: true` 静默走 mock ·
     现在 primary 默认 force_mock=false · 失败显 banner 让用户分辨真假. */
  type LiveFail = {
    endpoint: string;
    label: string;
    status: number;
    message: string;
    bodyExcerpt: string;
  };
  const [liveFail, setLiveFail] = useState<LiveFail | null>(null);
  const [retryHandler, setRetryHandler] = useState<(() => void) | null>(null);

  /* 件 #2 · data_source SSOT 真消费 (per Q-054 risk #1):
       liveFail !== null → mock_fallback (banner-spec rule 1 trust 一级降级)
       liveData?.data_source 直接消费 (后端 canon 5 enum)
       no live yet → "mock" (mock dropdown 演示态) */
  const currentDataSource: DataSourceKind = liveFail
    ? "mock_fallback"
    : liveData?.data_source
      ? normalizeDataSource(liveData.data_source)
      : "mock";

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

  /* Primary CTA · 上传政策 + 业务制度 → POST /api/compliance/policy_scan SSE.
     Stage Fix W-FIX2-A3 · force_mock 默认 false · primary 必须真接后端 ·
     失败 → liveFail banner · mock dropdown tertiary 才走 demo.
     Phase A worker-A4-compli (2026-04-29) · onDone callback 写 liveData (gate 3) ·
     panel 同步 overlay · 自动选 violations[0] (gate 4) · per draft §3.2 trigger path */
  const triggerPolicyScan = useCallback(async () => {
    setStarted(true);
    setTrigger("primary_scan");
    setScanRunning(true);
    setScanError("");
    setExportInfo({ status: "idle" });
    setLiveData(null);
    setSelectedViolationId(null);
    clearLiveFail();
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    try {
      const { scanId: captured } = await runPolicyScan(
        {
          /* TODO Stage D.5 · 上传文件 → 真政策文本 · 当前用 session 内文本触发 backend SSE */
          policyDoc:
            "第六条 个人消费贷款期限不得超过 12 个月。\n" +
            "第三条 联合贷款本行出资比例不得低于 30%。",
          businessDocs: [
            { event_id: "LN20251108", event_type: "loan",
              fields: { months: 18, amount: 100000, purpose: "个人消费" } },
            { event_id: "COOP202510007", event_type: "cooperation",
              fields: { bank_share_ratio: 0.15, amount: 5000000 } },
          ],
          policyMeta: { title: COMPLIANCE_SESSION.objective, fetched_at: COMPLIANCE_SESSION.updated },
          forceMock: false,
        },
        undefined,
        (env) => {
          /* gate 3 · done envelope → liveData · panel 整 overlay 渲染 · auto-pick violations[0] */
          setLiveData(env);
          const firstVio = Array.isArray(env.violations) && env.violations.length > 0
            ? String((env.violations[0] as Record<string, unknown>).violation_id ?? "")
            : "";
          if (firstVio) setSelectedViolationId(firstVio);
        },
        ac.signal,
      );
      if (ac.signal.aborted) return;
      if (captured) setScanId(captured);
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      recordLiveFail("policy_scan 政策比对", e, () => triggerPolicyScan());
      setScanError(e instanceof Error ? e.message : String(e));
    } finally {
      if (!ac.signal.aborted) setScanRunning(false);
    }
  }, []);

  /* Secondary CTA · 用模板快速比对 → POST /api/compliance/matrix_check */
  const triggerTemplateCheck = useCallback(async () => {
    setStarted(true);
    setTrigger("secondary_template");
    setScanRunning(true);
    setScanError("");
    clearLiveFail();
    try {
      await runMatrixCheck({
        policies: [
          { rule_id: "POL-T-001", article: "模板 · 期限",
            category: "期限", condition: "期限不超 12 月",
            threshold: { max_months: 12 }, severity_hint: "critical" },
        ],
        businessLines: [
          { event_id: "DEMO-LN", event_type: "loan",
            fields: { months: 18, purpose: "consumer" } },
        ],
        useLlm: false,
      });
      /* matrix_check 返同步 JSON · 不写 scanId · 仅 demo 触发 */
    } catch (e) {
      recordLiveFail("matrix_check 模板比对", e, () => triggerTemplateCheck());
      setScanError(e instanceof Error ? e.message : String(e));
    } finally {
      setScanRunning(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* Word 导出 · POST /api/compliance/export_docx */
  const triggerExportDocx = useCallback(async () => {
    if (!scanId) {
      setExportInfo({
        status: "error",
        message: "尚无 scan_id · 先跑一次政策比对",
      });
      return;
    }
    setExportInfo({ status: "running" });
    try {
      const blob = await exportDocxApi(scanId, session.objective);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `compliance_revision_${scanId}.docx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setExportInfo({ status: "done" });
    } catch (e) {
      if (e instanceof LiveFailError && e.status === 404) {
        /* 后端 endpoint 未上线 · 显式 pending 不弹 banner */
        setExportInfo({
          status: "error",
          message: "导出端点 /api/compliance/export_docx 待后端实装",
        });
        return;
      }
      recordLiveFail("export_docx 导出修订意见", e, () => triggerExportDocx());
      setExportInfo({
        status: "error",
        message: e instanceof Error ? e.message : String(e),
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scanId, session.objective]);

  return (
    /* ALL IN Phase B.1 fix (2026-05-09) · 删 COMPLIANCE_EVIDENCE 假证据 fixtures · EMPTY fallback ·
       真证据 step 4 已通过 Conflict.clauseHash + reason.* 字段级溯源闭环 · Evidence drawer 待 phase C 接 shared/evidence_drawer */
    <EvidenceProvider items={[]} unfilledFields={[]}>
    <div
      className="rpt-workspace"
      data-testid="compli-workspace"
      data-started={started ? "yes" : "no"}
      data-trigger={trigger ?? "none"}
      data-mode={isLive ? "live" : "mock"}
    >
      <HeroSection
        weeklyProcessed={COMPLIANCE_GLOBAL_STATS.weeklyProcessed}
        conflictRate={COMPLIANCE_GLOBAL_STATS.conflictRate}
        avgDuration={COMPLIANCE_GLOBAL_STATS.avgDuration}
        objective={session.objective}
        stage={session.stage}
        updated={session.updated}
        qcCounts={session.qcCounts}
      />

      <TriggerBar
        onTemplateCheck={triggerTemplateCheck}
        scanRunning={scanRunning}
      />

      {/* D3 Atomic F · UploadRail 移到 .compliance-settings-fold 内 · 上传不占主屏 (per Codex R1 选项 1) */}

      {started ? (
        <>
          {liveFail ? (
            <div
              className="compliance-live-fail-banner"
              role="alert"
              data-testid="compli-live-fail-banner"
              data-status={liveFail.status}
              data-endpoint={liveFail.endpoint}
            >
              <span className="compliance-live-fail-banner__icon" aria-hidden>⚠️</span>
              <span className="compliance-live-fail-banner__text">
                后端 <b>{liveFail.label}</b> 调用失败 (
                {liveFail.status > 0 ? `HTTP ${liveFail.status}` : "network/SSE"})
                · 当前显 fallback 演示数据 · 切真实路径请重试
                {liveFail.bodyExcerpt ? (
                  <span className="compliance-live-fail-banner__detail">
                    · 详情：{liveFail.bodyExcerpt}
                  </span>
                ) : null}
              </span>
              {retryHandler ? (
                <button
                  type="button"
                  className="compliance-live-fail-banner__retry"
                  onClick={() => retryHandler()}
                  data-testid="compli-live-fail-retry"
                >
                  重试
                </button>
              ) : null}
              <button
                type="button"
                className="compliance-live-fail-banner__dismiss"
                onClick={clearLiveFail}
                aria-label="关闭横幅"
              >
                ×
              </button>
            </div>
          ) : null}

          {scanError && !liveFail ? (
            <div
              className="compliance-error-banner"
              role="alert"
              data-testid="compli-error-banner"
            >
              扫描调用失败：{scanError}
            </div>
          ) : null}

          <div data-testid="compli-pilot-ticker">
            <PolicyTicker
              policies={session.policies}
              timeline={session.timeline}
              conflicts={session.conflicts}
            />
          </div>

          {/* D3 Atomic A · 主 layout 重排 (Codex R1 + Claude R1 双辩论 converge · 2026-05-05)
              - settings panels 折叠到 .rpt-grid 之前 (扫描设置 全宽 details · 默认收起)
              - .rpt-grid 三栏 = ViolationList (left) + ViolationDetail (mid) + RevisionPanel (right)
              - OutputPanel matrix/funnel/timeline 折叠到 .rpt-grid 之后 (深入分析 全宽 details)
              - DOM 仍 .rpt-grid + 3 child · CSS 不动 · Q-047 视觉冻不破
              D3 Atomic B+F · settings fold 内含 5 旧 panels + UploadRail (上传入口收敛)
              D3 Atomic C · 三视角 tabs 从 ViolationListPanel 内部提到 ComplianceStatsBar 同行 */}
          <details className="compliance-settings-fold" data-testid="compli-settings-fold">
            <summary>扫描设置 · 上传 / 政策 / 制度 / 流水 / 最近会话</summary>
            <div className="compliance-settings-fold__panels">
              <UploadRail
                innerUploads={session.innerPolicyUploads}
                outerUploads={session.outerPolicyUploads}
                onScanStart={triggerPolicyScan}
                scanRunning={scanRunning}
              />
              <QueryPanel q={session.query} />
              <PoliciesPanel policies={session.policies} />
              <DocsPanel docs={session.docs} />
              <PipelinePanel steps={session.pipeline} />
              <RecentPanel recent={session.recentSessions} />
            </div>
          </details>

          <ComplianceStatsBar
            conflicts={session.conflicts}
            matrixCells={session.matrix}
            view={view}
            onViewChange={setView}
            isLive={isLive}
            dataSourceKind={currentDataSource}
          />

          <div className="rpt-grid">
            <aside className="rpt-col rpt-col--left">
              <ViolationListPanel
                conflicts={session.conflicts}
                view={view}
                onViewChange={setView}
                selectedViolationId={selectedViolationId}
                onSelectViolation={setSelectedViolationId}
                isLive={isLive}
              />
            </aside>

            <section className="rpt-col rpt-col--mid">
              {selectedViolation ? (
                <ViolationDetailPanel
                  violation={selectedViolation}
                  revisions={session.revisionAdvices.filter((a) =>
                    selectedViolation.docTitle
                      ? a.docTitle === selectedViolation.clauseLabel || a.docTitle === selectedViolation.docTitle
                      : true,
                  )}
                  onClose={() => setSelectedViolationId(null)}
                  allConflicts={session.conflicts}
                />
              ) : (
                <div
                  className="compliance-detail-placeholder"
                  role="status"
                  data-testid="compli-detail-placeholder"
                >
                  <span>请从左栏选择违规查看详情 · evidence + 政策原文 + 业务摘录</span>
                </div>
              )}
            </section>

            <section
              className="rpt-col rpt-col--right"
              data-testid="compli-pilot-revisions"
            >
              <RevisionPanel
                advices={session.revisionAdvices}
                scanId={scanId}
                exportInfo={exportInfo}
                onExportDocx={triggerExportDocx}
              />
            </section>
          </div>

          <details className="compliance-output-fold" data-testid="compli-output-fold">
            <summary>深入分析 · 矩阵 / 漏斗 / 时间线</summary>
            <div data-testid="compli-pilot-matrix">
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
            </div>
          </details>

          {/* ALL IN Phase B.1 fix (2026-05-09): 删 COMPLIANCE_EVIDENCE.summary 假证据
              · 真分析结论 step 4 已通过每 violation 的 reviewReason (派生 narrative) 显示
              · 不再单独渲染顶层 "Evidence-grounded 结论" mock 块 · 避免误导审计 */}
        </>
      ) : (
        <EmptyStateSkeleton />
      )}
    </div>
    </EvidenceProvider>
  );
}

/* ── Tertiary + Secondary CTA bar ──────────────────────── */

function TriggerBar(p: {
  onTemplateCheck: () => void;
  scanRunning: boolean;
}) {
  const templateLabel = p.scanRunning ? "比对运行中…" : "用模板快速比对";
  return (
    <section
      className="compliance-trigger-bar"
      aria-label="次要触发入口 · 模板比对"
      data-testid="compli-trigger-bar"
    >
      <button
        type="button"
        className="compliance-trigger-bar__secondary"
        onClick={p.onTemplateCheck}
        disabled={p.scanRunning}
        data-testid="compli-template-check-cta"
      >
        {templateLabel}
      </button>
    </section>
  );
}

/* ── Empty-state skeleton (空骨架 · 不显示 mock 数据) ───── */

function EmptyStateSkeleton() {
  return (
    <section
      className="compliance-empty"
      aria-label="尚未触发巡检 · 等待用户输入"
      data-testid="compli-empty-skeleton"
    >
      <div className="compliance-empty__head">
        <h3 className="compliance-empty__title">等待触发巡检</h3>
        <p className="compliance-empty__hint">
          上方
          <strong>上传政策文件 + 业务制度</strong>
          → 点击「开始政策比对」启动真扫描；或
          <strong>用模板快速比对</strong>
          一键演示。
        </p>
      </div>
      <div className="compliance-empty__panels">
        <div className="compliance-empty__panel" data-panel="ticker">
          政策 Ticker · 扫描完成后此处显示最新 3 条事件
        </div>
        <div className="compliance-empty__panel" data-panel="matrix">
          冲突矩阵 doc × clause · 扫描完成显示矩阵
        </div>
        <div className="compliance-empty__panel" data-panel="conflict">
          冲突点列表 · 改 / 补 / 强 三类 chip
        </div>
        <div className="compliance-empty__panel" data-panel="revision">
          修订意见草稿 · 完成后可一键导出 Word
        </div>
      </div>
    </section>
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
  onScanStart?: () => void;
  scanRunning?: boolean;
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
    /* Stage CF · 通知上层切 started=true 并 fire POST /api/compliance/policy_scan SSE
       (上层 triggerPolicyScan 处理 fetch + SSE 解析 + scan_id 落 state) */
    p.onScanStart?.();
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
            data-testid="compli-policy-scan-cta"
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
          title="行内业务制度"
          hint="本行制度 · 审批办法 · 业务细则"
          uploads={p.innerUploads}
          side="inner"
          testId="compli-business-upload-cta"
        />
        <DropZoneCard
          title="外部监管政策"
          hint="监管规定 · 通知 · 指引 · 公开规范"
          uploads={p.outerUploads}
          side="outer"
          testId="compli-policy-upload-cta"
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
  testId?: string;
}) {
  const count = p.uploads.length;
  return (
    <div
      className="compliance-drop-card"
      data-side={p.side}
      data-testid={p.testId}
    >
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
  // pin-drop · 拖钉到 composer 时插入 `@引用:<title> ` · 不再让 textarea 吞 URL
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
                    data-testid="compli-matrix-cell"
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

/* ────────────────────── VIOLATION LIST + DETAIL · gate 3 ────────────────────── */
/* ALL IN Phase B step 1 (2026-05-09) · workspace-state-protocol §2 · gate 3 · click → 选 violation
   view tab compliance-only (by_violation/by_clause/by_event · 衍生 UI state · 不在 3 gate) */

const VIOLATION_VIEW_LABEL: Record<ViolationView, string> = {
  by_violation: "按违规",
  by_clause: "按条款",
  by_event: "按业务事件",
};

const SEVERITY_RANK: Record<Conflict["severity"], number> = {
  block: 0,
  warn: 1,
  info: 2,
};

/* ────────────────────── COMPLIANCE STATS BAR · gate 4 顶部 ──────────────────────
   D3 Atomic B (统计) + Atomic C (三视角 tabs 提升) · 2026-05-05
   - 数据派生 session.conflicts + session.matrix · 不与 ViolationListPanel 状态分叉
   - 命中率 matrix.cells.length === 0 时显 "—" (per Codex R1 verbatim "0% 语义像已扫描且无命中")
   - docId unique count 过滤空值 (per Codex R1 风险点 2)
*/
function ComplianceStatsBar(p: {
  conflicts: Conflict[];
  matrixCells: MatrixCell[];
  view: ViolationView;
  onViewChange: (v: ViolationView) => void;
  isLive: boolean;
  /* 件 #2 · data_source SSOT 真消费 · 5-enum trust model badge */
  dataSourceKind?: DataSourceKind;
}) {
  const total = p.conflicts.length;
  const block = p.conflicts.filter((c) => c.severity === "block").length;
  const warn = p.conflicts.filter((c) => c.severity === "warn").length;
  const info = p.conflicts.filter((c) => c.severity === "info").length;
  const cellCount = p.matrixCells.length;
  const hitRateLabel =
    cellCount > 0 ? `${((total / cellCount) * 100).toFixed(1)}%` : "—";
  const docCount = new Set(p.conflicts.map((c) => c.docId).filter(Boolean)).size;
  return (
    <section
      className="compliance-stats-bar"
      aria-label="合规扫描统计"
      data-testid="compli-stats-bar"
      data-mode={p.isLive ? "live" : "mock"}
    >
      <div className="compliance-stats-bar__metrics">
        {/* 件 #2 · data_source SSOT 真消费 · 5-enum trust model badge (Q-054 risk #1) */}
        <div
          className="compliance-stats-bar__item compliance-stats-bar__item--mode"
          data-testid="compli-stats-mode"
          data-mode={p.isLive ? "live" : "mock"}
          data-source={p.dataSourceKind ?? ""}
        >
          <span className="compliance-stats-bar__label">数据来源</span>
          <span className="compliance-stats-bar__value">
            {p.dataSourceKind ? (
              <DataSourceBadge kind={p.dataSourceKind} testId="compli-data-source-badge" size="sm" />
            ) : (
              p.isLive ? "● LIVE 真接" : "○ MOCK 演示"
            )}
          </span>
        </div>
        <div className="compliance-stats-bar__item" data-testid="compli-stats-total">
          <span className="compliance-stats-bar__label">违规数</span>
          <span className="compliance-stats-bar__value">{total}</span>
        </div>
        <div className="compliance-stats-bar__item" data-testid="compli-stats-hitrate">
          <span className="compliance-stats-bar__label">命中率</span>
          <span className="compliance-stats-bar__value">{hitRateLabel}</span>
        </div>
        <div className="compliance-stats-bar__item" data-testid="compli-stats-severity">
          <span className="compliance-stats-bar__label">严重度</span>
          <span className="compliance-stats-bar__value">
            严 {block} · 一般 {warn} · 观察 {info}
          </span>
        </div>
        <div className="compliance-stats-bar__item" data-testid="compli-stats-docs">
          <span className="compliance-stats-bar__label">业务单号</span>
          <span className="compliance-stats-bar__value">{docCount}</span>
        </div>
      </div>
      <div
        className="cp-out__tabs"
        role="tablist"
        data-testid="compli-violation-view-tabs"
      >
        {(["by_violation", "by_clause", "by_event"] as const).map((v) => (
          <button
            key={v}
            type="button"
            className="cp-out__tab"
            data-active={p.view === v ? "yes" : "no"}
            data-testid={`compli-violation-view-${v}`}
            onClick={() => p.onViewChange(v)}
          >
            {VIOLATION_VIEW_LABEL[v]}
          </button>
        ))}
      </div>
    </section>
  );
}

function ViolationListPanel(p: {
  conflicts: Conflict[];
  view: ViolationView;
  onViewChange: (v: ViolationView) => void;
  selectedViolationId: string | null;
  onSelectViolation: (id: string | null) => void;
  isLive: boolean;
}) {
  const sorted = useMemo(() => {
    const arr = [...p.conflicts];
    if (p.view === "by_violation") {
      return arr.sort((a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity]);
    }
    if (p.view === "by_clause") {
      return arr.sort((a, b) => a.clauseLabel.localeCompare(b.clauseLabel, "zh-CN"));
    }
    return arr.sort((a, b) => a.docId.localeCompare(b.docId));
  }, [p.conflicts, p.view]);

  const blockN = p.conflicts.filter((c) => c.severity === "block").length;
  const warnN = p.conflicts.filter((c) => c.severity === "warn").length;
  const infoN = p.conflicts.filter((c) => c.severity === "info").length;

  return (
    <section
      className="rpt-panel compliance-violations"
      aria-label="违规榜单"
      data-testid="compli-pilot-violations"
      data-mode={p.isLive ? "live" : "mock"}
      data-view={p.view}
    >
      <PanelPinHandle
        id="compliance:violations"
        title="违规榜单"
        subtitle={`严重 ${blockN} · 一般 ${warnN} · 观察 ${infoN}`}
        accentVar="--t-compli"
        agentKey="compliance"
        href="/archive/compliance"
        blurb={`${p.conflicts.length} 条违规 · 三视角 ${VIOLATION_VIEW_LABEL[p.view]}`}
      />
      <div className="rpt-panel__head cp-out__head">
        <div className="rpt-panel__eyebrow">
          违规榜单 · gate 4 · {VIOLATION_VIEW_LABEL[p.view]}
        </div>
        {/* D3 Atomic C · 三视角 tabs 提到 ComplianceStatsBar 同行 (per Codex R1 选项 1) */}
      </div>
      <div className="rpt-panel__body">
        <ul className="cp-fn__cf-list">
          {sorted.length === 0 ? (
            <li className="cp-fn__cf cp-fn__cf--empty">暂无违规 · 政策与业务无冲突</li>
          ) : null}
          {sorted.map((c) => {
            const active = p.selectedViolationId === c.id;
            return (
              <li
                key={c.id}
                className="cp-fn__cf"
                data-severity={c.severity}
                data-active={active ? "yes" : "no"}
                data-testid="compli-violation-card"
              >
                <button
                  type="button"
                  className="cp-fn__cf-btn"
                  onClick={() => p.onSelectViolation(active ? null : c.id)}
                  aria-pressed={active}
                  data-testid="compli-violation-card-btn"
                  style={{
                    width: "100%",
                    textAlign: "left",
                    background: "transparent",
                    border: "none",
                    padding: 0,
                    color: "inherit",
                    cursor: "pointer",
                  }}
                >
                  <div className="cp-fn__cf-head">
                    <span className="cp-fn__cf-mark" aria-hidden>
                      {c.severity === "block" ? "✕" : c.severity === "warn" ? "!" : "i"}
                    </span>
                    <div className="cp-fn__cf-cl">{c.clauseLabel}</div>
                    <span className="cp-fn__cf-doc">{c.docTitle} · {c.docId}</span>
                  </div>
                  <div className="cp-fn__cf-find">{c.finding}</div>
                  <div className="cp-fn__cf-cite">出处 · {c.cite || "—"}</div>
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}

/* ALL IN Phase B step 6 (2026-05-09) · per-entity 聚合 badge ·
   选中 violation 时显 "本客户共 N 条违规" + severity 拆分 · 给审贷员客户级深度感. */
function ComplianceEntityAggregateBadge(p: {
  violation: Conflict;
  allConflicts: Conflict[];
}) {
  const v = p.violation;
  // entity key 优先 client + clientUscc · 退化 client only · 都缺则 v.id
  const ek =
    v.clientUscc
      ? `uscc:${v.clientUscc}`
      : v.client
        ? `name:${v.client}`
        : "";
  if (!ek) return null;

  const sameEntity = p.allConflicts.filter((c) => {
    if (c.id === v.id) return false; // 不计自身
    const cek = c.clientUscc
      ? `uscc:${c.clientUscc}`
      : c.client
        ? `name:${c.client}`
        : "";
    return cek === ek;
  });

  if (sameEntity.length === 0) return null;

  const sev = sameEntity.reduce(
    (a, c) => {
      a[c.severity] = (a[c.severity] ?? 0) + 1;
      return a;
    },
    { block: 0, warn: 0, info: 0 } as Record<Conflict["severity"], number>,
  );

  const clientLabel = v.client || (v.clientUscc ?? "本客户");

  return (
    <div
      className="compliance-entity-aggregate"
      data-testid="compli-entity-aggregate"
      style={{
        marginTop: 6,
        marginBottom: 6,
        padding: "6px 10px",
        background: "rgba(45, 107, 74, 0.08)",
        border: "1px solid rgba(45, 107, 74, 0.20)",
        borderRadius: 6,
        fontSize: 12,
        display: "flex",
        flexWrap: "wrap",
        gap: 8,
        alignItems: "center",
      }}
      title="本客户在当前扫描中的总违规分布 · per-entity 联动 (ALL IN step 6)"
    >
      <strong>{clientLabel}</strong>
      <span>本次扫描共关联</span>
      <strong data-testid="compli-entity-aggregate-count">{sameEntity.length + 1}</strong>
      <span>条违规 (本条 + {sameEntity.length} 条同客户)</span>
      {sev.block > 0 ? (
        <span style={{ color: "rgb(160, 30, 30)", fontWeight: 600 }}>
          严重 {sev.block + (v.severity === "block" ? 1 : 0)}
        </span>
      ) : null}
      {sev.warn > 0 ? (
        <span style={{ color: "rgb(180, 120, 0)" }}>
          一般 {sev.warn + (v.severity === "warn" ? 1 : 0)}
        </span>
      ) : null}
      {sev.info > 0 ? (
        <span style={{ opacity: 0.7 }}>观察 {sev.info + (v.severity === "info" ? 1 : 0)}</span>
      ) : null}
    </div>
  );
}

/* ALL IN Phase B step 4 (2026-05-09) · 字段级溯源 audit block ·
   消费 ViolationReason 8 字段 + 3 freshness · 红线 #8 anchor */
function ComplianceAuditBlock(p: { violation: Conflict }) {
  const v = p.violation;
  const hasAudit =
    v.clauseHash || v.clauseId || v.policyId || v.policyVersion;
  const hasFreshness =
    typeof v.freshnessDays === "number" ||
    typeof v.stalenessPassed === "boolean" ||
    Boolean(v.evidenceDate);

  if (!hasAudit && !hasFreshness) return null;

  // 时效徽章颜色: 通过=绿 / 失效=红 / 不可计算=灰
  const freshTone: "ok" | "stale" | "unknown" =
    v.stalenessPassed === false
      ? "stale"
      : v.freshnessDays === -1 || v.stalenessPassed === undefined
        ? "unknown"
        : "ok";
  const freshLabel =
    freshTone === "stale"
      ? `政策超时效 (${v.freshnessDays}d > 365d SLA)`
      : freshTone === "unknown"
        ? "时效未知"
        : `政策时效内 (${v.freshnessDays}d / 365d)`;

  // 置信度色 (1.0=绿 hard-rule / 0.7=黄 LLM / <0.7=灰 兜底)
  const confTone: "high" | "med" | "low" =
    typeof v.confidence !== "number"
      ? "low"
      : v.confidence >= 0.95
        ? "high"
        : v.confidence >= 0.65
          ? "med"
          : "low";

  return (
    <div
      className="compliance-audit-block"
      data-testid="compli-audit-block"
      data-stale={freshTone === "stale" ? "yes" : "no"}
      style={{
        marginTop: 8,
        marginBottom: 12,
        padding: "10px 12px",
        border: "1px solid var(--c-line, #ddd)",
        borderRadius: 8,
        background: "var(--c-surface-1, #f8f8f6)",
        fontSize: 12,
        lineHeight: 1.6,
      }}
    >
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 8,
          alignItems: "center",
          marginBottom: hasAudit && hasFreshness ? 6 : 0,
        }}
      >
        {v.clauseId ? (
          <span
            data-testid="compli-audit-clause-id"
            style={{
              padding: "2px 6px",
              background: "var(--c-surface-2, #eee)",
              borderRadius: 4,
              fontFamily: "var(--ff-mono, monospace)",
            }}
            title="政策注册库 clause id (registry CL-xxxx)"
          >
            {v.clauseId}
          </span>
        ) : null}
        {v.policyVersion ? (
          <span
            data-testid="compli-audit-policy-version"
            style={{
              padding: "2px 6px",
              background: "var(--c-surface-2, #eee)",
              borderRadius: 4,
              fontFamily: "var(--ff-mono, monospace)",
            }}
            title="政策版本号 (registry VER-xxxx · 不可篡改)"
          >
            {v.policyVersion}
          </span>
        ) : null}
        {v.clauseHash ? (
          <span
            data-testid="compli-audit-clause-hash"
            style={{
              padding: "2px 6px",
              background: "rgba(40, 100, 60, 0.08)",
              color: "var(--t-compli, #2d6b4a)",
              borderRadius: 4,
              fontFamily: "var(--ff-mono, monospace)",
            }}
            title={`监管原文 SHA-256 前 16 hex · 红线 #8 篡改防御 · 完整 hash: ${v.clauseHash}`}
          >
            ⛓ {v.clauseHash}
          </span>
        ) : null}
        {typeof v.confidence === "number" ? (
          <span
            data-testid="compli-audit-confidence"
            data-tone={confTone}
            style={{
              padding: "2px 6px",
              background:
                confTone === "high"
                  ? "rgba(40, 100, 60, 0.10)"
                  : confTone === "med"
                    ? "rgba(180, 120, 0, 0.10)"
                    : "rgba(120, 120, 120, 0.10)",
              borderRadius: 4,
            }}
            title="LLM=0.7 / 硬规则=1.0 / 兜底<0.7"
          >
            置信 {(v.confidence * 100).toFixed(0)}%
          </span>
        ) : null}
      </div>

      {hasFreshness ? (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
          <span
            data-testid="compli-audit-freshness"
            data-tone={freshTone}
            style={{
              padding: "2px 6px",
              background:
                freshTone === "stale"
                  ? "rgba(180, 40, 40, 0.10)"
                  : freshTone === "ok"
                    ? "rgba(40, 100, 60, 0.10)"
                    : "rgba(120, 120, 120, 0.10)",
              color:
                freshTone === "stale"
                  ? "rgb(160, 30, 30)"
                  : freshTone === "ok"
                    ? "var(--t-compli, #2d6b4a)"
                    : "inherit",
              borderRadius: 4,
              fontWeight: freshTone === "stale" ? 600 : 400,
            }}
            title="政策时效 SLA 365d (CLAUDE.md §3.5.1 第 6 原则) · 失效需重抓"
          >
            {freshLabel}
          </span>
          {v.evidenceDate ? (
            <span data-testid="compli-audit-evidence-date" style={{ opacity: 0.75 }}>
              生效 {v.evidenceDate}
            </span>
          ) : null}
          {v.retrievedAt ? (
            <span data-testid="compli-audit-retrieved-at" style={{ opacity: 0.75 }}>
              · 扫描 {v.retrievedAt}
            </span>
          ) : null}
        </div>
      ) : null}

      {v.reviewReason ? (
        <div
          data-testid="compli-audit-review-reason"
          style={{ marginTop: 6, padding: "6px 8px", background: "var(--c-surface-2, #eee)", borderRadius: 4, fontStyle: "italic" }}
          title="ViolationReason.review_reason · 派生 narrative · 合规官单句签字理由"
        >
          {v.reviewReason}
        </div>
      ) : null}
    </div>
  );
}

function ViolationDetailPanel(p: {
  violation: Conflict;
  revisions: RevisionAdvice[];
  onClose: () => void;
  /* ALL IN Phase B step 6 (2026-05-09) · per-entity 联动 ·
     传入全 list 用于计算同客户其他违规数 (per-entity 聚合 badge) */
  allConflicts?: Conflict[];
}) {
  const sevLabel =
    p.violation.severity === "block" ? "严重违规" : p.violation.severity === "warn" ? "一般违规" : "观察项";
  return (
    <section
      className="rpt-panel compliance-violation-detail"
      aria-label="违规详情"
      data-testid="compli-pilot-detail"
      data-severity={p.violation.severity}
    >
      <PanelPinHandle
        id={`compliance:violation:${p.violation.id}`}
        title={`违规详情 · ${p.violation.clauseLabel}`}
        subtitle={p.violation.docId}
        accentVar="--t-compli"
        agentKey="compliance"
        href="/archive/compliance"
        blurb={p.violation.finding}
      />
      <div className="rpt-panel__head">
        <div className="rpt-panel__eyebrow">{sevLabel} · 业务单号 {p.violation.docId}</div>
        <button
          type="button"
          className="cp-out__tab"
          onClick={p.onClose}
          aria-label="关闭违规详情"
          data-testid="compli-violation-detail-close"
        >
          关闭 (ESC)
        </button>
      </div>
      <div
        className="rpt-panel__body"
        data-testid="compli-violation-detail"
      >
        <div className="cp-drawer__head">
          <span className="cp-drawer__sev" data-severity={p.violation.severity}>{sevLabel}</span>
          <span className="cp-drawer__doc">{p.violation.clauseLabel}</span>
        </div>

        {/* ALL IN Phase B step 6 (2026-05-09) · per-entity 联动 badge ·
            统计同客户 (按 v.id entity 派生) 其他违规数 · 让审贷员一眼看出此客户问题深度 */}
        <ComplianceEntityAggregateBadge violation={p.violation} allConflicts={p.allConflicts ?? []} />

        {/* ALL IN Phase B step 4 (2026-05-09) · audit + freshness 块 (字段级溯源) ·
            消费 backend ViolationReason 8 字段 + 3 freshness · 红线 #8 闭环 */}
        <ComplianceAuditBlock violation={p.violation} />

        {/* D3 Atomic D · 证据链增强 (per Codex R1 字段顺序: 业务单号 → 政策摘录 → 业务摘录 → AI 理由 → source row id) */}
        <dl className="compliance-evidence-chain">
          <dt>业务单号</dt>
          <dd data-testid="compli-evi-docid">{p.violation.docId || "—"}</dd>

          {p.violation.client ? (
            <>
              <dt>客户企业</dt>
              <dd data-testid="compli-evi-client">
                {p.violation.client}
                {p.violation.clientUscc ? (
                  <span style={{ marginLeft: 8, opacity: 0.7, fontFamily: "var(--ff-mono, monospace)" }}>
                    {p.violation.clientUscc}
                  </span>
                ) : null}
              </dd>
            </>
          ) : null}

          <dt>政策摘录</dt>
          <dd data-testid="compli-evi-policy">
            {(p.violation as unknown as { policy_excerpt?: string }).policy_excerpt
              || `${p.violation.clauseLabel} · ${p.violation.finding}`}
          </dd>

          <dt>业务原始记录</dt>
          <dd data-testid="compli-evi-business">
            {(p.violation as unknown as { business_excerpt?: string }).business_excerpt || "—"}
          </dd>

          <dt>AI 判定理由</dt>
          <dd data-testid="compli-evi-finding">{p.violation.finding}</dd>

          <dt>证据链 source</dt>
          <dd data-testid="compli-evi-source">{p.violation.cite || "—"}</dd>
        </dl>

        {p.revisions.length > 0 ? (
          <div className="cp-drawer__advice" data-testid="compli-violation-detail-revisions">
            <div className="cp-drawer__advice-head">
              <span className="cp-drawer__advice-tag">联动修订意见 · {p.revisions.length} 条</span>
            </div>
            <ul style={{ marginTop: 6, paddingLeft: 16 }}>
              {p.revisions.map((r) => (
                <li key={r.id} style={{ marginBottom: 4 }}>
                  <strong>{KIND_LABEL[r.kind]}</strong> · {r.title} — {r.body}
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <div style={{ marginTop: 8, opacity: 0.75, fontSize: 13 }}>
            暂无关联修订意见 · 见右栏「修订意见」区
          </div>
        )}
      </div>
    </section>
  );
}

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

function RevisionPanel(p: {
  advices: RevisionAdvice[];
  scanId?: string;
  exportInfo?: ExportInfo;
  onExportDocx?: () => void;
}) {
  const { advices, scanId, exportInfo, onExportDocx } = p;
  if (!advices.length) return null;

  const groups: Record<RevisionAdvice["kind"], RevisionAdvice[]> = {
    fix: [],
    add: [],
    strengthen: [],
  };
  advices.forEach((a) => groups[a.kind].push(a));

  const exportStatus = exportInfo?.status ?? "idle";
  const exportLabel =
    exportStatus === "running"
      ? "导出中…"
      : exportStatus === "done"
      ? "重新导出 Word"
      : exportStatus === "error"
      ? "重试导出"
      : "导出修订意见 Word";
  const exportDisabled = exportStatus === "running" || !scanId;

  return (
    <section
      className="rpt-panel compliance-bottom-revise"
      aria-label="修订意见"
      data-testid="compli-revision-draft"
    >
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
          {scanId ? (
            <p className="compliance-revise-sub" data-testid="compli-revision-scan-id">
              当前扫描 ID · {scanId}
            </p>
          ) : null}
        </div>
        <div className="compliance-revise-count">
          <span data-kind="fix" data-testid="compli-conflict-chip">
            改 <b>{groups.fix.length}</b>
          </span>
          <span data-kind="add" data-testid="compli-conflict-chip">
            补 <b>{groups.add.length}</b>
          </span>
          <span data-kind="strengthen" data-testid="compli-conflict-chip">
            强 <b>{groups.strengthen.length}</b>
          </span>
          {/* D3 Atomic E · 一键下发 RM hook (per Codex R1 verbatim "前端先落事件 hook · 不做假成功")
              disabled + tooltip · Sprint 5 后端实装 (RBAC dispatch endpoint) · 防假成功 */}
          <button
            type="button"
            className="compliance-dispatch-rm"
            data-testid="compli-dispatch-rm"
            disabled
            title="Sprint 5 后端实装 · 当前为前端 hook · 防假成功"
            aria-label="一键下发 RM (待 Sprint 5 后端实装)"
          >
            ↗ 一键下发 RM
          </button>
          <button
            type="button"
            className="compliance-revise-export"
            onClick={onExportDocx}
            disabled={exportDisabled}
            data-state={exportStatus}
            data-testid="compli-export-docx-btn"
          >
            {exportLabel}
          </button>
        </div>
      </div>

      {exportStatus === "error" && exportInfo?.message ? (
        <div className="compliance-revise-error" role="alert">
          导出失败：{exportInfo.message}
        </div>
      ) : null}

      <div className="compliance-revise-grid">
        {(["fix", "add", "strengthen"] as const).map((kind) => (
          <div key={kind} className="compliance-revise-col" data-kind={kind}>
            <div className="compliance-revise-col-head">
              <span
                className="compliance-revise-chip"
                data-kind={kind}
                data-testid="compli-conflict-chip"
              >
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
