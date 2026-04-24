/**
 * Agent Alert (预警 · A04) — Tiered portfolio watchlist fixtures.
 * Feeds the /archive/alert workspace (red/yellow/green tiered list + external signals + disposal).
 */

export type AlertTier = "red" | "amber" | "green";

export type AlertCustomer = {
  id: string;
  name: string;
  tier: AlertTier;
  exposure: string;
  industry: string;
  rm: string;
  trigger: string;
  lastChange: string;
  internalFlag: boolean;
  externalFlag: boolean;
  confidence: number;
};

export type AlertSignal = {
  id: string;
  ts: string;
  customerId: string;
  customerName: string;
  channel: "juridical" | "media" | "tax" | "trade" | "behavior";
  body: string;
  severity: "high" | "mid" | "low";
};

export type DisposalAction = {
  id: string;
  label: string;
  owner: string;
  sla: string;
  tier: AlertTier;
};

export type AlertRuleCategory = {
  id: string;
  label: string;
  count: number;
};

export const ALERT_STATS = {
  weeklyProcessed: "1,284",
  successRate: "94%",
  avgDuration: "自动 · 0 触达",
} as const;

export const ALERT_CATEGORIES: AlertRuleCategory[] = [
  { id: "all", label: "全部存量客户", count: 1284 },
  { id: "red", label: "红区 · 立即处置", count: 12 },
  { id: "amber", label: "黄区 · 观察", count: 48 },
  { id: "green", label: "绿区 · 正常", count: 1224 },
  { id: "src-jud", label: "司法 / 失信", count: 23 },
  { id: "src-media", label: "负面舆情", count: 57 },
  { id: "src-tax", label: "税务异常", count: 18 },
  { id: "src-trade", label: "交易异动", count: 64 },
  { id: "src-behav", label: "账户行为", count: 35 },
];

export const ALERT_CUSTOMERS: AlertCustomer[] = [
  // RED tier
  {
    id: "alt-001",
    name: "华晨实业集团",
    tier: "red",
    exposure: "3800 万",
    industry: "建材批发",
    rm: "李慎之",
    trigger: "法人被列入失信被执行人 · 账户资金 24h 内归零",
    lastChange: "04-21 07:22",
    internalFlag: true,
    externalFlag: true,
    confidence: 0.95,
  },
  {
    id: "alt-002",
    name: "瑞鑫精密机械",
    tier: "red",
    exposure: "1600 万",
    industry: "通用设备",
    rm: "王哲",
    trigger: "国税稽查立案 · 对公账户代发工资停滞 2 期",
    lastChange: "04-20 18:10",
    internalFlag: true,
    externalFlag: true,
    confidence: 0.89,
  },
  {
    id: "alt-003",
    name: "恒源纺织",
    tier: "red",
    exposure: "2400 万",
    industry: "纺织服装",
    rm: "张晓芸",
    trigger: "主要下游客户破产 · 应收账款账龄 >120d 比例 68%",
    lastChange: "04-20 14:45",
    internalFlag: true,
    externalFlag: true,
    confidence: 0.87,
  },
  // AMBER tier
  {
    id: "alt-101",
    name: "安华物流",
    tier: "amber",
    exposure: "900 万",
    industry: "道路运输",
    rm: "王哲",
    trigger: "油价波动 + 单月流水环比 -28%",
    lastChange: "04-20 11:08",
    internalFlag: true,
    externalFlag: false,
    confidence: 0.72,
  },
  {
    id: "alt-102",
    name: "鑫宇建设",
    tier: "amber",
    exposure: "1500 万",
    industry: "建筑施工",
    rm: "陈峰",
    trigger: "新增司法诉讼 2 件 · 标的合计 380 万",
    lastChange: "04-20 09:30",
    internalFlag: false,
    externalFlag: true,
    confidence: 0.68,
  },
  {
    id: "alt-103",
    name: "绿源食品",
    tier: "amber",
    exposure: "720 万",
    industry: "食品制造",
    rm: "李慎之",
    trigger: "负面舆情 · 区域媒体报道产品质量投诉",
    lastChange: "04-19 22:15",
    internalFlag: false,
    externalFlag: true,
    confidence: 0.61,
  },
  {
    id: "alt-104",
    name: "新苑电子",
    tier: "amber",
    exposure: "1100 万",
    industry: "电子元器件",
    rm: "张晓芸",
    trigger: "主要股东所持股权被冻结 · 冻结比例 19%",
    lastChange: "04-19 16:48",
    internalFlag: false,
    externalFlag: true,
    confidence: 0.75,
  },
  // GREEN samples (only keep a few for the panel)
  {
    id: "alt-201",
    name: "永康五金工贸",
    tier: "green",
    exposure: "400 万",
    industry: "五金制造",
    rm: "王哲",
    trigger: "全指标在阈值内,无外部负面",
    lastChange: "04-21 00:00",
    internalFlag: false,
    externalFlag: false,
    confidence: 0.92,
  },
  {
    id: "alt-202",
    name: "瀚蓝智控",
    tier: "green",
    exposure: "1500 万",
    industry: "工业软件",
    rm: "陈峰",
    trigger: "新获小巨人资质 · 指标全绿",
    lastChange: "04-20 17:30",
    internalFlag: false,
    externalFlag: false,
    confidence: 0.95,
  },
];

export const ALERT_SIGNAL_STREAM: AlertSignal[] = [
  {
    id: "as-001",
    ts: "09:24",
    customerId: "alt-001",
    customerName: "华晨实业",
    channel: "juridical",
    body: "法人张某被列入失信被执行人 · 全国统一执行系统",
    severity: "high",
  },
  {
    id: "as-002",
    ts: "09:11",
    customerId: "alt-001",
    customerName: "华晨实业",
    channel: "behavior",
    body: "对公结算账户 24 小时资金归零",
    severity: "high",
  },
  {
    id: "as-003",
    ts: "08:42",
    customerId: "alt-002",
    customerName: "瑞鑫精密",
    channel: "tax",
    body: "国税稽查局立案通知书(苏税稽立〔2026〕114号)",
    severity: "high",
  },
  {
    id: "as-004",
    ts: "08:30",
    customerId: "alt-103",
    customerName: "绿源食品",
    channel: "media",
    body: "某省消协公告 · 该批次油脂产品酸价超标",
    severity: "mid",
  },
  {
    id: "as-005",
    ts: "07:58",
    customerId: "alt-102",
    customerName: "鑫宇建设",
    channel: "juridical",
    body: "新增两起合同纠纷一审立案(被告方)",
    severity: "mid",
  },
  {
    id: "as-006",
    ts: "07:12",
    customerId: "alt-104",
    customerName: "新苑电子",
    channel: "juridical",
    body: "股东张某名下股权被冻结 19% · 金华中院执行",
    severity: "mid",
  },
  {
    id: "as-007",
    ts: "06:40",
    customerId: "alt-101",
    customerName: "安华物流",
    channel: "trade",
    body: "过去 30 天对公流水 1840 万 · 环比 -28%",
    severity: "low",
  },
];

export const ALERT_DISPOSAL: DisposalAction[] = [
  {
    id: "dp-1",
    label: "冻结存量授信 + 立即电话 RM 沟通",
    owner: "分行授信部 · 沈主任",
    sla: "2h",
    tier: "red",
  },
  {
    id: "dp-2",
    label: "提交紧急风险评审 · 触发提前回收评估",
    owner: "总行风险委",
    sla: "24h",
    tier: "red",
  },
  {
    id: "dp-3",
    label: "加快抵押物现场核查",
    owner: "抵押管理中心 · 范工",
    sla: "48h",
    tier: "red",
  },
  {
    id: "dp-4",
    label: "列入月度观察 · 加密数据拉取(T+1)",
    owner: "RM",
    sla: "每日",
    tier: "amber",
  },
  {
    id: "dp-5",
    label: "补做现场走访 · 询问资金用途变化",
    owner: "RM + 客户经理助理",
    sla: "7d",
    tier: "amber",
  },
];
