"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

/**
 * RuleReadOnlyList — Phase 1 Task D frontend stub
 *
 * 以只读表格 + 可折叠描述渲染 ruleset。schema 对齐 agent_riskctrl rules.json
 * （{rule_id, name, conditions[{field, operator, value}], action, priority,
 *   description, backtest}）。Phase 2 交付"进入编辑器"后此组件演化为 ReadWrite。
 */

export type Condition = {
  field: string;
  operator: string;
  value: string | number | boolean | Array<string | number>;
};

export type Rule = {
  rule_id: string;
  name: string;
  description?: string;
  conditions: Condition[];
  action: "approve" | "reject" | "manual_review" | string;
  priority: number;
  backtest?: Record<string, number | null | undefined>;
};

const ACTION_LABEL: Record<string, string> = {
  approve: "通过",
  reject: "拒绝",
  manual_review: "人工复核",
};

const ACTION_TONE: Record<string, string> = {
  approve: "text-[var(--color-sage)] border-[var(--color-sage)]",
  reject: "text-[var(--color-ember)] border-[var(--color-ember)]",
  manual_review: "text-[var(--color-brass)] border-[var(--color-brass)]",
};

function formatCondition(c: Condition): string {
  const v = Array.isArray(c.value) ? `[${c.value.join(", ")}]` : String(c.value);
  return `${c.field} ${c.operator} ${v}`;
}

export function RuleReadOnlyList({ rules }: { rules: Rule[] }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  return (
    <div className="overflow-hidden" style={{ borderRadius: "var(--r-md)" }}>
      <div className="grid grid-cols-12 gap-3 px-4 py-2.5 text-[10px] font-tabular tracking-[0.2em] text-[var(--color-ink-muted)] uppercase bg-[var(--color-paper-sunken)] border border-[var(--color-line)]">
        <div className="col-span-2">Rule ID</div>
        <div className="col-span-3">名称</div>
        <div className="col-span-4">条件（AND）</div>
        <div className="col-span-2">动作</div>
        <div className="col-span-1 text-right">优先级</div>
      </div>
      <ul className="border-x border-b border-[var(--color-line)] divide-y divide-[var(--color-line)]">
        {rules.map((r) => {
          const isOpen = expanded.has(r.rule_id);
          const tone = ACTION_TONE[r.action] || "text-[var(--color-ink-muted)] border-[var(--color-line-strong)]";
          const actionLabel = ACTION_LABEL[r.action] || r.action;
          const hasDesc = Boolean(r.description && r.description.trim().length > 0);
          return (
            <li key={r.rule_id} className="bg-[var(--color-paper-raised)]">
              <button
                type="button"
                onClick={() => hasDesc && toggle(r.rule_id)}
                disabled={!hasDesc}
                className="w-full grid grid-cols-12 gap-3 px-4 py-3 text-left items-center disabled:cursor-default hover:bg-[var(--color-overlay)] disabled:hover:bg-transparent transition-colors"
              >
                <div className="col-span-2 flex items-center gap-1.5 font-tabular text-[12px] text-[var(--color-brass)]">
                  {hasDesc ? (
                    isOpen ? (
                      <ChevronDown size={12} className="text-[var(--color-ink-muted)]" />
                    ) : (
                      <ChevronRight size={12} className="text-[var(--color-ink-muted)]" />
                    )
                  ) : (
                    <span className="w-3" />
                  )}
                  {r.rule_id}
                </div>
                <div className="col-span-3 text-[13px] text-[var(--color-ink)] truncate">
                  {r.name}
                </div>
                <div className="col-span-4 font-tabular text-[11px] text-[var(--color-ink-soft)] leading-snug">
                  {r.conditions.length > 0
                    ? r.conditions.map(formatCondition).join("  ∧  ")
                    : <span className="italic text-[var(--color-ink-muted)]">无条件</span>}
                </div>
                <div className="col-span-2">
                  <span
                    className={`inline-block px-2 py-0.5 border text-[10px] font-tabular tracking-wider uppercase ${tone}`}
                    style={{ borderRadius: "var(--r-md)" }}
                  >
                    {actionLabel}
                  </span>
                </div>
                <div className="col-span-1 text-right font-tabular text-[12px] text-[var(--color-ink-muted)]">
                  {r.priority}
                </div>
              </button>
              {isOpen && hasDesc && (
                <div className="px-4 pb-4 pt-1 text-[12px] text-[var(--color-ink-soft)] leading-relaxed whitespace-pre-wrap border-t border-[var(--color-line)] bg-[var(--color-paper-sunken)]">
                  {r.description}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
