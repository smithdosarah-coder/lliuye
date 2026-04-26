"use client";

/**
 * CanvasModeToggle · 整页画布模式开关
 *
 * 把当前 workspace 所有 .rpt-panel 切入自由拖排模式（FreePanelLayer 驱动）。
 * 按钮挂 Masthead 右端（persona 左侧）· 仅在 /archive/** 下可用。
 *
 * 开启流程：
 *   1. 找到 `.v-archive--canon[data-agent="X"]`，按 DOM 顺序遍历 `.rpt-panel`
 *   2. 对每个 panel 抓 `getBoundingClientRect()`（相对 `.v-archive--canon`），
 *      写 panel-layout-store.setPos + setSize · key = `${agent}::${idx}`
 *      （仅在 store 无对应 entry 时写 · 保留用户已拖过的位置）
 *   3. 写 `body.dataset.freePanels = "true"`，FreePanelLayer 的 MutationObserver
 *      自动接管 · 切 absolute 定位 · 初始位置 = 原 grid 位置，用户看不到堆叠
 *
 * 关闭流程：
 *   1. `panel-layout-store.clearAgent(agent)` 清当前 agent 布局快照
 *   2. 删 `body.dataset.freePanels`，FreePanelLayer 自动 unwireAll 回网格
 *
 * 红线：不改 FreePanelLayer 逻辑，只调它暴露的 store actions。
 */

import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { usePanelLayoutStore } from "@/lib/store/panel-layout-store";

const STORAGE_KEY = "platform.canvas-mode.v1";

function currentAgent(): string | null {
  if (typeof document === "undefined") return null;
  const root = document.querySelector<HTMLElement>(".v-archive--canon[data-agent]");
  return root?.getAttribute("data-agent") ?? null;
}

function snapshotPanels(agent: string) {
  const root = document.querySelector<HTMLElement>(
    `.v-archive--canon[data-agent="${agent}"]`,
  );
  if (!root) return;
  const parentRect = root.getBoundingClientRect();
  const panels = Array.from(root.querySelectorAll<HTMLElement>(".rpt-panel"));
  const store = usePanelLayoutStore.getState();
  panels.forEach((panel, idx) => {
    const key = `${agent}::${idx}`;
    // 已有用户拖过的位置就不覆盖；只为"首次进入画布"兜底 grid 初始坐标
    if (store.panels[key]) return;
    const rect = panel.getBoundingClientRect();
    const x = Math.round(rect.left - parentRect.left);
    const y = Math.round(rect.top - parentRect.top);
    const w = Math.round(rect.width);
    const h = Math.round(rect.height);
    usePanelLayoutStore.getState().setPos(key, x, y);
    usePanelLayoutStore.getState().setSize(key, w, h);
  });
}

export function CanvasModeToggle() {
  const pathname = usePathname() || "/";
  const inArchive = pathname.startsWith("/archive/");
  const [active, setActive] = useState(false);

  // 挂载时：先读 localStorage 恢复画布模式，再与真实 body dataset 校准 button 视觉
  useEffect(() => {
    if (typeof document === "undefined") return;
    let saved: string | null = null;
    try {
      saved = localStorage.getItem(STORAGE_KEY);
    } catch {
      /* localStorage 被禁用 · 走 dataset 回退 */
    }
    if (saved === "true" && document.body.dataset.freePanels !== "true") {
      // 刷新前处于画布模式 · 先 snapshot（若有 workspace）再激活，避免切 absolute 后堆叠
      const agent = currentAgent();
      if (agent) snapshotPanels(agent);
      document.body.dataset.freePanels = "true";
    }
    setActive(document.body.dataset.freePanels === "true");
  }, []);

  const toggle = useCallback(() => {
    if (typeof document === "undefined") return;
    const on = document.body.dataset.freePanels === "true";
    if (on) {
      const agent = currentAgent();
      if (agent) usePanelLayoutStore.getState().clearAgent(agent);
      delete document.body.dataset.freePanels;
      try {
        localStorage.setItem(STORAGE_KEY, "false");
      } catch {
        /* ignore */
      }
      setActive(false);
    } else {
      const agent = currentAgent();
      if (agent) snapshotPanels(agent);
      document.body.dataset.freePanels = "true";
      try {
        localStorage.setItem(STORAGE_KEY, "true");
      } catch {
        /* ignore */
      }
      setActive(true);
    }
  }, []);

  // ⌘⇧F / Ctrl+Shift+F 全局热键 · 与按钮 click 等价
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!(e.metaKey || e.ctrlKey)) return;
      if (!e.shiftKey) return;
      if (e.key !== "F" && e.key !== "f") return;
      e.preventDefault();
      toggle();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggle]);

  return (
    <button
      type="button"
      className={`canvas-mode-toggle${active ? " on" : ""}`}
      onClick={toggle}
      disabled={!inArchive}
      title={
        inArchive
          ? active
            ? "退出画布模式 (⌘⇧F)"
            : "整页画布模式 (⌘⇧F)"
          : "在 AI 助手工作区启用画布模式"
      }
      aria-pressed={active}
      aria-label="切换画布模式"
    >
      <span className="ic" aria-hidden>
        ▦
      </span>
      <span className="lbl">画布</span>
    </button>
  );
}
