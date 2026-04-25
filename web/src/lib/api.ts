/**
 * API client — thin wrapper around the FastAPI backend.
 * Base URL honors NEXT_PUBLIC_API_BASE env, defaulting to localhost:8000.
 *
 * Report (Agent6 V14-A) endpoints are served on a separate process :8002.
 * We expose them via Next.js rewrite `/api/report/*` → `:8002/api/report/*`
 * so the browser sees same-origin (no CORS preflight pain).
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

export const REPORT_API_BASE =
  process.env.NEXT_PUBLIC_REPORT_API_BASE ?? "/api/report";

export type BackendSegment = "corporate" | "retail";

// ---------------------------------------------------------------------------
// Evidence-First Protocol · SSE 扩展(Batch 2)
// ---------------------------------------------------------------------------
// 对齐 shared/evidence/protocol.py `AuditedResult.to_dict()` shape。
// 5 Agent(channel/credit/alert/compliance/riskctrl)的 done 事件 payload 可带;
// Agent6 report 目前不带,workspace 层自行处置。
// 前端只消费,不回写,不 mutate backend 契约。

export type { EvidenceItem, AuditPayload, AuditFinding } from "@/components/evidence/types";

export interface PresetsResponse {
  segment: BackendSegment;
  presets: string[];
}

export async function fetchPresets(
  segment: BackendSegment
): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/credit/presets/${segment}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`presets ${res.status}`);
  const j: PresetsResponse = await res.json();
  return j.presets;
}

export interface DecisionEvent {
  event: "profile_loaded" | "stage" | "done" | "error";
  stage?: string;
  payload?: unknown;
  profile?: unknown;
  message?: string;
  traceback?: string;
  /** Evidence-First 扩展(done 事件携带);见 shared/evidence/protocol.py */
  evidence_trail?: import("@/components/evidence/types").EvidenceItem[];
  unfilled_fields?: string[];
  findings?: import("@/components/evidence/types").AuditFinding[];
  blocked?: boolean;
}

/**
 * Stream decision events — reads SSE from backend.
 * Consumer passes onEvent callback for each event, and promise resolves when done.
 */
export async function streamDecision(
  req: {
    segment: BackendSegment;
    preset_name: string;
    provider?: string;
    api_key?: string;
  },
  onEvent: (evt: DecisionEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/credit/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`decision ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      const payload = line.slice(5).trim();
      if (!payload) continue;
      try {
        const obj = JSON.parse(payload) as DecisionEvent;
        onEvent(obj);
      } catch {
        // ignore malformed
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Agent6 — 信贷报告助手 (V14-A) streaming
// ---------------------------------------------------------------------------

import type { ReportEvent, ReportDonePayload, BusinessLine } from "./credit-types";

export interface ReportFillParams {
  preset?: string;              // "dingsheng_trade" 等,与后端 preset 对齐
  mock?: boolean;               // true → 走后端 ?mock=1 快速路径
  files?: File[];               // 真实上传(mock=false 时)
  business_line?: BusinessLine; // V14-D:业务线
  template_file?: File;         // V14-D:客户自传模板(可选)
}

export interface ReportHealth {
  status: string;
  llm_connected: boolean;
  version?: string;
}

/**
 * 查询后端 LLM 连接状态(用于右上角状态灯)。
 * 后端不会返回 API key 内容,只返回布尔。
 */
export async function getReportHealth(): Promise<ReportHealth> {
  try {
    // REPORT_API_BASE already includes /api/report, backend exposes /api/report/health
    const res = await fetch(`${REPORT_API_BASE}/health`, { cache: "no-store" });
    if (!res.ok) return { status: "error", llm_connected: false };
    return (await res.json()) as ReportHealth;
  } catch {
    return { status: "error", llm_connected: false };
  }
}

/** Generic SSE reader — yields each parsed JSON event object. */
async function* readSSE<T>(
  res: Response,
  signal?: AbortSignal
): AsyncGenerator<T> {
  if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      if (signal?.aborted) return;
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";
      for (const part of parts) {
        // SSE event chunk may contain "event: <type>\ndata: <json>" — parse both
        let eventType: string | undefined;
        let dataStr = "";
        for (const raw of part.split(/\r?\n/)) {
          const line = raw.trim();
          if (line.startsWith("event:")) {
            eventType = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            dataStr += line.slice(5).trim();
          }
        }
        if (!dataStr) continue;
        try {
          const parsed = JSON.parse(dataStr) as Record<string, unknown>;
          // Merge event type header into payload so discriminated union works
          yield (eventType ? { event: eventType, ...parsed } : parsed) as T;
        } catch {
          // ignore malformed
        }
      }
    }
  } finally {
    try { reader.releaseLock(); } catch { /* noop */ }
  }
}

/**
 * Stream report fill events — V14-A SSE.
 * Falls back to in-browser mock stream if backend unreachable.
 */
export async function* streamReportFill(
  params: ReportFillParams,
  signal?: AbortSignal
): AsyncGenerator<ReportEvent> {
  const qs = new URLSearchParams();
  if (params.preset) qs.set("preset", params.preset);
  if (params.mock) qs.set("mock", "1");
  if (params.business_line) qs.set("business_line", params.business_line);

  const url = `${REPORT_API_BASE}/fill?${qs.toString()}`;

  let res: Response;
  const isMock = !!params.mock;
  try {
    const hasFiles = params.files && params.files.length > 0;
    const hasTemplate = !!params.template_file;
    if (hasFiles || hasTemplate) {
      const fd = new FormData();
      if (hasFiles) {
        for (const f of params.files!) fd.append("files", f);
      }
      if (hasTemplate) {
        fd.append("template_file", params.template_file!);
      }
      res = await fetch(url, { method: "POST", body: fd, signal });
    } else {
      res = await fetch(url, { method: "POST", signal });
    }
  } catch {
    // Mock 模式下后端挂了,回退到浏览器内置 mock,保证演示不中断。
    // 真模式下后端挂是真问题——必须把 error 事件报给 UI,而不是偷偷 mock。
    if (isMock) {
      yield* mockReportStream(params.preset ?? "dingsheng_trade", signal);
    } else {
      yield {
        event: "error",
        message: "后端连接失败,请确认 agent_report 服务已启动(默认端口 8002)。",
      };
    }
    return;
  }

  if (!res.ok) {
    if (isMock) {
      yield* mockReportStream(params.preset ?? "dingsheng_trade", signal);
    } else {
      let detail = "";
      try {
        detail = (await res.text()).slice(0, 300);
      } catch {
        /* noop */
      }
      yield {
        event: "error",
        message: `后端返回 HTTP ${res.status}: ${detail || "未知错误"}`,
      };
    }
    return;
  }

  try {
    for await (const evt of readSSE<ReportEvent>(res, signal)) {
      yield evt;
    }
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    if (isMock) {
      // Upstream blew up mid-stream → fall forward with mock so UX doesn't stall
      yield* mockReportStream(params.preset ?? "dingsheng_trade", signal);
    } else {
      yield {
        event: "error",
        message: `数据流中断: ${(e as Error).message ?? e}`,
      };
    }
  }
}

export interface ReportRefineBody {
  session_id?: string;
  profile_id?: string;
  preset?: string;
  answers: Array<{ id: string; value: string }>;
}

export async function* streamReportRefine(
  body: ReportRefineBody,
  signal?: AbortSignal
): AsyncGenerator<ReportEvent> {
  let res: Response;
  try {
    res = await fetch(`${REPORT_API_BASE}/refine`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  } catch {
    yield* mockRefineStream(body, signal);
    return;
  }
  if (!res.ok) {
    yield* mockRefineStream(body, signal);
    return;
  }
  try {
    for await (const evt of readSSE<ReportEvent>(res, signal)) yield evt;
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    yield* mockRefineStream(body, signal);
  }
}

// ---------------------------------------------------------------------------
// In-browser mock stream — used when V14-A backend is not up yet.
// Keeps the UX demoable; real backend swaps in transparently once live.
// ---------------------------------------------------------------------------

const delay = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    const t = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => {
      clearTimeout(t);
      reject(new DOMException("Aborted", "AbortError"));
    });
  });

async function* mockReportStream(
  preset: string,
  signal?: AbortSignal
): AsyncGenerator<ReportEvent> {
  const { MOCK_PROFILES, MOCK_SECTIONS, MOCK_QUESTIONS } = await import(
    "./report-mock"
  );
  const profile = MOCK_PROFILES[preset] ?? MOCK_PROFILES.dingsheng_trade;
  const sections = MOCK_SECTIONS[preset] ?? MOCK_SECTIONS.dingsheng_trade;

  yield { event: "stage", stage: "ingest", message: "读取材料包…" };
  await delay(600, signal);
  yield { event: "profile", profile };

  yield { event: "stage", stage: "extract", message: "抽取财务与工商关键指标…" };
  await delay(700, signal);

  yield { event: "stage", stage: "infer", message: "补全缺失字段 / 证据回链…" };
  await delay(600, signal);

  yield { event: "stage", stage: "write", message: "按模板节段撰写…" };
  for (const sec of sections) {
    await delay(500, signal);
    yield { event: "section", section: sec };
  }

  yield { event: "stage", stage: "audit", message: "自证复核…" };
  await delay(500, signal);

  const donePayload: ReportDonePayload = {
    profile,
    sections,
    pending_questions: MOCK_QUESTIONS,
    stats: { total_fields: 492, auto_filled: 460, unfilled: 32 },
    downstream_handoff: {
      credit: `/credit?preset=${preset}`,
      alert: `/alert?preset=${preset}`,
      compliance: `/compliance?preset=${preset}`,
    },
    docx_url: `#mock-${preset}.docx`,
  };
  yield { event: "done", payload: donePayload };
}

async function* mockRefineStream(
  body: ReportRefineBody,
  signal?: AbortSignal
): AsyncGenerator<ReportEvent> {
  const preset = body.preset ?? "dingsheng_trade";
  const { MOCK_PROFILES, MOCK_SECTIONS } = await import("./report-mock");
  const profile = MOCK_PROFILES[preset] ?? MOCK_PROFILES.dingsheng_trade;
  const baseSections = MOCK_SECTIONS[preset] ?? MOCK_SECTIONS.dingsheng_trade;

  yield { event: "stage", stage: "infer", message: "合并用户补充信息…" };
  await delay(500, signal);
  yield { event: "stage", stage: "write", message: "重写受影响段落…" };

  // Append an "已根据补充" marker to the last section to visualize refinement
  const appended: typeof baseSections = baseSections.map((s, i) =>
    i === baseSections.length - 1
      ? {
          ...s,
          content:
            s.content +
            `\n\n【已根据用户补充更新】共 ${body.answers.length} 项补充信息已纳入。`,
        }
      : s
  );
  for (const sec of appended) {
    await delay(250, signal);
    yield { event: "section", section: sec };
  }
  yield { event: "stage", stage: "audit", message: "复核完成" };
  await delay(300, signal);
  yield {
    event: "done",
    payload: {
      profile,
      sections: appended,
      pending_questions: [],
      stats: { total_fields: 492, auto_filled: 476, unfilled: 16 },
      downstream_handoff: {
        credit: `/credit?preset=${preset}`,
        alert: `/alert?preset=${preset}`,
        compliance: `/compliance?preset=${preset}`,
      },
      docx_url: `#mock-${preset}-refined.docx`,
    },
  };
}

// ---------------------------------------------------------------------------
// Agent1 — 全渠道获客 (Channel Look-alike) streaming
// ---------------------------------------------------------------------------

import type { ChannelSearchEvent } from "./channel-types";

export interface ChannelHandoffResponse {
  session_id: string;
  profile_ids: string[];
  paths: string[];
  count: number;
  schema_version: string;
}

/** 调 POST /api/channel/handoff：候选企业 → Agent3 授信队列。 */
export async function handoffToCredit(body: {
  candidates: unknown[];
  session_id?: string;
  business_line?: string;
}): Promise<ChannelHandoffResponse> {
  const res = await fetch(`${API_BASE}/api/channel/handoff`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let msg = `handoff ${res.status}`;
    try {
      const err = await res.json();
      msg = err?.detail?.error?.message ?? msg;
    } catch {
      /* noop */
    }
    throw new Error(msg);
  }
  return (await res.json()) as ChannelHandoffResponse;
}

/** 调 POST /api/channel/export_xlsx：触发浏览器下载 xlsx。 */
export async function exportChannelXlsx(body: {
  candidates: unknown[];
  session_id?: string;
  business_line?: string;
}): Promise<{ rows: number; filename: string }> {
  const res = await fetch(`${API_BASE}/api/channel/export_xlsx`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let msg = `export ${res.status}`;
    try {
      const err = await res.json();
      msg = err?.detail?.error?.message ?? msg;
    } catch {
      /* noop */
    }
    throw new Error(msg);
  }
  const blob = await res.blob();
  const cd = res.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^"]+)"?/.exec(cd);
  const filename = match?.[1] ?? `agent1_candidates_${Date.now()}.xlsx`;
  const rows = parseInt(res.headers.get("X-Agent1-Export-Rows") ?? "0", 10);

  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
  return { rows, filename };
}

export async function* streamChannelSearch(
  req: { query: string; provider?: string; api_key?: string; top_n?: number },
  signal?: AbortSignal
): AsyncGenerator<ChannelSearchEvent> {
  const res = await fetch(`${API_BASE}/api/channel/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`channel ${res.status}`);
  }
  // 内联 SSE reader（readSSE 在本模块未导出；与 streamDecision 保持一致风格）
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      if (signal?.aborted) return;
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";
      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data:")) continue;
        const payload = line.slice(5).trim();
        if (!payload) continue;
        try {
          yield JSON.parse(payload) as ChannelSearchEvent;
        } catch {
          // ignore malformed
        }
      }
    }
  } finally {
    try {
      reader.releaseLock();
    } catch {
      /* noop */
    }
  }
}
