/**
 * Dispatch view · mock fixture (Task G 重写, 对齐 mockup L3145-3268)
 *
 * Shape 说明:
 * - TextSeg[]: 文本段落带 em 标记, 保 1:1 mockup 里 <em> 斜体 (italic font)
 * - Thread: 左栏 .ch 一行 + 中栏切到此 thread 时头部 .hd 的显示
 * - Msg: 中栏 .msg 一条 (me 表示本人, memo 附 callout 备忘块)
 * - MemoBlock: .memo callout with mhd + ol + mft chips (罗马数字列表)
 * - CaseFile: 右栏 .dp-info .body 的 5 row 卷宗摘要
 *
 * 偏离 mockup (R-0 优先, 按 Task D/E/F 套路记账):
 * - onboarding 说 "5 thread + 每 thread 8-12 memo" -> mockup 实有 6 channels, memo 是单消息
 *   内的罕见 callout (不是每消息一个), 按 mockup 实作 (每 thread 3-5 msg, 其中 1 条可能带 memo)
 * - onboarding 说 ".memo.urgent / .memo.system 两种标注" -> mockup 无此变体, 只有一种 .memo 样式
 * - onboarding 说 "3 个卷宗卡片" -> mockup 实 1 张卷宗 card (.dp-info 只有一个), 5 行信息
 * - onboarding 说 "未读红点 + 最近活跃时间 20s 刷新" -> mockup .ch .meta 是静态时间串, 无红点 UI
 *   (保留 unread 字段供未来, 但不渲染红点)
 */

export type TextSeg = { text: string; em?: boolean };

export type Thread = {
  id: string;
  name: string;
  meta: string;
  last: TextSeg[];
  activeTitleCn: string;
  activeTitleEm: string;
  activeCount: string;
  unread?: number;
};

export type MemoItem = {
  h: string;
  s: TextSeg[];
};

export type MemoBlock = {
  title: string;
  titleEm: string;
  rt: string;
  items: MemoItem[];
  chips: { label: string; ghost?: boolean }[];
};

export type Msg = {
  id: string;
  who: string;
  whoEm?: string;
  time: string;
  body: TextSeg[];
  me?: boolean;
  memo?: MemoBlock;
};

export type CaseRow = {
  k: string;
  vNum: string;
  vUnitCn?: string;
  vEm?: string;
  sub: TextSeg[];
};

export type CaseFile = {
  title: string;
  titleEm: string;
  n: string;
  rows: CaseRow[];
};

export const DISPATCH_THREADS: Thread[] = [
  {
    id: "th-ninghai",
    name: "#宁海汇通 · 授信",
    meta: "08:41",
    last: [{ text: "赵岩：" }, { text: "已打开，正在看第三页…", em: true }],
    activeTitleCn: "宁海汇通科技",
    activeTitleEm: "· 授信",
    activeCount: "3 人 · 1 AGENT",
    unread: 2,
  },
  {
    id: "th-xinghe",
    name: "#星河医药 · 政策",
    meta: "08:12",
    last: [{ text: "秦茉：" }, { text: "新政 §214，待你确认处置", em: true }],
    activeTitleCn: "星河医药",
    activeTitleEm: "· 政策",
    activeCount: "4 人 · 1 AGENT",
    unread: 1,
  },
  {
    id: "th-huadong",
    name: "#华东线 · 晨会",
    meta: "07:50",
    last: [{ text: "林楠：今天 10:30 · 视频" }],
    activeTitleCn: "华东线分行",
    activeTitleEm: "· 晨会",
    activeCount: "9 人",
  },
  {
    id: "th-haichuang",
    name: "#海创智能 · 获客",
    meta: "昨日",
    last: [{ text: "获客助手：" }, { text: "5 条相似企业线索", em: true }],
    activeTitleCn: "海创智能装备",
    activeTitleEm: "· 获客",
    activeCount: "2 人 · 1 AGENT",
  },
  {
    id: "th-linnan",
    name: "@林楠",
    meta: "昨日",
    last: [{ text: "下周一前给我额度建议" }],
    activeTitleCn: "林楠",
    activeTitleEm: "· 审贷员",
    activeCount: "DM",
  },
  {
    id: "th-riskctrl",
    name: "#风控 · 回测",
    meta: "04/16",
    last: [{ text: "风控助手：DSL 已生成" }],
    activeTitleCn: "风控回测",
    activeTitleEm: "· DSL",
    activeCount: "5 人 · 1 AGENT",
  },
];

const NINGHAI_MEMO: MemoBlock = {
  title: "备忘",
  titleEm: "三点",
  rt: "证据 · P.24 / 附注 7",
  items: [
    {
      h: "资金流向：股东陈宁海 → 公司主账户",
      s: [{ text: "3 笔共 ¥8.2M，期限均 < 12 个月，" }, { text: "无利息", em: true }, { text: "。" }],
    },
    {
      h: "定性：符合《企业会计准则》关联方定义",
      s: [{ text: "陈持股 62%，与公司存在控制关系 · " }, { text: "应披露", em: true }, { text: "。" }],
    },
    {
      h: "披露状态：附注 7 已披露，但未标注利率",
      s: [{ text: "建议补披露利率，或注明\u201C无偿拆借\u201D。" }],
    },
  ],
  chips: [
    { label: "全部采纳" },
    { label: "质疑", ghost: true },
    { label: "追溯原文", ghost: true },
  ],
};

export const DISPATCH_MESSAGES: Record<string, Msg[]> = {
  "th-ninghai": [
    {
      id: "m-nh-1",
      who: "赵岩",
      whoEm: "评审",
      time: "08:36",
      body: [
        { text: "新的授信材料已经拿到，" },
        { text: "财务附注 P.24", em: true },
        { text: " 看一下，股东往来是不是关联交易？" },
      ],
    },
    {
      id: "m-nh-2",
      who: "你",
      time: "08:38",
      me: true,
      body: [{ text: "在看。让报告助手重新解析这一段，把证据链列给你。" }],
    },
    {
      id: "m-nh-3",
      who: "报告助手",
      whoEm: "宁海汇通",
      time: "08:39",
      body: [{ text: "已解析 P.24 股东往来款 ¥8.2M。三点观察待你审核 —" }],
      memo: NINGHAI_MEMO,
    },
  ],
  "th-xinghe": [
    { id: "m-xh-1", who: "秦茉",       whoEm: "合规",   time: "08:05", body: [{ text: "§214 新政下发，涉票据质押的新定义。" }] },
    { id: "m-xh-2", who: "合规助手",   whoEm: "政策",   time: "08:07", body: [{ text: "业务矩阵命中 4 户，其中 " }, { text: "星河医药", em: true }, { text: " 位列首位。" }] },
    { id: "m-xh-3", who: "你",                           time: "08:12", me: true, body: [{ text: "先出合规意见草稿，今日 14:00 前我签字。" }] },
  ],
  "th-huadong": [
    { id: "m-hd-1", who: "林楠",       whoEm: "主持",   time: "07:48", body: [{ text: "今天 10:30 · 视频，议程发群里。" }] },
    { id: "m-hd-2", who: "你",                           time: "07:50", me: true, body: [{ text: "收到，" }, { text: "晨报 C-02", em: true }, { text: " 我来讲。" }] },
    { id: "m-hd-3", who: "钱启",       whoEm: "客户经理", time: "07:55", body: [{ text: "我补 5 分钟客户案例。" }] },
  ],
  "th-haichuang": [
    { id: "m-hc-1", who: "获客助手",   whoEm: "早报",   time: "昨 16:02", body: [{ text: "匹配 12 家 look-alike，其中 " }, { text: "4 家", em: true }, { text: " 命中 ≥ 3 类信号。" }] },
    { id: "m-hc-2", who: "你",                           time: "昨 16:10", me: true, body: [{ text: "先排前 3 家画像，明天路演用。" }] },
    { id: "m-hc-3", who: "获客助手",   whoEm: "交付",   time: "昨 17:20", body: [{ text: "画像三连已生成，已同步到 warroom。" }] },
  ],
  "th-linnan": [
    { id: "m-ln-1", who: "林楠",       whoEm: "审贷员", time: "昨 17:30", body: [{ text: "下周一前给我一版额度 + 期限建议，周会拍板。" }] },
    { id: "m-ln-2", who: "你",                           time: "昨 17:42", me: true, body: [{ text: "明天发初稿，含敏感性分析。" }] },
  ],
  "th-riskctrl": [
    { id: "m-rc-1", who: "陈诺",       whoEm: "风控",   time: "04/16 07:58", body: [{ text: "DSL v3.1 回测 KS 0.41，已推 staging 等复核。" }] },
    { id: "m-rc-2", who: "你",                           time: "04/16 08:06", me: true, body: [{ text: "先看通过率，别破 " }, { text: "38%", em: true }, { text: " 底线。" }] },
    { id: "m-rc-3", who: "风控助手",   whoEm: "回测",   time: "04/16 08:18", body: [{ text: "通过率 42.3%，KS 稳定，坏账样本召回率 71%。" }] },
  ],
};

export const DISPATCH_CASEFILES: Record<string, CaseFile> = {
  "th-ninghai": {
    title: "卷宗",
    titleEm: "· 宁海汇通",
    n: "#0487",
    rows: [
      { k: "卷宗号",     vNum: "2026",    vEm: "· 0487",       sub: [{ text: "审贷四部 · 华东一线" }] },
      { k: "授信金额",   vNum: "¥4,800",  vUnitCn: "万元",     sub: [{ text: "24 个月 · 基准 + 120 bps" }] },
      { k: "填写完成度", vNum: "93.5",    vUnitCn: "%",        sub: [{ text: "32 项 标为 " }, { text: "\u201C未能自动填写\u201D", em: true }, { text: "。" }] },
      { k: "红线",       vNum: "0 / 11",                        sub: [{ text: "确定性扫描 · " }, { text: "通过", em: true }, { text: "。" }] },
      { k: "签署进度",   vNum: "2 / 3",                         sub: [{ text: "待 " }, { text: "审贷会主席", em: true }, { text: " 签字。" }] },
    ],
  },
  "th-xinghe": {
    title: "卷宗",
    titleEm: "· 星河医药",
    n: "#0511",
    rows: [
      { k: "卷宗号",   vNum: "2026",    vEm: "· 0511",              sub: [{ text: "合规一部 · §214 新政组" }] },
      { k: "敞口",     vNum: "¥2,300",  vUnitCn: "万元",            sub: [{ text: "票据质押 · " }, { text: "命中新政", em: true }, { text: "。" }] },
      { k: "政策命中", vNum: "4 / 14",                               sub: [{ text: "4 户命中 · 意见待出。" }] },
      { k: "风险等级", vNum: "黄色",    vEm: "III",                 sub: [{ text: "观察名单 · 本周复核。" }] },
      { k: "处置建议", vNum: "补披露",  vEm: "+ 调高利率",          sub: [{ text: "待 " }, { text: "合规主管", em: true }, { text: " 签意见。" }] },
    ],
  },
  "th-huadong": {
    title: "议程",
    titleEm: "· 华东线晨会",
    n: "10:30",
    rows: [
      { k: "参会",     vNum: "9",      vUnitCn: "人",       sub: [{ text: "线上 · Teams 视频。" }] },
      { k: "主持",     vNum: "林楠",                        sub: [{ text: "审贷员 · 本周值班。" }] },
      { k: "议题",     vNum: "3",      vUnitCn: "项",       sub: [{ text: "晨报 / 宁海汇通 / §214 处置。" }] },
      { k: "时长",     vNum: "45",     vUnitCn: "分钟",      sub: [{ text: "含 5 分钟客户案例插播。" }] },
      { k: "纪要输出", vNum: "否",                           sub: [{ text: "行长不在线 · " }, { text: "下次再记", em: true }, { text: "。" }] },
    ],
  },
  "th-haichuang": {
    title: "画像",
    titleEm: "· 海创智能装备",
    n: "#LA-12",
    rows: [
      { k: "候选数",     vNum: "12", vUnitCn: "家",   sub: [{ text: "look-alike · 自 " }, { text: "宁海汇通", em: true }, { text: "。" }] },
      { k: "强信号命中", vNum: "4",  vUnitCn: "家",   sub: [{ text: "≥ 3 类信号 (招聘/舆情/征信)。" }] },
      { k: "已排产",     vNum: "3",  vUnitCn: "家",   sub: [{ text: "明天路演首讲用。" }] },
      { k: "授信建议",   vNum: "预审",                 sub: [{ text: "先过 Agent3 初筛再发意向。" }] },
      { k: "客户经理",   vNum: "你",                   sub: [{ text: "华东一线 · " }, { text: "王哲", em: true }, { text: "。" }] },
    ],
  },
  "th-linnan": {
    title: "档案",
    titleEm: "· 林楠",
    n: "DM",
    rows: [
      { k: "岗位",     vNum: "审贷员",                        sub: [{ text: "华东审贷四部 · 本周值班。" }] },
      { k: "本月交易", vNum: "23",    vUnitCn: "条",          sub: [{ text: "其中 " }, { text: "宁海汇通", em: true }, { text: " 是最大一笔。" }] },
      { k: "最近共事", vNum: "14",    vUnitCn: "次",          sub: [{ text: "平均响应 28 分钟。" }] },
      { k: "待办",     vNum: "1",     vUnitCn: "项",          sub: [{ text: "额度建议 · " }, { text: "周一前", em: true }, { text: "。" }] },
      { k: "联系",     vNum: "飞书",  vEm: "+ 电话",          sub: [{ text: "工作时间应答 ≤ 10 分钟。" }] },
    ],
  },
  "th-riskctrl": {
    title: "回测",
    titleEm: "· 风控 DSL v3.1",
    n: "#RC-031",
    rows: [
      { k: "KS",        vNum: "0.41",                        sub: [{ text: "staging · " }, { text: "较上版 +0.03", em: true }, { text: "。" }] },
      { k: "通过率",    vNum: "42.3",  vUnitCn: "%",         sub: [{ text: "超出底线 38% · 安全。" }] },
      { k: "坏账召回",  vNum: "71",    vUnitCn: "%",         sub: [{ text: "样本 N = 1,250 · 近 12 个月。" }] },
      { k: "规则条数",  vNum: "11",    vUnitCn: "条",        sub: [{ text: "新增 2 · 移除 1 · 微调 3。" }] },
      { k: "复核",      vNum: "2 / 3",                        sub: [{ text: "待 " }, { text: "风控主管", em: true }, { text: " 确认上生产。" }] },
    ],
  },
};
