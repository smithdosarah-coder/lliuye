import { test, expect, type Route } from "@playwright/test";

/**
 * B.3.4 fix-indep · 主活 A · alert idle 空白填实
 * (PM 2026-05-11 06:30 GO · KT R7 brutal 排序 · 凌晨 06:00 截图直接痛 #4)
 *
 * 真因:
 *   - PM 截图: started=yes 后 (队列出来) · 中间 + 右下 "大空白"
 *   - 现 alert-mid-placeholder (AlertWorkspace.tsx:959) 只一行文字 ·
 *     "等待扫描启动 · 启动后从下方红/黄/绿榜单选中客户查看处置建议"
 *   - 占满整个 mid 列空白 = 演示翻车
 *
 * 修法 (本 spec 验):
 *   1. started=yes && !selectedClientId 时 · mid 列必有 ≥ 2 个占位卡 (引导 + 概览 + Top)
 *   2. mid 列不能只是单行文字 (textContent length > 80 chars · 实质内容)
 *   3. right 列底部 (OutputPanel 之外 · TrafficLightWall 之上) 必有 next-step hint area
 *   4. started=no idle (AlertEmptyState) 已富 · 仅 sanity 验关键 testid 在
 *
 * Auth bypass: localStorage seed admin 角色 (alert.invoke 权限).
 *
 * TDD red-to-green: 本 spec commit 时 红 (AlertWorkspace 未改) ·
 * 主活 A-2 实现 commit 后 绿.
 */

const SEED_AUTH_ADMIN = JSON.stringify({
  state: {
    currentUser: {
      id: "u_admin",
      name: "管理员",
      role: "admin",
      team: "总行 · 风险中台",
      avatar: "管",
    },
  },
  version: 0,
});

test.beforeEach(async ({ context }) => {
  await context.addInitScript((seed) => {
    window.localStorage.setItem("platform.auth.v1", seed);
  }, SEED_AUTH_ADMIN);
});

/**
 * Build SSE done envelope for /api/alert/demo/run · 1 stage + 1 done event.
 * topCases 含 3 户 · 让 idle filled 状态有真数据 ground.
 */
function buildSseDone(): string {
  const stage = {
    event: "stage",
    stage: "summary",
    status: "done",
    message: "扫描完成",
  };
  const done = {
    event: "done",
    session_id: "alert-idle-fill-test-001",
    mode: "web_live",
    data_source: "live",
    panels: {
      hit_list: { red: [], yellow: [], green: [] },
      top_cases: [
        {
          client_id: "AP001",
          name: "示例客户 001 · 红档",
          tier: "red",
          score: 0.91,
          industry: "制造",
          rationale: "司法 + 舆情双源命中",
        },
        {
          client_id: "AP002",
          name: "示例客户 002 · 黄档",
          tier: "yellow",
          score: 0.62,
          industry: "批零",
          rationale: "工商变更 + 内部限额预警",
        },
      ],
      dispositions: {},
    },
    metrics: { red: 6, yellow: 14, green: 160, total_scanned: 180 },
    summary: "演示运行 · 6 红 / 14 黄 / 160 绿",
    scenario_key: "alert-pool",
    kb_state: "3 项联机中",
    totals: { red: 6, yellow: 14, green: 160 },
    industry_distribution: [
      { industry: "制造", total: 60, red: 3, yellow: 5, green: 52 },
      { industry: "批零", total: 40, red: 2, yellow: 4, green: 34 },
    ],
    signal_heatmap: [],
    reach_rate: [
      { tier: "red", reachedPct: 80.0 },
      { tier: "yellow", reachedPct: 45.0 },
    ],
    ledger_entries_written: 6,
  };
  return [
    `data: ${JSON.stringify(stage)}\n\n`,
    `data: ${JSON.stringify(done)}\n\n`,
  ].join("");
}

test.describe("B.3.4 fix-indep · 主活A · alert idle 空白填实", () => {
  test("sanity · started=no idle (AlertEmptyState) 关键 testid 在 (确保未回退)", async ({
    page,
  }) => {
    await page.goto("/archive/alert", { waitUntil: "networkidle" });

    const root = page.locator('[data-testid="alert-workspace"]');
    await expect(root).toBeVisible();
    await expect(root).toHaveAttribute("data-alert-started", "no");

    // 已富 placeholder 不能被回退
    await expect(page.locator('[data-testid="alert-empty-skeleton"]')).toBeVisible();
    await expect(page.locator('[data-testid="alert-empty-skeleton-panels"]')).toBeVisible();
    await expect(page.locator('[data-testid="alert-scan-cta"]')).toBeVisible();
    await expect(page.locator('[data-testid="alert-scan-cta-secondary"]')).toBeVisible();
  });

  test("RED · started=yes && !selectedClientId · mid 列必有 ≥ 2 个占位卡 (现仅 1 行文字 · 修前 fail)", async ({
    page,
  }) => {
    await page.route("**/api/alert/demo/run", async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: buildSseDone(),
      });
    });

    await page.goto("/archive/alert", { waitUntil: "networkidle" });

    // 切 demo 触发扫描 → started=yes
    await page.locator('[data-testid="alert-input-mode-demo"]').click();
    await page.locator('[data-testid="alert-scan-cta"]').click();

    const root = page.locator('[data-testid="alert-workspace"]');
    await expect(root).toHaveAttribute("data-alert-started", "yes", { timeout: 8000 });

    // 核心断言 1 · mid 列 idle overview 容器在
    const midOverview = page.locator('[data-testid="alert-idle-mid-overview"]');
    await expect(midOverview).toBeVisible();

    // 核心断言 2 · mid 列 ≥ 2 个 idle 卡片
    const midCards = page.locator('[data-testid="alert-idle-mid-card"]');
    await expect(midCards).toHaveCount(3);

    // 核心断言 3 · mid 列实质文本长度 > 120 chars (不只是一行 hint)
    const midText = (await midOverview.innerText()).replace(/\s+/g, "");
    expect(midText.length).toBeGreaterThan(120);
  });

  test("RED · started=yes && !selectedClientId · right-bottom next-step hint area 必在 (现无 · 修前 fail)", async ({
    page,
  }) => {
    await page.route("**/api/alert/demo/run", async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: buildSseDone(),
      });
    });

    await page.goto("/archive/alert", { waitUntil: "networkidle" });
    await page.locator('[data-testid="alert-input-mode-demo"]').click();
    await page.locator('[data-testid="alert-scan-cta"]').click();

    const root = page.locator('[data-testid="alert-workspace"]');
    await expect(root).toHaveAttribute("data-alert-started", "yes", { timeout: 8000 });

    // 核心断言 · 右下 next-step hint 容器在 (引导用户点榜单 + 列下一步动作)
    const rbHint = page.locator('[data-testid="alert-idle-rb-hint"]');
    await expect(rbHint).toBeVisible();

    // 至少含 "选中客户" 这类 drill 引导文案
    await expect(rbHint).toContainText(/选中|榜单|点击|drill/i);
  });

  test("RED · idle filled overview 含全池 totals 数字 (red/yellow/green) · 不留白", async ({
    page,
  }) => {
    await page.route("**/api/alert/demo/run", async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: buildSseDone(),
      });
    });

    await page.goto("/archive/alert", { waitUntil: "networkidle" });
    await page.locator('[data-testid="alert-input-mode-demo"]').click();
    await page.locator('[data-testid="alert-scan-cta"]').click();

    const root = page.locator('[data-testid="alert-workspace"]');
    await expect(root).toHaveAttribute("data-alert-started", "yes", { timeout: 8000 });

    const midOverview = page.locator('[data-testid="alert-idle-mid-overview"]');
    // 全池 6 红 14 黄 160 绿 三个数字必出现 · 不让 mid 留白
    await expect(midOverview).toContainText("6");
    await expect(midOverview).toContainText("14");
    await expect(midOverview).toContainText("160");
  });
});
