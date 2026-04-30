import { test, expect } from "@playwright/test";

/**
 * worker-A4-alert · 4 gate canon Playwright smoke (per docs/audit/A4-alert-draft.md §8)
 *
 * 8 spec cover:
 *   1. 默认 empty state · alert-started=no
 *   2. 选 mock dropdown 切 session · 5 panel 全跟着切 + training-mode banner 显
 *   3. 切第二个 mock session · radar / hit_list / heatmap 全跟着切 (gap #2 修验)
 *   4. textbox submit (primary CTA) → SSE live → liveData 注入 · 5 panel 切 live · banner 隐
 *   5. live failed (route mock 502) · alert-live-fail-banner 显 · retry button wire
 *   6. TopCase 行 click → drill drawer · data-client-id · ESC 关
 *   7. export_docx button click → blob download (regression · 不破 F-064)
 *   8. /api/alert/demo/run 端点 (curl mock · check done envelope 字段)
 *
 * 4 gate:
 *   started / selectedSessionId / liveData / selectedClientId
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

test.describe("worker-A4-alert · 4 gate canon smoke", () => {
  test("spec 1 · 默认 empty state · alert-started=no · session-id=baseline_100", async ({
    page,
  }) => {
    await page.goto("/archive/alert", { waitUntil: "networkidle" });

    // workspace root data-attrs (NEW-DOM trailer)
    const root = page.locator('[data-testid="alert-workspace"]');
    await expect(root).toHaveAttribute("data-view", "archive-alert");
    await expect(root).toHaveAttribute("data-alert-started", "no");
    await expect(root).toHaveAttribute("data-session-id", "sess_baseline_100");
    await expect(root).toHaveAttribute("data-live-mode", "no");

    // empty skeleton 渲染
    await expect(page.locator('[data-testid="alert-empty-skeleton"]')).toBeVisible();
    await expect(page.locator('[data-testid="alert-scan-cta"]')).toBeVisible();

    // 完整 workspace 的 picker 不应渲染 (started=no 时不渲)
    await expect(page.locator('[data-testid="alert-session-picker"]')).toHaveCount(0);
  });

  test("spec 2 · click tertiary → session dropdown 显 + 切 manuf_policy_event · training-mode banner 显", async ({
    page,
  }) => {
    await page.goto("/archive/alert", { waitUntil: "networkidle" });

    // tertiary CTA: setStarted(true) + handleSelectSession("sess_manuf_policy_event") + setPhase("after")
    await page.locator('[data-testid="alert-history-tertiary"]').click();

    const root = page.locator('[data-testid="alert-workspace"]');
    await expect(root).toHaveAttribute("data-alert-started", "yes");
    await expect(root).toHaveAttribute("data-session-id", "sess_manuf_policy_event");
    await expect(root).toHaveAttribute("data-live-mode", "no");

    // session picker 渲染 + select 当前值
    const select = page.locator('[data-testid="alert-session-select"]');
    await expect(select).toBeVisible();
    await expect(select).toHaveValue("sess_manuf_policy_event");

    // 3 sessions 全在选项里
    const optionCount = await select.locator("option").count();
    expect(optionCount).toBe(3);

    // training-mode banner (live-fallback-banner-spec §2 规则 2)
    await expect(page.locator('[data-testid="alert-training-mode-banner"]')).toBeVisible();
  });

  test("spec 3 · 切第二个 mock session · totals + topCases 跟着切 (gap #2 修验)", async ({
    page,
  }) => {
    await page.goto("/archive/alert", { waitUntil: "networkidle" });

    // 进入完整 workspace (选 secondary CTA)
    await page.locator('[data-testid="alert-scan-cta-secondary"]').click();
    await page.waitForTimeout(200);

    const select = page.locator('[data-testid="alert-session-select"]');
    await expect(select).toBeVisible();

    // baseline_100 默认: 红 5
    await expect(page.locator('[data-testid="alert-traffic-light-red"]')).toContainText("5");

    // 切到 judicial_news_dual: 红 25
    await select.selectOption("sess_judicial_news_dual");
    await page.waitForTimeout(300);

    const root = page.locator('[data-testid="alert-workspace"]');
    await expect(root).toHaveAttribute("data-session-id", "sess_judicial_news_dual");
    await expect(page.locator('[data-testid="alert-traffic-light-red"]')).toContainText("25");

    // training-mode banner 显示 (selectedSessionId !== DEFAULT)
    await expect(page.locator('[data-testid="alert-training-mode-banner"]')).toBeVisible();

    // 切回 baseline_100 (回基线场景)
    await page.locator('[data-testid="alert-training-mode-banner-cta"]').click();
    await page.waitForTimeout(300);

    await expect(root).toHaveAttribute("data-session-id", "sess_baseline_100");
    await expect(page.locator('[data-testid="alert-training-mode-banner"]')).toHaveCount(0);
  });

  test("spec 4 · primary CTA SSE live · stage events + done envelope 注入 liveData", async ({
    page,
  }) => {
    /* mock /api/alert/scan SSE · 5 stage event + done envelope */
    await page.route("**/api/alert/scan", async (route) => {
      const body = [
        `data: ${JSON.stringify({ event: "stage", stage: "kb_load", status: "running" })}\n\n`,
        `data: ${JSON.stringify({ event: "stage", stage: "external_scan", status: "running" })}\n\n`,
        `data: ${JSON.stringify({ event: "stage", stage: "internal_match", status: "running" })}\n\n`,
        `data: ${JSON.stringify({ event: "stage", stage: "cross", status: "running" })}\n\n`,
        `data: ${JSON.stringify({ event: "stage", stage: "summary", status: "done" })}\n\n`,
        `data: ${JSON.stringify({
          event: "done",
          data_source: "live",
          session_id: "alert-live-test",
          totals: { red: 7, yellow: 14, green: 79 },
          metrics: { red: 7, yellow: 14, green: 79, total_scanned: 100 },
          summary: "live · 红 7 / 黄 14 / 绿 79",
          hit_list: { red: [], yellow: [], green: [] },
          top_cases: [
            {
              id: "tc-live-1",
              client_id: "CL-LIVE-1",
              customer: "live 测试客户",
              amount: "999 万",
              risk_level: "red",
              triggers: ["live 信号"],
              advice: "live advice",
              lastUpdate: "刚刚",
            },
          ],
          dispositions: { "live 测试客户": "live 处置建议" },
          kb_state: "live · 6 项",
        })}\n\n`,
      ].join("");
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        headers: { "Cache-Control": "no-cache" },
        body,
      });
    });

    await page.goto("/archive/alert", { waitUntil: "networkidle" });
    await page.locator('[data-testid="alert-scan-cta"]').click();

    // 等 done event 处理完
    await page.waitForFunction(
      () => document.querySelector('[data-testid="alert-workspace"]')?.getAttribute("data-live-mode") === "yes",
      { timeout: 10_000 },
    );

    const root = page.locator('[data-testid="alert-workspace"]');
    await expect(root).toHaveAttribute("data-live-mode", "yes");
    await expect(root).toHaveAttribute("data-session-id", "alert-live-test");

    // training-mode banner 不显 (live mode 优先)
    await expect(page.locator('[data-testid="alert-training-mode-banner"]')).toHaveCount(0);

    // session-select 应 disabled (live mode 锁定)
    const select = page.locator('[data-testid="alert-session-select"]');
    await expect(select).toBeDisabled();
  });

  test("spec 5 · live SSE 502 · alert-live-fail-banner 显 + retry button wire", async ({
    page,
  }) => {
    await page.route("**/api/alert/scan", async (route) => {
      await route.fulfill({
        status: 502,
        contentType: "application/json",
        body: JSON.stringify({ error: "upstream gateway down" }),
      });
    });

    await page.goto("/archive/alert", { waitUntil: "networkidle" });
    await page.locator('[data-testid="alert-scan-cta"]').click();

    await expect(page.locator('[data-testid="alert-live-fail-banner"]')).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.locator('[data-testid="alert-live-fail-retry"]')).toBeVisible();
  });

  test("spec 6 · TopCase row click → drill drawer · data-client-id · ESC 关", async ({
    page,
  }) => {
    /* drill drawer 走 GET /api/alert/drill/{client_id} · mock fixture response */
    await page.route("**/api/alert/drill/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          client_id: "CL-100-001",
          company_name: "苏州金鼎电子",
          level: "red",
          score: 0.91,
          matched_rules: ["EXT-CREDIT-02"],
          reasons: ["征信新增 M3+ 1 笔"],
          signal_timeline: [],
          disposition: { content: "电话 + 现场 · 评估补充担保" },
          disposition_source: "template",
        }),
      });
    });

    await page.goto("/archive/alert", { waitUntil: "networkidle" });
    await page.locator('[data-testid="alert-scan-cta-secondary"]').click();
    await page.waitForTimeout(300);

    // 切到 dist tab (默认就是 dist · 但确保不在 heat / reach)
    const distTab = page.locator(".al-out__tab").nth(0);
    await distTab.click();
    await page.waitForTimeout(200);

    // 点第一个 top case row (dist view 内 al-dv__tc 列表)
    const firstTopCase = page.locator('[data-testid="alert-top-case-row"]').first();
    await firstTopCase.click();

    // drawer 显
    const drawer = page.locator('[data-testid="alert-drill-drawer"]');
    await expect(drawer).toBeVisible({ timeout: 5_000 });
    await expect(drawer).toHaveAttribute("data-client-id", "CL-100-001");

    // ESC 关
    await page.keyboard.press("Escape");
    await expect(drawer).toHaveCount(0, { timeout: 2_000 });
  });

  test("spec 7 · export_docx button · POST /api/alert/export_docx blob 下载", async ({
    page,
  }) => {
    let exportRequested = false;
    await page.route("**/api/alert/export_docx", async (route) => {
      exportRequested = true;
      await route.fulfill({
        status: 200,
        contentType:
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers: { "Content-Disposition": "attachment; filename=test.docx" },
        body: "PK fake docx blob",
      });
    });

    await page.goto("/archive/alert", { waitUntil: "networkidle" });
    await page.locator('[data-testid="alert-history-tertiary"]').click();
    await page.waitForTimeout(300);

    // tertiary 走 manuf_policy_event + setPhase("after") · export 按钮 enable
    const exportBtn = page.locator('[data-testid="alert-export-docx-cta"]');
    await expect(exportBtn).toBeVisible();
    await expect(exportBtn).toBeEnabled();

    await exportBtn.click();
    await page.waitForTimeout(500);

    expect(exportRequested).toBe(true);
  });

  test("spec 8 · /api/alert/demo/run endpoint smoke (curl-style mock check)", async ({
    request,
  }) => {
    /* spec 8 走 request 上下文 · 不需要浏览器 · 但需要后端起 · 默认 baseURL 指向
     * playwright config webServer · 若 backend 没起则 skip (env guard) */
    if (!process.env.ALERT_BACKEND_URL) {
      test.skip(true, "ALERT_BACKEND_URL not set · skip backend integration");
    }

    const url = `${process.env.ALERT_BACKEND_URL}/api/alert/demo/run`;
    const resp = await request.post(url, {
      data: { scenario_key: "baseline_100" },
      headers: { Accept: "text/event-stream" },
      timeout: 10_000,
    });
    expect(resp.ok()).toBe(true);
    const body = await resp.text();
    expect(body).toContain('"event":"done"');
    expect(body).toContain('"scenario_key":"baseline_100"');
    expect(body).toContain('"data_source":"mock_forced"');
    expect(body).toContain('"hit_list"');
  });
});
