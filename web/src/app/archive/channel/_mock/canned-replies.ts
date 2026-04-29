/**
 * Channel · demo 假回复字典（2026-04-22 CLI-C · Step 2）
 *
 * 纯前端 demo 用：不接 LLM、不接 API。
 * Composer 提交后调 pickReply(text) 返回一条预设回复，typing 占位 1.2-1.8s 后替换。
 *
 * 选回复策略：
 *   1. 关键词命中（candidate / signal / 行业 / 触达 / 增加 / ...）→ 返回首个命中条
 *   2. 都不命中 → round-robin 在 GENERIC 池里循环
 *
 * 字段约定：sectionDiff / fieldRef 沿用 ConversationMessage shape；
 *           回复条尽量带 fieldRef 让右栏 chip 可见，更"假"得真。
 */

import type { ConversationMessage } from "@/lib/mock/agent-channel-sessions";

export type CannedReply = {
  /** 关键词数组，命中即返回；空数组表示通用 fallback。 */
  keywords: string[];
  /** 回复正文（不要太长，单条控制 80-200 字以内）。 */
  content: string;
  fieldRef?: string;
  sectionDiff?: ConversationMessage["sectionDiff"];
};

const KEYED: CannedReply[] = [
  {
    keywords: ["候选", "推荐", "top"],
    content:
      "已为你筛选 Top 5 候选：瑞鼎(0.91) · 德丰(0.87) · 榕信(0.83) · 华盛(0.78) · 美禾(0.74)。其中瑞鼎刚中标厦门连锁便利店年度供应，触达时机最优。",
    fieldRef: "Candidates · Top 5",
    sectionDiff: {
      sectionAnchor: "Top · 推荐",
      after:
        "5 家首推 · 平均相似度 0.83 · 建议 T+1 内由客户经理优先触达",
    },
  },
  {
    keywords: ["信号", "扫描", "scan"],
    content:
      "8 信号源已轮询完毕：工商 / 招投标 / 舆情 / 司法 / 社保 / 纳税 / 招聘 全活跃，投融资在本客群覆盖低暂关。本轮新增 ¥420 万中标 + 7 岗招聘 + 1 项专精特新认定。",
    fieldRef: "Signals · 8 源",
  },
  {
    keywords: ["行业", "扩展", "扩"],
    content:
      "可同步扩到「日用品批发 + 食品配送 + 物流仓储」三邻行业，预计补 18 家候选。是否纳入？/expand 同意 · /reject 拒绝。",
    fieldRef: "Query · 行业范围",
  },
  {
    keywords: ["触达", "外呼", "电话", "拜访"],
    content:
      "建议触达节奏：T+0 电话铺垫(产品方向) → T+1 邮件发约访 → T+3 线下拜访带样品。对应话术已挂在 Candidates 卡片悬浮提示。",
    fieldRef: "Reach · 节奏建议",
  },
  {
    keywords: ["产品", "推", "贷"],
    content:
      "对该画像的最佳匹配三件套：普惠信用贷(无抵免登)、商超订单融资(应收质押)、仓单质押贷(实物抵押)。优先级按企业资质动态排序。",
    fieldRef: "Products · 匹配",
  },
  {
    keywords: ["风险", "排除", "exclude", "黑名单"],
    content:
      "风险过滤已生效：被执行 / 失信 / 行政处罚 ≥ 2 三类自动排除，本轮过滤掉 87 家。如需放宽到「行政处罚 1 次已结清」，发 /loosen-risk。",
    fieldRef: "Risk · 过滤策略",
  },
  {
    keywords: ["相似度", "阈值", "threshold"],
    content:
      "当前阈值 0.72，留 28 家。下降到 0.65 预计 +12 家(候选共 40 家)，但精准度会从 87% → 79%。建议保持 0.72，回退操作 /threshold 0.72。",
    fieldRef: "Match · 阈值",
  },
  {
    keywords: ["地域", "区域", "geo"],
    content:
      "当前覆盖福建 + 浙南，扩到「江西赣州 / 广东潮汕」可补 9 家同画像潜客；这两片区与福建商贸链路上下游高度协同。/expand-geo 同意。",
    fieldRef: "Query · 地域",
  },
  {
    keywords: ["导出", "export", "下载"],
    content:
      "已生成 Top 推荐 .xlsx · 28 家 · 含画像分 / 信号命中 / 风险标 / 建议产品 / 触达节奏 5 列；同时同步到客户经理的「待跟进」列表。",
    fieldRef: "Export · 完成",
  },
  {
    keywords: ["分配", "派单", "assign"],
    content:
      "Top 5 已按地域分派：瑞鼎 / 美禾 → 王哲；德丰 / 华盛 → 李华；榕信 → 陈凯。每人 24h 内反馈触达进度即可。",
    fieldRef: "Assign · 分派",
  },
];

const GENERIC: CannedReply[] = [
  {
    keywords: [],
    content:
      "收到。我会在 8 信号源里再回扫一轮，同时把这条诉求写入下一版画像权重；右侧候选列表 1 分钟内会刷新。",
  },
  {
    keywords: [],
    content:
      "明白，已记下。基于当前画像，下一步建议：把瑞鼎(0.91) 与 德丰(0.87) 这两家先排进本周触达。是否同意？",
    fieldRef: "Next · 触达计划",
  },
  {
    keywords: [],
    content:
      "继续推进中。如需切换标杆客户或者改 12 维特征权重，发 /switch <客户名> 或 /weight 指令我直接重算。",
  },
  {
    keywords: [],
    content:
      "已把你的指令并入扫描队列。这次会重点看「下沉商超 + 连锁便利店」两条供应链的同画像企业，预计 30 秒出新一版 Top 5。",
    fieldRef: "Scan · 重排队",
  },
];

let rrIdx = 0;

/** 选回复：先关键词，命中不上 round-robin generic；纯 demo，无 LLM。 */
export function pickReply(rawText: string): CannedReply {
  const text = rawText.toLowerCase().trim();
  for (const k of KEYED) {
    if (k.keywords.some((kw) => text.includes(kw.toLowerCase()))) {
      return k;
    }
  }
  const reply = GENERIC[rrIdx % GENERIC.length];
  rrIdx += 1;
  return reply;
}

/** 1.2 - 1.8 s 随机延时，模拟思考。 */
export function nextThinkDelayMs(): number {
  return 1200 + Math.floor(Math.random() * 600);
}
