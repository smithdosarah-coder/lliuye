import { test, expect } from "@playwright/test";

test.describe("F-001 · Logout Button", () => {
  test("logout button visible and click redirects to /login", async ({ page }) => {
    await page.goto("/today", { waitUntil: "networkidle" });
    const logoutBtn = page.locator('[data-testid="logout-button"]');
    await expect(logoutBtn).toBeVisible();
    await logoutBtn.click();
    await page.waitForURL(/\/login/, { timeout: 5000 });
    expect(page.url()).toContain("/login");
  });
});
