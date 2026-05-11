/**
 * B.4 · SLO-2 主活 A · admin 真号 E2E · credit 实时路径
 *
 * Credit 实时路径 (per CreditWorkspace.tsx:329 runDecisionWithAgent6Handoff):
 *   1. credit-input-mode-real (默认 active)
 *   2. credit-decision-cta · 触发 Agent6 报告 handoff + SSE /api/credit/decision
 *
 * 验收 (SLO-2 弱 GREEN · 实时模式 UI 真 wire · 不被 demo mock 冒充):
 *   ✓ credit-input-mode-real toggle 真存在 + 可点
 *   ✓ click 后 inputMode 切到 real (CTA 文案 = "从 Agent6 报告起决策" · 非 demo "一键运行")
 *   ✓ credit-decision-cta 真存在 (非 credit-demo-cta)
 *   ✓ backend /api/credit/reports/sessions 真在线 (status 200 · 不 503)
 *   ✓ click decision-cta 后 60s 内必有 反应 (started=yes / error-banner / handoff-banner)
 *
 * 不可 GO:
 *   - input-mode-real 缺失 = mock 冒充实时
 *   - decision-cta 缺失 = realtime UI wire 缺
 *   - /api/credit/reports/sessions 503 = backend fallback fake
 *   - 点 CTA 60s 无反应 = silent swallow
 */
import { adminTest as test, expect, E2E_TIMEOUT_MS, FIRST_PAINT_TIMEOUT_MS, REAL_PROD_BASE_URL } from "./_shared";

test.describe("B.4 SLO-2 主活 A · admin 真号 · credit realtime UI wire", () => {
  test("real mode UI 真 wire · decision-cta 真存在 · backend 真在线 · 不 mock 冒充", async ({
    page,
  }) => {
    test.setTimeout(E2E_TIMEOUT_MS);

    await page.goto("/archive/credit", { waitUntil: "networkidle" });

    await expect(
      page.locator('[data-testid="credit-empty-skeleton"]'),
    ).toBeVisible({ timeout: FIRST_PAINT_TIMEOUT_MS });

    // 1. realtime toggle 真存在 · 真可点 · 不被 demo 替代
    const realToggle = page.locator('[data-testid="credit-input-mode-real"]');
    await expect(realToggle, "real mode toggle 缺 · UI 已被 demo 冒充").toBeVisible();
    await realToggle.click();
    await expect(realToggle, "click 后 real mode 没 active").toHaveAttribute("data-active", "yes");

    // 2. real mode 下 CTA = credit-decision-cta (不是 credit-demo-cta)
    const decisionCta = page.locator('[data-testid="credit-decision-cta"]');
    await expect(decisionCta, "real mode CTA 缺 · realtime 路径未 wire").toBeVisible();
    const demoCta = page.locator('[data-testid="credit-demo-cta"]');
    expect(
      await demoCta.count(),
      "real mode 下 demo-cta 仍 visible · UI 模式切换 bug",
    ).toBe(0);

    // 3. backend health · /api/credit/reports/sessions 真返 200 (不 503 fallback fake)
    const sessionsRes = await page.request.get(
      `${REAL_PROD_BASE_URL}/api/credit/reports/sessions?status=done`,
    );
    expect(sessionsRes.status(), "Agent6 sessions endpoint 非 200 · backend 真挂").toBe(200);
    const sessionsJson = await sessionsRes.json();
    expect(typeof sessionsJson.count, "sessions response shape 错").toBe("number");

    // 4. click decision-cta · 60s 内必有反应 (started / error / handoff banner)
    await decisionCta.click();
    const reaction = page.locator(
      '[data-credit-started="yes"], [data-testid="credit-error-banner"], [data-testid="credit-handoff-banner"]',
    );
    await expect(
      reaction.first(),
      "click decision-cta 60s 无反应 · backend silent swallow",
    ).toBeVisible({ timeout: 60_000 });

    // 5. 任何反应都不允许是 "503 / Internal Server Error / mock fake" 字样
    const body = await page.locator("body").innerText();
    expect(body, "页面含 503").not.toMatch(/\b503\b/);
    expect(body, "页面含 Internal Server Error").not.toMatch(/Internal Server Error/i);
    expect(body, "页面含 [object Object]").not.toMatch(/\[object Object\]/);
  });
});
