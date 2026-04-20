import { notFound } from "next/navigation";
import type { ComponentType } from "react";
import { AGENTS, type AgentKey } from "@/lib/agents";
import ReportWorkspace from "@/components/workspace/ReportWorkspace";
import ChannelWorkspace from "@/components/workspace/ChannelWorkspace";
import CreditWorkspace from "@/components/workspace/CreditWorkspace";
import RiskctrlWorkspace from "@/components/workspace/RiskctrlWorkspace";
import AlertWorkspace from "@/components/workspace/AlertWorkspace";
import ComplianceWorkspace from "@/components/workspace/ComplianceWorkspace";
import { ArchiveAgentShell } from "./ArchiveAgentShell";

export const metadata = {
  title: "AI 助手 · 工作区 · 乾策 Studio",
};

const VALID: AgentKey[] = ["report", "channel", "credit", "riskctrl", "alert", "compliance"];

const WORKSPACES: Record<AgentKey, ComponentType> = {
  report: ReportWorkspace,
  channel: ChannelWorkspace,
  credit: CreditWorkspace,
  riskctrl: RiskctrlWorkspace,
  alert: AlertWorkspace,
  compliance: ComplianceWorkspace,
};

export default async function AgentWorkspace({
  params,
}: {
  params: Promise<{ agent: string }>;
}) {
  const { agent } = await params;
  const key = agent as AgentKey;
  const Workspace = WORKSPACES[key];
  if (!Workspace) {
    console.warn("[archive] unknown agent:", JSON.stringify(agent), "valid:", VALID);
    notFound();
  }
  const def = AGENTS.find((a) => a.key === key)!;

  return (
    <div
      className="v-archive ws-v2-skin px-8 py-8 max-w-[1400px] mx-auto"
      data-agent={key}
    >
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
