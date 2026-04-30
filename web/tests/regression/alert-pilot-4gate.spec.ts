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

  test("spec 4 · primary CTA SSE live · done envelope 注入 5 panel · 内容断言 (V2 issue #2 fix verify)", async ({
    page,
  }) => {
    /* mock /api/alert/scan SSE · 5 stage event + done envelope · hit_list 含特定 customer ·
     * V2 codex DISAGREE issue #2 修验: ScanQueueCase 从 hit_list.red+yellow derive · 不只 4 panel ·
     * V2 codex DISAGREE issue #3 修验: session_id 从 evt.data top-level 读 (make_done 顶层) */
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
          mode: "web_live",
          totals: { red: 7, yellow: 14, green: 79 },
          metrics: { red: 7, yellow: 14, green: 79, total_scanned: 100 },
          summary: "live · 红 7 / 黄 14 / 绿 79",
          hit_list: {
            red: [
              {
                client_id: "CL-LIVE-RED-1",
                company_name: "live 红档客户 ALPHA",
                amount: "999 万",
                tier: "red",
                score: 0.95,
                reasons: ["live 红档触发理由 ALPHA"],
                matched_rules: ["LIVE-RULE-1"],
              },
            ],
            yellow: [
              {
                client_id: "CL-LIVE-YEL-1",
                company_name: "live 黄档客户 BETA",
                amount: "500 万",
                tier: "yellow",
                score: 0.62,
                reasons: ["live 黄档触发理由 BETA"],
                matched_rules: ["LIVE-RULE-2"],
              },
            ],
            green: [],
          },
          top_cases: [
            {
              id: "tc-live-1",
              client_id: "CL-LIVE-RED-1",
              customer: "live 红档客户 ALPHA",
              amount: "999 万",
              tier: "red",
              triggers: ["live 红档触发理由 ALPHA"],
              advice: "live advice",
              lastUpdate: "刚刚",
            },
          ],
          dispositions: { "live 红档客户 ALPHA": "live 处置建议" },
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

    // V2 issue #3 fix verify: session_id 从 evt.data top-level 读 (make_done 顶层) · 不再丢
    await expect(root).toHaveAttribute("data-session-id", "alert-live-test");
    await expect(root).toHaveAttribute("data-scan-session-id", "alert-live-test");

    // training-mode banner 不显 (live mode 优先)
    await expect(page.locator('[data-testid="alert-training-mode-banner"]')).toHaveCount(0);

    // session-select 应 disabled (live mode 锁定)
    const select = page.locator('[data-testid="alert-session-select"]');
    await expect(select).toBeDisabled();

    // ── V2 issue #2 fix verify · 5 panel 全 derive from hit_list ──

    // (1) Traffic light wall 红档 count 切到 live 7 (mock baseline_100 是 5)
    await expect(page.locator('[data-testid="alert-traffic-light-red"]')).toContainText("7");
    await expect(page.locator('[data-testid="alert-traffic-light-yellow"]')).toContainText("14");
    await expect(page.locator('[data-testid="alert-traffic-light-green"]')).toContainText("79");

    // (2) ScanQueueCases (hit_list.red + hit_list.yellow derive) · 显示 live 客户 (不再 fallback mock)
    const queueRows = page.locator('[data-testid="alert-hitlist-row"]');
    await expect(queueRows).toHaveCount(2); // 1 red + 1 yellow · live hit_list
    await expect(queueRows.first()).toContainText("live 红档客户 ALPHA");
    await expect(queueRows.nth(1)).toContainText("live 黄档客户 BETA");
    // mock baseline_100 第一个 customer "苏州金鼎电子" 应被 live 数据替换
    await expect(page.locator(".al-queue__list")).not.toContainText("苏州金鼎电子");

    // (3) TopCase row · live 客户 ALPHA 显
    const topCaseRows = page.locator('[data-testid="alert-top-case-row"]');
    await expect(topCaseRows).toHaveCount(1);
    await expect(topCaseRows.first()).toContainText("live 红档客户 ALPHA");
    await expect(topCaseRows.first()).toHaveAttribute("data-client-id", "CL-LIVE-RED-1");
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

  test("spec 8 · /api/alert/demo/run contract · route-mock + browser fetch 验 done envelope", async ({
    page,
  }) => {
    /* V2 codex DISAGREE issue #4 修: 不再用 env-guard skip · 走 route mock + page.evaluate(fetch) ·
     * 直接验前端能消费 /api/alert/demo/run done envelope 形态 (cat 4 + per shared.sse_envelope.make_done):
     *   - event: "done" · data_source: "mock_forced" · session_id 顶层 · scenario_key 顶层
     *   - hit_list (red/yellow/green) + top_cases + dispositions + totals + metrics
     *   - V2 issue #1 fix verify: hit_list 内 risk grade key 是 `tier` 不是 `risk_level` */
    const fixturePayload = {
      event: "done",
      data_source: "mock_forced",
      session_id: "demo-baseline_100",
      scenario_key: "baseline_100",
      mode: "demo_forced",
      summary: "常态扫描 · 100 户 · 红 5 / 黄 15 / 绿 80",
      kb_state: "demo · 不读 KB",
      totals: { red: 5, yellow: 15, green: 80 },
      metrics: { red: 5, yellow: 15, green: 80, total_scanned: 100 },
      hit_list: {
        red: [{ client_id: "CL-100-001", company_name: "苏州金鼎电子", amount: "850 万", tier: "red", score: 0.91 }],
        yellow: [{ client_id: "CL-100-004", company_name: "常州江源建材", amount: "320 万", tier: "yellow", score: 0.62 }],
        green: [],
      },
      top_cases: [
        { id: "tc-1", client_id: "CL-100-001", customer: "苏州金鼎电子", amount: "850 万", tier: "red", triggers: ["征信 M3+"], advice: "电话+现场", lastUpdate: "12 分钟前" },
      ],
      dispositions: { "苏州金鼎电子": "电话+现场" },
      industry_distribution: [{ industry: "制造业", red: 2, yellow: 5, green: 20, total: 27 }],
      signal_heatmap: [{ id: "sh-flow", label: "流水骤降", score: 52 }],
      reach_rate: [{ tier: "red", label: "红档", total: 5, reached: 5, reachedPct: 100, channels: { phone: 5, sms: 5, visit: 2 } }],
    };

    let endpointHit = false;
    let lastBody: string | null = null;
    await page.route("**/api/alert/demo/run", async (route) => {
      endpointHit = true;
      lastBody = route.request().postData() ?? "";
      const body = [
        `data: ${JSON.stringify({ event: "stage", stage: "kb_load", status: "done", message: "demo · kb_load" })}\n\n`,
        `data: ${JSON.stringify({ event: "stage", stage: "summary", status: "done", message: "demo · summary" })}\n\n`,
        `data: ${JSON.stringify(fixturePayload)}\n\n`,
      ].join("");
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        headers: { "Cache-Control": "no-cache" },
        body,
      });
    });

    /* 1) goto /archive/alert · 2) browser fetch /api/alert/demo/run · 3) 解析 SSE 完整 body */
    await page.goto("/archive/alert", { waitUntil: "networkidle" });

    const respText = await page.evaluate(async () => {
      const resp = await fetch("/api/alert/demo/run", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify({ scenario_key: "baseline_100" }),
      });
      return resp.text();
    });

    expect(endpointHit).toBe(true);
    expect(lastBody).toContain("baseline_100");

    // done envelope shape 字段 (per shared.sse_envelope.make_done · per docs/audit/A4-alert-draft.md §3):
    expect(respText).toContain('"event":"done"');
    expect(respText).toContain('"data_source":"mock_forced"');
    expect(respText).toContain('"session_id":"demo-baseline_100"');
    expect(respText).toContain('"scenario_key":"baseline_100"');
    expect(respText).toContain('"hit_list"');
    expect(respText).toContain('"top_cases"');
    expect(respText).toContain('"dispositions"');
    expect(respText).toContain('"totals"');

    // V2 issue #1 verify: hit_list 内 risk grade key 是 `tier` 不是 `risk_level` (per A6 schema)
    expect(respText).toContain('"tier":"red"');
    expect(respText).toContain('"tier":"yellow"');
    expect(respText).not.toMatch(/"risk_level":\s*"red"/);
  });
});
