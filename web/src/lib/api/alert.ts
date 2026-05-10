/**
 * Alert API client (Stage Fix W-FIX-A3 · live-fallback-banner-spec v1.0).
 *
 * Endpoints (按 backend agent_alert/api.py):
 *   POST /api/alert/scan          · SSE · {scenario_key?, uploaded_files?, force_mock?}
 *   POST /api/alert/demo/run      · SSE · ALL IN Phase B.2 · 真后端 + alert-pool 180 户输入
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
const ENDPOINT_DEMO_RUN = "/api/alert/demo/run";
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


/**
 * ALL IN Phase B.2 (PM 2026-05-10 真意 reframe):
 * runAlertDemo · 调 /api/alert/demo/run · backend 真跑 + alert-pool 180 户输入 batch.
 *
 * 与 runAlertScan 共形 SSE envelope · 区别仅是输入来源 (live = 客户经理上传 ·
 * demo = backend 自动加载 data/mock/alert-pool/clients.csv) · backend pipeline 100% 同 ·
 * 真 Tavily 真 LLM disposition 真 persist 真 ledger.
 *
 * 结果不能 mock · 仅输入是 mock · backend emit 的 dataSource 反映真实路径 (live /
 * mock_fallback / mock_forced 取决 Tavily key/build · 与 /api/alert/scan 完全相同).
 */
export async function runAlertDemo(
  req: AlertScanRequest,
  onEvent?: AlertSseHandler,
  signal?: AbortSignal,
): Promise<AlertScanResult> {
  const body = {
    scenario_key: req.scenarioKey ?? "alert-pool",
  };
  let sessionId = "";
  let mode = "";
  /* demo 默认 expect "live" (Tavily 真接 · alert-pool input · backend 真跑) ·
     backend emit 真 data_source · 此处 preferred default. */
  let dataSource: DataSourceKind = "live";
  await streamSse(ENDPOINT_DEMO_RUN, body, (evt) => {
    if (signal?.aborted) return;
    onEvent?.(evt);
    const data = (evt.data ?? {}) as Record<string, unknown>;
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


/** ALL IN Phase B step 4 (2026-05-09): 收紧 signal_timeline 类型 ·
 *  字段级溯源 evidence chain (per scan_engine.build_drill_payload §197 · evidence per source).
 *  source: 数据源标签 (e.g. "external_scan" / "internal_txn" / "cross_match")
 *  snippet: 证据节选 (≤ 120 char)
 *  url: 跳源 URL (Tavily 抓的真实链接 · 空表示内部信号无 URL) */
export type AlertEvidence = {
  source: string;
  snippet: string;
  url: string;
};

export type AlertDrillResponse = {
  client_id: string;
  company_name?: string;
  level?: string;
  score?: number;
  matched_rules?: string[];
  reasons?: string[];
  signal_timeline?: AlertEvidence[];
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
