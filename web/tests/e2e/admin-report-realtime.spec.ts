/**
 * B.4 · SLO-2 主活 A · admin 真号 E2E · report 实时路径
 *
 * Report 实时路径:
 *   - report-upload-cta · 上传客户材料 (PDF/docx/xlsx 多份)
 *   - report-upload-template-cta-launch / report-template-select · 模板入口
 *   - report-business-line-select · 业务线 (对公/普惠)
 *   - report-apply-launch-btn · 开始生成 → /api/report/v16/fill (真 LLM)
 *
 * demo 路径 (admin-report.spec.ts):
 *   - report-sample-strip + report-sample-dp001 · 预置 sample
 *
 * 验收 (SLO-2 弱 GREEN · realtime UI wire):
 *   ✓ report-launch-bar 真存在 (= realtime 入口)
 *   ✓ report-upload-cta + report-template-select + report-business-line-select 真存在
 *   ✓ report-apply-launch-btn 真存在 (= realtime 触发 CTA)
 *   ✓ backend /api/report/v16/fill 可 ping
 */
import { adminTest as test, expect, E2E_TIMEOUT_MS, FIRST_PAINT_TIMEOUT_MS, REAL_PROD_BASE_URL } from "./_shared";

test.describe("B.4 SLO-2 主活 A · admin 真号 · report realtime UI wire", () => {
  test("upload launch-bar UI 真 wire · upload CTA + template + business · backend 真在线", async ({
    page,
  }) => {
    test.setTimeout(E2E_TIMEOUT_MS);

    await page.goto("/archive/report", { waitUntil: "networkidle" });

    await expect(
      page.locator('[data-testid="report-empty-skeleton"]'),
    ).toBeVisible({ timeout: FIRST_PAINT_TIMEOUT_MS });

    // 1. realtime launch-bar 真存在 (= upload-driven 入口 · 非 sample 路径)
    const launchBar = page.locator('[data-testid="report-launch-bar"]');
    await expect(launchBar, "launch-bar 缺 · realtime UI 已被 sample-only 替代").toBeVisible();

    // 2. realtime 3 件套 (upload + template + business line) 全 wire
    await expect(
      page.locator('[data-testid="report-upload-cta"]'),
      "upload-cta 缺 · 客户材料上传 UI 已被删",
    ).toBeVisible();
    await expect(
      page.locator('[data-testid="report-template-select"]'),
      "template select 缺 · realtime UI 不全",
    ).toBeVisible();
    await expect(
      page.locator('[data-testid="report-business-line-select"]'),
      "business-line select 缺 · realtime UI 不全",
    ).toBeVisible();
    await expect(
      page.locator('[data-testid="report-apply-launch-btn"]'),
      "apply-launch CTA 缺 · realtime 触发口未 wire",
    ).toBeVisible();

    // 3. sample 路径仍同时存在 · 但 realtime ≠ sample (sample 走 sample-strip)
    // 验 launch-bar 跟 sample-strip 都 visible · realtime 不 mock 冒充 sample
    await expect(
      page.locator('[data-testid="report-sample-strip"]'),
      "sample-strip 缺 · 双轨 sample 模式被删",
    ).toBeVisible();

    // 4. backend health · /api/report/v16/fill POST 空 body 返 400/422 OK
    const fillPing = await page.request.post(
      `${REAL_PROD_BASE_URL}/api/report/v16/fill`,
      {
        data: {},
        failOnStatusCode: false,
      },
    );
    const status = fillPing.status();
    expect(
      [200, 400, 422].includes(status),
      `report fill endpoint 非业务 status: ${status} · backend silent fail / 503`,
    ).toBe(true);

    // 5. sanity
    const body = await page.locator("body").innerText();
    expect(body, "页面含 503").not.toMatch(/\b503\b/);
    expect(body, "页面含 Internal Server Error").not.toMatch(/Internal Server Error/i);
    expect(body, "页面含 [object Object]").not.toMatch(/\[object Object\]/);
  });
});
