"use client";

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";

export interface RadarDim {
  label: string;
  score: number;
}

export function ScoreRadar({ data }: { data: RadarDim[] }) {
  return (
    <div className="w-full h-[280px]">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="72%">
          <PolarGrid
            stroke="rgba(26, 46, 40, 0.18)"
            strokeDasharray="2 3"
          />
          <PolarAngleAxis
            dataKey="label"
            tick={{
              fill: "var(--color-ink-soft)",
              fontSize: 12,
              fontFamily: "var(--font-sans)",
            }}
            tickLine={false}
          />
          <PolarRadiusAxis
            domain={[0, 100]}
            angle={90}
            tick={{
              fill: "var(--color-ink-muted)",
              fontSize: 10,
              fontFamily: "var(--font-mono)",
            }}
            tickCount={5}
            axisLine={false}
          />
          <Radar
            dataKey="score"
            stroke="var(--color-brass)"
            fill="var(--color-brass)"
            fillOpacity={0.18}
            strokeWidth={1.5}
            isAnimationActive
            animationDuration={600}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
