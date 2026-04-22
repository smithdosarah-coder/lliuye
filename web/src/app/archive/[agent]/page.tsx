import "../report/report-workspace.css";
import "../channel/channel-workspace.css";
import "../riskctrl/riskctrl-workspace.css";
import "../credit/credit-workspace.css";
import "../alert/alert-workspace.css";
import "../compliance/compliance-workspace.css";
import { notFound } from "next/navigation";
import type { ComponentType } from "react";
import type { AgentKey } from "@/lib/agents";
import { ReportWorkspace as ReportCanon } from "../report/_components/ReportWorkspace";
import ChannelCanon from "../channel/_components/ChannelWorkspace";
import RiskctrlCanon from "../riskctrl/_components/RiskctrlWorkspace";
import CreditCanon from "../credit/_components/CreditWorkspace";
import AlertCanon from "../alert/_components/AlertWorkspace";
import ComplianceCanon from "../compliance/_components/ComplianceWorkspace";
import { RbacGuard } from "./RbacGuard";

export const metadata = {
  title: "AI 助手 · 工作区 · 乾策 Studio",
};

const VALID: AgentKey[] = ["report", "channel", "credit", "riskctrl", "alert", "compliance"];

const WORKSPACES: Record<AgentKey, ComponentType> = {
  report: ReportCanon,
  channel: ChannelCanon,
  riskctrl: RiskctrlCanon,
  credit: CreditCanon,
  alert: AlertCanon,
  compliance: ComplianceCanon,
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

  return (
    <div
      className="v-archive v-archive--canon px-6 py-6 max-w-[1720px] mx-auto"
      data-agent={key}
    >
      <RbacGuard agent={key}>
        <Workspace />
      </RbacGuard>
    </div>
  );
}

export function generateStaticParams() {
  return VALID.map((agent) => ({ agent }));
}
