/**
 * Warroom view · mock fixture (Task I 重写, 对齐 mockup L3353-3478)
 *
 * Shape:
 * - TextSeg[]: body 富文本段 (em 斜体内联)
 * - MetaSeg:  category/status 行, 支持 `{cn: "..."}` wrap 或裸文字
 * - KCard:    单张卡片 (.kcard) 全部字段
 * - KColumn:  4 列 (.kcol) 元数据, done=true 附 .kcol.done 深色
 *
 * 偏离 mockup + onboarding (R-0 mockup 优先, Task D/E/F/G/H 套路):
 * - onboarding 列名 "待分配 / 进行中 / 等待回复 / 已完成" -> mockup 实 "待处理 /
 *   进行中 / 冒出 / 已归档", 按 mockup
 * - onboarding 要 "7 种 priority-pill (P0/P1/P2/P3/合规/法务/风险)" -> mockup
 *   只有 .pr default + .urg + .wait + .cn 4 样. 做法: 按 onboarding 7 种做
 *   CSS 变体, mockup 原 3 status 变体 (urg/wait/cn) 保留供 status 类 pill
 *   (非优先级), 共 10 个可选 variant
 * - onboarding 要 "每列 10-14 张 kcard 总 ~50" -> mockup 实 14 张总
 *   (4/5/2/3). 按 onboarding 扩到 50 (13/14/10/13), 用 mockup 的 14 张为
 *   种子保 1:1 复制, 其余按风格扩展
 * - onboarding 要 "case-in 首屏进场" -> mockup 只有 .kcol rise 逐列 stagger,
 *   按 onboarding 追加 .kcard case-in 逐卡 stagger (mockup rise 保留)
 */

export type TextSeg = { text: string; em?: boolean };

export type MetaSeg = string | { cn: string };

export type PriorityPill =
  | "P0"
  | "P1"
  | "P2"
  | "P3"
  | "compli"
  | "law"
  | "risk"
  // mockup-native status variants (保留供 mockup 1:1 种子卡)
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

export const WARROOM_COLUMNS: KColumn[] = [
  { key: "todo", label: "待处理", count: "13" },
  { key: "wip",  label: "进行中", count: "14" },
  { key: "new",  label: "冒出",   count: "11" },
  { key: "done", label: "已归档", count: "13", done: true },
];

// ═══ mockup L3372-3395 原文种子 (todo 列 4 张) ═══
const SEED_TODO: KCard[] = [
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

// ═══ mockup L3402-3431 种子 (wip 列 5 张) ═══
const SEED_WIP: KCard[] = [
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

// ═══ mockup L3438-3448 种子 (new 列 2 张) ═══
const SEED_NEW: KCard[] = [
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

// ═══ mockup L3456-3473 种子 (done 列 3 张) ═══
const SEED_DONE: KCard[] = [
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

// ═══ onboarding 扩展卡 (覆盖 7 priority variant) ═══
const EXT_TODO: KCard[] = [
  { id: "t-05", column: "todo", title: "宁海汇通 · 关联方披露补充",
    pill: { label: "合规", variant: "compli" },
    meta: ["合规", { cn: "今日 16:00" }],
    body: [{ text: "附注 7 补\u201C无偿拆借\u201D，已发林楠确认。" }],
    who: { av: "秦", name: "秦茉" }, go: "打开" },
  { id: "t-06", column: "todo", title: "林氏制造 · 法务审合同",
    pill: { label: "法务", variant: "law" },
    meta: ["法务", "04/23"],
    body: [{ text: "担保主体变更，" }, { text: "合同 v3", em: true }, { text: " 待法务过。" }],
    who: { av: "李", name: "李默" }, go: "打开" },
  { id: "t-07", column: "todo", title: "华东线晨报 · 4/20",
    pill: { label: "P3", variant: "P3" },
    meta: ["桌面", "04/20"],
    body: [{ text: "昨日 3 条要闻汇总，含宁海 QC 进度。" }],
    who: { av: "王", name: "王哲" }, go: "打开" },
  { id: "t-08", column: "todo", title: "季度授信池 · 回顾",
    pill: { label: "P2", variant: "P2" },
    meta: ["授信", "本周内"],
    body: [{ text: "Q1 授信同比 +12%，坏账 0.8% 稳定线内。" }],
    who: { av: "林", name: "林楠" }, go: "打开" },
  { id: "t-09", column: "todo", title: "瑞源纺织 · 授信审贷会准备",
    pill: { label: "P1", variant: "P1" },
    meta: ["授信", { cn: "明日 10:00" }],
    body: [{ text: "财报已解析，" }, { text: "四维评分 72", em: true }, { text: " 分。" }],
    who: { av: "赵", name: "赵岩" }, go: "打开" },
  { id: "t-10", column: "todo", title: "大客户拜访 · 山澜海工",
    pill: { label: "P3", variant: "P3" },
    meta: ["桌面", "04/24"],
    body: [{ text: "行长同去，议题聚焦航运周期对冲方案。" }],
    who: { av: "王", name: "王哲" }, go: "打开" },
  { id: "t-11", column: "todo", title: "行内培训 · AI 助手使用",
    pill: { label: "P3", variant: "P3" },
    meta: ["桌面", "04/26"],
    body: [{ text: "10 位客户经理首次上手，素材待准备。" }],
    who: { av: "王", name: "王哲" }, go: "打开" },
  { id: "t-12", column: "todo", title: "风控新规 · 敞口限额",
    pill: { label: "风险", variant: "risk" },
    meta: ["风控", { cn: "今日 18:00" }],
    body: [{ text: "单户敞口限额下调 8%，存量客户逐个核对。" }],
    who: { av: "陈", name: "陈诺" }, go: "打开" },
  { id: "t-13", column: "todo", title: "海创智能装备 · 董事会决议补件",
    pill: { label: "P2", variant: "P2" },
    meta: ["授信", "04/22"],
    body: [{ text: "缺股东会决议原件，已发对方公司章秘书。" }],
    who: { av: "王", name: "王哲" }, go: "打开" },
];

const EXT_WIP: KCard[] = [
  { id: "w-06", column: "wip", title: "风控 DSL v3.1 · staging 复核",
    pill: { label: "风险", variant: "risk" },
    meta: ["风控", { cn: "运行中" }],
    body: [{ text: "KS 0.41 稳定，通过率 42.3%，复核 2/3。" }],
    who: { av: "陈", name: "陈诺" }, go: "打开" },
  { id: "w-07", column: "wip", title: "晨星工艺 · 相似企业打标",
    pill: { label: "P2", variant: "P2" },
    meta: ["获客", { cn: "运行中" }],
    body: [{ text: "12 家 look-alike，已圈定" }, { text: "top 3", em: true }, { text: "。" }],
    who: { av: "王", name: "王哲" }, go: "打开" },
  { id: "w-08", column: "wip", title: "授信评分模型 · 对私 v2",
    pill: { label: "P1", variant: "P1" },
    meta: ["授信", { cn: "运行中" }],
    body: [{ text: "对私板块评分表 6 维，样本训练到第 4 轮。" }],
    who: { av: "林", name: "林楠" }, go: "打开" },
  { id: "w-09", column: "wip", title: "§214 合规意见书 · 4 户批量",
    pill: { label: "合规", variant: "compli" },
    meta: ["合规", { cn: "运行中" }, "ETA 14:00"],
    body: [{ text: "首户星河医药已出草稿，其余 3 户同构复用。" }],
    who: { av: "秦", name: "秦茉" }, go: "打开" },
  { id: "w-10", column: "wip", title: "法务 · 宁海担保函核对",
    pill: { label: "法务", variant: "law" },
    meta: ["法务", { cn: "运行中" }],
    body: [{ text: "担保额度与主合同匹配，补充连带条款。" }],
    who: { av: "李", name: "李默" }, go: "打开" },
  { id: "w-11", column: "wip", title: "晨报 C-02 · 周三晨会",
    pill: { label: "P3", variant: "P3" },
    meta: ["桌面", { cn: "你的" }],
    body: [{ text: "含 5 分钟客户案例插播，幻灯在写。" }],
    who: { av: "王", name: "王哲" }, go: "打开" },
  { id: "w-12", column: "wip", title: "宁海汇通 · 红线扫描 v3",
    pill: { label: "P0", variant: "P0" },
    meta: ["授信", { cn: "运行中" }],
    body: [{ text: "11 项红线，当前命中 " }, { text: "0 条", em: true }, { text: "。" }],
    who: { av: "赵", name: "赵岩" }, go: "打开" },
  { id: "w-13", column: "wip", title: "获客信号 · 招聘爬取 4/19",
    pill: { label: "等候", variant: "wait" },
    meta: ["定时", { cn: "每日 02:00" }],
    body: [{ text: "昨日新增 238 条岗位信号，关键词命中 17 家。" }],
    who: { av: "S", name: "系统" }, go: "打开" },
  { id: "w-14", column: "wip", title: "风险日报 · 分行层汇总",
    pill: { label: "风险", variant: "risk" },
    meta: ["风险", "04/19"],
    body: [{ text: "华东一线关注户 6 家，其中 2 家需行长复核。" }],
    who: { av: "陈", name: "陈诺" }, go: "打开" },
];

const EXT_NEW: KCard[] = [
  { id: "n-03", column: "new", title: "澜熠新材 · 融资意向",
    pill: { label: "新", variant: "cn" },
    meta: ["获客", { cn: "1 小时前" }],
    body: [{ text: "客户主动询问流动资金贷款，首访待排。" }],
    who: { av: "王", name: "王哲" }, go: "打开" },
  { id: "n-04", column: "new", title: "央行 4/18 利率通报",
    pill: { label: "合规", variant: "compli" },
    meta: ["合规", { cn: "3 小时前" }],
    body: [{ text: "LPR 1Y 不变，但房贷下限浮动口径调整。" }],
    who: { av: "秦", name: "秦茉" }, go: "打开" },
  { id: "n-05", column: "new", title: "海创设备 · 担保房屋变更",
    pill: { label: "风险", variant: "risk" },
    meta: ["预警", { cn: "4 小时前" }],
    body: [{ text: "抵押物产权异动，系统自动标黄。" }],
    who: { av: "秦", name: "秦茉" }, go: "打开" },
  { id: "n-06", column: "new", title: "同业 · 工行小微 DSL 白皮书",
    pill: { label: "P3", variant: "P3" },
    meta: ["风控", { cn: "昨日" }],
    body: [{ text: "对标参考，内部研讨会时间待定。" }],
    who: { av: "陈", name: "陈诺" }, go: "打开" },
  { id: "n-07", column: "new", title: "瑞通新材 · 复审自动触发",
    pill: { label: "新", variant: "cn" },
    meta: ["预警", { cn: "6 小时前" }],
    body: [{ text: "到期前 30 天自动发复审任务，待分流。" }],
    who: { av: "S", name: "系统" }, go: "打开" },
  { id: "n-08", column: "new", title: "客户反馈 · 信贷报告助手",
    pill: { label: "P3", variant: "P3" },
    meta: ["桌面", { cn: "今日 09:00" }],
    body: [{ text: "林楠：\u201C财务附注段证据链想要更密\u201D，已记。" }],
    who: { av: "林", name: "林楠" }, go: "打开" },
  { id: "n-09", column: "new", title: "新线索 · 智普能源",
    pill: { label: "新", variant: "cn" },
    meta: ["获客", { cn: "2 小时前" }],
    body: [{ text: "风电整机商，招聘信号 + 专利信号同时命中。" }],
    who: { av: "王", name: "王哲" }, go: "打开" },
  { id: "n-10", column: "new", title: "舆情 · 星河医药研发延期",
    pill: { label: "加急", variant: "urg" },
    meta: ["预警", { cn: "45 分钟前" }],
    body: [{ text: "核心管线 Ph-III 数据推迟，股价 -4.2%。" }],
    who: { av: "秦", name: "秦茉" }, go: "打开" },
  { id: "n-11", column: "new", title: "内部 · 审贷会议程变动",
    pill: { label: "P3", variant: "P3" },
    meta: ["桌面", { cn: "1 小时前" }],
    body: [{ text: "行长调整，宁海汇通移到本周四早场。" }],
    who: { av: "林", name: "林楠" }, go: "打开" },
];

const EXT_DONE: KCard[] = [
  { id: "d-04", column: "done", title: "瑞通新材 · 完成放款",
    pill: { label: "完", variant: "cn" },
    meta: ["授信", "04/14"],
    body: [{ text: "¥1,800" }, { text: "万", em: true }, { text: " / 12 个月，已入账。" }],
    who: { av: "王", name: "王哲" }, go: "查看" },
  { id: "d-05", column: "done", title: "碧海纺织 · 合规整改",
    pill: { label: "合规", variant: "compli" },
    meta: ["合规", "04/13"],
    body: [{ text: "§198 涉票据，整改 " }, { text: "3 处", em: true }, { text: "，已过审。" }],
    who: { av: "秦", name: "秦茉" }, go: "查看" },
  { id: "d-06", column: "done", title: "金城建材 · 预警降级",
    pill: { label: "完", variant: "cn" },
    meta: ["预警", "04/12"],
    body: [{ text: "黄转绿，下次常规复审 04/28。" }],
    who: { av: "秦", name: "秦茉" }, go: "查看" },
  { id: "d-07", column: "done", title: "清风塑料 · 授信续贷",
    pill: { label: "完", variant: "cn" },
    meta: ["授信", "04/11"],
    body: [{ text: "额度 +8%，期限 24 个月，基准 + 95 bps。" }],
    who: { av: "赵", name: "赵岩" }, go: "查看" },
  { id: "d-08", column: "done", title: "法务 · 宁海主合同二审过",
    pill: { label: "完", variant: "cn" },
    meta: ["法务", "04/10"],
    body: [{ text: "条款补丁 " }, { text: "4 处", em: true }, { text: "，已双方用印。" }],
    who: { av: "李", name: "李默" }, go: "查看" },
  { id: "d-09", column: "done", title: "获客 · 风电产业链 look-alike",
    pill: { label: "完", variant: "cn" },
    meta: ["获客", "04/09"],
    body: [{ text: "首期候选 12 家，3 家转首访。" }],
    who: { av: "王", name: "王哲" }, go: "查看" },
  { id: "d-10", column: "done", title: "风控 · 通过率底线复核",
    pill: { label: "完", variant: "cn" },
    meta: ["风控", "04/08"],
    body: [{ text: "底线 38%，上周均值 42.1%，差额正常。" }],
    who: { av: "陈", name: "陈诺" }, go: "查看" },
  { id: "d-11", column: "done", title: "培训 · 报告助手首讲",
    pill: { label: "完", variant: "cn" },
    meta: ["桌面", "04/07"],
    body: [{ text: "10 位客户经理到场，现场试跑 1 户。" }],
    who: { av: "王", name: "王哲" }, go: "查看" },
  { id: "d-12", column: "done", title: "同业 · 招行小微对标",
    pill: { label: "完", variant: "cn" },
    meta: ["风控", "04/05"],
    body: [{ text: "对标报告已归档，下周策略会复用。" }],
    who: { av: "陈", name: "陈诺" }, go: "查看" },
  { id: "d-13", column: "done", title: "客户面谈 · 山澜海工",
    pill: { label: "完", variant: "cn" },
    meta: ["桌面", "04/04"],
    body: [{ text: "航运订单回流，拟续贷 ¥2,400" }, { text: "万", em: true }, { text: "。" }],
    who: { av: "王", name: "王哲" }, go: "查看" },
];

export const WARROOM_CARDS: KCard[] = [
  ...SEED_TODO, ...EXT_TODO,
  ...SEED_WIP, ...EXT_WIP,
  ...SEED_NEW, ...EXT_NEW,
  ...SEED_DONE, ...EXT_DONE,
];
