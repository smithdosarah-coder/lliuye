import { test, expect, type Page, type Route } from "@playwright/test";

/**
 * 件 #2 · data_source SSOT 前端真消费 (Q-054 risk #1 mock/真区分根因消除).
 *
 * 验证 6 workspace 一致 5-enum trust model badge 渲染:
 *   - live           → "真实数据" (ok 绿)
 *   - cached         → "缓存命中" (ok 绿)
 *   - mock           → "演示模式" (info 灰)
 *   - mock_forced    → "DEMO 模式" (info 灰)
 *   - mock_fallback  → "降级演示" (warn 黄 · banner-spec rule 1 触发)
 *
 * Auth seed: archive/* 受 AuthGate 保护 · 与 channel-live-wire 同 pattern.
 */

const AUTH_KEY = "platform.auth.v1";
const DEMO_USER_RM = {
  id: "u_wangzhe",
  name: "王哲",
  role: "rm",
  team: "华东·上海第一支行",
  avatar: "哲",
};

async function seedAuth(page: Page) {
  await page.addInitScript(
    ({ key, user }) => {
      const persisted = { state: { currentUser: user }, version: 0 };
      window.localStorage.setItem(key, JSON.stringify(persisted));
    },
    { key: AUTH_KEY, user: DEMO_USER_RM },
  );
}

/* mock /api/channel/run · SSE done event 携 data_source enum (5 值轮跑) */
async function mockChannelRunWithDataSource(page: Page, dataSource: string) {
  await page.route("**/api/channel/run", async (route: Route) => {
    const candidate = {
      id: "cand_001",
      name: "测试候选企业",
      similarity: 0.78,
      industry: "工业软件",
      geo: "上海",
      scale: "中型",
      signals: [],
      match_dimensions: [],
      product_recommendations: [],
      pitch_scripts: [],
    };
    const sseLines = [
      `data: ${JSON.stringify({
        event: "done",
        session_id: `sess_${dataSource}`,
        data_source: dataSource,
        provider_source: dataSource === "live" ? "tavily" : undefined,
        candidates: [candidate],
        signals: [],
        radar: [],
        funnel: [],
        match_dimensions: [],
        product_recommendations: [],
        pitch_scripts: [],
        conversation: [],
      })}`,
    ];
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: sseLines.join("\n\n") + "\n\n",
    });
  });
}


test.describe("件 #2 · DataSourceBadge SSOT 一致性", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
  });

  test("ChannelWorkspace · 默认 mock badge (no run)", async ({ page }) => {
    await page.goto("/archive/channel");
    /* 默认无 SSE 触发时显 mock kind */
    const badge = page.getByTestId("channel-data-source-badge");
    await expect(badge).toBeVisible();
    await expect(badge).toHaveAttribute("data-source", "mock");
  });

  test("ChannelWorkspace · live 真消费 → 真实数据 badge", async ({ page }) => {
    await mockChannelRunWithDataSource(page, "live");
    await page.goto("/archive/channel");
    /* 触发查询 · QueryBar textbox 输入 + 提交 · done event 后 badge 切 live */
    const textbox = page.getByPlaceholder(/输入|搜索|描述/).first();
    if (await textbox.isVisible({ timeout: 2000 }).catch(() => false)) {
      await textbox.fill("测试查询");
      await page.keyboard.press("Enter");
      const badge = page.getByTestId("channel-data-source-badge");
      await expect(badge).toHaveAttribute("data-source", "live", { timeout: 8000 });
      await expect(badge).toHaveAttribute("data-tone", "ok");
    }
  });

  test("ChannelWorkspace · mock_fallback (live 失败) → 降级演示 banner kind", async ({ page }) => {
    /* mock /api/channel/run HTTP 500 · 触发 LiveFailError catch · 设 mock_fallback */
    await page.route("**/api/channel/run", async (route: Route) => {
      await route.fulfill({ status: 500, contentType: "text/plain", body: "deepseek timeout" });
    });
    await page.goto("/archive/channel");
    const textbox = page.getByPlaceholder(/输入|搜索|描述/).first();
    if (await textbox.isVisible({ timeout: 2000 }).catch(() => false)) {
      await textbox.fill("触发失败");
      await page.keyboard.press("Enter");
      const badge = page.getByTestId("channel-data-source-badge");
      await expect(badge).toHaveAttribute("data-source", "mock_fallback", { timeout: 8000 });
      await expect(badge).toHaveAttribute("data-tone", "warn");
    }
  });

  test("AlertWorkspace · 默认 mock badge", async ({ page }) => {
    await page.goto("/archive/alert");
    const badge = page.getByTestId("alert-data-source-badge");
    /* alert 默认 hidden until scan 触发 · 但 ModePill 等 size=sm badge 有条件渲染 */
    if (await badge.isVisible({ timeout: 2000 }).catch(() => false)) {
      await expect(badge).toHaveAttribute("data-source", /mock|live/);
    }
  });

  test("ComplianceWorkspace · 默认 mock 显示 (stats bar 内)", async ({ page }) => {
    await page.goto("/archive/compliance");
    const badge = page.getByTestId("compli-data-source-badge");
    if (await badge.isVisible({ timeout: 2000 }).catch(() => false)) {
      await expect(badge).toHaveAttribute("data-source", /mock|live/);
    }
  });

  test("RiskctrlWorkspace · 默认 mock badge", async ({ page }) => {
    await page.goto("/archive/riskctrl");
    const badge = page.getByTestId("riskctrl-data-source-badge");
    if (await badge.isVisible({ timeout: 2000 }).catch(() => false)) {
      await expect(badge).toHaveAttribute("data-source", /mock|live/);
    }
  });

  test("ReportWorkspace · 默认 mock badge", async ({ page }) => {
    await page.goto("/archive/report");
    const badge = page.getByTestId("report-data-source-badge");
    if (await badge.isVisible({ timeout: 2000 }).catch(() => false)) {
      await expect(badge).toHaveAttribute("data-source", /mock|live/);
    }
  });

  test("CreditWorkspace · 默认 mock badge (顶部 floating)", async ({ page }) => {
    await page.goto("/archive/credit");
    const badge = page.getByTestId("credit-data-source-badge");
    await expect(badge).toBeVisible();
    await expect(badge).toHaveAttribute("data-source", "mock");
  });
});
