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

/**
 * D Phase 4 worker 5 · v16 placeholder schema v1.1 (templates/placeholder-schema.json)。
 * 前端可选传入 client_metadata · v16_generator REPLACE handler 用此填 {{KEY}} placeholder。
 * 所有字段 optional · 缺则保留 {{KEY}} 原文 + pending (符合"幻觉零容忍 · 字段填不了标 未能自动填写"红线)。
 *
 * scope_tag 分组 (per placeholder-schema.json:scope_tag_legend):
 *   - corporate (31): 对公场景 · 经纬测绘 / 兴业资管 / 普惠 / 科创
 *   - retail (23):    对私场景 · 小微对私 (worker 4)
 *   - both (3):       CLIENT_FULL_NAME / CREDIT_AMOUNT / CREDIT_PERIOD
 *
 * 后端契约:
 *   - 后端按 schema_version 校验 · v1.0 调用方仍兼容 (v1.0 字段全保留)
 *   - 后端不会 reject 多余 key · 但 v16_classifier 按 scope_tag 路由 · 跨 scope 传值 = 浪费 (e.g. 对私场景传 CLIENT_USCC 不会被消费)
 *
 * 不破坏既有 fetch logic: 调用方可不传 client_metadata · 兼容 ReportV16FillRequest / ReportDemoRunRequest 旧 shape。
 */
export interface ClientMetadata {
  /* ── scope=both (v1.0 复用 · 对公/对私通用) ─────────────────────── */
  /** 客户主体全称 · 对公=企业全称 · 对私=自然人姓名 */
  CLIENT_FULL_NAME?: string;
  /** 综合授信额度 (含单位) */
  CREDIT_AMOUNT?: string;
  /** 授信期限 */
  CREDIT_PERIOD?: string;

  /* ── scope=corporate · v1.0 对公场景 ────────────────────────────── */
  CLIENT_CORE_NAME?: string;
  CLIENT_LEGAL_REP?: string;
  CLIENT_USCC?: string;
  CLIENT_ESTABLISHMENT_DATE?: string;
  CLIENT_REGISTERED_CAPITAL?: string;
  CLIENT_PAID_IN_CAPITAL?: string;
  CLIENT_REGISTERED_ADDRESS?: string;
  CLIENT_OPERATING_ADDRESS?: string;
  CLIENT_LOCATION_CITY?: string;
  CLIENT_INDUSTRY_FULL?: string;
  CLIENT_INDUSTRY_CODE?: string;
  CLIENT_INDUSTRY_CATEGORY?: string;
  CLIENT_BUSINESS_SCOPE?: string;
  CLIENT_BUSINESS_DESC?: string;
  CLIENT_BACKGROUND?: string;
  CLIENT_PARENT_FULL_NAME?: string;
  CLIENT_PARENT_SHORT_NAME?: string;
  CLIENT_GROUP_FULL_NAME?: string;
  CLIENT_GROUP_SHORT_NAME?: string;
  CLIENT_LONG_CORE_NAME?: string;
  CLIENT_OPERATING_YEARS?: string;
  CLIENT_EMPLOYEE_COUNT?: string;
  CLIENT_SHAREHOLDER_PRIMARY?: string;
  CLIENT_SHARE_PCT_PRIMARY?: string;
  CREDIT_EXPOSURE?: string;
  PD_RATING?: string;
  INDUSTRY_POLICY_GUIDANCE?: string;
  FOUNDED_YEAR?: string;
  BUSINESS_QUALIFICATION_DESC?: string;
  BUSINESS_HISTORY_DESC?: string;
  BUSINESS_STRATEGY_DESC?: string;

  /* ── scope=retail · v1.1 worker 4 小微对私 (5 分组) ─────────────── */

  /* group: personal_identity */
  /** 身份证号 (18 位 · 极敏感) */
  CLIENT_ID_NUMBER?: string;
  /** 工作单位或经营实体名称 */
  CLIENT_EMPLOYER_OR_BUSINESS?: string;
  /** 职务或经营年限 */
  CLIENT_POSITION_OR_YEARS?: string;
  /** 婚姻状况 (enum: 已婚 / 未婚 / 离异 / 丧偶) · checkbox_tick handler 消费 */
  CLIENT_MARITAL_STATUS?: "已婚" | "未婚" | "离异" | "丧偶";
  /** 家庭年收入 (万元) */
  CLIENT_HOUSEHOLD_INCOME?: string;
  /** 家庭住址 (敏感) */
  CLIENT_HOME_ADDRESS?: string;
  /** 联系方式 · 手机号 (敏感) */
  CLIENT_PHONE?: string;

  /* group: credit_report_facts */
  /** 本人查询次数 (近 2 年) */
  CREDIT_QUERY_COUNT_2Y?: number;
  /** 贷款审批查询 (近 6 个月) */
  CREDIT_LOAN_QUERY_6M?: number;
  /** 信用卡审批查询 (近 6 个月) */
  CREDIT_CARD_QUERY_6M?: number;
  /** 在贷余额 (万元) */
  CREDIT_OUTSTANDING_BALANCE?: string;
  /** 逾期记录 (无逾期 / 1 次 30 天内 / N 次) */
  CREDIT_OVERDUE_RECORD?: string;

  /* group: repayment_capacity */
  /** 月均收入 (元) */
  CLIENT_MONTHLY_INCOME?: string;
  /** 月均负债支出 (元) */
  CLIENT_MONTHLY_DEBT_PAYMENT?: string;
  /** 月均偿债比 Debt-Service Ratio (%) */
  CLIENT_DSR?: string;
  /** 可还款能力评估 (短叙述) */
  REPAYMENT_ABILITY_ASSESSMENT?: string;

  /* group: credit_application_personal */
  /** 还款方式 (enum) · checkbox_tick handler 消费 */
  REPAYMENT_METHOD?: "等额本息" | "等额本金" | "一次还本付息";
  /** 授信用途 */
  CREDIT_PURPOSE?: string;
  /** 担保方式 (enum) · checkbox_tick handler 消费 */
  GUARANTEE_METHOD?: "信用" | "抵押" | "第三方保证";

  /* group: risk_and_conclusion */
  /** 主要风险点 */
  RISK_KEY_POINTS?: string;
  /** 缓释措施 */
  RISK_MITIGATION?: string;
  /** 建议授信结论 (enum) */
  CREDIT_CONCLUSION?: "同意" | "不同意" | "有条件同意";
  /** 前提条件 */
  CREDIT_PRECONDITIONS?: string;

  /** 未来扩展兜底 · 后端遇到未知 key 不 reject · 但 v16_classifier 不会路由 */
  [k: string]: string | number | boolean | undefined;
}

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
  const resp = await fetch(url, { method: "POST", body: fd, credentials: "include" });
  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw new Error(`upload 失败 HTTP ${resp.status} · ${text.slice(0, 120)}`);
  }
  return (await resp.json()) as ReportUploadResponse;
}

/* ── Q6-B · 用户自定义 docx 模板上传 + lint ────────────────────────────
   后端: POST /api/report/upload-template (multipart: file + ?template_name=...&business_line=...)
   - byte-level diff standalone lint 自动检测 placeholder 完整性
   - 返 validation_report 给客户经理 (PASS/WARN/ERROR)
   - persistent 到 data/kb/templates/{id}/ · 共享可见 (uploader 字段审计)
*/

export type TemplateValidationReport = {
  template_id: string;
  template_name: string;
  filename: string;
  business_line: string;
  uploader: string;
  uploaded_at: string;
  size_bytes: number;
  placeholder_count: number;       // 位置维度 · 一个 element 多 placeholder 算多次
  placeholder_keys: string[];      // unique {{KEY}} 列表 · sorted
  residue_count: number;           // 未 placeholder 化的 specific 字面数
  residue_samples: Array<{
    location: string;              // "P3" / "T0R1C2P0" element 位置
    element_kind: "para" | "cell";
    kind: "company" | "person" | "money" | "date" | "id_number" | "uscc";
    value: string;
    snippet: string;               // 前 100 字符上下文
  }>;
  validation: "PASS" | "WARN" | "ERROR" | "SKIP";
  element_count: number;
  lint_error?: string | null;
  template_ref: string;            // "user-template:{id}" · V16FillRequest source_docx 直接用
};

export type TemplateUploadResponse = {
  template_id: string;
  template_path: string;           // = template_ref
  validation_report: TemplateValidationReport;
  /** CRUD 完整 (2026-05-21) · 同 template_name 已存在的 user 模板 ID 列表 · 已被自动 archive
   *  前端可在 banner 提示 "已替换 N 份同名旧模板" · 让客户经理知道 supersede 发生 */
  superseded_ids?: string[];
};

export async function uploadReportTemplate(
  file: File,
  templateName: string,
  businessLine: string = "corporate",
): Promise<TemplateUploadResponse> {
  if (!file) throw new Error("请选模板 docx 文件");
  if (!templateName || templateName.trim().length < 2) {
    throw new Error("template_name 至少 2 字符");
  }
  const fd = new FormData();
  fd.append("file", file, file.name);
  const qs = new URLSearchParams({
    template_name: templateName,
    business_line: businessLine,
  });
  const url = `${API_BASE}/api/report/upload-template?${qs.toString()}`;
  const resp = await fetch(url, { method: "POST", body: fd, credentials: "include" });
  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    // typed error code (per 后端 detail.error.code)
    let typedMsg = `upload-template 失败 HTTP ${resp.status}`;
    try {
      const parsed = JSON.parse(text) as { detail?: { error?: { code?: string; message?: string } } };
      const inner = parsed?.detail?.error;
      if (inner?.code) typedMsg = `[${inner.code}] ${inner.message ?? ""}`.trim();
    } catch {
      typedMsg = `${typedMsg} · ${text.slice(0, 160)}`;
    }
    throw new Error(typedMsg);
  }
  return (await resp.json()) as TemplateUploadResponse;
}

export type TemplateListItem = {
  template_path: string;          // builtin "samples/xxx.docx" · user "user-template:{id}"
  name: string;
  type: "builtin" | "user";
  business_line?: string;
  // user 字段 (builtin 没有)
  uploader?: string;
  uploaded_at?: string;
  placeholder_count?: number;
  residue_count?: number;
  validation?: "PASS" | "WARN" | "ERROR" | "SKIP";
  size_bytes?: number;
  filename?: string;
  template_id?: string;
};

export type TemplateListResponse = {
  builtin: TemplateListItem[];     // 5 内置
  user: TemplateListItem[];        // N user 上传 · sort by uploaded_at DESC
};

export async function listReportTemplates(): Promise<TemplateListResponse> {
  const url = `${API_BASE}/api/report/templates`;
  const resp = await fetch(url, { method: "GET", credentials: "include" });
  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw new Error(`templates 列表失败 HTTP ${resp.status} · ${text.slice(0, 120)}`);
  }
  return (await resp.json()) as TemplateListResponse;
}

/* ── Q6-B CRUD 完整 (2026-05-21 · agent17 TODO medium-value 3 项) ─────────
   DELETE  /api/report/templates/{id}  → soft-delete (搬 .archived/{id}/)
   PATCH   /api/report/templates/{id}  → 重命名 (只改 metadata.template_name)
   Boundary: 只允许 user-* template · builtin 拒 (typed error · banner 友好提示)
*/

/** typed error · 把后端 detail.error.{code, message} 揉成可读 Error · 前端 banner 消费 */
function _parseTypedError(text: string, fallbackHttp: number): Error {
  try {
    const parsed = JSON.parse(text) as {
      detail?: { error?: { code?: string; message?: string } };
    };
    const inner = parsed?.detail?.error;
    if (inner?.code) {
      const e = new Error(`[${inner.code}] ${inner.message ?? ""}`.trim());
      (e as Error & { code?: string }).code = inner.code;
      return e;
    }
  } catch {
    /* fall through to plain HTTP */
  }
  return new Error(`HTTP ${fallbackHttp} · ${text.slice(0, 160)}`);
}

export type TemplateDeleteResponse = {
  deleted: string;
  archive_path: string;
  archived_at: string;
  archive_reason: string;
};

export async function deleteReportTemplate(
  templateId: string,
): Promise<TemplateDeleteResponse> {
  if (!templateId || !templateId.startsWith("user-")) {
    throw new Error("仅 user-* 模板可删 · 内置模板拒删");
  }
  const url = `${API_BASE}/api/report/templates/${encodeURIComponent(templateId)}`;
  const resp = await fetch(url, { method: "DELETE", credentials: "include" });
  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw _parseTypedError(text, resp.status);
  }
  return (await resp.json()) as TemplateDeleteResponse;
}

export type TemplatePatchResponse = {
  updated: string;
  metadata: TemplateValidationReport & { renamed_at?: string; renamed_by?: string };
  noop: boolean;
};

export async function renameReportTemplate(
  templateId: string,
  newName: string,
): Promise<TemplatePatchResponse> {
  if (!templateId || !templateId.startsWith("user-")) {
    throw new Error("仅 user-* 模板可重命名 · 内置模板拒改");
  }
  const trimmed = (newName ?? "").trim();
  if (trimmed.length < 2 || trimmed.length > 80) {
    throw new Error("模板名长度必须 2-80 字符");
  }
  const url = `${API_BASE}/api/report/templates/${encodeURIComponent(templateId)}`;
  const resp = await fetch(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ template_name: trimmed }),
  });
  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw _parseTypedError(text, resp.status);
  }
  return (await resp.json()) as TemplatePatchResponse;
}

/* ── SSE consume: POST /api/report/v16/fill ────────────────────────── */

export type ReportV16FillRequest = {
  report_id?: string;
  source_docx?: string;
  material_dir?: string;
  classified_json?: string;
  business_line?: string;
  mock?: boolean;
  /** D Phase 4 worker 5 · v16 placeholder schema v1.1 client_metadata · 缺则保留 {{KEY}} pending */
  client_metadata?: ClientMetadata;
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
      credentials: "include",
    credentials: "include",
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
  /** D Phase 4 worker 5 · 演示 (demo) 路径也支持 v16 placeholder schema v1.1 client_metadata · 缺则用 sample fixture 自身 metadata */
  client_metadata?: ClientMetadata;
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
      credentials: "include",
    credentials: "include",
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
    credentials: "include",
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
    credentials: "include",
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
    credentials: "include",
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
