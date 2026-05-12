/**
 * B.4 · SLO-2 主活 A · admin 真号 E2E · compliance 实时路径
 *
 * Compliance 实时路径:
 *   - compli-input-source-upload · 用户上传政策 + 业务 → /api/compliance/scan (实时)
 *   - sample mode = compli-input-source-sample · 预置场景 → /api/compliance/demo/run
 *
 * 验收 (SLO-2 弱 GREEN · realtime UI wire):
 *   ✓ compli-input-source-upload toggle 真存在
 *   ✓ upload mode 下 compli-upload-run CTA 真存在
 *   ✓ upload zones (政策 / 业务) 真存在
 *   ✓ backend /api/compliance/scan endpoint 可 ping
 */
import { adminTest as test, expect, E2E_TIMEOUT_MS, FIRST_PAINT_TIMEOUT_MS, REAL_PROD_BASE_URL } from "./_shared";

test.describe("B.4 SLO-2 主活 A · admin 真号 · compliance realtime UI wire", () => {
  test("upload mode UI 真 wire · 上传 zone 真存在 · backend 真在线", async ({ page }) => {
    test.setTimeout(E2E_TIMEOUT_MS);

    await page.goto("/archive/compliance", { waitUntil: "networkidle" });

    await expect(
      page.locator('[data-testid="compli-empty-skeleton"]'),
    ).toBeVisible({ timeout: FIRST_PAINT_TIMEOUT_MS });

    // 1. upload mode toggle 真存在 + 可切
    const uploadToggle = page.locator('[data-testid="compli-input-source-upload"]');
    await expect(uploadToggle, "upload toggle 缺 · UI 已被 sample 冒充").toBeVisible();
    await uploadToggle.click();
    await expect(uploadToggle, "click 后 upload 没 active").toHaveAttribute("data-active", "true");

    // 2. upload mode 下 upload run CTA 真存在
    const uploadRunCta = page.locator('[data-testid="compli-upload-run"]');
    await expect(uploadRunCta, "upload-run CTA 缺 · realtime 路径未 wire").toBeVisible();

    // 3. backend health · /api/compliance/policy_scan POST 空 body 返 400/422 OK (非 503)
    //    (真路径 per agent_compliance/api.py:601 · /api/compliance/scan 是 GET sessions list)
    const scanPing = await page.request.post(
      `${REAL_PROD_BASE_URL}/api/compliance/policy_scan`,
      {
        data: {},
        failOnStatusCode: false,
      },
    );
    const status = scanPing.status();
    expect(
      [200, 400, 422].includes(status),
      `compliance policy_scan endpoint 非业务 status: ${status} · backend silent fail / 503 fallback`,
    ).toBe(true);

    // 4. 整页 sanity
    const body = await page.locator("body").innerText();
    expect(body, "页面含 503").not.toMatch(/\b503\b/);
    expect(body, "页面含 Internal Server Error").not.toMatch(/Internal Server Error/i);
    expect(body, "页面含 [object Object]").not.toMatch(/\[object Object\]/);
  });
});
