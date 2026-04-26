"use client";

/**
 * FreePanelLayer · 自由拖排驱动层
 *
 * 挂在 shell 级，始终 return null（不渲染 DOM），通过 effect + 事件委托
 * 给所有 .rpt-panel 增删自由拖排能力。
 *
 * 触发：`document.body.dataset.freePanels === "true"` 时启用；反之回到
 *       原生网格排版（移除 inline style 与 data-panel-id）。
 *
 * 每次进入 free 模式：
 *   1. 扫描所有 `.v-archive--canon[data-agent="X"] .rpt-panel`
 *   2. 以 agent + DOM 内索引生成稳定 key `X::idx`，写 data-panel-id
 *   3. 应用 store 中已保存的 position / size / z
 *
 * 交互（事件委托到 document）：
 *   - mousedown on .rpt-panel-head（非 .pp-grip/button 内）→ 起拖
 *   - mousemove → 写 store.setPos + inline style transform
 *   - mouseup → 结束
 *   - click on .rpt-panel → bringToFront
 *   - dblclick on .rpt-panel-head → reset（回网格位）
 *   - resize observer → 记录用户 resize:both 后的新 size
 *
 * 不引入新 drag 库（红线：保持 HTML5 / native 事件）。
 */

import { useEffect } from "react";
import { usePanelLayoutStore } from "@/lib/store/panel-layout-store";

const PANEL_ID_ATTR = "data-panel-id";

/** 从 .rpt-panel 元素算稳定 key：基于 agent key + DOM 索引（workspace 内）。 */
function computeKey(panel: HTMLElement): string | null {
  const root = panel.closest<HTMLElement>(".v-archive--canon[data-agent]");
  if (!root) return null;
  const agent = root.getAttribute("data-agent") || "unknown";
  const siblings = Array.from(root.querySelectorAll<HTMLElement>(".rpt-panel"));
  const idx = siblings.indexOf(panel);
  if (idx < 0) return null;
  return `${agent}::${idx}`;
}

/** 应用 store 中的 box 到 inline style（仅在 free 模式下）。 */
function applyBox(panel: HTMLElement, box: { x: number; y: number; w?: number; h?: number; z: number }) {
  panel.style.left = `${box.x}px`;
  panel.style.top = `${box.y}px`;
  if (box.w != null) panel.style.width = `${box.w}px`;
  if (box.h != null) panel.style.height = `${box.h}px`;
  panel.style.zIndex = String(box.z);
}

/** 清除 inline 位置/尺寸（退出 free 模式或 reset 单个 panel 时）。 */
function clearBox(panel: HTMLElement) {
  panel.style.removeProperty("left");
  panel.style.removeProperty("top");
  panel.style.removeProperty("width");
  panel.style.removeProperty("height");
  panel.style.removeProperty("z-index");
  panel.style.removeProperty("transform");
}

export function FreePanelLayer() {
  // store actions 在 effect 内通过 getState 调用，避免 hook 订阅触发无谓重渲染
  useEffect(() => {
    if (typeof document === "undefined") return;

    let dragging: {
      panel: HTMLElement;
      key: string;
      startX: number;
      startY: number;
      origX: number;
      origY: number;
    } | null = null;

    const resizeObservers = new WeakMap<HTMLElement, ResizeObserver>();

    function isFree(): boolean {
      return document.body.dataset.freePanels === "true";
    }

    /** 扫描 + wire：为每个 .rpt-panel 加 data-panel-id + .rpt-panel--free 类 + 回填 box。 */
    function wireAll() {
      const panels = document.querySelectorAll<HTMLElement>(
        ".v-archive--canon[data-agent] .rpt-panel",
      );
      const state = usePanelLayoutStore.getState();
      panels.forEach((panel) => {
        const key = computeKey(panel);
        if (!key) return;
        panel.setAttribute(PANEL_ID_ATTR, key);
        panel.classList.add("rpt-panel--free");
        const box = state.panels[key];
        if (box) applyBox(panel, box);
        // 监听用户手动 resize:both 的 size 变化
        if (!resizeObservers.has(panel)) {
          const ro = new ResizeObserver(() => {
            if (!isFree()) return;
            const k = panel.getAttribute(PANEL_ID_ATTR);
            if (!k) return;
            const w = panel.offsetWidth;
            const h = panel.offsetHeight;
            const prev = usePanelLayoutStore.getState().panels[k];
            // 只在用户改过 size 之后持续记录（首次出现 w/h 等于初始尺寸 · 写入也无害）
            if (!prev || prev.w !== w || prev.h !== h) {
              usePanelLayoutStore.getState().setSize(k, w, h);
            }
          });
          ro.observe(panel);
          resizeObservers.set(panel, ro);
        }
      });
    }

    /** 退出 free 模式：清 inline + 移除 class + 断 ResizeObserver。 */
    function unwireAll() {
      const panels = document.querySelectorAll<HTMLElement>(
        `.rpt-panel[${PANEL_ID_ATTR}]`,
      );
      panels.forEach((panel) => {
        clearBox(panel);
        panel.classList.remove("rpt-panel--free");
        panel.removeAttribute(PANEL_ID_ATTR);
        const ro = resizeObservers.get(panel);
        if (ro) {
          ro.disconnect();
          resizeObservers.delete(panel);
        }
      });
    }

    /** mousedown on .rpt-panel-head → 起拖（忽略 button / .pp-grip / .mp-grip 内）。 */
    function onMouseDown(e: MouseEvent) {
      if (!isFree()) return;
      const target = e.target as HTMLElement;
      if (!target) return;
      // 允许从 head 起拖，但点击 head 内的 button / grip 不拖
      if (target.closest("button, .pp-grip, .mp-grip, input, textarea")) return;
      const head = target.closest<HTMLElement>(".rpt-panel-head");
      if (!head) return;
      const panel = head.closest<HTMLElement>(".rpt-panel");
      if (!panel) return;
      const key = panel.getAttribute(PANEL_ID_ATTR);
      if (!key) return;
      e.preventDefault();
      const rect = panel.getBoundingClientRect();
      const parentRect = panel.offsetParent?.getBoundingClientRect() ?? { left: 0, top: 0 };
      const origX = rect.left - (parentRect as DOMRect).left;
      const origY = rect.top - (parentRect as DOMRect).top;
      dragging = {
        panel,
        key,
        startX: e.clientX,
        startY: e.clientY,
        origX,
        origY,
      };
      // 立即置顶，避免拖到其它 panel 底下
      usePanelLayoutStore.getState().bringToFront(key);
      const z = usePanelLayoutStore.getState().panels[key]?.z ?? 10;
      panel.style.zIndex = String(z);
      document.body.style.userSelect = "none";
    }

    function onMouseMove(e: MouseEvent) {
      if (!dragging) return;
      const dx = e.clientX - dragging.startX;
      const dy = e.clientY - dragging.startY;
      const nx = dragging.origX + dx;
      const ny = dragging.origY + dy;
      dragging.panel.style.left = `${nx}px`;
      dragging.panel.style.top = `${ny}px`;
    }

    function onMouseUp() {
      if (!dragging) return;
      const { panel, key } = dragging;
      const nx = parseFloat(panel.style.left) || 0;
      const ny = parseFloat(panel.style.top) || 0;
      usePanelLayoutStore.getState().setPos(key, nx, ny);
      dragging = null;
      document.body.style.userSelect = "";
    }

    /** 单击 panel 内部（非拖拽）→ 置顶。 */
    function onClick(e: MouseEvent) {
      if (!isFree()) return;
      const target = e.target as HTMLElement;
      const panel = target?.closest<HTMLElement>(".rpt-panel");
      if (!panel) return;
      const key = panel.getAttribute(PANEL_ID_ATTR);
      if (!key) return;
      usePanelLayoutStore.getState().bringToFront(key);
      const z = usePanelLayoutStore.getState().panels[key]?.z ?? 10;
      panel.style.zIndex = String(z);
    }

    /** 双击 head → reset 回网格位（删 store entry + 清 inline style）。 */
    function onDblClick(e: MouseEvent) {
      if (!isFree()) return;
      const target = e.target as HTMLElement;
      // 双击 button/input 仍放行
      if (target.closest("button, .pp-grip, .mp-grip, input, textarea")) return;
      const head = target.closest<HTMLElement>(".rpt-panel-head");
      if (!head) return;
      const panel = head.closest<HTMLElement>(".rpt-panel");
      if (!panel) return;
      const key = panel.getAttribute(PANEL_ID_ATTR);
      if (!key) return;
      usePanelLayoutStore.getState().reset(key);
      clearBox(panel);
    }

    /** 响应 body[data-free-panels] 切换 + children 变化（SPA 路由切换后重扫）。 */
    const bodyObserver = new MutationObserver(() => {
      if (isFree()) wireAll();
      else unwireAll();
    });
    bodyObserver.observe(document.body, {
      attributes: true,
      attributeFilter: ["data-free-panels"],
    });

    // 监听 shell-views 下子树变化（workspace 切换、动态挂载的 panel）
    const stage =
      document.querySelector(".shell-views") || document.body;
    const treeObserver = new MutationObserver(() => {
      if (isFree()) wireAll();
    });
    treeObserver.observe(stage, { childList: true, subtree: true });

    // 初始化
    if (isFree()) wireAll();

    document.addEventListener("mousedown", onMouseDown);
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    document.addEventListener("click", onClick);
    document.addEventListener("dblclick", onDblClick);

    return () => {
      bodyObserver.disconnect();
      treeObserver.disconnect();
      document.removeEventListener("mousedown", onMouseDown);
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
      document.removeEventListener("click", onClick);
      document.removeEventListener("dblclick", onDblClick);
      // 卸载时顺手清空 wire 状态
      unwireAll();
    };
  }, []);

  return null;
}
