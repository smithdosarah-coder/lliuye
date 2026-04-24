/**
 * Agent Credit (授信 · A03) — Four-dimension scoring fixtures.
 * Feeds the /archive/credit workspace (radar + red-line checklist + limit card).
 */

export type CreditScoreAxis = {
  key: "finance" | "industry" | "operation" | "collateral";
  label: string;
  score: number; // 0..100
  note: string;
};

export type RedlineCheck = {
  id: string;
  rule: string;
  status: "pass" | "warn" | "fail";
  detail: string;
  citation: string;
};

export type CreditSuggestion = {
  limit: string;
  tenor: string;
  rate: string;
  structure: string;
  risk: "low" | "mid" | "high";
  confidence: number;
};

export type CaseRecall = {
  id: string;
  name: string;
  similarity: number;
  outcome: "approved" | "rejected" | "conditional";
  year: string;
};

export type CreditCaseInFlight = {
  id: string;
  name: string;
  stage: string;
  updated: string;
  amount: string;
};

export const CREDIT_STATS = {
  weeklyProcessed: "47",
  successRate: "91%",
  avgDuration: "6.1 分钟",
} as const;

export const CREDIT_INFLIGHT: CreditCaseInFlight[] = [
  { id: "c-ZA2604-0019", name: "福建惠民商贸", stage: "四维评分中", updated: "刚刚", amount: "800 万" },
  { id: "c-ZA2604-0018", name: "瀚蓝智控", stage: "红线检查", updated: "2 分钟前", amount: "1500 万" },
  { id: "c-ZA2604-0017", name: "东阳塑橡", stage: "额度测算", updated: "5 分钟前", amount: "2400 万" },
  { id: "c-ZA2604-0015", name: "宁波鼎承精密", stage: "案例召回", updated: "12 分钟前", amount: "1100 万" },
  { id: "c-ZA2604-0013", name: "常州鑫拓", stage: "等待面签", updated: "27 分钟前", amount: "900 万" },
  { id: "c-ZA2604-0009", name: "嘉兴远航物流", stage: "已出草稿", updated: "1 小时前", amount: "600 万" },
];

// radar axes — currently shown for "福建惠民商贸" (the lead card)
export const CREDIT_RADAR: CreditScoreAxis[] = [
  { key: "finance", label: "财务实力", score: 72, note: "营收同比 +18% · 资产负债率 54%" },
  { key: "industry", label: "行业前景", score: 81, note: "细分赛道景气度高,下游扩产期" },
  { key: "operation", label: "经营能力", score: 68, note: "核心客户集中度偏高,前五占 42%" },
  { key: "collateral", label: "担保覆盖", score: 85, note: "厂房抵押估值 2600 万,覆盖倍数 3.2x" },
];

export const CREDIT_REDLINES: RedlineCheck[] = [
  {
    id: "rl-1",
    rule: "统一社会信用代码与工商登记一致",
    status: "pass",
    detail: "USCC 91350102MA...一致,企查查工商同步时间 04-20",
    citation: "企查查 / 工商基础信息",
  },
  {
    id: "rl-2",
    rule: "法定代表人无失信被执行记录",
    status: "pass",
    detail: "中国执行信息公开网最新扫描 04-21 08:00,未命中",
    citation: "执信网 / 失信人名单",
  },
  {
    id: "rl-3",
    rule: "近 24 月无逾期且逾期总次数 ≤ 2",
    status: "warn",
    detail: "央行征信显示 2024-07 有 1 次 15 天逾期,已结清",
    citation: "人民银行征信报告 · P.04",
  },
  {
    id: "rl-4",
    rule: "同业授信合计不超过净资产 3 倍",
    status: "pass",
    detail: "同业在贷余额 1200 万 / 净资产 580 万,比率 2.07",
    citation: "审贷会纪要附件 · 2026-04-18",
  },
  {
    id: "rl-5",
    rule: "非限制行业 / 非产能过剩清单",
    status: "pass",
    detail: "商贸批发行业未进入银保监限制名录",
    citation: "总行 2026 行业政策 §3.2",
  },
  {
    id: "rl-6",
    rule: "主业毛利率不低于同业均值 -20%",
    status: "fail",
    detail: "毛利率 7.8%,同业中位 12.5%,低于阈值 -37%",
    citation: "行业卡片 · 批发零售业 / 2025Q4",
  },
];

export const CREDIT_SUGGESTION: CreditSuggestion = {
  limit: "¥ 560 万",
  tenor: "12 个月循环",
  rate: "LPR+1.85%",
  structure: "应收账款质押 + 法人保证",
  risk: "mid",
  confidence: 0.78,
};

export const CREDIT_CASE_RECALL: CaseRecall[] = [
  { id: "case-A", name: "厦门悦丰批发", similarity: 0.89, outcome: "approved", year: "2024" },
  { id: "case-B", name: "泉州海联供应链", similarity: 0.83, outcome: "conditional", year: "2025" },
  { id: "case-C", name: "漳州兴盛商贸", similarity: 0.77, outcome: "approved", year: "2024" },
  { id: "case-D", name: "福州丰华日化", similarity: 0.72, outcome: "rejected", year: "2023" },
];
