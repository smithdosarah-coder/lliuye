# Worker A2 (Stage C frontend 第 2 批) · Agent4 Alert Workspace frontend · Onboarding

> Worker CLI 在 `D:/claude code/work-A2-contracts` (branch
> `feat/contracts-bootstrap-A2`) · 复用 worktree。
> 上批 Stage CF Credit frontend (`ae803b8`) 已 cherry-pick MERGED (`71a22a8`) ·
> 本批 Alert frontend 启动。

## Goal

实装 master plan §C.3 frontend — Agent4 Alert Workspace · production-grade
完整 deliver。复刻 Channel pattern · 必遵 empty-state-design-protocol。
**gap #6 (Alert Workspace) frontend 闭环**。

## Acceptance

- [ ] **必读** `docs/contracts/empty-state-design-protocol.md` v1.0
- [ ] **必读** `docs/contracts/agent-alert-spec.md` (Stage A.5 cherry-pick)
- [ ] **必读** Channel + Credit + Compli pattern (`web/src/app/archive/{channel,credit,compliance}/_components/*Workspace.tsx`)
- [ ] **空白启动**: `started` default false · 渲染 Hero + 3 CTA + panel 空骨架 + status pill
- [ ] **3 CTA 分级**:
  - Primary 显著: "启动风险扫描" → POST /api/alert/scan SSE (在贷客户池规则扫)
  - Secondary: 选规则集 / 调整阈值
  - Tertiary 降级: 历史扫描 dropdown 标 `(示例)`
- [ ] **Panel 空骨架** (无真数据):
  - TrafficLight 红/黄/绿三灯墙 (扫完显)
  - HitList list (红/黄/绿榜单 · 客户数 + 最严重信号)
  - SignalMap 30 天热力 + 触达率
  - DrillDetail drawer (点客户 → 信号 timeline + 处置建议)
- [ ] **后端 wire** (A3 上批已 deliver):
  - 启动扫描 → POST /api/alert/scan (SSE · 规则扫 → 命中 → 分级)
  - 榜单 → GET /api/alert/hitlist
  - 详情 → GET /api/alert/drill/{client_id}
- [ ] tsc 0 error · `cd web && npx playwright test web/tests/regression/alert-empty-state.spec.ts` 跑通
- [ ] features-inventory.md 加 F-049 (Alert empty state) + F-055 (Alert 完整 workspace)
- [ ] commit trailer:
  ```
  Signal: WORKER-A2-STAGE-CF2-ALERT-FRONTEND-DONE
  PRESERVES: F-001~F-054 (列全)
  RESPECTS: docs/contracts/empty-state-design-protocol.md
  NEW-DOM: data-testid="alert-scan-cta", data-testid="alert-traffic-light-{red,yellow,green}",
           data-testid="alert-hitlist-row", data-testid="alert-drill-drawer",
           data-testid="alert-empty-skeleton", data-testid="alert-export-docx-btn"
  SMOKE-PASS: web/tests/regression/alert-empty-state.spec.ts
  INVENTORY-ADDED: F-049, F-055
  ```

## Boundary

- **改**: `web/src/app/archive/alert/_components/AlertWorkspace.tsx` 全套 panel + `alert-workspace.css`
- **加**: `web/tests/regression/alert-empty-state.spec.ts`
- **不动**: backend agent_alert/ (上批 5f310ae 已 deliver) · 其他 Workspace · CLAUDE.md · RFC

## 红线

- 不抄 ChannelWorkspace 整 file · 复刻 pattern 但适配 Alert PRD (红黄绿 + drill detail + 在贷客户池)
- empty-state default false · DO NOT 自动 trigger LLM call
- mock data 不 default load · dropdown 标 (示例)
- F-001~F-054 全保留
- 中文文案别 inline `'...'`

## Method

1. Read empty-state-design-protocol + agent-alert-spec + Compli/Credit pattern
2. Sketch AlertWorkspace 红黄绿 layout + drill drawer + empty state
3. 实装 surgical · tsc · playwright smoke
4. inventory + trailer

## Estim

5-7 hr (Workspace 复刻 + 红黄绿 panel + drill drawer + 在贷客户池 mock + smoke)
