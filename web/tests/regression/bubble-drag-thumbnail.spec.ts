import { test, expect } from "@playwright/test";

test.describe("F-008 · Bubble Drag to Whiteboard · Thumbnail (not URL link)", () => {
  test("drag message bubble handle to whiteboard creates thumbnail card", async ({ page }) => {
    await page.goto("/dispatch", { waitUntil: "networkidle" });
    const dragHandle = page.locator('[data-pin-handle="message"]').first();
    // TODO: confirm whiteboard drop zone selector after F-008 restored
    const whiteboardArea = page.locator('[data-testid="whiteboard-drop-zone"]').first();
    await dragHandle.dragTo(whiteboardArea);
    const thumbnail = page.locator('[data-pin-type="message"]');
    await expect(thumbnail).toBeVisible();
    // F-008 约束: 不允许是 url 链接形态
    const hrefCount = await thumbnail.locator("a[href]").count();
    expect(hrefCount).toBe(0);
  });
});
