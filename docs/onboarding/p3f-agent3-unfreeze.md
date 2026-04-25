# Phase 3-Final · 轨 2 · Agent3 解冻 + 合流 Onboarding

**状态**：Phase 3-Final GO（待 user dispatch）
**发布日期**：2026-04-25
**Signal 入口（ACK）**：`PHASE-3-FINAL-T2-ACK`
**前置**：commit `4f2132e ORCHESTRATOR-HANDOFF-PHASE-3-FINAL-PLANNED` + Q-032（Phase 3-F 总规划 · 推翻 Q-031 档 2/3 冻结）
**参照决策**：Q-030（Batch 2 closeout） / Q-031（Mesh 大清理 · 已被 Q-032 部分推翻） / Q-032（Phase 3-F 8 轨规划） + `docs/handoff/session-2026-04-25-phase-3-final-handoff.md` + `docs/scorecard/dod-current-status-2026-04-24.md`
**worker 建议**：新建 worktree `code-agent3-unfreeze`（fork from `feat/agent3-productize` · 不在原 demo-agent3 worktree 直接动）
**Final commit signal**：`READY-FOR-AGENT3-UNFREEZE-REVIEW`
**中间 signal 链**：`AGENT3-UNFREEZE-ACK` → `AGENT3-REBASE-CLEAN` → `READY-FOR-AGENT3-UNFREEZE-REVIEW`

---

## 1. 背景与目标

### 1.1 DoD 当前打分（post-Batch 2）

| 层 | Batch 2 后 | Phase 3-F 目标 | 本轨贡献 |
|---|---|---|---|
| L1 Demo 完整 | 60% | **90%** | L1-3 Agent3 RiskRadar · L1-4 Agent3 docx 导出 · L1-11 Agent6→Agent3 handoff button |
| L2 金融合规 | 75% | **95%** | L2-7 Agent3 reason_codes Top-5 · L2-8 Agent3 字典文件 |
| L3 客户 POC | 45% | **85%** | （间接 · agent3 evaluation 由 Batch 2 已合 baseline 锚定） |

**核心缺件**：`feat/agent3-productize` branch 上 11 commit 未合，含 5 条 🔴 极高价值（4 条解 DoD + 1 条 evaluation 已被 Batch 2 重做）+ 6 条 🟡 中价值（marker / refactor / L0 tests / rebase marker）。

### 1.2 本轨硬边界

只动 `agent_credit/` 业务代码 + `tests/agent_credit/` + 必要的 `evaluation/runner/adapters/agent3_credit.py` 冲突解。**不动**：`financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py`（红区）/ `web/`（前端归轨 4） / `v16_*.py` / `data/mock/` / `evaluation/runner/base_evaluator.py` / `cli.py`（A-024 路径规范）。

agent3 branch 的 evaluation 改动（`14a4a34` / `d221115`）**已被 Batch 2 evaluation 重做**（commit `c2776b4`）· 优先保 Batch 2 · 本轨只取 agent3 branch 的业务代码改动。

### 1.3 11 commit 归类（参照 handoff §2.2）

#### 🔴 极高价值 · 解 DoD（必合）
| SHA | commit | 解 DoD |
|---|---|---|
| `4107b16` | feat(agent_credit): L1-4/L2-15 local python-docx decision letter export | **L1-4** Agent3 docx 导出 · **L2-15** 客户数据本地处理 |
| `68985dc` | feat(agent_credit): L2-7/L2-8 standard reason codes — Top-5 derived per decision | **L2-7** Top-5 reason_codes · **L2-8** 字典文件 |
| `596283f` | feat(agent_credit): L1-3 RiskRadar thin wrapper dispatching 4-dim radar by segment | **L1-3** RiskRadar 雷达图 |
| `8f1a35c` | feat(agent_credit): L1-11 Agent6→Agent3 handoff button + 2 demo profiles | **L1-11** 跨 Agent handoff button |

#### 🟡 中价值 · 工程品质（合时谨慎处理）
| SHA | commit | 处理 |
|---|---|---|
| `14a4a34` | feat(evaluation): L3-1/L3-2 Agent3 baseline first run | **过期** · Batch 2 evaluation 已重做 · skip / 走 ours 策略 |
| `d221115` | feat(eval): Agent3 credit adapter (Phase B) — deterministic metrics online | **可能冲突** · Batch 2 已重写 adapter · 优先保 Batch 2 |
| `83cf560` | refactor(agent_credit): migrate severity to red/yellow/green, drop is_hard | schema refactor · 合 |
| `23737c4` | test(agent_credit): L0 self-check — 16 tests + ruff-clean | L0 tests · 合（Task B 复用） |
| `c101597` | chore(handoff): ack A-004 + Phase 1 APPROVED — rebase onto chore/l0-infra clean | rebase marker · 自动消解 |
| `d67576f` | chore(handoff): Phase 2 batch complete — ready for main CLI review | marker · 可 skip 或合 |
| `6c5820a` | window-close: Phase 2 Batch 1 approved | marker · branch tip |

### 1.4 关键 rebase 风险（main CLI 必读）

最后同步 main 是 `c101597`（Phase 1 APPROVED clean）· 期间 main 前进 Batch 1 + Batch 2。

**主要冲突面预测**（按风险降序）：

1. **`agent_credit/scoring_model_corporate.py`** —— Batch 1 code-urgent 改了 `_score_financial` 接 `financial_analyzer` 注入 · agent3 branch 的 reason_codes commit `68985dc` 也碰这文件 · **必须保留 Batch 1 的 financial_analyzer 注入**，叠加 agent3 的 reason_codes Top-5 派生逻辑
2. **`agent_credit/advisor_formatter.py`** —— Batch 1 code-urgent 改过（接 financial_analyzer 输出） · agent3 的 `4107b16`（docx 导出）和 `596283f`（RiskRadar）也可能碰 · 谨慎合
3. **`evaluation/runner/adapters/agent3_credit.py`** —— Batch 2 evaluation 重写过（real baseline + EV-12 cross-agent） · agent3 branch `d221115` 改动**优先丢弃** · 取 Batch 2 ours

---

## 2. Task 清单

### Task A · rebase origin/chore/l0-infra

**目标**：在新 `code-agent3-unfreeze` worktree 上把 `feat/agent3-productize` rebase 到 `origin/chore/l0-infra` 当前 tip（含 Batch 1 + Batch 2 全部改动 · HEAD = `4f2132e` 或之后）。

**步骤**：
1. `git worktree add ../code-agent3-unfreeze feat/agent3-productize`
2. `cd ../code-agent3-unfreeze && git fetch origin chore/l0-infra`
3. `git rebase origin/chore/l0-infra`
4. 解冲突时**逐 commit 处理**（11 commit 串行 · 不要 squash）：
   - **保留**：Batch 1 code-urgent 的 `_score_financial` + `financial_analyzer` 注入（`scoring_model_corporate.py`）
   - **保留**：Batch 1 code-urgent 的 `advisor_formatter.py` financial_analyzer 接线
   - **保留**：Batch 2 evaluation 已合的 `evaluation/runner/adapters/agent3_credit.py`（agent3 branch 的 evaluation 改动 `14a4a34` / `d221115` 走 `git checkout --ours` 或直接 skip）
   - **吸收**：agent3 branch 的 reason_codes Top-5 派生（`68985dc`） / docx 导出（`4107b16`） / RiskRadar wrapper（`596283f`） / handoff button（`8f1a35c`） / severity refactor（`83cf560`） / L0 tests（`23737c4`）
5. 冲突 > 4 文件 → 立即停手回 Q-033 askout · 主 CLI 裁决（不要硬解）

**约束**：
- rebase 过程中 11 commit 的原 SHA 会变 · 在 final commit body 附**新旧 SHA 对照表**（见 §2.4）
- 不动红区文件（`financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py`） · 任何冲突触及红区立即停手
- 不 git push · 主 CLI 统一合流

**完成信号**：`Signal: AGENT3-REBASE-CLEAN`

---

### Task B · pytest 全绿

**目标**：rebase 后跑 `pytest tests/agent_credit/ -v` 全绿（含 agent3 branch `23737c4` 带来的 16 个 L0 self-check tests + 既有 tests）。

**步骤**：
1. `pytest tests/agent_credit/ -v` · 期望 100% 通过
2. 如有 fail：
   - 是 financial_analyzer 注入路径错 → 修 `scoring_model_corporate._score_financial` 接线
   - 是 reason_codes 字典 schema 不齐 → 补 `agent_credit/reason_codes.yaml` 字段
   - 是 RiskRadar 4 维度入参不全 → 修 `agent_credit/risk_radar.py` thin wrapper
3. 顺带跑 `ruff check agent_credit/ tests/agent_credit/` 0 error

**约束**：
- 不为了让 test 跑通注释 assert · 找根因
- 不动红区 · 出现红区 import 错误立即停手 askout

**完成信号**：`Signal: AGENT3-PYTEST-GREEN`（也可省略此 signal · 折叠进 Task A 的 REBASE-CLEAN 后续 fix-up commit）

---

### Task C · 解决 evaluation adapter 冲突（如有）

**目标**：处理 `evaluation/runner/adapters/agent3_credit.py` 在 rebase 时的冲突。

**策略硬线**：**优先保 Batch 2 evaluation**（已合 main · commit `c2776b4`） · agent3 branch 的 evaluation 改动是过期的。

**步骤**：
1. rebase 到 `14a4a34` / `d221115` 时如有冲突，`git checkout --ours evaluation/runner/adapters/agent3_credit.py`（`ours` 在 rebase 语义里是 chore/l0-infra 上的 Batch 2 版本）
2. 跑 `pytest tests/evaluation/ -v` 验证 Batch 2 evaluation adapter 仍正常
3. 跑 `py evaluation/runner/cli.py --agent agent3` 一次 · 与 Batch 2 baseline `evaluation/baselines/2026-04-26-real-run.md` 对比 Agent3 跑分 · 不应漂移

**约束**：
- 不改 `base_evaluator.py` / `cli.py`（A-024 路径规范）
- 不重新 enable agent3 branch 的 evaluation 改动（Batch 2 已是 source of truth）

**完成信号**：折叠进 `AGENT3-REBASE-CLEAN`（不单独 Signal · evaluation 冲突解为 rebase 一部分）

---

### Task D · READY signal + body 自检

**目标**：最终 `READY-FOR-AGENT3-UNFREEZE-REVIEW` commit 的 body 必须含：

1. **新旧 SHA 对照表**（11 commit · rebase 前 SHA → rebase 后 SHA · skip 的标 `[skipped]`）
2. **`git diff --name-only origin/chore/l0-infra...HEAD`**（rebase 后所有改动文件清单）
3. **解 DoD 条目自检**：
   - [ ] L2-7 Agent3 reason_codes Top-5 落地（`agent_credit/scoring_model_corporate.py` 派生 + adapter 输出）
   - [ ] L2-8 Agent3 字典文件落盘（`agent_credit/reason_codes.yaml` 或 `docs/reason_codes/agent3_credit.yaml`）
   - [ ] L1-3 Agent3 RiskRadar wrapper 可用（`agent_credit/risk_radar.py`）
   - [ ] L1-4 Agent3 docx 导出可生成（`agent_credit/decision_letter_docx.py` + 跑通 1 次冒烟）
   - [ ] L1-11 Agent6→Agent3 handoff button 在 demo profile 中可触发
4. **红区漂移自检**：`git diff --name-only origin/chore/l0-infra...HEAD | grep -E '^(financial_analyzer|quality_scorer|truth_fill|web/|v16_|data/mock/|evaluation/runner/(base_evaluator|cli))'` 输出 0 行
5. **Batch 1 注入保留自检**：grep `financial_analyzer` 在 `agent_credit/scoring_model_corporate.py` / `advisor_formatter.py` 中仍有引用

**完成信号**：`Signal: READY-FOR-AGENT3-UNFREEZE-REVIEW`

---

## 3. 验收硬指标（T2-1 ~ T2-12 · 12 项）

| # | 指标 | 阈值 | 判定 |
|---|---|---|---|
| T2-1 | Signal trailer 链齐 | `AGENT3-UNFREEZE-ACK` + `AGENT3-REBASE-CLEAN` + `READY-FOR-AGENT3-UNFREEZE-REVIEW` 至少 3 单行 trailer | `git log --format=%B` grep |
| T2-2 | rebase 完成 | `git log feat/agent3-productize-rebased --oneline origin/chore/l0-infra..HEAD` 输出 ≥ 7 commit（11 - skip 的 evaluation 4 commit） | git log |
| T2-3 | 红区漂移 0 | `financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py` / `web/` / `v16_*.py` / `data/mock/` / `evaluation/runner/{base_evaluator,cli}.py` 全 0 改动 | `git diff --name-only` |
| T2-4 | A-024 路径规范 | `evaluation/runner/base_evaluator.py` + `cli.py` 未改 | stat 0 改动 |
| T2-5 | financial_analyzer 注入仍在 | `agent_credit/scoring_model_corporate.py` 内 grep `financial_analyzer` ≥ 1 | grep |
| T2-6 | reason_codes 字典文件落盘 | `agent_credit/reason_codes.yaml` 或 `docs/reason_codes/agent3_credit.yaml` 存在 + 含 ≥ 5 条标准条目（对标 FCRA AAN） | ls + cat |
| T2-7 | reason_codes Top-5 派生可用 | adapter 输出含 `reason_codes` 字段 · 长度 ≤ 5 · 每条带 `code` + `description` | adapter dry-run |
| T2-8 | docx 导出可生成 | `py -c "from agent_credit.decision_letter_docx import export; export(<demo profile>, '/tmp/test.docx')"` 生成有效 .docx | 文件 size > 0 + 可打开 |
| T2-9 | RiskRadar wrapper 可用 | `agent_credit/risk_radar.py` 导出 4 维度数据 · adapter 端可消费 | import + call |
| T2-10 | handoff button demo 可触发 | 2 demo profile 在 `agent_credit/demo_profiles/` · handoff button 元数据齐 | grep + ls |
| T2-11 | pytest 全绿 | `pytest tests/agent_credit/ -v` 100% 通过（含 23737c4 带来的 16 tests） | exit 0 |
| T2-12 | ruff clean + Batch 2 evaluation 不漂 | `ruff check agent_credit/ tests/agent_credit/` 0 error · `pytest tests/evaluation/test_agent3*` 全绿 · Agent3 跑分与 Batch 2 baseline 一致 | 双 grep |

---

## 4. 红线

- ❌ **不动红区**：`financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py`（任何 import 错误 / 隐式碰触都属违规）
- ❌ **不覆盖 Batch 2 evaluation**：agent3 branch 的 evaluation 改动（`14a4a34` / `d221115`）是过期的 · 冲突时一律 `--ours` 走 chore/l0-infra 版本
- ❌ **不动 web/**（前端归轨 4 整合 · 不在本轨范围）
- ❌ **不动 v16_*.py / data/mock/**
- ❌ **不改 `evaluation/runner/base_evaluator.py` / `cli.py`**（A-024 路径规范）
- ❌ **不 git push**（主 CLI 统一合流）
- ❌ **不 squash commit**（11 commit 串行 rebase · 保留 SHA 对照可追溯）
- ❌ **冲突 > 4 文件立即停手** · Q-033 askout（不要硬解）
- ✅ 每 Task 独立 commit · trailer 单行 `Signal: <NAME>`（多 signal 拆 commit）
- ✅ Final commit body 附：11 commit 新旧 SHA 对照 + `git diff --name-only` 全清单 + 解 DoD 条目自检勾选 + 红区漂移自检 + Batch 1 注入保留自检

---

## 5. 工期

- Task A · rebase 11 commit + 解冲突 · ~1 天
- Task B · pytest 全绿 + ruff · ~0.25 天
- Task C · evaluation adapter 冲突解（如有） · ~0.25 天
- Task D · READY signal + body 自检 · ~0.5 天
- 合计 **1-2 天**（冲突 > 4 文件 askout 不计入）
