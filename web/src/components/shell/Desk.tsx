"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { DESK_QUICK_CREATE, DESK_SECTIONS } from "@/lib/mock/desk";

export function Desk() {
  const [open, setOpen] = useState(false);
  const [pinned, setPinned] = useState(false);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const moveThrottle = useRef<number>(0);
  const searchRef = useRef<HTMLInputElement | null>(null);

  // Sync pin state -> body dataset so main content can reserve space via CSS.
  // Stays in sync with Esc-unpin and togglePin in one place.
  useEffect(() => {
    if (typeof document === "undefined") return;
    if (pinned) {
      document.body.dataset.deskPinned = "true";
    } else {
      delete document.body.dataset.deskPinned;
    }
    return () => {
      delete document.body.dataset.deskPinned;
    };
  }, [pinned]);

  useEffect(() => {
    function onMove(e: MouseEvent) {
      if (pinned) return;
      // throttle to ~60fps (16ms) — mousemove fires per-pixel on some OSes
      const now = performance.now();
      if (now - moveThrottle.current < 16) return;
      moveThrottle.current = now;

      if (e.clientX < 22) {
        if (closeTimer.current) clearTimeout(closeTimer.current);
        setOpen(true);
      } else if (open && e.clientX > 360) {
        if (closeTimer.current) clearTimeout(closeTimer.current);
        closeTimer.current = setTimeout(() => setOpen(false), 180);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
        setPinned(false);
        return;
      }
      // ⌘K / Ctrl+K → 展开 drawer 并聚焦搜索
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(true);
        // wait for drawer transform transition-ready frame
        requestAnimationFrame(() => searchRef.current?.focus());
      }
    }
    document.addEventListener("mousemove", onMove);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("keydown", onKey);
      if (closeTimer.current) clearTimeout(closeTimer.current);
    };
  }, [open, pinned]);

  function togglePin() {
    setPinned((p) => !p);
    setOpen(true);
  }

  const cls = ["drawer", open ? "open" : "", pinned ? "pin" : ""].filter(Boolean).join(" ");

  return (
    <aside className={cls} aria-label="工作台 Desk">
      <div className="dr-hint" />
      <div className="dr-panel" role="region">
        <div className="dr-head">
          <span className="t">
            <span className="cn">工作台</span>
            <em>Desk.</em>
          </span>
          <button className="dr-pin" onClick={togglePin} title={pinned ? "解钉" : "钉住"} aria-pressed={pinned}>
            ◆
          </button>
        </div>

        <div className="dr-search">
          <input ref={searchRef} placeholder="搜客户 / 卷宗 / 政策 / 对话" />
          <kbd>⌘K</kbd>
        </div>

        {DESK_SECTIONS.map((sec) => (
          <div className="dr-sec" key={sec.title}>
            <div className="hd">
              <span>{sec.title}</span>
              <em>{sec.meta}</em>
            </div>
            {sec.rows.map((r) => (
              <Link
                key={`${sec.title}-${r.nm}`}
                href={r.href}
                className="dr-row"
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.effectAllowed = "copy";
                  e.dataTransfer.setData(
                    "application/x-desk-row",
                    JSON.stringify({ name: r.nm, href: r.href }),
                  );
                  // plain-text fallback for other drop targets / copy-into-text
                  e.dataTransfer.setData("text/plain", r.nm);
                }}
              >
                <span className={`ic${r.icClass ? ` ${r.icClass}` : ""}`}>{r.ic}</span>
                <span className="nm-wrap">
                  <span className="nm">{r.nm}</span>
                  <span className="sub">{r.sub}</span>
                </span>
                <span className="ts">{r.ts}</span>
              </Link>
            ))}
            {sec.more && (
              <span className="dr-more">
                {sec.more.label} {sec.more.count && <span className="a">{sec.more.count}</span>} <span className="a">↘</span>
              </span>
            )}
          </div>
        ))}

        <div className="dr-sec">
          <div className="hd">
            <span>新建</span>
            <em>CREATE</em>
          </div>
          <div className="dr-qc">
            {DESK_QUICK_CREATE.map((q) => (
              <Link key={q.label} href={q.href}>
                <button type="button">
                  <span className="plus">+</span>
                  {q.label}
                </button>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}
