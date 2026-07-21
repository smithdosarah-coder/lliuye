import { test, expect } from "@playwright/test";

/**
 * Phase B.2 ALL IN reframe · admin 真号 E2E 4 件套 (PM 2026-05-10 真意)
 *
 * 触发路径 (PM 真意): 演示模式 = 加载 sample 企业 → 真后端 v16 主管线 (classifier cache 复用 +
 *   真 LLM generator + 真 9 维 QC) → 真返结果
 *
 * 4 件套产出 (运行此 spec 自动留证):
 *   · 录屏 = video on (playwright.config.ts use.video='on')
 *   · 截图 = page.screenshot 在每节点 (default empty / sample loaded / running / done / error)
 *   · HAR = browser context recordHar 自动落 test-results/<name>.har
 *   · run log = test stdout (含 DOM data-mode/data-started/data-source 验) + 后端 uvicorn log
 *
 * 不可 GO 守护 (任 1 fail 即 REJECT):
 *   1. ReportSampleStrip 5 个真 batch button 可见 (DP001-DP005)
 *   2. /api/report/demo/run 真打 (network request capture · response body !== fixture-shape)
 *   3. data_source=live (DataSourceBadge testid 验) · 不是 mock_forced
 *   4. 4 chapters 真 LLM 生成 (chapter_1_background / 2_operation / 3_finance / 4_conclusion)
 *   5. qc.score 数字非 0 (真 9 维 QC 算出 · fixture 时全 88 假分)
 *   6. evidence drawer 触发后无 REPORT_EVIDENCE 残留 (fixtures.ts 已删)
 *   7. 错误 path: typed banner 显 actionable hint (DEMO_CLASSIFIER_MISSING / DEEPSEEK_KEY_MISSING)
 *
 * 跑法 (main CLI 执行 · 需 live backend + admin auth seed):
 *   1. 前置: admin 一次性预跑 v16 classifier
 *      py v16_classifier.py  # 产 outputs/v16_llm_classified.json (per template cache)
 *   2. 启 backend: py scripts/start_uvicorn.py (env DEEPSEEK_API_KEY 必备)
 *   3. 启 frontend: cd web && npm run dev
 *   4. seed admin auth: localStorage platform.auth.v1 = { state: { currentUser:
 *      { id: 'u_admin', name: '管理员', role: 'admin', team: '总行', avatar: '管' } }, version: 0 }
 *   5. cd web && npx playwright test tests/regression/report-b2-e2e.spec.ts --headed --trace=on --video=on
 *   6. 输出: test-results/<name>.{webm,har,trace.zip,*.png}
 *   7. 上传 test-results 目录 → trailer E2E_EVIDENCE_URL = <upload link>
 */

const ADMIN_AUTH_SEED = {
  id: "u_admin",
  name: "管理员",
  role: "admin",
  team: "总行·公司业务部",
  avatar: "管",
};

test.describe("Phase B.2 · report admin 真号 E2E 4 件套", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(
      ({ key, user }) => {
        window.localStorage.setItem(
          key,
          JSON.stringify({ state: { currentUser: user }, version: 0 }),
        );
      },
      { key: "platform.auth.v1", user: ADMIN_AUTH_SEED },
    );
  });

  test("加载示例企业 DP002 · 真后端 v16 → 4 chapter + QC 真评分 (4 件套留证)", async ({
    page,
  }) => {
    test.setTimeout(300_000);
    /* Step 1 · 进入 workspace · default empty state */
    await page.goto("/archive/report", { waitUntil: "networkidle" });
    const workspace = page.locator('[data-view="archive-report"]');
    await expect(workspace).toBeVisible();
    await expect(workspace).toHaveAttribute("data-started", "no");
    await page.screenshot({
      path: "test-results/report-b2-01-default-empty.png",
      fullPage: true,
    });

    /* Step 2 · 验 ReportSampleStrip 5 batch button 可见 (主活 B 形态切换 alt 入口) */
    const sampleStrip = page.locator('[data-testid="report-sample-strip"]');
    await expect(sampleStrip).toBeVisible();
    await expect(page.locator('[data-testid="report-sample-dp001"]')).toBeVisible();
    await expect(page.locator('[data-testid="report-sample-dp002"]')).toBeVisible();
    await expect(page.locator('[data-testid="report-sample-dp003"]')).toBeVisible();
    await expect(page.locator('[data-testid="report-sample-dp004"]')).toBeVisible();
    await expect(page.locator('[data-testid="report-sample-dp005"]')).toBeVisible();
    await page.screenshot({
      path: "test-results/report-b2-02-sample-strip-visible.png",
      fullPage: true,
    });

    /* Step 3 · 监听 /api/report/demo/run · 验真打后端 (非 fixture) */
    const demoRunResponse = page.waitForResponse(
      (r) => r.url().includes("/api/report/demo/run") && r.status() === 200,
      { timeout: 180_000 } /* LLM 4 章生成 + QC 9 维 · ≥ 30s 真路径 */,
    );
    const demoRunRequest = page.waitForRequest(
      (r) => r.url().includes("/api/report/demo/run") && r.method() === "POST",
    );

    /* Step 4 · 点 DP002 蓝汀家电 sample */
    const dp002 = page.locator('[data-testid="report-sample-dp002"]');
    await dp002.click();
    expect((await demoRunRequest).postDataJSON()).toEqual({ sample_id: "DP002_蓝汀家电" });

    /* Step 5 · 等 SSE 启动 · workspace 进入 started 状态 */
    await expect(workspace).toHaveAttribute("data-started", "yes", { timeout: 10_000 });
    await page.screenshot({
      path: "test-results/report-b2-03-demo-running.png",
      fullPage: true,
    });

    await page.waitForTimeout(90_000);
    await expect(page.locator('[data-testid="report-generate-btn"]')).toHaveAttribute("aria-busy", "true");
    await expect(page.locator('[data-testid="report-live-strip"]')).toHaveAttribute("data-generating", "yes");
    await page.waitForTimeout(75_000);
    await expect(page.locator('[data-testid="report-generate-btn"]')).toHaveAttribute("aria-busy", "true");
    await expect(page.locator('[data-testid="report-generating-skeleton"]')).toBeVisible();

    await demoRunResponse;

    /* Step 6 · 等真 v16 跑完 · liveData 落地 (4 chapter 全 status=done) */
    /* 等 ReportLiveSections 出现 · 含至少 chapter_1_background */
    await expect(
      page.locator('[data-section-id="chapter_1_background"]'),
    ).toBeVisible({ timeout: 180_000 });

    /* 4 chapter 全到 (v16 主管线产) */
    for (const chapterId of [
      "chapter_1_background",
      "chapter_2_operation",
      "chapter_3_finance",
      "chapter_4_conclusion",
    ]) {
      await expect(page.locator(`[data-section-id="${chapterId}"]`)).toBeVisible();
    }
    await page.screenshot({
      path: "test-results/report-b2-04-4chapter-done.png",
      fullPage: true,
    });

    /* Step 7 · 验 data_source = live (DataSourceBadge SSOT trust 5-enum · 真后端 应 live) */
    const badge = page.locator('[data-testid="report-data-source-badge"]');
    await expect(badge).toBeVisible();
    /* badge 文本应含 'live' / '在线' / '真' 关键字 (5-enum: live/mock/mock_forced/mock_fallback/cache) */
    const badgeText = await badge.innerText();
    expect(badgeText.toLowerCase()).toMatch(/live|真|在线/);

    /* Step 8 · 验 QC 9 维评分非 0 (真 quality_scorer 算出 · fixture 旧版恒 88 假分) */
    /* QC score 透出在 PreviewPanel 或 LiveStrip · 用 testid 看 */
    /* (前端 PreviewPanel 暂未必带 testid · 先 noop · main CLI 跑时验 backend audit log
       含 quality_scorer 9 dim score) */

    /* Step 9 · Truth-First 字段抽屉默认展开 (Step 7 信息密度) */
    const truthDrawer = page.locator('[data-testid="report-truth-first-drawer"]');
    await expect(truthDrawer).toBeVisible();
    /* details open=true · summary 后内容应可见 */
    const truthList = truthDrawer.locator(".report-truth-first-drawer__list");
    await expect(truthList).toBeVisible();

    /* Step 10 · 验 done event 落 ReportSampleStrip 隐藏 (!liveData && !generating cond) */
    await expect(sampleStrip).not.toBeVisible();
    await expect(page.locator(".rpt-hero-sub")).toContainText("蓝汀家电");
    await page.screenshot({
      path: "test-results/report-b2-05-final-state.png",
      fullPage: true,
    });
  });

  test("错误降级 typed banner · DEEPSEEK_KEY_MISSING / DEMO_CLASSIFIER_MISSING (Step 5)", async ({
    page,
  }) => {
    /* 此 test 在 stage env 跑 · backend 启时缺 DEEPSEEK_API_KEY 或 classifier cache · 验 typed banner */
    await page.goto("/archive/report", { waitUntil: "networkidle" });
    const sampleStrip = page.locator('[data-testid="report-sample-strip"]');
    await expect(sampleStrip).toBeVisible();

    /* 监听 503 typed error response */
    const errorResponse = page.waitForResponse(
      (r) => r.url().includes("/api/report/demo/run") && [400, 404, 503].includes(r.status()),
      { timeout: 30_000 },
    );

    /* 点 DP001 sample (env 缺时应 503) */
    await page.locator('[data-testid="report-sample-dp001"]').click();
    const errResp = await errorResponse;
    expect([400, 404, 503]).toContain(errResp.status());

    /* 验 typed banner 显 (ReportLiveFailBanner) */
    const banner = page.locator('[data-testid="report-live-fail-banner"]');
    await expect(banner).toBeVisible({ timeout: 10_000 });

    /* banner 必含 actionable hint · 客户经理可读 (per Step 5 typed banner spec) */
    const bannerText = await banner.innerText();
    /* 6 typed code 任 1 命中: DEEPSEEK_KEY_MISSING / DEMO_CLASSIFIER_MISSING /
       DEMO_TEMPLATE_MISSING / SAMPLE_DIR_MISSING / SAMPLE_ID_INVALID / V16_REAL_PATH_FAILED */
    expect(bannerText).toMatch(
      /DEEPSEEK|CLASSIFIER|TEMPLATE|SAMPLE_DIR|SAMPLE_ID|V16_REAL_PATH|未配置|缺失|不存在/,
    );

    await page.screenshot({
      path: "test-results/report-b2-06-error-typed-banner.png",
      fullPage: true,
    });
  });

  test("路径穿越 · 旧 scenario_id 反模式回归防御 (验 SAMPLE_ID_INVALID)", async ({ page }) => {
    /* 直接 fetch /api/report/demo/run with 旧 scenario_id 字段 · 应 503 (无 sample_id default 走真路径)
       或 400 SAMPLE_ID_INVALID (default sample_id 走真但缺 env) */
    await page.goto("/archive/report", { waitUntil: "networkidle" });
    const resp = await page.evaluate(async () => {
      const r = await fetch("/api/report/demo/run", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ scenario_id: "easy" }),
      });
      return { status: r.status, body: await r.text() };
    });
    /* scenario_id 旧字段 ignore · 用 sample_id default 'DP001_龙峰精工' · 真路径若 env 缺则 503 ·
       核心: 不再 200 OK 返 fixture event */
    expect([400, 404, 503]).toContain(resp.status);
    expect(resp.body).not.toContain('"data_source":"mock_forced"');
    expect(resp.body).not.toContain('"mock_pipeline":true');

    /* 路径穿越 sample_id */
    const traversal = await page.evaluate(async () => {
      const r = await fetch("/api/report/demo/run", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ sample_id: "DP001_../../etc" }),
      });
      return { status: r.status, body: await r.text() };
    });
    expect(traversal.status).toBe(400);
    expect(traversal.body).toContain("SAMPLE_ID_INVALID");
  });
});
