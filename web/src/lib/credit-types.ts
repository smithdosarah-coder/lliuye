/**
 * Type shapes for Agent3 — mirrors Python dataclasses.
 */

export type Segment = "corporate" | "sme" | "retail";

/** Backend only knows corporate|retail; SME reuses retail pipeline. */
export function toBackendSegment(s: Segment): "corporate" | "retail" {
  return s === "corporate" ? "corporate" : "retail";
}

export interface ScoringPayload {
  financial_score?: number;
  industry_score?: number;
  operational_score?: number;
  guarantee_score?: number;
  composite_score?: number;
  risk_grade?: string;
  sub_scores?: Record<string, unknown>;
  industry_peer_gap?: Record<string, number>;
  amount_methods?: Record<string, number>;
  // retail backend fields
  fico_score?: number;
  grade?: string;
  category_scores?: {
    repayment_capacity?: number;
    repayment_willingness?: number;
    stability?: number;
    collateral?: number;
  };
  approved_limit_cap?: number;
  rate_tier?: string;
}

export interface RedLineHit {
  rule_id: string;
  rule_name: string;
  category?: string;
  threshold?: number | string;
  actual_value?: number | string;
  severity?: "low" | "medium" | "high" | string;
  is_hard?: boolean;
  can_waive?: boolean;
  waiver_conditions?: string[];
  description?: string;
}

export interface DecisionAdvice {
  advice_id: string;
  segment: string;
  subject_name: string;
  decision_time: string;
  decision: "批准" | "有条件批准" | "拒绝" | string;
  amount_provided?: boolean;
  approved_amount: number | null;
  approved_term_months: number;
  interest_rate: number;
  rate_benchmark: string;
  composite_score: number;
  risk_grade: string;
  conditions: string[];
  red_line_hits: RedLineHit[];
  red_line_explanations: Array<{ rule_id: string; explanation: string }>;
  decision_reason: string;
  similar_cases_summary?: string;
  amount_methods?: Record<string, number>;
  approval_section_text?: string;
}

export interface CaseMatch {
  case_id?: string;
  subject_name?: string;
  similarity?: number;
  decision?: string;
  outcome?: string;
  year?: number | string;
  [k: string]: unknown;
}

export interface Profile {
  profile_id?: string;
  company_name?: string;
  subject_name?: string;
  industry?: string;
  region?: string;
  main_business?: string;
  employee_count?: number;
  registered_capital?: string;
  establishment_date?: string;
  request?: { amount?: number; purpose?: string; term_months?: number };
  financial_anchors?: Record<string, number | string>;
  [k: string]: unknown;
}

export interface DecisionState {
  profile?: Profile;
  scoring?: ScoringPayload;
  cases?: CaseMatch[];
  advice?: DecisionAdvice;
  stageHistory: string[];
  activeStage?: string;
  doneStages: Set<string>;
  error?: string;
  phase: "idle" | "running" | "done" | "error";
}

export const INITIAL_STATE: DecisionState = {
  stageHistory: [],
  doneStages: new Set(),
  phase: "idle",
};

/** Map raw backend stage names → UI stage keys (so the rail can highlight). */
export const CORP_STAGES = [
  { key: "feature_extracting", label: "特征抽取" },
  { key: "scoring", label: "四维评分" },
  { key: "rule_checking", label: "红线检查" },
  { key: "case_retrieving", label: "案例搜索" },
  { key: "advising", label: "决策整合" },
];

export const SME_STAGES = [
  { key: "feature_extracting", label: "特征抽取" },
  { key: "scoring", label: "小微评分" },
  { key: "rule_checking", label: "红线检查" },
  { key: "case_retrieving", label: "案例搜索" },
  { key: "advising", label: "决策整合" },
];

export const RETAIL_STAGES = [
  { key: "feature_extracting", label: "特征抽取" },
  { key: "scoring", label: "评分卡计算" },
  { key: "rule_checking", label: "红线检查" },
  { key: "case_retrieving", label: "案例搜索" },
  { key: "advising", label: "决策整合" },
];

export function stageOf(raw: string): string | undefined {
  if (raw.endsWith("_done")) return raw.slice(0, -5);
  if (raw === "all_done") return undefined;
  return raw;
}

// ---------------------------------------------------------------------------
// Agent6 — 信贷报告助手 types (V14-A)
// ---------------------------------------------------------------------------

/** 业务线:银行第一步必选分流 */
export type BusinessLine = "inclusive" | "corporate" | "reserved";

/** EnterpriseProfile — 对齐 agent_credit 的 corporate_profiles schema,
 *  作为跨 Agent 握手载荷(sessionStorage 传递)。 */
export interface EnterpriseProfile {
  profile_id?: string;
  company_name?: string;
  unified_credit_code?: string;
  industry?: string;
  establishment_date?: string;
  registered_capital?: string;
  employee_count?: number;
  region?: string;
  main_business?: string;
  controller_name?: string;
  controller_share_pct?: string;
  financial_anchors?: Record<string, number | string>;
  guarantee_info?: Record<string, unknown>;
  related_party_info?: Record<string, unknown>;
  existing_credit?: Record<string, unknown>;
  tax_rating?: string;
  request?: { amount?: number; purpose?: string; term_months?: number };
  chapters?: Record<string, string>;
  business_line?: BusinessLine;
  [k: string]: unknown;
}

export type ReportStage = "ingest" | "extract" | "infer" | "write" | "audit";

export const REPORT_STAGES: Array<{ key: ReportStage; label: string }> = [
  { key: "ingest", label: "材料读取" },
  { key: "extract", label: "关键指标抽取" },
  { key: "infer", label: "补全与推理" },
  { key: "write", label: "段落生成" },
  { key: "audit", label: "自证复核" },
];

export interface ReportSection {
  id: string;
  title: string;
  content: string;
}

export interface Question {
  id: string;
  section_id?: string;
  question: string;
  hint?: string;
  input_type?: "text" | "textarea" | "number" | "select";
  options?: string[];
}

export interface DownstreamHandoff {
  credit?: string;      // /credit?preset=xxx
  alert?: string;       // /alert?preset=xxx
  compliance?: string;  // /compliance?preset=xxx
  [k: string]: string | undefined;
}

export interface ReportDonePayload {
  profile: EnterpriseProfile;
  sections: ReportSection[];
  pending_questions?: Question[];
  downstream_handoff?: DownstreamHandoff;
  stats?: {
    total_fields?: number;
    auto_filled?: number;
    unfilled?: number;
  };
  docx_url?: string;
}

/** Discriminated union for /api/report SSE events. */
export type ReportEvent =
  | { event: "stage"; stage: ReportStage; message?: string; section?: ReportSection }
  | { event: "section"; section: ReportSection }
  | { event: "profile"; profile: EnterpriseProfile }
  | { event: "done"; payload: ReportDonePayload; session_id?: string }
  | { event: "error"; message: string; traceback?: string };

export interface ReportState {
  profile?: EnterpriseProfile;
  sessionId?: string;
  sections: ReportSection[];
  activeStage?: ReportStage;
  doneStages: Set<ReportStage>;
  pendingQuestions: Question[];
  handoff?: DownstreamHandoff;
  stats?: ReportDonePayload["stats"];
  docxUrl?: string;
  error?: string;
  phase: "idle" | "running" | "done" | "error" | "refining";
}

export const INITIAL_REPORT_STATE: ReportState = {
  sections: [],
  doneStages: new Set(),
  pendingQuestions: [],
  phase: "idle",
};
