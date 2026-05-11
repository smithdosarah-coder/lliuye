/**
 * B.3.4 · P0-R5 · 主活 B · admin 真号 E2E 共享 helper
 *
 * 6 admin-*.spec.ts 复用 · cookie 注入 / baseURL / 跳过条件统一.
 *
 * 用法 (per spec):
 *   import { adminTest, expect, REAL_PROD_BASE_URL } from "./_shared";
 *
 *   adminTest("...", async ({ page }) => {
 *     await page.goto("/archive/channel"); // baseURL 自动用 prod
 *     ...
 *   });
 *
 * Env (per scripts/e2e/run_admin_daily.sh + .github/workflows/daily-visual.yml):
 *   ADMIN_COOKIE     JWT (just value · 或完整 "zhongan_auth=<value>") · REQUIRED
 *   E2E_BASE_URL     默认 https://liuye.me
 */

import { test as base, expect } from "@playwright/test";

export { expect };

export const REAL_PROD_BASE_URL =
  process.env.E2E_BASE_URL ?? "https://liuye.me";

const RAW_COOKIE = process.env.ADMIN_COOKIE ?? "";
const COOKIE_VALUE = RAW_COOKIE.replace(/^zhongan_auth=/, "").trim();

export const COOKIE_NAME = "zhongan_auth";

/**
 * Fixture · admin 真号 cookie 注入 · baseURL = prod
 *
 * 未配 ADMIN_COOKIE 时所有 spec 自动 skip · 不假装通过 / 不 mock cookie (per KT R5 硬线).
 */
export const adminTest = base.extend<{ adminCookie: string }>({
  adminCookie: async ({}, use, testInfo) => {
    if (!COOKIE_VALUE) {
      testInfo.skip(
        true,
        "ADMIN_COOKIE 未配 · admin 真号 E2E spec 自动 skip · " +
          "本地: export ADMIN_COOKIE=<jwt> · CI: secrets.ADMIN_COOKIE",
      );
    }
    await use(COOKIE_VALUE);
  },
});

adminTest.use({
  baseURL: REAL_PROD_BASE_URL,
});

adminTest.beforeEach(async ({ context, adminCookie }) => {
  if (!adminCookie) return; // skip 已在 fixture 触发
  const url = new URL(REAL_PROD_BASE_URL);
  await context.addCookies([
    {
      name: COOKIE_NAME,
      value: adminCookie,
      domain: url.hostname,
      path: "/",
      httpOnly: true,
      secure: url.protocol === "https:",
      sameSite: "Lax",
    },
  ]);
});

/**
 * 单 spec 通用超时 · SSE done 在 60s 内是 PM SLA · 留 1.5x buffer
 */
export const E2E_TIMEOUT_MS = 90_000;
