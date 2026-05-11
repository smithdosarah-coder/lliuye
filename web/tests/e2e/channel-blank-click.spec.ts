import { test, expect, type Page, type Route } from "@playwright/test";

/**
 * B.3.4 · fix-bugs Bug A · channel 点空白触发搜索 (TDD red-to-green)
 *
 * PM 痛 (5/11 凌晨): 获客 (channel): 点击空白页也会跳转出查询
 *
 * 契约 (KT R2 TDD · 此 spec 是安全网):
 *   T1 · 点 hero badge → NOT 触发 search (无 SSE event)
 *   T2 · 点 Stat label / Stat value → NOT 触发 search
 *   T3 · 点 hero 空白条 (header 内非按钮区) → NOT 触发 search
 *   T4 · 点 empty-state section 背景 (非 chip 按钮) → NOT 触发 search
 *   T5 · 输入框 内点 Enter → 触发 search (这是允许的真路径 · 用 ⌘/Ctrl+Enter 也可)
 *
 * 反模式禁忌 (per prompt "不可 GO"):
 *   - 不靠 onClick stopPropagation 修 (那只 mask 现象 · 真因可能是全局 keydown / autoFocus)
 *   - 真因排查路径: input/textarea autofocus + 全局 keydown handler
 *
 * Auth bypass per 既有 spec 习惯 · channel-pilot-4gate.spec.ts pattern
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
  accessibleAgents: ["channel", "report", "credit", "alert", "compli", "riskctrl"],
};

/** Track every SSE-bearing endpoint call · 任何一次命中 = 误触发搜索 */
function attachSseSentinel(page: Page): { hits: () => number; reset: () => void } {
  let n = 0;
  page.on("request", (req) => {
    const url = req.url();
    if (url.includes("/api/channel/run") || url.includes("/api/channel/demo/run")) {
      n += 1;
    }
  });
  return {
    hits: () => n,
    reset: () => {
      n = 0;
    },
  };
}

test.beforeEach(async ({ context }) => {
  await context.route("**/api/auth/me", async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_ME_RESPONSE),
    });
  });

  // 拦 SSE endpoint 全部返 empty done · 即便不小心触发也不挂网络
  const stubSse = async (route: Route) => {
    const body =
      `event: done\ndata: ${JSON.stringify({
        event: "done",
        data_source: "live",
        session_id: "blank-click-stub",
        metrics: { signalTotal: 0, companiesFound: 0, final: 0 },
        candidates: [],
        radar: [],
        signals: [],
        funnel: [],
        match_dimensions: [],
        product_recommendations: [],
        pitch_scripts: [],
        conversation: [],
      })}\n\n`;
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body,
    });
  };
  await context.route("**/api/channel/run", stubSse);
  await context.route("**/api/channel/demo/run", stubSse);
});

test.describe("B.3.4 Bug A · channel 空白点击不触发搜索 (TDD red-to-green)", () => {
  test("T1 · 点 hero badge · NOT 触发 /api/channel/run|demo/run", async ({ page }) => {
    const sentinel = attachSseSentinel(page);
    await page.goto("/archive/channel", { waitUntil: "networkidle" });

    // 等 hero 渲完
    const badge = page.locator(".rpt-hero-badge").first();
    await expect(badge).toBeVisible();

    sentinel.reset();
    await badge.click();
    // 给 React event loop 100ms · 任何异步 SSE fetch 都已触发
    await page.waitForTimeout(200);

    expect(sentinel.hits()).toBe(0);
  });

  test("T2 · 点 Stat label + Stat value · NOT 触发 search", async ({ page }) => {
    const sentinel = attachSseSentinel(page);
    await page.goto("/archive/channel", { waitUntil: "networkidle" });

    const statLabel = page.locator(".rpt-stat-label").first();
    const statValue = page.locator(".rpt-stat-value").first();
    await expect(statLabel).toBeVisible();
    await expect(statValue).toBeVisible();

    sentinel.reset();
    await statLabel.click();
    await page.waitForTimeout(150);
    await statValue.click();
    await page.waitForTimeout(150);

    expect(sentinel.hits()).toBe(0);
  });

  test("T3 · 点 hero 区域非按钮空白条 · NOT 触发 search", async ({ page }) => {
    const sentinel = attachSseSentinel(page);
    await page.goto("/archive/channel", { waitUntil: "networkidle" });

    const hero = page.locator(".rpt-hero").first();
    await expect(hero).toBeVisible();

    sentinel.reset();
    // 取 hero 外框边缘 · gap 之间 · 不在任何 button 内
    const box = await hero.boundingBox();
    if (!box) throw new Error("hero bbox 不可读");
    // 中下沿 · 在两栏 gap 之间
    await page.mouse.click(box.x + box.width / 2, box.y + box.height - 4);
    await page.waitForTimeout(200);

    expect(sentinel.hits()).toBe(0);
  });

  test("T4 · 点 empty-state section 背景 (非 chip 按钮) · NOT 触发 search", async ({ page }) => {
    const sentinel = attachSseSentinel(page);
    await page.goto("/archive/channel", { waitUntil: "networkidle" });

    const empty = page.locator('[data-testid="channel-empty-state"]');
    await expect(empty).toBeVisible();

    sentinel.reset();
    // 取 empty-state 左下角内边距区 (非 chip 按钮坐标)
    const box = await empty.boundingBox();
    if (!box) throw new Error("empty-state bbox 不可读");
    await page.mouse.click(box.x + 6, box.y + box.height - 6);
    await page.waitForTimeout(200);

    expect(sentinel.hits()).toBe(0);
  });

  test("T5 · 输入框 内 Enter / ⌘+Enter · 触发 /api/channel/run (允许真路径)", async ({ page }) => {
    const sentinel = attachSseSentinel(page);
    await page.goto("/archive/channel", { waitUntil: "networkidle" });

    const input = page.locator(".ch-querybar-input");
    await expect(input).toBeVisible();

    sentinel.reset();
    await input.fill("blank-click TDD · enter triggers search");
    // 现行 onKeyDown 走 ⌘/Ctrl+Enter · 用 Control+Enter 跨 OS · 防 macOS 上是 Meta key
    await input.press("Control+Enter");
    // SSE fetch 是异步 · 给 fetch dispatch + route handler 充足时间
    await page.waitForTimeout(500);

    expect(sentinel.hits()).toBeGreaterThanOrEqual(1);
  });
});
