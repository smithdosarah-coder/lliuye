"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { useAuthStore } from "@/lib/store";

/**
 * AuthGate — 未登录一律跳 /login；已登录访问 /login 跳 /today。
 *
 * Hydration 纪律：zustand persist 在 client hydrate 前视为 "未登录"，
 * 直接 redirect 会与 SSR 输出失配并闪一帧。先等 hydrate，再判定。
 */
export function AuthGate({ children }: { children: ReactNode }) {
  const pathname = usePathname() || "/";
  const currentUser = useAuthStore((s) => s.currentUser);
  const router = useRouter();
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHydrated(true);
  }, []);

  const isLogin = pathname === "/login";

  useEffect(() => {
    if (!hydrated) return;
    if (!currentUser && !isLogin) {
      router.replace("/login");
      return;
    }
    if (currentUser && isLogin) {
      router.replace("/today");
    }
  }, [hydrated, currentUser, isLogin, router]);

  if (!hydrated) return null;
  if (!currentUser && !isLogin) return null;
  if (currentUser && isLogin) return null;

  return <>{children}</>;
}
