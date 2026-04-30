import { test, expect, type Page } from "@playwright/test";

/**
 * F-RISKCTRL-SAMPLE-SEGMENT-DETAIL · 4 gate selectedRuleOrSegment 接 SampleView click
 *
 * 验证:
 *   1) 进入 started state · 切到 RiskOutputPanel "样本分布" tab
 *   2) 点击 "通过" 档 → data-selected="yes" · 其他档 data-selected="no"
 *   3) 切到 "拒绝" 档 → 状态切
 *   4) 切 session 后 selection 清 (Step 2 · onSelectRecent setSelectedRuleOrSegment(null))
 *
 * Phase A worker-A4 · 替 Channel 的 candidate drawer pattern · riskctrl 业务无 customer
 * level · 用 sample segment / rule node 作 detail 焦点.
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
    await page.goto("/archive/riskctrl", { waitUntil: "networkidle" });

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
    await page.goto("/archive/riskctrl", { waitUntil: "networkidle" });

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
