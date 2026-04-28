# Worker A3 (FIX 第 1 批) · Riskctrl + Alert Live-Fallback Banner · Onboarding

> Worker CLI 在 `D:/claude code/work-A3-prd` (branch `feat/prd-summaries-A3`) ·
> 复用 worktree。
> 上批 Stage E.2 monitoring (`33a6b63`) 已 cherry-pick MERGED · 本批 fix user 报 bug 1+2。

## Goal

User 报 production bug 1+2 (同 root):

1. Riskctrl: 后端 backtest 调用失败 (HTTP 422) · 但 mock 数据仍 fallback 显出 ("左右脑互博")
2. Alert: 点任何按键直接出 mock 数据 · 没真 trigger backend SSE

修按 `docs/contracts/live-fallback-banner-spec.md` v1.0 规范。

## Acceptance

- [ ] **必读** `docs/contracts/live-fallback-banner-spec.md` v1.0 全文
- [ ] **Riskctrl Workspace fix**:
  - "样本回测" button 真接 POST `/api/riskctrl/backtest` (现状: 后端返 422 但前端 swap mock)
  - HTTP 422 / 4xx / 5xx → 顶部 banner "⚠️ 后端 backtest 调用失败 (<code>) · 当前显 fallback 演示 · [重试]"
  - 同处理 dsl_gen / run endpoint
- [ ] **Alert Workspace fix**:
  - "启动风险扫描" button 真接 POST `/api/alert/scan` SSE (现状: 不真 wire · 直接 dispatch mock store action)
  - SSE error / 4xx / 5xx → 顶部 banner "⚠️ 后端 alert scan 调用失败 (<code>) · 当前显 fallback 演示 · [重试]"
  - hitlist + drill 路径同
- [ ] tsc 0 error · 加 smoke `web/tests/regression/riskctrl-alert-fix.spec.ts` (4 case · riskctrl 422 banner / alert scan wire / hitlist wire / drill wire)
- [ ] features-inventory.md 加 F-061 (Riskctrl/Alert live-fallback banner)
- [ ] commit trailer:
  ```
  Signal: WORKER-A3-FIX-RISKCTRL-ALERT-FALLBACK-DONE
  RECOVER-FROM: 33a6b63
  PRESERVES: F-001~F-060
  RESPECTS: docs/contracts/live-fallback-banner-spec.md
  NEW-DOM: data-testid="riskctrl-live-fail-banner", data-testid="alert-live-fail-banner"
  SMOKE-PASS: web/tests/regression/riskctrl-alert-fix.spec.ts
  INVENTORY-ADDED: F-061
  ```

## Boundary

- 改: `web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx` ·
      `web/src/app/archive/alert/_components/AlertWorkspace.tsx` ·
      `web/src/lib/api/riskctrl.ts` (or new) + `web/src/lib/api/alert.ts` (or new)
      (live fail handling)
- 加: `web/tests/regression/riskctrl-alert-fix.spec.ts` · F-061 inventory
- 不动: backend agent_riskctrl/ · agent_alert/ · 其他 Workspace · CLAUDE.md · RFC

## Estim

4-5 hr (2 Workspace + 2 endpoint + banner + 4 case smoke · careful 不破 backtest core)

## NB

- Riskctrl backend 422 真原因可能是 frontend req body shape 不对 · 先验 backend
  expect (`agent_riskctrl/api.py` /backtest body schema) · 然后 frontend match
- Alert "启动扫描" button 现 click 直接 dispatch mock store action · 改成真 fetch
  POST /api/alert/scan SSE · 流式更新红黄绿榜单
