import Link from "next/link";
import { AGENTS } from "@/lib/agents";
import { ArrowUpRight } from "lucide-react";

export default function HomePage() {
  return (
    <div className="px-8 py-10 max-w-[1200px] mx-auto">
      {/* Editorial masthead */}
      <section className="border-b-2 border-[var(--color-ink)] pb-10 mb-10 relative">
        <div className="flex items-center gap-3 text-[11px] font-tabular tracking-[0.3em] text-[var(--color-brass)] uppercase">
          <span className="w-8 h-[1px] bg-[var(--color-brass)]" />
          信贷 AI 智能体矩阵
          <span className="text-[var(--color-ink-muted)]">/ v2.0 DEMO</span>
        </div>
        <h1 className="mt-5 font-display text-[56px] leading-[1.05] tracking-tight text-[var(--color-ink)] max-w-[900px]">
          让每一位客户经理，<br />
          拥有一支 AI 作战参谋。
        </h1>
        <p className="mt-6 text-[15px] text-[var(--color-ink-soft)] max-w-[720px] leading-relaxed">
          覆盖 <strong className="text-[var(--color-ink)]">获客 → 决策 → 贷后</strong> 全周期的 6 个智能体，
          用确定性规则与大模型协同把 60% 的重复劳动压到零。
          数据看板驱动 · 证据链可追溯 · 无编造。
        </p>

        <div className="mt-10 grid grid-cols-4 gap-8">
          {[
            { label: "智能体", value: "6", sub: "覆盖全流程" },
            { label: "决策平均时长", value: "< 30", sub: "秒 / 单" },
            { label: "自动填写率", value: "93%", sub: "Agent6 最新跑" },
            { label: "证据链命中", value: "100%", sub: "无幻觉承诺" },
          ].map((s) => (
            <div key={s.label}>
              <div className="text-[10px] font-tabular tracking-[0.2em] text-[var(--color-ink-muted)] uppercase">
                {s.label}
              </div>
              <div className="mt-2 font-display text-[40px] leading-none text-[var(--color-ink)]">
                {s.value}
              </div>
              <div className="mt-1 text-[11px] text-[var(--color-ink-muted)]">{s.sub}</div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <div className="flex items-baseline justify-between mb-6">
          <h2 className="font-display text-[22px] text-[var(--color-ink)]">智能体目录</h2>
          <span className="text-[11px] font-tabular tracking-[0.2em] text-[var(--color-ink-muted)] uppercase">
            点击进入工作台
          </span>
        </div>

        <div className="grid grid-cols-2 gap-5">
          {AGENTS.map((agent) => {
            const Icon = agent.icon;
            return (
              <Link
                key={agent.key}
                href={agent.path}
                className="group relative bg-[var(--color-paper-raised)] border border-[var(--color-line)] hover:border-[var(--color-ink)] transition-all p-6 overflow-hidden"
              >
                <div
                  className="absolute top-0 left-0 bottom-0 w-[3px] transition-all group-hover:w-[6px]"
                  style={{ background: agent.accent }}
                />
                <div className="pl-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <span className="font-tabular text-[11px] tracking-[0.2em] text-[var(--color-ink-muted)]">
                        {agent.code}
                      </span>
                      <Icon size={16} className="text-[var(--color-ink-soft)]" />
                    </div>
                    <ArrowUpRight
                      size={18}
                      className="text-[var(--color-ink-muted)] group-hover:text-[var(--color-brass)] group-hover:-translate-y-0.5 group-hover:translate-x-0.5 transition-all"
                    />
                  </div>
                  <h3 className="mt-4 font-display text-[22px] text-[var(--color-ink)] leading-tight">
                    {agent.title}
                  </h3>
                  <p className="mt-1.5 text-[13px] text-[var(--color-ink-muted)]">
                    {agent.tagline}
                  </p>
                </div>
              </Link>
            );
          })}
        </div>
      </section>
    </div>
  );
}
