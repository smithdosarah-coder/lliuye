"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { DEMO_USERS, useAuthStore } from "@/lib/store";
import type { Role } from "@/lib/store/types";

const ROLE_LABEL: Record<Role, string> = {
  rm: "客户经理",
  credit_officer: "审贷官",
  compliance_officer: "合规官",
  risk_manager: "风险经理",
  admin: "平台管理员",
};

export function LoginForm() {
  const login = useAuthStore((s) => s.login);
  const currentUser = useAuthStore((s) => s.currentUser);
  const router = useRouter();
  const [userId, setUserId] = useState<string>(DEMO_USERS[0].id);
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);

  const current = DEMO_USERS.find((u) => u.id === userId);

  useEffect(() => {
    if (currentUser) {
      router.replace("/today");
    }
  }, [currentUser, router]);

  /* 5 user demo 密码 (前端校验 · prod 阶段接 backend /api/auth/login 替换)
     2026-04-27 user 要"真密码" · password = user 名拼音小写 · 5 固定账号 */
  const PASSWORD_MAP: Record<string, string> = {
    u_wangzhe: "wangzhe",
    u_lihua: "lihua",
    u_zhoumin: "zhoumin",
    u_chenkai: "chenkai",
    u_liuye: "liuye",
  };

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setAuthError(null);
    const expected = PASSWORD_MAP[userId];
    if (!expected || expected !== password) {
      setAuthError("账号或密码错误");
      return;
    }
    login(userId);
  }

  return (
    <form className="login-form" onSubmit={handleSubmit}>
      <header className="lf-head">
        <div className="lf-eyebrow">
          <span>PLATFORM</span>
          <span className="dot" />
          <em>local demo</em>
        </div>
        <h2 className="lf-title">
          <span className="cn">登 录</span>
          <span className="en">sign in</span>
        </h2>
        <p className="lf-sub">
          乾策 Studio · 信贷 AI 协作平台
        </p>
      </header>

      <div className="lf-field">
        <label className="lf-label" htmlFor="lf-persona">
          身份 <span className="mono">persona</span>
        </label>
        <div className="lf-select-wrap">
          <select
            id="lf-persona"
            className="lf-select"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            data-role={current?.role}
          >
            {DEMO_USERS.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name} · {ROLE_LABEL[u.role]} · {u.team}
              </option>
            ))}
          </select>
          <span className="lf-select-chev" aria-hidden>
            ▾
          </span>
        </div>
      </div>

      <div className="lf-field">
        <label className="lf-label" htmlFor="lf-pass">
          访问口令
        </label>
        <input
          id="lf-pass"
          className="lf-input"
          type="password"
          placeholder="输入密码 · 见下方提示"
          autoComplete="off"
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            if (authError) setAuthError(null);
          }}
        />
        {authError && (
          <div
            role="alert"
            style={{
              fontSize: 12,
              color: "#E89B91",
              fontFamily: "var(--cjk)",
              marginTop: 8,
              padding: "6px 10px",
              background: "rgba(215, 83, 74, 0.12)",
              border: "1px solid rgba(215, 83, 74, 0.32)",
              borderRadius: 8,
            }}
          >
            ⚠ {authError}
          </div>
        )}
      </div>

      <div className="lf-row">
        <label className="lf-check">
          <input type="checkbox" defaultChecked disabled />
          <span>保持登录</span>
        </label>
        <span className="lf-link" aria-disabled>
          忘记口令？
        </span>
      </div>

      <button
        type="submit"
        className="lf-submit"
        data-role={current?.role}
      >
        <span className="cn">进入 {current?.name ?? ""}</span>
        <span className="en">
          <em>enter</em> ↘
        </span>
      </button>

      <div className="lf-sso">
        <span className="lf-sep">
          <i />
          <em>或其他方式</em>
          <i />
        </span>
        <div className="lf-sso-row">
          <button type="button" className="lf-sso-btn" disabled>
            <span className="dot" />
            <span>企业 SSO</span>
          </button>
          <button type="button" className="lf-sso-btn" disabled>
            <span className="dot" />
            <span>短信登录</span>
          </button>
        </div>
      </div>

      <footer className="lf-foot">
        <span className="mono">platform.auth.v1</span>
        <span>© 2026 众安信科 · AI 中台</span>
      </footer>
    </form>
  );
}
