import { test, expect } from "@playwright/test";

test.describe("F-007 · Today Page Empty State (no PriorityQueue/Timeline/KPI)", () => {
  test("today page should NOT contain priority queue, event timeline, or kpi belt blocks", async ({
    page,
  }) => {
    await page.goto("/today", { waitUntil: "networkidle" });
    await expect(page.locator('[data-testid="today-priority-queue"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="today-event-timeline"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="today-kpi-belt"]')).toHaveCount(0);
    // 兜底文案断言 (data-testid 未列时按 inventory MUST NOT 文案抓)
    await expect(page.getByText("今日队列")).toHaveCount(0);
    await expect(page.getByText("事件流")).toHaveCount(0);
    await expect(page.getByText("本月已放款")).toHaveCount(0);
  });
});
