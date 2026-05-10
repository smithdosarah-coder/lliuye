import { test, expect } from "@playwright/test";

/**
 * F-051 · Riskctrl/Forge Workspace · 空白启动 + Primary DSL CTA
 *
 * ALL IN Phase B step 1 重写 (2026-05-09):
 *   原 3 CTA (Primary DSL gen / Secondary preset / Tertiary history) 删除
 *   secondary_preset / tertiary_history 是 mock 入口 · 违反红线 #1 (假 live)
 *   Phase B 后入口收敛到 Primary DSL gen 真路径 (LLM 生成 → 真回测)
 *
 * 必读 contracts:
 *   - docs/contracts/empty-state-design-protocol.md v1.0
 *   - docs/contracts/agent-forge-spec.md (Stage A.5)
 *
 * 验:
 *   1. /archive/riskctrl default state · started=no · 必备 testid 都在
 *   2. mock 数据**不 default load** · DSL editor / KS chart / sample dist / export btn 不渲染
 *   3. Primary DSL CTA 单入口 · click 后 started=yes (mock SSE)
 *   4. (已删) preset / history dropdown · ModePill · demo banner
 */
test.describe("F-051 · Riskctrl Workspace 空白启动 + Primary DSL CTA", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/archive/riskctrl", { waitUntil: "networkidle" });
  });

  test("default state · started=no · 必备 testid 都在 + 不显示 mock 真数据", async ({
    page,
  }) => {
    const root = page.locator('[data-testid="riskctrl-workspace"]');
    await expect(root).toBeVisible();
    await expect(root).toHaveAttribute("data-started", "no");

    /* 必备 testid · empty 状态下应可见的:
       dsl-gen-cta · empty-skeleton · trigger-bar */
    await expect(page.locator('[data-testid="riskctrl-dsl-gen-cta"]')).toBeVisible();
    await expect(page.locator('[data-testid="riskctrl-empty-skeleton"]')).toBeVisible();
    await expect(page.locator('[data-testid="riskctrl-trigger-bar"]')).toBeVisible();

    /* empty 状态下 · DSL editor / KS / sample / export / backtest 不渲染 (在 started 块内) */
    await expect(page.locator('[data-testid="riskctrl-dsl-editor"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="riskctrl-ks-chart"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="riskctrl-sample-dist"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="riskctrl-backtest-cta"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="riskctrl-export-docx-btn"]')).toHaveCount(0);
  });

  test("ALL IN step 1 · 已删 mock UI 入口 (preset / history dropdown · ModePill · demo banner)", async ({
    page,
  }) => {
    /* preset dropdown 已删 */
    await expect(page.locator('[data-testid="riskctrl-preset-dropdown"]')).toHaveCount(0);
    /* history dropdown 已删 */
    await expect(page.locator('[data-testid="riskctrl-history-dropdown"]')).toHaveCount(0);
    /* "应用" 按钮已删 */
    await expect(page.locator('[data-testid="riskctrl-apply-cta"]')).toHaveCount(0);
    /* ModePill 已删 (DataSourceBadge 5-enum trust model 已含 LIVE/MOCK 区分) */
    await expect(page.locator('[data-testid="riskctrl-mode-pill"]')).toHaveCount(0);
    /* tertiary_history demo banner 已删 (history dropdown 入口已无) */
    await expect(page.locator('[data-testid="riskctrl-demo-banner"]')).toHaveCount(0);
  });

  test("Primary CTA 可触发 · DSL gen 按钮 click 后 started=yes (mock SSE)", async ({
    page,
  }) => {
    /* mock backend SSE response · 不依赖真后端起来 */
    await page.route("**/api/riskctrl/dsl_gen", async (route) => {
      const resp = [
        'data: {"event":"stage","payload":{"phase":"intent_detection","intent":"strategy_config"}}',
        '',
        'data: {"event":"stage","payload":{"phase":"dsl_generation","ruleset_id":"test-rs-001"}}',
        '',
        'data: {"event":"done"}',
        '',
        '',
      ].join("\n");
      await route.fulfill({
        status: 200,
        headers: { "content-type": "text/event-stream; charset=utf-8" },
        body: resp,
      });
    });

    const cta = page.locator('[data-testid="riskctrl-dsl-gen-cta"]');
    await cta.click();

    await expect(page.locator('[data-testid="riskctrl-workspace"]')).toHaveAttribute(
      "data-started",
      "yes",
    );
    /* trigger 仅 primary_dsl 单值 · secondary_preset / tertiary_history 已删 */
    await expect(page.locator('[data-testid="riskctrl-workspace"]')).toHaveAttribute(
      "data-trigger",
      "primary_dsl",
    );
  });
});
