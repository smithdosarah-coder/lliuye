# Worker A3 (Stage C frontend 第 2 批) · Agent2 Forge/Riskctrl Workspace frontend · Onboarding

> Worker CLI 在 `D:/claude code/work-A3-prd` (branch `feat/prd-summaries-A3`) ·
> 复用 worktree。
> 上批 Stage CF Compli frontend (`c75488f`) 已 cherry-pick MERGED (`7b517a4`) ·
> 本批 Riskctrl frontend 启动。

## Goal

实装 master plan §C.5 frontend — Agent2 Forge/Riskctrl Workspace · production-grade
完整 deliver。复刻 Channel pattern · 必遵 empty-state-design-protocol。
**gap #6 (Riskctrl Workspace) frontend 闭环 · 收尾 5 Agent Workspace 全 production-grade**。

## Acceptance

- [ ] **必读** `docs/contracts/empty-state-design-protocol.md` v1.0
- [ ] **必读** `docs/contracts/agent-forge-spec.md` (Stage A.5 cherry-pick)
- [ ] **必读** Channel + Credit + Compli pattern
- [ ] **空白启动**: `started` default false · 渲染 Hero + 3 CTA + panel 空骨架 + status pill
- [ ] **3 CTA 分级**:
  - Primary 显著: "选样本 + 写策略" → POST /api/riskctrl/dsl_gen 真生成 DSL
  - Secondary: 选预置规则集
  - Tertiary 降级: 历史回测 dropdown 标 `(示例)`
- [ ] **Panel 空骨架** (无真数据):
  - DSL Editor (规则树 viewer · IF/AND/OR/THEN 4 op)
  - KS / AUC / 通过率 三大指标卡 + KS 双线图
  - Sample 分布 stacked bars (pass / review / block)
  - ScanCTA "样本回测" 5 步进度
- [ ] **后端 wire** (上批 cb8bff1 已 deliver):
  - dsl_gen → POST /api/riskctrl/dsl_gen (真 LLM 生成)
  - backtest → POST /api/riskctrl/backtest (真跑 · KS/AUC)
  - run → POST /api/riskctrl/run (placeholder · 暂不真上线)
- [ ] tsc 0 error · `cd web && npx playwright test web/tests/regression/riskctrl-empty-state.spec.ts` 跑通
- [ ] features-inventory.md 加 F-051 (Riskctrl empty state) + F-056 (Riskctrl 完整 workspace)
- [ ] commit trailer:
  ```
  Signal: WORKER-A3-STAGE-CF2-RISKCTRL-FRONTEND-DONE
  PRESERVES: F-001~F-055 (列全)
  RESPECTS: docs/contracts/empty-state-design-protocol.md
  NEW-DOM: data-testid="riskctrl-dsl-editor", data-testid="riskctrl-dsl-gen-cta",
           data-testid="riskctrl-backtest-cta", data-testid="riskctrl-ks-chart",
           data-testid="riskctrl-sample-dist", data-testid="riskctrl-empty-skeleton",
           data-testid="riskctrl-export-docx-btn"
  SMOKE-PASS: web/tests/regression/riskctrl-empty-state.spec.ts
  INVENTORY-ADDED: F-051, F-056
  ```

## Boundary

- **改**: `web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx` 全套 panel + `riskctrl-workspace.css`
- **加**: `web/tests/regression/riskctrl-empty-state.spec.ts`
- **不动**: backend agent_riskctrl/ (上批 c69f021 已 deliver) · 其他 Workspace · CLAUDE.md · RFC

## 红线

- 不抄 ChannelWorkspace 整 file · 复刻 pattern 但适配 Riskctrl PRD (DSL 树 + KS 图 + sample 分布)
- empty-state default false · DSL editor 默认空 · 用户 LLM gen / 自己写
- mock data 不 default load · dropdown 标 (示例)
- F-001~F-055 全保留
- 中文文案别 inline `'...'`

## Method

1. Read empty-state-design-protocol + agent-forge-spec + Compli/Credit pattern
2. Sketch RiskctrlWorkspace DSL editor + KS chart + sample dist + empty state
3. 实装 surgical · tsc · playwright smoke
4. inventory + trailer

## Estim

5-7 hr (DSL editor + KS chart + sample stacked + 回测 CTA + smoke)
