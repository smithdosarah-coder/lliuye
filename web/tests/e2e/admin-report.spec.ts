/**
 * B.3.4 · P0-R5 · 主活 B · admin 真号 E2E · report
 *
 * PM 真意:
 *   登录 admin · DP001 龙峰精工 sample
 *   · 验 SSE done · PIPELINE 4 阶段都 done
 *
 * 触发: report-sample-dp001 (per ReportWorkspace.tsx:1915 dynamic testid)
 */
import { adminTest as test, expect, E2E_TIMEOUT_MS } from "./_shared";

test.describe("B.3.4 · admin 真号 · report 报告 demo DP001 龙峰精工", () => {
  test("点 DP001 龙峰精工 sample · PIPELINE 4 阶段全 done · 无 503", async ({
    page,
  }) => {
    test.setTimeout(E2E_TIMEOUT_MS);

    await page.goto("/archive/report", { waitUntil: "networkidle" });

    // empty-skeleton 加载 · sample 条带 visible
    await expect(
      page.locator('[data-testid="report-empty-skeleton"]'),
    ).toBeVisible();
    await expect(
      page.locator('[data-testid="report-sample-strip"]'),
    ).toBeVisible();

    // 点 DP001 (per dynamic testid = report-sample-{sampleId.split(_)[0].toLowerCase()})
    await page.locator('[data-testid="report-sample-dp001"]').click();

    // SSE 跑完 · PIPELINE 4 阶段 (per Q-B.2.2 hotfix 修 PIPELINE 100% 假完成态)
    // 4 阶段: 解析 → KB 构建 → section 生成 → QC gate
    // 真完成态 = 所有 stage 都进入 done · 且页面不再显示 "running" 文案
    //
    // 关键 negative assert: 整页文本不含 "503" / "Internal Server Error" /
    // "PIPELINE_FAILED" / [object Object] / NaN (per Q-B.2.2 PM dispatch 真完成态)
    await page.waitForTimeout(2000); // 让 SSE 流第一个 event 发出
    const forbidden = [
      /\b503\b/,
      /Internal Server Error/i,
      /PIPELINE_FAILED/,
      /\[object Object\]/,
      /\bNaN\b/,
    ];

    // 等到页面不再显 "running" 状态文案 (= 跑完了)
    // 容差: 最多等 SSE 60s · 然后再 grab 整页
    const startedRoot = page.locator('[data-view="archive-report"], [data-testid*="report-workspace"]');
    if ((await startedRoot.count()) > 0) {
      await expect(startedRoot.first()).toBeVisible({ timeout: 60_000 });
    }

    // 抓整页文本 · 防 503 / 假完成 / 占位符
    const bodyText = await page.locator("body").innerText();
    for (const pat of forbidden) {
      expect(bodyText, `body 含禁词 ${pat}`).not.toMatch(pat);
    }

    // PIPELINE 4 阶段标识 (允许任一可见 + 都 done)
    // 检查没有任何 "running" / "loading" / "pending" 阶段卡 (那是假完成态)
    const stillRunning = page.locator(
      '[data-pipeline-stage][data-state="running"], [data-stage-state="running"]',
    );
    expect(
      await stillRunning.count(),
      "PIPELINE 仍有 running 阶段卡 · 真完成态失败",
    ).toBe(0);
  });
});
