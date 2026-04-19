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

// Task E: shape 对齐 mockup L2823-2942 (rm-assistant-final-2026-04-19)
// - av / avVariant: 头像字符 + 变体 (sys/warn) 对应 .feed-av.sys / .feed-av.warn
// - urgent / unread: 对应 .feed-item.urgent / .feed-item.unread class modifier
// - org: feed-who 内的次级标签 (不带前导 · , 渲染时加)
// - time: mockup 原样 (含"昨 18:14" "前天" "04-15" 等非规整字符串)
export type FeedItem = {
  id: string;
  av: string;
  avVariant?: "sys" | "warn";
  who: string;
  org: string;
  msg: string;
  time: string;
  urgent?: boolean;
  unread?: boolean;
};

export const TODAY_FEED: FeedItem[] = [
  { id: "fd-01", av: "林",  who: "林楠",       org: "宁海汇通",   msg: "下周一前给一版额度与期限建议，周会要拍板。",             time: "08:42",    urgent: true,  unread: true },
  { id: "fd-02", av: "王",  avVariant: "warn", who: "王审贷",     org: "QC 终审",    msg: "财务段两处数字不一致，请 12:00 前给修订稿。",             time: "08:31",    urgent: true,  unread: true },
  { id: "fd-03", av: "SYS", avVariant: "sys",  who: "合规 agent", org: "政策扫描",   msg: "3 号文发布，命中在贷客户 14 家。",                         time: "08:05",    urgent: true,  unread: true },
  { id: "fd-04", av: "陈",  who: "陈诺",       org: "风控",       msg: "DSL v3.1 回测 KS 0.41，已推 staging 等复核。",             time: "07:58",                   unread: true },
  { id: "fd-05", av: "SYS", avVariant: "sys",  who: "报告 agent", org: "交付",       msg: "义华精工授信报告已生成，QC 9.2 / 10，待签发。",             time: "07:44",                   unread: true },
  { id: "fd-06", av: "赵",  who: "赵蒙",       org: "客户经理",   msg: "锦程物流想把额度从 800 万提到 1500 万，补一下画像。",       time: "07:22",                   unread: true },
  { id: "fd-07", av: "SYS", avVariant: "sys",  who: "预警 agent", org: "贷中",       msg: "扫出 2 家黄牌：东海建材、星辰电子。",                       time: "06:50",                   unread: true },
  { id: "fd-08", av: "孙",  who: "孙璐",       org: "合规官",     msg: "5 号文对票据质押的新定义跟业务矩阵第 7 条冲突。",           time: "昨 18:14",                 unread: true },
  { id: "fd-09", av: "周",  who: "周迎",       org: "审贷",       msg: "第二家的原料依赖度给分偏高，能回一下你的理由吗？",           time: "昨 17:30",                 unread: true },
  { id: "fd-10", av: "SYS", avVariant: "sys",  who: "获客 agent", org: "早报",       msg: "匹配 12 家 look-alike，4 家命中 ≥ 3 类信号。",             time: "昨 16:02" },
  { id: "fd-11", av: "吴",  who: "吴嘉",       org: "宁海汇通",   msg: "三月营业数据更新版发你了，毛利好看一点。",                   time: "昨 14:20" },
  { id: "fd-12", av: "郑",  who: "郑文",       org: "风险经理",   msg: "季度风险组会纪要已发群里，记得看一眼。",                     time: "昨 11:45" },
  { id: "fd-13", av: "SYS", avVariant: "sys",  who: "平台",       org: "账号",       msg: "RBAC 权限本周刷新为\"客户经理 + 审贷代理\"。",             time: "前天" },
  { id: "fd-14", av: "冯",  who: "冯慎",       org: "支行长",     msg: "下周北部湾演示，把 Agent3 放第二个讲。",                     time: "前天" },
  { id: "fd-15", av: "SYS", avVariant: "sys",  who: "feedback",   org: "数据飞轮",   msg: "审贷员修改已沉淀 31 条，建议下周更新 few-shot。",           time: "04-15" },
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
