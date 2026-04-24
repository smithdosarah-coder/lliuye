# code-arch · Product Hardening Batch 1 · 执行进度

**Worker**: code-arch
**Worktree**: `D:/claude code/demo-code-arch`
**Branch**: `feat/code-arch`
**Onboarding**: `docs/onboarding/code-arch-phase-1.md`
**Batch 源决策**: `docs/handoff/decisions-log.md` Q-023/A-023

---

## Task 清单

| # | Task | 状态 | Signal | Commit |
|---|---|---|---|---|
| 0 | ACK | ✅ | `PRODUCT-HARDENING-BATCH-1-ACK` | `c2e3092` |
| A | 5 Agent 工具域 §3.2 重拆 | ✅ | `TOOL-DOMAIN-SPLIT-DONE` | `dd3a269` |
| B | 5 Agent Evidence 三阶段协议 | ✅ | `EVIDENCE-PROTOCOL-5AGENTS-DONE` | `357e511` |
| C | 飞轮第 4 环 feedback→fewshot 脚本 | ✅ | `FEEDBACK-FEWSHOT-PIPELINE-DONE` | `a076166` |
| Z | 交付 review | ✅ | `READY-FOR-CODE-ARCH-REVIEW` | 本 commit |

---

## 验证摘要

- **Task A**：5 Agent × 17 子域 × 42 个 `<域>_<动作>` 命名 public 函数；3 项契约测试（可 import / 命名合规 / 禁跨域互导）全绿
- **Task B**：`shared/evidence/protocol.py` 抽象基类 + 6 Agent 各自 `evidence_pipeline.py`；18 case（5 Agent × 2 + Agent6 × 2 + 抽象契约 × 6）全绿
- **Task C**：`feedback_to_fewshot` + `inject_fewshot_to_prompts` 两段式脚本 + PM SOP runbook + 10 条合成 fixture；4 case（聚合 / min-count 阈值 / inject-revert roundtrip / dry-run 不写盘）全绿
- **总 test 数**：33 passed（tests/test_domain_imports + test_evidence_pipelines + test_feedback_fewshot）
- **红线**：Agent6 / financial_analyzer / quality_scorer / truth_fill / web/ 均未动；code-urgent / data-foundation / evaluation 地盘未碰
- **pre-existing 上游 bug**：`agent_credit.risk_classifier` 依赖 `prompts.SYSTEM_RISK_ASSESS`（code-urgent 地盘），本 worker 不修；scoring_calc / redline_check 的两个相关 import 下沉到函数体以不扩散破坏面

---

## 红线自检

- ❌ 不动 Agent6 行为（`v16_*.py` / `section_generator.py` / `truth_fill.py`）
- ❌ 不动 `financial_analyzer.py` / `quality_scorer.py`
- ❌ 不动 `web/**`
- ❌ 不碰 code-urgent 的 §3.1 修复 / 占位符 QC / Agent2/4 api.py
- ❌ 不碰 data-foundation / evaluation 地盘
- ✅ 5 Agent 目录内部重组
- ✅ `shared/evidence/` 新增
- ✅ `scripts/feedback_to_fewshot.py` + `scripts/inject_fewshot_to_prompts.py` 新增
- ✅ `docs/runbook/feedback-flywheel.md` 新增

---

## 进度备注

按 Task A → B → C 顺序执行，每 Task 独立 commit 携带对应 Signal trailer。

---

## HOLDING 阶段（Batch 1 已合流后的清尾）

Batch 1 APPROVED · 合流主线。进 HOLDING 不抢 Batch 2 scope。

| # | Task | 状态 | Signal | Commit |
|---|---|---|---|---|
| H-0 | HOLDING ACK | ⏳ | `HOLDING-CA-ACK` | 本 commit |
| H-A | `feedback_to_fewshot.py` 加 `--dry-run` + 测试 | ⏳ | `HOLDING-CA-H-A-DONE` | — |
| H-Z | HOLDING 收尾 | ⏳ | `HOLDING-CA-DONE` | — |
