import { test, expect } from "@playwright/test";

/**
 * F-049 · Alert empty state (W-CF2-A2 · empty-state-design-protocol v1.0)
 *
 * 验证 Alert Workspace 默认空白启动:
 *   - 进 /archive/alert 默认 started=false · 渲染 EmptyState
 *   - Hero (一句话 problem statement) + 3 CTA + 红黄绿三灯 skeleton + status pill
 *   - DO NOT 渲染 mock topCases / hitlist / signal map 真实数字
 *   - 6 必加 testid 全可见 (alert-scan-cta / alert-traffic-light-{red,yellow,green} /
 *     alert-empty-skeleton / alert-export-docx-btn)
 *   - 点 secondary CTA → setStarted(true) · workspace 全 panel 渲染
 *   - 点 tertiary (示例) → setStarted(true) + phase=after 看 mock 演示 + demo banner
 *   - tertiary 文案标 (示例) tag (empty-state-design-protocol §2.5)
 *
 * Auth bypass: localStorage seed `platform.auth.v1` 模拟王哲已登录
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

test.describe("F-049 · Alert empty-state default render", () => {
  test("default 进 /archive/alert · 渲染 EmptyState 而非 mock topCases", async ({
    page,
  }) => {
    await page.goto("/archive/alert", { waitUntil: "networkidle" });

    // EmptyState 容器 · 标 started=no
    const root = page.locator('[data-alert-started="no"]');
    await expect(root).toBeVisible();

    const skeleton = page.locator('[data-testid="alert-empty-skeleton"]');
    await expect(skeleton).toBeVisible();

    // §2.3 panel 空骨架 (3 灯 + hitlist + signalmap · 不渲 mock topCases 数字)
    const skeletonPanels = page.locator(
      '[data-testid="alert-empty-skeleton-panels"]',
    );
    await expect(skeletonPanels).toBeVisible();

    // 状态 pill (§2.4)
    const status = page.locator('[data-testid="alert-empty-status-pill"]');
    await expect(status).toBeVisible();
    await expect(status).toContainText("服务正常");

    // 6 必加 testid 全可见
    await expect(page.locator('[data-testid="alert-scan-cta"]')).toBeVisible();
    await expect(page.locator('[data-testid="alert-scan-cta-secondary"]')).toBeVisible();
    await expect(page.locator('[data-testid="alert-history-tertiary"]')).toBeVisible();
    await expect(page.locator('[data-testid="alert-traffic-light-red"]')).toBeVisible();
    await expect(page.locator('[data-testid="alert-traffic-light-yellow"]')).toBeVisible();
    await expect(page.locator('[data-testid="alert-traffic-light-green"]')).toBeVisible();

    // export_docx button (default disabled · 未完成扫描)
    const exportBtn = page.locator('[data-testid="alert-export-docx-btn"]');
    await expect(exportBtn).toBeVisible();
    await expect(exportBtn).toBeDisabled();

    // started=false 时不应渲染完整 workspace 的 traffic-light wall (老 TrafficLightWall)
    // .alert-wall (started=true 才渲) 应该 0
    await expect(page.locator(".alert-wall")).toHaveCount(0);
  });

  test("点 tertiary 历史 (示例) → setStarted true · 渲染完整 workspace + training-mode banner", async ({
    page,
  }) => {
    await page.goto("/archive/alert", { waitUntil: "networkidle" });

    await page.locator('[data-testid="alert-history-tertiary"]').click();

    // 切到 started=yes 的完整 workspace
    const startedRoot = page.locator('[data-alert-started="yes"]');
    await expect(startedRoot).toBeVisible();

    // EmptyState 不再渲染
    await expect(page.locator('[data-alert-started="no"]')).toHaveCount(0);

    // training-mode banner 显示 (tertiary 触发 handleSelectSession("sess_manuf_policy_event")
    // → selectedSessionId !== DEFAULT_SESSION_ID && !liveData → showTrainingModeBanner=true)
    // worker-A4-alert 4-gate · live-fallback-banner-spec §2 规则 2
    await expect(page.locator('[data-testid="alert-training-mode-banner"]')).toBeVisible();

    // 完整 workspace 的老 TrafficLightWall 渲染 (含 hitlist row testid)
    await expect(page.locator(".alert-wall")).toBeVisible();
    const hitRows = page.locator('[data-testid="alert-hitlist-row"]');
    expect(await hitRows.count()).toBeGreaterThan(0);
  });

  test("tertiary CTA 文案标 (示例) tag · empty-state-design-protocol §2.5 demo 显式标记", async ({
    page,
  }) => {
    await page.goto("/archive/alert", { waitUntil: "networkidle" });

    const tertiary = page.locator('[data-testid="alert-history-tertiary"]');
    await expect(tertiary).toContainText("示例");
    await expect(tertiary).toContainText("培训演示");
  });

  test("点 primary CTA · setStarted(true) + scan 进入 scanning phase", async ({
    page,
  }) => {
    await page.goto("/archive/alert", { waitUntil: "networkidle" });

    await page.locator('[data-testid="alert-scan-cta"]').click();

    // 切到 started=yes
    const startedRoot = page.locator('[data-alert-started="yes"]');
    await expect(startedRoot).toBeVisible();

    // 完整 workspace 渲染 (TrafficLightWall · ScanProgress)
    await expect(page.locator(".alert-wall")).toBeVisible();

    // primary trigger 不显 training-mode banner (只 tertiary 切 mock session 才显)
    // worker-A4-alert: primary CTA 保持 DEFAULT_SESSION_ID · showTrainingModeBanner=false
    await expect(page.locator('[data-testid="alert-training-mode-banner"]')).toHaveCount(0);
  });
});
