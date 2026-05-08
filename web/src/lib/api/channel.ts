/**
 * Channel (Agent1 全渠道获客) API client.
 *
 * Endpoints (按 backend agent_channel/api.py):
 *   POST /api/channel/run         · SSE · {query, mock?, top_n?}  · 真搜 (Tavily) OR mock_fallback
 *   POST /api/channel/demo/run    · SSE · {scenario_id} · 纯 mock 演示流 (easy/medium/hard)
 *   POST /api/channel/export_xlsx · 候选企业 xlsx 导出
 *   POST /api/channel/export_docx · 候选企业 docx 导出
 *   POST /api/channel/handoff     · 候选 → Agent6 报告 handoff
 *   GET  /api/channel/scenarios   · 列演示场景
 *
 * Q-041 ratify (2026-04-28 · CLAUDE.md §3.7.2): SSE candidate event payload 必出
 * 4 字段 — industry / geo / scale / similarity · 任何字段缺失或值为 null/"未知"/"[object Object]"
 * 视作 regression · 前端 banner 必显式 fail-fast。
 *
 * 不 silent swap mock · 失败抛 LiveFailError → UI 显 banner + retry。
 *
 * Codex peer-review protocol v2 (Q-043 · CLAUDE.md §3.7.4): provider/api_key 不通过
 * body 暴露 · 一律走 backend env (PIPL fallback chain)。
 */
"use client";

import { type DataSourceKind, normalizeDataSource } from "./_data-source";
import { LiveFailError, streamSse } from "./_live";

export { LiveFailError };
export type { DataSourceKind };

const ENDPOINT_RUN = "/api/channel/run";
const ENDPOINT_DEMO = "/api/channel/demo/run";
const ENDPOINT_EXPORT_XLSX = "/api/channel/export_xlsx";
const ENDPOINT_EXPORT_DOCX = "/api/channel/export_docx";
const ENDPOINT_HANDOFF = "/api/channel/handoff";
const ENDPOINT_SCENARIOS = "/api/channel/scenarios";


// ============================================================================
// Run (live · Tavily search OR mock_fallback)
// ============================================================================

export type ChannelRunRequest = {
  query: string;
  topN?: number;
  // True → 前端显式切 DEMO MODE，后端跳过 Tavily，直接走 mock 池
  mock?: boolean;
};


export type ChannelSseHandler = (event: {
  type: string;
  data: Record<string, unknown>;
}) => void;


/**
 * Q-041 4 字段必出契约 · per CLAUDE.md §3.7.2。
 * candidate 单条来自 backend SSE done event payload.candidates[]。
 */
export type CandidateMetadata = {
  /** 行业分类 · e.g. "制造 · 通用设备" · 不允许 null/"未知"/"[object Object]" */
  industry: string;
  /** 地理位置 · e.g. "上海 · 闵行区" · 同上不允许 fallback 字面 */
  geo: string;
  /** 企业规模 · e.g. "中型 · 200-1000 人" · 同上 */
  scale: string;
  /** look-alike 相似度评分 · 0-100 数值 · 不允许 null */
  similarity: number;
};


export type ChannelCandidate = CandidateMetadata & {
  /** 候选企业唯一 id (e.g. "cand_001") */
  id?: string;
  /** 企业名 · 中文全称 */
  name?: string;
  /** 统一社会信用代码 (USCC · 18 位) */
  uscc?: string;
  /** 注册资本 · 元 (内部数据 · 展示走 formatter) */
  registered_capital?: number;
  /** 成立日期 · ISO 8601 */
  founded_at?: string;
  /** 联系信息 · 法人 / 电话 / 地址 */
  contact?: Record<string, unknown>;
  /** 信号触发列表 · 来源 + 时间 + 摘要 */
  signals?: Array<Record<string, unknown>>;
  /** 推荐产品列表 · 来自 backend pitch 阶段 */
  recommended_products?: Array<Record<string, unknown>>;
  /** 话术脚本 (按角色) */
  pitch_script?: Record<string, unknown>;
  /** PM 2026-05-07 ALL IN step 2.1 · 字段级溯源 · backend realtime_stream:1153 emit camelCase
     evidence drawer 让用户点 hint URL 跳源验证 · per codex R1 第 4 项 + PM 第 3 条硬规 */
  dataSources?: Array<{ label: string; hint: string }>;
  /** 其他 backend 透传字段 (radar / funnel 等内联) */
  [key: string]: unknown;
};


export type ChannelDoneEnvelope = {
  /** session id (live OR demo · 后者形如 "demo_<scenario>_<ts>") */
  session_id?: string;
  /** 5 enum (per shared.sse_envelope.py:81-86 canon · 走 _data-source.ts SSOT) */
  data_source?: DataSourceKind;
  /** Q-041 候选清单 · 每条必含 4 字段 */
  candidates?: ChannelCandidate[];
  /** 信号时间线 (跨候选 · 5 路: 工商/招投标/资本/招聘/舆情) */
  signals?: Array<Record<string, unknown>>;
  /** 雷达图维度 (per candidate) */
  radar?: Array<Record<string, unknown>>;
  /** 漏斗 (Tavily → 解析 → 评分 → 推荐) */
  funnel?: Array<Record<string, unknown>>;
  /** 匹配维度展示 */
  match_dimensions?: Array<Record<string, unknown>>;
  /** 产品推荐表 */
  product_recommendations?: Array<Record<string, unknown>>;
  /** 话术脚本 */
  pitch_scripts?: Array<Record<string, unknown>>;
  /** 对话流 (V3 fix · CHANNEL_PANEL_KEYS 8 keys 之一 · scenario JSON 可选) */
  conversation?: Array<Record<string, unknown>>;
  /** 顶层 metrics (latency / token / cost) */
  metrics?: Record<string, unknown>;
};


export type ChannelRunResult = {
  sessionId: string;
  dataSource: DataSourceKind;
  doneEnvelope: ChannelDoneEnvelope | null;
};


/**
 * Run channel scan SSE · 流式收 stage + done.
 *
 * 失败 (4xx/5xx · TAVILY_KEY_MISSING · network · SSE error) 抛 LiveFailError →
 * caller render banner (live-fallback-banner-spec §1.5)。
 *
 * 不 silent fallback to mock · 必显式让用户知道为什么 fail。
 *
 * Per Q-041 (CLAUDE.md §3.7.2): caller 收到 done envelope 后必检每个 candidate
 * 4 字段 (industry/geo/scale/similarity) · 任何字段缺失或 null/"未知"/"[object Object]"
 * 必触发 banner-spec blocked_by_env · 不 silent fallback。
 */
export async function runChannel(
  req: ChannelRunRequest,
  onEvent?: ChannelSseHandler,
): Promise<ChannelRunResult> {
  const body = {
    query: req.query,
    top_n: req.topN ?? 8,
    mock: req.mock ?? false,
    // provider/api_key 不传 · 一律 backend env (per Q-043 PIPL · CLAUDE.md §3.7.4)
  };
  let sessionId = "";
  /* default "mock" 而非 "" · stream 没 done 时安全降级 trust model · UI 可显式 banner. */
  let dataSource: DataSourceKind = "mock";
  let doneEnvelope: ChannelDoneEnvelope | null = null;

  await streamSse(ENDPOINT_RUN, body, (evt) => {
    onEvent?.(evt);
    const data = (evt.data ?? {}) as Record<string, unknown>;

    if (data.event === "done") {
      doneEnvelope = data as ChannelDoneEnvelope;
      if (data.session_id) sessionId = String(data.session_id);
      if (data.data_source) dataSource = normalizeDataSource(data.data_source);
    }
  });

  return { sessionId, dataSource, doneEnvelope };
}


// ============================================================================
// Demo run (纯 mock SSE · 不依赖 Tavily/LLM · 客户走访稳定路径)
// ============================================================================

export type ChannelDemoScenarioId = "easy" | "medium" | "hard";


export type ChannelDemoRequest = {
  scenarioId: ChannelDemoScenarioId;
};


/** Demo run · 同 runChannel signature · 但走 /api/channel/demo/run · 纯 mock. */
export async function runChannelDemo(
  req: ChannelDemoRequest,
  onEvent?: ChannelSseHandler,
): Promise<ChannelRunResult> {
  const body = { scenario_id: req.scenarioId };
  let sessionId = "";
  let dataSource: DataSourceKind = "mock_forced";
  let doneEnvelope: ChannelDoneEnvelope | null = null;

  await streamSse(ENDPOINT_DEMO, body, (evt) => {
    onEvent?.(evt);
    const data = (evt.data ?? {}) as Record<string, unknown>;
    if (data.event === "done") {
      doneEnvelope = data as ChannelDoneEnvelope;
      if (data.session_id) sessionId = String(data.session_id);
      if (data.data_source) dataSource = normalizeDataSource(data.data_source);
    }
  });

  return { sessionId, dataSource, doneEnvelope };
}


// ============================================================================
// Scenarios list (GET)
// ============================================================================

export type ChannelScenarioMeta = {
  id: ChannelDemoScenarioId;
  label: string;
  difficulty?: string;
  description?: string;
};


export async function listChannelScenarios(): Promise<ChannelScenarioMeta[]> {
  let resp: Response;
  try {
    resp = await fetch(ENDPOINT_SCENARIOS, { method: "GET" });
  } catch (e) {
    throw new LiveFailError(
      `network error: ${e instanceof Error ? e.message : String(e)}`,
      0,
      ENDPOINT_SCENARIOS,
      "",
    );
  }
  if (!resp.ok) {
    const excerpt = (await resp.text().catch(() => "")).slice(0, 200);
    throw new LiveFailError(`HTTP ${resp.status}`, resp.status, ENDPOINT_SCENARIOS, excerpt);
  }
  const data = (await resp.json()) as { scenarios?: ChannelScenarioMeta[] };
  return data.scenarios ?? [];
}


// ============================================================================
// Export (xlsx / docx)
// ============================================================================

export type ChannelExportRequest = {
  candidates: ChannelCandidate[];
  sessionId?: string;
  scenarioId?: string;
};


/** Export xlsx · 返 Blob · caller 走 download flow. */
export async function exportChannelXlsx(req: ChannelExportRequest): Promise<Blob> {
  const body = {
    candidates: req.candidates,
    session_id: req.sessionId ?? "",
    scenario_id: req.scenarioId ?? "",
  };
  let resp: Response;
  try {
    resp = await fetch(ENDPOINT_EXPORT_XLSX, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (e) {
    throw new LiveFailError(
      `network error: ${e instanceof Error ? e.message : String(e)}`,
      0,
      ENDPOINT_EXPORT_XLSX,
      "",
    );
  }
  if (!resp.ok) {
    const excerpt = (await resp.text().catch(() => "")).slice(0, 200);
    throw new LiveFailError(`HTTP ${resp.status}`, resp.status, ENDPOINT_EXPORT_XLSX, excerpt);
  }
  return await resp.blob();
}


/** Export docx · 同上. */
export async function exportChannelDocx(req: ChannelExportRequest): Promise<Blob> {
  const body = {
    candidates: req.candidates,
    session_id: req.sessionId ?? "",
    scenario_id: req.scenarioId ?? "",
  };
  let resp: Response;
  try {
    resp = await fetch(ENDPOINT_EXPORT_DOCX, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (e) {
    throw new LiveFailError(
      `network error: ${e instanceof Error ? e.message : String(e)}`,
      0,
      ENDPOINT_EXPORT_DOCX,
      "",
    );
  }
  if (!resp.ok) {
    const excerpt = (await resp.text().catch(() => "")).slice(0, 200);
    throw new LiveFailError(`HTTP ${resp.status}`, resp.status, ENDPOINT_EXPORT_DOCX, excerpt);
  }
  return await resp.blob();
}


// ============================================================================
// Handoff to Agent6 (报告)
// ============================================================================

export type ChannelHandoffRequest = {
  candidates: ChannelCandidate[];
  sessionId?: string;
  reason?: string;
};


export type ChannelHandoffResponse = {
  handoff_id: string;
  to_agent: string;
  payload: Record<string, unknown>;
  created_at?: string;
};


/** 把候选清单 handoff 给 Agent6 报告 · 后端写 data/handoff/channel_to_report/<id>.json. */
export async function channelHandoff(req: ChannelHandoffRequest): Promise<ChannelHandoffResponse> {
  const body = {
    candidates: req.candidates,
    session_id: req.sessionId ?? "",
    reason: req.reason ?? "客户经理选择 look-alike 候选 · 转 Agent6 出报告",
  };
  let resp: Response;
  try {
    resp = await fetch(ENDPOINT_HANDOFF, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (e) {
    throw new LiveFailError(
      `network error: ${e instanceof Error ? e.message : String(e)}`,
      0,
      ENDPOINT_HANDOFF,
      "",
    );
  }
  if (!resp.ok) {
    const excerpt = (await resp.text().catch(() => "")).slice(0, 200);
    throw new LiveFailError(`HTTP ${resp.status}`, resp.status, ENDPOINT_HANDOFF, excerpt);
  }
  return (await resp.json()) as ChannelHandoffResponse;
}


// ============================================================================
// Q-041 4 字段 verify (主 CLI 推荐 · caller 收到 done envelope 后调)
// ============================================================================

/**
 * Verify candidate 4 字段全合法 (per Q-041 + CLAUDE.md §3.7.2).
 *
 * 任何 candidate 缺字段 OR 值为 null/"未知"/"[object Object]" · 返 false ·
 * caller 触发 banner-spec blocked_by_env · 不 silent fallback。
 */
export function verifyCandidateMetadata(candidate: ChannelCandidate): boolean {
  const fields: (keyof CandidateMetadata)[] = ["industry", "geo", "scale", "similarity"];
  for (const field of fields) {
    const value = candidate[field];
    if (value === null || value === undefined) return false;
    if (typeof value === "string" && (value === "未知" || value === "[object Object]" || value === "")) return false;
    if (field === "similarity" && typeof value !== "number") return false;
  }
  return true;
}


/** Verify 整个 candidates 数组 · 返第一个不合法 candidate id (or null if 全合法). */
export function findInvalidCandidate(candidates: ChannelCandidate[]): string | null {
  for (let i = 0; i < candidates.length; i++) {
    if (!verifyCandidateMetadata(candidates[i])) {
      return candidates[i].id ?? `index_${i}`;
    }
  }
  return null;
}
