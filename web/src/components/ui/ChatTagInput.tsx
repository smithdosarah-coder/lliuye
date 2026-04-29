"use client";

import { useEffect, useRef, useState } from "react";
import { Sparkles, X } from "lucide-react";

export interface Tag {
  category: string;
  value: string;
}

/**
 * 输入模式：用户以自然语言描述需求，系统在输入停顿后自动结构化为标签。
 * 标签作为"AI 已理解"的反馈展示，可一键删除误识别项，不强制编辑。
 */
export function ChatTagInput({
  placeholder,
  presetPrompts = [],
  parseFn,
  onTagsChange,
  onTextChange,
  busy,
  debounceMs = 500,
}: {
  placeholder: string;
  presetPrompts?: string[];
  parseFn: (text: string) => Promise<Tag[]>;
  onTagsChange?: (tags: Tag[]) => void;
  onTextChange?: (text: string) => void;
  busy?: boolean;
  debounceMs?: number;
}) {
  const [text, setText] = useState("");
  const [tags, setTags] = useState<Tag[]>([]);
  const [parsing, setParsing] = useState(false);
  const tokenRef = useRef(0);

  useEffect(() => {
    onTextChange?.(text);
    const trimmed = text.trim();
    if (!trimmed) {
      setTags([]);
      onTagsChange?.([]);
      return;
    }
    const token = ++tokenRef.current;
    const timer = setTimeout(async () => {
      setParsing(true);
      try {
        const next = await parseFn(trimmed);
        // 丢弃过期结果（用户又改字了）
        if (token !== tokenRef.current) return;
        setTags(next);
        onTagsChange?.(next);
      } finally {
        if (token === tokenRef.current) setParsing(false);
      }
    }, debounceMs);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, debounceMs]);

  const removeTag = (i: number) => {
    const next = tags.filter((_, idx) => idx !== i);
    setTags(next);
    onTagsChange?.(next);
  };

  return (
    <div className="space-y-4">
      <div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={placeholder}
          disabled={busy}
          rows={3}
          className="w-full px-3 py-2.5 text-[13px] bg-[var(--chalk)] border border-[var(--ink-14)] text-[var(--ink)] focus:outline-none focus:border-[var(--ink)] resize-none font-sans leading-relaxed"
        />
        {presetPrompts.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {presetPrompts.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setText(p)}
                className="text-[11px] text-[var(--ink-48)] hover:text-[var(--ink)] border-b border-dashed border-[var(--ink-14)] pb-0.5"
              >
                {p}
              </button>
            ))}
          </div>
        )}
        <div className="mt-3 flex items-center justify-between">
          <span className="text-[11px] text-[var(--ink-48)] font-tabular">
            {text.length}/200
          </span>
          <span className="inline-flex items-center gap-1 text-[11px] font-tabular text-[var(--ink-48)]">
            <Sparkles size={11} className={parsing ? "animate-pulse text-[var(--accent)]" : ""} />
            {parsing ? "AI 理解中…" : tags.length > 0 ? `已识别 ${tags.length} 个维度` : "输入后自动识别"}
          </span>
        </div>
      </div>

      {tags.length > 0 && (
        <div className="pt-4 border-t border-[var(--ink-08)]">
          <div className="text-[10px] font-tabular tracking-[0.2em] text-[var(--ink-48)] uppercase mb-2">
            AI 识别到的维度 · 误识别可一键删除
          </div>
          <div className="flex flex-wrap gap-1.5">
            {tags.map((t, i) => (
              <span
                key={`${t.category}:${t.value}:${i}`}
                className="inline-flex items-center gap-1 pl-2 pr-1 py-0.5 text-[11px] font-tabular border border-[var(--ink-65)] bg-[var(--chalk)]"
              >
                <span className="text-[var(--ink-48)]">{t.category}</span>
                <span className="opacity-40">:</span>
                <span className="text-[var(--ink)]">{t.value}</span>
                <button
                  onClick={() => removeTag(i)}
                  className="ml-0.5 p-0.5 text-[var(--ink-48)] hover:text-[var(--t-alert)]"
                >
                  <X size={10} />
                </button>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
