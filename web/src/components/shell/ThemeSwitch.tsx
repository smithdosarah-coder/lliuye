"use client";

import { useEffect, useState } from "react";

type Theme = "canvas" | "matcha" | "dusk" | "crimson";

/**
 * 4 可见主题；Ink 故意不出现在切换器里（mockup L3562-3569）,
 * 但 data-theme="ink" 仍可通过 devtools / URL 参数手动激活。
 * Letterpress 沿用 mockup selector `data-t="crimson"` 保 1:1。
 */
const THEMES: { key: Theme; label: string }[] = [
  { key: "canvas", label: "Canvas" },
  { key: "matcha", label: "Matcha" },
  { key: "dusk", label: "Blush" },
  { key: "crimson", label: "Letterpress" },
];

const STORAGE_KEY = "platform-shell-theme";

export function ThemeSwitch() {
  const [theme, setTheme] = useState<Theme>("canvas");

  useEffect(() => {
    const saved = (typeof window !== "undefined" && localStorage.getItem(STORAGE_KEY)) as Theme | null;
    if (saved && ["canvas", "matcha", "dusk", "crimson"].includes(saved)) {
      setTheme(saved);
      applyTheme(saved);
    }
  }, []);

  function applyTheme(t: Theme) {
    if (t === "canvas") document.body.removeAttribute("data-theme");
    else document.body.setAttribute("data-theme", t);
  }

  function handleClick(t: Theme) {
    setTheme(t);
    applyTheme(t);
    localStorage.setItem(STORAGE_KEY, t);
  }

  return (
    <div className="theme-sw" role="radiogroup" aria-label="主题切换">
      <span className="lbl">Palette</span>
      {THEMES.map(({ key, label }) => (
        <button
          key={key}
          type="button"
          role="radio"
          aria-checked={theme === key}
          data-t={key}
          className={theme === key ? "on" : undefined}
          onClick={() => handleClick(key)}
        >
          <span className="sw-dot" />
          {label}
        </button>
      ))}
    </div>
  );
}
