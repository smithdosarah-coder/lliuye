/**
 * Stage 5 visual-ref exporter
 *
 * 从设计稿 SPA (original/Agent6 Workspace.html + agent6/router.js) 切出 6 份
 * 独立的 visual-ref HTML，每份对应一个 agent 的 workspace view。
 *
 * 目的: 冻结 "视觉语言" 作 worker 实装参照 + 后续 Playwright baseline 起点。
 * 产物: visual-ref/<canonical>-visual-ref.html × 6
 *
 * 约束: 导出后 HTML 不再依赖 router.js (frozen DOM)，stylesheet 路径修正为
 * `../original/agent6/styles.css`。内容保留设计稿原样 (含 Dossier Scrivener 等
 * 错位命名) —— 业务域纠偏在 Step 2 主 CLI 合成时处理，此阶段只冻结视觉。
 *
 * 运行: 从 web/ 目录跑 (@playwright/test 解析依赖):
 *   cd web && node ../design_mockups/stage5/scripts/export-views.mjs
 */

import { chromium } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const STAGE5_ROOT = resolve(__dirname, "..");
const SPA_ABS = resolve(STAGE5_ROOT, "original", "Agent6 Workspace.html");
const SPA_URL_BASE = pathToFileURL(SPA_ABS).href;

const AGENTS = [
  { id: "report", canonical: "report" },
  { id: "chan", canonical: "channel" },
  { id: "credit", canonical: "credit" },
  { id: "alert", canonical: "alert" },
  { id: "compli", canonical: "compliance" },
  { id: "risk", canonical: "riskctrl" },
];

const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1480, height: 1800 },
});
const page = await context.newPage();

for (const a of AGENTS) {
  const url = `${SPA_URL_BASE}#/a/${a.id}`;
  await page.goto(url);
  await page.waitForSelector(`.v-${a.id}`, { timeout: 10_000 });
  // allow drift / rise / bar-in animations to settle
  await page.waitForTimeout(1200);

  let html = await page.content();

  // fix relative asset paths (agent6/ lives under original/, visual-ref/ is sibling)
  html = html.replace(/href="agent6\//g, 'href="../original/agent6/');
  html = html.replace(/src="agent6\//g, 'src="../original/agent6/');

  // strip router.js so DOM stays frozen at capture time
  html = html.replace(
    /<script\s+src="\.\.\/original\/agent6\/router\.js"[^>]*><\/script>/gi,
    "<!-- router.js stripped: DOM frozen at capture -->",
  );

  // stamp stage5 marker for traceability
  const ts = new Date().toISOString();
  html = html.replace(
    /<title>/,
    `<meta name="stage5-visual-ref" content="agent=${a.canonical}; src=Agent6 Workspace.html#/a/${a.id}; captured=${ts}">\n<!-- STAGE5 VISUAL REF · ${a.canonical} · DO NOT EDIT · see design_mockups/stage5/README.md -->\n<title>`,
  );

  const outPath = resolve(
    STAGE5_ROOT,
    "visual-ref",
    `${a.canonical}-visual-ref.html`,
  );
  writeFileSync(outPath, html, "utf-8");
  console.log(
    `[ok] ${a.canonical.padEnd(12)} -> visual-ref/${a.canonical}-visual-ref.html  (${html.length} bytes)`,
  );
}

await browser.close();
console.log("\nDone. 6 visual-ref HTMLs exported.");
