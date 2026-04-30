/**
 * Agent Report · 单 session 对话式工作流 mock（2026-04-21 redesign）
 * 替代 agent-report.ts 的「多 draft 列表」语义，改为单 session 的
 * template / materials / timeline / conversation / preview 五块完整 shape。
 * P1 骨架阶段 · P2-P4 panel 直接消费本文件。
 */

export const REPORT_GLOBAL_STATS = {
  weeklyProcessed: "82",
  successRate: "93.5%",
  avgDuration: "11.4 分钟",
} as const;

/* ── 类型 ─────────────────────────────────────────────── */

export type ReportTemplate = {
  id: string;
  name: string;
  kind: "预置" | "自定义";
  version: string;
  fieldTotal: number;
  recentUsed: number;
};

export type ReportMaterial = {
  id: string;
  name: string;
  kind: "pdf" | "docx" | "xlsx" | "img";
  pages: number;
  bytes: string;
  parsed: boolean;
  parseNote: string;
  linkedSections: string[];
};

export type TimelineEvent = {
  id: string;
  at: string;
  kind:
    | "template.select"
    | "material.upload"
    | "material.parsed"
    | "ai.question"
    | "user.reply"
    | "section.done"
    | "qc.run"
    | "export";
  priority: "p0" | "p1" | "p2" | "done";
  label: string;
  detail?: string;
};

/**
 * RefCardPayload · 拖入对话框生成「ref-card」消息的 payload。
 * 来源：PANEL_PIN 拖拽载荷（或 CARD_PIN 退化载荷），composer 解析后 emit 给
 * conversation state，以 ConversationMessage.kind = "ref-card" 入流。
 */
export type RefCardPayload = {
  /** 主标题（e.g. "营销优先级雷达"）。 */
  title: string;
  /** 副标题（e.g. "获客 · 厦门瑞鼎"），可空。 */
  subtitle?: string;
  /** 1-2 行摘要（预览态），未来接 snapshot API 后展开为全文。 */
  blurb?: string;
  /** 点击"跳转"时 router.push 目标路由。 */
  href?: string;
  /** 源 workspace 的 agent key（channel / credit / ...）。 */
  agentKey?: string;
  /** 6 Agent 功能色 CSS var 名（如 `--t-channel`），用于卡片 accent。 */
  accentVar?: string;
};

export type ConversationMessage = {
  id: string;
  at: string;
  kind:
    | "ai-question"
    | "user-reply"
    | "user-command"
    | "ai-response"
    | "system-event"
    | "ai-thinking"
    | "ref-card";
  content: string;
  fieldRef?: string;
  sectionDiff?: {
    sectionAnchor: string;
    before?: string;
    after: string;
  };
  thinking?: {
    steps: { label: string; evidences: string[] }[];
  };
  /** kind === "ref-card" 时必填。 */
  refPayload?: RefCardPayload;
  /** kind === "ref-card" 时 optional · 发送者显示名（默认"客户经理 · 王哲"）。 */
  speaker?: string;
};

export type PreviewField = {
  id: string;
  label: string;
  state: "filled" | "unfilled" | "uncertain";
  value?: string;
  source?: string;
  qc?: {
    level: "block" | "warn" | "info";
    detail: string;
  };
};

export type PreviewSection = {
  id: string;
  anchor: string;
  title: string;
  filled: number;
  total: number;
  marked: number;
  evidenceRate: number;
  status: "pending" | "running" | "ok" | "needs-review";
  content?: string;
  fields: PreviewField[];
};

export type RecentSession = {
  id: string;
  clientName: string;
  updated: string;
  progress: number;
  stage: string;
};

export type ReportSession = {
  id: string;
  clientName: string;
  amount: string;
  stage: string;
  updated: string;
  template: ReportTemplate;
  availableTemplates: ReportTemplate[];
  materials: ReportMaterial[];
  timeline: TimelineEvent[];
  conversation: ConversationMessage[];
  preview: PreviewSection[];
  coverage: { filled: number; total: number; marked: number };
  qcCounts: { block: number; warn: number; info: number };
  recentSessions: RecentSession[];
};

/* ── 常量 ─────────────────────────────────────────────── */

const TEMPLATES: ReportTemplate[] = [
  {
    id: "tpl-p1",
    name: "普惠授信申报及审查审批意见表",
    kind: "预置",
    version: "2025 新版",
    fieldTotal: 460,
    recentUsed: 38,
  },
  {
    id: "tpl-c1",
    name: "对公授信申报书",
    kind: "预置",
    version: "2024.12",
    fieldTotal: 612,
    recentUsed: 21,
  },
  {
    id: "tpl-m1",
    name: "小微续贷审批意见书",
    kind: "预置",
    version: "2025.03",
    fieldTotal: 218,
    recentUsed: 14,
  },
];

const MATERIALS: ReportMaterial[] = [
  {
    id: "m-1",
    name: "工商营业执照副本.pdf",
    kind: "pdf",
    pages: 1,
    bytes: "0.8 MB",
    parsed: true,
    parseNote: "OCR 完成 · 工商 11 字段全部提取",
    linkedSections: ["§一.1", "§一.2"],
  },
  {
    id: "m-2",
    name: "最新财务报表 2025.xlsx",
    kind: "xlsx",
    pages: 4,
    bytes: "86 KB",
    parsed: true,
    parseNote: "资产负债 + 利润 + 现金流三表对齐",
    linkedSections: ["§三.1", "§三.2", "§三.3"],
  },
  {
    id: "m-3",
    name: "经营流水近 12 月.pdf",
    kind: "pdf",
    pages: 24,
    bytes: "3.2 MB",
    parsed: true,
    parseNote: "月均流水 ¥412 万 · 环比稳定",
    linkedSections: ["§二.2", "§二.3"],
  },
  {
    id: "m-4",
    name: "主要合同与订单.pdf",
    kind: "pdf",
    pages: 11,
    bytes: "2.1 MB",
    parsed: true,
    parseNote: "5 份采购合同 · 金额合计 ¥1,840 万",
    linkedSections: ["§二.1", "§四.3"],
  },
  {
    id: "m-5",
    name: "厂房抵押评估报告.pdf",
    kind: "pdf",
    pages: 9,
    bytes: "1.5 MB",
    parsed: true,
    parseNote: "评估价 ¥2,600 万 · 评估日 2026-03-28",
    linkedSections: ["§五.1", "§五.2"],
  },
  {
    id: "m-6",
    name: "股权结构图.png",
    kind: "img",
    pages: 1,
    bytes: "420 KB",
    parsed: true,
    parseNote: "法人张某持股 62% · 无外部投资人",
    linkedSections: ["§一.2"],
  },
  {
    id: "m-7",
    name: "授信审批历史档案.docx",
    kind: "docx",
    pages: 6,
    bytes: "180 KB",
    parsed: true,
    parseNote: "历史 3 笔授信均按时结清",
    linkedSections: ["§四.4"],
  },
  {
    id: "m-8",
    name: "税务完税凭证.pdf",
    kind: "pdf",
    pages: 3,
    bytes: "720 KB",
    parsed: false,
    parseNote: "扫描件模糊 · 待手工确认 2 项金额",
    linkedSections: ["§三.5"],
  },
];

const TIMELINE: TimelineEvent[] = [
  {
    id: "ev-1",
    at: "32 分钟前",
    kind: "template.select",
    priority: "done",
    label: "选定模板",
    detail: "普惠授信申报及审查审批意见表 · 2025 新版",
  },
  {
    id: "ev-2",
    at: "30 分钟前",
    kind: "material.upload",
    priority: "done",
    label: "上传 8 份材料",
    detail: "工商 / 财务 / 流水 / 合同 / 抵押 / 股权 / 历史 / 税务",
  },
  {
    id: "ev-3",
    at: "28 分钟前",
    kind: "material.parsed",
    priority: "done",
    label: "7 份已解析 · 1 份待处理",
    detail: "税务完税凭证扫描件模糊",
  },
  {
    id: "ev-4",
    at: "24 分钟前",
    kind: "ai.question",
    priority: "p1",
    label: "AI 提问 · §四.3 授信用途",
    detail: "未在材料中找到采购设备对应合同段",
  },
  {
    id: "ev-5",
    at: "22 分钟前",
    kind: "user.reply",
    priority: "done",
    label: "客户经理回复",
    detail: "定向采购 2 台包装线 · 补充合同编号 HT-2026-044",
  },
  {
    id: "ev-6",
    at: "18 分钟前",
    kind: "section.done",
    priority: "done",
    label: "§一 基本情况生成完成",
    detail: "82 / 82 · 证据率 98%",
  },
  {
    id: "ev-7",
    at: "14 分钟前",
    kind: "section.done",
    priority: "done",
    label: "§二 经营情况生成完成",
    detail: "88 / 96 · 证据率 94% · 未填 6",
  },
  {
    id: "ev-8",
    at: "9 分钟前",
    kind: "section.done",
    priority: "p1",
    label: "§三 财务情况生成完成",
    detail: "112 / 118 · 需复核流动比率",
  },
  {
    id: "ev-9",
    at: "6 分钟前",
    kind: "section.done",
    priority: "done",
    label: "§五 担保情况生成完成",
    detail: "40 / 42 · 证据率 97%",
  },
  {
    id: "ev-10",
    at: "3 分钟前",
    kind: "qc.run",
    priority: "p0",
    label: "QC 终审 · 2 阻断",
    detail: "数字不一致 · 证据缺失各 1",
  },
  {
    id: "ev-11",
    at: "刚刚",
    kind: "ai.question",
    priority: "p0",
    label: "AI 请求确认 · §三.2 流动比率",
    detail: "LLM 1.67 vs analyzer 1.71 · 建议采用 analyzer",
  },
];

const CONVERSATION: ConversationMessage[] = [
  {
    id: "msg-1",
    at: "30 分钟前",
    kind: "system-event",
    content:
      "已选用模板《普惠授信申报及审查审批意见表 · 2025 新版》· 共 460 项字段待填",
  },
  {
    id: "msg-2",
    at: "28 分钟前",
    kind: "system-event",
    content: "已解析 7 份材料 · 1 份待手工确认（税务完税凭证扫描模糊）",
  },
  {
    id: "msg-3",
    at: "24 分钟前",
    kind: "ai-question",
    content:
      "§四.3 授信用途 — 材料中未找到对应合同段，请问本次 560 万的具体用途？",
    fieldRef: "§四.3 授信用途",
  },
  {
    id: "msg-4",
    at: "22 分钟前",
    kind: "user-reply",
    content:
      "定向采购 2 台自动包装线（单价约 260 万），合同号 HT-2026-044，已上传到材料区。",
  },
  {
    id: "msg-5",
    at: "18 分钟前",
    kind: "ai-response",
    content:
      "已据此回填 §四.3 授信用途 · 采购设备明细已引用合同 HT-2026-044 第 3 条",
    fieldRef: "§四.3 授信用途",
    sectionDiff: {
      sectionAnchor: "§四.3",
      after:
        "本次授信额度 ¥560 万元，用于采购 2 台自动包装线（合同 HT-2026-044，单价 ¥260 万）…",
    },
  },
  {
    id: "msg-6",
    at: "9 分钟前",
    kind: "ai-thinking",
    content: "正在计算财务比率 · Evidence-First 证据链构建中",
    thinking: {
      steps: [
        {
          label: "从 最新财务报表 2025.xlsx 提取",
          evidences: ["流动资产 = 2,135 万", "流动负债 = 1,248 万"],
        },
        {
          label: "financial_analyzer 确定性计算",
          evidences: ["流动比率 = 2,135 / 1,248 = 1.71"],
        },
        {
          label: "LLM 初稿交叉校验",
          evidences: ["LLM 给出 1.67 · 偏差 2.4%"],
        },
      ],
    },
  },
  {
    id: "msg-7",
    at: "3 分钟前",
    kind: "ai-question",
    content:
      "§三.2 流动比率存在数字不一致：LLM 写 1.67，确定性层算得 1.71（偏差 2.4%）。建议以 analyzer 结果 1.71 为准。是否覆盖？",
    fieldRef: "§三.2 流动比率",
  },
  {
    id: "msg-8",
    at: "2 分钟前",
    kind: "user-command",
    content: "/QC 重跑一遍，我看一下完整阻断清单",
  },
  {
    id: "msg-9",
    at: "2 分钟前",
    kind: "system-event",
    content: "QC 终审完成 · 2 阻断 / 2 警告 / 1 提示",
  },
  {
    id: "msg-10",
    at: "刚刚",
    kind: "ai-question",
    content:
      "§二.1 主营业务 — 残留占位符 {{主营业务}} 未被替换。从营业执照「经营范围」抽取改写，还是手工填？",
    fieldRef: "§二.1 主营业务",
  },
];

const PREVIEW: PreviewSection[] = [
  {
    id: "s-1",
    anchor: "§一",
    title: "基本情况",
    filled: 82,
    total: 82,
    marked: 0,
    evidenceRate: 0.98,
    status: "ok",
    content:
      "福建惠民商贸有限公司（以下简称本企业）成立于 2014 年 3 月，统一社会信用代码 91350102MA****XX，注册资本 800 万元，法定代表人张某，股权结构为张某持股 62%、配偶李某持股 38%，无外部机构投资人。注册地福建省福州市鼓楼区。",
    fields: [
      { id: "f-1-1", label: "企业名称", state: "filled", value: "福建惠民商贸有限公司", source: "工商营业执照副本" },
      { id: "f-1-2", label: "统一社会信用代码", state: "filled", value: "91350102MA****XX", source: "工商营业执照副本" },
      { id: "f-1-3", label: "注册资本", state: "filled", value: "800 万元", source: "工商营业执照副本" },
      { id: "f-1-4", label: "成立日期", state: "filled", value: "2014-03-15", source: "工商营业执照副本" },
      { id: "f-1-5", label: "法定代表人", state: "filled", value: "张某", source: "工商营业执照副本" },
    ],
  },
  {
    id: "s-2",
    anchor: "§二",
    title: "经营情况",
    filled: 88,
    total: 96,
    marked: 6,
    evidenceRate: 0.94,
    status: "ok",
    content:
      "本企业主要经营食品、日用品批发与零售，下辖 3 个仓储点，覆盖福州、泉州、厦门三地。2025 年 1-12 月账面营业收入 5,210 万元，月均经营流水约 ¥412 万，环比稳定。主要客户集中在本地连锁超市与便利店渠道。",
    fields: [
      { id: "f-2-1", label: "主营业务", state: "uncertain", value: "{{主营业务}}", qc: { level: "warn", detail: "残留占位符未被替换 · 可从营业执照经营范围抽取生成" }, source: "—" },
      { id: "f-2-2", label: "经营模式", state: "filled", value: "批发 + 零售 双渠道", source: "授信审批历史档案" },
      { id: "f-2-3", label: "月均流水", state: "filled", value: "¥412 万", source: "经营流水近 12 月" },
      { id: "f-2-4", label: "主要客户", state: "filled", value: "本地连锁超市 / 便利店", source: "授信审批历史档案" },
      { id: "f-2-5", label: "2025 营业收入", state: "filled", value: "5,210 万元", source: "最新财务报表 2025" },
    ],
  },
  {
    id: "s-3",
    anchor: "§三",
    title: "财务情况",
    filled: 112,
    total: 118,
    marked: 3,
    evidenceRate: 0.96,
    status: "needs-review",
    content:
      "本企业 2025 年末资产总额 4,820 万元，负债总额 2,985 万元，所有者权益 1,835 万元，资产负债率 61.9%。流动资产 2,135 万元，流动负债 1,248 万元，流动比率 1.71（确定性层计算值，LLM 初稿误写 1.67，已按证据优先协议覆盖）。",
    fields: [
      { id: "f-3-1", label: "资产总额", state: "filled", value: "4,820 万元", source: "最新财务报表 2025" },
      { id: "f-3-2", label: "流动比率", state: "filled", value: "1.71", qc: { level: "block", detail: "LLM 写 1.67，确定性层 analyzer 算得 1.71（差 2.4%）· 建议 analyzer 覆盖" }, source: "financial_analyzer" },
      { id: "f-3-3", label: "资产负债率", state: "filled", value: "61.9%", source: "最新财务报表 2025" },
      { id: "f-3-4", label: "净利润率", state: "filled", value: "8.4%", source: "最新财务报表 2025" },
      { id: "f-3-5", label: "税务信用等级", state: "unfilled", value: "—", qc: { level: "info", detail: "税务完税凭证扫描模糊，待手工确认" }, source: "税务完税凭证（待解析）" },
    ],
  },
  {
    id: "s-4",
    anchor: "§四",
    title: "授信情况",
    filled: 58,
    total: 64,
    marked: 4,
    evidenceRate: 0.91,
    status: "needs-review",
    content:
      "本次拟授信 560 万元（续授信），期限 12 个月，利率 LPR+150BP，用于采购 2 台自动包装线（合同 HT-2026-044，单价 ¥260 万）。历史累计授信 3 笔均按时结清，无逾期记录。",
    fields: [
      { id: "f-4-1", label: "授信金额", state: "filled", value: "560 万元", source: "授信申报记录" },
      { id: "f-4-2", label: "期限", state: "filled", value: "12 个月", source: "授信申报记录" },
      { id: "f-4-3", label: "利率", state: "filled", value: "LPR+150BP", source: "授信申报记录" },
      { id: "f-4-4", label: "授信用途", state: "filled", value: "采购自动包装线 2 台", qc: { level: "block", detail: "LLM 初稿未指向合同，已据客户经理补充回填 HT-2026-044 引用" }, source: "主要合同与订单 / 客户经理补充" },
      { id: "f-4-5", label: "历史授信", state: "filled", value: "3 笔均按时结清", source: "授信审批历史档案" },
    ],
  },
  {
    id: "s-5",
    anchor: "§五",
    title: "担保情况",
    filled: 40,
    total: 42,
    marked: 1,
    evidenceRate: 0.97,
    status: "ok",
    content:
      "以本企业位于福州市晋安区的 1 处厂房作为抵押物（建筑面积 2,850 ㎡），评估价值 2,600 万元（评估日 2026-03-28，距今 24 天，未超 90 天，符合规定）。抵押率 21.5%。",
    fields: [
      { id: "f-5-1", label: "抵押物", state: "filled", value: "福州市晋安区厂房 · 2,850 ㎡", source: "厂房抵押评估报告" },
      { id: "f-5-2", label: "评估价值", state: "filled", value: "2,600 万元", source: "厂房抵押评估报告" },
      { id: "f-5-3", label: "评估日", state: "filled", value: "2026-03-28", qc: { level: "info", detail: "距今 24 天 · 未超 90 天 · 符合" }, source: "厂房抵押评估报告" },
      { id: "f-5-4", label: "抵押率", state: "filled", value: "21.5%", source: "financial_analyzer" },
    ],
  },
  {
    id: "s-6",
    anchor: "§六",
    title: "审查意见",
    filled: 52,
    total: 58,
    marked: 4,
    evidenceRate: 0.89,
    status: "running",
    content:
      "综合本企业经营稳定性、历史授信履约情况与本次抵押充足性，整体风险在可承受范围内。建议按申报金额批准授信 560 万元。",
    fields: [
      { id: "f-6-1", label: "风险评级", state: "filled", value: "BB+", source: "quality_scorer" },
      { id: "f-6-2", label: "审查结论", state: "filled", value: "整体风险在可承受范围内", qc: { level: "warn", detail: "LLM 原写 风险可控 · 合规术语库要求改用 整体风险在可承受范围内 · 已 rewrite" }, source: "合规术语库" },
      { id: "f-6-3", label: "审批建议", state: "filled", value: "建议批准 560 万元授信 · 期限 12 个月", source: "quality_scorer" },
      { id: "f-6-4", label: "附加条件", state: "unfilled", value: "—", qc: { level: "info", detail: "待审贷会讨论" }, source: "—" },
    ],
  },
];

const RECENT: RecentSession[] = [
  { id: "rs-001", clientName: "福建惠民商贸 · 续授信", updated: "刚刚（当前）", progress: 0.86, stage: "QC 终审中" },
  { id: "rs-002", clientName: "宁海汇通精工 · 首贷", updated: "3 分钟前", progress: 0.72, stage: "段落生成" },
  { id: "rs-003", clientName: "苏州星河医药 · 增信", updated: "9 分钟前", progress: 0.58, stage: "字段抽取" },
  { id: "rs-004", clientName: "东阳塑橡 · 周转续签", updated: "18 分钟前", progress: 0.41, stage: "材料解析" },
  { id: "rs-005", clientName: "瀚蓝智控 · 新增额度", updated: "1 小时前", progress: 1.0, stage: "已完成" },
];

/* Phase A worker-A4 V2 (codex DISAGREE issue 1 fix · 2026-04-29):
   liveToReportSession · 把 v16 done envelope 标准化成 ReportSession shape ·
   让 5 panel (Hero / Material / Timeline / Preview / FieldChip) 单点从 sessionData 派生 ·
   不再静态 REPORT_SESSION 占主源 (避免 demo/live 切换无视觉变化).

   Backend 暂不暴露 materials / fields / timeline 真原型 · 这些字段先保留 mock 形态
   (REPORT_SESSION fallback) · 真原型由 v16_runner 后续 stage 扩展契约 (Phase B). */

type V16DoneShape = {
  session_id?: string;
  report_id?: string;
  sections?: { id: string; title: string; content?: string; status?: string; word_count?: number }[];
  profile?: Record<string, unknown>;
  qc?: { passed?: boolean; score?: number; fatal_fail?: boolean; halluc_count?: number; warn_count?: number };
  stats?: Record<string, unknown>;
  pending_questions?: { id: string; label?: string }[];
};

const _ANCHORS = ["§一", "§二", "§三", "§四", "§五", "§六"];

export function liveToReportSession(live: V16DoneShape | null | undefined): ReportSession | null {
  if (!live) return null;
  const profile = live.profile ?? {};
  const company = (profile.company_name as string) || `Live · ${(live.session_id ?? "").slice(0, 8) || "—"}`;
  const stats = live.stats ?? {};
  const qc = live.qc ?? {};
  const sections = live.sections ?? [];
  const previewSections: PreviewSection[] = sections.map((s, i) => {
    const anchor = _ANCHORS[i] ?? `§${i + 1}`;
    const cleanTitle = (s.title || s.id || `章节 ${i + 1}`).replace(/^[一二三四五六七八九十]+、/, "");
    const wc = s.word_count ?? (s.content ?? "").length;
    let status: PreviewSection["status"] = "pending";
    if (s.status === "done") status = "ok";
    else if (s.status === "writing" || s.status === "running") status = "running";
    else if (s.status === "qc_blocked") status = "needs-review";
    return {
      id: s.id,
      anchor,
      title: cleanTitle,
      filled: wc,
      total: Math.max(wc, 1),
      marked: 0,
      evidenceRate: qc.passed ? 0.9 : 0.6,
      status,
      content: s.content || "",
      fields: [], // backend 暂不暴露 field-level · Phase B 扩展契约
    };
  });

  const totalFields = (stats.total_fields as number) ?? sections.reduce((a, b) => a + (b.word_count ?? 0), 0);
  const autoFilled = (stats.auto_filled as number) ?? totalFields;
  const unfilled = (stats.unfilled as number) ?? Math.max(totalFields - autoFilled, 0);
  const block = qc.fatal_fail ? 1 : 0;
  const warn = (qc.warn_count as number) ?? 0;
  const info = 0;

  return {
    id: live.session_id ?? live.report_id ?? `live-${Date.now()}`,
    clientName: company,
    amount: ((profile.revenue_yuan_2024 as string) || (profile.registered_capital_yuan as string) || "(待提取)") as string,
    stage: qc.passed ? "已 QC 通过" : qc.fatal_fail ? "QC 阻断 · 待补材料" : `QC ${qc.score ?? "-"}`,
    updated: "刚刚",
    template: TEMPLATES[0],
    availableTemplates: TEMPLATES,
    materials: MATERIALS, // backend 暂不提供 · keep mock fallback (Phase B 扩展)
    timeline: TIMELINE,   // backend 暂不提供 · keep mock fallback (Phase B 扩展)
    conversation: CONVERSATION,
    preview: previewSections.length > 0 ? previewSections : PREVIEW,
    coverage: { filled: autoFilled, total: Math.max(totalFields, 1), marked: unfilled },
    qcCounts: { block, warn, info },
    recentSessions: RECENT,
  };
}

export const REPORT_SESSION: ReportSession = {
  id: "rs-001",
  clientName: "福建惠民商贸 · 续授信",
  amount: "¥560 万",
  stage: "QC 终审中",
  updated: "刚刚",
  template: TEMPLATES[0],
  availableTemplates: TEMPLATES,
  materials: MATERIALS,
  timeline: TIMELINE,
  conversation: CONVERSATION,
  preview: PREVIEW,
  coverage: { filled: 432, total: 460, marked: 18 },
  qcCounts: { block: 2, warn: 2, info: 1 },
  recentSessions: RECENT,
};
