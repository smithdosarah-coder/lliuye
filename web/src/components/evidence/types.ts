/**
 * Evidence-First Protocol · 前端类型
 *
 * 与后端 `shared/evidence/protocol.py` `AuditedResult.to_dict()` 对齐:
 *   { content, evidence_trail, unfilled_fields, findings, blocked }
 *
 * 前端只消费,不回写后端。backend red line 见 batch-2 onboarding §5。
 */

export const LOW_CONFIDENCE_THRESHOLD = 0.5;

export const UNFILLED_MARKER_TEXT = "未能自动填写";

export type UnfilledReason =
  | "qc_blocked"
  | "no_evidence"
  | "conflict"
  | "unknown";

export interface EvidenceMeta {
  page?: number;
  paragraph_id?: string;
  year?: number | string;
  entity?: string;
  [key: string]: unknown;
}

export interface EvidenceItem {
  source: string;
  snippet: string;
  ref_id: string;
  confidence: number;
  meta?: EvidenceMeta;
}

export interface AuditFinding {
  level: "block" | "warn" | "info";
  code: string;
  message: string;
  related_ref?: string | null;
}

/**
 * AuditReport payload — 后端 SSE done event 负载的一部分。
 * 所有 5 Agent(channel/credit/alert/compliance/riskctrl)的 done 事件都应带这两个字段;
 * Agent6(report)的 ReportDonePayload 目前 shape 未带,workspace 层可用 local mock 过渡。
 */
export interface AuditPayload {
  evidence_trail?: EvidenceItem[];
  unfilled_fields?: string[];
  findings?: AuditFinding[];
  blocked?: boolean;
}

export interface EvidenceTrailResponse extends AuditPayload {
  evidence_trail: EvidenceItem[];
  unfilled_fields: string[];
}

export function isLowConfidence(
  item: EvidenceItem,
  threshold: number = LOW_CONFIDENCE_THRESHOLD
): boolean {
  return item.confidence < threshold;
}

export function isPdfSource(source: string): boolean {
  return /\.pdf(\?|#|$)/i.test(source);
}

export function buildSourceHref(item: EvidenceItem): string | undefined {
  const { source, meta } = item;
  if (!source) return undefined;
  if (isPdfSource(source) && typeof meta?.page === "number") {
    const base = source.split("#")[0];
    return `${base}#page=${meta.page}`;
  }
  if (/^https?:\/\//i.test(source)) return source;
  return undefined;
}
