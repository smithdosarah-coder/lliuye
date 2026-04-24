# Batch 3 · code-arch Agent2 硬化 Onboarding

**状态**：Batch 3 GO（待 user dispatch）
**发布日期**：2026-04-25
**Signal 入口**：`BATCH-3-CA-ACK`
**前置**：Batch 2（commit `8b66bd2` `PHASE-2-CODE-ARCH-APPROVED`）—— Agent1/5 外搜 + integration test 已落地
**参照决策**：`docs/handoff/decisions-log.md` Q-030（Batch 2 closeout）/ Q-031（Phase 4 规划）

---

## 1. 背景与目标

Agent2 评估 🟡 **5/10 指标 PARTIAL**。5 pending 的根因都是 **adapter 探针 / 对照组 / LLM-judge 未实装**（非实现缺失）：

| pending 指标 | 卡在哪 | 本轨 Task |
|---|---|---|
| `field_completeness` | adapter 无 runtime 探针 | Task A |
| `dsl_syntax_correctness` | adapter 无 parser round-trip | Task A |
| `ks_improvement` | 无 baseline_ruleset 对照组 + LLM-judge | Task B + C |
| `rule_interpretability` | 无 LLM-judge | Task C |
| `per_rule_fpr_spread` | 有效规则不足 2 条（样本量级问题） | 本轨不管 · data-foundation 轨解决 |

Agent2 代码已有 production 骨架（`agent_riskctrl/` 1283 行核心 + 3 domain），本轨只做**补齐探针 + 对照组 + LLM-judge**，不重写引擎。

**硬边界**：只动 `agent_riskctrl/` + `evaluation/runner/adapters/agent2_riskctrl.py` + 新 `shared/llm_judge/` + `tests/`。**不动** `financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py` / `web/` / `v16_*.py` / `data/mock/` / `evaluation/runner/base_evaluator.py` / `cli.py`。

---

## 2. Task 清单

### Task A · Agent2 adapter runtime 探针

**目标**：`evaluation/runner/adapters/agent2_riskctrl.py` 加 2 个 runtime 探针：
1. `field_completeness` · 跑 adapter 时记录每个 DSL 字段的非空率，聚合成指标
2. `dsl_syntax_correctness` · DSL 生成后做 parser round-trip 校验（parse → serialize → compare），正确率入指标

**约束**：
- 探针要 deterministic（同样输入同样输出）
- 不改 base_evaluator.py / cli.py（A-024 路径规范 · 见 Q-024/A-024）
- 探针输出形态对齐 Batch 2 `precision@10` 的 module-level function 模式

**完成信号**：`Signal: AGENT2-ADAPTER-PROBES-DONE`

---

### Task B · baseline_ruleset 对照组

**目标**：在 `agent_riskctrl/baseline_ruleset.py` 新建一组**固定 5 条**的 baseline DSL 规则（业界常见的简单阈值规则如 `credit_score < 600 THEN reject` / `debt_ratio > 0.7 THEN reject` 等）· 作为 KS 改进对比的对照组。

**路径**：
- `agent_riskctrl/baseline_ruleset.py`（新建）· 5 条规则 + 解析器
- 集成到 `backtesting.py` · `--compare-baseline` 标志跑对照
- adapter 把对照 KS 写入 `ks_baseline` 字段 · Agent2 输出 KS 写 `ks_current` · `ks_improvement = ks_current - ks_baseline`

**约束**：
- baseline 规则**硬编码 · 不随样本变化** · 真实对照组意义
- 接 data-foundation 轨 `agent2-samples/loans.csv`（若未到位走 fixture stub · 参照 Batch 2 evaluation 模式）

**完成信号**：`Signal: AGENT2-BASELINE-RULESET-DONE`

---

### Task C · LLM-judge 实装

**目标**：`shared/llm_judge/` 新模块 · 一个通用 LLM-judge 基类 + 2 个 Agent2 专用 judge：
1. `rule_interpretability_judge` · 4-point Likert scale（清晰/一般/勉强/不可读）· 给一条规则的自然语言描述打分
2. `ks_improvement_judge`（辅助）· 给定 baseline + current 对比解读，输出定性评价（deterministic 是主指标 · judge 辅助可选）

**路径**：
- `shared/llm_judge/base.py` · 基类（prompt + parser + retry）
- `shared/llm_judge/rule_interpretability.py` · rule_interpretability 专用
- `shared/llm_judge/ks_explainer.py`（可选）
- adapter 把 judge 分数写入 `rule_interpretability` 指标

**约束**：
- judge 调 DeepSeek（项目 .env 读 key · 不硬编）
- 失败降级（无 key / 网络失败）不 crash · 写 `judge_status: unavailable` 指标标 `method: manual` 留 pending
- judge 结果**不覆盖 deterministic 指标** · 只补 manual 指标
- 新建模块**归在 `shared/llm_judge/`** · 不进红区 · 非红区改动

**完成信号**：`Signal: AGENT2-LLM-JUDGE-DONE`

---

### Task D · integration test + Agent1/5 stub → deterministic 升级

**目标**：
1. 新 `tests/agent_riskctrl/test_batch3_integration.py` · 3 case：
   - probes + baseline_ruleset + judge 端到端跑一遍
   - field_completeness / dsl_syntax_correctness deterministic 结果校验
   - judge 失败降级不 crash
2. **Q-030 Follow-up** · evaluation/runner/adapters/agent1_channel.py + agent5_compliance.py 的 stub method → deterministic
   - 现 stub `method=heuristic`（Batch 2 时 code-arch oracle 未合入）· 现已合入（commit `8b66bd2`）· 把 stub 分支改成调 code-arch 新 `compute_external_search_metrics` / `compute_policy_compare_metrics`
   - adapter 重新指定 `method=deterministic`

**完成信号**：`Signal: AGENT2-INTEGRATION-TEST-DONE`（含 Agent1/5 升级）

---

## 3. 验收硬指标（CA-B3-1 ~ CA-B3-12 · 12 项）

| # | 指标 | 阈值 | 判定 |
|---|---|---|---|
| CA-B3-1 | 4 Task Signal trailer 齐 | AGENT2-ADAPTER-PROBES-DONE / AGENT2-BASELINE-RULESET-DONE / AGENT2-LLM-JUDGE-DONE / AGENT2-INTEGRATION-TEST-DONE | `git log` grep |
| CA-B3-2 | 越界 0 | diff 只在白名单：agent_riskctrl/ · shared/llm_judge/ · evaluation/runner/adapters/agent{1,2,5}* · tests/ | `git diff --name-only` |
| CA-B3-3 | 红区漂移 0 | financial_analyzer / quality_scorer / truth_fill / web/ / v16_*.py / evaluation runner base+cli 全 0 | diff 校验 |
| CA-B3-4 | A-024 路径规范 | base_evaluator.py / cli.py 未改 | stat 0 |
| CA-B3-5 | adapter 探针 2 项 deterministic | field_completeness + dsl_syntax_correctness 同输入同输出 | 跑 2 次取值一致 |
| CA-B3-6 | baseline_ruleset 固定 5 条 | `baseline_ruleset.py` 导出 5 条规则 · 不随样本变 | 读代码 |
| CA-B3-7 | ks_improvement 有对照组 | adapter 输出含 `ks_baseline` + `ks_current` + `ks_improvement` | 跑 adapter JSON |
| CA-B3-8 | LLM-judge 基类可复用 | `shared/llm_judge/base.py` 有抽象 `judge(prompt) -> {score, rationale}` | grep |
| CA-B3-9 | judge 失败降级不 crash | 无 key / 网络失败时 adapter 仍完成 · 写 unavailable · method=manual | mock 测试 |
| CA-B3-10 | Agent1/5 stub → deterministic | agent1_channel.py / agent5_compliance.py 改 method=deterministic · 调 code-arch 新函数 | grep |
| CA-B3-11 | pytest 绿 | tests/agent_riskctrl/* + Agent1/5 回归 | `pytest -v` |
| CA-B3-12 | ruff clean | `ruff check agent_riskctrl/ shared/llm_judge/ evaluation/runner/adapters/` | 0 error |

---

## 4. 红线

- ❌ 不动 `financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py` / `web/` / `v16_*.py` / `evaluation/runner/base_evaluator.py` / `cli.py` / `data/mock/`
- ❌ judge 不覆盖 deterministic 指标 · 只补 manual
- ❌ baseline_ruleset 不随样本变 · 必须硬编码
- ✅ 每 Task 独立 commit 带 Signal trailer
- ✅ 最终 commit Signal: `READY-FOR-CODE-ARCH-B3-REVIEW`
- ✅ body 附 4 Task SHA + `git diff --name-only` + CA-B3-1~12 自检结论

---

## 5. 工期

- Task A · 2 探针 · ~0.5 天
- Task B · baseline_ruleset · ~0.75 天
- Task C · LLM-judge · ~1 天
- Task D · integration test + Agent1/5 升级 · ~0.75 天
- 合计 ~3 天
