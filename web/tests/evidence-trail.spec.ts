import { test, expect, type Page } from "@playwright/test";

/**
 * Task A · EvidenceTrail 5 case
 *
 * 测试策略:
 *   EvidenceProvider 会在挂载时读 `window.__EVIDENCE_TEST__` 作为最高优先级数据源。
 *   我们通过 page.addInitScript 在 navigation 前注入 fixture,驱动已挂载
 *   <EvidenceTrail> 的 archive workspace(默认以 /archive/credit 为 harness)。
 *
 * 覆盖(5 case):
 *   1) 空 evidence_trail → "暂无证据"空态
 *   2) 多源(≥3 source,含重复)→ 按 source 分组 + 折叠默认仅首组展开
 *   3) 低置信度(confidence < 0.5) → .is-low-confidence + title 提示
 *   4) popover 打开 / 关闭 → 点击弹出 · Esc 关闭
 *   5) pdf 跳页 → source .pdf + meta.page → href 带 #page=N
 */

type TestEvidenceItem = {
  source: string;
  snippet: string;
  ref_id: string;
  confidence: number;
  meta?: Record<string, unknown>;
};

type TestInjection = {
  evidence_trail?: TestEvidenceItem[];
  unfilled_fields?: string[];
};

const HARNESS_ROUTE = "/archive/credit";

/** Seed persisted auth state so RbacGuard lets the workspace render. */
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

async function seed(page: Page, payload: TestInjection): Promise<void> {
  await seedAuth(page);
  await page.addInitScript((p) => {
    (window as unknown as { __EVIDENCE_TEST__: TestInjection }).__EVIDENCE_TEST__ = p;
  }, payload);
}

async function gotoHarness(page: Page): Promise<void> {
  await page.goto(HARNESS_ROUTE, { waitUntil: "domcontentloaded" });
  await page.waitForSelector(".ev-trail", { timeout: 10_000 });
}

test.describe("EvidenceTrail · Task A", () => {
  test("case 1 · 空 evidence_trail 渲染空态", async ({ page }) => {
    await seed(page, { evidence_trail: [], unfilled_fields: [] });
    await gotoHarness(page);
    const trail = page.locator(".ev-trail").first();
    await expect(trail).toHaveClass(/ev-trail--empty/);
    await expect(trail.locator(".ev-trail-empty-msg")).toHaveText("暂无证据");
    await expect(trail.locator(".ev-trail-count")).toContainText("0 条");
  });

  test("case 2 · 多源按 source 分组 + 首组默认展开", async ({ page }) => {
    await seed(page, {
      evidence_trail: [
        { source: "材料/bs_2024.pdf", snippet: "流动资产 2135 万", ref_id: "e1", confidence: 0.95 },
        { source: "材料/bs_2024.pdf", snippet: "流动负债 1248 万", ref_id: "e2", confidence: 0.93 },
        { source: "内部 KB · F5189", snippet: "行业毛利率 28.7%", ref_id: "e3", confidence: 0.82 },
        { source: "政府采购网", snippet: "2025-03 中标", ref_id: "e4", confidence: 0.71 },
      ],
      unfilled_fields: [],
    });
    await gotoHarness(page);
    const trail = page.locator(".ev-trail").first();
    await expect(trail.locator(".ev-trail-count")).toContainText("4 条");
    await expect(trail.locator(".ev-trail-count")).toContainText("3 源");
    const groups = trail.locator(".ev-trail-group");
    await expect(groups).toHaveCount(3);
    await expect(groups.nth(0)).toHaveAttribute("data-open", "true");
    await expect(groups.nth(1)).toHaveAttribute("data-open", "false");
    const firstItems = groups.nth(0).locator(".ev-trail-item");
    await expect(firstItems).toHaveCount(2);
  });

  test("case 3 · 低置信度加 .is-low-confidence + title 提示", async ({ page }) => {
    // 首组 "审贷员批注" 默认展开,包含 2 条低置信;"审计报告" 首组之外,合成断言仅验首组低置信。
    await seed(page, {
      evidence_trail: [
        { source: "审贷员批注", snippet: "季节性备货 · 口述", ref_id: "low1", confidence: 0.32 },
        { source: "审贷员批注", snippet: "意向产品 · 未书面", ref_id: "low2", confidence: 0.48 },
        { source: "审计报告", snippet: "营收 5820 万", ref_id: "hi1", confidence: 0.97 },
      ],
      unfilled_fields: [],
    });
    await gotoHarness(page);
    const trail = page.locator(".ev-trail").first();
    const lowItems = trail.locator(".ev-trail-item.is-low-confidence");
    await expect(lowItems).toHaveCount(2);
    await expect(lowItems.first().locator(".ev-trail-item-btn")).toHaveAttribute(
      "title",
      "置信度偏低"
    );
  });

  test("case 4 · popover 点开 · Esc 关闭", async ({ page }) => {
    await seed(page, {
      evidence_trail: [
        { source: "审计报告.pdf", snippet: "毛利率 32.4%", ref_id: "p1", confidence: 0.94, meta: { page: 7 } },
      ],
      unfilled_fields: [],
    });
    await gotoHarness(page);
    const trail = page.locator(".ev-trail").first();
    const btn = trail.locator(".ev-trail-item-btn").first();
    await btn.click();
    const popover = trail.locator(".ev-popover").first();
    await expect(popover).toBeVisible();
    await expect(popover.locator(".ev-popover-snippet")).toContainText("毛利率 32.4%");
    await page.keyboard.press("Escape");
    await expect(popover).toHaveCount(0);
  });

  test("case 5 · pdf source + meta.page → href 带 #page=N", async ({ page }) => {
    await seed(page, {
      evidence_trail: [
        {
          source: "materials/顶盛_审计报告_2024.pdf",
          snippet: "流动比率 1.71",
          ref_id: "pdf1",
          confidence: 0.96,
          meta: { page: 14 },
        },
      ],
      unfilled_fields: [],
    });
    await gotoHarness(page);
    const trail = page.locator(".ev-trail").first();
    await trail.locator(".ev-trail-item-btn").first().click();
    const link = trail.locator(".ev-popover-link").first();
    const href = await link.getAttribute("href");
    expect(href).toBeTruthy();
    expect(href!).toContain("#page=14");
    expect(href!.endsWith(".pdf#page=14")).toBe(true);
  });
});
