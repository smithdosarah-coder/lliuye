/**
 * B.3.4 · P0-R5 · 主活 B · admin 真号 E2E · credit
 *
 * PM 真意:
 *   登录 admin · 鼎盛商贸 sample (corp_dingsheng_trade)
 *   · 等 SSE done · 验 4 维评分真分数 ≠ NaN ≠ [object Object]
 *
 * 触发: credit-input-mode-demo + credit-demo-cta (per CreditWorkspace.tsx:2030,2062)
 */
import { adminTest as test, expect, E2E_TIMEOUT_MS, FIRST_PAINT_TIMEOUT_MS } from "./_shared";

test.describe("B.3.4 · admin 真号 · credit 授信 demo 鼎盛商贸", () => {
  test("点 demo 鼎盛商贸 · 4 维评分真分数 · 无 NaN/[object", async ({ page }) => {
    test.setTimeout(E2E_TIMEOUT_MS);

    await page.goto("/archive/credit", { waitUntil: "networkidle" });

    // empty-skeleton 加载 · 切 demo 模式 · 点 demo CTA
    // (AuthGate bootstrap + CF 首连延迟 · CF cold + SPA hydration 容差 30s)
    await expect(
      page.locator('[data-testid="credit-empty-skeleton"]'),
    ).toBeVisible({ timeout: FIRST_PAINT_TIMEOUT_MS });
    await page.locator('[data-testid="credit-input-mode-demo"]').click();
    await page.locator('[data-testid="credit-demo-cta"]').click();

    // SSE done → started=yes (per CreditWorkspace.tsx data-credit-started attr)
    await expect(
      page.locator('[data-credit-started="yes"]'),
    ).toBeVisible({ timeout: 60_000 });

    // demo path 走 /api/credit/demo/run · `done` event 落入 liveData (scoring/sub_scores
    // /radar/rule_hits 等) · 不走 decision-advice-live body (那是 /api/credit/decision
    // 路径下的 advising_done stage 触发的). 验收: scanned=yes + 整页无占位符 + 含数字.
    //
    // 等 SSE done 真完成 = data-credit-started + data-scanned 全 yes
    await expect(
      page.locator('[data-credit-started="yes"][data-scanned="yes"]'),
    ).toBeVisible({ timeout: 90_000 });

    // 整页文本不允许含 "NaN" / "[object Object]" / "undefined"
    // (Q-B.2.1 hotfix sub_scores 必须 int dict · PM 2026-05-10 truenum verify)
    const bodyText = await page.locator("body").innerText();
    expect(bodyText, "body 含 NaN").not.toMatch(/\bNaN\b/);
    expect(bodyText, "body 含 [object").not.toMatch(/\[object Object\]/);
    expect(bodyText, "body 含 undefined 值").not.toMatch(/:\s*undefined\b/);

    // PM "4 维评分真分数" · 至少有 4 个独立的数字 (财务 / 行业 / 经营 / 担保)
    const numbers = bodyText.match(/\b\d{1,3}(?:\.\d+)?\b/g) ?? [];
    expect(numbers.length, "body 中数字过少 · 评分可能没渲染").toBeGreaterThanOrEqual(4);
  });
});
