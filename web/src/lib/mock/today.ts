/**
 * Today view · mock fixture (Stage 2)
 * Stage 3+ 切到 GET /api/today/*
 */

export type TodaySummary = {
  pipeline: { value: string; sub: string };
  queue:    { value: string; sub: string };
  risk:     { value: string; sub: string };
};

export const TODAY_SUMMARY: TodaySummary = {
  pipeline: { value: "12", sub: "在贷案 · 在审" },
  queue:    { value: "4",  sub: "今日待办 · P0 1" },
  risk:     { value: "2",  sub: "黄/红 客户 · 待复核" },
};

export type FeedItem = {
  id: string;
  kind: "msg" | "task" | "report" | "policy";
  who: string;
  preview: string;
  ts: string;
  href: string;
};

export const TODAY_FEED: FeedItem[] = [
  { id: "f1", kind: "msg",    who: "@林楠 · 审贷员", preview: "下周一前给出宁海汇通的额度建议", ts: "2h",    href: "/dispatch" },
  { id: "f2", kind: "msg",    who: "#华东线晨会",     preview: "5 位参会 · 今日 09:30",          ts: "07:50", href: "/dispatch" },
  { id: "f3", kind: "report", who: "报告助手",        preview: "宁海汇通报告生成中 · 78%",       ts: "08:32", href: "/archive/report" },
  { id: "f4", kind: "policy", who: "NMPA",            preview: "§214 政策已解析 · 4 户命中",     ts: "04/12", href: "/archive/compliance" },
  { id: "f5", kind: "task",   who: "你",              preview: "海创智能装备 · 材料补全 7/9",    ts: "昨日",  href: "/warroom" },
];

export type InFlightItem = {
  id: string;
  agent: "report" | "alert" | "compliance" | "riskctrl" | "channel" | "credit";
  title: string;
  status: string;
  progress?: number;
  href: string;
};

export const TODAY_IN_FLIGHT: InFlightItem[] = [
  { id: "i1", agent: "report",     title: "报告助手 · 宁海汇通",   status: "生成中 · ETA 09:12", progress: 78, href: "/archive/report" },
  { id: "i2", agent: "alert",      title: "预警助手 · 星河医药",   status: "运行 2:34",          progress: 42, href: "/archive/alert" },
  { id: "i3", agent: "compliance", title: "合规助手 · §214 筛查",  status: "4 户命中 · 待出意见",                href: "/warroom" },
];

export type TaskItem = {
  id: string;
  title: string;
  prio: "P0" | "P1" | "P2";
  due: string;
  href: string;
};

export const TODAY_TASKS: TaskItem[] = [
  { id: "t1", title: "宁海汇通 · 终审会前补 3 项材料", prio: "P0", due: "今日 14:00", href: "/warroom" },
  { id: "t2", title: "海创智能装备 · 预审材料 7/9",    prio: "P1", due: "本周内",     href: "/warroom" },
  { id: "t3", title: "星河医药 · 黄色预警复核",        prio: "P1", due: "明日",       href: "/warroom" },
];

// A-017: Today .card.warm.sheet-card (agent · 正在跑) — shell.html:2047-2131 spec
export type RunningSheet = {
  id: string;
  tag: string;     // e.g. "报告助手 · Agent 6"
  state: string;   // e.g. "running · 78%"
  title: string;   // 企业 · 阶段
  sub: string;     // 下一步说明
  eta: string;     // "ETA 09:12"
  pct: number;     // 0-100 → --p CSS var
};

export type IdleSheet = {
  id: string;
  tag: string;     // "授信助手 · Agent 3"
  title: string;   // 企业 · 等待原因
  sub: string;     // 背景说明
};

export const TODAY_RUNNING_SHEETS: RunningSheet[] = [
  { id: "r1", tag: "报告助手 · Agent 6", state: "running · 78%", title: "宁海汇通 · 授信报告生成中", sub: "材料解析完成，进入财务段", eta: "ETA 09:12", pct: 78 },
  { id: "r2", tag: "预警助手 · Agent 4", state: "running · 42%", title: "星河医药 · 舆情与征信扫描中", sub: "外路第 3 轮 · 内路队列 12", eta: "ETA 09:48", pct: 42 },
  { id: "r3", tag: "合规助手 · Agent 5", state: "running · 56%", title: "§214 新政 · 业务矩阵筛查", sub: "已命中 4 户 · 意见待出", eta: "ETA 10:30", pct: 56 },
];

export const TODAY_IDLE_SHEETS: IdleSheet[] = [
  { id: "i1", tag: "授信助手 · Agent 3", title: "河东纺织 · 待 Agent 6 交付", sub: "等报告产出，预计午后启动" },
  { id: "i2", tag: "获客助手 · Agent 1", title: "小微 · 广东建材画像未输入", sub: "需客户经理起草关键词" },
  { id: "i3", tag: "风控助手 · Agent 2", title: "小微 DSL · 待样本投入", sub: "CSV 格式待确认" },
];
