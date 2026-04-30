/**
 * Agent registry — single source of truth for navigation, colors, and routing.
 */
import {
  FileText,
  Search,
  Scale,
  SlidersHorizontal,
  Activity,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";

export type AgentKey =
  | "report"
  | "channel"
  | "credit"
  | "riskctrl"
  | "alert"
  | "compliance";

export interface AgentDef {
  key: AgentKey;
  order: number;
  code: string;          // A06, A01 ...
  title: string;         // CJK title
  tagline: string;       // archive index tile (short one-liner)
  description: string;   // A-015: /archive/[agent] lede (page-level)
  eyebrowLabel: string;  // A-016: "Report Generation" / "Credit Decision Assistant" etc.
  path: string;
  icon: LucideIcon;
  accent: string;        // css color token — used for rail stripe
}

export const AGENTS: AgentDef[] = [
  {
    key: "report",
    order: 1,
    code: "A06",
    title: "信贷报告助手",
    tagline: "材料 → 授信申报书",
    description:
      "读入企业材料包,按「普惠授信申报及审查审批意见表」节段自动撰写,未能填写字段显式标注。",
    eyebrowLabel: "Report Generation",
    path: "/report",
    icon: FileText,
    accent: "var(--t-report)",
  },
  {
    key: "channel",
    order: 2,
    code: "A01",
    title: "全渠道获客",
    tagline: "画像 → Look-alike 候选池",
    description:
      "从细微信号（中标/专利/扩产/获奖/认证）中挖出小而美的公司 — 5 路并行信号搜索 + 信号密度排序",
    eyebrowLabel: "Signal-Driven Prospecting",
    path: "/channel",
    icon: Search,
    accent: "var(--t-channel)",
  },
  {
    key: "credit",
    order: 3,
    code: "A03",
    title: "授信决策辅助",
    tagline: "报告 → 评分 → 额度建议",
    // default-state description (segment = corporate); credit workspace overrides
    // dynamically via HeaderSlot as the user switches segments.
    description:
      "面向中大型企业：财务 / 行业 / 经营 / 担保四维评分 + 红线 + 同业案例。",
    eyebrowLabel: "Credit Decision Assistant",
    path: "/credit",
    icon: Scale,
    accent: "var(--t-credit)",
  },
  {
    key: "riskctrl",
    order: 4,
    code: "A02",
    title: "风控策略运营",
    tagline: "规则 · 回测 · 指标",
    description:
      "用历史样本回测新策略：业务上是否更赚钱？坏账是否受控？给出可直接拍板的上线建议。",
    eyebrowLabel: "Strategy Operations",
    path: "/riskctrl",
    icon: SlidersHorizontal,
    accent: "var(--t-riskctrl)",
  },
  {
    key: "alert",
    order: 5,
    code: "A04",
    title: "贷中风险预警",
    tagline: "客户 × 风险规则矩阵",
    description:
      "对存量客户进行外部舆情/司法与内部行为/交易的双路扫描，交叉命中后形成红黄绿三级预警与处置建议。",
    eyebrowLabel: "Portfolio Early Warning",
    path: "/alert",
    icon: Activity,
    accent: "var(--t-alert)",
  },
  {
    key: "compliance",
    order: 6,
    code: "A05",
    title: "合规巡检",
    tagline: "新政策 × 存量制度",
    description:
      "新政策发布事件触发，自动对存量制度文件进行冲突检测，输出分级修订建议。",
    eyebrowLabel: "Policy Compliance Audit",
    path: "/compliance",
    icon: ShieldCheck,
    accent: "var(--t-compli)",
  },
];

export function findAgentByPath(pathname: string): AgentDef | undefined {
  return AGENTS.find((a) => pathname === a.path || pathname.startsWith(a.path + "/"));
}
