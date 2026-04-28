import { test, expect } from "@playwright/test";

/**
 * F-051 · Riskctrl/Forge Workspace · 空白启动 + 3 CTA 分级
 *
 * 必读 contracts:
 *   - docs/contracts/empty-state-design-protocol.md v1.0
 *   - docs/contracts/agent-forge-spec.md (Stage A.5)
 *
 * 验:
 *   1. /archive/riskctrl default state · started=no · 7 必备 testid 全在 (含 empty-skeleton)
 *   2. mock 数据**不 default load** · DSL editor / KS chart / sample dist / export btn 不渲染
 *   3. dropdown 标 (示例) tag · production 路径分离
 *   4. Tertiary 历史选项触发 → started=yes + demo banner 显示
 *   5. Primary CTA「生成 DSL」按钮可点击 (mock SSE)
 *   6. Secondary 「预置规则集」dropdown 存在
 */
test.describe("F-051 · Riskctrl Workspace 空白启动 + 3 CTA", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/archive/riskctrl", { waitUntil: "networkidle" });
  });

  test("default state · started=no · 必备 testid 都在 + 不显示 mock 真数据", async ({
    page,
  }) => {
    const root = page.locator('[data-testid="riskctrl-workspace"]');
    await expect(root).toBeVisible();
    await expect(root).toHaveAttribute("data-started", "no");

    /* 7 onboarding 必备 testid · empty 状态下应可见的:
       dsl-gen-cta · empty-skeleton (在 empty 状态可见) */
    await expect(page.locator('[data-testid="riskctrl-dsl-gen-cta"]')).toBeVisible();
    await expect(page.locator('[data-testid="riskctrl-empty-skeleton"]')).toBeVisible();

    /* empty 状态下 · DSL editor / KS / sample / export / backtest 不渲染 (在 started 块内) */
    await expect(page.locator('[data-testid="riskctrl-dsl-editor"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="riskctrl-ks-chart"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="riskctrl-sample-dist"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="riskctrl-backtest-cta"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="riskctrl-export-docx-btn"]')).toHaveCount(0);
  });

  test("dropdown 显式标 (示例) tag · production / demo 路径分离", async ({ page }) => {
    const dropdown = page.locator('[data-testid="riskctrl-history-dropdown"]');
    await expect(dropdown).toBeVisible();
    /* 至少含一个 (示例) 选项 */
    await expect(dropdown.locator("option")).toContainText(/示例/);
  });

  test("3 CTA 分级 · primary · secondary · tertiary 都存在", async ({ page }) => {
    /* Primary · 生成 DSL 按钮 */
    await expect(page.locator('[data-testid="riskctrl-dsl-gen-cta"]')).toBeVisible();
    /* Secondary · 预置规则集 dropdown */
    await expect(page.locator('[data-testid="riskctrl-preset-dropdown"]')).toBeVisible();
    /* Tertiary · 历史 dropdown */
    await expect(page.locator('[data-testid="riskctrl-history-dropdown"]')).toBeVisible();
  });

  test("Tertiary 历史选项触发 → started=yes · demo banner 显示", async ({ page }) => {
    const dropdown = page.locator('[data-testid="riskctrl-history-dropdown"]');
    const firstDemoOption = dropdown.locator("option").nth(1);
    const value = await firstDemoOption.getAttribute("value");
    if (!value) test.skip(true, "no demo option to select");

    await dropdown.selectOption(value!);

    await expect(page.locator('[data-testid="riskctrl-workspace"]')).toHaveAttribute(
      "data-started",
      "yes",
    );
    await expect(page.locator('[data-testid="riskctrl-demo-banner"]')).toBeVisible();
    await expect(page.locator('[data-testid="riskctrl-empty-skeleton"]')).toHaveCount(0);

    /* mock 数据现在出现 (DSL editor / KS chart 渲染) */
    await expect(page.locator('[data-testid="riskctrl-dsl-editor"]').first()).toBeVisible();
  });

  test("Secondary 预置触发 → started=yes · trigger=secondary_preset", async ({ page }) => {
    const presetDropdown = page.locator('[data-testid="riskctrl-preset-dropdown"]');
    const firstOption = presetDropdown.locator("option").nth(1);
    const value = await firstOption.getAttribute("value");
    if (!value) test.skip(true, "no preset option to select");

    await presetDropdown.selectOption(value!);
    await expect(page.locator('[data-testid="riskctrl-workspace"]')).toHaveAttribute(
      "data-started",
      "yes",
    );
    await expect(page.locator('[data-testid="riskctrl-workspace"]')).toHaveAttribute(
      "data-trigger",
      "secondary_preset",
    );
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
  });
});
