"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, HelpCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import type { Question } from "@/lib/credit-types";

export interface QuestionnaireAnswer {
  id: string;
  answer: string;
  skipped?: boolean;
}

/**
 * Inline 问卷面板 — 右栏组件。
 * 每题 title + 可展开 hint + textarea/input + 跳过按钮。
 * 提交时仅回传有实际作答(非空且未跳过)的条目。
 */
export function QuestionnairePanel({
  questions,
  onSubmit,
  busy = false,
  submitLabel = "完善报告",
}: {
  questions: Question[];
  onSubmit: (answers: QuestionnaireAnswer[]) => void;
  busy?: boolean;
  submitLabel?: string;
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [skipped, setSkipped] = useState<Set<string>>(new Set());
  const [openHints, setOpenHints] = useState<Set<string>>(new Set());

  const toggleHint = (id: string) => {
    setOpenHints((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSkip = (id: string) => {
    setSkipped((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSubmit = () => {
    const answers: QuestionnaireAnswer[] = [];
    for (const q of questions) {
      if (skipped.has(q.id)) {
        answers.push({ id: q.id, answer: "", skipped: true });
        continue;
      }
      const v = (values[q.id] ?? "").trim();
      if (v) answers.push({ id: q.id, answer: v });
    }
    onSubmit(answers);
  };

  const filledCount = questions.filter(
    (q) => !skipped.has(q.id) && (values[q.id] ?? "").trim().length > 0
  ).length;
  const skippedCount = skipped.size;

  return (
    <div className="space-y-4">
      <div className="text-[11px] font-tabular tracking-wider text-[var(--color-ink-muted)]">
        共 {questions.length} 项 · 已填 {filledCount} · 跳过 {skippedCount}
      </div>

      <ul className="space-y-5">
        {questions.map((q) => {
          const hintOpen = openHints.has(q.id);
          const isSkipped = skipped.has(q.id);
          return (
            <li
              key={q.id}
              className={`border-l-2 pl-3 transition-colors ${
                isSkipped
                  ? "border-[var(--color-line-strong)] opacity-50"
                  : "border-[var(--color-ink)]"
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="text-[13px] text-[var(--color-ink)] leading-relaxed flex-1">
                  {q.question}
                </div>
                <button
                  type="button"
                  onClick={() => toggleSkip(q.id)}
                  className="shrink-0 text-[10px] font-tabular tracking-wider text-[var(--color-ink-muted)] hover:text-[var(--color-ember)] underline underline-offset-2"
                >
                  {isSkipped ? "恢复" : "跳过"}
                </button>
              </div>

              {q.hint && (
                <button
                  type="button"
                  onClick={() => toggleHint(q.id)}
                  className="mt-1.5 inline-flex items-center gap-1 text-[10px] font-tabular tracking-wider text-[var(--color-brass)] hover:text-[var(--color-brass-dim)]"
                >
                  {hintOpen ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
                  <HelpCircle size={10} />
                  填写提示
                </button>
              )}
              {hintOpen && q.hint && (
                <div className="mt-1.5 text-[11px] text-[var(--color-ink-muted)] leading-relaxed bg-[var(--color-overlay)] border-l border-[var(--color-brass)] px-2.5 py-1.5">
                  {q.hint}
                </div>
              )}

              <div className="mt-2">
                {renderInput(q, values[q.id] ?? "", (v) =>
                  setValues((prev) => ({ ...prev, [q.id]: v }))
                , isSkipped)}
              </div>
            </li>
          );
        })}
      </ul>

      <div className="pt-2 border-t border-[var(--color-line)]">
        <Button
          onClick={handleSubmit}
          disabled={busy || (filledCount === 0 && skippedCount === 0)}
          className="w-full"
        >
          {busy ? "正在完善…" : submitLabel}
        </Button>
      </div>
    </div>
  );
}

function renderInput(
  q: Question,
  value: string,
  onChange: (v: string) => void,
  disabled: boolean
) {
  const cls =
    "w-full px-3 py-2 text-[13px] bg-[var(--color-paper)] border border-[var(--color-line-strong)] focus:border-[var(--color-ink)] focus:outline-none transition-colors text-[var(--color-ink)] disabled:opacity-50";

  if (q.input_type === "number") {
    return (
      <input
        type="number"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className={cls}
      />
    );
  }
  if (q.input_type === "select" && q.options) {
    return (
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className={cls}
      >
        <option value="">请选择…</option>
        {q.options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    );
  }
  if (q.input_type === "text") {
    return (
      <input
        type="text"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className={cls}
      />
    );
  }
  // default: textarea
  return (
    <textarea
      rows={3}
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
      placeholder="请在此作答…"
      className={cls + " resize-none leading-relaxed"}
    />
  );
}
