import { CosmicStageGate } from "./_components/CosmicStageGate";
import { LoginForm } from "./_components/LoginForm";
import "./login.css";

export const metadata = {
  title: "登录 · 乾策 Studio",
};

export default function LoginPage() {
  return (
    <div className="login-root">
      <div className="login-sky" aria-hidden>
        <div className="login-sky__field" />
        <div className="login-sky__stars" />
      </div>
      <section className="login-stage" aria-hidden>
        <CosmicStageGate />
      </section>
      <aside className="login-aside">
        <LoginForm />
      </aside>
    </div>
  );
}
