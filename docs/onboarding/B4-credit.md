# Worker-B4-credit Onboarding · Agent3 decision graph + peer_gap (Phase B Sprint 1)

> Phase B Stream 2 · 后端 deep work · BE2 P0 必做 · 解决审贷员痛点 1.2.1+4 (AI 评分黑盒 + 缺同业对标)
>
> Dispatch signal: `PHASE-B-SPRINT-1-DISPATCHED`

## 0. worktree

- `D:\claude code\work-B4-credit` · branch `feat/phase-b4-credit` (新建 · 已 checkout)
- resume: cd worktree · `git status` (clean) · 直接干 §1

## 1. 任务 (per `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` BE2)

**真痛**: 审贷员痛 1.2.1 — Agent3 LLM 评分"看不到理由" · 不接受黑盒推荐 · 要看支撑数据 + 同业对标 · 现 Agent3 evidence 是 fixture (Codex Bug 2)。

| # | 交付 | Evidence |
|---|---|---|
| 1 | Agent3 **decision graph**: 每结论挂 feature snapshot + rule hit + 阈值 + 来源段落 + 版本 | 现状: `agent_credit/decision_engine.py:98-125` 前 4 步确定性 + 最后 `agent_credit/advisor_formatter.py:205-244` LLM 包装 |
| 2 | Agent3 **peer_gap (同业对标)** 纳入可复核链 | 现状: `agent_credit/scoring_model_corporate.py:215-240` 同业 gap 已有字段 · 但未纳入可复核链 · 加 `peer_gap` 段到 decision graph |
| 3 | **Decision graph schema** 落 `docs/contracts/agent-credit-decision-graph.md` (与 BE7 跨 Agent decision ledger 配套) |
| 4 | `data/mock/workspace/credit/scenarios/*.json` 加 decision graph fixture · 演示 demo 用 |
| 5 | `tests/agent_credit/test_decision_graph.py` 单元测试 · 验 decision graph schema 完整性 |

## 2. 必读

- `RESET_MASTER_PLAN.md`
- `docs/reset/phase-b-charter.md` v2 (Stream 2 worker-B4-credit)
- `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` BE2 + BE7 (decision ledger 配套)
- `docs/research/two-way-debate-backend-r1-codex-2026-05-01.md` §3.2 + §4 (Codex R1 evidence-based audit verdict)
- `docs/contracts/agent-handoff-schemas.md` v1.1 (与 6.2 Agent3.report_gap → Agent6 配套)
- `agent_credit/api.py` (811 行 · 当前 SSE + decision)
- `agent_credit/decision_engine.py` (114 行 · 当前 4 步确定性)
- `agent_credit/advisor_formatter.py` (LLM 包装段)
- `agent_credit/scoring_model_corporate.py` (peer_gap 字段)
- `agent_credit/scoring_model_retail.py` (零售 FICO)

## 3. 红线 (per Codex R2)

- ❌ **不引入 ML (logistic/GBDT)** — Codex 已 verdict ML 是手段不是目的 · 真痛是 evidence 链 · 不是 ML
- ❌ 不动现有 4 步确定性评分 (decision_engine.py 1-114) · decision graph 是上层 wrapper · 不是替换
- ❌ 不跨 worktree
- ❌ commit 不带 `Signal:` trailer (per Q-043 codex protocol v2)
- ❌ 不破现有 mock 路径 (per Stage 5a smoke 验过 6 SSE 真流 · 不能 regress)

## 4. ACK

DONE commit `Signal: WORKER-B4-CREDIT-DECISION-GRAPH-DONE` · trailer:
```
BE-DELIVERED: BE2 (Agent3 decision graph + peer_gap)
SCHEMA-DOC: docs/contracts/agent-credit-decision-graph.md
DECISION-GRAPH-FIELDS: feature_snapshot/rule_hit/threshold/source_segment/version/peer_gap
FIXTURE-UPDATED: data/mock/workspace/credit/scenarios/*.json
TESTS-PASS: tests/agent_credit/test_decision_graph.py 全 pass
PRESERVES: F-XXX (现有 SSE 不破)
HARDLINE-PHASE-B-#4: 部分 met (BE2 部分 · 13 BE 全完后完整 met)
```

## 5. Codex (插入点 1+2 per Q-043 protocol v2)

Pre-dispatch draft 落 `docs/audit/codex-drafts/B4-credit.md` (worker 启动后立即 fire · medium reasoning · ~10 min)

Post-DONE Codex review (主 CLI fire · high reasoning · 验 decision graph schema 完整 + 与 BE7 ledger 兼容)

---

**Author**: 主 CLI · 2026-05-01 · Worker-B4-credit (Phase B Sprint 1 · 3 of 4)
