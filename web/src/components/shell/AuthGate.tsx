"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useAuthStore } from "@/lib/store";

export function AuthGate({ children }: { children: ReactNode }) {
  const pathname = usePathname() || "/";
  const currentUser = useAuthStore((s) => s.currentUser);
  const logout = useAuthStore((s) => s.logout);
  const router = useRouter();
  const [hydrated, setHydrated] = useState(false);
  const initialMountRef = useRef(true);

  useEffect(() => {
    setHydrated(true);
  }, []);

  const isLogin = pathname === "/login";

  useEffect(() => {
    if (!hydrated) return;

    if (initialMountRef.current) {
      initialMountRef.current = false;
      if (currentUser && isLogin) {
        logout();
        return;
      }
    }

    if (!currentUser && !isLogin) {
      router.replace("/login");
      return;
    }

    if (currentUser && isLogin) {
      router.replace("/today");
    }
  }, [hydrated, currentUser, isLogin, router, logout]);

  if (!hydrated) return null;
  if (!currentUser && !isLogin) return null;

  return <>{children}</>;
}
