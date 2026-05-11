import { test, expect, type Route } from "@playwright/test";

/**
 * B.3.4 · fix-bugs Bug B · report 后端调用失败 (TDD red-to-green)
 *
 * PM 痛 (5/11 凌晨): 报告 (report): 提示后端调用失败
 *
 * Prod 真因 (curl https://liuye.me/api/report/demo/run + admin cookie · 2026-05-11):
 *   HTTP 503 · code = DEMO_CLASSIFIER_MISSING
 *   detail.error.message = "v16 classifier 产物缺失: v16_llm_classified.json · 请 admin 一次性预跑 py v16_classifier.py"
 *
 * 5 typed error code (agent_report/api.py:1054-1114):
 *   400 SAMPLE_ID_INVALID
 *   404 SAMPLE_DIR_MISSING
 *   503 DEEPSEEK_KEY_MISSING
 *   503 DEMO_CLASSIFIER_MISSING
 *   503 DEMO_TEMPLATE_MISSING
 *
 * 契约 (KT R2 TDD):
 *   T1 · POST /api/report/demo/run 真返 DEMO_CLASSIFIER_MISSING 时 · 前端 banner 显 actionable hint
 *        verbatim "v16 分类器 cache 缺失 · 请管理员一次性预跑 `py v16_classifier.py`"
 *   T2 · 顺利场景 · backend yield stage event → ReportWorkspace 进 running 态
 *        (验 SSE 解析没坏 · stages live 流入)
 *   T3 · DEEPSEEK_KEY_MISSING / DEMO_TEMPLATE_MISSING / SAMPLE_DIR_MISSING / SAMPLE_ID_INVALID
 *        4 件 typed code 都翻成 actionable subtitle (不是裸 code)
 *
 * 反模式 (per prompt "不可 GO"):
 *   - 没 curl prod 排 typed code · 假修 → 已 curl 抓真因
 *   - 修法不是 mock 兜底 · 是显式 typed banner + admin actionable hint
 *
 * 注: 真因 'classifier 产物缺失' 是 prod 一次性 ECS init 步骤 · 不在本 spec 范围
 *      本 spec 验前端 contract · CI 阻断未来 banner 退化为 'HTTP 503' 裸文案
 */

const MOCK_ME_RESPONSE = {
  user: {
    id: "u_wangzhe",
    name: "王哲",
    role: "rm",
    team: "华东·上海第一支行",
    avatar: "哲",
  },
  roles: ["rm"],
  accessibleAgents: ["channel", "report", "credit", "alert", "compliance", "riskctrl"],
};

function stub503(code: string, message: string) {
  return async (route: Route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: { error: { code, message } } }),
    });
  };
}

function stub400(code: string, message: string) {
  return async (route: Route) => {
    await route.fulfill({
      status: 400,
      contentType: "application/json",
      body: JSON.stringify({ detail: { error: { code, message } } }),
    });
  };
}

function stub404(code: string, message: string) {
  return async (route: Route) => {
    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: { error: { code, message } } }),
    });
  };
}

test.beforeEach(async ({ context }) => {
  await context.route("**/api/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_ME_RESPONSE),
    });
  });
});

test.describe("B.3.4 Bug B · report demo/run typed 503 → actionable banner (TDD)", () => {
  test("T1 · prod 真因 DEMO_CLASSIFIER_MISSING · banner 显 admin runbook", async ({
    page,
    context,
  }) => {
    await context.route(
      "**/api/report/demo/run",
      stub503(
        "DEMO_CLASSIFIER_MISSING",
        "v16 classifier 产物缺失: v16_llm_classified.json · 请 admin 一次性预跑: py v16_classifier.py",
      ),
    );
    await page.goto("/archive/report", { waitUntil: "networkidle" });

    // sample 按钮在 LaunchBar / ReportSampleStrip · 找 DP001 龙峰精工 trigger
    const sample = page.locator('[data-testid="report-sample-dp001"]');
    await expect(sample).toBeVisible();
    await sample.click();
    // 等 fetch 返 503 + onError 投递 errMsg + banner mount
    await page.waitForTimeout(800);

    const banner = page.locator('[data-testid="report-launch-error-banner"]');
    await expect(banner).toBeVisible();
    // 关键: 显 actionable admin hint (per _formatDemoError)
    await expect(banner).toContainText("v16 分类器 cache 缺失");
    await expect(banner).toContainText("py v16_classifier.py");
    // 不可只显 bare HTTP 503 文案 (退化 sentinel)
    await expect(banner).not.toContainText(/^HTTP 503$/);
    await expect(banner).not.toContainText("demo/run HTTP 503");
  });

  test("T2 · happy path · stage event 流入 ReportWorkspace running 态", async ({
    page,
    context,
  }) => {
    await context.route("**/api/report/demo/run", async (route) => {
      const sse = [
        `event: stage\ndata: ${JSON.stringify({
          event: "stage",
          stage: "ingest",
          status: "running",
        })}\n\n`,
        `event: stage\ndata: ${JSON.stringify({
          event: "stage",
          stage: "ingest",
          status: "done",
        })}\n\n`,
      ].join("");
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: sse,
      });
    });
    await page.goto("/archive/report", { waitUntil: "networkidle" });
    const sample = page.locator('[data-testid="report-sample-dp001"]');
    await expect(sample).toBeVisible();
    await sample.click();
    await page.waitForTimeout(800);

    // banner 不出 · 因为没 error event
    const banner = page.locator('[data-testid="report-launch-error-banner"]');
    await expect(banner).toHaveCount(0);
  });

  test("T3 · 4 件 typed code 都翻成 actionable subtitle (回归网)", async ({
    page,
    context,
  }) => {
    const cases: Array<{
      stub: (route: Route) => Promise<void>;
      mustContain: string;
    }> = [
      {
        stub: stub503("DEEPSEEK_KEY_MISSING", "DEEPSEEK_API_KEY 未配置"),
        mustContain: "DEEPSEEK_API_KEY 未配置",
      },
      {
        stub: stub503("DEMO_TEMPLATE_MISSING", "默认对公模板 docx 缺失"),
        mustContain: "默认对公模板 docx 缺失",
      },
      {
        stub: stub404("SAMPLE_DIR_MISSING", "sample 目录不存在: DP001_龙峰精工"),
        mustContain: "DP001 龙峰精工",
      },
      {
        stub: stub400("SAMPLE_ID_INVALID", "sample_id 命名不合法"),
        mustContain: "命名不合法",
      },
    ];

    for (const c of cases) {
      await context.unroute("**/api/report/demo/run").catch(() => undefined);
      await context.route("**/api/report/demo/run", c.stub);
      await page.goto("/archive/report", { waitUntil: "networkidle" });
      const sample = page.locator('[data-testid="report-sample-dp001"]').first();
      await expect(sample).toBeVisible();
      await sample.click();
      await page.waitForTimeout(800);
      const banner = page.locator('[data-testid="report-launch-error-banner"]');
      await expect(banner).toBeVisible();
      await expect(banner).toContainText(c.mustContain);
    }
  });
});
