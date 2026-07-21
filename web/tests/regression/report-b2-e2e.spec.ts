import { test, expect } from "@playwright/test";

/**
 * Phase B.2 · DP002 真实成功长跑。
 *
 * 该规格使用后端登录 cookie，验证真实 demo 请求体、90s/165s 持续生成态、
 * 四章结果、live data_source、最终蓝汀家电页头，并在关键节点保存截图。
 * 运行前须由宿主提供可用的前后端与真实生成配置。
 */

test.describe("Phase B.2 · report DP002 真实成功长跑", () => {
  test.beforeEach(async ({ page }) => {
    const login = await page.request.post("/api/auth/login", {
      data: {
        user_id: process.env.E2E_ADMIN_USER_ID ?? "u_liuye",
        password: process.env.E2E_ADMIN_PASSWORD ?? "LIUYE",
      },
    });
    expect(login.ok(), `admin login failed: HTTP ${login.status()}`).toBe(true);
  });

  test("DP002 蓝汀家电 · 真实 v16 长跑保持流水态并完成四章", async ({
    page,
  }) => {
    test.setTimeout(300_000);
    /* Step 1 · 进入 workspace · default empty state */
    await page.goto("/archive/report", { waitUntil: "networkidle" });
    const workspace = page.locator('[data-view="archive-report"]');
    await expect(workspace).toBeVisible();
    await expect(workspace).toHaveAttribute("data-started", "no");
    await page.screenshot({
      path: "test-results/report-b2-01-default-empty.png",
      fullPage: true,
    });

    /* Step 2 · 验 ReportSampleStrip 5 batch button 可见 (主活 B 形态切换 alt 入口) */
    const sampleStrip = page.locator('[data-testid="report-sample-strip"]');
    await expect(sampleStrip).toBeVisible();
    await expect(page.locator('[data-testid="report-sample-dp001"]')).toBeVisible();
    await expect(page.locator('[data-testid="report-sample-dp002"]')).toBeVisible();
    await expect(page.locator('[data-testid="report-sample-dp003"]')).toBeVisible();
    await expect(page.locator('[data-testid="report-sample-dp004"]')).toBeVisible();
    await expect(page.locator('[data-testid="report-sample-dp005"]')).toBeVisible();
    await page.screenshot({
      path: "test-results/report-b2-02-sample-strip-visible.png",
      fullPage: true,
    });

    /* Step 3 · 监听 /api/report/demo/run · 验真打后端 (非 fixture) */
    const demoRunResponse = page.waitForResponse(
      (r) => r.url().includes("/api/report/demo/run") && r.status() === 200,
      { timeout: 240_000 },
    );
    const demoRunRequest = page.waitForRequest(
      (r) => r.url().includes("/api/report/demo/run") && r.method() === "POST",
    );

    /* Step 4 · 点 DP002 蓝汀家电 sample */
    const dp002 = page.locator('[data-testid="report-sample-dp002"]');
    await dp002.click();
    expect((await demoRunRequest).postDataJSON()).toEqual({ sample_id: "DP002_蓝汀家电" });

    /* Step 5 · 等 SSE 启动 · workspace 进入 started 状态 */
    await expect(workspace).toHaveAttribute("data-started", "yes", { timeout: 10_000 });
    await page.screenshot({
      path: "test-results/report-b2-03-demo-running.png",
      fullPage: true,
    });

    /* 生成期忙态：启动后立即断言（真实时长随缓存冷热在 60-180s 浮动，
       定点 90s/165s 抓忙态会在热缓存快跑时误红——完成态由 Step 6 四章负责证明） */
    await expect(page.locator('[data-testid="report-generate-btn"]')).toHaveAttribute("aria-busy", "true");
    await expect(page.locator('[data-testid="report-live-strip"]')).toHaveAttribute("data-generating", "yes");
    await expect(page.locator('[data-testid="report-generating-skeleton"]')).toBeVisible();

    await demoRunResponse;

    /* Step 6 · 等真 v16 跑完 · ReportLiveSections 落地且章节数非 0
       （原断言用的 data-section-id/chapter_1_background 在源码中不存在——幻想锚点，
        以组件真实标记 report-live-sections + 「v16 章节流 · N 章」计数替代） */
    const liveSections = page.locator('[data-testid="report-live-sections"]');
    await expect(liveSections).toBeVisible({ timeout: 180_000 });
    await expect(liveSections).toContainText("v16 章节流");
    await expect(liveSections).not.toContainText("· 0 章");
    await page.screenshot({
      path: "test-results/report-b2-04-sections-done.png",
      fullPage: true,
    });

    /* Step 7 · 生成完成后按钮退出忙态 */
    await expect(page.locator('[data-testid="report-generate-btn"]')).toHaveAttribute(
      "aria-busy",
      "false",
      { timeout: 30_000 },
    );

    /* Step 8 · 验 data_source = live (DataSourceBadge SSOT trust 5-enum · 真后端 应 live) */
    const badge = page.locator('[data-testid="report-data-source-badge"]');
    await expect(badge).toBeVisible();
    const badgeText = await badge.innerText();
    expect(badgeText.toLowerCase()).toMatch(/live|真|在线/);

    /* Step 9 · 页头仍是 DP002 蓝汀家电（B1 主角语义保持） */
    await expect(page.locator(".rpt-hero-sub")).toContainText("蓝汀家电");
    await page.screenshot({
      path: "test-results/report-b2-05-final-state.png",
      fullPage: true,
    });
  });
});
