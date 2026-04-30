/**
 * Agent4 alert · Multi-session 4-gate canon (worker-A4-alert · 2026-04-29)
 *
 * 取代单 const `ALERT_SESSION` (web/src/lib/mock/agent-alert-session.ts) ·
 * 4 gate (selectedSessionId / liveData / started / selectedClientId) 在
 * AlertWorkspace.tsx 直 lookup ALERT_MOCK_SESSIONS_MAP[selectedSessionId].
 *
 * 反 5 原则 #2 难度分层 (3 sessions):
 *   sess_baseline_100        · 简单 · 在贷 100 户 (常态周度)
 *   sess_manuf_policy_event  · 中等 · 制造业 + 政策升级 (Agent5 政策事件交叉)
 *   sess_judicial_news_dual  · 困难 · 司法+舆情双路命中
 *
 * 反 5 原则 #5 环境边界: fixture 不含 difficulty / tier 答案字段 ·
 * Agent 自己算 (HitList + RiskLevel mapping by scan_engine).
 *
 * V2 fix (cat 5 grade 命名 · per A6 schema agent-handoff-schemas.md:421-422):
 *   - frontend mock canon = `tier` ("red" | "yellow" | "green")  · 本文件
 *   - 后端 export = `risk_level` ("high" | "medium" | "low")  · 不同 domain · 不混
 *   - Agent3 runtime = `risk_grade` (字母 / 中文)            · 不同 domain · 不混
 *   - V1 误把 frontend 改成 risk_level (违 A6 schema) · V2 revert 回 tier
 *   - HeatCell.level (热力 intensity ramp 0..4) NOT touched · 与 grade 同名不同义
 *   - Backend SSE done envelope 也 emit `tier` (matches frontend canon) ·
 *     normalizeAlertSession 仍兼容 risk_level / level / grade input fallback
 *
 * Backend SSE done envelope 通过 normalizeAlertSession 注入到 liveData ·
 * 形态对齐 §3 of docs/audit/A4-alert-draft.md.
 */

import type { ConversationMessage } from "./agent-report-session";
export type { ConversationMessage };

export const ALERT_GLOBAL_STATS = {
  weeklyProcessed: "3,200",
  redRate: "4.1%",
  avgDuration: "6.5 分钟",
} as const;

/* ── 类型 ─────────────────────────────────────────────── */

export type AlertQuery = {
  id: string;
  objective: string;
  poolLabel: string;
  poolSize: number;
  windowLabel: string;
  ruleVersion: string;
  triggerSource: string;
  updated: string;
};

export type AlertRule = {
  id: string;
  code: string;
  label: string;
  category: "external" | "internal" | "cross";
  severity: "high" | "mid" | "low";
  hit: number;
  enabled: boolean;
};

export type AlertPipelineStep = {
  id: string;
  label: string;
  status: "done" | "active" | "pending";
  note?: string;
};

export type IndustryDistribution = {
  industry: string;
  red: number;
  yellow: number;
  green: number;
  total: number;
};

/** 热力 intensity ramp 0..4 · NOT 风险分级 grade · 名 level 不动. */
export type HeatCell = {
  date: string;
  count: number;
  level: 0 | 1 | 2 | 3 | 4;
};

export type ReachRate = {
  tier: "red" | "yellow" | "green";
  label: string;
  total: number;
  reached: number;
  reachedPct: number;
  channels: { phone: number; sms: number; visit: number };
};

export type TopCase = {
  id: string;
  client_id: string;
  customer: string;
  amount: string;
  tier: "red" | "yellow" | "green";
  triggers: string[];
  advice: string;
  lastUpdate: string;
};

export type AlertRecentSession = {
  id: string;
  objective: string;
  updated: string;
  pool: number;
  redCount: number;
};

export type ScanRangeOption = {
  id: string;
  label: string;
  coverage: number;
  hint?: string;
};

export type KnowledgeSource = {
  id: string;
  label: string;
  desc: string;
  status: "online" | "upgrading" | "offline";
  statusLabel: string;
};

export type ScanQueueCase = {
  id: string;
  client_id: string;
  customer: string;
  tier: "red" | "yellow";
  reason: string;
  updated: string;
};

export type SignalHeatBar = {
  id: string;
  label: string;
  score: number;
  desc?: string;
};

export type ScanSnapshot = {
  summary: string;
  warnCount: number;
  warnDelta: string;
  kbState: string;
  tiers: { tier: "red" | "yellow" | "green"; count: number; caption: string }[];
  signals: {
    id: string;
    label: string;
    desc: string;
    severity: "high" | "mid" | "low";
  }[];
  queue: ScanQueueCase[];
  heat: SignalHeatBar[];
  sources: KnowledgeSource[];
};

export type ScanStep = {
  id: string;
  text: string;
  pct: number;
};

export type AlertSession = {
  id: string;
  objective: string;
  stage: string;
  updated: string;
  scenario_key: string;
  difficulty_label: string;
  trigger_source_label: string;
  query: AlertQuery;
  rules: AlertRule[];
  pipeline: AlertPipelineStep[];
  distribution: IndustryDistribution[];
  totals: { red: number; yellow: number; green: number };
  heat: HeatCell[];
  reach: ReachRate[];
  topCases: TopCase[];
  conversation: ConversationMessage[];
  qcCounts: { block: number; warn: number; info: number };
  recentSessions: AlertRecentSession[];
  scanRange: ScanRangeOption[];
  knowledgeBaseSources: KnowledgeSource[];
  scanQueueCases: ScanQueueCase[];
  signalHeatmap: SignalHeatBar[];
  scanSteps: ScanStep[];
  scanSnapshotAfter: ScanSnapshot;
};

/* ─────────────── shared building-blocks ─────────────── */

const SCAN_STEPS: ScanStep[] = [
  { id: "st-1", text: "正在抓取外部链接", pct: 18 },
  { id: "st-2", text: "正在识别内部风险信号", pct: 43 },
  { id: "st-3", text: "正在分析客户流水", pct: 71 },
  { id: "st-4", text: "正在合成风险分级", pct: 93 },
  { id: "st-5", text: "扫描完成", pct: 100 },
];

const SCAN_RANGE_BASE: ScanRangeOption[] = [
  { id: "sr-all", label: "全部客户", coverage: 100, hint: "在贷客户池 · 对公 + 普惠" },
  { id: "sr-key", label: "重点客户", coverage: 36, hint: "额度 ≥ 500 万 + 主办行" },
  { id: "sr-mfg", label: "制造业", coverage: 28, hint: "行业专项扫描" },
  { id: "sr-retail", label: "零售客群", coverage: 22, hint: "批发零售 + 餐饮住宿" },
];

function makeHeatStream(seed: number[], startDate: string, days: number): HeatCell[] {
  const start = new Date(startDate);
  return Array.from({ length: days }, (_, i) => {
    const d = new Date(start.getTime() + i * 86400000);
    const iso = d.toISOString().slice(0, 10);
    const count = seed[i % seed.length] ?? 0;
    const level = (count >= 18 ? 4 : count >= 12 ? 3 : count >= 7 ? 2 : count >= 3 ? 1 : 0) as
      0 | 1 | 2 | 3 | 4;
    return { date: iso, count, level };
  });
}

/* ===============================================================
 * Session 1 · sess_baseline_100 · 简单 · 在贷 100 户 (常态周度)
 * =============================================================== */

const S1_QUERY: AlertQuery = {
  id: "al-baseline-100",
  objective: "2026-04-21 周度贷中预警扫描（常态批次）",
  poolLabel: "在贷客户池（100 户 · 对公 + 普惠）",
  poolSize: 100,
  windowLabel: "近 30 天行为 + 外部信号",
  ruleVersion: "v3.1.4",
  triggerSource: "央行征信批次更新（常态周度）",
  updated: "2 分钟前",
};

const S1_RULES: AlertRule[] = [
  { id: "ar-1", code: "EXT-LEGAL-01", label: "新增司法/行政处罚", category: "external", severity: "high", hit: 1, enabled: true },
  { id: "ar-2", code: "EXT-CREDIT-02", label: "征信新增 M3+ 逾期", category: "external", severity: "high", hit: 1, enabled: true },
  { id: "ar-3", code: "EXT-BIZ-03", label: "工商变更（股东/地址/经营范围）", category: "external", severity: "mid", hit: 3, enabled: true },
  { id: "ar-4", code: "EXT-TAX-04", label: "税务评级下调 ≥ 1 档", category: "external", severity: "mid", hit: 0, enabled: true },
  { id: "ar-5", code: "INT-FLOW-01", label: "账户日均流水环比 ↓ ≥ 40%", category: "internal", severity: "high", hit: 2, enabled: true },
  { id: "ar-6", code: "INT-UTIL-02", label: "信用卡额度使用率 ≥ 90% 持续 7 天", category: "internal", severity: "mid", hit: 4, enabled: true },
  { id: "ar-7", code: "INT-REPAY-03", label: "还款日提前赎回 ≥ 80% 资金", category: "internal", severity: "low", hit: 2, enabled: true },
  { id: "ar-8", code: "INT-CONC-04", label: "关联账户向同一对手方集中转出", category: "internal", severity: "mid", hit: 1, enabled: true },
  { id: "ar-9", code: "CRX-DUAL-01", label: "双路命中（外部 + 内部 同客户）", category: "cross", severity: "high", hit: 2, enabled: true },
  { id: "ar-10", code: "CRX-BIZ-02", label: "工商变更 + 流水骤降", category: "cross", severity: "high", hit: 0, enabled: true },
  { id: "ar-11", code: "CRX-LEGAL-03", label: "被执行 + 还款延迟", category: "cross", severity: "high", hit: 0, enabled: true },
  { id: "ar-12", code: "INT-COLLAT-05", label: "抵押物价值下跌 ≥ 15%", category: "internal", severity: "mid", hit: 0, enabled: false },
];

const S1_PIPELINE: AlertPipelineStep[] = [
  { id: "ap-1", label: "事件触发 · 外部信号", status: "done", note: "央行征信批次（常态）" },
  { id: "ap-2", label: "在贷客户池拉取", status: "done", note: "对公 42 · 普惠 58 · 合计 100" },
  { id: "ap-3", label: "规则批量扫描", status: "done", note: "12 条规则 · 11 启用 · 16 命中" },
  { id: "ap-4", label: "双路交叉 · 红档合成", status: "done", note: "红 5 · 黄 15 · 绿 80" },
  { id: "ap-5", label: "处置建议生成", status: "done", note: "按档位分配触达策略" },
  { id: "ap-6", label: "触达任务下发", status: "active", note: "已派 8 · 在途 12" },
];

const S1_DISTRIBUTION: IndustryDistribution[] = [
  { industry: "批发零售", red: 1, yellow: 4, green: 22, total: 27 },
  { industry: "制造业", red: 2, yellow: 5, green: 20, total: 27 },
  { industry: "建筑建材", red: 1, yellow: 2, green: 13, total: 16 },
  { industry: "餐饮住宿", red: 0, yellow: 1, green: 8, total: 9 },
  { industry: "信息服务", red: 0, yellow: 1, green: 11, total: 12 },
  { industry: "其他", red: 1, yellow: 2, green: 6, total: 9 },
];

const S1_HEAT: HeatCell[] = makeHeatStream(
  [1, 2, 0, 1, 3, 2, 1, 0, 2, 4, 3, 2, 1, 2, 3, 5, 4, 2, 1, 0, 1, 3, 4, 5, 6, 4, 2, 3, 5, 7],
  "2026-03-23",
  30,
);

const S1_REACH: ReachRate[] = [
  { tier: "red", label: "红档 · 立即触达", total: 5, reached: 5, reachedPct: 100, channels: { phone: 5, sms: 5, visit: 2 } },
  { tier: "yellow", label: "黄档 · 本周触达", total: 15, reached: 9, reachedPct: 60, channels: { phone: 6, sms: 15, visit: 0 } },
  { tier: "green", label: "绿档 · 观察", total: 80, reached: 80, reachedPct: 100, channels: { phone: 0, sms: 80, visit: 0 } },
];

const S1_TOP: TopCase[] = [
  { id: "tc-1", client_id: "CL-100-001", customer: "苏州金鼎电子", amount: "850 万", tier: "red", triggers: ["征信新增 M3+ 1 笔", "近 14 天流水 ↓ 47%"], advice: "电话 + 现场 · 评估补充担保", lastUpdate: "12 分钟前" },
  { id: "tc-2", client_id: "CL-100-002", customer: "无锡安固塑业", amount: "620 万", tier: "red", triggers: ["新增被执行 86 万"], advice: "限额冻结 · 律师函", lastUpdate: "30 分钟前" },
  { id: "tc-3", client_id: "CL-100-003", customer: "南京汇润商贸", amount: "480 万", tier: "red", triggers: ["税务降级 + 流水 ↓ 41%"], advice: "现场走访 · 重新评估", lastUpdate: "1 小时前" },
  { id: "tc-4", client_id: "CL-100-004", customer: "常州江源建材", amount: "320 万", tier: "yellow", triggers: ["卡额度使用率 92% 持续 8 天"], advice: "电话回访 · 评估还款压力", lastUpdate: "2 小时前" },
  { id: "tc-5", client_id: "CL-100-005", customer: "镇江盛达机械", amount: "260 万", tier: "yellow", triggers: ["流水 ↓ 41%"], advice: "短信提醒 · 下月重扫", lastUpdate: "3 小时前" },
];

const S1_QUEUE: ScanQueueCase[] = [
  { id: "sq-1", client_id: "CL-100-001", customer: "苏州金鼎电子", tier: "red", reason: "征信 M3+ + 流水 ↓ 47%", updated: "12 分钟前" },
  { id: "sq-2", client_id: "CL-100-002", customer: "无锡安固塑业", tier: "red", reason: "被执行 86 万", updated: "30 分钟前" },
  { id: "sq-3", client_id: "CL-100-003", customer: "南京汇润商贸", tier: "red", reason: "税务降级 + 流水 ↓ 41%", updated: "1 小时前" },
  { id: "sq-4", client_id: "CL-100-004", customer: "常州江源建材", tier: "yellow", reason: "卡额度使用率 92% 持续 8 天", updated: "2 小时前" },
  { id: "sq-5", client_id: "CL-100-005", customer: "镇江盛达机械", tier: "yellow", reason: "流水 ↓ 41%", updated: "3 小时前" },
];

const S1_HEAT_BARS: SignalHeatBar[] = [
  { id: "sh-legal", label: "外部司法命中", score: 38, desc: "1 户客户出现被执行" },
  { id: "sh-flow", label: "流水骤降", score: 52, desc: "近 30 日 2 户回款下降超 40%" },
  { id: "sh-public", label: "舆情负面", score: 24, desc: "无显著负面舆情" },
  { id: "sh-guarantee", label: "担保链扩散", score: 18, desc: "担保链平稳" },
  { id: "sh-internal", label: "内部名单交叉", score: 31, desc: "审批备注 4 户多点联动" },
];

const S1_KB_SOURCES: KnowledgeSource[] = [
  { id: "ks-ext-news", label: "外部舆情源", desc: "新闻、公告、公开媒体链接扫描", status: "online", statusLabel: "在线" },
  { id: "ks-judicial", label: "司法与处罚链接", desc: "诉讼、被执行、行政处罚命中", status: "online", statusLabel: "在线" },
  { id: "ks-int-rule", label: "内部风险信号", desc: "逾期苗头、名单规则、审批备注联动", status: "online", statusLabel: "在线" },
  { id: "ks-flow", label: "流水识别模型", desc: "异常波动、断流、回款周期识别", status: "online", statusLabel: "在线" },
  { id: "ks-guarantee", label: "担保链关联库", desc: "关联担保、互保圈、上下游传导", status: "online", statusLabel: "在线" },
  { id: "ks-industry", label: "行业黑白名单", desc: "高压行业清单、重点观察名录", status: "online", statusLabel: "在线" },
];

const S1_CONVERSATION: ConversationMessage[] = [
  { id: "al-msg-1", at: "8 分钟前", kind: "system-event", content: "预警扫描触发 · 来源：央行征信批次更新（常态周度）· 在贷池 100 · 规则 v3.1.4" },
  { id: "al-msg-2", at: "8 分钟前", kind: "ai-question", content: "本次扫描命中 16 条 · 双路交叉出红档 5 户。要不要按「红档→48h 现场、黄档→本周电话、绿档→观察」的默认触达分配？" },
  { id: "al-msg-3", at: "6 分钟前", kind: "user-reply", content: "先按默认配 · 把红档明细推一份给我看" },
  { id: "al-msg-4", at: "5 分钟前", kind: "ai-response", content: "5 户红档明细见右栏「触达率」Tab · 平均额度 530 万 · 都已纳入 48h 触达任务。", fieldRef: "TopCases · 红档" },
  { id: "al-msg-5", at: "刚刚", kind: "system-event", content: "5 张红档触达工单已下发 · 截止 48h" },
];

const S1_RECENT: AlertRecentSession[] = [
  { id: "alr-1", objective: "2026-04-21 周度扫描（当前 · 常态）", updated: "刚刚", pool: 100, redCount: 5 },
  { id: "alr-2", objective: "2026-04-14 周度扫描", updated: "7 天前", pool: 98, redCount: 3 },
  { id: "alr-3", objective: "2026-04-07 周度扫描", updated: "14 天前", pool: 102, redCount: 4 },
];

const SESSION_BASELINE_100: AlertSession = {
  id: "sess_baseline_100",
  scenario_key: "baseline_100",
  difficulty_label: "简单 · 常态批次",
  trigger_source_label: "央行征信批次（周度）",
  objective: S1_QUERY.objective,
  stage: "已出榜 · 触达任务下发中",
  updated: "刚刚",
  query: S1_QUERY,
  rules: S1_RULES,
  pipeline: S1_PIPELINE,
  distribution: S1_DISTRIBUTION,
  totals: { red: 5, yellow: 15, green: 80 },
  heat: S1_HEAT,
  reach: S1_REACH,
  topCases: S1_TOP,
  conversation: S1_CONVERSATION,
  qcCounts: { block: 0, warn: 1, info: 3 },
  recentSessions: S1_RECENT,
  scanRange: SCAN_RANGE_BASE,
  knowledgeBaseSources: S1_KB_SOURCES,
  scanQueueCases: S1_QUEUE,
  signalHeatmap: S1_HEAT_BARS,
  scanSteps: SCAN_STEPS,
  scanSnapshotAfter: {
    summary: "常态扫描 · 5 户红档已分配触达 · 全池整体平稳。",
    warnCount: 5,
    warnDelta: "较扫描前 +1",
    kbState: "6 项联机中",
    tiers: [
      { tier: "red", count: 5, caption: "强信号双路命中" },
      { tier: "yellow", count: 15, caption: "弱风险组合持续" },
      { tier: "green", count: 80, caption: "信号已缓和" },
    ],
    signals: [
      { id: "sg-1", label: "司法+流水双击穿", desc: "1 户客户被执行 + 流水骤降", severity: "high" },
      { id: "sg-2", label: "回款周期拉长", desc: "3 户账期拉长", severity: "mid" },
    ],
    queue: S1_QUEUE,
    heat: S1_HEAT_BARS,
    sources: S1_KB_SOURCES,
  },
};

/* ===============================================================
 * Session 2 · sess_manuf_policy_event · 中等 · 制造业 + 政策升级
 * =============================================================== */

const S2_QUERY: AlertQuery = {
  id: "al-manuf-policy",
  objective: "2026-04-22 制造业政策事件触发扫描",
  poolLabel: "在贷客户池（750 户 · 制造业占 60%）",
  poolSize: 750,
  windowLabel: "近 60 天行为 + 政策事件",
  ruleVersion: "v3.1.5",
  triggerSource: "国务院《制造业绿色低碳转型指导意见》(2026-04-19) · Agent5 政策事件交叉",
  updated: "1 小时前",
};

const S2_RULES: AlertRule[] = [
  { id: "ar-1", code: "EXT-POLICY-01", label: "政策准入门槛升级（行业 KPI）", category: "external", severity: "high", hit: 18, enabled: true },
  { id: "ar-2", code: "EXT-LEGAL-01", label: "新增司法/行政处罚", category: "external", severity: "high", hit: 7, enabled: true },
  { id: "ar-3", code: "EXT-BIZ-03", label: "工商变更（经营范围）", category: "external", severity: "mid", hit: 12, enabled: true },
  { id: "ar-4", code: "EXT-TAX-04", label: "税务评级下调 ≥ 1 档", category: "external", severity: "mid", hit: 6, enabled: true },
  { id: "ar-5", code: "INT-FLOW-01", label: "账户日均流水环比 ↓ ≥ 40%", category: "internal", severity: "high", hit: 14, enabled: true },
  { id: "ar-6", code: "INT-UTIL-02", label: "信用卡额度使用率 ≥ 90%", category: "internal", severity: "mid", hit: 22, enabled: true },
  { id: "ar-7", code: "INT-REPAY-03", label: "还款日提前赎回 ≥ 80% 资金", category: "internal", severity: "low", hit: 8, enabled: true },
  { id: "ar-8", code: "CRX-POLICY-FLOW", label: "政策升级 + 流水骤降（同客户）", category: "cross", severity: "high", hit: 11, enabled: true },
  { id: "ar-9", code: "CRX-DUAL-01", label: "双路命中（外部 + 内部）", category: "cross", severity: "high", hit: 9, enabled: true },
  { id: "ar-10", code: "CRX-BIZ-02", label: "工商变更 + 流水骤降", category: "cross", severity: "high", hit: 4, enabled: true },
  { id: "ar-11", code: "CRX-LEGAL-03", label: "被执行 + 还款延迟", category: "cross", severity: "high", hit: 2, enabled: true },
  { id: "ar-12", code: "INT-COLLAT-05", label: "抵押物价值下跌 ≥ 15%", category: "internal", severity: "mid", hit: 5, enabled: true },
];

const S2_PIPELINE: AlertPipelineStep[] = [
  { id: "ap-1", label: "事件触发 · 政策升级", status: "done", note: "Agent5 政策矩阵命中" },
  { id: "ap-2", label: "在贷客户池筛选（制造业）", status: "done", note: "对公 312 · 普惠 138 · 合计 450 制造客户" },
  { id: "ap-3", label: "规则批量扫描", status: "done", note: "12 条规则 · 12 启用 · 118 命中" },
  { id: "ap-4", label: "双路交叉 · 红档合成", status: "done", note: "红 18 · 黄 52 · 绿 680" },
  { id: "ap-5", label: "处置建议生成", status: "done", note: "政策影响优先 · 70 户提示" },
  { id: "ap-6", label: "触达任务下发", status: "active", note: "已派 22 · 在途 48" },
];

const S2_DISTRIBUTION: IndustryDistribution[] = [
  { industry: "制造业", red: 15, yellow: 36, green: 399, total: 450 },
  { industry: "建筑建材", red: 1, yellow: 6, green: 60, total: 67 },
  { industry: "批发零售", red: 1, yellow: 4, green: 75, total: 80 },
  { industry: "餐饮住宿", red: 0, yellow: 2, green: 30, total: 32 },
  { industry: "信息服务", red: 1, yellow: 2, green: 70, total: 73 },
  { industry: "其他", red: 0, yellow: 2, green: 46, total: 48 },
];

const S2_HEAT: HeatCell[] = makeHeatStream(
  [3, 4, 5, 4, 5, 6, 7, 6, 8, 7, 9, 11, 14, 18, 22, 19, 17, 14, 12, 10, 9, 8, 7, 6, 5, 4, 3, 4, 5, 6],
  "2026-03-24",
  30,
);

const S2_REACH: ReachRate[] = [
  { tier: "red", label: "红档 · 立即触达", total: 18, reached: 16, reachedPct: 88.9, channels: { phone: 14, sms: 18, visit: 6 } },
  { tier: "yellow", label: "黄档 · 本周触达", total: 52, reached: 28, reachedPct: 53.8, channels: { phone: 18, sms: 52, visit: 0 } },
  { tier: "green", label: "绿档 · 观察", total: 680, reached: 680, reachedPct: 100, channels: { phone: 0, sms: 680, visit: 0 } },
];

const S2_TOP: TopCase[] = [
  { id: "tc-1", client_id: "CL-MFG-201", customer: "盐城绿能科技", amount: "1800 万", tier: "red", triggers: ["政策升级未达标 · 准入失格", "近 30 天流水 ↓ 58%"], advice: "立即停增 · 评估退出路径", lastUpdate: "8 分钟前" },
  { id: "tc-2", client_id: "CL-MFG-202", customer: "扬州精铸机械", amount: "1450 万", tier: "red", triggers: ["环保限产通知", "工商经营范围变更", "对公流水断流 7 天"], advice: "现场核查 · 启动风险分类", lastUpdate: "22 分钟前" },
  { id: "tc-3", client_id: "CL-MFG-203", customer: "泰州瑞通模具", amount: "920 万", tier: "red", triggers: ["税务降级 A→B", "回款周期 +28 天"], advice: "限额冻结 · 现场谈判", lastUpdate: "45 分钟前" },
  { id: "tc-4", client_id: "CL-MFG-204", customer: "南通启航重工", amount: "780 万", tier: "yellow", triggers: ["卡额度使用率 91% 持续 12 天", "政策升级影响"], advice: "电话 + 政策说明", lastUpdate: "1 小时前" },
  { id: "tc-5", client_id: "CL-MFG-205", customer: "徐州恒达精工", amount: "560 万", tier: "yellow", triggers: ["流水 ↓ 38%"], advice: "短信提醒 · 重点观察", lastUpdate: "2 小时前" },
];

const S2_QUEUE: ScanQueueCase[] = [
  { id: "sq-1", client_id: "CL-MFG-201", customer: "盐城绿能科技", tier: "red", reason: "政策升级未达标 + 流水 ↓ 58%", updated: "8 分钟前" },
  { id: "sq-2", client_id: "CL-MFG-202", customer: "扬州精铸机械", tier: "red", reason: "环保限产 + 流水断流", updated: "22 分钟前" },
  { id: "sq-3", client_id: "CL-MFG-203", customer: "泰州瑞通模具", tier: "red", reason: "税务降级 + 回款 +28 天", updated: "45 分钟前" },
  { id: "sq-4", client_id: "CL-MFG-204", customer: "南通启航重工", tier: "yellow", reason: "卡额度 91% + 政策影响", updated: "1 小时前" },
  { id: "sq-5", client_id: "CL-MFG-205", customer: "徐州恒达精工", tier: "yellow", reason: "流水 ↓ 38%", updated: "2 小时前" },
];

const S2_HEAT_BARS: SignalHeatBar[] = [
  { id: "sh-policy", label: "政策准入失格", score: 88, desc: "18 户客户在新政策门槛之下" },
  { id: "sh-flow", label: "流水骤降", score: 71, desc: "14 户对公流水环比下滑超 40%" },
  { id: "sh-legal", label: "外部司法命中", score: 56, desc: "7 户客户出现处罚动态" },
  { id: "sh-guarantee", label: "担保链扩散", score: 49, desc: "上游环保限产传导" },
  { id: "sh-internal", label: "内部名单交叉", score: 38, desc: "审批备注与名单规则联动" },
];

const S2_KB_SOURCES: KnowledgeSource[] = [
  { id: "ks-ext-news", label: "外部舆情源", desc: "新闻、公告、公开媒体链接扫描", status: "online", statusLabel: "在线" },
  { id: "ks-policy", label: "政策矩阵库（Agent5 共享）", desc: "国务院 / 行业主管部门政策事件", status: "online", statusLabel: "在线" },
  { id: "ks-judicial", label: "司法与处罚链接", desc: "诉讼、被执行、行政处罚命中", status: "online", statusLabel: "在线" },
  { id: "ks-int-rule", label: "内部风险信号", desc: "逾期苗头、名单规则、审批备注联动", status: "online", statusLabel: "在线" },
  { id: "ks-flow", label: "流水识别模型", desc: "异常波动、断流、回款周期识别", status: "upgrading", statusLabel: "升级" },
  { id: "ks-industry", label: "行业黑白名单", desc: "高压行业清单", status: "online", statusLabel: "在线" },
];

const S2_CONVERSATION: ConversationMessage[] = [
  { id: "al-msg-1", at: "1 小时前", kind: "system-event", content: "预警扫描触发 · 来源：国务院《制造业绿色低碳转型指导意见》· Agent5 政策事件交叉 · 在贷池 750 · 规则 v3.1.5" },
  { id: "al-msg-2", at: "1 小时前", kind: "ai-question", content: "政策升级在制造业池命中 18 户红档 · 主要触发是「准入门槛失格 + 流水骤降」· 要不要按行业切片优先看？" },
  { id: "al-msg-3", at: "55 分钟前", kind: "user-reply", content: "看 top 5 红档 · 重点关注江苏制造业" },
  { id: "al-msg-4", at: "50 分钟前", kind: "ai-thinking", content: "拉取 top 5 红档明细 · 按江苏分行切片 · 校准触达优先级", thinking: { steps: [
    { label: "红档明细", evidences: ["盐城绿能科技 1800 万 · 准入失格 + 流水 ↓ 58%", "扬州精铸机械 1450 万 · 环保限产 + 流水断流", "泰州瑞通模具 920 万 · 税务降级 + 回款 +28 天"] },
    { label: "江苏制造业集中度", evidences: ["江苏分行 制造客户 312 · 红 14 (4.5%)", "近 60 天政策传导热力 +180%", "交叉规则 CRX-POLICY-FLOW 江苏命中 11 户"] },
  ] } },
  { id: "al-msg-5", at: "45 分钟前", kind: "ai-response", content: "Top 5 红档详情见右栏「触达率」· 江苏制造业建议立即升级 · 由分行长直触。", fieldRef: "Distribution · 制造业" },
  { id: "al-msg-6", at: "10 分钟前", kind: "user-command", content: "/dispatch 江苏制造业红档 14 户 · 分行长直触 · 48h 截止" },
  { id: "al-msg-7", at: "刚刚", kind: "system-event", content: "14 张触达工单已下发到江苏分行长 · 抄送风险部" },
];

const S2_RECENT: AlertRecentSession[] = [
  { id: "alr-1", objective: "2026-04-22 制造业政策事件扫描（当前）", updated: "刚刚", pool: 750, redCount: 18 },
  { id: "alr-2", objective: "2026-04-15 制造业月度扫描", updated: "7 天前", pool: 743, redCount: 9 },
  { id: "alr-3", objective: "2026-04-08 行业专项扫描", updated: "14 天前", pool: 749, redCount: 7 },
];

const SESSION_MANUF_POLICY_EVENT: AlertSession = {
  id: "sess_manuf_policy_event",
  scenario_key: "manuf_policy_event",
  difficulty_label: "中等 · 政策事件交叉",
  trigger_source_label: "国务院制造业政策升级（Agent5 交叉）",
  objective: S2_QUERY.objective,
  stage: "已出榜 · 江苏分行触达进行中",
  updated: "刚刚",
  query: S2_QUERY,
  rules: S2_RULES,
  pipeline: S2_PIPELINE,
  distribution: S2_DISTRIBUTION,
  totals: { red: 18, yellow: 52, green: 680 },
  heat: S2_HEAT,
  reach: S2_REACH,
  topCases: S2_TOP,
  conversation: S2_CONVERSATION,
  qcCounts: { block: 0, warn: 3, info: 5 },
  recentSessions: S2_RECENT,
  scanRange: [
    { id: "sr-all", label: "全部客户", coverage: 750, hint: "在贷客户池" },
    { id: "sr-mfg", label: "制造业", coverage: 450, hint: "政策影响行业" },
    { id: "sr-key", label: "重点客户", coverage: 220, hint: "额度 ≥ 500 万" },
    { id: "sr-jiangsu", label: "江苏分行", coverage: 312, hint: "区域专项" },
  ],
  knowledgeBaseSources: S2_KB_SOURCES,
  scanQueueCases: S2_QUEUE,
  signalHeatmap: S2_HEAT_BARS,
  scanSteps: SCAN_STEPS,
  scanSnapshotAfter: {
    summary: "政策升级在制造业 750 户中命中 18 红档 · 江苏分行受冲击最大 · 建议立即触达。",
    warnCount: 18,
    warnDelta: "较上周 +9",
    kbState: "5 项联机中 · 1 项升级",
    tiers: [
      { tier: "red", count: 18, caption: "政策准入失格 + 双路命中" },
      { tier: "yellow", count: 52, caption: "政策影响弱信号组合" },
      { tier: "green", count: 680, caption: "未触发政策门槛" },
    ],
    signals: [
      { id: "sg-1", label: "政策准入失格", desc: "18 户在新政策门槛之下", severity: "high" },
      { id: "sg-2", label: "环保限产传导", desc: "上游 6 户进入限产名单", severity: "high" },
      { id: "sg-3", label: "回款周期拉长", desc: "11 户账期拉长超 25 天", severity: "mid" },
    ],
    queue: S2_QUEUE,
    heat: S2_HEAT_BARS,
    sources: S2_KB_SOURCES,
  },
};

/* ===============================================================
 * Session 3 · sess_judicial_news_dual · 困难 · 司法+舆情双路命中
 * =============================================================== */

const S3_QUERY: AlertQuery = {
  id: "al-judicial-news",
  objective: "2026-04-23 司法+舆情双路命中专项扫描",
  poolLabel: "在贷客户池（200 户 · 重点客群）",
  poolSize: 200,
  windowLabel: "近 14 天行为 + 双路信号",
  ruleVersion: "v3.1.6",
  triggerSource: "区域大额司法立案爆发 + 舆情热搜（双路命中）",
  updated: "10 分钟前",
};

const S3_RULES: AlertRule[] = [
  { id: "ar-1", code: "EXT-LEGAL-01", label: "新增司法/行政处罚", category: "external", severity: "high", hit: 22, enabled: true },
  { id: "ar-2", code: "EXT-NEWS-01", label: "舆情负面热搜（≥3 平台）", category: "external", severity: "high", hit: 19, enabled: true },
  { id: "ar-3", code: "EXT-CREDIT-02", label: "征信新增 M3+ 逾期", category: "external", severity: "high", hit: 15, enabled: true },
  { id: "ar-4", code: "EXT-BIZ-03", label: "工商变更（股东/经营范围）", category: "external", severity: "mid", hit: 18, enabled: true },
  { id: "ar-5", code: "INT-FLOW-01", label: "账户日均流水环比 ↓ ≥ 40%", category: "internal", severity: "high", hit: 24, enabled: true },
  { id: "ar-6", code: "INT-CONC-04", label: "向同一对手方集中转出", category: "internal", severity: "mid", hit: 13, enabled: true },
  { id: "ar-7", code: "INT-UTIL-02", label: "信用卡额度使用率 ≥ 90%", category: "internal", severity: "mid", hit: 21, enabled: true },
  { id: "ar-8", code: "INT-REPAY-03", label: "还款日提前赎回 ≥ 80%", category: "internal", severity: "low", hit: 9, enabled: true },
  { id: "ar-9", code: "CRX-DUAL-LEGAL-NEWS", label: "双路命中（司法 + 舆情 同客户）", category: "cross", severity: "high", hit: 14, enabled: true },
  { id: "ar-10", code: "CRX-DUAL-01", label: "双路命中（外部 + 内部）", category: "cross", severity: "high", hit: 18, enabled: true },
  { id: "ar-11", code: "CRX-LEGAL-FLOW", label: "司法立案 + 流水骤降", category: "cross", severity: "high", hit: 11, enabled: true },
  { id: "ar-12", code: "CRX-NEWS-CONC", label: "舆情爆发 + 资金集中转出", category: "cross", severity: "high", hit: 7, enabled: true },
];

const S3_PIPELINE: AlertPipelineStep[] = [
  { id: "ap-1", label: "事件触发 · 司法+舆情双路", status: "done", note: "区域大额司法立案 + 舆情热搜" },
  { id: "ap-2", label: "在贷重点客户池", status: "done", note: "重点客户 200 户" },
  { id: "ap-3", label: "规则批量扫描", status: "done", note: "12 条规则 · 191 命中（含双路）" },
  { id: "ap-4", label: "双路交叉 · 红档合成", status: "done", note: "红 25 · 黄 35 · 绿 140" },
  { id: "ap-5", label: "处置建议生成", status: "done", note: "司法+舆情双路客户优先升级" },
  { id: "ap-6", label: "触达任务下发", status: "active", note: "已派 35 · 在途 25" },
];

const S3_DISTRIBUTION: IndustryDistribution[] = [
  { industry: "建筑建材", red: 8, yellow: 9, green: 23, total: 40 },
  { industry: "批发零售", red: 7, yellow: 8, green: 35, total: 50 },
  { industry: "制造业", red: 5, yellow: 7, green: 28, total: 40 },
  { industry: "餐饮住宿", red: 3, yellow: 4, green: 13, total: 20 },
  { industry: "信息服务", red: 1, yellow: 4, green: 25, total: 30 },
  { industry: "其他", red: 1, yellow: 3, green: 16, total: 20 },
];

const S3_HEAT: HeatCell[] = makeHeatStream(
  [4, 5, 6, 7, 8, 9, 12, 16, 21, 26, 24, 22, 19, 18, 16, 14, 13, 11, 9, 8, 7, 6, 5, 4, 3, 2, 3, 4, 5, 6],
  "2026-04-08",
  30,
);

const S3_REACH: ReachRate[] = [
  { tier: "red", label: "红档 · 立即触达", total: 25, reached: 23, reachedPct: 92.0, channels: { phone: 22, sms: 25, visit: 11 } },
  { tier: "yellow", label: "黄档 · 本周触达", total: 35, reached: 21, reachedPct: 60.0, channels: { phone: 18, sms: 35, visit: 0 } },
  { tier: "green", label: "绿档 · 观察", total: 140, reached: 140, reachedPct: 100, channels: { phone: 0, sms: 140, visit: 0 } },
];

const S3_TOP: TopCase[] = [
  { id: "tc-1", client_id: "CL-DUAL-301", customer: "广州瑞河商贸", amount: "2400 万", tier: "red", triggers: ["司法立案 320 万 · 已查封", "舆情热搜 5 平台联动", "对公流水 ↓ 71% (近 7 天)"], advice: "立即停贷 · 资产保全申请", lastUpdate: "5 分钟前" },
  { id: "tc-2", client_id: "CL-DUAL-302", customer: "深圳鸿祥建材", amount: "1900 万", tier: "red", triggers: ["新增被执行 480 万", "媒体曝光资金链断裂", "信用卡额度 100% + 集中转出"], advice: "立即升级风险分类 · 律师函", lastUpdate: "18 分钟前" },
  { id: "tc-3", client_id: "CL-DUAL-303", customer: "佛山联铸贸易", amount: "1280 万", tier: "red", triggers: ["征信 M3+ 2 笔", "舆情 3 平台爆负面", "回款断流 14 天"], advice: "现场谈判 · 限额冻结", lastUpdate: "32 分钟前" },
  { id: "tc-4", client_id: "CL-DUAL-304", customer: "东莞鼎华科技", amount: "950 万", tier: "red", triggers: ["对手方集中转出 75%", "工商变更 + 实控人股权质押"], advice: "立即调查关联方", lastUpdate: "1 小时前" },
  { id: "tc-5", client_id: "CL-DUAL-305", customer: "中山华业实业", amount: "780 万", tier: "yellow", triggers: ["卡额度 92% + 还款延迟 5 天"], advice: "电话回访 + 升级评估", lastUpdate: "2 小时前" },
];

const S3_QUEUE: ScanQueueCase[] = [
  { id: "sq-1", client_id: "CL-DUAL-301", customer: "广州瑞河商贸", tier: "red", reason: "司法立案 + 舆情 + 流水 ↓ 71%", updated: "5 分钟前" },
  { id: "sq-2", client_id: "CL-DUAL-302", customer: "深圳鸿祥建材", tier: "red", reason: "被执行 480 万 + 媒体曝光", updated: "18 分钟前" },
  { id: "sq-3", client_id: "CL-DUAL-303", customer: "佛山联铸贸易", tier: "red", reason: "征信 M3+ + 舆情 + 回款断流", updated: "32 分钟前" },
  { id: "sq-4", client_id: "CL-DUAL-304", customer: "东莞鼎华科技", tier: "red", reason: "对手方集中转出 75%", updated: "1 小时前" },
  { id: "sq-5", client_id: "CL-DUAL-305", customer: "中山华业实业", tier: "yellow", reason: "卡额度 92% + 还款延迟", updated: "2 小时前" },
];

const S3_HEAT_BARS: SignalHeatBar[] = [
  { id: "sh-legal", label: "外部司法命中", score: 92, desc: "22 户客户出现司法立案" },
  { id: "sh-news", label: "舆情负面热搜", score: 86, desc: "19 户客户在 ≥3 平台爆负面" },
  { id: "sh-flow", label: "流水骤降", score: 81, desc: "24 户对公流水断流或骤降" },
  { id: "sh-conc", label: "资金集中转出", score: 74, desc: "13 户向同一对手方集中转出" },
  { id: "sh-cross", label: "双路交叉命中", score: 95, desc: "司法+舆情同客户命中 14 户" },
];

const S3_KB_SOURCES: KnowledgeSource[] = [
  { id: "ks-judicial", label: "司法与处罚链接", desc: "诉讼、被执行、行政处罚命中", status: "online", statusLabel: "在线" },
  { id: "ks-news", label: "舆情多平台聚合", desc: "微博、知乎、企业头条等多源", status: "online", statusLabel: "在线" },
  { id: "ks-ext-news", label: "外部舆情源（基础）", desc: "新闻、公告、公开媒体", status: "online", statusLabel: "在线" },
  { id: "ks-flow", label: "流水识别模型", desc: "异常波动、断流、回款周期", status: "online", statusLabel: "在线" },
  { id: "ks-int-rule", label: "内部风险信号", desc: "逾期苗头、名单、审批备注", status: "online", statusLabel: "在线" },
  { id: "ks-cross", label: "跨源交叉合成", desc: "双路命中合成引擎", status: "online", statusLabel: "在线" },
];

const S3_CONVERSATION: ConversationMessage[] = [
  { id: "al-msg-1", at: "10 分钟前", kind: "system-event", content: "预警扫描触发 · 区域大额司法立案 + 舆情热搜双路命中 · 在贷重点池 200 · 规则 v3.1.6" },
  { id: "al-msg-2", at: "10 分钟前", kind: "ai-question", content: "本次扫描红档 25 户 · 其中 14 户「司法+舆情」双路命中 · 11 户「司法+流水」双路命中 · 是否立即升级？" },
  { id: "al-msg-3", at: "8 分钟前", kind: "user-reply", content: "立即升级 · 双路客户优先 · 资产保全要不要发？" },
  { id: "al-msg-4", at: "7 分钟前", kind: "ai-thinking", content: "评估资产保全条件 · 拉取 top 5 红档", thinking: { steps: [
    { label: "司法+舆情双路 14 户", evidences: ["广州瑞河商贸 2400 万 · 已查封", "深圳鸿祥建材 1900 万 · 媒体曝光", "佛山联铸贸易 1280 万 · 资金链质疑"] },
    { label: "资产保全可行性", evidences: ["8 户已具备查封先决条件 (已立案 + 财产线索清晰)", "6 户尚需补充债权证据"] },
  ] } },
  { id: "al-msg-5", at: "5 分钟前", kind: "ai-response", content: "建议：8 户立即发资产保全申请 (查封先决条件已具备) · 6 户先补债权证据再发 · 11 户「司法+流水」客户立即限额冻结。", fieldRef: "TopCases · 红档双路" },
  { id: "al-msg-6", at: "3 分钟前", kind: "user-command", content: "/dispatch 8 户资产保全 + 11 户限额冻结 · 法务部牵头 · 24h 内完成" },
  { id: "al-msg-7", at: "刚刚", kind: "system-event", content: "19 项处置工单已下发 · 法务部 + 风险部联动 · 24h 截止" },
];

const S3_RECENT: AlertRecentSession[] = [
  { id: "alr-1", objective: "2026-04-23 司法+舆情双路扫描（当前）", updated: "刚刚", pool: 200, redCount: 25 },
  { id: "alr-2", objective: "2026-04-16 重点客户专项", updated: "7 天前", pool: 198, redCount: 11 },
  { id: "alr-3", objective: "2026-04-09 月度重点扫描", updated: "14 天前", pool: 195, redCount: 9 },
];

const SESSION_JUDICIAL_NEWS_DUAL: AlertSession = {
  id: "sess_judicial_news_dual",
  scenario_key: "judicial_news_dual",
  difficulty_label: "困难 · 双路命中",
  trigger_source_label: "区域司法立案 + 舆情热搜",
  objective: S3_QUERY.objective,
  stage: "已出榜 · 资产保全 + 限额冻结进行中",
  updated: "刚刚",
  query: S3_QUERY,
  rules: S3_RULES,
  pipeline: S3_PIPELINE,
  distribution: S3_DISTRIBUTION,
  totals: { red: 25, yellow: 35, green: 140 },
  heat: S3_HEAT,
  reach: S3_REACH,
  topCases: S3_TOP,
  conversation: S3_CONVERSATION,
  qcCounts: { block: 1, warn: 4, info: 6 },
  recentSessions: S3_RECENT,
  scanRange: [
    { id: "sr-all", label: "全部重点客户", coverage: 200, hint: "在贷重点客群" },
    { id: "sr-key", label: "高额客户", coverage: 78, hint: "额度 ≥ 1000 万" },
    { id: "sr-region", label: "珠三角", coverage: 92, hint: "区域专项" },
    { id: "sr-dual", label: "双路命中候选", coverage: 36, hint: "司法+舆情或司法+流水" },
  ],
  knowledgeBaseSources: S3_KB_SOURCES,
  scanQueueCases: S3_QUEUE,
  signalHeatmap: S3_HEAT_BARS,
  scanSteps: SCAN_STEPS,
  scanSnapshotAfter: {
    summary: "司法+舆情双路在 200 户重点客群中命中 25 红档 · 14 户司法+舆情 · 11 户司法+流水 · 建议资产保全 + 限额冻结。",
    warnCount: 25,
    warnDelta: "较上周 +14",
    kbState: "6 项联机中",
    tiers: [
      { tier: "red", count: 25, caption: "司法+舆情/流水双路命中" },
      { tier: "yellow", count: 35, caption: "弱风险组合 + 单路命中" },
      { tier: "green", count: 140, caption: "未触发双路" },
    ],
    signals: [
      { id: "sg-1", label: "司法立案爆发", desc: "22 户客户出现司法立案", severity: "high" },
      { id: "sg-2", label: "舆情多平台传导", desc: "19 户客户 ≥3 平台爆负面", severity: "high" },
      { id: "sg-3", label: "资金集中转出", desc: "13 户向同对手方集中转出", severity: "high" },
    ],
    queue: S3_QUEUE,
    heat: S3_HEAT_BARS,
    sources: S3_KB_SOURCES,
  },
};

/* ─────────────── Exports ─────────────── */

export const ALERT_MOCK_SESSIONS: AlertSession[] = [
  SESSION_BASELINE_100,
  SESSION_MANUF_POLICY_EVENT,
  SESSION_JUDICIAL_NEWS_DUAL,
];

export const ALERT_MOCK_SESSIONS_MAP: Record<string, AlertSession> = {
  [SESSION_BASELINE_100.id]: SESSION_BASELINE_100,
  [SESSION_MANUF_POLICY_EVENT.id]: SESSION_MANUF_POLICY_EVENT,
  [SESSION_JUDICIAL_NEWS_DUAL.id]: SESSION_JUDICIAL_NEWS_DUAL,
};

export const ALERT_MOCK_SESSIONS_LIST: AlertRecentSession[] = ALERT_MOCK_SESSIONS.map((s) => ({
  id: s.id,
  objective: `${s.difficulty_label} · ${s.objective}`,
  updated: s.updated,
  pool: s.query.poolSize,
  redCount: s.totals.red,
}));

export const DEFAULT_SESSION_ID = SESSION_BASELINE_100.id;
