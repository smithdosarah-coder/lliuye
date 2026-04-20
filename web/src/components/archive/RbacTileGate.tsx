"use client";

import { Fragment, type CSSProperties } from "react";
import type { ArchiveTile } from "@/lib/mock/archive";
import { AGENT_KEY_TO_ID } from "@/lib/auth/agent-id";
import { useAuthStore } from "@/lib/store";
import type { Role } from "@/lib/store/types";
import { AgentTile } from "./AgentTile";

const ROLE_LABEL: Record<Role, string> = {
  rm: "客户经理",
  credit_officer: "审贷官",
  compliance_officer: "合规官",
  risk_manager: "风险经理",
  admin: "平台管理员",
};

/**
 * RbacTileGate — archive index 6 tile 的权限包装。
 * 有权 → 渲染 <AgentTile> (原 Link)；无权 → 置灰 div + native tooltip + aria-disabled。
 */
export function RbacTileGate({ tile }: { tile: ArchiveTile }) {
  const can = useAuthStore((s) => s.can);
  const user = useAuthStore((s) => s.currentUser);
  const allowed = can({ kind: "agent.access", agent: AGENT_KEY_TO_ID[tile.key] });
  if (allowed) return <AgentTile tile={tile} />;

  const roleLabel = user ? ROLE_LABEL[user.role] : "当前角色";
  const reason = `${roleLabel}暂无「${tile.cn}」模块权限`;
  const cls = `agent locked${tile.variant ? ` ${tile.variant}` : ""}`;

  return (
    <div
      className={cls}
      style={{ "--tile-accent": tile.accent } as CSSProperties}
      data-locked="true"
      aria-disabled="true"
      title={reason}
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
          权限受限
          <span className="num">—</span>
        </div>
        <span className="open locked">{roleLabel} · ✕</span>
      </div>
    </div>
  );
}
