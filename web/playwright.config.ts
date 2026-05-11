import { defineConfig, devices } from "@playwright/test";

/**
 * Stage 4 final baseline · 5 theme × 4 view = 20 screenshots
 * - Chromium headless only; ±2% anti-alias tolerance 由 toMatchSnapshot maxDiffPixelRatio 控制
 *
 * A5 V3 (2026-04-30 · codex V3 · hermetic by default):
 *   - 默认 baseURL :3101 · 自动起 fresh dev (reuseExistingServer:false)
 *   - 移除 V2 的 PLAYWRIGHT_LP_WEBSERVER opt-in · 现在永远 hermetic
 *   - 跨 worktree Next 16 单实例锁: 跑前需手动 kill 同 dir 旧 dev (用 PowerShell Get-Process)
 *   - 显式覆盖: PLAYWRIGHT_BASE_URL=http://127.0.0.1:NNNN 跳过 webServer 用既有 server
 */
const explicitBaseUrl = process.env.PLAYWRIGHT_BASE_URL;
const useWebServer = !explicitBaseUrl;

export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  // B.4 SLO-2 主活 D · prod E2E retries: 1 抗 CF cold start transient
  // (本地 dev visual baseline 仍 0 retry · 用 PLAYWRIGHT_RETRIES=0 显式跳)
  retries: process.env.PLAYWRIGHT_RETRIES !== undefined
    ? parseInt(process.env.PLAYWRIGHT_RETRIES, 10)
    : (process.env.PLAYWRIGHT_BASE_URL?.startsWith("https://") ? 1 : 0),
  reporter: [["list"]],
  expect: {
    // 截屏 baseline 容差 · 抗 anti-alias / 字体 hinting 跨机器漂
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.02,
      animations: "disabled",
    },
  },
  use: {
    baseURL: explicitBaseUrl ?? "http://127.0.0.1:3101",
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
    ignoreHTTPSErrors: true,
    screenshot: "off",
    video: "off",
    trace: "off",
  },
  webServer: useWebServer
    ? {
        command: "npm run dev -- --port 3101",
        url: "http://127.0.0.1:3101",
        reuseExistingServer: false, // hermetic · 永远起 fresh
        timeout: 180_000,
        stdout: "ignore",
        stderr: "pipe",
      }
    : undefined,
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    /* P3F 轨 4 Stage 5 跨 browser smoke · Edge 111+ 银行内网兼容主线
       (per CLAUDE.md §7 "color-mix() 要求 Chrome/Edge 111+") */
    {
      name: "edge",
      use: { ...devices["Desktop Edge"], channel: "msedge" },
    },
  ],
});
