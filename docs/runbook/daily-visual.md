# Runbook · daily-visual 视觉回归 (B.3.4 · P0-R5)

> 每天 06:00 Asia/Shanghai 自动跑 6 助手 idle 状态视觉巡检 · 失败时开 GitHub Issue 通知。
> Owner: e2e-daily worker · 接手人按本 doc 处置。

## 1. 这是干啥的

PM 2026-05-11 03:45 admin 真号 verify production 给出 6 件痛 · 总结 "**所有后端前端都混乱**"。e2e-daily 是 4 worker 之一 · 角色是**安全网 / 回归探测器** — 不修 bug · 只确保修了之后不被改回去。

每天 PM 起床前 (06:00 CST) 自动跑一次 · 任何 worker 改坏前端在 PM 看到之前先报警。

## 2. 触发时机

| 触发 | 跑啥 | fail 时行为 |
|---|---|---|
| `cron 22:00 UTC` (= 06:00 CST) | 6 helper × 1 idle snapshot diff | **开 GitHub Issue** (label `daily-visual,regression`) |
| `workflow_dispatch` 手动 | 同上 · 可选 `update_baseline=true` | 不开 Issue · 上传 artifact |
| `push` 到 `feat/b34-e2e-daily` / `main` (改 spec / snapshots / workflow 时) | 同上 | 不开 Issue (Issue 仅 schedule 触发开) |

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

**未来扩展** (本 sprint 不做): 加飞书 webhook · GHA Issue 开后调 lark-cli 发群消息 (per CLAUDE.md skill 触发映射 lark-im)。当前用 GitHub Issue 邮件兜底。

## 7. 退役条件

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
