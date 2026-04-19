import { test, expect, type Page } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";
import { pathToFileURL } from "node:url";

/**
 * Task L · mockup 参照基线（file:// 直渲 rm-assistant-final-2026-04-19.html）
 *
 * 目的：建 canvas 主题 4 view 的 mockup 端 PNG 基线，与 stage-4-final/canvas-*.png
 * 并置供人眼 1:1 比对。自动 pixel-diff 在 live clock / persona / 动画 mid-flight
 * 三源方差下强度不足，此处仅建参照，不断言 pixel threshold。
 *
 * 输出：web/__snapshots__/mockup-ref/{today,dispatch,archive,warroom}.png
 */

const MOCKUP_ABS = path.resolve(
  __dirname,
  "..",
  "..",
  "design_mockups",
  "rm-assistant-final-2026-04-19.html",
);
const MOCKUP_URL = pathToFileURL(MOCKUP_ABS).href;

const OUT_DIR = path.join(__dirname, "..", "__snapshots__", "mockup-ref");
fs.mkdirSync(OUT_DIR, { recursive: true });

const VIEWS = ["today", "dispatch", "archive", "warroom"] as const;
type View = (typeof VIEWS)[number];

async function switchToView(page: Page, view: View) {
  await page.evaluate((v) => {
    const tabs = document.querySelectorAll<HTMLElement>(".tabs button");
    tabs.forEach((t) => t.classList.toggle("on", t.dataset.v === v));
    const views = document.querySelectorAll<HTMLElement>(".view");
    views.forEach((x) => x.classList.toggle("on", x.dataset.view === v));
    window.scrollTo({ top: 0 });
  }, view);
  await page.waitForTimeout(650);
}

test.describe("mockup ref · canvas default", () => {
  test.beforeAll(() => {
    if (!fs.existsSync(MOCKUP_ABS)) {
      throw new Error(`mockup not found at ${MOCKUP_ABS}`);
    }
  });

  for (const view of VIEWS) {
    test(`mockup · ${view}`, async ({ page }) => {
      await page.goto(MOCKUP_URL, { waitUntil: "networkidle" });
      // 主题默认 canvas（无 data-theme attr）
      await expect(page.locator("body")).toBeVisible();
      await switchToView(page, view);

      const shot = path.join(OUT_DIR, `${view}.png`);
      await page.screenshot({ path: shot, fullPage: false });

      // 存在性 assertion · 基线文件落盘即 pass
      expect(fs.existsSync(shot)).toBe(true);
    });
  }
});
