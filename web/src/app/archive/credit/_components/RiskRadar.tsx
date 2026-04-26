"use client";

/**
 * RiskRadar — Agent3 L1-3 四维风险雷达（对公 / 对私自动派发）。
 *
 * Q-033 backlog landing · 来源 596283f (agent3 pre-rebase tip 6c5820a · agent_credit
 * P3F rebase 时 auto-dropped empty 因 web/ 红线触发)。本任 (P3F 轨 4 Stage 2)
 * 路径迁移 web/src/app/credit/components/ (legacy 顶层 6 页 · 主 CLI 已删 5b575c8)
 * → web/src/app/archive/credit/_components/ (canon /archive/[agent] 路径)。
 *
 * 对公 4 维：财务 / 行业 / 经营 / 担保（0-100）
 * 对私 / 普惠 4 维：还款能力 / 还款意愿 / 稳定性 / 担保（0-100）
 *
 * 数据消费自 agent_credit.scoring_model_{corporate,retail} 产出 ScoringPayload。
 * 底层渲染复用通用 ScoreRadar (web/src/components/viz/ScoreRadar.tsx · recharts
 * RadarChart)。
 */

import { ScoreRadar } from "@/components/viz/ScoreRadar";
import type { ScoringPayload } from "@/lib/credit-types";

const CORP_DIMS = [
  { label: "财务", key: "financial_score" as const },
  { label: "行业", key: "industry_score" as const },
  { label: "经营", key: "operational_score" as const },
  { label: "担保", key: "guarantee_score" as const },
];

const RETAIL_DIMS = [
  { label: "还款能力", key: "repayment_capacity" as const },
  { label: "还款意愿", key: "repayment_willingness" as const },
  { label: "稳定性", key: "stability" as const },
  { label: "担保", key: "collateral" as const },
];

export type RiskRadarSegment = "corporate" | "retail" | "sme";

export function RiskRadar({
  scoring,
  segment,
}: {
  scoring: ScoringPayload;
  segment: RiskRadarSegment;
}) {
  const data =
    segment === "corporate"
      ? CORP_DIMS.map((d) => ({
          label: d.label,
          score: (scoring[d.key] as number | undefined) ?? 0,
        }))
      : RETAIL_DIMS.map((d) => ({
          label: d.label,
          score:
            (scoring.category_scores?.[d.key] as number | undefined) ?? 0,
        }));
  return (
    <div data-testid="risk-radar" data-segment={segment}>
      <ScoreRadar data={data} />
    </div>
  );
}
