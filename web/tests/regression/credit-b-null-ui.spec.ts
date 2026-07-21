import { expect, test, type BrowserContext, type Page } from "@playwright/test";

const USER = {
  user: { id: "u_test", name: "测试", role: "admin", team: "测试", avatar: "测" },
  roles: ["admin"],
  accessibleAgents: ["credit", "report"],
};

type AmountCase = { flag?: boolean; amount: number | null; graphFlag?: boolean; graphAmount: number | null };

async function stubCase(context: BrowserContext, amountCase: AmountCase) {
  await context.route("**/api/auth/me", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(USER) }));
  await context.route("**/api/credit/reports/sessions**", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ sessions: [{ session_id: "s1", report_id: "r1", company_name: "额度契约企业", segment: "corporate", generated_at: "2026-07-21", status: "done" }], count: 1 }),
  }));
  await context.route("**/api/credit/handoff/from_report", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ session_id: "s1", report_id: "r1", company_name: "额度契约企业", industry: "测试", generated_at: "2026-07-21", enterprise_profile: { profile_id: "p1", company_name: "额度契约企业" }, ready_for_decision: true, missing_fields: [] }),
  }));
  await context.route("**/api/credit/decision", (route) => {
    const advice = { decision: "拒绝", approved_amount: amountCase.amount, composite_score: 44, ...(amountCase.flag === undefined ? {} : { amount_provided: amountCase.flag }) };
    const done = {
      event: "done", stage_tab: "corporate", source: "report_json", profile: { company_name: "额度契约企业" },
      scoring: { composite_score: 44, sub_scores: {} }, rule_hits: [], case_matches: [], advice,
      decision_graph: { decision_summary: { amount_provided: amountCase.graphFlag, approved_amount: amountCase.graphAmount } },
    };
    const body = [
      `data: ${JSON.stringify({ event: "stage", stage: "advising_done", payload: advice })}\n\n`,
      `data: ${JSON.stringify(done)}\n\n`,
    ].join("");
    return route.fulfill({ status: 200, contentType: "text/event-stream", body });
  });
}

async function runAndOpenLimit(page: Page) {
  await page.goto("/archive/credit", { waitUntil: "networkidle" });
  const realMode = page.locator('[data-testid="credit-input-mode-real"]');
  await realMode.click();
  await expect(realMode).toHaveAttribute("aria-selected", "true");
  await expect(page.locator('[data-testid="credit-decision-cta"]')).toBeVisible();
  await page.locator('[data-testid="credit-decision-cta"]').click();
  await expect(page.locator('[data-testid="credit-live-advice-amount"]')).toBeVisible();
  await expect(page.locator('[data-testid="credit-dashboard-limit"]')).toBeAttached();
  await page.locator('[data-testid="credit-output-tab-limit"]').click();
  await expect(page.locator('[data-testid="credit-limit-view"]')).toBeVisible();
}

for (const scenario of [
  { name: "false+0 and graph false/null is missing", data: { flag: false, amount: 0, graphFlag: false, graphAmount: null }, missing: true },
  { name: "true+0 is a real zero amount", data: { flag: true, amount: 0, graphFlag: true, graphAmount: 0 }, missing: false },
  { name: "legacy absent flag + 0 remains provided", data: { amount: 0, graphAmount: 0 }, missing: false },
] as const) {
  test(`B-null UI · ${scenario.name}`, async ({ page, context }) => {
    await stubCase(context, scenario.data);
    await runAndOpenLimit(page);
    const live = page.locator('[data-testid="credit-live-advice-amount"]');
    const dashboard = page.locator('[data-testid="credit-dashboard-limit"]');
    const limit = page.locator('[data-testid="credit-limit-view"]');
    if (scenario.missing) {
      for (const target of [live, dashboard, limit]) {
        await expect(target).toContainText("额度未提供 · 仅风险评估");
        await expect(target).not.toContainText(/¥0|0万元|NaN|Infinity/);
      }
    } else {
      for (const target of [live, dashboard, limit]) {
        await expect(target).toContainText("0");
        await expect(target).not.toContainText("额度未提供 · 仅风险评估");
        await expect(target).not.toContainText(/NaN|Infinity/);
      }
    }
  });
}
