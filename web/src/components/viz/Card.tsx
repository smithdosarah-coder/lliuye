"use client";

import { cn } from "@/lib/utils";

export function Card({
  children,
  className,
  title,
  eyebrow,
  action,
}: {
  children: React.ReactNode;
  className?: string;
  title?: string;
  eyebrow?: string;
  action?: React.ReactNode;
}) {
  return (
    <section
      className={cn(
        "relative bg-[var(--chalk)] border border-[var(--ink-08)]",
        className
      )}
    >
      {(title || eyebrow || action) && (
        <header className="flex items-end justify-between gap-3 px-5 py-4 border-b border-[var(--ink-08)]">
          <div>
            {eyebrow && (
              <div className="text-[10px] font-tabular tracking-[0.25em] text-[var(--accent)] uppercase">
                {eyebrow}
              </div>
            )}
            {title && (
              <h3 className="mt-0.5 font-display text-[17px] text-[var(--ink)] leading-tight">
                {title}
              </h3>
            )}
          </div>
          {action}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function Stat({
  label,
  value,
  unit,
  hint,
}: {
  label: string;
  value: string | number;
  unit?: string;
  hint?: string;
}) {
  return (
    <div>
      <div className="text-[10px] font-tabular tracking-[0.2em] text-[var(--ink-48)] uppercase">
        {label}
      </div>
      <div className="mt-1.5 flex items-baseline gap-1.5">
        <span className="font-display font-tabular text-[28px] text-[var(--ink)] leading-none">
          {value}
        </span>
        {unit && (
          <span className="text-[12px] text-[var(--ink-48)] font-tabular">
            {unit}
          </span>
        )}
      </div>
      {hint && (
        <div className="mt-1 text-[11px] text-[var(--ink-48)]">{hint}</div>
      )}
    </div>
  );
}
