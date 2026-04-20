"use client";

import type { ReactNode } from "react";
import { NoPermission } from "@/components/shell/NoPermission";
import type { AgentKey } from "@/lib/agents";
import { AGENT_KEY_TO_ID } from "@/lib/auth/agent-id";
import { useAuthStore } from "@/lib/store";

/**
 * RbacGuard — archive/[agent] 入口权限判定。
 *
 * AuthGate 保证未登录用户不会到达本组件，所以只判 `agent.access`。
 */
export function RbacGuard({
  agent,
  children,
}: {
  agent: AgentKey;
  children: ReactNode;
}) {
  const can = useAuthStore((s) => s.can);
  const allowed = can({ kind: "agent.access", agent: AGENT_KEY_TO_ID[agent] });
  if (!allowed) return <NoPermission agent={agent} />;
  return <>{children}</>;
}
