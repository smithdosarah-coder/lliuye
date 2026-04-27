import { test, expect } from "@playwright/test";

test.describe("F-004 · Forge ScanCTA Trigger", () => {
  test("ScanCTA button visible on /archive/riskctrl and click triggers progress", async ({ page }) => {
    await page.goto("/archive/riskctrl", { waitUntil: "networkidle" });
    // TODO: confirm selector after F-004 verified · ScanCTA shared component
    const scanBtn = page.locator('[data-testid="scan-trigger"]').first();
    await expect(scanBtn).toBeVisible();
    await scanBtn.click();
    const progress = page.locator('[data-testid="scan-progress"]');
    await expect(progress).toBeVisible({ timeout: 3000 });
  });
});
