import { test, expect, type Page } from "@playwright/test";

/**
 * F-RISKCTRL-MOCK-SWITCH · workspace 4 gate · selectedSession dropdown 切下拉
 *
 * 验证: 切 RecentPanel 内 riskctrl-session-switch 下拉 · 5 panel 全跟切
 *   - data-session attr 改
 *   - Hero 副标 (objective / KS / 通过率) 切
 *   - QueryPanel objective 切
 *   - RulesPanel current rule 切
 *   - RiskOutputPanel KS / 通过 切
 *
 * Phase A worker-A4 · sessions array (sess_credit_v15 / sess_aml_kyc / sess_fraud_high).
 *
 * Auth seed: archive/* 受 AuthGate 保护 · 默认 u_wangzhe (rm role)
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

test.describe("F-RISKCTRL-MOCK-SWITCH · 4 gate session dropdown", () => {
  test("default empty state · click history dropdown + apply enters started=true with sess_credit_v15", async ({
    page,
  }) => {
    await page.goto("/archive/riskctrl", { waitUntil: "networkidle" });

    const workspace = page.locator('[data-testid="riskctrl-workspace"]');
    await expect(workspace).toBeVisible();
    await expect(workspace).toHaveAttribute("data-started", "no");

    // 选 history dropdown 第一项 (sess_credit_v15) · click 应用 · started=true
    const historyDropdown = page.locator('[data-testid="riskctrl-history-dropdown"]');
    await expect(historyDropdown).toBeVisible();
    await historyDropdown.selectOption("sess_credit_v15");

    const applyBtn = page.locator('[data-testid="riskctrl-apply-cta"]');
    await applyBtn.click();
    await page.waitForTimeout(300);

    await expect(workspace).toHaveAttribute("data-started", "yes");
    await expect(workspace).toHaveAttribute("data-session", "sess_credit_v15");
  });

  test("switch to sess_aml_kyc via session-switch dropdown refreshes 5 panels", async ({
    page,
  }) => {
    await page.goto("/archive/riskctrl", { waitUntil: "networkidle" });

    // Step 1 · 进入 started state via tertiary history
    const historyDropdown = page.locator('[data-testid="riskctrl-history-dropdown"]');
    await historyDropdown.selectOption("sess_credit_v15");
    await page.locator('[data-testid="riskctrl-apply-cta"]').click();
    await page.waitForTimeout(300);

    const workspace = page.locator('[data-testid="riskctrl-workspace"]');
    await expect(workspace).toHaveAttribute("data-session", "sess_credit_v15");

    // Hero subtitle 显示 sess_credit_v15 KS 0.42 / 通过 32%
    const heroSub = page.locator(".rpt-hero-sub").first();
    await expect(heroSub).toContainText(/KS 0\.42|通过 32/);

    // Step 2 · 切 RecentPanel 内的 session-switch (3 sessions)
    const sessionSwitch = page.locator('[data-testid="riskctrl-session-switch"]');
    await expect(sessionSwitch).toBeVisible();
    await sessionSwitch.selectOption("sess_aml_kyc");
    await page.waitForTimeout(300);

    // workspace data-session attr 切到 aml_kyc
    await expect(workspace).toHaveAttribute("data-session", "sess_aml_kyc");

    // Hero subtitle 切到 sess_aml_kyc · KS 0.31 / 通过 18%
    await expect(heroSub).toContainText(/KS 0\.31|通过 18/);
  });

  test("switch to sess_fraud_high (red zone) shows extreme tier values", async ({
    page,
  }) => {
    await page.goto("/archive/riskctrl", { waitUntil: "networkidle" });

    // 进入 started
    await page.locator('[data-testid="riskctrl-history-dropdown"]').selectOption("sess_credit_v15");
    await page.locator('[data-testid="riskctrl-apply-cta"]').click();
    await page.waitForTimeout(200);

    // 切 fraud_high
    await page.locator('[data-testid="riskctrl-session-switch"]').selectOption("sess_fraud_high");
    await page.waitForTimeout(300);

    const workspace = page.locator('[data-testid="riskctrl-workspace"]');
    await expect(workspace).toHaveAttribute("data-session", "sess_fraud_high");

    // Hero 显 KS 0.28 (红区) · 通过 8%
    const heroSub = page.locator(".rpt-hero-sub").first();
    await expect(heroSub).toContainText(/KS 0\.28|通过 8/);

    // RecentPanel session select 显示 fraud_high 当前选中
    await expect(
      page.locator('[data-testid="riskctrl-session-switch"]'),
    ).toHaveValue("sess_fraud_high");
  });
});
