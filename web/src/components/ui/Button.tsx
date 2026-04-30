"use client";

import { cn } from "@/lib/utils";
import { forwardRef } from "react";

type Variant = "primary" | "secondary" | "ghost";
type Size = "sm" | "md" | "lg";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", children, ...rest }, ref) => {
    const variantStyle = {
      primary:
        "bg-[var(--ink)] text-[var(--chalk)] hover:bg-[var(--ink-65)] active:bg-[var(--ink)]",
      secondary:
        "bg-[var(--chalk)] text-[var(--ink)] border border-[var(--ink-14)] hover:border-[var(--ink)]",
      ghost:
        "bg-transparent text-[var(--ink-65)] hover:bg-[var(--ink-04)]",
    }[variant];

    const sizeStyle = {
      sm: "h-8 px-3 text-[12px]",
      md: "h-10 px-5 text-[13px]",
      lg: "h-12 px-7 text-[14px]",
    }[size];

    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center gap-2 font-medium tracking-tight transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--chalk)]",
          variantStyle,
          sizeStyle,
          className
        )}
        {...rest}
      >
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
}: {
  options: Array<{ value: T; label: string }>;
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="inline-flex border border-[var(--ink-14)] p-0.5 bg-[var(--chalk)]">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={cn(
            "px-4 py-1.5 text-[12px] font-medium transition-all",
            value === opt.value
              ? "bg-[var(--ink)] text-[var(--chalk)]"
              : "text-[var(--ink-65)] hover:bg-[var(--ink-04)]"
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
