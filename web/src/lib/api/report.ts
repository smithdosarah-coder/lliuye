/**
 * Agent6 Report backend client · 6 endpoint helper · Phase A worker-A4 (2026-04-29).
 *
 * 后端契约 (Phase A worker-A4 align v16 · audit cat 4):
 *   POST /api/report/upload          → {report_id, file_summary, total_*}
 *   POST /api/report/v16/fill        → SSE stage / done events (live · DEEPSEEK 必需)
 *   POST /api/report/demo/run        → SSE 演示 (live · sample_id DP001-005 · 真后端跑 · Phase B.2)
 *   POST /api/report/refine_section  → {section, status, llm_used}
 *   POST /api/report/export_docx     → docx blob (attachment)
 *   POST /api/report/export_pdf      → pdf blob (attachment · G-10 闭环)
 *   GET  /api/report/downloads/{id}  → docx blob (attachment alias)
 *
 * 设计:
 *   - 走相对 path · prod 透 nginx · dev 用 NEXT_PUBLIC_API_BASE
 *   - SSE 消费用 fetch + ReadableStream + 行级解析(无外部依赖)
 *   - empty-state-design-protocol §3 · 调用方负责 user-trigger 时机
 */
import { type DataSourceKind, normalizeDataSource } from "./_data-source";

export type { DataSourceKind };

const API_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE) || "";

export type ReportFileSummary = {
  name: string;
  type: string;
  size_bytes: number;
  parsed_chars: number;
  parse_status: "ok" | "skipped" | "deferred" | "empty" | "error" | "save_failed";
  parse_note?: string;
  saved_path?: string;
};

export type ReportUploadResponse = {
  report_id: string;
  session_id: string;
  business_line: string;
  file_summary: ReportFileSummary[];
  total_files: number;
  total_parsed_chars: number;
};

export type ReportV16StageEvent = {
  event: "stage";
  stage: "ingest" | "extract" | "infer" | "write" | "audit";
  progress: number;
  message: string;
  pipeline?: "v16";
};

export type ReportV16Section = {
  id: string;
  title: string;
  content: string;
  status: "pending" | "writing" | "done" | "qc_blocked";
  word_count?: number;
};

export type ReportV16PendingQuestion = {
  id: string;
  label?: string;
  recommended?: string;
  source_ref?: string;
};

/** ALL IN Phase B step 6 · per shared/entity_resolver/resolver.py:EntityKey dataclass.
 *  报告对象企业归一 · 防同企业多次写报告 + 跨 agent handoff 主键稳定 (per entity-resolution-contract v1.1 §5) */
export type ReportEntityKey = {
  uscc: string;            // 18 位 USCC (per GB 32100-2015) · empty 时退化 name_only
  name_normalized: string; // 规则化清洗后企业名
  confidence: number;      // 1.0 (USCC anchored) / 0.5 (name only) / 0.0 (empty)
};

export type ReportProfile = {
  company_name?: string;
  uscc?: string;
  entity_key?: ReportEntityKey;  // ALL IN step 6 · 跨 agent handoff 主键 (Agent3 决策回写 / Agent6 重复检测)
  [k: string]: unknown;
};

/** ALL IN Phase B step 4 · per shared/evidence_drawer/drawer.py:Evidence dataclass.
 *  字段级 evidence · claim_id 关联到具体 section/field (e.g. "chapter_3_finance")
 *  EvidenceDrawer 渲染时按 claim_id group · 消费 to_drawer_payload 同源 schema. */
export type ReportV16Evidence = {
  evidence_id: string;
  claim_id: string;
  source: string;            // "uploaded_material:行业研究.docx" / "tavily:url" / "gsxt:USCC"
  anchor: string;            // "page=3§2" / "Sheet1!B7" / "para=2"
  snippet: string;
  source_tier: 1 | 2 | 3 | 4; // 1=内部权威 / 2=政府监管 / 3=行业 / 4=公开 web
  source_url?: string | null;
  evidence_date?: string | null;
  retrieved_at: string;
  claim_type: string;        // "news" / "financial" / "registry" / "industry" / ...
  version: string;
  content_hash: string;
  confidence: number;        // 0.0-1.0
};

export type ReportV16DoneEvent = {
  event: "done";
  report_id: string;
  session_id: string;
  pipeline: "v16";
  /** 历史 boolean · 件 #2 起以 data_source 5 enum 为 trust model 一级 · 本字段保留向后兼容. */
  mock_pipeline: boolean;
  /** 5 enum (per shared/sse_envelope.py:81-86 + agent_report/api.py:1138). */
  data_source?: DataSourceKind;
  source_docx?: string;
  report_docx_url?: string | null;
  output_docx_path?: string | null;
  qc?: {
    passed?: boolean;
    score?: number;
    fatal_fail?: boolean;
    halluc_count?: number;
  };
  stats?: Record<string, unknown>;
  pending_questions?: ReportV16PendingQuestion[];
  sections?: ReportV16Section[];
  /** ALL IN Phase B step 4 · 字段级 evidence list · per shared/evidence_drawer · 前端按 claim_id group */
  evidences?: ReportV16Evidence[];
  /** ALL IN Phase B step 6 · 报告对象企业归一 · 含 entity_key (per entity-resolution-contract v1.1 §5) */
  profile?: ReportProfile;
};


/**
 * 派生工具 · ReportV16DoneEvent 兜底取 data_source.
 * 优先 done.data_source · 缺失则按 mock_pipeline 派生 (兼容旧 backend 没填 data_source 的现场).
 *
 * - mock_pipeline=true 但缺 data_source → "mock_forced" (前端显式 DEMO 触发的情况)
 * - mock_pipeline=false 但缺 data_source → "live"
 * - 任何非 5 enum 字符串 → "mock" (normalizeDataSource 兜空)
 */
export function reportDoneDataSource(done: ReportV16DoneEvent): DataSourceKind {
  if (done.data_source) return normalizeDataSource(done.data_source);
  return done.mock_pipeline ? "mock_forced" : "live";
}

export type ReportV16ErrorEvent = {
  event: "error";
  stage?: string;
  message: string;
  pipeline?: "v16";
  /* Phase B.2 (PM 2026-05-10) · 后端 SSE error event 可带 typed code (V16_REAL_PATH_FAILED 等) ·
     前端 typed banner 消费 (per dispatch §"错误降级" Step 5) */
  code?: string;
};

export type ReportV16Event =
  | ReportV16StageEvent
  | ReportV16DoneEvent
  | ReportV16ErrorEvent;

export type ReportRefineResponse = {
  session_id: string;
  report_id: string;
  section: ReportV16Section & { refined_at?: string };
  status: "ok";
  llm_used: boolean;
};

/* ── multipart upload ──────────────────────────────────────────────── */

export async function uploadReportMaterials(
  files: File[],
  businessLine: string = "corporate",
): Promise<ReportUploadResponse> {
  if (!files.length) throw new Error("至少选一个材料文件");
  const fd = new FormData();
  for (const f of files) fd.append("files", f, f.name);
  const url = `${API_BASE}/api/report/upload?business_line=${encodeURIComponent(businessLine)}`;
  const resp = await fetch(url, { method: "POST", body: fd });
  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw new Error(`upload 失败 HTTP ${resp.status} · ${text.slice(0, 120)}`);
  }
  return (await resp.json()) as ReportUploadResponse;
}

/* ── SSE consume: POST /api/report/v16/fill ────────────────────────── */

export type ReportV16FillRequest = {
  report_id?: string;
  source_docx?: string;
  material_dir?: string;
  classified_json?: string;
  business_line?: string;
  mock?: boolean;
};

/**
 * 流式消费 v16 fill SSE event 队列。每条 event 调 onEvent。
 * 完成或 error 时触发 onClose / onError(由 caller 决定 abort 控制)。
 */
export async function streamReportV16Fill(
  body: ReportV16FillRequest,
  callbacks: {
    onEvent: (evt: ReportV16Event) => void;
    onClose?: () => void;
    onError?: (err: Error) => void;
    signal?: AbortSignal;
  },
): Promise<void> {
  const url = `${API_BASE}/api/report/v16/fill`;
  let resp: Response;
  try {
    resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: callbacks.signal,
    });
  } catch (e) {
    callbacks.onError?.(e instanceof Error ? e : new Error(String(e)));
    return;
  }
  if (!resp.ok || !resp.body) {
    const txt = await resp.text().catch(() => "");
    callbacks.onError?.(
      new Error(`v16/fill HTTP ${resp.status} · ${txt.slice(0, 120)}`),
    );
    return;
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buf = "";
  try {
    /* eslint-disable no-await-in-loop */
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      // Split on SSE record separator
      let idx: number;
      while ((idx = buf.indexOf("\n\n")) !== -1) {
        const chunk = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        const evt = parseSseChunk(chunk);
        if (evt) callbacks.onEvent(evt);
      }
    }
    /* eslint-enable no-await-in-loop */
  } catch (e) {
    callbacks.onError?.(e instanceof Error ? e : new Error(String(e)));
    return;
  } finally {
    callbacks.onClose?.();
  }
}

function parseSseChunk(chunk: string): ReportV16Event | null {
  let event = "";
  let data = "";
  for (const line of chunk.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data = line.slice(5).trim();
  }
  if (!event || !data) return null;
  try {
    const parsed = JSON.parse(data);
    return { event, ...parsed } as ReportV16Event;
  } catch {
    return null;
  }
}

/* ── SSE consume: POST /api/report/demo/run ─────────────────────────────
   Phase B.2 (PM 2026-05-10 真意 reframe) · 演示 = 上传 sample 跑真后端
   sample_id 映射到 data/mock/deep-pillar/<id>/ 真材料 (DP001-005) ·
   后端: v16_runner.fill_stream(explicit_mock=False) · 真 LLM (DeepSeek) + 真 9 维 QC
   契约同 v16/fill done event (sections + qc + stats + profile + data_source=live)
   反模式 (已废): scenario_id easy/medium/hard yield fixture (Phase A worker-A4) */

export type ReportSampleId =
  | "DP001_龙峰精工"
  | "DP002_蓝汀家电"
  | "DP003_宸星家装"
  | "DP004_汇德建材"
  | "DP005_星胤实业";

export type ReportDemoRunRequest = {
  sample_id: ReportSampleId | string; // string fallback · 后端白名单校验
};

export async function streamReportDemoRun(
  body: ReportDemoRunRequest,
  callbacks: {
    onEvent: (evt: ReportV16Event) => void;
    onClose?: () => void;
    onError?: (err: Error) => void;
    signal?: AbortSignal;
  },
): Promise<void> {
  const url = `${API_BASE}/api/report/demo/run`;
  let resp: Response;
  try {
    resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: callbacks.signal,
    });
  } catch (e) {
    callbacks.onError?.(e instanceof Error ? e : new Error(String(e)));
    return;
  }
  if (!resp.ok || !resp.body) {
    /* Phase B.2 (PM 2026-05-10) · 错误降级 typed banner · Step 5
       后端 typed error: 503 + {detail: {error: {code, message}}} (DEEPSEEK_KEY_MISSING /
       DEMO_CLASSIFIER_MISSING / DEMO_TEMPLATE_MISSING / SAMPLE_DIR_MISSING / SAMPLE_ID_INVALID)
       不 silent · 不 fallback fake · 直接抛带 code 的 Error · ReportLaunchErrorBanner 消费 */
    const txt = await resp.text().catch(() => "");
    let typedMsg = `demo/run HTTP ${resp.status}`;
    let typedCode: string | undefined;
    try {
      const parsed = JSON.parse(txt) as { detail?: { error?: { code?: string; message?: string } } };
      const inner = parsed?.detail?.error;
      if (inner?.code) {
        typedCode = inner.code;
        typedMsg = `[${inner.code}] ${inner.message ?? ""}`.trim();
      }
    } catch {
      typedMsg = `${typedMsg} · ${txt.slice(0, 200)}`;
    }
    const err = new Error(typedMsg);
    if (typedCode) (err as Error & { code?: string }).code = typedCode;
    callbacks.onError?.(err);
    return;
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buf = "";
  try {
    /* eslint-disable no-await-in-loop */
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let idx: number;
      while ((idx = buf.indexOf("\n\n")) !== -1) {
        const chunk = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        const evt = parseSseChunk(chunk);
        if (evt) callbacks.onEvent(evt);
      }
    }
    /* eslint-enable no-await-in-loop */
  } catch (e) {
    callbacks.onError?.(e instanceof Error ? e : new Error(String(e)));
    return;
  } finally {
    callbacks.onClose?.();
  }
}

/* ── refine_section ─────────────────────────────────────────────────── */

export async function refineReportSection(args: {
  session_id: string;
  section_id: string;
  user_edit: string;
  target_word_count?: number;
}): Promise<ReportRefineResponse> {
  const url = `${API_BASE}/api/report/refine_section`;
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(args),
  });
  if (!resp.ok) {
    const txt = await resp.text().catch(() => "");
    throw new Error(
      `refine_section HTTP ${resp.status} · ${txt.slice(0, 120)}`,
    );
  }
  return (await resp.json()) as ReportRefineResponse;
}

/* ── export_docx ────────────────────────────────────────────────────── */

export type ReportExportPayload = {
  session_id?: string;
  report_id?: string;
  profile?: Record<string, unknown>;
  sections?: ReportV16Section[];
  pending_questions?: ReportV16PendingQuestion[];
  stats?: Record<string, unknown>;
  qc?: Record<string, unknown>;
  business_line?: string;
  client_manager?: string;
};

/**
 * 调 export_docx 端点 · 返 Blob (caller 用 URL.createObjectURL + a.click 触发下载)。
 */
export async function exportReportDocx(
  payload: ReportExportPayload,
): Promise<{ blob: Blob; filename: string }> {
  const url = `${API_BASE}/api/report/export_docx`;
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const txt = await resp.text().catch(() => "");
    throw new Error(`export_docx HTTP ${resp.status} · ${txt.slice(0, 120)}`);
  }
  const blob = await resp.blob();
  const filename = parseFilenameFromContentDisposition(
    resp.headers.get("content-disposition") || "",
  );
  return { blob, filename };
}

function parseFilenameFromContentDisposition(cd: string): string {
  // RFC 6266 · 优先 filename*=UTF-8''<encoded>
  const star = cd.match(/filename\*=UTF-8''([^;]+)/i);
  if (star) {
    try {
      return decodeURIComponent(star[1].trim());
    } catch {
      /* fall through */
    }
  }
  const ascii = cd.match(/filename="?([^"';]+)"?/i);
  if (ascii) return ascii[1].trim();
  return "agent6_report.docx";
}

/**
 * 调 export_pdf 端点 · 返 Blob (Phase A worker-A4 · prd-evidence-frozen G-10 闭环).
 * 与 export_docx 共用 ReportExportPayload schema · 同源异格 (docx 走 word_export.py · pdf 走 reportlab).
 */
export async function exportReportPdf(
  payload: ReportExportPayload,
): Promise<{ blob: Blob; filename: string }> {
  const url = `${API_BASE}/api/report/export_pdf`;
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const txt = await resp.text().catch(() => "");
    throw new Error(`export_pdf HTTP ${resp.status} · ${txt.slice(0, 120)}`);
  }
  const blob = await resp.blob();
  const filename = parseFilenameFromContentDisposition(
    resp.headers.get("content-disposition") || "",
  );
  return { blob, filename };
}

/**
 * 触发浏览器下载 · 用 export_docx 返的 Blob + 文件名。
 */
export function triggerDownloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    URL.revokeObjectURL(url);
    a.remove();
  }, 100);
}
