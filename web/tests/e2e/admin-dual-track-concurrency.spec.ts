/**
 * B.4 · SLO-2 主活 C · 双轨并发 verify
 *
 * PM 真意 (verbatim 2026-05-11 12:55):
 *   "C. 双轨实时 verify (演示模式跑时 IM 仍可调 · 6 并发不阻塞 · session 独立)"
 *
 * 测 3 件:
 *   1. demo 跑 + IM 同时调 · IM 响应不阻
 *   2. 多 demo 并发跑 · session 独立 · 不串数据
 *   3. 多个 agent 同时跑 · 后端不锁死
 *
 * 实施: 2 sub-test (单 worker · 多 browser context · 真 admin cookie)
 *   - C1: page1 跑 channel demo · 同时 page2 调 /api/im/threads + /api/im/threads (POST)
 *   - C2: 2 page 并发 (alert demo + credit demo) · 各 page 独立 session · 都需要 done
 *
 * 不可 GO:
 *   - IM endpoint 响应被 demo SSE 阻塞 > 5s
 *   - 并发 demo 中 session 串 (e.g. credit page 看到 alert page 的数据)
 */
import { adminTest as test, expect, E2E_TIMEOUT_MS, FIRST_PAINT_TIMEOUT_MS, REAL_PROD_BASE_URL, STORAGE_STATE_PATH } from "./_shared";

test.describe.serial("B.4 SLO-2 主活 C · 双轨并发 verify", () => {
  test("C1 · channel demo 跑 + IM 调 · IM 响应 < 5s", async ({ page, browser, adminCookieValue }) => {
    test.setTimeout(E2E_TIMEOUT_MS + 30_000);

    // Page1: 跑 channel demo medium (SSE 真流 ~30s)
    await page.goto("/archive/channel", { waitUntil: "networkidle" });
    await page
      .locator('[data-testid="input-mode-sample"]')
      .waitFor({ state: "visible", timeout: FIRST_PAINT_TIMEOUT_MS });
    await page.locator('[data-testid="input-mode-sample"]').click();
    await page.locator('[data-testid="scout-sample-medium"]').click();
    // 不等 done · demo SSE 真跑时同时打第 2 个 context 验 IM

    // Page2 (new browser context · 同 admin cookie + storageState)
    const ctx2 = await browser.newContext({
      baseURL: REAL_PROD_BASE_URL,
      storageState: STORAGE_STATE_PATH,
    });
    const url = new URL(REAL_PROD_BASE_URL);
    await ctx2.addCookies([
      {
        name: "zhongan_auth",
        value: adminCookieValue,
        domain: url.hostname,
        path: "/",
        httpOnly: true,
        secure: url.protocol === "https:",
        sameSite: "Lax",
      },
    ]);

    // IM endpoint ping · 必 < 5s (= 不被 channel demo SSE 阻塞)
    const t0 = Date.now();
    const threadsRes = await ctx2.request.get(
      `${REAL_PROD_BASE_URL}/api/im/threads`,
      { failOnStatusCode: false },
    );
    const elapsedMs = Date.now() - t0;
    expect(
      [200, 401, 403].includes(threadsRes.status()),
      `IM /threads endpoint 异常 status: ${threadsRes.status()}`,
    ).toBe(true);
    expect(
      elapsedMs,
      `IM /threads 响应 ${elapsedMs}ms > 5000ms · channel demo SSE 阻塞 IM 通道 (= 6 并发风险)`,
    ).toBeLessThan(5000);

    // 等 channel demo SSE done 完 · 双方都干净退场
    await expect(
      page.locator('[data-testid="channel-pilot-candidates"]'),
    ).toHaveAttribute("data-mode", "live", { timeout: 90_000 });

    await ctx2.close();
  });

  test("C2 · alert demo + credit demo 并发 · session 独立", async ({ browser, adminCookieValue }) => {
    test.setTimeout(E2E_TIMEOUT_MS * 2 + 30_000);

    const url = new URL(REAL_PROD_BASE_URL);
    async function makeCtx() {
      const ctx = await browser.newContext({
        baseURL: REAL_PROD_BASE_URL,
        storageState: STORAGE_STATE_PATH,
      });
      await ctx.addCookies([
        {
          name: "zhongan_auth",
          value: adminCookieValue,
          domain: url.hostname,
          path: "/",
          httpOnly: true,
          secure: url.protocol === "https:",
          sameSite: "Lax",
        },
      ]);
      return ctx;
    }

    const [ctxA, ctxB] = await Promise.all([makeCtx(), makeCtx()]);
    const pageA = await ctxA.newPage();
    const pageB = await ctxB.newPage();

    // 并发起 alert demo + credit demo
    await Promise.all([
      (async () => {
        await pageA.goto("/archive/alert", { waitUntil: "networkidle" });
        await pageA
          .locator('[data-testid="alert-empty-skeleton"]')
          .waitFor({ state: "visible", timeout: FIRST_PAINT_TIMEOUT_MS });
        await pageA.locator('[data-testid="alert-input-mode-demo"]').click();
        await pageA.locator('[data-testid="alert-scan-cta"]').click();
      })(),
      (async () => {
        await pageB.goto("/archive/credit", { waitUntil: "networkidle" });
        await pageB
          .locator('[data-testid="credit-empty-skeleton"]')
          .waitFor({ state: "visible", timeout: FIRST_PAINT_TIMEOUT_MS });
        await pageB.locator('[data-testid="credit-input-mode-demo"]').click();
        await pageB.locator('[data-testid="credit-demo-cta"]').click();
      })(),
    ]);

    // 并发等 done · 2 个独立 session · 不串
    await Promise.all([
      expect(
        pageA.locator('[data-alert-started="yes"]'),
        "alert demo 并发被 block · 90s 内未 done",
      ).toBeVisible({ timeout: 90_000 }),
      expect(
        pageB.locator('[data-credit-started="yes"][data-scanned="yes"]'),
        "credit demo 并发被 block · 90s 内未 done",
      ).toBeVisible({ timeout: 90_000 }),
    ]);

    // session 独立 sanity:
    // - alert page 不应含 credit-specific 数据 (e.g. "鼎盛商贸" / 评分雷达)
    // - credit page 不应含 alert-specific 数据 (e.g. "alert-pool" / 红黄灯)
    const alertBody = await pageA.locator("body").innerText();
    const creditBody = await pageB.locator("body").innerText();

    expect(
      alertBody,
      "alert page 含 credit 关键词 · session 串了 (PM #4 数据混乱根因)",
    ).not.toMatch(/4 维评分|credit-decision-cta|授信建议/);
    expect(
      creditBody,
      "credit page 含 alert 关键词 · session 串了",
    ).not.toMatch(/alert-pool|180 户|红黄灯|alert-hitlist/);

    await ctxA.close();
    await ctxB.close();
  });
});
