import { defineConfig, devices } from "@playwright/test";

/**
 * Stage 4 final baseline · 5 theme × 4 view = 20 screenshots
 * - baseURL 127.0.0.1:3000（Next.js dev 端口，避开代理）
 * - Chromium headless only; ±2% anti-alias tolerance 由 toMatchSnapshot maxDiffPixelRatio 控制
 *
 * A5 V2 (2026-04-30 · codex DISAGREE issue #2+#3 · fail-loud 策略):
 *   - 默认 baseURL :3000 (保留既有 dev workflow)
 *   - letterpress-purge spec 不再 skip-when-unavail · server 不在 = 直接 fail (loud)
 *   - 真 hermetic 需求: PLAYWRIGHT_LP_WEBSERVER=1 起 :3101 (opt-in · Next 16 多 worktree 锁规避)
 *   - 显式覆盖: PLAYWRIGHT_BASE_URL=http://127.0.0.1:NNNN
 */
const explicitBaseUrl = process.env.PLAYWRIGHT_BASE_URL;
const useWebServer = process.env.PLAYWRIGHT_LP_WEBSERVER === "1";

export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: explicitBaseUrl ?? (useWebServer ? "http://127.0.0.1:3101" : "http://127.0.0.1:3000"),
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
        reuseExistingServer: !process.env.PLAYWRIGHT_NO_REUSE,
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
