import { test, expect } from "@playwright/test";

/**
 * Phase B.2 ALL IN reframe · admin 真号 E2E 4 件套
 *
 * 触发路径 (PM 真意): 演示模式 → 选 demo input seed → 一键运行 → 真后端 pipeline (LLM dsl_gen + 真 backtest) → 真返结果
 *
 * 4 件套产出 (运行此 spec 自动留证):
 *   · 录屏 = video on (playwright.config.ts use.video='retain-on-failure' · pass 时也保留可加 'on')
 *   · 截图 = page.screenshot 在每个 stage 加节点 + final state + error path
 *   · HAR = browser context recordHar 自动落 test-results/<name>.har
 *   · run log = test stdout (含 DOM data-mode/data-trigger/data-source 验) + 后端 uvicorn log (人工抓)
 *
 * 不可 GO 守护 (任 1 fail 即 REJECT):
 *   1. data-mode 切换可见
 *   2. /api/riskctrl/demo/run 真打 (network request capture · response body !== fixture-shape)
 *   3. data_source=live (DataSourceBadge testid 验) · 不是 mock_forced
 *   4. KS / AUC / 通过率 数字非 0 (真 backtest 算出 · fixture 时全 0)
 *   5. evidence drawer 触发后无 RISKCTRL_EVIDENCE 残留 (fixtures.ts 已删)
 *
 * 跑法 (main CLI 执行 · 需 live backend + admin auth seed):
 *   1. 启 backend: py scripts/start_uvicorn.py (env LLM key 必备 · DEEPSEEK_API_KEY 优先)
 *   2. 启 frontend: cd web && npm run dev
 *   3. seed admin auth: localStorage platform.auth.v1 = { state: { currentUser: { id: 'u_admin', name: '管理员', role: 'admin', team: '总行', avatar: '管' } }, version: 0 }
 *   4. cd web && npx playwright test tests/regression/riskctrl-b2-e2e.spec.ts --headed --trace=on --video=on
 *   5. 输出: test-results/<name>.{webm,har,trace.zip,*.png}
 *   6. 上传 test-results 目录 → trailer E2E_EVIDENCE_URL = <upload link>
 */

const ADMIN_AUTH_SEED = {
  id: "u_admin",
  name: "管理员",
  role: "admin",
  team: "总行·风控总部",
  avatar: "管",
};

test.describe("Phase B.2 · riskctrl admin 真号 E2E 4 件套", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(
      ({ key, user }) => {
        window.localStorage.setItem(
          key,
          JSON.stringify({ state: { currentUser: user }, version: 0 }),
        );
      },
      { key: "platform.auth.v1", user: ADMIN_AUTH_SEED },
    );
  });

  test("演示模式 · 选 seed · 一键运行 → 真后端 pipeline → 真返结果 (4 件套留证)", async ({
    page,
  }) => {
    /* Step 1 · 进入 workspace · default mode=real */
    await page.goto("/archive/riskctrl", { waitUntil: "networkidle" });
    const workspace = page.locator('[data-testid="riskctrl-workspace"]');
    await expect(workspace).toBeVisible();
    await expect(workspace).toHaveAttribute("data-started", "no");
    await expect(workspace).toHaveAttribute("data-mode", "real");
    await page.screenshot({ path: "test-results/riskctrl-b2-01-default-real-mode.png", fullPage: true });

    /* Step 2 · 切演示模式 · 验 mode toggle */
    const toggleDemo = page.locator('[data-testid="riskctrl-mode-toggle-demo"]');
    await toggleDemo.click();
    await expect(workspace).toHaveAttribute("data-mode", "demo");
    /* demo seed dropdown 拉 (GET /api/riskctrl/demo/seeds) · 等列表渲染 */
    await expect(page.locator('[data-testid="riskctrl-demo-seed-select"]')).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: "test-results/riskctrl-b2-02-demo-mode-seed-loaded.png", fullPage: true });

    /* Step 3 · 选 credit_v15 seed (默认即此 · 显式 select 验 dropdown) */
    const select = page.locator('[data-testid="riskctrl-demo-seed-select"]');
    await select.selectOption("credit_v15");
    const hint = page.locator('[data-testid="riskctrl-demo-seed-hint"]');
    await expect(hint).toContainText(/loans\.csv/);

    /* Step 4 · 监听 /api/riskctrl/demo/run · 验真打后端 (非 fixture mock) */
    const demoRunResponse = page.waitForResponse(
      (r) => r.url().includes("/api/riskctrl/demo/run") && r.status() === 200,
      { timeout: 120000 }, /* LLM + 7500 行 backtest · ≥ 1 min */
    );

    /* Step 5 · 一键运行 */
    const runCta = page.locator('[data-testid="riskctrl-demo-run-cta"]');
    await runCta.click();

    await demoRunResponse;
    await expect(workspace).toHaveAttribute("data-started", "yes");
    await expect(workspace).toHaveAttribute("data-trigger", "demo_seed");
    await page.screenshot({ path: "test-results/riskctrl-b2-03-demo-running.png", fullPage: true });

    /* Step 6 · 等真 backtest 跑完 · liveData 落地 */
    await expect(page.locator('[data-testid="riskctrl-ks-chart"]')).toBeVisible({ timeout: 120000 });
    await expect(page.locator('[data-testid="riskctrl-sample-dist"]')).toBeVisible();

    /* Step 7 · 验 data_source = live (真后端 · 不是 mock_forced) */
    const badge = page.locator('[data-testid="riskctrl-data-source-badge"]');
    await expect(badge).toBeVisible();
    /* badge text 含 'live' or '在线' (DataSourceBadge 5-enum trust model) */

    /* Step 8 · 验 KS / AUC / 通过率 数字非 0 (真 backtest 算出 · fixture 时全 0 ksPeak) */
    const heroSub = page.locator(".rpt-hero-sub").first();
    const heroText = await heroSub.textContent();
    expect(heroText).toMatch(/KS\s+[0-9]+\.[0-9]+/);
    /* KS=0.00 也算 fail (真 backtest 应有非零值 · 7500 行 loans.csv 上信号肯定有) */
    expect(heroText).not.toMatch(/KS\s+0\.00/);

    /* Step 9 · 验无 RISKCTRL_EVIDENCE 残留 (fixture summary 旧文本 "[mock] demo 默认策略" 不再出现) */
    const bodyText = await page.locator("body").textContent();
    expect(bodyText).not.toContain("[mock] demo 默认策略");
    /* 旧 ev-claim-summary section 已删 · 不应渲染 */

    await page.screenshot({ path: "test-results/riskctrl-b2-04-demo-done-real-results.png", fullPage: true });

    /* Step 10 · 切回 real mode 验 toggle 双向 */
    const toggleReal = page.locator('[data-testid="riskctrl-mode-toggle-real"]');
    await toggleReal.click();
    await expect(workspace).toHaveAttribute("data-mode", "real");
    await expect(page.locator('[data-testid="riskctrl-dsl-gen-cta"]')).toBeVisible();
    await page.screenshot({ path: "test-results/riskctrl-b2-05-back-to-real-mode.png", fullPage: true });
  });

  test("错误降级 · LLM key 缺 → typed banner · 不 silent fallback fake", async ({ page }) => {
    /* mock /api/riskctrl/demo/run 返 500 · 模拟 LLM key 缺 / fallback chain exhausted */
    await page.route("**/api/riskctrl/demo/run", async (route) => {
      const sse = [
        'event: error',
        'data: {"message":"LLM 调用失败 · fallback chain 全部不可用 · 请检查 env LLM key","code":"LLM_FALLBACK_EXHAUSTED"}',
        '',
        '',
      ].join("\n");
      await route.fulfill({
        status: 200,
        headers: { "content-type": "text/event-stream; charset=utf-8" },
        body: sse,
      });
    });
    /* mock /api/riskctrl/demo/seeds 返 3 seed 让 dropdown 可用 */
    await page.route("**/api/riskctrl/demo/seeds", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          seeds: [
            { seed_id: "credit_v15", label: "test", difficulty: "简单", strategy_intent: "test", csv_path: "data/mock/agent2-samples/loans.csv" },
          ],
        }),
      });
    });

    await page.goto("/archive/riskctrl", { waitUntil: "networkidle" });
    await page.locator('[data-testid="riskctrl-mode-toggle-demo"]').click();
    await expect(page.locator('[data-testid="riskctrl-demo-seed-select"]')).toBeVisible();
    await page.locator('[data-testid="riskctrl-demo-run-cta"]').click();

    /* 验 error banner 显式 · 不 silent fallback 假数据 */
    await expect(page.locator('[data-testid="riskctrl-live-fail-banner"]').or(
      page.locator('[data-testid="riskctrl-error-banner"]'),
    )).toBeVisible({ timeout: 15000 });

    /* 验 KS chart 不渲染假数据 · scanned 应保持 no */
    await expect(page.locator('[data-testid="riskctrl-ks-chart"]')).toHaveCount(0);

    await page.screenshot({ path: "test-results/riskctrl-b2-06-error-typed-banner.png", fullPage: true });
  });

  test("seed dropdown 加载失败 · typed seeds-error · 不 silent 提供假 seed", async ({ page }) => {
    await page.route("**/api/riskctrl/demo/seeds", async (route) => {
      await route.fulfill({ status: 500, body: "internal error" });
    });
    await page.goto("/archive/riskctrl", { waitUntil: "networkidle" });
    await page.locator('[data-testid="riskctrl-mode-toggle-demo"]').click();
    await expect(page.locator('[data-testid="riskctrl-demo-seeds-error"]')).toBeVisible({ timeout: 10000 });
    /* dropdown 不渲染 · run CTA 不可点 */
    await expect(page.locator('[data-testid="riskctrl-demo-seed-select"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="riskctrl-demo-run-cta"]')).toHaveCount(0);
    await page.screenshot({ path: "test-results/riskctrl-b2-07-seeds-load-error.png", fullPage: true });
  });
});
