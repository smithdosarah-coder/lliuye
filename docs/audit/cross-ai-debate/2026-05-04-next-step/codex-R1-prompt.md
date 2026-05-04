# Codex Round 1 · "下一步 1-3 周 plan" · Independent v1 (anti-bias rule 1)

You are an independent staff engineer. PM (orchestrator 刘野 · 众安信科 AI 中台产品负责人) wants 主 CLI (Claude Opus 4.7) and you (Codex gpt-5.5-codex) to EACH propose "下一步 1-3 周 plan" for the banking AI 6-agent product (Phase B Sprint 2 starting).

Both write Round 1 v1 INDEPENDENTLY. You do NOT see main CLI's v1 yet — main CLI is writing v1 in parallel right now. Round 2 you will see main CLI's v1 + your own v1 and write v2 (改 / 坚持 / 对方弱点 / 吸收对方 / final).

## Anti-bias rules (verbatim · 违反 = invalidate)

- Independent v1 · NOT see main CLI v1
- ≤ 3500 词
- Concrete deliverable + 时间 + risk + DoD
- file:line / commit sha 必备 · 无抽象散文
- Dissent appendix 必含 (≤ 300 词 · 你预期 main CLI 会推荐什么 · 你不同意哪些 · 不强行收敛)
- 不站队你之前三方辩论 v2.1 立场 · 本次是独立看现状

## Required reading (按顺序读完再答)

1. `RESET_MASTER_PLAN.md` (umbrella 索引 + 三步框架 + PM 拍板 5)
2. `docs/reset/north-star.md` (6 Agent 闭环 + 走歪诊断)
3. `docs/reset/phase-a-charter.md` (Phase A 8 硬线 + 7 worker)
4. `docs/reset/phase-b-charter.md` (Phase B v2 三方辩论 final · 9 worker · BE1-BE13)
5. `docs/reset/state-snapshot.md` 末 200 行 (Day 1+2 + Q-046 + Q-047)
6. `docs/handoff/decisions-log.md` 末 250 行 (Q-043 codex protocol v2 + Q-044 三方辩论 + Q-045 后端 v2.1 + Q-046 Sprint 2 真主线 + Q-047 视觉冻结)
7. `docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_2026-05-02.md` (v3 含 §0 Q-047)
8. `CLAUDE.md` (root · 必读 §3.7 active runtime rules + §13 ECS 部署 + §14 必读协议 + §15 SSOT 优先级)
9. spot-check Sprint 1 已 ship 代码 (≥ 3): `agent_credit/decision_graph.py` / `shared/decision_ledger/store.py` / `agent_credit/decision_engine.py` / `agent_report/api.py`
10. spot-check Sprint 2 三 onboarding (全 3): `docs/onboarding/B4-alert.md` + `docs/onboarding/B4-compliance.md` + `docs/onboarding/B2-biz.md`
11. spot-check Phase A 漏的可能 partial 项: `docs/contracts/agent-handoff-schemas.md` (是否 v1.1 真存在?) + `docs/prd/master-*.md` (worker-A7 PRD master 是否落地?)

## 现状摘要 (新 main CLI 2026-05-04 写 · 仅参考 · 不限定你思考)

Sprint 1 已 ship (Q-046 接受既成事实):
- B1-flywheel BE10 ship + Sprint 2 enrich 误派 ship (6 commit · charter 没列 · 但 PM 接受)
- B4-credit BE2 ship + Sprint 2 BE7 误派 ship (BE7 是 Sprint 3 worker-B7 · 提前 · Sprint 3 减半)
- B4-report BE3 ship
- B3 视觉 Q-047 全撤 (commit 413a9ab · production = Phase A exit 视觉 · PM verbatim "原来的方案")

Sprint 2 真主线 (charter v2 line 63-100 · 待 PM 双击 launch.bat 启):
- B4-alert BE5+BE9 (3 周) · onboarding ready
- B4-compliance BE4 (2-2.5 周) · onboarding ready
- B2 BE11 商业化 doc only (1 周) · onboarding ready

Sprint 3 真主线 (charter line 78-89 · BE7 提前 · worker-B7 减半):
- B4-channel BE1+BE12 (4-4.5 周)
- B4-riskctrl BE6+BE8 (4-4.5 周)
- B7 BE13 final (减半 · 1-1.5 周 → 0.75-1 周)

Phase A 8 硬线 (commit fb4cead 已 declared exit · 但 Q-047 visual reset 后 #5 Letterpress 状态不明 · #6 handoff schema + #7 PRD master 也不确定 partial 或 done)

Codex 状态: 你 (Codex) 用尽 until 2026-05-08 已恢复 (本 R1 prompt 就是证据 · 2026-05-04 medium reasoning ping PONG OK)。Q-043 protocol v2: medium reasoning default · sequential 不并发 · 90 min CPU=0 fallback manual。

视觉路线: Q-047 PM ratify 视觉冻结 · 不再派视觉 worker · 任何视觉变更 PM 显式 unfreeze 才启。Phase B 本期 token 全花后端。

## 你要回答的开放问题

**主 CLI 在接下来 1-3 周应该做什么 · 怎么排 · 给 PM 一个可执行 plan。**

特别考虑 (但不局限):
- Sprint 2 三 worker 启动 prep (onboarding update? audit? cron?)
- Sprint 1 已 ship 4 worker 后续审查 (codex 已恢复 · 是否 fire post-DONE peer review for B1/B4-credit/B4-report? B3 视觉撤了不需 review)
- Phase A 8 硬线 partial 项 (e.g. handoff schema #6 / PRD master #7 / Letterpress 真清 #5 Q-047 后状态) 何时补 (Sprint 2 启前 / Sprint 3 减半时间 / Sprint 4 整合)
- 视觉冻结后 token 全花后端 · 排期是否需要重 sequence?
- Demo 4 维评价 (Sprint 5) 反推 · 1-3 周做的事是否在 critical path?
- 数据飞轮 + decision ledger 已落地 · 是否需要 Sprint 2 增 monitoring/observability gate?
- Q-046 5 跑偏 root cause 硬规如何在 1-3 周持续被 enforce?

## Output schema (verbatim · 主 CLI 直接 grep 结构)

```markdown
# Codex Round 1 · v1 · "下一步 1-3 周 plan" · Independent

## 1. Scope 界定 (≤200 词)
<你怎么界定"下一步 1-3 周" · 含哪些 / 不含哪些>

## 2. TL;DR (≤150 词)
<1 段 · 3-5 件最重要的事 + 总判断>

## 3. Concrete deliverable (table)
| # | item | owner | 时间 | DoD (file:line / signal) |
|---|---|---|---|---|
...

## 4. 风险 (≤5 个 · 缓解措施)
| # | 风险 | 触发条件 | 缓解 | 缓解 owner |
|---|---|---|---|---|
...

## 5. DoD (整体 3 周后 PM 看到什么) (≤200 词)

## 6. 不做的事 (反 Q-046 5 跑偏) (≤200 词)

## 7. 替代方案 evaluated rejected (≥3 个 · 理由) (≤300 词)

## 8. Critical path 反推 (Sprint 5 demo 4 维 → 现在 1-3 周) (≤300 词)
<这 1-3 周做的事是否在 demo critical path 上 · 还是平行支线>

## 9. Dissent appendix (≤300 词)
<你预期 main CLI 会推什么 · 你不同意哪些 · 不强行收敛 · 给 R2 用>
```

≤ 3500 words total. Begin.
