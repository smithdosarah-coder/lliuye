import { LoginForm } from "./_components/LoginForm";
import "./login.css";

export const metadata = {
  title: "登录 · 乾策 Studio",
};

/**
 * F4 (V4 plan · Phase B-1) · 登录页黑洞重设 · 极简磨砂玻璃 + 中性深灰蓝。
 * 撤除前版 Interstellar (Gargantua + 星空 + cosmic vignette)：银行客户首屏不
 * 联想"资金被吞" (per V4 plan F4 + Gemini R2 提权 P1 + R2 v2 三方一致)。
 * 视觉走 frosted-glass 卡 + 中性 slate-blue 背景 · 端正稳重 · 无重 3D 资源。
 */
export default function LoginPage() {
  return (
    <div className="login-root" data-testid="login-root">
      <div className="login-bg" aria-hidden>
        <div className="login-bg__plate" />
        <div className="login-bg__halo" />
      </div>
      <main className="login-aside">
        <LoginForm />
      </main>
    </div>
  );
}
