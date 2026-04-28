"use client";

/**
 * /403 · 权限不足 page · Stage D.1 frontend (W-D1F-A2 · 2026-04-28)
 *
 * 触发: AuthGate 检 ACCESS matrix · 用户角色无权访问目标 /archive/<agent>
 * 例: 李华 (credit_officer) 访问 /archive/channel → AuthGate redirect /403
 *
 * Spec: docs/contracts/auth-protocol.md §6.3 · friendly forbid 页 + 返回 today link
 */

import Link from "next/link";
import { useAuthStore } from "@/lib/store";

const ROLE_LABEL: Record<string, string> = {
  rm: "客户经理",
  credit_officer: "审贷官",
  compliance_officer: "合规官",
  risk_manager: "风险经理",
  admin: "平台管理员",
};

export default function ForbiddenPage() {
  const currentUser = useAuthStore((s) => s.currentUser);
  const accessibleAgents = useAuthStore((s) => s.accessibleAgents);

  return (
    <main
      className="auth-403-page"
      data-testid="auth-403-page"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "calc(100vh - 80px)",
        padding: "48px 24px",
        textAlign: "center",
        gap: 18,
      }}
    >
      <div
        aria-hidden
        style={{
          fontSize: 64,
          fontFamily: "var(--display)",
          color: "var(--ink-40)",
          letterSpacing: "0.08em",
        }}
      >
        403
      </div>
      <h1
        style={{
          fontFamily: "var(--display)",
          fontSize: 24,
          fontWeight: 500,
          color: "var(--ink)",
          margin: 0,
        }}
      >
        无权访问此 Agent
      </h1>
      <p
        style={{
          fontFamily: "var(--cjk)",
          fontSize: 14,
          color: "var(--ink-65)",
          lineHeight: 1.7,
          maxWidth: 520,
          margin: 0,
        }}
      >
        {currentUser ? (
          <>
            当前账号 <strong>{currentUser.name}</strong> ({ROLE_LABEL[currentUser.role] ?? currentUser.role})
            的角色 ACCESS matrix 不包含此 Agent。
            {accessibleAgents.length > 0 ? (
              <>
                {" "}你可访问的 Agent: <code style={{ fontFamily: "var(--mono)" }}>{accessibleAgents.join(" / ")}</code>
              </>
            ) : null}
          </>
        ) : (
          "未识别到当前会话 · 请重新登录。"
        )}
      </p>
      <Link
        href="/today"
        data-testid="auth-403-back-today"
        style={{
          marginTop: 12,
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          padding: "8px 18px",
          fontFamily: "var(--cjk)",
          fontSize: 13,
          color: "#fff",
          background: "var(--ink)",
          borderRadius: 6,
          textDecoration: "none",
        }}
      >
        ← 返回 today
      </Link>
    </main>
  );
}
