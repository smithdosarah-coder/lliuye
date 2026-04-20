import { notFound } from "next/navigation";
import type { ComponentType } from "react";
import { AGENTS, type AgentKey } from "@/lib/agents";
import ReportV2 from "@/components/workspace/v2/ReportV2";
import ChannelV2 from "@/components/workspace/v2/ChannelV2";
import CreditV2 from "@/components/workspace/v2/CreditV2";
import RiskctrlV2 from "@/components/workspace/v2/RiskctrlV2";
import AlertV2 from "@/components/workspace/v2/AlertV2";
import CompliV2 from "@/components/workspace/v2/CompliV2";

export const metadata = {
  title: "AI 助手 · 工作区 · 乾策 Studio",
};

const VALID: AgentKey[] = ["report", "channel", "credit", "riskctrl", "alert", "compliance"];

const WORKSPACES: Record<AgentKey, ComponentType> = {
  report: ReportV2,
  channel: ChannelV2,
  credit: CreditV2,
  riskctrl: RiskctrlV2,
  alert: AlertV2,
  compliance: CompliV2,
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
  void AGENTS.find((a) => a.key === key);

  return (
    <div className="v-archive">
      <Workspace />
    </div>
  );
}

export function generateStaticParams() {
  return VALID.map((agent) => ({ agent }));
}
