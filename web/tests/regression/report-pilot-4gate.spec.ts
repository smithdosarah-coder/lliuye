import { test, expect } from "@playwright/test";

/**
 * Phase A worker-A4 · report pilot · 4 gate state model + 5 panel testid + demo/run + export wire
 *
 * 验:
 *   T1 · gate 1 (started=false → empty skeleton 显)
 *   T2 · gate 1+2 (started + historyChoice) · 选 history → 5 panel 同步亮 (mock 模式)
 *   T3 · gate 3 (liveData) · /api/report/demo/run mock SSE done → 5 panel hydrate + preview data-mode=live
 *   T4 · gate 4 (selectedSection) · TOC click → preview data-selected-section 设 + ESC 清
 *   T5 · 5 panel testid 全在 (materials / timeline / preview / fieldchip / toolbar)
 *   T6 · export Word + PDF toolbar 按钮真接 endpoint
 *
 * Auth bypass: mock /api/auth/me · 同 channel-pilot-4gate.spec.ts pattern
 * Health bypass: mock /api/report/health (默认 llm_connected=false · 不卡)
 */
const MOCK_ME_RESPONSE = {
  user: {
    id: "u_wangzhe",
    name: "王哲",
    role: "rm",
    team: "华东·上海第一支行",
    avatar: "哲",
  },
  roles: ["rm"],
  accessibleAgents: ["channel", "report", "credit", "alert", "compli", "riskctrl"],
};

test.beforeEach(async ({ context }) => {
  await context.route("**/api/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_ME_RESPONSE),
    });
  });
  await context.route("**/api/report/health", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "ok", llm_connected: true, version: "0.1.0" }),
    });
  });
});

test.describe("worker-A4 · report pilot · 4 gate", () => {
  test("T1 · gate 1 default · empty skeleton 显 · 5 panel 隐", async ({ page }) => {
    await page.goto("/archive/report", { waitUntil: "networkidle" });

    // 默认 started=false · empty skeleton 必显
    await expect(
      page.locator('[data-testid="report-empty-skeleton"]'),
    ).toBeVisible();

    // 5 panel 全隐 (started 守门)
    for (const k of ["materials", "timeline", "preview", "toolbar"]) {
      await expect(
        page.locator(`[data-testid="report-pilot-${k}"]`),
      ).toHaveCount(0);
    }
  });

  test("T2 · gate 1+2 · 选 history → 开始生成 → 5 panel 同步亮 (mock 模式)", async ({
    page,
    context,
  }) => {
    /* 拦 v16/fill 注入 mock done envelope · 让 mock-history 路径 hydrate 后 panel 全亮 */
    await context.route("**/api/report/v16/fill", async (route) => {
      const sse = [
        `event: stage\ndata: ${JSON.stringify({ event: "stage", stage: "ingest", progress: 0.2, message: "材料解析" })}\n\n`,
        `event: done\ndata: ${JSON.stringify({
          event: "done",
          data_source: "mock",
          pipeline: "v16",
          mock_pipeline: true,
          session_id: "mock-history-1",
          report_id: "mock-history-1",
          sections: [],
          qc: { passed: true, score: 80, fatal_fail: false, halluc_count: 0 },
          stats: {},
          pending_questions: [],
        })}\n\n`,
      ].join("");
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: sse,
      });
    });

    await page.goto("/archive/report", { waitUntil: "networkidle" });

    // 选 history dropdown 第 1 个非空选项
    const histDropdown = page.locator('[data-testid="report-history-dropdown"]');
    await expect(histDropdown).toBeVisible();
    const firstHist = await histDropdown.locator("option").nth(1).getAttribute("value");
    expect(firstHist).toBeTruthy();
    await histDropdown.selectOption(firstHist!);

    // apply launch
    await page.locator('[data-testid="report-apply-launch-btn"]').click();
    await page.waitForTimeout(500);

    // 5 panel 全亮 (gate 1 started=true · materials/timeline/preview 显 · toolbar 在 preview 内)
    for (const k of ["materials", "timeline", "preview", "toolbar"]) {
      await expect(
        page.locator(`[data-testid="report-pilot-${k}"]`),
      ).toBeVisible();
    }

    // FieldChip 至少一个 (REPORT_SESSION mock 必有 field) · 其中一个 testid
    await expect(
      page.locator('[data-testid="report-pilot-fieldchip"]').first(),
    ).toBeVisible();
  });

  test("T3 · gate 3 liveData · /api/report/demo/run · 5 panel + preview data-mode=live", async ({
    page,
    context,
  }) => {
    let demoEndpointHit = false;
    let demoScenario: string | null = null;
    await context.route("**/api/report/demo/run", async (route) => {
      demoEndpointHit = true;
      try {
        const body = route.request().postDataJSON() as { scenario_id?: string };
        demoScenario = body?.scenario_id ?? null;
      } catch {
        demoScenario = null;
      }
      const sse = [
        `event: stage\ndata: ${JSON.stringify({ event: "stage", stage: "ingest", progress: 0.2, message: "解析" })}\n\n`,
        `event: stage\ndata: ${JSON.stringify({ event: "stage", stage: "audit", progress: 1.0, message: "审" })}\n\n`,
        `event: done\ndata: ${JSON.stringify({
          event: "done",
          data_source: "mock_forced",
          pipeline: "v16",
          mock_pipeline: true,
          session_id: "demo_report_medium_test",
          report_id: "demo_report_medium_test",
          sections: [
            {
              id: "chapter_1_background",
              title: "一、企业背景",
              content: "Demo 背景内容 · A4-test-sentinel",
              status: "done",
              word_count: 100,
            },
          ],
          profile: { company_name: "Demo 测试公司" },
          stats: { total_fields: 100, auto_filled: 90 },
          qc: { passed: true, score: 85, fatal_fail: false, halluc_count: 0 },
          pending_questions: [],
        })}\n\n`,
      ].join("");
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: sse,
      });
    });

    await page.goto("/archive/report", { waitUntil: "networkidle" });

    // demo strip 3 档全显
    await expect(page.locator('[data-testid="report-demo-easy"]')).toBeVisible();
    await expect(page.locator('[data-testid="report-demo-medium"]')).toBeVisible();
    await expect(page.locator('[data-testid="report-demo-hard"]')).toBeVisible();

    // 点 medium · 验 endpoint hit + scenario_id payload 正确
    await page.locator('[data-testid="report-demo-medium"]').click();
    await page.waitForTimeout(800);

    expect(demoEndpointHit).toBe(true);
    expect(demoScenario).toBe("medium");

    // 5 panel 全亮 + preview data-mode=live (liveData hydrated · gate 3)
    for (const k of ["materials", "timeline", "preview", "toolbar"]) {
      await expect(
        page.locator(`[data-testid="report-pilot-${k}"]`),
      ).toBeVisible();
    }
    await expect(
      page.locator('[data-testid="report-pilot-preview"]'),
    ).toHaveAttribute("data-mode", "live");

    // ReportLiveStrip 显示 stage chip + qc passed (live data hydrate 成功)
    await expect(
      page.locator('[data-testid="report-live-strip"]'),
    ).toBeVisible();
  });

  test("T4 · gate 4 selectedSection · TOC click 设 data-selected-section · ESC 清", async ({
    page,
    context,
  }) => {
    /* 走 demo run 让 started=true · 然后点第一个 section TOC button */
    await context.route("**/api/report/demo/run", async (route) => {
      const sse = [
        `event: done\ndata: ${JSON.stringify({
          event: "done",
          data_source: "mock_forced",
          pipeline: "v16",
          mock_pipeline: true,
          session_id: "demo_test_4",
          report_id: "demo_test_4",
          sections: [],
          profile: {},
          stats: {},
          qc: { passed: true, score: 80, fatal_fail: false, halluc_count: 0 },
          pending_questions: [],
        })}\n\n`,
      ].join("");
      await route.fulfill({ status: 200, contentType: "text/event-stream", body: sse });
    });

    await page.goto("/archive/report", { waitUntil: "networkidle" });
    await page.locator('[data-testid="report-demo-easy"]').click();
    await page.waitForTimeout(500);

    // 点第 1 个 TOC button (REPORT_SESSION.preview 第 1 个 section)
    const firstToc = page.locator('[data-testid^="report-section-toc-"]').first();
    await expect(firstToc).toBeVisible();
    const sectionId = (await firstToc.getAttribute("data-testid"))?.replace(
      "report-section-toc-",
      "",
    );
    await firstToc.click();
    await page.waitForTimeout(200);

    const preview = page.locator('[data-testid="report-pilot-preview"]');
    await expect(preview).toHaveAttribute("data-selected-section", sectionId!);

    // ESC 清 (gate 4 ESC handler · 4-gate parity with channel selectedCandidate)
    await page.keyboard.press("Escape");
    await page.waitForTimeout(200);
    await expect(preview).toHaveAttribute("data-selected-section", "");
  });

  test("T6 · V2 issue 1 fix · 5 panel content switch · easy vs hard demo 切场景 preview 内容必变", async ({
    page,
    context,
  }) => {
    /* V2 codex DISAGREE issue 1 fix verify · 5 panel sessionData = liveData ?? mock 单点派生
       验: easy 跑完 preview 显 "杭州方舟" · hard 跑完 preview 显 "华南普华" · 内容 hash 必不同
       (之前静态 REPORT_SESSION 占主源 · demo 切场景视觉无变化 · 这是 codex 卡的根因) */
    let currentScenario: string | null = null;
    await context.route("**/api/report/demo/run", async (route) => {
      const body = route.request().postDataJSON() as { scenario_id: string };
      currentScenario = body.scenario_id;
      const sentinel =
        body.scenario_id === "easy"
          ? "杭州方舟智装-EASY-SENTINEL"
          : body.scenario_id === "hard"
            ? "华南普华纺织-HARD-SENTINEL"
            : "演示中等场景-MEDIUM-SENTINEL";
      const sse = [
        `event: stage\ndata: ${JSON.stringify({ event: "stage", stage: "ingest", progress: 0.2 })}\n\n`,
        `event: done\ndata: ${JSON.stringify({
          event: "done",
          data_source: "mock_forced",
          pipeline: "v16",
          mock_pipeline: true,
          session_id: `00000000-0000-4000-8000-${body.scenario_id.padStart(12, "0")}`,
          report_id: `00000000-0000-4000-8000-${body.scenario_id.padStart(12, "0")}`,
          sections: [
            {
              id: "chapter_1_background",
              title: "一、企业背景",
              content: sentinel,
              status: "done",
              word_count: 100,
            },
          ],
          profile: {
            company_name:
              body.scenario_id === "easy"
                ? "杭州方舟智能装备"
                : body.scenario_id === "hard"
                  ? "华南普华纺织"
                  : "厦门海风餐饮",
          },
          stats: { total_fields: 100, auto_filled: 90 },
          qc: { passed: body.scenario_id !== "hard", score: 80, fatal_fail: body.scenario_id === "hard", halluc_count: 0 },
          pending_questions: [],
        })}\n\n`,
      ].join("");
      await route.fulfill({ status: 200, contentType: "text/event-stream", body: sse });
    });

    /* edge 在 SSE-heavy 场景下 networkidle 不稳 (ERR_ABORTED) · 用 domcontentloaded */
    await page.goto("/archive/report", { waitUntil: "domcontentloaded" });

    // 跑 easy · preview 应显 SENTINEL_EASY
    await page.locator('[data-testid="report-demo-easy"]').click();
    await page.waitForTimeout(600);
    const preview = page.locator('[data-testid="report-pilot-preview"]');
    await expect(preview).toBeVisible();
    await expect(preview).toContainText("杭州方舟智装-EASY-SENTINEL");
    expect(currentScenario).toBe("easy");

    // 切 hard · preview 内容应换 (V2 codex callout · 5 panel hydrate 真生效)
    await page.locator('[data-testid="report-demo-hard"]').click();
    await page.waitForTimeout(600);
    await expect(preview).toContainText("华南普华纺织-HARD-SENTINEL");
    // easy 内容应消失 (sessionData 切走)
    await expect(preview).not.toContainText("杭州方舟智装-EASY-SENTINEL");
    expect(currentScenario).toBe("hard");
  });

  test("T5 · toolbar Word + PDF 按钮真接 endpoint", async ({ page, context }) => {
    let docxHit = false;
    let pdfHit = false;
    await context.route("**/api/report/export_docx", async (route) => {
      docxHit = true;
      await route.fulfill({
        status: 200,
        contentType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers: {
          "content-disposition": 'attachment; filename="test.docx"',
        },
        body: Buffer.from("PK"),  // minimal docx zip header (fake but blob OK)
      });
    });
    await context.route("**/api/report/export_pdf", async (route) => {
      pdfHit = true;
      await route.fulfill({
        status: 200,
        contentType: "application/pdf",
        headers: {
          "content-disposition": 'attachment; filename="test.pdf"',
        },
        body: Buffer.from("%PDF-1.4"),
      });
    });
    await context.route("**/api/report/demo/run", async (route) => {
      const sse = [
        `event: done\ndata: ${JSON.stringify({
          event: "done",
          data_source: "mock_forced",
          pipeline: "v16",
          mock_pipeline: true,
          session_id: "toolbar_test",
          report_id: "toolbar_test",
          sections: [{ id: "x", title: "X", content: "x", status: "done", word_count: 1 }],
          profile: {},
          stats: {},
          qc: { passed: true, score: 80, fatal_fail: false, halluc_count: 0 },
          pending_questions: [],
        })}\n\n`,
      ].join("");
      await route.fulfill({ status: 200, contentType: "text/event-stream", body: sse });
    });

    /* edge 在 SSE-heavy 场景下 networkidle 不稳 (ERR_ABORTED) · 用 domcontentloaded */
    await page.goto("/archive/report", { waitUntil: "domcontentloaded" });
    await page.locator('[data-testid="report-demo-easy"]').click();
    await page.waitForTimeout(500);

    // Word
    await page.locator('[data-testid="report-toolbar-word"]').click();
    await page.waitForTimeout(400);
    expect(docxHit).toBe(true);

    // PDF (G-10 闭环)
    await page.locator('[data-testid="report-toolbar-pdf"]').click();
    await page.waitForTimeout(400);
    expect(pdfHit).toBe(true);

    // 分享 / 版本 buttons disabled (Phase B placeholder · G-10 后两个仍 Phase B)
    await expect(
      page.locator('[data-testid="report-toolbar-share"]'),
    ).toBeDisabled();
    await expect(
      page.locator('[data-testid="report-toolbar-version"]'),
    ).toBeDisabled();
  });
});
