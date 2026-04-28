/**
 * Agent Channel (Scout) · 多 session 多企业 look-alike 获客 mock
 * 2026-04-28 · master plan §B.1 (gap #2 mock 单 const 不切) + §B.2 (gap #3 panel 不接 props)
 *
 * 5 个标杆企业 session (5 行业 × 5 阶段 × 5 区域差异化) · 反 5 原则 §3.5 难度分层
 *   sess_haichao    · SaaS B 轮 · 上海工业软件 (中等档 50%)
 *   sess_zhirong    · 智能制造 A 轮 · 苏州精密制造 (中等档 50%)
 *   sess_yuemao     · 跨境电商成长期 · 深圳跨境电商 (简单档 20%)
 *   sess_kangyuan   · 生物医药早期 · 杭州生物医药 (困难档 20%)
 *   sess_jiarui     · 新消费成熟期 · 成都新消费 (极端档 10%)
 *
 * 每 session 之间 radar/signals/funnel/candidates 实质不同 · 不许 deep-copy 改名
 * 见: docs/contracts/workspace-state-protocol.md §3 + agent-channel-spec.md §6
 *
 * 承接原 agent-channel-session.ts (单 const) · 旧 const 仍 export 用于过渡兼容
 */

import type { ConversationMessage, RefCardPayload } from "./agent-report-session";
export type { ConversationMessage, RefCardPayload };

export const CHANNEL_GLOBAL_STATS = {
  weeklyProcessed: "164",
  hitRate: "32.8%",
  avgDuration: "6.2 分钟",
} as const;

/* ── 类型 (与原单 const file 保持一致 · 不破坏外部 import) ─────────────── */

export type ScoutQuery = {
  id: string;
  benchmark: string;
  industry: string;
  geo: string;
  scaleRange: string;
  featureTags: string[];
  updated: string;
  kbRefs: { id: string; label: string; hitBy: string }[];
};

export type SignalSource = {
  id: string;
  key: "biz" | "bidding" | "pr" | "legal" | "social" | "tax" | "hr" | "funding";
  label: string;
  status: "active" | "degraded" | "off";
  weight: number;
  freq: string;
  coverage: number;
  hits: number;
  note?: string;
};

export type MatchSetting = {
  similarity: number;
  geoInclude: string[];
  industryInclude: string[];
  scaleRange: string;
  excludeActive: boolean;
  excludeRiskTags: string[];
};

export type RadarQuadrant = "base" | "bonus" | "demand" | "health" | "market";
export type RadarDimension = {
  axis: string;
  score: number;
  benchmark: number;
  quadrant: RadarQuadrant;
  note?: string;
};

export type FunnelStage = {
  id: string;
  label: string;
  count: number;
  detail?: string;
};

export type SignalEventKind =
  | "biz-change"
  | "bid-win"
  | "recruit"
  | "fund"
  | "policy"
  | "legal"
  | "tax"
  | "news";

export type SignalEvent = {
  id: string;
  at: string;
  kind: SignalEventKind;
  title: string;
  detail: string;
  source: { label: string; url?: string };
  severity: "pos" | "neu" | "neg";
};

export type Candidate = {
  id: string;
  name: string;
  similarity: number;
  industry: string;
  geo: string;
  scale: string;
  signals: string[];
  riskTags: string[];
  products: string[];
  note?: string;
  timeline?: SignalEvent[];
};

export type RecentScoutSession = {
  id: string;
  benchmark: string;
  updated: string;
  progress: number;
  stage: string;
};

export type ChannelSession = {
  id: string;
  benchmarkName: string;
  candidateCount: number;
  stage: string;
  updated: string;
  query: ScoutQuery;
  signals: SignalSource[];
  match: MatchSetting;
  conversation: ConversationMessage[];
  radar: RadarDimension[];
  funnel: FunnelStage[];
  candidates: Candidate[];
  qcCounts: { block: number; warn: number; info: number };
  recentSessions: RecentScoutSession[];
};

/* ────────────────────────────────────────────────────────────────────
   Session 1 · sess_haichao · SaaS B 轮 · 上海工业软件
   难度档：中等 50% · SaaS 行业景气高 · 信号丰富
   ──────────────────────────────────────────────────────────────────── */

const QUERY_HAICHAO: ScoutQuery = {
  id: "q-haichao-0428",
  benchmark: "上海海潮工业软件有限公司",
  industry: "工业软件 · SaaS",
  geo: "上海 · 浦东/张江",
  scaleRange: "营收 1-3 亿元",
  featureTags: [
    "B 轮已完成",
    "估值 12 亿",
    "客户 200+",
    "ARR 1.4 亿",
    "续费率 92%",
    "团队 180 人",
    "研发占比 65%",
    "国家高新企业",
    "专精特新小巨人",
    "PMC SaaS 龙头",
    "标普客户认可",
    "工信部白名单",
  ],
  updated: "5 分钟前",
  kbRefs: [
    { id: "kb-h1", label: "工业软件赛道 2026 投资白皮书", hitBy: "行业风口" },
    { id: "kb-h2", label: "本行 SaaS 客户精选档案", hitBy: "标杆相似度" },
    { id: "kb-h3", label: "上海张江 AIoT 产业目录 2025", hitBy: "区域聚类" },
  ],
};

const SIGNALS_HAICHAO: SignalSource[] = [
  { id: "s-h1", key: "funding", label: "投融资", status: "active", weight: 0.20, freq: "事件触发", coverage: 92, hits: 48, note: "B 轮披露密集" },
  { id: "s-h2", key: "hr", label: "招聘", status: "active", weight: 0.15, freq: "每日", coverage: 95, hits: 1820, note: "研发岗扩张明显" },
  { id: "s-h3", key: "biz", label: "工商", status: "active", weight: 0.12, freq: "每日", coverage: 99, hits: 542 },
  { id: "s-h4", key: "pr", label: "舆情", status: "active", weight: 0.13, freq: "每小时", coverage: 88, hits: 612, note: "SaaS 公关密度高" },
  { id: "s-h5", key: "bidding", label: "招投标", status: "active", weight: 0.11, freq: "每日", coverage: 80, hits: 234 },
  { id: "s-h6", key: "tax", label: "纳税", status: "active", weight: 0.12, freq: "季度", coverage: 78, hits: 196 },
  { id: "s-h7", key: "legal", label: "司法", status: "active", weight: 0.09, freq: "每日", coverage: 96, hits: 14 },
  { id: "s-h8", key: "social", label: "社保", status: "active", weight: 0.08, freq: "月度", coverage: 84, hits: 312 },
];

const RADAR_HAICHAO: RadarDimension[] = [
  { axis: "营收体量", quadrant: "base", score: 78, benchmark: 50, note: "ARR 1.4 亿 · 行业 P50 ≈ 6,000 万" },
  { axis: "成长动能", quadrant: "base", score: 92, benchmark: 60, note: "ARR YoY +85% · 招聘 +120%" },
  { axis: "资质含金量", quadrant: "bonus", score: 88, benchmark: 45, note: "专精特新小巨人 · 工信部白名单" },
  { axis: "行业风口度", quadrant: "bonus", score: 95, benchmark: 70, note: "工业 SaaS 融资指数 · 政策 boost +15" },
  { axis: "用信需求度", quadrant: "demand", score: 65, benchmark: 50, note: "B 轮已到位 · 短期信贷需求中等" },
  { axis: "合规健康度", quadrant: "health", score: 96, benchmark: 75, note: "无诉讼 · 无失信 · 历史合规优秀" },
  { axis: "营销蓝海度", quadrant: "market", score: 88, benchmark: 55, note: "他行接触少 · 我行有完整 SaaS 产品线" },
  { axis: "决策可及度", quadrant: "market", score: 72, benchmark: 60, note: "CFO 公开活跃 · 创始人 LinkedIn 活跃" },
];

const FUNNEL_HAICHAO: FunnelStage[] = [
  { id: "fn-h1", label: "信号池", count: 3780, detail: "8 信号源 · 投融资源加权" },
  { id: "fn-h2", label: "工商匹配", count: 1240, detail: "工业软件 · SaaS · 长三角" },
  { id: "fn-h3", label: "画像命中", count: 482, detail: "B 轮后 · 研发占比 ≥ 50%" },
  { id: "fn-h4", label: "风险过滤", count: 218, detail: "司法 / 失信 / 异常滤" },
  { id: "fn-h5", label: "Top 推荐", count: 35, detail: "相似度 ≥ 0.78 · 排除已授信" },
];

const TIMELINE_HAICHAO_C1: SignalEvent[] = [
  { id: "tl-h1-1", at: "今早 · 09:12", kind: "fund", title: "B+ 轮 4 亿融资完成 · 红杉领投", detail: "本轮估值 18 亿 · 主要用于产品研发 + 海外拓展", source: { label: "36 氪 · 2026-04-28", url: "#" }, severity: "pos" },
  { id: "tl-h1-2", at: "昨天", kind: "recruit", title: "近 30 天新招 35 人 · AI 算法岗 12 个", detail: "高级工程师月薪 50K+ · CTO 直招", source: { label: "脉脉 + Boss 直聘聚合", url: "#" }, severity: "pos" },
  { id: "tl-h1-3", at: "1 周前", kind: "policy", title: "入选工信部 2026 第一批专精特新小巨人", detail: "认定编号 GZX-2026-0114 · 100 万一次性补贴", source: { label: "工信部公告 2026-04-21", url: "#" }, severity: "pos" },
  { id: "tl-h1-4", at: "2 周前", kind: "bid-win", title: "中标某央企 PMC 系统改造项目", detail: "金额 6,800 万 · 36 个月 · 标普背书", source: { label: "中央政采 · 公示 2026-04-14", url: "#" }, severity: "pos" },
];

const CANDIDATES_HAICHAO: Candidate[] = [
  { id: "c-h1", name: "杭州智云工业软件", similarity: 0.94, industry: "工业软件 SaaS", geo: "浙江杭州", scale: "营收 1.8 亿", signals: ["投融资", "招聘", "招投标"], riskTags: [], products: ["科创信用贷", "并购贷"], note: "ARR YoY +92% · A 轮", timeline: TIMELINE_HAICHAO_C1 },
  { id: "c-h2", name: "苏州工创智能", similarity: 0.91, industry: "PMC SaaS", geo: "江苏苏州", scale: "营收 1.2 亿", signals: ["招聘", "舆情", "纳税"], riskTags: [], products: ["科创信用贷", "知识产权质押贷"] },
  { id: "c-h3", name: "南京菱研工业", similarity: 0.88, industry: "MES + IoT", geo: "江苏南京", scale: "营收 8,400 万", signals: ["投融资", "招投标"], riskTags: [], products: ["科创信用贷", "供应链金融"] },
  { id: "c-h4", name: "上海创鼎数控", similarity: 0.84, industry: "数控软件", geo: "上海闵行", scale: "营收 2.4 亿", signals: ["工商", "纳税", "舆情"], riskTags: [], products: ["对公流动资金贷", "贸易融资"], note: "全市场份额 8%" },
  { id: "c-h5", name: "无锡澜创工业云", similarity: 0.79, industry: "工业云", geo: "江苏无锡", scale: "营收 6,200 万", signals: ["招聘", "招投标"], riskTags: ["民事诉讼 × 1"], products: ["科创信用贷"], note: "知识产权纠纷待结" },
];

const CONVERSATION_HAICHAO: ConversationMessage[] = [
  { id: "cm-h1", at: "20 分钟前", kind: "system-event", content: "Scout 任务启动 · 标杆：上海海潮工业软件 · B 轮已完成 · 8 信号源 standby" },
  { id: "cm-h2", at: "20 分钟前", kind: "ai-question", content: "想找像海潮的 SaaS 企业？我会聚焦工业软件 + B 轮后 + 长三角 + 研发占比高这 4 维。" },
  { id: "cm-h3", at: "18 分钟前", kind: "user-reply", content: "对 · 想挖一批工业软件 SaaS 同画像企业 · 重点要 B 轮后估值 5-30 亿区间。" },
  { id: "cm-h4", at: "15 分钟前", kind: "ai-response", content: "已抽 12 维画像 · ARR 1-3 亿 / 研发占比 60%+ / 客户 100+ / 长三角集中。准备扫 8 信号源（投融资 0.20 + 招聘 0.15 加权）。", fieldRef: "Query · 12 维特征" },
  { id: "cm-h5", at: "8 分钟前", kind: "ai-response", content: "Funnel：3,780 → 1,240（工商）→ 482（画像 B 轮后）→ 218（风险过滤）→ Top 35。雷达综合分 84。", fieldRef: "Funnel · 5 阶段" },
  { id: "cm-h6", at: "3 分钟前", kind: "ai-response", content: "Top 5：杭州智云(0.94) · 苏州工创(0.91) · 南京菱研(0.88) · 上海创鼎(0.84) · 无锡澜创(0.79)。", fieldRef: "Candidates · Top 5" },
];

const RECENT_HAICHAO: RecentScoutSession[] = [
  { id: "rc-h1", benchmark: "上海海潮工业软件 · SaaS B 轮", updated: "刚刚（当前）", progress: 1.0, stage: "已生成 · 35 推荐" },
  { id: "rc-h2", benchmark: "深圳粤峰跨境电商 · 成长期", updated: "1 小时前", progress: 1.0, stage: "已生成 · 22 推荐" },
];

/* ────────────────────────────────────────────────────────────────────
   Session 2 · sess_zhirong · 智能制造 A 轮 · 苏州精密制造
   难度档：中等 50% · 制造业景气复杂 · 信号交叉多
   ──────────────────────────────────────────────────────────────────── */

const QUERY_ZHIRONG: ScoutQuery = {
  id: "q-zhirong-0428",
  benchmark: "苏州智荣精密制造有限公司",
  industry: "智能制造 · 精密机械",
  geo: "江苏 · 苏州工业园区",
  scaleRange: "营收 5,000 万 - 1.5 亿",
  featureTags: [
    "A 轮 5,000 万",
    "员工 220 人",
    "数控车床 80 台",
    "客户特斯拉 + 比亚迪",
    "ISO 9001/14001",
    "国家高新企业",
    "省级专精特新",
    "出口占比 35%",
    "汽车零部件主营",
    "EBITDA 18%",
    "应收账款周转 75 天",
    "厂房 12,000㎡ 自有",
  ],
  updated: "8 分钟前",
  kbRefs: [
    { id: "kb-z1", label: "苏州工业园区高新名录 2025Q4", hitBy: "区域 + 资质" },
    { id: "kb-z2", label: "汽车零部件供应链黄页", hitBy: "下游客户穿透" },
    { id: "kb-z3", label: "本行制造业历史授信档案", hitBy: "标杆相似" },
  ],
};

const SIGNALS_ZHIRONG: SignalSource[] = [
  { id: "s-z1", key: "biz", label: "工商", status: "active", weight: 0.18, freq: "每日", coverage: 99, hits: 2380 },
  { id: "s-z2", key: "bidding", label: "招投标", status: "active", weight: 0.18, freq: "每日", coverage: 92, hits: 612 },
  { id: "s-z3", key: "tax", label: "纳税", status: "active", weight: 0.16, freq: "季度", coverage: 88, hits: 824 },
  { id: "s-z4", key: "hr", label: "招聘", status: "active", weight: 0.13, freq: "每日", coverage: 86, hits: 1240 },
  { id: "s-z5", key: "social", label: "社保", status: "active", weight: 0.12, freq: "月度", coverage: 76, hits: 658 },
  { id: "s-z6", key: "legal", label: "司法", status: "active", weight: 0.10, freq: "每日", coverage: 95, hits: 184 },
  { id: "s-z7", key: "pr", label: "舆情", status: "degraded", weight: 0.07, freq: "每小时", coverage: 52, hits: 78, note: "工业舆情数据稀疏" },
  { id: "s-z8", key: "funding", label: "投融资", status: "active", weight: 0.06, freq: "事件触发", coverage: 64, hits: 28 },
];

const RADAR_ZHIRONG: RadarDimension[] = [
  { axis: "营收体量", quadrant: "base", score: 64, benchmark: 48, note: "营收 8,400 万 · 行业 P50 ≈ 4,500 万" },
  { axis: "成长动能", quadrant: "base", score: 78, benchmark: 52, note: "营收 YoY +35% · 订单 +42%" },
  { axis: "资质含金量", quadrant: "bonus", score: 82, benchmark: 50, note: "省级专精特新 · ISO 双证 · 国高新" },
  { axis: "行业风口度", quadrant: "bonus", score: 75, benchmark: 58, note: "新能源汽车供应链 · 政策强支持" },
  { axis: "用信需求度", quadrant: "demand", score: 88, benchmark: 55, note: "新订单需流贷 + 设备采购 4,200 万" },
  { axis: "合规健康度", quadrant: "health", score: 86, benchmark: 70, note: "1 起经济纠纷已和解 · 无失信" },
  { axis: "营销蓝海度", quadrant: "market", score: 70, benchmark: 60, note: "他行 2 家授信 · 我行有制造业方案" },
  { axis: "决策可及度", quadrant: "market", score: 78, benchmark: 55, note: "实控人 1 位 · 公开电话邮箱完整" },
];

const FUNNEL_ZHIRONG: FunnelStage[] = [
  { id: "fn-z1", label: "信号池", count: 4860, detail: "8 信号源 · 招投标 + 工商加权" },
  { id: "fn-z2", label: "工商匹配", count: 1620, detail: "汽车零部件 · 长三角" },
  { id: "fn-z3", label: "画像命中", count: 358, detail: "≥ 8 维 · 资质 + 客户穿透" },
  { id: "fn-z4", label: "风险过滤", count: 168, detail: "司法 + 经营异常 双滤" },
  { id: "fn-z5", label: "Top 推荐", count: 24, detail: "相似度 ≥ 0.74" },
];

const TIMELINE_ZHIRONG_C1: SignalEvent[] = [
  { id: "tl-z1-1", at: "昨天", kind: "bid-win", title: "中标比亚迪二期电池托盘加工订单", detail: "金额 1.2 亿 · 24 个月 · 含设备投入 2,800 万", source: { label: "比亚迪供应商门户", url: "#" }, severity: "pos" },
  { id: "tl-z1-2", at: "5 天前", kind: "biz-change", title: "注册资本由 2,000 万增至 5,000 万", detail: "实缴 + 3,000 万 · 股东原比例不变", source: { label: "国家企业信用信息系统" }, severity: "pos" },
  { id: "tl-z1-3", at: "10 天前", kind: "recruit", title: "近 30 天招聘 25 人 · 数控车工 + 工艺工程师", detail: "扩产前置 · 月薪 8-15K", source: { label: "Boss 直聘 + 智联", url: "#" }, severity: "pos" },
  { id: "tl-z1-4", at: "2 周前", kind: "tax", title: "Q1 纳税 A 级 · 同比 +28%", detail: "增值税 ¥186 万 · 所得税 ¥92 万", source: { label: "苏州工业园区税务" }, severity: "pos" },
];

const CANDIDATES_ZHIRONG: Candidate[] = [
  { id: "c-z1", name: "无锡精弘机械有限公司", similarity: 0.92, industry: "精密机械", geo: "江苏无锡", scale: "营收 1.1 亿", signals: ["招投标", "工商", "纳税"], riskTags: [], products: ["设备融资租赁", "供应链金融", "对公流动资金贷"], note: "宁德时代供应商", timeline: TIMELINE_ZHIRONG_C1 },
  { id: "c-z2", name: "宁波鸿基汽车零部件", similarity: 0.89, industry: "汽车零部件", geo: "浙江宁波", scale: "营收 7,200 万", signals: ["工商", "招投标"], riskTags: [], products: ["对公流动资金贷", "应收账款保理"] },
  { id: "c-z3", name: "常州毅鼎数控", similarity: 0.86, industry: "数控加工", geo: "江苏常州", scale: "营收 5,400 万", signals: ["纳税", "招聘", "社保"], riskTags: [], products: ["普惠信用贷", "设备融资租赁"] },
  { id: "c-z4", name: "嘉兴铭锐精密", similarity: 0.81, industry: "精密铸件", geo: "浙江嘉兴", scale: "营收 3,800 万", signals: ["工商", "纳税"], riskTags: ["行政处罚 × 1"], products: ["对公流动资金贷"], note: "环保整改已结清" },
  { id: "c-z5", name: "扬州瑞翔模具", similarity: 0.76, industry: "汽车模具", geo: "江苏扬州", scale: "营收 2,600 万", signals: ["招投标", "招聘"], riskTags: [], products: ["普惠信用贷"], note: "上汽供应商资格" },
];

const CONVERSATION_ZHIRONG: ConversationMessage[] = [
  { id: "cm-z1", at: "30 分钟前", kind: "system-event", content: "Scout 任务启动 · 标杆：苏州智荣精密制造 · A 轮 · 智能制造" },
  { id: "cm-z2", at: "30 分钟前", kind: "ai-question", content: "找像智荣的精密制造企业？我聚焦汽车零部件 + 国高新 + 长三角 + 营收 5K-1.5 亿。" },
  { id: "cm-z3", at: "27 分钟前", kind: "user-reply", content: "对 · 重点是有汽车 OEM 客户穿透的精密制造小厂 · 营收 5 千万往上的。" },
  { id: "cm-z4", at: "20 分钟前", kind: "ai-response", content: "已抽 12 维 · 含资质 + 主营 + 大客户 + 财务结构。8 信号源（工商 + 招投标 + 纳税三档加权）启动扫描。", fieldRef: "Query · 12 维特征" },
  { id: "cm-z5", at: "10 分钟前", kind: "ai-response", content: "Funnel：4,860 → 1,620（工商）→ 358（画像）→ 168（风险）→ Top 24。综合分 78。", fieldRef: "Funnel · 5 阶段" },
  { id: "cm-z6", at: "5 分钟前", kind: "ai-response", content: "Top 5：无锡精弘(0.92) · 宁波鸿基(0.89) · 常州毅鼎(0.86) · 嘉兴铭锐(0.81) · 扬州瑞翔(0.76)。", fieldRef: "Candidates · Top 5" },
];

const RECENT_ZHIRONG: RecentScoutSession[] = [
  { id: "rc-z1", benchmark: "苏州智荣精密制造 · 智能制造 A 轮", updated: "刚刚（当前）", progress: 1.0, stage: "已生成 · 24 推荐" },
];

/* ────────────────────────────────────────────────────────────────────
   Session 3 · sess_yuemao · 跨境电商成长期 · 深圳跨境电商
   难度档：简单 20% · 跨境电商数据透明 · 信号集中
   ──────────────────────────────────────────────────────────────────── */

const QUERY_YUEMAO: ScoutQuery = {
  id: "q-yuemao-0428",
  benchmark: "深圳粤峰跨境电商有限公司",
  industry: "跨境电商 · 3C 数码品类",
  geo: "广东 · 深圳南山",
  scaleRange: "营收 8,000 万 - 2 亿",
  featureTags: [
    "亚马逊店铺 12 家",
    "TikTok 店铺 5 家",
    "出口占比 95%",
    "美国市场 60%",
    "毛利率 38%",
    "周转 45 天",
    "员工 95 人",
    "GMV 月 ¥2,800 万",
    "海外仓 3 个",
    "无 VC 融资",
    "家族股权 80/20",
    "无境外受限",
  ],
  updated: "12 分钟前",
  kbRefs: [
    { id: "kb-y1", label: "跨境电商 3C 类目分析 2025", hitBy: "类目 + 市场" },
    { id: "kb-y2", label: "本行跨境电商授信档案", hitBy: "历史标杆" },
    { id: "kb-y3", label: "深圳南山跨境企业目录", hitBy: "区域聚类" },
  ],
};

const SIGNALS_YUEMAO: SignalSource[] = [
  { id: "s-y1", key: "biz", label: "工商", status: "active", weight: 0.16, freq: "每日", coverage: 96, hits: 1860 },
  { id: "s-y2", key: "tax", label: "纳税", status: "active", weight: 0.20, freq: "季度", coverage: 92, hits: 524, note: "出口退税亮眼" },
  { id: "s-y3", key: "pr", label: "舆情", status: "active", weight: 0.18, freq: "每小时", coverage: 88, hits: 462, note: "Trustpilot 评分跟踪" },
  { id: "s-y4", key: "hr", label: "招聘", status: "active", weight: 0.12, freq: "每日", coverage: 92, hits: 388 },
  { id: "s-y5", key: "social", label: "社保", status: "active", weight: 0.09, freq: "月度", coverage: 78, hits: 286 },
  { id: "s-y6", key: "legal", label: "司法", status: "active", weight: 0.10, freq: "每日", coverage: 92, hits: 42 },
  { id: "s-y7", key: "bidding", label: "招投标", status: "off", weight: 0.05, freq: "每日", coverage: 0, hits: 0, note: "电商基本无政采" },
  { id: "s-y8", key: "funding", label: "投融资", status: "degraded", weight: 0.10, freq: "事件触发", coverage: 32, hits: 18, note: "本类多无外部融资" },
];

const RADAR_YUEMAO: RadarDimension[] = [
  { axis: "营收体量", quadrant: "base", score: 72, benchmark: 50, note: "GMV 月 ¥2,800 万 · 行业 P50 ≈ ¥1,500 万" },
  { axis: "成长动能", quadrant: "base", score: 85, benchmark: 60, note: "GMV YoY +52% · 新店 4 家上线" },
  { axis: "资质含金量", quadrant: "bonus", score: 48, benchmark: 35, note: "无国家资质 · AEO 高级认证" },
  { axis: "行业风口度", quadrant: "bonus", score: 68, benchmark: 50, note: "TikTok 跨境直播红利期" },
  { axis: "用信需求度", quadrant: "demand", score: 92, benchmark: 60, note: "海外仓铺货 + 4 季度旺季备货" },
  { axis: "合规健康度", quadrant: "health", score: 84, benchmark: 65, note: "无重大处罚 · Trustpilot 4.6 分" },
  { axis: "营销蓝海度", quadrant: "market", score: 82, benchmark: 50, note: "我行无跨境产品体验客户" },
  { axis: "决策可及度", quadrant: "market", score: 86, benchmark: 60, note: "创始人活跃 · 公开课讲师" },
];

const FUNNEL_YUEMAO: FunnelStage[] = [
  { id: "fn-y1", label: "信号池", count: 2240, detail: "8 信号源 · 纳税 + 舆情加权" },
  { id: "fn-y2", label: "工商匹配", count: 685, detail: "跨境电商 · 珠三角" },
  { id: "fn-y3", label: "画像命中", count: 198, detail: "≥ 7 维 · GMV + 海外仓" },
  { id: "fn-y4", label: "风险过滤", count: 96, detail: "司法 + 退税异常 双滤" },
  { id: "fn-y5", label: "Top 推荐", count: 22, detail: "相似度 ≥ 0.70" },
];

const TIMELINE_YUEMAO_C1: SignalEvent[] = [
  { id: "tl-y1-1", at: "今天 · 14:30", kind: "tax", title: "Q1 出口退税 ¥180 万到账", detail: "申报金额准确率 100% · 未发现疑点", source: { label: "深圳市税务局", url: "#" }, severity: "pos" },
  { id: "tl-y1-2", at: "3 天前", kind: "news", title: "TikTok Shop 美国小店通过最高级认证", detail: "可享受平台流量倾斜 + 物流补贴", source: { label: "亿邦动力 · 2026-04-25", url: "#" }, severity: "pos" },
  { id: "tl-y1-3", at: "1 周前", kind: "biz-change", title: "新增子公司 · 深圳粤峰国际物流", detail: "注册资本 1,000 万 · 自营海外仓 SOP", source: { label: "国家企业信用信息系统" }, severity: "pos" },
  { id: "tl-y1-4", at: "2 周前", kind: "recruit", title: "招聘 18 人 · 海外站点运营 + 客服", detail: "美国 + 欧洲方向 · 月薪 8-20K + 年终", source: { label: "前程无忧 + Boss 直聘" }, severity: "pos" },
];

const CANDIDATES_YUEMAO: Candidate[] = [
  { id: "c-y1", name: "广州海森数码贸易", similarity: 0.93, industry: "跨境电商 3C", geo: "广东广州", scale: "GMV 月 ¥1,800 万", signals: ["纳税", "舆情", "工商"], riskTags: [], products: ["跨境信用贷", "应收账款保理"], note: "亚马逊优秀卖家", timeline: TIMELINE_YUEMAO_C1 },
  { id: "c-y2", name: "深圳锐启国际贸易", similarity: 0.88, industry: "跨境电商家居", geo: "广东深圳", scale: "GMV 月 ¥1,200 万", signals: ["工商", "纳税"], riskTags: [], products: ["跨境信用贷", "供应链金融"] },
  { id: "c-y3", name: "东莞雅创外贸", similarity: 0.84, industry: "跨境电商 3C", geo: "广东东莞", scale: "GMV 月 ¥980 万", signals: ["招聘", "纳税"], riskTags: [], products: ["跨境信用贷", "出口退税融资"] },
  { id: "c-y4", name: "厦门启源跨境", similarity: 0.78, industry: "跨境电商服装", geo: "福建厦门", scale: "GMV 月 ¥760 万", signals: ["工商", "舆情"], riskTags: [], products: ["跨境信用贷"] },
  { id: "c-y5", name: "杭州萌芯跨境", similarity: 0.72, industry: "跨境电商小家电", geo: "浙江杭州", scale: "GMV 月 ¥620 万", signals: ["纳税", "招聘"], riskTags: ["民事诉讼 × 1"], products: ["跨境信用贷"], note: "侵权纠纷已和解" },
];

const CONVERSATION_YUEMAO: ConversationMessage[] = [
  { id: "cm-y1", at: "1 小时前", kind: "system-event", content: "Scout 任务启动 · 标杆：深圳粤峰跨境电商 · GMV 月 2,800 万" },
  { id: "cm-y2", at: "1 小时前", kind: "ai-question", content: "找像粤峰的跨境电商？聚焦 3C 类目 + 珠三角 + GMV 月 ¥800 万 - ¥3,000 万。" },
  { id: "cm-y3", at: "55 分钟前", kind: "user-reply", content: "对 · 想挖一批跨境电商成长期客户 · 重点要海外仓 + 美国市场为主。" },
  { id: "cm-y4", at: "40 分钟前", kind: "ai-response", content: "已抽 12 维 · GMV/类目/平台/退税/海外仓/股权结构。准备扫 8 信号源（纳税 + 舆情 + 工商三档加权）。", fieldRef: "Query · 12 维特征" },
  { id: "cm-y5", at: "20 分钟前", kind: "ai-response", content: "Funnel：2,240 → 685（工商）→ 198（画像）→ 96（风险）→ Top 22。综合分 77。", fieldRef: "Funnel · 5 阶段" },
  { id: "cm-y6", at: "5 分钟前", kind: "ai-response", content: "Top 5：广州海森(0.93) · 深圳锐启(0.88) · 东莞雅创(0.84) · 厦门启源(0.78) · 杭州萌芯(0.72)。", fieldRef: "Candidates · Top 5" },
];

const RECENT_YUEMAO: RecentScoutSession[] = [
  { id: "rc-y1", benchmark: "深圳粤峰跨境电商 · 成长期", updated: "刚刚（当前）", progress: 1.0, stage: "已生成 · 22 推荐" },
];

/* ────────────────────────────────────────────────────────────────────
   Session 4 · sess_kangyuan · 生物医药早期 · 杭州生物医药
   难度档：困难 20% · 生医早期信号稀疏 · 多维证据匮乏
   ──────────────────────────────────────────────────────────────────── */

const QUERY_KANGYUAN: ScoutQuery = {
  id: "q-kangyuan-0428",
  benchmark: "杭州康源生物科技有限公司",
  industry: "生物医药 · 创新药",
  geo: "浙江 · 杭州滨江/未来科技城",
  scaleRange: "营收 < 5,000 万 · 研发驱动",
  featureTags: [
    "Pre-A 轮 6,000 万",
    "管线 5 条",
    "1 期临床 2 条",
    "员工 65 人",
    "博士占比 30%",
    "专利 22 项",
    "无营收 · 研发期",
    "高校合作 3 家",
    "BIOBAY 入驻",
    "国家高新企业",
    "无银行授信",
    "创始团队海归",
  ],
  updated: "20 分钟前",
  kbRefs: [
    { id: "kb-k1", label: "生物医药创新药融资白皮书 2026", hitBy: "行业判断" },
    { id: "kb-k2", label: "杭州滨江 · 未来科技城生医名录", hitBy: "区域聚类" },
    { id: "kb-k3", label: "本行生医投贷联动产品手册", hitBy: "产品适配" },
  ],
};

const SIGNALS_KANGYUAN: SignalSource[] = [
  { id: "s-k1", key: "funding", label: "投融资", status: "active", weight: 0.30, freq: "事件触发", coverage: 86, hits: 38, note: "唯一硬信号源" },
  { id: "s-k2", key: "biz", label: "工商 + 资质", status: "active", weight: 0.18, freq: "每日", coverage: 96, hits: 248, note: "FDA / NMPA 申报与工商变更并轨" },
  { id: "s-k3", key: "hr", label: "招聘", status: "active", weight: 0.18, freq: "每日", coverage: 88, hits: 168, note: "博士岗为关键信号" },
  { id: "s-k4", key: "pr", label: "舆情", status: "active", weight: 0.12, freq: "每小时", coverage: 78, hits: 86, note: "管线进展媒体跟踪" },
  { id: "s-k5", key: "social", label: "社保", status: "active", weight: 0.10, freq: "月度", coverage: 72, hits: 64, note: "研发团队稳定度参考" },
  { id: "s-k6", key: "tax", label: "纳税", status: "degraded", weight: 0.04, freq: "季度", coverage: 28, hits: 18, note: "研发期纳税参考意义低" },
  { id: "s-k7", key: "bidding", label: "招投标", status: "off", weight: 0.04, freq: "每日", coverage: 0, hits: 0, note: "创新药基本无政采" },
  { id: "s-k8", key: "legal", label: "司法", status: "active", weight: 0.04, freq: "每日", coverage: 96, hits: 6 },
];

const RADAR_KANGYUAN: RadarDimension[] = [
  { axis: "营收体量", quadrant: "base", score: 28, benchmark: 35, note: "无营收 · 研发期 · 行业 P50 也低" },
  { axis: "成长动能", quadrant: "base", score: 76, benchmark: 50, note: "管线 5 条 · 临床 1 期 2 条 · 招聘 +24%" },
  { axis: "资质含金量", quadrant: "bonus", score: 92, benchmark: 60, note: "国家高新 · BIOBAY · 22 项专利" },
  { axis: "行业风口度", quadrant: "bonus", score: 88, benchmark: 65, note: "创新药政策 boost · 集采压力外行业" },
  { axis: "用信需求度", quadrant: "demand", score: 95, benchmark: 60, note: "Pre-A 已完成 · A 轮前急需研发流贷" },
  { axis: "合规健康度", quadrant: "health", score: 94, benchmark: 75, note: "无诉讼 · 无失信 · 历史合规优秀" },
  { axis: "营销蓝海度", quadrant: "market", score: 92, benchmark: 50, note: "无银行授信 · 我行投贷联动产品适配" },
  { axis: "决策可及度", quadrant: "market", score: 78, benchmark: 55, note: "创始人公开活跃 · 学术演讲多" },
];

const FUNNEL_KANGYUAN: FunnelStage[] = [
  { id: "fn-k1", label: "信号池", count: 1480, detail: "8 信号源 · 投融资 + 招聘加权" },
  { id: "fn-k2", label: "工商匹配", count: 386, detail: "创新药 · 长三角 · 高新企业" },
  { id: "fn-k3", label: "画像命中", count: 86, detail: "≥ 6 维 · 管线 + 临床 + 团队" },
  { id: "fn-k4", label: "风险过滤", count: 48, detail: "司法 + 受限滤" },
  { id: "fn-k5", label: "Top 推荐", count: 12, detail: "相似度 ≥ 0.65 · 早期段" },
];

const TIMELINE_KANGYUAN_C1: SignalEvent[] = [
  { id: "tl-k1-1", at: "5 天前", kind: "fund", title: "Pre-A 轮 6,000 万融资完成", detail: "本轮估值 3 亿 · 启明创投 + 高瓴生医", source: { label: "动脉网 · 2026-04-23", url: "#" }, severity: "pos" },
  { id: "tl-k1-2", at: "2 周前", kind: "policy", title: "管线 BG-2024 获 NMPA 1 期临床批件", detail: "靶点：CD47 单抗 · 适应症肿瘤", source: { label: "NMPA 公告 · 2026-04-15" }, severity: "pos" },
  { id: "tl-k1-3", at: "1 个月前", kind: "recruit", title: "首席医学官（CMO）就位", detail: "前默沙东资深科学家 · 海归博士", source: { label: "脉脉行业认证" }, severity: "pos" },
  { id: "tl-k1-4", at: "2 个月前", kind: "biz-change", title: "注册资本由 1,000 万增至 2,500 万", detail: "实缴 + 1,500 万 · 创始团队增持", source: { label: "国家企业信用信息系统" }, severity: "pos" },
];

const CANDIDATES_KANGYUAN: Candidate[] = [
  { id: "c-k1", name: "上海源辰生物医药", similarity: 0.86, industry: "创新药 · 单抗", geo: "上海张江", scale: "Pre-A 已完成", signals: ["投融资", "招聘", "资质"], riskTags: [], products: ["科创信用贷", "投贷联动"], note: "管线 4 条 · 临床 1 期 1 条", timeline: TIMELINE_KANGYUAN_C1 },
  { id: "c-k2", name: "苏州盛泽医药科技", similarity: 0.82, industry: "ADC · 偶联药", geo: "江苏苏州", scale: "天使轮", signals: ["投融资", "招聘"], riskTags: [], products: ["科创信用贷", "知识产权质押贷"] },
  { id: "c-k3", name: "无锡灵药生物", similarity: 0.76, industry: "小分子靶向", geo: "江苏无锡", scale: "天使轮", signals: ["投融资", "舆情"], riskTags: [], products: ["科创信用贷"] },
  { id: "c-k4", name: "杭州博睿基因", similarity: 0.71, industry: "基因治疗", geo: "浙江杭州", scale: "种子轮", signals: ["招聘", "工商"], riskTags: ["核心团队不稳"], products: ["科创信用贷"], note: "联合创始人变更 · 谨慎" },
  { id: "c-k5", name: "南京泰生医药", similarity: 0.66, industry: "细胞治疗 CAR-T", geo: "江苏南京", scale: "种子轮", signals: ["投融资"], riskTags: ["临床进度滞后"], products: ["科创信用贷"], note: "管线 1 期临床中" },
];

const CONVERSATION_KANGYUAN: ConversationMessage[] = [
  { id: "cm-k1", at: "2 小时前", kind: "system-event", content: "Scout 任务启动 · 标杆：杭州康源生物 · 创新药 · Pre-A 轮" },
  { id: "cm-k2", at: "2 小时前", kind: "ai-question", content: "想找像康源的早期生医？我聚焦创新药 + 管线 ≥ 3 + 长三角 + Pre-A 阶段。" },
  { id: "cm-k3", at: "1.5 小时前", kind: "user-reply", content: "对 · 投贷联动方向 · 重点是管线进展靠前的早期生医。早期数据稀疏没关系。" },
  { id: "cm-k4", at: "1 小时前", kind: "ai-response", content: "已抽 12 维 · 管线/临床/团队/股权/资质/区域。投融资 0.30 + 招聘 0.18 + 工商 0.18 三档高加权（早期信号稀疏 · 投融资变成主要锚定）。", fieldRef: "Query · 12 维特征" },
  { id: "cm-k5", at: "30 分钟前", kind: "ai-response", content: "Funnel：1,480 → 386（工商）→ 86（画像）→ 48（风险）→ Top 12。早期段池子小是正常。", fieldRef: "Funnel · 5 阶段" },
  { id: "cm-k6", at: "10 分钟前", kind: "ai-response", content: "Top 5：上海源辰(0.86) · 苏州盛泽(0.82) · 无锡灵药(0.76) · 杭州博睿(0.71) · 南京泰生(0.66)。", fieldRef: "Candidates · Top 5" },
];

const RECENT_KANGYUAN: RecentScoutSession[] = [
  { id: "rc-k1", benchmark: "杭州康源生物 · 创新药 Pre-A", updated: "刚刚（当前）", progress: 1.0, stage: "已生成 · 12 推荐" },
];

/* ────────────────────────────────────────────────────────────────────
   Session 5 · sess_jiarui · 新消费成熟期 · 成都新消费
   难度档：极端 10% · 新消费舆情噪声大 · 假成熟期辨识难
   ──────────────────────────────────────────────────────────────────── */

const QUERY_JIARUI: ScoutQuery = {
  id: "q-jiarui-0428",
  benchmark: "成都嘉瑞食品科技有限公司",
  industry: "新消费 · 烘焙连锁",
  geo: "四川 · 成都/绵阳/德阳",
  scaleRange: "营收 3-8 亿元",
  featureTags: [
    "门店 480 家",
    "覆盖西南 5 省",
    "单店日均 ¥1.4 万",
    "员工 4,200 人",
    "B+ 轮 8 亿",
    "估值 60 亿",
    "央厨自营",
    "外卖占比 35%",
    "毛利率 65%",
    "上市辅导阶段",
    "小红书话题 8 亿",
    "复购率 42%",
  ],
  updated: "32 分钟前",
  kbRefs: [
    { id: "kb-j1", label: "新消费连锁餐饮专题 2026", hitBy: "行业 + 阶段" },
    { id: "kb-j2", label: "西南区域消费力指数报告", hitBy: "区域容量" },
    { id: "kb-j3", label: "本行连锁连锁授信案例库", hitBy: "标杆相似" },
  ],
};

const SIGNALS_JIARUI: SignalSource[] = [
  { id: "s-j1", key: "pr", label: "舆情", status: "active", weight: 0.22, freq: "每小时", coverage: 96, hits: 4820, note: "小红书 + 抖音热度榜" },
  { id: "s-j2", key: "biz", label: "工商", status: "active", weight: 0.16, freq: "每日", coverage: 99, hits: 3260, note: "门店子公司密集" },
  { id: "s-j3", key: "tax", label: "纳税", status: "active", weight: 0.14, freq: "季度", coverage: 84, hits: 826 },
  { id: "s-j4", key: "hr", label: "招聘", status: "active", weight: 0.12, freq: "每日", coverage: 92, hits: 2864, note: "门店扩张主信号" },
  { id: "s-j5", key: "social", label: "社保", status: "active", weight: 0.11, freq: "月度", coverage: 78, hits: 1248 },
  { id: "s-j6", key: "funding", label: "投融资", status: "active", weight: 0.10, freq: "事件触发", coverage: 88, hits: 56 },
  { id: "s-j7", key: "legal", label: "司法", status: "degraded", weight: 0.09, freq: "每日", coverage: 88, hits: 286, note: "门店纠纷常见 · 噪声多" },
  { id: "s-j8", key: "bidding", label: "招投标", status: "off", weight: 0.06, freq: "每日", coverage: 0, hits: 0, note: "新消费基本无政采" },
];

const RADAR_JIARUI: RadarDimension[] = [
  { axis: "营收体量", quadrant: "base", score: 92, benchmark: 55, note: "营收 5.4 亿 · 行业 P50 ≈ ¥6,000 万" },
  { axis: "成长动能", quadrant: "base", score: 68, benchmark: 60, note: "营收 YoY +15% · 增速放缓 · 进入成熟期" },
  { axis: "资质含金量", quadrant: "bonus", score: 56, benchmark: 40, note: "区域龙头 · 食品安全 A 级" },
  { axis: "行业风口度", quadrant: "bonus", score: 48, benchmark: 55, note: "新消费投资降温 · 连锁压力增大" },
  { axis: "用信需求度", quadrant: "demand", score: 84, benchmark: 50, note: "央厨扩建 + 新区域开店 + 上市备战" },
  { axis: "合规健康度", quadrant: "health", score: 72, benchmark: 65, note: "门店食安投诉 12 起 · 已整改" },
  { axis: "营销蓝海度", quadrant: "market", score: 64, benchmark: 55, note: "已有 3 家银行授信 · 我行可介入并购贷" },
  { axis: "决策可及度", quadrant: "market", score: 75, benchmark: 60, note: "上市辅导期 · CFO 频繁公开活动" },
];

const FUNNEL_JIARUI: FunnelStage[] = [
  { id: "fn-j1", label: "信号池", count: 6240, detail: "8 信号源 · 舆情 + 工商加权（小红书 8 亿）" },
  { id: "fn-j2", label: "工商匹配", count: 1860, detail: "新消费连锁 · 西南 + 华南" },
  { id: "fn-j3", label: "画像命中", count: 412, detail: "≥ 8 维 · 门店数 + 估值 + 复购" },
  { id: "fn-j4", label: "风险过滤", count: 156, detail: "门店食安 + 司法噪声深度滤" },
  { id: "fn-j5", label: "Top 推荐", count: 18, detail: "相似度 ≥ 0.72 · 已上市辅导" },
];

const TIMELINE_JIARUI_C1: SignalEvent[] = [
  { id: "tl-j1-1", at: "今天 · 11:20", kind: "news", title: "门店突破 500 家 · 进军北上广深", detail: "首店落地北京西单 · 含央厨改造投入 6,000 万", source: { label: "餐饮老板内参 · 2026-04-28", url: "#" }, severity: "pos" },
  { id: "tl-j1-2", at: "1 周前", kind: "fund", title: "B+ 轮 8 亿融资完成 · 高瓴 + IDG 联投", detail: "本轮估值 60 亿 · 上市前最后一轮", source: { label: "投资界 · 2026-04-21", url: "#" }, severity: "pos" },
  { id: "tl-j1-3", at: "2 周前", kind: "biz-change", title: "新增子公司 · 嘉瑞（成都）品牌管理", detail: "用于商标授权与连锁加盟管理 · 上市架构调整", source: { label: "国家企业信用信息系统" }, severity: "neu" },
  { id: "tl-j1-4", at: "1 个月前", kind: "legal", title: "门店食品安全投诉 3 起 · 全部已整改", detail: "成都市市场监管局监督 · 处罚 ¥2.4 万 · 已结清", source: { label: "成都市监 · 公示" }, severity: "neu" },
];

const CANDIDATES_JIARUI: Candidate[] = [
  { id: "c-j1", name: "重庆鲜花花茶饮", similarity: 0.92, industry: "新消费 茶饮", geo: "重庆", scale: "门店 320 家", signals: ["舆情", "工商", "纳税"], riskTags: [], products: ["对公流动资金贷", "并购贷", "上市辅导信用贷"], note: "复购率 38%", timeline: TIMELINE_JIARUI_C1 },
  { id: "c-j2", name: "西安长安食代连锁", similarity: 0.88, industry: "新消费 中式快餐", geo: "陕西西安", scale: "门店 280 家", signals: ["舆情", "招聘"], riskTags: [], products: ["对公流动资金贷", "中长期固贷"] },
  { id: "c-j3", name: "昆明云味天厨", similarity: 0.83, industry: "新消费 米线连锁", geo: "云南昆明", scale: "门店 220 家", signals: ["工商", "纳税", "社保"], riskTags: [], products: ["对公流动资金贷"], note: "稳健增长" },
  { id: "c-j4", name: "贵阳鲜里多卤味", similarity: 0.75, industry: "新消费 卤味连锁", geo: "贵州贵阳", scale: "门店 180 家", signals: ["舆情", "招聘"], riskTags: ["门店食安投诉 × 5"], products: ["对公流动资金贷"], note: "舆情噪声大 · 谨慎" },
  { id: "c-j5", name: "南宁邕江味道", similarity: 0.68, industry: "新消费 螺蛳粉", geo: "广西南宁", scale: "门店 95 家", signals: ["舆情", "工商"], riskTags: ["民事诉讼 × 3"], products: ["普惠信用贷"], note: "成熟度待观察" },
];

const CONVERSATION_JIARUI: ConversationMessage[] = [
  { id: "cm-j1", at: "3 小时前", kind: "system-event", content: "Scout 任务启动 · 标杆：成都嘉瑞食品科技 · 新消费连锁 · 上市辅导期" },
  { id: "cm-j2", at: "3 小时前", kind: "ai-question", content: "找像嘉瑞这种新消费连锁？聚焦门店 ≥ 100 家 + 估值 ≥ 30 亿 + 西南/华南，要剔除舆情噪声。" },
  { id: "cm-j3", at: "2.5 小时前", kind: "user-reply", content: "对 · 重点是已经过 B 轮的成熟期连锁 · 营收 3 亿+ · 想介入并购贷或上市辅导信用贷。" },
  { id: "cm-j4", at: "2 小时前", kind: "ai-response", content: "已抽 12 维 · 门店/估值/复购/品牌力/食安/上市进度。8 信号源（舆情 0.22 + 工商 0.16 主信号源 · 司法降级处理避免误杀）。", fieldRef: "Query · 12 维特征" },
  { id: "cm-j5", at: "1 小时前", kind: "ai-response", content: "Funnel：6,240 → 1,860（工商）→ 412（画像）→ 156（深度过滤舆情）→ Top 18。综合分 70 (略低 · 行业风口降温)。", fieldRef: "Funnel · 5 阶段" },
  { id: "cm-j6", at: "20 分钟前", kind: "ai-response", content: "Top 5：重庆鲜花花(0.92) · 西安长安食代(0.88) · 昆明云味(0.83) · 贵阳鲜里多(0.75) · 南宁邕江(0.68)。后两家有舆情风险标记。", fieldRef: "Candidates · Top 5" },
];

const RECENT_JIARUI: RecentScoutSession[] = [
  { id: "rc-j1", benchmark: "成都嘉瑞食品科技 · 新消费上市辅导", updated: "刚刚（当前）", progress: 1.0, stage: "已生成 · 18 推荐" },
];

/* ────────────────────────────────────────────────────────────────────
   导出 · MOCK_SESSIONS_MAP + DEFAULT_SESSION_ID + 兼容用 array
   ──────────────────────────────────────────────────────────────────── */

export const SESS_HAICHAO: ChannelSession = {
  id: "sess_haichao",
  benchmarkName: "上海海潮工业软件 · SaaS B 轮",
  candidateCount: 35,
  stage: "Top 推荐已生成",
  updated: "5 分钟前",
  query: QUERY_HAICHAO,
  signals: SIGNALS_HAICHAO,
  match: { similarity: 0.78, geoInclude: ["上海", "江苏", "浙江"], industryInclude: ["工业软件", "SaaS"], scaleRange: "营收 5K-3 亿", excludeActive: true, excludeRiskTags: ["失信", "被执行"] },
  conversation: CONVERSATION_HAICHAO,
  radar: RADAR_HAICHAO,
  funnel: FUNNEL_HAICHAO,
  candidates: CANDIDATES_HAICHAO,
  qcCounts: { block: 0, warn: 1, info: 3 },
  recentSessions: RECENT_HAICHAO,
};

export const SESS_ZHIRONG: ChannelSession = {
  id: "sess_zhirong",
  benchmarkName: "苏州智荣精密制造 · 智能制造 A 轮",
  candidateCount: 24,
  stage: "Top 推荐已生成",
  updated: "8 分钟前",
  query: QUERY_ZHIRONG,
  signals: SIGNALS_ZHIRONG,
  match: { similarity: 0.74, geoInclude: ["江苏", "浙江"], industryInclude: ["精密机械", "汽车零部件"], scaleRange: "营收 5K 万-1.5 亿", excludeActive: true, excludeRiskTags: ["失信", "被执行", "重大行政处罚"] },
  conversation: CONVERSATION_ZHIRONG,
  radar: RADAR_ZHIRONG,
  funnel: FUNNEL_ZHIRONG,
  candidates: CANDIDATES_ZHIRONG,
  qcCounts: { block: 0, warn: 2, info: 4 },
  recentSessions: RECENT_ZHIRONG,
};

export const SESS_YUEMAO: ChannelSession = {
  id: "sess_yuemao",
  benchmarkName: "深圳粤峰跨境电商 · 成长期",
  candidateCount: 22,
  stage: "Top 推荐已生成",
  updated: "12 分钟前",
  query: QUERY_YUEMAO,
  signals: SIGNALS_YUEMAO,
  match: { similarity: 0.70, geoInclude: ["广东", "福建"], industryInclude: ["跨境电商", "外贸"], scaleRange: "GMV 月 ¥800 万-3,000 万", excludeActive: true, excludeRiskTags: ["失信", "被执行", "境外受限"] },
  conversation: CONVERSATION_YUEMAO,
  radar: RADAR_YUEMAO,
  funnel: FUNNEL_YUEMAO,
  candidates: CANDIDATES_YUEMAO,
  qcCounts: { block: 0, warn: 1, info: 2 },
  recentSessions: RECENT_YUEMAO,
};

export const SESS_KANGYUAN: ChannelSession = {
  id: "sess_kangyuan",
  benchmarkName: "杭州康源生物 · 创新药 Pre-A",
  candidateCount: 12,
  stage: "Top 推荐已生成",
  updated: "20 分钟前",
  query: QUERY_KANGYUAN,
  signals: SIGNALS_KANGYUAN,
  match: { similarity: 0.65, geoInclude: ["上海", "江苏", "浙江"], industryInclude: ["创新药", "生物医药"], scaleRange: "Pre-A / 天使轮", excludeActive: false, excludeRiskTags: ["失信", "被执行", "核心团队不稳"] },
  conversation: CONVERSATION_KANGYUAN,
  radar: RADAR_KANGYUAN,
  funnel: FUNNEL_KANGYUAN,
  candidates: CANDIDATES_KANGYUAN,
  qcCounts: { block: 1, warn: 3, info: 2 },
  recentSessions: RECENT_KANGYUAN,
};

export const SESS_JIARUI: ChannelSession = {
  id: "sess_jiarui",
  benchmarkName: "成都嘉瑞食品科技 · 新消费上市辅导",
  candidateCount: 18,
  stage: "Top 推荐已生成",
  updated: "32 分钟前",
  query: QUERY_JIARUI,
  signals: SIGNALS_JIARUI,
  match: { similarity: 0.72, geoInclude: ["四川", "重庆", "云南", "贵州", "广西"], industryInclude: ["新消费", "连锁餐饮"], scaleRange: "门店 ≥ 100 家 · 营收 ≥ 3 亿", excludeActive: true, excludeRiskTags: ["失信", "被执行", "门店食安投诉 ≥ 10"] },
  conversation: CONVERSATION_JIARUI,
  radar: RADAR_JIARUI,
  funnel: FUNNEL_JIARUI,
  candidates: CANDIDATES_JIARUI,
  qcCounts: { block: 0, warn: 4, info: 5 },
  recentSessions: RECENT_JIARUI,
};

/** Master map · ChannelWorkspace 切下拉 · 5 sessions 标杆企业 */
export const MOCK_SESSIONS_MAP: Record<string, ChannelSession> = {
  [SESS_HAICHAO.id]: SESS_HAICHAO,
  [SESS_ZHIRONG.id]: SESS_ZHIRONG,
  [SESS_YUEMAO.id]: SESS_YUEMAO,
  [SESS_KANGYUAN.id]: SESS_KANGYUAN,
  [SESS_JIARUI.id]: SESS_JIARUI,
};

/** 默认 session id · ChannelWorkspace 初渲染时 selectedSessionId 默认值 */
export const DEFAULT_SESSION_ID = SESS_HAICHAO.id;

/** 历史 session 列表 · QueryBar 下拉用 (id + 显示名) · 顺序固定 5 sessions */
export const MOCK_SESSIONS_LIST: { id: string; benchmark: string }[] = [
  { id: SESS_HAICHAO.id,  benchmark: SESS_HAICHAO.benchmarkName },
  { id: SESS_ZHIRONG.id,  benchmark: SESS_ZHIRONG.benchmarkName },
  { id: SESS_YUEMAO.id,   benchmark: SESS_YUEMAO.benchmarkName },
  { id: SESS_KANGYUAN.id, benchmark: SESS_KANGYUAN.benchmarkName },
  { id: SESS_JIARUI.id,   benchmark: SESS_JIARUI.benchmarkName },
];
