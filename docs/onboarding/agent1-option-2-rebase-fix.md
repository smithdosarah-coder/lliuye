# Agent1 Option 2 · rebase fix（补发）

**状态**：CONDITIONAL → 待 worker 修复
**发布日期**：2026-04-19
**前置**：`docs/review/agent1-phase-2-batch-1-review.md`（Phase 2 Batch 1 review 裁决）
**Signal 入口**：`PHASE-2-BATCH-1-CONDITIONAL-APPROVE`

---

## 为什么补发这份

Phase 2 Batch 1 review 里 Option 2（evaluation adapter + sampling CSV）verdict 是 **CONDITIONAL-APPROVE**：

- Adapter 代码本身符合 onboarding 规范 ✅
- `evaluation/manual/sampling_20260419.csv` 生成可跑 ✅
- 但 `py -m evaluation.runner --agent channel` 报 `No module named evaluation.runner.__main__`
- 根因：`feat/agent1-productize` merge base 停在 `e9eeaf0`，未带上主 CLI 最新 `705326d feat(eval): runner framework` 提供的 schemas / base_evaluator / registry / cli / __main__

commit `f2bee8c` 的 message 声称该冒烟命令能跑，实测不通——属**交付未闭环**，必须先修才能合并主干。

---

## Worker 修复动作（S 量级，半小时内）

1. 重开 agent1 CLI 窗口（走 AGENT_IDENTITY.md 标准 resume）
2. `git fetch upstream && git log upstream/chore/l0-infra --oneline -10` 确认看到 `705326d` / `de1b6b5` / `3febf0f`
3. `git rebase upstream/chore/l0-infra`
4. **预期冲突**：`evaluation/runner/__init__.py` —— Agent1 自建的 docstring 版本 vs 主 CLI `705326d` 的 framework 版本
   - **保留主 CLI 版（framework 完整）**
   - Agent1 docstring 若有独特内容可合并到 `evaluation/runner/adapters/__init__.py`
5. 冒烟回归：
   ```bash
   py -m evaluation.runner --list                # 必须列出 "channel"
   py -m evaluation.runner --agent channel       # 必须不再 ImportError
   py -m pytest agent_channel/ -q                # 必须 29/29 保持绿
   ```
6. commit trailer `Signal: OPTION-2-REBASE-FIXED`
7. 主 CLI 收到信号后二验 → 满足即 `PHASE-2-BATCH-1-APPROVED`

---

## 边界（继续守）

- ❌ 不碰 `shared/` / `docs/contracts/`（A-004 §〇 仍生效）
- ❌ 不改 Option 4（8/8 已 APPROVED）
- ❌ 不补 Option 2 的人工回录侧（仍 on hold 等用户触发）
- ✅ 只做 rebase + 冲突解决 + 冒烟回归

---

## 新增硬规则（从此批次起生效）

**冒烟命令必须在提交分支 checkout 后实测过再写入 commit message。**

具体：
- commit body / message 里写 `冒烟: <cmd>` 或 `python -m ...` 任何命令示例前，必须在**当前分支当前提交状态下**实测能跑
- 若依赖主 CLI 上游尚未到达的 commit，必须先 rebase 再 commit（不得 "假设 rebase 后能跑" 就入 commit message）
- 违反 → review 直接 CONDITIONAL，要求重建 commit（而非简单补救）

**Why**：commit message 里的冒烟命令是给后人（review / 审计 / 未来 worker）用的。假设"应该能跑"而非"实测跑过"是幻觉。

**How to apply**：worker 写 commit message 时自查一遍：文档里声称的命令，**当前工作树是否已经至少跑过一次**？如果没有，先跑。

该规则下一批次起所有 worker 执行。

---

## ACK 协议

1. Worker 重开窗口读到本文件后，commit trailer `Signal: REBASE-FIX-ACK`（可选，若嫌繁琐合并到修复 commit 里也行）
2. 修复完 `Signal: OPTION-2-REBASE-FIXED`
3. 主 CLI 二验通过 `Signal: PHASE-2-BATCH-1-APPROVED`
