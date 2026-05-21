/**
 * B.4 · SLO-2 主活 A · admin 真号 E2E · channel 实时路径
 *
 * PM 真意 (verbatim 2026-05-11 12:55):
 *   6 助手各跑 1 次实时模式 · 真 Tavily/DeepSeek 调 · 任何 503/null/fallback fake = 记 issue.
 *
 * Channel 实时路径:
 *   - input-mode-free (默认) · 用户输入业务诉求 → /api/channel/run 真 Tavily/AI
 *   - 验 ≥ 1 候选 · 候选含 industry/geo/scale/similarity 4 字段 · data-mode="live"
 *   - 任何 fallback 到 mock / [object] / null / "未知" / `data-mode="mock"` = fail
 *
 * 跟 admin-channel.spec.ts (demo medium 路径 · input-mode-sample) 完全互补.
 *
 * NOTE: codex R2 R2.1 #3 strict assertion ·
 * channel 历来就是 6 spec 里最严的 (data-mode=live + ≥ 1 候选 + 4 字段 + 占位拒) ·
 * 本次仅补 body 无 MOCK / fallback 字样 (跟其他 5 spec 统一 silent 降级阻 spec).
 */
import { adminTest as test, expect, E2E_TIMEOUT_MS, FIRST_PAINT_TIMEOUT_MS } from "./_shared";

test.describe("B.4 SLO-2 主活 A · admin 真号 · channel realtime", () => {
  test("free mode + scout-search · 真 Tavily 真候选 · data-mode=live · 不 fallback", async ({
    page,
  }) => {
    test.setTimeout(E2E_TIMEOUT_MS);

    await page.goto("/archive/channel", { waitUntil: "networkidle" });

    // free mode 是默认 · input-mode-free 应该 active · scout-search 应该 visible
    const freeMode = page.locator('[data-testid="input-mode-free"]');
    await expect(freeMode).toBeVisible({ timeout: FIRST_PAINT_TIMEOUT_MS });
    await freeMode.click(); // 显式切 free · 防默认状态被改

    // 输入真实业务诉求 + 触发 AI 搜索
    const queryInput = page.locator(".ch-querybar-input");
    await queryInput.fill("华东高端制造业 · 应收账款融资意愿");
    await page.locator('[data-testid="scout-search"]').click();

    // 等候选 panel 进入 live · SSE done · 真 Tavily 跑完
    // 实时调 Tavily/DeepSeek 比 demo 略慢 · 90s 容差
    await expect(
      page.locator('[data-testid="channel-pilot-candidates"]'),
    ).toHaveAttribute("data-mode", "live", { timeout: 90_000 });

    // 实时路径必有 ≥ 1 候选 (demo 阈 8 · realtime 不强 · 重点是不 fallback)
    const cards = page.locator('[data-testid="channel-candidate-card"]');
    const count = await cards.count();
    expect(count, "realtime 路径候选数 = 0 · Tavily/AI 真调返空 (= fallback fake silent)").toBeGreaterThanOrEqual(1);

    // 每张候选含 4 字段 · 不允许占位符 / mock fake (per Q-041 + PM SLO-2 红线)
    const forbidden = /\[object|undefined|^null$|^未知$|^MOCK\b|^N\/A\b/;
    for (let i = 0; i < count; i++) {
      const card = cards.nth(i);
      const meta = (await card.locator(".ch-cd-meta").innerText()).trim();
      expect(meta, `候选 #${i} meta 空 · realtime 路径无值`).not.toEqual("");
      expect(meta, `候选 #${i} meta 含占位 / mock fake: "${meta}"`).not.toMatch(forbidden);
      const parts = meta.split("·").map((s) => s.trim()).filter(Boolean);
      expect(parts.length, `候选 #${i} meta "${meta}" 不足 3 段 (industry/geo/scale)`).toBeGreaterThanOrEqual(3);

      const sim = (await card.locator(".ch-cd-sim-pct").innerText()).trim();
      expect(sim, `候选 #${i} similarity 空`).not.toEqual("");
      expect(sim, `候选 #${i} similarity 格式错: "${sim}"`).toMatch(/^\d+%$/);
    }

    // 整页不允许有 503 / fallback banner 红字
    const body = await page.locator("body").innerText();
    expect(body, "页面含 503 错误").not.toMatch(/\b503\b/);
    expect(body, "页面含 Internal Server Error").not.toMatch(/Internal Server Error/i);
    expect(
      body,
      "页面含 fallback banner (Tavily key 缺 / 0 命中 fallback)",
    ).not.toMatch(/Tavily key 缺|TavilyClient init 失败|5 路 0 命中/);

    // codex R2 R2.1 #3 strict · body 不允许 MOCK / mock fake / fallback 字样
    // (silent 降级 阻 spec · Q-055 §4 后端默认假数据混跑红线)
    expect(
      body,
      "页面含 MOCK / mock fake / fallback · backend silent 降级",
    ).not.toMatch(/\bMOCK\b|mock fake|fallback/i);
  });
});
