import Link from "next/link";
import { AGENTS } from "@/lib/agents";

export const metadata = {
  title: "AI 助手 · 乾策 Studio",
};

export default function ArchivePage() {
  const sorted = [...AGENTS].sort((a, b) => a.order - b.order);

  return (
    <div className="v-archive">
      <h1 className="archive-h">
        AI 助手 <em>archive</em>
      </h1>
      <p className="archive-lede">
        6 个 Agent 覆盖信贷全流程 · 每个助手独立工作区与历史 · 点击进入详情
      </p>

      <div className="v-tile-grid">
        {sorted.map((a) => (
          <Link key={a.key} href={`/archive/${a.key}`} className="v-tile">
            <div className="v-tile-code">
              {a.code} · {a.key.toUpperCase()}
            </div>
            <div className="v-tile-name">
              <span className="cn">{a.title}</span>
            </div>
            <div className="v-tile-tag">{a.tagline}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
