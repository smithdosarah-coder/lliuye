import { test, expect } from "@playwright/test";

/**
 * F-041 · Channel multi-session mock switch (master plan §B.1+§B.2)
 *
 * 验证：选下拉切 session · 全 5 panel 跟着切 (RadarPanel / FunnelStrip /
 * CandidatesPanel / SignalTimelinePanel / Hero benchmarkName)
 *
 * Mock 默认 session = sess_haichao (上海海潮工业软件)
 * 切到 sess_zhirong (苏州智荣精密制造) · 验:
 *   - hero benchmark 文字变 (Hero sub)
 *   - candidate 第 1 家 name 变 (杭州智云 → 无锡精弘)
 *   - signal timeline 主 candidate name 变
 *   - funnel 顶部 "信号池" count 变 (3,780 → 4,860)
 *
 * Spec 强制 trigger started=true 走点 select (而非 textbox · textbox 真接 SSE)
 *
 * Auth bypass: localStorage seed `platform.auth.v1` (Zustand persist key) 模拟王哲已登录
 *   王哲 role=rm · ACCESS=[channel, report, credit, alert, compli, riskctrl] 全开
 */

const SEED_AUTH = JSON.stringify({
  state: {
    currentUser: {
      id: "u_wangzhe",
      name: "王哲",
      role: "rm",
      team: "华东·上海第一支行",
      avatar: "哲",
    },
  },
  version: 0,
});

test.beforeEach(async ({ page, context }) => {
  // 通过 init script 在第一次 navigate 前 seed localStorage · 避免 AuthGate
  // 在 /login 路径上首挂 ref 触发 logout 把 seed 清掉。Init script 会在每次 frame 创建前跑。
  await context.addInitScript((seed) => {
    window.localStorage.setItem("platform.auth.v1", seed);
  }, SEED_AUTH);
});

test.describe("F-041 · Channel mock_sessions multi-pattern session select", () => {
  test("default session render hero + 5 panels with sess_haichao data", async ({
    page,
  }) => {
    await page.goto("/archive/channel", { waitUntil: "networkidle" });

    // Workspace 默认 started=false · 通过点 session select 触发 started=true
    const sessionSelect = page.locator('[data-testid="channel-session-select"]');
    await expect(sessionSelect).toBeVisible();

    // 默认 selectedSessionId = DEFAULT_SESSION_ID = sess_haichao
    await expect(sessionSelect).toHaveValue("sess_haichao");

    // 5 sessions 都在下拉选项里
    const optionCount = await page
      .locator('[data-testid="channel-session-option"]')
      .count();
    expect(optionCount).toBe(5);

    // 触发 started=true 走 sess_haichao mock 视图
    await sessionSelect.selectOption("sess_haichao");
    await page.waitForTimeout(300);

    // Hero sub 显示 sess_haichao 标杆名
    const heroSub = page.locator(".rpt-hero-sub").first();
    await expect(heroSub).toContainText(/海潮|SaaS B/);
  });

  test("switch session sess_zhirong refreshes all 5 panels", async ({ page }) => {
    await page.goto("/archive/channel", { waitUntil: "networkidle" });

    const sessionSelect = page.locator('[data-testid="channel-session-select"]');

    // 第一步：先切到 default session 让 started=true
    await sessionSelect.selectOption("sess_haichao");
    await page.waitForTimeout(300);

    // 默认状态记录 candidate 第 1 家 name
    const firstCandHaichao = await page
      .locator(".ch-cd-name")
      .first()
      .textContent();
    expect(firstCandHaichao).toContain("杭州智云");

    // 切到 sess_zhirong (苏州智荣精密制造)
    await sessionSelect.selectOption("sess_zhirong");
    await page.waitForTimeout(300);

    // (1) Hero benchmark 文字应变化 (sess_haichao 海潮 → sess_zhirong 智荣)
    const heroSub = page.locator(".rpt-hero-sub").first();
    await expect(heroSub).toContainText(/智荣|智能制造|A 轮/);

    // (2) Candidates 第 1 家 name 变 (杭州智云 → 无锡精弘)
    const firstCandZhirong = await page
      .locator(".ch-cd-name")
      .first()
      .textContent();
    expect(firstCandZhirong).toContain("无锡精弘");

    // (3) Signal Timeline 顶部 panel title 也跟着切到 sess_zhirong 第一个 candidate
    const timelineTitle = page
      .locator(".ch-tl-panel .rpt-panel-title")
      .first();
    await expect(timelineTitle).toContainText("无锡精弘");

    // (4) Funnel 顶部 "信号池" count 变 (3,780 → 4,860)
    const funnelFirstCount = page
      .locator(".ch-funnel-strip-cell .ch-funnel-strip-count")
      .first();
    await expect(funnelFirstCount).toContainText("4,860");

    // (5) Radar panel title (该候选 + P50 对标)
    const radarTitle = page.locator(".ch-radar-panel .rpt-panel-title");
    await expect(radarTitle).toContainText(/无锡精弘|P50/);
  });

  test("switch to sess_kangyuan (early-stage biotech) shows minimal funnel", async ({
    page,
  }) => {
    await page.goto("/archive/channel", { waitUntil: "networkidle" });

    const sessionSelect = page.locator('[data-testid="channel-session-select"]');

    // start
    await sessionSelect.selectOption("sess_haichao");
    await page.waitForTimeout(200);

    // 切到 sess_kangyuan (创新药 Pre-A · Top 12 候选 · 池子小是正常 · 极端档)
    await sessionSelect.selectOption("sess_kangyuan");
    await page.waitForTimeout(300);

    // Hero 显示 12 家候选 (而非 sess_haichao 的 35 家)
    const heroSub = page.locator(".rpt-hero-sub").first();
    await expect(heroSub).toContainText("12 家候选");

    // 第 1 候选应是 "上海源辰生物医药"
    const firstCand = await page.locator(".ch-cd-name").first().textContent();
    expect(firstCand).toContain("上海源辰");
  });
});
