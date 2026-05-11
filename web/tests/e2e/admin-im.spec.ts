/**
 * B.4 SLO-1 · admin 真号 E2E · /dispatch IM 真聊
 *
 * PM SLO (verbatim 2026-05-11 11:50):
 *   有完整的产品回路 · 用户使用 IM 功能 · 真的能聊天 · 也真的能调用模型问问题
 *
 * Brief 主活 D (mesh-prompt-b4-im.txt:43-46):
 *   web/tests/e2e/admin-im.spec.ts · 真发 5 消息 · 看 backend log DeepSeek 真调
 *   截图 + HAR + 后端 log artifact (HAR/截图 在 playwright.config.ts 全局开)
 *
 * 验收:
 *   - /dispatch 渲染 + ThreadList ≥ 1 thread
 *   - 选第一个 thread · 在 composer 真发 5 条带 @agent 路由的消息
 *   - 每条期待: 用户气泡 + agent 回复气泡 (DeepSeek 真调用 30s 内回)
 *   - 不出现 LLM 错误 banner (silent fallback 已替为 typed banner)
 *
 * 失败模式 (brief 不可 GO):
 *   - mock fallback (违 PM 真意) → 这里压根不调用 mock · 全走 /api/im/send 真 LLM
 *   - env 没真配 假 PASS → DEEPSEEK_API_KEY 缺则 backend 503 · banner 显错 · assert fail
 *   - 没 admin 真号 E2E 跑过 → 本 spec 走 _shared.ts adminTest · 真 cookie + storage
 */
import { adminTest as test, expect, E2E_TIMEOUT_MS } from "./_shared";

/* B.4 SLO-1 artifact 硬要求: HAR + 截图 + video · 强开 (overrides playwright.config 默认 off)
   - trace: "on" 含 network.har + dom snapshot + screencast (一份 zip 出全 artifact)
   - screenshot/video: 强开 (即使 pass 也留 · brief 要 before/after 截图)
   - HAR 走 trace 内嵌 · 不另开 recordHar (后者只在 newContext 时可配) */
test.use({
  screenshot: "on",
  video: "on",
  trace: "on",
});

const PROMPTS = [
  "@报告 请用 1 句话点评这家客户的整体情况",
  "@授信 大致建议什么额度区间和期限?",
  "@预警 当前是否有需要重点关注的风险信号?",
  "@合规 这类业务最常踩的合规红线是哪些?",
  "@获客 是否有可扩展的相似企业方向?",
];

test.describe("B.4 SLO-1 · admin 真号 IM 真聊 (DeepSeek)", () => {
  test("点 thread → 真发 5 消息 → DeepSeek 真返回 · 无 silent fallback", async ({
    page,
  }) => {
    test.setTimeout(E2E_TIMEOUT_MS * 2); // 5 message · 每条 ≤ 30s · 留 buffer

    await page.goto("/dispatch", { waitUntil: "networkidle" });

    // AuthGate bootstrap + 首次连接延迟 · 15s 容差
    await expect(
      page.locator('[data-testid="dispatch-view"]'),
    ).toBeVisible({ timeout: 15_000 });

    // 选第 1 个 thread (seed thread thr_zrgs / thr_dingchuan 之一)
    const firstRow = page.locator("aside.dpx-list button.dpx-row").first();
    await expect(firstRow).toBeVisible({ timeout: 10_000 });
    await firstRow.click();

    // composer 出现
    const textarea = page.locator(
      "form.dpx-composer textarea.dpx-composer-input",
    );
    const sendBtn = page.locator(
      "form.dpx-composer button.dpx-composer-send",
    );
    await expect(textarea).toBeVisible({ timeout: 5_000 });

    // 选 thread 后 stream-body 真存在 (seed message + 后续真发)
    const allBubbles = page.locator(".dpx-stream-body .wc-msg");

    let beforeAll = await allBubbles.count();
    for (let i = 0; i < PROMPTS.length; i++) {
      const msg = PROMPTS[i];
      // 输入 + 发送
      await textarea.fill(msg);
      await sendBtn.click();

      // 期待新增 2 条气泡 (用户 + DeepSeek 回复) · DeepSeek 慢路径留 30s
      // 注意: pin_ref / handoff_card / system_event 不进 .wc-msg · 只 text bubble
      await expect(allBubbles).toHaveCount(beforeAll + 2, {
        timeout: 30_000,
      });

      // 不出现 LLM 失败 banner (silent fallback 替为 typed banner · banner 不该亮)
      await expect(
        page.locator('[data-testid="im-llm-fail-banner"]'),
      ).toBeHidden();

      beforeAll = await allBubbles.count();
    }

    // 总计至少新增 PROMPTS.length * 2 条气泡
    const finalCount = await allBubbles.count();
    expect(finalCount).toBeGreaterThanOrEqual(PROMPTS.length * 2);
  });
});
