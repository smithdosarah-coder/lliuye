/**
 * Agent Alert · 单 session 对话式贷中预警 mock（2026-04-21 H4 · canon 横向迁移）
 * 业务：预警官触发扫描（事件驱动：客户行为/外部信号变化），Agent 对在贷客户池做批量多规则扫描，
 *       产出红/黄/绿三档客户榜单 + 处置建议 + 触达任务
 * 五块完整 shape：query / rules / pipeline / conversation / output(分档 stacked + 热力日历 + 触达率)
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

export type AlertSession = {
  id: string;
  objective: string;
  stage: string;
  updated: string;
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
};

/* ── 常量 ─────────────────────────────────────────────── */

const QUERY: AlertQuery = {
  id: "al-0421-batch",
  objective: "2026-04-21 · 周度贷中预警扫描（事件触发）",
  poolLabel: "在贷客户池（对公 + 普惠）",
  poolSize: 3200,
  windowLabel: "近 30 天行为 + 外部信号",
  ruleVersion: "v3.1.4",
  triggerSource: "央行征信批次更新 + 工商变更信号聚合",
  updated: "2 分钟前",
};

const RULES: AlertRule[] = [
  { id: "ar-1", code: "EXT-LEGAL-01", label: "新增司法/行政处罚", category: "external", severity: "high", hit: 18, enabled: true },
  { id: "ar-2", code: "EXT-CREDIT-02", label: "征信新增 M3+ 逾期", category: "external", severity: "high", hit: 11, enabled: true },
  { id: "ar-3", code: "EXT-BIZ-03", label: "工商变更（股东/地址/经营范围）", category: "external", severity: "mid", hit: 36, enabled: true },
  { id: "ar-4", code: "EXT-TAX-04", label: "税务评级下调 ≥ 1 档", category: "external", severity: "mid", hit: 7, enabled: true },
  { id: "ar-5", code: "INT-FLOW-01", label: "账户日均流水环比 ↓ ≥ 40%", category: "internal", severity: "high", hit: 24, enabled: true },
  { id: "ar-6", code: "INT-UTIL-02", label: "信用卡额度使用率 ≥ 90% 持续 7 天", category: "internal", severity: "mid", hit: 52, enabled: true },
  { id: "ar-7", code: "INT-REPAY-03", label: "还款日提前赎回 ≥ 80% 资金", category: "internal", severity: "low", hit: 14, enabled: true },
  { id: "ar-8", code: "INT-CONC-04", label: "关联账户向同一对手方集中转出", category: "internal", severity: "mid", hit: 9, enabled: true },
  { id: "ar-9", code: "CRX-DUAL-01", label: "双路命中（外部 + 内部 同客户）", category: "cross", severity: "high", hit: 22, enabled: true },
  { id: "ar-10", code: "CRX-BIZ-02", label: "工商变更 + 流水骤降", category: "cross", severity: "high", hit: 5, enabled: true },
  { id: "ar-11", code: "CRX-LEGAL-03", label: "被执行 + 还款延迟", category: "cross", severity: "high", hit: 3, enabled: true },
  { id: "ar-12", code: "INT-COLLAT-05", label: "抵押物价值下跌 ≥ 15%", category: "internal", severity: "mid", hit: 8, enabled: false },
];

const PIPELINE: AlertPipelineStep[] = [
  { id: "ap-1", label: "事件触发 · 外部信号", status: "done", note: "央行征信批次 + 工商变更聚合" },
  { id: "ap-2", label: "在贷客户池拉取", status: "done", note: "对公 1420 · 普惠 1780 · 合计 3200" },
  { id: "ap-3", label: "规则批量扫描", status: "done", note: "12 条规则 · 11 启用 · 209 命中" },
  { id: "ap-4", label: "双路交叉 · 红档合成", status: "done", note: "红 131 · 黄 384 · 绿 2685" },
  { id: "ap-5", label: "处置建议生成", status: "done", note: "按档位分配触达策略" },
  { id: "ap-6", label: "触达任务下发", status: "active", note: "已派 132 · 在途 83" },
];

const DISTRIBUTION: IndustryDistribution[] = [
  { industry: "批发零售", red: 38, yellow: 112, green: 680, total: 830 },
  { industry: "制造业", red: 41, yellow: 96, green: 612, total: 749 },
  { industry: "建筑建材", red: 22, yellow: 78, green: 408, total: 508 },
  { industry: "餐饮住宿", red: 14, yellow: 38, green: 266, total: 318 },
  { industry: "信息服务", red: 9, yellow: 32, green: 428, total: 469 },
  { industry: "其他", red: 7, yellow: 28, green: 291, total: 326 },
];

const HEAT: HeatCell[] = (() => {
  const base = [2, 5, 3, 4, 6, 8, 4, 3, 7, 9, 5, 4, 3, 6, 8, 11, 14, 9, 6, 4, 5, 8, 12, 16, 19, 14, 9, 11, 18, 22];
  return base.map((count, i) => {
    const day = 22 - Math.floor(i / 1); // placeholder, mapped below
    const d = new Date(2026, 2, 23 + i); // 2026-03-23 start, 30 days → to 2026-04-21
    const iso = d.toISOString().slice(0, 10);
    const level = count >= 18 ? 4 : count >= 12 ? 3 : count >= 7 ? 2 : count >= 3 ? 1 : 0;
    return { date: iso, count, level: level as 0 | 1 | 2 | 3 | 4 };
  });
})();

const REACH: ReachRate[] = [
  {
    tier: "red",
    label: "红档 · 立即触达",
    total: 131,
    reached: 119,
    reachedPct: 90.8,
    channels: { phone: 94, sms: 131, visit: 42 },
  },
  {
    tier: "yellow",
    label: "黄档 · 本周触达",
    total: 384,
    reached: 218,
    reachedPct: 56.8,
    channels: { phone: 132, sms: 384, visit: 0 },
  },
  {
    tier: "green",
    label: "绿档 · 观察",
    total: 2685,
    reached: 2685,
    reachedPct: 100,
    channels: { phone: 0, sms: 2685, visit: 0 },
  },
];

const TOP_CASES: TopCase[] = [
  {
    id: "tc-1",
    customer: "泉州联泰建材",
    amount: "1500 万",
    tier: "red",
    triggers: ["新增被执行 312 万", "近 14 天流水 ↓ 62%"],
    advice: "48h 内现场走访 + 要求补充担保",
    lastUpdate: "18 分钟前",
  },
  {
    id: "tc-2",
    customer: "厦门宏福贸易",
    amount: "900 万",
    tier: "red",
    triggers: ["征信新增 M3+ 1 笔", "股东 3 月内变更 2 次"],
    advice: "电话 + 律师函 · 启动风险分类",
    lastUpdate: "42 分钟前",
  },
  {
    id: "tc-3",
    customer: "漳州丰联机械",
    amount: "680 万",
    tier: "red",
    triggers: ["税务降级 A→B", "抵押物价值 ↓ 18%"],
    advice: "要求重新评估 + 补保证金",
    lastUpdate: "1 小时前",
  },
  {
    id: "tc-4",
    customer: "福州兴达建材",
    amount: "420 万",
    tier: "yellow",
    triggers: ["卡额度使用率 92% 持续 9 天"],
    advice: "电话回访 · 评估还款压力",
    lastUpdate: "2 小时前",
  },
  {
    id: "tc-5",
    customer: "宁德海源电子",
    amount: "260 万",
    tier: "yellow",
    triggers: ["流水 ↓ 41%", "前 3 大客户集中度 63%"],
    advice: "短信提醒 + 下月重扫",
    lastUpdate: "3 小时前",
  },
];

const CONVERSATION: ConversationMessage[] = [
  {
    id: "al-msg-1",
    at: "8 分钟前",
    kind: "system-event",
    content: "预警扫描触发 · 来源：央行征信批次更新 + 工商变更信号聚合 · 在贷池 3200 · 规则 v3.1.4",
  },
  {
    id: "al-msg-2",
    at: "8 分钟前",
    kind: "ai-question",
    content: "本次扫描命中 209 条 · 双路交叉出红档 131 户。要不要按「红档→48h 现场、黄档→本周电话、绿档→观察」的默认触达分配？还是想先看 top 红档再定？",
  },
  {
    id: "al-msg-3",
    at: "6 分钟前",
    kind: "user-reply",
    content: "先看 top 3 红档 · 建材行业近来雷多，单独拎出来",
  },
  {
    id: "al-msg-4",
    at: "5 分钟前",
    kind: "ai-thinking",
    content: "拉取 top 3 红档明细 · 按行业切片看建材集中度 · 校准触达优先级",
    thinking: {
      steps: [
        {
          label: "红档 top 3 明细",
          evidences: [
            "泉州联泰建材（1500 万）· 新增被执行 + 流水 ↓ 62%",
            "厦门宏福贸易（900 万）· 征信 M3+ + 股东频变",
            "漳州丰联机械（680 万）· 税务降级 + 抵押物贬值",
          ],
        },
        {
          label: "建材行业集中度",
          evidences: [
            "建筑建材总 508 · 红 22 · 占全池红档 16.8%",
            "近 30 天热力：4-16 以来日均触发从 6 涨到 18（+200%）",
            "交叉规则 CRX-BIZ-02（工商变更 + 流水骤降）在建材集中命中 3 户",
          ],
        },
        {
          label: "触达优先级校准",
          evidences: [
            "红档 131 中已触达 119（90.8%）· 在途 12",
            "建议：建材红档 22 户由区域分行一把手直接介入",
            "黄档 384 中已触达 218（56.8%）· 本周剩余 2 个工作日",
          ],
        },
      ],
    },
  },
  {
    id: "al-msg-5",
    at: "3 分钟前",
    kind: "ai-response",
    content:
      "Top 3 红档详情见右栏「触达率」Tab · 建材行业近 30 天触发热力见「热力日历」· 建议：红档建材 22 户即刻升级，由区域行长直接介入。",
    fieldRef: "Distribution · 建筑建材",
    sectionDiff: {
      sectionAnchor: "Industry slice · 建筑建材",
      after: "508 户 · 红 22（4.3%）· 近 30 天热力 ↑200%",
    },
  },
  {
    id: "al-msg-6",
    at: "2 分钟前",
    kind: "ai-question",
    content: "是否立即给建材 22 红档生成分行长触达任务单（含处置建议 + 联系人 + 截止时间）？预计生成 22 张工单。",
  },
  {
    id: "al-msg-7",
    at: "1 分钟前",
    kind: "user-command",
    content: "/dispatch 建材红档 22 户 · 分行长直触 · 48h 截止 · 同步给风险部",
  },
  {
    id: "al-msg-8",
    at: "刚刚",
    kind: "system-event",
    content: "22 张触达工单已生成并下发到分行长 · 抄送风险部 · 48h 截止时间设为 2026-04-23 18:00",
  },
];

const RECENT: AlertRecentSession[] = [
  { id: "alr-1", objective: "2026-04-21 周度扫描（当前）", updated: "刚刚", pool: 3200, redCount: 131 },
  { id: "alr-2", objective: "2026-04-14 周度扫描", updated: "7 天前", pool: 3180, redCount: 116 },
  { id: "alr-3", objective: "2026-04-07 周度扫描", updated: "14 天前", pool: 3150, redCount: 104 },
  { id: "alr-4", objective: "行业专项 · 建材建筑 Q1 回顾", updated: "21 天前", pool: 512, redCount: 28 },
];

export const ALERT_SESSION: AlertSession = {
  id: "alr-1",
  objective: "2026-04-21 周度贷中预警扫描",
  stage: "已出榜 · 触达任务下发中",
  updated: "刚刚",
  query: QUERY,
  rules: RULES,
  pipeline: PIPELINE,
  distribution: DISTRIBUTION,
  totals: {
    red: DISTRIBUTION.reduce((s, r) => s + r.red, 0),
    yellow: DISTRIBUTION.reduce((s, r) => s + r.yellow, 0),
    green: DISTRIBUTION.reduce((s, r) => s + r.green, 0),
  },
  heat: HEAT,
  reach: REACH,
  topCases: TOP_CASES,
  conversation: CONVERSATION,
  qcCounts: { block: 0, warn: 2, info: 4 },
  recentSessions: RECENT,
};
