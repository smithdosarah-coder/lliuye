/**
 * Credit · backend done envelope → UI CreditSession shape mapper
 *
 * Phase A worker-A4-credit · 2026-04-29 · per workspace-state-protocol §4 +
 * agent_credit/api.py:_build_done_envelope (cat 4 fix · 2026-04-29).
 *
 * Backend done envelope shape (from agent_credit/api.py · _build_done_envelope):
 *   {
 *     event: "done",
 *     stage_tab: "corporate" | "small_business" | "retail",
 *     source: "mock" | "preset" | "report_json" | "unknown",
 *     preset_name: string | null,
 *     decision_id: string | null,
 *     profile: { profile_id, company_name, ... },
 *     scoring: { composite_score, score_max, risk_grade, sub_scores },
 *     rule_hits: Array<{ rule_id, rule_name, is_hard, can_waive, severity, actual_value, threshold }>,
 *     case_matches: Array<{ case_id, company_name, similarity, decision, approved_amount }>,
 *     advice: { decision, approved_amount, approved_term_months, interest_rate, rate_benchmark, risk_grade, composite_score, conditions, decision_reason, stage_tab }
 *   }
 *
 * 映射策略: 仅 hydrate 高价值字段 (radar / overallScore / redLines / cases / limit / decision / profile.tagline)
 * 其余字段 (conversation / materials / dataSources / evidences / pipeline / generateSteps / recentSessions /
 * qcCounts / objective / stage / updated / query) 走 fallback (mock session) · backend 不透传。
 *
 * 这是 4-gate state model 的 liveData 注入器: setLiveData(normalizeCreditDone(payload, sessionData))。
 */

import type {
  CaseRecall,
  CreditMode,
  CreditRadarDim,
  CreditSession,
  LimitSuggestion,
  RedLine,
} from "@/lib/mock/agent-credit-session";

// ----------------------------------------------------------------------------
// Backend envelope types (mirrored from agent_credit/api.py)
// ----------------------------------------------------------------------------

type BackendStageTab = "corporate" | "small_business" | "retail";

export type BackendCreditDoneEnvelope = {
  event: "done";
  stage_tab: BackendStageTab;
  source: "mock" | "preset" | "report_json" | "unknown";
  preset_name?: string | null;
  decision_id?: string | null;
  profile?: Record<string, unknown> | null;
  scoring?: {
    composite_score?: number | null;
    score_max?: number | null;
    risk_grade?: string | null;
    sub_scores?: Record<string, number> | null;
  } | null;
  rule_hits?: Array<{
    rule_id?: string;
    rule_name?: string;
    is_hard?: boolean;
    can_waive?: boolean;
    severity?: string;
    actual_value?: unknown;
    threshold?: unknown;
    waiver_conditions?: string[];
  }> | null;
  case_matches?: Array<{
    case_id?: string;
    company_name?: string;
    similarity?: number;
    decision?: string;
    approved_amount?: number;
    approved_term?: number | null;
    interest_rate?: number | null;
    decision_reason?: string;
  }> | null;
  advice?: {
    decision?: string;
    approved_amount?: number;
    approved_term_months?: number;
    interest_rate?: number;
    rate_benchmark?: string;
    risk_grade?: string;
    composite_score?: number;
    conditions?: string[];
    decision_reason?: string;
    stage_tab?: string;
  } | null;
};

// ----------------------------------------------------------------------------
// Mapping helpers
// ----------------------------------------------------------------------------

const STAGE_TAB_TO_MODE: Record<BackendStageTab, CreditMode> = {
  corporate: "corp",
  small_business: "small",
  retail: "retail",
};

const RADAR_AXIS_LABEL: Record<string, { key: CreditRadarDim["key"]; label: string }> = {
  // corporate / small_business 4 维 (per agent_credit/api.py _STAGE_DIMENSIONS)
  financial: { key: "fin", label: "经营财务" },
  industry: { key: "comp", label: "行业前景" },
  operational: { key: "ops", label: "经营管理" },
  guarantee: { key: "guar", label: "担保条件" },
  // retail 4 维 (FICO 式)
  ability: { key: "fin", label: "偿债能力" },
  willingness: { key: "comp", label: "还款意愿" },
  stability: { key: "ops", label: "工作稳定" },
  collateral: { key: "guar", label: "抵押 / 担保" },
};

function severityToStatus(severity?: string): RedLine["status"] {
  switch ((severity ?? "").toLowerCase()) {
    case "high":
      return "fail";
    case "medium":
      return "warn";
    case "low":
    default:
      return "pass";
  }
}

function decisionToCaseEnum(d?: string): CaseRecall["decision"] {
  if (!d) return "approved";
  if (d.includes("拒")) return "rejected";
  if (d.includes("条件") || d.includes("打折") || d.includes("有条件")) return "approved-cut";
  return "approved";
}

function decisionToSessionEnum(d?: string): CreditSession["decision"] {
  if (!d) return "pending";
  if (d.includes("拒")) return "rejected";
  if (d.includes("条件") || d.includes("打折") || d.includes("有条件")) return "approved-cut";
  if (d.includes("批")) return "approved";
  return "pending";
}

// ----------------------------------------------------------------------------
// Per-section normalizers
// ----------------------------------------------------------------------------

function normalizeRadar(
  scoring: BackendCreditDoneEnvelope["scoring"],
  fallback: CreditRadarDim[],
): CreditRadarDim[] {
  const sub = scoring?.sub_scores;
  if (!sub) return fallback;
  // backend axis_id (financial/industry/operational/guarantee 或 ability/willingness/stability/collateral)
  // → UI CreditRadarDim shape · 保留 fallback 的 weight/note/tags
  return Object.entries(sub).map(([axisId, score], i) => {
    const meta = RADAR_AXIS_LABEL[axisId];
    const fb = fallback[i];
    return {
      key: meta?.key ?? fb?.key ?? "fin",
      label: meta?.label ?? fb?.label ?? axisId,
      score: Number(score),
      weight: fb?.weight ?? 0.25,
      note: fb?.note ?? `${meta?.label ?? axisId} 得分 ${score}`,
      tags: fb?.tags ?? [],
    };
  });
}

function normalizeRedLines(
  hits: BackendCreditDoneEnvelope["rule_hits"],
  fallback: RedLine[],
): RedLine[] {
  if (!hits || hits.length === 0) return fallback;
  return hits.map((h, i) => ({
    id: h.rule_id ?? `rl-live-${i}`,
    rule: h.rule_name ?? "未命名规则",
    detail: `阈值 ${String(h.threshold ?? "—")} · 实测 ${String(h.actual_value ?? "—")}${
      h.is_hard ? " · 硬红线" : (h.can_waive ? " · 可豁免" : " · 软红线")
    }${h.waiver_conditions?.length ? ` · 豁免条件: ${h.waiver_conditions.join(" / ")}` : ""}`,
    status: severityToStatus(h.severity),
    citation: `backend rule_done · ${h.rule_id ?? ""}`,
  }));
}

function normalizeCases(
  matches: BackendCreditDoneEnvelope["case_matches"],
  fallback: CaseRecall[],
): CaseRecall[] {
  if (!matches || matches.length === 0) return fallback;
  return matches.map((m, i) => ({
    id: m.case_id ?? `case-live-${i}`,
    name: m.company_name ?? "(unknown)",
    similarity: m.similarity ?? 0,
    amount: m.approved_amount != null ? `${m.approved_amount} 万` : "—",
    decision: decisionToCaseEnum(m.decision),
    note:
      m.decision_reason ??
      `相似度 ${Math.round((m.similarity ?? 0) * 100)}% · ${m.decision ?? ""} ${m.approved_amount ?? 0} 万`,
    tags: [],
  }));
}

function normalizeLimit(
  advice: BackendCreditDoneEnvelope["advice"],
  fallback: LimitSuggestion,
): LimitSuggestion {
  if (!advice) return fallback;
  const suggested = advice.approved_amount ?? fallback.suggested;
  const tenor = advice.approved_term_months ?? fallback.tenorMonths;
  // interest_rate 0.065 → bps 与 LPR 基准的差值需后端 rate_benchmark 解 · 此处简化
  const rateBps = advice.interest_rate != null ? Math.round(advice.interest_rate * 10000) - 320 : fallback.rateBps;
  return {
    applied: fallback.applied,
    suggested,
    floor: Math.min(fallback.floor, suggested),
    ceiling: Math.max(fallback.ceiling, suggested),
    tenorMonths: tenor,
    tenorRange: fallback.tenorRange,
    rateBps,
    rateRange: fallback.rateRange,
    rationale: advice.decision_reason ? [advice.decision_reason] : (advice.conditions ?? fallback.rationale),
  };
}

// ----------------------------------------------------------------------------
// Entry point
// ----------------------------------------------------------------------------

/**
 * 把 backend `/api/credit/decision` 或 `/api/credit/demo/run` SSE done event payload
 * normalize 成 UI CreditSession shape · 注入 setLiveData(...).
 *
 * fallback 是 4-gate state model 当前 mock sessionData (用作未透传字段的 default 值)。
 */
export function normalizeCreditDone(
  envelope: Record<string, unknown>,
  fallback: CreditSession,
): CreditSession {
  const env = envelope as BackendCreditDoneEnvelope;
  const stageTab = env.stage_tab ?? "corporate";
  const mode = STAGE_TAB_TO_MODE[stageTab] ?? fallback.mode;

  const profileBackend = env.profile ?? null;
  const advice = env.advice ?? null;

  // 派生 profile chips · 优先用 backend profile 字段 · 否则保留 fallback
  let chips = fallback.profile.chips;
  if (profileBackend && typeof profileBackend === "object") {
    const p = profileBackend as Record<string, unknown>;
    const newChips: string[] = [];
    if (typeof p.company_name === "string") newChips.push(String(p.company_name));
    if (typeof p.industry === "string") newChips.push(String(p.industry));
    if (typeof p.annual_revenue_wan === "number") newChips.push(`年营收 ${p.annual_revenue_wan} 万`);
    if (typeof p.employees === "number") newChips.push(`员工 ${p.employees} 人`);
    if (newChips.length > 0) chips = newChips;
  }
  const tagline = advice?.decision_reason ?? fallback.profile.tagline;

  return {
    ...fallback,
    id: `${fallback.id}__live`,
    mode,
    profile: { chips, tagline },
    radar: normalizeRadar(env.scoring, fallback.radar),
    overallScore: env.scoring?.composite_score ?? fallback.overallScore,
    decision: decisionToSessionEnum(advice?.decision),
    redLines: normalizeRedLines(env.rule_hits, fallback.redLines),
    cases: normalizeCases(env.case_matches, fallback.cases),
    limit: normalizeLimit(advice, fallback.limit),
  };
}
