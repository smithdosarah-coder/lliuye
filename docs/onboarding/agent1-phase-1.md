# Agent1 获客 · Phase 1 Productize Onboarding

**对应 worktree**：`D:\claude code\demo-agent1`（`feat/agent1-productize`）
**发布日期**：2026-04-19
**前置**：已读 `AGENT_IDENTITY.md` + `CLAUDE.md` + 本文 + `docs/review/agent1-option2-rebase-review.md` + `docs/review/agent1-phase-2-batch-1-review.md`
**目标**：把 Agent1 从「82% / Phase 2 Batch 1 CONDITIONAL」推到「Phase 1 productize APPROVED」（scorecard ≥ 85%）。

---

## 背景（3 行速读）

Option 2 Rebase 刚 APPROVED（`6523777` / Signal `AGENT1-OPTION2-APPROVED`），但 review 明确 Top 3 Gap 是 Phase 1 强制吸收项：red-zone 矩阵盲点（runner `__init__.py` + `decisions-log.md`）、yaml 双配置形态（runner `metrics.*` vs legacy `general/specialized_metrics`）、`candidate_relevance_at_top10` 人工回录空白。本 Phase 1 的硬任务就是把这三个 Gap 合拢 + 对齐 bank delivery DoD L0~L3 形态，让 Agent1 获得「可交付银行内网」的 productize 验收。

---

## 1. 范围 & 不做什么

### productize 定义（对齐 `memory/project_bank_delivery_dod.md`）

| 层 | 本 Phase 交付项 | 当前状态 |
|---|---|---|
| L0 最低起跑线 | handoff contract 8/8 + full suite 29/29 不倒退 | ✅ Option 2 已达成 |
| L1 功能完整 | 信号驱动搜索 + look-alike + 产品推荐（已 v4.0） | ✅ 不动 |
| L2 可审计可追溯 | 评估协议红区收敛 + yaml 单源 + 抽样回录闭环 | ❌ 本 Phase 做 |
| L3 可量化可验收 | runner `--agent channel` = PASS（不是 PARTIAL） | ❌ 本 Phase 做 |

### 不做什么（明确排除，防 scope creep）

- ❌ **不做 autopilot**：候选清单仍需人工复核，不下自动授信/放款决策
- ❌ **不做 SFT / fine-tune**：走 few-shot 注入 + feedback loop 飞轮（CLAUDE.md §6）
- ❌ **不做 cross-agent 编排**：Agent1 边界在「产出候选清单 + handoff payload」，不触发 Agent3 决策
- ❌ **不做前端 Shell 接入**：等前端 Stage 3 workspace 解耦完再接，本 Phase 只保 API 形态
- ❌ **不做 Option 1（Tavily 生产 key）**：等用户外部触发，与本 Phase 解耦
- ❌ **不做新工具域**：工具按现有 4 子域（信号搜索 / 企业画像 / 匹配评分 / 产品推荐）组织，不新增

---

## 2. 前置条件

- 主 CLI HEAD：`6523777`（`AGENT1-OPTION2-APPROVED`）之后；可 `git fetch upstream && git log upstream/chore/l0-infra --oneline -5` 确认
- worker 起点：`feat/agent1-productize` @ `37ba301`（上次 window-close commit）
- `git fetch upstream && git rebase upstream/chore/l0-infra` 拿到本 onboarding + 主干最新，再开工
- 红线闸门基线（Option 2 已验证）：halluc 0.0000 / evidence 1.0000 / task 1.0000 / diversity_pass 0.8+ — 本 Phase 不许倒退

---

## 3. Task 清单（4 Task，预计 1.5-2.5 工时）

### Task A · 评估协议红区矩阵堵漏（Gap 1）

**goal**：把 `evaluation/runner/**/__init__.py` 与 `docs/handoff/decisions-log.md` 显式写进红区字面枚举，堵住 Option 2 rebase 暴露的两个灰区盲点。

**modules**：
- 新写 `docs/handoff/shared-change-protocol.md`（主干尚不存在，本 Phase 由 worker 起草，主 CLI review 时若认为应主 CLI 唯一写则会 reject 此文件并改为 `docs/progress/agent1-phase-1-redzone-gap.md`；worker 起草前先通过 Q-012 确认归属）
- 或直接扩 `evaluation/agent1_channel.yaml` 顶部注释块声明红区（fallback 方案，如 Q-012 不允许 worker 写 handoff 文档）

**deliverables**：
- 字面枚举 6 条红区（§5 详列）
- 说明「worker 遇冲突**只许保 upstream + abort + Q**」— 任何 dedup / 删除（即使是删自己先前的 commit 内容）必须先发 Q，拿 A-NNN 后再动
- 文中给反例：引用 fddb1c6 对 `__init__.py` add-only docstring、e69244f 对 `decisions-log.md` 127 行 dedup 删除——这两次都是灰区，下次再犯直接 REJECTED

**DoD**：
- [ ] 文档 diff 显式列出新红区 6 条（`grep -n "evaluation/runner/\*\*/__init__.py\|decisions-log.md" <file>` 命中 ≥ 1）
- [ ] 模拟冲突演练：worker 在本地创一个假分支，手工 fabricate 一次 `decisions-log.md` 的 remove-only 冲突，演示 `git rebase --abort` + Q 流程可完整走通（commit message 里贴演练命令输出）
- [ ] `git log --grep="Signal: NEED-DECISION"` 在 worker 分支上可检索到历史（Q-007/Q-008/Q-009 要能 trace）

---

### Task B · yaml 单源收敛（Gap 2）

**goal**：`evaluation/agent1_channel.yaml` 只保 runner 消费的 `metrics.common/domain`，彻底去掉 worker 分支上残留的 legacy `general_metrics/specialized_metrics` + scenarios 段。

**modules**：
- `evaluation/agent1_channel.yaml`（worker 分支上的版本——主干最新版见 `upstream/chore/l0-infra` 只有 `metrics.common/domain`；worker 分支上 A-008.A A 保了「完整型」，两套阈值共存）
- `scripts/eval_run.py`（worker 分支上如存在则处理；主干不存在）
- CI / README / 任何引 `scripts/eval_run.py` 的文档

**deliverables**：
- `evaluation/agent1_channel.yaml` 只剩 `metrics.common/domain` + `baseline`；移除 `scenarios` `general_metrics` `specialized_metrics`
- 若 worker 分支 `scripts/eval_run.py` 仍需保留 → 改薄壳转调 `evaluation.runner.cli`；若已无消费方 → 删除 + 清掉引用
- `grep -rn "general_metrics\|specialized_metrics" evaluation/` = 0 行
- 把原 `signal_diversity ≥ 2` 硬闸的**等价语义**搬到 runner `metrics.domain` 的 `signal_diversity` / `signal_diversity_pass` 里（runner framework 已支持）——不许丢硬闸

**DoD**：
- [ ] `py -m evaluation.runner --agent channel` verdict = **PASS**（不是 PARTIAL，common 5/5 + domain 5/5 全绿；`candidate_relevance_at_top10` 若走 Task C D 方案可保 N/A 但必须显式标 `pending: Phase-2-Batch-2`）
- [ ] `grep -rn "general_metrics\|specialized_metrics" evaluation/` 输出 0
- [ ] `evaluation/agent1_channel.yaml` 仅含 `agent / version / updated / metrics.common / metrics.domain / baseline` 六个顶层 key
- [ ] `scripts/eval_run.py` 要么删、要么是 ≤ 20 行的壳转调；`grep -rn "scripts/eval_run" .` 无残留引用
- [ ] 红线闸门不倒退：halluc ≤ 0.01 / evidence ≥ 0.95 / task ≥ 0.95 / diversity ≥ 2.0 / diversity_pass ≥ 0.80

---

### Task C · `candidate_relevance_at_top10` 人工抽样回录（Gap 3）

**goal**：把 Option 2 里长期 `NotImplementedError` 的 `score_from_recording` stub 落地成可跑闭环，让 domain 指标从 3/5 绿升级到 4/5 或 5/5。

**两选项，worker ACK 时明示选 D 还是 skip**：

#### D 方案 · 本 Phase 触发人工回录

**modules**：
- `evaluation/runner/adapters/agent1_channel.py`（补 `score_from_recording` 实现）
- `evaluation/manual/1_relevance_YYYYMMDD.yaml`（人工标注模板，由 worker 起草 schema）
- `scripts/sample_for_manual.py`（或复用 Option 2 已有 `generate --top-n 5` 子命令；抽样规则：从最近一次 baseline 产物里取 top-10 候选 × 3 个种子画像，共 30 条）

**deliverables**：
- 抽样规则书面化（种子画像怎么选、top-N 怎么定、去重策略）
- 人工标注 yaml schema（字段至少含 `candidate_id / seed_profile_id / relevance_score{1-5} / rationale / reviewer / date`）
- adapter 里 `score_from_recording` 消费 yaml → 输出 `candidate_relevance_at_top10` 数值
- `evaluation/manual/1_relevance_20260419.yaml` 至少填 10 行真实数据（worker 自己先过一版作为 bootstrap 基线，后续产品侧再找业务方二审）
- 更新 `evaluation/agent1_channel.yaml` 的 `baseline` 字段引用最新产物路径

**DoD（D 方案）**：
- [ ] `py -m evaluation.runner --agent channel` 中 `candidate_relevance_at_top10` 有实数值（非 N/A）
- [ ] `evaluation/manual/1_relevance_20260419.yaml` 实存且 ≥ 10 行 annotation
- [ ] adapter `score_from_recording` 无 `NotImplementedError`，有单测 ≥ 1 条

#### skip 方案 · 推 Phase 2 Batch 2

**modules**：
- `evaluation/runner/adapters/agent1_channel.py`（显式 skip 分支）
- `evaluation/agent1_channel.yaml`（baseline 段加 `pending`）

**deliverables**：
- adapter 在 `candidate_relevance_at_top10` 分支显式 return `MetricResult(value=None, method="manual", note="pending Phase-2-Batch-2 manual sampling")`，不再 raise
- yaml `baseline` 段加 `pending_metrics: [candidate_relevance_at_top10]` + `pending_reason: "Phase-2-Batch-2 human review"`
- runner 产物 `evaluation/results/1_YYYYMMDD.yaml` 该指标行带 `note: pending`

**DoD（skip 方案）**：
- [ ] runner 输出该指标 = N/A，但**带显式 note 而非 raise**
- [ ] yaml `pending_metrics` 字段存在
- [ ] verdict 仍可为 PASS（4/5 domain 绿 + 1/5 pending 不算失败）— 这点要与 `base_evaluator.py` 的 verdict 逻辑对齐，如 framework 现状判 PARTIAL 则先 Q-012 问主 CLI 是否放行

---

### Task D · 主 CLI 待决（worker ACK 时问）

**主 CLI 待定，worker ACK 时问**。候选两个方向：

- **D1 · Tavily production ingress**（参考 Phase 2 draft Option 1）：真生产 key 接入 + 降级策略 + 配额监控。依赖合规批文。
- **D2 · Feedback loop 端到端**（参考 Phase 2 draft Option 3）：`/api/feedback` 收审贷员对候选清单的反馈，写 `data/feedback/YYYY-MM-DD.jsonl`，跑一次 few-shot 回注 demo。对齐 CLAUDE.md §6 数据飞轮第 3/4 环。

worker ACK commit 时用 `## [Q-012]` 问主 CLI 选 D1 还是 D2，或推 Phase 2 Batch 2。在 A-012 裁决前**不要**动 Task D。

---

## 4. 红区 & 硬规则

### 红区字面枚举（含 Gap 1 修补）

❌ 以下路径 worker **不得改动**；遇冲突只许保 upstream + abort + Q：

- `shared/**`
- `docs/contracts/**`
- `api_server.py`
- `agent_*/api/**`
- **新增**（Option 2 rebase 暴露的盲点）：
  - `evaluation/runner/__init__.py`
  - `evaluation/runner/adapters/__init__.py`
  - `evaluation/runner/base_evaluator.py`
  - `evaluation/runner/registry.py`
  - `evaluation/runner/cli.py`
  - `evaluation/runner/__main__.py`
  - `docs/handoff/decisions-log.md`

**灰区澄清**：Option 2 对 `evaluation/runner/__init__.py` 加 2 行 docstring（add-only）、对 `decisions-log.md` 127 行 dedup 删除——两次都判 PARTIAL。本 Phase 起这两个路径都归主 CLI 唯一写，**add-only 也不行**，删/加/注释都必须先 Q。

允许 worker 动：

- ✅ `evaluation/runner/adapters/agent1_channel.py`
- ✅ `evaluation/agent1_channel.yaml`
- ✅ `evaluation/results/1_*.yaml`
- ✅ `evaluation/manual/*.yaml / *.csv`
- ✅ `agent_channel/**`（工具域内部，不含对外 API）
- ✅ `agent_channel/tests/**`
- ✅ `docs/progress/agent1-phase-1-*.md`（worker 自己的进度文档）
- ✅ `scripts/eval_run.py`（若存在；可删可改薄壳）

### 硬规则

- **R-A smoke-must-test**：每 Task commit message 声称跑过的冒烟命令，必须在**提交分支当前 HEAD** 上实测过（A-006 新规）。违反 → review 自动 CONDITIONAL
- **R-B 一 commit 一 Signal**：`git log --format='%b' HEAD` 自检 trailer 数量 = 1
- **R-C cherry-pick amend trailer**：本 Phase worker 不会 cherry-pick，但若真遇到则必须 amend 从 worker signal 改主 CLI 视角
- **Signal await semantics**（`memory/feedback_signal_await_semantics.md`）：worker 每个 `READY-FOR-REVIEW` / `NEED-DECISION` 都是**隐式 await-proceed gate**，必须停下等主 CLI GO；不许自己一路推到底
- **无基线不改码**（CLAUDE.md §5.2）：本 Phase 质量类动作都要对标 runner 产物 `evaluation/results/1_*.yaml` 里的数字，不许拍脑袋

---

## 5. Signal 流程

| 时点 | Signal |
|---|---|
| 读完 onboarding | `AGENT1-PHASE-1-ACK` |
| Task A 完成 | `AGENT1-PHASE-1-TASK-A-DONE` |
| Task B 完成 | `AGENT1-PHASE-1-TASK-B-DONE` |
| Task C 完成 | `AGENT1-PHASE-1-TASK-C-DONE` |
| Task D 完成（若主 CLI 批了 D1/D2） | `AGENT1-PHASE-1-TASK-D-DONE` |
| 全部 ready | `AGENT1-PHASE-1-READY-FOR-REVIEW` |
| Review 通过收工 | `WINDOW-CLOSED-CLEAN` |
| 有疑问 | `NEED-DECISION Q-NNN`（下一个可用 **Q-012**） |

ACK 命令：

```bash
git commit --allow-empty -m "ack(agent1): Phase 1 onboarding absorbed" -m "" -m "Signal: AGENT1-PHASE-1-ACK"
```

ACK commit 里顺手提一句 Task C 选 D 还是 skip、Task D 提问（或等主 CLI 后续 A-012）。

---

## 6. DoD 汇总 / 评估基线预期

### 全 Phase 终态

- [ ] runner `py -m evaluation.runner --agent channel` verdict = **PASS**（这是 Phase 2 Batch 1 CONDITIONAL 升 APPROVED 的硬条件；不是 PARTIAL）
- [ ] 红线闸门不倒退：
  - `hallucination_rate ≤ 0.01`
  - `evidence_rate ≥ 0.95`
  - `task_completion_rate ≥ 0.95`
  - `signal_diversity ≥ 2.0`
  - `signal_diversity_pass ≥ 0.80`
- [ ] `py -m pytest agent_channel/ -q` = 29 passed（不倒退）
- [ ] `py -m pytest agent_channel/tests/test_handoff_contract.py -v` = 8 passed（Option 4 成果）
- [ ] `evaluation/results/1_YYYYMMDD.yaml` 新 baseline 落盘，verdict = PASS
- [ ] scorecard ≥ 85%（主 CLI review 更新 `docs/scorecard/GLOBAL.md`）

### 任一红线不过

→ 写 `docs/progress/agent1-phase-1-gap.md` 记录 gap 原因，**不要**强改 adapter / fixture 让指标达标（CLAUDE.md §12）。

---

## 7. 时限 & 推进顺序

- 建议 1.5-2.5 工时（不含 Task D；Task C 选 D 方案则 +0.5-1 工时人工回录）
- 顺序：**A → B → C → (等 A-012) → D → READY-FOR-REVIEW**
- Task A / B 无依赖可并行起草 commit；Task C 依赖 B 的 yaml 终态
- 每 Task DONE 后主 CLI 可能发 mid-review 指令，worker 停等 GO 再进下一个 Task

---

## 8. Q/A

疑问 → `docs/handoff/decisions-log.md` append `## [Q-012]`（或后续 Q-013 / Q-014）→ trailer `Signal: NEED-DECISION Q-NNN` → 等主 CLI append `### [A-NNN]`。

**特别注意**：
- 红区冲突 **立即 abort + Q**，任何"优化 / dedup / add-only" 都不自决
- Task C 选 D 还是 skip 可在 ACK commit 里顺便问 Q-012
- Task D 必须等 A-NNN 才动

---

## 附：参考文件速查

- Review 依据：`docs/review/agent1-option2-rebase-review.md`（Top 3 Gap）/ `docs/review/agent1-phase-2-batch-1-review.md`
- 协议基线：`docs/handoff/decisions-log.md` A-006（R-A/B/C 硬规则）/ A-008 / A-009（红区矩阵历史版本）
- Runner framework：`evaluation/runner/base_evaluator.py` / `registry.py` / `cli.py` / `__main__.py`（红区，只读）
- Adapter 参考：`evaluation/runner/adapters/agent6_report.py`（Phase A 模式）
- DoD 定义：`docs/scorecard/definition-of-done.md` v1.0 / `memory/project_bank_delivery_dod.md`
- 全局看板：`docs/scorecard/GLOBAL.md`
