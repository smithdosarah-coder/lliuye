import { test } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";
import { pathToFileURL } from "node:url";

/**
 * Stage 5 · visual-ref exporter (one-shot)
 *
 * 从设计稿 SPA (design_mockups/stage5/original/Agent6 Workspace.html) 按 hash 切 6 个 view，
 * 把每份 view 的完整 DOM dump 成独立 HTML 落 design_mockups/stage5/visual-ref/。
 *
 * 目的: 冻结视觉语言作 R-V1 基线源，供 worker 实装参照 + 后续 Playwright pixel diff baseline 起点。
 *
 * 此文件不做 assert，只做 export。跑完后 6 份 visual-ref HTML 产出。
 *
 * 运行: cd web && pnpm exec playwright test stage5-export
 */

const STAGE5_ROOT = path.resolve(__dirname, "..", "..", "design_mockups", "stage5");
const SPA_ABS = path.resolve(STAGE5_ROOT, "original", "Agent6 Workspace.html");
const SPA_URL_BASE = pathToFileURL(SPA_ABS).href;
const OUT_DIR = path.resolve(STAGE5_ROOT, "visual-ref");

const AGENTS = [
  { id: "report", canonical: "report" },
  { id: "chan", canonical: "channel" },
  { id: "credit", canonical: "credit" },
  { id: "alert", canonical: "alert" },
  { id: "compli", canonical: "compliance" },
  { id: "risk", canonical: "riskctrl" },
] as const;

test.describe("stage5 visual-ref export", () => {
  test.beforeAll(() => {
    if (!fs.existsSync(SPA_ABS)) {
      throw new Error(`SPA source not found at ${SPA_ABS}`);
    }
    fs.mkdirSync(OUT_DIR, { recursive: true });
  });

  for (const a of AGENTS) {
    test(`export ${a.canonical}`, async ({ page }) => {
      await page.setViewportSize({ width: 1480, height: 1800 });
      const url = `${SPA_URL_BASE}#/a/${a.id}`;
      await page.goto(url);
      await page.waitForSelector(`.v-${a.id}`, { timeout: 10_000 });
      // allow drift / rise / bar-in animations to settle
      await page.waitForTimeout(1200);

      let html = await page.content();

      // fix asset paths: agent6/ lives under original/, visual-ref/ is sibling
      html = html.replace(/href="agent6\//g, 'href="../original/agent6/');
      html = html.replace(/src="agent6\//g, 'src="../original/agent6/');

      // strip router.js: DOM is frozen at capture, no re-render needed
      html = html.replace(
        /<script\s+src="\.\.\/original\/agent6\/router\.js"[^>]*><\/script>/gi,
        "<!-- router.js stripped: DOM frozen at capture -->",
      );

      // stamp stage5 marker
      const ts = new Date().toISOString();
      html = html.replace(
        /<title>/,
        `<meta name="stage5-visual-ref" content="agent=${a.canonical}; src=Agent6 Workspace.html#/a/${a.id}; captured=${ts}">\n<!-- STAGE5 VISUAL REF · ${a.canonical} · DO NOT EDIT · see design_mockups/stage5/README.md -->\n<title>`,
      );

      const outPath = path.join(OUT_DIR, `${a.canonical}-visual-ref.html`);
      fs.writeFileSync(outPath, html, "utf-8");
      console.log(
        `[ok] ${a.canonical.padEnd(12)} -> visual-ref/${a.canonical}-visual-ref.html  (${html.length} bytes)`,
      );
    });
  }
});
