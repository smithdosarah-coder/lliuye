import type { ReactNode } from "react";
import { Desk } from "./Desk";
import { FloatBadge } from "./FloatBadge";
import { Masthead } from "./Masthead";
import { ThemeSwitch } from "./ThemeSwitch";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="shell-root">
      <Desk />
      <main className="shell-stage">
        <Masthead />
        <section className="shell-views">{children}</section>
      </main>
      <FloatBadge />
      <ThemeSwitch />
    </div>
  );
}
