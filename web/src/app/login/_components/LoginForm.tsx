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
  const authBusy = useAuthStore((s) => s.authBusy);
  const lastError = useAuthStore((s) => s.lastError);
  const router = useRouter();
  const [userId, setUserId] = useState<string>(DEMO_USERS[0].id);
  const [password, setPassword] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  const current = DEMO_USERS.find((u) => u.id === userId);
  const errorMessage = localError ?? lastError;

  useEffect(() => {
    if (currentUser) {
      router.replace("/today");
    }
  }, [currentUser, router]);

  /* W-D1F-A2 · 2026-04-28 · 前端 PASSWORD_MAP 已彻底移除
     password 走 backend bcrypt verify (auth_service/users.py · auth_service/__init__.py)
     login() 是 async · 调 POST /api/auth/login · cookie httpOnly 浏览器接管
     失败 backend 返 401 + AUTH_FAILED · UI 拿 lastError 显错误条 */

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLocalError(null);
    if (!userId || !password.trim()) {
      setLocalError("请填写身份和密码");
      return;
    }
    const ok = await login(userId, password);
    if (!ok) {
      // lastError 由 store 设置 · 不需要在这里重复设
      return;
    }
    // 成功 redirect 由 useEffect 处理
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
        <p className="lf-sub">乾策 Studio · 信贷 AI 协作平台</p>
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
            onChange={(e) => {
              setUserId(e.target.value);
              setLocalError(null);
            }}
            data-role={current?.role}
            data-testid="login-user-select"
            disabled={authBusy}
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
            if (errorMessage) setLocalError(null);
          }}
          data-testid="login-password-input"
          disabled={authBusy}
        />
        {errorMessage && (
          <div
            role="alert"
            data-testid="login-error-banner"
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
            ⚠ {errorMessage}
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
        data-testid="login-submit"
        disabled={authBusy}
      >
        <span className="cn">{authBusy ? "验证中…" : `进入 ${current?.name ?? ""}`}</span>
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
        <span className="mono">platform.auth.v1 · backend bcrypt</span>
        <span>© 2026 众安信科 · AI 中台</span>
      </footer>
    </form>
  );
}
