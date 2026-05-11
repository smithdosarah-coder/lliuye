# Runbook · daily-visual + admin-e2e (B.3.4 · P0-R5)

> 每天 06:00 Asia/Shanghai 自动跑 **2 件事**: (1) 6 助手 idle 视觉回归 (2) 6 agent admin 真号 E2E。失败时开 GitHub Issue 通知。
> Owner: e2e-daily worker · 接手人按本 doc 处置。
>
> **2 件事区别**:
> - **daily-visual** (主活 C+D · 视觉回归): 本地 dev server pixel diff · 防 worker 改坏前端 UI
> - **admin-e2e** (主活 A+B · 真号 E2E): prod backend SSE + UI flow · 防真后端假完成 / 503 / 字段缺

## 1. 这是干啥的

PM 2026-05-11 03:45 admin 真号 verify production 给出 6 件痛 · 总结 "**所有后端前端都混乱**"。e2e-daily 是 4 worker 之一 · 角色是**安全网 / 回归探测器** — 不修 bug · 只确保修了之后不被改回去。

每天 PM 起床前 (06:00 CST) 自动跑一次 · 任何 worker 改坏前端在 PM 看到之前先报警。

## 2. 触发时机 (2 job 共用)

workflow 内 2 个 job 独立 enable / 独立 Issue (per §7 admin-e2e job):

| 触发 | daily-visual job (flag) | admin-e2e job (flag) | fail 时行为 |
|---|---|---|---|
| `cron 22:00 UTC` (= 06:00 CST) | 要 `vars.DAILY_VISUAL_ENABLED=true` | 要 `vars.ADMIN_E2E_ENABLED=true` + `secrets.ADMIN_COOKIE` | 各 job 独立开 Issue (label 不同) |
| `workflow_dispatch` 手动 | 永远允许 (可选 `update_baseline=true`) | 永远允许 · spec 无 cookie 自动 skip | 不开 Issue · 上传 artifact |
| `push` 到 `feat/b34-e2e-daily` / `main` | 受 flag 限 | 受 flag 限 | 不开 Issue (Issue 仅 schedule 触发开) |

### 2.1 Feature flag enable 流程 (PM 操作)

**当前默认**: `DAILY_VISUAL_ENABLED` 未设 = disabled · cron 每天 fire 但 job 被 `if` 短路 · 不消耗 CI quota · 不开 Issue。

**enable 前置条件** (全满足才 enable · 防误报):

1. ✅ fix-indep worker 主活 B 完成 + cherry-pick 进 main (alert idle 加密度后 TDD red 转 green)
2. ✅ 手动 `workflow_dispatch` 设 `update_baseline=true` 跑一次 · 下载 artifact `daily-visual-snapshots-${run_id}` · 解压 commit baseline 到 `web/tests/regression/daily-visual.spec.ts-snapshots/` · push main
3. ✅ 再手动 `workflow_dispatch` (不设 update) 验证 baseline 跑通 · 6 个 idle 截图全 PASS

满足后 PM enable:
```bash
# GitHub repo Settings → Secrets and variables → Actions → Variables tab → New repository variable
# Name: DAILY_VISUAL_ENABLED
# Value: true
```

或用 gh CLI:
```bash
gh variable set DAILY_VISUAL_ENABLED --body "true" \
  --repo <owner>/<repo>
```

**disable** (维护期 / 误报暴雷): 同处 set value=`false` 或删 variable。

## 3. baseline 管理 (chicken-and-egg 问题)

Playwright `toHaveScreenshot` 第一次跑会 fail (`snapshot does not exist` · 自动写出 baseline)。流程:

### 3.1 首次创建 baseline

```bash
# 本地 (推荐 · 跨机器漂可控)
cd web
npx playwright test tests/regression/daily-visual.spec.ts \
  --project=chromium --update-snapshots

# 或 GHA: workflow_dispatch 触发 · 设 update_baseline=true
# 然后下载 artifact daily-visual-snapshots-* · 解压 commit 到
# web/tests/regression/daily-visual.spec.ts-snapshots/
```

commit baseline 用单独 commit:
```bash
git add web/tests/regression/daily-visual.spec.ts-snapshots/
git commit -m "test(b34-e2e-daily): create daily-visual baseline · 6 助手 idle"
```

### 3.2 baseline 更新 (合法 UI 变更)

UI 设计变了 / 新功能上线 / Theme 调色 → baseline 失效。**这不是 regression** · 走 `workflow_dispatch` 重建:

1. GHA UI → Actions → Daily Visual Regression → Run workflow
2. 选 branch · 设 `update_baseline=true` → Run
3. 等跑完 · 下载 artifact `daily-visual-snapshots-${run_id}`
4. 解压覆盖 `web/tests/regression/daily-visual.spec.ts-snapshots/`
5. commit + push:
   ```
   test(b34-e2e-daily): update daily-visual baseline · <reason>
   Reason: <UI change reason>
   Authorized-By: PM (or assigned reviewer)
   ```

## 4. 收到 fail Issue 怎么办

### 4.1 第一步: 看 diff

下载 artifact `daily-visual-report-${run_id}` · 解压看 `playwright-report/index.html`。

每个 fail case 有 3 张图: `expected.png` (baseline) · `actual.png` (实际) · `diff.png` (像素差)。

### 4.2 第二步: 判断真假 regression

| 现象 | 判断 | 处置 |
|---|---|---|
| diff 集中在某个组件 (如 button 颜色变了) · 没人 PR / merge | **真 regression** (可能是 dependency 升级 / SSR drift) | 找 commit `git log --since="24 hours ago" -- web/` · 找责任 worker fix-forward |
| diff 是有意 UI 变更 (有 PR merged) | **预期变化** | 走 §3.2 重建 baseline |
| diff 全屏 / 大面积 · 6 个 helper 都 fail | **环境问题** (字体加载失败 / Next 16 渲染 bug) | 检查 GHA log · 重跑一次 · 还 fail 找 fix-bugs worker |
| 单个 alert idle TDD red 锚点 fail (`expect(visibleTextCount).toBeGreaterThanOrEqual(24)`) | **预期 fail** (`test.fail()` 标记) | **不处置** · fix-indep ship 后此 test 转 green · 那时去 spec 删 `.fail()` 注解 |

### 4.3 第三步: 若是真 regression

1. 找 `git log --since="<since fail>" -- web/` 列嫌疑 commit
2. 找责任 worker (cherry-pick 来源 / commit author)
3. 让 worker fix-forward (改 web/ 必带 `PRESERVES / NEW-DOM / SMOKE-PASS` trailer per CLAUDE.md §13.5)
4. fix merge 后 daily-visual 自动转绿 · Issue 自动 close (worker 手 close 也行)
5. 若 fix-forward 也跟 baseline 略不同 (合理 diff) · 走 §3.2 重建 baseline

## 5. alert idle TDD red 锚点

spec 里有一个 `test.fail()` 注解的 test:

```ts
test.fail("alert idle 主区可见文本节点数 ≥ 24 · 内容密度 sanity", async ({ page }) => {
  // 当前 alert empty 渲染约 21 节点 · 锚点 24 强迫 fix-indep 加密度
});
```

**意义**: PM 痛 4 (2026-05-11 03:45) "预警: 队列出来了但不能点客户详情 · 严重排版问题"。`test.fail()` 表示**期望此 test fail** · fail 时 framework 视为 PASS。

fix-indep worker ship 后 alert empty 加密度 (≥ 24 节点) → test 实际 PASS → framework 报错 ("Test was expected to fail, but passed") → 此时去 daily-visual.spec.ts 删 `.fail()` 注解 → 永久 green。

**主 CLI 验收**: 当 GHA daily-visual 因为这个 test "意外通过" 而 fail 时 · 那是 fix-indep 修绿的信号 · PM 验完后让 e2e-daily worker 去 spec 删 `.fail()`。

## 6. 失败通知接收

GitHub Issue auto-create · default subscribers:
- repo `Watch`/`All Activity` 的人 (邮件)
- mention 的人 (TBD: 主 CLI / PM 配上)

**Fault-tolerance** (2026-05-11 PM 反馈加 · daily-visual.yml v1.1):
- **labels 自动建** — `gh label create daily-visual / regression --force` 在 issue 步前置 · 不依赖 PM 手动 · `|| true` 兜底权限失败
- **issue 步 continue-on-error** — gh API 500 / repo 权限不足 / network drop 都不再拖垮整个 job · workflow conclusion 跟 spec 跑结果一致

**未来扩展** (本 sprint 不做): 加飞书 webhook · GHA Issue 开后调 lark-cli 发群消息 (per CLAUDE.md skill 触发映射 lark-im)。当前用 GitHub Issue 邮件兜底。

## 7. admin-e2e job (主活 A + B · 2026-05-11 PM reframe)

### 7.1 干啥

跟 daily-visual 同 workflow 同 cron 触发 · 但**完全不同**:

| 项 | daily-visual | admin-e2e |
|---|---|---|
| baseURL | http://127.0.0.1:3101 (本地 dev server) | https://liuye.me (prod) |
| 内容 | 6 助手 idle 截图 diff | 6 agent demo/run 真后端 SSE + UI E2E |
| 依赖 | 无 (Playwright 自带) | secrets.ADMIN_COOKIE + 真 LLM/Tavily key 在 prod 上 |
| Issue label | daily-visual,regression | admin-e2e,regression |
| flag | vars.DAILY_VISUAL_ENABLED | vars.ADMIN_E2E_ENABLED |

### 7.2 admin-e2e enable 流程 (PM 操作)

**前置条件**:
1. ✅ 在 GitHub Settings → Secrets and variables → Actions → **Secrets** tab 加 `ADMIN_COOKIE`
   - Value: admin 真号 cookie JWT (浏览器 DevTools Application → Cookies → 复制 `zhongan_auth` 值)
   - 或完整 `zhongan_auth=<value>` 也接受 (脚本会自动 strip 前缀)
2. ✅ 手动 `workflow_dispatch` 跑一次 admin-e2e job · 6 spec + bash 探针都过
3. ✅ enable flag:
   ```bash
   gh variable set ADMIN_E2E_ENABLED --body "true" --repo <owner>/<repo>
   ```

**cookie 过期处理**: cookie 过期后 GHA fail → 自动开 Issue ("ADMIN_COOKIE 过期") → PM 重新登 prod 取 cookie → 在 Secrets 里更新 (覆盖即可)。

### 7.3 admin-e2e fail 怎么办

GHA Issue 自动开 (label `admin-e2e,regression`) · 含可能原因列表:
1. cookie 过期 (bash 探针 exit 2 BLOCKED)
2. prod 5xx (找 ECS uvicorn log)
3. UI selector 漂 (调 admin-*.spec.ts selector)
4. SSE 慢超时 (真 LLM/Tavily 慢)

下载 artifact `admin-e2e-report-${run_id}` 看 Playwright report (含每 spec 的失败截图 + trace)。

### 7.4 本地跑 admin-e2e 验

```bash
export ADMIN_COOKIE='eyJhbGc...'           # 或 'zhongan_auth=eyJhbGc...'
export E2E_BASE_URL='https://liuye.me'
export PLAYWRIGHT_BASE_URL='https://liuye.me'  # 让 Playwright 跳过本地 dev server

# bash 探针 (curl SSE · 快 · 10-60s):
bash scripts/e2e/run_admin_daily.sh

# 6 Playwright spec (UI E2E · 慢 · 3-10 分钟):
cd web && npx playwright test tests/e2e/admin-*.spec.ts --project=chromium
```

## 8. 退役条件

本 daily-visual 是 B.3.4 的安全网。退役时机:
- 所有 6 助手 idle/running/done 状态都有专门 spec 覆盖 (各 agent worker 自己加)
- alert idle TDD red 锚点已 green 删除 (fix-indep ship 后)
- 6 个月内 0 次真 regression 触发 → 可以降级到周跑 / 删除

退役需 PM 显式 ratify · 同 commit `Authorized-By: PM` trailer (per CLAUDE.md §13.5)。

---

## Refs

- `web/tests/regression/daily-visual.spec.ts` (spec)
- `.github/workflows/daily-visual.yml` (GHA cron)
- B.3.4 修正版 commit `5f3d2ec` (2026-05-11 06:30 GO · KT R5)
- `docs/onboarding/B.3.4-mesh-onboarding.md` (4 worker 总说明)
- CLAUDE.md §13 (production 同步纪律 + web/ 改动 trailer 规则)
