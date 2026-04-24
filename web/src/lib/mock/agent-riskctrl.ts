/**
 * Agent Riskctrl (风控 · A02) — DSL rule + backtest mock fixtures.
 * Feeds the /archive/riskctrl workspace (DSL editor stub + KS/approval backtest cards).
 */

export type RuleDraft = {
  id: string;
  name: string;
  status: "draft" | "backtesting" | "staged" | "live";
  owner: string;
  updated: string;
  dsl: string;
};

export type BacktestMetric = {
  label: string;
  value: string;
  hint: string;
  delta: string;
  positive: boolean;
};

export type IndicatorCoverage = {
  id: string;
  indicator: string;
  coverage: number; // 0..1
  trigger: number; // 命中数
  sample: number; // 样本量
};

export type RuleAuditEntry = {
  id: string;
  ts: string;
  actor: string;
  rule: string;
  verb: "create" | "backtest" | "stage" | "publish" | "rollback";
  note: string;
};

export const RISKCTRL_STATS = {
  weeklyProcessed: "9 策略",
  successRate: "KS 0.41 均值",
  avgDuration: "回测 42 秒",
} as const;

export const RISKCTRL_RULES: RuleDraft[] = [
  {
    id: "rule-2026-041",
    name: "R-2026-041 · 小微商贸高风险三项合成",
    status: "backtesting",
    owner: "王哲",
    updated: "02 分钟前",
    dsl: `# R-2026-041
rule "商贸高风险三项" when
  industry.code in ["5141", "5142"] and
  feature.monthly_flow_mom < -0.25 and
  feature.overdue_count_24m >= 1 and
  collateral.ltv > 0.72
then
  set risk_tag = "high";
  set limit_factor = 0.6;
end`,
  },
  {
    id: "rule-2026-040",
    name: "R-2026-040 · 制造业设备抵押放宽",
    status: "staged",
    owner: "王哲",
    updated: "今天 09:40",
    dsl: `rule "设备抵押放宽" when
  industry.grand == "制造业" and
  collateral.type == "equipment" and
  appraisal.days_since <= 180 and
  collateral.ltv <= 0.58
then
  set waiver = "ltv_strict";
  set reviewer = "branch_credit_lead";
end`,
  },
  {
    id: "rule-2026-039",
    name: "R-2026-039 · 关联交易单笔限额",
    status: "live",
    owner: "李慎之",
    updated: "昨天",
    dsl: "rule \"关联交易限额\" when related_party and amount > 5_000_000 then ...",
  },
  {
    id: "rule-2026-038",
    name: "R-2026-038 · 专精特新首贷白名单",
    status: "live",
    owner: "陈峰",
    updated: "04-18",
    dsl: "rule \"SRDC-小巨人-首贷\" when flag.srdi_list and first_loan then ...",
  },
  {
    id: "rule-2026-037",
    name: "R-2026-037 · 共债指数熔断",
    status: "draft",
    owner: "张晓芸",
    updated: "04-17",
    dsl: "rule \"共债熔断\" when pbc.multi_lending_score >= 88 then ...",
  },
];

export const RISKCTRL_BACKTEST: BacktestMetric[] = [
  { label: "KS", value: "0.48", hint: "坏样本分布分离度", delta: "+0.06 vs baseline", positive: true },
  { label: "AUC", value: "0.81", hint: "单点拔高", delta: "+0.03", positive: true },
  { label: "通过率", value: "72.4%", hint: "准入率", delta: "-4.1pt", positive: false },
  { label: "坏账率(模拟)", value: "1.82%", hint: "回测 12M 坏账估计", delta: "-0.47pt", positive: true },
  { label: "PSI", value: "0.08", hint: "样本稳定性", delta: "绿区(<0.1)", positive: true },
  { label: "Lift @ Top 20%", value: "2.7x", hint: "相对基线提升", delta: "+0.4x", positive: true },
];

export const RISKCTRL_INDICATORS: IndicatorCoverage[] = [
  { id: "ind-1", indicator: "monthly_flow_mom", coverage: 0.94, trigger: 186, sample: 8420 },
  { id: "ind-2", indicator: "overdue_count_24m", coverage: 1.0, trigger: 412, sample: 8420 },
  { id: "ind-3", indicator: "ltv", coverage: 0.88, trigger: 241, sample: 8420 },
  { id: "ind-4", indicator: "industry.code", coverage: 1.0, trigger: 1256, sample: 8420 },
  { id: "ind-5", indicator: "pbc.multi_lending_score", coverage: 0.72, trigger: 98, sample: 8420 },
];

export const RISKCTRL_AUDIT: RuleAuditEntry[] = [
  { id: "a-1", ts: "09:22", actor: "王哲", rule: "R-2026-041", verb: "backtest", note: "启动全量样本回测 · 估算 42 秒" },
  { id: "a-2", ts: "09:18", actor: "王哲", rule: "R-2026-041", verb: "create", note: "复用 R-037 模板 · 合成三项条件" },
  { id: "a-3", ts: "09:05", actor: "李慎之", rule: "R-2026-040", verb: "stage", note: "影子灰度 5% 流量 · 观察 7 天" },
  { id: "a-4", ts: "昨 22:14", actor: "陈峰", rule: "R-2026-038", verb: "publish", note: "KS 0.44 ok · 全量生效" },
  { id: "a-5", ts: "04-18", actor: "张晓芸", rule: "R-2026-037", verb: "rollback", note: "PSI 0.14 超阈 · 回滚到 R-033" },
];
