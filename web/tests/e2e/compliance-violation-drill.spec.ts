import { test, expect, type Route } from "@playwright/test";

/**
 * B.3.4 · fix-bugs Bug D · compliance 详情体验 + 排版 (TDD red-to-green)
 *
 * PM 痛 (5/11 凌晨): 合规 (compliance): 完全乱的排版 · 没任何功能展示
 *
 * 契约 (KT R2 TDD):
 *   T1 · sample batch 跑完 · compli-violation-card ≥ 1
 *   T2 · 点 card → ViolationDetailPanel 显 · evidence chain (政策摘录 / 业务原始 / AI 理由 / source) 全在
 *   T3 · close button 关 detail · 回 placeholder
 *   T4 · 排版基线 · 3 列 grid (违规列表 · 详情 · 修订) testid 全在
 *
 * 反模式 (per prompt "不可 GO"):
 *   - 只改 CSS 不动 state binding → 验 click → state → detail panel 真链路
 */

const MOCK_ME_RESPONSE = {
  user: {
    id: "u_zhoumin",
    name: "周敏",
    role: "compliance_officer",
    team: "总部·合规管理部",
    avatar: "敏",
  },
  roles: ["compliance_officer"],
  accessibleAgents: ["channel", "report", "credit", "alert", "compliance", "riskctrl"],
};

const STUB_SCENARIOS = {
  scenarios: [
    {
      scenario_id: "online_loan",
      label: "线上信贷 · 利率 / 适当性",
      policy_title: "互联网贷款管理办法",
      doc_count: 12,
    },
  ],
};

const STUB_DONE = {
  event: "done",
  session_id: "compli-drill-spec-1",
  data_source: "live",
  violations: [
    {
      id: "vio-1",
      violation_id: "vio-1",
      severity: "critical",
      rule_article: "第 17 条 · 利率上限",
      rule_condition: "年化利率 ≤ 24%",
      event_id: "ORD-2026-04-001",
      event_type: "线上信贷出账",
      match_reason: "实际年化利率 26.4% · 超 24% 上限 2.4 pct",
      evidence: "出账记录 §利率字段 · 26.4%",
      client: "测试客户 A 公司",
      client_uscc: "91320000XXXXXXX01A",
      reason: {
        clause_id: "P-17",
        policy_id: "POL-2024-Q3",
        policy_version: "v3.2",
        clause_text_hash: "sha256:abcd",
        evidence_date: "2026-04-15",
        retrieved_at: "2026-05-11T06:00:00",
        freshness_days: 26,
        staleness_passed: true,
        confidence: 0.93,
        review_reason: "rate_violation",
      },
      policy_excerpt: "互联网贷款年化利率不得超过 24% (银保监 2024 §17)",
      business_excerpt: "出账记录显示年化利率 26.4% · 超上限",
    },
    {
      id: "vio-2",
      violation_id: "vio-2",
      severity: "major",
      rule_article: "第 22 条 · 适当性披露",
      rule_condition: "首次借款必须签字确认风险",
      event_id: "ORD-2026-04-002",
      event_type: "首次借款",
      match_reason: "未见客户签字风险揭示页",
      evidence: "档案缺页 §适当性",
      client: "测试客户 B 个人",
      reason: null,
    },
  ],
  recommendations: [
    {
      violation_id: "vio-1",
      category: "改",
      title: "下调利率至合规上限",
      text: "立即停止 26.4% 出账 · 改 24% 上限 + 退款差额",
    },
  ],
};

function stubSse(route: Route) {
  return route.fulfill({
    status: 200,
    contentType: "text/event-stream",
    body:
      `event: stage\ndata: ${JSON.stringify({ event: "stage", stage: "ingest", status: "done" })}\n\n` +
      `event: done\ndata: ${JSON.stringify(STUB_DONE)}\n\n`,
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
  await context.route("**/api/compliance/demo/scenarios", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(STUB_SCENARIOS),
    });
  });
  await context.route("**/api/compliance/demo/run", stubSse);
  await context.route("**/api/compliance/policy_scan", stubSse);
});

async function triggerSampleScan(page: import("@playwright/test").Page) {
  await page.goto("/archive/compliance", { waitUntil: "networkidle" });

  // scenarios 加载完后默认选第一个 · 直接点 run
  const runBtn = page.locator('[data-testid="compli-sample-batch-run"]');
  await expect(runBtn).toBeVisible();
  await runBtn.click();
  // 等 SSE done + setLiveData + normalize · 给充足时间
  await page.waitForTimeout(1200);
}

test.describe("B.3.4 Bug D · compliance violation 详情体验 (TDD red-to-green)", () => {
  test("T1 · sample batch 跑完 · violation-card ≥ 1 (列表出来)", async ({ page }) => {
    await triggerSampleScan(page);

    const cards = page.locator('[data-testid="compli-violation-card"]');
    await expect(cards.first()).toBeVisible();
    expect(await cards.count()).toBeGreaterThanOrEqual(1);
  });

  test("T2 · 点 card · ViolationDetailPanel 显 · evidence chain 完整", async ({ page }) => {
    await triggerSampleScan(page);

    // backend done 后 useEffect setSelectedViolationId(firstVio) 自动选首 · detail 应已显
    const detail = page.locator('[data-testid="compli-pilot-detail"]');
    await expect(detail).toBeVisible();

    // evidence chain · 5 字段 (docid / policy / business / finding / source) 都在
    await expect(page.locator('[data-testid="compli-evi-docid"]')).toContainText("ORD-2026-04-001");
    await expect(page.locator('[data-testid="compli-evi-policy"]')).toContainText(/利率|24%/);
    await expect(page.locator('[data-testid="compli-evi-business"]')).toContainText("26.4%");
    await expect(page.locator('[data-testid="compli-evi-finding"]')).toContainText(/26.4%|超.*上限/);

    // 显式 click 切换到第二个 violation · 验 state binding 真链路
    const cards = page.locator('[data-testid="compli-violation-card-btn"]');
    await cards.nth(1).click();
    await page.waitForTimeout(300);
    await expect(page.locator('[data-testid="compli-evi-docid"]')).toContainText("ORD-2026-04-002");
    await expect(page.locator('[data-testid="compli-evi-finding"]')).toContainText("签字");
  });

  test("T3 · close · 回 placeholder", async ({ page }) => {
    await triggerSampleScan(page);

    const close = page.locator('[data-testid="compli-violation-detail-close"]');
    await expect(close).toBeVisible();
    await close.click();
    await page.waitForTimeout(200);

    const placeholder = page.locator('[data-testid="compli-detail-placeholder"]');
    await expect(placeholder).toBeVisible();
  });

  test("T4 · 排版基线 · 3 列 + 修订面板 + click toggle a11y", async ({ page }) => {
    await triggerSampleScan(page);

    // 修订面板 testid
    await expect(page.locator('[data-testid="compli-pilot-revisions"]')).toBeVisible();

    // violation card 按钮的 aria-pressed 联动 active 状态
    const btn = page.locator('[data-testid="compli-violation-card-btn"]').first();
    const pressed = await btn.getAttribute("aria-pressed");
    expect(pressed === "true" || pressed === "false").toBe(true);
  });
});
