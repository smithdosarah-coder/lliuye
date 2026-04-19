# Agent2 Phase 1 · Task C · per_rule_fpr_spread

**日期**：2026-04-19
**merge commit (A-019 intake)**：`8ec4283`
**worktree**：`D:\claude code\demo-agent2` (`feat/agent2-productize`)
**onboarding 锚点**：`docs/onboarding/agent2-phase-1.md` §3 Task C
**依赖裁决**：`A-019 @ c947906` · 总体方差 σ² ≤ 0.03（Phase 1 草案阈值）

---

## 目标与闭环

Phase 0 / Task A 的 `false_positive_rate = 0.0439` 是全规则合并 FPR —— 单条 reject 规则的误杀分布被"整体绿"掩盖。A-019 下发"σ² ≤ 0.03"作警戒：

- `agent_riskctrl/backtesting.py` per-rule 独立匹配算 `{FP, TN, FP_rate}`
- `evaluation/runner/adapters/agent2_riskctrl.py` 消费 rules.json 的 per-rule 字段算 σ²
- `evaluation/agent2_riskctrl.yaml` metrics.domain 追加 `per_rule_fpr_spread` · target `<= 0.03`
- 单测用 2 规则构造已知 FPR 分布对手算 σ² = 0.006944...

---

## 交付物

### 1. 新建文件

| 文件 | 作用 |
|---|---|
| `agent_riskctrl/tests/test_per_rule_fpr_spread.py` | 3 单测：run_backtest per-rule FP/TN · adapter σ² 手算对照 · < 2 规则 value=None |
| `docs/progress/agent2-phase-1-task-c.md` | 本文件 |

### 2. 修改文件

| 文件 | 变更 |
|---|---|
| `agent_riskctrl/backtesting.py` | `run_backtest(df, ruleset, label_column=None)` 新增可选 label_column；rule_stats 每条加 `{FP, TN, FP_rate}`；仅 reject 规则非零，其余 N/A |
| `evaluation/runner/adapters/agent2_riskctrl.py` | `compute_domain_metrics` 追加 `per_rule_fpr_spread` MetricOutcome · `method=deterministic` · 少于 2 条有效规则返回 value=None |
| `evaluation/agent2_riskctrl.yaml` | metrics.domain 加 `per_rule_fpr_spread` target `<= 0.03`；baseline.results 回填 `0.0002`；last_run/commit 刷新到 `8ec4283` |
| `scripts/run_agent2_baseline.py` | `build_rules_json` 把 rule_stats 的 FP/TN/FP_rate 透传到 `rules.json` 每条规则 `backtest` 子对象 |

### 3. Runtime 产物刷新（gitignored）

`evaluation/runtime/2_20260419T094032/` + `2_latest/`

---

## 实现要点

### Per-rule FP/TN 独立匹配（非 priority-stop）

`apply_ruleset` 命中即停 —— 一条记录只贡献一条规则的 `hit_rule_id`。但 per-rule spread 要看"这条规则单独作决策时的误杀率"，所以对每条 reject 规则 × 每条 label=0 的记录独立调 `apply_rule(rule, rec)`：

```python
# agent_riskctrl/backtesting.py
if labels is not None and rule.action == "reject":
    fp = 0
    tn = 0
    for rec, lbl in zip(records, labels):
        if lbl != 0:
            continue
        if apply_rule(rule, rec):
            fp += 1
        else:
            tn += 1
    stat["FP"] = fp
    stat["TN"] = tn
```

approve / manual_review 规则保持 FP=TN=0 —— adapter 在 `(FP+TN)>0` 条件下跳过（对齐 A-019 "N/A 规则跳过"语义）。

### σ² 计算（A-019 公式 1:1 实装）

```python
# evaluation/runner/adapters/agent2_riskctrl.py
fprs = [fp/(fp+tn) for r in rules if (fp:=r.backtest.FP) or True
        if (tn:=r.backtest.TN) >= 0 and (fp+tn) > 0]
if len(fprs) < 2:
    value = None  # 不适用
else:
    mean = sum(fprs) / len(fprs)
    value = sum((x - mean) ** 2 for x in fprs) / len(fprs)  # 总体方差
```

（实装代码为可读风格展开，上为概念示意）

### label 列自动探测

`run_backtest` 未显式传 `label_column` 时按 `label_default` / `label` 顺序探测，保持 `agent.py` 调用点零改动。synthesized CSV 用 `label_default`，fixture schema 亦然。

---

## Runtime 结果（8ec4283 基线）

| 指标 | Runtime | 阈值 | Verdict |
|---|---:|---|---|
| task_completion_rate | 1.0000 | ≥ 0.95 | PASS |
| evidence_rate | 1.0000 | ≥ 0.98 | PASS |
| hallucination_rate | 0.0000 | ≤ 0.01 | PASS |
| tool_success_rate | 1.0000 | ≥ 0.95 | PASS |
| false_positive_rate | 0.0439 | ≤ 0.15 | PASS |
| **per_rule_fpr_spread** | **0.0002** | **≤ 0.03** | **PASS** |
| ks_improvement | null | ≥ 0.02 | pending (A-013) |
| rule_interpretability | null | ≥ 4.0 | pending (A-013) |

Per-rule 分解（reject 规则）：
- R001 overdue_days_90d>30：FP=4 / TN=110 → FPR=0.0351
- R002 debt_ratio>=0.8 ∧ overdue_count_12m>=2：FP=1 / TN=113 → FPR=0.0088

σ² = ((0.0351-0.02195)² + (0.0088-0.02195)²) / 2 ≈ 0.0002

**解读**：当前 runtime ruleset 的 reject 规则误拒率高度均衡（σ² 距阈值 2 数量级）。A-019 §"6. 若观测值 ≤ 0.005（过度均衡）：标 '规则同质性过高，可能冗余'，不触 fail 但记 follow-up" —— **本 Phase 1 草案观测值 0.0002 触发 follow-up**：Phase 2 Batch 2 真实 baseline 分布锚定时需评估"两条 reject 规则覆盖面是否重叠过高"，并在 ruleset 扩展到 ≥5 条 reject 规则后重评 σ² 阈值（当前 2 条规则方差信息量本身有限）。

---

## 单测证据

`py -m pytest agent_riskctrl/tests/test_per_rule_fpr_spread.py -v` → 3/3 passed

- `test_run_backtest_emits_per_rule_fp_tn`：2 reject + 1 manual_review，手算 FP/TN 对上
- `test_per_rule_fpr_spread_variance_matches_manual_calc`：手算 σ² ≈ 0.006944 · `math.isclose(abs_tol=1e-4)`
- `test_per_rule_fpr_spread_insufficient_rules`：1 条 reject 规则 → value=None, passed=None

---

## A-012.D / A-012.E 对齐

- **A-012.D SHA 不可变**：本 Task 仅新增 / 改黄区文件（`backtesting.py` / adapter / yaml / script / tests），未触 5 个已被 review 引用的 SHA
- **A-012.E merge-only**：upstream catch-up 用 `git merge --no-ff upstream/chore/l0-infra` @ `8ec4283` 拿 A-019 + A-012.E；冲突用 `python` 手工 union（保留 Q-019 + 删 TBD stub + 吸收上游 A-012.E + A-019 两块），未 rebase / --skip / --abort

## 红区不可碰验证

```
git diff evaluation/runner/{base_evaluator,registry,cli,__main__,schemas}.py
```
empty → 合规。

---

## DoD 逐条对账

- [x] `backtesting.py` rule_stats per 条加 `{FP, TN, FP_rate}`
- [x] adapter `compute_domain_metrics` 追加 `per_rule_fpr_spread` · `method=deterministic`
- [x] yaml metrics.domain 加 name/desc/target `<= 0.03`（实填，不 TBD）
- [x] yaml baseline.results 回填 `per_rule_fpr_spread: 0.0002`
- [x] 单测构造 2 规则手算 σ² 验证（3/3 pass）
- [x] runner 跑出真实数值 `0.0002` · verdict PASS
- [x] `git diff` 红区 kernel 文件 0 行
- [x] A-012.E merge-only（`8ec4283` merge commit，非 rebase）
- [x] A-012.D SHA 不可变（仅新增 / 黄区改）
- [x] R-A smoke-must-test（pytest + `py -m evaluation.runner --agent riskctrl` 本 commit HEAD 上实测）
- [x] R-B 一 commit 一 Signal

## 下一步

Task C 结束 → commit `AGENT2-PHASE-1-TASK-C-DONE` → **idle 等主 CLI GO** 再进 Task D（前端存根 / fallback 设计稿）。
