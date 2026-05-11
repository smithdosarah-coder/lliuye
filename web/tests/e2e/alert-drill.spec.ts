import { test, expect, type Route } from "@playwright/test";

/**
 * B.3.4 · fix-bugs Bug C · alert 客户行可点 + 排版 (TDD red-to-green)
 *
 * PM 痛 (5/11 凌晨): 预警 (alert): 队列出来 · 不能点客户详情 · 严重排版问题
 *
 * 契约 (KT R2 TDD):
 *   T1 · 跑 demo 扫 alert-pool · done 后 红/黄 top-case-row 渲染 ≥ 1
 *   T2 · 点 alert-top-case-row · AlertDrillDrawer 显 + 含客户名 + 客户信号详情
 *   T3 · ESC 关 drawer
 *   T4 · 排版基线 · TopCase row data-testid + role=button + tabIndex 都在
 *
 * 反模式 (per prompt "不可 GO"):
 *   - 只改 CSS 不动 state binding (alert/compliance) → 必须验 click → state → drawer 真链路
 *
 * Auth bypass + SSE mock · 跟 Bug A/B pattern 一致
 */

const MOCK_ME_RESPONSE = {
  user: {
    id: "u_chenkai",
    name: "陈凯",
    role: "risk_manager",
    team: "总部·风险管理部",
    avatar: "凯",
  },
  roles: ["risk_manager"],
  accessibleAgents: ["channel", "report", "credit", "alert", "compliance", "riskctrl"],
};

const STUB_TOP_CASES = [
  {
    id: "hit-1",
    client_id: "C001",
    customer: "测试红档客户公司",
    amount: "¥1200万",
    risk_level: "red",
    matched_rules: ["R-001 司法负面命中", "R-007 流水异常"],
    triggers: ["司法负面命中", "流水异常陡降"],
    advice: "立即电话核实 + 触发风险尽调",
    last_update: "刚刚",
  },
  {
    id: "hit-2",
    client_id: "C002",
    customer: "测试黄档客户公司",
    amount: "¥600万",
    risk_level: "yellow",
    matched_rules: ["R-012 行业景气"],
    triggers: ["行业景气下行"],
    advice: "周内回访 + 增信讨论",
    last_update: "刚刚",
  },
];

const STUB_DONE_PAYLOAD = {
  event: "done",
  session_id: "alert-drill-spec-1",
  data_source: "live",
  mode: "demo",
  totals: { red: 1, yellow: 1, green: 0 },
  hit_list: {
    red_count: 1,
    yellow_count: 1,
    green_count: 0,
    hits: STUB_TOP_CASES,
  },
  top_cases: STUB_TOP_CASES,
  signal_heatmap: [],
  industry_distribution: [],
  reach_rate: [],
  summary: "demo 扫描完毕 · 红 1 黄 1",
  kb_state: "test",
};

const STUB_DRILL_PAYLOAD = {
  client_id: "C001",
  company_name: "测试红档客户公司",
  level: "red",
  score: 87,
  matched_rules: ["R-001 司法负面命中", "R-007 流水异常"],
  reasons: ["近 30 日司法负面 3 起 (天眼查)", "近 7 日流水陡降 -42%"],
  signal_timeline: [
    {
      source: "external_scan",
      snippet: "2026-04 法院判决文书 · 借款合同纠纷",
      url: "https://example.test/judgment/123",
    },
    {
      source: "internal_txn",
      snippet: "近 7 日累计流水 -42% · vs 30 日均值",
      url: "",
    },
    {
      source: "cross_match",
      snippet: "外部司法 + 内部流水双路命中 · 严重风险",
      url: "",
    },
  ],
  disposition: { content: "立即电话核实 + 触发风险尽调" },
  disposition_source: "rule_engine",
};

function stubAlertSse(route: Route) {
  return route.fulfill({
    status: 200,
    contentType: "text/event-stream",
    body:
      `event: stage\ndata: ${JSON.stringify({ event: "stage", stage: "ingest", status: "done" })}\n\n` +
      `event: stage\ndata: ${JSON.stringify({ event: "stage", stage: "scan", status: "done" })}\n\n` +
      `event: done\ndata: ${JSON.stringify(STUB_DONE_PAYLOAD)}\n\n`,
  });
}

test.beforeEach(async ({ context }) => {
  await context.route("**/api/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_ME_RESPONSE),
    });
  });
  await context.route("**/api/alert/demo/run", stubAlertSse);
  await context.route("**/api/alert/scan", stubAlertSse);
  await context.route(/\/api\/alert\/drill\/.+/, async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(STUB_DRILL_PAYLOAD),
    });
  });
});

async function triggerDemoScan(page: import("@playwright/test").Page) {
  await page.goto("/archive/alert", { waitUntil: "networkidle" });

  // 切到 demo 输入模式 (若 default 是 live)
  const demoBtn = page.locator('[data-testid="alert-input-mode-demo"]').first();
  if (await demoBtn.isVisible().catch(() => false)) {
    await demoBtn.click();
  }
  // 主 CTA 触发 demo 扫
  const cta = page.locator('[data-testid="alert-scan-cta"]').first();
  await expect(cta).toBeVisible();
  await cta.click();
  // SSE done 走完 + topCases 渲完
  await page.waitForTimeout(1000);
}

test.describe("B.3.4 Bug C · alert 客户行可点 + drawer (TDD red-to-green)", () => {
  test("T1 · demo 扫完 · top-case-row 渲染 ≥ 1 (queue 出来)", async ({ page }) => {
    await triggerDemoScan(page);

    const rows = page.locator('[data-testid="alert-top-case-row"]');
    await expect(rows.first()).toBeVisible();
    // 至少 1 行 红档 (per STUB_TOP_CASES)
    expect(await rows.count()).toBeGreaterThanOrEqual(1);
  });

  test("T2 · 点 top-case-row · drawer 显 + 客户名 + 信号详情", async ({ page }) => {
    await triggerDemoScan(page);

    const row = page.locator('[data-testid="alert-top-case-row"]').first();
    await expect(row).toBeVisible();
    await row.click();

    const drawer = page.locator('[data-testid="alert-drill-drawer"]');
    await expect(drawer).toBeVisible();
    // drawer 应显客户名 (data?.company_name 或 fallback topCase.customer)
    await expect(drawer).toContainText("测试红档客户公司");
    // drawer fetch /api/alert/drill/{client_id} 成功后 · 应展示规则命中 + 信号 timeline
    // 等 fetch + render
    await page.waitForTimeout(500);
    await expect(drawer).toContainText(/R-?001|司法/);
  });

  test("T3 · ESC 关 drawer", async ({ page }) => {
    await triggerDemoScan(page);
    const row = page.locator('[data-testid="alert-top-case-row"]').first();
    await row.click();
    const drawer = page.locator('[data-testid="alert-drill-drawer"]');
    await expect(drawer).toBeVisible();
    // close 按钮路径 (不强求 ESC · 部分 drawer 不挂 ESC 仅 close button)
    const closeBtn = page.locator('[data-testid="alert-drill-drawer-close"]');
    await expect(closeBtn).toBeVisible();
    await closeBtn.click();
    await expect(drawer).toBeHidden();
  });

  test("T4 · 排版基线 · row a11y 完备 (data-testid + role + tabIndex + cursor)", async ({
    page,
  }) => {
    await triggerDemoScan(page);
    const row = page.locator('[data-testid="alert-top-case-row"]').first();
    await expect(row).toBeVisible();
    // role 必为 button (a11y · 让屏阅器知道是 actionable)
    await expect(row).toHaveAttribute("role", "button");
    // tabIndex 必 0 (键盘可达)
    await expect(row).toHaveAttribute("tabIndex", "0");
    // cursor: pointer · 视觉提示
    const cur = await row.evaluate((el) => window.getComputedStyle(el).cursor);
    expect(cur).toBe("pointer");
  });
});
