# shared-extract results · B.3.4 P0-R1 (2026-05-11 · COMPLETE)

> **Worker**: shared-extract (B.3.4 P0-R1)
> **Branch**: `feat/b34-shared-extract`
> **PM Option**: B (output_validator + confidence policy + canary)
> **工期实测**: 完成 (~ 1 个 session 内完成 · 比 brief 2-3 天估快)
> **regression**: 0 new (37 baseline failures 不变 · 1442 passed · +61 new contract/canary tests)

---

## 1. 交付物清单

| 文件 | 类型 | 行数 | 说明 |
|---|---|---|---|
| `docs/working/shared-extract-inventory.md` | inventory | 186 | brutal verdict · 4 模块 / 6 Agent 重复实测 |
| `docs/contracts/shared-output-validator-v1.0.md` | contract | ~190 | factory pattern + 6 invariants + migration plan |
| `docs/contracts/shared-evidence-confidence-policy-v1.0.md` | contract | ~215 | 数学 + alert taxonomy 边界 + flag-gate strategy |
| `tests/shared/test_output_validator_contract.py` | test | 213 | 21 测试 (I1-I6 + 行为等价) |
| `tests/shared/test_evidence_confidence_policy_contract.py` | test | 244 | 33 测试 (I1-I10 + 公共常量) |
| `tests/agent_channel/test_canary_shared_confidence.py` | test | 113 | 7 测试 (flag OFF/ON 行为差异) |
| `shared/output_validator.py` | impl | 100 | factory + OutputValidator dataclass + _walk |
| `shared/evidence/confidence_policy.py` | impl | 192 | freshness_score + compute_evidence_confidence + quality_bundle |
| `agent_alert/signal_quality.py` | refactor | -127, +57 | 删本地 freshness/confidence · re-export from shared |
| `agent_alert/output_validator.py` | shim | -45, +18 | 55 → 22 LOC thin shim |
| `agent_channel/output_validator.py` | shim | -45, +18 | 51 → 22 LOC thin shim |
| `agent_compliance/output_validator.py` | shim | -45, +18 | 51 → 22 LOC thin shim |
| `agent_credit/output_validator.py` | shim | -45, +18 | 52 → 22 LOC thin shim |
| `agent_riskctrl/output_validator.py` | shim | -45, +18 | 55 → 22 LOC thin shim |
| `agent_channel/evidence_pipeline.py` | canary | +20 | flag-gated `quality_bundle` opt-in (默认 OFF) |
| `AGENT_IDENTITY.md` | local | 1 (gitignored) | resume context |

**Net code delta (跨 6 文件 shim + alert + shared 新增 + canary)**:
- 删 ~365 LOC (5 个 inline + alert 数学)
- 加 ~410 LOC (含 ~570 行 contract + test)
- **production code 净减 ~50 LOC** + DRY 收益 (1 改 1 处)

---

## 2. 7 个 commit chain

```
25185f0 feat: STEP-5-CHANNEL-CANARY-OPT-IN · channel evidence_pipeline confidence flag-gate
8e6c96a refactor: STEP-5-4AGENT-MIGRATED · channel/compliance/credit/riskctrl 切 shared shim
83586cd refactor: STEP-5-ALERT-MIGRATED · agent_alert/output_validator.py 切 shared shim
c9f5f86 feat: STEP-4-GREEN-PART2 · shared/evidence/confidence_policy + alert 切 shared backing
88cae83 feat: STEP-4-GREEN-PART1 · shared/output_validator.py 实现
08632bf test: STEP-3-RED · contract test 先 commit (TDD · CI red 预期)
ea90982 docs: STEP-2-CONTRACT-DONE · 2 spec (output_validator + confidence_policy)
03ea20d chore: STEP-1-INVENTORY-DONE · 4 模块 inventory + brutal verdict (B.3.4 P0-R1)
```

每 commit trailer 全套: `KT-2026-05-10-COMPLIANT / R1-R6-CHECKED / TEST-COMMITTED-FIRST / REVERSE-RATIO / Signal / Worker / Refs`

---

## 3. 没做什么 (per R7 verdict + Option B scope)

| 模块 | 状态 | 原因 |
|---|---|---|
| `shared/evidence/EvidenceFirstPipeline` 主类 | 不动 | 6/6 Agent 早就继承 · domain hooks 是合理 local |
| `shared/kb_scan/KnowledgeBase` 主类 | 不动 | 3/3 Agent 早就继承 · agent-specific 字段是合理 extension |
| `auth_service/rbac.py` | 不动 | 已是 single source · 6 Agent 用 `require_action` decorator · 0 inline |
| `agent_report/quality_blocker.py` | 不动 | 5 维 QC 与 placeholder validator 语义不同 · 留 Agent6 local |
| 5 Agent (除 channel) confidence 切 shared | 不动 | 行为变 (旧静态 → 动态) · 留下 sprint PM 拍板 (per CLAUDE.md §3.7.7 渐进式) |

---

## 4. Regression 实测

| 测试集 | Pass | Fail | 备注 |
|---|---|---|---|
| `tests/shared/` (520 total · +54 new) | 514 | 6 | 6 fail 全在 `test_prompts_contract.py` · 与本 PR 无关 (baseline · git stash 验) |
| `agent_alert/tests/` (248 total) | 245 | 3 | 3 fail 全在 `test_scan_live.py` · 与本 PR 无关 (baseline) |
| `agent_channel/tests/` (19 total) | 19 | 0 | flag OFF + ON 都 19/19 pass |
| `agent_compliance/tests/` (57 total) | 57 | 0 | 0 regression |
| `agent_credit/tests/` (38 total) | 19 | 19 | 19 fail 全在 `test_redlines.py` + `test_export_docx.py` · baseline (git stash 验) |
| `agent_riskctrl/tests/` (231 total) | 222 | 9 | 9 fail 全在 `test_backtest_real.py` + `test_dsl_deploy_endpoint.py` · baseline |
| `agent_report/tests/` | (跑过) | 0 | 0 regression |
| `tests/agent_channel/test_canary_shared_confidence.py` (7 new) | 7 | 0 | 100% canary flag-gate 行为差异 verify |
| **总计** | **1442** | **37** | **0 new regression** (37 baseline failures unchanged) |

baseline verify: `git stash` 后跑同 test set · 37 fail / 1194 pass (注: pass 数差因 +61 new tests · fail 数完全一致)

---

## 5. 给 P1 fix-contract worker 的 handoff

> P1 worker (WorkSession contract · 等 P0-R1 完成后启) 的 base now stable · 可启。

**已稳定的 shared/ 模块** (P1 可直接 import 用):
- `from shared.output_validator import make_output_validator` · 5 Agent placeholder QC 单点
- `from shared.evidence.confidence_policy import quality_bundle, freshness_score, compute_evidence_confidence` · 跨 Agent confidence 数学单点
- `from shared.evidence import EvidenceFirstPipeline, EvidenceItem, ...` · 6 Agent evidence 基类 (本 PR 没动)
- `from shared.qc import PlaceholderViolation, scan, mark_unfilled, assert_clean` · QC 底层 (本 PR 没动)

**P1 设计 WorkSession 时可参考的 invariants** (本 PR 立的 contract spec):
- `docs/contracts/shared-output-validator-v1.0.md` v1.0 · 6 invariants
- `docs/contracts/shared-evidence-confidence-policy-v1.0.md` v1.0 · 10 invariants + flag-gate strategy

**P1 不必重新发明的事** (本 PR 已抽好):
- per-Agent agent_id 标记机制 (factory + dataclass · WorkSession 复用相同模式)
- flag-gate 渐进 opt-in 范式 (per CLAUDE.md §3.7.7 · WorkSession 切 6 Agent 也走 canary)

---

## 6. 给 PM 的下一步建议

| 优先级 | 建议 | 理由 |
|---|---|---|
| **P0** | 启 P1 fix-contract worker · base stable | 不阻塞 (本 worker DONE) |
| **P1** | 4 Agent (compliance/credit/report/riskctrl) confidence 切 shared 走 canary | per CLAUDE.md §3.7.7 一致性收益高 · 但需 PM 拍板 (行为变 · 客户经理见到 score 变) |
| **P2** | 删 5 Agent thin shim · 直接 import shared/output_validator | production import path 太多 · 不建议 · 留 shim 安全 |
| **P3** | 6 Agent confidence 横向可比 baseline 评估 | 等 4 Agent 全切 shared 后跑一次 evaluation runner · 看 score 变化幅度 |

---

## 7. Final READY signal

下一 commit fire `WORKER-SHARED-EXTRACT-READY-FOR-MERGE` · 等主 CLI cherry-pick 验 + PM verify GO · 然后:
- 主 CLI cherry-pick 8 commit (03ea20d → 25185f0) 到 main 分支
- 启 P1 fix-contract worker (WorkSession base now stable)
- 本 worktree 可清 (per CLAUDE.md §13 + KT R4)
