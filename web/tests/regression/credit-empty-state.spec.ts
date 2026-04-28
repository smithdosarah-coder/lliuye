import { test, expect } from "@playwright/test";

/**
 * F-048 · Credit empty state (W-CF-A2 · empty-state-design-protocol v1.0)
 *
 * 验证 Credit Workspace 默认空白启动:
 *   - 进 /archive/credit 默认 started=false · 渲染 EmptyState
 *   - Hero (一句话 problem statement) + 3 stage_tab + 3 CTA + skeleton + status pill
 *   - DO NOT 渲染 mock candidates / radar / signals / 真实数字
 *   - 切 stage_tab → testid 命中 corporate / small_business / retail
 *   - 点 secondary CTA (mock) → setStarted(true) · workspace 全 panel 渲染
 *   - 点 tertiary (示例) → setStarted(true) + scanned=true · 看 mock 演示
 *
 * Auth bypass: localStorage seed `platform.auth.v1` 模拟王哲已登录
 *   王哲 role=rm · ACCESS=[channel, report, credit, alert, compli, riskctrl] 全开
 */

const SEED_AUTH = JSON.stringify({
  state: {
    currentUser: {
      id: "u_wangzhe",
      name: "王哲",
      role: "rm",
      team: "华东·上海第一支行",
      avatar: "哲",
    },
  },
  version: 0,
});

test.beforeEach(async ({ context }) => {
  await context.addInitScript((seed) => {
    window.localStorage.setItem("platform.auth.v1", seed);
  }, SEED_AUTH);
});

test.describe("F-048 · Credit empty-state default render", () => {
  test("default 进 /archive/credit · 渲染 EmptyState 而非 mock data", async ({
    page,
  }) => {
    await page.goto("/archive/credit", { waitUntil: "networkidle" });

    // EmptyState 容器可见 · 标 started=no
    const root = page.locator('[data-credit-started="no"]');
    await expect(root).toBeVisible();

    // EmptyState skeleton 容器
    const skeleton = page.locator('[data-testid="credit-empty-skeleton"]');
    await expect(skeleton).toBeVisible();

    // §2.3 panel 空骨架 (不渲染真实 candidates / mock data 数字)
    const skeletonPanels = page.locator(
      '[data-testid="credit-empty-skeleton-panels"]',
    );
    await expect(skeletonPanels).toBeVisible();

    // 状态 pill 在 (§2.4 status pill)
    const status = page.locator('[data-testid="credit-empty-status-pill"]');
    await expect(status).toBeVisible();
    await expect(status).toContainText("服务正常");

    // 主 CTA / 次 CTA / 历史 CTA 都在
    await expect(page.locator('[data-testid="credit-decision-cta"]')).toBeVisible();
    await expect(page.locator('[data-testid="credit-decision-cta-secondary"]')).toBeVisible();
    await expect(page.locator('[data-testid="credit-history-tertiary"]')).toBeVisible();

    // 红线列表 placeholder
    await expect(page.locator('[data-testid="credit-redlines-list"]')).toBeVisible();

    // export_docx button (default disabled · 未决策完成)
    const exportBtn = page.locator('[data-testid="credit-export-docx-btn"]');
    await expect(exportBtn).toBeVisible();
    await expect(exportBtn).toBeDisabled();

    // 不应渲染完整 workspace 的 RiskRadarPreview (那是 started=true 后才渲)
    await expect(page.locator('[data-testid="risk-radar-preview"]')).toHaveCount(0);
  });

  test("3 stage_tab 切换 · testid 命中 corporate / small_business / retail", async ({
    page,
  }) => {
    await page.goto("/archive/credit", { waitUntil: "networkidle" });

    // 默认 corp (= corporate)
    const corpTab = page.locator('[data-testid="credit-stage-tab-corporate"]');
    const sbTab = page.locator('[data-testid="credit-stage-tab-small_business"]');
    const retailTab = page.locator('[data-testid="credit-stage-tab-retail"]');

    await expect(corpTab).toBeVisible();
    await expect(sbTab).toBeVisible();
    await expect(retailTab).toBeVisible();

    // 默认 corporate 选中
    await expect(corpTab).toHaveAttribute("data-active", "yes");

    // 切 small_business · root data-credit-mode 切 small
    await sbTab.click();
    await expect(sbTab).toHaveAttribute("data-active", "yes");
    await expect(corpTab).toHaveAttribute("data-active", "no");
    const root = page.locator('[data-credit-started="no"]');
    await expect(root).toHaveAttribute("data-credit-mode", "small");

    // 切 retail
    await retailTab.click();
    await expect(retailTab).toHaveAttribute("data-active", "yes");
    await expect(root).toHaveAttribute("data-credit-mode", "retail");
  });

  test("点 tertiary 历史 (示例) → setStarted true · 渲染完整 workspace + scanned=yes", async ({
    page,
  }) => {
    await page.goto("/archive/credit", { waitUntil: "networkidle" });

    // 点 tertiary (示例 · 培训演示)
    await page.locator('[data-testid="credit-history-tertiary"]').click();

    // 切到 started=yes 的完整 workspace
    const startedRoot = page.locator('[data-credit-started="yes"]');
    await expect(startedRoot).toBeVisible();

    // EmptyState 不再渲染
    await expect(page.locator('[data-credit-started="no"]')).toHaveCount(0);

    // RiskRadarPreview (Q-033) 这时应渲染
    await expect(page.locator('[data-testid="risk-radar-preview"]')).toBeVisible();

    // scanned=yes (mock 数据 fade-in)
    await expect(startedRoot).toHaveAttribute("data-scanned", "yes");
  });

  test("tertiary CTA 文案标 (示例) tag · empty-state-design-protocol §2.5 demo 显式标记", async ({
    page,
  }) => {
    await page.goto("/archive/credit", { waitUntil: "networkidle" });

    const tertiary = page.locator('[data-testid="credit-history-tertiary"]');
    await expect(tertiary).toContainText("示例");
    await expect(tertiary).toContainText("培训演示");
  });
});
