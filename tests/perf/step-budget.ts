/**
 * W2-mock-test · 第 2 棒 · 2026-05-12
 * tests/perf/step-budget.ts · step 级耗时 utility + ±20% hard gate + baseline JSON append
 *
 * SSOT: W2-mock-test brief §4.2 (verbatim STEP_BUDGETS + withBudget + saveBaseline 形态)
 * 引用: v3 spec §6.3 demo path 70s 9 step + 附录 C.1 时间预算表 + 附录 C.3 hard gate ±20%
 *
 * 9 step demo path 总预算 (v3 §6.3 verbatim):
 *   step1 静默首页加载                    3s   (F-007 · bootstrap GET cached)
 *   step2 点「🔍 找合适企业」chip         1s   (client only)
 *   step3 F-066 Channel SSE ranked 5      15s  (Tavily + LLM rerank)
 *   step4 A1-NEW-1 IdealProfile 12 维     10s  (LLM call · 12 维 progressive)
 *   step5 拖 artifact → composer ref chip 2s   (client only · drag-drop)
 *   step6 F-067-handoff Credit SSE        15s  (LLM + tool chain · parent_tool_call_id 透传)
 *   step7 F-053 progressive radar 4 维    10s  (tail of step 6 SSE · 大字 92 + 4 small badge)
 *   step8 A3-NEW confirm modal 「提交并上链」 5s (ledger 写入 + idempotency_key · PermissionRequest medium)
 *   step9 LE-01 trace modal 弹审计链      5s   (trace GET · decision → tool_call → artifact → evidence)
 *   ─────────────────────────────────────────────────────
 *   总:                                  66s  (≤ 70s buffer 4s · 客户走访 < 70s 硬线)
 *
 * Hard gate ±20% (v3 附录 C.3): 单 step 耗时 > budget × 1.2 视作 regression · 立即 fail.
 *
 * 使用模式 (spec 内):
 *   import { withBudget, saveBaseline, STEP_BUDGETS } from '../../perf/step-budget';
 *
 *   test('demo path step 4-7', async ({ page }) => {
 *     const perStep: Record<string, number> = {};
 *     perStep.step4 = await withBudget('step4', async () => { ... step 4 动作 ... });
 *     perStep.step5 = await withBudget('step5', async () => { ... step 5 动作 ... });
 *     // ...
 *     await saveBaseline('demo-path-step4-9', perStep);
 *   });
 */
import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

// ============================================================================
// STEP_BUDGETS · v3 §6.3 verbatim (W2-mock-test brief §4.2 verbatim 命名 step1..step9)
// ============================================================================
export const STEP_BUDGETS = {
  step1: 3000, // 静默首页加载
  step2: 1000, // 点 chip
  step3: 15000, // Channel SSE ranked 5
  step4: 10000, // IdealProfile 12 维
  step5: 2000, // 拖 artifact → composer ref chip
  step6: 15000, // Credit handoff SSE
  step7: 10000, // progressive radar 4 维
  step8: 5000, // confirm modal 提交并上链
  step9: 5000, // LE-01 trace modal
} as const;

export type StepName = keyof typeof STEP_BUDGETS;

// ±20% hard gate (v3 附录 C.3)
const HARD_GATE_RATIO = 1.2;

// 总预算 (sum of STEP_BUDGETS) · 用于 saveBaseline utilization 字段
const TOTAL_BUDGET_MS: number = Object.values(STEP_BUDGETS).reduce<number>((a, b) => a + b, 0);

// ============================================================================
// withBudget · test.step wrap + ±20% hard gate + 返回 elapsed
// ============================================================================
/**
 * 用 Playwright `test.step` 包裹 step body · 测耗时 · 超 ±20% hard gate 即 fail.
 *
 * @param name   step 名 (STEP_BUDGETS key)
 * @param fn     step body async fn
 * @returns      elapsed ms (调用方可累积进 baseline perStep)
 *
 * 行为:
 * - 用 `Date.now()` 起止差值 (per W1 demo-path-step1-3 同模式)
 * - 输出 console.log `[step-budget] <name>: <elapsed>ms / budget <budget>ms (utilization xx.x%)`
 * - 断言 `elapsed <= budget * 1.2` · 超 = fail · 错误信息含 budget / threshold / 实际
 */
export async function withBudget(
  name: StepName,
  fn: () => Promise<void>
): Promise<number> {
  const budget = STEP_BUDGETS[name];
  const hardLimit = budget * HARD_GATE_RATIO;
  const start = Date.now();
  await test.step(name, fn);
  const elapsed = Date.now() - start;
  // eslint-disable-next-line no-console
  console.log(
    `  [step-budget] ${name}: ${elapsed}ms / budget ${budget}ms (utilization ${((elapsed / budget) * 100).toFixed(1)}% · threshold ${hardLimit}ms)`
  );
  expect(
    elapsed,
    `step "${name}" 耗时 ${elapsed}ms 超 hard gate ${hardLimit}ms (budget ${budget}ms × ${HARD_GATE_RATIO} · v3 附录 C.3)`
  ).toBeLessThanOrEqual(hardLimit);
  return elapsed;
}

// ============================================================================
// saveBaseline · append-to-JSON-array baseline 入库 (跨 spec 累积同一文件)
// ============================================================================

/**
 * 单次 baseline record 形态 (写入 _temp/w2-rehearsal-baseline.json array element).
 */
export interface BaselineRecord {
  spec: string;
  timestamp: string;
  perStep: Record<string, number>;
  totalElapsed: number;
  totalBudget: number;
  utilization: number; // percentage 0-100+
  env: 'mock' | 'hybrid' | 'live'; // LIUYE_DEMO_MODE / per-adapter URL 推断
}

/**
 * 把单次 spec 跑的 step 耗时 append 进 `_temp/w2-rehearsal-baseline.json` (root-relative).
 * 文件不存在则创建为 `[]` · 已存在则读 + append + 写回.
 *
 * @param spec     spec 标识 (e.g. 'demo-path-step4-9' / 'rehearsal-mock' / 'rehearsal-hybrid' / 'rehearsal-live')
 * @param perStep  step name → elapsed ms map (e.g. {step4: 8200, step5: 1500, ...})
 * @param env      'mock' / 'hybrid' / 'live' · 默认从 process.env.LIUYE_DEMO_MODE 推断 (1='mock' · 0='live')
 *
 * 注:
 * - 默认 path = repo root 的 `_temp/w2-rehearsal-baseline.json` (相对 spec 文件 ../../_temp/...)
 * - 文件级 atomic-ish write (read-then-write 短窗口 · 单 worker config 不并发 · 安全)
 * - 不抛错 (写失败 silent-fail · 不阻 spec pass · 写入失败本身不是 regression)
 */
export async function saveBaseline(
  spec: string,
  perStep: Record<string, number>,
  env?: 'mock' | 'hybrid' | 'live'
): Promise<void> {
  const totalElapsed = Object.values(perStep).reduce<number>((a, b) => a + b, 0);
  const inferredEnv: 'mock' | 'hybrid' | 'live' =
    env ??
    (process.env.LIUYE_DEMO_MODE === '1'
      ? 'mock'
      : process.env.LIUYE_BACKEND_CHANNEL_URL && !process.env.LIUYE_BACKEND_CREDIT_URL
        ? 'hybrid'
        : 'live');

  const record: BaselineRecord = {
    spec,
    timestamp: new Date().toISOString(),
    perStep,
    totalElapsed,
    totalBudget: TOTAL_BUDGET_MS,
    utilization: (totalElapsed / TOTAL_BUDGET_MS) * 100,
    env: inferredEnv,
  };

  // path: tests/perf/step-budget.ts → ../../ = repo root → _temp/w2-rehearsal-baseline.json
  const baselinePath = path.resolve(__dirname, '..', '..', '_temp', 'w2-rehearsal-baseline.json');
  const baselineDir = path.dirname(baselinePath);

  try {
    // 确保目录存在 (repo 现可能无 _temp/ · 创它)
    if (!fs.existsSync(baselineDir)) {
      fs.mkdirSync(baselineDir, { recursive: true });
    }
    let existing: BaselineRecord[] = [];
    if (fs.existsSync(baselinePath)) {
      try {
        const raw = fs.readFileSync(baselinePath, 'utf-8');
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          existing = parsed as BaselineRecord[];
        }
      } catch {
        // 文件损坏 → 重置 (上一次 partial write · 不影响本次)
        existing = [];
      }
    }
    existing.push(record);
    fs.writeFileSync(baselinePath, JSON.stringify(existing, null, 2), 'utf-8');
    // eslint-disable-next-line no-console
    console.log(
      `  [baseline] saved "${spec}" → ${baselinePath} (totalElapsed ${totalElapsed}ms / budget ${TOTAL_BUDGET_MS}ms · utilization ${record.utilization.toFixed(1)}% · env ${inferredEnv})`
    );
  } catch (err) {
    // silent-fail · 不阻 spec
    // eslint-disable-next-line no-console
    console.warn(
      `  [baseline] save FAILED for "${spec}" · ${(err as Error).message} · 不阻 spec pass · 视为 baseline 非 critical`
    );
  }
}

// ============================================================================
// Re-export 公用常量 · 调用方需要时可读 (e.g. 自定义 step 加超额 buffer)
// ============================================================================
export { HARD_GATE_RATIO, TOTAL_BUDGET_MS };
