import Link from "next/link";
import dynamic from "next/dynamic";
import { notFound } from "next/navigation";
import type { ComponentType } from "react";
import { AGENTS, type AgentKey } from "@/lib/agents";

export const metadata = {
  title: "AI 助手 · 工作区 · 乾策 Studio",
};

const VALID: AgentKey[] = ["report", "channel", "credit", "riskctrl", "alert", "compliance"];

const WORKSPACES: Record<AgentKey, ComponentType> = {
  report: dynamic(() => import("@/components/workspace/ReportWorkspace")),
  channel: dynamic(() => import("@/components/workspace/ChannelWorkspace")),
  credit: dynamic(() => import("@/components/workspace/CreditWorkspace")),
  riskctrl: dynamic(() => import("@/components/workspace/RiskctrlWorkspace")),
  alert: dynamic(() => import("@/components/workspace/AlertWorkspace")),
  compliance: dynamic(() => import("@/components/workspace/ComplianceWorkspace")),
};

export default async function AgentWorkspace({
  params,
}: {
  params: Promise<{ agent: string }>;
}) {
  const { agent } = await params;
  if (!VALID.includes(agent as AgentKey)) notFound();
  const key = agent as AgentKey;
  const def = AGENTS.find((a) => a.key === key)!;
  const Workspace = WORKSPACES[key];

  return (
    <div className="v-archive px-8 py-8 max-w-[1400px] mx-auto">
      <div
        className="eyebrow"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 18,
          fontFamily: "var(--mono)",
          fontSize: 11,
          letterSpacing: ".16em",
          textTransform: "uppercase",
          color: "var(--ink-65)",
          marginTop: 10,
        }}
      >
        <span style={{ width: 32, height: 1, background: "var(--ink-28)" }} />
        {def.code} · {def.key.toUpperCase()}
        <Link
          href="/archive"
          style={{ marginLeft: "auto", color: "var(--accent)", textDecoration: "none" }}
        >
          ← 返回助手目录
        </Link>
      </div>

      <h1 className="archive-h" style={{ marginTop: 12 }}>
        <span style={{ fontFamily: "var(--cjk)", fontWeight: 700 }}>{def.title}</span>
      </h1>
      <p className="archive-lede">{def.tagline}</p>

      <div style={{ marginTop: 24 }}>
        <Workspace />
      </div>
    </div>
  );
}

export function generateStaticParams() {
  return VALID.map((agent) => ({ agent }));
}
