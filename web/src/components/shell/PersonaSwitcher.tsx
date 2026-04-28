"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { DEMO_USERS, useAuthStore } from "@/lib/store";
import type { Role } from "@/lib/store/types";

const ROLE_LABEL: Record<Role, string> = {
  rm: "客户经理",
  credit_officer: "审贷官",
  compliance_officer: "合规官",
  risk_manager: "风险经理",
  admin: "平台管理员",
};

/** team 字段 "华东·上海第一支行" 取首段做 masthead 短显示。 */
function shortTeam(team: string): string {
  return team.split("·")[0] ?? team;
}

export function PersonaSwitcher() {
  const user = useAuthStore((s) => s.currentUser);
  const login = useAuthStore((s) => s.login);
  const logout = useAuthStore((s) => s.logout);
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  // AuthGate 已拦未登录路径，这里兜底 —— masthead 在 /login 外层不渲染
  if (!user) return null;

  return (
    <div className="persona-sw" ref={rootRef}>
      <button
        type="button"
        className="persona-sw-trigger"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <span className="dot" aria-hidden />
        <span className="name">{user.name}</span>
        <span className="role">
          {ROLE_LABEL[user.role]} · {shortTeam(user.team)}
        </span>
      </button>
      {open && (
        <div className="persona-sw-pop" role="menu">
          <div className="persona-sw-head">切换 persona</div>
          {DEMO_USERS.map((u) => {
            const active = u.id === user.id;
            return (
              <button
                key={u.id}
                type="button"
                role="menuitemradio"
                aria-checked={active}
                className={`persona-sw-item${active ? " on" : ""}`}
                onClick={() => {
                  /* W-D1F-A2 · 2026-04-28 · login 改 backend bcrypt verify
                     demo 期 password = userId 后缀 (u_wangzhe → wangzhe · per LoginForm.tsx:33 注释)
                     production 期 PersonaSwitcher 应改"先 logout 再 redirect /login"流程
                     · demo 期保留快速切换 UX */
                  if (!active) {
                    const demoPwd = u.id.replace(/^u_/, "");
                    void login(u.id, demoPwd);
                  }
                  setOpen(false);
                }}
              >
                <span
                  className="persona-sw-avatar"
                  data-role={u.role}
                  aria-hidden
                >
                  {u.avatar ?? u.name.slice(-1)}
                </span>
                <span className="persona-sw-body">
                  <span className="cn">{u.name}</span>
                  <span className="sub">
                    {ROLE_LABEL[u.role]} · {u.team}
                  </span>
                </span>
                {active && (
                  <span className="persona-sw-check" aria-hidden>
                    ✓
                  </span>
                )}
              </button>
            );
          })}
          <div className="persona-sw-sep" role="separator" />
          <button
            type="button"
            role="menuitem"
            className="persona-sw-logout"
            onClick={() => {
              logout();
              setOpen(false);
              router.replace("/login");
            }}
          >
            退出登录
            <span className="mono">↪</span>
          </button>
        </div>
      )}
    </div>
  );
}
