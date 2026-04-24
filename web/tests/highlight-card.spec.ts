import { test, expect, type Page } from "@playwright/test";

/**
 * Task B · HighlightCard + claimParser 3 case
 *
 * 3 case:
 *   1. 正文含 [ref:ev_001]...[/ref] → 渲染 <mark.ev-highlight data-ref-id>;hover 弹 mini popover
 *   2. 正文无 [ref:] 锚点 → 原样文本,无高亮
 *   3. ref_id 在 evidence_trail 里找不到 → HighlightCard 降级为 <span data-ref-missing>,不报错
 */

type TestEvidenceItem = {
  source: string;
  snippet: string;
  ref_id: string;
  confidence: number;
  meta?: Record<string, unknown>;
};

const HARNESS_ROUTE = "/archive/credit";

async function seedAuth(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const user = {
      id: "u_wangzhe",
      name: "王哲",
      role: "rm",
      team: "华东·上海第一支行",
      avatar: "哲",
    };
    window.localStorage.setItem(
      "platform.auth.v1",
      JSON.stringify({ state: { currentUser: user }, version: 0 })
    );
  });
}

async function seed(
  page: Page,
  evidence: TestEvidenceItem[],
  claimText: string
): Promise<void> {
  await seedAuth(page);
  await page.addInitScript(
    (args) => {
      (window as unknown as { __EVIDENCE_TEST__: unknown }).__EVIDENCE_TEST__ = {
        evidence_trail: args.ev,
        unfilled_fields: [],
      };
      (window as unknown as { __CLAIM_TEST_TEXT__: string }).__CLAIM_TEST_TEXT__ =
        args.text;
    },
    { ev: evidence, text: claimText }
  );
}

async function gotoHarness(page: Page): Promise<void> {
  await page.goto(HARNESS_ROUTE, { waitUntil: "domcontentloaded" });
  await page.waitForSelector(".ev-claim-summary", { timeout: 10_000 });
}

test.describe("HighlightCard · Task B", () => {
  test("case 1 · [ref:] 锚点渲染高亮 + hover 弹 mini popover", async ({ page }) => {
    await seed(
      page,
      [
        {
          source: "审计报告.pdf",
          snippet: "营收 5820 万 · 毛利率 32.4%",
          ref_id: "ev_001",
          confidence: 0.94,
          meta: { page: 14 },
        },
      ],
      "根据审计报告,[ref:ev_001]2024 年营收 5820 万,毛利率 32.4%[/ref],处于行业 70 分位以上。"
    );
    await gotoHarness(page);
    const summary = page.locator(".ev-claim-summary").first();
    const marks = summary.locator("mark.ev-highlight");
    await expect(marks).toHaveCount(1);
    await expect(marks.first()).toHaveAttribute("data-ref-id", "ev_001");
    await expect(marks.first()).toContainText("2024 年营收 5820 万");

    await marks.first().hover();
    const mini = summary.locator(".ev-highlight-mini").first();
    await expect(mini).toBeVisible();
    await expect(mini.locator(".ev-highlight-mini-source")).toHaveText("审计报告.pdf");
    await expect(mini.locator(".ev-highlight-mini-num")).toContainText("94%");
  });

  test("case 2 · 无 [ref:] 锚点原样渲染,无高亮", async ({ page }) => {
    await seed(
      page,
      [
        {
          source: "tax.csv",
          snippet: "申报稳定",
          ref_id: "ev_tax",
          confidence: 0.8,
        },
      ],
      "这段结论没有任何证据锚点,应该原样文本渲染,没有 mark 标签被生成。"
    );
    await gotoHarness(page);
    const summary = page.locator(".ev-claim-summary").first();
    await expect(summary.locator("mark.ev-highlight")).toHaveCount(0);
    await expect(summary).toContainText("应该原样文本渲染");
    await expect(summary).toContainText("没有 mark 标签被生成");
  });

  test("case 3 · ref_id 在 evidence_trail 找不到 → 降级 span,不报错", async ({
    page,
  }) => {
    const consoleErrors: string[] = [];
    page.on("pageerror", (err) => consoleErrors.push(err.message));
    await seed(
      page,
      [
        {
          source: "known.pdf",
          snippet: "已知证据",
          ref_id: "ev_known",
          confidence: 0.9,
        },
      ],
      "这条引用的证据 [ref:ev_missing]实际并不存在于 evidence_trail[/ref],前端不得报错。"
    );
    await gotoHarness(page);
    const summary = page.locator(".ev-claim-summary").first();
    // 降级 <span data-ref-missing="ev_missing"> · 不是 <mark.ev-highlight>
    await expect(summary.locator("mark.ev-highlight")).toHaveCount(0);
    const fallback = summary.locator('span[data-ref-missing="ev_missing"]');
    await expect(fallback).toHaveCount(1);
    await expect(fallback).toContainText("实际并不存在于 evidence_trail");
    expect(consoleErrors).toEqual([]);
  });
});
