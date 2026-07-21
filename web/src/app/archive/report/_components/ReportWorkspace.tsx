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
// Phase B.1.3 hotfix (PM 2026-05-10) · revert ModePill 双控 · PM 真意是上传sample跑真后端 · 不是切假按钮
import { DataSourceBadge } from "@/components/shared/DataSourceBadge";
import { type DataSourceKind } from "@/lib/api/_data-source";
import { usePinDrop, type PinDropPayload } from "@/components/composer/use-pin-drop";
import { MessagePinHandle } from "@/components/shell/MessagePinHandle";
import { ScanCTA } from "@/components/shared/ScanCTA";
import { CustomerSelector } from "@/components/shared/CustomerSelector";
import { PanelPinHandle } from "@/components/shell/PanelPinHandle";
import {
  deleteReportTemplate,
  exportReportDocx,
  exportReportPdf,
  listReportTemplates,
  refineReportSection,
  renameReportTemplate,
  streamReportDemoRun,
  streamReportV16Fill,
  triggerDownloadBlob,
  uploadReportMaterials,
  uploadReportTemplate,
  type ReportExportPayload,
  type ReportFileSummary,
  reportDoneDataSource,
  type ReportV16DoneEvent,
  type ReportV16ErrorEvent,
  type ReportV16Event,
  type ReportV16Evidence,
  type ReportV16Section,
  type ReportV16StageEvent,
  type TemplateListItem,
  type TemplateValidationReport,
} from "@/lib/api/report";
import { ClaimText, EvidenceProvider } from "@/components/evidence";
/* PM 2026-05-09 ALL IN Phase B.1 fix: 删 REPORT_EVIDENCE / REPORT_GLOBAL_STATS fixtures import
   假证据/假统计走 EMPTY 兜底 · 后端真出 evidences 时前端消费 (per shared/evidence_drawer schema). */
import {
  liveToReportSession,
  type ConversationMessage,
  type PreviewField,
  type PreviewSection,
  type ReportSession,
  type TimelineEvent,
} from "@/lib/mock/agent-report-session";

/* ALL IN Phase B.1 fix · EvidenceProvider items 空兜底 (后端真 evidences 走 EvidenceDrawer panel) */
const EMPTY_EVIDENCE_ITEMS: Array<{ source: string; snippet: string; ref_id: string; confidence: number }> = [];
const EMPTY_UNFILLED_FIELDS: string[] = [];
const EMPTY_CLAIM_SUMMARY = "";

/* ALL IN Phase B.1 fix · 全局统计 EMPTY 兜底 (后端真 stats endpoint 待 Phase C+) */
const EMPTY_GLOBAL_STATS = { weeklyProcessed: "—", successRate: "—", avgDuration: "—" };

const AGENT_KEY = "report";
const AGENT_HREF = "/archive/report";
const AGENT_ACCENT = "--t-report";

/* PM 2026-05-09 ALL IN 真产品 · sessionData fallback 用此空对象 · 不再 fallback 到 REPORT_SESSION mock.
   5 panel 消费时 .map / .find / .reduce 不 crash · 字段空 → 显空 / 0 / "—" 不显假数据.
   per channel ALL IN 模板 (de79725) + AGENT_IDENTITY-report.md §6 step 2 */
const EMPTY_SESSION: ReportSession = {
  id: "empty",
  clientName: "",
  amount: "",
  stage: "",
  updated: "",
  template: {
    id: "",
    name: "",
    kind: "预置",
    version: "",
    fieldTotal: 0,
    recentUsed: 0,
  },
  availableTemplates: [],
  materials: [],
  timeline: [],
  conversation: [],
  preview: [],
  coverage: { filled: 0, total: 0, marked: 0 },
  qcCounts: { block: 0, warn: 0, info: 0 },
  recentSessions: [],
};

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
  const [mode, setMode] = useState<"mock" | "live">("live");
  const [businessLine, setBusinessLine] = useState<string>("corporate");
  const [templateChoice, setTemplateChoice] = useState<string>("");

  // v16 fill / demo/run 流式状态 · liveData = gate 3 (workspace-state-protocol §2)
  const [liveStages, setLiveStages] = useState<ReportV16StageEvent[]>([]);
  const [liveData, setLiveData] = useState<ReportV16DoneEvent | null>(null);
  const [generating, setGenerating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);

  // gate 4 · selectedSection · TOC click 切章节 · ESC 关 (Channel 4-gate parity · drawer pattern 复用)
  const [selectedSection, setSelectedSection] = useState<string | null>(null);

  /* Phase B.1.3 (PM 2026-05-10) · revert ModePill 双控 · 错设计
     PM 真意: 演示 = 上传 sample 跑真后端 · 不需切按钮 */

  /* sessionData 单点派生 · ALL IN 真产品 · liveData → ReportSession ·
     liveData null 时 fallback EMPTY_SESSION (不 fallback 到 REPORT_SESSION mock · 防显假数据).
     5 panel + Hero + PipelineBand 都消费此 derived value */
  const derivedFromLive = liveToReportSession(liveData);
  const sessionData: ReportSession = derivedFromLive ?? EMPTY_SESSION;
  const s = sessionData;
  const coverPct = Math.round((s.coverage.filled / Math.max(s.coverage.total, 1)) * 100);
  const [llmConnected, setLlmConnected] = useState<boolean | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);
  // user 反馈 2026-05-22 · 已上传材料列表必须可见 (含 filename / size / parsed_chars / 删除按钮)
  // 不再只存 filename 字符串 · 而是完整 ReportFileSummary[] 让 UI 显 size + parse_status
  const [uploadedFiles, setUploadedFiles] = useState<ReportFileSummary[]>([]);
  const [uploadedTemplate, setUploadedTemplate] = useState<string>("");
  // Q6-B · 用户上传模板 + dropdown 双 section (builtin + user)
  const [templateList, setTemplateList] = useState<{ builtin: TemplateListItem[]; user: TemplateListItem[] }>({
    builtin: [],
    user: [],
  });
  const [lastTemplateReport, setLastTemplateReport] = useState<TemplateValidationReport | null>(null);
  const [uploadingTemplate, setUploadingTemplate] = useState(false);
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

  // Q6-B · 加载模板列表 (5 内置 + N user) · started 切真时刷新 + 上传后 manual refetch
  useEffect(() => {
    let cancelled = false;
    listReportTemplates()
      .then((j) => {
        if (!cancelled) setTemplateList(j);
      })
      .catch(() => {
        if (!cancelled) setTemplateList({ builtin: [], user: [] });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const refreshTemplateList = useCallback(async () => {
    try {
      const j = await listReportTemplates();
      setTemplateList(j);
    } catch {
      /* silent · 失败不阻塞主流程 · 已有 list 仍可用 */
    }
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
      // Q6-B · templateChoice 选了具体模板 (内置 path 或 user-template:{id}) 时显式传 source_docx
      // 空时后端默认走 V16FillRequest.source_docx 缺省 (samples/经纬测绘_对公成稿A.docx)
      const sourceDocx = templateChoice || undefined;
      streamReportV16Fill(
        {
          report_id: opts?.reportIdOverride ?? reportId ?? "",
          business_line: businessLine,
          mock: useMock,
          ...(sourceDocx ? { source_docx: sourceDocx } : {}),
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
    [generating, reportId, businessLine, mode, templateChoice],
  );

  const handleUpload = useCallback(
    async (files: File[]) => {
      if (!files.length) return;
      setErrMsg(null);
      try {
        const resp = await uploadReportMaterials(files, businessLine);
        setReportId(resp.report_id);
        // user 反馈 2026-05-22 · 累加而非覆盖 · 客户经理多批次上传也都能看见
        setUploadedFiles((prev) => [...prev, ...resp.file_summary]);
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
  const handleSelectTemplate = useCallback((tpl: string) => {
    setTemplateChoice(tpl);
  }, []);

  /* user 反馈 2026-05-22 · 从已上传列表移除一份 (前端 state 移除 · 后端无 per-file 删 endpoint
     效果: UI 立即看不见 · 下次 v16/fill 仍走 report_id 全集 · 如需后端真删需扩 endpoint) */
  const handleRemoveUploadedFile = useCallback((idx: number) => {
    setUploadedFiles((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  /* PM 2026-05-09 ALL IN: handleApplyLaunch 仅留 live 路径 · 删 historyChoice mock 触发分支
     上传材料 + 选模板 (或默认按 business_line) → 真 v16 主管线 · 不 silent fallback mock */
  const handleApplyLaunch = useCallback(() => {
    setMode("live");
    setStarted(true);
    setTimeout(() => triggerV16Fill({ explicitMock: false }), 0);
  }, [triggerV16Fill]);

  // Q6-B · 真用户自定义 docx 模板上传 · 走专用 endpoint
  // - 后端自动跑 byte-level diff lint · 返 validation_report
  // - 上传成功后 templateChoice 自动切到 user-template:{id} · 客户经理可直接生成
  const handleUploadTemplate = useCallback(
    async (files: File[]) => {
      if (!files.length) return;
      setErrMsg(null);
      const file = files[0];
      // 模板名默认取 docx basename (去 .docx 扩展) · 用户后续可在 metadata 看
      const templateName = file.name.replace(/\.docx$/i, "").slice(0, 80);
      setUploadingTemplate(true);
      try {
        const resp = await uploadReportTemplate(file, templateName, businessLine);
        setUploadedTemplate(resp.validation_report.template_name);
        setLastTemplateReport(resp.validation_report);
        // 自动选用此 user template · 客户经理点 "开始生成" 即用此模板
        setTemplateChoice(resp.template_path);
        setMode("live");
        setStarted(true);
        // 刷新列表 (dropdown 下次打开能看到)
        await refreshTemplateList();
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        setErrMsg(msg);
        const statusMatch = /HTTP (\d{3})/.exec(msg);
        setLiveFailErr({
          endpoint: "/api/report/upload-template",
          status: statusMatch ? statusMatch[1] : "network",
          message: msg,
        });
      } finally {
        setUploadingTemplate(false);
      }
    },
    [businessLine, refreshTemplateList],
  );

  /* CRUD 完整 (2026-05-21 · agent17 TODO medium-value 3 项)
     - 删 user 模板: confirm → DELETE endpoint → 列表刷 + 若选中则清 templateChoice
     - 重命名: prompt → PATCH endpoint → 列表刷 + 若选中则同步 templateChoice 内的 name (id 不变 path 不变)
     Boundary: 只对 user-* 模板暴露按钮 · 内置不让动 (后端也拒) */
  const handleDeleteUserTemplate = useCallback(
    async (templateId: string, templateName: string) => {
      if (typeof window !== "undefined") {
        const ok = window.confirm(
          `确认删除模板「${templateName}」?\n\n操作可由管理员从 .archived/ 恢复 · 但客户经理 dropdown 立即看不到。`,
        );
        if (!ok) return;
      }
      try {
        await deleteReportTemplate(templateId);
        // 若当前选中的就是被删的 · 清掉 (用户得重新选)
        if (templateChoice === `user-template:${templateId}`) {
          setTemplateChoice("");
        }
        await refreshTemplateList();
        setErrMsg(null);
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        setErrMsg(msg);
        setLiveFailErr({
          endpoint: `DELETE /api/report/templates/${templateId}`,
          status: (e as Error & { code?: string })?.code ?? "ERR",
          message: msg,
        });
      }
    },
    [templateChoice, refreshTemplateList],
  );

  const handleRenameUserTemplate = useCallback(
    async (templateId: string, currentName: string) => {
      if (typeof window === "undefined") return;
      const newName = window.prompt(
        `重命名模板 (2-80 字符):`,
        currentName,
      );
      if (newName === null) return; // user cancelled
      const trimmed = newName.trim();
      if (trimmed.length < 2 || trimmed.length > 80) {
        setErrMsg("模板名长度必须 2-80 字符");
        return;
      }
      if (trimmed === currentName) return; // noop
      try {
        await renameReportTemplate(templateId, trimmed);
        await refreshTemplateList();
        setErrMsg(null);
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        setErrMsg(msg);
        setLiveFailErr({
          endpoint: `PATCH /api/report/templates/${templateId}`,
          status: (e as Error & { code?: string })?.code ?? "ERR",
          message: msg,
        });
      }
    },
    [refreshTemplateList],
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
    /* PM 2026-05-09 ALL IN: 删 REPORT_SESSION mock fallback · liveData null 时直拒导出
       (导出 = 客户经理把 AI 报告稿当定稿带去审贷会 · 不允许 mock 假数据出门) */
    if (!liveData) {
      setErrMsg("请先生成报告 · 上传材料触发 v16 主管线后再导出");
      return;
    }
    setExporting(true);
    setErrMsg(null);
    try {
      const payload: ReportExportPayload = {
        session_id: liveData.session_id,
        sections: liveData.sections,
        pending_questions: liveData.pending_questions,
        stats: (liveData.stats ?? {}) as Record<string, unknown>,
        qc: (liveData.qc ?? {}) as Record<string, unknown>,
        business_line: businessLine,
        client_manager: "客户经理",
      };
      const { blob, filename } = await exportReportDocx(payload);
      triggerDownloadBlob(blob, filename);
    } catch (e) {
      setErrMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setExporting(false);
    }
  }, [exporting, liveData, businessLine]);

  /* Phase B.2 (PM 2026-05-10 真意 reframe) · demo/run · sample_id (DP001-005)
     反模式 (已废): scenario_id easy/medium/hard 切假数据 fixture
     PM 真意: 演示 = 上传 sample 真材料 → 真后端 (v16 主管线) → 真返结果
     mode 仍设 "mock" 仅作前端 UX flag (区分手动上传 vs 优质 batch 加载) ·
     done.data_source 真值由后端给 ("live") · 不再前端预判
     错误降级 (Step 5 typed banner · 不 silent · 不 fallback fake) · 把后端 typed error code
     翻成客户经理可读的 actionable hint (per dispatch §"错误降级") */
  const _formatDemoError = useCallback((codeOrMsg: string): string => {
    if (codeOrMsg.includes("DEEPSEEK_KEY_MISSING")) {
      return "AI 模型未配置，暂时无法生成报告 · 请联系管理员开通后重试";
    }
    if (codeOrMsg.includes("DEMO_CLASSIFIER_MISSING")) {
      return "该模板尚未完成首次准备 · 请联系管理员初始化后重试";
    }
    if (codeOrMsg.includes("DEMO_TEMPLATE_MISSING")) {
      return "默认对公模板缺失 · 请联系管理员检查模板库";
    }
    if (codeOrMsg.includes("SAMPLE_DIR_MISSING")) {
      return "示例企业暂不可用 · 可选：DP001 龙峰精工 / DP002 蓝汀家电 / DP003 宸星家装 / DP004 汇德建材 / DP005 星胤实业";
    }
    if (codeOrMsg.includes("SAMPLE_ID_INVALID")) {
      return "示例企业标识不正确 · 请重新选择示例企业";
    }
    if (codeOrMsg.includes("V16_REAL_PATH_FAILED")) {
      return "本次生成未成功 · 请稍后重试；若持续失败请联系管理员";
    }
    return codeOrMsg;
  }, []);

  const handleDemoRun = useCallback(
    (sampleId: string) => {
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
        { sample_id: sampleId },
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
              const err = evt as ReportV16ErrorEvent;
              const friendly = _formatDemoError(`${err.code ?? ""} ${err.message ?? ""}`);
              setErrMsg(friendly);
              setLiveFailErr({
                endpoint: "/api/report/demo/run",
                status: err.code ?? "SSE error",
                message: friendly,
              });
            }
          },
          onClose: () => setGenerating(false),
          onError: (e) => {
            const friendly = _formatDemoError(e.message);
            setErrMsg(friendly);
            // 真路径 demo 失败 · 顶部 banner (与 v16/fill 同 UX)
            setLiveFailErr({
              endpoint: "/api/report/demo/run",
              status: (e as Error & { code?: string }).code ?? `HTTP ${e.message.match(/HTTP (\d+)/)?.[1] ?? "ERR"}`,
              message: friendly,
            });
            setGenerating(false);
          },
        },
      );
    },
    [generating, _formatDemoError],
  );

  /* G-10 闭环 · export PDF 真接 · 与 export Word 同源 payload · pdf 走 reportlab */
  const handleExportPdf = useCallback(async () => {
    if (exportingPdf) return;
    /* PM 2026-05-09 ALL IN: 同 export_docx · 拒 liveData null 导出 · 不 mock fallback */
    if (!liveData) {
      setErrMsg("请先生成报告 · 上传材料触发 v16 主管线后再导出");
      return;
    }
    setExportingPdf(true);
    setErrMsg(null);
    try {
      const payload: ReportExportPayload = {
        session_id: liveData.session_id,
        sections: liveData.sections,
        pending_questions: liveData.pending_questions,
        stats: (liveData.stats ?? {}) as Record<string, unknown>,
        qc: (liveData.qc ?? {}) as Record<string, unknown>,
        business_line: businessLine,
        client_manager: "客户经理",
      };
      const { blob, filename } = await exportReportPdf(payload);
      triggerDownloadBlob(blob, filename);
    } catch (e) {
      setErrMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setExportingPdf(false);
    }
  }, [exportingPdf, liveData, businessLine]);

  const lastStage = liveStages.length
    ? liveStages[liveStages.length - 1]
    : null;

  return (
    <EvidenceProvider
      items={EMPTY_EVIDENCE_ITEMS}
      unfilledFields={EMPTY_UNFILLED_FIELDS}
    >
      <div
        data-view="archive-report"
        data-started={started ? "yes" : "no"}
        data-mode={mode}
        data-scanned={started ? "yes" : "no"} /* legacy attr · 保留向后兼容 */
      >
        <ReportHero
          coverPct={coverPct}
          sessionData={sessionData}
          isLive={derivedFromLive !== null}
          dataSourceKind={
            liveFailErr
              ? "mock_fallback"
              : liveData
                ? reportDoneDataSource(liveData)
                : "mock"
          }
        />
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
        {/* B.2.3 hotfix (主 CLI 2026-05-10 自验) · sample strip 上移到 LaunchBar 之前
            · PM 第一眼看到 1-click 示例企业 (5 真 batch) · 不需先滚到下方
            · 业务线按钮 + 上传 + 生成 留 LaunchBar · sample CTA 独立 hero 段 */}
        {!liveData && !generating ? (
          <ReportSampleStrip
            onRun={handleDemoRun}
            disabled={generating}
          />
        ) : null}
        <ReportLaunchBar
          started={started}
          mode={mode}
          reportId={reportId}
          businessLine={businessLine}
          templateChoice={templateChoice}
          uploadedFiles={uploadedFiles}
          generating={generating}
          exporting={exporting}
          errMsg={errMsg}
          onUpload={handleUpload}
          onRemoveUploadedFile={handleRemoveUploadedFile}
          onSelectTemplate={handleSelectTemplate}
          onApplyLaunch={handleApplyLaunch}
          onBusinessLineChange={setBusinessLine}
          onStartGenerate={() => triggerV16Fill()}
          onExport={handleExportDocx}
          /* Q6-B · 模板上传 + dropdown 真接 */
          templateList={templateList}
          lastTemplateReport={lastTemplateReport}
          uploadingTemplate={uploadingTemplate}
          onUploadTemplate={handleUploadTemplate}
          onDismissTemplateReport={() => setLastTemplateReport(null)}
          /* CRUD 完整 (2026-05-21) · 删 / 重命名 user 模板 */
          onDeleteUserTemplate={handleDeleteUserTemplate}
          onRenameUserTemplate={handleRenameUserTemplate}
        />
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
                {/* PM 2026-05-09 ALL IN: 删 ScanCTA "生成报告 (mock 路径)" · ALL IN 后只走真 v16 主管线 · launch bar 已有 "开始生成" 真触发 */}
                <ConversationPanel sessionData={sessionData}>
                  <ReportComposer sessionData={sessionData} />
                </ConversationPanel>
                {liveData?.sections && liveData.sections.length > 0 ? (
                  <ReportLiveSections
                    sections={liveData.sections}
                    evidences={liveData.evidences}
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
                {/* Phase B.2 (PM 2026-05-10) Step 7 信息密度: 折叠 default → 展开 default ·
                    审贷员一开就看到 truth/llm 分层 · 不再隐藏 · per dispatch §"信息密度" */}
                <details
                  className="report-truth-first-drawer"
                  data-testid="report-truth-first-drawer"
                  open
                >
                  <summary>字段来源清单 · 审贷员核对</summary>
                  <dl className="report-truth-first-drawer__list">
                    <dt data-kind="truth">资产负债率</dt>
                    <dd>系统计算 · 总负债 / 总资产 · 确定值</dd>
                    <dt data-kind="truth">流动比率</dt>
                    <dd>系统计算 · 流动资产 / 流动负债 · 确定值</dd>
                    <dt data-kind="truth">净利润同比</dt>
                    <dd>系统计算 · (本期 - 上期) / 上期 · 确定值</dd>
                    <dt data-kind="truth">应收账款周转天数</dt>
                    <dd>系统计算 · 应收账款 / 营业收入 × 365 · 确定值</dd>
                    <dt data-kind="truth">行业基准对比</dt>
                    <dd>行业基准库 · 行业卡匹配 · 确定值</dd>
                    <dt data-kind="llm">行业意见</dt>
                    <dd>AI 生成 · 依据上传材料 · 参考值</dd>
                    <dt data-kind="llm">经营风险点</dt>
                    <dd>AI 生成 · 经证据链核对 · 参考值</dd>
                    <dt data-kind="llm">话术建议</dt>
                    <dd>AI 生成 · 参考值</dd>
                  </dl>
                  <p className="report-truth-first-drawer__note">
                    确定值字段由系统计算，AI 不可改写；质检未通过的内容会被拦截，不进入报告。
                  </p>
                </details>
              </aside>
            </div>
            <section
              className="ev-claim-summary"
              aria-label="Evidence-grounded 分析结论"
            >
              <span className="ev-claim-summary-label">
                分析结论 · 证据支撑
              </span>
              <ClaimText text={EMPTY_CLAIM_SUMMARY} />
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

function ReportHero({ coverPct, sessionData, isLive, dataSourceKind }: {
  coverPct: number;
  sessionData: ReportSession;
  isLive?: boolean;
  /* 件 #2 · data_source SSOT 真消费 · 5-enum trust model badge */
  dataSourceKind?: DataSourceKind;
}) {
  const s = sessionData;
  // Phase B.1.3 (PM 2026-05-10) · revert ModePill 双控 · isLive 留作 future ref
  void isLive;
  /* QC 结论单一真源: 与时间线/预览徽章同源 (s.qcCounts) 派生, 不再信任 s.stage 静态串 —
     根治 "页头 QC 通过 vs 时间线 2 阻断" 矛盾. 无 QC 信号时回退生命周期 stage. */
  const _qcTotal = s.qcCounts.block + s.qcCounts.warn + s.qcCounts.info;
  const qcState =
    _qcTotal > 0
      ? s.qcCounts.block > 0
        ? `QC 阻断 · ${s.qcCounts.block} 项`
        : s.qcCounts.warn > 0
          ? `QC 待复核 · ${s.qcCounts.warn} 项`
          : "QC 通过"
      : s.stage;
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
          {/* Phase B.2 (PM 2026-05-10) Step 7 信息密度: empty state 文案明确动作 ·
              不再显 "·  ·  · 字段覆盖 0%" 一串空 separator · 客户经理直观知下一步做啥 */}
          <div className="rpt-hero-sub">
            {s.clientName ? (
              <>
                {s.clientName} · {s.amount} · {qcState} · 字段覆盖 {coverPct}%
              </>
            ) : (
              <span style={{ color: "var(--ink-65)", fontStyle: "italic" }}>
                尚未开始 · 请<strong>上传客户材料</strong>(主入口) 或<strong>加载示例企业</strong>(下方 5 个真 batch) → 真后端 v16 主管线
              </span>
            )}
          </div>
        </div>
      </div>
      {/* Phase B.1.3 · DataSourceBadge SSOT trust 标记保留 · ModePill 双控删 */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        {dataSourceKind && (
          <DataSourceBadge kind={dataSourceKind} testId="report-data-source-badge" />
        )}
        <div className="rpt-hero-stats">
          <Stat label="本周处理" value={EMPTY_GLOBAL_STATS.weeklyProcessed} />
          <Stat label="成功率" value={EMPTY_GLOBAL_STATS.successRate} />
          <Stat label="平均时长" value={EMPTY_GLOBAL_STATS.avgDuration} />
        </div>
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
  // Phase B.2.2 hotfix · 上游未完成时 QC 强制 0/pending · 修复 0 材料时 PIPELINE 100% 假完成
  const upstreamDone = matTotal > 0 && matPct === 100 && fieldPct >= 90 && secPct >= 80;
  const qcPct = !upstreamDone
    ? 0
    : (s.qcCounts.block === 0 ? (s.qcCounts.warn === 0 ? 100 : 70) : 40);

  const stages = [
    {
      key: "mat",
      label: "原始材料",
      caption: `${matParsed} / ${matTotal} 已解析`,
      detail: matTotal - matParsed === 0 ? "全部就位" : `${matTotal - matParsed} 份待处理`,
      pct: matPct,
      state: matTotal === 0 ? "pending" : matPct === 100 ? "done" : matPct > 0 ? "running" : "pending",
    },
    {
      key: "field",
      label: "字段抽取",
      caption: `${s.coverage.filled} / ${s.coverage.total} 字段`,
      detail: `${s.coverage.marked} 项标未填`,
      pct: fieldPct,
      state: s.coverage.total === 0 ? "pending" : fieldPct >= 90 ? "done" : fieldPct > 0 ? "running" : "pending",
    },
    {
      key: "sec",
      label: "段落生成",
      caption: `${secDone} / ${secTotal} 段完成`,
      detail: secRun > 0 ? `${secRun} 段生成中` : "—",
      pct: secPct,
      state: secTotal === 0 ? "pending" : secPct >= 80 ? "done" : secPct > 0 ? "running" : "pending",
    },
    {
      key: "qc",
      label: "QC 终审",
      caption: `阻断 ${s.qcCounts.block} · 警告 ${s.qcCounts.warn}`,
      detail: `${qcTotal} 条问题`,
      pct: qcPct,
      state: !upstreamDone
        ? "pending"
        : s.qcCounts.block === 0 && s.qcCounts.warn === 0
          ? "done"
          : s.qcCounts.block > 0
            ? "pending"
            : "running",
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
  position: "relative",  // Q6-B · validation_report banner absolute-positions inside
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
/* Phase B.1.4 (PM 2026-05-10) · 统一 height 36 · 业务线 select 跟主入口 button 对齐 */
const _LAUNCH_BTN_PRIMARY: CSSProperties = {
  fontFamily: "var(--cjk)",
  fontSize: 13,
  padding: "0 14px",
  height: 36,
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
  fontSize: 13,
  padding: "0 14px",
  height: 36,
  background: "var(--chalk)",
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
  padding: "0 10px",
  height: 36,
  background: "var(--chalk)",
  color: "var(--ink)",
  border: "1px solid var(--ink-14)",
  borderRadius: "var(--r-md)",
  cursor: "pointer",
};

/* Phase B.2 (PM 2026-05-10 真意 reframe) · sample CTA · sample_id DP001-005
   PM 真意: 演示 = 上传 sample 真材料 → 真后端 (v16 主管线) → 真返结果
   反模式 (已废): scenario_id easy/medium/hard fixture (Phase A worker-A4)
   POST /api/report/demo/run · 后端 fill_stream(explicit_mock=False) 真 LLM 跑 */
const REPORT_SAMPLE_OPTIONS = [
  { id: "DP001_龙峰精工",   label: "DP001 · 龙峰精工",   hint: "精密零部件 · 福建专精特新" },
  { id: "DP002_蓝汀家电",   label: "DP002 · 蓝汀家电",   hint: "家电制造 · 浙江规上" },
  { id: "DP003_宸星家装",   label: "DP003 · 宸星家装",   hint: "家装零售 · 民营连锁" },
  { id: "DP004_汇德建材",   label: "DP004 · 汇德建材",   hint: "建材贸易 · 区域龙头" },
  { id: "DP005_星胤实业",   label: "DP005 · 星胤实业",   hint: "实业控股 · 多元经营" },
] as const;

function ReportSampleStrip({
  onRun,
  disabled,
}: {
  onRun: (sampleId: string) => void;
  disabled: boolean;
}) {
  const btnStyle: CSSProperties = {
    fontFamily: "var(--cjk)",
    fontSize: 12,
    padding: "8px 14px",
    background: "transparent",
    color: "var(--ink)",
    border: "1px solid var(--ink-14)",
    borderRadius: "var(--r-md)",
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.5 : 1,
    whiteSpace: "nowrap",
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-start",
    gap: 2,
    /* B.4 SLO-3 · report-bug-6 · 5 sample btn 横向占 70% · 右 30% 空
     * 真因: minWidth 132 · 5 btn × 132 + gap = ~700px · 父若宽 1200 则右 ~500px 空
     * 修: flex 1 1 0 + minWidth 132 (兜底 wrap) · 5 btn 平均分宽 · 撑满 row
     */
    flex: "1 1 0",
    minWidth: 132,
  };
  return (
    <section
      data-testid="report-sample-strip"
      style={{
        margin: "12px 0",
        padding: "12px 16px",
        background: "color-mix(in srgb, var(--chalk) 60%, transparent)",
        border: "1px dashed var(--ink-14)",
        borderRadius: "var(--r-md)",
        display: "flex",
        gap: 10,
        alignItems: "center",
        flexWrap: "wrap",
        fontFamily: "var(--cjk)",
        fontSize: 12,
        color: "var(--ink)",
      }}
      aria-label="加载示例企业 · 真材料 batch"
    >
      <span style={{ color: "var(--ink-65)", textTransform: "uppercase", letterSpacing: ".04em", fontSize: 10, marginRight: 4 }}>
        示例企业 · 真材料跑真后端
      </span>
      {REPORT_SAMPLE_OPTIONS.map((opt) => (
        <button
          key={opt.id}
          type="button"
          data-testid={`report-sample-${opt.id.split("_")[0].toLowerCase()}`}
          style={btnStyle}
          disabled={disabled}
          onClick={() => onRun(opt.id)}
          title={`${opt.label} · ${opt.hint}`}
        >
          <span style={{ fontSize: 13, fontWeight: 500 }}>{opt.label}</span>
          <span style={{ fontSize: 10, color: "var(--ink-65)" }}>{opt.hint}</span>
        </button>
      ))}
      {/* B.4 SLO-3 · report-bug-3 · "真 LLM..." 飘右 · 跟 sample btn 不对齐
       * 真因: 原 marginLeft auto 推到 row 右端 · 跟 sample btn 视觉错位
       * 修: 移出 flex row · 改 div block flex-basis 100% · 撑满下一行 · 不再 floating */}
      <div
        style={{
          flexBasis: "100%",
          marginTop: 4,
          color: "var(--ink-50)",
          fontSize: 11,
          fontStyle: "italic",
          fontFamily: "var(--cjk)",
        }}
      >
        真 LLM (DeepSeek) + 真 9 维 QC · PM 2026-05-10 真意 reframe
      </div>
    </section>
  );
}

function ReportLaunchBar(p: {
  started: boolean;
  mode: "mock" | "live";
  reportId: string;
  businessLine: string;
  templateChoice: string;
  /* user 反馈 2026-05-22 · 改 ReportFileSummary[] · UI 显 size + parse_status + 删除按钮 */
  uploadedFiles: ReportFileSummary[];
  generating: boolean;
  exporting: boolean;
  errMsg: string | null;
  onUpload: (files: File[]) => void;
  onRemoveUploadedFile: (idx: number) => void;
  onSelectTemplate: (tpl: string) => void;
  onApplyLaunch: () => void;
  onBusinessLineChange: (v: string) => void;
  onStartGenerate: () => void;
  onExport: () => void;
  /* Q6-B · 用户自定义模板上传 (per Q6-B 实施单 2026-05-21) */
  templateList: { builtin: TemplateListItem[]; user: TemplateListItem[] };
  lastTemplateReport: TemplateValidationReport | null;
  uploadingTemplate: boolean;
  onUploadTemplate: (files: File[]) => void;
  onDismissTemplateReport: () => void;
  /* CRUD 完整 (2026-05-21) · 删 / 重命名 user 模板 (icon button 旁挂 dropdown · 选中 user 模板时显式) */
  onDeleteUserTemplate: (templateId: string, templateName: string) => void;
  onRenameUserTemplate: (templateId: string, currentName: string) => void;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const templateInputRef = useRef<HTMLInputElement | null>(null);

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    if (files.length) p.onUpload(files);
    e.target.value = "";
  }

  function handleTemplateChange(e: ChangeEvent<HTMLInputElement>) {
    // Q6-B · "上传模板" 走专用 endpoint (POST /api/report/upload-template)
    // 自动跑 byte-level diff lint · 返 validation_report
    const files = Array.from(e.target.files ?? []);
    if (files.length) p.onUploadTemplate(files);
    e.target.value = "";
  }

  return (
    <>
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
            ? `已上传 ${p.uploadedFiles.length} 份 · 见下方列表`
            /* B.4 SLO-3 · report-bug-4 · 5 标签分隔符统一
             * 真因: "PDF / Word / Excel / 图片 · 多文件" 混用 " / " 和 " · "
             *      → 标签间距视觉不一致 (· 中圆点 vs / 斜杠 视觉重量不同)
             * 修: 统一用 " / " 分隔 · 5 标签间距视觉一致
             */
            : "PDF / Word / Excel / 图片 / 多文件"}
        </span>
      </div>

      {/* Q6-B · 模板双入口 (PM 2026-05-21): 上传 docx (自动 byte-level lint) + 选预制/已上传 */}
      <div style={_LAUNCH_GROUP_STYLE}>
        <span style={_LAUNCH_LABEL_STYLE}>模板</span>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button
            type="button"
            data-testid="report-upload-template-cta-launch"
            onClick={() => templateInputRef.current?.click()}
            disabled={p.uploadingTemplate}
            style={{
              ..._LAUNCH_BTN_SECONDARY,
              opacity: p.uploadingTemplate ? 0.5 : 1,
              cursor: p.uploadingTemplate ? "wait" : "pointer",
            }}
          >
            {p.uploadingTemplate ? "上传中…" : "⇪ 上传模板"}
          </button>
          <input
            ref={templateInputRef}
            type="file"
            hidden
            accept=".docx"
            onChange={handleTemplateChange}
          />
          <select
            data-testid="report-template-select"
            value={p.templateChoice}
            onChange={(e) => p.onSelectTemplate(e.target.value)}
            style={_LAUNCH_SELECT_STYLE}
          >
            <option value="">默认 (按业务线)</option>
            <optgroup label="内置模板">
              {p.templateList.builtin.map((t) => (
                <option key={t.template_path} value={t.template_path}>
                  {t.name}
                </option>
              ))}
            </optgroup>
            {p.templateList.user.length > 0 ? (
              <optgroup label="我上传的">
                {p.templateList.user.map((t) => (
                  <option key={t.template_path} value={t.template_path}>
                    {t.name}
                    {t.validation === "WARN" ? " ⚠" : ""}
                    {t.validation === "ERROR" ? " ✗" : ""}
                    {" · "}
                    {t.placeholder_count ?? 0} 占位
                    {t.residue_count && t.residue_count > 0 ? ` · ${t.residue_count} 残留` : ""}
                  </option>
                ))}
              </optgroup>
            ) : null}
          </select>
          {/* CRUD 完整 (2026-05-21) · 选中 user 模板时显式 重命名 / 删除 icon 按钮
              boundary: 仅 user-template:xxx · builtin 不显示 (内置不让动) */}
          {(() => {
            if (!p.templateChoice.startsWith("user-template:")) return null;
            const selected = p.templateList.user.find(
              (t) => t.template_path === p.templateChoice,
            );
            if (!selected || !selected.template_id) return null;
            const tid = selected.template_id;
            const tname = selected.name;
            return (
              <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                <button
                  type="button"
                  data-testid="report-template-rename-btn"
                  onClick={() => p.onRenameUserTemplate(tid, tname)}
                  title={`重命名「${tname}」`}
                  aria-label={`重命名模板 ${tname}`}
                  style={{
                    padding: "4px 6px",
                    fontSize: 12,
                    fontFamily: "var(--cjk)",
                    background: "transparent",
                    border: "1px solid var(--ink-25, #d1d5db)",
                    borderRadius: 4,
                    color: "var(--ink-65)",
                    cursor: "pointer",
                  }}
                >
                  ✎
                </button>
                <button
                  type="button"
                  data-testid="report-template-delete-btn"
                  onClick={() => p.onDeleteUserTemplate(tid, tname)}
                  title={`删除「${tname}」(soft delete · 可恢复)`}
                  aria-label={`删除模板 ${tname}`}
                  style={{
                    padding: "4px 6px",
                    fontSize: 12,
                    fontFamily: "var(--cjk)",
                    background: "transparent",
                    border: "1px solid #ef4444",
                    borderRadius: 4,
                    color: "#dc2626",
                    cursor: "pointer",
                  }}
                >
                  🗑
                </button>
              </div>
            );
          })()}
        </div>
        <span style={_LAUNCH_HINT_STYLE}>
          上传 .docx 自动 lint · 选预制或已上传 · 我上传的可改名 / 删
        </span>
      </div>

      {/* Q6-B · validation_report banner · 上传成功后显示 placeholder / residue · 让客户经理决定是否继续 */}
      {p.lastTemplateReport ? (
        <div
          data-testid="report-template-validation-banner"
          style={{
            position: "absolute",
            top: -2,
            right: 12,
            maxWidth: 360,
            padding: "8px 12px",
            background:
              p.lastTemplateReport.validation === "PASS"
                ? "color-mix(in srgb, #22c55e 12%, var(--surface))"
                : p.lastTemplateReport.validation === "ERROR"
                  ? "color-mix(in srgb, #ef4444 14%, var(--surface))"
                  : "color-mix(in srgb, #f59e0b 14%, var(--surface))",
            border: `1px solid ${
              p.lastTemplateReport.validation === "PASS"
                ? "#22c55e"
                : p.lastTemplateReport.validation === "ERROR"
                  ? "#ef4444"
                  : "#f59e0b"
            }`,
            borderRadius: 6,
            fontSize: 11,
            fontFamily: "var(--cjk)",
            color: "var(--ink-85)",
            zIndex: 5,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
            <strong>
              {p.lastTemplateReport.validation === "PASS"
                ? "✓ 模板验证通过"
                : p.lastTemplateReport.validation === "ERROR"
                  ? "✗ 模板验证失败"
                  : "⚠ 模板含残留 specific 字面"}
            </strong>
            <button
              type="button"
              onClick={p.onDismissTemplateReport}
              style={{
                background: "none",
                border: "none",
                color: "var(--ink-65)",
                cursor: "pointer",
                fontSize: 14,
                padding: 0,
                marginLeft: 8,
              }}
              aria-label="关闭"
            >
              ×
            </button>
          </div>
          <div>
            占位符 {p.lastTemplateReport.placeholder_count} 个 · 唯一 key{" "}
            {p.lastTemplateReport.placeholder_keys.length} · 残留{" "}
            {p.lastTemplateReport.residue_count}
          </div>
          {p.lastTemplateReport.residue_samples.length > 0 ? (
            <div style={{ marginTop: 4, color: "var(--ink-65)" }}>
              示例:{" "}
              {p.lastTemplateReport.residue_samples
                .slice(0, 3)
                .map((r) => `${r.kind}=${r.value}`)
                .join(" · ")}
            </div>
          ) : null}
          {p.lastTemplateReport.lint_error ? (
            <div style={{ marginTop: 4, color: "#dc2626" }}>{p.lastTemplateReport.lint_error}</div>
          ) : null}
        </div>
      ) : null}

      {/* PM 2026-05-09 ALL IN: 删 "历史 (示例 · 仅培训演示)" dropdown · 历史 session 走 mock 残留 · 后端 history endpoint 待 Phase C */}

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
          started 时切到 "重新生成 / 导出" 双 chip-style 按钮
          B.4 SLO-3 · report-bug-5 · 加 "执行" label 跟其他 column (主入口/模板/业务线) 视觉对齐
          原因: 其他 column 都有 label + content + (hint) · 开始生成 column 只有 btn → 视觉不对齐 */}
      {!p.started ? (
        <div style={_LAUNCH_GROUP_STYLE}>
          <span style={_LAUNCH_LABEL_STYLE}>执行</span>
          <button
            type="button"
            data-testid="report-apply-launch-btn"
            onClick={p.onApplyLaunch}
            disabled={!p.templateChoice && p.uploadedFiles.length === 0}
            style={{
              ..._LAUNCH_BTN_SECONDARY,
              borderColor: "var(--t-report)",
              color: "var(--t-report)",
              opacity: !p.templateChoice && p.uploadedFiles.length === 0 ? 0.5 : 1,
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

    {/* user 反馈 2026-05-22 fix · 已上传材料列表 (per-file 可见 + 删除按钮)
        agent17 commit b9c7fbf 只把 count 塞 hint · user 反馈"看不到已上传列表" → 此处真展开 */}
    <UploadedMaterialsList
      files={p.uploadedFiles}
      onRemove={p.onRemoveUploadedFile}
    />

    {/* user 反馈 2026-05-22 fix · 已上传模板列表 (always-visible · 不仅在 dropdown 内)
        builtin 5 (folder icon · 不可删) + user N (user icon · ✎ 重命名 / 🗑 删除)
        validation badge: PASS ✓ / WARN ⚠ / ERROR ✗ */}
    <TemplateLibraryList
      templates={p.templateList}
      selectedPath={p.templateChoice}
      onSelect={p.onSelectTemplate}
      onRename={p.onRenameUserTemplate}
      onDelete={p.onDeleteUserTemplate}
    />
    </>
  );
}

/* user 反馈 2026-05-22 · 已上传材料列表 (visible · per-file row)
   columns: filename / size / parsed_chars / parse_status / 删除按钮
   empty state: hint "尚未上传 · 点击上方'上传材料'选文件" */
function UploadedMaterialsList(p: {
  files: ReportFileSummary[];
  onRemove: (idx: number) => void;
}) {
  if (p.files.length === 0) {
    return (
      <section
        data-testid="report-uploaded-materials-empty"
        aria-label="已上传材料 (空)"
        style={{
          margin: "8px 0 16px 0",
          padding: "10px 14px",
          background: "color-mix(in srgb, var(--chalk) 40%, transparent)",
          border: "1px dashed var(--ink-14)",
          borderRadius: "var(--r-md)",
          fontFamily: "var(--cjk)",
          fontSize: 12,
          color: "var(--ink-65)",
          fontStyle: "italic",
        }}
      >
        尚未上传材料 · 点击上方「上传材料文件」选 PDF / Word / Excel / 图片
      </section>
    );
  }
  const fmtBytes = (n: number): string => {
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / 1024 / 1024).toFixed(2)} MB`;
  };
  const statusColor: Record<ReportFileSummary["parse_status"], string> = {
    ok: "#22c55e",
    skipped: "#f59e0b",
    deferred: "#f59e0b",
    empty: "#9ca3af",
    error: "#ef4444",
    save_failed: "#ef4444",
  };
  return (
    <section
      data-testid="report-uploaded-materials-list"
      aria-label={`已上传材料 · ${p.files.length} 份`}
      style={{
        margin: "8px 0 16px 0",
        padding: "12px 14px",
        background: "color-mix(in srgb, var(--chalk) 55%, transparent)",
        border: "1px solid var(--ink-14)",
        borderRadius: "var(--r-md)",
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 8,
          marginBottom: 8,
          fontFamily: "var(--cjk)",
        }}
      >
        <strong style={{ fontSize: 13, color: "var(--ink)" }}>
          已上传材料 · {p.files.length} 份
        </strong>
        <span style={{ fontSize: 11, color: "var(--ink-65)" }}>
          总解析 {p.files.reduce((s, f) => s + (f.parsed_chars ?? 0), 0)} 字 · 后端真返回
        </span>
      </header>
      <ul
        style={{
          listStyle: "none",
          padding: 0,
          margin: 0,
          display: "flex",
          flexDirection: "column",
          gap: 6,
        }}
      >
        {p.files.map((f, idx) => (
          <li
            key={`${f.name}-${idx}`}
            data-testid="report-uploaded-material-row"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "8px 10px",
              background: "var(--chalk)",
              border: "1px solid var(--ink-14)",
              borderRadius: 6,
              fontFamily: "var(--cjk)",
              fontSize: 12,
            }}
          >
            <span aria-hidden style={{ fontSize: 14 }}>
              {f.type.includes("pdf")
                ? "📄"
                : f.type.includes("word") || f.name.endsWith(".docx")
                  ? "📝"
                  : f.type.includes("sheet") || f.name.match(/\.xlsx?$/)
                    ? "📊"
                    : f.type.includes("image")
                      ? "🖼"
                      : "📎"}
            </span>
            <span
              style={{
                flex: 1,
                color: "var(--ink)",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
              title={f.name}
            >
              {f.name}
            </span>
            <span style={{ color: "var(--ink-65)", fontSize: 11, minWidth: 60 }}>
              {fmtBytes(f.size_bytes)}
            </span>
            <span style={{ color: "var(--ink-65)", fontSize: 11, minWidth: 80 }}>
              {f.parsed_chars} 字
            </span>
            <span
              data-status={f.parse_status}
              title={f.parse_note ?? f.parse_status}
              style={{
                fontSize: 10,
                padding: "2px 6px",
                borderRadius: 3,
                background: `color-mix(in srgb, ${statusColor[f.parse_status]} 18%, transparent)`,
                color: statusColor[f.parse_status],
                fontWeight: 500,
                minWidth: 50,
                textAlign: "center",
              }}
            >
              {f.parse_status}
            </span>
            <button
              type="button"
              data-testid="report-uploaded-material-remove"
              onClick={() => p.onRemove(idx)}
              aria-label={`从列表移除 ${f.name}`}
              title="从列表移除 (前端 state · 不删后端材料)"
              style={{
                padding: "3px 8px",
                fontSize: 11,
                fontFamily: "var(--cjk)",
                background: "transparent",
                border: "1px solid var(--ink-14)",
                borderRadius: 4,
                color: "var(--ink-65)",
                cursor: "pointer",
              }}
            >
              ✕
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

/* user 反馈 2026-05-22 · 模板库列表 (always-visible · 不只在 dropdown 内)
   - builtin: 5 内置 · folder icon · 不可删
   - user: N 上传 · user icon · ✎ 重命名 + 🗑 删除
   - selected 行高亮 + 点击切换 templateChoice (同 dropdown 同源)
   - validation badge: PASS / WARN / ERROR */
function TemplateLibraryList(p: {
  templates: { builtin: TemplateListItem[]; user: TemplateListItem[] };
  selectedPath: string;
  onSelect: (path: string) => void;
  onRename: (templateId: string, currentName: string) => void;
  onDelete: (templateId: string, templateName: string) => void;
}) {
  const all = [...p.templates.builtin, ...p.templates.user];
  if (all.length === 0) {
    return (
      <section
        data-testid="report-template-library-empty"
        style={{
          margin: "0 0 16px 0",
          padding: "10px 14px",
          background: "color-mix(in srgb, var(--chalk) 40%, transparent)",
          border: "1px dashed var(--ink-14)",
          borderRadius: "var(--r-md)",
          fontFamily: "var(--cjk)",
          fontSize: 12,
          color: "var(--ink-65)",
          fontStyle: "italic",
        }}
      >
        模板库加载中 · 或后端 /api/report/templates 不可达
      </section>
    );
  }
  const validBadge = (v?: TemplateListItem["validation"]) => {
    if (!v) return null;
    const m: Record<NonNullable<TemplateListItem["validation"]>, { txt: string; bg: string }> = {
      PASS: { txt: "✓ PASS", bg: "#22c55e" },
      WARN: { txt: "⚠ WARN", bg: "#f59e0b" },
      ERROR: { txt: "✗ ERROR", bg: "#ef4444" },
      SKIP: { txt: "— SKIP", bg: "#9ca3af" },
    };
    const x = m[v];
    return (
      <span
        data-validation={v}
        style={{
          fontSize: 10,
          padding: "2px 6px",
          borderRadius: 3,
          background: `color-mix(in srgb, ${x.bg} 18%, transparent)`,
          color: x.bg,
          fontWeight: 500,
        }}
      >
        {x.txt}
      </span>
    );
  };
  return (
    <section
      data-testid="report-template-library-list"
      aria-label={`模板库 · 内置 ${p.templates.builtin.length} + 我上传 ${p.templates.user.length}`}
      style={{
        margin: "0 0 16px 0",
        padding: "12px 14px",
        background: "color-mix(in srgb, var(--chalk) 55%, transparent)",
        border: "1px solid var(--ink-14)",
        borderRadius: "var(--r-md)",
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 8,
          marginBottom: 8,
          fontFamily: "var(--cjk)",
        }}
      >
        <strong style={{ fontSize: 13, color: "var(--ink)" }}>
          模板库 · 内置 {p.templates.builtin.length} · 我上传 {p.templates.user.length}
        </strong>
        <span style={{ fontSize: 11, color: "var(--ink-65)" }}>
          点击选用 · 上传新模板见上方「⇪ 上传模板」
        </span>
      </header>
      <ul
        style={{
          listStyle: "none",
          padding: 0,
          margin: 0,
          display: "flex",
          flexDirection: "column",
          gap: 6,
        }}
      >
        {p.templates.builtin.map((t) => {
          const active = p.selectedPath === t.template_path;
          return (
            <li
              key={t.template_path}
              data-testid="report-template-row-builtin"
              data-active={active ? "yes" : "no"}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "8px 10px",
                background: active
                  ? "color-mix(in srgb, var(--t-report) 12%, var(--chalk))"
                  : "var(--chalk)",
                border: `1px solid ${active ? "var(--t-report)" : "var(--ink-14)"}`,
                borderRadius: 6,
                fontFamily: "var(--cjk)",
                fontSize: 12,
                cursor: "pointer",
              }}
              onClick={() => p.onSelect(t.template_path)}
            >
              <span aria-hidden style={{ fontSize: 14 }}>📁</span>
              <span style={{ flex: 1, color: "var(--ink)" }} title={t.template_path}>
                {t.name}
              </span>
              <span
                style={{
                  fontSize: 10,
                  padding: "2px 6px",
                  borderRadius: 3,
                  background: "color-mix(in srgb, #6b7280 18%, transparent)",
                  color: "#4b5563",
                }}
              >
                内置 · 不可删
              </span>
              {t.business_line ? (
                <span style={{ fontSize: 10, color: "var(--ink-65)" }}>
                  {t.business_line}
                </span>
              ) : null}
            </li>
          );
        })}
        {p.templates.user.map((t) => {
          const active = p.selectedPath === t.template_path;
          const tid = t.template_id ?? "";
          return (
            <li
              key={t.template_path}
              data-testid="report-template-row-user"
              data-active={active ? "yes" : "no"}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "8px 10px",
                background: active
                  ? "color-mix(in srgb, var(--t-report) 12%, var(--chalk))"
                  : "var(--chalk)",
                border: `1px solid ${active ? "var(--t-report)" : "var(--ink-14)"}`,
                borderRadius: 6,
                fontFamily: "var(--cjk)",
                fontSize: 12,
              }}
            >
              <span aria-hidden style={{ fontSize: 14 }}>👤</span>
              <button
                type="button"
                onClick={() => p.onSelect(t.template_path)}
                style={{
                  flex: 1,
                  textAlign: "left",
                  background: "none",
                  border: "none",
                  padding: 0,
                  color: "var(--ink)",
                  cursor: "pointer",
                  fontFamily: "var(--cjk)",
                  fontSize: 12,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
                title={t.template_path}
              >
                {t.name}
              </button>
              {validBadge(t.validation)}
              <span style={{ fontSize: 10, color: "var(--ink-65)" }}>
                {t.placeholder_count ?? 0} 占位
                {t.residue_count && t.residue_count > 0
                  ? ` · ${t.residue_count} 残留`
                  : ""}
              </span>
              {t.uploaded_at ? (
                <span
                  style={{ fontSize: 10, color: "var(--ink-65)", minWidth: 80 }}
                  title={`上传者 ${t.uploader ?? "—"}`}
                >
                  {t.uploaded_at.slice(0, 10)}
                </span>
              ) : null}
              {tid ? (
                <>
                  <button
                    type="button"
                    data-testid="report-template-row-rename"
                    onClick={() => p.onRename(tid, t.name)}
                    title={`重命名「${t.name}」`}
                    aria-label={`重命名模板 ${t.name}`}
                    style={{
                      padding: "3px 8px",
                      fontSize: 11,
                      fontFamily: "var(--cjk)",
                      background: "transparent",
                      border: "1px solid var(--ink-14)",
                      borderRadius: 4,
                      color: "var(--ink-65)",
                      cursor: "pointer",
                    }}
                  >
                    ✎
                  </button>
                  <button
                    type="button"
                    data-testid="report-template-row-delete"
                    onClick={() => p.onDelete(tid, t.name)}
                    title={`删除「${t.name}」(soft delete · 可由管理员从 .archived/ 恢复)`}
                    aria-label={`删除模板 ${t.name}`}
                    style={{
                      padding: "3px 8px",
                      fontSize: 11,
                      fontFamily: "var(--cjk)",
                      background: "transparent",
                      border: "1px solid #ef4444",
                      borderRadius: 4,
                      color: "#dc2626",
                      cursor: "pointer",
                    }}
                  >
                    🗑
                  </button>
                </>
              ) : null}
            </li>
          );
        })}
      </ul>
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
        /* B.4 SLO-3 · report-bug-2 · 等待触发 panel 中间 500-600px 巨大空白
         * 真因: padding 48/24 + minHeight calc(100vh-360px) 强 ~720px @ 1080 viewport
         *      内容 (title + 1 段 + 4 li) 只 ~200px · flex column justify-content center
         *      = panel 上下大量空白
         * 修: padding 28/24 + 删 minHeight (跟内容走) · 仍 flex column 居中
         */
        padding: "28px 24px",
        textAlign: "center",
        background: "color-mix(in srgb, var(--chalk) 50%, transparent)",
        borderRadius: "var(--r-md)",
        border: "1px dashed var(--ink-14)",
        margin: "24px 0 64px 0",
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
        触发 v16 主管线（classifier → generator → QC gate）。
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
        生成流程 {p.mode === "mock" ? "· 示例" : ""}
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
        </span>
      ) : null}
    </section>
  );
}

function ReportLiveSections(p: {
  sections: ReportV16Section[];
  evidences?: ReportV16Evidence[];
  onRefine: (sectionId: string, userEdit: string) => void;
  mode: "mock" | "live";
}) {
  const [activeId, setActiveId] = useState<string | null>(
    p.sections[0]?.id ?? null,
  );
  const [draft, setDraft] = useState<string>("");
  const active = p.sections.find((s) => s.id === activeId) ?? null;
  /* ALL IN Phase B step 4 · 字段级 evidence drawer · per shared/evidence_drawer + AGENT_IDENTITY-report.md §6
     filter 当前 active section 的 evidence (claim_id 关联) · 显示 source / tier / date 等 */
  const activeEvidences = (p.evidences ?? []).filter(
    (ev) => ev.claim_id === activeId,
  );

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
      {/* ALL IN Phase B step 4 · 字段级 evidence drawer · per shared/evidence_drawer
          每 active section 下方列证据来源 · source / tier / date / snippet · 红线 3 (无证据 claim) 闸门 */}
      {activeEvidences.length > 0 ? (
        <div
          data-testid="report-evidence-drawer"
          style={{
            marginTop: 10,
            padding: "10px 12px",
            background: "color-mix(in srgb, var(--t-report) 6%, transparent)",
            border: "1px dashed color-mix(in srgb, var(--t-report) 40%, transparent)",
            borderRadius: 6,
            fontFamily: "var(--cjk)",
            fontSize: 11.5,
            color: "var(--ink-65)",
          }}
        >
          <strong style={{ display: "block", marginBottom: 6, color: "var(--ink)", fontSize: 12 }}>
            §证 字段级溯源 · {activeEvidences.length} 条
          </strong>
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 6 }}>
            {activeEvidences.map((ev) => (
              <li
                key={ev.evidence_id}
                data-testid="report-evidence-item"
                data-evidence-id={ev.evidence_id}
                style={{
                  padding: "6px 8px",
                  background: "var(--chalk)",
                  borderRadius: 4,
                  borderLeft: `3px solid ${
                    ev.source_tier === 1
                      ? "var(--t-compli, #4A7A5E)"
                      : ev.source_tier === 2
                        ? "var(--t-report)"
                        : ev.source_tier === 3
                          ? "var(--ink-65)"
                          : "var(--ink-14)"
                  }`,
                }}
              >
                <div style={{ display: "flex", gap: 8, alignItems: "baseline", flexWrap: "wrap" }}>
                  <span style={{ fontSize: 10, padding: "1px 5px", borderRadius: 3, background: "var(--ink-14)", color: "var(--ink)" }}>
                    Tier {ev.source_tier}
                  </span>
                  <span style={{ fontFamily: "var(--mono)", fontSize: 10.5 }}>
                    {ev.source}
                  </span>
                  {ev.evidence_date ? (
                    <span style={{ fontSize: 10, color: "var(--ink-65)" }}>
                      · {ev.evidence_date}
                    </span>
                  ) : null}
                  {ev.source_url ? (
                    <a
                      href={ev.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ fontSize: 10, color: "var(--t-report)", textDecoration: "underline" }}
                    >
                      跳源 ↗
                    </a>
                  ) : null}
                </div>
                <div style={{ marginTop: 3, color: "var(--ink)", fontSize: 11 }}>
                  {ev.anchor} · {ev.snippet}
                </div>
              </li>
            ))}
          </ul>
          <p style={{ margin: "6px 0 0 0", fontSize: 10, color: "var(--ink-65)", fontStyle: "italic" }}>
            每个字段均可回链到来源材料；材料更新后自动复核。
          </p>
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
