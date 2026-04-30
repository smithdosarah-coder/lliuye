/**
 * Agent Credit · 对话式授信决策 mock（2026-04-22 v3 · Codex 融合 + 三板块）
 *
 * Agent3 v3.1 的三板块（对公 / 普惠 / 对私）现在前端也暴露。
 * 顶部模式 tab 切 CREDIT_SESSIONS[mode] → workspace 整体重绘。
 *
 * 新增字段（Codex 融合）：
 *   - profile · 大 Hero 头（企业 chips + 一句话定位）
 *   - materials · 资料上传与解析状态
 *   - dataSources · 资料库接口状态
 *   - evidences · 证据链（正向 / 提醒 / 缺失 三档）
 *   - generateSteps · CTA "生成授信辅助" 进度条 5 步
 */

import type { ConversationMessage } from "./agent-report-session";
export type { ConversationMessage };

export const CREDIT_GLOBAL_STATS = {
  weeklyProcessed: "63",
  avgAmount: "680 万",
  avgDuration: "11.2 分钟",
} as const;

/* ── 类型 ─────────────────────────────────────────────── */

export type CreditMode = "corp" | "small" | "retail";

export const CREDIT_MODE_LABEL: Record<CreditMode, string> = {
  corp: "对公",
  small: "普惠",
  retail: "对私",
};

export type CreditQuery = {
  id: string;
  customer: string;
  customerCode: string;
  product: "对公经营贷" | "普惠小微贷" | "对私消费贷" | "对私经营贷";
  applyAmount: string;
  applyTenor: string;
  purpose: string;
  industry: string;
  updated: string;
};

export type CreditRadarDim = {
  key: "fin" | "ops" | "comp" | "guar";
  label: string;
  score: number;
  weight: number;
  note: string;
  tags: string[];
};

export type RedLine = {
  id: string;
  rule: string;
  detail: string;
  status: "pass" | "warn" | "fail";
  citation: string;
};

export type CaseRecall = {
  id: string;
  name: string;
  similarity: number;
  amount: string;
  decision: "approved" | "approved-cut" | "rejected";
  note: string;
  tags: string[];
};

export type LimitSuggestion = {
  applied: number;
  suggested: number;
  floor: number;
  ceiling: number;
  tenorMonths: number;
  tenorRange: [number, number];
  rateBps: number;
  rateRange: [number, number];
  rationale: string[];
};

export type CreditPipelineStep = {
  id: string;
  label: string;
  status: "done" | "active" | "pending";
  note?: string;
};

export type CreditRecentSession = {
  id: string;
  customer: string;
  product: string;
  amount: string;
  updated: string;
  decision: "approved" | "approved-cut" | "rejected" | "pending";
};

export type CreditProfile = {
  /** 企业/个人画像标签，显示为 hero chips · 3-5 个 */
  chips: string[];
  /** 一句话综合判断，显示在 hero 底部 · 20-40 字 */
  tagline: string;
};

export type MaterialFileStatus = "done" | "warn" | "pending";
export type MaterialFile = {
  id: string;
  icon: string;
  name: string;
  note: string;
  status: MaterialFileStatus;
};

export type MaterialsPanel = {
  /** 0–100 · 资料完整度百分比 */
  completeness: number;
  /** 一行缺失概要（空字符串表示无缺失） */
  missing: string;
  files: MaterialFile[];
};

export type DataSourceStatus = "online" | "warn" | "offline";
export type DataSource = {
  id: string;
  name: string;
  desc: string;
  status: DataSourceStatus;
};

export type DataSourcesPanel = {
  /** 接入数量 · 展示用字符串（"5 项已接入"） */
  summary: string;
  /** 数据最近刷新时间 */
  updated: string;
  sources: DataSource[];
};

export type EvidenceTone = "positive" | "warning" | "missing";
export type EvidenceItem = {
  id: string;
  icon: string;
  title: string;
  detail: string;
  tone: EvidenceTone;
};

export type EvidencesPanel = {
  positive: EvidenceItem[];
  warnings: EvidenceItem[];
  missing: EvidenceItem[];
};

export type GenerateStep = {
  label: string;
  /** 0–100 · 这一步完成时的累积进度 */
  pct: number;
};

export type CreditSession = {
  id: string;
  mode: CreditMode;
  objective: string;
  stage: string;
  updated: string;
  profile: CreditProfile;
  query: CreditQuery;
  pipeline: CreditPipelineStep[];
  radar: CreditRadarDim[];
  overallScore: number;
  decision: "approved" | "approved-cut" | "rejected" | "pending";
  limit: LimitSuggestion;
  redLines: RedLine[];
  cases: CaseRecall[];
  conversation: ConversationMessage[];
  qcCounts: { block: number; warn: number; info: number };
  recentSessions: CreditRecentSession[];
  materials: MaterialsPanel;
  dataSources: DataSourcesPanel;
  evidences: EvidencesPanel;
  generateSteps: GenerateStep[];
};

/* ── 通用进度 5 步（三模通用） ─────────────────────────── */

const GEN_STEPS: GenerateStep[] = [
  { label: "资料解析中", pct: 22 },
  { label: "资料库匹配中", pct: 48 },
  { label: "多维评估中", pct: 76 },
  { label: "策略生成中", pct: 96 },
  { label: "已完成综合判断", pct: 100 },
];

/* ══════════════════════════════════════════════════════
 * 对公 · 福建惠民商贸 · 对公经营贷 800 万
 * ════════════════════════════════════════════════════ */

const CORP_QUERY: CreditQuery = {
  id: "cr-fj-hmsm-0421",
  customer: "福建惠民商贸有限公司",
  customerCode: "CR-2026-04-21-0037",
  product: "对公经营贷",
  applyAmount: "800 万",
  applyTenor: "24 个月",
  purpose: "补充流动资金 · 采购旺季备货",
  industry: "批发零售 · 日用百货",
  updated: "3 分钟前",
};

const CORP_PIPELINE: CreditPipelineStep[] = [
  { id: "p-1", label: "消费 Agent6 报告", status: "done", note: "ReportJSON v7.23 · 460 项" },
  { id: "p-2", label: "四维评分", status: "done", note: "财 72 / 经 78 / 合 81 / 担 66" },
  { id: "p-3", label: "红线检查", status: "done", note: "6 项 · 5 过 1 警" },
  { id: "p-4", label: "案例召回", status: "done", note: "3 个相似案例 · 相似度 ≥ 0.82" },
  { id: "p-5", label: "额度 · 期限 · 利率", status: "done", note: "720 万 / 18 月 / LPR+120bps" },
  { id: "p-6", label: "送审贷会", status: "pending" },
];

const CORP_RADAR: CreditRadarDim[] = [
  {
    key: "fin",
    label: "财务健康",
    score: 72,
    weight: 0.3,
    note: "毛利率 18.4% 稳健 · 流动比 1.42 · 速动比 0.86 偏低",
    tags: ["应收账款周转 44 天", "资产负债率 58%"],
  },
  {
    key: "ops",
    label: "经营稳健",
    score: 78,
    weight: 0.3,
    note: "成立 11 年 · 年营收 7420 万 · 3 年复合增速 9.2%",
    tags: ["核心客户 12 家", "无关联交易异常"],
  },
  {
    key: "comp",
    label: "合规征信",
    score: 81,
    weight: 0.25,
    note: "央行征信无不良 · 税务 A 级 · 无司法冻结 · 近 24 月无逾期",
    tags: ["税务 A 级", "无失信"],
  },
  {
    key: "guar",
    label: "担保增信",
    score: 66,
    weight: 0.15,
    note: "抵押物为自有商铺 · 估值 960 万 · 抵押率 75%；无第三方担保",
    tags: ["抵押率 75%", "需补保证人"],
  },
];

const CORP_RED_LINES: RedLine[] = [
  {
    id: "rl-1",
    rule: "近 12 月 M3+ 逾期 = 0",
    detail: "核查通过 · 客户近 24 月无任何逾期",
    status: "pass",
    citation: "央行征信 2026-04 · 对公简版",
  },
  {
    id: "rl-2",
    rule: "无失信/被执行/行政处罚",
    detail: "国家企业信用网、裁判文书网、行政处罚公示库均无命中",
    status: "pass",
    citation: "信用中国 · 裁判文书网 2026-04-20",
  },
  {
    id: "rl-3",
    rule: "税务评级 ≥ B",
    detail: "当前税务信用 A 级",
    status: "pass",
    citation: "福建省税务总局 · 2025 年度",
  },
  {
    id: "rl-4",
    rule: "资产负债率 ≤ 70%",
    detail: "当前 58% · 距上限 12pp 缓冲",
    status: "pass",
    citation: "财务报表 2025-12 · 经四方会计师事务所审计",
  },
  {
    id: "rl-5",
    rule: "抵押率 ≤ 70%",
    detail: "当前 75% · 超阈 5pp；需补足其他抵押或保证人",
    status: "warn",
    citation: "评估报告 2026-03 · 恒信评估",
  },
  {
    id: "rl-6",
    rule: "主营业务集中度 ≤ 60%",
    detail: "前 3 大客户占比 41% · 通过",
    status: "pass",
    citation: "销售台账 2025-Q4",
  },
];

const CORP_CASES: CaseRecall[] = [
  {
    id: "c-1",
    name: "宁德普惠日化贸易 · 2025-08",
    similarity: 0.91,
    amount: "750 万",
    decision: "approved-cut",
    note: "同行业 · 年营收相近 · 抵押率同样 75% · 终批 620 万 / 18 月 / LPR+130bps",
    tags: ["批发零售", "抵押率 75%"],
  },
  {
    id: "c-2",
    name: "厦门新力百货批发 · 2025-11",
    similarity: 0.87,
    amount: "900 万",
    decision: "approved",
    note: "同地区 · 但抵押率 60% · 终批 880 万 / 24 月 / LPR+110bps",
    tags: ["同地区", "抵押率 60%"],
  },
  {
    id: "c-3",
    name: "福州信达商贸 · 2026-01",
    similarity: 0.83,
    amount: "1000 万",
    decision: "rejected",
    note: "同行业 · 但资产负债率 72% 触红线 + 近 12 月有 M1 逾期 · 拒",
    tags: ["负债率超线", "近期逾期"],
  },
];

const CORP_LIMIT: LimitSuggestion = {
  applied: 800,
  suggested: 720,
  floor: 600,
  ceiling: 800,
  tenorMonths: 18,
  tenorRange: [12, 24],
  rateBps: 120,
  rateRange: [100, 150],
  rationale: [
    "抵押率 75% 超 70% 上限 5pp · 额度下调 10%",
    "期限 18 月匹配旺季备货周期 · 短于申请 24 月降低展期风险",
    "LPR+120bps 参考案例 C-1/C-2 中位，兼顾客户获得感与风险溢价",
  ],
};

const CORP_CONVERSATION: ConversationMessage[] = [
  {
    id: "cr-msg-1",
    at: "12 分钟前",
    kind: "system-event",
    content: "审贷 session 启动 · 客户：福建惠民商贸 · 产品：对公经营贷 · 申请 800 万 / 24 月",
  },
  {
    id: "cr-msg-2",
    at: "12 分钟前",
    kind: "ai-question",
    content:
      "已消费 Agent6 报告（ReportJSON v7.23）· 四维评分跑完。主持人希望优先围绕哪个维度深看：财务、经营、合规、还是担保？",
  },
  {
    id: "cr-msg-3",
    at: "10 分钟前",
    kind: "user-reply",
    content: "担保维度 66 分是最低的，先看抵押情况 + 有没有可以补位的第二还款来源",
  },
  {
    id: "cr-msg-4",
    at: "9 分钟前",
    kind: "ai-thinking",
    content: "拆解担保维度 66 分的构成 · 召回 3 个相似案例 · 给额度/期限/利率建议",
    thinking: {
      steps: [
        {
          label: "担保维度拆解",
          evidences: [
            "抵押物：自有商铺，评估 960 万",
            "抵押率：800/960 = 83% · 已超 70% 红线",
            "第二还款来源：目前空缺（无保证人、无质押）",
            "触发红线 RL-5：抵押率 ≤ 70%（现状 warn）",
          ],
        },
        {
          label: "案例召回 · 相似度 ≥ 0.80",
          evidences: [
            "C-1 宁德普惠日化（0.91）· 同抵押率 75% · 批 620 万 / 18 月",
            "C-2 厦门新力百货（0.87）· 抵押率 60% · 批 880 万 / 24 月",
            "C-3 福州信达商贸（0.83）· 负债率触线 · 拒",
          ],
        },
        {
          label: "额度 · 期限 · 利率推导",
          evidences: [
            "抵押率 75% 触 warn · 建议额度从 800 下调至 720 万（70% 抵押率阈）",
            "期限 18 月匹配旺季备货周期 · 短于申请 24 月",
            "利率 LPR+120bps · 取 C-1/C-2 中位",
          ],
        },
      ],
    },
  },
  {
    id: "cr-msg-5",
    at: "6 分钟前",
    kind: "ai-response",
    content:
      "建议批复：额度 720 万 / 期限 18 月 / 利率 LPR+120bps · 等同打折批（approved-cut）。关键触发点：担保维度唯一 warn · 建议要求客户补保证人或追加质押将抵押率压至 ≤ 70%。",
    fieldRef: "Decision Dashboard · 担保增信维度",
    sectionDiff: {
      sectionAnchor: "Limit & Tenor Suggestion",
      after: "720 万 / 18 月 / LPR+120bps · 触发条件：补保证人后放款",
    },
  },
  {
    id: "cr-msg-6",
    at: "4 分钟前",
    kind: "ai-question",
    content: "是否要将「补保证人」作为放款前置条件写入决议？如同意，自动生成审贷会议决议草稿 + 合同附加条款。",
  },
  {
    id: "cr-msg-7",
    at: "2 分钟前",
    kind: "user-command",
    content: "/lock 720 万 · 18 月 · LPR+120bps · 前置条件=补保证人 · 提交审贷会",
  },
  {
    id: "cr-msg-8",
    at: "刚刚",
    kind: "system-event",
    content:
      "决议已锁版 · 自动生成送审包（决策 Dashboard + 四维评分 + 红线明细 + 相似案例 3 条 + 决议草稿）· 待审贷会表决",
  },
];

const CORP_MATERIALS: MaterialsPanel = {
  completeness: 84,
  missing: "担保材料 1 项（保证人资料）",
  files: [
    { id: "m-1", icon: "照", name: "营业执照.pdf", note: "已提取主体信息", status: "done" },
    { id: "m-2", icon: "报", name: "近三年财报.xlsx", note: "已分析营收与负债率", status: "done" },
    { id: "m-3", icon: "流", name: "对公账户流水.zip", note: "已匹配回款节奏", status: "warn" },
    { id: "m-4", icon: "押", name: "商铺评估报告.pdf", note: "评估 960 万 · 抵押率 75% 超线", status: "done" },
    { id: "m-5", icon: "保", name: "保证人资料", note: "客户尚未提交", status: "pending" },
  ],
};

const CORP_SOURCES: DataSourcesPanel = {
  summary: "5 项已接入",
  updated: "2026-04-22 · 实时",
  sources: [
    { id: "s-1", name: "客户基础信息库", desc: "工商、主体、关联校验", status: "online" },
    { id: "s-2", name: "央行征信 · 对公", desc: "对公简版 · 征信与担保记录", status: "online" },
    { id: "s-3", name: "税务信用评级", desc: "省税务总局 A/B/C 级", status: "online" },
    { id: "s-4", name: "司法与处罚链接", desc: "裁判文书、被执行、行政处罚", status: "online" },
    { id: "s-5", name: "行内同类客户饱和度", desc: "批发零售敞口占比 · 预警", status: "warn" },
  ],
};

const CORP_EVIDENCES: EvidencesPanel = {
  positive: [
    {
      id: "ev-p-1",
      icon: "正",
      title: "回款节奏稳定 · 近 12 月无明显拖延",
      detail: "账户流水显示主要客户按期回款，周期 42-48 天与行业中位一致",
      tone: "positive",
    },
    {
      id: "ev-p-2",
      icon: "正",
      title: "税务 A 级 · 无失信记录",
      detail: "国家企业信用网 + 裁判文书网 + 行政处罚公示库三查无命中",
      tone: "positive",
    },
    {
      id: "ev-p-3",
      icon: "正",
      title: "3 年复合增速 9.2%",
      detail: "稳健成长段 · 高于区域同类商贸平均 5.8%",
      tone: "positive",
    },
  ],
  warnings: [
    {
      id: "ev-w-1",
      icon: "提",
      title: "抵押率 75% 超阈 5pp",
      detail: "红线 RL-5 触发 warn · 需要补保证人或追加质押",
      tone: "warning",
    },
    {
      id: "ev-w-2",
      icon: "提",
      title: "行内同类客户饱和度偏高",
      detail: "批发零售行业敞口 29%，接近区域上限 32%",
      tone: "warning",
    },
  ],
  missing: [
    {
      id: "ev-m-1",
      icon: "缺",
      title: "保证人资料未提交",
      detail: "第二还款来源评估无法完成 · 影响担保维度最终评分",
      tone: "missing",
    },
  ],
};

const CORP_PROFILE: CreditProfile = {
  chips: ["成立 11 年", "批发零售细分龙头", "年营收 7420 万", "区域集中 · 闽中"],
  tagline: "基本面稳健、现金流可支撑中额度授信，担保维度是唯一 warn，建议补保证人后放款",
};

/* ══════════════════════════════════════════════════════
 * 普惠 · 厦门瑞鼎机电科技 · 普惠小微贷 300 万
 * ════════════════════════════════════════════════════ */

const SMALL_QUERY: CreditQuery = {
  id: "cr-xm-rdjd-0422",
  customer: "厦门瑞鼎机电科技有限公司",
  customerCode: "CR-2026-04-22-0021",
  product: "普惠小微贷",
  applyAmount: "300 万",
  applyTenor: "18 个月",
  purpose: "采购数控机床配件 · 扩产能",
  industry: "制造业 · 数控机床零部件",
  updated: "18 分钟前",
};

const SMALL_PIPELINE: CreditPipelineStep[] = [
  { id: "p-1", label: "消费 Agent6 报告", status: "done", note: "ReportJSON v7.23 · 302 项" },
  { id: "p-2", label: "四维评分", status: "done", note: "财 62 / 经 71 / 合 78 / 担 58" },
  { id: "p-3", label: "红线检查", status: "done", note: "5 项 · 2 过 3 警" },
  { id: "p-4", label: "案例召回", status: "active", note: "匹配中 · 行业相似度偏低" },
  { id: "p-5", label: "额度 · 期限 · 利率", status: "pending" },
  { id: "p-6", label: "送审贷会", status: "pending" },
];

const SMALL_RADAR: CreditRadarDim[] = [
  {
    key: "fin",
    label: "财务健康",
    score: 62,
    weight: 0.3,
    note: "毛利率 14.2% 偏薄 · 流动比 1.18 · 应收账款周转 63 天偏长",
    tags: ["毛利率 14.2%", "应收周期长"],
  },
  {
    key: "ops",
    label: "经营稳健",
    score: 71,
    weight: 0.3,
    note: "成立 6 年 · 年营收 2180 万 · 近 2 年增速 15%",
    tags: ["核心客户 5 家", "订单波动中等"],
  },
  {
    key: "comp",
    label: "合规征信",
    score: 78,
    weight: 0.25,
    note: "央行征信无不良 · 税务 B 级 · 近 12 月无逾期但有 2 笔关注",
    tags: ["税务 B 级", "有关注记录"],
  },
  {
    key: "guar",
    label: "担保增信",
    score: 58,
    weight: 0.15,
    note: "无抵押物 · 仅实控人连带保证 · 信用担保为主",
    tags: ["信用担保", "需追加抵押"],
  },
];

const SMALL_RED_LINES: RedLine[] = [
  {
    id: "rl-1",
    rule: "近 12 月 M3+ 逾期 = 0",
    detail: "核查通过 · 无 M3+ 逾期",
    status: "pass",
    citation: "央行征信 2026-04",
  },
  {
    id: "rl-2",
    rule: "税务评级 ≥ B",
    detail: "当前税务 B 级 · 恰在阈值",
    status: "warn",
    citation: "福建省税务总局 2025",
  },
  {
    id: "rl-3",
    rule: "核心客户集中度 ≤ 70%",
    detail: "前 3 大客户占比 68% · 接近上限",
    status: "warn",
    citation: "销售台账 2025-Q4",
  },
  {
    id: "rl-4",
    rule: "资产负债率 ≤ 75%",
    detail: "当前 69% · 距上限 6pp 缓冲",
    status: "pass",
    citation: "财报 2025-12 · 未审计",
  },
  {
    id: "rl-5",
    rule: "实控人征信无不良",
    detail: "实控人有 2 笔关注记录（非逾期）· 需人工复核",
    status: "warn",
    citation: "个人征信 2026-04",
  },
];

const SMALL_CASES: CaseRecall[] = [
  {
    id: "c-1",
    name: "泉州精诚机械小微 · 2025-10",
    similarity: 0.84,
    amount: "280 万",
    decision: "approved-cut",
    note: "同行业小微 · 信用担保 · 终批 220 万 / 12 月 / LPR+180bps",
    tags: ["信用担保", "小微"],
  },
  {
    id: "c-2",
    name: "漳州鑫源电子配件 · 2025-12",
    similarity: 0.79,
    amount: "350 万",
    decision: "approved-cut",
    note: "制造业小微 · 追加房产抵押后批 300 万 / 18 月 / LPR+150bps",
    tags: ["追加抵押", "LPR+150bps"],
  },
  {
    id: "c-3",
    name: "莆田顺达机加工 · 2026-02",
    similarity: 0.75,
    amount: "250 万",
    decision: "rejected",
    note: "同行业 · 但税务 C 级 + 实控人 M1 逾期 · 拒",
    tags: ["税务 C 级", "近期逾期"],
  },
];

const SMALL_LIMIT: LimitSuggestion = {
  applied: 300,
  suggested: 220,
  floor: 150,
  ceiling: 300,
  tenorMonths: 12,
  tenorRange: [6, 18],
  rateBps: 180,
  rateRange: [150, 220],
  rationale: [
    "无抵押 + 信用担保 · 额度下调至 220 万（申请额 73%）",
    "期限 12 月匹配订单回款周期 · 后续表现良好可续签",
    "LPR+180bps 参考案例 C-1 · 小微信用类溢价合理",
  ],
};

const SMALL_CONVERSATION: ConversationMessage[] = [
  {
    id: "crs-msg-1",
    at: "18 分钟前",
    kind: "system-event",
    content: "审贷 session 启动 · 客户：厦门瑞鼎机电科技 · 产品：普惠小微贷 · 申请 300 万 / 18 月",
  },
  {
    id: "crs-msg-2",
    at: "17 分钟前",
    kind: "ai-question",
    content:
      "小微客户 · 担保维度 58 分 + 财务维度 62 分是两个低分。主持人想先看哪一块：押担保薄弱的处置方案，还是财务指标的拆解？",
  },
  {
    id: "crs-msg-3",
    at: "14 分钟前",
    kind: "user-reply",
    content: "先看担保 · 小微放款几乎都信用担保，要看案例是怎么卡的",
  },
  {
    id: "crs-msg-4",
    at: "12 分钟前",
    kind: "ai-thinking",
    content: "拆解担保维度 + 召回小微类案例 · 识别能走的信用担保或追加抵押路径",
    thinking: {
      steps: [
        {
          label: "担保维度拆解",
          evidences: [
            "无房产抵押 · 实控人连带保证为唯一担保",
            "实控人个人征信：2 笔关注（2023 年某银行信用卡轻微逾期、2024 年汽车贷款晚还 3 天）",
            "触发红线 RL-5：实控人征信无不良（现状 warn，需人工复核）",
          ],
        },
        {
          label: "案例召回",
          evidences: [
            "C-1 泉州精诚机械（0.84）· 信用担保 · 批 220 万 / 12 月 / LPR+180bps",
            "C-2 漳州鑫源电子（0.79）· 追加房产抵押 · 批 300 万 / 18 月 / LPR+150bps",
            "C-3 莆田顺达（0.75）· 税务 C + 逾期 · 拒",
          ],
        },
      ],
    },
  },
  {
    id: "crs-msg-5",
    at: "8 分钟前",
    kind: "ai-response",
    content:
      "建议：金额下调至 220 万 · 期限 12 月 · LPR+180bps · 维持信用担保（pending · 需审贷会拍板）。可向客户询问是否能追加任一商铺抵押，若可追加则参考 C-2 批至 300 万 / 18 月。",
  },
  {
    id: "crs-msg-6",
    at: "4 分钟前",
    kind: "ai-question",
    content: "现在主持人希望发起客户追加抵押询问，还是直接提交审贷会走信用担保版？",
  },
];

const SMALL_MATERIALS: MaterialsPanel = {
  completeness: 72,
  missing: "实控人资产证明 1 项 · 订单合同 2 份",
  files: [
    { id: "m-1", icon: "照", name: "营业执照.pdf", note: "已提取主体信息", status: "done" },
    { id: "m-2", icon: "报", name: "2024 财报.xlsx", note: "未经审计 · 客户自填", status: "warn" },
    { id: "m-3", icon: "流", name: "对公流水.zip", note: "12 月流水已归集", status: "done" },
    { id: "m-4", icon: "征", name: "实控人征信.pdf", note: "2 笔关注需人工复核", status: "warn" },
    { id: "m-5", icon: "单", name: "订单合同", note: "尚缺 2 份主要客户合同", status: "pending" },
    { id: "m-6", icon: "产", name: "实控人资产证明", note: "客户尚未提交", status: "pending" },
  ],
};

const SMALL_SOURCES: DataSourcesPanel = {
  summary: "6 项已接入",
  updated: "2026-04-22 · 实时",
  sources: [
    { id: "s-1", name: "小微客户画像库", desc: "成立年限、行业、实控人画像", status: "online" },
    { id: "s-2", name: "央行征信 · 个人", desc: "实控人征信 + 连带保证记录", status: "online" },
    { id: "s-3", name: "央行征信 · 对公简版", desc: "基础征信 · 对公条线", status: "online" },
    { id: "s-4", name: "税务信用", desc: "省税务总局 A/B/C", status: "online" },
    { id: "s-5", name: "司法与处罚", desc: "裁判文书 + 被执行", status: "online" },
    { id: "s-6", name: "订单真实性校验", desc: "海关、物流单据联查", status: "warn" },
  ],
};

const SMALL_EVIDENCES: EvidencesPanel = {
  positive: [
    {
      id: "ev-p-1",
      icon: "正",
      title: "成长性好 · 2 年增速 15%",
      detail: "制造业小微细分，高于行业平均 8%",
      tone: "positive",
    },
    {
      id: "ev-p-2",
      icon: "正",
      title: "主要客户关系稳定",
      detail: "与前 3 大客户合作均超过 3 年，订单复购率 78%",
      tone: "positive",
    },
  ],
  warnings: [
    {
      id: "ev-w-1",
      icon: "提",
      title: "核心客户集中度 68% · 接近 70% 上限",
      detail: "前 3 大客户占比高，单一客户流失会导致明显波动",
      tone: "warning",
    },
    {
      id: "ev-w-2",
      icon: "提",
      title: "实控人征信 2 笔关注",
      detail: "非逾期但需人工复核 · 会影响担保维度最终分",
      tone: "warning",
    },
    {
      id: "ev-w-3",
      icon: "提",
      title: "财报未经审计",
      detail: "2024 财报客户自填，关键指标（毛利、应收周转）需现场访谈核对",
      tone: "warning",
    },
  ],
  missing: [
    {
      id: "ev-m-1",
      icon: "缺",
      title: "实控人资产证明未提交",
      detail: "无法核实连带保证的实际担保能力",
      tone: "missing",
    },
    {
      id: "ev-m-2",
      icon: "缺",
      title: "2 份核心客户合同未到",
      detail: "订单真实性只能靠流水间接验证",
      tone: "missing",
    },
  ],
};

const SMALL_PROFILE: CreditProfile = {
  chips: ["成立 6 年", "制造业小微", "年营收 2180 万", "无抵押 · 信用担保"],
  tagline: "小微信用担保类 · 担保薄、客户集中度偏高，建议下调金额至 220 万并跟进资产证明",
};

/* ══════════════════════════════════════════════════════
 * 对私 · 王晨曦 · 对私消费贷 50 万
 * ════════════════════════════════════════════════════ */

const RETAIL_QUERY: CreditQuery = {
  id: "cr-wcx-0422",
  customer: "王晨曦",
  customerCode: "CR-2026-04-22-PR-0054",
  product: "对私消费贷",
  applyAmount: "50 万",
  applyTenor: "36 个月",
  purpose: "装修自住房 + 教育支出",
  industry: "零售客群 · 工薪 + 个体复合",
  updated: "6 分钟前",
};

const RETAIL_PIPELINE: CreditPipelineStep[] = [
  { id: "p-1", label: "消费身份与资产材料", status: "done", note: "身份证 / 工资流水 / 房产证" },
  { id: "p-2", label: "四维评分", status: "done", note: "财 86 / 经 90 / 合 92 / 担 83" },
  { id: "p-3", label: "红线检查", status: "done", note: "5 项 · 5 过 0 警" },
  { id: "p-4", label: "案例召回", status: "done", note: "3 个同画像案例 · 相似度 ≥ 0.85" },
  { id: "p-5", label: "额度 · 期限 · 利率", status: "done", note: "50 万 / 36 月 / LPR+60bps" },
  { id: "p-6", label: "快速审批", status: "done", note: "优先推荐 · 标准化通道" },
];

const RETAIL_RADAR: CreditRadarDim[] = [
  {
    key: "fin",
    label: "个人偿付",
    score: 86,
    weight: 0.3,
    note: "月均税后收入 3.8 万 · 月供建议 1.4 万 · 偿付比 37%",
    tags: ["月入 3.8 万", "偿付比 37%"],
  },
  {
    key: "ops",
    label: "职业稳定",
    score: 90,
    weight: 0.25,
    note: "工龄 6 年 · 现单位 4 年 · 个体经营副业 3 年（母婴店）",
    tags: ["工龄 6 年", "双收入源"],
  },
  {
    key: "comp",
    label: "征信表现",
    score: 92,
    weight: 0.3,
    note: "央行征信无逾期无关注 · 近 24 月查询次数 4 次（均为自查）",
    tags: ["无逾期", "查询正常"],
  },
  {
    key: "guar",
    label: "客群空间",
    score: 83,
    weight: 0.15,
    note: "零售客群敞口充足 · 同画像客户余额占比 6.2%（上限 12%）",
    tags: ["信用为主", "空间充足"],
  },
];

const RETAIL_RED_LINES: RedLine[] = [
  {
    id: "rl-1",
    rule: "近 12 月 M1+ 逾期 = 0",
    detail: "无任何逾期记录",
    status: "pass",
    citation: "央行征信 2026-04",
  },
  {
    id: "rl-2",
    rule: "DTI ≤ 55%",
    detail: "当前 37% · 距上限 18pp",
    status: "pass",
    citation: "负债测算 2026-04",
  },
  {
    id: "rl-3",
    rule: "无黑名单/反欺诈命中",
    detail: "反欺诈规则库全查无命中",
    status: "pass",
    citation: "反欺诈 2026-04-22",
  },
  {
    id: "rl-4",
    rule: "工龄 ≥ 2 年",
    detail: "工龄 6 年 · 现单位 4 年",
    status: "pass",
    citation: "社保记录 2026-04",
  },
  {
    id: "rl-5",
    rule: "月收入 ≥ 月供 × 2",
    detail: "3.8 万 ≥ 1.4 万 × 2 · 覆盖 2.7 倍",
    status: "pass",
    citation: "工资流水 12 月",
  },
];

const RETAIL_CASES: CaseRecall[] = [
  {
    id: "c-1",
    name: "同画像客户 · 2025-12（厦门·工薪+个体）",
    similarity: 0.92,
    amount: "48 万",
    decision: "approved",
    note: "终批 48 万 / 36 月 / LPR+55bps · 标准化快速审批",
    tags: ["双收入", "工龄 5 年"],
  },
  {
    id: "c-2",
    name: "同画像客户 · 2026-01（漳州·纯工薪）",
    similarity: 0.88,
    amount: "40 万",
    decision: "approved",
    note: "终批 40 万 / 30 月 / LPR+70bps · 纯工薪溢价略高",
    tags: ["工薪", "低负债"],
  },
  {
    id: "c-3",
    name: "同画像客户 · 2025-11（福州·征信良好）",
    similarity: 0.85,
    amount: "55 万",
    decision: "approved",
    note: "终批 50 万 / 36 月 / LPR+60bps · 近乎满额批",
    tags: ["征信优秀", "余额占比低"],
  },
];

const RETAIL_LIMIT: LimitSuggestion = {
  applied: 50,
  suggested: 50,
  floor: 30,
  ceiling: 60,
  tenorMonths: 36,
  tenorRange: [24, 48],
  rateBps: 60,
  rateRange: [50, 90],
  rationale: [
    "双收入源 + 征信干净 · 无需下调，按申请额 50 万足额批",
    "期限 36 月匹配装修 + 教育中期支出节奏",
    "LPR+60bps 参考 C-1/C-3 中位 · 优质客群溢价低",
  ],
};

const RETAIL_CONVERSATION: ConversationMessage[] = [
  {
    id: "crr-msg-1",
    at: "6 分钟前",
    kind: "system-event",
    content: "审贷 session 启动 · 客户：王晨曦 · 产品：对私消费贷 · 申请 50 万 / 36 月",
  },
  {
    id: "crr-msg-2",
    at: "5 分钟前",
    kind: "ai-response",
    content:
      "客户综合分 88 · 征信干净 · 双收入源（工薪+个体）· 负债健康度高。四维均在 83 分以上，无红线 warn。建议走标准化快速审批通道。",
  },
  {
    id: "crr-msg-3",
    at: "4 分钟前",
    kind: "user-reply",
    content: "双收入源的个体经营部分稳定吗？",
  },
  {
    id: "crr-msg-4",
    at: "3 分钟前",
    kind: "ai-thinking",
    content: "核查客户个体经营副业的收入稳定性",
    thinking: {
      steps: [
        {
          label: "个体经营画像",
          evidences: [
            "母婴店 · 位于集美区 · 经营 3 年",
            "月均流水 3.6 万 · 净利约 1.2 万",
            "位置固定 · 口碑稳定（点评 4.5 分）",
          ],
        },
        {
          label: "双收入交叉验证",
          evidences: [
            "工资流水：每月固定 25 日到账 2.6 万",
            "个体经营：每日流水 800-1500 元 · 月均 1.2 万",
            "总月入 3.8 万 · 税后可支配约 3.4 万",
          ],
        },
      ],
    },
  },
  {
    id: "crr-msg-5",
    at: "1 分钟前",
    kind: "ai-response",
    content:
      "个体经营稳定 · 与工薪收入形成互补。综合判断：无需下调，50 万满额批 / 36 月 / LPR+60bps · 标准化快速审批。",
  },
  {
    id: "crr-msg-6",
    at: "刚刚",
    kind: "user-command",
    content: "/lock 50 万 · 36 月 · LPR+60bps · 标准化通道 · 直接放款",
  },
];

const RETAIL_MATERIALS: MaterialsPanel = {
  completeness: 91,
  missing: "婚姻证明 1 项",
  files: [
    { id: "m-1", icon: "身", name: "身份证明.pdf", note: "已校验身份与住址", status: "done" },
    { id: "m-2", icon: "信", name: "个人征信.pdf", note: "无逾期 · 查询正常", status: "done" },
    { id: "m-3", icon: "收", name: "工资流水.xlsx", note: "已分析收入稳定性", status: "done" },
    { id: "m-4", icon: "商", name: "个体经营流水.xlsx", note: "已匹配母婴店经营数据", status: "done" },
    { id: "m-5", icon: "房", name: "房产证明.pdf", note: "已识别自有不动产", status: "done" },
    { id: "m-6", icon: "婚", name: "婚姻证明", note: "客户尚未补交", status: "pending" },
  ],
};

const RETAIL_SOURCES: DataSourcesPanel = {
  summary: "6 项已接入",
  updated: "2026-04-22 · 实时",
  sources: [
    { id: "s-1", name: "央行征信 · 个人", desc: "征信表现与负债校验", status: "online" },
    { id: "s-2", name: "社保记录", desc: "工龄与现单位年限", status: "online" },
    { id: "s-3", name: "个体经营画像库", desc: "经营稳定性与业态匹配", status: "online" },
    { id: "s-4", name: "零售客群画像库", desc: "同画像客户结构与空间", status: "online" },
    { id: "s-5", name: "反欺诈规则库", desc: "异常行为与黑名单校验", status: "online" },
    { id: "s-6", name: "房产估值接口", desc: "自有房产市价", status: "online" },
  ],
};

const RETAIL_EVIDENCES: EvidencesPanel = {
  positive: [
    {
      id: "ev-p-1",
      icon: "正",
      title: "双收入源稳定 · 工薪 + 个体",
      detail: "工资 2.6 万 + 个体 1.2 万 · 两条独立现金流",
      tone: "positive",
    },
    {
      id: "ev-p-2",
      icon: "正",
      title: "征信优秀 · 近 24 月无逾期",
      detail: "查询次数 4 次均为自查 · 无多头借贷信号",
      tone: "positive",
    },
    {
      id: "ev-p-3",
      icon: "正",
      title: "DTI 37% · 远低于 55% 上限",
      detail: "偿付能力有明显余地，可承接装修 + 教育两笔中期支出",
      tone: "positive",
    },
    {
      id: "ev-p-4",
      icon: "正",
      title: "同画像客群敞口充足",
      detail: "零售客群余额占比 6.2%，距上限 12% 有空间，不触区域饱和度",
      tone: "positive",
    },
  ],
  warnings: [],
  missing: [
    {
      id: "ev-m-1",
      icon: "缺",
      title: "婚姻证明未补交",
      detail: "不影响本笔批准 · 配偶家庭负债测算无此项可精确到户",
      tone: "missing",
    },
  ],
};

const RETAIL_PROFILE: CreditProfile = {
  chips: ["工龄 6 年", "双收入源", "征信优秀", "房产自有"],
  tagline: "个人优质客群 · 双收入稳定、征信干净，建议满额批 50 万走标准化快速审批",
};

/* ══════════════════════════════════════════════════════
 * 共享 Recent 列表（三模使用相同近期历史）
 * ════════════════════════════════════════════════════ */

const RECENT: CreditRecentSession[] = [
  { id: "crr-1", customer: "福建惠民商贸", product: "对公经营贷", amount: "720 万", updated: "刚刚", decision: "approved-cut" },
  { id: "crr-2", customer: "漳州丰华食品", product: "普惠小微贷", amount: "180 万", updated: "1 小时前", decision: "approved" },
  { id: "crr-3", customer: "王晨曦", product: "对私消费贷", amount: "50 万", updated: "2 小时前", decision: "approved" },
  { id: "crr-4", customer: "泉州泰昌机械", product: "对公经营贷", amount: "1200 万", updated: "今天早上", decision: "pending" },
  { id: "crr-5", customer: "厦门瑞鼎机电", product: "普惠小微贷", amount: "220 万", updated: "18 分钟前", decision: "pending" },
  { id: "crr-6", customer: "福州兴达建材", product: "对私经营贷", amount: "300 万", updated: "昨天", decision: "rejected" },
];

/* ══════════════════════════════════════════════════════
 * 组装 · 三套 CreditSession
 * ════════════════════════════════════════════════════ */

const CORP_SESSION: CreditSession = {
  id: "credit-corp-0422",
  mode: "corp",
  objective: "福建惠民商贸 · 对公经营贷 800 万 · 审贷决策",
  stage: "已锁版 · 待审贷会表决",
  updated: "刚刚",
  profile: CORP_PROFILE,
  query: CORP_QUERY,
  pipeline: CORP_PIPELINE,
  radar: CORP_RADAR,
  overallScore: 75,
  decision: "approved-cut",
  limit: CORP_LIMIT,
  redLines: CORP_RED_LINES,
  cases: CORP_CASES,
  conversation: CORP_CONVERSATION,
  qcCounts: { block: 0, warn: 1, info: 3 },
  recentSessions: RECENT,
  materials: CORP_MATERIALS,
  dataSources: CORP_SOURCES,
  evidences: CORP_EVIDENCES,
  generateSteps: GEN_STEPS,
};

const SMALL_SESSION: CreditSession = {
  id: "credit-small-0422",
  mode: "small",
  objective: "厦门瑞鼎机电 · 普惠小微贷 300 万 · 审贷决策",
  stage: "评估中 · 召回案例",
  updated: "4 分钟前",
  profile: SMALL_PROFILE,
  query: SMALL_QUERY,
  pipeline: SMALL_PIPELINE,
  radar: SMALL_RADAR,
  overallScore: 66,
  decision: "pending",
  limit: SMALL_LIMIT,
  redLines: SMALL_RED_LINES,
  cases: SMALL_CASES,
  conversation: SMALL_CONVERSATION,
  qcCounts: { block: 0, warn: 3, info: 2 },
  recentSessions: RECENT,
  materials: SMALL_MATERIALS,
  dataSources: SMALL_SOURCES,
  evidences: SMALL_EVIDENCES,
  generateSteps: GEN_STEPS,
};

const RETAIL_SESSION: CreditSession = {
  id: "credit-retail-0422",
  mode: "retail",
  objective: "王晨曦 · 对私消费贷 50 万 · 快速审批",
  stage: "已批 · 快速审批通道",
  updated: "刚刚",
  profile: RETAIL_PROFILE,
  query: RETAIL_QUERY,
  pipeline: RETAIL_PIPELINE,
  radar: RETAIL_RADAR,
  overallScore: 88,
  decision: "approved",
  limit: RETAIL_LIMIT,
  redLines: RETAIL_RED_LINES,
  cases: RETAIL_CASES,
  conversation: RETAIL_CONVERSATION,
  qcCounts: { block: 0, warn: 0, info: 4 },
  recentSessions: RECENT,
  materials: RETAIL_MATERIALS,
  dataSources: RETAIL_SOURCES,
  evidences: RETAIL_EVIDENCES,
  generateSteps: GEN_STEPS,
};

/* ══════════════════════════════════════════════════════
 * 导出 · 三套合集 + 向后兼容 alias
 * ════════════════════════════════════════════════════ */

export const CREDIT_SESSIONS: Record<CreditMode, CreditSession> = {
  corp: CORP_SESSION,
  small: SMALL_SESSION,
  retail: RETAIL_SESSION,
};

/** Backward-compat · 旧 import { CREDIT_SESSION } 指向 corp 默认 */
export const CREDIT_SESSION: CreditSession = CORP_SESSION;

/* ══════════════════════════════════════════════════════
 * 对公 · 中锐网络科技 · SaaS · 关联交易软红线 · approved-cut
 * （难度: hard · 关联交易 32% 软红线可豁免 · 应收账款 140 天）
 * ════════════════════════════════════════════════════ */

const ZHONGRUI_QUERY: CreditQuery = {
  id: "cr-zr-saas-0428",
  customer: "中锐网络科技股份有限公司",
  customerCode: "CR-2026-04-28-0103",
  product: "对公经营贷",
  applyAmount: "500 万",
  applyTenor: "24 个月",
  purpose: "SaaS 产品研发投入 + 销售扩张周转",
  industry: "信息技术服务 · 企业级 SaaS",
  updated: "1 小时前",
};

const ZHONGRUI_PIPELINE: CreditPipelineStep[] = [
  { id: "p-1", label: "消费 Agent6 报告", status: "done", note: "ReportJSON v7.23 · 388 项" },
  { id: "p-2", label: "四维评分", status: "done", note: "财 64 / 经 70 / 合 73 / 担 60" },
  { id: "p-3", label: "红线检查", status: "done", note: "7 项 · 5 过 2 警（关联交易 + 应收账龄）" },
  { id: "p-4", label: "案例召回", status: "done", note: "3 个相似 SaaS 案例 · 相似度 ≥ 0.81" },
  { id: "p-5", label: "额度 · 期限 · 利率", status: "done", note: "380 万 / 18 月 / LPR+150bps" },
  { id: "p-6", label: "送审贷会", status: "pending", note: "需主审会议豁免关联交易软红线" },
];

const ZHONGRUI_RADAR: CreditRadarDim[] = [
  {
    key: "fin",
    label: "财务健康",
    score: 64,
    weight: 0.3,
    note: "毛利率 58% 高（SaaS 行业特征）· 流动比 1.21 · 应收账款周转 140 天偏长",
    tags: ["毛利 58%", "应收 140 天"],
  },
  {
    key: "ops",
    label: "经营稳健",
    score: 70,
    weight: 0.3,
    note: "成立 7 年 · ARR 4200 万 · NDR 112% · 客户续约率 87%",
    tags: ["NDR 112%", "续约 87%"],
  },
  {
    key: "comp",
    label: "合规征信",
    score: 73,
    weight: 0.25,
    note: "央行征信无不良 · 税务 B 级 · 关联交易占比 32%（软红线 · 集团内 SaaS 互购）",
    tags: ["关联交易 32%", "税务 B"],
  },
  {
    key: "guar",
    label: "担保增信",
    score: 60,
    weight: 0.15,
    note: "无土地房产 · 软件著作权 + 应收账款质押 · 控股股东连带保证",
    tags: ["软资产质押", "股东连带"],
  },
];

const ZHONGRUI_RED_LINES: RedLine[] = [
  {
    id: "rl-1",
    rule: "近 12 月 M3+ 逾期 = 0",
    detail: "核查通过 · 无 M3+ 逾期",
    status: "pass",
    citation: "央行征信 2026-04",
  },
  {
    id: "rl-2",
    rule: "无失信/被执行/行政处罚",
    detail: "三库联查无命中",
    status: "pass",
    citation: "信用中国 2026-04-25",
  },
  {
    id: "rl-3",
    rule: "税务评级 ≥ B",
    detail: "税务 B 级 · 恰在阈值",
    status: "pass",
    citation: "省税务总局 2025",
  },
  {
    id: "rl-4",
    rule: "资产负债率 ≤ 70%",
    detail: "当前 54% · 距上限 16pp",
    status: "pass",
    citation: "财报 2025-12 · 经审计",
  },
  {
    id: "rl-5",
    rule: "关联交易占比 ≤ 30%（软红线）",
    detail: "当前 32% · 超阈 2pp · SaaS 行业内集团互购属性可豁免，需主审会议批",
    status: "warn",
    citation: "审计报告 2025 · 关联方说明",
  },
  {
    id: "rl-6",
    rule: "应收账款账龄 ≤ 120 天",
    detail: "当前 140 天 · 超阈 20 天 · 大客户回款节奏决定",
    status: "warn",
    citation: "应收账款明细 2026-Q1",
  },
  {
    id: "rl-7",
    rule: "主营业务集中度 ≤ 60%",
    detail: "前 3 大客户占比 47% · 通过",
    status: "pass",
    citation: "销售台账 2025-Q4",
  },
];

const ZHONGRUI_CASES: CaseRecall[] = [
  {
    id: "c-1",
    name: "杭州睿启信息 · 2025-09（SaaS）",
    similarity: 0.88,
    amount: "600 万",
    decision: "approved-cut",
    note: "同业 SaaS · 关联交易 28% · 应收账款质押 · 终批 480 万 / 18 月 / LPR+140bps",
    tags: ["SaaS", "应收质押"],
  },
  {
    id: "c-2",
    name: "苏州云算软件 · 2025-12",
    similarity: 0.85,
    amount: "500 万",
    decision: "approved-cut",
    note: "同业 · 关联交易 35% 经主审会议豁免 · 终批 360 万 / 18 月 / LPR+160bps",
    tags: ["关联交易豁免", "B 级"],
  },
  {
    id: "c-3",
    name: "上海智云数据 · 2026-02",
    similarity: 0.81,
    amount: "800 万",
    decision: "rejected",
    note: "同业 · 但关联交易 41% + 应收 180 天 · 双警拒",
    tags: ["关联交易超线", "应收过长"],
  },
];

const ZHONGRUI_LIMIT: LimitSuggestion = {
  applied: 500,
  suggested: 380,
  floor: 300,
  ceiling: 500,
  tenorMonths: 18,
  tenorRange: [12, 24],
  rateBps: 150,
  rateRange: [130, 180],
  rationale: [
    "关联交易 32% 软红线超阈 2pp · 额度下调 24%（参考案例 C-2 经豁免后批 72%）",
    "应收账款 140 天偏长 · 期限收紧至 18 月匹配回款周期",
    "LPR+150bps 取案例 C-1/C-2 中位 · 反映软资产担保溢价",
  ],
};

const ZHONGRUI_CONVERSATION: ConversationMessage[] = [
  {
    id: "crz-msg-1",
    at: "1 小时前",
    kind: "system-event",
    content: "审贷 session 启动 · 客户：中锐网络科技 · 产品：对公经营贷 · 申请 500 万 / 24 月",
  },
  {
    id: "crz-msg-2",
    at: "55 分钟前",
    kind: "ai-response",
    content:
      "客户为 SaaS 行业 · 综合分 67 · 触发 2 项软红线警告：关联交易 32%（软红线 30%）+ 应收账款账龄 140 天（阈值 120 天）。两项均可经主审会议豁免，召回 3 个相似案例对照。",
  },
  {
    id: "crz-msg-3",
    at: "40 分钟前",
    kind: "user-reply",
    content: "关联交易这块仔细看一下，是真集团内业务还是套壳？",
  },
  {
    id: "crz-msg-4",
    at: "30 分钟前",
    kind: "ai-thinking",
    content: "拆解关联交易构成 · 验证商业实质 · 对照案例 C-2 豁免路径",
    thinking: {
      steps: [
        {
          label: "关联交易明细",
          evidences: [
            "总关联交易 1340 万 · 占总营收 32%",
            "构成：集团内 SaaS 服务互购 980 万（73%）+ 共享研发资源 210 万（16%）+ 关联方采购 150 万（11%）",
            "定价：均按市场公允价 · 经审计师核查无利益输送痕迹",
          ],
        },
        {
          label: "案例豁免路径对标",
          evidences: [
            "C-2 苏州云算（0.85）· 关联交易 35% · 主审会议出具豁免意见后批 72%",
            "豁免要件：商业实质成立 + 公允定价 + 审计师无保留意见",
            "本笔 3 项要件均满足 · 路径可行",
          ],
        },
      ],
    },
  },
  {
    id: "crz-msg-5",
    at: "10 分钟前",
    kind: "ai-response",
    content:
      "建议：批 380 万 / 18 月 / LPR+150bps · 等同打折批（approved-cut）· 前置条件 = 主审会议出具关联交易豁免意见 + 客户提供应收账款质押合同。",
  },
];

const ZHONGRUI_MATERIALS: MaterialsPanel = {
  completeness: 78,
  missing: "应收账款质押合同 1 份",
  files: [
    { id: "m-1", icon: "照", name: "营业执照.pdf", note: "已提取主体 + 关联方架构", status: "done" },
    { id: "m-2", icon: "审", name: "2025 经审计财报.pdf", note: "关联交易明细已抽取", status: "done" },
    { id: "m-3", icon: "应", name: "应收账款明细.xlsx", note: "账龄 140 天 · 超阈", status: "warn" },
    { id: "m-4", icon: "押", name: "应收账款质押合同", note: "客户尚未提交", status: "pending" },
  ],
};

const ZHONGRUI_SOURCES: DataSourcesPanel = {
  summary: "5 项已接入",
  updated: "2026-04-28 · 实时",
  sources: [
    { id: "s-1", name: "客户基础信息库", desc: "工商 + 关联方架构图", status: "online" },
    { id: "s-2", name: "央行征信 · 对公", desc: "征信与担保记录", status: "online" },
    { id: "s-3", name: "税务信用评级", desc: "省税务总局 A/B/C 级", status: "online" },
    { id: "s-4", name: "关联交易识别引擎", desc: "集团互购 · 公允定价校验", status: "online" },
    { id: "s-5", name: "行内 SaaS 行业敞口", desc: "信息技术服务饱和度", status: "online" },
  ],
};

const ZHONGRUI_EVIDENCES: EvidencesPanel = {
  positive: [
    {
      id: "ev-p-1",
      icon: "正",
      title: "SaaS 业务模型健康 · NDR 112%",
      detail: "续约率 87% · 净金额留存 112% 高于行业中位 105%",
      tone: "positive",
    },
    {
      id: "ev-p-2",
      icon: "正",
      title: "毛利率 58% · 高于行业中位",
      detail: "SaaS 行业特征 · 软件订阅型收入弹性好",
      tone: "positive",
    },
  ],
  warnings: [
    {
      id: "ev-w-1",
      icon: "提",
      title: "关联交易 32% · 触软红线",
      detail: "超阈 2pp · 商业实质成立 · 需主审会议豁免",
      tone: "warning",
    },
    {
      id: "ev-w-2",
      icon: "提",
      title: "应收账款 140 天 · 超阈 20 天",
      detail: "大客户回款慢 · 需补应收账款质押缓释",
      tone: "warning",
    },
  ],
  missing: [
    {
      id: "ev-m-1",
      icon: "缺",
      title: "应收账款质押合同未签",
      detail: "影响第二还款来源完成度 · 放款前置条件",
      tone: "missing",
    },
  ],
};

const ZHONGRUI_PROFILE: CreditProfile = {
  chips: ["成立 7 年", "企业级 SaaS", "ARR 4200 万", "集团旗下"],
  tagline: "SaaS 业务健康但关联交易触软红线 · 建议批 380 万、要求主审豁免 + 应收质押",
};

const ZHONGRUI_SESSION: CreditSession = {
  id: "cs-zhongrui-network",
  mode: "corp",
  objective: "中锐网络科技 · 对公经营贷 500 万 · 关联交易软红线豁免决策",
  stage: "待主审豁免 · 决议草稿已生成",
  updated: "10 分钟前",
  profile: ZHONGRUI_PROFILE,
  query: ZHONGRUI_QUERY,
  pipeline: ZHONGRUI_PIPELINE,
  radar: ZHONGRUI_RADAR,
  overallScore: 67,
  decision: "approved-cut",
  limit: ZHONGRUI_LIMIT,
  redLines: ZHONGRUI_RED_LINES,
  cases: ZHONGRUI_CASES,
  conversation: ZHONGRUI_CONVERSATION,
  qcCounts: { block: 0, warn: 2, info: 4 },
  recentSessions: RECENT,
  materials: ZHONGRUI_MATERIALS,
  dataSources: ZHONGRUI_SOURCES,
  evidences: ZHONGRUI_EVIDENCES,
  generateSteps: GEN_STEPS,
};

/* ══════════════════════════════════════════════════════
 * 对公 · 鼎盛商贸 · D 级 · 双红线 fail · rejected
 * （难度: extreme · 高负债率 0.78 + 关联方占款 · 直接拒）
 * ════════════════════════════════════════════════════ */

const DINGSHENG_QUERY: CreditQuery = {
  id: "cr-ds-trade-0427",
  customer: "鼎盛商贸有限公司",
  customerCode: "CR-2026-04-27-0089",
  product: "对公经营贷",
  applyAmount: "300 万",
  applyTenor: "12 个月",
  purpose: "补流 · 偿还到期借款",
  industry: "批发零售 · 建材",
  updated: "30 分钟前",
};

const DINGSHENG_PIPELINE: CreditPipelineStep[] = [
  { id: "p-1", label: "消费 Agent6 报告", status: "done", note: "ReportJSON v7.23 · 274 项" },
  { id: "p-2", label: "四维评分", status: "done", note: "财 32 / 经 38 / 合 41 / 担 28" },
  { id: "p-3", label: "红线检查", status: "done", note: "6 项 · 2 过 2 警 2 fail（双硬红线）" },
  { id: "p-4", label: "案例召回", status: "done", note: "3 个负面案例 · 全部拒贷" },
  { id: "p-5", label: "额度 · 期限 · 利率", status: "done", note: "拒贷 · 不出额度建议" },
  { id: "p-6", label: "送审贷会", status: "done", note: "已生成拒贷意见 · 自动下架" },
];

const DINGSHENG_RADAR: CreditRadarDim[] = [
  {
    key: "fin",
    label: "财务健康",
    score: 32,
    weight: 0.3,
    note: "毛利率 6.8% 极薄 · 流动比 0.79 · 资产负债率 78% 触红线 · 现金流连续 4 季度净流出",
    tags: ["负债率 78%", "现金净流出"],
  },
  {
    key: "ops",
    label: "经营稳健",
    score: 38,
    weight: 0.3,
    note: "成立 9 年但近 2 年营收下滑 22% · 核心客户流失 3 家 · 库存周转 218 天",
    tags: ["营收下滑 22%", "库存堆积"],
  },
  {
    key: "comp",
    label: "合规征信",
    score: 41,
    weight: 0.25,
    note: "近 12 月有 3 笔 M1+ 逾期 · 税务 C 级 · 控股股东 1 笔被执行（已结案）",
    tags: ["M1 逾期 3 笔", "税务 C"],
  },
  {
    key: "guar",
    label: "担保增信",
    score: 28,
    weight: 0.15,
    note: "抵押物为陈旧库存（建材 · 易跌价）· 估值水分大 · 关联方占款 480 万未归还",
    tags: ["关联方占款", "存货抵押"],
  },
];

const DINGSHENG_RED_LINES: RedLine[] = [
  {
    id: "rl-1",
    rule: "近 12 月 M3+ 逾期 = 0",
    detail: "无 M3+ · 但有 3 笔 M1+ · 接近上限",
    status: "warn",
    citation: "央行征信 2026-04",
  },
  {
    id: "rl-2",
    rule: "无失信/被执行/行政处罚",
    detail: "控股股东 1 笔被执行（2024-08 已结案）· 接近边线",
    status: "warn",
    citation: "信用中国 2026-04-26",
  },
  {
    id: "rl-3",
    rule: "税务评级 ≥ B",
    detail: "当前 C 级 · 触硬红线",
    status: "fail",
    citation: "省税务总局 2025",
  },
  {
    id: "rl-4",
    rule: "资产负债率 ≤ 70%",
    detail: "当前 78% · 超阈 8pp · 触硬红线",
    status: "fail",
    citation: "财报 2025-12 · 未审计",
  },
  {
    id: "rl-5",
    rule: "关联方占款 = 0",
    detail: "关联方占款 480 万 · 占净资产 31% · 严重侵蚀偿付能力",
    status: "fail",
    citation: "应收明细 2026-Q1",
  },
  {
    id: "rl-6",
    rule: "现金流为正",
    detail: "近 4 季度经营性现金流净流出 · 趋势恶化",
    status: "warn",
    citation: "现金流量表 2025",
  },
];

const DINGSHENG_CASES: CaseRecall[] = [
  {
    id: "c-1",
    name: "唐山兴隆建材贸易 · 2025-08",
    similarity: 0.89,
    amount: "400 万",
    decision: "rejected",
    note: "同业 · 负债率 76% + 关联方占款 · 拒贷",
    tags: ["建材", "负债率超线"],
  },
  {
    id: "c-2",
    name: "邯郸金顺商贸 · 2025-11",
    similarity: 0.84,
    amount: "350 万",
    decision: "rejected",
    note: "同业 · 税务 C 级 + 现金流恶化 · 拒贷",
    tags: ["税务 C", "现金流恶化"],
  },
  {
    id: "c-3",
    name: "石家庄宏达建材 · 2026-02",
    similarity: 0.82,
    amount: "300 万",
    decision: "rejected",
    note: "同业 · 库存周转 230 天 · 关联方占款 600 万 · 直接拒",
    tags: ["库存堆积", "关联方占款"],
  },
];

const DINGSHENG_LIMIT: LimitSuggestion = {
  applied: 300,
  suggested: 0,
  floor: 0,
  ceiling: 0,
  tenorMonths: 0,
  tenorRange: [0, 0],
  rateBps: 0,
  rateRange: [0, 0],
  rationale: [
    "触发 3 项硬红线（税务 C + 负债率 78% + 关联方占款 480 万）· 直接拒贷",
    "案例 C-1/C-2/C-3 同行业全部拒贷 · 无可比放款先例",
    "建议：客户先化解关联方占款 + 改善税务评级至 B 级后再行评估",
  ],
};

const DINGSHENG_CONVERSATION: ConversationMessage[] = [
  {
    id: "crd-msg-1",
    at: "30 分钟前",
    kind: "system-event",
    content: "审贷 session 启动 · 客户：鼎盛商贸 · 产品：对公经营贷 · 申请 300 万 / 12 月",
  },
  {
    id: "crd-msg-2",
    at: "28 分钟前",
    kind: "ai-response",
    content:
      "客户综合分 35 · 触发 3 项硬红线（税务 C + 负债率 78% + 关联方占款 480 万）· 直接进入拒贷判定。已召回 3 个同业案例对照确认。",
  },
  {
    id: "crd-msg-3",
    at: "20 分钟前",
    kind: "user-reply",
    content: "关联方占款这块走个明细，确认一下能不能短期化解",
  },
  {
    id: "crd-msg-4",
    at: "15 分钟前",
    kind: "ai-thinking",
    content: "拆解关联方占款明细 · 评估化解可能",
    thinking: {
      steps: [
        {
          label: "关联方占款明细",
          evidences: [
            "关联方 A（实控人配偶名下贸易公司）· 占款 320 万 · 形成于 2023-Q2 · 账龄 22 月",
            "关联方 B（实控人弟弟）· 占款 110 万 · 个人借款用途 · 无书面协议",
            "关联方 C（参股 30% 子公司）· 占款 50 万 · 投资性挪用",
            "合计 480 万 · 占净资产 31% · 远超监管 5% 提示线",
          ],
        },
        {
          label: "化解可行性评估",
          evidences: [
            "关联方 A 自身负债 280 万 · 短期无现金归还能力",
            "关联方 B 个人借款无文件支撑 · 法律追索难",
            "结论：3-6 月内无可见化解路径 · 不建议放款",
          ],
        },
      ],
    },
  },
  {
    id: "crd-msg-5",
    at: "5 分钟前",
    kind: "ai-response",
    content:
      "决策建议：拒贷（rejected）· 不出额度。关键依据 = 3 项硬红线齐发 + 关联方占款无短期化解路径 + 同业 3 个案例全部拒。已生成拒贷意见书草稿。",
  },
];

const DINGSHENG_MATERIALS: MaterialsPanel = {
  completeness: 65,
  missing: "审计报告 1 份 · 关联方化解承诺 1 份",
  files: [
    { id: "m-1", icon: "照", name: "营业执照.pdf", note: "已提取主体信息", status: "done" },
    { id: "m-2", icon: "报", name: "2025 财报.xlsx", note: "未审计 · 自填 · 数据可信度低", status: "warn" },
    { id: "m-3", icon: "征", name: "央行征信对公.pdf", note: "M1 逾期 3 笔", status: "warn" },
    { id: "m-4", icon: "审", name: "审计报告", note: "客户尚未提交", status: "pending" },
  ],
};

const DINGSHENG_SOURCES: DataSourcesPanel = {
  summary: "5 项已接入",
  updated: "2026-04-27 · 实时",
  sources: [
    { id: "s-1", name: "客户基础信息库", desc: "工商 + 关联方架构", status: "online" },
    { id: "s-2", name: "央行征信 · 对公", desc: "征信与逾期记录", status: "online" },
    { id: "s-3", name: "税务信用评级", desc: "省税务总局", status: "online" },
    { id: "s-4", name: "关联方占款识别", desc: "占款明细 + 账龄分布", status: "online" },
    { id: "s-5", name: "建材行业敞口", desc: "区域饱和 + 风险预警", status: "warn" },
  ],
};

const DINGSHENG_EVIDENCES: EvidencesPanel = {
  positive: [],
  warnings: [
    {
      id: "ev-w-1",
      icon: "提",
      title: "近 12 月 M1 逾期 3 笔",
      detail: "未升至 M3 但已显风险征兆",
      tone: "warning",
    },
    {
      id: "ev-w-2",
      icon: "提",
      title: "经营性现金流连续 4 季度净流出",
      detail: "趋势恶化 · 偿付能力被侵蚀",
      tone: "warning",
    },
    {
      id: "ev-w-3",
      icon: "提",
      title: "库存周转 218 天",
      detail: "建材积压 · 减值风险高",
      tone: "warning",
    },
  ],
  missing: [
    {
      id: "ev-m-1",
      icon: "缺",
      title: "经审计财报缺失",
      detail: "未审计版数据可信度无法评估",
      tone: "missing",
    },
  ],
};

const DINGSHENG_PROFILE: CreditProfile = {
  chips: ["成立 9 年", "建材批发", "营收下滑 22%", "高负债 + 关联方占款"],
  tagline: "3 项硬红线齐发（税务 C + 负债率 78% + 关联方占款 480 万）· 直接拒贷",
};

const DINGSHENG_SESSION: CreditSession = {
  id: "cs-dingsheng-trade",
  mode: "corp",
  objective: "鼎盛商贸 · 对公经营贷 300 万 · 双红线拒贷判定",
  stage: "已拒 · 拒贷意见书生成",
  updated: "5 分钟前",
  profile: DINGSHENG_PROFILE,
  query: DINGSHENG_QUERY,
  pipeline: DINGSHENG_PIPELINE,
  radar: DINGSHENG_RADAR,
  overallScore: 35,
  decision: "rejected",
  limit: DINGSHENG_LIMIT,
  redLines: DINGSHENG_RED_LINES,
  cases: DINGSHENG_CASES,
  conversation: DINGSHENG_CONVERSATION,
  qcCounts: { block: 3, warn: 4, info: 1 },
  recentSessions: RECENT,
  materials: DINGSHENG_MATERIALS,
  dataSources: DINGSHENG_SOURCES,
  evidences: DINGSHENG_EVIDENCES,
  generateSteps: GEN_STEPS,
};

/* ══════════════════════════════════════════════════════
 * 对私 · 王五 · 装修工头 · 810 优 · 房产抵押 · approved
 * （难度: simple · 评分卡子项均高 · 满额批 · LPR-10BP）
 * ════════════════════════════════════════════════════ */

const WANGWU_QUERY: CreditQuery = {
  id: "cr-ww-deco-0428",
  customer: "王五",
  customerCode: "CR-2026-04-28-PR-0066",
  product: "对私经营贷",
  applyAmount: "200 万",
  applyTenor: "60 个月",
  purpose: "装修队规模化运营 · 工程款周转 + 设备采购",
  industry: "建筑装饰 · 个体工头",
  updated: "20 分钟前",
};

const WANGWU_PIPELINE: CreditPipelineStep[] = [
  { id: "p-1", label: "消费身份与资产材料", status: "done", note: "身份证 / 流水 / 房产 / 工程合同" },
  { id: "p-2", label: "四维评分", status: "done", note: "财 84 / 经 86 / 合 92 / 担 88" },
  { id: "p-3", label: "红线检查", status: "done", note: "5 项 · 5 过 0 警" },
  { id: "p-4", label: "案例召回", status: "done", note: "3 个同画像案例 · 相似度 ≥ 0.83" },
  { id: "p-5", label: "额度 · 期限 · 利率", status: "done", note: "200 万 / 60 月 / LPR-10BP" },
  { id: "p-6", label: "快速审批", status: "done", note: "评分卡 810 · 优级通道" },
];

const WANGWU_RADAR: CreditRadarDim[] = [
  {
    key: "fin",
    label: "个人偿付",
    score: 84,
    weight: 0.3,
    note: "近 24 月装修工程结算流水月均 5.6 万 · 月供建议 3.8 万 · 偿付比 41%",
    tags: ["月入 5.6 万", "偿付比 41%"],
  },
  {
    key: "ops",
    label: "职业稳定",
    score: 86,
    weight: 0.25,
    note: "工龄 12 年 · 装修队规模 18 人 · 与 3 家精装公司常年合作",
    tags: ["工龄 12 年", "队伍稳定"],
  },
  {
    key: "comp",
    label: "征信表现",
    score: 92,
    weight: 0.3,
    note: "央行征信无逾期无关注 · 评分卡综合 810 优级 · 近 24 月查询次数 3 次",
    tags: ["评分 810", "无逾期"],
  },
  {
    key: "guar",
    label: "担保增信",
    score: 88,
    weight: 0.15,
    note: "自有住宅 1 套（评估 380 万）抵押 · 抵押率 53%",
    tags: ["房产抵押", "抵押率 53%"],
  },
];

const WANGWU_RED_LINES: RedLine[] = [
  {
    id: "rl-1",
    rule: "近 12 月 M1+ 逾期 = 0",
    detail: "无任何逾期",
    status: "pass",
    citation: "央行征信 2026-04",
  },
  {
    id: "rl-2",
    rule: "DTI ≤ 55%",
    detail: "当前 41% · 距上限 14pp",
    status: "pass",
    citation: "负债测算 2026-04",
  },
  {
    id: "rl-3",
    rule: "无黑名单/反欺诈命中",
    detail: "全查无命中",
    status: "pass",
    citation: "反欺诈 2026-04-28",
  },
  {
    id: "rl-4",
    rule: "经营年限 ≥ 3 年",
    detail: "工龄 12 年 · 装修队成立 8 年",
    status: "pass",
    citation: "工程合同 + 流水佐证",
  },
  {
    id: "rl-5",
    rule: "抵押率 ≤ 70%",
    detail: "200/380 = 53% · 充裕",
    status: "pass",
    citation: "评估报告 2026-03",
  },
];

const WANGWU_CASES: CaseRecall[] = [
  {
    id: "c-1",
    name: "同画像客户 · 2025-12（厦门·装修工头）",
    similarity: 0.93,
    amount: "200 万",
    decision: "approved",
    note: "终批 200 万 / 60 月 / LPR-15BP · 评分 815 优级通道",
    tags: ["装修", "评分 815"],
  },
  {
    id: "c-2",
    name: "同画像客户 · 2026-01（漳州·建装个体）",
    similarity: 0.88,
    amount: "180 万",
    decision: "approved",
    note: "终批 180 万 / 48 月 / LPR-5BP · 房产抵押率 58%",
    tags: ["建装", "房产抵押"],
  },
  {
    id: "c-3",
    name: "同画像客户 · 2025-11（福州·工程承包）",
    similarity: 0.83,
    amount: "220 万",
    decision: "approved",
    note: "终批 200 万 / 60 月 / LPR-10BP · 评分 805",
    tags: ["工程承包", "满额批"],
  },
];

const WANGWU_LIMIT: LimitSuggestion = {
  applied: 200,
  suggested: 200,
  floor: 150,
  ceiling: 240,
  tenorMonths: 60,
  tenorRange: [36, 60],
  rateBps: -10,
  rateRange: [-15, 5],
  rationale: [
    "评分卡 810 优级 · 满额批 200 万",
    "期限 60 月匹配工程款长周期回笼 · 月供压力小",
    "LPR-10BP 取案例 C-1/C-3 中位 · 优级客群享利率优惠",
  ],
};

const WANGWU_CONVERSATION: ConversationMessage[] = [
  {
    id: "crw-msg-1",
    at: "20 分钟前",
    kind: "system-event",
    content: "审贷 session 启动 · 客户：王五 · 产品：对私经营贷 · 申请 200 万 / 60 月",
  },
  {
    id: "crw-msg-2",
    at: "18 分钟前",
    kind: "ai-response",
    content:
      "客户综合分 87 · 评分卡 810 优级 · 房产抵押率仅 53% · 征信干净 · 工龄 12 年。四维全部高分，无红线警告。建议走优级快速审批通道。",
  },
  {
    id: "crw-msg-3",
    at: "10 分钟前",
    kind: "user-reply",
    content: "工程款回款节奏怎么样？60 月期限会不会偏长",
  },
  {
    id: "crw-msg-4",
    at: "5 分钟前",
    kind: "ai-thinking",
    content: "校验工程款回款节奏与期限匹配度",
    thinking: {
      steps: [
        {
          label: "工程款回款画像",
          evidences: [
            "客户与 3 家精装公司常年合作 · 回款节奏稳定（结算后 30-60 天到账）",
            "近 24 月月均到账 5.6 万 · 季节波动 ±18% 在可控范围",
            "60 月期限可平摊月供至 3.8 万 · 偿付比 41%（健康区间）",
          ],
        },
      ],
    },
  },
  {
    id: "crw-msg-5",
    at: "1 分钟前",
    kind: "ai-response",
    content:
      "评估通过 · 60 月期限合理。最终建议：满额 200 万 / 60 月 / LPR-10BP · 优级快速审批通道直接放款。",
  },
];

const WANGWU_MATERIALS: MaterialsPanel = {
  completeness: 96,
  missing: "",
  files: [
    { id: "m-1", icon: "身", name: "身份证明.pdf", note: "已校验身份与住址", status: "done" },
    { id: "m-2", icon: "信", name: "个人征信.pdf", note: "无逾期 · 评分 810", status: "done" },
    { id: "m-3", icon: "流", name: "工程结算流水.xlsx", note: "近 24 月已分析", status: "done" },
    { id: "m-4", icon: "房", name: "房产评估报告.pdf", note: "评估 380 万 · 抵押率 53%", status: "done" },
  ],
};

const WANGWU_SOURCES: DataSourcesPanel = {
  summary: "5 项已接入",
  updated: "2026-04-28 · 实时",
  sources: [
    { id: "s-1", name: "央行征信 · 个人", desc: "征信表现 + 评分卡", status: "online" },
    { id: "s-2", name: "工程合同登记库", desc: "近 24 月合同明细", status: "online" },
    { id: "s-3", name: "结算流水归集", desc: "三家合作方付款节奏", status: "online" },
    { id: "s-4", name: "反欺诈规则库", desc: "异常行为校验", status: "online" },
    { id: "s-5", name: "房产估值接口", desc: "自有房产市价", status: "online" },
  ],
};

const WANGWU_EVIDENCES: EvidencesPanel = {
  positive: [
    {
      id: "ev-p-1",
      icon: "正",
      title: "评分卡 810 · 优级客群",
      detail: "高于优级阈值 750 · 享利率优惠通道",
      tone: "positive",
    },
    {
      id: "ev-p-2",
      icon: "正",
      title: "工程款回款稳定 · 月均 5.6 万",
      detail: "近 24 月与 3 家精装公司合作 · 季节波动可控",
      tone: "positive",
    },
    {
      id: "ev-p-3",
      icon: "正",
      title: "房产抵押率 53% · 充裕",
      detail: "自有住宅评估 380 万 · 抵押缓释充足",
      tone: "positive",
    },
  ],
  warnings: [],
  missing: [],
};

const WANGWU_PROFILE: CreditProfile = {
  chips: ["工龄 12 年", "装修工头 18 人队", "评分 810", "房产自有"],
  tagline: "优级客群 · 评分 810 + 房产抵押充裕，建议满额批 200 万走优级通道",
};

const WANGWU_SESSION: CreditSession = {
  id: "cs-wangwu-decoration",
  mode: "retail",
  objective: "王五 · 对私经营贷 200 万 · 优级快速审批",
  stage: "已批 · 优级快速审批通道",
  updated: "刚刚",
  profile: WANGWU_PROFILE,
  query: WANGWU_QUERY,
  pipeline: WANGWU_PIPELINE,
  radar: WANGWU_RADAR,
  overallScore: 87,
  decision: "approved",
  limit: WANGWU_LIMIT,
  redLines: WANGWU_RED_LINES,
  cases: WANGWU_CASES,
  conversation: WANGWU_CONVERSATION,
  qcCounts: { block: 0, warn: 0, info: 5 },
  recentSessions: RECENT,
  materials: WANGWU_MATERIALS,
  dataSources: WANGWU_SOURCES,
  evidences: WANGWU_EVIDENCES,
  generateSteps: GEN_STEPS,
};

/* ── 新出口 (Phase A worker-A4 · workspace-state-protocol §2 适配) ───── */

/** 全 mock sessions array · 反 5 原则 #2 难度分层覆盖 (1 simple + 3 medium + 1 hard + 1 extreme) */
export const CREDIT_MOCK_SESSIONS: CreditSession[] = [
  CORP_SESSION,        // medium · 福建惠民商贸 · approved-cut B+
  SMALL_SESSION,       // medium · 厦门瑞鼎机电 · pending B
  RETAIL_SESSION,      // medium · 张三 · approved 720
  ZHONGRUI_SESSION,    // hard   · 中锐网络 · 关联交易软红线 approved-cut
  DINGSHENG_SESSION,   // extreme · 鼎盛商贸 · 双红线 rejected
  WANGWU_SESSION,      // simple · 王五装修 · 810 approved
];

/** id → session 查找 · panel 单点派生用 */
export const CREDIT_MOCK_SESSIONS_MAP: Record<string, CreditSession> =
  Object.fromEntries(CREDIT_MOCK_SESSIONS.map((s) => [s.id, s])) as Record<string, CreditSession>;

/** EmptyState skeleton 之后 · started=true 时第一个加载的 session id */
export const CREDIT_DEFAULT_SESSION_ID = CORP_SESSION.id;
