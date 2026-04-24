/**
 * Agent Compliance · 单 session 对话式合规扫描 mock（2026-04-21 H5 · canon 横向迁移）
 * 业务：政策发布事件驱动，Agent 对业务制度/产品做条款级冲突点扫描，产出违规明细 + 整改优先级
 * 五块完整 shape：query / policies / pipeline / conversation / output(矩阵 + funnel + 政策 timeline)
 */

import type { ConversationMessage } from "./agent-report-session";
export type { ConversationMessage };

export const COMPLIANCE_GLOBAL_STATS = {
  weeklyProcessed: "17",
  conflictRate: "7.8%",
  avgDuration: "14.3 分钟",
} as const;

/* ── 类型 ─────────────────────────────────────────────── */

export type ComplianceQuery = {
  id: string;
  policyTitle: string;
  policyCode: string;
  issuer: string;
  issueDate: string;
  effectiveDate: string;
  clauseCount: number;
  scope: string;
  updated: string;
};

export type PolicyRef = {
  id: string;
  title: string;
  issuer: string;
  date: string;
  severity: "high" | "mid" | "low";
  scanStatus: "done" | "scanning" | "pending";
  conflicts: number;
};

export type InternalDoc = {
  id: string;
  title: string;
  type: "条款" | "办法" | "规程" | "标准";
  lastRev: string;
  coverage: number;
};

export type MatrixCell = {
  docId: string;
  clauseId: string;
  severity: "block" | "warn" | "info" | "pass";
  note?: string;
};

export type Conflict = {
  id: string;
  clauseLabel: string;
  docId: string;
  docTitle: string;
  severity: "block" | "warn" | "info";
  finding: string;
  cite: string;
  advice: string;
};

export type FunnelStage = {
  key: "clauses" | "scanned" | "hit" | "resolved";
  label: string;
  count: number;
  sub?: string;
};

export type PolicyTimelineItem = {
  id: string;
  date: string;
  title: string;
  issuer: string;
  kind: "issued" | "effective" | "scanned" | "resolved";
  note?: string;
};

export type PipelineStep = {
  id: string;
  label: string;
  status: "done" | "active" | "pending";
  note?: string;
};

export type ComplianceRecentSession = {
  id: string;
  policy: string;
  updated: string;
  conflicts: number;
  resolved: number;
};

export type ComplianceSession = {
  id: string;
  objective: string;
  stage: string;
  updated: string;
  query: ComplianceQuery;
  policies: PolicyRef[];
  docs: InternalDoc[];
  pipeline: PipelineStep[];
  matrix: MatrixCell[];
  clauses: { id: string; label: string }[];
  conflicts: Conflict[];
  funnel: FunnelStage[];
  timeline: PolicyTimelineItem[];
  conversation: ConversationMessage[];
  qcCounts: { block: number; warn: number; info: number };
  recentSessions: ComplianceRecentSession[];
};

/* ── 常量 ─────────────────────────────────────────────── */

const QUERY: ComplianceQuery = {
  id: "cp-cbirc-2026-18",
  policyTitle: "《消费金融公司管理办法》修订版",
  policyCode: "银保监发〔2026〕18 号",
  issuer: "国家金融监督管理总局",
  issueDate: "2026-04-08",
  effectiveDate: "2026-06-01",
  clauseCount: 78,
  scope: "消费金融公司 + 合作银行 · 全国",
  updated: "6 分钟前",
};

const POLICIES: PolicyRef[] = [
  {
    id: "pr-1",
    title: "《消费金融公司管理办法》修订版（当前）",
    issuer: "金监总局",
    date: "2026-04-08",
    severity: "high",
    scanStatus: "done",
    conflicts: 11,
  },
  {
    id: "pr-2",
    title: "《个人信息保护法》实施细则 2026 Q2",
    issuer: "网信办",
    date: "2026-03-20",
    severity: "high",
    scanStatus: "done",
    conflicts: 4,
  },
  {
    id: "pr-3",
    title: "《征信业务管理办法》修正通知",
    issuer: "人行",
    date: "2026-02-15",
    severity: "mid",
    scanStatus: "done",
    conflicts: 2,
  },
  {
    id: "pr-4",
    title: "《反洗钱法》司法解释 v3",
    issuer: "最高法",
    date: "2026-01-28",
    severity: "mid",
    scanStatus: "scanning",
    conflicts: 0,
  },
];

const DOCS: InternalDoc[] = [
  { id: "d-1", title: "信用卡章程 2025 版", type: "条款", lastRev: "2025-09-12", coverage: 93 },
  { id: "d-2", title: "消费贷办法 v4.2", type: "办法", lastRev: "2025-11-30", coverage: 88 },
  { id: "d-3", title: "催收操作规程 2025 Q4", type: "规程", lastRev: "2025-12-18", coverage: 96 },
  { id: "d-4", title: "合作方接入标准 v2.7", type: "标准", lastRev: "2026-01-20", coverage: 81 },
];

const CLAUSES = [
  { id: "c-12", label: "第 12 条 · 贷款利率" },
  { id: "c-23", label: "第 23 条 · 信息披露" },
  { id: "c-31", label: "第 31 条 · 催收行为" },
  { id: "c-42", label: "第 42 条 · 合作方尽调" },
  { id: "c-56", label: "第 56 条 · 数据出境" },
  { id: "c-67", label: "第 67 条 · 贷后管理" },
];

const MATRIX: MatrixCell[] = [
  // 信用卡章程（d-1）
  { docId: "d-1", clauseId: "c-12", severity: "warn", note: "利率披露位置需提前至合同首页" },
  { docId: "d-1", clauseId: "c-23", severity: "block", note: "信息披露范围不含逾期违约金阶梯计算" },
  { docId: "d-1", clauseId: "c-31", severity: "pass" },
  { docId: "d-1", clauseId: "c-42", severity: "info" },
  { docId: "d-1", clauseId: "c-56", severity: "warn", note: "数据传至海外分支需补 CAC 申报" },
  { docId: "d-1", clauseId: "c-67", severity: "pass" },
  // 消费贷办法（d-2）
  { docId: "d-2", clauseId: "c-12", severity: "block", note: "综合年化利率上限 24% 与新规 23.9% 冲突" },
  { docId: "d-2", clauseId: "c-23", severity: "warn", note: "还款计划披露粒度按月；新规要求按日" },
  { docId: "d-2", clauseId: "c-31", severity: "pass" },
  { docId: "d-2", clauseId: "c-42", severity: "warn", note: "合作方尽调表缺少股权穿透到自然人" },
  { docId: "d-2", clauseId: "c-56", severity: "pass" },
  { docId: "d-2", clauseId: "c-67", severity: "info" },
  // 催收操作规程（d-3）
  { docId: "d-3", clauseId: "c-12", severity: "pass" },
  { docId: "d-3", clauseId: "c-23", severity: "pass" },
  { docId: "d-3", clauseId: "c-31", severity: "block", note: "通讯录催收口径需按新规限定为紧急联系人" },
  { docId: "d-3", clauseId: "c-42", severity: "pass" },
  { docId: "d-3", clauseId: "c-56", severity: "pass" },
  { docId: "d-3", clauseId: "c-67", severity: "warn", note: "延期还款触达次数上限下调 5→3" },
  // 合作方接入标准（d-4）
  { docId: "d-4", clauseId: "c-12", severity: "pass" },
  { docId: "d-4", clauseId: "c-23", severity: "info" },
  { docId: "d-4", clauseId: "c-31", severity: "pass" },
  { docId: "d-4", clauseId: "c-42", severity: "block", note: "新规要求合作方 5 年业绩 + 合规审核，现版缺失" },
  { docId: "d-4", clauseId: "c-56", severity: "warn", note: "合作方数据接入后需独立加密存储" },
  { docId: "d-4", clauseId: "c-67", severity: "info" },
];

const CONFLICTS: Conflict[] = [
  {
    id: "cf-1",
    clauseLabel: "第 23 条 · 信息披露",
    docId: "d-1",
    docTitle: "信用卡章程 2025 版",
    severity: "block",
    finding: "现版未披露逾期违约金阶梯计算公式，新规要求「可量化可复算」",
    cite: "新规第 23 条 第 2 款 · 2026-04-08 发布",
    advice: "2026-06-01 前更新信用卡章程 §4.3 并通过董事会审议；历史存量合同逐户增补披露附件",
  },
  {
    id: "cf-2",
    clauseLabel: "第 12 条 · 贷款利率",
    docId: "d-2",
    docTitle: "消费贷办法 v4.2",
    severity: "block",
    finding: "综合年化利率上限 24.0% > 新规 23.9%",
    cite: "新规第 12 条 第 1 款 · 2026-04-08 发布",
    advice: "重定价引擎统一将 24% 封顶降至 23.9%；新发放合同于 2026-05-15 起切换；存量合同下次重定价生效",
  },
  {
    id: "cf-3",
    clauseLabel: "第 31 条 · 催收行为",
    docId: "d-3",
    docTitle: "催收操作规程 2025 Q4",
    severity: "block",
    finding: "通讯录全量催收不符合「限于申请人授权的紧急联系人」",
    cite: "新规第 31 条 第 3 款 · 2026-04-08 发布",
    advice: "催收系统 2026-05-10 前改造：通讯录字段不再接入；紧急联系人栏需用户重新授权",
  },
  {
    id: "cf-4",
    clauseLabel: "第 42 条 · 合作方尽调",
    docId: "d-4",
    docTitle: "合作方接入标准 v2.7",
    severity: "block",
    finding: "标准未覆盖「5 年合规业绩 + 最终受益人穿透」两项",
    cite: "新规第 42 条 · 2026-04-08 发布",
    advice: "准入表单新增两项；已签约合作方 90 天内补充尽调",
  },
  {
    id: "cf-5",
    clauseLabel: "第 23 条 · 信息披露",
    docId: "d-2",
    docTitle: "消费贷办法 v4.2",
    severity: "warn",
    finding: "还款计划按月披露，新规要求按日明细",
    cite: "新规第 23 条 第 4 款",
    advice: "还款计划视图增加按日明细切换；新合同起默认按日",
  },
  {
    id: "cf-6",
    clauseLabel: "第 12 条 · 贷款利率",
    docId: "d-1",
    docTitle: "信用卡章程 2025 版",
    severity: "warn",
    finding: "利率披露位置位于合同附件，新规要求前置到首页显著位置",
    cite: "新规第 12 条 第 2 款",
    advice: "合同排版模板调整：首页增加「APR 公示卡」样式",
  },
  {
    id: "cf-7",
    clauseLabel: "第 67 条 · 贷后管理",
    docId: "d-3",
    docTitle: "催收操作规程 2025 Q4",
    severity: "warn",
    finding: "延期还款触达次数上限 5，需下调至 3",
    cite: "新规第 67 条",
    advice: "规程修订 + 催收系统触达上限配置调整",
  },
];

const FUNNEL: FunnelStage[] = [
  { key: "clauses", label: "新规条款", count: 78, sub: "总量" },
  { key: "scanned", label: "已扫描制度", count: 4, sub: "4 份内部文档" },
  { key: "hit", label: "冲突命中", count: 11, sub: "严重 4 · 警告 5 · 提示 2" },
  { key: "resolved", label: "已处置", count: 3, sub: "派工单 · 27% 完成" },
];

const TIMELINE: PolicyTimelineItem[] = [
  {
    id: "t-1",
    date: "2026-04-21",
    title: "《消费金融公司管理办法》修订版 · 扫描完成",
    issuer: "金监总局",
    kind: "scanned",
    note: "11 条冲突 · 4 份制度受影响",
  },
  {
    id: "t-2",
    date: "2026-04-08",
    title: "《消费金融公司管理办法》修订版 · 发布",
    issuer: "金监总局",
    kind: "issued",
    note: "78 条款 · 2026-06-01 生效",
  },
  {
    id: "t-3",
    date: "2026-03-20",
    title: "《个保法》实施细则 2026 Q2 · 发布",
    issuer: "网信办",
    kind: "issued",
    note: "4 条冲突 · 已完成整改 3 条",
  },
  {
    id: "t-4",
    date: "2026-03-15",
    title: "《个保法》实施细则 · 整改完成 3/4",
    issuer: "内部 · 合规办",
    kind: "resolved",
    note: "剩余 1 条追 CAC 申报",
  },
  {
    id: "t-5",
    date: "2026-02-15",
    title: "《征信业务管理办法》修正通知 · 生效",
    issuer: "人行",
    kind: "effective",
    note: "2 条冲突 · 已处置",
  },
];

const PIPELINE: PipelineStep[] = [
  { id: "p-1", label: "政策解析 · 78 条款", status: "done", note: "NLP 提取 · 人工抽查 8 条" },
  { id: "p-2", label: "业务矩阵加载", status: "done", note: "4 份制度 · 覆盖率 81-96%" },
  { id: "p-3", label: "条款级冲突扫描", status: "done", note: "6×4=24 cell · 11 条冲突" },
  { id: "p-4", label: "严重性分级", status: "done", note: "block 4 · warn 5 · info 2" },
  { id: "p-5", label: "整改建议生成", status: "done", note: "11 条建议 · 含截止日期" },
  { id: "p-6", label: "工单派发 · 跨部门", status: "active", note: "已派 3 · 在途 4 · 待派 4" },
];

const CONVERSATION: ConversationMessage[] = [
  {
    id: "cp-msg-1",
    at: "14 分钟前",
    kind: "system-event",
    content: "合规扫描触发 · 事件：《消费金融公司管理办法》修订版 2026-04-08 发布 · 2026-06-01 生效",
  },
  {
    id: "cp-msg-2",
    at: "14 分钟前",
    kind: "ai-question",
    content: "新规 78 条 · 对标我们的 4 份内部制度，扫出 11 条冲突（严重 4 · 警告 5 · 提示 2）。先重点看严重档的 4 条？还是按制度归属拆开看？",
  },
  {
    id: "cp-msg-3",
    at: "12 分钟前",
    kind: "user-reply",
    content: "先严重档 4 条 · 尤其利率上限那条 · 看下改造成本和截止节奏",
  },
  {
    id: "cp-msg-4",
    at: "10 分钟前",
    kind: "ai-thinking",
    content: "拆解 4 条 block 冲突 · 评估改造路径 · 对齐新规生效节奏",
    thinking: {
      steps: [
        {
          label: "4 条 block 冲突逐条看",
          evidences: [
            "CF-1 信用卡章程 §4.3 · 违约金阶梯披露缺失",
            "CF-2 消费贷办法 · 24% 利率上限 > 新规 23.9%",
            "CF-3 催收规程 · 通讯录全量催收不合规",
            "CF-4 合作方标准 · 缺 5 年业绩 + 最终受益人穿透",
          ],
        },
        {
          label: "改造路径与成本估算",
          evidences: [
            "CF-2 重定价引擎切阈值：T+10 工作日，影响新合同 · 存量重定价波次",
            "CF-3 催收系统字段下线 + 紧急联系人重授权：T+3 周 · 法务需配合隐私政策更新",
            "CF-1 章程排版模板调整 + 存量合同增补附件：T+4 周 · 需董事会审议",
            "CF-4 准入流程改造 + 已签约合作方补尽调：T+12 周 · 合作方配合成本高",
          ],
        },
        {
          label: "生效节奏对齐",
          evidences: [
            "新规 2026-06-01 生效 · 距今 41 天",
            "CF-1/2/3 建议在 2026-05-15 前落地（留 16 天缓冲）",
            "CF-4 拆两期：新准入 T+4 周、存量尽调 6-9 月完成",
          ],
        },
      ],
    },
  },
  {
    id: "cp-msg-5",
    at: "6 分钟前",
    kind: "ai-response",
    content:
      "4 条严重档均可在新规生效前落地（CF-4 存量部分延后）· 风险敞口最大的是 CF-2 利率上限（每日新发合同 1800 笔涉及），建议优先拉齐重定价引擎。",
    fieldRef: "Conflicts · block tier",
    sectionDiff: {
      sectionAnchor: "Priority queue · Phase-1 by 2026-05-15",
      after: "CF-1 / CF-2 / CF-3 三条工单已派；CF-4 拆 Phase-2",
    },
  },
  {
    id: "cp-msg-6",
    at: "4 分钟前",
    kind: "ai-question",
    content: "是否按「CF-1/2/3 → 2026-05-15 · CF-4 → 2026-08-31」两阶段派工单？同步给合规办、法务、信用卡中心、催收中心、合作方管理部。",
  },
  {
    id: "cp-msg-7",
    at: "2 分钟前",
    kind: "user-command",
    content: "/dispatch 两阶段派工 · 合规办 owner · 我本周三要首次复核进度",
  },
  {
    id: "cp-msg-8",
    at: "刚刚",
    kind: "system-event",
    content: "工单已派发：CF-1/2/3 截止 2026-05-15 · CF-4 拆两期 · 本周三 2026-04-24 第一次进度复核会已生成",
  },
];

const RECENT: ComplianceRecentSession[] = [
  { id: "cpr-1", policy: "消费金融公司管理办法（当前）", updated: "刚刚", conflicts: 11, resolved: 3 },
  { id: "cpr-2", policy: "个保法实施细则 2026 Q2", updated: "2 天前", conflicts: 4, resolved: 3 },
  { id: "cpr-3", policy: "征信业务管理办法修正", updated: "2 周前", conflicts: 2, resolved: 2 },
  { id: "cpr-4", policy: "反洗钱法司法解释 v3", updated: "扫描中", conflicts: 0, resolved: 0 },
];

export const COMPLIANCE_SESSION: ComplianceSession = {
  id: "cpr-1",
  objective: "《消费金融公司管理办法》修订版 · 条款冲突扫描",
  stage: "已扫 · 工单派发中",
  updated: "刚刚",
  query: QUERY,
  policies: POLICIES,
  docs: DOCS,
  pipeline: PIPELINE,
  matrix: MATRIX,
  clauses: CLAUSES,
  conflicts: CONFLICTS,
  funnel: FUNNEL,
  timeline: TIMELINE,
  conversation: CONVERSATION,
  qcCounts: { block: 4, warn: 5, info: 2 },
  recentSessions: RECENT,
};
