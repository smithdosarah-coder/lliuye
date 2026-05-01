# 6 Agent 基线 · 2026-05-01 (Phase B 启动 · BE10 blocker_threshold gate first run)

**Commit**: `47e7cad` (feat/phase-b1-flywheel)
**Schema**: A-024 + A-025 双字段 + Phase B BE10 blocker_threshold gate 启用
**Runner**: `py -m evaluation.runner --all --out evaluation/baselines/2026-05-01-phase-b-start.json`
**Gate dry-run**: `py -m evaluation.runner --all --gate` 当前会退出码 3 (4 项 blocker 触发 · 见下)

## 一览表

| Agent | verdict | blockers | 实算 / 总数 | 主要 gap |
|---|---|---|---|---|
| alert | 🟢 PASS | `signal_diversity=0.0000` | 7 / 10 | signal_diversity 持续 0 (与 2026-04-26 同, 待 worker-B4-alert BE5 信号质量改) |
| channel | 🟡 PARTIAL | — | 8 / 10 | `portrait_match_precision=0.50` (target ≥0.70 · 非 blocker · 待 worker-B4-channel BE1) |
| compliance | 🟡 PARTIAL | `policy_coverage=0.50`, `conflict_recall=0.50` | 5 / 10 | 两条 blocker 待 worker-B4-compliance BE4 policy registry 落地后重跑 |
| credit | 🟡 PARTIAL | — | 7 / 10 | `field_completeness=0.926` (>baseline 0.90 · OK) · 4 项 N/A 待 adapter 实现 |
| report | 🟡 PARTIAL | `task_completion_rate=0.0` | 2 / 10 | `task_completion_rate=0` 是 v16 pipeline summary 取值口径问题 · 待 worker-B4-report BE3 排查 |
| riskctrl | 🟡 PARTIAL | — | 7 / 10 | `false_positive_rate=0.067` 通过 · 3 项 N/A 待 backtest deeper coverage |

## Blocker 详单 (CI gate 阻断 4 条)

| Agent | metric | value | blocker_threshold | 方向 | 后续 owner |
|---|---|---|---|---|---|
| alert | signal_diversity | 0.0000 | 0.60 | ≥ | worker-B4-alert BE5 信号质量 |
| compliance | policy_coverage | 0.5000 | 0.90 | ≥ | worker-B4-compliance BE4 policy registry |
| compliance | conflict_recall | 0.5000 | 0.90 | ≥ | worker-B4-compliance BE4 policy registry |
| report | task_completion_rate | 0.0000 | 0.98 | ≥ | worker-B4-report BE3 v16 pipeline summary 取值口径 |

## Phase B BE10 自检

✅ /api/feedback → audit_service.recorder 流水可查 (admin GET /api/audit/llm_calls?endpoint=/api/feedback)
✅ blocker_threshold gate 真接 verdict + CLI 退 3
✅ FEW_SHOT_EXAMPLES 在 agent_credit 闭环 (build_system_prompt + e2e smoke)
✅ 6 agent baseline 跑通 + JSON/MD 双产出
✅ runbook §audit-modify + §blocker-gate + §PoC-scope 更新

## 备注

- 4 项 blocker 是 Phase B 启动时**预期存在**的 known gap · 不阻 worker-B1 DONE · 它们的 owner 写明了
- gate 设计意图: 后续 worker-B4-* 改动后跑 `--gate` 验自身 agent 该项 blocker 是否清掉; 全清后 phase-b-sprint{N}-end tag 才能打
- 反 §3.5 第 5 原则: baseline 跑的是当前 mock 数据 · "稳态内部 context" · 真客户 POC 时另跑

## 历史

- 2026-04-26 real-run: 5 / 6 PARTIAL · 1 PASS · 当时 blocker_threshold 字段定义但未消费
- 2026-04-25 post-agent6-merge: agent6 field=0.935
- 2026-04-24 first-run: framework 首跑
