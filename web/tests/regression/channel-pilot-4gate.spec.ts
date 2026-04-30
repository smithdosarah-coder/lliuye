import { test, expect } from "@playwright/test";

/**
 * Phase A worker-A3 · channel pilot · 4 gate state model + done envelope + banner-spec rule 2
 *
 * 验:
 *   T1 · gate 1+2 (started + selectedSession) · 切下拉 + 切换演示 → 5 panel 同步亮
 *   T2 · gate 3 (liveData) · /api/channel/run mock SSE 7-panel envelope → 5 panel + isLive 指示
 *   T3 · gate 4 (selectedCandidate) · 候选 click → drawer 出 · ESC 关
 *   T4 · banner-spec rule 2 · backend stage warning + done.warnings → mock-fallback banner
 *
 * Auth bypass: localStorage seed `platform.auth.v1` (Zustand persist) · rm 全 ACCESS
 */

/* Auth bypass · mock /api/auth/me 拒绝走 backend (无 uvicorn 时 ECONNREFUSED · AuthGate redirect /login)
   返 rm 全 ACCESS · channel/report/credit/alert/compli/riskctrl 6 agent 全开 */
const MOCK_ME_RESPONSE = {
  user: {
    id: "u_wangzhe",
    name: "王哲",
    role: "rm",
    team: "华东·上海第一支行",
    avatar: "哲",
  },
  roles: ["rm"],
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

test.describe("worker-A3 · channel pilot · 4 gate", () => {
  test("T1 · gate 1+2 mock session select → 5 panel sync", async ({ page }) => {
    await page.goto("/archive/channel", { waitUntil: "networkidle" });

    const sessionSelect = page.locator('[data-testid="channel-session-select"]');
    const sessionApply = page.locator('[data-testid="channel-session-apply"]');

    // 默认 started=false · 走切换演示触发 started=true (apply button 含 setStarted(true))
    await sessionSelect.selectOption("sess_haichao");
    // 默认 pending===selected · apply disabled · 改选别的 session 让 button enabled
    await sessionSelect.selectOption("sess_zhirong");
    await sessionApply.click();
    await page.waitForTimeout(300);

    // 5 panel 全亮 (data-testid 在 panel section root)
    for (const k of ["radar", "funnel", "candidates", "signals", "conversation"]) {
      await expect(
        page.locator(`[data-testid="channel-pilot-${k}"]`),
      ).toBeVisible();
    }

    // candidates panel 模式 mock (非 live)
    await expect(
      page.locator('[data-testid="channel-pilot-candidates"]'),
    ).toHaveAttribute("data-mode", "mock");
  });

  test("T2 · gate 3 liveData · /api/channel/run mock SSE → 7 panel hydrate + isLive=true", async ({
    page,
    context,
  }) => {
    // 拦 /api/channel/run · 注入扁平 7-panel done envelope (per shared/sse_envelope.make_done)
    await context.route("**/api/channel/run", async (route) => {
      const sse = [
        // 6 stage running/done (压缩单段 · 让流总结束)
        `event: stage\ndata: ${JSON.stringify({ event: "stage", stage: "parse", status: "done", tags: [] })}\n\n`,
        `event: stage\ndata: ${JSON.stringify({ event: "stage", stage: "rank", status: "done" })}\n\n`,
        // done · 7 panel + metrics + data_source=live + session_id
        `event: done\ndata: ${JSON.stringify({
          event: "done",
          data_source: "live",
          session_id: "test-live-1",
          metrics: { signalTotal: 10, companiesFound: 5, final: 3 },
          warnings: [],
          candidates: [
            {
              id: "live-1",
              name: "Test 测试候选公司",
              similarity: 0.81,
              industry: "测试行业",
              geo: "测试区域",
              scale: "测试规模",
              signals: [],
              riskTags: [],
              products: [],
              match_dimensions: [],
              product_recommendations: [],
              pitch_scripts: [],
            },
          ],
          radar: [
            { axis: "信号密度", score: 80, benchmark: 50, quadrant: "base" },
            { axis: "行业匹配", score: 75, benchmark: 50, quadrant: "base" },
          ],
          signals: [
            { id: "s1", key: "biz", label: "工商", status: "active", weight: 0.2, freq: "T+1", coverage: 80, hits: 3 },
          ],
          funnel: [
            { id: "f1", label: "信号池", count: 1000 },
            { id: "f2", label: "Top 推荐", count: 3 },
          ],
          match_dimensions: [],
          product_recommendations: [],
          pitch_scripts: [],
        })}\n\n`,
      ].join("");
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: sse,
      });
    });

    await page.goto("/archive/channel", { waitUntil: "networkidle" });

    // 起 textbox · 触发 live
    const input = page.locator(".ch-querybar-input");
    await input.fill("测试 query · 自由输入触发 live");
    await page.locator('[data-testid="scout-search"]').click();
    await page.waitForTimeout(500);

    // 5 panel 全亮 · candidates 切到 live 模式 (data-mode="live")
    for (const k of ["radar", "funnel", "candidates", "signals", "conversation"]) {
      await expect(
        page.locator(`[data-testid="channel-pilot-${k}"]`),
      ).toBeVisible();
    }
    await expect(
      page.locator('[data-testid="channel-pilot-candidates"]'),
    ).toHaveAttribute("data-mode", "live");

    // 候选已切到 live 注入的 Test 测试候选
    const firstCand = page.locator(".ch-cd-name").first();
    await expect(firstCand).toContainText("Test 测试候选公司");
  });

  test("T3 · gate 4 selectedCandidate · candidate click → drawer 必显 · ESC 关", async ({
    page,
  }) => {
    await page.goto("/archive/channel", { waitUntil: "networkidle" });

    // 走 mock session 让 started=true
    await page.locator('[data-testid="channel-session-select"]').selectOption("sess_zhirong");
    await page.locator('[data-testid="channel-session-apply"]').click();
    await page.waitForTimeout(300);

    // V2 issue 4 · drawer 必显 (不再 conditional) · click candidate card → drawer visible
    const card = page.locator('[data-testid="channel-candidate-card"]').first();
    await expect(card).toBeVisible();
    await card.click();

    const drawer = page.locator('[data-testid="channel-candidate-drawer"]');
    await expect(drawer).toBeVisible();

    // ESC 关闭 · drawer 隐
    await page.keyboard.press("Escape");
    await expect(drawer).toBeHidden();
  });

  test("T5 · demo run · /api/channel/demo/run wired · data_source=mock_forced + 5 panel hydrate", async ({
    page,
    context,
  }) => {
    // V2 issue 2 · 验 demo button 调对 endpoint + payload + done envelope data_source=mock_forced
    let demoEndpointHit = false;
    let demoScenarioPayload: string | null = null;
    await context.route("**/api/channel/demo/run", async (route) => {
      demoEndpointHit = true;
      try {
        const body = route.request().postDataJSON() as { scenario_id?: string };
        demoScenarioPayload = body?.scenario_id ?? null;
      } catch {
        demoScenarioPayload = null;
      }
      const sse = [
        `event: stage\ndata: ${JSON.stringify({ event: "stage", stage: "parse", status: "done" })}\n\n`,
        `event: stage\ndata: ${JSON.stringify({ event: "stage", stage: "rank", status: "done" })}\n\n`,
        `event: done\ndata: ${JSON.stringify({
          event: "done",
          data_source: "mock_forced",
          session_id: "demo_medium_test",
          metrics: { signalTotal: 12, companiesFound: 6, final: 4 },
          candidates: [
            {
              id: "demo-1",
              name: "Demo 演示候选公司",
              similarity: 0.78,
              industry: "演示行业",
              geo: "演示区域",
              scale: "演示规模",
              signals: [],
              riskTags: [],
              products: [],
              match_dimensions: [],
              product_recommendations: [],
              pitch_scripts: [],
            },
          ],
          radar: [{ axis: "信号密度", score: 70, benchmark: 50, quadrant: "base" }],
          signals: [
            { id: "ds1", key: "biz", label: "工商", status: "active", weight: 0.2, freq: "T+1", coverage: 70, hits: 2 },
          ],
          funnel: [
            { id: "df1", label: "信号池", count: 500 },
            { id: "df2", label: "Top 推荐", count: 4 },
          ],
          match_dimensions: [],
          product_recommendations: [],
          pitch_scripts: [],
        })}\n\n`,
      ].join("");
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: sse,
      });
    });

    await page.goto("/archive/channel", { waitUntil: "networkidle" });

    // 3 档按钮都应 visible
    await expect(page.locator('[data-testid="channel-demo-easy"]')).toBeVisible();
    await expect(page.locator('[data-testid="channel-demo-hard"]')).toBeVisible();

    // 点 medium · 验 endpoint hit + scenario_id payload 正确
    await page.locator('[data-testid="channel-demo-medium"]').click();
    await page.waitForTimeout(500);

    expect(demoEndpointHit).toBe(true);
    expect(demoScenarioPayload).toBe("medium");

    // candidates panel data-mode=live (liveData != null · demo 也走 setLiveData 路径)
    await expect(
      page.locator('[data-testid="channel-pilot-candidates"]'),
    ).toHaveAttribute("data-mode", "live");

    // 5 panel 全亮
    for (const k of ["radar", "funnel", "candidates", "signals", "conversation"]) {
      await expect(
        page.locator(`[data-testid="channel-pilot-${k}"]`),
      ).toBeVisible();
    }

    // candidate 切到 demo 注入的 "Demo 演示候选公司"
    await expect(page.locator(".ch-cd-name").first()).toContainText(
      "Demo 演示候选公司",
    );

    // mock_forced 是显式 demo 选择 · 不应触发 mock_fallback banner (banner-spec rule 2)
    const fallbackBanner = page.locator('[data-testid="channel-pilot-banner-mock-fallback"]');
    await expect(fallbackBanner).toHaveCount(0);
  });

  test("T4 · banner-spec rule 2 · backend stage warning + done.warnings → mock-fallback banner", async ({
    page,
    context,
  }) => {
    await context.route("**/api/channel/run", async (route) => {
      const sse = [
        // 后端 yield ("warning", msg) → main loop yield stage status=warning event
        `event: stage\ndata: ${JSON.stringify({
          event: "stage",
          stage: "signal_scan",
          status: "warning",
          message: "TAVILY_API_KEY 未配置 · 已降级为 mock 演示数据 · 配置 key 后可恢复 live",
        })}\n\n`,
        // done · data_source=mock_fallback + warnings 透传
        `event: done\ndata: ${JSON.stringify({
          event: "done",
          data_source: "mock_fallback",
          session_id: "test-fallback-1",
          metrics: { signalTotal: 0, companiesFound: 0, final: 0 },
          warnings: ["TAVILY_API_KEY 未配置 · 已降级为 mock 演示数据 · 配置 key 后可恢复 live"],
          candidates: [],
          radar: [],
          signals: [],
          funnel: [],
          match_dimensions: [],
          product_recommendations: [],
          pitch_scripts: [],
        })}\n\n`,
      ].join("");
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: sse,
      });
    });

    await page.goto("/archive/channel", { waitUntil: "networkidle" });
    await page.locator(".ch-querybar-input").fill("找浙江精密零部件");
    await page.locator('[data-testid="scout-search"]').click();
    await page.waitForTimeout(500);

    // mock-fallback banner 显 · kind=info · text 含 TAVILY
    const banner = page.locator('[data-testid="channel-pilot-banner-mock-fallback"]');
    await expect(banner).toBeVisible();
    await expect(banner).toContainText("TAVILY");
    await expect(banner).toHaveAttribute("data-banner-kind", "info");
  });
});
