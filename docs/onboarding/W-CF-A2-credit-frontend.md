# Worker A2 (Stage C frontend 第 1 批) · Agent3 Credit Workspace frontend · Onboarding

> Worker CLI 在 `D:/claude code/work-A2-contracts` (branch
> `feat/contracts-bootstrap-A2`) · 复用 Stage A+B+C backend 同 worktree。
> 上批 Stage C.2 Credit backend (`4cb1690`) 已 cherry-pick MERGED (`cc0be4a`) ·
> 本批 Stage C.2 frontend 启动。

## Goal

实装 master plan §C.2 frontend — Agent3 Credit Workspace · production-grade
完整 deliver。复刻 Channel pattern · 必遵 empty-state-design-protocol。
**gap #6 (Credit Workspace) frontend 闭环**。

## Acceptance

- [ ] **必读** `docs/contracts/empty-state-design-protocol.md` v1.0
- [ ] **必读** `docs/contracts/agent-credit-spec.md` (Stage A.5 cherry-pick)
- [ ] **必读** Channel pattern `web/src/app/archive/channel/_components/ChannelWorkspace.tsx`
- [ ] **空白启动**: `started` default false · 渲染 Hero + 3 CTA + panel 空骨架 + status pill
- [ ] **3 stage_tab 切换** (corporate / small_business / retail · per agent-credit-spec.md)
- [ ] **3 CTA 分级**:
  - Primary 显著: 选 Agent6 handoff 来的报告材料 + 起决策 (POST /api/credit/decision SSE)
  - Secondary: 直接输入字段 + 起决策
  - Tertiary 降级: 历史决策 dropdown 标 `(示例)`
- [ ] **Panel 空骨架** (无真数据):
  - ScoreRadar 4 维 + ScoreRing decision badge (评分完显示)
  - Decision Letter (LLM 生成的决策建议书 + Word 导出 button)
  - 红线检查 list (pass / warn / fail)
  - Stage tabs (corporate/small_business/retail)
  - EvidenceLane + RiskRadar (Q-033 路由)
- [ ] **后端 wire**:
  - 起决策 → POST /api/credit/decision (SSE · stage_tab + report_json + materials)
  - 预设 → GET /api/credit/presets
  - 导出 → POST /api/credit/export_docx
- [ ] tsc 0 error · `cd web && npx playwright test web/tests/regression/credit-empty-state.spec.ts` 跑通
- [ ] features-inventory.md 加 F-048 (Credit empty state) + F-053 (Credit 完整 workspace)
- [ ] commit trailer:
  ```
  Signal: WORKER-A2-STAGE-CF-CREDIT-FRONTEND-DONE
  PRESERVES: F-001~F-046
  RESPECTS: docs/contracts/empty-state-design-protocol.md
  NEW-DOM: data-testid="credit-stage-tab-corporate", "...-small_business", "...-retail",
           data-testid="credit-decision-cta", data-testid="credit-redlines-list",
           data-testid="credit-export-docx-btn", data-testid="credit-empty-skeleton"
  SMOKE-PASS: web/tests/regression/credit-empty-state.spec.ts
  INVENTORY-ADDED: F-048, F-053
  ```

## Boundary

- **改**: `web/src/app/archive/credit/_components/CreditWorkspace.tsx` 全套 panel
- **加**: `web/tests/regression/credit-empty-state.spec.ts`
- **不动**: backend agent_credit/ (已 deliver) · 其他 Workspace · CLAUDE.md · RFC

## 红线

- 不抄 ChannelWorkspace · 复刻 pattern 但适配 Credit PRD (3 stage_tab + 4 维评分 + 红线)
- empty-state default false · 3 stage_tab 切换不破坏 empty state
- mock data 不 default load · dropdown 标 (示例)
- F-001~F-046 全保留 · trailer PRESERVES 列全
- 中文文案别 inline `'...'`

## Method

1. Read empty-state-design-protocol + agent-credit-spec + ChannelWorkspace
2. Sketch CreditWorkspace 3 stage_tab 切换 + empty state
3. 实装 surgical · tsc · playwright smoke
4. inventory + trailer

## Estim

5-7 hr (3 stage_tab 切换 + 5 panel + SSE consume + smoke)
