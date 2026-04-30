/**
 * Agent Riskctrl (DSL) · 多 session 策略工作流 mock (Phase A worker-A4 · 2026-04-29)
 *
 * 3 个差异化 session · 反 5 原则 §3.5 难度分层:
 *   sess_credit_v15  · 新客户首贷批核 v1.5 (绿区 · 简单档)  · KS 0.42 / 通过 32% / 坏账 2.4%
 *   sess_aml_kyc     · AML/KYC 准入策略 v2.3 (关注档 · 中等)· KS 0.31 / 通过 18% / 坏账 1.6%
 *   sess_fraud_high  · 高风险欺诈拦截 v0.7 (红区 · 极端档)  · KS 0.28 / 通过 8%  / 坏账 12.4%
 *
 * 每 session 间 ruleset / ks.points / samples / rule_stats 实质不同 · 不许 deep-copy 改名
 * 见: docs/contracts/workspace-state-protocol.md §3 + agent-forge-spec.md (DSL/回测语义)
 *
 * 承接旧 agent-riskctrl-session.ts (单 const) · workspace state 4 gate 切下拉用本 array
 */

import type { ConversationMessage } from "./agent-report-session";
export type { ConversationMessage };

export const RISKCTRL_GLOBAL_STATS = {
  weeklyProcessed: "38",
  ksAvg: "0.34",
  avgDuration: "9.4 分钟",
} as const;

/* ── 类型 ─────────────────────────────────────────────── */

export type StrategyQuery = {
  id: string;
  objective: string;
  sampleLabel: string;
  sampleSize: number;
  windowLabel: string;
  targetKS: number;
  targetPassRange: [number, number];
  targetBadRate: number;
  updated: string;
};

export type RuleRef = {
  id: string;
  code: string;
  label: string;
  version: string;
  hit: number;
  status: "active" | "draft" | "retired";
};

export type DslNode = {
  id: string;
  op: "IF" | "AND" | "OR" | "THEN";
  field?: string;
  expr?: string;
  action?: "pass" | "block" | "review";
  reason?: string;
  children?: DslNode[];
};

export type KSPoint = {
  bin: number;
  tpr: number;
  fpr: number;
  ks: number;
};

export type SampleBar = {
  key: "pass" | "block" | "review";
  label: string;
  count: number;
  pct: number;
  badRate: number;
};

/** Per-rule 命中明细 (回测 backend done payload `rule_stats`) */
export type RuleStat = {
  ruleId: string;
  hit: number;
  fp: number;
  tn: number;
};

export type RiskctrlRecentSession = {
  id: string;
  objective: string;
  updated: string;
  ks: number;
  status: "done" | "backtesting" | "drafting";
};

export type RiskctrlSession = {
  id: string;
  objective: string;
  stage: string;
  updated: string;
  query: StrategyQuery;
  rules: RuleRef[];
  currentRule: { id: string; name: string; version: string };
  dsl: DslNode;
  ks: {
    ksPeak: number;
    auc: number;
    passRate: number;
    badRate: number;
    points: KSPoint[];
  };
  samples: SampleBar[];
  ruleStats: RuleStat[];
  conversation: ConversationMessage[];
  qcCounts: { block: number; warn: number; info: number };
  recentSessions: RiskctrlRecentSession[];
};

/* helpers ─ KS 11-point series · monotonic */
const buildKsPoints = (
  tprArr: number[],
  fprArr: number[],
): KSPoint[] =>
  tprArr.map((tpr, i) => ({
    bin: i,
    tpr,
    fpr: fprArr[i],
    ks: Number((tpr - fprArr[i]).toFixed(3)),
  }));

/* ──────────────────────────────────────────────────────
   Session 1 · sess_credit_v15 (绿区 · 简单档)
   新客户首贷批核 · KS 0.42 / 通过 32% / 坏账 2.4%
   ────────────────────────────────────────────────────── */

const QUERY_CREDIT_V15: StrategyQuery = {
  id: "q-credit-v15",
  objective: "新客户首贷批核策略 · 2026 Q2",
  sampleLabel: "2025-10 ~ 2026-03 放款客户",
  sampleSize: 12400,
  windowLabel: "6 个月滚动样本",
  targetKS: 0.35,
  targetPassRange: [0.3, 0.4],
  targetBadRate: 0.028,
  updated: "4 分钟前",
};

const RULES_CREDIT_V15: RuleRef[] = [
  { id: "r-cv15-1", code: "NC-2025Q4", label: "新客户策略 v1.3 (在线)", version: "v1.3", hit: 6812, status: "active" },
  { id: "r-cv15-2", code: "NC-2026Q1", label: "新客户策略 v1.4 (在线)", version: "v1.4", hit: 5122, status: "active" },
  { id: "r-cv15-3", code: "NC-2026Q2-DRAFT", label: "新客户策略 v1.5 (草稿 · 当前)", version: "v1.5-d3", hit: 0, status: "draft" },
  { id: "r-cv15-4", code: "NC-2024Q3", label: "新客户策略 v1.0 (已下线)", version: "v1.0", hit: 0, status: "retired" },
];

const DSL_CREDIT_V15: DslNode = {
  id: "root",
  op: "IF",
  children: [
    {
      id: "n-cv15-1",
      op: "AND",
      children: [
        { id: "n-cv15-1-1", op: "IF", field: "age", expr: ">= 22 AND <= 55" },
        { id: "n-cv15-1-2", op: "IF", field: "credit_score", expr: ">= 620" },
        {
          id: "n-cv15-1-3",
          op: "OR",
          children: [
            { id: "n-cv15-1-3-a", op: "IF", field: "job_tenure_months", expr: ">= 12" },
            { id: "n-cv15-1-3-b", op: "IF", field: "business_years", expr: ">= 2" },
          ],
        },
      ],
    },
    {
      id: "n-cv15-2",
      op: "AND",
      children: [
        { id: "n-cv15-2-1", op: "IF", field: "debt_income_ratio", expr: "<= 0.55" },
        { id: "n-cv15-2-2", op: "IF", field: "overdue_90_l12m", expr: "== 0" },
        { id: "n-cv15-2-3", op: "IF", field: "legal_risk_tags", expr: "not contains [被执行, 失信, 行政处罚]" },
      ],
    },
    { id: "n-cv15-3", op: "THEN", action: "pass", reason: "主链全通过 · 进入额度决策" },
    {
      id: "n-cv15-4",
      op: "IF",
      field: "credit_score",
      expr: ">= 580 AND < 620",
      children: [{ id: "n-cv15-4-1", op: "THEN", action: "review", reason: "边际客户 · 人工复核" }],
    },
    { id: "n-cv15-5", op: "THEN", action: "block", reason: "其他 · 拒绝" },
  ],
};

const KS_CREDIT_V15 = buildKsPoints(
  [0, 0.18, 0.34, 0.48, 0.6, 0.72, 0.81, 0.88, 0.93, 0.97, 1],
  [0, 0.06, 0.13, 0.21, 0.3, 0.4, 0.51, 0.63, 0.76, 0.88, 1],
);

const SAMPLES_CREDIT_V15: SampleBar[] = [
  { key: "pass", label: "通过", count: 3968, pct: 32.0, badRate: 2.4 },
  { key: "review", label: "复核", count: 1612, pct: 13.0, badRate: 5.8 },
  { key: "block", label: "拒绝", count: 6820, pct: 55.0, badRate: 18.4 },
];

const RULE_STATS_CREDIT_V15: RuleStat[] = [
  { ruleId: "n-cv15-1", hit: 6432, fp: 188, tn: 5772 },
  { ruleId: "n-cv15-2", hit: 4870, fp: 132, tn: 4548 },
  { ruleId: "n-cv15-4", hit: 1612, fp: 94, tn: 1418 },
  { ruleId: "n-cv15-5", hit: 6820, fp: 1252, tn: 5568 },
];

const CONVERSATION_CREDIT_V15: ConversationMessage[] = [
  {
    id: "rc-cv15-1",
    at: "10 分钟前",
    kind: "system-event",
    content: "策略会话启动 · 目标：新客户批核 v1.5 · 样本 12,400 · 目标 KS ≥ 0.35",
  },
  {
    id: "rc-cv15-2",
    at: "10 分钟前",
    kind: "ai-question",
    content: "基于 v1.4 的在线表现（KS 0.38 · 通过率 34.1%），本次重点优化什么？通过率再提 2pp / 坏账再压 0.3pp / 还是收窄边际客户的复核口径？",
  },
  {
    id: "rc-cv15-3",
    at: "8 分钟前",
    kind: "user-reply",
    content: "坏账再压 0.3pp · 通过率保持 32% 左右 · 把 580-620 分段一律走人工复核而不是直接拒",
  },
  {
    id: "rc-cv15-4",
    at: "7 分钟前",
    kind: "ai-thinking",
    content: "采样 12,400 笔 · 按用户诉求生成 v1.5 DSL 草稿 · 跑样本回测",
    thinking: {
      steps: [
        {
          label: "DSL 生成 · 14 条规则 · 3 层决策",
          evidences: [
            "主链：年龄/评分/工作/负债/逾期/司法 6 关",
            "边际链：580-620 转复核（非直接拒绝）",
            "兜底：其他拒绝",
          ],
        },
        {
          label: "样本回测 · 12,400 笔 · K-S 分桶",
          evidences: [
            "KS peak 0.42（目标 0.35 · 超标 0.07）",
            "AUC 0.762 · 单调性良好",
            "通过率 32.0% · 复核率 13.0%",
          ],
        },
      ],
    },
  },
  {
    id: "rc-cv15-5",
    at: "5 分钟前",
    kind: "ai-response",
    content: "v1.5 草案生成完毕 · KS 0.42 / 通过 32.0% / 通过段坏账 2.4%，三项目标均达成。规则树见右栏 DSL 视图。",
    fieldRef: "DSL · v1.5-d3",
    sectionDiff: { sectionAnchor: "Key metrics", after: "KS 0.42 ↑0.04 · 通过 32.0% · 通过段坏账 2.4% ↓0.3pp" },
  },
];

const RECENT_CREDIT_V15: RiskctrlRecentSession[] = [
  { id: "rcr-cv15", objective: "新客户首贷批核 v1.5 (当前)", updated: "刚刚", ks: 0.42, status: "done" },
  { id: "rcr-aml", objective: "AML/KYC 准入策略 v2.3", updated: "1 小时前", ks: 0.31, status: "backtesting" },
  { id: "rcr-fraud", objective: "高风险欺诈拦截 v0.7", updated: "昨天", ks: 0.28, status: "drafting" },
];

export const SESS_CREDIT_V15: RiskctrlSession = {
  id: "sess_credit_v15",
  objective: "新客户首贷批核策略 v1.5",
  stage: "已锁版 · 待审批",
  updated: "刚刚",
  query: QUERY_CREDIT_V15,
  rules: RULES_CREDIT_V15,
  currentRule: { id: "r-cv15-3", name: "NC-2026Q2-DRAFT", version: "v1.5-d3" },
  dsl: DSL_CREDIT_V15,
  ks: { ksPeak: 0.42, auc: 0.762, passRate: 32.0, badRate: 2.4, points: KS_CREDIT_V15 },
  samples: SAMPLES_CREDIT_V15,
  ruleStats: RULE_STATS_CREDIT_V15,
  conversation: CONVERSATION_CREDIT_V15,
  qcCounts: { block: 0, warn: 0, info: 2 },
  recentSessions: RECENT_CREDIT_V15,
};

/* ──────────────────────────────────────────────────────
   Session 2 · sess_aml_kyc (关注档 · 中等)
   AML/KYC 准入 · KS 0.31 / 通过 18% / 坏账 1.6%
   ────────────────────────────────────────────────────── */

const QUERY_AML: StrategyQuery = {
  id: "q-aml-v23",
  objective: "对公开户 AML/KYC 准入策略 v2.3",
  sampleLabel: "2025-09 ~ 2026-02 对公开户申请",
  sampleSize: 8200,
  windowLabel: "5 个月窗口 · 含 SAR 标记",
  targetKS: 0.28,
  targetPassRange: [0.15, 0.22],
  targetBadRate: 0.02,
  updated: "1 小时前",
};

const RULES_AML: RuleRef[] = [
  { id: "r-aml-1", code: "AML-CORP-2025", label: "对公 KYC v2.2 (在线)", version: "v2.2", hit: 1432, status: "active" },
  { id: "r-aml-2", code: "AML-CORP-2026Q1", label: "对公 KYC v2.3 (草稿)", version: "v2.3-d2", hit: 0, status: "draft" },
  { id: "r-aml-3", code: "AML-PEP-2025", label: "PEP 增强尽调 (在线)", version: "v1.4", hit: 86, status: "active" },
  { id: "r-aml-4", code: "AML-CORP-2024", label: "对公 KYC v2.0 (已下线)", version: "v2.0", hit: 0, status: "retired" },
];

const DSL_AML: DslNode = {
  id: "root",
  op: "IF",
  children: [
    {
      id: "n-aml-1",
      op: "AND",
      children: [
        { id: "n-aml-1-1", op: "IF", field: "sanctions_list_match", expr: "== false" },
        { id: "n-aml-1-2", op: "IF", field: "pep_status", expr: "in [none, low]" },
        { id: "n-aml-1-3", op: "IF", field: "high_risk_country_flag", expr: "== false" },
      ],
    },
    {
      id: "n-aml-2",
      op: "AND",
      children: [
        { id: "n-aml-2-1", op: "IF", field: "ubo_disclosure_complete", expr: "== true" },
        { id: "n-aml-2-2", op: "IF", field: "registered_capital", expr: ">= 1000000" },
        { id: "n-aml-2-3", op: "IF", field: "industry_sic", expr: "not in [shell_company_high_risk_sic]" },
        { id: "n-aml-2-4", op: "IF", field: "address_verification_score", expr: ">= 0.7" },
      ],
    },
    { id: "n-aml-3", op: "THEN", action: "pass", reason: "标准准入 · 进入对公开户流程" },
    {
      id: "n-aml-4",
      op: "OR",
      children: [
        { id: "n-aml-4-1", op: "IF", field: "pep_status", expr: "in [medium]" },
        { id: "n-aml-4-2", op: "IF", field: "ubo_disclosure_complete", expr: "== false" },
        { id: "n-aml-4-3", op: "IF", field: "address_verification_score", expr: ">= 0.4 AND < 0.7" },
      ],
    },
    { id: "n-aml-5", op: "THEN", action: "review", reason: "EDD 增强尽调 · 反洗钱总部复核" },
    { id: "n-aml-6", op: "THEN", action: "block", reason: "命中制裁/PEP 高/UBO 缺失/地址欺诈 · 拒绝" },
  ],
};

const KS_AML = buildKsPoints(
  [0, 0.12, 0.22, 0.33, 0.43, 0.54, 0.65, 0.75, 0.84, 0.93, 1],
  [0, 0.05, 0.11, 0.18, 0.27, 0.38, 0.49, 0.62, 0.75, 0.88, 1],
);

const SAMPLES_AML: SampleBar[] = [
  { key: "pass", label: "通过", count: 1476, pct: 18.0, badRate: 1.6 },
  { key: "review", label: "EDD 复核", count: 2624, pct: 32.0, badRate: 4.2 },
  { key: "block", label: "拒绝", count: 4100, pct: 50.0, badRate: 22.6 },
];

const RULE_STATS_AML: RuleStat[] = [
  { ruleId: "n-aml-1", hit: 7980, fp: 64, tn: 7916 },
  { ruleId: "n-aml-2", hit: 4920, fp: 138, tn: 4782 },
  { ruleId: "n-aml-4", hit: 2624, fp: 412, tn: 2212 },
  { ruleId: "n-aml-6", hit: 4100, fp: 814, tn: 3286 },
];

const CONVERSATION_AML: ConversationMessage[] = [
  { id: "rc-aml-1", at: "1 小时前", kind: "system-event", content: "AML/KYC v2.3 策略会话启动 · 样本 8,200 · 目标 KS ≥ 0.28" },
  {
    id: "rc-aml-2",
    at: "55 分钟前",
    kind: "ai-question",
    content: "v2.2 在线表现：KS 0.27 · 通过 21% · 坏账 1.9%。本次优化方向？(1) 收紧 PEP 中等档 (2) 强化 UBO 完整性 (3) 引入地址核验分？",
  },
  { id: "rc-aml-3", at: "50 分钟前", kind: "user-reply", content: "三个方向都要 · 优先地址核验分 · UBO 必须完整否则直拒" },
  {
    id: "rc-aml-4",
    at: "45 分钟前",
    kind: "ai-thinking",
    content: "生成 v2.3 DSL · 加 address_verification_score 字段 · 跑回测",
    thinking: {
      steps: [
        { label: "DSL 生成 · 18 条规则 · 4 层决策", evidences: ["制裁/PEP/高风险国 3 道一票否决", "UBO+注册资本+行业+地址 4 关 AND", "PEP 中/UBO 缺/地址低 → EDD 复核", "兜底拒绝"] },
        { label: "样本回测 · 8,200 笔", evidences: ["KS peak 0.31（目标 0.28 ↑0.03）", "通过 18% (v2.2 21% · ↓3pp)", "通过段坏账 1.6% (v2.2 1.9% · ↓0.3pp)"] },
      ],
    },
  },
  {
    id: "rc-aml-5",
    at: "40 分钟前",
    kind: "ai-response",
    content: "v2.3 草案完成 · KS 0.31 / 通过 18% / 坏账 1.6%。EDD 复核档增至 32% (v2.2 是 22%)，需评估反洗钱总部产能。",
    fieldRef: "DSL · v2.3-d2",
  },
];

const RECENT_AML: RiskctrlRecentSession[] = [
  { id: "rcr-aml", objective: "AML/KYC 准入 v2.3 (当前)", updated: "刚刚", ks: 0.31, status: "backtesting" },
  { id: "rcr-cv15", objective: "新客户首贷批核 v1.5", updated: "1 小时前", ks: 0.42, status: "done" },
];

export const SESS_AML_KYC: RiskctrlSession = {
  id: "sess_aml_kyc",
  objective: "AML/KYC 对公开户准入策略 v2.3",
  stage: "回测中 · 待 EDD 产能评估",
  updated: "40 分钟前",
  query: QUERY_AML,
  rules: RULES_AML,
  currentRule: { id: "r-aml-2", name: "AML-CORP-2026Q1", version: "v2.3-d2" },
  dsl: DSL_AML,
  ks: { ksPeak: 0.31, auc: 0.694, passRate: 18.0, badRate: 1.6, points: KS_AML },
  samples: SAMPLES_AML,
  ruleStats: RULE_STATS_AML,
  conversation: CONVERSATION_AML,
  qcCounts: { block: 0, warn: 1, info: 3 },
  recentSessions: RECENT_AML,
};

/* ──────────────────────────────────────────────────────
   Session 3 · sess_fraud_high (红区 · 极端档)
   高风险欺诈拦截 v0.7 · KS 0.28 / 通过 8% / 坏账 12.4%
   ────────────────────────────────────────────────────── */

const QUERY_FRAUD: StrategyQuery = {
  id: "q-fraud-v07",
  objective: "高风险欺诈拦截策略 v0.7 (设备指纹+网络团伙)",
  sampleLabel: "2026-03 已标记可疑申请样本 (含 SAR)",
  sampleSize: 3200,
  windowLabel: "1 个月样本 · 含人工标注欺诈标签",
  targetKS: 0.25,
  targetPassRange: [0.05, 0.12],
  targetBadRate: 0.15,
  updated: "昨天",
};

const RULES_FRAUD: RuleRef[] = [
  { id: "r-fraud-1", code: "FRAUD-DEV-2026", label: "设备指纹聚类 v0.6 (在线)", version: "v0.6", hit: 412, status: "active" },
  { id: "r-fraud-2", code: "FRAUD-NET-2026Q2", label: "团伙网络识别 v0.7 (草稿)", version: "v0.7-d1", hit: 0, status: "draft" },
  { id: "r-fraud-3", code: "FRAUD-VEL-2025", label: "申请速率异常 (在线)", version: "v0.4", hit: 286, status: "active" },
];

const DSL_FRAUD: DslNode = {
  id: "root",
  op: "IF",
  children: [
    {
      id: "n-fraud-1",
      op: "OR",
      children: [
        { id: "n-fraud-1-1", op: "IF", field: "device_fingerprint_cluster_size", expr: ">= 5" },
        { id: "n-fraud-1-2", op: "IF", field: "ip_geolocation_mismatch", expr: "== true" },
        { id: "n-fraud-1-3", op: "IF", field: "behavioral_biometric_score", expr: "<= 0.3" },
      ],
    },
    { id: "n-fraud-2", op: "THEN", action: "block", reason: "设备/IP/行为特征异常 · 直接拒绝" },
    {
      id: "n-fraud-3",
      op: "AND",
      children: [
        { id: "n-fraud-3-1", op: "IF", field: "social_graph_risk_score", expr: ">= 0.7" },
        { id: "n-fraud-3-2", op: "IF", field: "shared_device_with_blacklist", expr: "== true" },
      ],
    },
    { id: "n-fraud-4", op: "THEN", action: "block", reason: "团伙网络高风险 · 直接拒绝" },
    {
      id: "n-fraud-5",
      op: "OR",
      children: [
        { id: "n-fraud-5-1", op: "IF", field: "application_velocity_24h", expr: ">= 3" },
        { id: "n-fraud-5-2", op: "IF", field: "id_fraud_signal", expr: "in [medium, high]" },
        { id: "n-fraud-5-3", op: "IF", field: "amount_anomaly_score", expr: ">= 0.6" },
      ],
    },
    { id: "n-fraud-6", op: "THEN", action: "review", reason: "速率/身份/金额异常 · 反欺诈复核" },
    { id: "n-fraud-7", op: "THEN", action: "pass", reason: "欺诈风险 < 阈值 · 流入信用主链" },
  ],
};

const KS_FRAUD = buildKsPoints(
  [0, 0.08, 0.18, 0.28, 0.39, 0.51, 0.63, 0.74, 0.84, 0.93, 1],
  [0, 0.04, 0.10, 0.18, 0.27, 0.38, 0.50, 0.63, 0.76, 0.88, 1],
);

const SAMPLES_FRAUD: SampleBar[] = [
  { key: "pass", label: "通过", count: 256, pct: 8.0, badRate: 12.4 },
  { key: "review", label: "复核", count: 768, pct: 24.0, badRate: 28.6 },
  { key: "block", label: "拒绝", count: 2176, pct: 68.0, badRate: 64.2 },
];

const RULE_STATS_FRAUD: RuleStat[] = [
  { ruleId: "n-fraud-1", hit: 1248, fp: 92, tn: 1156 },
  { ruleId: "n-fraud-3", hit: 412, fp: 38, tn: 374 },
  { ruleId: "n-fraud-5", hit: 768, fp: 162, tn: 606 },
  { ruleId: "n-fraud-6", hit: 768, fp: 162, tn: 606 },
];

const CONVERSATION_FRAUD: ConversationMessage[] = [
  { id: "rc-fraud-1", at: "昨天 14:00", kind: "system-event", content: "欺诈拦截 v0.7 策略会话启动 · 极端档样本 3,200 · 目标 KS ≥ 0.25" },
  {
    id: "rc-fraud-2",
    at: "昨天 13:55",
    kind: "ai-question",
    content: "v0.6 仅靠设备指纹聚类 · KS 0.21。本次目标：(1) 加团伙网络识别 (社交图风险) (2) 加行为生物特征 (3) 速率+身份+金额三联检 复核档。优先级？",
  },
  { id: "rc-fraud-3", at: "昨天 13:50", kind: "user-reply", content: "团伙网络优先 · 行为生物特征次之 · 速率/身份/金额走复核 · 通过率别太低否则误伤多" },
  {
    id: "rc-fraud-4",
    at: "昨天 13:40",
    kind: "ai-thinking",
    content: "生成 v0.7 草案 · 加 social_graph_risk_score / shared_device_with_blacklist / behavioral_biometric_score / ip_geolocation_mismatch 4 字段 · 跑回测",
    thinking: {
      steps: [
        { label: "DSL 生成 · 21 条规则 · 4 层决策 (一票否决 → 团伙否决 → 复核 → 兜底通过)", evidences: ["设备/IP/行为 OR 一票否决", "团伙图谱+共享设备 AND 否决", "速率/身份/金额 OR 转复核", "其他默认通过流入主链"] },
        { label: "样本回测 · 3,200 已标欺诈样本", evidences: ["KS peak 0.28（目标 0.25 ↑0.03）", "通过 8% (vs v0.6 11% · 误伤可控)", "通过段坏账 12.4% (vs v0.6 18.6% · ↓6.2pp)", "复核段 24% · 反欺诈队列产能 50/天 紧张"] },
      ],
    },
  },
  {
    id: "rc-fraud-5",
    at: "昨天 13:30",
    kind: "ai-response",
    content: "v0.7 草案完成 · KS 0.28 / 通过 8% / 通过段坏账 12.4%。复核档 24%（768 笔）远超反欺诈日产能 50 件 · 建议分批送审或优先级排序。",
    fieldRef: "DSL · v0.7-d1",
  },
];

const RECENT_FRAUD: RiskctrlRecentSession[] = [
  { id: "rcr-fraud", objective: "欺诈拦截 v0.7 (当前 · 草稿)", updated: "昨天", ks: 0.28, status: "drafting" },
  { id: "rcr-aml", objective: "AML/KYC v2.3", updated: "1 小时前", ks: 0.31, status: "backtesting" },
  { id: "rcr-cv15", objective: "新客户首贷 v1.5", updated: "刚刚", ks: 0.42, status: "done" },
];

export const SESS_FRAUD_HIGH: RiskctrlSession = {
  id: "sess_fraud_high",
  objective: "高风险欺诈拦截 v0.7",
  stage: "草稿 · 反欺诈队列产能压测",
  updated: "昨天",
  query: QUERY_FRAUD,
  rules: RULES_FRAUD,
  currentRule: { id: "r-fraud-2", name: "FRAUD-NET-2026Q2", version: "v0.7-d1" },
  dsl: DSL_FRAUD,
  ks: { ksPeak: 0.28, auc: 0.638, passRate: 8.0, badRate: 12.4, points: KS_FRAUD },
  samples: SAMPLES_FRAUD,
  ruleStats: RULE_STATS_FRAUD,
  conversation: CONVERSATION_FRAUD,
  qcCounts: { block: 1, warn: 4, info: 1 },
  recentSessions: RECENT_FRAUD,
};

/* ──────────────────────────────────────────────────────
   导出 · MOCK_SESSIONS_MAP + DEFAULT_SESSION_ID + LIST
   ────────────────────────────────────────────────────── */

/** Master map · RiskctrlWorkspace 切下拉 · 3 sessions 难度分层 */
export const RISKCTRL_MOCK_SESSIONS_MAP: Record<string, RiskctrlSession> = {
  [SESS_CREDIT_V15.id]: SESS_CREDIT_V15,
  [SESS_AML_KYC.id]: SESS_AML_KYC,
  [SESS_FRAUD_HIGH.id]: SESS_FRAUD_HIGH,
};

/** 默认 session id · 初渲染 selectedSession 默认值 */
export const RISKCTRL_DEFAULT_SESSION_ID = SESS_CREDIT_V15.id;

/** 历史 session 列表 · QueryBar 下拉 · 顺序固定 */
export const RISKCTRL_MOCK_SESSIONS_LIST: { id: string; objective: string; ks: number }[] = [
  { id: SESS_CREDIT_V15.id, objective: SESS_CREDIT_V15.objective, ks: SESS_CREDIT_V15.ks.ksPeak },
  { id: SESS_AML_KYC.id, objective: SESS_AML_KYC.objective, ks: SESS_AML_KYC.ks.ksPeak },
  { id: SESS_FRAUD_HIGH.id, objective: SESS_FRAUD_HIGH.objective, ks: SESS_FRAUD_HIGH.ks.ksPeak },
];

/** 兼容 · 旧 RISKCTRL_SESSION 入口 · 指向 SESS_CREDIT_V15 (Step 11 删旧文件后由本 export 接替) */
export const RISKCTRL_SESSION = SESS_CREDIT_V15;
