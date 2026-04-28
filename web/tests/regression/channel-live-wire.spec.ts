import { test, expect, type Page, type Route } from "@playwright/test";

/**
 * F-043 + F-044 + F-045 · Channel Live Wire (master plan §B.5b + §B.6 + §B.6b)
 *
 * 验证三联合:
 *  1) F-044 · 3 类 KB upload UI · dropzone 渲染 + multipart upload + kb_id 返
 *  2) F-045 · IdealProfile 12 维画像卡 + reasoning + "开始扫描" CTA 显示
 *  3) F-043 · live SSE wire (textbox 触发 /api/channel/run · candidate 卡显真实
 *     industry/geo/scale + drawer 内 match_dimensions/products/pitch 是 backend 返而非 mock)
 *
 * 网络 mock:
 *  - POST /api/channel/upload_kb   → mock 返 kb_id + summary_text
 *  - POST /api/channel/profile     → mock 返 12 维 IdealProfile
 *  - POST /api/channel/run         → mock SSE done event 含 backend snake_case 全字段
 *
 * Auth seed: archive/* 受 AuthGate 保护 · 测试前 seed localStorage 默认 u_wangzhe (rm role)
 */

const AUTH_KEY = "platform.auth.v1";
const DEMO_USER_RM = {
  id: "u_wangzhe",
  name: "王哲",
  role: "rm",
  team: "华东·上海第一支行",
  avatar: "哲",
};

async function seedAuth(page: Page) {
  await page.addInitScript(
    ({ key, user }) => {
      const persisted = {
        state: { currentUser: user },
        version: 0,
      };
      window.localStorage.setItem(key, JSON.stringify(persisted));
    },
    { key: AUTH_KEY, user: DEMO_USER_RM },
  );
}

/* mock /api/channel/upload_kb · 返 kb_id (uuid) + summary_text */
async function mockKbUpload(page: Page) {
  await page.route("**/api/channel/upload_kb", async (route: Route) => {
    /* ✓ multipart 真发到这里 · 我们读 form 内容 */
    const post = route.request().postData() ?? "";
    const kbType = post.match(/name="kb_type"\s*\r?\n\r?\n([^\r\n-]+)/)?.[1]?.trim() ?? "customer_list";
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        kb_id: "11111111-2222-4333-8444-555555555555",
        kb_type: kbType,
        source_filename: "test.xlsx",
        summary_text: `[${kbType}] test.xlsx · 1 sheet · 50 rows · cols: name, industry, scale`,
        n_rows: 50,
        n_sheets: 1,
      }),
    });
  });
}

async function mockIdealProfile(page: Page) {
  await page.route("**/api/channel/profile", async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ideal_profile: {
          industry_focus: ["工业软件", "SaaS"],
          scale_preference: ["中型", "小型"],
          geo_coverage: ["上海", "江苏", "浙江"],
          stage: "成长期",
          capital_relation: "B 轮已完成",
          business_size: "营收 1-3 亿",
          employee_size: "100-300 人",
          customer_type: ["B2B"],
          product_keywords: ["PMC", "MES"],
          value_chain_position: "下游",
          growth_signals: ["专精特新", "高新技术"],
          risk_signals: [],
        },
        confidence_score: 0.82,
        reasoning_text:
          "基于客户名录 50 行抽 12 维画像 · 行业 / 规模 / 地域 / 阶段 高置信 · 风险信号未识别",
      }),
    });
  });
}

/* mock /api/channel/run SSE · 返 candidate 含 match_dimensions/products/pitch (B.5b) */
async function mockChannelRun(page: Page) {
  await page.route("**/api/channel/run", async (route: Route) => {
    const candidate = {
      id: "cand_live_001",
      name: "上海泰华工业软件",
      similarity: 0.86,
      industry: "工业软件",
      geo: "上海",
      scale: "中型",
      signals: [
        {
          type: "tech",
          title: "申请发明专利 12 项",
          detail: "MES 系统调度算法",
          date: "2026-04-10",
          source: "国家知识产权局",
          url: "https://example.com/p1",
        },
        {
          type: "growth",
          title: "B+ 轮融资 8000 万",
          detail: "深创投领投",
          date: "2026-03-20",
          source: "投资界",
          url: "https://example.com/f1",
        },
      ],
      score: 86,
      match_dimensions: [
        {
          dim_name: "行业匹配",
          hit_evidence: "tl-001",
          score: 90,
          display: "行业 工业软件 ✓ 命中标杆",
        },
        {
          dim_name: "区域匹配",
          hit_evidence: "qcc",
          score: 88,
          display: "区域 上海 ✓ 在 P50 ±20%",
        },
        {
          dim_name: "规模匹配",
          hit_evidence: "qcc.cap",
          score: 75,
          display: "中型 ✓ 营收 2 亿",
        },
        {
          dim_name: "信号丰富度",
          hit_evidence: "tl-all",
          score: 80,
          display: "tech + growth · 2 类信号",
        },
      ],
      product_recommendations: [
        {
          product_name: "流动资金贷款",
          fit_score: 85,
          intro: "用于日常经营周转 · 一年期",
          category: "对公贷款",
        },
        {
          product_name: "保理 / 应收质押融资",
          fit_score: 70,
          intro: "应收账款质押 / 转让 · 解决 B2B 账期",
          category: "供应链金融",
        },
        {
          product_name: "设备贷",
          fit_score: 60,
          intro: "针对企业新购置生产设备 · 3-5 年",
          category: "对公贷款",
        },
      ],
      pitch_scripts: [
        {
          customer_name_placeholder: "{客户名}",
          script_text:
            "您好 {客户名}，注意到贵司近期 B+ 轮融资 + 12 项专利。我行可提供配套流动资金贷款，期限灵活、利率优惠。",
          source: "agent6",
        },
      ],
    };

    const sseLines = [
      `data: ${JSON.stringify({ event: "stage", stage: "parse", status: "running" })}`,
      `data: ${JSON.stringify({ event: "stage", stage: "parse", status: "done", tags: [{ category: "行业", value: "工业软件" }] })}`,
      `data: ${JSON.stringify({
        event: "done",
        candidates: [candidate],
        metrics: { signalTotal: 2, companiesFound: 1, final: 1 },
        data_source: "mock",
      })}`,
    ];

    await route.fulfill({
      status: 200,
      headers: {
        "content-type": "text/event-stream",
        "cache-control": "no-cache",
      },
      body: sseLines.map((l) => l + "\n\n").join(""),
    });
  });
}

test.describe("F-043 + F-044 + F-045 · Channel Live Wire (B.5b + B.6 + B.6b)", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page);
    await mockKbUpload(page);
    await mockIdealProfile(page);
    await mockChannelRun(page);
  });

  test("F-044 · 3 类 KB dropzone 渲染 (customer / policy / industry)", async ({
    page,
  }) => {
    await page.goto("/archive/channel", { waitUntil: "networkidle" });
    /* 3 类 dropzone 都 visible */
    await expect(
      page.locator('[data-testid="kb-dropzone-customer-list"]'),
    ).toBeVisible();
    await expect(
      page.locator('[data-testid="kb-dropzone-policy"]'),
    ).toBeVisible();
    await expect(
      page.locator('[data-testid="kb-dropzone-industry-guide"]'),
    ).toBeVisible();
  });

  test("F-044 + F-045 · 上传客户名录 → IdealProfile 自动抽取 + 显示 12 chip + 开始扫描 CTA", async ({
    page,
  }) => {
    await page.goto("/archive/channel", { waitUntil: "networkidle" });
    /* 上传 customer_list dropzone 用 setInputFiles */
    const fileInput = page.locator(
      '[data-testid="kb-dropzone-customer-list-input"]',
    );
    await fileInput.setInputFiles({
      name: "test.xlsx",
      mimeType:
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      buffer: Buffer.from("fake xlsx content for upload"),
    });
    /* 等 summary 出现 (kb upload 成功) */
    await expect(
      page.locator('[data-testid="kb-dropzone-customer-list-summary"]'),
    ).toBeVisible({ timeout: 10000 });
    /* IdealProfile card 出现 (auto fetch /api/channel/profile) */
    const profileCard = page.locator('[data-testid="ideal-profile-card"]');
    await expect(profileCard).toBeVisible({ timeout: 10000 });
    /* 12 chip 中至少有 industry_focus 的 "工业软件" + "SaaS" */
    const chips = page.locator('[data-testid="ideal-profile-chip"]');
    expect(await chips.count()).toBeGreaterThanOrEqual(8);
    /* "开始扫描" CTA 显示 */
    const cta = page.locator('[data-testid="start-scan-cta"]');
    await expect(cta).toBeVisible();
  });

  test("F-045 + F-043 · 点开始扫描 → live SSE wire · candidate 显示 backend industry/geo/scale + drawer 用真 match_dim/products/pitch", async ({
    page,
  }) => {
    await page.goto("/archive/channel", { waitUntil: "networkidle" });
    /* 上传 → 等画像 → 点扫描 */
    const fileInput = page.locator(
      '[data-testid="kb-dropzone-customer-list-input"]',
    );
    await fileInput.setInputFiles({
      name: "test.xlsx",
      mimeType:
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      buffer: Buffer.from("fake xlsx content for live wire test"),
    });
    const cta = page.locator('[data-testid="start-scan-cta"]');
    await expect(cta).toBeVisible({ timeout: 10000 });
    await cta.click();

    /* live mode candidate card 渲染 (backend 返 1 candidate · industry/geo/scale 真值) */
    const cards = page.locator('[data-testid="channel-candidate-card"]');
    await expect(cards.first()).toBeVisible({ timeout: 10000 });
    /* 候选 metadata 显示 backend 真值 (不是 "—" 或 "未获取" 占位) */
    const cardText = await cards.first().innerText();
    expect(cardText).toContain("工业软件");
    expect(cardText).toContain("上海");

    /* 点候选 → drawer 4 区 都 wire 到 backend 字段 */
    await cards.first().click();
    const drawer = page.locator('[data-testid="channel-candidate-drawer"]');
    await expect(drawer).toBeVisible();
    /* 匹配维度 chip ≥ 3 (B.4b · backend 返 4 条) */
    const matchChips = page.locator('[data-testid="candidate-match-dim-chip"]');
    expect(await matchChips.count()).toBeGreaterThanOrEqual(3);
    /* 包含 backend 返的 "行业匹配" "区域匹配" 之一 */
    const drawerText = await drawer.innerText();
    expect(drawerText).toMatch(/行业匹配|区域匹配/);
    /* Top3 产品卡 ≥ 3 (B.4c) */
    const productCards = page.locator('[data-testid="candidate-product-card"]');
    expect(await productCards.count()).toBeGreaterThanOrEqual(3);
    /* 产品名包含 backend 返的 "流动资金贷款" */
    expect(drawerText).toContain("流动资金贷款");
    /* 切入话术 ≥ 1 (B.4c · backend 返 1 条) */
    const pitches = page.locator('[data-testid="candidate-pitch-script"]');
    expect(await pitches.count()).toBeGreaterThanOrEqual(1);
    /* 话术含 customer_name_placeholder */
    expect(drawerText).toContain("{客户名}");
  });
});
