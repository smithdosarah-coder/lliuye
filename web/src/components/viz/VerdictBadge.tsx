"use client";

import { cn } from "@/lib/utils";

type Verdict = "批准" | "有条件批准" | "拒绝" | string;

export function VerdictBadge({ decision, grade }: { decision: Verdict; grade?: string }) {
  const tone =
    decision === "批准"
      ? { bg: "var(--safe)", ink: "var(--chalk)" }
      : decision === "有条件批准"
      ? { bg: "var(--accent)", ink: "var(--chalk)" }
      : { bg: "var(--t-alert)", ink: "var(--chalk)" };

  return (
    <div className="inline-flex items-stretch font-display tracking-tight select-none">
      <div
        className="px-5 py-3 text-[28px] leading-none"
        style={{ background: tone.bg, color: tone.ink }}
      >
        {decision}
      </div>
      {grade && (
        <div
          className="px-4 py-3 text-[20px] leading-none border-l"
          style={{
            background: "var(--ink)",
            color: "var(--chalk)",
            borderColor: "rgba(255,255,255,0.15)",
          }}
        >
          {grade}
          <span className="text-[11px] opacity-60 ml-1 font-tabular">级</span>
        </div>
      )}
    </div>
  );
}

export function VerdictRibbon({ label }: { label: string }) {
  return (
    <div
      className={cn(
        "inline-block px-2 py-0.5 text-[10px] font-tabular tracking-[0.2em] uppercase",
        "bg-[var(--ink)] text-[var(--chalk)]"
      )}
    >
      {label}
    </div>
  );
}
