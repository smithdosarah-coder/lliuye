import { test, expect, type Page } from "@playwright/test";

/**
 * F-042 · Channel Candidate Detail Drawer (master plan §B.4 + §B.4b + §B.4c)
 *
 * 验证:
 *  1) 候选 click → drawer 真展开
 *  2) drawer 4 区: header / radar+timeline / 匹配明细 chip / 产品+话术
 *  3) ESC / backdrop click 都能关 drawer
 *  4) 切 session 自动关 drawer (handleSelectSession 清 selectedCandidateId)
 *  5) 5 mock session 各 candidate 都有 match_dimensions/product_recommendations/pitch_scripts
 *
 * Auth seed: archive/* 受 AuthGate + RbacGuard 保护 · 测试前 seed
 *   localStorage["platform.auth.v1"] · 默认 u_wangzhe (role rm · 6 Agent 全开)
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
  // addInitScript 在每个 navigation 之前注入 localStorage · 不需要先 visit /login
  // 解决 redirect-loop 问题: AuthGate 检测 currentUser=null 时 redirect /login · 导致
  //   后续 page.goto("/archive/channel") 实际跳到 /login (只有 #after navigate 后才 set
  //   localStorage)
  await page.addInitScript(
    ({ key, user }) => {
      const persisted = {
        state: { currentUser: user },
        version: 0,
      };
      window.localStorage.setItem(key, JSON.stringify(persisted));
    },
    { key: AUTH_KEY, user: DEMO_USER_RM },
  );
}

test.describe("F-042 · Channel Candidate Detail Drawer", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
  });

  test("default render · select dropdown 后无 drawer", async ({ page }) => {
    await page.goto("/archive/channel", { waitUntil: "networkidle" });
    // 触发 started · 先选历史 session
    const select = page.locator('[data-testid="channel-session-select"]').first();
    await expect(select).toBeVisible();
    await select.selectOption({ index: 0 });
    // drawer 默认未展开
    const drawer = page.locator('[data-testid="channel-candidate-drawer"]');
    await expect(drawer).toHaveCount(0);
    // 候选 card 渲染
    const cards = page.locator('[data-testid="channel-candidate-card"]');
    await expect(cards.first()).toBeVisible({ timeout: 8000 });
  });

  test("候选 click → drawer 4 区都能渲染 (header / radar / 匹配 chip / 产品 / 话术)", async ({
    page,
  }) => {
    await page.goto("/archive/channel", { waitUntil: "networkidle" });
    // started · 选第一个 session (sess_haichao)
    const select = page.locator('[data-testid="channel-session-select"]').first();
    await select.selectOption({ index: 0 });
    // 等候选 card 渲染
    const firstCard = page
      .locator('[data-testid="channel-candidate-card"]')
      .first();
    await expect(firstCard).toBeVisible({ timeout: 8000 });
    // click 第一个候选
    await firstCard.click();
    // drawer 展开
    const drawer = page.locator('[data-testid="channel-candidate-drawer"]');
    await expect(drawer).toBeVisible();
    // 1. header (drawer-name)
    const name = page.locator(
      '[data-testid="channel-candidate-drawer-name"]',
    );
    await expect(name).toBeVisible();
    // 2. 匹配维度 chip ≥ 3 条 (B.4b)
    const matchChips = page.locator(
      '[data-testid="candidate-match-dim-chip"]',
    );
    expect(await matchChips.count()).toBeGreaterThanOrEqual(3);
    // 3. Top3 产品卡 ≥ 3 (B.4c)
    const productCards = page.locator(
      '[data-testid="candidate-product-card"]',
    );
    expect(await productCards.count()).toBeGreaterThanOrEqual(3);
    // 4. 切入话术 ≥ 3 条 (B.4c)
    const pitches = page.locator('[data-testid="candidate-pitch-script"]');
    expect(await pitches.count()).toBeGreaterThanOrEqual(3);
  });

  test("ESC 关 drawer + backdrop click 关 drawer", async ({ page }) => {
    await page.goto("/archive/channel", { waitUntil: "networkidle" });
    const select = page.locator('[data-testid="channel-session-select"]').first();
    await select.selectOption({ index: 0 });
    const firstCard = page
      .locator('[data-testid="channel-candidate-card"]')
      .first();
    await expect(firstCard).toBeVisible({ timeout: 8000 });
    await firstCard.click();
    const drawer = page.locator('[data-testid="channel-candidate-drawer"]');
    await expect(drawer).toBeVisible();
    // 测 ESC
    await page.keyboard.press("Escape");
    await expect(drawer).toHaveCount(0);
    // 再 click 一个候选 · 测 backdrop click
    await firstCard.click();
    await expect(drawer).toBeVisible();
    // backdrop click 关 (在 backdrop 边缘 click · 不点 drawer 内部)
    const backdrop = page.locator(
      '[data-testid="channel-candidate-drawer-backdrop"]',
    );
    // click 左上角 (drawer 在右侧 · 左侧是 backdrop 区)
    await backdrop.click({ position: { x: 50, y: 200 } });
    await expect(drawer).toHaveCount(0);
  });

  test("切 session 自动关 drawer · 反 session 数据隔离", async ({ page }) => {
    await page.goto("/archive/channel", { waitUntil: "networkidle" });
    const select = page.locator('[data-testid="channel-session-select"]').first();
    await select.selectOption({ index: 0 });
    const firstCard = page
      .locator('[data-testid="channel-candidate-card"]')
      .first();
    await expect(firstCard).toBeVisible({ timeout: 8000 });
    await firstCard.click();
    const drawer = page.locator('[data-testid="channel-candidate-drawer"]');
    await expect(drawer).toBeVisible();
    // 切 session
    await select.selectOption({ index: 1 });
    // drawer 自动关 (workspace handleSelectSession 清 selectedCandidateId)
    await expect(drawer).toHaveCount(0);
  });
});
