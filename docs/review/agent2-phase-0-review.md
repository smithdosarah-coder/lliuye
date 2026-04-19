# Agent2 Phase 0 Review

**日期**：2026-04-19
**reviewer**：主 CLI
**onboarding**：docs/onboarding/agent2-phase-0.md
**HEAD**：7a2579e
**Signal**：AGENT2-PHASE-0-READY-FOR-REVIEW

## Verdict
APPROVED

## DoD 对账（逐条）
| 条目 | 状态 | 证据 |
|---|---|---|
| Task A · adapter 可 import | OK | `evaluation/runner/adapters/agent2_riskctrl.py` @ b21737e（283 行，`@register_evaluator("riskctrl")` 在 56 行） |
| Task A · registry 含 riskctrl | OK | registry.py L26 `_LAZY_MODULES["riskctrl"]` 路径正确；`--list` 输出 report/riskctrl |
| Task A · `--agent riskctrl` 输出 PARTIAL | OK | `evaluation/results/2026-04-19/riskctrl_*.json` 三份落盘，verdict=PARTIAL |
| Task B · `2_YYYYMMDD.yaml` 落盘 | OK | `evaluation/results/2_20260419.yaml`（gitignored），13:50 生成 |
| Task B · 确定性指标全部有值 | OK | 5/5 deterministic 指标有值（tc/evidence/halluc/tool/fpr） |
| Task B · yaml baseline 区块更新 | OK | `evaluation/agent2_riskctrl.yaml` L32-46 @ f7e98d1 |
| 红线闸门 halluc ≤ 0.01 | OK | 0.0000 |
| 红线闸门 evidence ≥ 0.98 | OK | 1.0000 |
| 红线闸门 task_completion ≥ 0.95 | OK | 1.0000 |
| Phase C stub 不假装能跑 | OK | ks_improvement / rule_interpretability value=None method=manual（adapter L259-281） |
| 红区零变动 | OK | diff 只动 adapter 新增 + fixture 新增 + yaml baseline 区块 + progress doc |

## 硬规则对账
| 规则 | 状态 | 说明 |
|---|---|---|
| R-A smoke-must-test | OK | b21737e 13:37:23 commit，runner JSON 13:37:29；f7e98d1 13:38:07 声称 HEAD=b21737e6 与 JSON 13:37 吻合；7a2579e 13:51 声称 HEAD=3f69075，JSON 13:49:56 吻合 |
| R-B 一 commit 一 signal | OK | 5 commit 每条 trailer 仅一个 `Signal:` |

## Top 3 Gap（为 Phase 1 锚点）
1. **Fixture 是合成 good-run，不是 runtime 产出** — 5 指标全绿只证明 adapter 能识别合格形态，不证明 Agent2 LLM 链路质量。Phase 1 必须接 `RiskControlAgent.process_message` 端到端产物替换 `baseline_v1/`，`baseline_v1` 降级为回归锚。
2. **Phase C 两 stub 卡在框架能力外** — `ks_improvement` 缺 `baseline_ruleset` 对照组概念；`rule_interpretability` 依赖 LLM-judge runtime（评估框架未实现）。Phase 1 需在 `rule_engine.py` 引入 baseline 集，短期可为 interpretability 接 heuristic 降级（非红线）。
3. **false_positive_rate 只到汇总层** — 0.0673 是全规则合并 FPR，R002 高负债率等单条误杀率被掩盖。Phase 1 扩 `BacktestResult.metrics.rule_stats` per-rule confusion matrix，新增 `per_rule_fpr_spread` 警戒高方差。

## 亮点
- `hallucination_rate` 走字段名严格比对（conditions.field ∉ schema.columns），而非关键词黑名单，遵循 CLAUDE.md §12 治本原则。
- adapter 对 rules / schema / backtest 三份缺失场景分别返回 `value=None + note`，不 silent pass。
- progress doc 主动坦白 "fixture 合成 good-run，全绿 ≠ Agent2 达标"，并自陈 Signal await semantics 违规（ACK 后未分步等 GO）。工程诚实度达标。
- Phase 1 Baseline Contract 把 fixture 全绿值固化为"不允许回退"的警戒线（fpr ≤ 0.07 严于 yaml 0.15）。

## Required Actions
无（APPROVED）。Phase 1 onboarding 起草时采纳 Top 3 Gap 作为主线锚点；并重申 Signal await semantics 默认启用，worker 不要一口气推到 READY。
