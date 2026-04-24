/**
 * Agent Riskctrl (DSL) · 单 session 对话式策略工作流 mock（2026-04-21 H2 · canon 横向迁移）
 * 业务：策略经理协同 AI 写 DSL 规则 → 样本回测 → 调参 → 落地
 * 五块完整 shape：query / rules / dsl / conversation / output(dsl tree + ks dual-line + sample bar)
 */

import type { ConversationMessage } from "./agent-report-session";
export type { ConversationMessage };

export const RISKCTRL_GLOBAL_STATS = {
  weeklyProcessed: "38",
  ksAvg: "0.41",
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
  conversation: ConversationMessage[];
  qcCounts: { block: number; warn: number; info: number };
  recentSessions: RiskctrlRecentSession[];
};

/* ── 常量 ─────────────────────────────────────────────── */

const QUERY: StrategyQuery = {
  id: "q-nc-approval-0421",
  objective: "新客户首贷批核策略 · 2026 Q2",
  sampleLabel: "2025-10 ~ 2026-03 放款客户",
  sampleSize: 12400,
  windowLabel: "6 个月滚动样本",
  targetKS: 0.35,
  targetPassRange: [0.3, 0.4],
  targetBadRate: 0.028,
  updated: "4 分钟前",
};

const RULES: RuleRef[] = [
  { id: "r-1", code: "NC-2025Q4", label: "新客户策略 v1.3 (在线)", version: "v1.3", hit: 6812, status: "active" },
  { id: "r-2", code: "NC-2026Q1", label: "新客户策略 v1.4 (在线)", version: "v1.4", hit: 5122, status: "active" },
  { id: "r-3", code: "NC-2026Q2-DRAFT", label: "新客户策略 v1.5 (草稿 · 当前)", version: "v1.5-d3", hit: 0, status: "draft" },
  { id: "r-4", code: "NC-2024Q3", label: "新客户策略 v1.0 (已下线)", version: "v1.0", hit: 0, status: "retired" },
];

const DSL: DslNode = {
  id: "root",
  op: "IF",
  children: [
    {
      id: "n-1",
      op: "AND",
      children: [
        { id: "n-1-1", op: "IF", field: "age", expr: ">= 22 AND <= 55" },
        { id: "n-1-2", op: "IF", field: "credit_score", expr: ">= 620" },
        {
          id: "n-1-3",
          op: "OR",
          children: [
            { id: "n-1-3-a", op: "IF", field: "job_tenure_months", expr: ">= 12" },
            { id: "n-1-3-b", op: "IF", field: "business_years", expr: ">= 2" },
          ],
        },
      ],
    },
    {
      id: "n-2",
      op: "AND",
      children: [
        { id: "n-2-1", op: "IF", field: "debt_income_ratio", expr: "<= 0.55" },
        { id: "n-2-2", op: "IF", field: "overdue_90_l12m", expr: "== 0" },
        { id: "n-2-3", op: "IF", field: "legal_risk_tags", expr: "not contains [被执行, 失信, 行政处罚]" },
      ],
    },
    {
      id: "n-3",
      op: "THEN",
      action: "pass",
      reason: "主链全通过 · 进入额度决策",
    },
    {
      id: "n-4",
      op: "IF",
      field: "credit_score",
      expr: ">= 580 AND < 620",
      children: [
        { id: "n-4-1", op: "THEN", action: "review", reason: "边际客户 · 人工复核" },
      ],
    },
    {
      id: "n-5",
      op: "THEN",
      action: "block",
      reason: "其他 · 拒绝",
    },
  ],
};

const KS_POINTS: KSPoint[] = Array.from({ length: 11 }, (_, i) => {
  const bin = i;
  const tpr = [0, 0.18, 0.34, 0.48, 0.6, 0.71, 0.8, 0.87, 0.92, 0.97, 1][i];
  const fpr = [0, 0.06, 0.13, 0.21, 0.3, 0.4, 0.51, 0.63, 0.76, 0.88, 1][i];
  return { bin, tpr, fpr, ks: Number((tpr - fpr).toFixed(3)) };
});

const SAMPLES: SampleBar[] = [
  { key: "pass", label: "通过", count: 4490, pct: 36.2, badRate: 2.4 },
  { key: "review", label: "复核", count: 1520, pct: 12.3, badRate: 5.8 },
  { key: "block", label: "拒绝", count: 6390, pct: 51.5, badRate: 18.4 },
];

const CONVERSATION: ConversationMessage[] = [
  {
    id: "rc-msg-1",
    at: "10 分钟前",
    kind: "system-event",
    content: "策略会话启动 · 目标：新客户批核 v1.5 · 样本 12,400 · 目标 KS ≥ 0.35",
  },
  {
    id: "rc-msg-2",
    at: "10 分钟前",
    kind: "ai-question",
    content: "基于 v1.4 的在线表现（KS 0.38 · 通过率 34.1%），本次重点优化什么？通过率再提 2pp / 坏账再压 0.3pp / 还是收窄边际客户的复核口径？",
  },
  {
    id: "rc-msg-3",
    at: "8 分钟前",
    kind: "user-reply",
    content: "坏账再压 0.3pp · 通过率保持 36% 左右 · 把 580-620 分段一律走人工复核而不是直接拒",
  },
  {
    id: "rc-msg-4",
    at: "7 分钟前",
    kind: "ai-thinking",
    content:
      "采样 12,400 笔 · 按用户诉求生成 v1.5 DSL 草稿 · 跑样本回测",
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
            "KS peak 0.41（目标 0.35 · 超标 0.06）",
            "AUC 0.758 · 单调性良好",
            "通过率 36.2% · 复核率 12.3%",
          ],
        },
        {
          label: "坏账率测算 · 与 v1.4 对比",
          evidences: [
            "通过段坏账 2.4% (v1.4 是 2.7%，下降 0.3pp ✓)",
            "复核段坏账 5.8% · 建议上限提至 8%",
            "拒绝段坏账 18.4% · 已拦截高风险客户",
          ],
        },
      ],
    },
  },
  {
    id: "rc-msg-5",
    at: "5 分钟前",
    kind: "ai-response",
    content:
      "v1.5 草案生成完毕 · KS 0.41 / 通过 36.2% / 通过段坏账 2.4%，三项目标均达成。规则树见右栏 DSL 视图。",
    fieldRef: "DSL · v1.5-d3",
    sectionDiff: {
      sectionAnchor: "Key metrics",
      after: "KS 0.41 ↑0.03 · 通过 36.2% 持平 · 通过段坏账 2.4% ↓0.3pp",
    },
  },
  {
    id: "rc-msg-6",
    at: "3 分钟前",
    kind: "ai-question",
    content: "是否进一步：将年龄下限从 22 放宽到 20？预计覆盖年轻客群 + 840 笔，KS 微降 0.005 · 通过率 +0.7pp。",
  },
  {
    id: "rc-msg-7",
    at: "2 分钟前",
    kind: "user-command",
    content: "/lock v1.5-d3 · 年龄下限保持 22 · 坏账控住优先 · 准备送审",
  },
  {
    id: "rc-msg-8",
    at: "刚刚",
    kind: "system-event",
    content: "v1.5-d3 已锁版 · 自动生成送审包（规则 DSL + 回测报告 + 与 v1.4 对比表）· 待风险总监审批",
  },
];

const RECENT: RiskctrlRecentSession[] = [
  { id: "rcr-1", objective: "新客户首贷策略 v1.5 (当前)", updated: "刚刚", ks: 0.41, status: "done" },
  { id: "rcr-2", objective: "存量续贷策略 v2.1", updated: "1 小时前", ks: 0.36, status: "backtesting" },
  { id: "rcr-3", objective: "小微商户应急贷 v0.3", updated: "昨天", ks: 0.29, status: "drafting" },
  { id: "rcr-4", objective: "场景分期 · 教育 v1.2", updated: "3 天前", ks: 0.44, status: "done" },
];

export const RISKCTRL_SESSION: RiskctrlSession = {
  id: "rcr-1",
  objective: "新客户首贷批核策略 v1.5",
  stage: "已锁版 · 待审批",
  updated: "刚刚",
  query: QUERY,
  rules: RULES,
  currentRule: { id: "r-3", name: "NC-2026Q2-DRAFT", version: "v1.5-d3" },
  dsl: DSL,
  ks: {
    ksPeak: 0.41,
    auc: 0.758,
    passRate: 36.2,
    badRate: 2.4,
    points: KS_POINTS,
  },
  samples: SAMPLES,
  conversation: CONVERSATION,
  qcCounts: { block: 0, warn: 0, info: 2 },
  recentSessions: RECENT,
};
