/**
 * B.3.4 · P0-R5 · 主活 B · admin 真号 E2E · alert
 *
 * PM 真意:
 *   登录 admin · 扫 alert-pool 180 户 (scenario_key=baseline_100 · /api/alert/demo/run)
 *   · 验 红 ≥ 1 + 黄 ≥ 1 真出 + drill drawer 可点
 *
 * 触发: alert-input-mode-demo → alert-scan-cta (= 一键示例 + 触发扫描)
 *   per AlertWorkspace.tsx:2088,2158
 */
import { adminTest as test, expect, E2E_TIMEOUT_MS } from "./_shared";

test.describe("B.3.4 · admin 真号 · alert 预警 demo 180 户", () => {
  test("扫 alert-pool · 红 ≥ 1 + 黄 ≥ 1 + drill drawer 可点", async ({ page }) => {
    test.setTimeout(E2E_TIMEOUT_MS);

    await page.goto("/archive/alert", { waitUntil: "networkidle" });

    // 切 demo 输入模式 (= 用 alert-pool 180 户 batch) · 点扫描 CTA
    await expect(
      page.locator('[data-testid="alert-empty-skeleton"]'),
    ).toBeVisible();
    await page.locator('[data-testid="alert-input-mode-demo"]').click();
    await page.locator('[data-testid="alert-scan-cta"]').click();

    // SSE done → alert-started=yes · 红/黄/绿 traffic-light 已 render
    await expect(
      page.locator('[data-alert-started="yes"]'),
    ).toBeVisible({ timeout: 60_000 });

    // 红 ≥ 1 (per PM "红 ≥ 1 真出")
    const redLight = page.locator('[data-testid="alert-traffic-light-red"]');
    await expect(redLight).toBeVisible();
    // 黄 ≥ 1
    const yellowLight = page.locator('[data-testid="alert-traffic-light-yellow"]');
    await expect(yellowLight).toBeVisible();

    // hitlist 真有客户行 (≥ 2 = 至少 1 红 + 1 黄)
    const hitRows = page.locator('[data-testid="alert-hitlist-row"]');
    await expect(hitRows).not.toHaveCount(0);
    const rowCount = await hitRows.count();
    expect(rowCount, "hitlist row 数量").toBeGreaterThanOrEqual(2);

    // 点第一行 → drill drawer 弹出 + 可见 (per PM "drill drawer 可点")
    await hitRows.first().click();
    await expect(
      page.locator('[data-testid="alert-drill-drawer"]'),
    ).toBeVisible({ timeout: 10_000 });

    // drawer 加载完 (drill-loading 消失 或 drill-fail 不出)
    await expect(
      page.locator('[data-testid="alert-drill-fail"]'),
    ).toHaveCount(0);
  });
});
