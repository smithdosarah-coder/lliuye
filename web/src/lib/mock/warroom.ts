/**
 * Warroom view · mock fixture (Task K2 裁回 mockup L3354-3478)
 *
 * Shape:
 * - TextSeg[]: body 富文本段 (em 斜体内联)
 * - MetaSeg:  category/status 行, 支持 `{cn: "..."}` wrap 或裸文字
 * - KCard:    单张卡片 (.kcard) 全部字段
 * - KColumn:  4 列 (.kcol) 元数据, done=true 附 .kcol.done 深色
 *
 * K2 修正 (Task I 过度扩展 → 回到 mockup 字面)
 * - 14 卡总 (4/5/2/3) · 删 37 张 onboarding 扩展卡
 * - 6 pill variant (P0/P1/P2/urg/wait/cn) · 删 P3/compli/law/risk 4 个未用变体
 * - 列标签与 mockup L3370/L3400/L3436/L3454 对齐: 待处理/进行中/冒出/已归档
 */

export type TextSeg = { text: string; em?: boolean };

export type MetaSeg = string | { cn: string };

export type PriorityPill =
  | "P0"
  | "P1"
  | "P2"
  | "urg"
  | "wait"
  | "cn";

export type ColumnKey = "todo" | "wip" | "new" | "done";

export type KCard = {
  id: string;
  column: ColumnKey;
  title: string;
  pill: { label: string; variant: PriorityPill };
  meta: MetaSeg[];
  body: TextSeg[];
  who: { av: string; name: string };
  go: "打开" | "查看";
};

export type KColumn = {
  key: ColumnKey;
  label: string;
  count: string;
  done?: boolean;
};

// 列头 count 对齐 mockup khd 原文: 待处理·04 / 进行中·05 / 冒出·02 / 已归档·03
export const WARROOM_COLUMNS: KColumn[] = [
  { key: "todo", label: "待处理", count: "04" },
  { key: "wip",  label: "进行中", count: "05" },
  { key: "new",  label: "冒出",   count: "02" },
  { key: "done", label: "已归档", count: "03", done: true },
];

// 与 mockup eyebrow/lede 数字一致 ("12 项在飞" 是 mockup 字面, 即便
// 4+5+2+3=14. R-0 mockup 优先 · 不自作主张改到 14)
export const WARROOM_LEDE_COUNT = "12";

// ═══ mockup L3372-3395 (todo 列 4 张) ═══
const TODO: KCard[] = [
  {
    id: "t-01", column: "todo",
    title: "海创智能 · 授信预审",
    pill: { label: "P1", variant: "P1" },
    meta: ["授信", { cn: "明日到期" }],
    body: [{ text: "已收齐 7/9 份材料。" }, { text: "财报 P.24 待补披露利率。", em: true }],
    who: { av: "王", name: "王哲" }, go: "打开",
  },
  {
    id: "t-02", column: "todo",
    title: "政策 §214 · 影响筛查",
    pill: { label: "加急", variant: "urg" },
    meta: ["合规", { cn: "今日 12:00" }],
    body: [{ text: "NMPA 新政，医药口 " }, { text: "4 户", em: true }, { text: " 命中，合规意见待出。" }],
    who: { av: "秦", name: "秦茉" }, go: "打开",
  },
  {
    id: "t-03", column: "todo",
    title: "风控 DSL · 小微贷",
    pill: { label: "等候", variant: "wait" },
    meta: ["风控", "04/22"],
    body: [{ text: "等林楠给回测样本，到齐即可跑 KS。" }],
    who: { av: "林", name: "林楠" }, go: "打开",
  },
  {
    id: "t-04", column: "todo",
    title: "设计评审 · Studio 外壳",
    pill: { label: "P2", variant: "P2" },
    meta: ["桌面", "04/21"],
    body: [{ text: "平台外壳第二轮评审 · " }, { text: "一次过", em: true }, { text: "。" }],
    who: { av: "王", name: "王哲" }, go: "打开",
  },
];

// ═══ mockup L3402-3431 (wip 列 5 张) ═══
const WIP: KCard[] = [
  {
    id: "w-01", column: "wip",
    title: "宁海汇通 · QC 终审",
    pill: { label: "P0", variant: "P0" },
    meta: ["报告", { cn: "运行中" }, "ETA 09:12"],
    body: [{ text: "证据优先第 3 轮，" }, { text: "32 项", em: true }, { text: " 标注\u201C未能自动填写\u201D。" }],
    who: { av: "赵", name: "赵岩" }, go: "打开",
  },
  {
    id: "w-02", column: "wip",
    title: "星河医药 · 预警",
    pill: { label: "加急", variant: "urg" },
    meta: ["预警", { cn: "运行中" }],
    body: [{ text: "二次交叉命中：外网舆情 + 内部交易。" }, { text: "黄色", em: true }, { text: "。" }],
    who: { av: "秦", name: "秦茉" }, go: "打开",
  },
  {
    id: "w-03", column: "wip",
    title: "获客 · 科创板分层",
    pill: { label: "P2", variant: "P2" },
    meta: ["获客", { cn: "运行中" }],
    body: [{ text: "5 家候选已进第 3 圈，产品线匹配中。" }],
    who: { av: "王", name: "王哲" }, go: "打开",
  },
  {
    id: "w-04", column: "wip",
    title: "对话 · 消息归档",
    pill: { label: "等候", variant: "wait" },
    meta: ["定时", { cn: "每晚" }],
    body: [{ text: "过去 7 天频道归档，下次 02:00 自动运行。" }],
    who: { av: "S", name: "系统" }, go: "打开",
  },
  {
    id: "w-05", column: "wip",
    title: "客户面谈纪要 · 03/28",
    pill: { label: "P2", variant: "P2" },
    meta: ["桌面", { cn: "你的" }],
    body: [{ text: "写给林楠 · " }, { text: "120 分钟复盘", em: true }, { text: "。" }],
    who: { av: "王", name: "王哲" }, go: "打开",
  },
];

// ═══ mockup L3438-3448 (new 列 2 张) ═══
const NEW_COL: KCard[] = [
  {
    id: "n-01", column: "new",
    title: "政策 §212 · 冲突点",
    pill: { label: "新", variant: "cn" },
    meta: ["合规", { cn: "2 小时前" }],
    body: [{ text: "冒出业务制度 3 处冲突，" }, { text: "待分流", em: true }, { text: "。" }],
    who: { av: "秦", name: "秦茉" }, go: "打开",
  },
  {
    id: "n-02", column: "new",
    title: "凌云装备 · 相似企业",
    pill: { label: "新", variant: "cn" },
    meta: ["获客", { cn: "30 分钟前" }],
    body: [{ text: "与海创智能匹配度 " }, { text: "0.87", em: true }, { text: "，进入第 3 圈候选。" }],
    who: { av: "王", name: "王哲" }, go: "打开",
  },
];

// ═══ mockup L3456-3473 (done 列 3 张) ═══
const DONE: KCard[] = [
  {
    id: "d-01", column: "done",
    title: "东方生物 · 授信决议",
    pill: { label: "完", variant: "cn" },
    meta: ["授信", "04/16"],
    body: [{ text: "审贷会通过 · ¥6,200" }, { text: "万", em: true }, { text: " / 36 个月。" }],
    who: { av: "赵", name: "赵岩" }, go: "查看",
  },
  {
    id: "d-02", column: "done",
    title: "碧桂园北湾 · 预警复盘",
    pill: { label: "完", variant: "cn" },
    meta: ["预警", "04/15"],
    body: [{ text: "红转黄 · 已降额。复盘笔记已归档。" }],
    who: { av: "秦", name: "秦茉" }, go: "查看",
  },
  {
    id: "d-03", column: "done",
    title: "锋芒材料 · 获客 → 授信",
    pill: { label: "完", variant: "cn" },
    meta: ["获客 → 授信", "04/14"],
    body: [{ text: "闭环：线索 → 面谈 → 报告 → 决议。全流程 " }, { text: "11 天", em: true }, { text: "。" }],
    who: { av: "王", name: "王哲" }, go: "查看",
  },
];

export const WARROOM_CARDS: KCard[] = [...TODO, ...WIP, ...NEW_COL, ...DONE];
