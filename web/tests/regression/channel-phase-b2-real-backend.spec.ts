import { test, expect } from "@playwright/test";

/**
 * Phase B.2 真意 reframe (PM 2026-05-10) · channel real-backend E2E spec
 *
 * 验整链路 (与 Step 11 admin E2E 4 件套配套):
 *   T1 · 形态切换 toggle 默认 free · 切 sample 后 3 难度按钮 visible
 *   T2 · sample 形态点 medium · /api/channel/demo/run 收 demo_context 事件 · 透出 sample_files
 *   T3 · TAVILY 缺时 typed banner TAVILY_KEY_MISSING_FOR_DEMO · 不 silent fallback
 *   T4 · 双形态都打不同 endpoint · free → /run · sample → /demo/run
 *
 * 关键 selector (Phase B.2 新增):
 *   [data-testid="input-mode-free"]
 *   [data-testid="input-mode-sample"]
 *   [data-testid="scout-sample-{easy,medium,hard}"]
 *   [data-testid="scout-demo-context"]
 *   [data-testid="channel-empty-state"]
 *
 * Auth bypass: localStorage seed `platform.auth.v1` (Zustand persist)
 */

const MOCK_ME_RESPONSE = {
  user: {
    id: "u_admin_e2e",
    name: "Admin E2E",
    role: "admin",
    team: "总部",
    avatar: "管",
  },
  roles: ["admin"],
  accessibleAgents: ["channel", "report", "credit", "alert", "compli", "riskctrl"],
};

test.beforeEach(async ({ context }) => {
  await context.route("**/api/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_ME_RESPONSE),
    });
  });
});

test.describe("Phase B.2 · channel · 真后端形态 E2E", () => {
  test("T1 · 形态切换默认 free · sample 切换显 3 档难度", async ({ page }) => {
    await page.goto("/archive/channel", { waitUntil: "networkidle" });

    // 默认 free 形态 active · sample tab 存在但未选
    const freeTab = page.locator('[data-testid="input-mode-free"]');
    const sampleTab = page.locator('[data-testid="input-mode-sample"]');
    await expect(freeTab).toBeVisible();
    await expect(sampleTab).toBeVisible();
    await expect(freeTab).toHaveAttribute("aria-selected", "true");
    await expect(sampleTab).toHaveAttribute("aria-selected", "false");

    // free 形态: input + AI 搜索 button visible · sample 按钮 hidden
    await expect(page.locator('[data-testid="scout-search"]')).toBeVisible();
    await expect(page.locator('[data-testid="scout-sample-medium"]')).toHaveCount(0);

    // 切到 sample · 3 档按钮 + demo_context 容器 visible
    await sampleTab.click();
    await expect(sampleTab).toHaveAttribute("aria-selected", "true");
    await expect(page.locator('[data-testid="scout-sample-easy"]')).toBeVisible();
    await expect(page.locator('[data-testid="scout-sample-medium"]')).toBeVisible();
    await expect(page.locator('[data-testid="scout-sample-hard"]')).toBeVisible();
    // 切回 free · sample 按钮重新 hidden
    await freeTab.click();
    await expect(page.locator('[data-testid="scout-sample-medium"]')).toHaveCount(0);
  });

  test("T2 · sample 形态点 medium · 真后端 demo_context 事件透出 sample_files", async ({
    page,
    context,
  }) => {
    let demoBody: { scenario_id?: string } | null = null;
    await context.route("**/api/channel/demo/run", async (route) => {
      try {
        demoBody = route.request().postDataJSON() as { scenario_id?: string };
      } catch {
        demoBody = null;
      }
      const sse = [
        `event: demo_context\ndata: ${JSON.stringify({
          event: "demo_context",
          scenario_id: "medium",
          sample_source: "data/mock/channel-kb/marketing-preferences",
          sample_files: ["2026-Q2-区域重点.docx", "2026-Q1-重点拓展.docx"],
          derived_seed_query: "苏州 半导体 专精特新 企业",
          tavily_configured: true,
          pipeline: "run_channel_search_stream (real)",
        })}\n\n`,
        `event: stage\ndata: ${JSON.stringify({ event: "stage", stage: "parse", status: "done" })}\n\n`,
        `event: done\ndata: ${JSON.stringify({
          event: "done",
          data_source: "live",
          session_id: "demo_e2e_test",
          metrics: { signalTotal: 8, companiesFound: 4, final: 3 },
          candidates: [
            { id: "uscc_TESTUSCCFORE2E1", name: "E2E 测试候选", similarity: 0.78, industry: "半导体", geo: "苏州", scale: "中型", signals: [], riskTags: [], products: [], match_dimensions: [], product_recommendations: [], pitch_scripts: [] },
          ],
          radar: [], signals: [], funnel: [{ id: "f1", label: "signal", count: 8 }, { id: "f2", label: "final", count: 3 }],
          match_dimensions: [], product_recommendations: [], pitch_scripts: [], conversation: [],
        })}\n\n`,
      ].join("");
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: sse,
      });
    });

    await page.goto("/archive/channel", { waitUntil: "networkidle" });
    await page.locator('[data-testid="input-mode-sample"]').click();
    await page.locator('[data-testid="scout-sample-medium"]').click();
    await page.waitForTimeout(500);

    // 验 endpoint 收到 scenario_id="medium"
    expect(demoBody).toEqual({ scenario_id: "medium" });

    // demo_context UI 透出 sample 文件名 + 派生 query (透明演示)
    const ctx = page.locator('[data-testid="scout-demo-context"]');
    await expect(ctx).toBeVisible();
    await expect(ctx).toContainText("2026-Q2-区域重点.docx");
    await expect(ctx).toContainText("苏州 半导体 专精特新 企业");

    // candidates panel 真实 hydrate (live 数据)
    await expect(
      page.locator('[data-testid="channel-pilot-candidates"]'),
    ).toHaveAttribute("data-mode", "live");
  });

  test("T3 · TAVILY 缺时 typed banner · 不 silent fallback fake", async ({
    page,
    context,
  }) => {
    await context.route("**/api/channel/demo/run", async (route) => {
      // 模拟 backend yield typed error event
      const sse = [
        `event: demo_context\ndata: ${JSON.stringify({
          event: "demo_context",
          scenario_id: "easy",
          sample_source: "data/mock/channel-kb/marketing-preferences",
          sample_files: ["2026-Q1-重点拓展.docx"],
          derived_seed_query: "高端制造 专精特新 企业",
          tavily_configured: false,
          pipeline: "run_channel_search_stream (real)",
        })}\n\n`,
        `event: error\ndata: ${JSON.stringify({
          event: "error",
          stage: "search",
          code: "TAVILY_KEY_MISSING_FOR_DEMO",
          message: "TAVILY_API_KEY 未配置 · 真后端演示需 Tavily 实搜",
        })}\n\n`,
      ].join("");
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: sse,
      });
    });

    await page.goto("/archive/channel", { waitUntil: "networkidle" });
    await page.locator('[data-testid="input-mode-sample"]').click();
    await page.locator('[data-testid="scout-sample-easy"]').click();
    await page.waitForTimeout(500);

    // typed banner 显 · 含 error code 关键字
    const banner = page.locator(
      '[data-testid="channel-pilot-banner-live-fail"]',
    );
    await expect(banner).toBeVisible();
    await expect(banner).toContainText("TAVILY_KEY_MISSING_FOR_DEMO");

    // candidates panel 不应进入 live 模式 (没有真后端数据)
    const candidatesPanel = page.locator(
      '[data-testid="channel-pilot-candidates"]',
    );
    // panel 仍 mock 模式 (因为 done event 没收到 · live 数据没 ready)
    await expect(candidatesPanel).not.toHaveAttribute("data-mode", "live");
  });

  test("T4 · 双形态打不同 endpoint · free → /run · sample → /demo/run", async ({
    page,
    context,
  }) => {
    let runHit = false;
    let demoHit = false;
    await context.route("**/api/channel/run", async (route) => {
      runHit = true;
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: `event: done\ndata: ${JSON.stringify({
          event: "done",
          data_source: "live",
          session_id: "free_test",
          metrics: { signalTotal: 0, companiesFound: 0, final: 0 },
          candidates: [], radar: [], signals: [], funnel: [{ id: "f1", label: "x", count: 0 }, { id: "f2", label: "y", count: 0 }],
          match_dimensions: [], product_recommendations: [], pitch_scripts: [], conversation: [],
        })}\n\n`,
      });
    });
    await context.route("**/api/channel/demo/run", async (route) => {
      demoHit = true;
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: `event: demo_context\ndata: ${JSON.stringify({
          event: "demo_context",
          scenario_id: "easy",
          sample_source: "data/mock/channel-kb/marketing-preferences",
          sample_files: ["2026-Q1-重点拓展.docx"],
          derived_seed_query: "test query",
          tavily_configured: true,
          pipeline: "run_channel_search_stream (real)",
        })}\n\nevent: done\ndata: ${JSON.stringify({
          event: "done",
          data_source: "live",
          session_id: "demo_test",
          metrics: { signalTotal: 0, companiesFound: 0, final: 0 },
          candidates: [], radar: [], signals: [], funnel: [{ id: "f1", label: "x", count: 0 }, { id: "f2", label: "y", count: 0 }],
          match_dimensions: [], product_recommendations: [], pitch_scripts: [], conversation: [],
        })}\n\n`,
      });
    });

    await page.goto("/archive/channel", { waitUntil: "networkidle" });

    // free 形态: 类型 query + 点 search · 应打 /run · 不打 /demo/run
    await page.locator('[data-testid="input-mode-free"]').click();
    await page.locator('.ch-querybar-input').fill("江苏 半导体 中型企业");
    await page.locator('[data-testid="scout-search"]').click();
    await page.waitForTimeout(400);
    expect(runHit).toBe(true);
    expect(demoHit).toBe(false);

    // sample 形态: 点 medium · 应打 /demo/run
    await page.locator('[data-testid="input-mode-sample"]').click();
    await page.locator('[data-testid="scout-sample-medium"]').click();
    await page.waitForTimeout(400);
    expect(demoHit).toBe(true);
  });
});
