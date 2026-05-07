/**
 * Compliance API client (Stage Fix W-FIX2-A3 · live-fallback-banner-spec v1.0).
 *
 * Endpoints (按 backend agent_compliance/api.py):
 *   POST /api/compliance/policy_scan   · SSE · {policy_doc, business_docs, policy_meta?, force_mock?}
 *   POST /api/compliance/matrix_check  · sync JSON · {policies, business_lines, use_llm?}
 *   POST /api/compliance/export_docx   · returns docx Blob · {scan_id, title?}
 *
 * Bug #5 root cause: ComplianceWorkspace primary CTA hardcode `force_mock: true` ·
 * UI 仍标 live · 用户无法分辨真假数据 (live-fallback-banner-spec.md §1.5 违反).
 *
 * 此 client 默认 `forceMock=false` · failed → LiveFailError → UI 显 banner + retry.
 */
"use client";

import { LiveFailError, postLive, streamSse } from "./_live";

export { LiveFailError };

const ENDPOINT_POLICY_SCAN = "/api/compliance/policy_scan";
const ENDPOINT_MATRIX_CHECK = "/api/compliance/matrix_check";
const ENDPOINT_EXPORT_DOCX = "/api/compliance/export_docx";
const ENDPOINT_DEMO_RUN = "/api/compliance/demo/run";


export type PolicyScanRequest = {
  policyDoc: string;
  businessDocs: Array<Record<string, unknown> | string>;
  policyMeta?: Record<string, unknown>;
  /** 默认 false · primary CTA 必须 false · mock dropdown tertiary 才允许 true. */
  forceMock?: boolean;
};


export type MatrixCheckRequest = {
  policies: Array<Record<string, unknown> | string>;
  businessLines: Array<Record<string, unknown> | string>;
  useLlm?: boolean;
};


export type ComplianceSseHandler = (event: {
  type: string;
  data: Record<string, unknown>;
}) => void;


/**
 * Phase A worker-A4-compli (2026-04-29) · done envelope shape (per shared/sse_envelope.make_done
 * + AGENT_PANEL_KEYS_RECOMMENDED["compliance"] · 与 channel 同 pattern · panels 展开顶层).
 */
export type ComplianceDoneEnvelope = {
  event: "done";
  data_source: "live" | "mock" | "mock_forced" | "mock_fallback" | "cached" | string;
  session_id?: string;
  mode_label?: string;
  scenario_id?: string;
  metrics?: {
    rule_count?: number;
    event_count?: number;
    cell_count?: number;
    severe?: number;
    normal?: number;
    observation?: number;
    violation_count?: number;
    duration_seconds?: number;
  };
  /** 4 panel keys (AGENT_PANEL_KEYS_RECOMMENDED["compliance"]) · 顶层扁平 */
  violations: Array<Record<string, unknown>>;
  matrix?: unknown[];
  events?: Array<Record<string, unknown>>;
  recommendations?: Array<Record<string, unknown>>;
  /** Extras */
  rules_preview?: Array<Record<string, unknown>>;
  events_preview?: Array<Record<string, unknown>>;
  policy_meta?: Record<string, unknown>;
};


export type PolicyScanResult = {
  scanId: string;
  doneEnvelope: ComplianceDoneEnvelope | null;
};


/** Run policy_scan SSE · 捕获 done envelope + scan_id · 失败抛 LiveFailError.
 *
 * V2 (Phase A worker-A4-compli · 2026-04-29): 后端拼 make_done envelope (panels 4 keys
 * 展开顶层 + metrics + data_source + extras) · 前端 onDone 回 caller 整 envelope.
 * Pre-V2 fallback (legacy backend): payload.type==="scan" stage event 取 scan_id.
 */
export async function runPolicyScan(
  req: PolicyScanRequest,
  onEvent?: ComplianceSseHandler,
  onDone?: (env: ComplianceDoneEnvelope) => void,
  signal?: AbortSignal,
): Promise<PolicyScanResult> {
  const body = {
    policy_doc: req.policyDoc,
    business_docs: req.businessDocs,
    policy_meta: req.policyMeta ?? null,
    force_mock: req.forceMock ?? false,
  };
  let captured = "";
  let doneEnvelope: ComplianceDoneEnvelope | null = null;
  await streamSse(ENDPOINT_POLICY_SCAN, body, (evt) => {
    if (signal?.aborted) return;
    onEvent?.(evt);
    if (evt.type === "done") {
      const env = evt.data as unknown as ComplianceDoneEnvelope;
      doneEnvelope = env;
      if (env.session_id) captured = String(env.session_id);
      onDone?.(env);
      return;
    }
    /* Pre-V2 fallback · 旧 backend payload.type==="scan" stage event 携 scan_id */
    const payload = (evt.data?.payload as Record<string, unknown> | undefined) ?? {};
    if (payload.type === "scan" && payload.scan_id) {
      captured = String(payload.scan_id);
    }
  }, { signal });
  return { scanId: captured, doneEnvelope };
}


/** Run demo/run SSE · 重放预置 scenario · 同 done envelope shape · 失败抛 LiveFailError. */
export async function runComplianceDemo(
  scenarioId: "online_loan" | "aml" | "data_protect",
  onEvent?: ComplianceSseHandler,
  onDone?: (env: ComplianceDoneEnvelope) => void,
  signal?: AbortSignal,
): Promise<PolicyScanResult> {
  let captured = "";
  let doneEnvelope: ComplianceDoneEnvelope | null = null;
  await streamSse(ENDPOINT_DEMO_RUN, { scenario_id: scenarioId }, (evt) => {
    if (signal?.aborted) return;
    onEvent?.(evt);
    if (evt.type === "done") {
      const env = evt.data as unknown as ComplianceDoneEnvelope;
      doneEnvelope = env;
      if (env.session_id) captured = String(env.session_id);
      onDone?.(env);
    }
  }, { signal });
  return { scanId: captured, doneEnvelope };
}


/** Sync matrix_check · 单次 JSON · 失败抛 LiveFailError. */
export async function runMatrixCheck(
  req: MatrixCheckRequest,
): Promise<Record<string, unknown>> {
  const body = {
    policies: req.policies,
    business_lines: req.businessLines,
    use_llm: req.useLlm ?? false,
  };
  return await postLive<Record<string, unknown>>(ENDPOINT_MATRIX_CHECK, body);
}


/** Export docx · 失败抛 LiveFailError (含 404 端点未实装). */
export async function exportDocx(scanId: string, title?: string): Promise<Blob> {
  let resp: Response;
  try {
    resp = await fetch(ENDPOINT_EXPORT_DOCX, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scan_id: scanId, title: title ?? "" }),
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
      "endpoint not implemented",
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
