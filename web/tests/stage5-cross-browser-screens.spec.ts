import { test, type Page } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";

/**
 * P3F 轨 4 · Stage 5 · 跨 browser smoke + 截屏 (FE-STAGE-5-SMOKE-DONE)
 *
 * 矩阵: 2 browser project (chromium + edge · per playwright.config.ts) ×
 *       4 主题 (canvas / matcha / dusk / ink) ×
 *       4 view (/today /dispatch /archive /warroom) =
 *       **32 张 PNG**
 *
 * 截屏路径: docs/screens/frontend-integration/{chrome,edge}/{theme}/{view}.png
 * (project.name "chromium" 落 chrome dir 与 onboarding §2 Task E 路径约定一致)
 *
 * 主题切换走 ThemeSwitch UI 按钮 (right Masthead .theme-sw role=radio button[data-t=*])
 * · NOT localStorage 直改 (per kickoff #3)。
 *
 * 截屏 viewport 1440×900 (per onboarding §2 Task E "≥ 1440×900 全屏")。
 * fullPage: false · 仅 viewport (含 Masthead + Desk hint + ThemeSwitch · Desk
 * pin 默认收起 · 不展开避免 hover-from-edge race)。
 */

const SCREENS_ROOT = path.resolve(
  __dirname,
  "..",
  "..",
  "docs",
  "screens",
  "frontend-integration",
);

type ThemeKey = "canvas" | "matcha" | "dusk" | "ink";
const THEMES: ReadonlyArray<{ key: ThemeKey; name: string }> = [
  { key: "canvas", name: "canvas" },
  { key: "matcha", name: "matcha" },
  { key: "dusk", name: "dusk" },
  { key: "ink", name: "ink" },
];

type ViewKey = "today" | "dispatch" | "archive" | "warroom";
const VIEWS: ReadonlyArray<{ path: string; name: ViewKey }> = [
  { path: "/today", name: "today" },
  { path: "/dispatch", name: "dispatch" },
  { path: "/archive", name: "archive" },
  { path: "/warroom", name: "warroom" },
];

async function seedAuth(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const user = {
      id: "u_wangzhe",
      name: "王哲",
      role: "rm",
      team: "华东·上海第一支行",
      avatar: "哲",
    };
    window.localStorage.setItem(
      "platform.auth.v1",
      JSON.stringify({ state: { currentUser: user }, version: 0 }),
    );
  });
}

function browserDir(projectName: string): string {
  /* project.name "chromium" → docs/screens/.../chrome/ (onboarding 路径约定)
     "edge" → edge/ */
  return projectName === "edge" ? "edge" : "chrome";
}

test.describe("Stage 5 · cross-browser × 4-theme × 4-view smoke screens", () => {
  for (const theme of THEMES) {
    for (const view of VIEWS) {
      test(`${view.name} · ${theme.name}`, async ({ page }, testInfo) => {
        const dir = browserDir(testInfo.project.name);
        await seedAuth(page);
        await page.setViewportSize({ width: 1440, height: 900 });

        await page.goto(view.path);
        /* shell render + ThemeSwitch DOM 在 effect 后挂 · 等 200ms */
        await page.waitForTimeout(200);

        /* 主题切换走 ThemeSwitch button (per kickoff #3 · UI driven · 非 localStorage) */
        const themeBtn = page.locator(`button[data-t="${theme.key}"]`);
        await themeBtn.click();
        /* 让 bodyBreath 22s + drift 38s + glyph-rise stagger + card-rise 至少跑过一个
           完整 entry 周期 (per CLAUDE.md §7 动画 token) · 800ms 取自 stage5-export
           成熟基线 1200ms 的 2/3 · 截屏稳态够用 */
        await page.waitForTimeout(800);

        const outPath = path.resolve(
          SCREENS_ROOT,
          dir,
          theme.name,
          `${view.name}.png`,
        );
        fs.mkdirSync(path.dirname(outPath), { recursive: true });
        await page.screenshot({ path: outPath, fullPage: false });
      });
    }
  }
});
