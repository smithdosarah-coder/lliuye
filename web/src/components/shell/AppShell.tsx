"use client";

import { usePathname, useRouter } from "next/navigation";
import { useRef, useState, type DragEvent, type ReactNode } from "react";
import {
  CARD_PIN_MIME,
  type CardPinPayload,
} from "@/lib/store/whiteboard-store";
import { PANEL_PIN_MIME } from "@/lib/store/panel-canvas-store";
import { AuthGate } from "./AuthGate";
import { CanvasModeToggle } from "./CanvasModeToggle";
import { CustomerContextGateway } from "./CustomerContextGateway";
import { CustomerDrawer } from "./CustomerDrawer";
import { Desk } from "./Desk";
import { FreePanelLayer } from "./FreePanelLayer";
import { Masthead } from "./Masthead";
import { PanelCanvas } from "./PanelCanvas";
import { ThemeSwitch } from "./ThemeSwitch";
import { Whiteboard } from "./Whiteboard";

const DESK_MIME = "application/x-desk-row";

type DropPayload = { name: string; href: string };

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname() || "/";
  const isLogin = pathname === "/login";

  // /login 走裸壳：无 Desk / Masthead / ThemeSwitch / drop target
  if (isLogin) {
    return <AuthGate>{children}</AuthGate>;
  }

  return (
    <AuthGate>
      <ShellChrome>{children}</ShellChrome>
    </AuthGate>
  );
}

function ShellChrome({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [dropHover, setDropHover] = useState<string | null>(null);
  // depth counter prevents flicker from child dragenter/leave fired on every nested node
  const depth = useRef(0);

  function hasDeskPayload(e: DragEvent<HTMLElement>): boolean {
    return Array.from(e.dataTransfer.types).includes(DESK_MIME);
  }

  function hasCardPinPayload(e: DragEvent<HTMLElement>): boolean {
    return Array.from(e.dataTransfer.types).includes(CARD_PIN_MIME);
  }

  function hasPanelPinPayload(e: DragEvent<HTMLElement>): boolean {
    return Array.from(e.dataTransfer.types).includes(PANEL_PIN_MIME);
  }

  function onDragEnter(e: DragEvent<HTMLElement>) {
    // Desk row drop hover label only —— card-pin payload doesn't need the
    // 「释放即可打开 …」hint on shell-views（拖到中央就走 navigate 路径，不提示）
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
    // 接受任一 MIME 都允许 drop（preventDefault 是必要的）
    // panel-pin 路过中央 → 允许 drag（让 ghost 不闪烁），但 onDrop 不消费 —
    // 真正的落点是右侧 PanelCanvas；落在中央属「误操作」，默默 noop。
    if (!hasDeskPayload(e) && !hasCardPinPayload(e) && !hasPanelPinPayload(e)) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  }

  function onDragLeave(e: DragEvent<HTMLElement>) {
    if (!hasDeskPayload(e)) return;
    depth.current = Math.max(0, depth.current - 1);
    if (depth.current === 0) setDropHover(null);
  }

  function onDrop(e: DragEvent<HTMLElement>) {
    // 优先消费 desk row（既有路径不变 · 拖客户行到 views 中心 → 跳客户页）
    const deskRaw = e.dataTransfer.getData(DESK_MIME);
    if (deskRaw) {
      e.preventDefault();
      depth.current = 0;
      setDropHover(null);
      try {
        const data = JSON.parse(deskRaw) as DropPayload;
        if (data?.href) router.push(data.href);
      } catch {
        /* ignore malformed payloads */
      }
      return;
    }
    // 次选：card-pin payload。落在 views 中心而不是白板 →
    // 行为约定：跳到 href（与 desk row 行为一致，符合 "拖到中央 = 打开" 的直觉）
    const pinRaw = e.dataTransfer.getData(CARD_PIN_MIME);
    if (pinRaw) {
      e.preventDefault();
      try {
        const data = JSON.parse(pinRaw) as CardPinPayload;
        if (data?.href) router.push(data.href);
      } catch {
        /* ignore malformed payloads */
      }
    }
  }

  return (
    <div className="shell-root">
      <CustomerContextGateway />
      <Desk />
      <Whiteboard />
      <PanelCanvas />
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
      {/* 2026-04-27 · 右下角只剩主题 pill · CanvasModeToggle (改名"编辑")
          挪到 Masthead 上方 (user 反馈底部 popup overlap + 命名混乱)
          shell-tools 容器保留以维持 ThemeSwitch 浮动定位 */}
      <div className="shell-tools" aria-label="工具栏">
        <ThemeSwitch />
      </div>
      <CustomerDrawer />
      <FreePanelLayer />
    </div>
  );
}
