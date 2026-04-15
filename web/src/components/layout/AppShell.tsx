"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AGENTS, findAgentByPath } from "@/lib/agents";
import { cn } from "@/lib/utils";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const activeAgent = findAgentByPath(pathname);

  return (
    <div className="flex min-h-screen">
      <Sidebar pathname={pathname} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar activeCode={activeAgent?.code} activeTitle={activeAgent?.title} />
        <main className="flex-1 overflow-y-auto">{children}</main>
        <footer className="border-t border-[var(--color-line)] px-8 py-4 text-[11px] text-[var(--color-ink-muted)] font-tabular tracking-wider">
          <div className="flex justify-between items-center">
            <span>ZHONGAN CREDIT AI · X-NEXUS · v2.0 DEMO</span>
            <span>{new Date().getFullYear()}</span>
          </div>
        </footer>
      </div>
    </div>
  );
}

function Sidebar({ pathname }: { pathname: string }) {
  return (
    <aside className="w-[260px] shrink-0 border-r border-[var(--color-line)] bg-[var(--color-paper-raised)] flex flex-col">
      <Link href="/" className="px-6 pt-8 pb-6 border-b border-[var(--color-line)] block">
        <div className="font-display text-[11px] tracking-[0.3em] text-[var(--color-brass)] uppercase">
          众安信科 · X-NEXUS
        </div>
        <div className="mt-2 font-display text-[26px] leading-none text-[var(--color-ink)]">
          乾策
        </div>
        <div className="mt-1 text-[13px] text-[var(--color-ink-muted)]">
          信贷 AI 智能体矩阵
        </div>
      </Link>

      <nav className="flex-1 px-3 py-4 space-y-0.5">
        <NavHeading>智能体 · 6</NavHeading>
        {AGENTS.map((agent) => {
          const Icon = agent.icon;
          const active = pathname === agent.path || pathname.startsWith(agent.path + "/");
          return (
            <Link
              key={agent.key}
              href={agent.path}
              className={cn(
                "group relative flex items-start gap-3 rounded-md px-3 py-2.5 transition-all",
                active
                  ? "bg-[var(--color-ink)] text-[var(--color-paper)]"
                  : "text-[var(--color-ink-soft)] hover:bg-[var(--color-overlay)]"
              )}
            >
              <span
                className="absolute left-0 top-2 bottom-2 w-[2px] rounded-full transition-all"
                style={{
                  background: active ? agent.accent : "transparent",
                }}
              />
              <Icon
                size={16}
                className={cn(
                  "mt-0.5 shrink-0 transition-colors",
                  active ? "text-[var(--color-brass-glow)]" : "text-[var(--color-ink-muted)]"
                )}
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline gap-2">
                  <span className="font-tabular text-[10px] tracking-wider opacity-60">
                    {agent.code}
                  </span>
                  <span className="font-display text-[14px] leading-tight truncate">
                    {agent.title}
                  </span>
                </div>
                <div
                  className={cn(
                    "text-[11px] mt-0.5 truncate",
                    active ? "text-[var(--color-paper)]/60" : "text-[var(--color-ink-muted)]"
                  )}
                >
                  {agent.tagline}
                </div>
              </div>
            </Link>
          );
        })}
      </nav>

      <div className="px-6 py-4 border-t border-[var(--color-line)]">
        <div className="text-[10px] font-tabular tracking-[0.2em] text-[var(--color-ink-muted)] uppercase">
          SESSION
        </div>
        <div className="mt-1 text-[12px] text-[var(--color-ink-soft)]">
          Demo · 本地运行
        </div>
      </div>
    </aside>
  );
}

function NavHeading({ children }: { children: React.ReactNode }) {
  return (
    <div className="px-3 pt-2 pb-1.5 text-[10px] font-tabular tracking-[0.25em] text-[var(--color-ink-muted)] uppercase">
      {children}
    </div>
  );
}

function TopBar({
  activeCode,
  activeTitle,
}: {
  activeCode?: string;
  activeTitle?: string;
}) {
  return (
    <header className="h-14 border-b border-[var(--color-line)] px-8 flex items-center justify-between bg-[var(--color-paper-raised)]/70 backdrop-blur-sm">
      <div className="flex items-center gap-4">
        {activeCode ? (
          <>
            <span className="font-tabular text-[11px] tracking-wider text-[var(--color-brass)]">
              / {activeCode}
            </span>
            <span className="font-display text-[15px] text-[var(--color-ink)]">
              {activeTitle}
            </span>
          </>
        ) : (
          <span className="font-display text-[15px] text-[var(--color-ink)]">
            工作台
          </span>
        )}
      </div>
      <div className="flex items-center gap-6 text-[11px] font-tabular tracking-wider text-[var(--color-ink-muted)]">
        <span className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-sage)] animate-ink-pulse" />
          API · READY
        </span>
        <span>DEMO MODE</span>
      </div>
    </header>
  );
}
