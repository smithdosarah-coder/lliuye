"use client";

import { cn } from "@/lib/utils";
import { ChevronDown } from "lucide-react";

export function Select({
  value,
  onChange,
  options,
  className,
}: {
  value: string;
  onChange: (v: string) => void;
  options: Array<{ value: string; label: string }>;
  className?: string;
}) {
  return (
    <div className={cn("relative", className)}>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          "w-full appearance-none border border-[var(--color-line-strong)] bg-[var(--color-paper-raised)]",
          "h-10 pl-4 pr-10 text-[13px] text-[var(--color-ink)]",
          "hover:border-[var(--color-ink)] focus:outline-none focus:border-[var(--color-ink)] transition-colors"
        )}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <ChevronDown
        size={14}
        className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-[var(--color-ink-muted)]"
      />
    </div>
  );
}
