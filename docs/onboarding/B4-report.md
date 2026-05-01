# Worker-B4-report Onboarding · Agent6 material gap + cross-section coherence (Phase B Sprint 1)

> Phase B Stream 2 · 后端 deep work · BE3 P0 必做 · 解决 RM + 审贷员痛点 1.2.3 (报告章节不一致 + 缺材料闭环)
>
> Dispatch signal: `PHASE-B-SPRINT-1-DISPATCHED`

## 0. worktree

- `D:\claude code\work-B4-report` · branch `feat/phase-b4-report` (新建 · 已 checkout)
- resume: cd worktree · `git status` (clean) · 直接干 §1

## 1. 任务 (per `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` BE3)

**真痛**:
- RM 痛: 现 v16 真路径缺材料/分类产物就 mock · RM 不知道哪些数据缺口影响结论 (`v16_runner.py:485`)
- 审贷员痛 1.2.3: 报告各章节数据不一致 (e.g. 营收章说 5 千万 · 经营章说 1 亿) · 现 v16 单 section 独立 + financial_consistency 只比对 anchor 不做跨章节语义 (`quality_blocker.py:4-8, 304-314`)

| # | 交付 | Evidence |
|---|---|---|
| 1 | Agent6 **material gap graph**: 每章节标 "缺哪份材料 → 影响哪章/哪项评分" · 不只 pending_questions list | 现状: pending_questions 只随 v16 summary 输出 (`v16_runner.py:342-350, 400-413`) · 缺 RM 视角 "缺这份材料会让授信评分降 X" |
| 2 | Agent6 **section impact**: material gap → section impact map (材料缺口对 ReportJSON 哪些字段有影响 · 影响幅度) | |
| 3 | Agent6 **cross-section coherence sanity check** (跨章节语义 + 历史一致性 · 不只 anchor) | 现状: `quality_blocker.py` financial_consistency 只比 anchor · 不跨章节 |
| 4 | Agent6 → Agent3 handoff (per `agent-handoff-schemas.md` §6.2 反向链 `Agent3.report_gap → Agent6.section_supplement`) — 评分发现报告缺章节回报告 |
| 5 | `data/mock/workspace/report/scenarios/*.json` 加 material gap fixture · 演示 demo 用 |
| 6 | `tests/agent_report/test_material_gap.py` 单元测试 |

## 2. 必读

- `RESET_MASTER_PLAN.md`
- `docs/reset/phase-b-charter.md` v2 (Stream 2 worker-B4-report)
- `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` BE3 + BE7 (decision ledger 配套)
- `docs/research/two-way-debate-backend-r1-codex-2026-05-01.md` §3.3 (Codex R1 verdict + file:line)
- `docs/contracts/agent-handoff-schemas.md` v1.1 (§6.2 反向链 Agent3→Agent6)
- `agent_report/api.py` (1074 行 · 当前 v16 + demo)
- `agent_report/v16_runner.py` (482 行 · 当前 classifier→generator→QC)
- `agent_report/quality_blocker.py` (financial_consistency anchor)

## 3. 红线 (per Codex R2)

- ❌ 不重写 v16 pipeline (classifier→generator→QC 是稳定核心 · material gap 是上层 wrapper)
- ❌ 不引入 ML (per 双方共识 · 真痛是 evidence + cross-section · 不是 ML)
- ❌ 不跨 worktree
- ❌ commit 不带 `Signal:` trailer (per Q-043 codex protocol v2)
- ❌ 不破现有 v16 mock 路径 (Stage 5a smoke 已验)

## 4. ACK

DONE commit `Signal: WORKER-B4-REPORT-MATERIAL-GAP-DONE` · trailer:
```
BE-DELIVERED: BE3 (Agent6 material gap + cross-section coherence)
SCHEMA-DOC: docs/contracts/agent-report-material-gap.md
HANDOFF-LINK: agent-handoff-schemas.md §6.2 (Agent3→Agent6 反向链)
CROSS-SECTION-COHERENCE: yes (跨章节语义 sanity check)
FIXTURE-UPDATED: data/mock/workspace/report/scenarios/*.json
TESTS-PASS: tests/agent_report/test_material_gap.py 全 pass
PRESERVES: F-XXX (v16 pipeline 不破)
HARDLINE-PHASE-B-#4: 部分 met (BE3 部分)
```

## 5. Codex (插入点 1+2 per Q-043 protocol v2)

Pre-dispatch draft 落 `docs/audit/codex-drafts/B4-report.md`

Post-DONE Codex review (主 CLI fire · high reasoning · 验 material gap 完整 + 与 BE2 decision graph + BE7 ledger 兼容)

---

**Author**: 主 CLI · 2026-05-01 · Worker-B4-report (Phase B Sprint 1 · 4 of 4)
