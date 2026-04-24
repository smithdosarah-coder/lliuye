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
| 0 | ACK | ✅ | `PRODUCT-HARDENING-BATCH-1-ACK` | 本 commit |
| A | 5 Agent 工具域 §3.2 重拆 | ⏳ | `TOOL-DOMAIN-SPLIT-DONE` | — |
| B | 5 Agent Evidence 三阶段协议 | ⏳ | `EVIDENCE-PROTOCOL-5AGENTS-DONE` | — |
| C | 飞轮第 4 环 feedback→fewshot 脚本 | ⏳ | `FEEDBACK-FEWSHOT-PIPELINE-DONE` | — |
| Z | 交付 review | ⏳ | `READY-FOR-CODE-ARCH-REVIEW` | — |

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
