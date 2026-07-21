"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { AuditEntry } from "./AuditEntry";
import { CanvasModeToggle } from "./CanvasModeToggle";
import { LogoutButton } from "./LogoutButton";
import { PersonaSwitcher } from "./PersonaSwitcher";

type Tab = {
  href: string;
  cn: string;
  match: (pathname: string) => boolean;
};

const TABS: Tab[] = [
  { href: "/today",    cn: "今日",     match: (p) => p === "/" || p.startsWith("/today") },
  { href: "/dispatch", cn: "对话",     match: (p) => p.startsWith("/dispatch") },
  { href: "/archive",  cn: "AI 助手",  match: (p) => p.startsWith("/archive") || ["/credit","/channel","/alert","/compliance","/report","/riskctrl"].some((r) => p.startsWith(r)) },
  { href: "/warroom",  cn: "任务",     match: (p) => p.startsWith("/warroom") },
];

export function Masthead() {
  const pathname = usePathname() || "/";
  const [time, setTime] = useState<string>("");

  useEffect(() => {
    function tick() {
      const d = new Date();
      const hh = String(d.getHours()).padStart(2, "0");
      const mm = String(d.getMinutes()).padStart(2, "0");
      setTime(`${hh}:${mm}`);
    }
    tick();
    const id = setInterval(tick, 20000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="shell-bar">
      <Link href="/today" className="shell-logo">
        <span className="cn">乾策</span>
        <sup>®</sup>
        <em>Studio</em>
      </Link>
      <nav className="shell-tabs">
        {TABS.map((t) => (
          <Link
            key={t.href}
            href={t.href}
            className={t.match(pathname) ? "on" : undefined}
          >
            <span className="cn">{t.cn}</span>
          </Link>
        ))}
      </nav>
      <div className="shell-op">
        <CanvasModeToggle />
        <AuditEntry />
        <PersonaSwitcher />
        <LogoutButton />
        <span className="time">{time || "--:--"}</span>
      </div>
    </header>
  );
}
