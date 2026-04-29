# Worker A3 · 6 Agent PRD Summaries · Onboarding

> Task spec for worker CLI in worktree `work-A3-prd` (branch
> `feat/prd-summaries-A3`). Read this + `AGENT_IDENTITY.md` on resume,
> then start work.

## Goal

Read all 6 Agent PRDs in `docs/PRD_*.md` and extract per-agent capability
specs into `docs/contracts/agent-{name}-spec.md` × 6. These specs are the
ground truth Stage C workers (Channel/Report/Credit/Alert/Compli/Forge
PRD-grade implementation) read on dispatch. They must capture:

- product positioning (1-paragraph)
- key capabilities list (numbered · checkable)
- input shape (file types · query format · trigger sources)
- output shape (what UI shows · what file formats exported)
- backend endpoints needed (path · request · response · SSE events)
- mock_sessions structure (≥3 sample sessions per agent)
- panel architecture (which panels need what data · per workspace-state-protocol.md)
- regression risks (what features to PRESERVE · cross-link to features-inventory)

## Deliverables

6 files under `docs/contracts/`:

1. `agent-channel-spec.md` — Agent1 Scout (look-alike 获客)
   - PRD: `docs/PRD_全渠道流量匹配智能体_v2.0.md`
   - Capabilities: KB upload (3 types) · IdealProfile extraction · 外网池扫 50+ · Top10 + 匹配明细 + 产品推荐 + 话术 · Word 导出
   - Workspace: archive/channel · panels (Query/Funnel/Radar/Candidates/SignalTimeline/Conversation)
   - Backend: `/api/channel/upload_kb` · `/api/channel/profile` · `/api/channel/run` (SSE) · `/api/channel/export_docx`

2. `agent-report-spec.md` — Agent6 Report (材料 → 报告 v16)
   - PRD: `docs/PRD_报告生成助手.md`
   - Capabilities: 文件上传 multi-type · classifier → generator → QC gate (v16 主管线) · 字段抽取 · Word 导出
   - Workspace: archive/report · panels (Materials/Fields/Draft/Preview/Conversation)
   - Backend: `/api/report/upload` · `/api/report/fill` (SSE) · `/api/report/refine` · `/api/report/downloads/*`

3. `agent-credit-spec.md` — Agent3 Credit (授信决策)
   - PRD: `docs/PRD_授信决策辅助智能体_v2.0.md`
   - Capabilities: 4-dim 评分 (对公/普惠/对私) · 红线判定 · 决策建议书 Word 导出
   - Workspace: archive/credit · panels (ProfileSummary/RadarScore/RedLines/StageTabs/DecisionLetter)
   - Backend: `/api/credit/decision` · `/api/credit/presets` · `/api/credit/export_docx`

4. `agent-alert-spec.md` — Agent4 Alert (贷后预警)
   - PRD: (look in docs/ for alert / 预警 / vigilance PRD · or extract from CLAUDE.md § 4)
   - Capabilities: 在贷客户池扫描 · 红/黄/绿榜单 · 信号事件 · drill detail · 处置建议
   - Workspace: archive/alert · panels (HitList/SignalMap/RuleStatus/DrillDetail/Conversation)
   - Backend: `/api/alert/scan` (SSE) · `/api/alert/hitlist` · `/api/alert/drill/{id}`

5. `agent-compli-spec.md` — Agent5 Compliance (合规巡检)
   - PRD: `docs/PRD_合规巡检智能体_v2.0.md`
   - Capabilities: 政策事件驱动 · 业务矩阵扫 · 冲突点明细 · 修订意见生成
   - Workspace: archive/compliance · panels (PolicyDiff/MatrixScan/ConflictPoints/RevisionDraft)
   - Backend: `/api/compliance/policy_scan` (SSE) · `/api/compliance/matrix_check`

6. `agent-forge-spec.md` — Agent2 Forge/Riskctrl (策略风控)
   - PRD: (extract from CLAUDE.md § 4 · agent_riskctrl/api.py current endpoints)
   - Capabilities: DSL 生成 · KS/AUC 回测 · 通过率 / 坏账率分析 · sample 分布 · 上线管理
   - Workspace: archive/riskctrl · panels (DSLEditor/MetricsRow/Backtest/Conversation)
   - Backend: `/api/riskctrl/dsl_gen` · `/api/riskctrl/backtest` · `/api/riskctrl/run`

## Acceptance

- 6 doc files created under `docs/contracts/`
- Each doc ≥ 100 lines · structured sections (positioning / capabilities / I/O / endpoints / mock / panels / risks)
- Capabilities list checkable (numbered) — Stage C worker can tick off as implemented
- Backend endpoint list specifies path · method · request body · response shape · SSE events (where applicable)
- Mock structure shows 3+ sample data points per panel (so Stage C worker has examples)
- Commit on `feat/prd-summaries-A3` with trailer:
  ```
  Signal: WORKER-A3-PRD-SUMMARIES-DONE
  ```

## Boundary

- Write ONLY: 6 new files under `docs/contracts/`
- Read-only: existing PRDs in `docs/PRD_*.md` · existing code in `agent_*/` · existing CLAUDE.md
- DO NOT modify: any code · existing PRDs · existing contracts

## Dependencies

- Master plan: `docs/contracts/master-execution-plan-2026-04-27.md` § Stage A.5
- 10 PRD files in `docs/PRD_*.md` (some agents have v1+v2 — read v2 as canonical)
- For agents without standalone PRD (Alert / Forge), extract spec from CLAUDE.md § 4 + agent_*/api.py
- Worker A2's `workspace-state-protocol.md` (read after A2 completes if dependency on architecture)

## Trailer protocol

```
Signal: WORKER-A3-PRD-SUMMARIES-DONE
```

## On completion

1. `git add docs/contracts/agent-*.md && git commit -m "..."` with trailer
2. `git push origin feat/prd-summaries-A3`
3. Main CLI reviews 6 specs · checks completeness / mock examples
4. Main CLI cherry-pick / merge to `chore/l0-infra`

## Estimated effort

4-5 hr — read 6 PRDs (some long) · structured extract per spec.
