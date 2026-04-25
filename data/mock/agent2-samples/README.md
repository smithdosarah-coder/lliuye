# Agent2 风控历史贷款样本（agent2-samples）

**消费方**：Agent2 riskctrl 引擎 DSL 规则回测 + KS / FPR / 通过率 / 坏账率统计；以及 `evaluation/runner/adapters/agent2_riskctrl.py` 跑 5 项 pending 指标的真 baseline。

**产物**：

| 文件 | 内容 |
|---|---|
| `loans.csv` | 7500 行 + 1 表头 · 29 字段 · 单表平面结构 |
| `field_dictionary.md` | 29 段字段字典（与 csv 字段一一对应） |
| `_gen/generate_loans.py` | 确定性生成器 · `random.seed=42` · 可重跑 |

**字段总览**：8 分组——样本 ID / 申请人基础 / 企业基础 / 财务指标 / 贷款结构 / 征信信号 / 行为信号 / 结果列。**唯一答案列是 `days_past_due`**（最长逾期天数），其他字段全部为特征侧。

**对公 / 对私混合**：~50/50，对私样本的企业基础 + 财务指标 5 项留空字符串 `""`。

**难度档位**：样本按真实信贷场景的健康度自然分布——大多数为正常履约样本，少量为边缘 / 困难 / 极端坏账样本。**具体档位由 PM 私下维护，不写入 csv 字段、不写入字段字典、不写入本 README**（反结果导向第 1 条盲测）。

**不含**：`labels.json` / `optimal_dsl.yaml` / `difficulty_tags.csv` / 任何派生答案字段。
