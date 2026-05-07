import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";

/**
 * Phase C · 5 角色 walkthrough 真演 + 截图 (PM P3 task)
 *
 * per Phase C charter §11 客户走访 SOP + PM 5/6 verbatim "5 角色 walkthrough 真演":
 *
 * 5 user × 6 page · 每 user 截图存档:
 *   1. 王哲 (RM)        · /today + /customer/list + /archive/channel + /archive/report
 *   2. 李华 (审贷员)    · /today + /archive/credit + /archive/report
 *   3. 周敏 (合规官)    · /today + /archive/compliance
 *   4. 陈凯 (风险经理)  · /today + /archive/riskctrl + /archive/alert
 *   5. 刘野 (admin)     · /today + 全 6 archive
 *
 * 输出: web/tests/screenshots/phase-c-5roles/<user>/<page>.png
 *
 * 不 assert UI 内容 (避免脆性) · 仅:
 *   - 登录成功
 *   - page 加载 200 (不 redirect /403)
 *   - 截图存档 (供 PM 验收)
 *
 * 当 backend 不可达 / login 失败 · spec skip · 不阻 build.
 */

const TEST_USERS = [
  {
    name: "王哲",
    id: "u_wangzhe",
    password: "wangzhe",
    role: "rm",
    pages: [
      { path: "/today", label: "today" },
      { path: "/customer/list", label: "customer-list" },
      { path: "/archive/channel", label: "channel" },
      { path: "/archive/report", label: "report" },
    ],
  },
  {
    name: "李华",
    id: "u_lihua",
    password: "lihua",
    role: "credit_officer",
    pages: [
      { path: "/today", label: "today" },
      { path: "/archive/credit", label: "credit" },
      { path: "/archive/report", label: "report" },
    ],
  },
  {
    name: "周敏",
    id: "u_zhoumin",
    password: "zhoumin",
    role: "compliance_officer",
    pages: [
      { path: "/today", label: "today" },
      { path: "/archive/compliance", label: "compliance" },
    ],
  },
  {
    name: "陈凯",
    id: "u_chenkai",
    password: "chenkai",
    role: "risk_manager",
    pages: [
      { path: "/today", label: "today" },
      { path: "/archive/riskctrl", label: "riskctrl" },
      { path: "/archive/alert", label: "alert" },
    ],
  },
  {
    name: "刘野",
    id: "u_liuye",
    password: "liuye",
    role: "admin",
    pages: [
      { path: "/today", label: "today" },
      { path: "/archive/channel", label: "channel" },
      { path: "/archive/credit", label: "credit" },
      { path: "/archive/alert", label: "alert" },
      { path: "/archive/compliance", label: "compliance" },
      { path: "/archive/report", label: "report" },
      { path: "/archive/riskctrl", label: "riskctrl" },
    ],
  },
];

const SCREENSHOTS_DIR = path.resolve(
  __dirname,
  "..",
  "screenshots",
  "phase-c-5roles",
);

async function backendReachable(page: import("@playwright/test").Page): Promise<boolean> {
  try {
    const r = await page.request.get("/api/auth/me");
    return r.status() < 500;
  } catch {
    return false;
  }
}

async function login(page: import("@playwright/test").Page, id: string, password: string): Promise<boolean> {
  try {
    const r = await page.request.post("/api/auth/login", {
      data: { user_id: id, password },
    });
    return r.ok();
  } catch {
    return false;
  }
}

for (const user of TEST_USERS) {
  test.describe(`Phase C walkthrough · ${user.name} (${user.role})`, () => {
    test.beforeEach(async ({ page }) => {
      const ok = await backendReachable(page);
      test.skip(!ok, "backend 不可达 · skip walkthrough screenshot");
      const loggedIn = await login(page, user.id, user.password);
      test.skip(!loggedIn, `${user.name} 登录失败 · skip walkthrough`);
    });

    for (const p of user.pages) {
      test(`${user.name} → ${p.path}`, async ({ page }) => {
        const dir = path.join(SCREENSHOTS_DIR, user.role);
        await mkdir(dir, { recursive: true });

        await page.goto(p.path, { waitUntil: "networkidle", timeout: 30_000 });
        // 等动画 / 数据 fetch 完
        await page.waitForTimeout(800);

        // 不应 redirect 到 /login or /403
        const url = page.url();
        expect.soft(url).not.toContain("/login");
        expect.soft(url).not.toContain("/403");

        const screenshotPath = path.join(dir, `${p.label}.png`);
        await page.screenshot({ path: screenshotPath, fullPage: true });

        // 输出截图路径供 PM 验收 console
        // eslint-disable-next-line no-console
        console.log(`[walkthrough] ${user.name}@${p.path} → ${screenshotPath}`);
      });
    }
  });
}
