import { test, expect, type Route } from "@playwright/test";

/**
 * ALL IN Phase B.2 (PM 2026-05-10 真意 reframe) · Alert Workspace E2E spec.
 *
 * 派活 §不可 GO 验收硬线:
 *   1. /api/alert/demo/run 不再 yield fixture event (走真后端 backbone)
 *   2. fixtures.ts / ALERT_EVIDENCE / ModePill grep 0 命中 (file-level grep ·
 *      由 step 11 doc + git log 验证 · 本 spec 验 runtime 行为)
 *   3. silent fallback fake → backend fallback banner 真显 (severity / reason)
 *   4. data-input-mode 反映 toggle 状态 · backend pipeline 都真跑
 *   5. data-data-source 反映 backend emit 真值 (live / mock_fallback / mock_forced)
 *
 * Auth bypass: localStorage seed admin 角色 (alert.invoke 权限)
 *
 * 替代 (DELETED):
 *   - alert-pilot-4gate.spec.ts · Phase A 4-gate (mock dropdown / tertiary CTA · 已删)
 *   - alert-empty-state.spec.ts · Phase A empty-state (3 CTA / tertiary 示例 · 已删)
 *
 * 不依赖真 Tavily / DeepSeek key · 用 page.route mock SSE 流.
 */

const SEED_AUTH_ADMIN = JSON.stringify({
  state: {
    currentUser: {
      id: "u_admin",
      name: "管理员",
      role: "admin",
      team: "总行 · 风险中台",
      avatar: "管",
    },
  },
  version: 0,
});

test.beforeEach(async ({ context }) => {
  await context.addInitScript((seed) => {
    window.localStorage.setItem("platform.auth.v1", seed);
  }, SEED_AUTH_ADMIN);
});

/** Build a minimal SSE response containing 1 stage + 1 done event. */
function buildSseResponse(opts: {
  sessionId: string;
  mode: string;
  dataSource: "live" | "mock_fallback" | "mock_forced" | "mock";
  fallback?: {
    source: string;
    reason: string;
    severity: "info" | "warn" | "error";
    message: string;
    hint: string;
    retried: boolean;
  };
}): string {
  const stage = {
    event: "stage",
    stage: "summary",
    status: "done",
    message: "扫描完成",
  };
  const done: Record<string, unknown> = {
    event: "done",
    session_id: opts.sessionId,
    mode: opts.mode,
    data_source: opts.dataSource,
    panels: {
      hit_list: { red: [], yellow: [], green: [] },
      top_cases: [],
      dispositions: {},
    },
    metrics: { red: 0, yellow: 0, green: 0, total_scanned: 0 },
    summary: "演示运行 · 0 命中",
    scenario_key: "alert-pool",
    kb_state: "0 项联机中",
    totals: { red: 0, yellow: 0, green: 0 },
    industry_distribution: [],
    signal_heatmap: [],
    reach_rate: [],
    ledger_entries_written: 0,
  };
  if (opts.fallback) done.fallback = opts.fallback;
  return [
    `data: ${JSON.stringify(stage)}\n\n`,
    `data: ${JSON.stringify(done)}\n\n`,
  ].join("");
}

test.describe("Phase B.2 · alert workspace · 形态切换 toggle + backend fallback banner", () => {
  test("spec 1 · 默认 live mode · workspace 渲染 toggle + 2 mode 按钮", async ({
    page,
  }) => {
    await page.goto("/archive/alert", { waitUntil: "networkidle" });

    const root = page.locator('[data-testid="alert-workspace"]');
    await expect(root).toBeVisible();
    await expect(root).toHaveAttribute("data-alert-started", "no");
    await expect(root).toHaveAttribute("data-input-mode", "live");
    await expect(root).toHaveAttribute("data-data-source", "live");

    // toggle 可见 + 2 mode 按钮
    const toggle = page.locator('[data-testid="alert-input-mode-toggle"]');
    await expect(toggle).toBeVisible();
    const liveBtn = page.locator('[data-testid="alert-input-mode-live"]');
    const demoBtn = page.locator('[data-testid="alert-input-mode-demo"]');
    await expect(liveBtn).toBeVisible();
    await expect(demoBtn).toBeVisible();
    await expect(liveBtn).toHaveAttribute("data-active", "yes");
    await expect(demoBtn).toHaveAttribute("data-active", "no");
  });

  test("spec 2 · click 演示模式 toggle · data-input-mode 切 demo · preview 卡切换", async ({
    page,
  }) => {
    await page.goto("/archive/alert", { waitUntil: "networkidle" });

    const demoBtn = page.locator('[data-testid="alert-input-mode-demo"]');
    await demoBtn.click();

    const root = page.locator('[data-testid="alert-workspace"]');
    await expect(root).toHaveAttribute("data-input-mode", "demo");

    const liveBtn = page.locator('[data-testid="alert-input-mode-live"]');
    await expect(demoBtn).toHaveAttribute("data-active", "yes");
    await expect(liveBtn).toHaveAttribute("data-active", "no");

    // CTA 文案 mode-aware (per AlertEmptyState ctaTitle)
    const ctaTitle = page.locator('[data-testid="alert-scan-cta"] .alert-empty__cta-title');
    await expect(ctaTitle).toContainText("启动 demo 扫描");

    // preview 卡 mode-aware (alert-pool 180 户 vs 真实模式输入清单)
    const preview = page.locator('[data-testid="alert-input-preview"]');
    await expect(preview).toHaveAttribute("data-mode", "demo");
    await expect(preview).toContainText("alert-pool/ batch");
    await expect(preview).toContainText("180 户");
  });

  test("spec 3 · live mode · /api/alert/scan SSE done · backend fallback banner reason=alert_pool_batch 不显 (live 路径)", async ({
    page,
  }) => {
    // mock /api/alert/scan SSE response (live mode · web_live · no fallback)
    await page.route("**/api/alert/scan", async (route: Route) => {
      const body = buildSseResponse({
        sessionId: "alert-test-live-001",
        mode: "web_live",
        dataSource: "live",
      });
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body,
      });
    });

    await page.goto("/archive/alert", { waitUntil: "networkidle" });

    // live mode default · click primary CTA 触发扫描
    const cta = page.locator('[data-testid="alert-scan-cta"]');
    await cta.click();

    // 等 SSE done event 处理完
    const root = page.locator('[data-testid="alert-workspace"]');
    await expect(root).toHaveAttribute("data-data-source", "live", { timeout: 5000 });

    // live + no fallback → backend-fallback-banner 不渲染
    const bannerLocator = page.locator('[data-testid="alert-backend-fallback-banner"]');
    await expect(bannerLocator).toHaveCount(0);
  });

  test("spec 4 · demo mode · /api/alert/demo/run · backend fallback banner reason=alert_pool_batch + severity=info", async ({
    page,
  }) => {
    await page.route("**/api/alert/demo/run", async (route: Route) => {
      const body = buildSseResponse({
        sessionId: "alert-test-demo-001",
        mode: "web_live",
        dataSource: "live",
        fallback: {
          source: "Demo Input",
          reason: "alert_pool_batch",
          severity: "info",
          message: "演示模式 · 输入 alert-pool 180 户在贷客户池 · backend 真跑双路扫 + LLM 处置",
          hint: "线上场景把 clients.csv 替换为银行真实在贷客户名录即可 · backend 路径不变",
          retried: false,
        },
      });
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body,
      });
    });

    await page.goto("/archive/alert", { waitUntil: "networkidle" });

    // 切 demo mode · 触发扫描
    await page.locator('[data-testid="alert-input-mode-demo"]').click();
    await page.locator('[data-testid="alert-scan-cta"]').click();

    // backend fallback banner 渲染 (severity=info · reason=alert_pool_batch · 派活红线)
    const banner = page.locator('[data-testid="alert-backend-fallback-banner"]');
    await expect(banner).toBeVisible({ timeout: 5000 });
    await expect(banner).toHaveAttribute("data-severity", "info");
    await expect(banner).toHaveAttribute("data-reason", "alert_pool_batch");
    await expect(banner).toContainText("Demo Input");
    await expect(banner).toContainText("alert-pool 180 户");
  });

  test("spec 5 · demo mode · Tavily key missing · backend fallback banner severity=warn + reason=tavily_key_missing", async ({
    page,
  }) => {
    await page.route("**/api/alert/demo/run", async (route: Route) => {
      const body = buildSseResponse({
        sessionId: "alert-test-demo-tavily-missing",
        mode: "tavily_key_missing",
        dataSource: "mock_fallback",
        fallback: {
          source: "Tavily",
          reason: "tavily_key_missing",
          severity: "warn",
          message: "Tavily API Key 未配置 · 仅内部规则命中 · 外部源 0 hit (不返合成 mock 结果)",
          hint: "设置 TAVILY_API_KEY 环境变量后重启服务 → 切真实外部源",
          retried: false,
        },
      });
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body,
      });
    });

    await page.goto("/archive/alert", { waitUntil: "networkidle" });
    await page.locator('[data-testid="alert-input-mode-demo"]').click();
    await page.locator('[data-testid="alert-scan-cta"]').click();

    const banner = page.locator('[data-testid="alert-backend-fallback-banner"]');
    await expect(banner).toBeVisible({ timeout: 5000 });
    await expect(banner).toHaveAttribute("data-severity", "warn");
    await expect(banner).toHaveAttribute("data-reason", "tavily_key_missing");
    await expect(banner).toContainText("Tavily");
    await expect(banner).toContainText("0 hit");

    // data-data-source 反映 backend emit · mock_fallback (用户必感知降级)
    const root = page.locator('[data-testid="alert-workspace"]');
    await expect(root).toHaveAttribute("data-data-source", "mock_fallback");
  });

  test("spec 6 · scan fail · 不 silent 切 mock_fallback 标签 · liveFail banner 显 retry", async ({
    page,
  }) => {
    await page.route("**/api/alert/scan", async (route: Route) => {
      await route.fulfill({
        status: 502,
        contentType: "text/plain",
        body: "Bad Gateway",
      });
    });

    await page.goto("/archive/alert", { waitUntil: "networkidle" });
    await page.locator('[data-testid="alert-scan-cta"]').click();

    // liveFail banner 显 (LiveFailError · 不假 wrap mock_fallback)
    const banner = page.locator('[data-testid="alert-live-fail-banner"]');
    await expect(banner).toBeVisible({ timeout: 5000 });
    await expect(banner).toHaveAttribute("data-status", "502");

    // data-data-source 留 default "live" · 不 silent 切 "mock_fallback" (派活红线 #4)
    const root = page.locator('[data-testid="alert-workspace"]');
    await expect(root).toHaveAttribute("data-data-source", "live");
  });
});
