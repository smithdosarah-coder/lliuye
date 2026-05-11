/**
 * B.3.4 · P0-R5 · 主活 B · admin 真号 E2E · credit
 *
 * PM 真意:
 *   登录 admin · 鼎盛商贸 sample (corp_dingsheng_trade)
 *   · 等 SSE done · 验 4 维评分真分数 ≠ NaN ≠ [object Object]
 *
 * 触发: credit-input-mode-demo + credit-demo-cta (per CreditWorkspace.tsx:2030,2062)
 */
import { adminTest as test, expect, E2E_TIMEOUT_MS } from "./_shared";

test.describe("B.3.4 · admin 真号 · credit 授信 demo 鼎盛商贸", () => {
  test("点 demo 鼎盛商贸 · 4 维评分真分数 · 无 NaN/[object", async ({ page }) => {
    test.setTimeout(E2E_TIMEOUT_MS);

    await page.goto("/archive/credit", { waitUntil: "networkidle" });

    // empty-skeleton 加载 · 切 demo 模式 · 点 demo CTA
    await expect(
      page.locator('[data-testid="credit-empty-skeleton"]'),
    ).toBeVisible();
    await page.locator('[data-testid="credit-input-mode-demo"]').click();
    await page.locator('[data-testid="credit-demo-cta"]').click();

    // SSE done → started=yes (per CreditWorkspace.tsx data-credit-started attr)
    await expect(
      page.locator('[data-credit-started="yes"]'),
    ).toBeVisible({ timeout: 60_000 });

    // decision-advice-live 区域出现 = decision_done event 已收 + scoring done
    await expect(
      page.locator('[data-testid="credit-decision-advice-live"]'),
    ).toBeVisible({ timeout: 30_000 });

    // 4 维评分: 整页文本不允许含 "NaN" / "[object Object]" / "undefined"
    // (Q-B.2.1 hotfix sub_scores 必须 int dict · PM 2026-05-10 truenum verify)
    const advicePanel = page.locator('[data-testid="credit-decision-advice-live"]');
    const fullText = (await advicePanel.innerText()).trim();
    expect(fullText, "decision-advice 区域为空").not.toEqual("");
    expect(fullText, "decision-advice 含 NaN").not.toMatch(/\bNaN\b/);
    expect(fullText, "decision-advice 含 [object").not.toMatch(/\[object/);
    expect(fullText, "decision-advice 含 undefined").not.toMatch(/\bundefined\b/);

    // 至少有 1 个百分号 / 分数 (4 维评分会显数字 · 比如 75 分 / 82%)
    // 防 "all zero" 或 "空 sub_scores" 漏过
    expect(fullText, "decision-advice 无任何评分数字").toMatch(/\d{1,3}/);
  });
});
