/**
 * Desk left drawer · mock fixture (Stage 2)
 * Stage 3+ 切到 GET /api/desk/{customers,in-flight,recent}
 */

export type DeskRow = {
  ic: string;
  icClass?: "dot-p0" | "dot-warn" | "dot-live" | "dot-chat";
  nm: string;
  sub: string;
  ts: string;
  href: string;
};

export type DeskSection = {
  title: string;
  meta: string;
  rows: DeskRow[];
  more?: { label: string; count?: string };
};

export const DESK_SECTIONS: DeskSection[] = [
  {
    title: "我的客户",
    meta: "BOOK · 03",
    rows: [
      { ic: "P0", icClass: "dot-p0",   nm: "宁海汇通科技",   sub: "授信案 · 待终审",       ts: "08:41", href: "/today" },
      { ic: "B",                        nm: "海创智能装备",   sub: "预审 · 材料 7/9",       ts: "昨日",  href: "/today" },
      { ic: "△", icClass: "dot-warn",  nm: "星河医药",       sub: "预警 · 黄色",           ts: "04/15", href: "/warroom" },
    ],
    more: { label: "查看全部客户", count: "(28)" },
  },
  {
    title: "进行中",
    meta: "IN FLIGHT · 04",
    rows: [
      { ic: "报", icClass: "dot-live", nm: "报告助手 · 宁海汇通", sub: "生成中 · 78% · ETA 09:12", ts: "活",    href: "/archive/report" },
      { ic: "预", icClass: "dot-live", nm: "预警助手 · 星河医药", sub: "运行 2:34 · 42%",          ts: "活",    href: "/archive/alert" },
      { ic: "急", icClass: "dot-p0",   nm: "合规助手 · §214 筛查", sub: "4 户命中 · 意见待出",      ts: "12:00", href: "/warroom" },
      { ic: "风",                       nm: "风控助手 · 小微 DSL",   sub: "等样本投入",               ts: "—",     href: "/archive/riskctrl" },
    ],
  },
  {
    title: "最近",
    meta: "RECENT",
    rows: [
      { ic: "@", icClass: "dot-chat", nm: "@林楠 · 审贷员",     sub: "下周一前给额度建议",  ts: "2h",    href: "/dispatch" },
      { ic: "#", icClass: "dot-chat", nm: "#华东线晨会",         sub: "5 位参会 · 09:30",     ts: "07:50", href: "/dispatch" },
      { ic: "§",                       nm: "NMPA §214 政策",      sub: "四月新政 · 已解析",   ts: "04/12", href: "/archive/compliance" },
    ],
  },
];

export const DESK_QUICK_CREATE = [
  { label: "新对话",     href: "/dispatch" },
  { label: "新任务",     href: "/warroom" },
  { label: "起草报告",   href: "/archive/report" },
  { label: "开始获客",   href: "/archive/channel" },
];
