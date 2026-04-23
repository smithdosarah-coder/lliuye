"use client";

import { useEffect, useRef, useState } from "react";

type Theme = "canvas" | "matcha" | "dusk" | "ink";

/**
 * 4 主题切换器（Canvas / Matcha / Dusk / Ink）。
 * Letterpress (crimson) / Nebula (紫粉) 已下架 — 用户判老 DEMO 视感 / 重 saturate。
 * 2026-04-23 · 改双态：
 *   - 缩略态（默认）· 单 pill 气泡（和 CanvasModeToggle 同大小），显示当前主题色圆点 + "主题"
 *   - 展开态 · 完整 4 主题横向 chip 栏
 *   - 外部点击 / Esc 自动收回 · 选中后 280ms 自动收回
 */

const THEMES: { key: Theme; label: string }[] = [
  { key: "canvas", label: "Canvas" },
  { key: "matcha", label: "Matcha" },
  { key: "dusk", label: "Dusk" },
  { key: "ink", label: "Ink" },
];

const STORAGE_KEY = "platform-shell-theme";

export function ThemeSwitch() {
  const [theme, setTheme] = useState<Theme>("canvas");
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const saved = (typeof window !== "undefined" && localStorage.getItem(STORAGE_KEY)) as Theme | null;
    if (saved && ["canvas", "matcha", "dusk", "ink"].includes(saved)) {
      setTheme(saved);
      applyTheme(saved);
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function applyTheme(t: Theme) {
    if (t === "canvas") document.body.removeAttribute("data-theme");
    else document.body.setAttribute("data-theme", t);
  }

  function handleClick(t: Theme) {
    setTheme(t);
    applyTheme(t);
    localStorage.setItem(STORAGE_KEY, t);
    // 选中后短延迟收回，给用户视觉确认机会
    window.setTimeout(() => setOpen(false), 280);
  }

  const currentLabel = THEMES.find((x) => x.key === theme)?.label ?? "Canvas";

  return (
    <div className={`theme-sw${open ? " is-open" : ""}`} ref={rootRef}>
      {/* 缩略态 · 小 pill · 和画布按钮同尺寸 */}
      <button
        type="button"
        className="theme-sw-trigger"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`主题 · 当前 ${currentLabel}`}
        title={open ? "收起主题切换" : `主题 · ${currentLabel}`}
      >
        <span className="sw-dot" data-t={theme} aria-hidden />
        <span className="lbl">主题</span>
      </button>

      {/* 展开态 · 横向 4 主题 chip 条 · 气泡样式 */}
      {open && (
        <div className="theme-sw-pop" role="listbox" aria-label="主题切换">
          {THEMES.map(({ key, label }) => (
            <button
              key={key}
              type="button"
              role="option"
              aria-selected={theme === key}
              data-t={key}
              className={theme === key ? "on" : undefined}
              onClick={() => handleClick(key)}
            >
              <span className="sw-dot" data-t={key} aria-hidden />
              {label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
