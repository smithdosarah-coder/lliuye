/**
 * B.4 · SLO-2 主活 A · admin 真号 E2E · alert 实时路径
 *
 * Alert 实时路径 (per AlertWorkspace.tsx:518):
 *   - alert-input-mode-live · 客户经理上传名录 + 规则 → /api/alert/scan
 *   - demo mode 同 pipeline · 仅输入源不同 (alert-pool 180 户 fixture)
 *
 * 验收 (SLO-2 弱 GREEN · realtime UI wire):
 *   ✓ alert-input-mode-live toggle 真存在
 *   ✓ live mode preview card 显 "客户名录 · Excel/CSV" (= real input 引导)
 *   ✓ alert-scan-cta 真存在
 *   ✓ backend /api/alert/scan endpoint 可 ping (非 503)
 */
import { adminTest as test, expect, E2E_TIMEOUT_MS, FIRST_PAINT_TIMEOUT_MS, REAL_PROD_BASE_URL } from "./_shared";

test.describe("B.4 SLO-2 主活 A · admin 真号 · alert realtime UI wire", () => {
  test("live mode UI 真 wire · preview 显客户名录 · backend 真在线", async ({ page }) => {
    test.setTimeout(E2E_TIMEOUT_MS);

    await page.goto("/archive/alert", { waitUntil: "networkidle" });

    await expect(
      page.locator('[data-testid="alert-empty-skeleton"]'),
    ).toBeVisible({ timeout: FIRST_PAINT_TIMEOUT_MS });

    // 1. live mode toggle 真存在
    const liveToggle = page.locator('[data-testid="alert-input-mode-live"]');
    await expect(liveToggle, "live mode toggle 缺 · UI 已被 demo 冒充").toBeVisible();
    await liveToggle.click();
    await expect(liveToggle, "click 后 live mode 没 active").toHaveAttribute("data-active", "yes");

    // 2. live mode preview 显客户名录引导 (= real input 引导 · 不被 demo "180 户" 文案替代)
    const preview = page.locator('[data-testid="alert-input-preview"]');
    await expect(preview).toHaveAttribute("data-mode", "live");
    const previewText = await preview.innerText();
    expect(previewText, "live preview 仍显 180 户 (= demo 文案没切)").not.toMatch(/180\s*户/);
    expect(previewText, "live preview 无客户名录引导").toMatch(/客户名录|名录|上传/);

    // 3. alert-scan-cta 真存在
    const scanCta = page.locator('[data-testid="alert-scan-cta"]');
    await expect(scanCta, "scan-cta 缺 · realtime 路径未 wire").toBeVisible();

    // 4. backend health · /api/alert/scan endpoint 可 ping (POST 无 body 返 400 OK · 非 503)
    const scanPing = await page.request.post(
      `${REAL_PROD_BASE_URL}/api/alert/scan`,
      {
        data: {},
        failOnStatusCode: false,
      },
    );
    const status = scanPing.status();
    expect(
      [200, 400, 422].includes(status),
      `alert scan endpoint 非业务 status: ${status} · backend silent fail / 503 fallback`,
    ).toBe(true);

    // 5. 整页不允许 503 / mock fake / [object
    const body = await page.locator("body").innerText();
    expect(body, "页面含 503").not.toMatch(/\b503\b/);
    expect(body, "页面含 Internal Server Error").not.toMatch(/Internal Server Error/i);
    expect(body, "页面含 [object Object]").not.toMatch(/\[object Object\]/);
  });
});
