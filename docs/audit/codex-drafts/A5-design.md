## 1. 12 consumer migration table

Round-2 schema: **改** = 12 点逐点迁 shell-v2；**坚持** = `grep -- --color-brass --color-ink` 必须 0；**对方弱点** = 只按 Cat 14 改 12 点会漏掉同文件后续 legacy；**吸收对方** = 先锁 audit 12 点，再用 grep 扩展清零；**v2 final** = 下表为最小必迁清单，0-grep 为验收门。

| # | consumer file:line | old token | new token | risk |
|---|---|---|---|---|
| 1 | `web/src/lib/agents.ts:47` | `var(--color-ink)` | `var(--t-report)` | Agent tile/report accent 变更，需比对 Archive tile |
| 2 | `web/src/lib/agents.ts:60` | `var(--color-brass)` | `var(--t-channel)` | Scout/channel 色相从金色归青绿 |
| 3 | `web/src/lib/agents.ts:75` | `var(--color-sage)` | `var(--t-credit)` | Cat 8 legacy，虽然不是 brass/ink，也必须迁 |
| 4 | `web/src/lib/agents.ts:88` | `var(--color-amber)` | `var(--t-riskctrl)` | 风控 purple 功能色替代 amber |
| 5 | `web/src/lib/agents.ts:101` | `var(--color-ember)` | `var(--t-alert)` | alert 仍保持红系，但用 shell token |
| 6 | `web/src/lib/agents.ts:114` | `var(--color-brass-dim)` | `var(--t-compli)` | compliance/compli 命名需不扩大到 A1 范围 |
| 7 | `web/src/components/viz/VerdictBadge.tsx:12` | `var(--color-brass)` | `var(--accent)` | “有条件批准”语义用主题 accent，非 agent 色 |
| 8 | `web/src/components/viz/VerdictBadge.tsx:27` | `var(--color-ink)` | `var(--ink)` | grade block 深底需保证 ink theme 对比 |
| 9 | `web/src/components/viz/VerdictBadge.tsx:45` | `bg-[var(--color-ink)] text-[var(--color-brass-glow)]` | `bg-[var(--ink)] text-[var(--chalk)]` | ribbon 可读性，不保留 glow |
| 10 | `web/src/components/viz/PipelineRail.tsx:42` | `text-[var(--color-ink)]` | `text-[var(--ink)]` | done label 对比 |
| 11 | `web/src/components/viz/PipelineRail.tsx:43` | `text-[var(--color-ink)]` | `text-[var(--ink)]` | active label 对比 |
| 12 | `web/src/components/viz/PipelineRail.tsx:44` | `text-[var(--color-ink-muted)]` | `text-[var(--ink-48)]` | pending muted 不能灰到不可读 |

Cites: Cat 14 lists these 12 under `docs/audit/conflict-register-v1.md:220-222`; Cat 8 names the six agent accent rewrites at `docs/audit/sub-agent-step2-round1/naming-route.md:13-18`; shell-v2 legal functional colors are in `web/src/app/tokens.css:69-74` and `CLAUDE.md:129-132`.

## 2. globals.css legacy 删除时机 + 删除内容 verbatim

删除时机：只在上表 12 点迁完、同文件额外残留也迁完、并且 `rg -n -- "--color-brass|--color-ink|letterpress|ink-brush-hr" web/src` 对 active code 0 命中后删除。理由：`docs/reset/phase-a-charter.md:15` 把 “12 consumer 全迁 + grep 0” 绑定为 Phase A hardline；`docs/reset/phase-a-charter.md:102-105` 明确 A5 交付要删 legacy 段、4 themes 一致、Playwright smoke。

Current verbatim delete/rewrite targets from `web/src/app/globals.css`:

```css
/* lines 12-13 */
   旧 6 Agent 页面继续消费 --color-paper / --color-ink / --color-brass；
   新 platform shell 消费 --g0..--g7 / --ink / --chalk / --accent。 */

/* lines 30-37 */
  --color-ink: #1a2e28;
  --color-ink-soft: #2d3f39;
  --color-ink-muted: #556962;
  --color-brass: #f0d488;
  --color-brass-dim: #d4b370;
  --color-brass-glow: #fff0c8;

/* lines 65-70 */
  --color-ink: var(--color-ink);
  --color-ink-soft: var(--color-ink-soft);
  --color-ink-muted: var(--color-ink-muted);
  --color-brass: var(--color-brass);
  --color-brass-dim: var(--color-brass-dim);
  --color-brass-glow: var(--color-brass-glow);

/* lines 153-160 */
  --color-ink: #f6f8fb;
  --color-ink-soft: #d0d6de;
  --color-ink-muted: #8a95a2;
  --color-brass: #f0d488;
  --color-brass-dim: #d4b370;
  --color-brass-glow: #fff0c8;

/* lines 205-210 */
[data-theme="ink"] [class*="text-[var(--color-brass)]"] {
  color: #f0d488 !important;
  text-shadow: 0 0 10px rgba(240, 212, 136, 0.35);
  font-weight: 500;
}
[data-theme="ink"] [class*="text-[var(--color-brass-dim)]"] {

/* line 388 */
  color: var(--color-brass);
```

Also rewrite same-file direct consumers before deletion: `body` color at `web/src/app/globals.css:93`, selection at `:103`, `hr-fine` border at `:130-131`, ink-theme button overrides at `:253/:273/:282/:295/:298/:307/:321/:325`. Current grep has no `.letterpress-*` or `ink-brush-hr` active hit, but hardline still requires guarding them in the final grep.

## 3. 4 themes 一致 verify 方法

Verify baseline: `design_mockups/rm-assistant-final-2026-04-19.html` defines Canvas/Matcha/Dusk/Ink switch at lines `3537-3543` and theme behavior at `3683-3690`; repo tokens mirror this in `web/src/app/tokens.css:8-125`. The smoke should test `/today`, `/archive`, and one agent workspace such as `/archive/report`, because A5 touches shared colors used by tiles and viz.

Proposed spec: `web/tests/regression/letterpress-purge-visual.spec.ts`.

```ts
import { test, expect } from "@playwright/test";

const themes = ["canvas", "matcha", "dusk", "ink"] as const;
const routes = ["/today", "/archive", "/archive/report"] as const;

test.describe("A5 Letterpress purge visual smoke", () => {
  for (const route of routes) {
    for (const theme of themes) {
      test(`${route} ${theme} has shell-v2 tokens only`, async ({ page }) => {
        await page.goto(route, { waitUntil: "networkidle" });

        await page.evaluate((t) => {
          document.body.setAttribute("data-theme", t);
          document.documentElement.setAttribute("data-theme", t);
        }, theme);

        const tokenState = await page.evaluate(() => {
          const root = getComputedStyle(document.documentElement);
          const body = getComputedStyle(document.body);
          return {
            g0: root.getPropertyValue("--g0").trim(),
            ink: root.getPropertyValue("--ink").trim(),
            chalk: root.getPropertyValue("--chalk").trim(),
            accent: root.getPropertyValue("--accent").trim(),
            brass: root.getPropertyValue("--color-brass").trim(),
            legacyInk: root.getPropertyValue("--color-ink").trim(),
            bodyColor: body.color,
            bg: body.backgroundColor,
          };
        });

        expect(tokenState.g0).not.toBe("");
        expect(tokenState.ink).not.toBe("");
        expect(tokenState.chalk).not.toBe("");
        expect(tokenState.accent).not.toBe("");
        expect(tokenState.brass).toBe("");
        expect(tokenState.legacyInk).toBe("");

        await expect(page).toHaveScreenshot(
          `a5-${route.replaceAll("/", "_") || "root"}-${theme}.png`,
          { fullPage: true, maxDiffPixelRatio: 0.015 },
        );
      });
    }
  }

  test("source has no retired Letterpress tokens", async ({ page }) => {
    await page.goto("/archive/report", { waitUntil: "networkidle" });
    const offenders = await page.evaluate(() =>
      [...document.styleSheets].some((sheet) =>
        [...(sheet.cssRules ?? [])].some((r) =>
          r.cssText.includes("--color-brass") ||
          r.cssText.includes("--color-ink") ||
          r.cssText.includes("ink-brush-hr") ||
          r.cssText.includes("letterpress-"),
        ),
      ),
    );
    expect(offenders).toBe(false);
  });
});
```

## 4. PRESERVES

PRESERVES: `F-003` theme switch must keep four visible themes and `data-theme` switching (`docs/features-inventory.md:42-50`), because A5 is about token cleanup, not changing shell UX. PRESERVES: `F-006` ScoreRadar visual style (`docs/features-inventory.md:72-79`) because shared `viz` token rewrites can affect radar/glass visuals. PRESERVES: `F-009` Report ScanCTA pipeline (`docs/features-inventory.md:109-117`), `F-010` template coverage ring (`:119-127`), `F-011` material upload grid (`:129-137`), `F-012` timeline/session switch (`:139-147`), `F-013` A4 preview/TOC/field chips (`:149-157`), and `F-014` report toolbar (`:159-167`) because `/archive/report` is the most exposed consumer of `VerdictBadge`, `PipelineRail`, and shared UI tokens. PRESERVES: `F-015` through `F-019` Credit workspace decision/radar/redline/evidence surfaces (`docs/features-inventory.md:173-221`) because `VerdictBadge` is credit-facing.

Dissent appendix: I disagree with a narrow interpretation of “12 consumer 全迁” as sufficient. The audit’s 12 points are necessary but not enough for the charter’s own grep-0 acceptance: current `web/src` still has many `--color-ink` / `--color-brass` consumers outside Cat 14, including `ScoreBar`, `Card`, `Select`, `QuestionnairePanel`, `FileDrop`, `ChatTagInput`, and `Button`. A5 should land as a purge spec with two gates: first the 12 audit consumers, then repository-wide retirement of `--color-brass`, `--color-ink*`, `.letterpress-*`, and `ink-brush-hr`.