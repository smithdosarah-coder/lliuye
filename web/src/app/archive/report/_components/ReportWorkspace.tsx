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

import { useCallback, useEffect, useRef, useState } from "react";
import type { CSSProperties, KeyboardEvent, ChangeEvent } from "react";
import { useAuthStore } from "@/lib/store";
import { usePinDrop, type PinDropPayload } from "@/components/composer/use-pin-drop";
import { MessagePinHandle } from "@/components/shell/MessagePinHandle";
import { ScanCTA } from "@/components/shared/ScanCTA";
import { CustomerSelector } from "@/components/shared/CustomerSelector";
import { PanelPinHandle } from "@/components/shell/PanelPinHandle";
import {
  exportReportDocx,
  exportReportPdf,
  refineReportSection,
  streamReportDemoRun,
  streamReportV16Fill,
  triggerDownloadBlob,
  uploadReportMaterials,
  type ReportExportPayload,
  type ReportV16DoneEvent,
  type ReportV16ErrorEvent,
  type ReportV16Event,
  type ReportV16Section,
  type ReportV16StageEvent,
} from "@/lib/api/report";
import { ClaimText, EvidenceProvider } from "@/components/evidence";
import { REPORT_EVIDENCE } from "@/components/evidence/fixtures";
import {
  REPORT_GLOBAL_STATS,
  REPORT_SESSION,
  liveToReportSession,
  type ConversationMessage,
  type PreviewField,
  type PreviewSection,
  type ReportSession,
  type TimelineEvent,
} from "@/lib/mock/agent-report-session";

const AGENT_KEY = "report";
const AGENT_HREF = "/archive/report";
const AGENT_ACCENT = "--t-report";

export function ReportWorkspace() {
  /* Phase A worker-A4 V2 (codex DISAGREE issue 1 fix · 2026-04-29):
     5 panel sessionData = liveData ?? REPORT_SESSION 单点派生 · 不再静态 mock 占主源.
     liveToReportSession 把 v16 done envelope 标准化成 ReportSession shape ·
     demo/run easy/medium/hard + real /v16/fill 都走同一管道 · 切换可见. */

  /* workspace-state-protocol §2 · 4 gate state model · Phase A worker-A4 (2026-04-29)
     (1) started          · user-trigger gate · 3 CTA (上传 / 模板 / 历史) 显式 setStarted(true)
     (2) selectedSession  · historyChoice · 选 mock 演示 session (training/demo)
     (3) liveData         · v16 fill / demo/run done envelope · 5 panel 单点派生 · 之前叫 livePayload
     (4) selectedSection  · 用户点 section nav 切到的章节 · 替代 ScanCTA onDone gate · ESC 关
     5 panel: 材料 grid (MaterialPanel) / 时间流 (TimelinePanel) / A4 预览 (PreviewPanel)
              / FieldChip 3 态 (FieldChip 内嵌 PreviewPanel) / 工具栏 (PreviewPanel toolbar) */

  const [started, setStarted] = useState(false);
  const [reportId, setReportId] = useState<string>("");
  const [mode, setMode] = useState<"mock" | "live">("mock");
  const [businessLine, setBusinessLine] = useState<string>("corporate");
  const [templateChoice, setTemplateChoice] = useState<string>("");
  const [historyChoice, setHistoryChoice] = useState<string>("");

  // v16 fill / demo/run 流式状态 · liveData = gate 3 (workspace-state-protocol §2)
  const [liveStages, setLiveStages] = useState<ReportV16StageEvent[]>([]);
  const [liveData, setLiveData] = useState<ReportV16DoneEvent | null>(null);
  const [generating, setGenerating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);

  // gate 4 · selectedSection · TOC click 切章节 · ESC 关 (Channel 4-gate parity · drawer pattern 复用)
  const [selectedSection, setSelectedSection] = useState<string | null>(null);

  /* sessionData 单点派生 (V2 issue 1 fix) · live > mock fallback ·
     5 panel + Hero + PipelineBand 都消费此 derived value · 不再 import REPORT_SESSION 直读 */
  const derivedFromLive = liveToReportSession(liveData);
  const sessionData: ReportSession = derivedFromLive ?? REPORT_SESSION;
  const s = sessionData;
  const coverPct = Math.round((s.coverage.filled / Math.max(s.coverage.total, 1)) * 100);
  const [llmConnected, setLlmConnected] = useState<boolean | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
  const [uploadedTemplate, setUploadedTemplate] = useState<string>("");
  // W-FIX-A1 · live-fallback-banner-spec §2 规则 1: live mode 调失败 → 顶部 banner
  const [liveFailErr, setLiveFailErr] = useState<{
    endpoint: string;
    status: string;
    message: string;
  } | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // status pill · GET /api/report/health (轻量·非 LLM 调用·empty-state §3 不违)
  useEffect(() => {
    let cancelled = false;
    const apiBase =
      (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE) || "";
    fetch(`${apiBase}/api/report/health`)
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => {
        if (cancelled) return;
        if (j && typeof j.llm_connected === "boolean") {
          setLlmConnected(j.llm_connected);
        }
      })
      .catch(() => {
        if (!cancelled) setLlmConnected(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // cleanup on unmount · 中断未完成 SSE
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  /* gate 4 · ESC 关 selectedSection · 4-gate parity with ChannelWorkspace selectedCandidate */
  useEffect(() => {
    if (!selectedSection) return;
    function onKey(e: globalThis.KeyboardEvent) {
      if (e.key === "Escape") setSelectedSection(null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedSection]);

  /* ── handlers ───────────────────────────────────────────────────── */

  const triggerV16Fill = useCallback(
    (opts?: { reportIdOverride?: string; explicitMock?: boolean }) => {
      if (generating) return;
      setGenerating(true);
      setLiveStages([]);
      setLiveData(null);
      setErrMsg(null);
      setLiveFailErr(null); // 重试时清旧 banner

      abortRef.current?.abort();
      const ac = new AbortController();
      abortRef.current = ac;

      const useMock = opts?.explicitMock ?? mode === "mock";
      streamReportV16Fill(
        {
          report_id: opts?.reportIdOverride ?? reportId ?? "",
          business_line: businessLine,
          mock: useMock,
        },
        {
          signal: ac.signal,
          onEvent: (evt: ReportV16Event) => {
            if (evt.event === "stage") {
              setLiveStages((prev) => [...prev, evt as ReportV16StageEvent]);
            } else if (evt.event === "done") {
              setLiveData(evt as ReportV16DoneEvent);
            } else if (evt.event === "error") {
              const msg = (evt as ReportV16ErrorEvent).message;
              setErrMsg(msg);
              // live mode 失败 · 显式 banner (live-fallback-banner-spec 规则 1)
              if (!useMock) {
                setLiveFailErr({
                  endpoint: "/api/report/v16/fill",
                  status: "SSE error",
                  message: msg,
                });
              }
            }
          },
          onClose: () => setGenerating(false),
          onError: (e) => {
            setErrMsg(e.message);
            // 网络 / HTTP 4xx / 5xx · live mode 时弹 banner
            if (!useMock) {
              const statusMatch = /HTTP (\d{3})/.exec(e.message);
              setLiveFailErr({
                endpoint: "/api/report/v16/fill",
                status: statusMatch ? statusMatch[1] : "network",
                message: e.message,
              });
            }
            setGenerating(false);
          },
        },
      );
    },
    [generating, reportId, businessLine, mode],
  );

  const handleUpload = useCallback(
    async (files: File[]) => {
      if (!files.length) return;
      setErrMsg(null);
      try {
        const resp = await uploadReportMaterials(files, businessLine);
        setReportId(resp.report_id);
        setUploadedFiles(resp.file_summary.map((fs) => fs.name));
        setMode("live");
        setStarted(true);
        // 不自动触发 fill · 用户须显式点 "开始生成" CTA (empty-state §3)
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        setErrMsg(msg);
        // W-FIX-A1 · upload endpoint live 失败也算 banner 触发
        const statusMatch = /HTTP (\d{3})/.exec(msg);
        setLiveFailErr({
          endpoint: "/api/report/upload",
          status: statusMatch ? statusMatch[1] : "network",
          message: msg,
        });
      }
    },
    [businessLine],
  );

  /* B-2 click-to-fire · dropdown 仅 set 选择 state · "开始生成" CTA 显式触发 */
  const handleSelectHistory = useCallback((key: string) => {
    setHistoryChoice(key);
  }, []);

  const handleSelectTemplate = useCallback((tpl: string) => {
    setTemplateChoice(tpl);
  }, []);

  /* "开始生成" CTA · 综合用户当前选择决定 mock vs live · 显式 button click 触发 started + 真 fire SSE */
  const handleApplyLaunch = useCallback(() => {
    /* 优先级:
       1) historyChoice 选了 → mock 模式 + 立刻 triggerV16Fill (explicit_mock=true · 后端走 mock pipeline · sections hydrate)
       2) templateChoice 选了 (含上传) → live 模式 + 立刻 triggerV16Fill (explicit_mock=false)
       3) 都没选 → 不动 (button disabled) */
    if (historyChoice) {
      const mid = `mock-${historyChoice}-${Date.now()}`;
      setMode("mock");
      setStarted(true);
      setReportId(mid);
      // 真 fire SSE → backend /v16/fill explicit_mock · liveData + sections hydrate · 主列不再空白
      // pass reportIdOverride 因 setReportId 异步 · closure 里 reportId 仍是旧值
      setTimeout(() => triggerV16Fill({ reportIdOverride: mid, explicitMock: true }), 0);
      return;
    }
    if (templateChoice) {
      setMode("live");
      setStarted(true);
      // live 路径 · 用现有 reportId (来自上传 · 没上传则 fill_stream 走 fail-banner)
      setTimeout(() => triggerV16Fill({ explicitMock: false }), 0);
    }
  }, [historyChoice, templateChoice, triggerV16Fill]);

  // W-FIX-A1 · live-fallback-banner-spec §3 规则 3: "上传模板" button 必 wire
  // 真后端·走同 /api/report/upload multipart endpoint·标 business_line=template
  const handleUploadTemplate = useCallback(
    async (files: File[]) => {
      if (!files.length) return;
      setErrMsg(null);
      try {
        const resp = await uploadReportMaterials(files, "corporate");
        // 模板单独存 · uploaded files 列表也 enrich
        setUploadedTemplate(resp.file_summary[0]?.name ?? files[0].name);
        if (!reportId) {
          setReportId(resp.report_id);
        }
        setMode("live");
        setStarted(true);
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        setErrMsg(msg);
        // upload endpoint live 失败 · 也算 banner 触发
        const statusMatch = /HTTP (\d{3})/.exec(msg);
        setLiveFailErr({
          endpoint: "/api/report/upload (template)",
          status: statusMatch ? statusMatch[1] : "network",
          message: msg,
        });
      }
    },
    [reportId],
  );

  const handleRefineSection = useCallback(
    async (sectionId: string, userEdit: string) => {
      const sid = liveData?.session_id;
      if (!sid) {
        setErrMsg("未拿到 session_id · 请先生成报告");
        return;
      }
      try {
        const resp = await refineReportSection({
          session_id: sid,
          section_id: sectionId,
          user_edit: userEdit,
        });
        setLiveData((prev) => {
          if (!prev) return prev;
          const sections: ReportV16Section[] = prev.sections ?? [];
          const idx = sections.findIndex((sec) => sec.id === sectionId);
          const newSections =
            idx >= 0
              ? sections.map((sec, i) => (i === idx ? resp.section : sec))
              : [...sections, resp.section];
          return { ...prev, sections: newSections };
        });
      } catch (e) {
        setErrMsg(e instanceof Error ? e.message : String(e));
      }
    },
    [liveData],
  );

  const handleExportDocx = useCallback(async () => {
    if (exporting) return;
    setExporting(true);
    setErrMsg(null);
    try {
      const payload: ReportExportPayload = liveData
        ? {
            session_id: liveData.session_id,
            sections: liveData.sections,
            pending_questions: liveData.pending_questions,
            stats: (liveData.stats ?? {}) as Record<string, unknown>,
            qc: (liveData.qc ?? {}) as Record<string, unknown>,
            business_line: businessLine,
            client_manager: "客户经理",
          }
        : {
            // 还没拿到 liveData · 用 REPORT_SESSION mock 兜底 export demo
            report_id: reportId || `demo-${Date.now()}`,
            profile: { company_name: REPORT_SESSION.clientName },
            sections: REPORT_SESSION.preview.map((p) => ({
              id: p.id,
              title: `${p.anchor} ${p.title}`,
              content: p.content || "(暂无内容)",
              status: "done" as const,
              word_count: (p.content ?? "").length,
            })),
            business_line: businessLine,
            client_manager: "客户经理 (示例)",
          };
      const { blob, filename } = await exportReportDocx(payload);
      triggerDownloadBlob(blob, filename);
    } catch (e) {
      setErrMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setExporting(false);
    }
  }, [exporting, liveData, businessLine, reportId]);

  /* Phase A worker-A4 · demo/run · scenario_id (easy/medium/hard) · 不调 LLM · 5 原则 §3.5 */
  const handleDemoRun = useCallback(
    (scenarioId: "easy" | "medium" | "hard") => {
      if (generating) return;
      setGenerating(true);
      setLiveStages([]);
      setLiveData(null);
      setErrMsg(null);
      setLiveFailErr(null);
      setStarted(true);
      setMode("mock");

      abortRef.current?.abort();
      const ac = new AbortController();
      abortRef.current = ac;

      streamReportDemoRun(
        { scenario_id: scenarioId },
        {
          signal: ac.signal,
          onEvent: (evt: ReportV16Event) => {
            if (evt.event === "stage") {
              setLiveStages((prev) => [...prev, evt as ReportV16StageEvent]);
            } else if (evt.event === "done") {
              const done = evt as ReportV16DoneEvent;
              setLiveData(done);
              if (done.session_id) setReportId(done.session_id);
            } else if (evt.event === "error") {
              setErrMsg((evt as ReportV16ErrorEvent).message);
            }
          },
          onClose: () => setGenerating(false),
          onError: (e) => {
            setErrMsg(e.message);
            setGenerating(false);
          },
        },
      );
    },
    [generating],
  );

  /* G-10 闭环 · export PDF 真接 · 与 export Word 同源 payload · pdf 走 reportlab */
  const handleExportPdf = useCallback(async () => {
    if (exportingPdf) return;
    setExportingPdf(true);
    setErrMsg(null);
    try {
      const payload: ReportExportPayload = liveData
        ? {
            session_id: liveData.session_id,
            sections: liveData.sections,
            pending_questions: liveData.pending_questions,
            stats: (liveData.stats ?? {}) as Record<string, unknown>,
            qc: (liveData.qc ?? {}) as Record<string, unknown>,
            business_line: businessLine,
            client_manager: "客户经理",
          }
        : {
            report_id: reportId || `demo-${Date.now()}`,
            profile: { company_name: REPORT_SESSION.clientName },
            sections: REPORT_SESSION.preview.map((p) => ({
              id: p.id,
              title: `${p.anchor} ${p.title}`,
              content: p.content || "(暂无内容)",
              status: "done" as const,
              word_count: (p.content ?? "").length,
            })),
            business_line: businessLine,
            client_manager: "客户经理 (示例)",
          };
      const { blob, filename } = await exportReportPdf(payload);
      triggerDownloadBlob(blob, filename);
    } catch (e) {
      setErrMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setExportingPdf(false);
    }
  }, [exportingPdf, liveData, businessLine, reportId]);

  const lastStage = liveStages.length
    ? liveStages[liveStages.length - 1]
    : null;

  return (
    <EvidenceProvider
      items={REPORT_EVIDENCE.items}
      unfilledFields={REPORT_EVIDENCE.unfilledFields}
    >
      <div
        data-view="archive-report"
        data-started={started ? "yes" : "no"}
        data-mode={mode}
        data-scanned={started ? "yes" : "no"} /* legacy attr · 保留向后兼容 */
      >
        <ReportHero coverPct={coverPct} sessionData={sessionData} />
        <ReportLiveFailBanner
          err={liveFailErr}
          onRetry={() => triggerV16Fill()}
          onDismiss={() => setLiveFailErr(null)}
        />
        {/* B-banner · LaunchBar errMsg 提到 workspace 顶部 · 与 ReportLiveFailBanner 同位 */}
        <ReportLaunchErrorBanner
          errMsg={errMsg}
          onRetry={() => triggerV16Fill()}
          onDismiss={() => setErrMsg(null)}
        />
        <ReportMockBanner started={started} mode={mode} />
        <ReportLaunchBar
          started={started}
          mode={mode}
          reportId={reportId}
          businessLine={businessLine}
          templateChoice={templateChoice}
          historyChoice={historyChoice}
          uploadedFiles={uploadedFiles}
          generating={generating}
          exporting={exporting}
          errMsg={errMsg}
          onUpload={handleUpload}
          onSelectTemplate={handleSelectTemplate}
          onSelectHistory={handleSelectHistory}
          onApplyLaunch={handleApplyLaunch}
          onBusinessLineChange={setBusinessLine}
          onStartGenerate={() => triggerV16Fill()}
          onExport={handleExportDocx}
        />
        {/* Phase A worker-A4 · 3-档 demo CTA · 5 原则 §3.5 难度分层 · 不调 LLM · 客户走访稳定 */}
        <ReportDemoStrip onRun={handleDemoRun} disabled={generating} />
        {started ? (
          <>
            {liveStages.length > 0 || liveData ? (
              <ReportLiveStrip
                stages={liveStages}
                lastStage={lastStage}
                done={liveData}
                generating={generating}
                mode={mode}
              />
            ) : null}
            <ReportPipelineBand sessionData={sessionData} />
            <div className="rpt-body">
              <aside className="rpt-side">
                <TemplatePanel
                  onUploadTemplate={handleUploadTemplate}
                  uploadedTemplate={uploadedTemplate}
                  sessionData={sessionData}
                />
                <MaterialPanel mode={mode} sessionData={sessionData} />
                <TimelinePanel mode={mode} sessionData={sessionData} />
              </aside>
              <main className="rpt-main">
                {/* B-cta · maxWidth 480 → 320 收紧 · 居中 · 解决 RM 抱怨"巨大不合理交互按钮" */}
                <div
                  data-testid="report-scancta-wrapper"
                  style={{ maxWidth: 320, margin: "0 auto 16px auto" }}
                >
                  <ScanCTA
                    label="生成报告 (mock 路径)"
                    tone="report"
                    onDone={() => triggerV16Fill({ explicitMock: true })}
                    steps={[
                      { label: "解析企业材料 · OCR 识别", pct: 18 },
                      { label: "字段结构化预填", pct: 42 },
                      { label: "段落 Evidence-First 生成", pct: 66 },
                      { label: "QC 终审 · 占位符检查", pct: 88 },
                      { label: "导出 Word · 完成", pct: 100 },
                    ]}
                  />
                </div>
                <ConversationPanel sessionData={sessionData}>
                  <ReportComposer sessionData={sessionData} />
                </ConversationPanel>
                {liveData?.sections && liveData.sections.length > 0 ? (
                  <ReportLiveSections
                    sections={liveData.sections}
                    onRefine={handleRefineSection}
                    mode={mode}
                  />
                ) : null}
              </main>
              <aside className="rpt-aux">
                <PreviewPanel
                  coverPct={coverPct}
                  mode={mode}
                  sessionData={sessionData}
                  isLive={derivedFromLive !== null}
                  selectedSection={selectedSection}
                  onSelectSection={setSelectedSection}
                  onExportDocx={handleExportDocx}
                  onExportPdf={handleExportPdf}
                  exporting={exporting}
                  exportingPdf={exportingPdf}
                />
                {/* Sprint 5 D3 · Truth-First 字段清单 drawer (Codex+Claude R1 minimal · per CLAUDE.md §3.1 确定性 vs 概率性硬隔离)
                    审贷员可一眼看哪些字段是 Python 规则计算 (truth-first · 不可幻觉) vs LLM 生成 (概率 · 需 evidence) */}
                <details
                  className="report-truth-first-drawer"
                  data-testid="report-truth-first-drawer"
                >
                  <summary>Truth-First 字段清单 · 审贷员核对</summary>
                  <dl className="report-truth-first-drawer__list">
                    <dt data-kind="truth">资产负债率</dt>
                    <dd>Python 计算 · 总负债 / 总资产 · 确定性</dd>
                    <dt data-kind="truth">流动比率</dt>
                    <dd>Python 计算 · 流动资产 / 流动负债 · 确定性</dd>
                    <dt data-kind="truth">净利润同比</dt>
                    <dd>Python 计算 · (本期 - 上期) / 上期 · 确定性</dd>
                    <dt data-kind="truth">应收账款周转天数</dt>
                    <dd>Python 计算 · 应收账款 / 营业收入 × 365 · 确定性</dd>
                    <dt data-kind="truth">行业基准对比</dt>
                    <dd>industry_benchmark.py · 行业卡 lookup · 确定性</dd>
                    <dt data-kind="llm">行业意见</dt>
                    <dd>LLM grounded · 证据来自材料锚定 · 概率</dd>
                    <dt data-kind="llm">经营风险点</dt>
                    <dd>LLM grounded · Evidence-First 三阶段 · 概率</dd>
                    <dt data-kind="llm">话术建议</dt>
                    <dd>LLM grounded · few-shot · 概率</dd>
                  </dl>
                  <p className="report-truth-first-drawer__note">
                    Truth-First 字段不可被 LLM 覆盖 · QC blocker 阻断 · 见 CLAUDE.md §3.1 + truth_fill.py
                  </p>
                </details>
              </aside>
            </div>
            <section
              className="ev-claim-summary"
              aria-label="Evidence-grounded 分析结论"
            >
              <span className="ev-claim-summary-label">
                分析结论 · Evidence-grounded
              </span>
              <ClaimText text={REPORT_EVIDENCE.summary} />
            </section>
          </>
        ) : (
          <ReportEmptySkeleton />
        )}
        <ReportStatusPill
          llmConnected={llmConnected}
          mode={mode}
          reportId={reportId}
          generating={generating}
          stage={lastStage?.stage}
        />
      </div>
    </EvidenceProvider>
  );
}

/* ── Hero ────────────────────────────────────────────── */

function ReportHero({ coverPct, sessionData }: { coverPct: number; sessionData: ReportSession }) {
  const s = sessionData;
  return (
    <header className="rpt-hero">
      <div className="rpt-hero-left">
        <div className="rpt-hero-badge" aria-hidden>◧</div>
        <div>
          {/* PM bug #3 fix · hero code 中文优先 · 英文 codename 保留 */}
          <div className="rpt-hero-code">AGENT · 06 · 报告 Press</div>
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

function ReportPipelineBand({ sessionData }: { sessionData: ReportSession }) {
  const s = sessionData;
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

function TemplatePanel(props: {
  onUploadTemplate?: (files: File[]) => void;
  uploadedTemplate?: string;
  sessionData: ReportSession;
}) {
  const tpl = props.sessionData.template;
  const avail = props.sessionData.availableTemplates;
  const cov = props.sessionData.coverage;
  const pct = Math.round((cov.filled / Math.max(cov.total, 1)) * 100);
  const R = 26;
  const CIRC = 2 * Math.PI * R;
  const FILL = (pct / 100) * CIRC;
  // W-FIX-A1 · live-fallback-banner-spec §3 · "上传模板" 真 wire file input
  const tplInputRef = useRef<HTMLInputElement | null>(null);
  function handleTplFileChange(e: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    if (files.length && props.onUploadTemplate) {
      props.onUploadTemplate(files);
    }
    e.target.value = "";
  }

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
          <button
            className="rpt-btn rpt-btn--ghost"
            type="button"
            data-testid="report-upload-template-cta"
            onClick={() => tplInputRef.current?.click()}
          >
            <span aria-hidden>⇪</span>上传模板
          </button>
          <input
            ref={tplInputRef}
            type="file"
            hidden
            accept=".docx,.doc"
            onChange={handleTplFileChange}
          />
          {/* B-cta · 模板库 disabled placeholder button 删除 (CLAUDE.md "no fake placeholder buttons")
              原 disabled + tooltip 是 "Stage X 计划" 占位 · 用户视觉上 = 摆设 · 此次去掉 */}
        </div>
        {props.uploadedTemplate ? (
          <div
            data-testid="report-uploaded-template-name"
            style={{
              marginTop: 6,
              padding: "4px 8px",
              fontSize: 11,
              color: "var(--ink-65)",
              background: "color-mix(in srgb, var(--t-report) 10%, transparent)",
              borderRadius: 4,
              fontFamily: "var(--cjk)",
            }}
          >
            ✓ 已上传 {props.uploadedTemplate}
          </div>
        ) : null}
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

function MaterialPanel({ mode, sessionData }: { mode: "mock" | "live"; sessionData: ReportSession }) {
  const mats = sessionData.materials;
  const parsed = mats.filter((m) => m.parsed).length;
  const pending = mats.length - parsed;
  return (
    <section
      className="rpt-panel rpt-panel--mat"
      data-testid="report-pilot-materials"
      data-mode={mode}
    >
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

function TimelinePanel({ mode, sessionData }: { mode: "mock" | "live"; sessionData: ReportSession }) {
  const evs = sessionData.timeline;
  const recent = sessionData.recentSessions;
  return (
    <section
      className="rpt-panel rpt-panel--tl"
      data-testid="report-pilot-timeline"
      data-mode={mode}
    >
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
          defaultValue={sessionData.id}
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

function ConversationPanel({ children, sessionData }: { children?: React.ReactNode; sessionData: ReportSession }) {
  const msgs = sessionData.conversation;
  const s = sessionData;
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
  /* PM bug #3 · P1 · 改 useAuthStore 动态 user */
  const u = useAuthStore((s) => s.currentUser);
  const userName = u?.name ?? "未登录";
  const userTeam = u?.team ?? "—";
  const userAvatar = u?.avatar || userName.slice(0, 1);
  return (
    <li className="rpt-msg rpt-msg--user">
      <MessagePinHandle {...msgPinProps(msg, userName)} />
      <div className="rpt-msg-body rpt-msg-body--user">
        <div className="rpt-msg-meta rpt-msg-meta--user">
          <span className="rpt-msg-at">{msg.at}</span>
          <span className="rpt-msg-who">{userTeam} · {userName}</span>
        </div>
        <div className="rpt-msg-card rpt-msg-card--user">{msg.content}</div>
      </div>
      <div className="rpt-msg-avatar rpt-msg-avatar--user" aria-hidden>
        {userAvatar}
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

function ReportComposer({ sessionData }: { sessionData: ReportSession }) {
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

  // pin-drop · 拖钉到 composer · 插入 `@引用:<title> ` · 不再让 textarea 吞 URL
  const onPin = (payload: PinDropPayload) => {
    setValue((v) => (v ? `${v} @引用:${payload.title} ` : `@引用:${payload.title} `));
  };
  const drop = usePinDrop<HTMLDivElement>(onPin);

  const materialCount = sessionData.materials.length;
  const sectionCount = sessionData.preview.length;

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

function PreviewPanel({
  coverPct,
  mode,
  sessionData,
  isLive,
  selectedSection,
  onSelectSection,
  onExportDocx,
  onExportPdf,
  exporting,
  exportingPdf,
}: {
  coverPct: number;
  mode: "mock" | "live";
  sessionData: ReportSession;
  isLive: boolean;
  selectedSection: string | null;
  onSelectSection: (id: string | null) => void;
  onExportDocx: () => void;
  onExportPdf: () => void;
  exporting: boolean;
  exportingPdf: boolean;
}) {
  /* V2 issue 1 fix · 5 panel sessionData = liveData ?? mock 单点派生 ·
     PreviewPanel 直接消费 sessionData.preview · liveData 命中时 derivedFromLive 已
     替换 sections (liveToReportSession 处理) · isLive 由父组件 derivedFromLive!==null 决定 */
  const s = sessionData;
  const sections = s.preview;
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeAnchor, setActiveAnchor] = useState<string>(sections[0]?.anchor ?? "§一");

  function scrollTo(id: string) {
    onSelectSection(id);
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
    <section
      className="rpt-panel rpt-panel--preview"
      data-testid="report-pilot-preview"
      data-mode={isLive ? "live" : mode}
      data-selected-section={selectedSection ?? ""}
    >
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

      <div
        className="rpt-pv-toolbar"
        role="toolbar"
        aria-label="导出 / 分享 / 版本 / 打印"
        data-testid="report-pilot-toolbar"
      >
        {/* Phase A worker-A4 · Word + PDF + Print 真接 · 分享 / 版本 标 Phase B carve-out
            理由 (V2 codex audit · 2026-04-29):
              - 分享链接 (/api/report/share) 需做权限/有效期/水印/PII 拦截 · 涉及 RBAC 接入 ·
                Phase B 与统一登录/审计平台联动落地
              - 版本时光机 (/api/report/versions) 需 docx diff + draft 历史持久 ·
                Phase B 接知识库存储 (data/audit/versions/) 后开
              - 当前 Phase A G-10 acceptable carve-out · Word + PDF 闭环已满足"客户带走" 的 KRR
            两按钮 disabled + aria-disabled · 视觉占位 · 不诈骗用户. */}
        <button
          type="button"
          className="rpt-pv-btn"
          title="下载 Word (.docx)"
          data-testid="report-toolbar-word"
          onClick={onExportDocx}
          disabled={exporting}
        >
          <span className="ic" aria-hidden>⇩</span>
          <span>{exporting ? "导出中…" : "Word"}</span>
        </button>
        <button
          type="button"
          className="rpt-pv-btn"
          title="导出 PDF (G-10)"
          data-testid="report-toolbar-pdf"
          onClick={onExportPdf}
          disabled={exportingPdf}
        >
          <span className="ic" aria-hidden>⇩</span>
          <span>{exportingPdf ? "导出中…" : "PDF"}</span>
        </button>
        <button
          type="button"
          className="rpt-pv-btn"
          title="生成只读分享链接 (Phase B)"
          data-testid="report-toolbar-share"
          disabled
          aria-disabled
        >
          <span className="ic" aria-hidden>↗</span>
          <span>分享</span>
        </button>
        <button
          type="button"
          className="rpt-pv-btn"
          title="版本时光机 · 对比历史稿 (Phase B)"
          data-testid="report-toolbar-version"
          disabled
          aria-disabled
        >
          <span className="ic" aria-hidden>⟳</span>
          <span>版本</span>
        </button>
        <button
          type="button"
          className="rpt-pv-btn"
          title="打印预览"
          data-testid="report-toolbar-print"
          onClick={() => window.print()}
        >
          <span className="ic" aria-hidden>⎙</span>
          <span>打印</span>
        </button>
      </div>

      <nav className="rpt-pv-toc" aria-label="章节目录">
        {sections.map((sec) => (
          <button
            key={sec.id}
            type="button"
            className={
              activeAnchor === sec.anchor || selectedSection === sec.id
                ? "on"
                : undefined
            }
            data-status={sec.status}
            data-testid={`report-section-toc-${sec.id}`}
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
      <div
        className="rpt-pv-fields"
        role="list"
        data-testid={`report-pilot-fields-${section.id}`}
      >
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
    <div
      className="rpt-pv-fc"
      data-testid="report-pilot-fieldchip"
      data-state={field.state}
      data-qc={field.qc?.level}
      role="listitem"
    >
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

/* ────────────────────────────────────────────────────────────────────────── */
/*  W-CF-A1 · Stage C frontend · empty-state-design-protocol v1.0 兼容组件    */
/*  ReportLaunchBar / ReportEmptySkeleton / ReportStatusPill / ReportLiveStrip */
/*  ReportLiveSections                                                        */
/* ────────────────────────────────────────────────────────────────────────── */

const _LAUNCH_ROOT_STYLE: CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: 14,
  alignItems: "flex-end",
  padding: "16px 20px",
  margin: "16px 0",
  background: "color-mix(in srgb, var(--chalk) 60%, transparent)",
  border: "1px solid var(--ink-14)",
  borderRadius: "var(--r-md)",
};

const _LAUNCH_GROUP_STYLE: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 4,
  minWidth: 160,
};

const _LAUNCH_LABEL_STYLE: CSSProperties = {
  fontFamily: "var(--cjk)",
  fontSize: 11,
  letterSpacing: ".04em",
  color: "var(--ink-65)",
  textTransform: "uppercase",
};

const _LAUNCH_HINT_STYLE: CSSProperties = {
  fontFamily: "var(--cjk)",
  fontSize: 11,
  color: "var(--ink-65)",
  marginTop: 2,
};

/* B-cta · chip-style 紧凑 · 单按钮 ≤ 200px · 不充满列宽
   primary 上传材料 / secondary 重新生成+导出 一致紧凑 · 解决 RM 抱怨"巨大不合理交互按钮" */
const _LAUNCH_BTN_PRIMARY: CSSProperties = {
  fontFamily: "var(--cjk)",
  fontSize: 13,
  padding: "8px 14px",
  background: "var(--t-report)",
  color: "var(--chalk)",
  border: "none",
  borderRadius: "var(--r-md)",
  cursor: "pointer",
  fontWeight: 500,
  maxWidth: 200,
  whiteSpace: "nowrap",
};

const _LAUNCH_BTN_SECONDARY: CSSProperties = {
  fontFamily: "var(--cjk)",
  fontSize: 12,
  padding: "6px 12px",
  background: "transparent",
  color: "var(--ink)",
  border: "1px solid var(--ink-14)",
  borderRadius: "var(--r-md)",
  cursor: "pointer",
  maxWidth: 200,
  whiteSpace: "nowrap",
};

const _LAUNCH_SELECT_STYLE: CSSProperties = {
  fontFamily: "var(--cjk)",
  fontSize: 13,
  padding: "7px 10px",
  background: "var(--chalk)",
  color: "var(--ink)",
  border: "1px solid var(--ink-14)",
  borderRadius: "var(--r-md)",
  cursor: "pointer",
};

/* Phase A worker-A4 (2026-04-29) · 3-档 demo CTA · scenario_id easy/medium/hard
   反 5 原则 §3.5 难度分层 · 不调 LLM · 客户走访稳定 demo 路径 · POST /api/report/demo/run */
function ReportDemoStrip({
  onRun,
  disabled,
}: {
  onRun: (scenarioId: "easy" | "medium" | "hard") => void;
  disabled: boolean;
}) {
  const btnStyle: CSSProperties = {
    fontFamily: "var(--cjk)",
    fontSize: 12,
    padding: "6px 12px",
    background: "transparent",
    color: "var(--ink)",
    border: "1px solid var(--ink-14)",
    borderRadius: "var(--r-md)",
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.5 : 1,
    whiteSpace: "nowrap",
  };
  return (
    <section
      data-testid="report-demo-strip"
      style={{
        margin: "12px 0",
        padding: "10px 16px",
        background: "color-mix(in srgb, var(--chalk) 60%, transparent)",
        border: "1px dashed var(--ink-14)",
        borderRadius: "var(--r-md)",
        display: "flex",
        gap: 12,
        alignItems: "center",
        fontFamily: "var(--cjk)",
        fontSize: 12,
        color: "var(--ink)",
      }}
      aria-label="演示数据 · 难度分层"
    >
      <span style={{ color: "var(--ink-65)", textTransform: "uppercase", letterSpacing: ".04em", fontSize: 10 }}>
        演示模式 · 5 原则 §3.5
      </span>
      <button
        type="button"
        data-testid="report-demo-easy"
        style={btnStyle}
        disabled={disabled}
        onClick={() => onRun("easy")}
      >
        简单 · 材料齐全
      </button>
      <button
        type="button"
        data-testid="report-demo-medium"
        style={btnStyle}
        disabled={disabled}
        onClick={() => onRun("medium")}
      >
        中等 · 部分缺
      </button>
      <button
        type="button"
        data-testid="report-demo-hard"
        style={btnStyle}
        disabled={disabled}
        onClick={() => onRun("hard")}
      >
        困难 · QC 阻断
      </button>
      <span style={{ marginLeft: "auto", color: "var(--ink-65)", fontSize: 11, fontStyle: "italic" }}>
        不调 LLM · 客户走访稳定路径
      </span>
    </section>
  );
}

function ReportLaunchBar(p: {
  started: boolean;
  mode: "mock" | "live";
  reportId: string;
  businessLine: string;
  templateChoice: string;
  historyChoice: string;
  uploadedFiles: string[];
  generating: boolean;
  exporting: boolean;
  errMsg: string | null;
  onUpload: (files: File[]) => void;
  onSelectTemplate: (tpl: string) => void;
  onSelectHistory: (key: string) => void;
  onApplyLaunch: () => void;
  onBusinessLineChange: (v: string) => void;
  onStartGenerate: () => void;
  onExport: () => void;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const histories = REPORT_SESSION.recentSessions;
  const templates = REPORT_SESSION.availableTemplates;

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    if (files.length) p.onUpload(files);
    e.target.value = "";
  }

  return (
    <section
      data-testid="report-launch-bar"
      style={_LAUNCH_ROOT_STYLE}
      aria-label="报告生成 · 触发入口"
    >
      {/* Primary: 上传材料 */}
      <div style={_LAUNCH_GROUP_STYLE}>
        <span style={_LAUNCH_LABEL_STYLE}>主入口</span>
        <button
          type="button"
          data-testid="report-upload-cta"
          onClick={() => inputRef.current?.click()}
          style={_LAUNCH_BTN_PRIMARY}
        >
          ⇪ 上传材料文件
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          hidden
          accept=".pdf,.docx,.doc,.xlsx,.xls,.txt,.jpg,.jpeg,.png"
          onChange={handleFileChange}
        />
        <span style={_LAUNCH_HINT_STYLE}>
          {p.uploadedFiles.length > 0
            ? `已上传 ${p.uploadedFiles.length} 份`
            : "PDF / Word / Excel / 图片 · 多文件"}
        </span>
      </div>

      {/* Secondary: 模板选择 */}
      <div style={_LAUNCH_GROUP_STYLE}>
        <span style={_LAUNCH_LABEL_STYLE}>模板</span>
        <select
          data-testid="report-template-select"
          value={p.templateChoice}
          onChange={(e) => p.onSelectTemplate(e.target.value)}
          style={_LAUNCH_SELECT_STYLE}
        >
          <option value="">默认 (按业务线)</option>
          {templates.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name} · {t.version}
            </option>
          ))}
        </select>
        <span style={_LAUNCH_HINT_STYLE}>选模板或留默认</span>
      </div>

      {/* Tertiary: 历史 dropdown · 标 (示例) */}
      <div style={_LAUNCH_GROUP_STYLE}>
        <span style={_LAUNCH_LABEL_STYLE}>
          历史 (示例 · 仅培训演示)
        </span>
        <select
          data-testid="report-history-dropdown"
          value={p.historyChoice}
          onChange={(e) => p.onSelectHistory(e.target.value)}
          style={{
            ..._LAUNCH_SELECT_STYLE,
            color: "var(--ink-65)",
            fontStyle: "italic",
          }}
        >
          <option value="">— 选择 —</option>
          {histories.map((r) => (
            <option key={r.id} value={r.id}>
              {r.clientName}（示例）
            </option>
          ))}
        </select>
        <span style={_LAUNCH_HINT_STYLE}>降级路径 · 显式 mock data</span>
      </div>

      {/* 业务线 segment */}
      <div style={_LAUNCH_GROUP_STYLE}>
        <span style={_LAUNCH_LABEL_STYLE}>业务线</span>
        <select
          data-testid="report-business-line-select"
          value={p.businessLine}
          onChange={(e) => p.onBusinessLineChange(e.target.value)}
          style={_LAUNCH_SELECT_STYLE}
        >
          <option value="corporate">对公</option>
          <option value="inclusive">普惠 / 个体</option>
          <option value="reserved">预留</option>
        </select>
      </div>

      {/* B-2 click-to-fire · !started 时显式 "开始生成" 应用模板/历史选择
          started 时切到 "重新生成 / 导出" 双 chip-style 按钮 */}
      {!p.started ? (
        <div style={{ ..._LAUNCH_GROUP_STYLE, flexDirection: "row", gap: 8 }}>
          <button
            type="button"
            data-testid="report-apply-launch-btn"
            onClick={p.onApplyLaunch}
            disabled={!p.templateChoice && !p.historyChoice}
            style={{
              ..._LAUNCH_BTN_SECONDARY,
              borderColor: "var(--t-report)",
              color: "var(--t-report)",
              opacity: !p.templateChoice && !p.historyChoice ? 0.5 : 1,
            }}
          >
            开始生成
          </button>
        </div>
      ) : (
        <div style={{ ..._LAUNCH_GROUP_STYLE, flexDirection: "row", gap: 8 }}>
          <button
            type="button"
            data-testid="report-generate-btn"
            onClick={p.onStartGenerate}
            disabled={p.generating}
            style={{
              ..._LAUNCH_BTN_SECONDARY,
              borderColor: "var(--t-report)",
              color: "var(--t-report)",
              opacity: p.generating ? 0.6 : 1,
            }}
          >
            {p.generating ? "生成中…" : "重新生成"}
          </button>
          <button
            type="button"
            data-testid="report-export-btn"
            onClick={p.onExport}
            disabled={p.exporting}
            style={{
              ..._LAUNCH_BTN_SECONDARY,
              opacity: p.exporting ? 0.6 : 1,
            }}
          >
            {p.exporting ? "导出中…" : "导出 Word"}
          </button>
        </div>
      )}

      {/* B-banner · errMsg 已提到 workspace 顶部 ReportLaunchErrorBanner · 此处不再 inline */}
    </section>
  );
}

/* B-banner · launch 错误 (上传 / 生成 / 导出 / refine) · 顶部贴边显式
   · 与 ReportLiveFailBanner 区分: live banner 是 fallback warning · 此为 actionable error */
function ReportLaunchErrorBanner(p: {
  errMsg: string | null;
  onRetry: () => void;
  onDismiss: () => void;
}) {
  if (!p.errMsg) return null;
  return (
    <section
      data-testid="report-launch-error-banner"
      role="alert"
      aria-live="assertive"
      style={{
        margin: "16px 0",
        padding: "12px 16px",
        background: "rgba(200, 90, 60, 0.10)",
        border: "1px solid rgba(200, 90, 60, 0.45)",
        borderRadius: "var(--r-md)",
        display: "flex",
        gap: 12,
        alignItems: "center",
        fontFamily: "var(--cjk)",
        fontSize: 13,
        color: "var(--ink)",
      }}
    >
      <span aria-hidden style={{ fontSize: 18 }}>⚠️</span>
      <span style={{ flex: 1 }}>
        <strong>报告操作失败</strong>
        <br />
        <span style={{ fontSize: 11, color: "var(--ink-65)", fontStyle: "italic" }}>
          {p.errMsg}
        </span>
      </span>
      <button
        type="button"
        data-testid="report-launch-error-retry"
        onClick={p.onRetry}
        style={{
          padding: "6px 14px",
          fontFamily: "var(--cjk)",
          fontSize: 12,
          background: "var(--t-report)",
          color: "var(--chalk)",
          border: "none",
          borderRadius: "var(--r-md)",
          cursor: "pointer",
        }}
      >
        重试
      </button>
      <button
        type="button"
        data-testid="report-launch-error-dismiss"
        onClick={p.onDismiss}
        aria-label="关闭"
        style={{
          padding: "4px 10px",
          fontFamily: "var(--cjk)",
          fontSize: 16,
          background: "transparent",
          color: "var(--ink-65)",
          border: "none",
          cursor: "pointer",
        }}
      >
        ×
      </button>
    </section>
  );
}

/* W-FIX-A1 · mock banner 提取为 root-level 组件 · 跟 LiveFailBanner / Hero 对齐
   live-fallback-banner-spec §2 规则 2 + §3 排版硬线 (margin 16px 0 一致) */
function ReportMockBanner(p: { started: boolean; mode: "mock" | "live" }) {
  if (!p.started || p.mode !== "mock") return null;
  return (
    <section
      data-testid="report-mock-banner"
      role="status"
      style={{
        margin: "16px 0",
        padding: "10px 16px",
        fontFamily: "var(--cjk)",
        fontSize: 12,
        color: "var(--ink)",
        background: "rgba(180, 140, 60, 0.10)",
        border: "1px dashed rgba(180, 140, 60, 0.45)",
        borderRadius: "var(--r-md)",
        display: "flex",
        alignItems: "center",
        gap: 10,
      }}
    >
      <span aria-hidden style={{ fontSize: 16 }}>⚠️</span>
      <span style={{ flex: 1 }}>
        您正在查看 <strong>示例数据 (training mode)</strong>
        {" · "}切真实路径请上传材料触发 v16 主管线
      </span>
    </section>
  );
}

/* ────────────────────────────────────────────────────────────────────────── */
/*  W-FIX-A1 · live-fallback-banner-spec v1.0 §2 规则 1 · live mode 失败 banner */
/*  顶部 alarm + endpoint + status + retry CTA · empty-state §1.5 配套规范      */
/* ────────────────────────────────────────────────────────────────────────── */

function ReportLiveFailBanner(p: {
  err: { endpoint: string; status: string; message: string } | null;
  onRetry: () => void;
  onDismiss: () => void;
}) {
  if (!p.err) return null;
  return (
    <section
      data-testid="report-live-fail-banner"
      role="alert"
      aria-live="assertive"
      style={{
        margin: "16px 0",
        padding: "12px 16px",
        background: "rgba(200, 90, 60, 0.10)",
        border: "1px solid rgba(200, 90, 60, 0.45)",
        borderRadius: "var(--r-md)",
        display: "flex",
        gap: 12,
        alignItems: "center",
        fontFamily: "var(--cjk)",
        fontSize: 13,
        color: "var(--ink)",
      }}
    >
      <span aria-hidden style={{ fontSize: 18 }}>⚠️</span>
      <span style={{ flex: 1 }}>
        <strong>后端 <code style={{ fontSize: 12 }}>{p.err.endpoint}</code> 调用失败</strong>
        {" "}
        <span style={{ color: "var(--ink-65)" }}>
          ({p.err.status}) · 当前显 fallback 演示数据
        </span>
        <br />
        <span style={{ fontSize: 11, color: "var(--ink-65)", fontStyle: "italic" }}>
          {p.err.message}
        </span>
      </span>
      <button
        type="button"
        data-testid="report-live-fail-retry"
        onClick={p.onRetry}
        style={{
          padding: "6px 14px",
          fontFamily: "var(--cjk)",
          fontSize: 12,
          background: "var(--t-report)",
          color: "var(--chalk)",
          border: "none",
          borderRadius: "var(--r-md)",
          cursor: "pointer",
        }}
      >
        重试
      </button>
      <button
        type="button"
        data-testid="report-live-fail-dismiss"
        onClick={p.onDismiss}
        aria-label="关闭"
        style={{
          padding: "4px 8px",
          fontFamily: "var(--cjk)",
          fontSize: 12,
          background: "transparent",
          color: "var(--ink-65)",
          border: "1px solid var(--ink-14)",
          borderRadius: "var(--r-md)",
          cursor: "pointer",
        }}
      >
        ✕
      </button>
    </section>
  );
}

function ReportEmptySkeleton() {
  return (
    <section
      data-testid="report-empty-skeleton"
      aria-label="等待触发 · 报告生成"
      style={{
        padding: "48px 24px",
        textAlign: "center",
        background: "color-mix(in srgb, var(--chalk) 50%, transparent)",
        borderRadius: "var(--r-md)",
        border: "1px dashed var(--ink-14)",
        margin: "24px 0 64px 0",
        minHeight: "calc(100vh - 360px)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <h3
        style={{
          fontFamily: "var(--display)",
          fontSize: 20,
          color: "var(--ink)",
          fontWeight: 500,
          margin: "0 0 14px 0",
          letterSpacing: ".02em",
        }}
      >
        等待触发
      </h3>
      <p
        style={{
          fontFamily: "var(--cjk)",
          fontSize: 14,
          color: "var(--ink-65)",
          lineHeight: 1.7,
          maxWidth: 520,
          margin: "0 auto 12px auto",
        }}
      >
        上传客户
        <strong style={{ color: "var(--t-report)" }}>原始材料</strong>
        触发 v16 主管线（classifier → generator → QC gate）· 或选
        <strong style={{ color: "var(--ink)" }}>历史会话</strong>
        看示例演示。
      </p>
      <ul
        style={{
          listStyle: "none",
          padding: 0,
          margin: "16px auto 0",
          maxWidth: 520,
          textAlign: "left",
          fontFamily: "var(--cjk)",
          fontSize: 12,
          color: "var(--ink-65)",
          lineHeight: 1.8,
        }}
      >
        <li>· 材料解析后此处显示 5 类槽位计数</li>
        <li>· 章节流式生成 · 4 chapter 渐进渲染</li>
        <li>· QC 9 维评分 · 通过后可导出 Word</li>
        <li>· 第 4 章「审批意见」预留 Agent3 决策回写</li>
      </ul>
    </section>
  );
}

const _STAGE_CN: Record<string, string> = {
  ingest: "材料解析",
  extract: "字段抽取",
  infer: "推断装载",
  write: "段落生成",
  audit: "QC 终审",
};

const _STATUS_PILL_STYLE: CSSProperties = {
  position: "fixed",
  right: 16,
  bottom: 16,
  zIndex: 30,
  display: "flex",
  alignItems: "center",
  gap: 8,
  padding: "8px 14px",
  background: "color-mix(in srgb, var(--chalk) 92%, transparent)",
  border: "1px solid var(--ink-14)",
  borderRadius: 999,
  fontFamily: "var(--cjk)",
  fontSize: 12,
  color: "var(--ink)",
  boxShadow: "0 4px 14px rgba(0,0,0,0.08)",
  pointerEvents: "auto",
};

function ReportStatusPill(p: {
  llmConnected: boolean | null;
  mode: "mock" | "live";
  reportId: string;
  generating: boolean;
  stage?: string;
}) {
  const llmDot =
    p.llmConnected === null ? "🟡" : p.llmConnected ? "🟢" : "🔴";
  const llmLbl =
    p.llmConnected === null
      ? "LLM 检测中"
      : p.llmConnected
        ? "LLM 已连"
        : "LLM 未连";
  const modeLbl = p.mode === "mock" ? "示例模式" : "真实模式";
  const stageLbl = p.generating && p.stage ? _STAGE_CN[p.stage] ?? p.stage : "";

  return (
    <div
      data-testid="report-status-pill"
      data-mode={p.mode}
      data-llm-connected={p.llmConnected ?? "unknown"}
      style={_STATUS_PILL_STYLE}
    >
      <span aria-hidden>{llmDot}</span>
      <span>{llmLbl}</span>
      <span style={{ color: "var(--ink-14)" }} aria-hidden>·</span>
      <span style={{ fontStyle: "italic" }}>{modeLbl}</span>
      {p.reportId ? (
        <>
          <span style={{ color: "var(--ink-14)" }} aria-hidden>·</span>
          <code
            style={{
              fontFamily: "var(--mono)",
              fontSize: 11,
              color: "var(--ink-65)",
            }}
          >
            {p.reportId.slice(0, 8)}
          </code>
        </>
      ) : null}
      {p.generating ? (
        <>
          <span style={{ color: "var(--ink-14)" }} aria-hidden>·</span>
          <span style={{ color: "var(--t-report)" }}>
            ⏳ {stageLbl || "生成中"}
          </span>
        </>
      ) : null}
    </div>
  );
}

function ReportLiveStrip(p: {
  stages: ReportV16StageEvent[];
  lastStage: ReportV16StageEvent | null;
  done: ReportV16DoneEvent | null;
  generating: boolean;
  mode: "mock" | "live";
}) {
  const allStages: ReportV16StageEvent["stage"][] = [
    "ingest",
    "extract",
    "infer",
    "write",
    "audit",
  ];
  const seen = new Set<ReportV16StageEvent["stage"]>(
    p.stages.map((s) => s.stage),
  );
  return (
    <section
      data-testid="report-live-strip"
      data-generating={p.generating ? "yes" : "no"}
      style={{
        margin: "12px 0",
        padding: "10px 16px",
        background: "color-mix(in srgb, var(--chalk) 70%, transparent)",
        border: "1px solid var(--ink-14)",
        borderRadius: "var(--r-md)",
        display: "flex",
        gap: 12,
        alignItems: "center",
        fontFamily: "var(--cjk)",
        fontSize: 12,
      }}
    >
      <span
        style={{
          color: "var(--ink-65)",
          textTransform: "uppercase",
          letterSpacing: ".04em",
          fontSize: 10,
        }}
      >
        v16 PIPELINE {p.mode === "mock" ? "· (mock)" : ""}
      </span>
      {allStages.map((st) => {
        const isDone = seen.has(st);
        const isActive = p.lastStage?.stage === st && p.generating;
        return (
          <span
            key={st}
            data-stage={st}
            data-state={isDone ? (isActive ? "active" : "done") : "pending"}
            style={{
              padding: "4px 10px",
              borderRadius: 999,
              background: isDone
                ? isActive
                  ? "var(--t-report)"
                  : "color-mix(in srgb, var(--t-report) 25%, transparent)"
                : "transparent",
              color: isDone && isActive ? "var(--chalk)" : "var(--ink)",
              border: "1px solid var(--ink-14)",
              fontSize: 11,
            }}
          >
            {_STAGE_CN[st] ?? st}
          </span>
        );
      })}
      {p.done ? (
        <span
          style={{
            marginLeft: "auto",
            color: p.done.qc?.passed
              ? "var(--t-compli, #4A7A5E)"
              : "var(--t-alert, #C85A3C)",
          }}
        >
          QC {p.done.qc?.passed ? "✓ 通过" : "△ 阻断"}
          {p.done.qc?.score !== undefined ? ` · ${p.done.qc.score}` : ""}
          {p.done.mock_pipeline ? " (mock)" : ""}
        </span>
      ) : null}
    </section>
  );
}

function ReportLiveSections(p: {
  sections: ReportV16Section[];
  onRefine: (sectionId: string, userEdit: string) => void;
  mode: "mock" | "live";
}) {
  const [activeId, setActiveId] = useState<string | null>(
    p.sections[0]?.id ?? null,
  );
  const [draft, setDraft] = useState<string>("");
  const active = p.sections.find((s) => s.id === activeId) ?? null;

  return (
    <section
      data-testid="report-live-sections"
      style={{
        marginTop: 16,
        padding: "12px 14px",
        background: "color-mix(in srgb, var(--chalk) 60%, transparent)",
        border: "1px solid var(--ink-14)",
        borderRadius: "var(--r-md)",
      }}
    >
      <header
        style={{
          display: "flex",
          gap: 10,
          alignItems: "baseline",
          marginBottom: 10,
        }}
      >
        <strong
          style={{
            fontFamily: "var(--display)",
            fontSize: 14,
          }}
        >
          v16 章节流 · {p.sections.length} 章
        </strong>
        {p.mode === "mock" ? (
          <span
            style={{
              fontSize: 11,
              color: "var(--ink-65)",
              fontStyle: "italic",
            }}
          >
            (示例 · refine 走 fallback 拼接)
          </span>
        ) : null}
      </header>
      <nav
        data-testid="report-section-nav"
        style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}
      >
        {p.sections.map((sec) => (
          <button
            key={sec.id}
            type="button"
            onClick={() => setActiveId(sec.id)}
            data-active={sec.id === activeId ? "yes" : "no"}
            style={{
              padding: "5px 10px",
              borderRadius: 999,
              border: "1px solid var(--ink-14)",
              background:
                sec.id === activeId
                  ? "color-mix(in srgb, var(--t-report) 28%, transparent)"
                  : "transparent",
              fontFamily: "var(--cjk)",
              fontSize: 11.5,
              cursor: "pointer",
            }}
          >
            {sec.title}
            {sec.status !== "done" ? ` · ${sec.status}` : ""}
          </button>
        ))}
      </nav>
      {active ? (
        <div
          data-testid="report-section-active"
          style={{
            padding: "10px 12px",
            background: "var(--chalk)",
            border: "1px solid var(--ink-14)",
            borderRadius: 6,
            fontFamily: "var(--cjk)",
            fontSize: 13,
            lineHeight: 1.65,
            whiteSpace: "pre-wrap",
            color: "var(--ink)",
          }}
        >
          {active.content}
        </div>
      ) : null}
      <div style={{ marginTop: 10 }}>
        <textarea
          data-testid="report-refine-input"
          rows={2}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="给客户经理引导 · LLM 重写本章 (示例: 强调财务比率 + 行业景气)"
          style={{
            width: "100%",
            padding: 8,
            border: "1px solid var(--ink-14)",
            borderRadius: 6,
            fontFamily: "var(--cjk)",
            fontSize: 12,
            background: "var(--chalk)",
            resize: "vertical",
          }}
        />
        <div style={{ marginTop: 6, textAlign: "right" }}>
          <button
            type="button"
            data-testid="report-refine-btn"
            disabled={!active || !draft.trim()}
            onClick={() => {
              if (!active || !draft.trim()) return;
              p.onRefine(active.id, draft.trim());
              setDraft("");
            }}
            style={{
              padding: "6px 12px",
              borderRadius: 6,
              border: "1px solid var(--ink-14)",
              background: "transparent",
              fontFamily: "var(--cjk)",
              fontSize: 12,
              cursor: "pointer",
              opacity: active && draft.trim() ? 1 : 0.5,
            }}
          >
            重写本章
          </button>
        </div>
      </div>
    </section>
  );
}
