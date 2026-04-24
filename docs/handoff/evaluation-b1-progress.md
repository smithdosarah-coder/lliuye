# Evaluation · Batch 1 Progress Tracker

**Worker**: evaluation (`feat/evaluation`)
**Batch**: Product Hardening · Batch 1
**Onboarding**: `docs/onboarding/evaluation-phase-1.md`
**Overrides**: A-024 / A-025（`docs/handoff/decisions-log.md` · 已覆盖 onboarding 字面）
**Resume 日**: 2026-04-24

---

## Task 状态

| # | Task | 工作量 | 完成 Signal | 状态 |
|---|---|---|---|---|
| ACK | Resume + 读 A-024/A-025 | S | `PRODUCT-HARDENING-BATCH-1-ACK` | 🟡 in-progress |
| A | 6 × rubric YAML（agent1-5 新 schema + agent6 双写） | M · 1.5d | `EVAL-RUBRIC-YAML-6AGENT-DONE` | ⏳ pending |
| B | 3 adapter（agent1/3/5）+ BaseEvaluator fallback 层 | L · 3d | `EVAL-RUNNER-BASE-DONE` | ⏳ pending |
| C | 首轮基线 JSON + markdown 报告 | S · 0.5d | `EVAL-BASELINE-FIRST-RUN` | ⏳ pending |
| 末 | 整批 review 触达 | — | `READY-FOR-EVALUATION-B1-REVIEW` | ⏳ pending |

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
