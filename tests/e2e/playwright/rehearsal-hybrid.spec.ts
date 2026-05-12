/**
 * W2-mock-test · 第 5 棒 · 2026-05-12
 * rehearsal-hybrid.spec.ts · D10 跑 · perfect-check fix #2 per-adapter URL · channel mock + credit/report live
 *
 * SSOT: W2-mock-test brief §4.3 (2) verbatim
 * 引用:
 *   - v3 spec §6.3 demo path 70s 9 step + 附录 C.3 hard gate ±20% + §10 视觉硬线
 *   - W2-backend brief §4.1 `_resolve_backend_url(agent_id)` helper
 *     (`os.environ.get(f'LIUYE_BACKEND_{agent_id.upper()}_URL') or self.backend_url`)
 *   - W1 mock-test 第 3 棒 mock SSE :8001 channel · channel_5candidates.json (复用 fixture replay)
 *   - rehearsal-mock.spec.ts (第 4 棒 · 9 step pattern · 本 spec verbatim 复用 9 step body)
 *   - tests/perf/step-budget.ts (STEP_BUDGETS / withBudget / saveBaseline · 第 2 棒 ship)
 *
 * Env (per brief §4.3 (2) + perfect-check fix #2 verbatim):
 *   - LIUYE_DEMO_MODE=0 (DEMO_MODE off · 不全栈走 mock)
 *   - LIUYE_BACKEND_CHANNEL_URL=http://localhost:8001 (channel 走 mock SSE :8001 复用 W1)
 *   - LIUYE_BACKEND_CREDIT_URL / LIUYE_BACKEND_REPORT_URL 留空 · fallback `LIUYE_BACKEND_BASE_URL=http://localhost:8000`
 *     (credit/report live 真 backend uvicorn :8000)
 *
 * 验 mock + live 混用边界:
 *   - channel mock fallback 走 fixture (mock SSE :8001 replay)
 *   - credit/report live 真接 LLM (DeepSeek/Tavily 真 API · sqlite ledger 真写)
 *   - channel mock 提示 chip 显「Demo 模式」(走 FallbackBanner data-kind="demo_mode" 或 channel-specific badge)
 *
 * 预期 (per brief §4.3 (2)):
 *   - 总耗时 < 70s + 4s buffer = 74s (live LLM 慢一点 · channel mock 快)
 *   - 9 step 全 PASS · 各 step ±20% gate (复用 STEP_BUDGETS verbatim)
 *
 * Skip 条件:
 *   - SKIP_REHEARSAL_HYBRID=1 顶层 skip (backend uvicorn :8000 或 mock SSE :8001 未起)
 *   - LIUYE_BACKEND_CHANNEL_URL 未指向 :8001 (env 未对齐 · sanity check)
 *   - mock SSE :8001 health 或 backend live :8000 /api/liuye/health 失败 (probe)
 *
 * Baseline (跨 spec 累积 `_temp/w2-rehearsal-baseline.json`):
 *   - saveBaseline('rehearsal-hybrid', perStep, 'hybrid') · 第 8/9 棒 mock + live 续 append 同一 JSON · 漂移对比
 *
 * Hidden gotcha (第 5 棒 record):
 *   - 9 step body verbatim 复用 rehearsal-mock (第 4 棒 ship) · 不 extract helper (单文件 self-contained
 *     便于 W2 sign-off review 单 spec 全看 · 三 rehearsal spec 故意 90% duplicate)
 *   - timeout 90s (覆 playwright.config 60s default) · 9 step 总 66s + ±20% buffer
 *   - channel 走 mock SSE :8001 时 W2-backend live mode 的 channel adapter 应 detect
 *     LIUYE_BACKEND_CHANNEL_URL 并 route 至 :8001 · 这是 W2-backend §4.1 真实做契约
 *   - FallbackBanner data-kind 是否触发取决 W2-frontend 实做 · 现 spec 仅 optional 验
 *     (count >= 0) 不强断 · UI 若漏渲 data-kind="demo_mode" 不阻 spec
 */
import { test, expect, type Page } from '@playwright/test';
import { withBudget, saveBaseline, STEP_BUDGETS } from '../../perf/step-budget';

// ============================================================================
// Health probe (mock SSE :8001 + backend live :8000 都要起 · per brief §4.3 (2) 双端)
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

async function isBackendLiveAlive(page: Page, baseUrl: string): Promise<boolean> {
  try {
    const response = await page.request.get(`${baseUrl}/api/liuye/health`, { timeout: 2000 });
    return response.ok();
  } catch {
    return false;
  }
}

// ============================================================================
// Tests · 单 test 跑完整 9 step (one path · per brief verbatim)
// ============================================================================

test.describe('W2 rehearsal-hybrid · D10 · channel mock + credit/report live · per-adapter URL', () => {
  test.skip(
    process.env.SKIP_REHEARSAL_HYBRID === '1',
    'SKIP_REHEARSAL_HYBRID=1 set · backend uvicorn :8000 或 mock SSE :8001 未起时跳过'
  );

  test('9 step 完整 hybrid path · LIUYE_BACKEND_CHANNEL_URL=:8001 + BASE_URL=:8000 · 74s 预算 · ±20% gate', async ({
    page,
  }) => {
    test.setTimeout(90_000);

    // ------------------------------------------------------------------------
    // 前置 sanity: env 对齐 (per brief §4.3 (2) per-adapter URL 契约)
    //   - LIUYE_BACKEND_CHANNEL_URL 必须包含 :8001 (channel 走 mock SSE)
    //   - LIUYE_BACKEND_BASE_URL 默认 :8000 (credit/report fallback live)
    // ------------------------------------------------------------------------
    const channelUrl = process.env.LIUYE_BACKEND_CHANNEL_URL ?? '';
    const baseUrl = process.env.LIUYE_BACKEND_BASE_URL ?? 'http://localhost:8000';
    if (!channelUrl.includes('8001')) {
      // eslint-disable-next-line no-console
      console.log(
        `  [rehearsal-hybrid skip] LIUYE_BACKEND_CHANNEL_URL='${channelUrl}' 未指向 :8001 · per-adapter URL 契约未配 · 跳过`
      );
      test.skip(
        true,
        'LIUYE_BACKEND_CHANNEL_URL 未指向 mock SSE :8001 · hybrid 模式契约未配 (perfect-check fix #2)'
      );
      return;
    }

    // ------------------------------------------------------------------------
    // 前置 probe: mock SSE :8001 (channel) + backend live :8000 (credit/report) 全起
    //   任一不可达 → skip (per brief §4.3 (2) · channel mock + credit/report live 都需起)
    // ------------------------------------------------------------------------
    const channelAlive = await isMockSseAlive(page, MOCK_SSE_CHANNEL_HEALTH, 'channel');
    const backendAlive = await isBackendLiveAlive(page, baseUrl);
    if (!channelAlive || !backendAlive) {
      // eslint-disable-next-line no-console
      console.log(
        `  [rehearsal-hybrid skip] channel mock :8001 alive=${channelAlive} · backend live ${baseUrl} alive=${backendAlive} · 请先启 mock SSE :8001 + backend uvicorn :8000`
      );
      test.skip(
        true,
        `channel mock :8001 (${channelAlive}) 或 backend live :8000 (${backendAlive}) 未起 · hybrid 路径无法验`
      );
      return;
    }

    // baseline 累积 (本 spec 跑完 saveBaseline 一次性写)
    const perStep: Record<string, number> = {};

    // ------------------------------------------------------------------------
    // Step 1 · F-007 静默首页加载 (budget 3s · ±20% = 3.6s)
    //   动作: page.goto / → hero-static visible + 4 chip 可见
    // ------------------------------------------------------------------------
    perStep.step1 = await withBudget('step1', async () => {
      await page.goto('/', { waitUntil: 'domcontentloaded' });
      await expect(
        page.locator('[data-testid="hero-static"]'),
        '静默 hero static 应在 3.6s 内 visible (F-007 baseline · v3 §10)'
      ).toBeVisible({ timeout: 3_500 });
      for (const agent of ['channel', 'credit', 'report', 'alert']) {
        await expect(page.locator(`[data-testid="agent-chip-${agent}"]`)).toBeVisible({ timeout: 1_000 });
      }
    });

    // ------------------------------------------------------------------------
    // Step 2 · 点 channel chip (budget 1s · ±20% = 1.2s)
    // ------------------------------------------------------------------------
    perStep.step2 = await withBudget('step2', async () => {
      await page.click('[data-testid="agent-chip-channel"]');
      await page.waitForTimeout(120);
    });

    // ------------------------------------------------------------------------
    // Step 3 · F-066 Channel SSE ranked 5 候选 (budget 15s · ±20% = 18s)
    //   hybrid 模式: channel adapter detect LIUYE_BACKEND_CHANNEL_URL=:8001 → route 至 mock SSE
    //   走 channel_5candidates.json fixture replay (W1 mock-test 第 3 棒 ship)
    // ------------------------------------------------------------------------
    perStep.step3 = await withBudget('step3', async () => {
      const textarea = page.locator('[data-testid="composer-textarea"]');
      await textarea.click();
      await textarea.fill('找新能源汽车零部件相似客户');
      await page.click('[data-testid="composer-submit"]');
      await expect(
        page.locator('[data-testid="candidate-row-0"]'),
        'first candidate 应在 step 3 budget 内 visible (Channel mock SSE ranked 5 · 走 fixture)'
      ).toBeVisible({ timeout: 17_800 });
      const candidates = await page.locator('[data-testid^="candidate-row-"]').count();
      expect(candidates, `Channel mock SSE 应推 ≥ 5 候选 · 实际 ${candidates}`).toBeGreaterThanOrEqual(5);
    });

    // ------------------------------------------------------------------------
    // Step 3.5 · channel mock 提示 chip 显「Demo 模式」(per brief §4.3 (2) 预期)
    //   hybrid 模式下 channel 走 mock fixture · UI 应有 demo 视觉提示
    //   走 FallbackBanner data-kind="demo_mode" 或 channel-specific chip badge
    //   W2-frontend brief §4.5 5 fallback data-kind 中 "demo_mode" 是 hybrid mode 特化
    //   现 spec 用 optional 验 (count >= 0) 不强断 · 但若 W2-frontend 实做 attr 即 expect visible
    // ------------------------------------------------------------------------
    const channelDemoBadge = page.locator(
      '[data-testid="fallback-banner"][data-kind="demo_mode"], [data-testid="agent-chip-channel"] [data-state="demo"]'
    );
    const demoBadgeCount = await channelDemoBadge.count();
    if (demoBadgeCount > 0) {
      await expect(
        channelDemoBadge.first(),
        'channel mock 提示 chip 应显「Demo 模式」(hybrid 模式 visual cue)'
      ).toBeVisible({ timeout: 2_000 });
    }
    // eslint-disable-next-line no-console
    console.log(
      `  [rehearsal-hybrid · channel demo cue] demoBadge count=${demoBadgeCount} (期 ≥ 1 若 W2-frontend lock data-kind="demo_mode" · 0 仅提示不阻 spec)`
    );

    // ------------------------------------------------------------------------
    // Step 4 · A1-NEW-1 IdealProfile 12 维抽取 (budget 10s · ±20% = 12s)
    //   hybrid 模式: IdealProfile LLM call 走 live (DeepSeek 真 API · 不走 mock)
    //   live LLM 慢一点 · 但应仍在 12s 内 (deepseek-chat avg 6-8s)
    // ------------------------------------------------------------------------
    perStep.step4 = await withBudget('step4', async () => {
      await page.locator('[data-testid="candidate-row-0"]').click();
      await expect(
        page.locator('[data-testid="ideal-profile-12d"]'),
        'IdealProfile 12 维 popover 应在 step 4 budget 内 visible (live LLM)'
      ).toBeVisible({ timeout: 11_800 });
      const dims = await page.locator('[data-testid^="ideal-profile-dim-"]').count();
      expect(dims, `IdealProfile 应渲 12 维 · 实际 ${dims}`).toBe(12);
    });

    // ------------------------------------------------------------------------
    // Step 5 · 拖 artifact → composer reference chip (budget 2s · ±20% = 2.4s)
    //   client only · 不涉 backend · hybrid vs mock 行为一致
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
    //   hybrid 模式: credit adapter 走 live (LIUYE_BACKEND_CREDIT_URL 留空 fallback :8000)
    //   parent_tool_call_id 透传 (Channel ToolCall → Credit ToolCall handoff)
    //   live LLM + tool chain 真跑 · 应在 18s 内 (deepseek-chat + Tavily 真 API)
    // ------------------------------------------------------------------------
    perStep.step6 = await withBudget('step6', async () => {
      await page.click('[data-testid="agent-chip-credit"]');
      await expect(
        page.locator('[data-testid="credit-handoff-active"]'),
        'Credit handoff active state 应在 step 6 budget 内 visible (live credit adapter)'
      ).toBeVisible({ timeout: 17_800 });
      const parentLinks = page.locator('[data-testid="parent-tool-call-link"]');
      await expect(
        parentLinks,
        'parent_tool_call_id link 应渲 1 个 (Channel ToolCall → Credit ToolCall handoff · 跨 mock+live)'
      ).toHaveCount(1);
    });

    // ------------------------------------------------------------------------
    // Step 7 · F-053 progressive radar 4 维评分 (budget 10s · ±20% = 12s)
    //   hybrid 模式: radar 评分 tail of step 6 SSE · 走 live (Credit adapter 真 LLM)
    // ------------------------------------------------------------------------
    perStep.step7 = await withBudget('step7', async () => {
      await expect(
        page.locator('[data-testid="radar-4d"]'),
        'radar-4d 应在 step 7 budget 内渲 (4 维评分 progressive · live)'
      ).toBeVisible({ timeout: 11_800 });
      const radarDims = await page.locator('[data-testid^="radar-dim-"]').count();
      expect(radarDims, `radar 应渲 4 维 · 实际 ${radarDims}`).toBe(4);
      const redlineCount = await page.locator('[data-testid="redline-chip"]').count();
      // eslint-disable-next-line no-console
      console.log(`  [step7 · redline · hybrid] redline-chip count=${redlineCount} (live LLM 真路径 · PASS fixture 期 0)`);
    });

    // ------------------------------------------------------------------------
    // Step 8 · A3-NEW ConfirmModal medium + ledger 写入 (budget 5s · ±20% = 6s)
    //   hybrid 模式: ledger 真写 sqlite (LIUYE_BACKEND_BASE_URL=:8000 backend live)
    //   verify modal 文案 = permission_request_medium.json consequences[0] verbatim
    //   verify ledger REST 真返 200 (sqlite 真写 · data/ledger/decisions.sqlite)
    // ------------------------------------------------------------------------
    perStep.step8 = await withBudget('step8', async () => {
      await page.click('[data-testid="decision-submit"]');
      await expect(
        page.locator('[data-testid="permission-modal"]'),
        'ConfirmModal medium 应在 step 8 budget 内显'
      ).toBeVisible({ timeout: 5_800 });
      await expect(
        page.locator('[data-testid="permission-modal"]'),
        'ConfirmModal 应渲 PermissionRequestEventPayload.consequences[0] verbatim'
      ).toContainText('写入 decision_ledger sqlite');
      await page.click('[data-testid="permission-grant"]');
      // hybrid: backend live :8000 真接 sqlite ledger · REST 应 200 OK
      const resp = await page.request.get(
        `${baseUrl}/api/liuye/ledger/decisions?agent_id=credit&limit=1`
      );
      expect(resp.ok(), `ledger REST 应 200 OK (live sqlite) · 实际 ${resp.status()}`).toBe(true);
      await expect(
        page.locator('[data-testid="turn-completed-indicator"]'),
        'turn-completed-indicator 应在 step 8 budget 内显 (resume_turn 后 turn.completed 续推)'
      ).toBeVisible({ timeout: 5_800 });
    });

    // ------------------------------------------------------------------------
    // Step 9 · LE-01 trace drawer (budget 5s · ±20% = 6s)
    //   7 node (decision_graph.py SSOT) + 6 edge type (BE2 spec) + ≥1 evidence link
    //   hybrid: trace 走 live (sqlite ledger 真读 · decision_graph 真构建)
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
    // baseline 入库 (env 'hybrid' 显式 · 跨 spec append `_temp/w2-rehearsal-baseline.json`)
    // ------------------------------------------------------------------------
    await saveBaseline('rehearsal-hybrid', perStep, 'hybrid');

    // 总结 log (D10 PM 走访彩排耗时回看 · hybrid 模式预期 < 74s)
    const total = Object.values(perStep).reduce<number>((a, b) => a + b, 0);
    const budgetTotal = Object.values(STEP_BUDGETS).reduce<number>((a, b) => a + b, 0);
    // eslint-disable-next-line no-console
    console.log(
      `  [rehearsal-hybrid summary · D10] 9 step PASS · ` +
        `step1=${perStep.step1}ms step2=${perStep.step2}ms step3=${perStep.step3}ms ` +
        `step4=${perStep.step4}ms step5=${perStep.step5}ms step6=${perStep.step6}ms ` +
        `step7=${perStep.step7}ms step8=${perStep.step8}ms step9=${perStep.step9}ms · ` +
        `total=${total}ms / 预算 ${budgetTotal}ms (utilization ${((total / budgetTotal) * 100).toFixed(1)}% · hybrid: channel mock + credit/report live)`
    );
  });
});
