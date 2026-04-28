# Worker A1 (Stage C frontend 第 1 批) · Agent6 Report Workspace frontend · Onboarding

> Worker CLI 在 `D:/claude code/work-A1-inventory` (branch
> `feat/inventory-expand-A1`) · 复用 Stage A+B+C backend 同 worktree。
> 上批 Stage C.1 Report backend (`b014813`) 已 cherry-pick MERGED (`129e7dc`) ·
> 本批 Stage C.1 frontend 启动。

## Goal

实装 master plan §C.1 frontend — Agent6 Report Workspace · production-grade
完整 deliver。复刻 Channel pattern (db7eb13) · 必遵 empty-state-design-protocol。
**gap #6 (Report Workspace) frontend 闭环**。

## Acceptance

- [ ] **必读** `docs/contracts/empty-state-design-protocol.md` v1.0 全文
- [ ] **必读** `docs/contracts/agent-report-spec.md` (Stage A.5 cherry-pick)
- [ ] **必读** Channel 现成 pattern: `web/src/app/archive/channel/_components/ChannelWorkspace.tsx`
- [ ] **空白启动**: `started` default false · 渲染 Hero + 3 CTA + panel 空骨架 + status pill
- [ ] **3 CTA 分级**:
  - Primary 显著: 上传材料文件 (multipart → POST /api/report/upload)
  - Secondary: 选模板 (来自 v16 templates)
  - Tertiary 降级: 历史 session (dropdown 标 `(示例)`)
- [ ] **Panel 空骨架** (无真数据 · 灰底 placeholder):
  - Materials grid (上传完后填)
  - Fields 抽取 (v16 fill 完后填)
  - Draft 预览 (LLM 生成完后填)
  - Preview A4 (Word 导出前)
  - Conversation seed
- [ ] **后端 wire**:
  - 上传材料 → POST /api/report/upload (返 report_id)
  - 触发生成 → POST /api/report/v16/fill (SSE · classifier → generator → QC gate)
  - refine → POST /api/report/refine_section
  - 导出 → POST /api/report/export_docx + GET /api/report/downloads/{id}
- [ ] tsc 0 error · `cd web && npx playwright test web/tests/regression/report-empty-state.spec.ts` 跑通
- [ ] features-inventory.md 加 F-047 (Report empty state) + F-052 (Report 完整 workspace)
- [ ] commit trailer:
  ```
  Signal: WORKER-A1-STAGE-CF-REPORT-FRONTEND-DONE
  PRESERVES: F-001~F-046
  RESPECTS: docs/contracts/empty-state-design-protocol.md
  NEW-DOM: data-testid="report-upload-cta", data-testid="report-template-select",
           data-testid="report-history-dropdown", data-testid="report-empty-skeleton",
           data-testid="report-status-pill"
  SMOKE-PASS: web/tests/regression/report-empty-state.spec.ts
  INVENTORY-ADDED: F-047, F-052
  ```

## Boundary

- **改**: `web/src/app/archive/report/_components/ReportWorkspace.tsx` (全新或 surgical 改造)
  + 各 panel inline component
- **加**: `web/tests/regression/report-empty-state.spec.ts`
- **不动**: backend agent_report/ (已 deliver) · 其他 Workspace · CLAUDE.md · RFC ·
  `web/src/app/archive/channel/*` (Channel 已完整)

## 红线

- 不抄 ChannelWorkspace 整 file · 复刻 pattern 但适配 Report PRD (字段抽取 · v16 pipeline events)
- empty-state default false · DO NOT 自动 trigger LLM call
- mock data 不 default load · 仅 dropdown 触发 + 标 (示例)
- F-001~F-046 全保留 · trailer PRESERVES 列全
- 中文文案别 inline `'...'` (web/CLAUDE.md 已知坑)
- Zustand selector 别 inline `?? []`

## Method

1. Read empty-state-design-protocol.md (规范)
2. Read agent-report-spec.md (PRD)
3. Read ChannelWorkspace.tsx (pattern reference)
4. Sketch ReportWorkspace.tsx 结构 (started state · 3 CTA · 5 panel · SSE consume)
5. 实装 surgical · tsc · playwright smoke
6. inventory + trailer

## Estim

5-7 hr (Workspace 复刻 + 5 panel + SSE consume + smoke)
