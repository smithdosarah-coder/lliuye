# Agent3 Phase 2 Batch 1 · Review

**Reviewer**: 主 CLI (orchestrator)
**Date**: 2026-04-19
**Target**: `feat/agent3-productize` @ d67576f + `chore/agent3-lint-cleanup` @ 50cf2a7
**Onboarding**: `docs/onboarding/agent3-phase-2.md`
**Worker signal**: `READY-FOR-PHASE-2-REVIEW` (d67576f)

---

## Verdict: **APPROVED**

允许 `chore/agent3-lint-cleanup` 直接 fast-forward 进 `chore/l0-infra`；`feat/agent3-productize` 的 Task A 保留在 feat 分支等后续 Phase 合流。

---

## Task A — evaluation adapter（d221115）

**亲跑冒烟**：`py -m evaluation.runner --agent credit`

```
=== credit · PARTIAL · 0.1s ===
[Common]  field_completeness 1.0000 / evidence_rate 1.0000 /
          hallucination_rate 0.0000 / tool_success_rate 1.0000 /
          task_completion_rate 1.0000
[Domain]  ratio_consistency 1.0000 / red_line_trigger_accuracy 1.0000 /
          score_monotonicity 0.0000 / reason_code_top5_coverage N/A (Phase C stub)
```

- 8/9 PASS + 1 Phase C stub（符合 onboarding "reason_code 待标注库"预设）
- 红线闸门全绿：hallucination < 0.02 / evidence ≥ 0.90 / field_completeness ≥ 0.90
- 三确定性指标（ratio_consistency / red_line_accuracy / score_monotonicity）按 onboarding §Task A 要求落地
- `evaluation/agent3_credit.yaml` 新增 `metrics.common` / `metrics.domain` 块对齐 `agent6_report.yaml` 双轨结构

**回归**：`py -m pytest agent_credit/ -q` → 16 passed

**红区合规**：无 `shared/` / `docs/contracts/` 改动 ✅

---

## Task B — BLE001 lint chore（50cf2a7, on chore/agent3-lint-cleanup）

**亲跑**（checkout chore/agent3-lint-cleanup 后）：
- `py -m ruff check agent_credit/advisor_formatter.py agent_credit/api.py --select BLE001` → **All checks passed!**
- `py -m ruff check agent_credit/advisor_formatter.py agent_credit/api.py` → **All checks passed!**

5 sites 全部收窄到具体异常元组：
- advisor_formatter.py L238/L254/L349 → `(RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError)`
- api.py L102 → `ImportError`；L122 → finite tuple（保留 SSE crash-guard）

**边界守住**：纯 except 收窄，无业务逻辑改动（12 insertions / 13 deletions，仅 2 个文件）✅
**分支基线**：从 `chore/l0-infra` 起的独立 chore 分支，不污染 feat 分支 ✅

---

## Follow-up

- `chore/agent3-lint-cleanup` 可在主 CLI 侧 fast-forward merge 进 `chore/l0-infra`（作为独立基建改动）
- Task A 的 reason_code_top5_coverage Phase C 需标注库上线后再解锁，不阻塞本次 verdict
- Agent3 worker 收到 `Signal: PHASE-2-APPROVED` 后可进入 maintenance 或等 Batch 2
