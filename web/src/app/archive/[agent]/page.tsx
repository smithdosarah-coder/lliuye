import dynamic from "next/dynamic";
import { notFound } from "next/navigation";
import type { ComponentType } from "react";
import { AGENTS, type AgentKey } from "@/lib/agents";
import { ArchiveAgentShell } from "./ArchiveAgentShell";

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
      <ArchiveAgentShell
        code={def.code}
        eyebrowLabel={def.eyebrowLabel}
        title={def.title}
        description={def.description}
      >
        <Workspace />
      </ArchiveAgentShell>
    </div>
  );
}

export function generateStaticParams() {
  return VALID.map((agent) => ({ agent }));
}
