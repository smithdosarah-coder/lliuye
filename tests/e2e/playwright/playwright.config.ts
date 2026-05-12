/**
 * Playwright config · W1 mock-test 第 5 棒 · 2026-05-12
 *
 * monorepo workspace 风格 (per brief): config 文件 sit `tests/e2e/playwright/` 目录下 ·
 * `testDir: '.'` · 仅匹配 spec.ts · 不引入 root config.
 *
 * Chromium 唯一 project (per brief · W1 跑通即可 · WebKit/Firefox 留 W7-W8).
 * Headless 默认 · `PLAYWRIGHT_HEADED=1` 切 headed 调试.
 *
 * baseURL: localhost:3210 (per W1-frontend 第 2 棒决策 · :3000 EADDRINUSE 退到 3210 ·
 * 见 docs/handoff/W1-frontend-progress.md checkpoint 2 + 4).
 *
 * webServer 不自动 spawn frontend dev (W1 frontend 已在跑 · 跨棒 dev server 不重启).
 * mock SSE :8001/8002/8003 也由调用方 (`npm run mock-sse:*` 在 tests/ 跑) 启动 ·
 * 本 config 不自启 (避免端口冲突).
 *
 * Step-budget gate (per brief · v3 附录 C.3 hard gate ±20%):
 * demo-path-step1-3.spec.ts 自己用 `test.step()` 内部计时 + 断言 · 不放 config.
 *
 * Worker count: 1 (W1 跑顺序 spec · 避免 dev server 单 instance 被多 worker 抢)
 */
import { defineConfig, devices } from '@playwright/test';

const isHeaded = process.env.PLAYWRIGHT_HEADED === '1';

export default defineConfig({
  testDir: '.',
  testMatch: ['**/*.spec.ts'],

  // Reporter: list 简洁 + html 留 W2-W4 调试 (本 W1 仅 list · 不入库 html report)
  reporter: [['list']],

  // 单 worker · 避免并发抢 :3210 dev server
  workers: 1,

  // 失败 retry 0 (W1 baseline · 任何 flake 视作 bug 立即查)
  retries: 0,

  // 全局 timeout: 单 test 60s (demo-path step3 mock SSE 15s 预算 + buffer)
  timeout: 60_000,

  // expect timeout: 单 assertion 10s
  expect: { timeout: 10_000 },

  use: {
    baseURL: 'http://localhost:3210',
    // headless 默认 · PLAYWRIGHT_HEADED=1 切 headed
    headless: !isHeaded,
    // viewport: ground truth 主视觉锚 (笔记本 1440)
    viewport: { width: 1440, height: 900 },
    // 中文页面 · locale + tz 对齐
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
    // trace on retry · W1 retry=0 故 trace 仅手动 PLAYWRIGHT_TRACE=on 时启
    trace: process.env.PLAYWRIGHT_TRACE === 'on' ? 'on' : 'off',
    // screenshot on failure (W2-W4 CI artifact 用)
    screenshot: 'only-on-failure',
    // video off (体积大 · W1 不录)
    video: 'off',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
