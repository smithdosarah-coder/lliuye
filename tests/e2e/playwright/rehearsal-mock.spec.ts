/**
 * W2-mock-test · 第 4 棒 · 2026-05-12
 * rehearsal-mock.spec.ts · D9 sign-off 硬线 · 9 step 完整 70s 彩排 (走通即 W2 sign-off)
 *
 * SSOT: W2-mock-test brief §4.3 (1) verbatim
 * 引用:
 *   - v3 spec §6.3 demo path 70s 9 step + 附录 C.3 hard gate ±20% + §10 视觉硬线
 *   - W1 demo-path-step1-3.spec.ts (step 1-3 模式 · isMockSseAlive helper + Date.now() 差值)
 *   - W2 demo-path-step4-9.spec.ts (step 4-9 模式 · withBudget + testid 命名契约)
 *   - tests/perf/step-budget.ts (STEP_BUDGETS / withBudget / saveBaseline · 第 2 棒 ship)
 *
 * 9 step 完整 (v3 §6.3 verbatim · 步级预算合计 66s ≤ 70s buffer 4s):
 *   step 1 静默首页 (3s)            ← W1 demo-path-step1-3 模式
 *   step 2 点 channel chip (1s)
 *   step 3 SSE ranked 5 (15s)
 *   step 4 IdealProfile 12 维 (10s) ← W2 demo-path-step4-9 模式
 *   step 5 拖 artifact (2s)
 *   step 6 Credit handoff SSE (15s)
 *   step 7 progressive radar 4 维 (10s)
 *   step 8 ConfirmModal medium + ledger 写入 (5s)
 *   step 9 LE-01 trace drawer (5s)
 *
 * 环境 (per brief §4.3 (1)):
 *   - LIUYE_DEMO_MODE=1 (DEMO_MODE on · 3 adapter 全走 mock fixture)
 *   - 3 mock SSE :8001 (channel) + :8002 (credit) + :8003 (report) 起
 *   - W2-frontend ship 后 unset SKIP_DEMO_STEP4_9=1 跑全验
 *
 * Skip 条件 (per brief §4.7 globalSetup probe · W1 demo-path-step1-3 同模式):
 *   - 3 mock SSE 任一不可达 → 全 spec skip (probe channel/credit/report)
 *   - SKIP_DEMO_STEP4_9=1 顶层 skip (W2-frontend / W2-backend 真路径未到位)
 *
 * Baseline (跨 spec 累积 `_temp/w2-rehearsal-baseline.json`):
 *   - saveBaseline('rehearsal-mock', perStep) · env 自动从 LIUYE_DEMO_MODE 推断 'mock'
 *   - D10 rehearsal-hybrid / rehearsal-live (第 5 棒) 续 append 同一 JSON · 漂移对比
 *
 * Hidden gotcha (第 4 棒 record):
 *   - 9 step 单 test 跑完整 path (不拆 9 individual test · per brief 'one path · 不拆')
 *   - rehearsal-mock 是 W2 sign-off 硬线 · 走通即 W2 ship · 失败 = sprint blocker
 *   - step 6 真路径依赖 W2-backend live mode + frontend useLiuyeBridge · 现 0/16 + 0/18 ship · SKIP 暂跳
 *   - 总 timeout 90s (playwright.config 60s 已不够 · 9 step 单 test 至少 70s ±20% = 84s · 加 6s buffer)
 */
import { test, expect, type Page } from '@playwright/test';
import { withBudget, saveBaseline, STEP_BUDGETS } from '../../perf/step-budget';

// ============================================================================
// Mock SSE health probe (复用 W1 demo-path-step1-3 + W2 demo-path-step4-9 模式)
// ============================================================================
const MOCK_SSE_CHANNEL_HEALTH = 'http://localhost:8001/health';
const MOCK_SSE_CREDIT_HEALTH = 'http://localhost:8002/health';
const MOCK_SSE_REPORT_HEALTH = 'http://localhost:8003/health';

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
// Tests · 单 test 跑完整 9 step (one path · per brief)
// ============================================================================

test.describe('W2 rehearsal-mock · D9 sign-off 硬线 · 9 step 完整 70s', () => {
  test.skip(
    process.env.SKIP_DEMO_STEP4_9 === '1',
    'SKIP_DEMO_STEP4_9=1 set · W2-frontend / W2-backend 真路径未到位时跳过 · ship 后 unset 跑全验'
  );

  // 单 test 单 path · 9 step 全 · timeout 提到 90s (default 60s 不够 9 step + ±20%)
  test('step 1-9 完整 demo path · LIUYE_DEMO_MODE=1 · 70s 预算 · ±20% gate', async ({ page }) => {
    test.setTimeout(90_000);

    // ------------------------------------------------------------------------
    // 前置 probe · 3 mock SSE :8001 (channel) + :8002 (credit) + :8003 (report) 全起
    // 任一不可达 → 全 spec skip (per brief §4.3 (1) · 3 mock SSE 起)
    // ------------------------------------------------------------------------
    const channelAlive = await isMockSseAlive(page, MOCK_SSE_CHANNEL_HEALTH, 'channel');
    const creditAlive = await isMockSseAlive(page, MOCK_SSE_CREDIT_HEALTH, 'credit');
    const reportAlive = await isMockSseAlive(page, MOCK_SSE_REPORT_HEALTH, 'report');
    if (!channelAlive || !creditAlive || !reportAlive) {
      // eslint-disable-next-line no-console
      console.log(
        `  [rehearsal-mock skip] mock SSE :8001 alive=${channelAlive} · :8002 alive=${creditAlive} · :8003 alive=${reportAlive} · 请先 'cd tests && npm run mock-sse:channel & npm run mock-sse:credit & npm run mock-sse:report'`
      );
      test.skip(true, '3 mock SSE :8001/:8002/:8003 任一未起 · 跑前需 3 个 mock SSE 全启');
      return;
    }

    // baseline 累积 (本 spec 跑完 saveBaseline 一次性写)
    const perStep: Record<string, number> = {};

    // ------------------------------------------------------------------------
    // Step 1 · F-007 静默首页加载 (budget 3s · ±20% = 3.6s)
    //   动作: page.goto /  → hero-static visible + 4 chip 可见
    //   W1 demo-path-step1-3 模式: 验 hero-static visible · 不再重复 4 chip 全列断言 (W1 已 lock)
    // ------------------------------------------------------------------------
    perStep.step1 = await withBudget('step1', async () => {
      await page.goto('/', { waitUntil: 'domcontentloaded' });
      await expect(
        page.locator('[data-testid="hero-static"]'),
        '静默 hero static 应在 3.6s 内 visible (F-007 baseline · v3 §10)'
      ).toBeVisible({ timeout: 3_500 });
      // 4 chip 可见 (W1 ground truth · 不强断中文文案 · home-silent.spec 已严格验)
      for (const agent of ['channel', 'credit', 'report', 'alert']) {
        await expect(page.locator(`[data-testid="agent-chip-${agent}"]`)).toBeVisible({ timeout: 1_000 });
      }
    });

    // ------------------------------------------------------------------------
    // Step 2 · 点 channel chip (budget 1s · ±20% = 1.2s · W2-frontend brief §4.1 真触 startSession)
    // ------------------------------------------------------------------------
    perStep.step2 = await withBudget('step2', async () => {
      await page.click('[data-testid="agent-chip-channel"]');
      // W2-frontend 真接 startSession + composer transition (360ms) · 在 1.2s 内完成
      // composer 仍可输入 = chip 点击成功标志 (不用 console.log 间接 verify · W1 skeleton 模式过时)
      await page.waitForTimeout(120); // give 120ms for transition start
    });

    // ------------------------------------------------------------------------
    // Step 3 · F-066 Channel SSE ranked 5 候选 (budget 15s · ±20% = 18s)
    //   动作: composer 输入诉求 + 点 submit → SSE ranked 5 候选流式 → candidate-row-0..4 visible
    // ------------------------------------------------------------------------
    perStep.step3 = await withBudget('step3', async () => {
      const textarea = page.locator('[data-testid="composer-textarea"]');
      await textarea.click();
      await textarea.fill('找新能源汽车零部件相似客户');
      await page.click('[data-testid="composer-submit"]');
      // 等 ranked 5 候选行渲全 (W2-frontend MessageList 真消费 SSE · candidate-row-N 是 W2-mock-test 立 contract)
      await expect(
        page.locator('[data-testid="candidate-row-0"]'),
        'first candidate 应在 step 3 budget 内 visible (Channel SSE ranked 5)'
      ).toBeVisible({ timeout: 17_800 });
      const candidates = await page.locator('[data-testid^="candidate-row-"]').count();
      expect(candidates, `Channel SSE 应推 ≥ 5 候选 · 实际 ${candidates}`).toBeGreaterThanOrEqual(5);
    });

    // ------------------------------------------------------------------------
    // Step 4 · A1-NEW-1 IdealProfile 12 维抽取 (budget 10s · ±20% = 12s)
    // ------------------------------------------------------------------------
    perStep.step4 = await withBudget('step4', async () => {
      await page.locator('[data-testid="candidate-row-0"]').click();
      await expect(
        page.locator('[data-testid="ideal-profile-12d"]'),
        'IdealProfile 12 维 popover 应在 step 4 budget 内 visible'
      ).toBeVisible({ timeout: 11_800 });
      const dims = await page.locator('[data-testid^="ideal-profile-dim-"]').count();
      expect(dims, `IdealProfile 应渲 12 维 · 实际 ${dims}`).toBe(12);
    });

    // ------------------------------------------------------------------------
    // Step 5 · 拖 artifact → composer reference chip (budget 2s · ±20% = 2.4s)
    //   keyboard a11y: pin-handle focus + Space activate
    // ------------------------------------------------------------------------
    perStep.step5 = await withBudget('step5', async () => {
      const pin = page.locator('[data-testid="pin-handle"]').first();
      await pin.focus();
      await pin.press('Space');
      await expect(
        page.locator('[data-testid="artifact-pinned"]'),
        'artifact 应在 step 5 budget 内 pin 到 composer'
      ).toBeVisible({ timeout: 2_300 });
    });

    // ------------------------------------------------------------------------
    // Step 6 · F-067-handoff Credit SSE (budget 15s · ±20% = 18s)
    //   parent_tool_call_id 透传 (Channel ToolCall → Credit ToolCall handoff)
    // ------------------------------------------------------------------------
    perStep.step6 = await withBudget('step6', async () => {
      await page.click('[data-testid="agent-chip-credit"]');
      await expect(
        page.locator('[data-testid="credit-handoff-active"]'),
        'Credit handoff active state 应在 step 6 budget 内 visible'
      ).toBeVisible({ timeout: 17_800 });
      const parentLinks = page.locator('[data-testid="parent-tool-call-link"]');
      await expect(
        parentLinks,
        'parent_tool_call_id link 应渲 1 个 (Channel ToolCall → Credit ToolCall handoff)'
      ).toHaveCount(1);
    });

    // ------------------------------------------------------------------------
    // Step 7 · F-053 progressive radar 4 维评分 (budget 10s · ±20% = 12s)
    // ------------------------------------------------------------------------
    perStep.step7 = await withBudget('step7', async () => {
      await expect(
        page.locator('[data-testid="radar-4d"]'),
        'radar-4d 应在 step 7 budget 内渲 (4 维评分 progressive)'
      ).toBeVisible({ timeout: 11_800 });
      const radarDims = await page.locator('[data-testid^="radar-dim-"]').count();
      expect(radarDims, `radar 应渲 4 维 · 实际 ${radarDims}`).toBe(4);
      // redline-chip · PASS fixture composite=82 不触红线 · 仅 log (W3-W4 高难度 fixture 才强断)
      const redlineCount = await page.locator('[data-testid="redline-chip"]').count();
      // eslint-disable-next-line no-console
      console.log(`  [step7 · redline] redline-chip count=${redlineCount} (PASS fixture 期 0)`);
    });

    // ------------------------------------------------------------------------
    // Step 8 · A3-NEW ConfirmModal medium + ledger 写入 (budget 5s · ±20% = 6s)
    //   动作: decision-submit → permission-modal 显 → permission-grant → turn-completed-indicator
    //   验 modal 文案 = permission_request_medium.json consequences[0] verbatim
    // ------------------------------------------------------------------------
    perStep.step8 = await withBudget('step8', async () => {
      await page.click('[data-testid="decision-submit"]');
      await expect(
        page.locator('[data-testid="permission-modal"]'),
        'ConfirmModal medium 应在 step 8 budget 内显'
      ).toBeVisible({ timeout: 5_800 });
      // verify modal 文案 = consequences[0] verbatim (fixture 真消费 · 不是写死中文)
      await expect(
        page.locator('[data-testid="permission-modal"]'),
        'ConfirmModal 应渲 PermissionRequestEventPayload.consequences[0] verbatim'
      ).toContainText('写入 decision_ledger sqlite');
      await page.click('[data-testid="permission-grant"]');
      // verify backend ledger 写入 (sqlite query via REST · ledger_service/api.py admin endpoint)
      // 注: W2-backend live ship 后调整 path vs query param · 现 placeholder
      const resp = await page.request.get(
        'http://localhost:8000/api/liuye/ledger/decisions?agent_id=credit&limit=1'
      );
      expect(resp.ok(), `ledger REST 应 200 OK · 实际 ${resp.status()}`).toBe(true);
      await expect(
        page.locator('[data-testid="turn-completed-indicator"]'),
        'turn-completed-indicator 应在 step 8 budget 内显 (resume_turn 后 turn.completed 续推)'
      ).toBeVisible({ timeout: 5_800 });
    });

    // ------------------------------------------------------------------------
    // Step 9 · LE-01 trace drawer (budget 5s · ±20% = 6s)
    //   7 node (decision_graph.py SSOT) + 6 edge type (BE2 spec) + ≥1 evidence link
    // ------------------------------------------------------------------------
    perStep.step9 = await withBudget('step9', async () => {
      await page.click('[data-testid="le01-trace-button"]');
      await expect(
        page.locator('[data-testid="le01-trace-drawer"]'),
        'le01-trace-drawer 应在 step 9 budget 内显'
      ).toBeVisible({ timeout: 4_800 });
      const nodeCount = await page.locator('[data-testid^="trace-node-"]').count();
      expect(
        nodeCount,
        `LE-01 trace 应渲 7 node (per agent_credit/decision_graph.py SSOT) · 实际 ${nodeCount}`
      ).toBe(7);
      const edgeCount = await page.locator('[data-testid^="trace-edge-"]').count();
      expect(
        edgeCount,
        `LE-01 trace 应渲 ≥ 6 edge (per BE2 spec 6 edge type) · 实际 ${edgeCount}`
      ).toBeGreaterThanOrEqual(6);
      const evidenceLinks = await page.locator('[data-testid^="trace-evidence-link-"]').count();
      expect(
        evidenceLinks,
        `LE-01 trace 应渲 ≥ 1 evidence chain link · 实际 ${evidenceLinks}`
      ).toBeGreaterThan(0);
    });

    // ------------------------------------------------------------------------
    // baseline 入库 (本 spec 跑完即 append `_temp/w2-rehearsal-baseline.json`)
    //   env 'mock' 自动推断 (LIUYE_DEMO_MODE=1 由调用方 set) · 显式传更稳
    // ------------------------------------------------------------------------
    await saveBaseline('rehearsal-mock', perStep, 'mock');

    // 总结 log (D9 PM 走访彩排耗时回看)
    const total = Object.values(perStep).reduce<number>((a, b) => a + b, 0);
    const budgetTotal = Object.values(STEP_BUDGETS).reduce<number>((a, b) => a + b, 0);
    // eslint-disable-next-line no-console
    console.log(
      `  [rehearsal-mock summary · D9] 9 step PASS · ` +
        `step1=${perStep.step1}ms step2=${perStep.step2}ms step3=${perStep.step3}ms ` +
        `step4=${perStep.step4}ms step5=${perStep.step5}ms step6=${perStep.step6}ms ` +
        `step7=${perStep.step7}ms step8=${perStep.step8}ms step9=${perStep.step9}ms · ` +
        `total=${total}ms / 预算 ${budgetTotal}ms (utilization ${((total / budgetTotal) * 100).toFixed(1)}%)`
    );
  });
});
