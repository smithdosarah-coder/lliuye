/**
 * B.3.4 · P0-R5 · 主活 B · admin 真号 E2E 共享 helper (v3 · cookie + storageState)
 *
 * v3 reframe (worker e2e-daily 实测 prod liuye.me · 2026-05-11):
 *   - 跟 PM 主 CLI commit 3e68f3c 说法不一致 · /api/auth/me 实测**仍需 cookie** ·
 *     无 cookie 返 401 AUTH_MISSING
 *   - AuthGate (web/src/components/shell/AuthGate.tsx:38) bootstrap() 调 /api/auth/me
 *     401 → currentUser=null → redirect /login
 *   - 所以**两者都需**:
 *     · storageState 注 localStorage `platform.auth.v1` (Zustand persist · 前端 state)
 *     · cookie 注 backend session (走 /api/auth/login 真拿)
 *
 * 用法:
 *   import { adminTest, expect, E2E_TIMEOUT_MS } from "./_shared";
 *   adminTest("...", async ({ page }) => { ... });
 *
 * 失败模式:
 *   - storage state 文件 missing → skip (不假冒)
 *   - /api/auth/login fail → skip (prod 真挂 · 不假装 PASS)
 */

import { test as base, expect } from "@playwright/test";
import * as path from "path";
import * as fs from "fs";

export { expect };

export const REAL_PROD_BASE_URL =
  process.env.E2E_BASE_URL ?? "https://liuye.me";

export const STORAGE_STATE_PATH = path.resolve(
  __dirname,
  ".auth/admin.json",
);

const STORAGE_STATE_EXISTS = fs.existsSync(STORAGE_STATE_PATH);

const ADMIN_USER_ID = process.env.E2E_ADMIN_USER_ID ?? "u_liuye";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "liuye";

/**
 * Module-level cache · 1 worker (per playwright.config.ts fullyParallel=false workers=1)
 * 避开复杂 base.extend<TestArgs, WorkerArgs> 类型签名坑 · 直接 beforeEach 注入
 */
let cachedAdminCookie: string | null = null;

async function loginAndCacheCookie(): Promise<string> {
  if (cachedAdminCookie) return cachedAdminCookie;
  const loginUrl = `${REAL_PROD_BASE_URL.replace(/\/$/, "")}/api/auth/login`;
  const res = await fetch(loginUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: ADMIN_USER_ID,
      password: ADMIN_PASSWORD,
    }),
  });
  if (!res.ok) {
    throw new Error(
      `admin login fail · status=${res.status} · url=${loginUrl} · ` +
        `body=${(await res.text()).slice(0, 200)}`,
    );
  }
  const setCookie = res.headers.get("set-cookie") ?? "";
  const match = setCookie.match(/zhongan_auth=([^;]+)/);
  if (!match) {
    throw new Error(
      `admin login OK 但无 zhongan_auth cookie · set-cookie="${setCookie.slice(0, 200)}"`,
    );
  }
  cachedAdminCookie = match[1];
  return cachedAdminCookie;
}

export const adminTest = base;

adminTest.use({
  baseURL: REAL_PROD_BASE_URL,
  // localStorage `platform.auth.v1` 从 .auth/admin.json 注 (前端 state)
  ...(STORAGE_STATE_EXISTS ? { storageState: STORAGE_STATE_PATH } : {}),
});

/**
 * ROI #5 (2026-05-21) · E2E 证据链 run_id 注入
 *
 * CI 模式: process.env.LIUYE_E2E_RUN_ID = ${{ github.run_id }} (GH Actions 设)
 * 本地模式: 缺该 env → fallback "local-<timestamp>" (避免空 header 写 NULL ·
 *           本地跑也能 grep audit log 自查 · "local-" 前缀防误入 cron audit 数据)
 *
 * 注入路径: page.setExtraHTTPHeaders 每个 page · 走真后端的所有 XHR/fetch 都带
 *
 * 失败模式: 注入失败 throw → spec fail · 不允许 silent skip (证据链是 PM gate)
 */
const E2E_RUN_ID =
  process.env.LIUYE_E2E_RUN_ID ||
  `local-${Date.now()}`;

adminTest.beforeEach(async ({ context, page }, testInfo) => {
  if (!STORAGE_STATE_EXISTS) {
    testInfo.skip(
      true,
      `storage state file missing: ${STORAGE_STATE_PATH} · 主 CLI commit 3e68f3c 应 ship`,
    );
    return;
  }
  // 注 backend session cookie (AuthGate.bootstrap() 调 /api/auth/me 必带)
  const cookie = await loginAndCacheCookie();
  const url = new URL(REAL_PROD_BASE_URL);
  await context.addCookies([
    {
      name: "zhongan_auth",
      value: cookie,
      domain: url.hostname,
      path: "/",
      httpOnly: true,
      secure: url.protocol === "https:",
      sameSite: "Lax",
    },
  ]);
  // ROI #5 · X-Liuye-E2E-Run-Id header 注入 · audit_service.middleware 读后
  // 写入 e2e_run_id 列 · daily-visual workflow 用 /api/audit/by_run_id/{run_id} 拉
  await page.setExtraHTTPHeaders({
    "X-Liuye-E2E-Run-Id": E2E_RUN_ID,
  });
});

/**
 * 单 spec 通用超时 · SSE done 在 60s 内是 PM SLA · 留 1.5x buffer
 */
export const E2E_TIMEOUT_MS = 90_000;

/**
 * 初次 selector 容差 · prod CF cold + AuthGate bootstrap + SPA hydration
 *
 * 历史 fail: 15s 在 CF cold start 下经常 timeout (实测 admin-credit / admin-riskctrl
 * 跑 6 spec 顺序时 transient fail · /api/auth/me 返 200 但 workspace 首次 render
 * 超 15s · per B.4 SLO-2 主活 D 排查 2026-05-11).
 *
 * 30s 容差: CF cold ~3-8s + AuthGate spinner 0.5-1s + bootstrap fetch ~1-2s + Next 16
 * hydration ~5-10s + workspace mount ~2-3s = worst case ~25s · 30s 留 buffer.
 */
export const FIRST_PAINT_TIMEOUT_MS = 30_000;
