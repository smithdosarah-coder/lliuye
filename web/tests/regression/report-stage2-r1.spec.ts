import { expect, test, type BrowserContext } from "@playwright/test";

const USER = {
  user: { id: "u_test", name: "测试", role: "admin", team: "测试", avatar: "测" },
  roles: ["admin"],
  accessibleAgents: ["report"],
};

async function stubShell(context: BrowserContext) {
  await context.route("**/api/auth/me", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(USER) }));
  await context.route("**/api/report/health", (route) => route.fulfill({ status: 200, contentType: "application/json", body: '{"llm_connected":true}' }));
  await context.route("**/api/report/templates", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ builtin: [{ name: "测试模板", template_path: "samples/test.docx" }], user: [] }),
  }));
}

test.beforeEach(async ({ context }) => stubShell(context));

test("B1 · 仅选模板无材料不发请求", async ({ page, context }) => {
  let requests = 0;
  await context.route("**/api/report/v16/fill", (route) => { requests += 1; return route.abort(); });
  await page.goto("/archive/report", { waitUntil: "networkidle" });
  await page.locator('[data-testid="report-template-select"]').selectOption("samples/test.docx");
  await page.locator('[data-testid="report-apply-launch-btn"]').click();
  await expect(page.locator('[data-testid="report-launch-error-banner"]')).toContainText("请先选择示例或上传材料");
  expect(requests).toBe(0);
});

test("B1/B2 · DP002 重试保持主角，延迟 SSE 立即且持续生成，error 立即退出", async ({ page, context }) => {
  const bodies: string[] = [];
  await context.route("**/api/report/upload?**", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      report_id: "old-report",
      session_id: "old-session",
      business_line: "corporate",
      file_summary: [{ name: "old.txt", type: "text/plain", size_bytes: 3, parsed_chars: 3, parse_status: "ok" }],
      total_files: 1,
      total_parsed_chars: 3,
    }),
  }));
  await context.route("**/api/report/demo/run", async (route) => {
    bodies.push(route.request().postData() ?? "");
    await new Promise((resolve) => setTimeout(resolve, 2_500));
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: 'event: error\ndata: {"event":"error","code":"V16_REAL_PATH_FAILED","message":"受控失败"}\n\n',
    });
  });
  await page.goto("/archive/report", { waitUntil: "networkidle" });
  await page.locator('[data-testid="report-upload-cta"] + input[type="file"]').setInputFiles({
    name: "old.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("old"),
  });
  await expect(page.locator('[data-testid="report-uploaded-material-row"]')).toHaveCount(1);
  await page.locator('[data-testid="report-sample-dp002"]').click();
  await expect(page.locator('[data-testid="report-uploaded-material-row"]')).toHaveCount(0);
  await expect(page.locator('[data-view="archive-report"]')).toHaveAttribute("data-mode", "mock", { timeout: 1_000 });
  await expect(page.locator('[data-testid="report-status-pill"]')).toHaveAttribute("data-mode", "mock", { timeout: 1_000 });
  await expect(page.locator('[data-testid="report-status-pill"]')).toContainText("示例模式", { timeout: 1_000 });
  const button = page.locator('[data-testid="report-generate-btn"]');
  await expect(button).toHaveAttribute("aria-busy", "true", { timeout: 1_000 });
  await expect(page.locator('[data-testid="report-generate-spinner"]')).toBeVisible({ timeout: 1_000 });
  await expect(page.locator('[data-testid="report-generating-skeleton"]')).toBeVisible({ timeout: 1_000 });
  await expect(page.locator('[data-testid="report-live-strip"] [data-stage="ingest"][data-state="active"]')).toBeVisible({ timeout: 1_000 });
  await expect(page.locator('[data-testid="report-live-message"]')).toHaveText("正在连接生成服务…", { timeout: 1_000 });
  await page.waitForTimeout(1_800);
  await expect(page.locator('[data-testid="report-generating-skeleton"]')).toBeVisible();
  await expect(page.getByText("蓝汀家电", { exact: false }).first()).toBeVisible();
  await expect(page.locator('[data-testid="report-live-fail-banner"]')).toBeVisible({ timeout: 5_000 });
  await expect(page.locator('[data-testid="report-generating-skeleton"]')).toHaveCount(0);
  await page.locator('[data-testid="report-live-fail-retry"]').click();
  await expect.poll(() => bodies.length).toBe(2);
  await expect(page.locator('[data-testid="report-live-fail-banner"]')).toBeVisible({ timeout: 5_000 });
  await page.locator('[data-testid="report-generate-btn"]').click();
  await expect.poll(() => bodies.length).toBe(3);
  expect(bodies.every((body) => body.includes("DP002_蓝汀家电"))).toBe(true);
});

test("B1 · DP002 受控成功后页头与请求体保持蓝汀家电", async ({ page, context }) => {
  let body: unknown;
  await context.route("**/api/report/demo/run", async (route) => {
    body = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: `event: done\ndata: ${JSON.stringify({
        event: "done",
        session_id: "session-dp002",
        report_id: "report-dp002",
        profile: { company_name: "蓝汀家电" },
        sections: [{ id: "chapter_1_background", title: "企业概况", content: "受控完成", status: "done" }],
        qc: { passed: true, score: 90 },
        stats: { total_fields: 1, auto_filled: 1, unfilled: 0 },
      })}\n\n`,
    });
  });
  await page.goto("/archive/report", { waitUntil: "networkidle" });
  await page.locator('[data-testid="report-sample-dp002"]').click();
  await expect.poll(() => body).toEqual({ sample_id: "DP002_蓝汀家电" });
  await expect(page.locator(".rpt-hero-sub")).toContainText("蓝汀家电");
  await expect(page.locator('[data-view="archive-report"]')).toHaveAttribute("data-mode", "mock");
  await expect(page.locator('[data-testid="report-status-pill"]')).toHaveAttribute("data-mode", "mock");
});
