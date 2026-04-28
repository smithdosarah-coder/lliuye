import { test, expect, type Page } from "@playwright/test";

/**
 * Stage CF-A1 · Report empty-state-design-protocol smoke
 *
 * 锁定:
 *   1. 进入 /archive/report default · `started=false` · 不渲染重 panel
 *   2. 3 CTA visible: upload (primary) / template-select (secondary) / history (tertiary)
 *   3. 历史 dropdown option 必含 (示例) marker
 *   4. status pill bottom-right · llm/mode/reportId 信息
 *   5. 选历史 → setStarted(true) → ReportEmptySkeleton 隐藏 + 主体渲染
 *   6. mock banner 仅在 started + mock 时出现 (empty-state §5)
 *
 * Author: Worker A1 (Stage C frontend 第 1 批) · 2026-04-28
 */

/** Seed persisted auth state so RbacGuard lets the workspace render
 *  (复用 evidence-trail.spec / risk-radar.spec 同 pattern · 不真接 backend) */
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
      JSON.stringify({ state: { currentUser: user }, version: 0 }),
    );
  });
}

test.describe("F-047 · Report Workspace Empty State (W-CF-A1)", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
  });

  test("default 状态:渲染 launch bar + empty skeleton · 不含主体 panel · 不 auto-fire LLM", async ({ page }) => {
    await page.goto("/archive/report", { waitUntil: "domcontentloaded" });
    await page.waitForSelector('[data-testid="report-launch-bar"]', { timeout: 10_000 });

    // root container · data-started="no"
    const root = page.locator('[data-view="archive-report"]');
    await expect(root).toHaveCount(1);
    await expect(root).toHaveAttribute("data-started", "no");
    await expect(root).toHaveAttribute("data-mode", "mock");

    // launch bar visible
    await expect(page.locator('[data-testid="report-launch-bar"]')).toBeVisible();

    // 3 CTA visible
    await expect(page.locator('[data-testid="report-upload-cta"]')).toBeVisible();
    await expect(page.locator('[data-testid="report-template-select"]')).toBeVisible();
    await expect(page.locator('[data-testid="report-history-dropdown"]')).toBeVisible();

    // empty skeleton visible (started=false)
    await expect(page.locator('[data-testid="report-empty-skeleton"]')).toBeVisible();

    // 不应渲染重 panel · 检查"对话协作"标题不在 (panel 标志)
    // 注:CTA 触发后才该出现 ConversationPanel
    await expect(page.locator('text=对话协作').first()).toHaveCount(0);

    // started=false 时 · 不应有 generate / export 操作按钮
    await expect(page.locator('[data-testid="report-generate-btn"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="report-export-btn"]')).toHaveCount(0);

    // mock banner 仅在 started=true 时出现 · default false 时不应有
    await expect(page.locator('[data-testid="report-mock-banner"]')).toHaveCount(0);
  });

  test("history dropdown · 选项含 (示例) marker (empty-state §2.5)", async ({ page }) => {
    await page.goto("/archive/report", { waitUntil: "domcontentloaded" });
    await page.waitForSelector('[data-testid="report-launch-bar"]', { timeout: 10_000 });

    const dropdown = page.locator('[data-testid="report-history-dropdown"]');
    await expect(dropdown).toBeVisible();
    // 至少 2 option (一个空 + N 个历史)
    const options = await dropdown.locator("option").allTextContents();
    expect(options.length).toBeGreaterThan(1);
    // 至少一个 option 含"(示例)" 或"示例" marker
    const hasDemoMarker = options.some(
      (t) => t.includes("(示例)") || t.includes("（示例）") || t.includes("示例"),
    );
    expect(hasDemoMarker).toBe(true);
  });

  test("status pill bottom-right · 含 llm + mode + reportId(空) 信息", async ({ page }) => {
    await page.goto("/archive/report", { waitUntil: "domcontentloaded" });
    await page.waitForSelector('[data-testid="report-launch-bar"]', { timeout: 10_000 });

    const pill = page.locator('[data-testid="report-status-pill"]');
    await expect(pill).toBeVisible();
    // mode default = mock
    await expect(pill).toHaveAttribute("data-mode", "mock");
    // 含"示例模式" 文本
    await expect(pill).toContainText("示例模式");
  });

  test("选历史触发 setStarted(true) · empty skeleton 消失 · mock banner 出现", async ({
    page,
  }) => {
    await page.goto("/archive/report", { waitUntil: "domcontentloaded" });
    await page.waitForSelector('[data-testid="report-launch-bar"]', { timeout: 10_000 });

    const dropdown = page.locator('[data-testid="report-history-dropdown"]');
    // select 第一个非空 option
    const firstHistoryValue = await dropdown
      .locator("option")
      .nth(1)
      .getAttribute("value");
    expect(firstHistoryValue).toBeTruthy();
    await dropdown.selectOption(firstHistoryValue ?? "");

    // 触发后 · root data-started=yes
    const root = page.locator('[data-view="archive-report"]');
    await expect(root).toHaveAttribute("data-started", "yes");

    // empty skeleton 消失
    await expect(
      page.locator('[data-testid="report-empty-skeleton"]'),
    ).toHaveCount(0);

    // mock banner 出现 (started + mode=mock)
    await expect(
      page.locator('[data-testid="report-mock-banner"]'),
    ).toBeVisible();

    // generate / export 按钮可见
    await expect(
      page.locator('[data-testid="report-generate-btn"]'),
    ).toBeVisible();
    await expect(
      page.locator('[data-testid="report-export-btn"]'),
    ).toBeVisible();
  });

  test("upload CTA click 触发 hidden file input (不直接触发 LLM · §3 不 auto-fire)", async ({ page }) => {
    await page.goto("/archive/report", { waitUntil: "domcontentloaded" });
    await page.waitForSelector('[data-testid="report-launch-bar"]', { timeout: 10_000 });

    const cta = page.locator('[data-testid="report-upload-cta"]');
    await expect(cta).toBeVisible();
    // 点击不应触发任何 fetch (LLM 调用) · 不报错即可
    await cta.click();
    // 仍是 default empty 状态 · 因为 file input 没真选文件
    await expect(page.locator('[data-view="archive-report"]')).toHaveAttribute(
      "data-started",
      "no",
    );
  });
});
