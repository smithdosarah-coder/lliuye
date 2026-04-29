# Worker A1 (FIX 第 1 批) · Report UI + Fallback Banner · Onboarding

> Worker CLI 在 `D:/claude code/work-A1-inventory` (branch
> `feat/inventory-expand-A1`) · 复用 worktree。
> 上批 Stage E.4 (`abd216c`) 已 cherry-pick MERGED · 本批 fix user 报 bug 4。

## Goal

User 报 production bug 4 + bug 1 (同 fallback root 问题):

1. Report mock 按钮排版没对齐
2. Report "生成报告" 按钮太大
3. Report "上传模板" 按钮是摆设 (无 file input wire)
4. Report 后端调用失败 → silent mock fallback (违反 live-fallback-banner-spec)

修按 `docs/contracts/live-fallback-banner-spec.md` v1.0 规范。

## Acceptance

- [ ] **必读** `docs/contracts/live-fallback-banner-spec.md` v1.0 全文
- [ ] **mock-banner align**: `.report-mock-banner` padding/margin 跟 ReportHero 对齐 · 不溢出
- [ ] **"生成报告" button**: width ≤ 50% panel · 不溢出 (现可能 width: 100% 或太大)
- [ ] **"上传模板" button**: 真接 file input wire (`<input type="file" hidden ref={...} />`)
      + onClick → input.click() · onChange → POST /api/report/upload (multipart)
- [ ] **live failed banner**: POST `/api/report/v16/fill` SSE error / 4xx / 5xx →
      顶部 banner "⚠️ 后端 v16 fill 调用失败 (<code>) · 当前显 fallback 演示 · [重试]"
- [ ] tsc 0 error · `cd web && npx playwright test web/tests/regression/report-empty-state.spec.ts` 跑通 (现 case 不破)
- [ ] 加 smoke `web/tests/regression/report-fix.spec.ts` (3 case · 模板 button file input wire / mock-banner align / live failed banner 显)
- [ ] features-inventory.md 加 F-059 (Report live-fallback banner)
- [ ] commit trailer:
  ```
  Signal: WORKER-A1-FIX-REPORT-UI-FALLBACK-DONE
  RECOVER-FROM: abd216c
  PRESERVES: F-001~F-058
  RESPECTS: docs/contracts/live-fallback-banner-spec.md
  NEW-DOM: data-testid="report-live-fail-banner", data-testid="report-mock-banner"
  SMOKE-PASS: web/tests/regression/report-fix.spec.ts
  INVENTORY-ADDED: F-059
  ```

## Boundary

- 改: `web/src/app/archive/report/_components/ReportWorkspace.tsx` · `report-workspace.css` (or inline) · `web/src/lib/api/report.ts` (live fail handling)
- 加: `web/tests/regression/report-fix.spec.ts` · `docs/features-inventory.md` F-059
- 不动: backend agent_report/ · 其他 Workspace · CLAUDE.md · RFC

## Estim

3-4 hr (UI 排版 + file input wire + live fail handler · careful 不破现有)
