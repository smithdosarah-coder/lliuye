/**
 * W2-mock-test · 第 5 棒 · 2026-05-12
 * rehearsal-live.spec.ts · D10 跑 · 3 adapter 全 live · Tavily + DeepSeek + sqlite 真路径
 *
 * SSOT: W2-mock-test brief §4.3 (3) verbatim
 * 引用:
 *   - v3 spec §6.3 demo path 70s 9 step + 附录 C.3 hard gate ±20% + §10 视觉硬线
 *   - W2-backend brief §4.1 `_resolve_backend_url(agent_id)` helper (LIUYE_BACKEND_BASE_URL fallback)
 *   - rehearsal-mock.spec.ts (第 4 棒 · 9 step pattern · 本 spec verbatim 复用 9 step body)
 *   - rehearsal-hybrid.spec.ts (第 5 棒 · hybrid 模式 · 本 spec env 反向 · 全 live)
 *   - tests/perf/step-budget.ts (STEP_BUDGETS / withBudget / saveBaseline · 第 2 棒 ship)
 *
 * Env (per brief §4.3 (3) verbatim):
 *   - LIUYE_DEMO_MODE=0 (DEMO_MODE off · 不走 mock)
 *   - LIUYE_BACKEND_BASE_URL=http://localhost:8000 (default · 3 adapter 全 fallback live)
 *   - LIUYE_BACKEND_CHANNEL_URL / LIUYE_BACKEND_CREDIT_URL / LIUYE_BACKEND_REPORT_URL 全留空
 *   - 3 adapter 全 live: Tavily 真 API + DeepSeek 真 API + sqlite ledger 真写
 *
 * 预期 (per brief §4.3 (3)):
 *   - 总耗时 < 70s + 4s buffer = 74s (live LLM 全栈跑)
 *   - 9 step 全 PASS · 各 step ±20% gate (复用 STEP_BUDGETS verbatim)
 *   - 5 应急流程不触 (live healthy · FallbackBanner count=0 sanity check)
 *
 * Skip 条件:
 *   - SKIP_REHEARSAL_LIVE=1 顶层 skip (backend uvicorn :8000 未起 或 Tavily/DeepSeek key 未配)
 *   - backend live :8000 /api/liuye/health 失败 (probe · isBackendAlive pattern per W1 mock-test)
 *
 * Baseline (跨 spec 累积 `_temp/w2-rehearsal-baseline.json`):
 *   - saveBaseline('rehearsal-live', perStep, 'live') · 与 mock/hybrid 三模式漂移对比
 *
 * Hidden gotcha (第 5 棒 record):
 *   - 9 step body verbatim 复用 rehearsal-mock + rehearsal-hybrid (三 rehearsal spec 故意 90% duplicate)
 *     · 单文件 self-contained 便于 W2 sign-off review (sub-agent 决策 copy 不 extract helper)
 *   - timeout 90s (覆 playwright.config 60s default) · 9 step 总 66s + ±20% buffer
 *   - LIUYE_DEMO_MODE=0 显式断言 (sanity · 防 env 漂)
 *   - 5 应急 sanity: 跑完 9 step 后断 FallbackBanner count == 0 (live healthy · 无 fallback 触发)
 *     不是断 0 → 触发 = bug · live 模式不应出 fallback (Tavily 真 / LLM 真 / sqlite 真都健康前提)
 *   - Tavily / DeepSeek API key 未配时 backend health 仍返 200 (key 校验在 adapter call 时) ·
 *     需 manual check (W3-W4 加 `/api/liuye/diagnostics` endpoint 暴露 key 是否配)
 */
import { test, expect, type Page } from '@playwright/test';
import { withBudget, saveBaseline, STEP_BUDGETS } from '../../perf/step-budget';

// ============================================================================
// Backend live health probe (per W1 mock-test isBackendAlive pattern)
// ============================================================================

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

test.describe('W2 rehearsal-live · D10 · 3 adapter 全 live · sanity check', () => {
  test.skip(
    process.env.SKIP_REHEARSAL_LIVE === '1',
    'SKIP_REHEARSAL_LIVE=1 set · backend uvicorn :8000 未起 或 Tavily/DeepSeek key 未配时跳过'
  );

  test('9 step 完整 live path · LIUYE_DEMO_MODE=0 · 3 adapter 全 live · 74s 预算 · ±20% gate · 5 应急不触 sanity', async ({
    page,
  }) => {
    test.setTimeout(90_000);

    // ------------------------------------------------------------------------
    // 前置 sanity: env 对齐 (per brief §4.3 (3) verbatim)
    //   - LIUYE_DEMO_MODE 必须为 '0' (live 模式 sanity 防 env 漂)
    // ------------------------------------------------------------------------
    const demoMode = process.env.LIUYE_DEMO_MODE ?? '';
    if (demoMode !== '0') {
      // eslint-disable-next-line no-console
      console.log(
        `  [rehearsal-live skip] LIUYE_DEMO_MODE='${demoMode}' 未设为 '0' · live 模式契约未对齐 · 跳过`
      );
      test.skip(
        true,
        `LIUYE_DEMO_MODE='${demoMode}' 不是 '0' · live 模式 sanity check 未满足 (brief §4.3 (3))`
      );
      return;
    }

    // ------------------------------------------------------------------------
    // 前置 probe: backend live :8000 health
    //   (Tavily/DeepSeek key 校验在 adapter call 时 · health 仅探 backend up · key 漏配跑到 step 3 才fail)
    // ------------------------------------------------------------------------
    const baseUrl = process.env.LIUYE_BACKEND_BASE_URL ?? 'http://localhost:8000';
    const backendAlive = await isBackendLiveAlive(page, baseUrl);
    if (!backendAlive) {
      // eslint-disable-next-line no-console
      console.log(
        `  [rehearsal-live skip] backend live ${baseUrl}/api/liuye/health 不可达 · 请先启 backend uvicorn :8000`
      );
      test.skip(true, `backend live ${baseUrl}/api/liuye/health 失败 · 3 adapter 全 live 无法验`);
      return;
    }

    // baseline 累积 (本 spec 跑完 saveBaseline 一次性写)
    const perStep: Record<string, number> = {};

    // ------------------------------------------------------------------------
    // Step 1 · F-007 静默首页加载 (budget 3s · ±20% = 3.6s)
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
    //   live 模式: channel adapter 走 Tavily 真 API · 真搜索 5 候选
    // ------------------------------------------------------------------------
    perStep.step3 = await withBudget('step3', async () => {
      const textarea = page.locator('[data-testid="composer-textarea"]');
      await textarea.click();
      await textarea.fill('找新能源汽车零部件相似客户');
      await page.click('[data-testid="composer-submit"]');
      await expect(
        page.locator('[data-testid="candidate-row-0"]'),
        'first candidate 应在 step 3 budget 内 visible (Channel live SSE · Tavily 真搜)'
      ).toBeVisible({ timeout: 17_800 });
      const candidates = await page.locator('[data-testid^="candidate-row-"]').count();
      expect(candidates, `Channel live SSE 应推 ≥ 5 候选 · 实际 ${candidates}`).toBeGreaterThanOrEqual(5);
    });

    // ------------------------------------------------------------------------
    // Step 4 · A1-NEW-1 IdealProfile 12 维抽取 (budget 10s · ±20% = 12s)
    //   live 模式: DeepSeek 真 API · 12 维抽取 progressive
    // ------------------------------------------------------------------------
    perStep.step4 = await withBudget('step4', async () => {
      await page.locator('[data-testid="candidate-row-0"]').click();
      await expect(
        page.locator('[data-testid="ideal-profile-12d"]'),
        'IdealProfile 12 维 popover 应在 step 4 budget 内 visible (DeepSeek 真 API)'
      ).toBeVisible({ timeout: 11_800 });
      const dims = await page.locator('[data-testid^="ideal-profile-dim-"]').count();
      expect(dims, `IdealProfile 应渲 12 维 · 实际 ${dims}`).toBe(12);
    });

    // ------------------------------------------------------------------------
    // Step 5 · 拖 artifact → composer reference chip (budget 2s · ±20% = 2.4s)
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
    //   live 模式: credit adapter 走 live (DeepSeek + Tavily + tool chain 真跑)
    //   parent_tool_call_id 透传 (Channel ToolCall → Credit ToolCall handoff)
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
        'parent_tool_call_id link 应渲 1 个 (Channel ToolCall → Credit ToolCall handoff · 全 live)'
      ).toHaveCount(1);
    });

    // ------------------------------------------------------------------------
    // Step 7 · F-053 progressive radar 4 维评分 (budget 10s · ±20% = 12s)
    //   live 模式: radar 评分 tail of step 6 SSE · DeepSeek 真 LLM 评 4 维
    // ------------------------------------------------------------------------
    perStep.step7 = await withBudget('step7', async () => {
      await expect(
        page.locator('[data-testid="radar-4d"]'),
        'radar-4d 应在 step 7 budget 内渲 (4 维评分 progressive · live LLM)'
      ).toBeVisible({ timeout: 11_800 });
      const radarDims = await page.locator('[data-testid^="radar-dim-"]').count();
      expect(radarDims, `radar 应渲 4 维 · 实际 ${radarDims}`).toBe(4);
      const redlineCount = await page.locator('[data-testid="redline-chip"]').count();
      // eslint-disable-next-line no-console
      console.log(`  [step7 · redline · live] redline-chip count=${redlineCount} (live 真 LLM 评 · 业务结果 deterministic 取决评分 vs 阈值)`);
    });

    // ------------------------------------------------------------------------
    // Step 8 · A3-NEW ConfirmModal medium + ledger 写入 (budget 5s · ±20% = 6s)
    //   live 模式: ledger 真写 sqlite (LIUYE_BACKEND_BASE_URL=:8000 backend live · data/ledger/decisions.sqlite)
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
      // live: backend uvicorn :8000 真接 sqlite ledger · REST 应 200 OK
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
    //   live: trace 走 live (sqlite ledger 真读 · decision_graph 真构建 · evidence_ref 真链)
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
    // 5 应急流程不触 sanity check (per brief §4.3 (3) verbatim 预期)
    //   live healthy 前提下 · FallbackBanner 不应渲任何 5 kind (tavily_quota / llm_provider /
    //   ledger_silent_fail / sse_conversion / network_offline) · count = 0 即 live 路径全健康
    //   若 > 0 = 某 adapter fall back · 即 live mode 翻车 (sanity blocker · spec fail)
    // ------------------------------------------------------------------------
    const fallbackBanners = await page.locator('[data-testid="fallback-banner"]').count();
    expect(
      fallbackBanners,
      `5 应急流程不触 sanity · live healthy 前提下 FallbackBanner count 应 = 0 · 实际 ${fallbackBanners} (>0 = 某 adapter fall back · live 翻车 blocker)`
    ).toBe(0);

    // ------------------------------------------------------------------------
    // baseline 入库 (env 'live' 显式 · 跨 spec append `_temp/w2-rehearsal-baseline.json`)
    // ------------------------------------------------------------------------
    await saveBaseline('rehearsal-live', perStep, 'live');

    // 总结 log (D10 PM 走访彩排耗时回看 · live 模式预期 < 74s)
    const total = Object.values(perStep).reduce<number>((a, b) => a + b, 0);
    const budgetTotal = Object.values(STEP_BUDGETS).reduce<number>((a, b) => a + b, 0);
    // eslint-disable-next-line no-console
    console.log(
      `  [rehearsal-live summary · D10] 9 step PASS · ` +
        `step1=${perStep.step1}ms step2=${perStep.step2}ms step3=${perStep.step3}ms ` +
        `step4=${perStep.step4}ms step5=${perStep.step5}ms step6=${perStep.step6}ms ` +
        `step7=${perStep.step7}ms step8=${perStep.step8}ms step9=${perStep.step9}ms · ` +
        `total=${total}ms / 预算 ${budgetTotal}ms (utilization ${((total / budgetTotal) * 100).toFixed(1)}% · live: 3 adapter 全 live · 5 应急 count=${fallbackBanners} OK)`
    );
  });
});
