/**
 * B.4 · SLO-2 主活 A · admin 真号 E2E · compliance 实时路径
 *
 * Compliance 实时路径:
 *   - compli-input-source-upload · 用户上传政策 + 业务 → /api/compliance/scan (实时)
 *   - sample mode = compli-input-source-sample · 预置场景 → /api/compliance/demo/run
 *
 * 验收 (SLO-2 强 GREEN · realtime UI wire + 渲染态无业务 fail):
 *   ✓ compli-input-source-upload toggle 真存在
 *   ✓ upload mode 下 compli-upload-run CTA 真存在
 *   ✓ backend /api/compliance/policy_scan endpoint 可 ping (200/400/422 业务 status · 非 503)
 *   ✓ compli-error-banner count = 0 (页面初渲染无业务 fail)
 *   ✓ compli-live-fail-banner count = 0 (页面初渲染无 backend fallback)
 *   ✓ body 无 MOCK / mock fake / fallback 字样
 *
 * NOTE: codex R2 R2.1 #3 strict assertion ·
 * 旧弱标准 仅 check UI wire + backend ping · 不 verify 渲染态无 banner ·
 * 新强标准 0-banner + 无 mock/fallback body 文字阻 spec.
 * 真号 click+wait 业务 done 需 file upload (政策/业务 zip) · spec 无法 synthesize ·
 * 强 done assertion 不可行 · 用 0-banner 当 "渲染态业务无 fail" 代理.
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

    // 4. codex R2 R2.1 #3 strict · 渲染态无业务 fail banner (旧弱标准容忍 · 新强标准阻 spec)
    expect(
      await page.locator('[data-testid="compli-error-banner"]').count(),
      "compli-error-banner visible · 后端业务 fail · 阻 spec",
    ).toBe(0);
    expect(
      await page.locator('[data-testid="compli-live-fail-banner"]').count(),
      "compli-live-fail-banner visible · backend live 路径 fallback fake · 阻 spec",
    ).toBe(0);

    // 5. 整页 sanity
    const body = await page.locator("body").innerText();
    expect(body, "页面含 503").not.toMatch(/\b503\b/);
    expect(body, "页面含 Internal Server Error").not.toMatch(/Internal Server Error/i);
    expect(body, "页面含 [object Object]").not.toMatch(/\[object Object\]/);

    // 6. codex R2 R2.1 #3 strict · body 无 MOCK / fallback 字样 (silent 降级阻 spec)
    expect(
      body,
      "页面含 MOCK / mock fake / fallback · backend silent 降级 (Q-055 §4)",
    ).not.toMatch(/\bMOCK\b|mock fake|fallback/i);
  });
});
