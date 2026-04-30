import { test, expect, type Page, type Route } from "@playwright/test";

/**
 * F-RISKCTRL-LIVE-DSL-GEN · primary CTA 触发 SSE dsl_gen · ruleset_id 进 state
 *
 * 验证: 点 "选样本+写策略 · 生成 DSL" CTA → POST /api/riskctrl/dsl_gen SSE →
 * done event panels.ruleset_id 显示在 RiskOutputPanel ruleset · 视图.
 *
 * Mock SSE: 3 stage events + 1 done event (DATA_SOURCE_LIVE · ruleset 含 2 rule).
 *
 * Phase A worker-A4 · 验 SSE 整流 + done event 解析 + RiskOutputPanel ruleset_id
 *   data-testid="riskctrl-ruleset-id" 渲染.
 */

const AUTH_KEY = "platform.auth.v1";
const DEMO_USER_RM = {
  id: "u_wangzhe",
  name: "王哲",
  role: "rm",
  team: "华东·上海第一支行",
  avatar: "哲",
};

async function seedAuth(page: Page) {
  await page.addInitScript(
    ({ key, user }) => {
      window.localStorage.setItem(
        key,
        JSON.stringify({ state: { currentUser: user }, version: 0 }),
      );
    },
    { key: AUTH_KEY, user: DEMO_USER_RM },
  );
}

async function mockDslGenSse(page: Page) {
  await page.route("**/api/riskctrl/dsl_gen", async (route: Route) => {
    const sseLines = [
      `data: ${JSON.stringify({ event: "stage", stage: "parse_intent", status: "running" })}`,
      `data: ${JSON.stringify({ event: "stage", stage: "parse_intent", status: "done" })}`,
      `data: ${JSON.stringify({ event: "stage", stage: "build_prompt", status: "running" })}`,
      `data: ${JSON.stringify({ event: "stage", stage: "build_prompt", status: "done" })}`,
      `data: ${JSON.stringify({ event: "stage", stage: "validate_dsl", status: "done" })}`,
      `data: ${JSON.stringify({
        event: "done",
        data_source: "live",
        session_id: "rs_llm_8765432",
        source: "llm",
        ruleset: {
          rules: [
            {
              rule_id: "R001",
              name: "高负债拒",
              description: "debt_ratio > 0.8",
              conditions: [{ field: "debt_ratio", operator: ">", value: 0.8 }],
              action: "reject",
              priority: 1,
            },
            {
              rule_id: "R002",
              name: "新企业转人工",
              description: "company_age_years < 1",
              conditions: [{ field: "company_age_years", operator: "<", value: 1 }],
              action: "manual_review",
              priority: 5,
            },
          ],
          description: "[mocked] LLM 生成 2 规则",
        },
        ruleset_id: "rs_llm_8765432",
        csv_columns: ["loan_id", "applicant_age", "debt_ratio"],
      })}`,
    ];
    await route.fulfill({
      status: 200,
      headers: {
        "content-type": "text/event-stream",
        "cache-control": "no-cache",
      },
      body: sseLines.map((l) => l + "\n\n").join(""),
    });
  });
}

test.describe("F-RISKCTRL-LIVE-DSL-GEN · primary CTA SSE wire", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockDslGenSse(page);
  });

  test("primary CTA triggers /api/riskctrl/dsl_gen SSE · ruleset_id renders", async ({
    page,
  }) => {
    await page.goto("/archive/riskctrl", { waitUntil: "domcontentloaded" });
    const workspace = page.locator('[data-testid="riskctrl-workspace"]');
    await workspace.waitFor({ state: "visible" });
    await expect(workspace).toHaveAttribute("data-started", "no");

    // Click primary CTA · 触发 dsl_gen SSE · waitForResponse 确定性等响应而非 networkidle
    const primaryCta = page.locator('[data-testid="riskctrl-dsl-gen-cta"]');
    await expect(primaryCta).toBeVisible();
    const dslGenResp = page.waitForResponse(
      (r) => r.url().includes("/api/riskctrl/dsl_gen") && r.status() === 200,
      { timeout: 5000 },
    );
    await primaryCta.click();
    await dslGenResp;

    // 等 SSE done event 完成 · workspace started=true
    await expect(workspace).toHaveAttribute("data-started", "yes", { timeout: 5000 });
    await expect(workspace).toHaveAttribute("data-trigger", "primary_dsl");

    // 等 ruleset_id 渲染到 RiskOutputPanel
    const rulesetIdLabel = page.locator('[data-testid="riskctrl-ruleset-id"]');
    await expect(rulesetIdLabel).toBeVisible({ timeout: 5000 });
    await expect(rulesetIdLabel).toContainText("rs_llm_8765432");
  });

  test("primary CTA shows live-fail banner on backend 500", async ({
    page,
  }) => {
    // override mock to return 500
    await page.route("**/api/riskctrl/dsl_gen", async (route: Route) => {
      await route.fulfill({
        status: 500,
        contentType: "text/plain",
        body: "internal server error · LLM provider unavailable",
      });
    });
    await page.goto("/archive/riskctrl", { waitUntil: "domcontentloaded" });
    await page.locator('[data-testid="riskctrl-workspace"]').waitFor({ state: "visible" });

    const dslGenResp = page.waitForResponse(
      (r) => r.url().includes("/api/riskctrl/dsl_gen"),
      { timeout: 5000 },
    );
    await page.locator('[data-testid="riskctrl-dsl-gen-cta"]').click();
    await dslGenResp;

    // banner 显式出现 (不 silent fallback mock)
    const banner = page.locator('[data-testid="riskctrl-live-fail-banner"]');
    await expect(banner).toBeVisible({ timeout: 5000 });
    await expect(banner).toContainText(/HTTP 500|DSL 生成/);
  });
});
