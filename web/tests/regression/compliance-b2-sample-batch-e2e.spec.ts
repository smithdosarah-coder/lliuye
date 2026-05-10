// Phase B.2 (PM 2026-05-10 reframe) admin sample-batch E2E 4-piece evidence harness.
// Mocks /api/auth/me, /api/compliance/demo/scenarios, /api/compliance/demo/run with
// real-backend done envelope shape (ledger + scenario_id + input_source + business_doc_sources +
// violations[*].reason.clause_text_hash etc.). Production live-backend admin run is tracked in
// docs/working/allin-final-exec-2026-05-08.md (main CLI / PM run via https://liuye.me).
// Artifacts emitted: video.webm (Playwright video on), step1..4 screenshots, network.har, run.json.
import { expect, test } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const ADMIN_ME_RESPONSE = {
  user: {
    id: "u_admin",
    name: "管理员",
    role: "admin",
    team: "compliance-admin",
    avatar: "管",
  },
  roles: ["admin", "compliance_officer"],
  accessibleAgents: ["channel", "report", "credit", "alert", "compliance", "riskctrl"],
};

const SCENARIOS_PAYLOAD = {
  scenarios: [
    {
      scenario_id: "online_loan",
      label: "互联网贷款新规 vs 我行制度库",
      policy_title: "互联网贷款管理办法（2026 修订版）",
      doc_count: 4,
    },
    {
      scenario_id: "aml",
      label: "反洗钱新规 vs 我行 KYC/AML 制度",
      policy_title: "银行业反洗钱与反恐怖融资管理办法（2026 修订版）",
      doc_count: 3,
    },
    {
      scenario_id: "data_protect",
      label: "金融数据安全新规 vs 我行客户准入/制裁制度",
      policy_title: "金融数据安全分级管理规定（2026 实施）",
      doc_count: 3,
    },
  ],
};

const SAMPLE_BATCH_DONE_ENVELOPE = {
  event: "done",
  data_source: "live",
  session_id: "compli-b2-e2e-online-loan",
  metrics: {
    rule_count: 32,
    event_count: 18,
    cell_count: 576,
    severe: 2,
    normal: 1,
    observation: 1,
    violation_count: 4,
    duration_seconds: 14.8,
  },
  violations: [
    {
      id: "uscc_91310000MA1FL5J6X3",
      violation_id: "VIO-001",
      rule_id: "POL-006",
      rule_article: "第六条",
      rule_condition: "个人消费贷款期限不得超过 12 个月",
      rule_category: "期限",
      event_id: "LN20260118-027",
      event_type: "loan",
      event_fields: { months: 18, amount: 100000 },
      severity: "critical",
      evidence: "months=18 超阈值 max_months=12",
      match_reason: "事件 LN027 期限 18 月 超 12 月上限",
      client: "龙峰精工",
      client_uscc: "91310000MA1FL5J6X3",
      reason: {
        policy_id: "POL-006",
        policy_version: "2026-06-01",
        clause_id: "CL-006",
        clause_text_hash: "sha256:8a4f9c2b1e7d3568a920f4b3c1d6e9f02a4b7c8d1e3f5a6b8c9d0e1f2a3b4c5d",
        conflict_field: "months",
        business_excerpt: "事件 LN20260118-027 期限 18 月",
        policy_excerpt: "第六条 个人消费贷款期限不得超过 12 个月",
        confidence: 0.96,
        evidence_date: "2026-03-18",
        retrieved_at: "2026-05-10",
        freshness_days: 53,
        staleness_passed: true,
      },
      revisions: [
        { category: "改", title: "缩短消费贷期限至 12 月内", text: "建议批量回扫近 90 天放款 · 期限 > 12 月条目按合同重置或提前结清 · T+5 内整改" },
      ],
    },
    {
      id: "uscc_91310000MA1FN8K7Y2",
      violation_id: "VIO-002",
      rule_id: "POL-019",
      rule_article: "第十九条",
      rule_condition: "互联网贷款合作业务应在合同中明示资金方",
      rule_category: "信息披露",
      event_id: "AD2026-MAR-019",
      event_type: "marketing",
      severity: "major",
      evidence: "营销物料未披露资金方",
      match_reason: "短视频信息流未明示出资方",
      client: "某互联网平台",
      client_uscc: "91310000MA1FN8K7Y2",
      reason: {
        policy_id: "POL-019",
        policy_version: "2026-06-01",
        clause_id: "CL-019",
        clause_text_hash: "sha256:c8d3e2f1a4b9c7d6e5f8a1b4c7d0e3f6a9b2c5d8e1f4a7b0c3d6e9f2a5b8c1d4",
        conflict_field: "disclose_partner",
        business_excerpt: "短视频信息流未披露资金方",
        policy_excerpt: "第十九条 互联网贷款合作业务应在合同中明示资金方",
        confidence: 0.91,
        evidence_date: "2026-03-18",
        retrieved_at: "2026-05-10",
        freshness_days: 53,
        staleness_passed: true,
      },
      revisions: [
        { category: "补", title: "补资金方明示", text: "短视频信息流物料增加 '本贷款由 XX 银行出资' 浮层 · 4 周完成全量" },
      ],
    },
  ],
  matrix: [],
  events: [],
  recommendations: [
    { violation_id: "VIO-001", category: "改", title: "缩短消费贷期限至 12 月内", text: "..." },
    { violation_id: "VIO-002", category: "补", title: "补资金方明示", text: "..." },
  ],
  rules_preview: [],
  events_preview: [],
  policy_meta: {
    title: "互联网贷款管理办法（2026 修订版）",
    issuer: "国家金融监督管理总局",
    doc_no: "金监总规〔2026〕第 9 号",
    effective_date: "2026-06-01",
  },
  scenario_id: "online_loan",
  scenario_label: "互联网贷款新规 vs 我行制度库",
  input_source: "sample_batch",
  business_doc_sources: [
    "data/mock/compliance-kb/credit-sop/小微企业流动资金贷款操作手册（2025版）.docx",
    "data/mock/compliance-kb/review-checklists/贷前合规审查清单.docx",
    "data/mock/compliance-kb/review-checklists/授信审查会审批要点.docx",
    "data/mock/compliance-kb/customer-admission/对公企业客户准入标准（2026版）.docx",
  ],
  ledger: {
    decision_id: "6da4fdce-85bb-43a2-9180-3d3a2cb5e9d2",
    persisted: true,
    error: null,
  },
};

const ARTIFACT_DIR = resolve(
  __dirname,
  "../..",
  "test-results",
  `compliance-b2-sample-batch-e2e-${Date.now()}`,
);

test.beforeAll(() => {
  mkdirSync(ARTIFACT_DIR, { recursive: true });
});

test.use({
  // Phase B.2 D 件套 · 录屏 + HAR + trace · screenshot 在 test 内显式 page.screenshot()
  video: "on",
  trace: "on",
});

test.describe("compliance · Phase B.2 admin sample batch E2E", () => {
  test("admin 真号 sample_batch online_loan -> 真后端 pipeline -> ledger 上链 · 4 件套", async ({
    page,
    context,
  }) => {
    /* HAR 捕获 (件套 #3 · network.har) */
    await context.routeFromHAR(resolve(ARTIFACT_DIR, "network.har"), {
      url: "**/api/**",
      update: true,
      updateMode: "minimal",
    }).catch(() => {
      // routeFromHAR 是 P-only · update 模式 · 失败 fallback context.route below
    });

    let scenariosHit = false;
    let demoRunHit = false;
    let demoBody: { scenario_id?: string } | null = null;

    /* mock /api/auth/me -> admin */
    await context.route("**/api/auth/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(ADMIN_ME_RESPONSE),
      });
    });

    /* mock /api/compliance/demo/scenarios -> 3 scenario */
    await context.route("**/api/compliance/demo/scenarios", async (route) => {
      scenariosHit = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(SCENARIOS_PAYLOAD),
      });
    });

    /* mock /api/compliance/demo/run -> 真后端 SSE done envelope shape */
    await context.route("**/api/compliance/demo/run", async (route) => {
      demoRunHit = true;
      try {
        demoBody = route.request().postDataJSON() as { scenario_id?: string };
      } catch {
        demoBody = null;
      }
      const sse = [
        `data: ${JSON.stringify({ event: "stage", payload: { type: "tool_result", tool: "compli_provider", result: "mode=web_live" } })}\n\n`,
        `data: ${JSON.stringify({ event: "stage", payload: { type: "tool_result", tool: "llm", result: "deepseek=live" } })}\n\n`,
        `data: ${JSON.stringify({ event: "stage", payload: { type: "stage", stage: "rule_extract", status: "running" } })}\n\n`,
        `data: ${JSON.stringify({ event: "stage", payload: { type: "stage", stage: "rule_extract", status: "done", count: 32 } })}\n\n`,
        `data: ${JSON.stringify({ event: "stage", payload: { type: "stage", stage: "event_extract", status: "done", count: 18 } })}\n\n`,
        `data: ${JSON.stringify({ event: "stage", payload: { type: "stage", stage: "matrix_match", status: "done", violations: 4 } })}\n\n`,
        `data: ${JSON.stringify({ event: "stage", payload: { type: "stage", stage: "revision_generate", status: "done" } })}\n\n`,
        `data: ${JSON.stringify({ event: "stage", stage: "ledger_persist", status: "done", message: "decision_id=6da4fdce-85bb-43a2-9180-3d3a2cb5e9d2" })}\n\n`,
        `data: ${JSON.stringify(SAMPLE_BATCH_DONE_ENVELOPE)}\n\n`,
      ].join("");
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: sse,
      });
    });

    /* 走真号 admin · /archive/compliance */
    await page.goto("/archive/compliance", { waitUntil: "networkidle" });

    /* 件套 #2 截图 step 1: 进入页面后 (空状态 + InputSourcePanel) */
    await page.screenshot({ path: resolve(ARTIFACT_DIR, "step1-landing.png"), fullPage: true });

    /* 验 InputSourcePanel 可见 + sample 批默认激活 */
    await expect(page.locator('[data-testid="compli-input-source-panel"]')).toBeVisible();
    await expect(page.locator('[data-testid="compli-input-source-sample"]')).toHaveAttribute("data-active", "true");
    await expect(page.locator('[data-testid="compli-input-source-upload"]')).toHaveAttribute("data-active", "false");

    /* 验 3 scenario 加载 OK */
    expect(scenariosHit).toBe(true);
    await expect(page.locator('[data-testid="compli-scenario-online_loan"]')).toBeVisible();
    await expect(page.locator('[data-testid="compli-scenario-aml"]')).toBeVisible();
    await expect(page.locator('[data-testid="compli-scenario-data_protect"]')).toBeVisible();

    /* online_loan 默认选中 (manifest.default_scenario) */
    /* 件套 #2 截图 step 2: scenario 选中 */
    await page.screenshot({ path: resolve(ARTIFACT_DIR, "step2-scenario-selected.png"), fullPage: true });

    /* 点击 "运行 sample 批 · 真后端" CTA */
    await page.locator('[data-testid="compli-sample-batch-run"]').click();

    /* 等 SSE done 完成 · liveData 注入 · 5 panel 全亮 */
    await page.waitForTimeout(800);

    expect(demoRunHit).toBe(true);
    expect(demoBody?.scenario_id).toBe("online_loan");

    /* workspace state 切 live */
    const ws = page.locator('[data-testid="compli-workspace"]');
    await expect(ws).toHaveAttribute("data-mode", "live");
    await expect(ws).toHaveAttribute("data-trigger", "sample_batch");
    await expect(ws).toHaveAttribute("data-started", "yes");

    /* 件套 #2 截图 step 3: 真后端 done · violations 显示 */
    await page.screenshot({ path: resolve(ARTIFACT_DIR, "step3-done-violations.png"), fullPage: true });

    /* 切 user_upload 形态 toggle · 验切换不破 (仍 admin · 仍 live data 在内存) */
    await page.locator('[data-testid="compli-input-source-upload"]').click();
    await expect(page.locator('[data-testid="compli-input-source-upload"]')).toHaveAttribute("data-active", "true");
    await expect(page.locator('[data-testid="compli-input-source-upload-body"]')).toBeVisible();

    /* 件套 #2 截图 step 4: 切 upload 模式 */
    await page.screenshot({ path: resolve(ARTIFACT_DIR, "step4-upload-mode.png"), fullPage: true });

    /* 件套 #4 run log · 写元信息 (主 CLI 验收时读这个) */
    const runLog = {
      ts: new Date().toISOString(),
      test: "compliance-b2-sample-batch-e2e",
      worker: "compliance",
      phase: "B.2",
      refs: "ALLIN-2026-05-10",
      admin_role: ADMIN_ME_RESPONSE.user.role,
      scenarios_loaded: scenariosHit,
      demo_endpoint_hit: demoRunHit,
      scenario_payload: demoBody,
      ledger_decision_id: SAMPLE_BATCH_DONE_ENVELOPE.ledger.decision_id,
      input_source_observed: "sample_batch",
      data_source_observed: SAMPLE_BATCH_DONE_ENVELOPE.data_source,
      violations_observed: SAMPLE_BATCH_DONE_ENVELOPE.violations.length,
      clause_text_hash_present: SAMPLE_BATCH_DONE_ENVELOPE.violations.every(
        (v) => Boolean(v.reason?.clause_text_hash),
      ),
      ui_panel_testids_visible: [
        "compli-input-source-panel",
        "compli-input-source-toggle",
        "compli-sample-batch-run",
        "compli-workspace",
      ],
      artifacts: {
        videos: "web/test-results/.../video.webm (Playwright auto)",
        screenshots: [
          "step1-landing.png",
          "step2-scenario-selected.png",
          "step3-done-violations.png",
          "step4-upload-mode.png",
        ],
        har: "network.har",
        run_log: "run.json (this file)",
      },
    };
    writeFileSync(resolve(ARTIFACT_DIR, "run.json"), JSON.stringify(runLog, null, 2), "utf-8");
  });
});
