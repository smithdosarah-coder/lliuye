# Agent2 Phase 1 · Task A · Fixture → Runtime

**日期**：2026-04-19
**commit**：待填（本文件随 TASK-A-DONE commit 落盘）
**worktree**：`D:\claude code\demo-agent2` (`feat/agent2-productize`)
**onboarding 锚点**：`docs/onboarding/agent2-phase-1.md` §3 Task A

---

## 目标与闭环

Phase 0 baseline 全绿来自**合成 good-run fixture**（`baseline_v1/`），只证明 adapter 能识别合格形态——不证明 Agent2 LLM 链路本身质量。Task A 的闭环：

- 替换 fixture 为 `RiskControlAgent.process_message` 真实端到端产物
- fixture 降级为"回归锚"，adapter 增加三级 fallback
- Phase 0 红线闸门 runtime 值**不倒退** → 证明 Agent2 LLM + 回测链路生产级可用

---

## 交付物

### 1. 新建文件

| 文件 | 作用 |
|---|---|
| `evaluation/manual/2_20260419.yaml` | runtime 输入契约（3 flow × 固定 prompt + CSV seed；可复现） |
| `scripts/run_agent2_baseline.py` | runtime baseline 脚本；跑 3 flow 产 3 JSON |
| `docs/progress/agent2-phase-1-task-a.md` | 本文件 |

### 2. 修改文件

| 文件 | 变更 |
|---|---|
| `evaluation/runner/adapters/agent2_riskctrl.py` | `_resolve_fixture_dir` 从单级 fallback 升为三级（artifacts → runtime/2_latest → fixture/baseline_v1） |
| `evaluation/agent2_riskctrl.yaml` | baseline 区块：fixture_dir 指向 runtime 路径、commit / results 来自 runtime 跑出、加 runtime_vs_fixture 对比 |
| `agent_riskctrl/tests/fixtures/baseline_v1/README.md` | 头部标注"回归锚（regression anchor）、非当期生产基线" |
| `.gitignore` | 新增 `evaluation/runtime/2_*/`（运行时产物 gitignored，保持 worktree 干净） |

### 3. Runtime 产物（gitignored · 由 seed=42 可复现）

路径：`evaluation/runtime/2_20260419T091022/`（+ `2_latest/` 软拷贝）

- `sample_data.csv` —— 150 行合成 CSV（11 列字段对齐 `baseline_v1/sample_schema.json`）
- `rules.json` —— flow_2 backtest 流 LLM 产出的 7 条 DSL 规则 + 各规则 runtime backtest 字段
- `sample_schema.json` —— 从合成 CSV 自动导出的 columns + label_column
- `backtest.json` —— runtime 3 个工具调用 trace + 真实 confusion_matrix（从 `label_default` 列对比 reject action 算）

---

## 实现要点（Agent2 代码零改动）

### Monkey-patch 捕获层（`scripts/run_agent2_baseline.py`）

`RiskControlAgent.process_message` 是 Generator，内部 `ruleset` / `backtest_result` 是局部变量。为**不改 `agent.py`**（降低 Task A 的 blast radius）采用 Python 导入机制 monkey-patch：

```python
import agent_riskctrl.agent as agent_mod
agent_mod.parse_natural_language_rules = _hooked_parse   # 捕获 ruleset
agent_mod.run_backtest = _hooked_backtest                # 捕获 backtest_result
```

因为 `agent.py` 里 `from .rule_engine import ... parse_natural_language_rules` 将名字**绑定到 `agent_mod` 的命名空间**，对模块属性打 patch 即可重定向调用。agent.py 代码行**未改一行**。

### 三级 fallback（`evaluation/runner/adapters/agent2_riskctrl.py`）

```python
def _resolve_fixture_dir(run) -> tuple[Path, str]:
    if run.artifacts:           return (<explicit>, "artifacts_arg")
    if runtime_2_latest_valid:  return (runtime_2_latest, "runtime_latest")
    return (fixture_baseline_v1, "fixture_baseline_v1_regression_anchor")
```

`fixture_source` 标签随 artifacts dict 传递，供 review 溯源"本次 baseline 从哪一级拿到的数据"。

### 合成 CSV 的 provenance

- seed=42 固定；150 行；字段 100% 取自 `baseline_v1/sample_schema.json` columns
- label_default 算法：`bad_signal = (credit<580) + (debt>0.75) + (overdue90>30) + (overdue12>=3)`；bad_signal>=2 → 1；==1 → 20% 概率 1；else 0
- 本合成 CSV 是**runtime 链路测试载荷**，非真实客户分布代表。生产基线的置信度由 "Agent2 LLM 对真实字段能生成合规 DSL + 回测产物 schema 正确" 两点证明，不对数据真实性做声明

---

## Runtime 结果（46051f20，2026-04-19 09:10 UTC）

| 指标 | Runtime | Phase 0 Fixture | 是否倒退 |
|---|---:|---:|---|
| task_completion_rate | 1.0000 | 1.0000 | 持平 ✅ |
| evidence_rate | 1.0000 | 1.0000 | 持平 ✅ |
| hallucination_rate | 0.0000 | 0.0000 | 持平 ✅ |
| tool_success_rate | 1.0000 | 1.0000 | 持平 ✅ |
| false_positive_rate | 0.0439 | 0.0673 | 严于 ✅（更好） |
| ks_improvement | null (Phase C stub) | null | 持平 |
| rule_interpretability | null (Phase C stub) | null | 持平 |

**红线闸门全绿**。verdict 仍为 `PARTIAL` —— 因 2 个 Phase C stub `passed=None` 未走白名单豁免。**Task B 会把它们纳入 `baseline.pending_metrics`，A-013 kernel 落 PASS**。本 Task A **不**在 yaml 加 `pending_metrics`（避免与 Task B 范围重叠 / 提前闯 verdict）。

### LLM 链路质量证据（实证，非合成）

- flow_1 rule_config：LLM 基于文字需求生成 5 条规则（与 onboarding §1-5 条策略诉求逐条吻合）
- flow_2 backtest：LLM 基于 150 行 CSV 数据摘要自主生成 **7 条** 规则（LLM 决定规则粒度 > 合成 fixture 的 5 条，展示真实链路更精细）
- flow_3 error_analysis smoke：分析 C_00017 误杀案产出建议文本；未纳入 baseline 但冒烟通过，证明第三流程链路健康
- 所有 LLM 输出字段 100% ∈ schema.columns（hallucination=0.0）——字段幻觉已由 prompts.py 的 `SYSTEM_RULE_PARSER` + data_summary 注入字段提示闭环

### 工具链证据

`tool_calls` 3 条全 success：`llm_generate_rules` / `backtest` / `calculate_confusion_matrix`。runtime 与 Phase 0 fixture 的 7 条 tool_calls 差异——runtime 仅暴露 agent 实际发出的事件（flow_2 只用到上述 3 个工具），fixture 是预先手写的 7 条范式。说明 **tool_success_rate 指标必须消费 runtime trace 而非 fixture**，否则只证明 fixture 书写合规。

---

## A-012.D SHA 不可变对齐

本 Task 仅**新增**文件 + 改动允许黄区文件，未触碰 5 个已被 review 引用的 SHA (`b21737e`/`f7e98d1`/`3f69075`/`7a2579e`/`ff1b1bd`)。无 rebase / amend / force-push。

## A-012.E upstream catch-up 对齐

本 Task 未进行 upstream 追 fetch（ACK 时已 `merge --no-ff chore/l0-infra @ 73d6732` at `9b78130`）。A-019 @ `c947906` 在上游，Task C 开始前会再走一次 `merge --no-ff` 拿 A-019 锚点，不用 rebase。

---

## DoD 逐条对账

- [x] `evaluation/manual/2_20260419.yaml` 存在，含 runtime 输入契约
- [x] `py scripts/run_agent2_baseline.py` 跑通；3 JSON 由真实 LLM + 回测链路产出
- [x] `py -m evaluation.runner --agent riskctrl` 默认读 runtime/2_latest/（fixture_source=`runtime_latest`）
- [x] `evaluation/agent2_riskctrl.yaml` baseline 区块刷新到 runtime 值、commit 为 46051f20
- [x] `baseline_v1/README.md` 标注"回归锚"
- [x] 红线闸门 runtime ≥ 0.9x fixture（实际全部 ≥ fixture，无需降级）
- [x] A-012.D SHA 不可变对齐（新增文件 + 黄区改动）
- [x] R-A smoke-must-test 对齐（本 commit HEAD 上实测 `py scripts/run_agent2_baseline.py` + `py -m evaluation.runner --agent riskctrl`）
- [x] R-B 一 commit 一 Signal

## 下一步

Task A 结束 → commit `AGENT2-PHASE-1-TASK-A-DONE` → **idle 等主 CLI GO** 再进 Task B（Signal await semantics，零容忍；Phase 0 曾违规一次）。
