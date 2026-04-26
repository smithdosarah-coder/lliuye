"use client";

/**
 * Whiteboard · 左侧白板 pinboard
 *
 * 与 Desk 抽屉并列，不复用其 hover-from-edge 触发机制（避免 22px 冲突）。
 * 唯一触发方式：
 *   1. 右下角 FAB（tiny 📌 button）点击
 *   2. 键盘 ⌘/Ctrl + B
 *
 * 拖拽协议：
 *   - 接收 MIME `application/x-card-pin`（见 whiteboard-store CARD_PIN_MIME）
 *   - 源头：archive agent tile / warroom ticket card
 *   - drop 时反序列化 payload → store.pin(payload)
 *
 * z-index：
 *   - panel: 44（Desk.drawer=45 上方可能打架 → 放低一级，让 Desk 永远压白板）
 *   - FAB: 42（ThemeSwitch 40 之上）
 *
 * mockup 对齐：没有 mockup 直接参照（白板是附加功能），视觉语言沿用 Desk
 *   的 `.dr-panel` 渐变 + backdrop-filter + var(--r-lg) 圆角，保持 shell v2
 *   风格一致。
 */

import Link from "next/link";
import { useEffect, type CSSProperties, type DragEvent } from "react";
import {
  CARD_PIN_MIME,
  useWhiteboardStore,
  type CardPinPayload,
  type WhiteboardPin,
} from "@/lib/store/whiteboard-store";
import {
  PANEL_PIN_MIME,
  type PanelPinPayload,
} from "@/lib/store/panel-canvas-store";

const KIND_LABEL: Record<WhiteboardPin["kind"], string> = {
  agent: "助手",
  ticket: "工单",
  customer: "客户",
};

const KIND_GLYPH: Record<WhiteboardPin["kind"], string> = {
  agent: "◇",
  ticket: "▤",
  customer: "○",
};

export function Whiteboard() {
  const pins = useWhiteboardStore((s) => s.pins);
  const open = useWhiteboardStore((s) => s.open);
  const setOpen = useWhiteboardStore((s) => s.setOpen);
  const toggle = useWhiteboardStore((s) => s.toggle);
  const pin = useWhiteboardStore((s) => s.pin);
  const unpin = useWhiteboardStore((s) => s.unpin);

  // Sync open → body dataset，让 main content（.shell-views）按需让位。
  // 与 Desk 的 data-desk-pinned 同模式，不冲突（两者独立 CSS selector）。
  useEffect(() => {
    if (typeof document === "undefined") return;
    if (open) {
      document.body.dataset.whiteboardOpen = "true";
    } else {
      delete document.body.dataset.whiteboardOpen;
    }
    return () => {
      delete document.body.dataset.whiteboardOpen;
    };
  }, [open]);

  // ⌘/Ctrl + B → toggle。Esc → 关闭（仅当当前打开时避免误伤其他 Esc 逻辑）。
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "b") {
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

  function hasAnyPin(e: DragEvent<HTMLElement>): boolean {
    const ts = Array.from(e.dataTransfer.types);
    return ts.includes(CARD_PIN_MIME) || ts.includes(PANEL_PIN_MIME);
  }

  function onDragOver(e: DragEvent<HTMLElement>) {
    if (!hasAnyPin(e)) return;
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = "copy";
  }

  /** 把 PANEL_PIN payload 兼容映射到 CARD 形状（白板统一字符条渲染）。 */
  function panelToCard(p: PanelPinPayload): CardPinPayload {
    return {
      id: `panel:${p.id}`,
      kind: "ticket",
      title: p.title,
      subtitle: p.subtitle ?? p.blurb ?? "面板",
      href: p.href ?? "#",
      accentVar: p.accentVar,
    };
  }

  function onDrop(e: DragEvent<HTMLElement>) {
    // 优先 CARD_PIN（已经是白板语义）；兜底 PANEL_PIN（双保险：
    // 即使 PanelPinHandle 没双写，Whiteboard 自己也能接）
    const cardRaw = e.dataTransfer.getData(CARD_PIN_MIME);
    const panelRaw = e.dataTransfer.getData(PANEL_PIN_MIME);
    if (!cardRaw && !panelRaw) return;
    e.preventDefault();
    e.stopPropagation();
    try {
      let data: CardPinPayload | null = null;
      if (cardRaw) {
        data = JSON.parse(cardRaw) as CardPinPayload;
      } else if (panelRaw) {
        const panelData = JSON.parse(panelRaw) as PanelPinPayload;
        if (!panelData?.id || !panelData?.title) return;
        data = panelToCard(panelData);
      }
      if (!data?.id || !data?.href) return;
      pin(data);
      // 用户刚拖过来：自动展开白板让 ta 看见
      if (!open) setOpen(true);
    } catch {
      /* malformed payload, ignore */
    }
  }

  const cls = ["wb", open ? "open" : ""].filter(Boolean).join(" ");

  return (
    <>
      {/* FAB 已移除（2026-04-22 · 用户 UI bug#1）——触发仅 ⌘B 或 drop-to-edge。
          pins 计数不再暴露入口，交由 aside 打开后自身展示。 */}
      <aside
        className={cls}
        aria-label="白板"
        aria-hidden={!open}
        onDragOver={onDragOver}
        onDrop={onDrop}
      >
        <div className="wb-panel" role="region">
          <div className="wb-head">
            <span className="t">
              <span className="cn">白板</span>
              <em>Pinboard.</em>
            </span>
            <button
              type="button"
              className="wb-close"
              onClick={() => setOpen(false)}
              aria-label="关闭白板"
              title="关闭 (Esc)"
            >
              ×
            </button>
          </div>

          <div className="wb-body">
            {pins.length === 0 ? (
              <div className="wb-empty">
                <div className="wb-empty-ic" aria-hidden>
                  ⌀
                </div>
                <div className="wb-empty-cn">拖拽功能卡到这里</div>
                <div className="wb-empty-sub">保留在你的桌面</div>
              </div>
            ) : (
              <ul className="wb-list">
                {pins.map((p) => {
                  const style: CSSProperties = p.accentVar
                    ? ({ "--wb-pin-accent": `var(${p.accentVar})` } as CSSProperties)
                    : {};
                  return (
                    <li key={p.id} className="wb-pin" style={style} data-kind={p.kind}>
                      <Link href={p.href} className="wb-pin-main">
                        <span className="wb-pin-rail" aria-hidden />
                        <span className="wb-pin-ic" aria-hidden>
                          {KIND_GLYPH[p.kind]}
                        </span>
                        <span className="wb-pin-txt">
                          <span className="wb-pin-title">{p.title}</span>
                          <span className="wb-pin-sub">{p.subtitle}</span>
                        </span>
                        <span className="wb-pin-kind">{KIND_LABEL[p.kind]}</span>
                      </Link>
                      <button
                        type="button"
                        className="wb-pin-x"
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

          <div className="wb-foot">
            <span className="wb-foot-n">
              已固定 <em>{pins.length}</em>
            </span>
            <span className="wb-foot-hint">⌘B 开合</span>
          </div>
        </div>
      </aside>
    </>
  );
}
