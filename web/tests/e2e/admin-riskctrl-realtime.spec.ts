/**
 * B.4 · SLO-2 主活 A · admin 真号 E2E · riskctrl 实时路径
 *
 * Riskctrl 实时路径 (per RiskctrlWorkspace.tsx:683):
 *   - riskctrl-mode-toggle-real · 用户输入策略 + CSV → /api/riskctrl/run (真 LLM DSL 生成 + 真回测)
 *   - riskctrl-dsl-gen-cta · 触发 onPrimaryDslGen
 *
 * demo 路径 (admin-riskctrl.spec.ts):
 *   - riskctrl-mode-toggle-demo · riskctrl-demo-seed-select · riskctrl-demo-run-cta
 *
 * 验收 (SLO-2 强 GREEN · realtime UI wire + 渲染态无业务 fail):
 *   ✓ riskctrl-mode-toggle-real 真存在 + 可点 + active
 *   ✓ riskctrl-dsl-gen-cta 真存在 (real mode 下)
 *   ✓ backend /api/riskctrl/dsl_gen 可 ping (200/400/422 业务 status · 非 503)
 *   ✓ riskctrl-error-banner count = 0 (页面初渲染无业务 fail)
 *   ✓ riskctrl-live-fail-banner count = 0 (页面初渲染无 backend fallback)
 *   ✓ body 无 MOCK / mock fake / fallback 字样
 *
 * 不可 GO:
 *   - real toggle 缺 = mock 冒充实时
 *   - real mode 下仍显 demo CTA = UI 模式切换 bug
 *   - error / live-fail banner visible = backend 业务 fail
 *   - body 含 MOCK / fallback = silent 降级
 *
 * NOTE: codex R2 R2.1 #3 strict assertion ·
 * 旧弱标准 仅 check UI wire + backend ping · 不 verify 渲染态无 banner.
 * 真号 click+wait done 需 策略 prompt + CSV 上传 · spec 无法 synthesize ·
 * 强 done assertion 不可行 · 用 0-banner 当 "渲染态业务无 fail" 代理.
 */
import { adminTest as test, expect, E2E_TIMEOUT_MS, FIRST_PAINT_TIMEOUT_MS, REAL_PROD_BASE_URL } from "./_shared";

test.describe("B.4 SLO-2 主活 A · admin 真号 · riskctrl realtime UI wire", () => {
  test("real mode UI 真 wire · dsl-gen-cta 真存在 · backend 真在线", async ({ page }) => {
    test.setTimeout(E2E_TIMEOUT_MS);

    await page.goto("/archive/riskctrl", { waitUntil: "networkidle" });

    await expect(
      page.locator('[data-testid="riskctrl-workspace"]'),
    ).toBeVisible({ timeout: FIRST_PAINT_TIMEOUT_MS });

    // 1. real mode toggle 真存在 (默认 active per RiskctrlWorkspace.tsx:190 mode="real")
    const realToggle = page.locator('[data-testid="riskctrl-mode-toggle-real"]');
    await expect(realToggle, "real toggle 缺 · UI 已被 demo 冒充").toBeVisible();
    await realToggle.click();
    await expect(realToggle, "click 后 real mode 没 active").toHaveAttribute("data-active", "yes");

    // 2. real mode 下 dsl-gen-cta 真存在 (demo 用 demo-run-cta)
    const dslGenCta = page.locator('[data-testid="riskctrl-dsl-gen-cta"]');
    await expect(dslGenCta, "dsl-gen CTA 缺 · realtime 路径未 wire").toBeVisible();
    const demoRunCta = page.locator('[data-testid="riskctrl-demo-run-cta"]');
    expect(
      await demoRunCta.count(),
      "real mode 下 demo-run-cta 仍 visible · UI 模式切换 bug",
    ).toBe(0);

    // 3. backend health · /api/riskctrl/dsl_gen POST 空 body 返 400/422 OK (非 503)
    //    (真路径 per agent_riskctrl/api.py:154 · 没有 /api/riskctrl/run 顶级 endpoint)
    const runPing = await page.request.post(
      `${REAL_PROD_BASE_URL}/api/riskctrl/dsl_gen`,
      {
        data: {},
        failOnStatusCode: false,
      },
    );
    const status = runPing.status();
    expect(
      [200, 400, 422].includes(status),
      `riskctrl dsl_gen endpoint 非业务 status: ${status} · backend silent fail / 503`,
    ).toBe(true);

    // 4. codex R2 R2.1 #3 strict · 渲染态无业务 fail banner (旧弱标准容忍 · 新强标准阻 spec)
    expect(
      await page.locator('[data-testid="riskctrl-error-banner"]').count(),
      "riskctrl-error-banner visible · 后端业务 fail · 阻 spec",
    ).toBe(0);
    expect(
      await page.locator('[data-testid="riskctrl-live-fail-banner"]').count(),
      "riskctrl-live-fail-banner visible · backend live 路径 fallback fake · 阻 spec",
    ).toBe(0);

    // 5. sanity
    const body = await page.locator("body").innerText();
    expect(body, "页面含 503").not.toMatch(/\b503\b/);
    expect(body, "页面含 Internal Server Error").not.toMatch(/Internal Server Error/i);
    expect(body, "页面含 [object Object]").not.toMatch(/\[object Object\]/);

    // 6. codex R2 R2.1 #3 strict · body 无 MOCK / fallback 字样 (silent 降级阻 spec)
    expect(
      body,
      "页面含 MOCK / mock fake / fallback · backend silent 降级 (Q-055 §4)",
    ).not.toMatch(/\bMOCK\b|mock fake|fallback/i);
  });
});
