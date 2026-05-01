"use client";

/**
 * F5 (V4 plan · Phase B-1) · CustomerContextGateway
 *
 * 用途: RM 从 /customer / /dispatch / /today 等任意入口跳进 4 view (today /
 * dispatch / archive/[agent] / warroom) 时，URL 携带 ?customer=cust_xxx ·
 * 由本组件读 query · focus customer-store · 4 view hero/query/默认 scan 一致。
 *
 * 来源: V4 plan F5 (Codex C7 + Gemini Customer Ribbon · 折中接受 PM 方案 4A)
 * 验收: RM 从 customer/dispatch/today 进 workspace 后 hero/query/默认 scan 一致 ·
 *      不删 CustomerSelector (保留 demo / 异常切换入口)
 *
 * 设计:
 * - 仅在 mount + ?customer 变化 时 focus(id)
 * - 命中后 router.replace 把 ?customer 抹除 · 避免 URL 残留 stale state
 *   (用户刷新或分享 URL 时仍能恢复 · 抹除是为了下次手动切换不被这个 query
 *    重置 store)
 * - 无效 id (不在 customers 列) · console.warn · 不破渲染流
 * - effect-only · 无 visual · 不影响 layout
 *
 * 嵌入点: AppShell ShellChrome (stage 内 · 4 view 共享)
 */

import { useEffect } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";

import { useCustomerStore } from "@/lib/store";

const CUSTOMER_QUERY_KEY = "customer";

export function CustomerContextGateway() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const focus = useCustomerStore((s) => s.focus);
  const byId = useCustomerStore((s) => s.byId);

  const customerId = params?.get(CUSTOMER_QUERY_KEY) ?? null;

  useEffect(() => {
    if (!customerId) return;
    const customer = byId(customerId);
    if (!customer) {
      console.warn(
        `[CustomerContextGateway] unknown customerId="${customerId}" — skipping focus`,
      );
      return;
    }
    focus(customerId);

    // 抹除 ?customer query · 避免 URL stale 状态影响下次手动切换
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    url.searchParams.delete(CUSTOMER_QUERY_KEY);
    const next = `${url.pathname}${url.search}${url.hash}`;
    router.replace(next || pathname || "/", { scroll: false });
  }, [customerId, focus, byId, router, pathname]);

  return null;
}

/** 拼客户跳转 URL · 4 view 入口统一用此 helper · 保证 query key 一致。
 *  示例: linkWithCustomer("/archive/credit", "cust_zrgs") → "/archive/credit?customer=cust_zrgs" */
export function linkWithCustomer(href: string, customerId: string): string {
  if (!customerId) return href;
  const sep = href.includes("?") ? "&" : "?";
  return `${href}${sep}${CUSTOMER_QUERY_KEY}=${encodeURIComponent(customerId)}`;
}
