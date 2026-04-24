/**
 * Agent Channel (Scout) · 单 session 对话式获客工作流 mock（2026-04-21 H1 · canon 横向迁移）
 * 业务：look-alike 获客 —— 输入标杆客户画像 → 8 信号源扫描 → 相似度打分 → 风险过滤 → 推荐 top N
 * 五块完整 shape：query / signals / match / conversation / output(radar+funnel+candidates)
 * 复用 ConversationMessage 类型（避免 ConversationPanel 双份实现）。
 */

import type { ConversationMessage, RefCardPayload } from "./agent-report-session";
export type { ConversationMessage, RefCardPayload };

export const CHANNEL_GLOBAL_STATS = {
  weeklyProcessed: "164",
  hitRate: "32.8%",
  avgDuration: "6.2 分钟",
} as const;

/* ── 类型 ─────────────────────────────────────────────── */

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

/**
 * 2026-04-22 重设：从「信号源覆盖 / look-alike 相似度」换成「营销优先级 B++ 8 维」
 *   axis:      维度名（简洁书面式）
 *   score:     该企业在该维度的得分 0-100（"自己"）
 *   benchmark: 同行业 P50 中位基准 0-100（"对标"）
 *   quadrant:  分象限分组，用于雷达填充分段配色
 *     base    · 基本盘（营收体量 / 成长动能）
 *     bonus   · 加分项（资质含金量 / 行业风口度）
 *     demand  · 需求信号（用信需求度）
 *     health  · 合规健康（合规健康度，反向评分）
 *     market  · 可营销（营销蓝海度 / 决策可及度）
 *   note:      该维度得分来源 / 加扣分明细（hover 展示）
 */
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

/* ── 常量 ─────────────────────────────────────────────── */

const QUERY: ScoutQuery = {
  id: "q-fjhm-0421",
  benchmark: "福建惠民商贸有限公司",
  industry: "批发零售 · 快消 B2B",
  geo: "福建 · 福州/泉州/厦门",
  scaleRange: "营收 500-5,000 万元",
  featureTags: [
    "连锁商超渠道",
    "多年合同稳定",
    "抵押充足",
    "家族股权 60/40",
    "无外部投资",
    "本地下沉市场",
    "批发占 78%",
    "月均流水 ¥400 万±",
    "历史授信无逾期",
    "2014 年成立",
    "注册资本 800 万",
    "税务 A 级",
  ],
  updated: "2 分钟前",
  kbRefs: [
    { id: "kb-1", label: "福建商贸行业画像 2025.pdf", hitBy: "行业 + 地域匹配" },
    { id: "kb-2", label: "本行普惠审批历史档案", hitBy: "历史标杆合集" },
    { id: "kb-3", label: "福州市连锁渠道名录 2025Q4", hitBy: "渠道下游穿透" },
  ],
};

const SIGNALS: SignalSource[] = [
  {
    id: "sig-1",
    key: "biz",
    label: "工商",
    status: "active",
    weight: 0.18,
    freq: "每日",
    coverage: 98,
    hits: 1205,
  },
  {
    id: "sig-2",
    key: "bidding",
    label: "招投标",
    status: "active",
    weight: 0.14,
    freq: "每小时",
    coverage: 86,
    hits: 342,
  },
  {
    id: "sig-3",
    key: "pr",
    label: "舆情",
    status: "active",
    weight: 0.08,
    freq: "每小时",
    coverage: 72,
    hits: 128,
  },
  {
    id: "sig-4",
    key: "legal",
    label: "司法",
    status: "active",
    weight: 0.14,
    freq: "每日",
    coverage: 94,
    hits: 87,
    note: "行政处罚 / 执行 / 失信",
  },
  {
    id: "sig-5",
    key: "social",
    label: "社保",
    status: "degraded",
    weight: 0.11,
    freq: "月度",
    coverage: 64,
    hits: 510,
    note: "本轮仅省会覆盖完整",
  },
  {
    id: "sig-6",
    key: "tax",
    label: "纳税",
    status: "active",
    weight: 0.15,
    freq: "季度",
    coverage: 82,
    hits: 468,
  },
  {
    id: "sig-7",
    key: "hr",
    label: "招聘",
    status: "active",
    weight: 0.09,
    freq: "每日",
    coverage: 78,
    hits: 236,
  },
  {
    id: "sig-8",
    key: "funding",
    label: "投融资",
    status: "off",
    weight: 0.11,
    freq: "事件触发",
    coverage: 0,
    hits: 0,
    note: "本客群基本无对外股权融资 · 默认关",
  },
];

const MATCH: MatchSetting = {
  similarity: 0.72,
  geoInclude: ["福建", "浙江南部"],
  industryInclude: ["批发零售", "日用快消"],
  scaleRange: "营收 300-6,000 万",
  excludeActive: true,
  excludeRiskTags: ["被执行", "失信", "行政处罚 ≥ 2"],
};

const RADAR: RadarDimension[] = [
  {
    axis: "营收体量",
    quadrant: "base",
    score: 68,
    benchmark: 52,
    note: "营收 2,180 万 · 行业 P50 ≈ 1,500 万 · 批发零售中型档位",
  },
  {
    axis: "成长动能",
    quadrant: "base",
    score: 74,
    benchmark: 55,
    note: "营收同比 +18% · 社保参保 12 月 +7 · 招聘近 3 月 ×1.6",
  },
  {
    axis: "资质含金量",
    quadrant: "bonus",
    score: 58,
    benchmark: 38,
    note: "省级专精特新 · 高新技术企业（2023）· 8 项发明专利",
  },
  {
    axis: "行业风口度",
    quadrant: "bonus",
    score: 62,
    benchmark: 50,
    note: "批发零售行业景气 54 · 本地下沉消费政策 boost +8",
  },
  {
    axis: "用信需求度",
    quadrant: "demand",
    score: 82,
    benchmark: 45,
    note: "近 6 月：大超市供应合同 × 3 · 新建仓储 2,400㎡ · 增资 300 万",
  },
  {
    axis: "合规健康度",
    quadrant: "health",
    score: 91,
    benchmark: 72,
    note: "无诉讼 / 无失信 / 无经营异常 · 历史处罚 1 次已结清（消防整改）",
  },
  {
    axis: "营销蓝海度",
    quadrant: "market",
    score: 78,
    benchmark: 60,
    note: "他行授信 1 家（额度 ¥500 万使用 42%）· 我行无历史合作",
  },
  {
    axis: "决策可及度",
    quadrant: "market",
    score: 71,
    benchmark: 58,
    note: "实控人 1 位 · 公开电话 / 邮箱完整 · 股东链 2 层 · 家族股权",
  },
];

const FUNNEL: FunnelStage[] = [
  { id: "fn-1", label: "信号池", count: 1200, detail: "8 信号源全量召回" },
  { id: "fn-2", label: "工商匹配", count: 826, detail: "行业 + 地域 + 规模" },
  { id: "fn-3", label: "画像命中", count: 312, detail: "12 维特征 ≥ 8 维吻合" },
  { id: "fn-4", label: "风险过滤", count: 142, detail: "司法 / 社保 / 行政 三重滤" },
  { id: "fn-5", label: "Top 推荐", count: 28, detail: "相似度 ≥ 0.72 · 排除已授信" },
];

const TIMELINE_CAND1: SignalEvent[] = [
  {
    id: "tl-1-1",
    at: "昨天 · 16:42",
    kind: "bid-win",
    title: "中标厦门市思明区连锁便利店日用品年度供应",
    detail: "金额 ¥420 万 · 为期 12 个月 · 核心客户：永辉 Mini + 见福便利 2 家",
    source: { label: "厦门公共资源交易中心 · 2026-04-21", url: "#" },
    severity: "pos",
  },
  {
    id: "tl-1-2",
    at: "3 天前",
    kind: "recruit",
    title: "近 30 天新增招聘 7 岗 · 均为仓储/配送/销售",
    detail: "仓管 2 · 司机 3 · 快消销售 2 · 月薪 5-8K · 招聘渠道 Boss 直聘",
    source: { label: "Boss 直聘 · 爬取聚合", url: "#" },
    severity: "pos",
  },
  {
    id: "tl-1-3",
    at: "2 周前",
    kind: "policy",
    title: "获评福建省省级专精特新中小企业（2026 年度）",
    detail: "认定编号 FJ-ZJTX-2026-0418 · 含 50 万一次性补贴",
    source: { label: "福建省工信厅 · 公告 2026-04-08", url: "#" },
    severity: "pos",
  },
  {
    id: "tl-1-4",
    at: "1 个月前",
    kind: "biz-change",
    title: "注册资本由 500 万增至 800 万",
    detail: "股东原出资比例不变（60/40）· 实缴 300 万 · 变更登记已完成",
    source: { label: "国家企业信用信息公示系统", url: "#" },
    severity: "pos",
  },
  {
    id: "tl-1-5",
    at: "1 个月前",
    kind: "tax",
    title: "Q1 季度纳税申报 · A 级 · 同比 +22%",
    detail: "Q1 增值税 ¥54 万 · 所得税 ¥28 万 · 连续 8 季度 A 级",
    source: { label: "厦门市税务局 · 信用等级公示", url: "#" },
    severity: "pos",
  },
  {
    id: "tl-1-6",
    at: "2 个月前",
    kind: "news",
    title: "本地媒体《海西都市报》报道 · 新建 2,400㎡ 冷链仓",
    detail: "投资 ¥380 万 · 预计 Q3 投运 · 拓展生鲜配送业务",
    source: { label: "海西都市报 · 2026-02-24", url: "#" },
    severity: "pos",
  },
  {
    id: "tl-1-7",
    at: "3 个月前",
    kind: "legal",
    title: "消防整改处罚已结清（2023 历史事项）",
    detail: "厦门市思明区消防大队处罚 ¥1.2 万 · 2024-01 已履行",
    source: { label: "企查查 · 司法风险模块", url: "#" },
    severity: "neu",
  },
];

const CANDIDATES: Candidate[] = [
  {
    id: "cand-1",
    name: "厦门瑞鼎日用品批发",
    similarity: 0.91,
    industry: "日用品批发",
    geo: "福建厦门",
    scale: "营收 2,180 万",
    signals: ["工商", "纳税", "社保"],
    riskTags: [],
    products: ["普惠信用贷", "商超订单融资"],
    note: "连锁便利店渠道 · 月均流水 ¥380 万",
    timeline: TIMELINE_CAND1,
  },
  {
    id: "cand-2",
    name: "泉州德丰快消品有限公司",
    similarity: 0.87,
    industry: "快消品批发",
    geo: "福建泉州",
    scale: "营收 3,840 万",
    signals: ["工商", "招投标", "纳税"],
    riskTags: [],
    products: ["对公流动资金贷", "应收账款保理"],
    note: "3 家大超市供应商 · 合同覆盖 68%",
  },
  {
    id: "cand-3",
    name: "福州榕信商贸",
    similarity: 0.83,
    industry: "商贸批发",
    geo: "福建福州",
    scale: "营收 1,520 万",
    signals: ["工商", "招聘"],
    riskTags: ["行政处罚 × 1"],
    products: ["普惠信用贷"],
    note: "2023 消防整改处罚已结清 · 不影响授信",
  },
  {
    id: "cand-4",
    name: "漳州华盛仓储",
    similarity: 0.78,
    industry: "物流仓储",
    geo: "福建漳州",
    scale: "营收 2,960 万",
    signals: ["工商", "纳税", "招聘"],
    riskTags: [],
    products: ["仓单质押贷", "普惠信用贷"],
    note: "有 4,200 ㎡ 仓库 · 可抵押",
  },
  {
    id: "cand-5",
    name: "莆田美禾食品配送",
    similarity: 0.74,
    industry: "食品配送",
    geo: "福建莆田",
    scale: "营收 1,080 万",
    signals: ["工商", "社保", "舆情"],
    riskTags: [],
    products: ["普惠信用贷"],
    note: "规模略小 · 但增长曲线陡 + 客户经理推荐",
  },
];

const CONVERSATION: ConversationMessage[] = [
  {
    id: "cmsg-1",
    at: "12 分钟前",
    kind: "system-event",
    content:
      "Scout 任务启动 · 标杆：福建惠民商贸 · 续授信客户 · 8 信号源已 standby",
  },
  {
    id: "cmsg-2",
    at: "12 分钟前",
    kind: "ai-question",
    content:
      "想找「像谁」的客户？可以指定标杆客户名、或描述画像（行业/规模/地域）。我会抽取 12 维特征并交叉 8 信号源。",
  },
  {
    id: "cmsg-3",
    at: "11 分钟前",
    kind: "user-reply",
    content:
      "像福建惠民这种福州/泉州的批发商 · 营收 500-5,000 万 · 本地连锁渠道稳定 · 想挖一批同画像的潜客。",
  },
  {
    id: "cmsg-4",
    at: "10 分钟前",
    kind: "ai-response",
    content:
      "已抽 12 维画像特征：批发零售 · 快消 B2B · 家族股权 · 本地下沉 · 连锁商超渠道 · 多年履约 · 抵押充足 · 税务 A 级 · …（全量见左栏 Query 画像区）。准备扫 8 信号源。",
    fieldRef: "Query · 标杆特征",
  },
  {
    id: "cmsg-5",
    at: "8 分钟前",
    kind: "ai-thinking",
    content:
      "8 信号源并行扫描中 · 权重配置从行业画像库继承（工商 0.18 / 纳税 0.15 / 招投标 0.14 / 司法 0.14 / 社保 0.11 / 投融资 0.11 / 招聘 0.09 / 舆情 0.08）",
    thinking: {
      steps: [
        {
          label: "工商源 · 1,205 家命中",
          evidences: ["行业代码 F5189 · 地域福建 · 规模区间吻合"],
        },
        {
          label: "纳税源 · 468 家纳税 A 级",
          evidences: ["季度纳税申报连续 ≥ 8 期 · 无异常"],
        },
        {
          label: "招投标源 · 342 家有政采/大客户订单",
          evidences: ["3 年内中标记录 ≥ 1 次 · 或为核心供应商"],
        },
        {
          label: "司法源 · 过滤 87 家高风险",
          evidences: ["被执行 / 失信 / 行政处罚 ≥ 2 次"],
        },
        {
          label: "社保源 · 510 家雇员稳定",
          evidences: ["月均在职 ≥ 8 · 连续 12 月无断缴"],
        },
        {
          label: "投融资源 · 本次不参与",
          evidences: ["本客群 98% 无对外股权融资 · 信号无区分度"],
        },
      ],
    },
  },
  {
    id: "cmsg-6",
    at: "6 分钟前",
    kind: "ai-response",
    content:
      "Funnel：1,200 → 826（工商匹配）→ 312（画像 ≥ 8 维吻合）→ 142（风险过滤）→ Top 28（相似度 ≥ 0.72）。雷达覆盖见右栏。",
    fieldRef: "Funnel · 5 阶段",
  },
  {
    id: "cmsg-7",
    at: "4 分钟前",
    kind: "ai-question",
    content:
      "是否排除本行已授信客户？以及是否继续放宽相似度到 0.65（预计可补 12 家）？",
  },
  {
    id: "cmsg-8",
    at: "3 分钟前",
    kind: "user-command",
    content:
      "/confirm 相似度阈值 0.72 保留 · 排除已授信 · 地域聚焦福建 + 浙南 · 产品优先推普惠信用贷",
  },
  {
    id: "cmsg-9",
    at: "2 分钟前",
    kind: "ai-response",
    content:
      "Top 5 推荐已生成：瑞鼎(0.91) · 德丰(0.87) · 榕信(0.83) · 华盛(0.78) · 美禾(0.74)。每家附产品建议 + 触达时机提示，见右栏候选面板。",
    fieldRef: "Candidates · Top 5",
    sectionDiff: {
      sectionAnchor: "Top · 推荐",
      after:
        "28 家候选 · Top 5 首推（相似度 0.91/0.87/0.83/0.78/0.74）· 预计转化 6-8 家 · 建议 T+1 内由客户经理电话/线下触达",
    },
  },
  {
    id: "cmsg-10",
    at: "刚刚",
    kind: "system-event",
    content: "本轮完成 · 28 家已推送到客户经理「待跟进」列表 · QC 通过（无阻断）",
  },
];

const RECENT: RecentScoutSession[] = [
  {
    id: "rc-001",
    benchmark: "福建惠民商贸 · 续授信画像",
    updated: "刚刚（当前）",
    progress: 1.0,
    stage: "已生成 · 28 推荐",
  },
  {
    id: "rc-002",
    benchmark: "宁海汇通精工 · 对公制造",
    updated: "26 分钟前",
    progress: 0.82,
    stage: "风险过滤中",
  },
  {
    id: "rc-003",
    benchmark: "苏州星河医药 · 高科技",
    updated: "1 小时前",
    progress: 0.54,
    stage: "信号扫描",
  },
  {
    id: "rc-004",
    benchmark: "东阳塑橡 · 周转需求",
    updated: "2 小时前",
    progress: 0.28,
    stage: "画像抽特征",
  },
  {
    id: "rc-005",
    benchmark: "瀚蓝智控 · 自营园区供应链",
    updated: "昨天",
    progress: 1.0,
    stage: "已完成 · 14 推荐",
  },
];

export const CHANNEL_SESSION: ChannelSession = {
  id: "rc-001",
  benchmarkName: "福建惠民商贸 · 续授信画像",
  candidateCount: 28,
  stage: "Top 推荐已生成",
  updated: "刚刚",
  query: QUERY,
  signals: SIGNALS,
  match: MATCH,
  conversation: CONVERSATION,
  radar: RADAR,
  funnel: FUNNEL,
  candidates: CANDIDATES,
  qcCounts: { block: 0, warn: 1, info: 2 },
  recentSessions: RECENT,
};
