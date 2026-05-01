# Baseline Gate · CI Release Checklist (V4 plan F6)

> **F6 (V4 plan · Phase B-1)** · Codex C14 加补 · worker-B1 (BE10 后端) +
> worker-B3 (前端 + CI 配套) 双侧落地。
>
> 来源: `docs/research/FINAL-FRONTEND-OPTIMIZATION-PLAN-V4-2026-05-01.md` F6
> Phase B charter: `docs/reset/phase-b-charter.md` §1.1 验收硬线 #1

---

## 1. 验收硬线 (V4 plan F6 DoD)

| # | 项 | 状态 | 责任 |
|---|---|---|---|
| 1 | 6 Agent baseline 跑通 (channel/credit/alert/compliance/report/riskctrl) | ✅ worker-B1 commit 1835c65 (Phase B start baseline) | worker-B1 |
| 2 | `evaluation.runner --gate` flag · blocker_threshold 触发退出码 3 | ✅ worker-B1 commit aa289ea + V2 273ae83 (gate semantics) | worker-B1 |
| 3 | evidence_rate / hallucination_rate / field_completeness 三 metric 在 6 agent yaml 配齐 | 🟡 部分 · alert/signal_diversity / compliance/{policy_coverage, conflict_recall} / report/task_completion_rate 已知 blocker (per 238ef6b commit message) | worker-B4-* (后续 sprint) |
| 4 | CI workflow 接 release checklist · PR/push 阻断 | 🟡 placeholder ship · `if: vars.BASELINE_GATE_ENABLED == 'true'` 默认关 · 等 worker-B1 merge + PM enable | worker-B3 (本 doc) |
| 5 | CI fail 时 PR 显示 `[BLOCKER]` 报告 + runbook 链接 | ✅ workflow `Show gate report` step (`if: failure()`) | worker-B3 (本 doc) |

---

## 2. CI workflow 文件

`.github/workflows/baseline-gate.yml` (worker-B3 · 本 commit ship · placeholder)

- **触发**: push 到 main / chore/** / feat/** / fix/** + PR 到 main
- **命令**: `python -m evaluation.runner --all --gate --out /tmp/baseline-gate.json`
- **退出码语义**:
  - `0` = PASS · 全 metric ≥ baseline_target
  - `1` = PARTIAL/FAIL · 至少一个没达 target (warning · 不阻断)
  - `2` = adapter 未实现 · 跳过 (不算 fail)
  - `3` = blocker_threshold 触发 · CI 阻断 (BE10 真红线)
- **Feature gate**: `if: vars.BASELINE_GATE_ENABLED == 'true'`
  - 默认 disabled · workflow 文件存在但 job skip · 不影响 PR
  - 等 worker-B1 merge + PM 拍板 enable 时设 `BASELINE_GATE_ENABLED=true` GitHub repo variable

---

## 3. PM Enable 步骤 (V4 plan F6 真激活 · 主 CLI 操作)

按顺序:

1. **worker-B1 merge 进 main**:
   - branch: `feat/phase-b1-flywheel` · DONE Signal: `WORKER-B1-FLYWHEEL-V2-DONE`
   - merge 后 `python -m evaluation.runner --all --gate` 在 main 上可用
2. **跑 1 次本地验**:
   ```bash
   python -m evaluation.runner --all --gate --out /tmp/baseline-gate.json
   echo "exit code: $?"
   ```
   - 期望: 退出码 0 (全 PASS) 或 1 (部分 metric 落后但无 blocker)
   - 如果 退出码 3 → 有 blocker · 修后才 enable
3. **GitHub repo settings → Variables → Repository variables**:
   - 加 `BASELINE_GATE_ENABLED=true`
4. **下次 PR 自动跑 baseline gate**:
   - PR 失败 (退出码 3) · 阻断 merge
   - PR 成功 · merge 进 main · 走部署流程 (CLAUDE.md §13)

---

## 4. 当前 known blockers (Phase B 启动时 · per worker-B1 commit 238ef6b)

V4 plan F6 验收 #3 待 worker-B4-* 各自修:

| Agent | 待修 metric | 责任 worker | Sprint |
|---|---|---|---|
| Agent4 alert | `signal_diversity` | worker-B4-alert | Sprint 2 (BE5) |
| Agent5 compliance | `policy_coverage` + `conflict_recall` | worker-B4-compliance | Sprint 2 (BE4) |
| Agent6 report | `task_completion_rate` | worker-B4-report | Sprint 1 (BE3) |

修完后 baseline 重跑 · `BASELINE_GATE_ENABLED=true` 才真红线。

---

## 5. 与既有 CI (lint-contracts.yml) 的关系

- `lint-contracts.yml` (Phase A · Q-043 配套) — 静态代码 SSOT lint (Agent Naming + Letterpress purge + ratify)
- `baseline-gate.yml` (本 PR · F6) — 动态评估 baseline gate (6 agent metric 跑通)
- 两个 workflow 独立 · 一个 fail 不影响另一个执行

---

## 6. Sign-off

- worker-B3 ship: `.github/workflows/baseline-gate.yml` placeholder + 本 doc (2026-05-01)
- worker-B1 ship: `evaluation.runner --gate` + 6 agent baseline + few-shot PoC (DONE 2026-05-01)
- PM enable pending: worker-B1 merge + `BASELINE_GATE_ENABLED=true` (主 CLI 协调)

> 任何 worker 改 `evaluation/` 后要重跑 baseline · 验 gate 不破。
