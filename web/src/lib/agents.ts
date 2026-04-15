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
  code: string;   // A06, A01 ...
  title: string;
  tagline: string;
  path: string;
  icon: LucideIcon;
  accent: string; // css color token — used for rail stripe
}

export const AGENTS: AgentDef[] = [
  {
    key: "report",
    order: 1,
    code: "A06",
    title: "信贷报告助手",
    tagline: "材料 → 授信申报书",
    path: "/report",
    icon: FileText,
    accent: "var(--color-ink)",
  },
  {
    key: "channel",
    order: 2,
    code: "A01",
    title: "全渠道获客",
    tagline: "画像 → Look-alike 候选池",
    path: "/channel",
    icon: Search,
    accent: "var(--color-brass)",
  },
  {
    key: "credit",
    order: 3,
    code: "A03",
    title: "授信决策辅助",
    tagline: "报告 → 评分 → 额度建议",
    path: "/credit",
    icon: Scale,
    accent: "var(--color-sage)",
  },
  {
    key: "riskctrl",
    order: 4,
    code: "A02",
    title: "风控策略运营",
    tagline: "规则 · 回测 · 指标",
    path: "/riskctrl",
    icon: SlidersHorizontal,
    accent: "var(--color-amber)",
  },
  {
    key: "alert",
    order: 5,
    code: "A04",
    title: "贷中风险预警",
    tagline: "客户 × 风险规则矩阵",
    path: "/alert",
    icon: Activity,
    accent: "var(--color-ember)",
  },
  {
    key: "compliance",
    order: 6,
    code: "A05",
    title: "合规巡检",
    tagline: "新政策 × 存量制度",
    path: "/compliance",
    icon: ShieldCheck,
    accent: "var(--color-brass-dim)",
  },
];

export function findAgentByPath(pathname: string): AgentDef | undefined {
  return AGENTS.find((a) => pathname === a.path || pathname.startsWith(a.path + "/"));
}
