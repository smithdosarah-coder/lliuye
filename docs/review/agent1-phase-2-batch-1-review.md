# Agent1 Phase 2 Batch 1 · Review

**Reviewer**: 主 CLI (orchestrator)
**Date**: 2026-04-19
**Target**: `feat/agent1-productize` @ e7ddd86
**Onboarding**: `docs/onboarding/agent1-phase-2.md`
**Worker signal**: `READY-FOR-PHASE-2-REVIEW` (d825479) → `WINDOW-CLOSED-CLEAN` (e7ddd86)

---

## Verdict: **CONDITIONAL-APPROVE**

Option 4 独立 APPROVED。Option 2 功能满足但**分支 rebase 债必须先偿**，否则 commit message 里声称的冒烟命令跑不起来。

合流主干前强制前置动作见 §Required actions。

---

## Option 4 — handoff contract smoke（d1df143）· APPROVED

**亲跑冒烟**：
- `py -m pytest agent_channel/tests/test_handoff_contract.py -v` → **8 passed in 0.60s**
- `py -m pytest agent_channel/ -q` → **29 passed in 7.44s**

**A-004 §〇 合规** ✅：
- 纯 pytest manual asserts，无 `shared.EnterpriseProfile.model_validate()` 调用
- 走 `TestClient` POST `/api/channel/handoff` 实测真实写入路径
- 8 断言覆盖 envelope / required fields / FinancialAnchors cold-start / GuaranteeInfo+ExistingCredit / CreditRequest cold-start / related_party_pct 范围 / cold-start 反编造守卫

**反编造守卫 ✅**：如果未来 look-alike 阶段误填 FinancialAnchors / Chapters，此 test 会 fail fast。

---

## Option 2 — evaluation adapter + sampling CSV（f2bee8c）· CONDITIONAL

### 能跑的部分
- `py -m evaluation.runner.adapters.agent1_channel generate --top-n 5` → **10 rows 输出到 `evaluation/manual/sampling_20260419.csv`** ✅
- UTF-8 BOM CSV（Excel 原生可开）✅
- `score_from_recording()` Phase C stub 明确 raise NotImplementedError，边界清晰 ✅

### 跑不了的部分
- `py -m evaluation.runner --agent channel` → **`No module named evaluation.runner.__main__`**
- 根因：`feat/agent1-productize` 的 merge base 停在 upstream `e9eeaf0`，未 rebase 到主 CLI 最新 `de1b6b5`
- 缺失文件：`evaluation/runner/schemas.py` / `base_evaluator.py` / `registry.py` / `cli.py` / `__main__.py`（主 CLI `705326d` 上线的 framework）
- 结果：adapter 挂不进 `@register_evaluator("channel")` 的 registry，主命令入口不通

### 为何 CONDITIONAL 不 REJECTED
- Adapter 代码本身符合 onboarding §Option 2 规范（sampling CSV generator、profile_id UUID v4、sampling 流程边界清晰）
- commit 上游依赖可靠（705326d framework 在主 CLI 已落地可拉）
- 修复工作量 S（半小时内 rebase + 冒烟）

---

## Required actions before merge

Agent1 worker 重开窗口后执行：

1. `git fetch upstream && git rebase upstream/chore/l0-infra`
2. 预期冲突：`evaluation/runner/__init__.py`（Agent1 自建 vs 主 CLI framework） → 保留主 CLI 版本（framework 完整），把 Agent1 的 docstring 内容 merge 进去
3. 冒烟：`py -m evaluation.runner --agent channel` 必须能执行（PARTIAL / PASS 皆可，只要不是 ImportError）
4. commit trailer `Signal: OPTION-2-REBASE-FIXED`
5. 主 CLI 二次冒烟过即 APPROVED

---

## Option 1 · PHASE-2-BLOCKED-EXTERNAL（保持）
Option 3 · 驳回（保持）

---

## Follow-up

- Agent1 commit message 声称的 "冒烟: py -m evaluation.runner --agent channel" 与实测不符——**真 bug 不是 lint 瑕疵，是交付质量**。主 CLI 侧会在下一批 onboarding 里加一条"冒烟命令必须在提交分支上实测过"的软规则
- `chore/agent3-lint-cleanup` 一样是从 l0-infra 独立分支，fast-forward 就能合并；Agent1 下次可参考这个模式
