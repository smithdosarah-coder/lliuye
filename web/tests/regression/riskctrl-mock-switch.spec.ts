import { test, expect, type Page } from "@playwright/test";

/**
 * F-RISKCTRL-MOCK-SWITCH · workspace 4 gate · selectedSession dropdown 切下拉
 *
 * ALL IN Phase B step 1 (2026-05-09) · 整文件 skip:
 *   原 setup 用 riskctrl-history-dropdown + riskctrl-apply-cta 进 mock session · 这两个
 *   testid 在 Step 1 删 mock UI 时已移除 (违反红线 #1 假 live · per KT §3.6)
 *   sidebar RecentPanel 切 mock session 的语义在 Step 2 sessionData=EMPTY_SESSION 后
 *   也将被替换为真 live ruleset 切换 · 本 spec 重写于 Step 2 后 (新 testid 待定)
 *
 * Auth seed: archive/* 受 AuthGate 保护 · 默认 u_wangzhe (rm role)
 */
test.describe.skip("F-RISKCTRL-MOCK-SWITCH · workspace 4 gate · session 切换 (ALL IN Phase B step 1 skip · 重写于 Step 2)", () => {
  test("placeholder · 待 Step 2 重写", () => {});
});

/* === 以下 legacy spec 暂保留作 Step 2 重写参考 · skip 已生效 === */
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

test.describe("F-RISKCTRL-MOCK-SWITCH · 4 gate session dropdown", () => {
  test("default empty state · click history dropdown + apply enters started=true with sess_credit_v15", async ({
    page,
  }) => {
    await page.goto("/archive/riskctrl", { waitUntil: "domcontentloaded" });
    await page.locator('[data-testid="riskctrl-workspace"]').waitFor({ state: "visible" });

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
    await page.goto("/archive/riskctrl", { waitUntil: "domcontentloaded" });
    await page.locator('[data-testid="riskctrl-workspace"]').waitFor({ state: "visible" });

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
    await page.goto("/archive/riskctrl", { waitUntil: "domcontentloaded" });
    await page.locator('[data-testid="riskctrl-workspace"]').waitFor({ state: "visible" });

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
}); /* end legacy describe.skip */
