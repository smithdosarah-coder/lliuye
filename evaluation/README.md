# Evaluation Framework

双轨评估配置：每个 Agent 一份 YAML，定义通用指标（任务完成度/幻觉/工具正确性）+ 领域专业指标（信贷场景特有）。

## 规则

1. 改 prompt / 改逻辑前，先跑对应 Agent 的评估基线。
2. 挑最大 gap 的 1-2 个维度下手，改完重新跑，确认没退化。
3. 新增维度先在这里加 metric 定义，再去改代码。
4. 目标值（`target`）代表可发布门槛，低于门槛不得上线。

## 文件清单

- `agent1_channel.yaml` — 全渠道获客
- `agent2_riskctrl.yaml` — 风控策略
- `agent3_credit.yaml` — 授信决策
- `agent4_alert.yaml` — 贷中预警
- `agent5_compliance.yaml` — 合规巡检
- `agent6_report.yaml` — 报告生成
