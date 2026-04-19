# Agent2 风控 · baseline_v1 fixture（回归锚 · regression anchor）

> **Phase 1 起始（2026-04-19）降级为回归锚**：当 `evaluation/runtime/2_latest/` 存在时，adapter 走 runtime 真实产物；本目录仅在无 runtime 产物时作为 fallback 使用，目的是防止"环境无 LLM / 脚本未跑"导致 adapter 失败。
>
> 当前生产基线来源：`py scripts/run_agent2_baseline.py` 产物（见 `docs/progress/agent2-phase-1-task-a.md`）。
> 本 fixture 值全绿 **不证明 Agent2 LLM 链路质量**，只证明 adapter 能识别合格形态（合成 good-run）。

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
