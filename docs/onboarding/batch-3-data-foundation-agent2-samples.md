# Batch 3 · data-foundation Agent2 历史贷款样本 CSV Onboarding

**状态**：Batch 3 GO（待 user dispatch）
**发布日期**：2026-04-25
**Signal 入口**：`PRODUCT-HARDENING-BATCH-3-DF-P3-ACK`
**前置**：Batch 2 Phase 2（commit `271eb6f` `PHASE-2-DATA-FOUNDATION-APPROVED`）—— Agent4 alert-pool 已落地通过 7/7 硬指标
**参照决策**：`docs/handoff/decisions-log.md` Q-028（反 5 原则 + 环境边界）/ Q-029（测试豁免）/ Q-030（Batch 2 closeout）/ Q-031（Phase 4 规划）

---

## 1. 背景与目标

Phase 1 v2 + Phase 2 已覆盖 Agent6/3/1/5/4 的数据底座。**Agent2 风控**是 Phase 3（最后一 Phase）——

Agent2 消费形态是 **历史贷款样本 CSV + 字段字典**，核心能力 = **DSL 规则生成 + 回测**（KS / 通过率 / 坏账率）。按 CLAUDE.md §3.5 环境边界表：Agent2 全内部建模，**外部不 mock**。

当前 Agent2 评估 🟡 **5/10 指标 PARTIAL**（2026-04-26-real-run.md · riskctrl 段）：
- `ks_improvement` · pending · Phase-2 runtime baseline_ruleset 对照组依赖
- `rule_interpretability` · pending · LLM-judge 未实装
- `dsl_syntax_correctness` · pending · adapter 未实装 parser round-trip 校验
- `field_completeness` · pending · adapter 未实装 runtime 探针
- `per_rule_fpr_spread` · 有效规则不足 2 条

前 4 条都要**真历史贷款数据**跑才有结果。本轨负责产数据底座。

**规模**：单表 CSV · 5000-10000 行 · ≥ 12 月历史跨度 · 字段字典 md 1 份。

**硬边界**：本 Phase **只产** `data/mock/agent2-samples/`，**不动** `agent_riskctrl/` / `shared/` / `evaluation/` / `web/`。代码硬化归 code-arch 轨（本 Batch 并行）。

---

## 2. Task 清单

### Task A · 历史贷款样本 `agent2-samples/loans.csv`

**目标**：单表 CSV · 5000-10000 行 · 每行一条已结清 / 在贷贷款 · 含 12-36 个特征字段 + 1 个逾期结果字段。

**路径**：`data/mock/agent2-samples/loans.csv`

**字段分组（必齐全）**：

| 分组 | 字段（示例） | 说明 |
|---|---|---|
| 样本 ID | `loan_id` | `L000001` ~ · 5000-10000 行范围 |
| 申请人基础 | `applicant_age` / `marriage` / `education` / `job_tenure_months` / `monthly_income_cny` | 人口学 + 就业 · 合理分布 |
| 企业基础（对公样本） | `company_age_years` / `industry_l1` / `scale` / `region` | 呼应 channel-kb/deep-pillar 行业/规模 |
| 财务指标 | `current_ratio` / `debt_ratio` / `roe` / `revenue_yoy` / `net_margin` | 对公样本必填 · 对私样本留空（允许 50% 对私 · 50% 对公混合） |
| 贷款结构 | `loan_amount_wan` / `term_months` / `rate_pct` / `collateral_type` / `purpose` | 10-2000 万合理分布 · 抵押/保证/信用三分 |
| 征信信号 | `credit_score` / `past_overdue_count_1y` / `current_overdue_count` / `guarantee_times_1y` / `query_times_3m` | 征信评分 350-900 · 历史逾期次数 |
| 行为信号 | `bank_balance_stddev_3m` / `large_debit_count_1m` / `cross_province_count_1m` | 流水行为变化 |
| **结果字段（唯一答案列）** | `days_past_due` | 关键监督信号 · 0 = 未逾期 · 1-30 轻度 · 31-90 中度 · 90+ 重度（坏账） |

**注意 `days_past_due` 是唯一允许的结果字段**——DSL 回测要用它算 KS / FPR。**不单独产 `labels.json` 或 `optimal_dsl.yaml`**（反结果导向第 1 条盲测 · Q-028/A-028）。

**难度分层（PM 私下维护 · 产物零答案字段）**：

| 档 | 比例 | PM 内部画像（**不得出现在字段/注释/README**） |
|---|---|---|
| 简单（未逾期） | ~60% | 征信良好 · 流水稳定 · 财务达标 · `days_past_due=0` |
| 边缘（轻度逾期） | ~20% | 个别特征处于阈值 · `days_past_due` 1-30 |
| 困难（中度/重度） | ~15% | 多特征劣化 · 31-90 或 90+ |
| 极端（坏账 + 欺诈） | ~5% | 多信号冲突 · 大额 + 短期 + 高 yoy 下滑 · 90+ |

**反结果导向 5 原则逐条合规**（CLAUDE.md §3.5）：
1. **盲测**：worker 不预知埋点 · PM 私下维护难度档位不入产物
2. **难度分层**：60/20/15/5（偏正常符合实际坏账率 ~2-5% 略放大）
3. **真实来源锚定**：参照央行征信报告字段 + 招行/建行零售审贷 SOP 可观测字段（可搜公开资料）
4. **脱敏再造**：编造姓名/企业名 · 改量级保合理 · 2026 Q2 测试阶段重名 OK（Q-029.D）
5. **环境边界**：Agent2 全内部 · **不** mock 外部数据

**完成信号**：`Signal: AGENT2-SAMPLES-LOANS-DONE`

---

### Task B · 字段字典 `agent2-samples/field_dictionary.md`

**目标**：每个字段的业务含义 + 取值范围 + 枚举值 + 异常值约定。供 DSL 引擎 / LLM-judge 消费。

**路径**：`data/mock/agent2-samples/field_dictionary.md`

**结构（每个字段一段）**：

```markdown
## `field_name`

- **类型**：int / float / str / date / enum
- **业务含义**：一句话
- **取值范围**：数值型给 min/max · 枚举给全量列表
- **空值约定**：NaN / 空串 / -1 代表啥
- **单位**：万元 / 月 / % / 分 / 天
- **异常值标记**：`-999` 不可用 · `null` 未采集 · 等
- **DSL 常用谓词**（可选）：该字段常被如何使用
```

每个字段对应一段 · 总计 20-35 段（按 Task A 实际字段数）。

**硬线**：字段字典**不得写难度档 / 答案字段 / 规则示例**（会喂 DSL 答案嘴边 · 触 Q-028 yaml-form-error 红线）。

**完成信号**：`Signal: AGENT2-SAMPLES-DICT-DONE`

---

### Task C · README `agent2-samples/README.md`

**目标**：3-5 行说明消费方（Agent2 riskctrl adapter 读 loans.csv 跑 DSL 回测 + evaluation/runner/adapters/agent2_riskctrl.py 读取）+ 字段数 + 样本数 + 难度档位总说明（不写具体比例）。

**完成信号**：`Signal: AGENT2-SAMPLES-README-DONE`

---

## 3. 验收硬指标（DF-P3-1 ~ DF-P3-10 · 10 项）

| # | 指标 | 阈值 | 判定 |
|---|---|---|---|
| DF-P3-1 | `data/mock/agent2-samples/` 新目录存在 | ls 返回 loans.csv + field_dictionary.md + README.md | ls |
| DF-P3-2 | loans.csv 行数 | 5000 ≤ n ≤ 10000（含表头） | `wc -l` |
| DF-P3-3 | loans.csv 字段数 | 20 ≤ cols ≤ 35 | `head -1 \| tr ',' '\n' \| wc -l` |
| DF-P3-4 | 唯一允许的结果字段是 `days_past_due` | grep 不含 `is_bad_loan` / `label` / `difficulty` / `risk_level` / `optimal_action` | grep -E 结果空 |
| DF-P3-5 | 逾期分布合理 | `days_past_due=0` 占 55-65% · 1-30 占 15-25% · 31-90 占 10-18% · 90+ 占 3-8% | awk 统计 |
| DF-P3-6 | 三分（抵押/保证/信用） | `collateral_type` 三档都有 · 最大 ≤ 60% · 最小 ≥ 10% | awk 统计 |
| DF-P3-7 | 对公 / 对私 混合 | 对公样本（有 `company_age_years`）30-70% | awk 统计 |
| DF-P3-8 | 数值合理 | `rate_pct` 3-30 · `loan_amount_wan` 10-2000 · `credit_score` 350-900 · 无 NaN | awk 边界检查 |
| DF-P3-9 | field_dictionary.md 每字段一段 | 段数 = loans.csv 字段数 ± 2 | grep `^## ` 数 |
| DF-P3-10 | 不越界 | diff 只动 `data/mock/agent2-samples/` + `docs/` | `git diff --name-only chore/l0-infra..feat/data-foundation \| grep -vE "^(data/mock/agent2-samples/\|docs/)"` 为空 |

---

## 4. 反 5 原则自查（worker commit 前必核）

- [ ] 盲测 · 零答案字段（difficulty / is_bad_loan / label / optimal_dsl 全 0 命中）
- [ ] 难度分层 · 60/20/15/5 · PM 内部维护 · 不入产物
- [ ] 真实锚定 · 字段集参照央行征信 + 零售审贷 SOP
- [ ] 脱敏再造 · 姓名 / 企业名 / loan_id 全自造
- [ ] 环境边界 · Agent2 内部建模 · 不 mock 外部

---

## 5. 红线

- ❌ 不动 `agent_riskctrl/` / `shared/` / `evaluation/` / `web/`
- ❌ 不写 `labels.json` / `optimal_dsl.yaml` / `difficulty_answer.csv`
- ❌ 字段字典不列 DSL 规则示例
- ❌ README 不写难度比例具体数字
- ✅ 每 Task 独立 commit 带 Signal trailer
- ✅ 最终 commit Signal: `READY-FOR-DATA-FOUNDATION-B3-REVIEW`

---

## 6. 工期

- Task A · 5000-10000 行合理分布 · ~1.5 天
- Task B · 25 字段字典 · ~0.5 天
- Task C · README · ~0.25 天
- 合计 ~2.25-2.5 天
