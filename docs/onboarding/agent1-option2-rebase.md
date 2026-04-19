# Agent1 · Option 2 Rebase 解锁 Onboarding

**对应 worktree**：`D:\claude code\demo-agent1`（`feat/agent1-productize`）
**发布日期**：2026-04-19
**前置**：已读 `AGENT_IDENTITY.md` + `CLAUDE.md` + 本文 + `docs/review/agent1-phase-2-batch-1-review.md`
**目标**：解 Phase 2 Batch 1 CONDITIONAL-APPROVE 的条件，让 Agent1 的 `evaluation/runner/adapters/agent1_channel.py` 挂进主 CLI `de1b6b5` framework 的 registry，`py -m evaluation.runner --agent channel` 跑通。

---

## 背景（3 行速读）

Batch 1 review verdict = CONDITIONAL-APPROVE。Option 4 独立 APPROVED，Option 2 adapter 代码规范对但跑不起来——因为 `feat/agent1-productize` merge base 停在 `e9eeaf0`，未 rebase 到主 CLI `de1b6b5`（runner framework 上线 commit），导致 `evaluation.runner.__main__` 等文件缺失。修复工作量 S。完整条件见 `docs/review/agent1-phase-2-batch-1-review.md` §Required actions。

---

## Task · Rebase + 冲突处理 + 冒烟（0.5-1 天）

### 步骤

1. 在 worktree 里拉主 CLI 最新
   ```bash
   cd "D:/claude code/demo-agent1"
   git fetch upstream
   git log --oneline upstream/chore/l0-infra -10    # 确认能看到 de1b6b5 / 705326d / 94c04f5 等
   ```

2. Rebase
   ```bash
   git rebase upstream/chore/l0-infra
   ```

3. 预期冲突：`evaluation/runner/__init__.py`
   - Agent1 自建版 vs 主 CLI framework 版
   - **保留主 CLI 版本**（framework 完整），把 Agent1 原 docstring 里有用的信息 merge 进主 CLI 版本顶部
   - 不要反向——主 CLI 版本是 `@register_evaluator` / `BaseEvaluator` 挂点，覆盖即 break

4. 其他可能冲突：极少；如遇到 `evaluation/results/.gitignore` 这类，保留主 CLI 版（`e9eeaf0` 已扩展）

5. 冒烟（必须实测过才 commit）
   ```bash
   py -m evaluation.runner --list                     # 预期包含 "channel"
   py -m evaluation.runner --agent channel            # 预期 PARTIAL 或 PASS，不能是 ImportError
   py -m pytest agent_channel/ -q                     # 预期 29 passed（不能倒退）
   py -m pytest agent_channel/tests/test_handoff_contract.py -v   # 预期 8 passed
   ```

6. 如果 adapter 需要按新 framework 重对齐（看 `base_evaluator.py` 签名变化）
   - 参考范式：`evaluation/runner/adapters/agent6_report.py`（Phase A）+ `evaluation/runner/adapters/agent3_credit.py`（Phase B）
   - 保留原有 sampling CSV 生成器逻辑（`generate --top-n 5` 子命令）不变

### DoD

- [ ] `git log --oneline` 能看到 `feat/agent1-productize` 已 rebase 到包含 `de1b6b5` 之后的 tip
- [ ] `py -m evaluation.runner --agent channel` 跑出 PARTIAL 或 PASS（无 ImportError / no module named）
- [ ] `py -m pytest agent_channel/ -q` 仍 29 passed（不能倒退 Option 4 Batch 1 成果）
- [ ] `evaluation/runner/adapters/agent1_channel.py` 的 `@register_evaluator("channel")` 挂进 registry
- [ ] `py -m evaluation.runner --list` 输出包含 `channel`
- [ ] **红线闸门**（对齐 CLAUDE.md §5.1）：
  - `hallucination_rate <= 0.01` ✅
  - `evidence_rate >= 0.95` ✅（Agent1 evidence 来源：CompanyProfile 信号时间线）
  - `task_completion_rate >= 0.95` ✅
  - 任一不过 → 写 `docs/progress/agent1-option2-rebase-gap.md`，**不要**强改 adapter / fixture 让指标达标

---

## 红区边界

- ❌ `shared/` / `docs/contracts/` —— A-004 §〇
- ❌ 其他 agent_* 目录
- ❌ `web/` 前端
- ❌ `evaluation/runner/` framework 核心（只能读、不能改 `base_evaluator.py` / `registry.py` / `cli.py` / `__main__.py`）
- ❌ **不做 Option 1（Tavily 生产 key）**—— 等用户外部触发
- ❌ **不做 Option 2 回录侧**（`score_from_recording` 保留 NotImplementedError stub）—— 等人工抽样流程启动
- ❌ **不做 Phase 2 Batch 2 新功能** —— 本批次只解 rebase 债

允许：
- ✅ `evaluation/runner/adapters/agent1_channel.py` 修改（按新 framework 对齐）
- ✅ `evaluation/agent1_channel.yaml` 修改（补 baseline 字段）
- ✅ `evaluation/results/1_YYYYMMDD.yaml` 落盘（baseline 首跑）
- ✅ `evaluation/manual/sampling_YYYYMMDD.csv` 更新（重跑 top-n 采样）
- ✅ `docs/progress/agent1-option2-rebase-gap.md`（如红线不过）

---

## Commit / Signal

R-A/B/C 硬规则同其他 agent。

### Milestone

| 时点 | Signal |
|---|---|
| 读完 onboarding | `AGENT1-OPTION2-REBASE-ACK` |
| Rebase + 冲突解决 + 冒烟通过 | `OPTION-2-REBASE-FIXED` |
| Baseline 首跑落盘 + 红线全绿 | `AGENT1-OPTION2-BASELINE-VALIDATED` |
| Ready for review | `AGENT1-OPTION2-READY-FOR-REVIEW` |
| Review 通过收工 | `WINDOW-CLOSED-CLEAN` |

### 主 CLI review 后下一步

Batch 1 CONDITIONAL → APPROVED 升级 → Agent1 完整度矩阵从 78% 抬到 ~82%，并下发 Phase 2 Batch 2（等前端 Stage 2 落地后启动，避免 UI 双写）。

---

## Q/A

疑问 → `docs/handoff/decisions-log.md` `Q-NNN` → trailer `Signal: Q-NNN-RAISED`。

**特别注意**：如果 rebase 遇到非 `evaluation/runner/__init__.py` 的冲突（比如 `agent_channel/*` 内部或 `shared/*`）—— **立即停止，写 Q-NNN 问主 CLI**，不要强推。

---

## ACK

```bash
git commit --allow-empty -m "ack(agent1): Option 2 rebase onboarding absorbed" -m "" -m "Signal: AGENT1-OPTION2-REBASE-ACK"
```
