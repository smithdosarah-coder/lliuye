"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { useAuthStore } from "@/lib/store";
import type { Action, AgentId } from "@/lib/store/types";

/**
 * AuthGate · Stage D.1 frontend (W-D1F-A2 · 2026-04-28)
 *
 * 改造 (vs Stage A 前端硬编版):
 *   - bootstrap() 启动时 GET /api/auth/me 真验 cookie · 200 → 拿 user · 401 → null
 *   - 未登录 + non-/login path → redirect /login
 *   - 登录 + /login path → redirect /today (避免重复登录)
 *   - 用户访问 /archive/<agent> 但 ACCESS matrix 不含该 agent → redirect /403
 *
 * 真 enforce 在 backend Depends(require_agent("X")) (auth_service/dependencies.py · D.1 backend).
 * 前端 ACCESS check 是 instant guard · 减少无效请求 · 不替代 backend.
 */

const AGENT_PATH_RE = /^\/archive\/(channel|report|credit|alert|compliance|riskctrl)/;

export function AuthGate({ children }: { children: ReactNode }) {
  const pathname = usePathname() || "/";
  const currentUser = useAuthStore((s) => s.currentUser);
  const accessibleAgents = useAuthStore((s) => s.accessibleAgents);
  const bootstrapped = useAuthStore((s) => s.bootstrapped);
  const bootstrap = useAuthStore((s) => s.bootstrap);
  const router = useRouter();
  const [hydrated, setHydrated] = useState(false);

  const isLogin = pathname === "/login";
  const isForbidden = pathname === "/403";

  // 启动时 bootstrap (GET /me · 拿 cookie 真验)
  useEffect(() => {
    setHydrated(true);
    void bootstrap();
  }, [bootstrap]);

  useEffect(() => {
    if (!hydrated || !bootstrapped) return;

    // 未登录 · 非 /login / /403 → redirect /login
    if (!currentUser && !isLogin && !isForbidden) {
      router.replace("/login");
      return;
    }

    // 已登录 · 在 /login → redirect /today
    if (currentUser && isLogin) {
      router.replace("/today");
      return;
    }

    // 已登录 · 访问 /archive/<agent> · ACCESS matrix 验
    if (currentUser) {
      const m = pathname.match(AGENT_PATH_RE);
      if (m) {
        const agent = m[1] as AgentId;
        if (!accessibleAgents.includes(agent)) {
          router.replace("/403");
          return;
        }
      }
    }
  }, [hydrated, bootstrapped, currentUser, accessibleAgents, isLogin, isForbidden, pathname, router]);

  // hydrate / bootstrap 前不渲染 · 防 SSR 闪
  if (!hydrated || !bootstrapped) return null;

  // 未登录 · non-login/403 path → 等 redirect (上面 useEffect 触发)
  if (!currentUser && !isLogin && !isForbidden) return null;

  return <>{children}</>;
}

/**
 * ActionGate · row-level/action gate component (Phase B Sprint 3 contract sub-PR 1 · 2026-05-05)
 *
 * 用 ACCESS_V2 row-level/action 检查 · 替代 binary AuthGate 的 agent-level binary check.
 *
 * Usage (sub-PR 2 起 wire 起来):
 *   <ActionGate agent="compliance" action="invoke">
 *     <PolicyDiffButton />
 *   </ActionGate>
 *
 *   <ActionGate agent="credit" action="read" fallback={<ReadOnlyBadge />}>
 *     <CreditEditPanel />
 *   </ActionGate>
 *
 * 前端 instant guard · 真 enforce 在 backend Depends(require_action(agent, action)).
 */
export function ActionGate({
  agent,
  action,
  children,
  fallback,
}: {
  agent: AgentId;
  action: Action;
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const can = useAuthStore((s) => s.can);
  if (!can({ kind: "agent.action", agent, action })) {
    return <>{fallback ?? null}</>;
  }
  return <>{children}</>;
}
