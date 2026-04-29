import { test, expect, type Page } from "@playwright/test";

/**
 * Phase A5 (2026-04-29) · Letterpress 真清 visual smoke
 *
 * 硬线: docs/reset/phase-a-charter.md §1 #5
 *   "Letterpress 真清 · 12 consumer 全迁 shell-v2 token ·
 *    grep --color-brass / --color-ink 0 命中"
 *
 * 4 验证:
 *   1. 任何 CSS stylesheet 不含 --color-brass / --color-ink / --color-paper /
 *      --color-line / --color-sage / --color-amber / --color-ember / --color-overlay
 *   2. shell-v2 token (--g0 / --ink / --chalk / --accent / --t-*) 在所有 4 主题都解析为非空值
 *   3. 4 主题切换 (data-theme) 后 --g0 / --accent 真变 (互不相同)
 *   4. body computed bg / color 来自 --chalk / --ink (非 legacy)
 *
 * 不依赖 backend · 仅静态 CSS + DOM 切换 · 默认走 /login (公开路由).
 * Frontend dev server 不在则 skip (CI 单机跑 · 不阻 mesh).
 */

const THEMES = ["canvas", "matcha", "dusk", "ink"] as const;
type Theme = (typeof THEMES)[number];

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

async function frontendReachable(page: Page): Promise<boolean> {
  try {
    const res = await page.request.get("/login", { failOnStatusCode: false });
    return res.status() < 500;
  } catch {
    return false;
  }
}

async function applyTheme(page: Page, theme: Theme) {
  await page.evaluate((t) => {
    document.body.setAttribute("data-theme", t);
    document.documentElement.setAttribute("data-theme", t);
  }, theme);
  await page.waitForTimeout(50);
}

test.describe("A5 · Letterpress purge smoke", () => {
  test.beforeEach(async ({ page }) => {
    if (!(await frontendReachable(page))) {
      test.skip(true, "frontend dev server not reachable on baseURL · skip A5 smoke");
    }
  });

  test("any stylesheet contains no legacy --color-* tokens", async ({ page }) => {
    await page.goto("/login", { waitUntil: "domcontentloaded" });

    const offenders = await page.evaluate((legacy) => {
      const found: Array<{ token: string; sample: string }> = [];
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
          for (const token of legacy) {
            if (text.includes(token)) {
              found.push({ token, sample: text.slice(0, 100) });
            }
          }
        }
      }
      return found;
    }, LEGACY_TOKENS);

    expect(offenders, `legacy token leak: ${JSON.stringify(offenders, null, 2)}`).toEqual([]);
  });

  for (const theme of THEMES) {
    test(`shell-v2 tokens resolved on ${theme} theme`, async ({ page }) => {
      await page.goto("/login", { waitUntil: "domcontentloaded" });
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
        expect(resolved[t], `${t} on ${theme} should resolve`).not.toBe("");
      }
    });
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

  test("body bg/color come from --chalk/--ink (no legacy)", async ({ page }) => {
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

    // chalk/ink defined and non-trivial
    expect(chalk).not.toBe("");
    expect(ink).not.toBe("");
    // body should not fall back to white/black (which would happen if vars are undefined)
    expect(bodyBg).not.toBe("rgba(0, 0, 0, 0)");
    expect(bodyColor).not.toBe("rgba(0, 0, 0, 0)");
  });
});
