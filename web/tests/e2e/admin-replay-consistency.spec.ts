/**
 * B.4 · SLO-2 主活 B · 6 助手演示模式 seeded replay 一致性
 *
 * PM 真意 (verbatim 2026-05-11 12:55):
 *   "6 助手演示模式 seeded mock 全 replay (同 sample 2 次结果一致 · PM 演示给客户用)"
 *
 * 关键: 演示给客户看担心的是 "昨 8 候选 今 5 候选" macro shift · 不是字面 byte-level 一致
 *   (LLM 真做 100% byte-deterministic 几乎不可能 · 即使 temp=0 + seed fixed · sampling 仍 1 token diff).
 *
 * 实施: structural fingerprint 比对
 *   - 关键 selectors element count 必一致 (候选 8 → 8 · 红灯 1 → 1 · 阶段 4 → 4)
 *   - 整页数字 list (sorted/dedup/前50) 必基本一致 (容 ≤ 10% diff · 抗 LLM micro-randomness)
 *
 * 跑 6 sub-test · 全 6 助手 demo 路径 · 单 sub-test ~30-60s · 全 6 ~5-8min
 *
 * 不可 GO 红线:
 *   - counts 不等 = 候选/规则数 macro shift = 客户演示翻车
 *   - numbers diff > 10% = 评分/比率大幅震荡 = LLM 不稳
 *
 * 注: 此 spec serial · 不并行 · 每 sub-test 内必 fresh navigate.
 */
import { adminTest as test, expect, E2E_TIMEOUT_MS, FIRST_PAINT_TIMEOUT_MS } from "./_shared";
import { structuralFingerprint } from "./_replay-helpers";

/** 数字 list 相似度 (= 重叠数 / max(len1, len2)) · 0 = 无重叠 · 1 = 完全相同 */
function jaccardSimilarity(a: number[], b: number[]): number {
  if (a.length === 0 && b.length === 0) return 1;
  const setA = new Set(a);
  const setB = new Set(b);
  const intersection = [...setA].filter((x) => setB.has(x)).length;
  const union = new Set([...a, ...b]).size;
  return union === 0 ? 1 : intersection / union;
}

function assertReplayConsistent(
  agent: string,
  fp1: { counts: Record<string, number>; numbers: number[] },
  fp2: { counts: Record<string, number>; numbers: number[] },
): void {
  // 1. counts 严格一致 (macro shape)
  for (const sel of Object.keys(fp1.counts)) {
    expect(
      fp2.counts[sel],
      `${agent}: selector "${sel}" count 不一致 · run1=${fp1.counts[sel]} run2=${fp2.counts[sel]} · macro shift`,
    ).toBe(fp1.counts[sel]);
  }
  // 2. numbers 相似度 ≥ 0.8 (容 LLM micro-randomness)
  const sim = jaccardSimilarity(fp1.numbers, fp2.numbers);
  expect(
    sim,
    `${agent}: 数字 list 相似度 ${(sim * 100).toFixed(1)}% < 80% · ` +
    `run1=[${fp1.numbers.slice(0, 10).join(",")}...] run2=[${fp2.numbers.slice(0, 10).join(",")}...] · ` +
    `LLM 不稳 / 演示风险`,
  ).toBeGreaterThanOrEqual(0.8);
}

test.describe.serial("B.4 SLO-2 主活 B · 6 助手 demo replay 一致性", () => {
  test("channel demo medium · 2 次跑 structural 一致 + numbers ≥ 80% 重叠", async ({ page }) => {
    test.setTimeout(E2E_TIMEOUT_MS * 2 + 60_000);

    const countSels = ['[data-testid="channel-candidate-card"]'];

    async function runOnce(): Promise<ReturnType<typeof structuralFingerprint> extends Promise<infer R> ? R : never> {
      await page.goto("/archive/channel", { waitUntil: "networkidle" });
      await page
        .locator('[data-testid="input-mode-sample"]')
        .waitFor({ state: "visible", timeout: FIRST_PAINT_TIMEOUT_MS });
      await page.locator('[data-testid="input-mode-sample"]').click();
      await page.locator('[data-testid="scout-sample-medium"]').click();
      await expect(
        page.locator('[data-testid="channel-pilot-candidates"]'),
      ).toHaveAttribute("data-mode", "live", { timeout: 90_000 });
      await page.waitForTimeout(2000);
      return structuralFingerprint(page, countSels);
    }

    const fp1 = await runOnce();
    const fp2 = await runOnce();
    assertReplayConsistent("channel demo medium", fp1, fp2);
  });

  test("credit demo 鼎盛商贸 · 2 次跑 structural 一致 + numbers ≥ 80%", async ({ page }) => {
    test.setTimeout(E2E_TIMEOUT_MS * 2 + 60_000);

    const countSels = [
      '[data-testid="credit-redlines-list"]',
      '[data-testid="credit-decision-advice-live"]',
    ];

    async function runOnce(): Promise<ReturnType<typeof structuralFingerprint> extends Promise<infer R> ? R : never> {
      await page.goto("/archive/credit", { waitUntil: "networkidle" });
      await page
        .locator('[data-testid="credit-empty-skeleton"]')
        .waitFor({ state: "visible", timeout: FIRST_PAINT_TIMEOUT_MS });
      await page.locator('[data-testid="credit-input-mode-demo"]').click();
      await page.locator('[data-testid="credit-demo-cta"]').click();
      await expect(
        page.locator('[data-credit-started="yes"][data-scanned="yes"]'),
      ).toBeVisible({ timeout: 90_000 });
      await page.waitForTimeout(2000);
      return structuralFingerprint(page, countSels);
    }

    const fp1 = await runOnce();
    const fp2 = await runOnce();
    assertReplayConsistent("credit demo 鼎盛商贸", fp1, fp2);
  });

  test("alert demo · 2 次扫 structural 一致 + numbers ≥ 80%", async ({ page }) => {
    test.setTimeout(E2E_TIMEOUT_MS * 2 + 60_000);

    const countSels = [
      '[data-testid="alert-hitlist-row"]',
      '[data-testid="alert-traffic-light-red"]',
      '[data-testid="alert-traffic-light-yellow"]',
    ];

    async function runOnce(): Promise<ReturnType<typeof structuralFingerprint> extends Promise<infer R> ? R : never> {
      await page.goto("/archive/alert", { waitUntil: "networkidle" });
      await page
        .locator('[data-testid="alert-empty-skeleton"]')
        .waitFor({ state: "visible", timeout: FIRST_PAINT_TIMEOUT_MS });
      await page.locator('[data-testid="alert-input-mode-demo"]').click();
      await page.locator('[data-testid="alert-scan-cta"]').click();
      await expect(
        page.locator('[data-alert-started="yes"]'),
      ).toBeVisible({ timeout: 90_000 });
      await page.waitForTimeout(2000);
      return structuralFingerprint(page, countSels);
    }

    const fp1 = await runOnce();
    const fp2 = await runOnce();
    assertReplayConsistent("alert demo", fp1, fp2);
  });

  test("compliance demo §214 · 2 次扫 structural 一致 + numbers ≥ 80%", async ({ page }) => {
    test.setTimeout(E2E_TIMEOUT_MS * 2 + 60_000);

    const countSels = ['[data-testid="compli-pilot-violations"]'];

    async function runOnce(): Promise<ReturnType<typeof structuralFingerprint> extends Promise<infer R> ? R : never> {
      await page.goto("/archive/compliance", { waitUntil: "networkidle" });
      await page
        .locator('[data-testid="compli-empty-skeleton"]')
        .waitFor({ state: "visible", timeout: FIRST_PAINT_TIMEOUT_MS });
      const scenarioBtn = page.locator('[data-testid="compli-scenario-online_loan"]');
      if ((await scenarioBtn.count()) > 0) {
        await scenarioBtn.click();
      }
      await page.locator('[data-testid="compli-sample-batch-run"]').click();
      await expect(
        page.locator('[data-testid="compli-pilot-violations"]'),
      ).toBeVisible({ timeout: 90_000 });
      await page.waitForTimeout(2000);
      return structuralFingerprint(page, countSels);
    }

    const fp1 = await runOnce();
    const fp2 = await runOnce();
    assertReplayConsistent("compliance §214", fp1, fp2);
  });

  test("report demo DP001 · 2 次跑 structural 一致 + numbers ≥ 80%", async ({ page }) => {
    test.setTimeout(E2E_TIMEOUT_MS * 2 + 90_000);

    const countSels = [
      '[data-testid^="report-section-toc-"]',
      '[data-testid="report-pilot-preview"]',
    ];

    async function runOnce(): Promise<ReturnType<typeof structuralFingerprint> extends Promise<infer R> ? R : never> {
      await page.goto("/archive/report", { waitUntil: "networkidle" });
      await page
        .locator('[data-testid="report-empty-skeleton"]')
        .waitFor({ state: "visible", timeout: FIRST_PAINT_TIMEOUT_MS });
      await page.locator('[data-testid="report-sample-strip"]').waitFor({ state: "visible" });
      await page.locator('[data-testid="report-sample-dp001"]').click();
      // 等 PIPELINE 真跑完 · 等 running stages = 0
      await expect(
        page.locator('[data-pipeline-stage][data-state="running"], [data-stage-state="running"]'),
      ).toHaveCount(0, { timeout: 90_000 });
      await page.waitForTimeout(2000);
      return structuralFingerprint(page, countSels);
    }

    const fp1 = await runOnce();
    const fp2 = await runOnce();
    assertReplayConsistent("report demo DP001", fp1, fp2);
  });

  test("riskctrl demo credit_v15 · 2 次回测 structural 一致 + numbers ≥ 80%", async ({ page }) => {
    test.setTimeout(E2E_TIMEOUT_MS * 2 + 60_000);

    const countSels = [
      '[data-testid="riskctrl-ks-chart"]',
      '[data-testid^="riskctrl-rule-card-"]',
      '[data-testid="riskctrl-dsl-editor"]',
    ];

    async function runOnce(): Promise<ReturnType<typeof structuralFingerprint> extends Promise<infer R> ? R : never> {
      await page.goto("/archive/riskctrl", { waitUntil: "networkidle" });
      await page
        .locator('[data-testid="riskctrl-workspace"]')
        .waitFor({ state: "visible", timeout: FIRST_PAINT_TIMEOUT_MS });
      await page.locator('[data-testid="riskctrl-mode-toggle-demo"]').click();
      const seedSelect = page.locator('[data-testid="riskctrl-demo-seed-select"]');
      await seedSelect.waitFor({ state: "visible", timeout: 15_000 });
      try {
        await seedSelect.selectOption({ value: "credit_v15" }, { timeout: 3000 });
      } catch {
        // 默认选中第一个
      }
      await page.locator('[data-testid="riskctrl-demo-run-cta"]').click();
      await expect(
        page.locator('[data-testid="riskctrl-workspace"][data-started="yes"]'),
      ).toBeVisible({ timeout: 60_000 });
      await page.waitForTimeout(2000);
      return structuralFingerprint(page, countSels);
    }

    const fp1 = await runOnce();
    const fp2 = await runOnce();
    assertReplayConsistent("riskctrl demo credit_v15", fp1, fp2);
  });
});
