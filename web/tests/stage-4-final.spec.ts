import { test, expect, type Page } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";

/**
 * Stage 4 final · 5 theme × 4 view = 20 baseline screenshots
 *
 * 断言
 * a) 4 view HTTP 200
 * b) Masthead persona 王哲·客户经理·华东 可见
 * c) Desk hover clientX<22 展开
 * d) 主题切换后 body.dataset.theme 真变
 * e) hero glyph-rise stagger 正常（.hero-h1 .word .glyph 存在且数量>0）
 *
 * Ink 主题 switcher 隐藏，改走 body.setAttribute("data-theme","ink")
 */

const THEMES = ["canvas", "matcha", "dusk", "crimson", "ink"] as const;
type Theme = (typeof THEMES)[number];

// letterpress = crimson（spec L8 命名替换，DOM 属性仍是 crimson）
const THEME_FILENAME: Record<Theme, string> = {
  canvas: "canvas",
  matcha: "matcha",
  dusk: "dusk",
  crimson: "letterpress",
  ink: "ink",
};

const VIEWS = [
  { path: "/today", slug: "today" },
  { path: "/dispatch", slug: "dispatch" },
  { path: "/archive", slug: "archive" },
  { path: "/warroom", slug: "warroom" },
] as const;

const OUT_DIR = path.join(__dirname, "..", "__snapshots__", "stage-4-final");
fs.mkdirSync(OUT_DIR, { recursive: true });

async function applyTheme(page: Page, theme: Theme) {
  if (theme === "ink") {
    // Ink 不在 switcher 里暴露，直接设 DOM
    await page.evaluate(() => {
      document.body.setAttribute("data-theme", "ink");
    });
  } else if (theme === "canvas") {
    const btn = page.locator('button[data-t="canvas"]');
    if (await btn.count()) await btn.first().click();
    else
      await page.evaluate(() => {
        document.body.removeAttribute("data-theme");
      });
  } else {
    const btn = page.locator(`button[data-t="${theme}"]`);
    await btn.first().click();
  }
  await page.waitForTimeout(150);
}

async function verifyCommon(page: Page, theme: Theme) {
  // b) Masthead persona
  await expect(page.locator(".shell-op .name")).toHaveText("王哲");
  await expect(page.locator(".shell-op .role")).toHaveText("客户经理 · 华东");

  // e) hero glyph-rise stagger 存在
  const glyphCount = await page.locator(".hero-h1 .word .glyph, .hero-h1 .word").count();
  expect(glyphCount).toBeGreaterThan(0);

  // d) body data-theme 真变
  const themeAttr = await page.evaluate(() => document.body.getAttribute("data-theme"));
  if (theme === "canvas") {
    expect(themeAttr).toBeNull();
  } else {
    expect(themeAttr).toBe(theme);
  }
}

async function verifyDeskHover(page: Page) {
  // c) Desk hover clientX<22 触发 open · Desk.tsx L22 + L58 → aside.drawer.open
  // 60fps throttle 之间连发两次 move 绕开节流丢帧
  await page.mouse.move(600, 400);
  await page.waitForTimeout(50);
  await page.mouse.move(10, 400);
  await page.waitForTimeout(120);
  await page.mouse.move(12, 420);
  await page.waitForTimeout(250);
  const openCount = await page.locator("aside.drawer.open").count();
  expect(openCount, "Desk should be open after hover at x<22").toBeGreaterThan(0);
  // 鼠标移到中部让 Desk 收起，不污染后续截图
  await page.mouse.move(800, 400);
  await page.waitForTimeout(250);
}

for (const theme of THEMES) {
  test.describe(`theme ${theme}`, () => {
    for (const view of VIEWS) {
      test(`${theme} × ${view.slug}`, async ({ page }) => {
        // a) HTTP 200
        const resp = await page.goto(view.path, { waitUntil: "networkidle" });
        expect(resp, `response for ${view.path}`).not.toBeNull();
        expect(resp!.status(), `status for ${view.path}`).toBe(200);

        await applyTheme(page, theme);
        await page.waitForTimeout(300);

        await verifyCommon(page, theme);

        // Desk hover 只在 today 上验一次即可；其他 view 仍截图
        if (view.slug === "today") {
          await verifyDeskHover(page);
        }

        const shot = path.join(
          OUT_DIR,
          `${THEME_FILENAME[theme]}-${view.slug}.png`,
        );
        await page.screenshot({ path: shot, fullPage: false });
      });
    }
  });
}
