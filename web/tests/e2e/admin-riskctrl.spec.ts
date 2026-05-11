/**
 * B.3.4 · P0-R5 · 主活 B · admin 真号 E2E · riskctrl
 *
 * PM 真意:
 *   登录 admin · credit_v15 回测 (seed_id=credit_v15 · /api/riskctrl/demo/run)
 *   · 验 KS 真出 + DSL 规则真出
 *
 * 触发: riskctrl-demo-seed-select (选 credit_v15) + riskctrl-demo-run-cta
 *   per RiskctrlWorkspace.tsx:715,740
 */
import { adminTest as test, expect, E2E_TIMEOUT_MS } from "./_shared";

test.describe("B.3.4 · admin 真号 · riskctrl 风控 demo credit_v15 回测", () => {
  test("跑 credit_v15 demo · KS chart 真出 + DSL rules 真出", async ({ page }) => {
    test.setTimeout(E2E_TIMEOUT_MS);

    await page.goto("/archive/riskctrl", { waitUntil: "networkidle" });

    // empty-skeleton 加载 · 选 credit_v15 seed
    await expect(
      page.locator('[data-testid="riskctrl-empty-skeleton"]'),
    ).toBeVisible();

    // 选择 credit_v15 demo seed (如果有 select dropdown)
    const seedSelect = page.locator('[data-testid="riskctrl-demo-seed-select"]');
    if ((await seedSelect.count()) > 0) {
      await seedSelect.selectOption({ value: "credit_v15" }).catch(async () => {
        // 若是 button group · 走 button click
        await page.locator('button:has-text("credit_v15")').click();
      });
    }

    // 触发 demo run
    await page.locator('[data-testid="riskctrl-demo-run-cta"]').click();

    // SSE done · workspace 切到 started 状态
    // KS chart 真出 = riskctrl-ks-chart 区域 visible
    const ksChart = page.locator('[data-testid="riskctrl-ks-chart"]');
    await expect(ksChart).toBeVisible({ timeout: 60_000 });

    // KS 区域不为空 · 含数字 (KS 是 0-1 之间 percentage · 现实 0.2-0.5 区间)
    const ksText = (await ksChart.innerText()).trim();
    expect(ksText, "KS chart 区域空").not.toEqual("");
    expect(ksText, "KS 含占位符").not.toMatch(/\[object|^null$|undefined/);
    expect(ksText, "KS 无任何数字").toMatch(/\d/);

    // DSL 规则真出 = ruleset 或 rule-card 任 1 visible
    const dslEditor = page.locator('[data-testid="riskctrl-dsl-editor"]');
    const ruleCards = page.locator('[data-testid^="riskctrl-rule-card-"]');
    const dslVisible = (await dslEditor.count()) > 0;
    const rulesVisible = (await ruleCards.count()) > 0;
    expect(
      dslVisible || rulesVisible,
      "DSL 编辑器 + rule cards 都不出 · 规则未生成",
    ).toBe(true);

    if (rulesVisible) {
      const ruleCount = await ruleCards.count();
      expect(ruleCount, "rule cards 数量").toBeGreaterThanOrEqual(1);
    }
  });
});
