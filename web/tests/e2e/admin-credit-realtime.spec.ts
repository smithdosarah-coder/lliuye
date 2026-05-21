/**
 * B.4 · SLO-2 主活 A · admin 真号 E2E · credit 实时路径
 *
 * Credit 实时路径 (per CreditWorkspace.tsx:329 runDecisionWithAgent6Handoff):
 *   1. credit-input-mode-real (默认 active)
 *   2. credit-decision-cta · 触发 Agent6 报告 handoff + SSE /api/credit/decision
 *
 * 验收 (SLO-2 强 GREEN · 实时模式 真业务 done · 不被 demo mock 冒充):
 *   ✓ credit-input-mode-real toggle 真存在 + 可点
 *   ✓ credit-decision-cta 真存在 (非 credit-demo-cta)
 *   ✓ backend /api/credit/reports/sessions 真在线 (status 200 · 不 503)
 *   ✓ click decision-cta 后 60s 内 data-credit-started="yes" (业务真启动 ·
 *     post-Agent6-handoff + setStarted true · 不接受 error-banner 作为 "反应")
 *   ✓ credit-error-banner count = 0 (业务 fail 阻 spec · 不再容忍)
 *   ✓ body 无 MOCK / mock fake / fallback 字样 (silent swallow 阻 spec)
 *
 * 不可 GO (旧弱标准 commit 8a7da1e 前接受 error-banner 当成功 · 新强标准业务 fail 阻 spec):
 *   - input-mode-real 缺失 = mock 冒充实时
 *   - decision-cta 缺失 = realtime UI wire 缺
 *   - /api/credit/reports/sessions 503 = backend fallback fake
 *   - 点 CTA 60s data-credit-started 没切 yes = handoff 失败 / silent swallow
 *   - credit-error-banner visible = 后端真业务 fail
 *   - body 含 MOCK / fallback 字样 = silent 降级 (Q-055 §4 后端默认假数据混跑)
 *
 * NOTE: codex R2 R2.1 #3 strict assertion ·
 * 旧弱标准 (commit 8a7da1e 前) 接受 error-banner / handoff-banner 当 "有反应" ·
 * 新强标准要 data-credit-started="yes" 才算 done · 任何 error-banner / mock 字样阻 spec.
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

    // 4. click decision-cta · 60s 内 data-credit-started="yes" (业务真启动 · Agent6 handoff 成功)
    //    NOTE: codex R2 R2.1 #3 strict · 旧弱标准 (8a7da1e 前) 接受 error-banner 当 "反应" ·
    //    新强标准只认 data-credit-started="yes" · 任何 error 阻 spec
    await decisionCta.click();
    await expect(
      page.locator('[data-credit-started="yes"]'),
      "click decision-cta 60s data-credit-started 没切 yes · Agent6 handoff fail / SSE silent swallow",
    ).toBeVisible({ timeout: 60_000 });

    // 5. 业务真 done 后 · credit-error-banner count = 0 (后端业务 fail 阻 spec)
    expect(
      await page.locator('[data-testid="credit-error-banner"]').count(),
      "credit-error-banner visible · 后端真业务 fail · 旧弱标准容忍 · 新强标准阻 spec",
    ).toBe(0);

    // 6. 任何 "503 / Internal Server Error / [object Object]" 字样阻 spec
    const body = await page.locator("body").innerText();
    expect(body, "页面含 503").not.toMatch(/\b503\b/);
    expect(body, "页面含 Internal Server Error").not.toMatch(/Internal Server Error/i);
    expect(body, "页面含 [object Object]").not.toMatch(/\[object Object\]/);

    // 7. 不允许 MOCK / mock fake / fallback 字样 (per codex R1 §3.2 silent 降级 阻 spec)
    expect(
      body,
      "页面含 MOCK / mock fake / fallback · backend silent 降级 (Q-055 §4 后端默认假数据混跑)",
    ).not.toMatch(/\bMOCK\b|mock fake|fallback/i);
  });
});
