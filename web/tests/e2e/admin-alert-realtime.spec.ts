/**
 * B.4 · SLO-2 主活 A · admin 真号 E2E · alert 实时路径
 *
 * Alert 实时路径 (per AlertWorkspace.tsx:518):
 *   - alert-input-mode-live · 客户经理上传名录 + 规则 → /api/alert/scan
 *   - demo mode 同 pipeline · 仅输入源不同 (alert-pool 180 户 fixture)
 *
 * 验收 (SLO-2 强 GREEN · realtime UI wire + click+wait 真业务 done):
 *   ✓ alert-input-mode-live toggle 真存在
 *   ✓ live mode preview card 显 "客户名录 · Excel/CSV" (= real input 引导)
 *   ✓ alert-scan-cta 真存在
 *   ✓ backend /api/alert/scan endpoint 可 ping (非 503)
 *   ✓ click scan-cta 后 60s 内 data-alert-started="yes" (业务真启动)
 *   ✓ alert-workspace data-data-source="live" (真 live · 非 mock_fallback)
 *   ✓ alert-scan-error-banner count = 0 (业务无 fail)
 *   ✓ alert-backend-fallback-banner count = 0 (backend 无 fallback fake)
 *   ✓ alert-live-fail-banner count = 0
 *   ✓ body 无 MOCK / mock fake / fallback 字样
 *
 * NOTE: codex R2 R2.1 #3 strict assertion ·
 * 旧弱标准 仅 check UI wire + backend ping · 不 click CTA · 不 verify business done.
 * alert 是 6 agent 里唯一 click+wait 可行 (scenarioKey 可空 · backend 自跑) ·
 * 因此本 spec 加 full click+wait flow + data-data-source="live" 强断言.
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

    // 5. codex R2 R2.1 #3 strict · click scan-cta + 60s 等业务 done
    //    NOTE: alert scenarioKey 可空 · backend 自走默认 scenario · spec 不需要 file upload
    //    旧弱标准 完全没 click · 新强标准 click + 等 data-alert-started="yes"
    await scanCta.click();

    const workspaceLocator = page.locator('[data-testid="alert-workspace"]');
    await expect(
      workspaceLocator,
      "click scan-cta 60s data-alert-started 没切 yes · backend SSE silent swallow",
    ).toHaveAttribute("data-alert-started", "yes", { timeout: 60_000 });

    // 6. data-data-source = "live" (per _data-source.ts SSOT · "mock_fallback" 阻 spec)
    //    若 backend 真 live 跑通 · setCurrentDataSource("live") · data-data-source 显 "live"
    //    若 backend live 路径 fail · setCurrentDataSource("mock_fallback") · 阻 spec
    await expect(
      workspaceLocator,
      'data-data-source ≠ "live" · backend live 路径 fallback 假数据 (Q-055 §4)',
    ).toHaveAttribute("data-data-source", "live", { timeout: 60_000 });

    // 7. 渲染态无业务 fail banner (旧弱标准容忍 · 新强标准阻 spec)
    expect(
      await page.locator('[data-testid="alert-scan-error-banner"]').count(),
      "alert-scan-error-banner visible · 后端业务 fail · 阻 spec",
    ).toBe(0);
    expect(
      await page.locator('[data-testid="alert-backend-fallback-banner"]').count(),
      "alert-backend-fallback-banner visible · backend emit fallback envelope · 阻 spec",
    ).toBe(0);
    expect(
      await page.locator('[data-testid="alert-live-fail-banner"]').count(),
      "alert-live-fail-banner visible · live 路径异常 · 阻 spec",
    ).toBe(0);

    // 8. 整页不允许 503 / mock fake / [object
    const body = await page.locator("body").innerText();
    expect(body, "页面含 503").not.toMatch(/\b503\b/);
    expect(body, "页面含 Internal Server Error").not.toMatch(/Internal Server Error/i);
    expect(body, "页面含 [object Object]").not.toMatch(/\[object Object\]/);

    // 9. codex R2 R2.1 #3 strict · body 无 MOCK / fallback 字样 (silent 降级阻 spec)
    expect(
      body,
      "页面含 MOCK / mock fake / fallback · backend silent 降级 (Q-055 §4)",
    ).not.toMatch(/\bMOCK\b|mock fake|fallback/i);
  });
});
