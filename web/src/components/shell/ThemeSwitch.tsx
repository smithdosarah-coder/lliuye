"use client";

import { useEffect, useState } from "react";

type Theme = "canvas" | "matcha" | "dusk" | "ink";

/**
 * 4 主题切换器（Canvas / Matcha / Dusk / Ink）。
 * Letterpress (crimson) 2026-04-20 下架 —— 用户判"黑红读老 DEMO"。
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

  useEffect(() => {
    const saved = (typeof window !== "undefined" && localStorage.getItem(STORAGE_KEY)) as Theme | null;
    if (saved && ["canvas", "matcha", "dusk", "ink"].includes(saved)) {
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
