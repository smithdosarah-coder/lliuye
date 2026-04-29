# RFC: 跨 Agent 评估 Runner 建设

**发起人**：主 CLI（源自 v16 CLI Q-002 坑 1 派发）
**日期**：2026-04-18
**变更类型**：黄区（新增 `evaluation/runner/` 模块；各 Agent `evaluation/*.yaml` 仅扩字段不改 schema）
**关联决策**：`docs/handoff/decisions-log.md` [A-002]
**审批状态**：**APPROVED + IMPLEMENTED · Phase A 已 ship**（2026-04-29 status sync）
- Phase A 落地：`evaluation/runner/` 完整 8 modules（base_evaluator + schemas + registry + cli + 6 adapter + cross_agent/ratio_consistency + tests/）
- 6 adapter 全 ready：agent1_channel / agent2_riskctrl / agent3_credit / agent4_alert / agent5_compliance / agent6_report
- 跨 Agent 验证：cross_agent.ratio_consistency 跨 agent3/agent6 财务比率一致性已接
- 锚点 baseline：v16 unfilled_marker 0.625（Phase A `94c04f5`）已入 yaml

---

## 0. 问题陈述

`evaluation/*.yaml` 6 份配置已落地（每 Agent 一份，含 common/domain metrics + baseline 字段），但**没有 runner 实现**：

- v16 CLI Phase 1 DoD 写明 `halluc_rate ≤ 0.01` / `evidence_rate ≥ 0.95`，但没有程序能跑出这两个数 → DoD 无法客观验证
- Agent2 风控的 KS / PSI / 混淆矩阵回测独立在 `agent_riskctrl/backtest.py`，与 evaluation 配置脱节
- Agent1 / Agent3 / Agent4 / Agent5 的 `tool_success_rate` / `evidence_rate` 均靠"commit message 里手写估计值"

**根因**：evaluation 配置是"声明式规格"，runner 是"执行层"，两者应 1:1 配套但当前只有前半。

**不解决的后果**：每个子 CLI 会各自写一套 ad-hoc 评估脚本，Agent2 backtest / Agent6 halluc 检测 / Agent1 信号多样性检查 → 3 套实现、3 种 JSON schema、3 套 CLI，对齐困难。

---

## 1. 提议架构

### 1.1 目录结构

```
evaluation/
  *.yaml                    ← 已存在，不动
  runner/                   ← 新建，黄区
    __init__.py
    base_evaluator.py       ← 抽象基类 + 公共 metric 实现
    registry.py             ← 各 Agent adapter 注册表
    cli.py                  ← `python -m evaluation.runner --agent report` 入口
    schemas.py              ← EvalRun / EvalResult / MetricOutcome Pydantic
    adapters/
      __init__.py
      agent1_channel.py     ← 每 Agent 一个 adapter，消费自家 artifacts
      agent2_riskctrl.py
      agent3_credit.py
      agent4_alert.py
      agent5_compliance.py
      agent6_report.py
  results/                  ← 新建，存每次 run 的结果 JSON
    YYYY-MM-DD/
      agent6_report_<commit>.json
```

### 1.2 `BaseEvaluator` 契约

```python
# evaluation/runner/base_evaluator.py
from abc import ABC, abstractmethod
from typing import Any
from .schemas import EvalRun, EvalResult, MetricOutcome

class BaseEvaluator(ABC):
    agent_id: str                       # "report" / "channel" / ...
    config_path: str                    # "evaluation/agent6_report.yaml"

    @abstractmethod
    def load_artifacts(self, run: EvalRun) -> dict[str, Any]:
        """从 outputs/ / data/ / api_server 抓本次 run 要评估的产出物。"""

    @abstractmethod
    def compute_domain_metrics(self, artifacts: dict) -> list[MetricOutcome]:
        """Agent 专属指标，各 adapter 必须实现。"""

    def compute_common_metrics(self, artifacts: dict) -> list[MetricOutcome]:
        """通用指标：field_completeness / evidence_rate / hallucination_rate /
           tool_success_rate / task_completion_rate。base 类给默认实现，adapter 可覆盖。"""
        ...

    def run(self, run: EvalRun) -> EvalResult:
        """标准流程：load_artifacts → common + domain → 对 target → 存 results/"""
        ...
```

### 1.3 Adapter 职责边界

| Adapter | 必须实现 | 可复用 base |
|---|---|---|
| agent1_channel | 信号多样性 / 候选新鲜度 | common 全部 |
| agent2_riskctrl | KS / PSI / 混淆矩阵（迁 `agent_riskctrl/backtest.py`） | common 全部 |
| agent3_credit | 四维评分与人审一致率 / 红线判定准确率 | common 全部 |
| agent4_alert | 双路交叉召回率 / 信号级联 FP | common 全部 |
| agent5_compliance | 违规点去重后精确率 / 缺陷分级一致率 | common 全部 |
| agent6_report | hallucination_rate / evidence_rate / financial_ratio_consistency / template_leakage_rate / quality_score_total | common 全部 |

**关键约束**：`compute_domain_metrics` 内部只能调各 Agent **自己 agent_*/ 目录下的函数** + `financial_analyzer` / `quality_scorer` / `quality_check`（红区共享）。禁止 adapter 之间互相 import。

### 1.4 CLI 入口

```bash
# 跑单 Agent 基线
python -m evaluation.runner --agent report --artifacts outputs/普惠申报书_骨架型_v16.docx

# 跑全部 6 Agent（CI 用）
python -m evaluation.runner --all

# 对比基线（commit hash → commit hash）
python -m evaluation.runner --agent report --compare-baseline
```

输出：`evaluation/results/YYYY-MM-DD/<agent>_<commit>.json` + stdout 摘要表。

---

## 2. 影响面

| 文件 | 变更 | 兼容性 |
|---|---|---|
| `evaluation/*.yaml` | 仅在 `baseline.result` 下增 `runner_version` 字段 | ✅ 向后兼容（旧字段保留） |
| `evaluation/runner/` | 新建 | ✅ 纯加法 |
| `evaluation/results/` | 新建（进 .gitignore，仅 baseline snapshot 入库） | ✅ |
| `agent_riskctrl/backtest.py` | 不改，由 `agent2_riskctrl.py` adapter 包一层消费 | ✅ 零破坏 |
| `quality_scorer.py` | 不改，adapter 直接调用 | ✅ 零破坏 |
| 各 `agent_*/` 目录 | 不改 | ✅ |

**跨 Agent 耦合**：adapter 之间**零耦合**，只共享 `BaseEvaluator` + `schemas`。

---

## 3. 替代方案

**Alt-A**：每 Agent 自己写 runner（v16 CLI 自己给 agent6 写一个、Agent2 用现成 backtest、其他 TBD）
- 否决：A-002 理由成立 —— 5 套 JSON schema / 5 套 CLI / 5 套 CI 接入方式，跨 Agent 对比不可能

**Alt-B（本方案）**：base_evaluator + per-agent adapter
- 选择：统一 schema / 统一 CLI / 跨 Agent 可合并跑 / CI 一键接入

**Alt-C**：外接评估框架（langsmith / promptfoo / helm）
- 否决：这些框架的指标体系面向通用 LLM 任务，信贷域的"财务比率一致率 / 红线判定准确率"无法表达；且 adapter 仍要写，等于双重工程

---

## 4. 实施路径（不占 v16 Phase 1）

**Phase A（2026-04-19 ~ 2026-04-22）· 主 CLI 亲自**：
1. `base_evaluator.py` + `schemas.py` + `registry.py` + `cli.py`
2. `adapters/agent6_report.py` —— 实现 hallucination_rate / evidence_rate / template_leakage_rate（v16 CLI Phase 1 DoD 直接受益）
3. 跑 `outputs/普惠申报书_骨架型_v16.docx` 出第一份 baseline

**Phase B（Phase 1 结束后）· 主 CLI 委派**：
4. `adapters/agent2_riskctrl.py` —— 迁 `agent_riskctrl/backtest.py` 的 KS/PSI 到 adapter，Agent2 CLI 配合
5. `adapters/agent1_channel.py` / `agent3_credit.py` / `agent4_alert.py` / `agent5_compliance.py` —— 各子 CLI 写自家 adapter（黄区变更，发 RFC 申明 domain metric 定义即可落地）

**Phase C（Phase 2）· 主 CLI 主导**：
6. CI 接入（github actions / gitlab ci）—— 每 commit 跑 `--all`，低于 target 阻断合并

---

## 5. v16 CLI 依赖时序

v16 CLI Phase 1 DoD 原定要求 halluc/evidence 阈值达标。A-002 已放宽为**骨架型 QC ≥ 75**，阈值验证推迟到 Phase A runner 落地后。

- **v16 Phase 1 DoD 不受 runner 缺失阻塞**（已在 A-002 调整）
- **Phase A runner 落地后**，v16 CLI 用 `python -m evaluation.runner --agent report` 补跑一次 baseline，数值入库 `evaluation/agent6_report.yaml` 的 `baseline.result`

---

## 6. 自审自批理由

本 RFC 虽属黄区（新建 `evaluation/runner/`）+ 红区 yaml 字段扩展（baseline.runner_version），按协议需 RFC，但：

1. 变更纯加法，零破坏性（旧字段保留、旧代码无依赖）
2. Phase A 由主 CLI 亲自动手，不委派
3. Phase B/C 的每个 adapter 落地时各子 CLI 单独发 RFC 定义 domain metric，二次 gating

故此 RFC 自审 ✅ APPROVED，Phase A 开工不等外部批复。Phase B 启动前需主 CLI 复盘本 RFC 是否需修订。

---

## 7. 验证计划

- [ ] Phase A 落地后，`python -m evaluation.runner --agent report` 能对 v16 骨架型产物跑出 hallucination_rate / evidence_rate 实测值
- [ ] 实测值与 `evaluation/agent6_report.yaml` 的 target 比较，产出达标 / 未达标结论
- [ ] adapter 之间无 cross-import（`grep -r "from evaluation.runner.adapters" evaluation/runner/adapters/` 为空）
- [ ] `evaluation/results/` 进 `.gitignore`，仅手工拣选的 baseline snapshot 入库

---

## 8. 协议层影响

本 RFC 不触发 `shared-change-protocol` 进一步修订。`evaluation/runner/` 属新建目录，不在现有红/黄区清单中。

Phase B/C 启动前，主 CLI 会评估是否把 `evaluation/runner/base_evaluator.py` / `schemas.py` 纳入红区（理由：被 6 个 adapter 消费，改签名 = 全员 break）。本 RFC 不预先声明，避免过度治理。
