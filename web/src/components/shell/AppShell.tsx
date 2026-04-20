"use client";

import { useRouter } from "next/navigation";
import { useRef, useState, type DragEvent, type ReactNode } from "react";
import { CustomerDrawer } from "./CustomerDrawer";
import { Desk } from "./Desk";
import { Masthead } from "./Masthead";
import { ThemeSwitch } from "./ThemeSwitch";

const DESK_MIME = "application/x-desk-row";

type DropPayload = { name: string; href: string };

export function AppShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [dropHover, setDropHover] = useState<string | null>(null);
  // depth counter prevents flicker from child dragenter/leave fired on every nested node
  const depth = useRef(0);

  function hasDeskPayload(e: DragEvent<HTMLElement>): boolean {
    return Array.from(e.dataTransfer.types).includes(DESK_MIME);
  }

  function onDragEnter(e: DragEvent<HTMLElement>) {
    if (!hasDeskPayload(e)) return;
    e.preventDefault();
    depth.current += 1;
    if (!dropHover) {
      // best-effort read of the dragged row's name (text/plain fallback set in Desk)
      const name = e.dataTransfer.getData("text/plain") || "该客户";
      setDropHover(name);
    }
  }

  function onDragOver(e: DragEvent<HTMLElement>) {
    if (!hasDeskPayload(e)) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  }

  function onDragLeave(e: DragEvent<HTMLElement>) {
    if (!hasDeskPayload(e)) return;
    depth.current = Math.max(0, depth.current - 1);
    if (depth.current === 0) setDropHover(null);
  }

  function onDrop(e: DragEvent<HTMLElement>) {
    const raw = e.dataTransfer.getData(DESK_MIME);
    if (!raw) return;
    e.preventDefault();
    depth.current = 0;
    setDropHover(null);
    try {
      const data = JSON.parse(raw) as DropPayload;
      if (data?.href) router.push(data.href);
    } catch {
      /* ignore malformed payloads */
    }
  }

  return (
    <div className="shell-root">
      <Desk />
      <main className="shell-stage">
        <Masthead />
        <section
          className={`shell-views${dropHover ? " drop-hover" : ""}`}
          onDragEnter={onDragEnter}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          data-drop-name={dropHover ?? undefined}
        >
          {children}
        </section>
      </main>
      <ThemeSwitch />
      <CustomerDrawer />
    </div>
  );
}
