/**
 * W2-mock-test · 第 2 棒 · 2026-05-12
 * demo-path-step4-9.spec.ts · demo path step 4-9 (扩 W1 step 1-3 至完整 9 step 70s)
 *
 * 本棒 (第 2 棒) 仅落 step 4-7 (4 个 step) · step 8-9 留第 3 棒
 *   (step 8 需 PermissionRequest fixture medium · step 9 需 LE-01 trace UI · 都依赖第 3 棒交付).
 *
 * SSOT: W2-mock-test brief §3 file checklist + §4.1 9 step 70s 时间预算 + §4.2 step-budget utility
 * 引用:
 *   - v3 spec §6.3 demo path 70s 9 step + §10 视觉硬线 + 附录 C 应急
 *   - W1 demo-path-step1-3.spec.ts (同模式: mock SSE health probe + skipIf + test.step 计时)
 *   - shared/contracts/liuye/schemas/liuye_chat_event.schema.json (11 event SSOT · W1 contract 已 lock)
 *
 * 9 step 预算 (v3 §6.3):
 *   step1 静默首页 (3s · W1 实做)
 *   step2 点 chip (1s · W1 实做)
 *   step3 Channel SSE ranked 5 (15s · W1 实做)
 *   step4 IdealProfile 12 维 (10s · 本棒)             ← step 4-7 本棒落
 *   step5 拖 artifact → composer ref chip (2s · 本棒)
 *   step6 Credit handoff SSE (15s · 本棒)
 *   step7 progressive radar 4 维 (10s · 本棒)
 *   step8 confirm modal 提交并上链 (5s · 第 3 棒)
 *   step9 LE-01 trace modal (5s · 第 3 棒)
 *
 * Mock SSE 启动前置 (调用方负责 · 本 spec 不自启):
 *   cd tests
 *   npm run mock-sse:channel    # :8001 · channel_5candidates.json
 *   npm run mock-sse:credit     # :8002 · credit_decision_PASS.json
 *   npm run mock-sse:report     # :8003 · report_v16_PARTIAL.json (本棒 step 4-7 不直接消费 · step 6 credit 消费)
 *
 * Skip 条件:
 *   - frontend dev :3210 不可达 → 全 spec skip (per W1 demo-path-step1-3 模式 · webServer disabled)
 *   - mock SSE :8001 (channel) 或 :8002 (credit) 不可达 → 标 test.skip (per brief §4.7 globalSetup probe)
 *
 * data-testid 命名契约 (本 spec 引入 · W2-frontend worker 据此实做):
 *   step 4: candidate-row-0 · ideal-profile-12d · ideal-profile-dim-{0..11}
 *   step 5: pin-handle · artifact-pinned
 *   step 6: credit-handoff-active · parent-tool-call-link
 *   step 7: radar-4d · radar-dim-{financial,industry,operation,guarantee} · redline-chip
 * (W2-frontend brief §4 已锁 permission-modal / permission-drawer / fallback-banner / evidence-ref-row · 本 spec 不重复)
 *
 * Hidden gotcha (第 2 棒 record):
 *   - W2-frontend 同 W2 并行 · W1 frontend skeleton 现 page.tsx 仅 console.log + 4 chip 渲 · step 4-7 真渲组件未到位 ·
 *     本 spec 真断言会失败 · 调用方应 SKIP_DEMO_STEP4_9=1 跳过 · 或 W2-frontend ship 后 unset 跑全验.
 *   - step 6 Credit handoff 真路径依赖 W2-backend live mode + W2-frontend useLiuyeBridge hook 接通 ·
 *     mock SSE :8002 仅吐 SSE event (老 v1.0 7 event) · adapter 在 backend (W1 sse_v1_to_liuye.py) ·
 *     本 spec 不直接消费 mock SSE · 只 probe alive · 真消费走 frontend useLiuyeBridge → backend BFF.
 *   - parent_tool_call_id 透传验证留 step 6: ToolCallCard 内部数据属性 (frontend brief §4.1 mapping tool.started event) ·
 *     本 spec selector [data-testid="parent-tool-call-link"] 是 W2-frontend ToolCallCard 内显示 parent_tool_call_id link 元素.
 */
import { test, expect, type Page } from '@playwright/test';
import { withBudget, saveBaseline } from '../../perf/step-budget';

// ============================================================================
// Mock SSE health probe (复用 W1 demo-path-step1-3 模式)
// ============================================================================
const MOCK_SSE_CHANNEL_HEALTH = 'http://localhost:8001/health';
const MOCK_SSE_CREDIT_HEALTH = 'http://localhost:8002/health';

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
// Tests
// ============================================================================

test.describe('demo path step 4-9 (本棒落 step 4-7 · step 8-9 留第 3 棒)', () => {
  test.skip(
    process.env.SKIP_DEMO_STEP4_9 === '1',
    'SKIP_DEMO_STEP4_9=1 set · W2-frontend 真渲组件未到位时跳过 · ship 后 unset'
  );

  test('step 4-7 跑通 + 各 step ±20% gate + baseline 入库', async ({ page }) => {
    // ------------------------------------------------------------------------
    // 前置: probe mock SSE (任一不可达 → skip · 不 fail · 与 W1 第 5 棒一致)
    // ------------------------------------------------------------------------
    const channelAlive = await isMockSseAlive(page, MOCK_SSE_CHANNEL_HEALTH, 'channel');
    const creditAlive = await isMockSseAlive(page, MOCK_SSE_CREDIT_HEALTH, 'credit');
    if (!channelAlive || !creditAlive) {
      // eslint-disable-next-line no-console
      console.log(
        `  [skip] mock SSE :8001 alive=${channelAlive} · :8002 alive=${creditAlive} · 请先 'cd tests && npm run mock-sse:channel' + 'npm run mock-sse:credit'`
      );
      test.skip(true, 'mock SSE :8001 (channel) 或 :8002 (credit) 未起 · 跑前需 npm run mock-sse:channel + mock-sse:credit');
      return;
    }

    // baseline 累积 (本 spec 跑完 saveBaseline 一次性写)
    const perStep: Record<string, number> = {};

    // ------------------------------------------------------------------------
    // 前置: 走完 W1 step 1-3 (静默首页 → 点 channel chip → SSE ranked 5)
    //   W1 demo-path-step1-3 真细节已 verify · 本 spec 仅快速走到 step 3 完成态
    //   不重复 W1 断言 (那是 step1-3.spec 的 scope · 本 spec 仅串前置上下文)
    // ------------------------------------------------------------------------
    await test.step('precondition · 走完 step 1-3 (前置 channel SSE ranked 5)', async () => {
      await page.goto('/', { waitUntil: 'domcontentloaded' });
      // step 1 短 wait: hero 静态可见
      await page.waitForSelector('[data-testid="hero-static"]', { state: 'visible', timeout: 5000 });
      // step 2 点 channel chip
      await page.getByTestId('agent-chip-channel').click();
      // step 3 等 ranked 5 候选 渲 (候选行 0 出现 = SSE ranked 5 完成 · per W2-frontend MessageList 真消费)
      //   timeout 18s = step 3 hard gate · 走完即进 step 4
      await page.waitForSelector('[data-testid="candidate-row-0"]', { state: 'visible', timeout: 18_000 });
    });

    // ------------------------------------------------------------------------
    // Step 4 · A1-NEW-1 IdealProfile 12 维抽取 (budget 10s · ±20% = 12s)
    //
    //   动作: 点 first candidate row → IdealProfile 12 维 popover 显
    //   断言: ideal-profile-12d visible · 12 个 ideal-profile-dim-{0..11} 全在
    //   v3 §3 IdealProfile: 12 维抽取 (规模 / 行业 / 地域 / 经营 / 财务 / 信用 / 关系 / 履约 / 担保 / 行业景气 / 政策 / 风偏)
    //   W2-frontend 真渲: A1NEW 域组件 + LLM 12 维 progressive section (后续棒 ship)
    // ------------------------------------------------------------------------
    perStep.step4 = await withBudget('step4', async () => {
      await page.getByTestId('candidate-row-0').click();
      // budget 10s · 取 wait 12s 接近 hard gate (留 200ms 给后续 assertion + log)
      await expect(page.getByTestId('ideal-profile-12d'), 'IdealProfile 12 维 popover 应在 budget 内显').toBeVisible({
        timeout: 11_800,
      });
      // verify 12 个维度 cell 全在 (per W2-frontend ideal-profile-dim-<idx> 命名契约)
      const dims = await page.locator('[data-testid^="ideal-profile-dim-"]').count();
      expect(dims, `IdealProfile 应渲 12 维 · 实际 ${dims}`).toBe(12);
    });

    // ------------------------------------------------------------------------
    // Step 5 · 拖 artifact → composer reference chip (budget 2s · ±20% = 2.4s)
    //
    //   动作: keyboard a11y · pin-handle focus + Space activate → artifact pin 到 composer
    //   断言: artifact-pinned visible
    //   v3 §10 + W2-frontend brief §4.7 PinHandle: Space/Enter activate · a11y mode
    //   (鼠标拖拽 Playwright 难复现 IME-OS · 用 keyboard activate 替代 · per W1 IME guard 同模式)
    // ------------------------------------------------------------------------
    perStep.step5 = await withBudget('step5', async () => {
      const pin = page.getByTestId('pin-handle').first();
      await pin.focus();
      await pin.press('Space');
      // budget 2s · ±20% = 2.4s
      await expect(page.getByTestId('artifact-pinned'), 'artifact 应在 budget 内 pin 到 composer').toBeVisible({
        timeout: 2_300,
      });
    });

    // ------------------------------------------------------------------------
    // Step 6 · F-067-handoff Credit SSE (budget 15s · ±20% = 18s)
    //
    //   动作: 点 credit chip → Credit handoff active · 起新 turn ·
    //         parent_tool_call_id 透传 (Channel ToolCall → Credit ToolCall handoff)
    //   断言: credit-handoff-active visible · parent-tool-call-link count == 1
    //   v3 §2.2 + matrix §4: tool.started event payload.parent_tool_call_id (W1 contract schema 已 lock)
    //   W2-frontend 真渲: ToolCallCard 内显示 parent_tool_call_id link → 点击跳到 parent ToolCall
    //   W2-backend 真路径: liuye_service/adapters/credit.py 透传 (W2-backend §4.1)
    //
    //   注: 本棒 mock SSE :8002 吐 老 v1.0 7 event · adapter 在 backend · frontend 消费 11 event ·
    //       真路径走 BFF :8000 (W2-backend live mode 同 W2 并行 · 未 ship 时 step 6 真断言会失败 · SKIP_DEMO_STEP4_9=1)
    // ------------------------------------------------------------------------
    perStep.step6 = await withBudget('step6', async () => {
      await page.getByTestId('agent-chip-credit').click();
      // budget 15s · ±20% = 18s
      await expect(
        page.getByTestId('credit-handoff-active'),
        'Credit handoff active state 应在 budget 内显 (turn.started + tool.started 真路径)'
      ).toBeVisible({ timeout: 17_800 });
      // parent_tool_call_id link · 必有 1 (Channel → Credit handoff inheritance)
      const parentLinks = page.getByTestId('parent-tool-call-link');
      await expect(parentLinks, 'parent_tool_call_id link 应渲 1 个 (Channel ToolCall → Credit ToolCall handoff)').toHaveCount(
        1
      );
    });

    // ------------------------------------------------------------------------
    // Step 7 · F-053 progressive radar 4 维评分 + 红线提示 (budget 10s · ±20% = 12s)
    //
    //   动作: 等 Credit SSE 推完 4 维评分 → radar 4d 渲 · 红线 (composite < 60) chip 渲 (deterministic in 难度分层 fixture)
    //   断言: radar-4d visible · radar-dim-{financial,industry,operation,guarantee} 4 个全在
    //   v3 §4 F-053 progressive radar · agent_credit/scoring_model_corporate.py 4 维 (财务 industry_peer_gap 等)
    //   红线 chip: composite score < 60 触发 (per agent_credit/scoring) ·
    //     难度分层 fixture (credit_decision_PASS.json) score=82 PASS · 无红线 · 故 redline-chip count 期 0
    //     (本 spec 不强断言 redline · 仅 log · W3-W4 跑高难度 fixture 时验红线 deterministic)
    // ------------------------------------------------------------------------
    perStep.step7 = await withBudget('step7', async () => {
      await expect(page.getByTestId('radar-4d'), 'radar-4d 应在 budget 内渲 (4 维评分 progressive)').toBeVisible({
        timeout: 11_800,
      });
      // 4 维 dim 全在 (per scoring_model_corporate.py 财务 / 行业 / 经营 / 担保)
      const radarDims = await page.locator('[data-testid^="radar-dim-"]').count();
      expect(radarDims, `radar 应渲 4 维 · 实际 ${radarDims}`).toBe(4);
      // 红线 chip · 当前 fixture credit_decision_PASS score=82 · 不触发红线 · count 期 0
      // (W3-W4 高难度 fixture composite < 60 时验 redline · 本 spec 仅 log status · 不强断)
      const redlineCount = await page.getByTestId('redline-chip').count();
      // eslint-disable-next-line no-console
      console.log(`  [step7 · redline] redline-chip count=${redlineCount} (PASS fixture 期 0 · 高难度 fixture 期 ≥1)`);
    });

    // ------------------------------------------------------------------------
    // step 8 · step 9 · 留第 3 棒 (需 PermissionRequest fixture medium + LE-01 trace UI)
    // ------------------------------------------------------------------------

    // ------------------------------------------------------------------------
    // baseline 入库 (本 spec 跑完即写 · 跨 spec append `_temp/w2-rehearsal-baseline.json` · 第 8-10 棒 rehearsal-* spec 续 append)
    // ------------------------------------------------------------------------
    await saveBaseline('demo-path-step4-9', perStep);

    // 总结 log (PM 走访彩排耗时回看用)
    const total = Object.values(perStep).reduce<number>((a, b) => a + b, 0);
    // eslint-disable-next-line no-console
    console.log(
      `  [demo-path step 4-7 summary] step4=${perStep.step4}ms · step5=${perStep.step5}ms · step6=${perStep.step6}ms · step7=${perStep.step7}ms · total=${total}ms · 预算 ${10000 + 2000 + 15000 + 10000}ms`
    );
  });
});
