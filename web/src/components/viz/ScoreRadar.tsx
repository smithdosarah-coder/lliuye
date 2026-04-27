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
    <div
      className="score-radar-wrap w-full h-[280px]"
      data-testid="score-radar"
    >
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="72%">
          <PolarGrid
            stroke="var(--ink-14)"
            strokeDasharray="2 3"
          />
          <PolarAngleAxis
            dataKey="label"
            tick={{
              fill: "var(--ink-65)",
              fontSize: 11.5,
              fontFamily: "var(--sans)",
            }}
            tickLine={false}
          />
          <PolarRadiusAxis
            domain={[0, 100]}
            angle={-45}
            tick={{
              fill: "var(--ink-48)",
              fontSize: 10,
              fontFamily: "var(--mono)",
            }}
            tickCount={5}
            axisLine={false}
          />
          <Radar
            dataKey="score"
            stroke="var(--t-channel)"
            fill="color-mix(in srgb, var(--t-channel) 24%, transparent)"
            fillOpacity={1}
            strokeWidth={1.6}
            isAnimationActive
            animationDuration={600}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
