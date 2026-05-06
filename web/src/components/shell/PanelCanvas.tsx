"use client";

/**
 * PanelCanvas · 右侧画布
 *
 * 用户明指「气泡支持拖拽钉选到右侧画布中以缩略图呈现」。与左侧 Whiteboard
 * 语义互补：白板钉 entity（agent/ticket/customer · 文本列），画布钉 panel
 * 本身（气泡快照 · 缩略图网格）。
 *
 * 触发方式：
 *   1. 右侧 FAB（右下角，位于 ThemeSwitch 正上方）
 *   2. 键盘 ⌘/Ctrl + Shift + K
 *
 * 拖拽协议：
 *   - 接收 MIME `application/x-panel-pin`（PANEL_PIN_MIME）
 *   - 源头：任意 `.rpt-panel`（P4 给它加 draggable + dragstart）
 *   - drop 时反序列化 → store.pin(payload) + 自动展开面板
 *
 * z-index 约定：
 *   - panel: 44（与 Whiteboard 同层；左右不互打架）
 *   - FAB: 42（ThemeSwitch=40 之上）
 *
 * 视觉语言：沿用 shell v2 气泡（chalk/g0b 渐变 + blur + --r-lg），右侧滑入。
 */

import Link from "next/link";
import { useEffect, type CSSProperties, type DragEvent } from "react";
import { usePathname } from "next/navigation";
import { agentLabel } from "@/lib/agent-labels";
import {
  PANEL_PIN_MIME,
  usePanelCanvasStore,
  type PanelPinPayload,
} from "@/lib/store/panel-canvas-store";

export function PanelCanvas() {
  /* PM 5/7 反馈"画布按钮没修复" · pc-fab 仅 /archive/ 路径显 (其他 page pin 来源不足 button 无意义) */
  const pathname = usePathname() || "/";
  const showFab = pathname.startsWith("/archive/");

  const pins = usePanelCanvasStore((s) => s.pins);
  const open = usePanelCanvasStore((s) => s.open);
  const setOpen = usePanelCanvasStore((s) => s.setOpen);
  const toggle = usePanelCanvasStore((s) => s.toggle);
  const pin = usePanelCanvasStore((s) => s.pin);
  const unpin = usePanelCanvasStore((s) => s.unpin);

  // body[data-panel-canvas-open] → 让 .shell-views 加右 padding 让位，避免画布
  // 覆盖主内容；与 whiteboard 左 padding 是独立 selector，可同开。
  useEffect(() => {
    if (typeof document === "undefined") return;
    if (open) {
      document.body.dataset.panelCanvasOpen = "true";
    } else {
      delete document.body.dataset.panelCanvasOpen;
    }
    return () => {
      delete document.body.dataset.panelCanvasOpen;
    };
  }, [open]);

  // ⌘/Ctrl + Shift + K → toggle（避开 ⌘K 命令面板保留位 + ⌘B 白板）。
  // Esc → 关闭（仅当当前打开时，避免误伤全局 Esc）。
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === "k") {
        e.preventDefault();
        toggle();
        return;
      }
      if (e.key === "Escape" && open) {
        setOpen(false);
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, setOpen, toggle]);

  function hasPanelPin(e: DragEvent<HTMLElement>): boolean {
    return Array.from(e.dataTransfer.types).includes(PANEL_PIN_MIME);
  }

  function onDragOver(e: DragEvent<HTMLElement>) {
    if (!hasPanelPin(e)) return;
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = "copy";
  }

  function onDrop(e: DragEvent<HTMLElement>) {
    const raw = e.dataTransfer.getData(PANEL_PIN_MIME);
    if (!raw) return;
    e.preventDefault();
    e.stopPropagation();
    try {
      const data = JSON.parse(raw) as PanelPinPayload;
      if (!data?.id || !data?.title) return;
      pin(data);
      if (!open) setOpen(true);
    } catch {
      /* malformed payload, ignore */
    }
  }

  const cls = ["pc", open ? "open" : ""].filter(Boolean).join(" ");

  return (
    <>
      {/* Toggle FAB · 右下角，ThemeSwitch（right:38,bottom:38）正上方。
          PM 5/7 反馈: pc-fab 仅 /archive/ 显 · /today / /dispatch / /warroom 等 page pin 来源不足 隐藏避免遮挡 */}
      {showFab && (
      <button
        type="button"
        className="pc-fab"
        onClick={toggle}
        aria-pressed={open}
        aria-label={open ? "收起画布" : "展开画布"}
        title={open ? "收起画布 (⌘⇧K)" : "画布 (⌘⇧K)"}
      >
        <span className="pc-fab-ic" aria-hidden>
          {open ? "▣" : "▢"}
        </span>
        <span className="pc-fab-lbl">画布</span>
        <span className="pc-fab-kbd" aria-hidden>
          ⌘⇧K
        </span>
        {pins.length > 0 ? <span className="pc-fab-count">{pins.length}</span> : null}
      </button>
      )}

      <aside
        className={cls}
        aria-label="画布"
        aria-hidden={!open}
        onDragOver={onDragOver}
        onDrop={onDrop}
      >
        <div className="pc-panel" role="region">
          <div className="pc-head">
            <span className="t">
              <span className="cn">画布</span>
              <em>Canvas.</em>
            </span>
            <button
              type="button"
              className="pc-close"
              onClick={() => setOpen(false)}
              aria-label="关闭画布"
              title="关闭 (Esc)"
            >
              ×
            </button>
          </div>

          <div className="pc-body">
            {pins.length === 0 ? (
              <div className="pc-empty">
                <div className="pc-empty-ic" aria-hidden>
                  ▢
                </div>
                <div className="pc-empty-cn">拖气泡到这里</div>
                <div className="pc-empty-sub">保留它的缩略</div>
              </div>
            ) : (
              <ul className="pc-grid">
                {pins.map((p) => {
                  const style: CSSProperties = p.accentVar
                    ? ({ "--pc-pin-accent": `var(${p.accentVar})` } as CSSProperties)
                    : {};
                  const Card = (
                    <>
                      <span className="pc-thumb-rail" aria-hidden />
                      <span className="pc-thumb-head">
                        <span className="pc-thumb-agent">
                          {agentLabel(p.agentKey)}
                        </span>
                        <span className="pc-thumb-title">{p.title}</span>
                      </span>
                      {p.blurb ? (
                        <span className="pc-thumb-blurb">{p.blurb}</span>
                      ) : (
                        <span className="pc-thumb-blurb muted">（面板快照）</span>
                      )}
                    </>
                  );
                  return (
                    <li key={p.id} className="pc-thumb" style={style}>
                      {p.href ? (
                        <Link href={p.href} className="pc-thumb-main">
                          {Card}
                        </Link>
                      ) : (
                        <div className="pc-thumb-main" role="article">
                          {Card}
                        </div>
                      )}
                      <button
                        type="button"
                        className="pc-thumb-x"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          unpin(p.id);
                        }}
                        aria-label={`取消固定 ${p.title}`}
                        title="取消固定"
                      >
                        ×
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          <div className="pc-foot">
            <span className="pc-foot-n">
              缩略 <em>{pins.length}</em>
            </span>
            <span className="pc-foot-hint">⌘⇧K 开合</span>
          </div>
        </div>
      </aside>
    </>
  );
}
