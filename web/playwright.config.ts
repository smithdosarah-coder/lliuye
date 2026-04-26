import { defineConfig, devices } from "@playwright/test";

/**
 * Stage 4 final baseline · 5 theme × 4 view = 20 screenshots
 * - baseURL 127.0.0.1:3000（Next.js dev 端口，避开代理）
 * - Chromium headless only; ±2% anti-alias tolerance 由 toMatchSnapshot maxDiffPixelRatio 控制
 */
export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000",
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
    ignoreHTTPSErrors: true,
    screenshot: "off",
    video: "off",
    trace: "off",
  },
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
