# Worker A3 (Stage C frontend 第 1 批) · Agent5 Compliance Workspace frontend · Onboarding

> Worker CLI 在 `D:/claude code/work-A3-prd` (branch `feat/prd-summaries-A3`) ·
> 复用 Stage A+B+C backend 同 worktree。
> 上批 Stage C.4 Compli backend (`a76cea2`) 已 cherry-pick MERGED (`fb78b85`) ·
> 本批 Stage C.4 frontend 启动。

## Goal

实装 master plan §C.4 frontend — Agent5 Compliance Workspace · production-grade
完整 deliver。复刻 Channel pattern · 必遵 empty-state-design-protocol。
**gap #6 (Compli Workspace) frontend 闭环**。

## Acceptance

- [ ] **必读** `docs/contracts/empty-state-design-protocol.md` v1.0
- [ ] **必读** `docs/contracts/agent-compli-spec.md` (Stage A.5 cherry-pick)
- [ ] **必读** Channel pattern `web/src/app/archive/channel/_components/ChannelWorkspace.tsx`
- [ ] **空白启动**: `started` default false · 渲染 Hero + 3 CTA + panel 空骨架 + status pill
- [ ] **3 CTA 分级**:
  - Primary 显著: 上传政策文件 + 上传业务制度 → POST /api/compliance/policy_scan SSE
  - Secondary: 选模板 + 起巡检 (matrix_check 路径)
  - Tertiary 降级: 历史巡检 dropdown 标 `(示例)`
- [ ] **Panel 空骨架** (无真数据):
  - PolicyDiff (政策 ticker 最新 3 条)
  - MatrixScan (N×M 冲突矩阵 doc × clause · 灰底 + "扫描完成显示矩阵")
  - ConflictPoints list (改/补/强 三类 chip)
  - RevisionDraft (修订意见草稿 + Word 导出 button)
- [ ] **后端 wire**:
  - 政策扫 → POST /api/compliance/policy_scan (SSE)
  - 矩阵 → POST /api/compliance/matrix_check
  - 导出 → POST /api/compliance/export_docx
- [ ] tsc 0 error · `cd web && npx playwright test web/tests/regression/compli-empty-state.spec.ts` 跑通
- [ ] features-inventory.md 加 F-050 (Compli empty state) + F-054 (Compli 完整 workspace)
- [ ] commit trailer:
  ```
  Signal: WORKER-A3-STAGE-CF-COMPLI-FRONTEND-DONE
  PRESERVES: F-001~F-046
  RESPECTS: docs/contracts/empty-state-design-protocol.md
  NEW-DOM: data-testid="compli-policy-upload-cta", data-testid="compli-business-upload-cta",
           data-testid="compli-policy-scan-cta", data-testid="compli-matrix-cell",
           data-testid="compli-conflict-chip", data-testid="compli-revision-draft",
           data-testid="compli-export-docx-btn", data-testid="compli-empty-skeleton"
  SMOKE-PASS: web/tests/regression/compli-empty-state.spec.ts
  INVENTORY-ADDED: F-050, F-054
  ```

## Boundary

- **改**: `web/src/app/archive/compliance/_components/CompliWorkspace.tsx` 全套 panel
- **加**: `web/tests/regression/compli-empty-state.spec.ts`
- **不动**: backend agent_compliance/ (已 deliver) · 其他 Workspace · CLAUDE.md · RFC

## 红线

- 不抄 ChannelWorkspace · 复刻 pattern 但适配 Compli PRD (政策事件驱动 + N×M 矩阵)
- empty-state default false · 用户必须主动上传政策 + 业务制度才扫
- mock data 不 default load · dropdown 标 (示例)
- F-001~F-046 全保留 · trailer PRESERVES 列全
- 中文文案别 inline `'...'`

## Method

1. Read empty-state-design-protocol + agent-compli-spec + ChannelWorkspace
2. Sketch CompliWorkspace empty state + 政策驱动 trigger pattern
3. 实装 surgical · tsc · playwright smoke
4. inventory + trailer

## Estim

5-7 hr (Workspace 复刻 + 矩阵 panel + 修订意见 + Word 导出 + smoke)
