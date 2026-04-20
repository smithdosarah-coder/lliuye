"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/lib/store";

/**
 * AuditEntry — masthead 内的审计入口按钮。
 * 仅对 `audit.view` 权限（合规官 + admin）渲染；其他 persona 返回 null。
 */
export function AuditEntry() {
  const can = useAuthStore((s) => s.can);
  const pathname = usePathname() || "/";
  if (!can({ kind: "audit.view" })) return null;
  const active = pathname.startsWith("/audit");
  return (
    <Link
      href="/audit"
      className={`audit-entry${active ? " on" : ""}`}
      aria-label="审计"
      title="审计视图 · 仅合规官 / 管理员可见"
    >
      <span className="ic" aria-hidden>
        ⌘
      </span>
      <span className="lbl">审计</span>
    </Link>
  );
}
