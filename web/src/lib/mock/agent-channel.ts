/**
 * Agent Channel (获客 · A01) — Signal-driven lookalike mock fixtures.
 * Feeds the /archive/channel workspace (timeline + candidate list + match panel).
 */

export type ChannelSignalKind = "bidding" | "patent" | "award" | "expansion" | "funding" | "cert";

export type ChannelSignalEvent = {
  id: string;
  ts: string; // ISO date, narrow for timeline render
  kind: ChannelSignalKind;
  company: string;
  headline: string;
  source: string;
  weight: number; // 0..1 · drives the timeline dot size
};

export type ChannelCandidate = {
  id: string;
  rank: number;
  name: string;
  industry: string;
  region: string;
  revenueBand: string;
  signalCount: number;
  lookalikeScore: number; // 0..100
  products: string[];
  lastSignal: string;
  matched: { label: string; hit: boolean }[];
};

export type ChannelFilter = {
  id: string;
  label: string;
  count: number;
  kind: "industry" | "region" | "stage" | "signal";
};

export const CHANNEL_STATS = {
  weeklyProcessed: "132",
  successRate: "68%",
  avgDuration: "3.4 分钟",
} as const;

export const CHANNEL_FILTERS: ChannelFilter[] = [
  { id: "ind-new-energy", label: "新能源装备", count: 42, kind: "industry" },
  { id: "ind-smart-mfg", label: "智能制造", count: 37, kind: "industry" },
  { id: "ind-biopharma", label: "生物医药", count: 18, kind: "industry" },
  { id: "ind-indsoft", label: "工业软件", count: 11, kind: "industry" },
  { id: "reg-yrd", label: "长三角", count: 64, kind: "region" },
  { id: "reg-prd", label: "珠三角", count: 28, kind: "region" },
  { id: "reg-bohai", label: "环渤海", count: 14, kind: "region" },
  { id: "stg-b", label: "B 轮前后", count: 22, kind: "stage" },
  { id: "stg-mature", label: "成熟期", count: 31, kind: "stage" },
  { id: "sig-bidding", label: "中标信号", count: 47, kind: "signal" },
  { id: "sig-patent", label: "专利授予", count: 33, kind: "signal" },
  { id: "sig-expansion", label: "扩产事件", count: 21, kind: "signal" },
];

export const CHANNEL_TIMELINE: ChannelSignalEvent[] = [
  {
    id: "sig-001",
    ts: "04-21 09:12",
    kind: "bidding",
    company: "宁海汇通精工",
    headline: "中标比亚迪电池支架模组 2600 万",
    source: "中国招标投标公共服务平台",
    weight: 0.9,
  },
  {
    id: "sig-002",
    ts: "04-21 08:45",
    kind: "patent",
    company: "苏州星河医药",
    headline: "发明专利授权 · 新型冠脉造影剂稳定制剂",
    source: "国家知识产权局",
    weight: 0.6,
  },
  {
    id: "sig-003",
    ts: "04-20 17:30",
    kind: "award",
    company: "瀚蓝智控",
    headline: "入选 2026 浙江专精特新「小巨人」名单",
    source: "浙江经信厅",
    weight: 0.78,
  },
  {
    id: "sig-004",
    ts: "04-20 14:08",
    kind: "expansion",
    company: "东阳塑橡科技",
    headline: "金华基地 4 号车间投产 · 产能翻倍",
    source: "财经周刊",
    weight: 0.7,
  },
  {
    id: "sig-005",
    ts: "04-20 11:22",
    kind: "funding",
    company: "安诺智药",
    headline: "完成 B 轮 2.8 亿人民币融资",
    source: "36Kr",
    weight: 0.82,
  },
  {
    id: "sig-006",
    ts: "04-19 16:55",
    kind: "cert",
    company: "宁波鼎承精密",
    headline: "通过 IATF 16949 汽车质量体系认证",
    source: "TÜV SÜD",
    weight: 0.54,
  },
  {
    id: "sig-007",
    ts: "04-19 10:14",
    kind: "bidding",
    company: "杭州云栖机电",
    headline: "中标中石化储罐改造项目 1800 万",
    source: "中石化电子招投标平台",
    weight: 0.75,
  },
  {
    id: "sig-008",
    ts: "04-18 15:40",
    kind: "patent",
    company: "常州鑫拓材料",
    headline: "PCT 国际专利公开 · 固态电解质配方",
    source: "WIPO",
    weight: 0.68,
  },
];

export const CHANNEL_CANDIDATES: ChannelCandidate[] = [
  {
    id: "cand-001",
    rank: 1,
    name: "宁海汇通精工有限公司",
    industry: "新能源汽车零部件",
    region: "浙江·宁海",
    revenueBand: "1.2-1.8 亿",
    signalCount: 6,
    lookalikeScore: 92,
    products: ["供应链融资", "票据池"],
    lastSignal: "中标比亚迪订单",
    matched: [
      { label: "行业匹配", hit: true },
      { label: "区域锚定", hit: true },
      { label: "规模下沿", hit: true },
      { label: "资质标签", hit: false },
    ],
  },
  {
    id: "cand-002",
    rank: 2,
    name: "苏州星河医药股份",
    industry: "生物医药",
    region: "江苏·苏州",
    revenueBand: "0.8-1.2 亿",
    signalCount: 5,
    lookalikeScore: 87,
    products: ["经营贷", "知识产权质押"],
    lastSignal: "发明专利授权",
    matched: [
      { label: "行业匹配", hit: true },
      { label: "区域锚定", hit: true },
      { label: "规模下沿", hit: false },
      { label: "资质标签", hit: true },
    ],
  },
  {
    id: "cand-003",
    rank: 3,
    name: "瀚蓝智控有限公司",
    industry: "工业软件",
    region: "浙江·杭州",
    revenueBand: "2.4-3.1 亿",
    signalCount: 7,
    lookalikeScore: 85,
    products: ["流动资金", "科创投联贷"],
    lastSignal: "专精特新小巨人",
    matched: [
      { label: "行业匹配", hit: true },
      { label: "区域锚定", hit: true },
      { label: "规模下沿", hit: true },
      { label: "资质标签", hit: true },
    ],
  },
  {
    id: "cand-004",
    rank: 4,
    name: "东阳塑橡科技集团",
    industry: "新材料",
    region: "浙江·金华",
    revenueBand: "3.5-4.2 亿",
    signalCount: 4,
    lookalikeScore: 78,
    products: ["固定资产贷", "承兑汇票"],
    lastSignal: "金华基地投产",
    matched: [
      { label: "行业匹配", hit: true },
      { label: "区域锚定", hit: true },
      { label: "规模下沿", hit: false },
      { label: "资质标签", hit: false },
    ],
  },
  {
    id: "cand-005",
    rank: 5,
    name: "安诺智药有限公司",
    industry: "生物医药",
    region: "上海·张江",
    revenueBand: "未披露",
    signalCount: 3,
    lookalikeScore: 74,
    products: ["科创贷", "研发补助贷"],
    lastSignal: "B 轮融资",
    matched: [
      { label: "行业匹配", hit: true },
      { label: "区域锚定", hit: false },
      { label: "规模下沿", hit: false },
      { label: "资质标签", hit: true },
    ],
  },
];
