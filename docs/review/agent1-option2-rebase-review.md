# Agent1 Option 2 Rebase Review

**日期**：2026-04-19
**reviewer**：主 CLI
**worktree**：`D:/claude code/demo-agent1` · branch `feat/agent1-productize`
**HEAD**：`e69244f`
**Signal**：`AGENT1-OPTION2-READY-FOR-REVIEW`
**Onboarding**：`docs/onboarding/agent1-option2-rebase.md`
**依据**：A-007 / A-008(.A + 批量矩阵) / A-009(扩展矩阵)

## Verdict
**APPROVED**

核心 DoD 全绿、R-A/R-B 全合规、授权矩阵解法正确；两处 PARTIAL 灰区（`evaluation/runner/__init__.py` docstring add-only / `docs/handoff/decisions-log.md` dedup 式删除）未越出 A-008/A-009 语义意图，归入 Gap 而非 REJECTED。

## DoD 对账（逐条）
| 条目 | 状态 | 证据 |
|---|---|---|
| rebase 到 `de1b6b5` 之后 tip | OK | fddb1c6 commit message "Rebased onto upstream/chore/l0-infra"；`git log 0d7d35f..fddb1c6` = 18 replay |
| `py -m evaluation.runner --agent channel` = PARTIAL | OK | 实测 stdout：verdict=PARTIAL，common 5/5 OK，domain 3/5 OK + 2 N/A（manual） |
| `py -m pytest agent_channel/ -q` 29 passed | OK | 实测 `29 passed in 5.29s` |
| adapter `@register_evaluator("channel")` 挂进 registry | OK | `evaluation/runner/adapters/agent1_channel.py:150` |
| `--list` 包含 channel | OK | 实测 stdout = `channel\nreport` |
| red-line `halluc ≤ 0.01` | OK | 0.0000（实测 + 1_20260419.yaml L16） |
| red-line `evidence ≥ 0.95` | OK | 1.0000（实测 + 1_20260419.yaml L15） |
| red-line `task_completion ≥ 0.95` | OK | 1.0000（实测 + 1_20260419.yaml L18） |
| baseline 首跑落盘 | OK | `evaluation/results/1_20260419.yaml` verdict=PASS |
| Option 4 handoff contract 8 passed 不倒退 | OK | 实测 `8 passed in 0.51s` |
| 红区零触碰 | OK | `git diff 0d7d35f..fddb1c6 -- shared/ docs/contracts/ api_server.py agent_*/api/ base_evaluator.py registry.py cli.py __main__.py` = 空 |

## 硬规则对账
| 规则 | 状态 | 说明 |
|---|---|---|
| R-A smoke-must-test（fddb1c6 声称的 4 条） | OK | 时序 fddb1c6(14:28) → 3484e96(14:29) → e69244f(14:30) 递增；runner 产物 `evaluation/results/2026-04-19/channel_3eac7eaa.json` 存在；本 reviewer 在 HEAD=e69244f 重跑 4 条全绿（红线一致） |
| R-B 一 commit 一 Signal | OK | d525d92 / 3412878 / 3eac7ea / fddb1c6 / 3484e96 / e69244f 每条 trailer 只 1 个 `Signal:`（实测 `grep -c` = 1×6） |
| A-007 C（agent_channel/__init__.py） | OK | `agent_channel/__init__.py:1-22`：保 docstring 主体，仅首行 `# -*- coding: utf-8 -*-` 保留——等价于 "C 合并版主体"；工具域 4 子域齐（L9-14） |
| A-008.A A（agent1_channel.yaml） | OK | `evaluation/agent1_channel.yaml` 完整保留 scenarios + general_metrics + specialized_metrics（含 signal_diversity≥2 硬闸 L87-91），同时折叠 upstream `baseline:{last_run, commit}` L121-124 |
| A-008 批量矩阵 runner framework | PARTIAL | `evaluation/runner/__init__.py` 额外加 2 行 Phase B docstring（fddb1c6 diff）；onboarding 红区枚举 `base_evaluator.py/registry.py/cli.py/__main__.py` 未含 `__init__.py`，且改动是 add-only 注释无语义 —— 未破坏 framework，记灰区 |
| A-009 A（.gitignore 两边并存） | OK | `.gitignore:64` 保 upstream `evaluation/results/**/*.json`，`.gitignore:66` 从 `!1_20260418.yaml` 泛化为 `!1_*.yaml`（3484e96 commit message L30-31 显式声明泛化） |

## 越规审计（spot-check 5 选 5）
1. **`agent_channel/__init__.py`** — A-007 C 正确（docstring 保、coding 行保）。合规。
2. **`evaluation/agent1_channel.yaml`** — A-008.A A 正确。合规。
3. **`.gitignore`** — A-009 A add-only 两边并存；3484e96 的 `1_20260418.yaml → 1_*.yaml` 泛化是 commit message 明示的治理性 add-only 变更，合规。
4. **`evaluation/runner/__init__.py` / `adapters/__init__.py`** — A-008 要求"保 upstream framework 版 + 合并 agent1 adapter"；worker 在 `__init__.py` 加了 2 行 Phase B 注释（非删除、非改接口），合并 adapter 走新文件 `adapters/agent1_channel.py`。**灰区**：onboarding 红区未列 `__init__.py` 但精神上 `evaluation/runner/**` 一刀切更稳。
5. **`docs/handoff/decisions-log.md`** — fddb1c6 对该文件有 **127 行纯删除**（worker 自己 Q-008/Q-009 worker-only 块丢弃，保 upstream 主 CLI 正式 A-007/A-008/A-009）。A-008 矩阵 `docs/{onboarding,review,progress}/**` 未列 `docs/handoff/`，且语义上是"非 add-only"——按 A-009 兜底本应 abort + Q。**灰区**：但效果是两端收敛到主 CLI 权威版（A-NNN 形态），未引入幻觉、未篡改主 CLI 决策内容，故不上升 REJECTED，记 Gap。

**结论**：无"自造解法/曲解 A-NNN"的硬越规；2 处 PARTIAL 灰区属 onboarding 红区列表不够穷尽造成的协议盲点，应在下批 onboarding 堵上。

## Top 3 Gap（Phase 1 锚点）
1. **Framework init 与 docs/handoff 在红区矩阵里是盲点** — `evaluation/runner/__init__.py` 被 worker 加注释、`docs/handoff/decisions-log.md` 被 worker dedup，两处都滑出现有矩阵。Phase 1 onboarding 需显式声明 "`evaluation/runner/**/__init__.py` 与 `docs/handoff/decisions-log.md` 归主 CLI 唯一写"，worker 遇冲突**只许保 upstream 版 + abort**，删除行为（即使是丢自己的）必须 Q。
2. **双配置形态（legacy + framework）并存是短期债** — `evaluation/agent1_channel.yaml` 同时挂 `metrics.common/domain`（runner 用）和 `general_metrics/specialized_metrics`（scripts/eval_run.py 用），两套指标定义重复、阈值不同（evidence 0.95 vs 0.90；completeness 0.80 vs 1.0）。Phase 1 需收敛到 runner `metrics.*` 单一源，`scripts/eval_run.py` 或废或转壳。
3. **`candidate_relevance_at_top10` 长期 manual stub** — domain 2/5 N/A（`source_url_reachable_rate` 因 mock 豁免、`candidate_relevance` 等人工回录）。`score_from_recording` 是 `NotImplementedError` stub（adapter L~250），相关性指标空白 = Phase 1 还有一半评估未落地。需要主 CLI 触发"人工抽样回录流程"或接受在 Phase 2 Batch 2 里闭环。

## 亮点
- R-A 时序完美贴合 onboarding "rebase → smoke → baseline → emit" 的四步顺序，三个关键 commit 间隔 1 分钟内。
- Q-007/Q-008/Q-009 三次连续 abort 在未被授权场景下严格按 "NEED-DECISION" 停下问，**非但没有过度代偿，反而暴露了主 CLI 矩阵过窄的协议盲点**——A-008 → A-009 扩展矩阵是被 worker 正确纪律倒逼出的治理升级。
- `1_20260419.yaml` baseline verdict=PASS + runner 产物 `channel_3eac7eaa.json` 双落盘，runner / legacy 两路交叉印证红线。
- commit message 里显式列 "audit trail for A-008 spot-check" 5 项（e69244f），主动供审——工程透明度达标。

## Required Actions
无（APPROVED）。Phase 1 onboarding 起草时必须吸收 Top 3 Gap：
- Gap 1 → 扩 onboarding 红区矩阵字面枚举 `evaluation/runner/**/__init__.py` + `docs/handoff/decisions-log.md`
- Gap 2 → 在 Phase 1 DoD 加"yaml 单源收敛"条目
- Gap 3 → 由主 CLI 决定是否本轮触发人工抽样回录，或推 Phase 2 Batch 2
