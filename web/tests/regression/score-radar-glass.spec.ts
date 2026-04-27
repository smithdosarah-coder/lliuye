import { test, expect } from "@playwright/test";

test.describe("F-006 · ScoreRadar 8-axis Visual", () => {
  test("score radar renders on /archive/channel", async ({ page }) => {
    await page.goto("/archive/channel", { waitUntil: "networkidle" });
    // TODO: confirm selector after F-006 redesigned · 当前 ScoreRadar 使用 recharts PolarGrid
    const radar = page.locator(".recharts-radar, [data-testid=\"score-radar\"]").first();
    await expect(radar).toBeVisible();
    // F-006 redesign 后改成 visual snapshot 守门:
    // await expect(radar).toHaveScreenshot("score-radar-glass.png");
  });
});
