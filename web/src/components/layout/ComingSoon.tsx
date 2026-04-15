"use client";

import { AGENTS, type AgentKey } from "@/lib/agents";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";

export function ComingSoon({ agentKey }: { agentKey: AgentKey }) {
  const agent = AGENTS.find((a) => a.key === agentKey);
  if (!agent) return null;
  const Icon = agent.icon;

  return (
    <div className="px-8 py-8 max-w-[1200px] mx-auto">
      <header className="flex items-start justify-between mb-8 pb-6 border-b border-[var(--color-ink)]">
        <div>
          <div className="text-[11px] font-tabular tracking-[0.3em] uppercase" style={{ color: agent.accent }}>
            {agent.code} · {agent.key.toUpperCase()}
          </div>
          <h1 className="mt-2 font-display text-[36px] leading-tight text-[var(--color-ink)]">
            {agent.title}
          </h1>
          <p className="mt-1 text-[13px] text-[var(--color-ink-muted)]">
            {agent.tagline}
          </p>
        </div>
        <Link
          href="/"
          className="flex items-center gap-1.5 text-[11px] font-tabular tracking-[0.2em] uppercase text-[var(--color-ink-muted)] hover:text-[var(--color-ink)]"
        >
          <ArrowLeft size={12} />
          返回目录
        </Link>
      </header>

      <div className="relative border border-[var(--color-line)] bg-[var(--color-paper-raised)] p-16">
        <div
          className="absolute top-0 left-0 bottom-0 w-1"
          style={{ background: agent.accent }}
        />
        <div className="flex items-start gap-8">
          <Icon size={64} className="text-[var(--color-ink-muted)] opacity-40 shrink-0" strokeWidth={1} />
          <div>
            <div className="text-[10px] font-tabular tracking-[0.3em] text-[var(--color-brass)] uppercase">
              WORK IN PROGRESS
            </div>
            <h2 className="mt-3 font-display text-[32px] leading-tight text-[var(--color-ink)]">
              此 Tab 前端正在重做中
            </h2>
            <p className="mt-4 text-[14px] text-[var(--color-ink-soft)] max-w-[560px] leading-relaxed">
              后端业务逻辑已就绪（运行在 FastAPI 上）。
              UI 层会按照授信决策 Tab 相同的设计语言依次铺开。
            </p>
            <div className="mt-8 flex flex-wrap gap-3 text-[11px] font-tabular tracking-wider text-[var(--color-ink-muted)]">
              <span className="px-2.5 py-1 border border-[var(--color-line-strong)]">DESIGN · READY</span>
              <span className="px-2.5 py-1 border border-[var(--color-line-strong)]">BACKEND · READY</span>
              <span className="px-2.5 py-1 bg-[var(--color-ink)] text-[var(--color-paper)]">UI · PENDING</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
