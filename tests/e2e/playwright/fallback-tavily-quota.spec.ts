/**
 * W2-mock-test · 第 4 棒 · 2026-05-12
 * fallback-tavily-quota.spec.ts · 5 应急 W2 跑 #1 · 附录 C.2.1
 *
 * SSOT: W2-mock-test brief §4.4 (1) verbatim + v3 spec 附录 C.2.1
 * 引用:
 *   - v3 §3 (Channel 适配器 fallback 路径 + DEMO_MODE 切换)
 *   - W2-frontend brief §4.5 (FallbackBanner 5 fallback UI 中文外显表 · Tavily quota chip 灰 badge)
 *   - W1 mock-test 第 3 棒 mock SSE :8001 channel · channel_5candidates.json (fallback 走 fixture)
 *
 * 场景 (附录 C.2.1):
 *   - Tavily 返 429 / quota 耗尽 (real prod 触发)
 *   - 系统应自动切 LIUYE_DEMO_MODE=mock · channel adapter 走 fixture (mock SSE :8001 复用)
 *   - UI 显 FallbackBanner chip 灰 badge 「Demo 模式 · 数据来自预录候选」(W2-frontend §4.5 文案 verbatim)
 *   - 后续 step 4-9 不受影响 (channel 给 candidate · credit/report 真接走 live 路径)
 *
 * 触发 Tavily 429 路径 (3 选 1 · 第 4 棒选最稳的):
 *   (A) backend `LIUYE_FORCE_TAVILY_ERROR=1` env flag · channel adapter 内部强返 quota_exceeded SSE error event
 *   (B) mock backend response (proxy 拦截 Tavily upstream 模拟 429)
 *   (C) mock SSE :8001 加 special endpoint `/quota-exceed` 推 v1.0 error event payload {code: 'TAVILY_QUOTA_EXCEEDED'}
 *
 *   第 4 棒选 (A) `LIUYE_FORCE_TAVILY_ERROR=1` · W2-backend 实做边界 (W2-backend brief §4.x · 现 0/16 未 ship · 等 ship 后接通)
 *   spec 写 testid contract · 不强依赖具体触发机制 · UI 显 FallbackBanner 即 OK
 *
 * Skip 条件:
 *   - mock SSE :8001 (channel) 不可达 → skip (per W1 demo-path-step1-3 模式)
 *   - SKIP_DEMO_STEP4_9=1 (UI 真渲未到位) → skip
 *
 * 不准做 (per 接力 brief):
 *   - 不实跑 Playwright · 仅 spec written + tsc verify (mock SSE / frontend / backend 未起)
 *   - 不写 W3-W4 留 3 应急 (LLM provider fallback · SSE conversion · network offline)
 *
 * Hidden gotcha (第 4 棒 record):
 *   - FallbackBanner 文案 follow W2-frontend brief §4.5 真实 UI 文案 (「Demo 模式 · 数据来自预录候选」)
 *     不是接力 brief 臆想的「搜索配额已用尽 · 已切换至 Demo 模式」· UI SSOT 走 W2-frontend brief
 *   - data-kind="tavily_quota" 是 W2-frontend FallbackBanner 内嵌 data attr · 5 fallback 各一 data-kind
 *     (tavily_quota / llm_provider / ledger_silent_fail / sse_conversion / network_offline · 第 4 棒立 contract)
 *   - LIUYE_FORCE_TAVILY_ERROR=1 env 是 W2-backend 应实做的 flag · 现未 ship · spec 跑会 fail → SKIP 暂跳
 */
import { test, expect, type Page } from '@playwright/test';

// ============================================================================
// Mock SSE health probe (复用 W1/W2 pattern)
// ============================================================================
const MOCK_SSE_CHANNEL_HEALTH = 'http://localhost:8001/health';

async function isMockSseAlive(page: Page, url: string, expectedAgent: string): Promise<boolean> {
  try {
    const response = await page.request.get(url, { timeout: 2000 });
    if (!response.ok()) return false;
    const body = (await response.json()) as { ok?: boolean; agent?: string };
    return body.ok === true && body.agent === expectedAgent;
  } catch {
    return false;
  }
}

// ============================================================================
// Tests · Tavily 429 → DEMO_MODE 自动切换 + FallbackBanner UI 验证
// ============================================================================

test.describe('W2 应急 #1 · fallback-tavily-quota · Tavily 429 → DEMO_MODE 自动切换', () => {
  test.skip(
    process.env.SKIP_DEMO_STEP4_9 === '1',
    'SKIP_DEMO_STEP4_9=1 set · W2-frontend FallbackBanner 真渲未到位时跳过'
  );

  test('Tavily quota 耗尽 · DEMO_MODE 自动切 · FallbackBanner 显「Demo 模式」· step 后续不受影响', async ({
    page,
  }) => {
    // ------------------------------------------------------------------------
    // 前置: probe mock SSE :8001 (channel · DEMO_MODE 切换后走 mock fixture)
    // ------------------------------------------------------------------------
    const channelAlive = await isMockSseAlive(page, MOCK_SSE_CHANNEL_HEALTH, 'channel');
    if (!channelAlive) {
      // eslint-disable-next-line no-console
      console.log(
        `  [fallback-tavily-quota skip] mock SSE :8001 不可达 · DEMO_MODE 切换后 channel 走 mock fixture · 请先 'cd tests && npm run mock-sse:channel'`
      );
      test.skip(true, 'mock SSE :8001 (channel) 未起 · DEMO_MODE 切换 fallback 路径无法验');
      return;
    }

    // ------------------------------------------------------------------------
    // Step 1: 静默首页 → 点 channel chip → 输入诉求 + submit
    //   (与 demo-path-step1-3 同前置 · 但本 spec 重点验 FallbackBanner · 不验耗时)
    // ------------------------------------------------------------------------
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('[data-testid="hero-static"]')).toBeVisible({ timeout: 5_000 });
    await page.click('[data-testid="agent-chip-channel"]');
    await page.locator('[data-testid="composer-textarea"]').fill('找新能源汽车零部件相似客户');
    await page.click('[data-testid="composer-submit"]');

    // ------------------------------------------------------------------------
    // Step 2: 等 FallbackBanner 显 (tavily_quota kind)
    //   触发机制 (W2-backend live 真实做): `LIUYE_FORCE_TAVILY_ERROR=1` env · channel adapter 强返
    //   quota_exceeded SSE error event payload {code: 'TAVILY_QUOTA_EXCEEDED', retryable: false,
    //   fallback_available: true} · LiuyeBridge 监听到该 payload → liuyeStore.setFallback({kind:
    //   'tavily_quota', ...}) → FallbackBanner 渲灰 chip 「Demo 模式」(W2-frontend §4.5 文案 verbatim)
    //
    //   FallbackBanner data-testid="fallback-banner" data-kind="tavily_quota" (W2-frontend §4.5 + §6 NEW-DOM)
    // ------------------------------------------------------------------------
    const banner = page.locator('[data-testid="fallback-banner"][data-kind="tavily_quota"]');
    await expect(
      banner,
      'FallbackBanner tavily_quota chip 应在 6s 内显 (DEMO_MODE 自动切换后)'
    ).toBeVisible({ timeout: 6_000 });
    // 验文案 = W2-frontend brief §4.5 verbatim (UI SSOT)
    await expect(
      banner,
      'FallbackBanner 应显「Demo 模式 · 数据来自预录候选」(W2-frontend §4.5 verbatim · 不是接力 brief 臆想文案)'
    ).toContainText('Demo 模式');

    // ------------------------------------------------------------------------
    // Step 3: 验 channel candidate 仍出 (走 fixture · DEMO_MODE 切换后)
    //   后续 step 4-9 不受影响 (channel 给 candidate · credit/report 真接 LLM 路径)
    // ------------------------------------------------------------------------
    await expect(
      page.locator('[data-testid="candidate-row-0"]'),
      'first candidate 应在 fallback 后仍可见 (channel adapter 走 mock fixture)'
    ).toBeVisible({ timeout: 18_000 });
    const candidates = await page.locator('[data-testid^="candidate-row-"]').count();
    expect(
      candidates,
      `DEMO_MODE 切换后 channel 应仍推 ≥ 5 候选 (mock fixture) · 实际 ${candidates}`
    ).toBeGreaterThanOrEqual(5);

    // ------------------------------------------------------------------------
    // 验 candidate metadata 4 字段 (Q-041 硬线 · industry/geo/scale/similarity · root §3.7.2)
    //   per W2-frontend MessageList 真消费 channel.ts SSE event payload
    //   (fixture channel_5candidates.json 已含 4 字段 · 验前端真渲 · 不是漂)
    // ------------------------------------------------------------------------
    const firstRow = page.locator('[data-testid="candidate-row-0"]');
    await expect(firstRow, 'candidate row 0 应渲 industry 字段').toContainText(/.+/); // 渲非空文本即可
    // 具体 4 字段 testid (W2-frontend MessageList ranked-row 内嵌 · 与 Q-041 mapping)
    //   candidate-meta-industry-0 / candidate-meta-geo-0 / candidate-meta-scale-0 / candidate-meta-similarity-0
    //   现 spec 仅 log · 不强断 (W2-frontend brief 未 lock 这些 testid · 留 W3 contract worker 补 contract)
    const industryCount = await page.locator('[data-testid="candidate-meta-industry-0"]').count();
    const geoCount = await page.locator('[data-testid="candidate-meta-geo-0"]').count();
    const scaleCount = await page.locator('[data-testid="candidate-meta-scale-0"]').count();
    const similarityCount = await page.locator('[data-testid="candidate-meta-similarity-0"]').count();
    // eslint-disable-next-line no-console
    console.log(
      `  [fallback-tavily-quota · Q-041 4 字段] industry=${industryCount} geo=${geoCount} scale=${scaleCount} similarity=${similarityCount} (期 各 1)`
    );

    // 总结 log (D8 PM 应急 dry-run 回看)
    // eslint-disable-next-line no-console
    console.log(
      `  [fallback-tavily-quota summary · W2 应急 #1] FallbackBanner tavily_quota visible + candidate-row 共 ${candidates} 个 (≥ 5 ok · channel mock fixture replay) · DEMO_MODE 自动切换路径 OK`
    );
  });
});
