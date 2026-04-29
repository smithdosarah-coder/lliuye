import { test, expect } from "@playwright/test";

/**
 * F-050 · Compliance Workspace · 空白启动 + 3 CTA 分级
 *
 * 必读 contracts:
 *   - docs/contracts/empty-state-design-protocol.md v1.0
 *   - docs/contracts/agent-compli-spec.md (Stage A.5)
 *
 * 验:
 *   1. /archive/compliance default state · started=no · 8 必备 testid 全在 (含 empty-skeleton)
 *   2. mock 数据**不 default load** · PolicyTicker / Matrix / RevisionPanel 不渲染
 *   3. dropdown 标 (示例) tag · 与 production 路径分离
 *   4. Tertiary 历史选项触发 → started=yes + demo banner 显示
 *   5. Primary CTA「开始政策比对」按钮可点击触发
 *   6. Secondary 「用模板快速比对」按钮存在
 */
test.describe("F-050 · Compliance Workspace 空白启动 + 3 CTA", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/archive/compliance", { waitUntil: "networkidle" });
  });

  test("default state · started=no · 8 必备 testid 都在 + 不显示 mock 真数据", async ({
    page,
  }) => {
    // 根容器 started=no
    const root = page.locator('[data-testid="compli-workspace"]');
    await expect(root).toBeVisible();
    await expect(root).toHaveAttribute("data-started", "no");

    // 8 个 onboarding 必备 testid 都在 page 上
    await expect(page.locator('[data-testid="compli-policy-upload-cta"]')).toBeVisible();
    await expect(page.locator('[data-testid="compli-business-upload-cta"]')).toBeVisible();
    await expect(page.locator('[data-testid="compli-policy-scan-cta"]')).toBeVisible();
    await expect(page.locator('[data-testid="compli-empty-skeleton"]')).toBeVisible();

    // empty 状态下 · matrix / revision / conflict-chip 不渲染（在 started 条件块内）
    await expect(page.locator('[data-testid="compli-matrix-cell"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="compli-conflict-chip"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="compli-revision-draft"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="compli-export-docx-btn"]')).toHaveCount(0);
  });

  test("dropdown 显式标 (示例) tag · production / demo 路径分离", async ({ page }) => {
    const dropdown = page.locator('[data-testid="compli-history-dropdown"]');
    await expect(dropdown).toBeVisible();
    // 至少含一个 (示例) 选项
    await expect(dropdown.locator("option")).toContainText(/示例/);
  });

  test("3 CTA 分级 · primary · secondary · tertiary 都存在", async ({ page }) => {
    // Primary · 上传后「开始政策比对」按钮 (UploadRail 内)
    await expect(page.locator('[data-testid="compli-policy-scan-cta"]')).toBeVisible();
    // Secondary · 「用模板快速比对」
    await expect(page.locator('[data-testid="compli-template-check-cta"]')).toBeVisible();
    // Tertiary · 历史 dropdown
    await expect(page.locator('[data-testid="compli-history-dropdown"]')).toBeVisible();
  });

  test("Tertiary 历史选项触发 → started=yes · demo banner 显示", async ({ page }) => {
    // 找第一个 (示例) option · 切下拉
    const dropdown = page.locator('[data-testid="compli-history-dropdown"]');
    const firstDemoOption = dropdown.locator("option").nth(1);
    const value = await firstDemoOption.getAttribute("value");
    if (!value) test.skip(true, "no demo option to select");

    await dropdown.selectOption(value!);

    // root data-started 切 yes
    await expect(page.locator('[data-testid="compli-workspace"]')).toHaveAttribute(
      "data-started",
      "yes",
    );

    // demo banner 显示
    await expect(page.locator('[data-testid="compli-demo-banner"]')).toBeVisible();

    // empty-skeleton 不再显示
    await expect(page.locator('[data-testid="compli-empty-skeleton"]')).toHaveCount(0);

    // mock data 现在出现 (matrix / revision / conflict-chip 渲染)
    await expect(page.locator('[data-testid="compli-revision-draft"]').first()).toBeVisible();
  });

  test("Primary CTA 可触发 · scan 按钮 click 后 started=yes (网络可能 mock)", async ({
    page,
  }) => {
    // mock backend SSE response · 不依赖真后端起来
    await page.route("**/api/compliance/policy_scan", async (route) => {
      const resp = [
        'data: {"event":"stage","payload":{"type":"stage","stage":"rule_extract","status":"done","count":2}}',
        '',
        'data: {"event":"stage","payload":{"type":"scan","scan_id":"test-sid-001","stats":{"violation_count":1,"severe_count":0,"normal_count":1,"observation_count":0}}}',
        '',
        'data: {"event":"done"}',
        '',
        '',
      ].join("\n");
      await route.fulfill({
        status: 200,
        headers: { "content-type": "text/event-stream; charset=utf-8" },
        body: resp,
      });
    });

    const cta = page.locator('[data-testid="compli-policy-scan-cta"]');
    await cta.click();

    // started=yes after click
    await expect(page.locator('[data-testid="compli-workspace"]')).toHaveAttribute(
      "data-started",
      "yes",
    );
  });

  /**
   * F-054 fix · W-FIX2-A3 (live-fallback-banner-spec v1.0 §1.5):
   *   Primary CTA 之前 hardcode `force_mock: true` 静默走 mock · UI 标 live · 用户欺骗.
   *   现在 primary 路径必须 force_mock:false · 失败显 banner · mock 仅 tertiary 路径.
   */
  test("F-054 fix · primary CTA POST body 必含 force_mock:false (不再 hardcode true)", async ({
    page,
  }) => {
    let captured: { force_mock?: unknown; policy_doc?: unknown } | null = null;
    await page.route("**/api/compliance/policy_scan", async (route) => {
      const req = route.request();
      try {
        captured = req.postDataJSON() as typeof captured;
      } catch {
        captured = null;
      }
      const sse = [
        'data: {"event":"stage","payload":{"type":"scan","scan_id":"sid-fix2","stats":{}}}',
        '',
        'data: {"event":"done"}',
        '',
        '',
      ].join("\n");
      await route.fulfill({
        status: 200,
        headers: { "content-type": "text/event-stream; charset=utf-8" },
        body: sse,
      });
    });

    await page.locator('[data-testid="compli-policy-scan-cta"]').click();

    // 等 SSE drain + state propagate (~3.5s 假进度 · 但 fetch 立即触发)
    await page.waitForTimeout(3500);

    expect(captured).not.toBeNull();
    expect(captured!.force_mock).toBe(false);
    expect(captured!.policy_doc).toBeTruthy();
  });

  test("F-054 fix · primary path 失败 → live-fail banner 显 (HTTP 503 · retry button)", async ({
    page,
  }) => {
    await page.route("**/api/compliance/policy_scan", async (route) => {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "service unavailable" }),
      });
    });

    await page.locator('[data-testid="compli-policy-scan-cta"]').click();

    /* UploadRail 假进度 5 step × 520ms ≈ 2.6s · 等到失败 banner 出现 */
    const banner = page.locator('[data-testid="compli-live-fail-banner"]');
    await expect(banner).toBeVisible({ timeout: 6000 });
    await expect(banner).toHaveAttribute("data-status", "503");
    await expect(banner).toContainText(/HTTP 503/);
    await expect(banner).toContainText(/policy_scan/);

    /* retry button 存在 */
    await expect(page.locator('[data-testid="compli-live-fail-retry"]')).toBeVisible();
  });
});
