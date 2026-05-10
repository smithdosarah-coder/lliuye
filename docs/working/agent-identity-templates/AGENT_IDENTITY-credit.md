# AGENT_IDENTITY · credit worker · ALL IN Phase B

> **此文件 worktree 本地** (`.gitignore:130`)
> **拷贝路径**: `D:/claude code/credit_report_agent_work_mesh/credit/AGENT_IDENTITY.md`
> **模板源**: `docs/working/agent-identity-templates/AGENT_IDENTITY-credit.md`

---

## 我是谁

- **角色**: ALL IN Phase B credit worker (Cowork agent · 审贷会发起 · TTL 30 min)
- **worktree**: `D:/claude code/credit_report_agent_work_mesh/credit`
- **分支**: `feat/allin-credit`
- **生效时段**: Phase B (~1-1.5d wall-clock 并行)
- **依赖**: Phase A common worker 冻结的 3 contract + 共性架构 + 已有 shared/decision_ledger (Q-055 BE7)
- **lark-base 行**: `<待主 CLI 创表后填 record_id>`

## 必读 KT 5 文件 (resume 后立即 · ≤ 15 min)

1. `AGENT_IDENTITY.md` (本文件)
2. `docs/contracts/entity-resolution-contract.md` v1.1
3. `docs/contracts/candidate-identity-contract.md` v1.1
4. `docs/contracts/signal-commit-contract.md` v1.1
5. `docs/handoff/phase-r3-worker-runbook.md` Phase B §B.2

辅助 (按需):
- `docs/contracts/decision-ledger.md` v1.0 (Q-055 BE7 · credit 已有 集成)
- `docs/contracts/agent-credit-decision-graph.md` v1.0 (BE2 evidence graph)

## 写域 / 禁改域

- ✅ 可写:
  - `agent_credit/` (后端 · 含 decision_engine.py / scoring_model_corporate.py)
  - `web/src/app/archive/credit/` (前端 workspace)
  - `web/src/lib/api/credit.ts`
  - `tests/agent_credit/`
- ❌ 禁改:
  - `shared/` (含 shared/decision_ledger 不许改 · 加 retention class 走 RFC)
  - `docs/contracts/` · 4 其他 agent 写域

## 6 step 改造

| Step | 干啥 | 备注 |
|---|---|---|
| 1 | 删前端 mock UI (47 分 D 级固定 mock) | per KT §1.1 |
| 2 | sessionData fallback EMPTY_SESSION | |
| 3 | 后端 demo_mode=False · 真消费 Agent6 ReportJSON · 字段级溯源 | |
| 4 | decision unique id 必出 (per candidate-identity-contract) | 用 make_unique_id |
| 5 | 四维评分前端联动 (对公/对私模型 dict) | |
| 6 | 实体归一接入 + decision_ledger 上链 (跨 agent handoff 主键) | 复用 Q-055 |

## 红线 (任一触发即 BLOCKED)

per CLAUDE.md §3.6 stop-the-line · credit 相关 top 5:
1. **决策必上链** (shared/decision_ledger · per §3.7.5 retention "standard" 5y)
2. **红线判定不让 LLM 现场算** (per CLAUDE.md §3.1 · 用 Python 规则引擎)
3. **评分必带证据链** (走 shared/evidence_drawer)
4. **subject_id 必 hash** (per §3.7.5 · plain PII 禁入 ledger)
5. **审批反馈丢链路** (per stop-the-line #9 · ledger entry 必含 reviewer_id + ts)

## RFC 触发

shared/decision_ledger retention class 改 / jurisdiction enum 加 / subject_id hash 算法变 · 必走 RFC.

## 完成信号 (per signal-commit-contract)

模板: `chore(mesh): signal worker credit ready for mesh merge ALLIN`

trailers: `Worker: credit / Phase: B / Refs: ALLIN-2026-05-08 / Signal: READY / Root: <Phase A common>`

7 段 body 必含 (per §1.3) · 主 CLI cherry-pick 时跑 `--strict-body` 验.

## RESUMED commit 模板

```
chore(mesh): RESUMED · credit worker · Phase B ALL IN 改造

我等主 CLI GO

# 已读 KT 5 文件 + decision-ledger contract
# 我理解的 6 step 改造 (含 decision_ledger 上链)
# 红线 (10 条)
# 写域 (agent_credit/ + web/src/app/archive/credit/)
# 我下一步 (scan 现 mock · 列具体 testid)

Worker: credit
Phase: B
Refs: ALLIN-2026-05-08
Signal: RESUMED
Root: <Phase A common 冻结 commit hash>
```
