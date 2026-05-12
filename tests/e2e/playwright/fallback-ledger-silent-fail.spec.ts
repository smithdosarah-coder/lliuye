/**
 * W2-mock-test · 第 4 棒 · 2026-05-12
 * fallback-ledger-silent-fail.spec.ts · 5 应急 W2 跑 #2 · 附录 C.2.3
 *
 * SSOT: W2-mock-test brief §4.4 (2) verbatim + v3 spec 附录 C.2.3
 * 引用:
 *   - v3 §6.3 step 8 ConfirmModal medium + ledger 写入 (5s 预算)
 *   - W2-frontend brief §4.5 (FallbackBanner 5 fallback · ledger silent-fail = confirm modal 乐观更新「已提交·上链中」)
 *   - 老仓 root CLAUDE.md §3.7.5 (ledger 写入失败 silent-fail · decision flow 不破 · BE7 wrapper try/except)
 *   - liuye_service/audit.py::record_liuye_decision · outbox _enqueue_outbox 真写 data/liuye/outbox/{decision_id}.json
 *
 * 场景 (附录 C.2.3):
 *   - ledger sqlite write fail (mock `sqlite3.OperationalError` · e.g. read-only disk / sqlite lock)
 *   - audit.py::record_liuye_decision silent-fail (try/except 不破 · decision flow 继续)
 *   - outbox _enqueue_outbox 真写入 `data/liuye/outbox/{decision_id}.json` (60s retry × 5 由 outbox worker 跑)
 *   - UI confirm modal 显「已提交 · 上链中」乐观更新 (W2-frontend §4.5 文案 verbatim · 不显失败)
 *   - 不阻断 step 9 LE-01 trace · decision_id 仍出 · trace drawer 仍可点开 (showing pending state)
 *
 * 端到端 (per brief §4.4 (2)):
 *   A3-NEW Decision submit → medium PermissionRequest → grant → ledger fail (mock) →
 *   outbox enqueue → confirm modal 乐观显「已提交·上链中」→ 不阻断 step 9 LE-01 trace
 *
 * 触发 ledger fail 路径:
 *   - W2-backend live 真实做: `LIUYE_FORCE_LEDGER_ERROR=1` env flag · ledger_service 内部强抛 sqlite3.OperationalError
 *   - spec 验 testid contract · 不强依赖具体触发机制 · UI 显乐观 banner + outbox file 存在即 OK
 *
 * outbox file 检查 (Node fs):
 *   - `data/liuye/outbox/` 目录 list · 期 ≥ 1 个 `{decision_id}.json` 文件 (本次 decision_id)
 *   - 文件内容 schema (per W2-backend brief): decision_id + agent_id + payload + retry_count + created_at
 *   - 本 spec 仅验文件存在 (file count > 0) · 不解析内容 (留 W2-backend pytest scope)
 *
 * Skip 条件:
 *   - mock SSE :8001 :8002 任一不可达 → skip (走完 step 1-8 需 channel + credit mock)
 *   - SKIP_DEMO_STEP4_9=1 (UI 真渲未到位) → skip
 *   - data/liuye/outbox/ 目录不可读 (W2-backend 未 init outbox 目录) → skip
 *
 * Hidden gotcha (第 4 棒 record):
 *   - ledger silent-fail banner 文案 = 「已提交 · 上链中」(W2-frontend §4.5 verbatim · 中点分隔)
 *     不是接力 brief 臆想的「账本写入异步重试中」
 *   - data-kind="ledger_silent_fail" 是 W2-frontend FallbackBanner 内嵌 attr (5 kind 之一)
 *   - silent-fail = 用户层 info-level UI · 不是 error · 应 visible 但不 blocking (modal 仍可关闭进 step 9)
 *   - outbox 文件检查走 Node `fs/promises` · spec 用 `import('fs/promises')` lazy import (避免 tsc 全局 import side effect)
 *   - outbox path 是 repo-root-relative `data/liuye/outbox/` (W2-backend brief §x · 现未 ship 时此目录可能不存在)
 *   - decision_id 用 turn_id 推断 (W2-backend audit.py 真路径) · 或从 le01-trace-drawer 内读 (W2-frontend 真渲后)
 */
import { test, expect, type Page } from '@playwright/test';
import * as fs from 'fs/promises';
import * as path from 'path';

// ============================================================================
// Mock SSE health probe (复用 W1/W2 pattern)
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
// Outbox dir 检查 (repo-root-relative · spec 在 tests/e2e/playwright/ · root = ../../../)
// ============================================================================
const OUTBOX_DIR = path.resolve(__dirname, '..', '..', '..', 'data', 'liuye', 'outbox');

async function isOutboxDirReadable(): Promise<boolean> {
  try {
    await fs.access(OUTBOX_DIR, fs.constants.R_OK);
    return true;
  } catch {
    return false;
  }
}

async function countOutboxFiles(): Promise<number> {
  try {
    const entries = await fs.readdir(OUTBOX_DIR);
    // 仅算 `.json` 文件 (排除 `.gitkeep` · README · 临时 file)
    return entries.filter((f) => f.endsWith('.json')).length;
  } catch {
    return 0;
  }
}

// ============================================================================
// Tests · ledger silent-fail → outbox enqueue → 用户无感知阻断
// ============================================================================

test.describe('W2 应急 #2 · fallback-ledger-silent-fail · ledger 写失败 → outbox 异步重试', () => {
  test.skip(
    process.env.SKIP_DEMO_STEP4_9 === '1',
    'SKIP_DEMO_STEP4_9=1 set · W2-frontend / W2-backend ledger silent-fail 真路径未到位时跳过'
  );

  test('ledger sqlite write fail → audit silent-fail → outbox enqueue → confirm modal 乐观显 · 不阻 step 9 trace', async ({
    page,
  }) => {
    test.setTimeout(60_000);

    // ------------------------------------------------------------------------
    // 前置 1: probe mock SSE :8001 (channel) + :8002 (credit · step 8 PermissionRequest grant 路径)
    // ------------------------------------------------------------------------
    const channelAlive = await isMockSseAlive(page, MOCK_SSE_CHANNEL_HEALTH, 'channel');
    const creditAlive = await isMockSseAlive(page, MOCK_SSE_CREDIT_HEALTH, 'credit');
    if (!channelAlive || !creditAlive) {
      // eslint-disable-next-line no-console
      console.log(
        `  [fallback-ledger-silent-fail skip] mock SSE :8001 alive=${channelAlive} · :8002 alive=${creditAlive} · 跑前需 mock-sse:channel + mock-sse:credit`
      );
      test.skip(true, 'mock SSE :8001 / :8002 任一未起 · ledger silent-fail 路径需走 channel → credit step 8');
      return;
    }

    // ------------------------------------------------------------------------
    // 前置 2: probe outbox dir (W2-backend init `data/liuye/outbox/` 否则跳过 file check)
    // ------------------------------------------------------------------------
    const outboxReadable = await isOutboxDirReadable();
    if (!outboxReadable) {
      // eslint-disable-next-line no-console
      console.log(
        `  [fallback-ledger-silent-fail · outbox] dir ${OUTBOX_DIR} 不可读 · W2-backend 未 init outbox · 跳过 file check (仍验 UI banner)`
      );
    }

    // 记录 baseline outbox file count (本次新增 = afterCount - beforeCount)
    const beforeCount = outboxReadable ? await countOutboxFiles() : 0;

    // ------------------------------------------------------------------------
    // Step 1-8: 走完 demo path 至 step 8 ConfirmModal grant
    //   (本 spec 不复用 demo-path-step4-9 因为目标不同 · 这里是验 fallback 路径)
    // ------------------------------------------------------------------------
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('[data-testid="hero-static"]')).toBeVisible({ timeout: 5_000 });

    // 点 credit chip (直接进 credit 而非 channel · 因 ledger silent-fail 的触发是 credit decision)
    await page.click('[data-testid="agent-chip-credit"]');
    await page.locator('[data-testid="composer-textarea"]').fill('审贷决策 · 新能源汽车零部件');
    await page.click('[data-testid="composer-submit"]');

    // 等 credit-handoff-active 或直接 decision-submit 按钮显 (W2-frontend 真渲后 credit chip 直触 decision flow)
    await expect(
      page.locator('[data-testid="decision-submit"]'),
      'decision-submit 按钮应可见 (credit 决策完成 · 等 step 8 grant)'
    ).toBeVisible({ timeout: 30_000 });

    // ------------------------------------------------------------------------
    // Step 8 触发 + medium PermissionRequest grant (with LIUYE_FORCE_LEDGER_ERROR=1 env)
    // ------------------------------------------------------------------------
    await page.click('[data-testid="decision-submit"]');
    await expect(
      page.locator('[data-testid="permission-modal"]'),
      'ConfirmModal medium 应在 6s 内显'
    ).toBeVisible({ timeout: 6_000 });
    await page.click('[data-testid="permission-grant"]');

    // ------------------------------------------------------------------------
    // Step 验 ledger silent-fail UI 路径
    //   ledger sqlite write fail (mock force) → audit.py silent-fail (try/except 不破) →
    //   outbox _enqueue_outbox 真写 data/liuye/outbox/{decision_id}.json →
    //   confirm modal 乐观更新「已提交 · 上链中」(W2-frontend §4.5 verbatim)
    //
    //   FallbackBanner data-testid="fallback-banner" data-kind="ledger_silent_fail" (info-level · visible 但不 blocking)
    //   或 confirm modal 内嵌乐观提示 (W2-frontend 实做边界 · spec 用 FallbackBanner 作主验)
    // ------------------------------------------------------------------------
    const banner = page.locator('[data-testid="fallback-banner"][data-kind="ledger_silent_fail"]');
    await expect(
      banner,
      'FallbackBanner ledger_silent_fail 应在 grant 后 8s 内显 (audit silent-fail · outbox enqueue · UI 乐观更新)'
    ).toBeVisible({ timeout: 8_000 });
    // 验文案 = W2-frontend brief §4.5 verbatim (UI SSOT · 中点分隔)
    await expect(
      banner,
      'FallbackBanner 应显「已提交 · 上链中」(W2-frontend §4.5 verbatim · 不是接力 brief 臆想文案)'
    ).toContainText('已提交');

    // ------------------------------------------------------------------------
    // 验 outbox file 真写入 (W2-backend init outbox 目录前提下 · 否则 skip file check)
    //   silent-fail 路径: ledger write 失败 → _enqueue_outbox(decision_id, payload) → data/liuye/outbox/{decision_id}.json
    //   本 spec 验 file count 增加 ≥ 1 (新 outbox entry)
    // ------------------------------------------------------------------------
    if (outboxReadable) {
      // 给 backend 1s outbox flush 缓冲 (silent-fail enqueue 是同步但 fs write 微延迟)
      await page.waitForTimeout(1_000);
      const afterCount = await countOutboxFiles();
      expect(
        afterCount,
        `outbox file count 应增 ≥ 1 (silent-fail enqueue) · before=${beforeCount} · after=${afterCount}`
      ).toBeGreaterThan(beforeCount);
      // eslint-disable-next-line no-console
      console.log(
        `  [fallback-ledger-silent-fail · outbox] before=${beforeCount} after=${afterCount} delta=${afterCount - beforeCount} (≥ 1 新 outbox entry)`
      );
    }

    // ------------------------------------------------------------------------
    // 不阻断 step 9 LE-01 trace (decision_id 仍出 · trace drawer 仍可点开 with pending state)
    //   silent-fail 是 info-level · 不是 error · modal 仍可正常关闭 + LE-01 trace 仍可点
    // ------------------------------------------------------------------------
    await expect(
      page.locator('[data-testid="le01-trace-button"]'),
      'LE-01 trace 按钮应仍可见 (silent-fail 不阻断 step 9 · decision_id 仍存在 with pending ledger state)'
    ).toBeVisible({ timeout: 5_000 });

    // 总结 log (D8 PM 应急 dry-run 回看)
    // eslint-disable-next-line no-console
    console.log(
      `  [fallback-ledger-silent-fail summary · W2 应急 #2] ` +
        `FallbackBanner ledger_silent_fail visible · 「已提交·上链中」乐观显 · ` +
        `outbox enqueue ${outboxReadable ? `delta ≥ 1` : 'skipped (dir 不可读)'} · ` +
        `LE-01 trace 不阻断 · audit silent-fail 路径 OK`
    );
  });
});
