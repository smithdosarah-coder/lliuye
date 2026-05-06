"use client";

import { RbacTileGate } from "@/components/archive/RbacTileGate";
import { ARCHIVE_TILES, type ArchiveTile } from "@/lib/mock/archive";
import { useAuthStore } from "@/lib/store";
import type { Role } from "@/lib/store/types";

/**
 * ArchiveGrid · Sprint 4 D2 d (Atomic 6) · role-aware tile sort.
 *
 * per Codex R1+R2 双辩论 verdict (D2 d 件 · 轻量做):
 *   - 不重排 ARCHIVE_TILES 默认顺序 (server-side stable)
 *   - 仅 client-side sort: 当前角色高频 tile 前置
 *   - 复用 RbacTileGate 权限 gate · 不破现 RBAC 架构
 *
 * 排序优先级 (per role · 主调 agent 前置):
 *   - rm                  · channel · report · credit · alert · compliance · riskctrl
 *   - credit_officer      · credit · report · alert · channel · compliance · riskctrl
 *   - compliance_officer  · compliance · report · alert · channel · credit · riskctrl
 *   - risk_manager        · riskctrl · alert · credit · channel · report · compliance
 *   - admin               · 默认顺序 (channel · riskctrl · credit · alert · compliance · report)
 */

const ROLE_PRIORITY: Record<Role, string[]> = {
  rm: ["channel", "report", "credit", "alert", "compliance", "riskctrl"],
  credit_officer: ["credit", "report", "alert", "channel", "compliance", "riskctrl"],
  compliance_officer: ["compliance", "report", "alert", "channel", "credit", "riskctrl"],
  risk_manager: ["riskctrl", "alert", "credit", "channel", "report", "compliance"],
  admin: ["channel", "riskctrl", "credit", "alert", "compliance", "report"],
};

function sortByRole(tiles: readonly ArchiveTile[], role: Role): ArchiveTile[] {
  const priority = ROLE_PRIORITY[role] ?? ROLE_PRIORITY.admin;
  const idx = (key: string) => {
    const i = priority.indexOf(key);
    return i === -1 ? 999 : i;
  };
  return [...tiles].sort((a, b) => idx(a.key) - idx(b.key));
}

export function ArchiveGrid() {
  const role: Role = useAuthStore((s) => s.currentUser?.role) ?? "admin";
  const sortedTiles = sortByRole(ARCHIVE_TILES, role);

  return (
    <div className="archive" data-role-sort={role}>
      {sortedTiles.map((t) => (
        <RbacTileGate key={t.key} tile={t} />
      ))}
    </div>
  );
}
