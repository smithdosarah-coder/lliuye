import { test, expect } from "@playwright/test";

/**
 * F-061 · Riskctrl + Alert live-fallback banner (W-FIX-A3 · live-fallback-banner-spec v1.0).
 *
 * 验:
 *   1. Riskctrl backtest 422 → live-fail banner 显 (HTTP 422 · retry button)
 *   2. Riskctrl dsl_gen 5xx → banner (HTTP 500)
 *   3. Alert scan SSE error → banner (network/SSE)
 *   4. Alert scan 200 → 不弹 banner (live mode 通)
 */

test.describe("F-061 · Riskctrl + Alert live-fallback banner", () => {
  test("Riskctrl backtest 422 · banner 显 + retry button + body excerpt", async ({ page }) => {
    /* mock backend 422 · 模拟 backend 必填 uploaded_files 缺失 */
    await page.route("**/api/riskctrl/backtest", async (route) => {
      await route.fulfill({
        status: 422,
        contentType: "application/json",
        body: JSON.stringify({
          detail: [
            { type: "missing", loc: ["body", "uploaded_files"], msg: "Field required" },
          ],
        }),
      });
    });
    await page.route("**/api/riskctrl/dsl_gen", async (route) => {
      const sse = [
        'data: {"event":"stage","payload":{"phase":"dsl_generation","ruleset_id":"rs-mock-1"}}',
        '',
        'data: {"event":"done"}',
        '',
        '',
      ].join("\n");
      await route.fulfill({
        status: 200,
        headers: { "content-type": "text/event-stream; charset=utf-8" },
        body: sse,
      });
    });

    await page.goto("/archive/riskctrl", { waitUntil: "networkidle" });

    /* Primary CTA · 启动 (mock dsl_gen 200) · 进 started=yes */
    const dslCta = page.locator('[data-testid="riskctrl-dsl-gen-cta"]');
    await dslCta.click();
    await expect(page.locator('[data-testid="riskctrl-workspace"]')).toHaveAttribute(
      "data-started", "yes",
    );

    /* 触发 backtest (ScanCTA · 5 step 假进度) · 然后真后端 fetch · 422 banner */
    /* 找 ScanCTA 内的 button (进度模拟 + onDone trigger backtest) */
    const backtestSection = page.locator('[data-testid="riskctrl-backtest-cta"]');
    await expect(backtestSection).toBeVisible();
    /* ScanCTA 按钮文案是 "样本回测" */
    const btn = backtestSection.getByRole("button", { name: /样本回测|扫描中|重试/ });
    await btn.click();

    /* 等假进度 + onDone 触发 backtest (5 step × 450ms ≈ 2.5s) · 用 4s timeout */
    const banner = page.locator('[data-testid="riskctrl-live-fail-banner"]');
    await expect(banner).toBeVisible({ timeout: 6000 });
    await expect(banner).toHaveAttribute("data-status", "422");
    await expect(banner).toContainText(/HTTP 422/);
    await expect(banner).toContainText(/样本回测/);

    /* retry button 存在 */
    await expect(page.locator('[data-testid="riskctrl-live-fail-retry"]')).toBeVisible();
  });

  test("Riskctrl dsl_gen 500 · banner 显 + 重试可点", async ({ page }) => {
    await page.route("**/api/riskctrl/dsl_gen", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "INTERNAL", message: "LLM timeout" } }),
      });
    });

    await page.goto("/archive/riskctrl", { waitUntil: "networkidle" });
    await page.locator('[data-testid="riskctrl-dsl-gen-cta"]').click();

    const banner = page.locator('[data-testid="riskctrl-live-fail-banner"]');
    await expect(banner).toBeVisible({ timeout: 4000 });
    await expect(banner).toHaveAttribute("data-status", "500");
    await expect(banner).toContainText(/DSL 生成/);
    await expect(banner).toContainText(/HTTP 500/);
  });

  test("Alert scan SSE 5xx · banner 显 (启动扫描 wire 真后端)", async ({ page }) => {
    await page.route("**/api/alert/scan", async (route) => {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "service unavailable" }),
      });
    });

    await page.goto("/archive/alert", { waitUntil: "networkidle" });

    /* 找「启动风险扫描」按钮 · HeroSection.onScan */
    const scanBtn = page.getByRole("button", { name: /启动风险扫描|扫描中|重新扫描/ });
    await scanBtn.click();

    const banner = page.locator('[data-testid="alert-live-fail-banner"]');
    await expect(banner).toBeVisible({ timeout: 4000 });
    await expect(banner).toHaveAttribute("data-status", "503");
    await expect(banner).toContainText(/alert scan/);
    await expect(banner).toContainText(/HTTP 503/);
    await expect(page.locator('[data-testid="alert-live-fail-retry"]')).toBeVisible();
  });

  test("Alert scan 200 · 不显 banner (live 通 · scanSessionId 落入 DOM)", async ({ page }) => {
    await page.route("**/api/alert/scan", async (route) => {
      const sse = [
        'data: {"event":"stage","payload":{"type":"tool_result","tool":"search_provider","result":"mock"}}',
        '',
        'data: {"event":"stage","payload":{"type":"session","session_id":"alert-spec-001","mode":"demo_forced"}}',
        '',
        'data: {"event":"done"}',
        '',
        '',
      ].join("\n");
      await route.fulfill({
        status: 200,
        headers: { "content-type": "text/event-stream; charset=utf-8" },
        body: sse,
      });
    });

    await page.goto("/archive/alert", { waitUntil: "networkidle" });
    const scanBtn = page.getByRole("button", { name: /启动风险扫描|扫描中|重新扫描/ });
    await scanBtn.click();

    /* 等真后端 SSE 完 + 假进度 (5 step × 500ms · ~3s) */
    await page.waitForTimeout(3500);
    /* banner 不应出现 */
    await expect(page.locator('[data-testid="alert-live-fail-banner"]')).toHaveCount(0);
    /* scanSessionId 落入 root data-attr */
    const root = page.locator('[data-testid="alert-workspace"]');
    await expect(root).toHaveAttribute("data-scan-session-id", "alert-spec-001");
  });
});
