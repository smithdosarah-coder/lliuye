import Link from "next/link";
import { notFound } from "next/navigation";
import { AGENTS, type AgentKey } from "@/lib/agents";

export const metadata = {
  title: "AI 助手 · 工作区 · 乾策 Studio",
};

const VALID: AgentKey[] = ["report", "channel", "credit", "riskctrl", "alert", "compliance"];

export default async function AgentWorkspace({
  params,
}: {
  params: Promise<{ agent: string }>;
}) {
  const { agent } = await params;
  if (!VALID.includes(agent as AgentKey)) notFound();
  const def = AGENTS.find((a) => a.key === agent)!;

  return (
    <div className="v-archive">
      <div className="eyebrow" style={{
        display: "flex", alignItems: "center", gap: 18,
        fontFamily: "var(--mono)", fontSize: 11, letterSpacing: ".16em",
        textTransform: "uppercase", color: "var(--ink-65)", marginTop: 10,
      }}>
        <span style={{ width: 32, height: 1, background: "var(--ink-28)" }} />
        {def.code} · {def.key.toUpperCase()}
        <Link href="/archive" style={{ marginLeft: "auto", color: "var(--accent)", textDecoration: "none" }}>
          ← 返回助手目录
        </Link>
      </div>

      <h1 className="archive-h" style={{ marginTop: 12 }}>
        <span style={{ fontFamily: "var(--cjk)", fontWeight: 700 }}>{def.title}</span>
      </h1>
      <p className="archive-lede">{def.tagline}</p>

      <div
        className="v-tile"
        style={{
          marginTop: 12,
          padding: "32px 28px",
          textAlign: "center",
          fontFamily: "var(--cjk)",
          color: "var(--ink-65)",
          fontSize: 14,
          lineHeight: 1.6,
        }}
      >
        <div style={{
          fontFamily: "var(--mono)", fontSize: 10.5, letterSpacing: ".18em",
          color: "var(--ink-48)", textTransform: "uppercase", marginBottom: 12,
        }}>
          STAGE 2 · WORKSPACE PLACEHOLDER
        </div>
        Stage 3 将把现有 <code style={{
          fontFamily: "var(--mono)", background: "var(--ink-08)",
          padding: "1px 7px", borderRadius: 4,
        }}>{def.path}</code> 页面内容迁入此 workspace。
        <div style={{ marginTop: 14 }}>
          当前阶段：路由可达，业务组件等 Stage 3 接入。
        </div>
      </div>
    </div>
  );
}

export function generateStaticParams() {
  return VALID.map((agent) => ({ agent }));
}
