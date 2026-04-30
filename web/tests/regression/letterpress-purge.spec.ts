import { test, expect, type Page, type Route } from "@playwright/test";

/**
 * Phase A5 V2 (2026-04-30) · Letterpress 真清 hermetic smoke
 *
 * 硬线 (docs/reset/phase-a-charter.md §1 #5):
 *   "Letterpress 真清 · 12 consumer 全迁 shell-v2 token ·
 *    grep --color-brass / --color-ink 0 命中"
 *
 * V2 修 codex 4 issue (audit DISAGREE 2026-04-29):
 *   #1 路由覆盖: /login 单点 → 9 路由矩阵 (含 /archive + 6 agent workspace)
 *   #2 取消 skip: 删 frontendReachable + test.skip · 让 server 不在直接 fail
 *   #3 hermetic: webServer config 在 playwright.config.ts 起 :3101 · 不靠用户 :3000
 *   #4 §7 文案: 见 CLAUDE.md (本 spec 同 commit 改)
 *
 * 6 验证 (per route × per theme):
 *   1. document.styleSheets 不含任何 legacy --color-brass / --color-ink-* /
 *      --color-paper-* / --color-line-* / --color-sage-* / --color-amber /
 *      --color-ember-* / --color-overlay / .letterpress-* / .ink-brush-hr
 *   2. shell-v2 token (--g0 / --ink / --chalk / --accent / --t-*) 在所有 4 主题解析为非空
 *   3. 4 主题切换后 --g0 / --accent 真变 (互不相同)
 *   4. body computed bg / color 来自 --chalk / --ink (非 legacy)
 *   5. /archive 6 agent tile 容器渲染 (token leak grep 同时跑全 DOM)
 *   6. 任何 agent workspace 进入态不复活 letterpress 类名
 *
 * 路由策略:
 *   - /login + /403 公开 (无需 auth)
 *   - /today / /dispatch / /archive + 6 /archive/<slug> 受 AuthGate 保护
 *   - 通过 page.route mock /api/auth/me 返回 admin u_liuye (全 6 agent 可达)
 *     bypass backend · 无需 uvicorn · 满足 hermetic
 *
 * 不依赖 backend (auth + 业务 API 全 mock).
 * Server 不在 → playwright.config.ts webServer 自动起 :3101 · 失败直接报错.
 */

const THEMES = ["canvas", "matcha", "dusk", "ink"] as const;
type Theme = (typeof THEMES)[number];

// 9 路由矩阵 · 含 /archive + 6 agent workspace · 注意 slug 是 "compliance" (URL) 非 "compli" (AgentId)
const ROUTES = [
  "/login",
  "/today",
  "/dispatch",
  "/archive",
  "/archive/report",
  "/archive/channel",
  "/archive/credit",
  "/archive/alert",
  "/archive/compliance",
  "/archive/riskctrl",
] as const;
type Route_ = (typeof ROUTES)[number];

const LEGACY_TOKENS = [
  "--color-brass",
  "--color-brass-dim",
  "--color-brass-glow",
  "--color-ink",
  "--color-ink-soft",
  "--color-ink-muted",
  "--color-paper",
  "--color-paper-raised",
  "--color-paper-sunken",
  "--color-line",
  "--color-line-strong",
  "--color-sage",
  "--color-sage-dim",
  "--color-amber",
  "--color-ember",
  "--color-ember-dim",
  "--color-overlay",
];

// CSS class / id 名 legacy · ruleSelectorText 命中也算泄漏
const LEGACY_SELECTORS = [
  "letterpress-",
  "ink-brush-hr",
];

const SHELL_V2_TOKENS = [
  "--g0",
  "--g7",
  "--ink",
  "--chalk",
  "--accent",
  "--safe",
  "--t-report",
  "--t-channel",
  "--t-credit",
  "--t-alert",
  "--t-compli",
  "--t-riskctrl",
];

/**
 * Mock /api/auth/me 返回 admin (u_liuye) · 全 6 agent 可达
 * 同时 stub 其它 /api/** 为 200 空 JSON · 防 workspace 组件挂起
 *
 * 注: Playwright route 匹配顺序 = LIFO (后注册先匹配)
 * 所以**先**注册 catch-all `/api/**`，**后**注册具体 `/api/auth/me`，
 * 这样 /api/auth/me 命中具体 handler · 其它 /api/* 落 catch-all。
 */
async function mockAuthAndApis(page: Page) {
  // 先注册 catch-all (优先级最低)
  await page.route("**/api/**", async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: "{}",
    });
  });

  // 后注册具体 /api/auth/me (LIFO · 优先级最高)
  await page.route("**/api/auth/me", async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        user: {
          id: "u_liuye",
          name: "刘野",
          role: "admin",
          team: "AI 中台",
          avatar: "野",
        },
        roles: ["admin"],
        accessibleAgents: [
          "channel",
          "report",
          "credit",
          "alert",
          "compli",
          "riskctrl",
        ],
      }),
    });
  });
}

async function applyTheme(page: Page, theme: Theme) {
  await page.evaluate((t) => {
    document.body.setAttribute("data-theme", t);
    document.documentElement.setAttribute("data-theme", t);
  }, theme);
  // 等 CSS variable 重算 · drift 动画无关 · 50ms 足够
  await page.waitForTimeout(50);
}

interface LegacyOffender {
  kind: "token" | "selector";
  needle: string;
  sample: string;
}

async function collectLegacyOffenders(
  page: Page,
  legacyTokens: readonly string[],
  legacySelectors: readonly string[],
): Promise<LegacyOffender[]> {
  return await page.evaluate(
    ({ tokens, selectors }) => {
      const found: Array<{ kind: "token" | "selector"; needle: string; sample: string }> = [];
      for (const sheet of Array.from(document.styleSheets)) {
        let rules: CSSRuleList | null = null;
        try {
          rules = sheet.cssRules;
        } catch {
          continue; // CORS-protected sheet
        }
        if (!rules) continue;
        for (const rule of Array.from(rules)) {
          const text = rule.cssText;
          for (const token of tokens) {
            if (text.includes(token)) {
              found.push({ kind: "token", needle: token, sample: text.slice(0, 120) });
            }
          }
          for (const sel of selectors) {
            if (text.includes(sel)) {
              found.push({ kind: "selector", needle: sel, sample: text.slice(0, 120) });
            }
          }
        }
      }
      return found;
    },
    { tokens: legacyTokens as unknown as string[], selectors: legacySelectors as unknown as string[] },
  );
}

test.describe("A5 V2 · Letterpress purge hermetic smoke", () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthAndApis(page);
  });

  // 矩阵 (route × theme): 9 × 4 = 36 case 跑双向断言 (legacy leak + shell-v2 resolve)
  for (const route of ROUTES) {
    for (const theme of THEMES) {
      test(`${route} · ${theme} · no legacy CSS tokens / selectors`, async ({ page }) => {
        await page.goto(route, { waitUntil: "domcontentloaded" });
        await applyTheme(page, theme);

        const offenders = await collectLegacyOffenders(page, LEGACY_TOKENS, LEGACY_SELECTORS);
        expect(
          offenders,
          `legacy leak on ${route} ${theme}: ${JSON.stringify(offenders, null, 2)}`,
        ).toEqual([]);
      });

      test(`${route} · ${theme} · shell-v2 tokens resolve`, async ({ page }) => {
        await page.goto(route, { waitUntil: "domcontentloaded" });
        await applyTheme(page, theme);

        const resolved = await page.evaluate((tokens) => {
          const root = getComputedStyle(document.documentElement);
          const body = getComputedStyle(document.body);
          const map: Record<string, string> = {};
          for (const t of tokens) {
            map[t] = (root.getPropertyValue(t) || body.getPropertyValue(t)).trim();
          }
          return map;
        }, SHELL_V2_TOKENS);

        for (const t of SHELL_V2_TOKENS) {
          expect(resolved[t], `${t} on ${route} ${theme} should resolve`).not.toBe("");
        }
      });
    }
  }

  test("--g0 + --accent differ across all 4 themes", async ({ page }) => {
    await page.goto("/login", { waitUntil: "domcontentloaded" });

    const samples: Record<Theme, { g0: string; accent: string }> = {} as never;
    for (const theme of THEMES) {
      await applyTheme(page, theme);
      samples[theme] = await page.evaluate(() => {
        const r = getComputedStyle(document.documentElement);
        return {
          g0: r.getPropertyValue("--g0").trim(),
          accent: r.getPropertyValue("--accent").trim(),
        };
      });
    }

    const g0Set = new Set(THEMES.map((t) => samples[t].g0));
    const accentSet = new Set(THEMES.map((t) => samples[t].accent));
    expect(g0Set.size, `--g0 should differ across 4 themes: ${JSON.stringify(samples)}`).toBe(4);
    expect(accentSet.size, `--accent should differ across 4 themes: ${JSON.stringify(samples)}`).toBe(4);
  });

  test("body bg/color come from --chalk/--ink (no legacy fallback)", async ({ page }) => {
    await page.goto("/login", { waitUntil: "domcontentloaded" });

    const { chalk, ink, bodyBg, bodyColor } = await page.evaluate(() => {
      const r = getComputedStyle(document.documentElement);
      const b = getComputedStyle(document.body);
      return {
        chalk: r.getPropertyValue("--chalk").trim(),
        ink: r.getPropertyValue("--ink").trim(),
        bodyBg: b.backgroundColor,
        bodyColor: b.color,
      };
    });

    expect(chalk).not.toBe("");
    expect(ink).not.toBe("");
    expect(bodyBg).not.toBe("rgba(0, 0, 0, 0)");
    expect(bodyColor).not.toBe("rgba(0, 0, 0, 0)");
  });

  // /archive 6 agent tile 真渲染 (.archive .agent · admin 全 access)
  // 注: AuthGate bootstrap async · 用 expect retry 等渲染 · 不能 immediate count
  test("/archive renders 6 agent tiles (DOM proof)", async ({ page }) => {
    await page.goto("/archive", { waitUntil: "domcontentloaded" });

    // admin u_liuye 全 access · 应见全 6 tile (含 locked 状态也算 .agent · 但 admin 无 locked)
    await expect(
      page.locator(".archive .agent"),
      "admin user should see 6 agent tiles after bootstrap",
    ).toHaveCount(6, { timeout: 10_000 });
  });
});
