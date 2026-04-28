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

/** B.4b · 候选 vs IdealProfile 单维度匹配命中 (per chip)
 *  - score: 0-100 该维度匹配分（不是 is_match 布尔答案 · 反 5 原则 §3.5）
 *  - hit_evidence: 命中证据来源 (signal id 或 KB ref id) */
export type MatchDimension = {
  id: string;
  dim_name: string;
  display: string;        // chip 显示文案 e.g. "营收 5,000 万 ✓ 匹配 P50 ±20%"
  hit_evidence: string;   // signal id "tl-h1-1" or KB ref "kb-h1"
  score: number;          // 0-100 单维度命中分 · 不是答案
};

/** B.4c · Top3 产品推荐 (per candidate)
 *  - fit_score: 0-100 适配评分 · LLM 后端真生成时填，mock 用 v1 channel_rules 评分
 *  - intro: 1-2 句卖点 (不含客户姓名占位 · 话术单独走 PitchScript) */
export type ProductRec = {
  id: string;
  product_name: string;
  fit_score: number;
  intro: string;          // 1-2 句产品卖点 · 不带客户姓名占位
  amount_range?: string;  // 额度档位 e.g. "500 万 - 3,000 万"
  rate_band?: string;     // 利率档位 e.g. "LPR + 80-150 BP"
};

/** B.4c · 切入话术 (per candidate · 3-5 条)
 *  - customer_name_placeholder: "{{客户姓名}}" or 真实负责人姓名 (LLM 真生成时填) */
export type PitchScript = {
  id: string;
  customer_name_placeholder: string;  // "{{张总}}" or "李工"
  script_text: string;                 // 60-150 字 · 含产品 + 关键卖点 + 政策红利
  product_ref?: string;                // 关联 ProductRec id
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
  /* B.4b/B.4c · drawer 详情区数据 (mock 时均填 · live 时由 SSE done event 注入) */
  match_dimensions?: MatchDimension[];
  product_recommendations?: ProductRec[];
  pitch_scripts?: PitchScript[];
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

/* ── B.4b/B.4c · HAICHAO 候选详情数据 (drawer 区) ────────── */
const MATCH_HAICHAO_C1: MatchDimension[] = [
  { id: "md-h1-1", dim_name: "行业", display: "工业软件 SaaS ✓ 命中标杆", hit_evidence: "kb-h2", score: 96 },
  { id: "md-h1-2", dim_name: "营收体量", display: "ARR 1.8 亿 ✓ 匹配 P50 ±20%", hit_evidence: "tl-h1-1", score: 92 },
  { id: "md-h1-3", dim_name: "成长阶段", display: "B 轮已完成 ✓ 标杆同段", hit_evidence: "tl-h1-1", score: 94 },
  { id: "md-h1-4", dim_name: "地域", display: "长三角 (浙江) ✓ 匹配", hit_evidence: "kb-h3", score: 88 },
  { id: "md-h1-5", dim_name: "资质", display: "专精特新小巨人 ✓ 强关联", hit_evidence: "tl-h1-3", score: 95 },
  { id: "md-h1-6", dim_name: "团队规模", display: "180 人 ✓ 研发占比相近", hit_evidence: "tl-h1-2", score: 86 },
];
const PRODUCTS_HAICHAO_C1: ProductRec[] = [
  { id: "pr-h1-1", product_name: "科创信用贷", fit_score: 94, intro: "针对国家级专精特新企业 · 无抵押 · 凭研发投入与知识产权放款", amount_range: "500 万 - 3,000 万", rate_band: "LPR + 60 BP" },
  { id: "pr-h1-2", product_name: "并购贷款", fit_score: 87, intro: "B+ 轮后 SaaS 企业拓展生态并购首选 · 标的可为客户/技术资产", amount_range: "1,000 万 - 1.5 亿", rate_band: "LPR + 120 BP" },
  { id: "pr-h1-3", product_name: "知识产权质押贷", fit_score: 82, intro: "用核心专利或软著质押 · 适合研发占比 ≥ 50% 的科技公司", amount_range: "300 万 - 1,500 万", rate_band: "LPR + 85 BP" },
];
const PITCH_HAICHAO_C1: PitchScript[] = [
  { id: "ps-h1-1", customer_name_placeholder: "{{张总}}", script_text: "{{张总}}您好 · 我是众安信银行的客户经理 · 看到杭州智云近期 ARR 同比 +92% · 又拿了专精特新小巨人 · 我们行有专门给国家级小巨人的科创信用贷 · 无抵押 · 单笔最高 3000 万 · 想跟您 15 分钟约个茶聊聊", product_ref: "pr-h1-1" },
  { id: "ps-h1-2", customer_name_placeholder: "{{张总}}", script_text: "{{张总}}贵公司这轮融资到位后 · 在并购整合方面是否有动作 · 我行并购贷专门服务 SaaS 行业生态扩张 · 标的可以是客户群、技术、团队 · 上限 1.5 亿 · 利率 LPR+120 BP · 想约个时间过去具体看看", product_ref: "pr-h1-2" },
  { id: "ps-h1-3", customer_name_placeholder: "{{李 CFO}}", script_text: "{{李 CFO}}您好 · 智云的 22 项发明专利 + 软著资产 · 是优质质押物 · 我行知识产权质押贷无需固定资产 · 评估周期 7 天 · 可作为研发现金流补充 · 上限 1500 万 · 您看下周哪天方便聊聊", product_ref: "pr-h1-3" },
];

/* 其他候选简化版 · 各 3 维匹配 + 3 产品 + 3 话术 (反 5 原则 §3.5 难度分层) */
const MATCH_HAICHAO_C2: MatchDimension[] = [
  { id: "md-h2-1", dim_name: "行业", display: "PMC SaaS ✓ 命中子赛道", hit_evidence: "kb-h2", score: 94 },
  { id: "md-h2-2", dim_name: "营收体量", display: "ARR 1.2 亿 ✓ 标杆下沿", hit_evidence: "kb-h1", score: 84 },
  { id: "md-h2-3", dim_name: "地域", display: "苏州 ✓ 长三角核心", hit_evidence: "kb-h3", score: 90 },
  { id: "md-h2-4", dim_name: "资质", display: "国家高新企业 ✓", hit_evidence: "kb-h2", score: 78 },
];
const PRODUCTS_HAICHAO_C2: ProductRec[] = [
  { id: "pr-h2-1", product_name: "科创信用贷", fit_score: 89, intro: "PMC SaaS 是 2026 信贷重点支持方向 · 凭研发投入定额", amount_range: "500 万 - 2,000 万", rate_band: "LPR + 75 BP" },
  { id: "pr-h2-2", product_name: "知识产权质押贷", fit_score: 84, intro: "PMC 软著资产丰厚 · 质押估值高 · 流程快", amount_range: "200 万 - 1,000 万", rate_band: "LPR + 95 BP" },
  { id: "pr-h2-3", product_name: "对公流动资金贷", fit_score: 76, intro: "稳健续贷型企业首选 · 季度还息年度续贷", amount_range: "300 万 - 1,500 万", rate_band: "LPR + 110 BP" },
];
const PITCH_HAICHAO_C2: PitchScript[] = [
  { id: "ps-h2-1", customer_name_placeholder: "{{王总}}", script_text: "{{王总}}您好 · 我是众安信银行的客户经理 · 看到苏州工创最近舆情很积极 · ARR 也站上 1 亿 · 我行有专门给 PMC SaaS 的科创信用贷 · 利率 LPR+75 BP · 想约您简单聊聊", product_ref: "pr-h2-1" },
  { id: "ps-h2-2", customer_name_placeholder: "{{王总}}", script_text: "{{王总}}工创的核心 PMC 系统软著估值 · 我们评估完可做质押贷 · 7 天放款 · 不占用您现有授信额度 · 想跟您过去当面看下", product_ref: "pr-h2-2" },
  { id: "ps-h2-3", customer_name_placeholder: "{{张 CFO}}", script_text: "{{张 CFO}}您好 · SaaS 现金流季节波动较明显 · 我行流贷可季度还息年度续贷 · 不影响您续费节奏 · 哪天方便见面聊", product_ref: "pr-h2-3" },
];

const MATCH_HAICHAO_C3: MatchDimension[] = [
  { id: "md-h3-1", dim_name: "行业", display: "MES + IoT ✓ 工业软件衍生", hit_evidence: "kb-h2", score: 88 },
  { id: "md-h3-2", dim_name: "营收体量", display: "8400 万 · 接近标杆下沿", hit_evidence: "kb-h1", score: 72 },
  { id: "md-h3-3", dim_name: "地域", display: "南京 ✓ 长三角", hit_evidence: "kb-h3", score: 84 },
];
const PRODUCTS_HAICHAO_C3: ProductRec[] = [
  { id: "pr-h3-1", product_name: "科创信用贷", fit_score: 84, intro: "MES + IoT 工业软件双轮驱动 · 政策利好", amount_range: "300 万 - 1,500 万", rate_band: "LPR + 90 BP" },
  { id: "pr-h3-2", product_name: "供应链金融", fit_score: 78, intro: "下游汽车 / 高端制造客户应收账款保理", amount_range: "200 万 - 2,000 万", rate_band: "LPR + 100 BP" },
  { id: "pr-h3-3", product_name: "对公流动资金贷", fit_score: 72, intro: "工业软件项目周期长 · 流贷支持研发到回款衔接", amount_range: "200 万 - 1,000 万", rate_band: "LPR + 115 BP" },
];
const PITCH_HAICHAO_C3: PitchScript[] = [
  { id: "ps-h3-1", customer_name_placeholder: "{{李总}}", script_text: "{{李总}}您好 · 南京菱研最近又中了央企单子 · 我行科创信用贷无需抵押 · 直接看研发投入和招投标流水 · 想约 30 分钟聊聊匹配", product_ref: "pr-h3-1" },
  { id: "ps-h3-2", customer_name_placeholder: "{{李总}}", script_text: "{{李总}}MES 项目下游应收周期普遍 90 天+ · 我行保理可即时回款 · 不增加贵司负债率 · 哪天方便登门拜访", product_ref: "pr-h3-2" },
  { id: "ps-h3-3", customer_name_placeholder: "{{周 CFO}}", script_text: "{{周 CFO}}您好 · 工业软件研发到回款周期长 · 我行流贷可灵活提还 · 季度还息 · 帮您平滑现金流", product_ref: "pr-h3-3" },
];

const CANDIDATES_HAICHAO: Candidate[] = [
  { id: "c-h1", name: "杭州智云工业软件", similarity: 0.94, industry: "工业软件 SaaS", geo: "浙江杭州", scale: "营收 1.8 亿", signals: ["投融资", "招聘", "招投标"], riskTags: [], products: ["科创信用贷", "并购贷"], note: "ARR YoY +92% · A 轮", timeline: TIMELINE_HAICHAO_C1, match_dimensions: MATCH_HAICHAO_C1, product_recommendations: PRODUCTS_HAICHAO_C1, pitch_scripts: PITCH_HAICHAO_C1 },
  { id: "c-h2", name: "苏州工创智能", similarity: 0.91, industry: "PMC SaaS", geo: "江苏苏州", scale: "营收 1.2 亿", signals: ["招聘", "舆情", "纳税"], riskTags: [], products: ["科创信用贷", "知识产权质押贷"], match_dimensions: MATCH_HAICHAO_C2, product_recommendations: PRODUCTS_HAICHAO_C2, pitch_scripts: PITCH_HAICHAO_C2 },
  { id: "c-h3", name: "南京菱研工业", similarity: 0.88, industry: "MES + IoT", geo: "江苏南京", scale: "营收 8,400 万", signals: ["投融资", "招投标"], riskTags: [], products: ["科创信用贷", "供应链金融"], match_dimensions: MATCH_HAICHAO_C3, product_recommendations: PRODUCTS_HAICHAO_C3, pitch_scripts: PITCH_HAICHAO_C3 },
  { id: "c-h4", name: "上海创鼎数控", similarity: 0.84, industry: "数控软件", geo: "上海闵行", scale: "营收 2.4 亿", signals: ["工商", "纳税", "舆情"], riskTags: [], products: ["对公流动资金贷", "贸易融资"], note: "全市场份额 8%", match_dimensions: [{ id: "md-h4-1", dim_name: "行业", display: "数控软件 ✓ 工业软件衍生", hit_evidence: "kb-h2", score: 86 }, { id: "md-h4-2", dim_name: "营收体量", display: "2.4 亿 · 标杆上沿", hit_evidence: "kb-h1", score: 82 }, { id: "md-h4-3", dim_name: "地域", display: "上海 ✓ 标杆同区", hit_evidence: "kb-h3", score: 95 }], product_recommendations: [{ id: "pr-h4-1", product_name: "对公流动资金贷", fit_score: 86, intro: "市场份额 8% 龙头 · 流贷信用授信优先级", amount_range: "1,000 万 - 5,000 万", rate_band: "LPR + 50 BP" }, { id: "pr-h4-2", product_name: "贸易融资", fit_score: 82, intro: "出口工业软件项目 · 收汇 + 押汇组合", amount_range: "300 万 - 2,000 万", rate_band: "LPR + 80 BP" }, { id: "pr-h4-3", product_name: "并购贷款", fit_score: 75, intro: "整合产业链下游小厂 · 拓展数控覆盖", amount_range: "1,000 万 - 1.2 亿", rate_band: "LPR + 130 BP" }], pitch_scripts: [{ id: "ps-h4-1", customer_name_placeholder: "{{陈总}}", script_text: "{{陈总}}您好 · 创鼎在数控软件 8% 份额 · 我行流贷可给到 5000 万 · 利率 LPR+50 BP · 想约时间过去聊匹配方案", product_ref: "pr-h4-1" }, { id: "ps-h4-2", customer_name_placeholder: "{{陈总}}", script_text: "{{陈总}}创鼎海外项目越来越多 · 我行贸易融资可一站式办收汇 + 押汇 · 减少汇率风险 · 哪天方便见面聊", product_ref: "pr-h4-2" }, { id: "ps-h4-3", customer_name_placeholder: "{{孙 CFO}}", script_text: "{{孙 CFO}}您好 · 数控软件行业整合期 · 我行并购贷可作为产业链下游收购弹药 · 上限 1.2 亿 · 想跟您聊聊战略匹配", product_ref: "pr-h4-3" }] },
  { id: "c-h5", name: "无锡澜创工业云", similarity: 0.79, industry: "工业云", geo: "江苏无锡", scale: "营收 6,200 万", signals: ["招聘", "招投标"], riskTags: ["民事诉讼 × 1"], products: ["科创信用贷"], note: "知识产权纠纷待结", match_dimensions: [{ id: "md-h5-1", dim_name: "行业", display: "工业云 ✓ 标杆延伸", hit_evidence: "kb-h2", score: 78 }, { id: "md-h5-2", dim_name: "营收体量", display: "6200 万 · 标杆下沿", hit_evidence: "kb-h1", score: 64 }, { id: "md-h5-3", dim_name: "司法风险", display: "民诉 1 起 · 待结", hit_evidence: "tl-h1-3", score: 45 }], product_recommendations: [{ id: "pr-h5-1", product_name: "科创信用贷", fit_score: 72, intro: "工业云赛道增速快 · 但司法待结需谨慎评估", amount_range: "200 万 - 800 万", rate_band: "LPR + 110 BP" }, { id: "pr-h5-2", product_name: "对公流动资金贷", fit_score: 68, intro: "案件结清后可续 · 现阶段建议小额试单", amount_range: "100 万 - 500 万", rate_band: "LPR + 130 BP" }, { id: "pr-h5-3", product_name: "知识产权质押贷", fit_score: 60, intro: "案件结清后再启 · 当前不适配", amount_range: "200 万 - 800 万", rate_band: "LPR + 100 BP" }], pitch_scripts: [{ id: "ps-h5-1", customer_name_placeholder: "{{周总}}", script_text: "{{周总}}您好 · 澜创工业云有空间 · 但建议先把民诉结清 · 我们小额试单 800 万 · 利率 LPR+110 BP · 想跟您聊下方案", product_ref: "pr-h5-1" }, { id: "ps-h5-2", customer_name_placeholder: "{{周总}}", script_text: "{{周总}}案件结清前 · 我行小额流贷可作过桥 · 上限 500 万 · 用于运营周转 · 待案件结清后即可申请大额", product_ref: "pr-h5-2" }, { id: "ps-h5-3", customer_name_placeholder: "{{张 CFO}}", script_text: "{{张 CFO}}您好 · 现阶段建议先观察 · 待司法明朗后再启知识产权质押贷流程 · 我们一直跟进", product_ref: "pr-h5-3" }] },
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

/* ── B.4b/B.4c · ZHIRONG 候选详情数据 (drawer 区) ──────── */
const MATCH_ZHIRONG_C1: MatchDimension[] = [
  { id: "md-z1-1", dim_name: "行业", display: "精密机械 ✓ 命中标杆", hit_evidence: "kb-z1", score: 95 },
  { id: "md-z1-2", dim_name: "下游客户", display: "宁德时代 ✓ 核心客户穿透", hit_evidence: "tl-z1-1", score: 92 },
  { id: "md-z1-3", dim_name: "营收体量", display: "1.1 亿 ✓ 匹配 P50", hit_evidence: "kb-z2", score: 88 },
  { id: "md-z1-4", dim_name: "地域", display: "江苏无锡 ✓ 长三角", hit_evidence: "kb-z1", score: 90 },
  { id: "md-z1-5", dim_name: "资质", display: "国家高新企业 ✓", hit_evidence: "kb-z3", score: 85 },
];
const PRODUCTS_ZHIRONG_C1: ProductRec[] = [
  { id: "pr-z1-1", product_name: "设备融资租赁", fit_score: 92, intro: "宁德时代订单需新增设备 2800 万 · 我行融资租赁优先级", amount_range: "500 万 - 3,000 万", rate_band: "等额年化 5.4%" },
  { id: "pr-z1-2", product_name: "供应链金融", fit_score: 88, intro: "上游 OEM 应收账款保理 · 90 天回款变 T+1", amount_range: "300 万 - 2,000 万", rate_band: "LPR + 90 BP" },
  { id: "pr-z1-3", product_name: "对公流动资金贷", fit_score: 84, intro: "扩产前置流贷 · 灵活提还", amount_range: "500 万 - 2,500 万", rate_band: "LPR + 80 BP" },
];
const PITCH_ZHIRONG_C1: PitchScript[] = [
  { id: "ps-z1-1", customer_name_placeholder: "{{孙总}}", script_text: "{{孙总}}您好 · 我是众安信银行的客户经理 · 看到精弘中标比亚迪二期 1.2 亿订单 · 设备需求 2800 万 · 我行融资租赁可一站办下来 · 等额年化 5.4% · 想约 30 分钟过去聊聊", product_ref: "pr-z1-1" },
  { id: "ps-z1-2", customer_name_placeholder: "{{孙总}}", script_text: "{{孙总}}比亚迪应收账款回款周期 90 天 · 我行保理可即收即付 · 额度上限 2000 万 · 不影响您与上游的合作 · 哪天方便登门", product_ref: "pr-z1-2" },
  { id: "ps-z1-3", customer_name_placeholder: "{{李 CFO}}", script_text: "{{李 CFO}}您好 · 精弘扩产期间流动资金压力大 · 我行流贷可季度提还 · 上限 2500 万 · 利率 LPR+80 BP · 想跟您具体聊下", product_ref: "pr-z1-3" },
];

const MATCH_ZHIRONG_C2: MatchDimension[] = [
  { id: "md-z2-1", dim_name: "行业", display: "汽车零部件 ✓ 行业风口", hit_evidence: "kb-z2", score: 92 },
  { id: "md-z2-2", dim_name: "营收体量", display: "7200 万 ✓ 匹配 P50", hit_evidence: "kb-z1", score: 84 },
  { id: "md-z2-3", dim_name: "地域", display: "浙江宁波 ✓ 长三角", hit_evidence: "kb-z1", score: 88 },
  { id: "md-z2-4", dim_name: "客户穿透", display: "上汽供应商 ✓", hit_evidence: "kb-z2", score: 86 },
];
const PRODUCTS_ZHIRONG_C2: ProductRec[] = [
  { id: "pr-z2-1", product_name: "对公流动资金贷", fit_score: 88, intro: "汽车零部件季度回款 · 流贷支持淡季运营", amount_range: "500 万 - 2,500 万", rate_band: "LPR + 95 BP" },
  { id: "pr-z2-2", product_name: "应收账款保理", fit_score: 84, intro: "OEM 应收转保理 · 即收即付 · 不增负债", amount_range: "200 万 - 1,500 万", rate_band: "LPR + 100 BP" },
  { id: "pr-z2-3", product_name: "设备融资租赁", fit_score: 76, intro: "扩产升级周期 · 设备资金分期", amount_range: "300 万 - 1,500 万", rate_band: "等额年化 5.6%" },
];
const PITCH_ZHIRONG_C2: PitchScript[] = [
  { id: "ps-z2-1", customer_name_placeholder: "{{陈总}}", script_text: "{{陈总}}您好 · 鸿基作为上汽供应商 · 我行流贷可保平稳运营 · 上限 2500 万 · LPR+95 BP · 想约时间聊", product_ref: "pr-z2-1" },
  { id: "ps-z2-2", customer_name_placeholder: "{{陈总}}", script_text: "{{陈总}}OEM 客户回款周期长 · 我行保理可即收即付 · 上限 1500 万 · 不增贵司负债率 · 哪天方便见面", product_ref: "pr-z2-2" },
  { id: "ps-z2-3", customer_name_placeholder: "{{周 CFO}}", script_text: "{{周 CFO}}您好 · 设备升级压力大 · 我行融资租赁分 36 期 · 等额年化 5.6% · 想跟您具体聊", product_ref: "pr-z2-3" },
];

const MATCH_ZHIRONG_C3: MatchDimension[] = [
  { id: "md-z3-1", dim_name: "行业", display: "数控加工 ✓ 标杆同子赛道", hit_evidence: "kb-z2", score: 86 },
  { id: "md-z3-2", dim_name: "营收体量", display: "5400 万 · 标杆下沿", hit_evidence: "kb-z1", score: 72 },
  { id: "md-z3-3", dim_name: "地域", display: "江苏常州 ✓", hit_evidence: "kb-z1", score: 84 },
];
const PRODUCTS_ZHIRONG_C3: ProductRec[] = [
  { id: "pr-z3-1", product_name: "普惠信用贷", fit_score: 82, intro: "小微制造企业普惠政策 · 利率优惠", amount_range: "100 万 - 500 万", rate_band: "LPR + 50 BP" },
  { id: "pr-z3-2", product_name: "设备融资租赁", fit_score: 78, intro: "数控设备升级专项 · 5 年期分摊", amount_range: "200 万 - 1,000 万", rate_band: "等额年化 5.8%" },
  { id: "pr-z3-3", product_name: "对公流动资金贷", fit_score: 70, intro: "稳定中小企业续贷型流贷", amount_range: "200 万 - 800 万", rate_band: "LPR + 110 BP" },
];
const PITCH_ZHIRONG_C3: PitchScript[] = [
  { id: "ps-z3-1", customer_name_placeholder: "{{王总}}", script_text: "{{王总}}您好 · 毅鼎规模符合普惠信用贷条件 · 利率 LPR+50 BP · 上限 500 万 · 流程 7 天 · 想跟您约时间聊", product_ref: "pr-z3-1" },
  { id: "ps-z3-2", customer_name_placeholder: "{{王总}}", script_text: "{{王总}}数控设备折旧快 · 我行融资租赁分 5 年 · 等额年化 5.8% · 不占贵司流动资金 · 哪天方便见面", product_ref: "pr-z3-2" },
  { id: "ps-z3-3", customer_name_placeholder: "{{李会计}}", script_text: "{{李会计}}您好 · 毅鼎稳健续贷型流贷上限 800 万 · 续贷免审批 · 适合长期合作 · 想跟您介绍下", product_ref: "pr-z3-3" },
];

const CANDIDATES_ZHIRONG: Candidate[] = [
  { id: "c-z1", name: "无锡精弘机械有限公司", similarity: 0.92, industry: "精密机械", geo: "江苏无锡", scale: "营收 1.1 亿", signals: ["招投标", "工商", "纳税"], riskTags: [], products: ["设备融资租赁", "供应链金融", "对公流动资金贷"], note: "宁德时代供应商", timeline: TIMELINE_ZHIRONG_C1, match_dimensions: MATCH_ZHIRONG_C1, product_recommendations: PRODUCTS_ZHIRONG_C1, pitch_scripts: PITCH_ZHIRONG_C1 },
  { id: "c-z2", name: "宁波鸿基汽车零部件", similarity: 0.89, industry: "汽车零部件", geo: "浙江宁波", scale: "营收 7,200 万", signals: ["工商", "招投标"], riskTags: [], products: ["对公流动资金贷", "应收账款保理"], match_dimensions: MATCH_ZHIRONG_C2, product_recommendations: PRODUCTS_ZHIRONG_C2, pitch_scripts: PITCH_ZHIRONG_C2 },
  { id: "c-z3", name: "常州毅鼎数控", similarity: 0.86, industry: "数控加工", geo: "江苏常州", scale: "营收 5,400 万", signals: ["纳税", "招聘", "社保"], riskTags: [], products: ["普惠信用贷", "设备融资租赁"], match_dimensions: MATCH_ZHIRONG_C3, product_recommendations: PRODUCTS_ZHIRONG_C3, pitch_scripts: PITCH_ZHIRONG_C3 },
  { id: "c-z4", name: "嘉兴铭锐精密", similarity: 0.81, industry: "精密铸件", geo: "浙江嘉兴", scale: "营收 3,800 万", signals: ["工商", "纳税"], riskTags: ["行政处罚 × 1"], products: ["对公流动资金贷"], note: "环保整改已结清", match_dimensions: [{ id: "md-z4-1", dim_name: "行业", display: "精密铸件 ✓ 标杆衍生", hit_evidence: "kb-z2", score: 80 }, { id: "md-z4-2", dim_name: "营收体量", display: "3800 万 · 中小企业", hit_evidence: "kb-z1", score: 64 }, { id: "md-z4-3", dim_name: "合规", display: "环保整改已结清", hit_evidence: "kb-z3", score: 70 }], product_recommendations: [{ id: "pr-z4-1", product_name: "对公流动资金贷", fit_score: 75, intro: "整改后续贷型企业 · 稳健流贷", amount_range: "200 万 - 800 万", rate_band: "LPR + 120 BP" }, { id: "pr-z4-2", product_name: "普惠信用贷", fit_score: 68, intro: "小微企业普惠 · 利率优惠", amount_range: "100 万 - 500 万", rate_band: "LPR + 60 BP" }, { id: "pr-z4-3", product_name: "应收账款保理", fit_score: 62, intro: "下游应收账款转化", amount_range: "100 万 - 500 万", rate_band: "LPR + 110 BP" }], pitch_scripts: [{ id: "ps-z4-1", customer_name_placeholder: "{{马总}}", script_text: "{{马总}}您好 · 铭锐环保整改完毕 · 我行流贷支持续贷型企业 · 上限 800 万 · 想约时间聊", product_ref: "pr-z4-1" }, { id: "ps-z4-2", customer_name_placeholder: "{{马总}}", script_text: "{{马总}}规模符合普惠信用贷 · 利率 LPR+60 BP · 流程 7 天 · 适合短期周转", product_ref: "pr-z4-2" }, { id: "ps-z4-3", customer_name_placeholder: "{{周会计}}", script_text: "{{周会计}}您好 · 应收账款转保理可即收即付 · 上限 500 万 · 哪天方便看下", product_ref: "pr-z4-3" }] },
  { id: "c-z5", name: "扬州瑞翔模具", similarity: 0.76, industry: "汽车模具", geo: "江苏扬州", scale: "营收 2,600 万", signals: ["招投标", "招聘"], riskTags: [], products: ["普惠信用贷"], note: "上汽供应商资格", match_dimensions: [{ id: "md-z5-1", dim_name: "行业", display: "汽车模具 ✓", hit_evidence: "kb-z2", score: 82 }, { id: "md-z5-2", dim_name: "营收体量", display: "2600 万 · 微小企业", hit_evidence: "kb-z1", score: 56 }, { id: "md-z5-3", dim_name: "客户穿透", display: "上汽供应商 ✓", hit_evidence: "kb-z2", score: 78 }], product_recommendations: [{ id: "pr-z5-1", product_name: "普惠信用贷", fit_score: 78, intro: "上汽供应商微小企业普惠优先 · 利率优惠", amount_range: "50 万 - 300 万", rate_band: "LPR + 40 BP" }, { id: "pr-z5-2", product_name: "应收账款保理", fit_score: 68, intro: "上汽应收账款转保理 · 即收即付", amount_range: "50 万 - 300 万", rate_band: "LPR + 95 BP" }, { id: "pr-z5-3", product_name: "对公流动资金贷", fit_score: 60, intro: "短期周转流贷", amount_range: "50 万 - 200 万", rate_band: "LPR + 130 BP" }], pitch_scripts: [{ id: "ps-z5-1", customer_name_placeholder: "{{曹总}}", script_text: "{{曹总}}您好 · 上汽供应商资格 + 普惠政策 · 我行可批 300 万信用贷 · 利率 LPR+40 BP · 想约时间", product_ref: "pr-z5-1" }, { id: "ps-z5-2", customer_name_placeholder: "{{曹总}}", script_text: "{{曹总}}上汽应收账款保理 · 上限 300 万 · 即收即付 · 不增负债率 · 哪天方便见面", product_ref: "pr-z5-2" }, { id: "ps-z5-3", customer_name_placeholder: "{{周 CFO}}", script_text: "{{周 CFO}}您好 · 短期周转流贷上限 200 万 · 流程快 · 适合订单淡旺季", product_ref: "pr-z5-3" }] },
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

/* ── B.4b/B.4c · YUEMAO 候选详情数据 (drawer 区) ─────── */
const MATCH_YUEMAO_C1: MatchDimension[] = [
  { id: "md-y1-1", dim_name: "行业", display: "跨境电商 3C ✓ 命中标杆", hit_evidence: "kb-y1", score: 95 },
  { id: "md-y1-2", dim_name: "GMV 体量", display: "月 1800 万 · 标杆下沿", hit_evidence: "kb-y2", score: 78 },
  { id: "md-y1-3", dim_name: "平台", display: "亚马逊优秀卖家 ✓", hit_evidence: "tl-y1-1", score: 92 },
  { id: "md-y1-4", dim_name: "地域", display: "广州 ✓ 珠三角", hit_evidence: "kb-y3", score: 88 },
  { id: "md-y1-5", dim_name: "出口结构", display: "出口占比 92% ✓", hit_evidence: "tl-y1-1", score: 90 },
];
const PRODUCTS_YUEMAO_C1: ProductRec[] = [
  { id: "pr-y1-1", product_name: "跨境电商信用贷", fit_score: 94, intro: "亚马逊优秀卖家流水绑定 · 凭出口数据放款 · 无抵押", amount_range: "200 万 - 1,500 万", rate_band: "LPR + 80 BP" },
  { id: "pr-y1-2", product_name: "出口退税融资", fit_score: 88, intro: "出口退税款提前融资 · 当季退税到账即还", amount_range: "100 万 - 800 万", rate_band: "LPR + 70 BP" },
  { id: "pr-y1-3", product_name: "应收账款保理", fit_score: 82, intro: "海外仓 + 平台账期保理 · 加速回笼", amount_range: "200 万 - 1,000 万", rate_band: "LPR + 100 BP" },
];
const PITCH_YUEMAO_C1: PitchScript[] = [
  { id: "ps-y1-1", customer_name_placeholder: "{{林总}}", script_text: "{{林总}}您好 · 我是众安信银行的客户经理 · 看到海森拿了亚马逊优秀卖家 · Q1 退税 180 万到账 · 我行跨境电商信用贷可凭流水放款 · 上限 1500 万 · LPR+80 BP · 想约 30 分钟见面聊", product_ref: "pr-y1-1" },
  { id: "ps-y1-2", customer_name_placeholder: "{{林总}}", script_text: "{{林总}}下次出口退税还要等 3 个月 · 我行出口退税融资可立即提前 · 上限 800 万 · 利率 LPR+70 BP · 退税到账即还 · 哪天方便见", product_ref: "pr-y1-2" },
  { id: "ps-y1-3", customer_name_placeholder: "{{陈 CFO}}", script_text: "{{陈 CFO}}您好 · 海森海外仓应收周期长 · 我行保理可加速回笼 · 上限 1000 万 · 不增贵司负债率 · 想跟您聊聊", product_ref: "pr-y1-3" },
];

const MATCH_YUEMAO_C2: MatchDimension[] = [
  { id: "md-y2-1", dim_name: "行业", display: "跨境电商家居 ✓ 标杆同档", hit_evidence: "kb-y1", score: 88 },
  { id: "md-y2-2", dim_name: "GMV 体量", display: "月 1200 万 · 中等档", hit_evidence: "kb-y2", score: 72 },
  { id: "md-y2-3", dim_name: "地域", display: "深圳 ✓ 标杆同区", hit_evidence: "kb-y3", score: 95 },
];
const PRODUCTS_YUEMAO_C2: ProductRec[] = [
  { id: "pr-y2-1", product_name: "跨境电商信用贷", fit_score: 86, intro: "深圳跨境电商集群优势 · 信用贷优先级", amount_range: "150 万 - 1,000 万", rate_band: "LPR + 90 BP" },
  { id: "pr-y2-2", product_name: "供应链金融", fit_score: 78, intro: "上游工厂应付账款融资", amount_range: "100 万 - 800 万", rate_band: "LPR + 100 BP" },
  { id: "pr-y2-3", product_name: "出口退税融资", fit_score: 72, intro: "退税款提前融资", amount_range: "100 万 - 500 万", rate_band: "LPR + 80 BP" },
];
const PITCH_YUEMAO_C2: PitchScript[] = [
  { id: "ps-y2-1", customer_name_placeholder: "{{张总}}", script_text: "{{张总}}您好 · 锐启在深圳跨境电商优势区 · 我行跨境信用贷可上限 1000 万 · LPR+90 BP · 想约时间聊", product_ref: "pr-y2-1" },
  { id: "ps-y2-2", customer_name_placeholder: "{{张总}}", script_text: "{{张总}}上游工厂应付占款大 · 我行供应链金融可分期付款 · 上限 800 万 · 哪天方便见", product_ref: "pr-y2-2" },
  { id: "ps-y2-3", customer_name_placeholder: "{{周会计}}", script_text: "{{周会计}}您好 · 退税款提前融资可缓现金流 · 上限 500 万 · 想跟您聊", product_ref: "pr-y2-3" },
];

const MATCH_YUEMAO_C3: MatchDimension[] = [
  { id: "md-y3-1", dim_name: "行业", display: "跨境电商 3C ✓ 命中", hit_evidence: "kb-y1", score: 90 },
  { id: "md-y3-2", dim_name: "GMV 体量", display: "月 980 万 · 中等档", hit_evidence: "kb-y2", score: 70 },
  { id: "md-y3-3", dim_name: "地域", display: "东莞 ✓ 珠三角", hit_evidence: "kb-y3", score: 86 },
];
const PRODUCTS_YUEMAO_C3: ProductRec[] = [
  { id: "pr-y3-1", product_name: "跨境电商信用贷", fit_score: 82, intro: "东莞 3C 集群 · 流水信用贷优先", amount_range: "100 万 - 800 万", rate_band: "LPR + 95 BP" },
  { id: "pr-y3-2", product_name: "出口退税融资", fit_score: 76, intro: "退税款融资 · 周转灵活", amount_range: "50 万 - 500 万", rate_band: "LPR + 80 BP" },
  { id: "pr-y3-3", product_name: "应收账款保理", fit_score: 68, intro: "海外仓应收转保理", amount_range: "50 万 - 500 万", rate_band: "LPR + 110 BP" },
];
const PITCH_YUEMAO_C3: PitchScript[] = [
  { id: "ps-y3-1", customer_name_placeholder: "{{黄总}}", script_text: "{{黄总}}您好 · 雅创跨境信用贷上限 800 万 · LPR+95 BP · 想约 30 分钟过去聊", product_ref: "pr-y3-1" },
  { id: "ps-y3-2", customer_name_placeholder: "{{黄总}}", script_text: "{{黄总}}退税款融资上限 500 万 · 退税到账即还 · 哪天方便见面", product_ref: "pr-y3-2" },
  { id: "ps-y3-3", customer_name_placeholder: "{{李 CFO}}", script_text: "{{李 CFO}}您好 · 海外仓应收账款保理 · 上限 500 万 · 想跟您聊聊", product_ref: "pr-y3-3" },
];

const CANDIDATES_YUEMAO: Candidate[] = [
  { id: "c-y1", name: "广州海森数码贸易", similarity: 0.93, industry: "跨境电商 3C", geo: "广东广州", scale: "GMV 月 ¥1,800 万", signals: ["纳税", "舆情", "工商"], riskTags: [], products: ["跨境信用贷", "应收账款保理"], note: "亚马逊优秀卖家", timeline: TIMELINE_YUEMAO_C1, match_dimensions: MATCH_YUEMAO_C1, product_recommendations: PRODUCTS_YUEMAO_C1, pitch_scripts: PITCH_YUEMAO_C1 },
  { id: "c-y2", name: "深圳锐启国际贸易", similarity: 0.88, industry: "跨境电商家居", geo: "广东深圳", scale: "GMV 月 ¥1,200 万", signals: ["工商", "纳税"], riskTags: [], products: ["跨境信用贷", "供应链金融"], match_dimensions: MATCH_YUEMAO_C2, product_recommendations: PRODUCTS_YUEMAO_C2, pitch_scripts: PITCH_YUEMAO_C2 },
  { id: "c-y3", name: "东莞雅创外贸", similarity: 0.84, industry: "跨境电商 3C", geo: "广东东莞", scale: "GMV 月 ¥980 万", signals: ["招聘", "纳税"], riskTags: [], products: ["跨境信用贷", "出口退税融资"], match_dimensions: MATCH_YUEMAO_C3, product_recommendations: PRODUCTS_YUEMAO_C3, pitch_scripts: PITCH_YUEMAO_C3 },
  { id: "c-y4", name: "厦门启源跨境", similarity: 0.78, industry: "跨境电商服装", geo: "福建厦门", scale: "GMV 月 ¥760 万", signals: ["工商", "舆情"], riskTags: [], products: ["跨境信用贷"], match_dimensions: [{ id: "md-y4-1", dim_name: "行业", display: "跨境电商服装 · 标杆衍生", hit_evidence: "kb-y1", score: 75 }, { id: "md-y4-2", dim_name: "GMV 体量", display: "月 760 万 · 标杆下沿", hit_evidence: "kb-y2", score: 60 }, { id: "md-y4-3", dim_name: "地域", display: "厦门 · 闽南", hit_evidence: "kb-y3", score: 70 }], product_recommendations: [{ id: "pr-y4-1", product_name: "跨境电商信用贷", fit_score: 76, intro: "服装类电商 · 季节性流水", amount_range: "50 万 - 500 万", rate_band: "LPR + 100 BP" }, { id: "pr-y4-2", product_name: "出口退税融资", fit_score: 70, intro: "退税款融资 · 应季周转", amount_range: "50 万 - 300 万", rate_band: "LPR + 85 BP" }, { id: "pr-y4-3", product_name: "应收账款保理", fit_score: 62, intro: "海外仓应收账款保理", amount_range: "50 万 - 300 万", rate_band: "LPR + 115 BP" }], pitch_scripts: [{ id: "ps-y4-1", customer_name_placeholder: "{{许总}}", script_text: "{{许总}}您好 · 启源服装类目 · 我行季节性信用贷上限 500 万 · 想约时间聊", product_ref: "pr-y4-1" }, { id: "ps-y4-2", customer_name_placeholder: "{{许总}}", script_text: "{{许总}}退税款融资上限 300 万 · 应季周转 · 哪天方便见面", product_ref: "pr-y4-2" }, { id: "ps-y4-3", customer_name_placeholder: "{{钱会计}}", script_text: "{{钱会计}}您好 · 海外仓应收保理 · 上限 300 万 · 想聊", product_ref: "pr-y4-3" }] },
  { id: "c-y5", name: "杭州萌芯跨境", similarity: 0.72, industry: "跨境电商小家电", geo: "浙江杭州", scale: "GMV 月 ¥620 万", signals: ["纳税", "招聘"], riskTags: ["民事诉讼 × 1"], products: ["跨境信用贷"], note: "侵权纠纷已和解", match_dimensions: [{ id: "md-y5-1", dim_name: "行业", display: "跨境电商小家电 · 标杆延伸", hit_evidence: "kb-y1", score: 68 }, { id: "md-y5-2", dim_name: "GMV 体量", display: "月 620 万 · 微小", hit_evidence: "kb-y2", score: 55 }, { id: "md-y5-3", dim_name: "司法风险", display: "侵权纠纷已和解", hit_evidence: "kb-y3", score: 60 }], product_recommendations: [{ id: "pr-y5-1", product_name: "跨境电商信用贷", fit_score: 70, intro: "和解后续贷型 · 小额试单", amount_range: "30 万 - 200 万", rate_band: "LPR + 130 BP" }, { id: "pr-y5-2", product_name: "出口退税融资", fit_score: 65, intro: "退税款融资 · 短期周转", amount_range: "30 万 - 200 万", rate_band: "LPR + 95 BP" }, { id: "pr-y5-3", product_name: "应收账款保理", fit_score: 58, intro: "应收账款保理 · 小额", amount_range: "20 万 - 150 万", rate_band: "LPR + 120 BP" }], pitch_scripts: [{ id: "ps-y5-1", customer_name_placeholder: "{{钱总}}", script_text: "{{钱总}}您好 · 纠纷已和解 · 我行小额信用贷可作过桥 · 上限 200 万 · 想约时间聊", product_ref: "pr-y5-1" }, { id: "ps-y5-2", customer_name_placeholder: "{{钱总}}", script_text: "{{钱总}}退税融资 200 万 · 短期周转 · 哪天方便见面", product_ref: "pr-y5-2" }, { id: "ps-y5-3", customer_name_placeholder: "{{林会计}}", script_text: "{{林会计}}您好 · 小额保理 150 万 · 想聊聊", product_ref: "pr-y5-3" }] },
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

/* ── B.4b/B.4c · KANGYUAN 候选详情数据 (drawer 区) ─────── */
const MATCH_KANGYUAN_C1: MatchDimension[] = [
  { id: "md-k1-1", dim_name: "行业", display: "创新药单抗 ✓ 命中标杆", hit_evidence: "kb-k1", score: 92 },
  { id: "md-k1-2", dim_name: "管线进度", display: "4 条管线 · 临床 1 期 1 条", hit_evidence: "tl-k1-2", score: 86 },
  { id: "md-k1-3", dim_name: "成长阶段", display: "Pre-A 已完成 ✓", hit_evidence: "tl-k1-1", score: 90 },
  { id: "md-k1-4", dim_name: "地域", display: "上海张江 ✓ 生医集群", hit_evidence: "kb-k2", score: 95 },
  { id: "md-k1-5", dim_name: "资质", display: "国家高新 + BIOBAY ✓", hit_evidence: "kb-k2", score: 88 },
];
const PRODUCTS_KANGYUAN_C1: ProductRec[] = [
  { id: "pr-k1-1", product_name: "投贷联动", fit_score: 92, intro: "Pre-A 后向 A 轮过渡的研发期专项 · 银行 + VC 同步注资", amount_range: "300 万 - 1,500 万", rate_band: "LPR + 100 BP + 股权认购" },
  { id: "pr-k1-2", product_name: "科创信用贷", fit_score: 85, intro: "凭管线进度 + 临床批件 + 团队评估放款 · 无抵押", amount_range: "200 万 - 1,000 万", rate_band: "LPR + 120 BP" },
  { id: "pr-k1-3", product_name: "知识产权质押贷", fit_score: 78, intro: "22 项专利 + 商标可质押 · 流程 14 天", amount_range: "100 万 - 600 万", rate_band: "LPR + 130 BP" },
];
const PITCH_KANGYUAN_C1: PitchScript[] = [
  { id: "ps-k1-1", customer_name_placeholder: "{{钱博士}}", script_text: "{{钱博士}}您好 · 我是众安信银行的客户经理 · 看到源辰拿了 Pre-A 6000 万 · 主管线 BG-2024 拿到临床批件 · 我行投贷联动可在 A 轮前补仓 1500 万 · 银行 + VC 同步参与 · 想约 30 分钟见面聊", product_ref: "pr-k1-1" },
  { id: "ps-k1-2", customer_name_placeholder: "{{钱博士}}", script_text: "{{钱博士}}研发期现金流压力大 · 我行科创信用贷凭管线进度评估 · 上限 1000 万 · LPR+120 BP · 不要求营收 · 哪天方便聊", product_ref: "pr-k1-2" },
  { id: "ps-k1-3", customer_name_placeholder: "{{孙 CFO}}", script_text: "{{孙 CFO}}您好 · 源辰 22 项专利可质押融资 · 上限 600 万 · 流程 14 天 · 不占用现有授信 · 想跟您聊", product_ref: "pr-k1-3" },
];

const MATCH_KANGYUAN_C2: MatchDimension[] = [
  { id: "md-k2-1", dim_name: "行业", display: "ADC 偶联药 ✓ 创新药细分", hit_evidence: "kb-k1", score: 88 },
  { id: "md-k2-2", dim_name: "成长阶段", display: "天使轮 · 标杆下沿", hit_evidence: "kb-k1", score: 64 },
  { id: "md-k2-3", dim_name: "地域", display: "苏州 ✓ 长三角生医", hit_evidence: "kb-k2", score: 86 },
];
const PRODUCTS_KANGYUAN_C2: ProductRec[] = [
  { id: "pr-k2-1", product_name: "投贷联动", fit_score: 82, intro: "天使轮后向 Pre-A 过渡 · 早期联动", amount_range: "100 万 - 800 万", rate_band: "LPR + 110 BP + 股权" },
  { id: "pr-k2-2", product_name: "知识产权质押贷", fit_score: 78, intro: "ADC 专利质押 · 早期可估值", amount_range: "100 万 - 500 万", rate_band: "LPR + 130 BP" },
  { id: "pr-k2-3", product_name: "科创信用贷", fit_score: 72, intro: "天使期适用 · 评估管线进度", amount_range: "80 万 - 400 万", rate_band: "LPR + 140 BP" },
];
const PITCH_KANGYUAN_C2: PitchScript[] = [
  { id: "ps-k2-1", customer_name_placeholder: "{{周教授}}", script_text: "{{周教授}}您好 · 盛泽 ADC 赛道有空间 · 我行投贷联动早期可介入 · 上限 800 万 · 想约 30 分钟过去", product_ref: "pr-k2-1" },
  { id: "ps-k2-2", customer_name_placeholder: "{{周教授}}", script_text: "{{周教授}}ADC 专利评估高 · 我行质押贷可即估即放 · 上限 500 万 · 哪天方便见", product_ref: "pr-k2-2" },
  { id: "ps-k2-3", customer_name_placeholder: "{{李博士}}", script_text: "{{李博士}}您好 · 早期管线评估科创信用贷 · 上限 400 万 · 想跟您聊", product_ref: "pr-k2-3" },
];

const MATCH_KANGYUAN_C3: MatchDimension[] = [
  { id: "md-k3-1", dim_name: "行业", display: "小分子靶向 ✓ 创新药", hit_evidence: "kb-k1", score: 84 },
  { id: "md-k3-2", dim_name: "成长阶段", display: "天使轮 · 早期", hit_evidence: "kb-k1", score: 60 },
  { id: "md-k3-3", dim_name: "地域", display: "无锡 · 长三角", hit_evidence: "kb-k2", score: 78 },
];
const PRODUCTS_KANGYUAN_C3: ProductRec[] = [
  { id: "pr-k3-1", product_name: "投贷联动", fit_score: 78, intro: "天使期投贷联动 · 早期介入", amount_range: "100 万 - 500 万", rate_band: "LPR + 120 BP + 股权" },
  { id: "pr-k3-2", product_name: "科创信用贷", fit_score: 72, intro: "凭管线 + 团队评估", amount_range: "50 万 - 300 万", rate_band: "LPR + 140 BP" },
  { id: "pr-k3-3", product_name: "知识产权质押贷", fit_score: 65, intro: "早期专利质押 · 估值有限", amount_range: "50 万 - 200 万", rate_band: "LPR + 150 BP" },
];
const PITCH_KANGYUAN_C3: PitchScript[] = [
  { id: "ps-k3-1", customer_name_placeholder: "{{李博士}}", script_text: "{{李博士}}您好 · 灵药小分子靶向 · 我行早期投贷联动 · 上限 500 万 · 想约时间聊", product_ref: "pr-k3-1" },
  { id: "ps-k3-2", customer_name_placeholder: "{{李博士}}", script_text: "{{李博士}}早期科创信用贷 · 凭管线评估 · 上限 300 万 · 哪天方便见", product_ref: "pr-k3-2" },
  { id: "ps-k3-3", customer_name_placeholder: "{{孙 CFO}}", script_text: "{{孙 CFO}}您好 · 早期专利质押 · 上限 200 万 · 想聊", product_ref: "pr-k3-3" },
];

const CANDIDATES_KANGYUAN: Candidate[] = [
  { id: "c-k1", name: "上海源辰生物医药", similarity: 0.86, industry: "创新药 · 单抗", geo: "上海张江", scale: "Pre-A 已完成", signals: ["投融资", "招聘", "资质"], riskTags: [], products: ["科创信用贷", "投贷联动"], note: "管线 4 条 · 临床 1 期 1 条", timeline: TIMELINE_KANGYUAN_C1, match_dimensions: MATCH_KANGYUAN_C1, product_recommendations: PRODUCTS_KANGYUAN_C1, pitch_scripts: PITCH_KANGYUAN_C1 },
  { id: "c-k2", name: "苏州盛泽医药科技", similarity: 0.82, industry: "ADC · 偶联药", geo: "江苏苏州", scale: "天使轮", signals: ["投融资", "招聘"], riskTags: [], products: ["科创信用贷", "知识产权质押贷"], match_dimensions: MATCH_KANGYUAN_C2, product_recommendations: PRODUCTS_KANGYUAN_C2, pitch_scripts: PITCH_KANGYUAN_C2 },
  { id: "c-k3", name: "无锡灵药生物", similarity: 0.76, industry: "小分子靶向", geo: "江苏无锡", scale: "天使轮", signals: ["投融资", "舆情"], riskTags: [], products: ["科创信用贷"], match_dimensions: MATCH_KANGYUAN_C3, product_recommendations: PRODUCTS_KANGYUAN_C3, pitch_scripts: PITCH_KANGYUAN_C3 },
  { id: "c-k4", name: "杭州博睿基因", similarity: 0.71, industry: "基因治疗", geo: "浙江杭州", scale: "种子轮", signals: ["招聘", "工商"], riskTags: ["核心团队不稳"], products: ["科创信用贷"], note: "联合创始人变更 · 谨慎", match_dimensions: [{ id: "md-k4-1", dim_name: "行业", display: "基因治疗 · 创新药细分", hit_evidence: "kb-k1", score: 78 }, { id: "md-k4-2", dim_name: "成长阶段", display: "种子轮 · 极早期", hit_evidence: "kb-k1", score: 50 }, { id: "md-k4-3", dim_name: "团队风险", display: "联合创始人变更 · 待观察", hit_evidence: "kb-k3", score: 40 }], product_recommendations: [{ id: "pr-k4-1", product_name: "投贷联动", fit_score: 70, intro: "团队稳定后再启 · 当前观望", amount_range: "50 万 - 300 万", rate_band: "LPR + 150 BP + 股权" }, { id: "pr-k4-2", product_name: "知识产权质押贷", fit_score: 60, intro: "已有专利可估 · 但估值偏低", amount_range: "30 万 - 200 万", rate_band: "LPR + 160 BP" }, { id: "pr-k4-3", product_name: "科创信用贷", fit_score: 55, intro: "需团队稳定后评估", amount_range: "30 万 - 150 万", rate_band: "LPR + 170 BP" }], pitch_scripts: [{ id: "ps-k4-1", customer_name_placeholder: "{{冯总}}", script_text: "{{冯总}}您好 · 博睿在团队稳定后我行可启动投贷联动 · 上限 300 万 · 想跟您聊聊时间表", product_ref: "pr-k4-1" }, { id: "ps-k4-2", customer_name_placeholder: "{{冯总}}", script_text: "{{冯总}}专利质押小额可启 · 上限 200 万 · 哪天方便见面", product_ref: "pr-k4-2" }, { id: "ps-k4-3", customer_name_placeholder: "{{张博士}}", script_text: "{{张博士}}您好 · 待团队稳定后科创信用贷再启 · 我们先保持联络", product_ref: "pr-k4-3" }] },
  { id: "c-k5", name: "南京泰生医药", similarity: 0.66, industry: "细胞治疗 CAR-T", geo: "江苏南京", scale: "种子轮", signals: ["投融资"], riskTags: ["临床进度滞后"], products: ["科创信用贷"], note: "管线 1 期临床中", match_dimensions: [{ id: "md-k5-1", dim_name: "行业", display: "CAR-T 细胞治疗 · 高门槛", hit_evidence: "kb-k1", score: 75 }, { id: "md-k5-2", dim_name: "成长阶段", display: "种子轮 · 早期", hit_evidence: "kb-k1", score: 48 }, { id: "md-k5-3", dim_name: "临床风险", display: "进度滞后 · 1 期延期", hit_evidence: "kb-k3", score: 38 }], product_recommendations: [{ id: "pr-k5-1", product_name: "投贷联动", fit_score: 65, intro: "等临床推进 · 暂缓动作", amount_range: "30 万 - 200 万", rate_band: "LPR + 150 BP + 股权" }, { id: "pr-k5-2", product_name: "知识产权质押贷", fit_score: 56, intro: "CAR-T 专利可估 · 估值波动大", amount_range: "20 万 - 150 万", rate_band: "LPR + 170 BP" }, { id: "pr-k5-3", product_name: "科创信用贷", fit_score: 50, intro: "等临床转入 2 期再评", amount_range: "20 万 - 100 万", rate_band: "LPR + 180 BP" }], pitch_scripts: [{ id: "ps-k5-1", customer_name_placeholder: "{{孟总}}", script_text: "{{孟总}}您好 · 泰生临床进度待加快 · 我行投贷联动暂缓 · 待 2 期推进后再聊 · 我们先保持联络", product_ref: "pr-k5-1" }, { id: "ps-k5-2", customer_name_placeholder: "{{孟总}}", script_text: "{{孟总}}CAR-T 专利可质押 · 但估值波动大 · 上限 150 万 · 哪天方便聊", product_ref: "pr-k5-2" }, { id: "ps-k5-3", customer_name_placeholder: "{{周博士}}", script_text: "{{周博士}}您好 · 等 2 期临床数据再评信用贷 · 我们一直跟进", product_ref: "pr-k5-3" }] },
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

/* ── B.4b/B.4c · JIARUI 候选详情数据 (drawer 区) ─────── */
const MATCH_JIARUI_C1: MatchDimension[] = [
  { id: "md-j1-1", dim_name: "行业", display: "新消费茶饮 ✓ 标杆同档", hit_evidence: "kb-j1", score: 90 },
  { id: "md-j1-2", dim_name: "门店规模", display: "320 家 ✓ 匹配标杆", hit_evidence: "kb-j2", score: 88 },
  { id: "md-j1-3", dim_name: "复购率", display: "38% ✓ 标杆下沿", hit_evidence: "kb-j3", score: 78 },
  { id: "md-j1-4", dim_name: "地域", display: "重庆 ✓ 西南核心", hit_evidence: "kb-j2", score: 92 },
  { id: "md-j1-5", dim_name: "成长阶段", display: "扩张期 ✓ 接近上市辅导", hit_evidence: "tl-j1-2", score: 84 },
];
const PRODUCTS_JIARUI_C1: ProductRec[] = [
  { id: "pr-j1-1", product_name: "上市辅导信用贷", fit_score: 92, intro: "扩张期向上市过渡专项 · 凭门店流水 + 估值放款", amount_range: "1,000 万 - 5,000 万", rate_band: "LPR + 60 BP" },
  { id: "pr-j1-2", product_name: "并购贷款", fit_score: 86, intro: "整合上下游或同业并购 · 标的可为门店 / 央厨", amount_range: "1,000 万 - 1.5 亿", rate_band: "LPR + 100 BP" },
  { id: "pr-j1-3", product_name: "对公流动资金贷", fit_score: 80, intro: "扩张期门店开业流动资金", amount_range: "500 万 - 3,000 万", rate_band: "LPR + 80 BP" },
];
const PITCH_JIARUI_C1: PitchScript[] = [
  { id: "ps-j1-1", customer_name_placeholder: "{{邓总}}", script_text: "{{邓总}}您好 · 我是众安信银行的客户经理 · 看到鲜花花门店突破 320 家 · 已进入扩张期 · 我行有专门给上市辅导期的信用贷 · 上限 5000 万 · LPR+60 BP · 想约 30 分钟见面聊", product_ref: "pr-j1-1" },
  { id: "ps-j1-2", customer_name_placeholder: "{{邓总}}", script_text: "{{邓总}}行业整合期 · 鲜花花并购弹药需求大 · 我行并购贷上限 1.5 亿 · 标的可为门店 / 央厨 / 同业 · 哪天方便聊", product_ref: "pr-j1-2" },
  { id: "ps-j1-3", customer_name_placeholder: "{{林 CFO}}", script_text: "{{林 CFO}}您好 · 新店开业前期占款大 · 我行流贷上限 3000 万 · 季度还息 · 不影响门店扩张节奏 · 想跟您聊", product_ref: "pr-j1-3" },
];

const MATCH_JIARUI_C2: MatchDimension[] = [
  { id: "md-j2-1", dim_name: "行业", display: "新消费中式快餐 · 标杆衍生", hit_evidence: "kb-j1", score: 85 },
  { id: "md-j2-2", dim_name: "门店规模", display: "280 家 ✓ 标杆下沿", hit_evidence: "kb-j2", score: 82 },
  { id: "md-j2-3", dim_name: "地域", display: "西安 · 西北扩张", hit_evidence: "kb-j2", score: 78 },
];
const PRODUCTS_JIARUI_C2: ProductRec[] = [
  { id: "pr-j2-1", product_name: "对公流动资金贷", fit_score: 84, intro: "扩张期流贷 · 季度还息", amount_range: "500 万 - 2,500 万", rate_band: "LPR + 90 BP" },
  { id: "pr-j2-2", product_name: "中长期固贷", fit_score: 78, intro: "央厨建设 · 5 年期分摊", amount_range: "500 万 - 3,000 万", rate_band: "LPR + 110 BP" },
  { id: "pr-j2-3", product_name: "并购贷款", fit_score: 70, intro: "区域整合贷款", amount_range: "500 万 - 5,000 万", rate_band: "LPR + 120 BP" },
];
const PITCH_JIARUI_C2: PitchScript[] = [
  { id: "ps-j2-1", customer_name_placeholder: "{{秦总}}", script_text: "{{秦总}}您好 · 长安食代扩张期流贷上限 2500 万 · LPR+90 BP · 想约时间聊", product_ref: "pr-j2-1" },
  { id: "ps-j2-2", customer_name_placeholder: "{{秦总}}", script_text: "{{秦总}}央厨建设资金大 · 我行中长期固贷 5 年分摊 · 上限 3000 万 · 哪天方便见", product_ref: "pr-j2-2" },
  { id: "ps-j2-3", customer_name_placeholder: "{{马 CFO}}", script_text: "{{马 CFO}}您好 · 区域整合贷款上限 5000 万 · 想聊聊", product_ref: "pr-j2-3" },
];

const MATCH_JIARUI_C3: MatchDimension[] = [
  { id: "md-j3-1", dim_name: "行业", display: "米线连锁 · 标杆延伸", hit_evidence: "kb-j1", score: 80 },
  { id: "md-j3-2", dim_name: "门店规模", display: "220 家 · 中等档", hit_evidence: "kb-j2", score: 76 },
  { id: "md-j3-3", dim_name: "地域", display: "昆明 · 西南腹地", hit_evidence: "kb-j2", score: 84 },
];
const PRODUCTS_JIARUI_C3: ProductRec[] = [
  { id: "pr-j3-1", product_name: "对公流动资金贷", fit_score: 82, intro: "稳健增长型连锁 · 续贷型流贷", amount_range: "300 万 - 2,000 万", rate_band: "LPR + 95 BP" },
  { id: "pr-j3-2", product_name: "供应链金融", fit_score: 76, intro: "上游食材供应链应付", amount_range: "200 万 - 1,500 万", rate_band: "LPR + 110 BP" },
  { id: "pr-j3-3", product_name: "中长期固贷", fit_score: 68, intro: "门店扩建 · 中长期分摊", amount_range: "300 万 - 1,500 万", rate_band: "LPR + 120 BP" },
];
const PITCH_JIARUI_C3: PitchScript[] = [
  { id: "ps-j3-1", customer_name_placeholder: "{{杨总}}", script_text: "{{杨总}}您好 · 云味稳健增长 · 我行流贷续贷型 · 上限 2000 万 · 想约时间聊", product_ref: "pr-j3-1" },
  { id: "ps-j3-2", customer_name_placeholder: "{{杨总}}", script_text: "{{杨总}}上游食材供应链应付占款大 · 我行供应链金融 · 上限 1500 万 · 哪天方便见", product_ref: "pr-j3-2" },
  { id: "ps-j3-3", customer_name_placeholder: "{{钱 CFO}}", script_text: "{{钱 CFO}}您好 · 门店扩建中长期固贷 · 上限 1500 万 · 想聊", product_ref: "pr-j3-3" },
];

const CANDIDATES_JIARUI: Candidate[] = [
  { id: "c-j1", name: "重庆鲜花花茶饮", similarity: 0.92, industry: "新消费 茶饮", geo: "重庆", scale: "门店 320 家", signals: ["舆情", "工商", "纳税"], riskTags: [], products: ["对公流动资金贷", "并购贷", "上市辅导信用贷"], note: "复购率 38%", timeline: TIMELINE_JIARUI_C1, match_dimensions: MATCH_JIARUI_C1, product_recommendations: PRODUCTS_JIARUI_C1, pitch_scripts: PITCH_JIARUI_C1 },
  { id: "c-j2", name: "西安长安食代连锁", similarity: 0.88, industry: "新消费 中式快餐", geo: "陕西西安", scale: "门店 280 家", signals: ["舆情", "招聘"], riskTags: [], products: ["对公流动资金贷", "中长期固贷"], match_dimensions: MATCH_JIARUI_C2, product_recommendations: PRODUCTS_JIARUI_C2, pitch_scripts: PITCH_JIARUI_C2 },
  { id: "c-j3", name: "昆明云味天厨", similarity: 0.83, industry: "新消费 米线连锁", geo: "云南昆明", scale: "门店 220 家", signals: ["工商", "纳税", "社保"], riskTags: [], products: ["对公流动资金贷"], note: "稳健增长", match_dimensions: MATCH_JIARUI_C3, product_recommendations: PRODUCTS_JIARUI_C3, pitch_scripts: PITCH_JIARUI_C3 },
  { id: "c-j4", name: "贵阳鲜里多卤味", similarity: 0.75, industry: "新消费 卤味连锁", geo: "贵州贵阳", scale: "门店 180 家", signals: ["舆情", "招聘"], riskTags: ["门店食安投诉 × 5"], products: ["对公流动资金贷"], note: "舆情噪声大 · 谨慎", match_dimensions: [{ id: "md-j4-1", dim_name: "行业", display: "卤味连锁 · 标杆延伸", hit_evidence: "kb-j1", score: 72 }, { id: "md-j4-2", dim_name: "门店规模", display: "180 家 · 中等", hit_evidence: "kb-j2", score: 68 }, { id: "md-j4-3", dim_name: "舆情风险", display: "食安投诉 5 起 · 待整改", hit_evidence: "kb-j3", score: 45 }], product_recommendations: [{ id: "pr-j4-1", product_name: "对公流动资金贷", fit_score: 68, intro: "食安整改后续贷型 · 谨慎额度", amount_range: "200 万 - 800 万", rate_band: "LPR + 130 BP" }, { id: "pr-j4-2", product_name: "供应链金融", fit_score: 60, intro: "上游食材供应链应付", amount_range: "100 万 - 500 万", rate_band: "LPR + 140 BP" }, { id: "pr-j4-3", product_name: "中长期固贷", fit_score: 55, intro: "整改完毕后再评", amount_range: "200 万 - 800 万", rate_band: "LPR + 150 BP" }], pitch_scripts: [{ id: "ps-j4-1", customer_name_placeholder: "{{陶总}}", script_text: "{{陶总}}您好 · 鲜里多食安整改后我行可启动小额流贷 · 上限 800 万 · 想跟您聊聊整改时间表", product_ref: "pr-j4-1" }, { id: "ps-j4-2", customer_name_placeholder: "{{陶总}}", script_text: "{{陶总}}上游食材应付占款 · 我行供应链金融 · 上限 500 万 · 哪天方便见", product_ref: "pr-j4-2" }, { id: "ps-j4-3", customer_name_placeholder: "{{周 CFO}}", script_text: "{{周 CFO}}您好 · 整改完毕后再启中长期固贷 · 我们先保持联络", product_ref: "pr-j4-3" }] },
  { id: "c-j5", name: "南宁邕江味道", similarity: 0.68, industry: "新消费 螺蛳粉", geo: "广西南宁", scale: "门店 95 家", signals: ["舆情", "工商"], riskTags: ["民事诉讼 × 3"], products: ["普惠信用贷"], note: "成熟度待观察", match_dimensions: [{ id: "md-j5-1", dim_name: "行业", display: "螺蛳粉连锁 · 标杆延伸", hit_evidence: "kb-j1", score: 65 }, { id: "md-j5-2", dim_name: "门店规模", display: "95 家 · 微小档", hit_evidence: "kb-j2", score: 50 }, { id: "md-j5-3", dim_name: "司法风险", display: "民诉 3 起 · 部分待结", hit_evidence: "kb-j3", score: 38 }], product_recommendations: [{ id: "pr-j5-1", product_name: "普惠信用贷", fit_score: 60, intro: "案件结清后小额试单", amount_range: "50 万 - 300 万", rate_band: "LPR + 120 BP" }, { id: "pr-j5-2", product_name: "对公流动资金贷", fit_score: 52, intro: "整体待观察 · 谨慎额度", amount_range: "30 万 - 200 万", rate_band: "LPR + 150 BP" }, { id: "pr-j5-3", product_name: "供应链金融", fit_score: 48, intro: "供应链小额", amount_range: "30 万 - 150 万", rate_band: "LPR + 160 BP" }], pitch_scripts: [{ id: "ps-j5-1", customer_name_placeholder: "{{覃总}}", script_text: "{{覃总}}您好 · 邕江案件结清后我行可启动普惠信用贷 · 上限 300 万 · 想跟您聊", product_ref: "pr-j5-1" }, { id: "ps-j5-2", customer_name_placeholder: "{{覃总}}", script_text: "{{覃总}}小额流贷可作过桥 · 上限 200 万 · 哪天方便见", product_ref: "pr-j5-2" }, { id: "ps-j5-3", customer_name_placeholder: "{{林 CFO}}", script_text: "{{林 CFO}}您好 · 供应链小额 150 万 · 想聊", product_ref: "pr-j5-3" }] },
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
