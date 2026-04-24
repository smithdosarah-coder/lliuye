/**
 * Agent Report (报告 · A06) — Material parse + field fill + QC mock fixtures.
 * Feeds the /archive/report workspace (material parse state + field progress + QC result).
 */

export type MaterialItem = {
  id: string;
  name: string;
  kind: "pdf" | "docx" | "xlsx" | "img";
  pages: number;
  bytes: string;
  parsed: boolean;
  parseNote: string;
};

export type ReportSection = {
  id: string;
  title: string;
  total: number;
  filled: number;
  marked: number; // 标注"未能自动填写"
  evidenceRate: number; // 0..1
  status: "pending" | "running" | "ok" | "needs-review";
};

export type QcFinding = {
  id: string;
  level: "block" | "warn" | "info";
  category: "placeholder" | "evidence-missing" | "number-mismatch" | "term-violation";
  field: string;
  detail: string;
  fix: string;
};

export type ReportDraft = {
  id: string;
  name: string;
  amount: string;
  progress: number;
  stage: string;
  updated: string;
};

export const REPORT_STATS = {
  weeklyProcessed: "82",
  successRate: "93.5%",
  avgDuration: "11.4 分钟",
} as const;

export const REPORT_DRAFTS: ReportDraft[] = [
  { id: "r-001", name: "福建惠民商贸 · 续授信", amount: "¥560 万", progress: 0.86, stage: "QC 终审中", updated: "刚刚" },
  { id: "r-002", name: "宁海汇通精工 · 首贷", amount: "¥1,200 万", progress: 0.72, stage: "段落生成", updated: "3 分钟前" },
  { id: "r-003", name: "苏州星河医药 · 增信", amount: "¥800 万", progress: 0.58, stage: "字段抽取", updated: "9 分钟前" },
  { id: "r-004", name: "东阳塑橡 · 周转续签", amount: "¥2,400 万", progress: 0.41, stage: "材料解析", updated: "18 分钟前" },
  { id: "r-005", name: "瀚蓝智控 · 新增额度", amount: "¥1,500 万", progress: 1.0, stage: "已完成", updated: "1 小时前" },
];

export const REPORT_MATERIALS: MaterialItem[] = [
  { id: "m-1", name: "工商营业执照副本.pdf", kind: "pdf", pages: 1, bytes: "0.8 MB", parsed: true, parseNote: "OCR 完成,工商 11 字段全部提取" },
  { id: "m-2", name: "最新财务报表 2025.xlsx", kind: "xlsx", pages: 4, bytes: "86 KB", parsed: true, parseNote: "资产负债 + 利润 + 现金流三表对齐" },
  { id: "m-3", name: "经营流水近 12 月.pdf", kind: "pdf", pages: 24, bytes: "3.2 MB", parsed: true, parseNote: "月均流水 ¥412 万,环比稳定" },
  { id: "m-4", name: "主要合同与订单.pdf", kind: "pdf", pages: 11, bytes: "2.1 MB", parsed: true, parseNote: "5 份采购合同,金额合计 ¥1,840 万" },
  { id: "m-5", name: "厂房抵押评估报告.pdf", kind: "pdf", pages: 9, bytes: "1.5 MB", parsed: true, parseNote: "评估价 ¥2,600 万,评估日 2026-03-28" },
  { id: "m-6", name: "股权结构图.png", kind: "img", pages: 1, bytes: "420 KB", parsed: true, parseNote: "法人张某持股 62%,无外部投资人" },
  { id: "m-7", name: "授信审批历史档案.docx", kind: "docx", pages: 6, bytes: "180 KB", parsed: true, parseNote: "历史 3 笔授信均按时结清" },
  { id: "m-8", name: "税务完税凭证.pdf", kind: "pdf", pages: 3, bytes: "720 KB", parsed: false, parseNote: "扫描件模糊 · 待手工确认 2 项金额" },
];

export const REPORT_SECTIONS: ReportSection[] = [
  { id: "s-1", title: "一、基本情况", total: 82, filled: 82, marked: 0, evidenceRate: 0.98, status: "ok" },
  { id: "s-2", title: "二、经营情况", total: 96, filled: 88, marked: 6, evidenceRate: 0.94, status: "ok" },
  { id: "s-3", title: "三、财务情况", total: 118, filled: 112, marked: 3, evidenceRate: 0.96, status: "needs-review" },
  { id: "s-4", title: "四、授信情况", total: 64, filled: 58, marked: 4, evidenceRate: 0.91, status: "needs-review" },
  { id: "s-5", title: "五、担保情况", total: 42, filled: 40, marked: 1, evidenceRate: 0.97, status: "ok" },
  { id: "s-6", title: "六、审查意见", total: 58, filled: 52, marked: 4, evidenceRate: 0.89, status: "running" },
];

export const REPORT_QC_FINDINGS: QcFinding[] = [
  {
    id: "q-1",
    level: "block",
    category: "number-mismatch",
    field: "§三.2 流动比率",
    detail: "LLM 写 1.67,确定性层算得 1.71(差 2.4%)",
    fix: "用 financial_analyzer 结果覆盖,证据指向 §流动资产 / §流动负债",
  },
  {
    id: "q-2",
    level: "block",
    category: "evidence-missing",
    field: "§四.3 授信用途",
    detail: "描述「用于采购设备」,但材料中未找到对应合同段",
    fix: "标注「未能自动填写」,转人工补件",
  },
  {
    id: "q-3",
    level: "warn",
    category: "placeholder",
    field: "§二.1 主营业务",
    detail: "残留占位 {{主营业务}} 未被替换",
    fix: "从营业执照经营范围抽取 → 生成模板",
  },
  {
    id: "q-4",
    level: "warn",
    category: "term-violation",
    field: "§六.2 审查结论",
    detail: "使用「风险可控」一词,合规术语库要求「整体风险在可承受范围内」",
    fix: "应用合规术语替换规则 · 已加入 rewrite 队列",
  },
  {
    id: "q-5",
    level: "info",
    category: "evidence-missing",
    field: "§五.1 抵押物描述",
    detail: "抵押评估日 2026-03-28,距今 24 天(未超 90 天,符合)",
    fix: "无需处理,仅提示",
  },
];
