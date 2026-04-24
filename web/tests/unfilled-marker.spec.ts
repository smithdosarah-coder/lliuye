import { test, expect, type Page } from "@playwright/test";

/**
 * Task C · UnfilledMarker 4 case
 *
 * 4 case(CLAUDE.md §12 硬红线):
 *   1. unfilled_fields 含字段名 → 渲染 <UnfilledMarker>,文案 "未能自动填写"
 *   2. 正文含字面值 "未能自动填写" → 替换为组件(不是纯文本 span)
 *   3. reason="qc_blocked" → hover tooltip "QC 拦截"
 *   4. reason="no_evidence" → hover tooltip "证据不足"
 *
 * 正文级测试(case 2-4)借 ClaimText 的 window.__CLAIM_TEST_TEXT__ 注入通道。
 * 字段级测试(case 1)借 window.__EVIDENCE_TEST__.unfilled_fields。
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
  opts: {
    evidence?: TestEvidenceItem[];
    unfilled?: string[];
    claim?: string;
  }
): Promise<void> {
  await seedAuth(page);
  await page.addInitScript((args) => {
    (window as unknown as { __EVIDENCE_TEST__: unknown }).__EVIDENCE_TEST__ = {
      evidence_trail: args.ev ?? [],
      unfilled_fields: args.unfilled ?? [],
    };
    if (typeof args.claim === "string") {
      (window as unknown as { __CLAIM_TEST_TEXT__: string }).__CLAIM_TEST_TEXT__ =
        args.claim;
    }
  }, {
    ev: opts.evidence ?? [],
    unfilled: opts.unfilled ?? [],
    claim: opts.claim,
  });
}

async function gotoHarness(page: Page): Promise<void> {
  await page.goto(HARNESS_ROUTE, { waitUntil: "domcontentloaded" });
  await page.waitForSelector(".rpt-workspace", { timeout: 10_000 });
}

test.describe("UnfilledMarker · Task C", () => {
  test("case 1 · unfilled_fields 命中 → 渲染 <UnfilledMarker>", async ({ page }) => {
    await seed(page, {
      evidence: [],
      unfilled: ["revenue_2024", "downstream_concentration"],
      claim: "本段无字面值,仅验字段级 marker 挂载。",
    });
    await gotoHarness(page);
    const list = page.locator(".ev-unfilled-list").first();
    await expect(list).toBeVisible();
    const markers = list.locator(".ev-unfilled");
    await expect(markers).toHaveCount(2);
    await expect(markers.first()).toHaveAttribute("data-field-name", "revenue_2024");
    await expect(markers.first()).toContainText("未能自动填写");
  });

  test("case 2 · 正文字面值 '未能自动填写' 替换为组件,不是纯文本", async ({ page }) => {
    await seed(page, {
      evidence: [],
      unfilled: [],
      claim: "申请人的担保人财报未能自动填写,需人工补材料。",
    });
    await gotoHarness(page);
    const summary = page.locator(".ev-claim-summary").first();
    // 命中内嵌 UnfilledMarker(inline)
    const inlineMarker = summary.locator(".ev-unfilled.ev-unfilled--inline");
    await expect(inlineMarker).toHaveCount(1);
    await expect(inlineMarker.first()).toContainText("未能自动填写");
    // 正文其余文本仍在
    await expect(summary).toContainText("申请人的担保人财报");
    await expect(summary).toContainText("需人工补材料");
  });

  test("case 3 · reason=qc_blocked → hover tooltip '· QC 拦截'", async ({ page }) => {
    await seed(page, {
      evidence: [],
      unfilled: ["guarantor_financials_2024"],
      claim: "验 reason qc_blocked tooltip。",
    });
    await gotoHarness(page);
    const marker = page
      .locator('.ev-unfilled[data-field-name="guarantor_financials_2024"]')
      .first();
    await expect(marker).toHaveAttribute("data-reason", "qc_blocked");
    const title = await marker.getAttribute("title");
    expect(title).toBeTruthy();
    expect(title!).toContain("未能自动填写");
    expect(title!).toContain("QC 拦截");
  });

  test("case 4 · reason=no_evidence → hover tooltip '证据不足'", async ({ page }) => {
    // 通过 EvidenceContext 扩展字段 unfilled_reasons 让 UnfilledFields 给特定字段覆盖 reason
    await seedAuth(page);
    await page.addInitScript(() => {
      (window as unknown as { __EVIDENCE_TEST__: unknown }).__EVIDENCE_TEST__ = {
        evidence_trail: [],
        unfilled_fields: ["external_rating_latest"],
        unfilled_reasons: { external_rating_latest: "no_evidence" },
      };
    });
    await gotoHarness(page);
    const marker = page
      .locator('.ev-unfilled[data-field-name="external_rating_latest"]')
      .first();
    await expect(marker).toHaveAttribute("data-reason", "no_evidence");
    const title = await marker.getAttribute("title");
    expect(title).toBeTruthy();
    expect(title!).toContain("证据不足");
    expect(title!).toContain("未能自动填写");
  });
});
