import { DEMO_USERS } from "@/lib/store/auth-store";
import { PersonaCard } from "./_components/PersonaCard";
import "./login.css";

export const metadata = {
  title: "登录 · 乾策 Studio",
};

/**
 * Login view · Phase 1 Batch 1 · Task A
 *
 * Demo 期不接真实 SSO：展示 5 个 persona 卡片，点击即登录。
 * 设计参考：Notion / Linear 的 workspace 选择器 —— 不要银行系统的用户名密码表单。
 */
export default function LoginPage() {
  return (
    <div className="login-root">
      <section className="login-card">
        <header className="login-head">
          <div className="eyebrow">
            <span>PLATFORM · 乾策 Studio</span>
            <span className="sep" />
            <em>Demo personas.</em>
          </div>
          <h1 className="login-h1">
            <span className="cn">选一位身份</span>{" "}
            <span className="en">
              <em>step in.</em>
            </span>
          </h1>
          <p className="login-lede">
            本地演示环境，选择任一 persona 即进入。所有数据仅存本机，不上传、不持久到服务端。
          </p>
        </header>
        <div className="persona-grid">
          {DEMO_USERS.map((u) => (
            <PersonaCard key={u.id} user={u} />
          ))}
        </div>
        <footer className="login-foot">
          <span>切换 persona · 进入后可在顶栏右上随时切换。</span>
          <span className="mono">platform.auth.v1 · local-only</span>
        </footer>
      </section>
    </div>
  );
}
