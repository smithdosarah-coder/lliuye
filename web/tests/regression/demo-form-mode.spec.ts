import { expect, test, type BrowserContext } from "@playwright/test";

const READONLY_MESSAGE = "演示环境为只读形态 · 已停用生成、上传与写入";

test.skip(
  process.env.NEXT_PUBLIC_DEMO_FORM_MODE !== "1",
  "requires NEXT_PUBLIC_DEMO_FORM_MODE=1 at next build/dev start",
);

const USER = {
  user: { id: "u_test", name: "测试管理员", role: "admin", team: "测试", avatar: "测" },
  roles: ["admin"],
  accessibleAgents: ["report", "credit", "channel", "alert", "compliance", "riskctrl"],
};

const MATERIALS = Array.from({ length: 7 }, (_, index) => ({
  id: `material-${index + 1}`,
  name: `蓝汀材料-${index + 1}.${index < 2 ? "pdf" : "xlsx"}`,
  kind: index < 2 ? "pdf" : "xlsx",
  pages: 1,
  bytes: "3.0 KB",
  parsed: true,
  parseNote: "本会话材料 · 已用于生成",
  linkedSections: [],
}));

const DEFAULT_SESSION = {
  event: "done",
  session_id: "11111111-1111-4111-8111-111111111111",
  report_id: "11111111-1111-4111-8111-111111111111",
  pipeline: "v16",
  mock_pipeline: false,
  data_source: "live",
  source_docx: "samples/经纬测绘_对公成稿A.docx",
  profile: {
    company_name: "蓝汀家电连锁（浙江）有限公司",
    unified_credit_code: "91330782MA2XXXX022",
  },
  template: {
    id: "tpl-corporate-a",
    name: "对公成稿 A",
    kind: "预置",
    version: "经纬测绘",
    fieldTotal: 0,
    recentUsed: 0,
  },
  materials: MATERIALS,
  timeline: [{
    id: "seed-template",
    at: new Date().toISOString(),
    kind: "template.select",
    priority: "done",
    label: "已选用模板 · 对公成稿 A",
  }],
  conversation: [{
    id: "seed-template-message",
    at: new Date().toISOString(),
    kind: "system-event",
    content: "已选用模板 · 对公成稿 A",
  }],
  sections: [{
    id: "chapter_1_background",
    title: "一、企业背景",
    content: "蓝汀家电已完成报告正文",
    status: "done",
    word_count: 13,
  }],
  qc: {
    passed: false,
    fatal_fail: true,
    score: 0,
    dimensions: [
      { name: "申报方案硬字段", raw_score: 3.08, pass_threshold: 5.0 },
      { name: "财务分析深度", raw_score: 6.0, pass_threshold: 7.0 },
    ],
  },
  stats: { total_fields: 10, auto_filled: 8, unfilled: 2 },
  pending_questions: [],
};

async function stubShell(context: BrowserContext) {
  await context.route("**/api/auth/me", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(USER),
  }));
  await context.route("**/api/report/health", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: '{"llm_connected":true}',
  }));
  await context.route("**/api/report/templates", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ builtin: [], user: [] }),
  }));
  await context.route("**/api/report/demo/default", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(DEFAULT_SESSION),
  }));
  await context.route("**/api/compliance/demo/scenarios", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      scenarios: [{
        scenario_id: "online_loan",
        label: "互联网贷款合规",
        policy_title: "互联网贷款监管办法",
        doc_count: 3,
      }],
    }),
  }));
  await context.route("**/api/riskctrl/demo/seeds", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      seeds: [{
        seed_id: "credit_v15",
        label: "授信评分样例",
        difficulty: "中",
        strategy_intent: "验证形态模式禁用一键运行",
        csv_path: "data/mock/riskctrl/credit_v15.csv",
      }],
    }),
  }));
}

test.beforeEach(async ({ context }) => stubShell(context));

test("B/C/D/E · report loads the completed coherent session and exposes no generation entry", async ({ page }) => {
  await page.goto("/archive/report", { waitUntil: "networkidle" });

  await expect(page.locator('[data-testid="report-demo-form-notice"]')).toContainText(
    READONLY_MESSAGE,
  );
  await expect(page.locator('[data-testid="report-sample-dp002"]')).toHaveCount(0);
  await expect(page.locator('[data-testid="report-upload-cta"]')).toHaveCount(0);
  await expect(page.locator('[data-testid="report-generate-btn"]')).toHaveCount(0);
  await expect(page.locator('[aria-label="上传材料"]')).toHaveCount(0);
  await expect(page.locator('[data-testid="report-upload-template-cta"]')).toHaveCount(0);
  await expect(page.locator('[data-testid="report-refine-input"]')).toHaveCount(0);
  await expect(page.locator('[data-testid="report-refine-btn"]')).toHaveCount(0);
  await expect(page.locator(".rpt-composer-ta")).toHaveCount(0);

  await expect(page.locator(".rpt-hero-sub")).toContainText("蓝汀家电");
  await expect(page.locator('[data-testid="report-pilot-materials"] .rpt-mat-card')).toHaveCount(7);
  await expect(page.locator('[data-testid="report-pilot-materials"]')).not.toContainText("厂房抵押评估报告");
  await expect(page.locator('[data-testid="report-pilot-timeline"]')).not.toContainText("福建惠民商贸");
  await expect(page.getByText("已选用模板 · 对公成稿 A", { exact: true })).toBeVisible();
  await expect(page.locator(".doc-title")).toContainText("对公成稿 A");
  await expect(page.locator('[data-testid="report-qc-dimensions"]')).toContainText("申报方案硬字段 3.08 / 5.0");
  await expect(page.locator("body")).not.toContainText("分 0.0");
});

test("B1 · visible mutation controls are disabled with one readable explanation", async ({ page }) => {
  await page.goto("/dispatch", { waitUntil: "networkidle" });
  await expect(page.locator(".dpx-composer")).toContainText(READONLY_MESSAGE);
  const composerInput = page.locator(".dpx-composer-input");
  if (await composerInput.count()) {
    await expect(composerInput).toBeDisabled();
    await expect(page.locator(".dpx-composer-send")).toBeDisabled();
  }

  await page.goto("/archive/compliance", { waitUntil: "networkidle" });
  await expect(page.locator('[data-testid="compli-sample-batch-run"]')).toBeDisabled();
  await expect(page.locator(".compliance-input-source__run-hint")).toHaveText(READONLY_MESSAGE);

  await page.goto("/archive/credit", { waitUntil: "networkidle" });
  await expect(page.locator('[data-testid="credit-demo-cta"]')).toBeDisabled();
  await expect(page.locator('[data-testid="credit-demo-cta"]')).toContainText(READONLY_MESSAGE);

  await page.goto("/archive/alert", { waitUntil: "networkidle" });
  await expect(page.locator('[data-testid="alert-scan-cta"]')).toBeDisabled();
  await expect(page.locator('[data-testid="alert-scan-cta"]')).toContainText(READONLY_MESSAGE);

  await page.goto("/archive/riskctrl", { waitUntil: "networkidle" });
  await expect(page.locator('[data-testid="riskctrl-dsl-gen-cta"]')).toBeDisabled();
  await expect(page.locator('[data-testid="riskctrl-dsl-gen-cta"]')).toHaveText(READONLY_MESSAGE);
  await page.locator('[data-testid="riskctrl-mode-toggle-demo"]').click();
  await expect(page.locator('[data-testid="riskctrl-demo-run-cta"]')).toBeDisabled();
  await expect(page.locator('[data-testid="riskctrl-demo-run-cta"]')).toHaveText(READONLY_MESSAGE);
});

test("F/G/H · today, warroom and audit use one customer directory and labeled shape data", async ({ page }) => {
  await page.goto("/today", { waitUntil: "networkidle" });
  await expect(page.locator(".priority-row")).toHaveCount(5);
  await expect(page.locator(".priority-queue__empty")).toHaveCount(0);
  await expect(page.getByText("活跃客户 · Active").locator("..")).toContainText("5");
  const eventTimes = await page.locator(".event-row__time").allTextContents();
  expect(eventTimes.length).toBeGreaterThan(0);
  expect(eventTimes.every((value) => /^(刚刚|\d+ (分|小时|天)前)$/.test(value))).toBe(true);
  const shanghai = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const part = (type: Intl.DateTimeFormatPartTypes) => shanghai.find((item) => item.type === type)?.value;
  await expect(page.locator(".rule .rt")).toContainText(`${part("year")} · ${part("month")} · ${part("day")}`);
  await expect(page.locator("body")).not.toContainText("中锐");
  await expect(page.locator("body")).not.toContainText("宁海汇通");
  await expect(page.locator("body")).not.toContainText("星河医药");

  await page.goto("/warroom", { waitUntil: "networkidle" });
  await expect(page.locator(".kcard")).toHaveCount(4);
  await expect(page.getByText("【示例】", { exact: false })).toHaveCount(4);

  await page.goto("/audit", { waitUntil: "networkidle" });
  await expect(page.locator(".audit-row .type", { hasText: "示例 ·" })).toHaveCount(9);
  await expect(page.locator(".audit-row .cust").first()).not.toContainText("cust_");
});
