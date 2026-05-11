/**
 * B.3.4 · P0-R5 · 主活 B · admin 真号 E2E · compliance
 *
 * PM 真意:
 *   登录 admin · 扫 §214 新政 (scenario_id=online_loan · /api/compliance/demo/run)
 *   · 验 冲突点 list ≥ 1
 *
 * 触发: compli-sample-batch-run (选择 scenario + 一键扫) · per ComplianceWorkspace.tsx:904
 */
import { adminTest as test, expect, E2E_TIMEOUT_MS } from "./_shared";

test.describe("B.3.4 · admin 真号 · compliance 合规 demo §214 政策", () => {
  test("扫 online_loan 政策场景 · 冲突点 list ≥ 1", async ({ page }) => {
    test.setTimeout(E2E_TIMEOUT_MS);

    await page.goto("/archive/compliance", { waitUntil: "networkidle" });

    // empty-skeleton 加载 · 选 online_loan scenario · 点 sample-batch-run
    await expect(
      page.locator('[data-testid="compli-empty-skeleton"]'),
    ).toBeVisible();

    // 选场景 (如果有显式 scenario picker)
    const scenarioBtn = page.locator(
      '[data-testid="compli-scenario-online_loan"]',
    );
    if ((await scenarioBtn.count()) > 0) {
      await scenarioBtn.click();
    }

    // 触发扫描
    await page.locator('[data-testid="compli-sample-batch-run"]').click();

    // SSE done → pilot-violations 区域可见 (冲突点 list)
    const violationsPanel = page.locator('[data-testid="compli-pilot-violations"]');
    await expect(violationsPanel).toBeVisible({ timeout: 60_000 });

    // 冲突点 ≥ 1 (per PM)
    // pilot-violations 内有可枚举的违规/冲突条目
    // 用通用 text 检查兜底 selector 变化
    const violationsText = (await violationsPanel.innerText()).trim();
    expect(violationsText, "violations 区域空").not.toEqual("");
    expect(
      violationsText,
      "violations 含占位符",
    ).not.toMatch(/\[object|undefined|^null$/);

    // 至少有 1 个条目卡 / 行 (li / row / item)
    const items = violationsPanel.locator("li, [role='listitem'], [data-testid*='violation-row'], [data-testid*='conflict']");
    const itemCount = await items.count();
    expect(itemCount, "冲突点 list 数量").toBeGreaterThanOrEqual(1);
  });
});
