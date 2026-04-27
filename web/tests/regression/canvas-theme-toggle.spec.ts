import { test, expect } from "@playwright/test";

test.describe("F-002 + F-003 · Canvas & Theme Pills", () => {
  test("dual pills visible at bottom-right + theme click switches data-theme", async ({ page }) => {
    await page.goto("/today", { waitUntil: "networkidle" });
    const canvasToggle = page.locator('[data-testid="canvas-mode-toggle"]');
    const themeSwitch = page.locator(".theme-sw-trigger").first();
    await expect(canvasToggle).toBeVisible();
    await expect(themeSwitch).toBeVisible();
    await themeSwitch.click();
    const matchaBtn = page.locator('.theme-sw-pop button[data-t="matcha"]');
    await matchaBtn.click();
    const bodyTheme = await page.evaluate(() =>
      document.body.getAttribute("data-theme"),
    );
    expect(bodyTheme).toBe("matcha");
  });
});
