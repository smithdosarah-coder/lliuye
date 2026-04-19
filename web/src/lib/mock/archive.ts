/**
 * Archive view · 6 Agent tile fixture (Task H, 对齐 mockup L3284-3350)
 *
 * 偏离 mockup + onboarding (R-0 mockup 优先, Task D/E/F/G 套路):
 * - onboarding 要 "本周使用次数 + 最近活跃时间" -> mockup 实只有 .stat 一行
 *   (标签 + 数字) · 保留 mockup 单行, 取消 "最近活跃时间" 第 2 行
 * - onboarding 要 "--t-* 功能色做 accent 边框 + icon 底纹" -> mockup 无此变体
 *   · 作为 R-0 上附加层: 每 tile 3px 左侧 rail (border-left: var(--tile-accent))
 *   + .circle 底色用 var(--tile-accent), 文字 chalk; 保留 mockup 原 g2-g6 渐变
 * - mockup tile 顺序 AGENT · 01-06 = 获客/风控/授信/预警/合规/报告,
 *   onboarding 列举 "报告 / 预警 / 合规 / 授信 / 风控 / 获客" (反序) ·
 *   按 mockup 顺序实现 (1:1)
 */
import type { AgentKey } from "@/lib/agents";

export type TextSeg = { text: string; em?: boolean };

export type ArchiveTile = {
  key: AgentKey;
  ix: string;
  cn: string;
  em: string;
  circle: string;
  variant?: "g2" | "g3" | "g4" | "g5" | "g6";
  blurb: TextSeg[];
  statLabel: string;
  statNum: string;
  accent: string;
};

export const ARCHIVE_TILES: ArchiveTile[] = [
  {
    key: "channel",
    ix: "AGENT · 01",
    cn: "获客",
    em: "Scout.",
    circle: "01",
    blurb: [
      { text: "相似企业 look-alike · 信号追踪 · 产品匹配。" },
      { text: "今日新增 5 条线索。", em: true },
    ],
    statLabel: "活跃线索",
    statNum: "14",
    accent: "var(--t-channel)",
  },
  {
    key: "riskctrl",
    ix: "AGENT · 02",
    cn: "风控",
    em: "Forge.",
    circle: "02",
    variant: "g2",
    blurb: [{ text: "DSL 规则生成 · KS / 通过率回测 · 指标诊断。" }],
    statLabel: "在用规则",
    statNum: "08",
    accent: "var(--t-riskctrl)",
  },
  {
    key: "credit",
    ix: "AGENT · 03",
    cn: "授信",
    em: "Bench.",
    circle: "03",
    variant: "g3",
    blurb: [{ text: "四维评分 · 额度与期限建议 · 红线检查 · 案例召回。" }],
    statLabel: "待审卷宗",
    statNum: "27",
    accent: "var(--t-credit)",
  },
  {
    key: "alert",
    ix: "AGENT · 04",
    cn: "预警",
    em: "Tower.",
    circle: "04",
    variant: "g4",
    blurb: [{ text: "外网舆情 + 内部交易双路扫描 · 红黄绿分级 · 处置建议。" }],
    statLabel: "今日告警",
    statNum: "08",
    accent: "var(--t-alert)",
  },
  {
    key: "compliance",
    ix: "AGENT · 05",
    cn: "合规",
    em: "Ledger.",
    circle: "05",
    variant: "g5",
    blurb: [{ text: "政策事件触发 · 业务制度矩阵扫描 · 违规冲突点明细。" }],
    statLabel: "本周新增",
    statNum: "04",
    accent: "var(--t-compli)",
  },
  {
    key: "report",
    ix: "AGENT · 06",
    cn: "报告",
    em: "Press.",
    circle: "06",
    variant: "g6",
    blurb: [{ text: "材料解析 · 字段抽取 · 证据优先生成 · 质检终审。" }],
    statLabel: "就绪草稿",
    statNum: "12",
    accent: "var(--t-report)",
  },
];
