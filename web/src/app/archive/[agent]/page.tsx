import dynamic from "next/dynamic";
import { notFound } from "next/navigation";
import type { ComponentType } from "react";
import { AGENTS, type AgentKey } from "@/lib/agents";

export const metadata = {
  title: "AI 助手 · 工作区 · 乾策 Studio",
};

const VALID: AgentKey[] = ["report", "channel", "credit", "riskctrl", "alert", "compliance"];

// v2 workspaces (mockup-v2 DOM-aligned) render their own eyebrow / hero /
// agent-bar / ap card, so no ArchiveAgentShell wrapper — page just loads the
// dynamic per-agent component under .v-archive.
const WORKSPACES: Record<AgentKey, ComponentType> = {
  report:     dynamic(() => import("@/components/workspace/v2/ReportV2")),
  channel:    dynamic(() => import("@/components/workspace/v2/ChannelV2")),
  credit:     dynamic(() => import("@/components/workspace/v2/CreditV2")),
  riskctrl:   dynamic(() => import("@/components/workspace/v2/RiskctrlV2")),
  alert:      dynamic(() => import("@/components/workspace/v2/AlertV2")),
  compliance: dynamic(() => import("@/components/workspace/v2/CompliV2")),
};

export default async function AgentWorkspace({
  params,
}: {
  params: Promise<{ agent: string }>;
}) {
  const { agent } = await params;
  if (!VALID.includes(agent as AgentKey)) notFound();
  const key = agent as AgentKey;
  // validate mapping presence (keeps AGENTS import wired for future tile routing)
  void AGENTS.find((a) => a.key === key);
  const Workspace = WORKSPACES[key];

  return (
    <div className="v-archive">
      <Workspace />
    </div>
  );
}

export function generateStaticParams() {
  return VALID.map((agent) => ({ agent }));
}
