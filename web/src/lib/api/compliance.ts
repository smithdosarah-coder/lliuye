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


export type PolicyScanResult = {
  scanId: string;
};


/** Run policy_scan SSE · 找 payload.type==="scan" 事件取 scan_id · 失败抛 LiveFailError. */
export async function runPolicyScan(
  req: PolicyScanRequest,
  onEvent?: ComplianceSseHandler,
): Promise<PolicyScanResult> {
  const body = {
    policy_doc: req.policyDoc,
    business_docs: req.businessDocs,
    policy_meta: req.policyMeta ?? null,
    force_mock: req.forceMock ?? false,
  };
  let captured = "";
  await streamSse(ENDPOINT_POLICY_SCAN, body, (evt) => {
    onEvent?.(evt);
    const payload = (evt.data?.payload as Record<string, unknown> | undefined) ?? {};
    if (payload.type === "scan" && payload.scan_id) {
      captured = String(payload.scan_id);
    }
  });
  return { scanId: captured };
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
