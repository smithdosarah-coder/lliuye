/**
 * Riskctrl/Forge API client (Phase A worker-A4 · 2026-04-29 · sse-envelope §1.5).
 *
 * Endpoints (按 backend agent_riskctrl/api.py v4.1 · SSE 化后):
 *   POST /api/riskctrl/dsl_gen     · SSE · {strategy_intent, sample_csv_path?, mock?}
 *     (provider/api_key 不通过 body 暴露 · 一律 backend env · CLAUDE.md §3.6 PIPL fallback)
 *   POST /api/riskctrl/backtest    · SSE · {ruleset, csv_path, label_column?, bad_threshold?}
 *   POST /api/riskctrl/export_docx · binary blob · {ruleset_id}
 *   POST /api/riskctrl/export_xlsx · binary blob · {ruleset_id}
 *   POST /api/riskctrl/export_pdf  · binary blob · {ruleset_id}
 *
 * 不 silent swap mock · 失败抛 LiveFailError → UI 显 banner + retry.
 *
 * Field alignment fix (audit Cat 3 mismatch #2 + #3):
 *   - dsl_gen body 改 strategy_intent (alias rule_text 双兼 · backend Pydantic 接两种)
 *   - backtest body 改 {ruleset, csv_path, label_column?, bad_threshold?} · v3.x 残留
 *     {instruction, uploaded_files} 已弃 (前端不再发 · backend 也不再接)
 *
 * Step 8 后续: runDslGen / runBacktest done event 的 panels 字段写入 workspace
 * liveData state · 当前函数 signature 已稳定 · onEvent callback 拉满 panels.
 */
"use client";

import { LiveFailError, streamSse } from "./_live";

export { LiveFailError };

const ENDPOINT_DSL_GEN = "/api/riskctrl/dsl_gen";
const ENDPOINT_BACKTEST = "/api/riskctrl/backtest";
const ENDPOINT_EXPORT_DOCX = "/api/riskctrl/export_docx";
const ENDPOINT_EXPORT_XLSX = "/api/riskctrl/export_xlsx";
const ENDPOINT_EXPORT_PDF = "/api/riskctrl/export_pdf";


export type DslGenRequest = {
  /** 自然语言策略意图 · 后端 strategy_intent (alias rule_text · 双兼) */
  strategyIntent: string;
  /** (可选) 历史样本 CSV 路径 · 用于 LLM 字段对齐 */
  sampleCsvPath?: string;
  /** true → backend 跳 LLM 走预设 mock RuleSet (无 key 环境演示) */
  mock?: boolean;
};


/** Backtest body · 与 backend BacktestRequest 1:1 (csv_path 由 sample_csv_path 流转 · ruleset 由 dsl_gen done payload 来) */
export type BacktestRequest = {
  /** RuleSet model_dump 结构 · 由 dsl_gen done event panel 透传 */
  ruleset: Record<string, unknown>;
  /** 历史样本 CSV 路径 · 相对 PROJECT_ROOT 或绝对 */
  csvPath: string;
  /** (可选) 坏账标签列名 · 默认自动探测 days_past_due / label_default / label */
  labelColumn?: string;
  /** (可选) days_past_due > 该值视作坏账 · 默认 30 */
  badThreshold?: number;
};


export type RiskctrlSseEvent = {
  type: string;
  data: Record<string, unknown>;
};

export type RiskctrlSseHandler = (event: RiskctrlSseEvent) => void;


/** dsl_gen done event 关键字段 (panels 已展开到顶层 · per shared/sse_envelope.make_done) */
export type DslGenDonePayload = {
  ruleset: Record<string, unknown>;
  ruleset_id: string;
  csv_columns?: string[];
  source: "llm" | "mock";
  data_source: "live" | "mock_forced" | "mock" | "mock_fallback" | "cached";
  session_id?: string;
};


/** Run dsl_gen SSE · 找 done event · 返结构化 panels payload · 失败抛 LiveFailError. */
export async function runDslGen(
  req: DslGenRequest,
  onEvent?: RiskctrlSseHandler,
  signal?: AbortSignal,
): Promise<DslGenDonePayload | null> {
  const body = {
    strategy_intent: req.strategyIntent,
    sample_csv_path: req.sampleCsvPath,
    mock: req.mock ?? false,
  };
  let donePayload: DslGenDonePayload | null = null;
  await streamSse(ENDPOINT_DSL_GEN, body, (evt) => {
    if (signal?.aborted) return;
    onEvent?.(evt);
    if (evt.type === "done") {
      donePayload = evt.data as unknown as DslGenDonePayload;
    }
  }, { signal });
  return donePayload;
}


/** backtest done event · panels: ruleset/ks/samples/rule_stats · metrics 顶层 KPI */
export type BacktestDonePayload = {
  ruleset: Record<string, unknown>;
  ks: {
    ksPeak: number;
    auc: number;
    passRate: number;
    badRate: number;
    points: Array<{ bin: number; tpr: number; fpr: number; ks: number }>;
  };
  samples: Array<{
    key: "pass" | "review" | "block";
    label: string;
    count: number;
    pct: number;
    bad_rate: number;
  }>;
  rule_stats: Array<{
    rule_id: string | null;
    hit: number;
    fp: number;
    tn: number;
  }>;
  metrics: {
    total_records: number;
    approved: number;
    rejected: number;
    manual_review: number;
    approval_rate: number;
    bad_rate: number | null;
    ks_peak: number | null;
    label_column_used: string | null;
  };
  data_source: "live" | "mock_forced" | "mock" | "mock_fallback" | "cached";
  session_id?: string;
};


/** Run backtest SSE · 找 done event · 返完整 backtest panels · 失败抛 LiveFailError. */
export async function runBacktest(
  req: BacktestRequest,
  onEvent?: RiskctrlSseHandler,
  signal?: AbortSignal,
): Promise<BacktestDonePayload | null> {
  const body = {
    ruleset: req.ruleset,
    csv_path: req.csvPath,
    label_column: req.labelColumn,
    bad_threshold: req.badThreshold ?? 30,
  };
  let donePayload: BacktestDonePayload | null = null;
  await streamSse(ENDPOINT_BACKTEST, body, (evt) => {
    if (signal?.aborted) return;
    onEvent?.(evt);
    if (evt.type === "done") {
      donePayload = evt.data as unknown as BacktestDonePayload;
    }
  }, { signal });
  return donePayload;
}


/* ──────────────────────────────────────────────────────
   Export trio · docx / xlsx / pdf
   后端 Step 7 实装 (agent_riskctrl/exports.py) · 不再 silent 404 fallback
   ────────────────────────────────────────────────────── */

async function _exportBinary(endpoint: string, rulesetId: string): Promise<Blob> {
  let resp: Response;
  try {
    resp = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ruleset_id: rulesetId }),
    });
  } catch (e) {
    throw new LiveFailError(
      `network error: ${e instanceof Error ? e.message : String(e)}`,
      0,
      endpoint,
      "",
    );
  }
  if (!resp.ok) {
    const excerpt = (await resp.text().catch(() => "")).slice(0, 200);
    throw new LiveFailError(`HTTP ${resp.status}`, resp.status, endpoint, excerpt);
  }
  return await resp.blob();
}


/** Export docx · 后端 Step 7 mount · 不 silent 404 (失败显式 banner) */
export async function exportDocx(rulesetId: string): Promise<Blob> {
  return _exportBinary(ENDPOINT_EXPORT_DOCX, rulesetId);
}

/** Export xlsx · 后端 Step 7 mount */
export async function exportXlsx(rulesetId: string): Promise<Blob> {
  return _exportBinary(ENDPOINT_EXPORT_XLSX, rulesetId);
}

/** Export pdf · 后端 Step 7 mount */
export async function exportPdf(rulesetId: string): Promise<Blob> {
  return _exportBinary(ENDPOINT_EXPORT_PDF, rulesetId);
}
