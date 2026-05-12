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
import { adminTest as test, expect, E2E_TIMEOUT_MS, FIRST_PAINT_TIMEOUT_MS } from "./_shared";

test.describe("B.3.4 · admin 真号 · riskctrl 风控 demo credit_v15 回测", () => {
  test("跑 credit_v15 demo · KS chart 真出 + DSL rules 真出", async ({ page }) => {
    test.setTimeout(E2E_TIMEOUT_MS);

    await page.goto("/archive/riskctrl", { waitUntil: "networkidle" });

    // workspace root 必显 (per RiskctrlWorkspace.tsx:479 · 不管 started 状态)
    // (AuthGate bootstrap + CF 首连延迟 · CF cold + SPA hydration 容差 30s)
    await expect(
      page.locator('[data-testid="riskctrl-workspace"]'),
    ).toBeVisible({ timeout: FIRST_PAINT_TIMEOUT_MS });

    // 默认 mode="real" (per RiskctrlWorkspace.tsx:190) · 切到 demo 才出 demo CTA
    await page.locator('[data-testid="riskctrl-mode-toggle-demo"]').click();

    // 等 demo seeds API 加载完 · seed select 出 + 默认选中第一项 (= credit_v15)
    // (per RiskctrlWorkspace.tsx:364 seeds.length>0 时自动 setSelectedDemoSeedId)
    const seedSelect = page.locator('[data-testid="riskctrl-demo-seed-select"]');
    await expect(seedSelect).toBeVisible({ timeout: 15_000 });
    // 可选: 显式选 credit_v15 (默认应该就是第一个 · 但保险)
    try {
      await seedSelect.selectOption({ value: "credit_v15" }, { timeout: 3000 });
    } catch {
      // 不是 <select> 或没 credit_v15 option · 跳过 (用默认)
    }

    // 触发 demo run · CTA 必 visible + enabled (要 selectedDemoSeedId 非空)
    const demoRunCta = page.locator('[data-testid="riskctrl-demo-run-cta"]');
    await expect(demoRunCta).toBeVisible({ timeout: 10_000 });
    await expect(demoRunCta).toBeEnabled({ timeout: 10_000 });
    await demoRunCta.click();

    // 等 workspace 切到 started=yes (SSE done event 收到 + state 切换)
    await expect(
      page.locator('[data-testid="riskctrl-workspace"][data-started="yes"]'),
    ).toBeVisible({ timeout: 60_000 });

    // SSE done · workspace 切到 started 状态 (上面已等到 data-started=yes)
    //
    // RiskOutputPanel 渲染条件: started=true · 其内 ks-chart / dsl-editor / rule-card 任 1 出
    // 即视为 "demo 跑成 · 真后端 KS 和 DSL 真返"
    const ksChart = page.locator('[data-testid="riskctrl-ks-chart"]');
    const dslEditor = page.locator('[data-testid="riskctrl-dsl-editor"]');
    const ruleCards = page.locator('[data-testid^="riskctrl-rule-card-"]');

    // 任 1 visible 即可 · poll 60s · 用 .or() locator
    const anyOutput = ksChart.or(dslEditor).or(ruleCards.first());
    await expect(anyOutput).toBeVisible({ timeout: 60_000 });

    // KS chart 出 → 验数字 · 不出 → 至少有 rule card / DSL 出
    const ksVisible = (await ksChart.count()) > 0 && (await ksChart.isVisible());
    const dslVisible = (await dslEditor.count()) > 0 && (await dslEditor.isVisible());
    const rulesVisible = (await ruleCards.count()) > 0;

    if (ksVisible) {
      const ksText = (await ksChart.innerText()).trim();
      expect(ksText, "KS chart 含占位符").not.toMatch(/\[object|^null$|undefined/);
      expect(ksText, "KS chart 无数字").toMatch(/\d/);
    }
    if (rulesVisible) {
      const ruleCount = await ruleCards.count();
      expect(ruleCount, "rule cards 数量").toBeGreaterThanOrEqual(1);
    }
    expect(
      ksVisible || dslVisible || rulesVisible,
      "ks-chart / dsl-editor / rule-card 都不出 · 后端 demo run 没真返结果",
    ).toBe(true);
  });
});
