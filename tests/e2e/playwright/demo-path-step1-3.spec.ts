/**
 * W1-mock-test · 第 5 棒 · 2026-05-12
 * demo-path-step1-3.spec.ts · demo path 前 3 步 (brief §3 + §4.4 · v3 §6.3 demo path 70s 9 step)
 *
 * 9 步 (v3 §6.3 verbatim):
 *   1. F-007 静默首页 (3s) — ground truth + 4 Agent chip                ← 本 spec 验
 *   2. 点「🔍 找合适企业」chip (1s)                                       ← 本 spec 验
 *   3. F-066 Channel SSE ranked 5 候选流式 (15s)                          ← 本 spec 验
 *   ... (4-9 由 W2-W6 集成测试覆盖)
 *
 * 预算 hard gate (per brief · v3 附录 C.3 · ±20% threshold):
 *   Step 1 ≤ 3.0s · +20% = 3.6s fail threshold
 *   Step 2 ≤ 2.0s · +20% = 2.4s fail threshold (注: brief 写 2s · v3 spec §6.3 写 1s · brief 优先)
 *   Step 3 ≤ 15.0s · +20% = 18.0s fail threshold
 *
 * W1 minimal 路径:
 *   - Step 1 验静默 hero static 渲染 + 4 chip 可见
 *   - Step 2 点 channel chip · 期 console.log 触发 (W1 frontend page.tsx 仅 console.log · W2-W4 真接 SSE)
 *   - Step 3 mock SSE :8001 在跑前提下 · 期 candidate 数据可达 (W1 skeleton 不真 consume · 故验 mock 端可达即可)
 *
 * Mock SSE 启动前置 (调用方负责 · 本 spec 不自启):
 *   cd tests && npm run mock-sse:channel (background · :8001)
 *
 * Skip 条件:
 *   - mock SSE :8001 不可达 → step 3 标 `test.skip()` 跳过 (per brief: 若 frontend SSE consumer 未实做 · 标 .skip)
 *   - W1 frontend page.tsx 当前不接 SSE consumer · 故 step 3 仅验 mock 端口可达 + 占位渲染
 *
 * 注: 真接 SSE + 真验 ranked 5 候选 UI 由 W2-W4 frontend SSE consumer 落地后跑 (本 spec 留 placeholder)
 */
import { test, expect, type Page } from '@playwright/test';

// ============================================================================
// Constants · brief §3 verbatim
// ============================================================================
const BUDGET = {
  step1Ms: 3000,
  step2Ms: 2000,
  step3Ms: 15000,
  // ±20% gate (v3 附录 C.3 hard gate)
  thresholdMultiplier: 1.2,
} as const;

const MOCK_SSE_CHANNEL_URL = 'http://localhost:8001';
const MOCK_SSE_HEALTH_URL = `${MOCK_SSE_CHANNEL_URL}/health`;

// ============================================================================
// Helpers
// ============================================================================

/**
 * 检查 mock SSE channel :8001 是否在跑 · timeout 2s
 */
async function isMockSseAlive(page: Page): Promise<boolean> {
  try {
    const response = await page.request.get(MOCK_SSE_HEALTH_URL, { timeout: 2000 });
    if (!response.ok()) return false;
    const body = (await response.json()) as { ok?: boolean; agent?: string };
    return body.ok === true && body.agent === 'channel';
  } catch {
    return false;
  }
}

/**
 * 验 step 耗时 ≤ budget × (1 + tolerance) · 超 ±20% 走 fail
 */
function assertStepBudget(label: string, elapsedMs: number, budgetMs: number): void {
  const threshold = budgetMs * BUDGET.thresholdMultiplier;
  // 不允许等于 threshold (严格 < · 给 ±0.001% 余量)
  expect(
    elapsedMs,
    `${label} 耗时 ${elapsedMs}ms 超预算 ${budgetMs}ms × ${BUDGET.thresholdMultiplier} = ${threshold}ms (v3 附录 C.3 hard gate)`
  ).toBeLessThan(threshold);
  // 提示性 log (Playwright list reporter 看见)
  // eslint-disable-next-line no-console
  console.log(`  [step-budget] ${label} · ${elapsedMs.toFixed(0)}ms / 预算 ${budgetMs}ms (threshold ${threshold.toFixed(0)}ms · ratio ${(elapsedMs / budgetMs).toFixed(2)})`);
}

// ============================================================================
// Tests · sequential (前一 step pass 是后一 step 前提)
// ============================================================================

test.describe('demo path step 1-3 (v3 §6.3 · brief §3)', () => {
  test('完整 step 1-3 跑通 + 耗时 hard gate (±20%)', async ({ page }) => {
    let step1Elapsed = 0;
    let step2Elapsed = 0;
    let step3Elapsed = 0;

    // ------------------------------------------------------------------------
    // Step 1: 静默首页 → 4 Agent chip 可见 (budget 3s · ±20% = 3.6s)
    // ------------------------------------------------------------------------
    await test.step('Step 1 · F-007 静默首页 (≤3.0s · +20% = 3.6s)', async () => {
      const t0 = Date.now();

      await page.goto('/', { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('[data-testid="hero-static"]', { state: 'visible', timeout: 3500 });

      // 验 4 Agent chip 全可见 (W1 baseline · ground truth)
      await expect(page.getByTestId('agent-chip-channel')).toBeVisible();
      await expect(page.getByTestId('agent-chip-credit')).toBeVisible();
      await expect(page.getByTestId('agent-chip-report')).toBeVisible();
      await expect(page.getByTestId('agent-chip-alert')).toBeVisible();

      step1Elapsed = Date.now() - t0;
      assertStepBudget('Step 1 · 静默首页', step1Elapsed, BUDGET.step1Ms);
    });

    // ------------------------------------------------------------------------
    // Step 2: 点 channel chip ("找合适企业") (budget 2s · ±20% = 2.4s)
    // ------------------------------------------------------------------------
    await test.step('Step 2 · 点 channel chip (≤2.0s · +20% = 2.4s)', async () => {
      const t0 = Date.now();

      // 捕获 console.log "agent chip clicked: channel" (W1 skeleton 仅 console · W2-W4 真触发 SSE turn)
      const consoleLogs: string[] = [];
      page.on('console', (msg) => {
        if (msg.type() === 'log') consoleLogs.push(msg.text());
      });

      await page.getByTestId('agent-chip-channel').click();

      // 等 console.log 出现 (W1 skeleton · page.tsx click handler)
      await page.waitForFunction(
        () => true, // 不能直接 read consoleLogs (跨域 closure) · 改下方手动 check
        undefined,
        { timeout: 500 }
      );
      // 微小延迟让 console.log 落到 page event listener
      await page.waitForTimeout(100);

      const channelClickLogged = consoleLogs.some(
        (s) => s.includes('agent chip clicked') && s.includes('channel')
      );
      expect(
        channelClickLogged,
        `期望 console.log "[W1 skeleton] agent chip clicked: channel" 触发 · 实际 logs: ${consoleLogs.join(' | ')}`
      ).toBe(true);

      step2Elapsed = Date.now() - t0;
      assertStepBudget('Step 2 · 点 channel chip', step2Elapsed, BUDGET.step2Ms);
    });

    // ------------------------------------------------------------------------
    // Step 3: F-066 Channel SSE ranked 5 候选 (budget 15s · ±20% = 18s)
    //   W1 skeleton: frontend page.tsx 不接 SSE consumer · 仅验 mock SSE 端口可达 +
    //   composer 仍可输入诉求 "找新能源汽车零部件相似客户" (UI 占位 ready · W2-W4 接消费)
    // ------------------------------------------------------------------------
    const mockAlive = await isMockSseAlive(page);

    if (!mockAlive) {
      // eslint-disable-next-line no-console
      console.log(
        `  [step3] mock SSE :8001 不可达 · 跳过 step 3 验证 (per brief: frontend SSE consumer 未实做 · skip · W2-W4 跑)`
      );
      test.skip(true, 'mock SSE :8001 not running · run `cd tests && npm run mock-sse:channel` first');
      return;
    }

    await test.step('Step 3 · F-066 mock SSE 端口可达 + composer 输入诉求 (≤15.0s · +20% = 18.0s)', async () => {
      const t0 = Date.now();

      // 验 mock SSE health endpoint 已 alive (前置 check 已过 · 这里只确认 fixture name 对)
      const healthResponse = await page.request.get(MOCK_SSE_HEALTH_URL, { timeout: 3000 });
      expect(healthResponse.ok(), `mock SSE :8001 /health 应返 200`).toBe(true);
      const healthBody = (await healthResponse.json()) as Record<string, unknown>;
      expect(healthBody.agent, `mock SSE agent`).toBe('channel');
      expect(healthBody.fixture, `mock SSE fixture name`).toBe('channel_5candidates.json');

      // 模拟用户输入诉求 (per brief: "找新能源汽车零部件相似客户")
      const textarea = page.getByTestId('composer-textarea');
      await textarea.click();
      await textarea.fill('找新能源汽车零部件相似客户');
      const value = await textarea.inputValue();
      expect(value, 'composer textarea 接受中文诉求输入').toBe('找新能源汽车零部件相似客户');

      // W1 minimal: 不真发 SSE (frontend SSE consumer W2-W4 接) · 不点 submit (会清空 textarea)
      // 仅验 fixture 内 5 候选可加载 (mock SSE 端 fixture file 形态对)
      // 真 ranked rows UI 占位渲染 由 W2-W4 messages-shell 接入 SSE 后跑

      // verify fixture loaded · 直接 fetch /api/channel/run SSE (W1 仅验 200 + 起 SSE stream · 不解析全部 5 候选)
      // 用 page.request.fetch 拿前 200ms 的 SSE 流头部 · 验 event 序列正确开始
      const ssePromise = page.evaluate(async (url) => {
        const controller = new AbortController();
        setTimeout(() => controller.abort(), 2000);
        try {
          const r = await fetch(`${url}/api/channel/run`, { signal: controller.signal });
          if (!r.body) return { ok: false, head: '' };
          const reader = r.body.getReader();
          const decoder = new TextDecoder();
          let head = '';
          // 读前 2KB 或 1s
          const deadline = Date.now() + 1000;
          while (Date.now() < deadline && head.length < 2048) {
            const { value, done } = await reader.read();
            if (done) break;
            head += decoder.decode(value);
          }
          controller.abort();
          return { ok: r.ok, head };
        } catch (e) {
          return { ok: false, head: `error: ${(e as Error).message}` };
        }
      }, MOCK_SSE_CHANNEL_URL);

      const sseHead = await ssePromise;
      expect(sseHead.ok, `mock SSE /api/channel/run 应返 200`).toBe(true);
      // SSE 流头部应含至少 1 个 event · profile_loaded 是第一个 (per channel.ts buildEventSequence)
      expect(
        sseHead.head,
        `mock SSE 流头部应含 "event:" 行 · 实际 head 前 200 字: ${sseHead.head.slice(0, 200)}`
      ).toContain('event:');

      step3Elapsed = Date.now() - t0;
      assertStepBudget('Step 3 · mock SSE + 输入', step3Elapsed, BUDGET.step3Ms);
    });

    // ------------------------------------------------------------------------
    // 总体 summary log (PM 走访彩排耗时记录用 · v3 附录 C.3)
    // ------------------------------------------------------------------------
    const total = step1Elapsed + step2Elapsed + step3Elapsed;
    // eslint-disable-next-line no-console
    console.log(
      `  [demo-path step1-3 summary] step1=${step1Elapsed}ms · step2=${step2Elapsed}ms · step3=${step3Elapsed}ms · total=${total}ms · 预算 ${BUDGET.step1Ms + BUDGET.step2Ms + BUDGET.step3Ms}ms`
    );
  });
});
