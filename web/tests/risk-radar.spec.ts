import { test, expect, type Page } from "@playwright/test";

/**
 * Q-033 · RiskRadar 4-dim render spec
 *
 * 验收点（onboarding p3f-frontend-integration §3a）:
 *   1) /archive/credit 页面挂载 RiskRadar (Q-033 backlog landing · 路径迁移
 *      web/src/app/credit/components/ legacy → web/src/app/archive/credit/_components/ canon)
 *   2) 默认 corp mode → segment="corporate" → 4 维 (财务/行业/经营/担保)
 *   3) 切 small mode → segment="sme" → 4 维 (还款能力/还款意愿/稳定性/担保)
 *   4) 切 retail mode → segment="retail" → 4 维 (还款能力/还款意愿/稳定性/担保)
 */

const HARNESS_ROUTE = "/archive/credit";

async function seedAuth(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const user = {
      id: "u_wangzhe",
      name: "王哲",
      role: "rm",
      team: "华东·上海第一支行",
      avatar: "哲",
    };
    window.localStorage.setItem(
      "platform.auth.v1",
      JSON.stringify({ state: { currentUser: user }, version: 0 })
    );
  });
}

test.describe("RiskRadar (Q-033 · L1-3 four-dim)", () => {
  test("Case 1 · canon path mount · default corp segment", async ({ page }) => {
    await seedAuth(page);
    await page.goto(HARNESS_ROUTE);
    const preview = page.locator('[data-testid="risk-radar-preview"]');
    await expect(preview).toBeVisible();
    const radar = preview.locator('[data-testid="risk-radar"]');
    await expect(radar).toBeVisible();
    await expect(radar).toHaveAttribute("data-segment", "corporate");
    /* corp 4 维 label · 经 PolarAngleAxis 渲染为 SVG <text> */
    for (const label of ["财务", "行业", "经营", "担保"]) {
      await expect(preview.locator(`text=${label}`).first()).toBeVisible();
    }
  });

  test("Case 2 · small mode segment dispatch (sme)", async ({ page }) => {
    await seedAuth(page);
    await page.goto(HARNESS_ROUTE);
    /* 切普惠 tab · CreditTopBar role="tab" + 中文 label "普惠" */
    const smallTab = page.getByRole("tab", { name: "普惠" });
    await smallTab.click();
    const radar = page.locator('[data-testid="risk-radar"]');
    await expect(radar).toBeVisible();
    await expect(radar).toHaveAttribute("data-segment", "sme");
    for (const label of ["还款能力", "还款意愿", "稳定性", "担保"]) {
      await expect(
        page
          .locator('[data-testid="risk-radar-preview"]')
          .locator(`text=${label}`)
          .first()
      ).toBeVisible();
    }
  });

  test("Case 3 · retail mode segment dispatch", async ({ page }) => {
    await seedAuth(page);
    await page.goto(HARNESS_ROUTE);
    const retailTab = page.getByRole("tab", { name: "对私" });
    await retailTab.click();
    const radar = page.locator('[data-testid="risk-radar"]');
    await expect(radar).toBeVisible();
    await expect(radar).toHaveAttribute("data-segment", "retail");
  });
});
