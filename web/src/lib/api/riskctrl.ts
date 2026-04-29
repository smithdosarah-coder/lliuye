/**
 * Riskctrl/Forge API client (Stage Fix W-FIX-A3 · live-fallback-banner-spec v1.0).
 *
 * Endpoints (按 backend agent_riskctrl/api.py):
 *   POST /api/riskctrl/dsl_gen     · SSE · {rule_text, provider?, api_key?}
 *   POST /api/riskctrl/backtest    · SSE · {instruction, uploaded_files, provider?, api_key?}
 *   POST /api/riskctrl/export_docx · stub (待 Stage D 后端) · 404 容忍
 *
 * 422 root cause: backend require instruction + uploaded_files 都必填 (Pydantic
 * 默认 list[str] 没 default factory · 缺则 422).
 *
 * 不 silent swap mock · 失败抛 LiveFailError → UI 显 banner + retry.
 */
"use client";

import { LiveFailError, streamSse } from "./_live";

export { LiveFailError };

const ENDPOINT_DSL_GEN = "/api/riskctrl/dsl_gen";
const ENDPOINT_BACKTEST = "/api/riskctrl/backtest";
const ENDPOINT_EXPORT_DOCX = "/api/riskctrl/export_docx";


export type DslGenRequest = {
  ruleText: string;
  provider?: string;
};


export type BacktestRequest = {
  instruction: string;
  uploadedFiles: string[];
  provider?: string;
};


export type RiskctrlSseHandler = (event: {
  type: string;
  data: Record<string, unknown>;
}) => void;


/** Run dsl_gen SSE · 找 ruleset_id event · 失败抛 LiveFailError. */
export async function runDslGen(
  req: DslGenRequest,
  onEvent?: RiskctrlSseHandler,
): Promise<{ rulesetId: string }> {
  const body = {
    rule_text: req.ruleText,
    provider: req.provider ?? "deepseek",
  };
  let captured = "";
  await streamSse(ENDPOINT_DSL_GEN, body, (evt) => {
    onEvent?.(evt);
    const payload = (evt.data?.payload as Record<string, unknown> | undefined) ?? {};
    const sid = payload.ruleset_id ?? payload.rule_id ?? payload.session_id;
    if (sid) captured = String(sid);
  });
  return { rulesetId: captured };
}


/** Run backtest SSE · drain 流 · 失败抛 LiveFailError (含 422 detail). */
export async function runBacktest(
  req: BacktestRequest,
  onEvent?: RiskctrlSseHandler,
): Promise<void> {
  const body = {
    instruction: req.instruction,
    uploaded_files: req.uploadedFiles,
    provider: req.provider ?? "deepseek",
  };
  await streamSse(ENDPOINT_BACKTEST, body, (evt) => {
    onEvent?.(evt);
  });
}


/** Export docx · 404 时返 not_implemented 状态 · 其他错误抛 LiveFailError. */
export async function exportDocx(rulesetId: string): Promise<Blob> {
  let resp: Response;
  try {
    resp = await fetch(ENDPOINT_EXPORT_DOCX, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ruleset_id: rulesetId }),
    });
  } catch (e) {
    throw new LiveFailError(
      `network error: ${e instanceof Error ? e.message : String(e)}`,
      0,
      ENDPOINT_EXPORT_DOCX,
      "",
    );
  }
  if (resp.status === 404) {
    throw new LiveFailError(
      "endpoint not implemented (Stage D backend pending)",
      404,
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
