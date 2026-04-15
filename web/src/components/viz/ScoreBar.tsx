"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export function ScoreBar({
  label,
  value,
  max = 100,
  size = "md",
}: {
  label: string;
  value: number;
  max?: number;
  size?: "sm" | "md";
}) {
  const pct = Math.max(0, Math.min(1, value / max));
  const tone =
    value >= 70
      ? "var(--color-sage)"
      : value >= 50
      ? "var(--color-brass)"
      : value >= 30
      ? "var(--color-amber)"
      : "var(--color-ember)";

  return (
    <div className={cn("group", size === "sm" ? "space-y-1" : "space-y-1.5")}>
      <div className="flex items-baseline justify-between gap-2">
        <span
          className={cn(
            "text-[var(--color-ink-soft)]",
            size === "sm" ? "text-[11px]" : "text-[12px]"
          )}
        >
          {label}
        </span>
        <span
          className={cn(
            "font-tabular text-[var(--color-ink)]",
            size === "sm" ? "text-[12px]" : "text-[14px] font-medium"
          )}
        >
          {value}
        </span>
      </div>
      <div
        className={cn(
          "relative w-full bg-[var(--color-paper-sunken)] overflow-hidden",
          size === "sm" ? "h-[3px]" : "h-[5px]"
        )}
      >
        <motion.div
          className="absolute top-0 left-0 h-full"
          style={{ background: tone }}
          initial={{ width: 0 }}
          animate={{ width: `${pct * 100}%` }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        />
      </div>
    </div>
  );
}
