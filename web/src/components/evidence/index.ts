export { EvidenceTrail } from "./EvidenceTrail";
export type { EvidenceTrailProps } from "./EvidenceTrail";
export { EvidencePopover } from "./EvidencePopover";
export { EvidenceProvider, useEvidence } from "./EvidenceContext";
export { HighlightCard, ClaimText } from "./HighlightCard";
export type { HighlightCardProps, ClaimTextProps } from "./HighlightCard";
export { parseClaims, hasAnchors } from "./claimParser";
export type { ClaimToken } from "./claimParser";
export type {
  EvidenceItem,
  EvidenceMeta,
  EvidenceTrailResponse,
  AuditPayload,
  AuditFinding,
  UnfilledReason,
} from "./types";
export {
  LOW_CONFIDENCE_THRESHOLD,
  UNFILLED_MARKER_TEXT,
  isLowConfidence,
  isPdfSource,
  buildSourceHref,
} from "./types";
