import { CosmicStage } from "./_components/CosmicStage";
import { LoginForm } from "./_components/LoginForm";
import "./login.css";

export const metadata = {
  title: "登录 · 乾策 Studio",
};

export default function LoginPage() {
  return (
    <div className="login-root">
      <section className="login-stage" aria-hidden>
        <CosmicStage />
      </section>
      <aside className="login-aside">
        <LoginForm />
      </aside>
    </div>
  );
}
