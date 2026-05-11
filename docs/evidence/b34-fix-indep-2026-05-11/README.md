# B.3.4 fix-indep · 视觉 evidence (deferred to main CLI)

**Worker**: fix-indep · feat/b34-fix-indep
**Date**: 2026-05-11
**主活**: A · alert idle 空白填实 (PM 截图直接痛 #4)

## Why deferred

worker worktree 无 `node_modules` (worker 设计上是 isolated git worktree · 不装 deps ·
省盘 + 跑测仍走 main CLI 协调统一). 视觉 evidence 必须真起 dev server + Playwright 截图 ·
worker 跑不了. 走以下 2 路:

1. **主 CLI cherry-pick 后跑 spec**: `cd web && npm run test:snap -- alert-idle-fill.spec.ts`
   预期 4 PASS · 任何 RED 主 CLI 立即 stop the line · 不 silent merge.
2. **e2e-daily worker (P0-R5) 收 baseline**: 按 onboarding · cron 6am 跑 admin E2E +
   Playwright 视觉回归 · alert idle 空白入 spec 已交付 P0-R5 worker 接收.

## 待补 PNG (主 CLI 跑后填)

- `alert-idle-pre-scan.png` · started=no · AlertEmptyState (已富 · sanity 用)
- `alert-idle-post-scan.png` · started=yes && !selectedClientId · 新 mid + rb hint 出
- `alert-drill-open.png` · started=yes && selectedClientId · drill drawer 开 · idle 组件不渲染

## 验收硬线 (主 CLI 跑后填)

- [ ] `alert-idle-mid-overview` 容器存在
- [ ] `alert-idle-mid-card` × 3 (totals + top + next)
- [ ] mid 列 innerText > 120 chars
- [ ] `alert-idle-rb-hint` 容器存在 + 含 选中/榜单/点击/drill
- [ ] totals 数字 (red/yellow/green) 渲染
- [ ] drill drawer 打开后 idle 组件全消 (无 overlap)

## Cross-reference

- spec: `web/tests/regression/alert-idle-fill.spec.ts`
- impl commit: `2e18eb0` (feat · A-2 GREEN)
- test commit: `c356e87` (test · A-1 RED)
- onboarding: `docs/onboarding/B.3.4-mesh-onboarding.md` (4 worker mesh)
