# Evaluation · Batch 1 Progress Tracker

**Worker**: evaluation (`feat/evaluation`)
**Batch**: Product Hardening · Batch 1
**Onboarding**: `docs/onboarding/evaluation-phase-1.md`
**Overrides**: A-024 / A-025（`docs/handoff/decisions-log.md` · 已覆盖 onboarding 字面）
**Resume 日**: 2026-04-24

---

## Task 状态

| # | Task | 工作量 | 完成 Signal | 状态 | Commit |
|---|---|---|---|---|---|
| ACK | Resume + 读 A-024/A-025 | S | `PRODUCT-HARDENING-BATCH-1-ACK` | ✅ done | `c25f7cb` |
| A | 6 × rubric YAML（agent1-5 新 schema + agent6 双写） | M · 1.5d | `EVAL-RUBRIC-YAML-6AGENT-DONE` | ✅ done | `f38490b` |
| B | 3 adapter（agent1/3/5）+ BaseEvaluator fallback 层 | L · 3d | `EVAL-RUNNER-BASE-DONE` | ✅ done | `0b47270` |
| C | 首轮基线 JSON + markdown 报告 | S · 0.5d | `EVAL-BASELINE-FIRST-RUN` | ✅ done | `b243913` |
| 末 | 整批 review 触达 | — | `READY-FOR-EVALUATION-B1-REVIEW` | ✅ done | `8c4f087` |

---

## HOLDING 阶段（Batch 1 APPROVED 合流后）

| # | Task | 工作量 | 完成 Signal | 状态 | Commit |
|---|---|---|---|---|---|
| H-ACK | HOLDING 启动 | S | `HOLDING-EV-ACK` | 🟡 in-progress | (本 commit) |
| H-A | v16 summary parse · agent6 3 项 method=manual→deterministic | S | `HOLDING-EV-H-A-DONE` | ⏳ pending | — |
| H-末 | HOLDING 结 | — | `HOLDING-EV-DONE` | ⏳ pending | — |

### HOLDING 红线
- ❌ 不改 `v16_pipeline.py` / `agent_*/` / `data/mock/` / evaluation rubric YAML
- ❌ 不碰 EV-12 `ratio_calc_consistency`（Batch 2 议题）
- ✅ 只动 `evaluation/runner/adapters/agent6_report.py`（加 v16 summary JSON parse）
- ✅ 必要时 CLI 增强（加 `--out` 等纯加法）
- ✅ 基线 md "首轮数字偏乐观" 警示段保留

## 基线首轮 verdict 速览

| Agent | verdict | 实算/总 | 说明 |
|---|---|---|---|
| alert | 🟢 PASS | 6/10 | 红线全绿 · pending 4 条豁免 |
| riskctrl | 🟡 PARTIAL | 5/10 | 红线全绿 · pending 5 条（含 B1 新加 2 条） |
| credit | 🟡 PARTIAL | 6/10 | 红线全绿 · 需 tool 埋点 + 术语表 + 人工真值 |
| channel | 🟡 PARTIAL | 0/10 | 缺 runtime dump · adapter 就绪等 `agent_channel.api.py` 埋点 |
| compliance | 🟡 PARTIAL | 0/10 | 缺 runtime dump · adapter 就绪等 `agent_compliance.api.py` 埋点 |
| report | 🔴 FAIL | 3/10 | artifact 退化（骨架自比）· Phase 2 用真 v16 产出重跑 |

---

## A-024 / A-025 关键点（覆盖 onboarding 的地方）

### A-024 · Runner 路径修正
- ❌ 不新建 `evaluation/base_evaluator.py` / `evaluation/cli.py`
- ✅ `evaluation/runner/base_evaluator.py` 已生产就绪（182 行 ABC + agent2/4/6 adapter）
- ✅ Task B 只补 `evaluation/runner/adapters/{agent1_channel,agent3_credit,agent5_compliance}.py` 3 份
- ✅ CLI 入口：`py -m evaluation.runner --agent <id>`

### A-025 · YAML schema 双写
- ✅ agent1-5 新 YAML 严格新 schema：`name` / `description` / `method` / `baseline_target` / `blocker_threshold`
- ✅ `agent6_report.yaml` 保留老 `desc` / `target`（v16 pipeline 消费）+ 追加新字段双写
- ✅ `BaseEvaluator._metrics_config()` 实现 fallback：新字段优先 → fallback 老字段（`desc→description`）→ parse `target` 字符串（`">= 0.9"`）→ `baseline_target` float

---

## 红线（不越界）

- ❌ 不改 `v16_pipeline.py` / `v16_generator.py` 等 Agent6 核心文件
- ❌ 不改 `agent_*/` 业务代码（code-urgent / code-arch 地盘）
- ❌ 不碰 `data/mock/`（data-foundation 地盘）
- ❌ 不改 `agent6_report.yaml` 老字段（只能追加）
- 变更 A-024 / A-025 须开 RFC

---

## 警示

首轮基线分数会"偏乐观"——mock 数据简单。Batch 2 等 data-foundation Batch 2 真脏数据落地后重跑对比 gap。本轮数字**起点参照**，**非客户证据**。
