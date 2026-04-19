# Agent2 风控 · baseline_v1 fixture

Phase 0 evaluation adapter 的基线产出物。**非真实客户数据**，合成用于锚定 Phase 1 产品化前的量化起点。

## 文件

| 文件 | 含义 | 被哪些指标消费 |
|---|---|---|
| `sample_schema.json` | 授信样本 CSV 的字段 schema + label 列 | `hallucination_rate`（规则字段 ∉ schema = 幻觉） |
| `rules.json` | DSL 生成输出（5 条规则，每条带回测证据字段） | `task_completion_rate`（inputs/outputs 比） + `evidence_rate`（规则是否带 ks/approve_rate/bad_rate） + `hallucination_rate`（规则字段 vs schema） |
| `backtest.json` | 回测工具调用 trace + 汇总混淆矩阵 | `tool_success_rate`（工具调用成功率） + `false_positive_rate`（FP / (FP+TN)） |

## 消费方

`evaluation/runner/adapters/agent2_riskctrl.py` 默认读取本目录（当 `run.artifacts` 为空时）。

## 更新规则

改 fixture = 改基线。每次变更记录在 commit message 里，不走 Phase 0 规则（Phase 1+ 再建 contract）。
