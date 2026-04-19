import Link from "next/link";
import { Fragment, type CSSProperties } from "react";
import type { ArchiveTile } from "@/lib/mock/archive";

/** .agent tile · mockup L3284-3349 · 点击跳 /archive/<key> workspace */
export function AgentTile({ tile }: { tile: ArchiveTile }) {
  const cls = tile.variant ? `agent ${tile.variant}` : "agent";
  return (
    <Link
      href={`/archive/${tile.key}`}
      className={cls}
      style={{ "--tile-accent": tile.accent } as CSSProperties}
    >
      <div className="ix">{tile.ix}</div>
      <h4>
        <span className="cn">{tile.cn}</span>
        <em>{tile.em}</em>
      </h4>
      <div className="circle">{tile.circle}</div>
      <div className="blurb">
        {tile.blurb.map((s, i) =>
          s.em ? <em key={i}>{s.text}</em> : <Fragment key={i}>{s.text}</Fragment>,
        )}
      </div>
      <div className="foot">
        <div className="stat">
          {tile.statLabel}
          <span className="num">{tile.statNum}</span>
        </div>
        <span className="open">
          打开 <span>↘</span>
        </span>
      </div>
    </Link>
  );
}
