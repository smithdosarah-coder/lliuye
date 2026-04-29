"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export interface Stage {
  key: string;
  label: string;
}

type Status = "pending" | "active" | "done" | "error";

export function PipelineRail({
  stages,
  active,
  done,
  error,
}: {
  stages: Stage[];
  active?: string;
  done: Set<string>;
  error?: boolean;
}) {
  return (
    <ol className="relative space-y-0">
      <div className="absolute left-[7px] top-2 bottom-2 w-px bg-[var(--ink-08)]" />
      {stages.map((s, i) => {
        const status: Status = error
          ? "error"
          : done.has(s.key)
          ? "done"
          : active === s.key
          ? "active"
          : "pending";
        return (
          <li key={s.key} className="relative flex items-center gap-3 py-2.5">
            <StageDot status={status} />
            <div className="flex-1 flex items-baseline justify-between">
              <span
                className={cn(
                  "text-[13px] transition-colors",
                  status === "done" && "text-[var(--ink)]",
                  status === "active" && "text-[var(--ink)] font-medium",
                  status === "pending" && "text-[var(--ink-48)]",
                  status === "error" && "text-[var(--t-alert)]"
                )}
              >
                {s.label}
              </span>
              <span className="font-tabular text-[10px] tracking-wider text-[var(--ink-48)]">
                {String(i + 1).padStart(2, "0")}
              </span>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

function StageDot({ status }: { status: Status }) {
  const base = "relative w-[15px] h-[15px] rounded-full border flex items-center justify-center z-10 bg-[var(--chalk)]";
  if (status === "done") {
    return (
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        className={cn(base, "border-[var(--safe)] bg-[var(--safe)]")}
      >
        <svg width="8" height="8" viewBox="0 0 8 8" className="text-[var(--chalk)]">
          <path d="M1.5 4L3.2 5.7L6.5 2" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </motion.div>
    );
  }
  if (status === "active") {
    return (
      <div className={cn(base, "border-[var(--accent)]")}>
        <motion.div
          className="w-[7px] h-[7px] rounded-full bg-[var(--accent)]"
          animate={{ opacity: [1, 0.3, 1], scale: [1, 1.2, 1] }}
          transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>
    );
  }
  if (status === "error") {
    return <div className={cn(base, "border-[var(--t-alert)] bg-[var(--t-alert)]")} />;
  }
  return <div className={cn(base, "border-[var(--ink-14)]")} />;
}
