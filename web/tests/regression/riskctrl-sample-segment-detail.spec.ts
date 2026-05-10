import { test, expect, type Page } from "@playwright/test";

/**
 * F-RISKCTRL-SAMPLE-SEGMENT-DETAIL · 4 gate selectedRuleOrSegment 接 SampleView click
 *
 * ALL IN Phase B step 1 (2026-05-09) · 整文件 skip:
 *   原 setup 用 riskctrl-history-dropdown.selectOption("sess_credit_v15") + apply-cta
 *   进 mock session · 这两个 testid 在 Step 1 删 mock UI 时已移除
 *   Step 6 (per-rule 联动) 实施后本 spec 重写 · 用真 backtest 出 ruleStats 后切 segment
 */
test.describe.skip("F-RISKCTRL-SAMPLE-SEGMENT-DETAIL · selectedRuleOrSegment (ALL IN Phase B step 1 skip · 重写于 Step 6)", () => {
  test("placeholder · 待 Step 6 重写", () => {});
});

/* === 以下 legacy spec 暂保留作 Step 6 重写参考 · skip 已生效 === */
test.describe.skip("legacy · pre-ALL-IN", () => {

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
      window.localStorage.setItem(
        key,
        JSON.stringify({ state: { currentUser: user }, version: 0 }),
      );
    },
    { key: AUTH_KEY, user: DEMO_USER_RM },
  );
}

test.beforeEach(async ({ page }) => {
  await seedAuth(page);
});

test.describe("F-RISKCTRL-SAMPLE-SEGMENT-DETAIL · selection 4th gate", () => {
  test("click sample segment toggles data-selected · multi-segment exclusive", async ({
    page,
  }) => {
    await page.goto("/archive/riskctrl", { waitUntil: "domcontentloaded" });
    await page.locator('[data-testid="riskctrl-workspace"]').waitFor({ state: "visible" });

    // 进 started · 选 sess_credit_v15 (12,400 样本 · pass/review/block)
    await page.locator('[data-testid="riskctrl-history-dropdown"]').selectOption("sess_credit_v15");
    await page.locator('[data-testid="riskctrl-apply-cta"]').click();
    await page.waitForTimeout(300);

    // RiskOutputPanel "样本分布" tab 切换 (默认 dsl tab)
    const sampleTab = page.locator(".rc-out-tabs button", { hasText: "样本分布" });
    await sampleTab.click();
    await page.waitForTimeout(150);

    // SampleView 三档可见
    const passSeg = page.locator('[data-testid="riskctrl-sample-segment-pass"]');
    const reviewSeg = page.locator('[data-testid="riskctrl-sample-segment-review"]');
    const blockSeg = page.locator('[data-testid="riskctrl-sample-segment-block"]');
    await expect(passSeg).toBeVisible();
    await expect(reviewSeg).toBeVisible();
    await expect(blockSeg).toBeVisible();

    // 默认无选中
    await expect(passSeg).toHaveAttribute("data-selected", "no");
    await expect(reviewSeg).toHaveAttribute("data-selected", "no");
    await expect(blockSeg).toHaveAttribute("data-selected", "no");

    // 点击 "通过" 档 → data-selected="yes"
    await passSeg.click();
    await expect(passSeg).toHaveAttribute("data-selected", "yes");
    await expect(reviewSeg).toHaveAttribute("data-selected", "no");
    await expect(blockSeg).toHaveAttribute("data-selected", "no");

    // 点击 "拒绝" 档 · 互斥切换
    await blockSeg.click();
    await expect(blockSeg).toHaveAttribute("data-selected", "yes");
    await expect(passSeg).toHaveAttribute("data-selected", "no");
  });

  test("session switch clears selectedRuleOrSegment", async ({ page }) => {
    await page.goto("/archive/riskctrl", { waitUntil: "domcontentloaded" });
    await page.locator('[data-testid="riskctrl-workspace"]').waitFor({ state: "visible" });

    // 进 started · 选样本档
    await page.locator('[data-testid="riskctrl-history-dropdown"]').selectOption("sess_credit_v15");
    await page.locator('[data-testid="riskctrl-apply-cta"]').click();
    await page.waitForTimeout(300);

    await page.locator(".rc-out-tabs button", { hasText: "样本分布" }).click();
    await page.waitForTimeout(150);

    const reviewSeg = page.locator('[data-testid="riskctrl-sample-segment-review"]');
    await reviewSeg.click();
    await expect(reviewSeg).toHaveAttribute("data-selected", "yes");

    // 切到 sess_aml_kyc · selection 清
    await page.locator('[data-testid="riskctrl-session-switch"]').selectOption("sess_aml_kyc");
    await page.waitForTimeout(300);

    // 切 session 后 sample tab 仍开 · 但 review 档 selection 清 (sample shape 不同)
    const reviewSegAml = page.locator('[data-testid="riskctrl-sample-segment-review"]');
    await expect(reviewSegAml).toHaveAttribute("data-selected", "no");
  });
});
}); /* end legacy describe.skip */
