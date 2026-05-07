/**
 * Alert API client (Stage Fix W-FIX-A3 · live-fallback-banner-spec v1.0).
 *
 * Endpoints (按 backend agent_alert/api.py):
 *   POST /api/alert/scan          · SSE · {scenario_key?, uploaded_files?, force_mock?}
 *   GET  /api/alert/hitlist       · 持久化榜单
 *   GET  /api/alert/drill/{cid}   · 单客户 drill
 *
 * 不 silent swap mock · 失败抛 LiveFailError → UI 显 banner + retry.
 */
"use client";

import { type DataSourceKind, normalizeDataSource } from "./_data-source";
import { LiveFailError, postLive, streamSse } from "./_live";

export { LiveFailError };
export type { DataSourceKind };

const ENDPOINT_SCAN = "/api/alert/scan";
const ENDPOINT_HITLIST = "/api/alert/hitlist";


export type AlertScanRequest = {
  scenarioKey?: string;
  uploadedFiles?: string[];
  forceMock?: boolean;
};


export type AlertSseHandler = (event: {
  type: string;
  data: Record<string, unknown>;
}) => void;


export type AlertScanResult = {
  sessionId: string;
  mode: string;
  /** 后端 emit (per agent_alert/api.py:343 + scan_engine done envelope · per shared/sse_envelope canon) */
  dataSource: DataSourceKind;
};


/** Run alert scan SSE · 流式收 hit + done · 找 session_id 落 state.
 *  失败 (4xx/5xx/SSE error) 抛 LiveFailError → caller render banner.
 *
 *  V2 fix · session_id 读两路 (per shared.sse_envelope.make_done · 顶层位置):
 *    - legacy: evt.data.payload.type === "session" → payload.session_id (旧 scan_engine yield)
 *    - canon:  evt.data.event === "done" → evt.data.session_id (make_done 顶层 · cat 4 共形 envelope)
 *  否则 done envelope 顶层的 session_id 会丢 · scanSessionId 永远空字符串. */
export async function runAlertScan(
  req: AlertScanRequest,
  onEvent?: AlertSseHandler,
  signal?: AbortSignal,
): Promise<AlertScanResult> {
  const body = {
    scenario_key: req.scenarioKey ?? "",
    uploaded_files: req.uploadedFiles ?? null,
    force_mock: req.forceMock ?? false,
  };
  let sessionId = "";
  let mode = "";
  /* 默认 "mock" · 后端 force_mock=True OR 没 emit data_source 时安全降级 (banner-spec rule 1+2). */
  let dataSource: DataSourceKind = req.forceMock ? "mock_forced" : "mock";
  await streamSse(ENDPOINT_SCAN, body, (evt) => {
    if (signal?.aborted) return;
    onEvent?.(evt);
    const data = (evt.data ?? {}) as Record<string, unknown>;
    const payload = (data.payload as Record<string, unknown> | undefined) ?? {};

    // legacy path · scan_engine yield {"type": "session", "session_id": ...}
    if (payload.type === "session" && payload.session_id) {
      sessionId = String(payload.session_id);
      if (payload.mode) mode = String(payload.mode);
    }

    // V2 fix · canon path · make_done 顶层 session_id (per shared.sse_envelope)
    if (data.event === "done") {
      if (data.session_id) sessionId = String(data.session_id);
      if (data.mode) mode = String(data.mode);
      if (data.data_source) dataSource = normalizeDataSource(data.data_source);
    }
  }, { signal });
  return { sessionId, mode, dataSource };
}


export type AlertHitListResponse = {
  session_id?: string;
  generated_at?: string;
  mode?: string;
  hit_list?: {
    red_count?: number;
    yellow_count?: number;
    green_count?: number;
    hits?: Array<Record<string, unknown>>;
  };
  dispositions?: Record<string, unknown>;
};


export async function fetchHitlist(sessionId?: string): Promise<AlertHitListResponse> {
  const qs = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
  let resp: Response;
  try {
    resp = await fetch(`${ENDPOINT_HITLIST}${qs}`, { method: "GET" });
  } catch (e) {
    throw new LiveFailError(
      `network error: ${e instanceof Error ? e.message : String(e)}`,
      0,
      ENDPOINT_HITLIST,
      "",
    );
  }
  if (!resp.ok) {
    const excerpt = (await resp.text().catch(() => "")).slice(0, 200);
    throw new LiveFailError(`HTTP ${resp.status}`, resp.status, ENDPOINT_HITLIST, excerpt);
  }
  return (await resp.json()) as AlertHitListResponse;
}


export type AlertDrillResponse = {
  client_id: string;
  company_name?: string;
  level?: string;
  score?: number;
  matched_rules?: string[];
  reasons?: string[];
  signal_timeline?: Array<Record<string, unknown>>;
  disposition?: Record<string, unknown>;
  disposition_source?: string;
};


export async function fetchDrill(
  clientId: string,
  sessionId?: string,
): Promise<AlertDrillResponse> {
  const qs = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
  const path = `/api/alert/drill/${encodeURIComponent(clientId)}${qs}`;
  let resp: Response;
  try {
    resp = await fetch(path, { method: "GET" });
  } catch (e) {
    throw new LiveFailError(
      `network error: ${e instanceof Error ? e.message : String(e)}`,
      0,
      path,
      "",
    );
  }
  if (!resp.ok) {
    const excerpt = (await resp.text().catch(() => "")).slice(0, 200);
    throw new LiveFailError(`HTTP ${resp.status}`, resp.status, path, excerpt);
  }
  return (await resp.json()) as AlertDrillResponse;
}
