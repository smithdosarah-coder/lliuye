"use client";

/**
 * LogoutButton · Masthead 顶栏常驻退出按钮
 *
 * 首页（/today）用户反馈看不到退出入口（PersonaSwitcher 里藏在下拉菜单里）。
 * 这里提供一个始终可见的小 pill，一键调 authStore.logout + router.push("/login")。
 * 视觉和 .canvas-mode-toggle / .theme-sw-trigger 同风格（共享 .shell-pill base class）。
 */

import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store";

export function LogoutButton() {
  const user = useAuthStore((s) => s.currentUser);
  const logout = useAuthStore((s) => s.logout);
  const router = useRouter();
  if (!user) return null;

  /* W-D1F-A2 · 2026-04-28 · logout 改 async backend call (POST /api/auth/logout 清 cookie)
     即使 backend error · store 仍清前端 currentUser · UI 不阻 */
  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  return (
    <button
      type="button"
      className="logout-btn"
      onClick={handleLogout}
      title="退出登录，回到登录页"
      aria-label="退出登录"
    >
      <span className="ic" aria-hidden>
        ↪
      </span>
      <span className="lbl">退出</span>
    </button>
  );
}
