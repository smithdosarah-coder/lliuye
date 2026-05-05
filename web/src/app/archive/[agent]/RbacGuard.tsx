"use client";

import type { ReactNode } from "react";
import { NoPermission } from "@/components/shell/NoPermission";
import type { AgentKey } from "@/lib/agents";
import { AGENT_KEY_TO_ID } from "@/lib/auth/agent-id";
import { useAuthStore } from "@/lib/store";

/**
 * RbacGuard — archive/[agent] 入口权限判定。
 *
 * AuthGate 保证未登录用户不会到达本组件，所以只判 row-level/action gate。
 *
 * Phase B Sprint 3 sub-PR 2 (2026-05-05 · per Q-052 #8):
 *   - 入口判定从 binary `agent.access` 升级到 row-level/action `agent.action: "read"`
 *   - read 是工作区入口最低门槛 (RM 看 credit/alert 仅 read · 进得去 workspace 但 invoke 按钮 hide)
 *   - workspace 内部 invoke/export/handoff/approve 按钮由 <ActionGate> wrap (B4 worker owns)
 *   - 后端 require_action(<agent>, "invoke"/"export"/...) defence in depth
 */
export function RbacGuard({
  agent,
  children,
}: {
  agent: AgentKey;
  children: ReactNode;
}) {
  const can = useAuthStore((s) => s.can);
  // row-level/action gate · 入口最低门槛 read · 进入后 ActionGate wrap 按钮
  const allowed = can({
    kind: "agent.action",
    agent: AGENT_KEY_TO_ID[agent],
    action: "read",
  });
  if (!allowed) return <NoPermission agent={agent} />;
  return <>{children}</>;
}
