import { test, expect } from "@playwright/test";

/**
 * F-057 · AuthGate enforce real backend (W-D1F-A2 · 2026-04-28)
 *
 * 验证 frontend 真接 backend Stage D.1 (auth_service · `bd143b5` MERGED):
 *   POST /api/auth/login    → Set-Cookie zhongan_auth httpOnly
 *   GET  /api/auth/me       → 拿 user + accessibleAgents
 *   POST /api/auth/logout   → 清 cookie
 *
 * Spec: docs/contracts/auth-protocol.md v1.0
 *
 * 5 case:
 *   1. 未登录访问 /archive/credit → redirect /login
 *   2. u_lihua (credit_officer) 登录 + 访问 /archive/credit → OK
 *   3. u_lihua 访问 /archive/channel (无权) → redirect /403
 *   4. u_liuye (admin) 登录 + 访问 /archive/channel → OK (admin full access)
 *   5. logout → cookie 清 + 再访问 protected path → redirect /login
 *
 * 注: spec 真调 backend `/api/auth/login` · 必须先起 uvicorn (api_server:app · 8000 或代理).
 *     本仓库 dev 环境 frontend 走相对 path · proxy 转 backend · 或 NEXT_PUBLIC_API_BASE 指向。
 *     如 backend 不可达 · spec skip · 不阻 mesh (frontend tsc + 静态审 review 仍通)。
 */

const TEST_USERS = {
  lihua: { id: "u_lihua", password: "lihua", role: "credit_officer" },
  liuye: { id: "u_liuye", password: "liuye", role: "admin" },
};

async function backendReachable(page: import("@playwright/test").Page): Promise<boolean> {
  try {
    const res = await page.request.get("/api/auth/me", { failOnStatusCode: false });
    // 200 (有 cookie) 或 401 (无 cookie) 都说明 backend reachable
    return res.status() === 200 || res.status() === 401;
  } catch {
    return false;
  }
}

async function loginViaApi(
  page: import("@playwright/test").Page,
  user: { id: string; password: string },
): Promise<void> {
  const res = await page.request.post("/api/auth/login", {
    data: { user_id: user.id, password: user.password },
    failOnStatusCode: false,
  });
  if (!res.ok()) {
    throw new Error(`login fail: HTTP ${res.status()}`);
  }
}

test.describe("F-057 · AuthGate real backend enforce", () => {
  test.beforeEach(async ({ context }) => {
    // 清掉所有 cookie (避免上 case 残留)
    await context.clearCookies();
  });

  test("未登录访问 /archive/credit → redirect /login", async ({ page }) => {
    if (!(await backendReachable(page))) {
      test.skip(true, "backend /api/auth/me unreachable · skip");
    }
    await page.goto("/archive/credit", { waitUntil: "networkidle" });
    // AuthGate /me 401 → redirect /login
    await expect(page).toHaveURL(/\/login(\/|$|\?)/, { timeout: 8000 });
  });

  test("u_lihua (credit_officer) 登录 + 访问 /archive/credit → OK", async ({ page }) => {
    if (!(await backendReachable(page))) {
      test.skip(true, "backend unreachable");
    }
    await loginViaApi(page, TEST_USERS.lihua);
    await page.goto("/archive/credit", { waitUntil: "networkidle" });
    // 应在 /archive/credit · 不被 redirect /login 或 /403
    await expect(page).toHaveURL(/\/archive\/credit/, { timeout: 8000 });
    // workspace 容器渲染 (CreditEmptyState · started=false default)
    const workspace = page.locator('[data-credit-started]');
    await expect(workspace).toBeVisible({ timeout: 8000 });
  });

  test("u_lihua 访问 /archive/channel (无权) → redirect /403", async ({ page }) => {
    if (!(await backendReachable(page))) {
      test.skip(true, "backend unreachable");
    }
    await loginViaApi(page, TEST_USERS.lihua);
    await page.goto("/archive/channel", { waitUntil: "networkidle" });
    // ACCESS matrix 拒 (credit_officer 无 channel) → redirect /403
    await expect(page).toHaveURL(/\/403/, { timeout: 8000 });
    await expect(page.locator('[data-testid="auth-403-page"]')).toBeVisible();
    await expect(page.locator('[data-testid="auth-403-back-today"]')).toBeVisible();
  });

  test("u_liuye (admin) 登录 + 访问 /archive/channel → OK", async ({ page }) => {
    if (!(await backendReachable(page))) {
      test.skip(true, "backend unreachable");
    }
    await loginViaApi(page, TEST_USERS.liuye);
    await page.goto("/archive/channel", { waitUntil: "networkidle" });
    await expect(page).toHaveURL(/\/archive\/channel/, { timeout: 8000 });
    // admin 全 access · channel workspace 容器渲染
    const ch = page.locator('[data-view="archive-channel"], [data-credit-started]');
    // Channel workspace data-view 或 fallback selector
    await expect(ch.first()).toBeVisible({ timeout: 8000 });
  });

  test("logout → cookie 清 · 再访问 /archive/credit → redirect /login", async ({
    page,
  }) => {
    if (!(await backendReachable(page))) {
      test.skip(true, "backend unreachable");
    }
    await loginViaApi(page, TEST_USERS.liuye);
    // 直接 call logout API (LogoutButton 等价 · 测试简化)
    const res = await page.request.post("/api/auth/logout");
    expect(res.ok()).toBeTruthy();
    // 再访问 protected path → redirect /login
    await page.goto("/archive/credit", { waitUntil: "networkidle" });
    await expect(page).toHaveURL(/\/login(\/|$|\?)/, { timeout: 8000 });
  });
});
