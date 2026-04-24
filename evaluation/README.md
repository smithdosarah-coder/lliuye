# Evaluation Framework

双轨评估配置：每个 Agent 一份 YAML，定义通用指标（任务完成度/幻觉/工具正确性）+ 领域专业指标（信贷场景特有）。

## 规则

1. 改 prompt / 改逻辑前，先跑对应 Agent 的评估基线。
2. 挑最大 gap 的 1-2 个维度下手，改完重新跑，确认没退化。
3. 新增维度先在这里加 metric 定义，再去改代码。
4. `baseline_target` 是 PM 锚定的期望值；`blocker_threshold` 是"低于此线阻断发布"的红线。

## Schema (A-025 · 双字段)

每条 metric 同时带两套字段，保证新老消费者兼容：

| 字段 | 来源 | 谁消费 |
|---|---|---|
| `desc` | 老 schema | `agent6_report.yaml` · `v16_pipeline` 继续读 |
| `target` | 老 schema (字符串表达式 `">= 0.9" / "<= 0.02" / "pass"`) | `BaseEvaluator._lookup_target` · `mark()` 判 pass |
| `description` | 新 schema | 产品文案 · rubric 渲染 |
| `method` | 新 schema (自然语言描述计算公式) | PM review · 基线报告 |
| `baseline_target` | 新 schema (数字) | PM 对标 · 趋势图 |
| `blocker_threshold` | 新 schema (数字) | 发布闸门 · 红绿灯 |

语义规则：**`baseline_target` 与 `target` 方向一致**——
- `target: ">= 0.95"` → `baseline_target: 0.95`（期望值，越大越好）
- `target: "<= 0.02"` → `baseline_target: 0.02`（期望值，越小越好）
- `blocker_threshold` 比 `baseline_target` 宽松一档，跨此线阻断发布。

## 文件清单

| YAML | Agent | common × domain | Baseline 状态 |
|---|---|---|---|
| `agent1_channel.yaml` | 全渠道获客 | 5 × 5 | ⏳ 待首跑 |
| `agent2_riskctrl.yaml` | 风控策略 | 5 × 5 | ✅ `8ec4283` PASS (2 pending · A-013 白名单 + B1 新加 2 pending) |
| `agent3_credit.yaml` | 授信决策 | 5 × 5 | ⏳ 待首跑 |
| `agent4_alert.yaml` | 贷中预警 | 5 × 5 | 🟡 `52d3f90` PARTIAL (2 pending + B1 新加 2 pending) |
| `agent5_compliance.yaml` | 合规巡检 | 5 × 5 | ⏳ 待首跑 |
| `agent6_report.yaml` | 报告生成 | 5 × 5 | 🟡 `2026-04-03` field=0.935 |

## Runner

路径：`evaluation/runner/`（见 A-024）

```bash
# 单 Agent
py -m evaluation.runner --agent report --artifacts outputs/普惠申报书_骨架型_v16.docx

# 全部
py -m evaluation.runner --all

# 仅列已注册 adapter
py -m evaluation.runner --list
```

每次运行产出：`evaluation/results/YYYY-MM-DD/<agent>_<commit>.json`（gitignored 除手工拣选的 baseline snapshot 外）。

## 如何读基线报告

`evaluation/baselines/YYYY-MM-DD-first-run.md` 的每 Agent 段落：

1. **verdict** — `PASS` / `PARTIAL` / `FAIL` 一行判定
2. **红线闸门** — `hallucination_rate / evidence_rate / task_completion_rate` 三闸门是否全绿
3. **gap top 3** — 本 Agent 距 `baseline_target` 差距最大的 3 条指标 + 数字
4. **改进建议** — 对应每条 gap 一条动作（prompt/代码/数据侧）

**警示**：首轮基线"偏乐观"——mock 数据简单、真值集未到位。Batch 2 真脏数据落地后重跑对比。
