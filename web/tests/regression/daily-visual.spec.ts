import { test, expect } from "@playwright/test";

/**
 * B.3.4 · P0-R5 · daily-visual
 *
 * 6 助手 idle 状态视觉基线 + alert idle "空白" 入 spec (TDD red-first).
 *
 * 目的:
 *   - 每天 6am cron 跑此 spec · 任一 worker 改坏前端 · 截图 diff > 2% 立刻报警
 *   - alert idle 当前 PM 痛点 (2026-05-11 03:45 admin verify · 痛 4)
 *     "队列出来了但不能点客户详情 · 严重排版问题" — 入 baseline 后 fix-indep 修绿
 *
 * 范围:
 *   - 6 助手 × 1 idle snapshot = 6 baseline (channel/credit/report/alert/compli/riskctrl)
 *   - 不覆盖 running/done/error 状态 — 那些是 fix-bugs / 各 agent worker 的 spec
 *
 * 失败处置: 见 docs/runbook/daily-visual.md
 *
 * Auth bypass: localStorage seed `platform.auth.v1` 模拟王哲 (rm 全权限)
 */

const SEED_AUTH = JSON.stringify({
  state: {
    currentUser: {
      id: "u_wangzhe",
      name: "王哲",
      role: "rm",
      team: "华东·上海第一支行",
      avatar: "哲",
    },
  },
  version: 0,
});

test.beforeEach(async ({ context }) => {
  await context.addInitScript((seed) => {
    window.localStorage.setItem("platform.auth.v1", seed);
  }, SEED_AUTH);
});

type AgentSpec = {
  id: string;
  route: string;
  emptySelector: string;
  rootSelector?: string;
};

const AGENTS: AgentSpec[] = [
  {
    id: "channel",
    route: "/archive/channel",
    emptySelector: '[data-testid="channel-empty-state"]',
  },
  {
    id: "credit",
    route: "/archive/credit",
    emptySelector: '[data-testid="credit-empty-skeleton"]',
    rootSelector: '[data-credit-started="no"]',
  },
  {
    id: "report",
    route: "/archive/report",
    emptySelector: '[data-testid="report-empty-skeleton"]',
  },
  {
    id: "alert",
    route: "/archive/alert",
    emptySelector: '[data-testid="alert-empty-skeleton"]',
    rootSelector: '[data-testid="alert-workspace"][data-alert-started="no"]',
  },
  {
    id: "compli",
    route: "/archive/compliance",
    emptySelector: '[data-testid="compli-empty-skeleton"]',
    rootSelector: '[data-testid="compli-workspace"]',
  },
  {
    id: "riskctrl",
    route: "/archive/riskctrl",
    emptySelector: '[data-testid="riskctrl-empty-skeleton"]',
    rootSelector: '[data-testid="riskctrl-workspace"]',
  },
];

test.describe("B.3.4 · daily-visual · 6 助手 idle 视觉基线", () => {
  for (const agent of AGENTS) {
    test(`${agent.id} · idle 状态视觉基线 · ${agent.route}`, async ({ page }) => {
      await page.goto(agent.route, { waitUntil: "networkidle" });

      if (agent.rootSelector) {
        await expect(page.locator(agent.rootSelector)).toBeVisible();
      }
      const empty = page.locator(agent.emptySelector);
      await expect(empty).toBeVisible();

      // 截屏前再等 200ms · 让 Funnel Display glyph-rise 等动画 settle
      // (Playwright config 已 animations: "disabled" · 这层兜底防 SSR/CSR 切换)
      await page.waitForTimeout(200);

      await expect(page).toHaveScreenshot(`${agent.id}-idle.png`, {
        fullPage: true,
        // mask live clock (顶栏 20s tick) 避免误报
        mask: [
          page.locator('[data-testid="masthead-live-clock"]'),
          page.locator(".masthead-clock"),
        ],
      });
    });
  }
});

test.describe("B.3.4 · alert idle TDD red 锚点 (fix-indep 修绿)", () => {
  /**
   * PM 痛 4 (2026-05-11 03:45): "预警: 队列出来了但不能点客户详情 · 严重排版问题".
   *
   * 当前 alert idle 渲染了 input toggle / preview / 2 CTA / 3 skeleton card / status pill —
   * 看起来不空. 但 PM 真现场反馈是 "感官空白" — 推测原因:
   *   (a) skeleton card 占位符没数据 · 视觉上像 "空 div"
   *   (b) input preview 卡片在 demo 模式下信息密度低
   *
   * 此 test 锚定一个**可量化的密度要求** · fix-indep 修绿后 PM 真号 verify.
   * 如果 fix-indep 已经达到密度 · 此 test 直接通过 · 把 .fail() 注解去掉即可.
   */
  test.fail(
    "alert idle 主区可见文本节点数 ≥ 24 (内容密度 sanity)",
    async ({ page }) => {
      await page.goto("/archive/alert", { waitUntil: "networkidle" });
      await expect(page.locator('[data-testid="alert-empty-skeleton"]')).toBeVisible();

      // 主区可见文本节点 = empty-skeleton 内有非空 textContent 的 element 数
      const visibleTextCount = await page
        .locator('[data-testid="alert-empty-skeleton"] *:visible')
        .evaluateAll((els) =>
          els.filter((el) => {
            const t = (el.textContent ?? "").trim();
            return t.length > 0 && t.length < 200; // 排除整段 wrapping
          }).length,
        );

      // 锚点 24 = 当前 hero(3) + toggle(4) + preview(~6) + CTA(2) + skel(3) + status(3) ~ 21
      // 设 ≥ 24 略高于现状 · 强迫 fix-indep 加密度 · 修绿后此处通过
      expect(visibleTextCount).toBeGreaterThanOrEqual(24);
    },
  );
});
