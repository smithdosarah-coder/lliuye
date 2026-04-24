# Batch 3 · evaluation Agent2 5 pending 指标跑真 Onboarding

**状态**：Batch 3 GO（待 user dispatch）
**发布日期**：2026-04-25
**Signal 入口**：`BATCH-3-EV-ACK`
**前置**：Batch 2（commit `c2776b4` `PHASE-2-EVALUATION-APPROVED`）—— 真基线 + EV-12 + Agent1/5 stub 已落地
**参照决策**：`docs/handoff/decisions-log.md` Q-024（evaluation 路径）/ Q-025（rubric schema）/ Q-030（Batch 2 closeout）/ Q-031（Phase 4 规划）

---

## 1. 背景与目标

Batch 2 evaluation 跑出的 baseline 里 Agent2 🟡 PARTIAL · 5/10 pending。Batch 3 要把这 5 条跑真（依赖 data-foundation 的样本 CSV + code-arch 的探针/对照组/judge · 都是本 Batch 并行轨）。

本轨是 Batch 3 最下游——**依赖另外两轨的产出**。合流顺序：data-foundation + code-arch 先合 · evaluation 最后合。Batch 3 预计 READY 到达顺序：data-foundation → code-arch → evaluation。

**硬边界**：只动 `evaluation/`（含 `agent2_riskctrl.yaml` + `runner/adapters/agent2_riskctrl.py` + `baselines/` 产出）· **不动** `agent_*/` / `shared/` / `data/mock/` / `web/` / `v16_*.py` / `runner/base_evaluator.py` / `cli.py`。

---

## 2. Task 清单

### Task A · Agent2 真 baseline 重跑

**目标**：用 data-foundation 轨产的 `data/mock/agent2-samples/loans.csv` 重跑 Agent2 adapter · 出 real baseline。

**路径**：
- `evaluation/baselines/2026-04-27-real-run-b3.json` + `.md`（日期按实际跑日写）
- 更新 `evaluation/scripts/build_real_baseline.py` · 把 agent2 从 fixture 切到真 loans.csv 消费
- adapter `evaluation/runner/adapters/agent2_riskctrl.py` · 接 code-arch 新探针 + baseline_ruleset + judge

**预期指标**（本轮跑真后应落成）：
| metric | method | 本轮期望 |
|---|---|---|
| `field_completeness` | deterministic | ≥ 0.95 |
| `task_completion_rate` | deterministic | ≥ 0.98 |
| `evidence_rate` | deterministic | ≥ 0.98 |
| `hallucination_rate` | deterministic | ≤ 0.01 |
| `tool_success_rate` | deterministic | ≥ 0.95 |
| `false_positive_rate` | deterministic | ≤ 0.15 |
| `per_rule_fpr_spread` | deterministic | ≤ 0.03（样本足则跑出，不足则留 — `note: insufficient rules`） |
| `ks_improvement` | deterministic | ≥ 0.02（vs baseline_ruleset） |
| `rule_interpretability` | manual (LLM-judge) | ≥ 4.0 / 5 |
| `dsl_syntax_correctness` | deterministic | ≥ 0.98 |

**完成信号**：`Signal: AGENT2-REAL-BASELINE-DONE`

---

### Task B · rubric YAML 精修

**目标**：`evaluation/agent2_riskctrl.yaml` · 5 pending 指标从 `method: manual` / 注释写死 pending 切到本轮 actual method。具体：
- `field_completeness` manual → deterministic · `method_description` 更新
- `dsl_syntax_correctness` manual → deterministic
- `ks_improvement` manual → deterministic
- `rule_interpretability` 保留 manual（LLM-judge） · 更新 judge 路径
- `per_rule_fpr_spread` deterministic（样本不足时 note）

**A-025 schema 兼容层**：agent2_riskctrl.yaml 严格新 schema（`description` + `method` + `baseline_target` + `blocker_threshold`）· 不含 Agent6 的老 `desc/target` 双写。

**完成信号**：`Signal: AGENT2-RUBRIC-UPDATED-DONE`

---

### Task C · 全 6 Agent 综合报告 + 收口

**目标**：
1. baseline .md 除了 Agent2 的 per-metric 差值表，补一张 **全 6 Agent 最终状态总览表**（PASS / PARTIAL / FAIL + key gap）
2. Phase 3 closeout 建议段：哪些 Agent 已达 DoD L3 · 哪些还差啥
3. 回填 Q-030 Follow-up：Agent1/5 的 metric 从 stub 升 deterministic · 本轮真跑数字是否 ≥ stub 的启发式值

**完成信号**：`Signal: AGENT2-FINAL-REPORT-DONE`

---

## 3. 验收硬指标（EV-B3-1 ~ EV-B3-10 · 10 项）

| # | 指标 | 阈值 | 判定 |
|---|---|---|---|
| EV-B3-1 | 3 Task Signal trailer 齐 | AGENT2-REAL-BASELINE-DONE / AGENT2-RUBRIC-UPDATED-DONE / AGENT2-FINAL-REPORT-DONE | git log |
| EV-B3-2 | 越界 0 | diff 只在 evaluation/ | diff 校验 |
| EV-B3-3 | A-024 路径规范 | base_evaluator.py / cli.py 未改 | stat 0 |
| EV-B3-4 | 红区漂移 0 | v16_*.py / agent_*/ / financial_analyzer / quality_scorer / truth_fill / web/ / data/mock/ | diff 校验 |
| EV-B3-5 | baseline JSON 结构 | 6 agent × 10 metric 齐 | py json load |
| EV-B3-6 | Agent2 5 pending 跑真 | field_completeness / dsl_syntax_correctness / ks_improvement / per_rule_fpr_spread / rule_interpretability 都有 value（不 None） | adapter 输出 |
| EV-B3-7 | ks_improvement 达标 | ≥ 0.02 | 读 JSON |
| EV-B3-8 | rubric schema A-025 兼容 | agent2_riskctrl.yaml 新 schema · Agent6 老字段保留不删 | yaml lint |
| EV-B3-9 | 全 6 Agent 总览表在 md | mean/min/max 行 × 6 Agent 齐 + key gap 注 | md grep |
| EV-B3-10 | Agent1/5 升级确认 | baseline JSON 里 Agent1 precision@10 / recall@10 + Agent5 precision@10 / recall@10 method=deterministic 不是 heuristic | JSON grep |

---

## 4. 红线

- ❌ 不动 `agent_*/` / `shared/` / `data/mock/` / `web/` / `v16_*.py` / `evaluation/runner/base_evaluator.py` / `cli.py`
- ❌ 跑 Agent6 v16 baseline 的数字不得漂移 ≥ 1%
- ❌ rubric yaml 不得删 Agent6 老 `desc/target` 字段（A-025 兼容层）
- ✅ 每 Task 独立 commit 带 Signal trailer
- ✅ 最终 commit Signal: `READY-FOR-EVALUATION-B3-REVIEW`

---

## 5. 依赖与时序

- **硬依赖** data-foundation Task A/B 完成（loans.csv + field_dictionary.md 落盘）
- **硬依赖** code-arch Task A/B/C 完成（adapter 探针 + baseline_ruleset + LLM-judge 合入）
- 两轨都合到 `chore/l0-infra` 后本轨 rebase 再开工
- 若 data-foundation 或 code-arch REJECT-V2 → 本轨阻塞等返工

---

## 6. 工期

- Task A · real baseline 重跑 + adapter 接管 · ~1 天
- Task B · rubric 精修 · ~0.25 天
- Task C · 6 Agent 总览 + 报告 · ~0.5 天
- 合计 ~1.75-2 天（仅本轨 · 等上游合流时等待时间另计）
