# Agent4 Phase 0 Review

**日期**：2026-04-19
**reviewer**：主 CLI
**onboarding**：docs/onboarding/agent4-phase-0.md
**HEAD**：`e881d24`
**Signal**：AGENT4-PHASE-0-READY-FOR-REVIEW

## Verdict
**APPROVED**

## DoD 对账（逐条）

| 条目 | 状态 | 证据 |
|---|---|---|
| Task A · adapter 可 import | PASS | `52d3f90` 新增 `evaluation/runner/adapters/agent4_alert.py` 279 行，结构对齐 `agent6_report.py` 范式 |
| Task A · `@register_evaluator("alert")` | PASS | `--list` 输出含 `alert` + `report` |
| Task A · `--list` 看到 alert | PASS | 主 CLI 实测 `py -m evaluation.runner --list` |
| Task A · `--agent alert` 出 PARTIAL | PASS | 实测 verdict=PARTIAL，6 deterministic PASS + 2 stub N/A |
| Task A · Phase C 返回 `None/manual` | PASS | cross_hit_precision / recall_on_known_bad 正确标 stub，note 交代缺什么数据 |
| Task B · `4_20260419.yaml` 落盘 | PASS | yaml baseline 区块已填，result_file 路径在 gitignored 目录（符合 `de1b6b5`） |
| Task B · 4 确定性指标有值 | PASS | task=1.00 / evidence=1.00 / hallucination=0.00 / tool=0.9667 |
| Task B · 红线闸门全绿 | PASS | hall ≤ 0.01、evidence ≥ 0.95、task ≥ 0.95 三条均满足 |
| 红区守线 | PASS | 未碰 `shared/` `docs/contracts/` `web/` runner framework |
| Productize 禁令 | PASS | 无 UI / API endpoint / Pipeline 改动 |

## 硬规则对账

| 规则 | 状态 | 说明 |
|---|---|---|
| R-A smoke-must-test | PASS | 主 CLI 实测 `--list` + `--agent alert`，输出与 3 个 commit message 声称完全一致（PARTIAL + 6 PASS + 2 N/A） |
| R-B 一 commit 一 Signal | PASS | `c7060a0` ACK / `52d3f90` ADAPTER-READY / `9dfcaf2` BASELINE-FIRST-RUN / `e881d24` READY-FOR-REVIEW，粒度清晰 |

## Top 3 Gap（Phase 1 锚点）

1. **Phase C 真值缺失**：`cross_hit_precision` / `recall_on_known_bad` 需要标注库（ground truth + known-bad 清单）才能从 manual 升 deterministic；当前基线只证"流程跑通"，**没证"识别准不准"**，Agent4 核心价值未量化。
2. **Fixture 是合成数据**：3/22/75 分布、均匀分布 180-2200ms 延迟、固定枚举 signal 是人工拍的；接真 ledger + 真外部源（Tavily / 工商 / 司法）后基线大概率会塌档。
3. **无回归护栏**：`agent_alert/tests/` 只有 fixtures/，无 pytest；adapter 的 `_p95`、grade 阈值、evidence 判定逻辑裸奔，后续 fixture 手抖改错会静默漂移。

## Required Actions
无（Phase 0 边界严格守住；gap 已自认并写入 Phase 1 锚点，不阻塞合并）。

## 亮点
- **自我诚实**：PARTIAL verdict 不粉饰，Phase C 按 onboarding 指示走 stub，不为达标而造数据，符合 CLAUDE.md §12 "字段填不了就标未能自动填写"。
- **commit 粒度规范**：ACK / ADAPTER-READY / BASELINE-FIRST-RUN / READY-FOR-REVIEW 四段独立，方便 `git revert` 精准回滚。
- **Phase 1 锚点清晰**：baseline 报告已把后端接真源 / Phase C RFC / 回归护栏 / 前端越界红线四条写明，下发 phase-1 onboarding 可直接引用。
- **范式复用**：adapter 严格对齐 `agent6_report.py` 的 `register_evaluator` + `BaseEvaluator` + `MetricOutcome` stub 模式，零框架漂移。
