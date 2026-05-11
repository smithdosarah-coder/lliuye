/**
 * B.3.4 · P0-R5 · 主活 B · admin 真号 E2E · channel
 *
 * PM 真意 (verbatim 2026-05-11 reframe):
 *   登录 admin · 点 "一键示例·中等" · 等 SSE done ·
 *   验 ≥ 8 候选 + 4 字段 industry/geo/scale/similarity 全出 (per Q-041)
 */
import { adminTest as test, expect, E2E_TIMEOUT_MS } from "./_shared";

test.describe("B.3.4 · admin 真号 · channel 获客 demo medium", () => {
  test("点 一键示例·中等 · ≥ 8 候选 + 4 字段全出 · 无 [object/未知/null", async ({
    page,
  }) => {
    test.setTimeout(E2E_TIMEOUT_MS);

    await page.goto("/archive/channel", { waitUntil: "networkidle" });

    // AuthGate bootstrap + Cloudflare 首次连接延迟 · 第 1 assert 15s 容差
    await expect(
      page.locator('[data-testid="input-mode-sample"]'),
    ).toBeVisible({ timeout: 15_000 });

    // 切到 sample 形态 → 点 medium
    await page.locator('[data-testid="input-mode-sample"]').click();
    await page.locator('[data-testid="scout-sample-medium"]').click();

    // 候选 panel 进入 live 模式 (= SSE done event 已收 · candidates 已 hydrate)
    await expect(
      page.locator('[data-testid="channel-pilot-candidates"]'),
    ).toHaveAttribute("data-mode", "live", { timeout: 60_000 });

    // ≥ 8 候选卡 (per Q-041 + PM dispatch B 验收)
    const cards = page.locator('[data-testid="channel-candidate-card"]');
    await expect(cards).not.toHaveCount(0);
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(8);

    // 每张卡 4 字段 sanity: meta 文本 + 相似度 % 都非空 / 无占位符
    // (Q-041: industry/geo/scale/similarity 任 1 缺 / null / "未知" / "[object Object]" = regression)
    const forbidden = /\[object|undefined|^null$|^未知$/;

    for (let i = 0; i < count; i++) {
      const card = cards.nth(i);
      // meta = "industry · geo · scale" 文本 · 必有 2 个 "·" 分隔
      const meta = (await card.locator(".ch-cd-meta").innerText()).trim();
      expect(meta, `候选 #${i} meta 空`).not.toEqual("");
      expect(meta, `候选 #${i} meta 含占位: "${meta}"`).not.toMatch(forbidden);
      const parts = meta.split("·").map((s) => s.trim()).filter(Boolean);
      expect(parts.length, `候选 #${i} meta "${meta}" 不足 3 段`).toBeGreaterThanOrEqual(3);

      // similarity = "NN%" 文本 · 必为数字 + %
      const sim = (await card.locator(".ch-cd-sim-pct").innerText()).trim();
      expect(sim, `候选 #${i} similarity 空`).not.toEqual("");
      expect(sim, `候选 #${i} similarity 格式错: "${sim}"`).toMatch(/^\d+%$/);
      expect(sim, `候选 #${i} similarity 含占位`).not.toMatch(forbidden);
    }
  });
});
