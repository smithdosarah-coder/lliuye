# Phase B Charter · 商业化推进

> Phase A 验收硬线全过 · 进 Phase B。Phase A 期间已可启动 Phase B (B1 + B2 准备工作 · 不阻 Phase A)。

---

## 1. Phase B 验收硬线 (3 项 · 全 yes 才算 reset 工程完毕)

| # | 验收项 | 怎么算 done |
|---|---|---|
| 1 | **数据飞轮 thin MVP** | feedback endpoint 接 audit modify · 写出第一批 jsonl · evaluation baseline 跑出 6 agent 各 5 项指标第一组数字 |
| 2 | **商业化 doc** | `docs/biz/{pricing, multi-tenant, trial-flow}-assumptions.md` v1 · PM + 销售视角 |
| 3 | **6 Agent 端到端 demo chain** | RM 工作台 1 客户全流程跑通 · 1 个完整 video 录 · 客户演示 ready |

---

## 2. 2 worker 拆分

### worker-B1 · 数据飞轮 thin MVP

- **worktree**: `D:\claude code\work-B1-flywheel`
- **branch**: `feat/phase-b1-flywheel`
- **可与 Phase A 后期并行**
- **交付**:
  - `/api/feedback` endpoint 真接 audit modify · 写 `data/feedback/YYYY-MM-DD.jsonl`
  - `evaluation/runner/cli.py` 跑 6 agent baseline · 输出 `evaluation/baselines/agent_{n}_2026-XX-XX.json`
  - `scripts/inject_fewshot_to_prompts.py` 真跑通 · 把高质量 feedback 注入 `agent_*/prompts.py` few-shot
  - `docs/runbook/feedback-flywheel.md` runbook
- **DONE signal**: `WORKER-B1-FLYWHEEL-DONE`

### worker-B2 · 商业化 doc

- **worktree**: `D:\claude code\work-B2-biz` (轻量 · 主要 PM 写 + AI 协助)
- **branch**: `feat/phase-b2-biz`
- **交付**:
  - `docs/biz/pricing-assumptions.md` (per-agent / per-seat / bundled · POC vs production)
  - `docs/biz/multi-tenant-assumptions.md` (现状 ECS 单租户 · 多租户路径)
  - `docs/biz/trial-flow-assumptions.md` (POC → 试用 → 转化)
  - `docs/biz/sales-playbook-v1.md` (基于 §6 闭环 · 演示脚本 · 价值锚点 3 个)
- **DONE signal**: `WORKER-B2-BIZ-DOC-DONE`

---

## 3. Phase B 退出 = reset 工程完毕

3 项验收 + Phase A 8 项验收 · 共 11 项硬线全过 → 产品"全新出发" · 可拿出去给客户卖。

---

## 4. Codex 介入

- 插入点 4 · periodic audit (Phase B 末跑全仓 audit · 确认无新 drift)
- 插入点 2 · post-DONE peer review (B1 / B2 各一次)
