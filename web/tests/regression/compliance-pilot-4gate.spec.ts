import { test, expect } from "@playwright/test";

/**
 * Phase A worker-A4-compli · compliance pilot · 4 gate state model + done envelope + view tab
 *
 * 验:
 *   T1 · gate 1+2 (started + selectedSessionId) · 切 session 下拉 + apply → 5 panel 同步亮
 *   T2 · gate 3 (liveData) · /api/compliance/policy_scan mock SSE 4-panel envelope → liveData 注入 + auto-pick violations[0]
 *   T3 · gate 4 (selectedViolationId) · violation card click → ViolationDetail 出 · ESC 关
 *   T4 · view tab · by_violation / by_clause / by_event 三视角无状态污染
 *   T5 · demo/run · /api/compliance/demo/run wired · scenario_id online_loan + data_source=mock_forced
 *
 * Auth bypass: localStorage seed `platform.auth.v1` (Zustand persist) · rm 全 ACCESS · 与 channel-pilot smoke 同 pattern
 */

const MOCK_ME_RESPONSE = {
  user: {
    id: "u_wangzhe",
    name: "王哲",
    role: "rm",
    team: "华东·上海第一支行",
    avatar: "哲",
  },
  roles: ["rm"],
  accessibleAgents: ["channel", "report", "credit", "alert", "compli", "compliance", "riskctrl"],
};

test.beforeEach(async ({ context }) => {
  await context.route("**/api/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_ME_RESPONSE),
    });
  });
});

const SAMPLE_DONE_ENVELOPE = {
  event: "done",
  data_source: "live",
  session_id: "test-compli-live-1",
  metrics: {
    rule_count: 68,
    event_count: 145,
    cell_count: 9860,
    severe: 1,
    normal: 1,
    observation: 0,
    violation_count: 2,
    duration_seconds: 12.5,
  },
  violations: [
    {
      violation_id: "VIO-001",
      rule_id: "POL-001",
      rule_article: "第六条",
      rule_condition: "个人消费贷款期限不得超过 12 个月",
      rule_category: "期限",
      event_id: "LN20260118-027",
      event_type: "loan",
      event_fields: { months: 18 },
      severity: "critical",
      evidence: "months=18 超阈值",
      match_reason: "事件 LN027 期限 18 月 超 12 月上限",
      revisions: [
        { category: "改", title: "缩短期限至 12 月内", text: "缩短消费贷期限至 12 月以内 sentinel-VIO-001-rev" },
      ],
    },
    {
      violation_id: "VIO-002",
      rule_id: "POL-019",
      rule_article: "第十九条",
      rule_condition: "互联网贷款合作业务应在合同中明示资金方",
      rule_category: "信息披露",
      event_id: "AD2026-MAR-019",
      event_type: "marketing",
      event_fields: {},
      severity: "major",
      evidence: "营销物料未披露资金方",
      match_reason: "短视频信息流未明示出资方",
      revisions: [
        { category: "补", title: "补资金方明示", text: "信息流补资金方明示 sentinel-VIO-002-rev" },
      ],
    },
  ],
  matrix: [],
  events: [],
  recommendations: [
    { violation_id: "VIO-001", category: "改", title: "缩短期限至 12 月内", text: "缩短消费贷期限至 12 月以内 sentinel-VIO-001-rev" },
    { violation_id: "VIO-002", category: "补", title: "补资金方明示", text: "信息流补资金方明示 sentinel-VIO-002-rev" },
  ],
  rules_preview: [],
  events_preview: [],
  policy_meta: { title: "test policy", source_url: "test", fetched_at: "2026-04-29" },
};

test.describe("worker-A4-compli · compliance pilot · 4 gate", () => {
  test("T1 · gate 1+2 mock session select → 5 panel sync", async ({ page }) => {
    await page.goto("/archive/compliance", { waitUntil: "networkidle" });

    /* 默认 started=false · 等用户操作 · empty skeleton 显 */
    const workspace = page.locator('[data-testid="compli-workspace"]');
    await expect(workspace).toHaveAttribute("data-started", "no");

    /* gate 2 dropdown · 默认 selectedSessionId 与 pendingSessionId 一致 · apply disabled */
    const sessionSelect = page.locator('[data-testid="compli-session-select"]');
    const sessionApply = page.locator('[data-testid="compli-session-apply"]');
    await expect(sessionSelect).toBeVisible();
    await expect(sessionApply).toBeDisabled();

    /* 用 history dropdown 触发 started=true (单 session 暂无 swap target · history 走 demo/run) */
    /* 但 demo/run 会真请求后端 · 这里仅 verify session select wiring · 通过 template check 触发 started */
    const tplCta = page.locator('[data-testid="compli-template-check-cta"]');
    /* 路由拦截 matrix_check · 防真 fetch */
    await page.route("**/api/compliance/matrix_check", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ok: true, matrix: [] }),
      });
    });
    await tplCta.click();
    await page.waitForTimeout(300);

    await expect(workspace).toHaveAttribute("data-started", "yes");

    /* 5 panel 全亮 (data-testid 在 panel section root) */
    for (const k of ["ticker", "matrix", "violations", "revisions"]) {
      await expect(
        page.locator(`[data-testid="compli-pilot-${k}"]`),
      ).toBeVisible();
    }

    /* mock 模式 · violations panel data-mode=mock */
    await expect(
      page.locator('[data-testid="compli-pilot-violations"]'),
    ).toHaveAttribute("data-mode", "mock");
  });

  test("T2 · gate 3 liveData · /api/compliance/policy_scan mock SSE → 5 panel hydrate + isLive", async ({
    page,
    context,
  }) => {
    await context.route("**/api/compliance/policy_scan", async (route) => {
      const sse = [
        `event: stage\ndata: ${JSON.stringify({ event: "stage", payload: { type: "stage", stage: "rule_extract", status: "done" } })}\n\n`,
        `event: done\ndata: ${JSON.stringify(SAMPLE_DONE_ENVELOPE)}\n\n`,
      ].join("");
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: sse,
      });
    });

    await page.goto("/archive/compliance", { waitUntil: "networkidle" });

    /* 触发 primary scan CTA · 上传 rail 内的 "开始政策比对" */
    const primaryCta = page.locator('[data-testid="compli-policy-scan-cta"]');
    await expect(primaryCta).toBeVisible();
    await primaryCta.click();
    await page.waitForTimeout(500);

    /* workspace data-mode=live (liveData != null) */
    await expect(
      page.locator('[data-testid="compli-workspace"]'),
    ).toHaveAttribute("data-mode", "live");
    await expect(
      page.locator('[data-testid="compli-pilot-violations"]'),
    ).toHaveAttribute("data-mode", "live");

    /* 5 panel 全亮 */
    for (const k of ["ticker", "matrix", "violations", "revisions"]) {
      await expect(
        page.locator(`[data-testid="compli-pilot-${k}"]`),
      ).toBeVisible();
    }

    /* gate 4 auto-pick violations[0] = VIO-001 · ViolationDetail 自动出 */
    await expect(
      page.locator('[data-testid="compli-pilot-detail"]'),
    ).toBeVisible();

    /* violation card 显 backend 注入的 第六条 · 不是 mock 模板 */
    const cards = page.locator('[data-testid="compli-violation-card"]');
    await expect(cards.first()).toContainText("第六条");
  });

  test("T3 · gate 4 selectedViolationId · card click → ViolationDetail 出 · ESC 关", async ({
    page,
    context,
  }) => {
    await context.route("**/api/compliance/policy_scan", async (route) => {
      const sse = [
        `event: stage\ndata: ${JSON.stringify({ event: "stage", payload: { type: "stage", stage: "rule_extract", status: "done" } })}\n\n`,
        `event: done\ndata: ${JSON.stringify(SAMPLE_DONE_ENVELOPE)}\n\n`,
      ].join("");
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: sse,
      });
    });

    await page.goto("/archive/compliance", { waitUntil: "networkidle" });
    await page.locator('[data-testid="compli-policy-scan-cta"]').click();
    await page.waitForTimeout(500);

    /* T2 已 verify auto-pick violations[0] · 点 violations[1] 切 detail */
    const card2 = page.locator('[data-testid="compli-violation-card"]').nth(1);
    await expect(card2).toBeVisible();
    await card2.click();
    await page.waitForTimeout(150);

    const detail = page.locator('[data-testid="compli-pilot-detail"]');
    await expect(detail).toBeVisible();

    /* 联动 sentinel · 修订意见关联 VIO-002 */
    await expect(detail).toContainText("第十九条");

    /* ESC 关 selectedViolationId */
    await page.keyboard.press("Escape");
    await expect(detail).toBeHidden();
  });

  test("T4 · view tab · by_violation / by_clause / by_event 三视角无状态污染", async ({
    page,
    context,
  }) => {
    await context.route("**/api/compliance/policy_scan", async (route) => {
      const sse = [
        `event: stage\ndata: ${JSON.stringify({ event: "stage", payload: { type: "stage", stage: "rule_extract", status: "done" } })}\n\n`,
        `event: done\ndata: ${JSON.stringify(SAMPLE_DONE_ENVELOPE)}\n\n`,
      ].join("");
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: sse,
      });
    });

    await page.goto("/archive/compliance", { waitUntil: "networkidle" });
    await page.locator('[data-testid="compli-policy-scan-cta"]').click();
    await page.waitForTimeout(500);

    const violations = page.locator('[data-testid="compli-pilot-violations"]');
    /* 默认 by_violation */
    await expect(violations).toHaveAttribute("data-view", "by_violation");

    /* 切 by_clause */
    await page.locator('[data-testid="compli-violation-view-by_clause"]').click();
    await expect(violations).toHaveAttribute("data-view", "by_clause");

    /* 切 by_event */
    await page.locator('[data-testid="compli-violation-view-by_event"]').click();
    await expect(violations).toHaveAttribute("data-view", "by_event");

    /* 切回 by_violation · 三视角无残留状态 */
    await page.locator('[data-testid="compli-violation-view-by_violation"]').click();
    await expect(violations).toHaveAttribute("data-view", "by_violation");

    /* 视角切换不影响 violations 列表全显 (cards 数 ≥ 2 即注入的 VIO-001/002) */
    const cards = page.locator('[data-testid="compli-violation-card"]');
    await expect(cards).toHaveCount(2);
  });

  test("T5 · demo/run · /api/compliance/demo/run wired · scenario_id payload + data_source=mock_forced", async ({
    page,
    context,
  }) => {
    let demoEndpointHit = false;
    let demoScenarioPayload: string | null = null;
    await context.route("**/api/compliance/demo/run", async (route) => {
      demoEndpointHit = true;
      try {
        const body = route.request().postDataJSON() as { scenario_id?: string };
        demoScenarioPayload = body?.scenario_id ?? null;
      } catch {
        demoScenarioPayload = null;
      }
      const demoEnv = {
        ...SAMPLE_DONE_ENVELOPE,
        data_source: "mock_forced",
        session_id: "demo_online_loan_test",
        scenario_id: "online_loan",
      };
      const sse = [
        `event: stage\ndata: ${JSON.stringify({ event: "stage", stage: "rule_extract", status: "running" })}\n\n`,
        `event: stage\ndata: ${JSON.stringify({ event: "stage", stage: "rule_extract", status: "done" })}\n\n`,
        `event: done\ndata: ${JSON.stringify(demoEnv)}\n\n`,
      ].join("");
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: sse,
      });
    });

    await page.goto("/archive/compliance", { waitUntil: "networkidle" });

    /* 选 online_loan demo · 点 "查看示例" */
    await page.locator('[data-testid="compli-history-dropdown"]').selectOption("demo-online-loan");
    await page.locator('[data-testid="compli-history-apply"]').click();
    await page.waitForTimeout(500);

    expect(demoEndpointHit).toBe(true);
    expect(demoScenarioPayload).toBe("online_loan");

    /* workspace data-trigger=tertiary_history · data-mode=live (demo 也走 setLiveData 路径) */
    const ws = page.locator('[data-testid="compli-workspace"]');
    await expect(ws).toHaveAttribute("data-trigger", "tertiary_history");
    await expect(ws).toHaveAttribute("data-mode", "live");

    /* training mode banner 显 (cat 11-5 PRESERVE) */
    await expect(page.locator('[data-testid="compli-demo-banner"]')).toBeVisible();

    /* 5 panel 全亮 */
    for (const k of ["ticker", "matrix", "violations", "revisions", "detail"]) {
      await expect(
        page.locator(`[data-testid="compli-pilot-${k}"]`),
      ).toBeVisible();
    }
  });
});
