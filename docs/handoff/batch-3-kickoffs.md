# Batch 3 · 3 Worker Kickoff Prompts

> **定位**：Batch 3 正式派发 · Agent2 风控硬化（最后一批 Product Hardening）。3 轨——data-foundation（历史贷款样本 CSV）/ code-arch（Agent2 adapter 探针 + baseline_ruleset + LLM-judge）/ evaluation（5 pending 指标跑真 + Agent1/5 stub 升 deterministic）。
>
> **Batch 3 启动前提**：Batch 2 全 APPROVED 合流 main（commits `271eb6f` data-foundation · `8b66bd2` code-arch · `bc75ed1` code-urgent · `c2776b4` evaluation）+ Q-030 closeout 落地 + Q-031 mesh 清理执行。
>
> **粘发时机**：各 worker 只在主 CLI 发 `Signal: BATCH-3-DISPATCHED` 的 commit 落 main 之后才粘对应 kickoff。worker 先 `git fetch origin chore/l0-infra` 确认 dispatch commit 可见，再 ACK。
>
> **时序依赖**：evaluation Task A 硬依赖 data-foundation Task A/B + code-arch Task A/B/C 全部合入。data-foundation 和 code-arch 可并行。Batch 3 合流顺序：data-foundation → code-arch → evaluation。
>
> **Batch 3 是 Product Hardening 最后一批**。完结后进入 **Phase 4 · 前端整合 Batch**（见 Q-031 档 2/3 · 3 worker 漏合 + 7 前端 branch）。

---

## ① data-foundation · Batch 3 · Agent2 历史贷款样本 CSV

```
你是 data-foundation worker · Batch 3 · Phase 3 Agent2 样本。先 ACK 再动手。

【Step 0 · ACK】
1) git fetch origin chore/l0-infra && git log origin/chore/l0-infra -10
2) 读 docs/handoff/decisions-log.md 中 Q-030/A-030(Batch 2 closeout) + Q-031/A-031(mesh 清理 + Phase 4 规划)
3) 读 docs/onboarding/batch-3-data-foundation-agent2-samples.md 全文
4) 读 CLAUDE.md §3.5 反结果导向 5 原则(尤其环境边界第 5 条)
5) ls data/mock/agent2-samples/ 确认当前目录状态
6) commit 一条 doc-only,trailer `Signal: PRODUCT-HARDENING-BATCH-3-DF-P3-ACK`

【Step 1 · Task A · loans.csv】
- 5000-10000 行单表 · 20-35 字段 · 结果字段只保留 days_past_due
- 难度 60/20/15/5 (PM 私下维护 · 产物零答案)
- 对公/对私混合 30-70% · 抵押/保证/信用三分
- Signal: AGENT2-SAMPLES-LOANS-DONE

【Step 2 · Task B · field_dictionary.md】
- 每字段一段(类型/含义/范围/空值/单位/异常值标记)
- 不写 DSL 规则示例 · 不写难度档
- Signal: AGENT2-SAMPLES-DICT-DONE

【Step 3 · Task C · README.md】
- 3-5 行 · 消费方 + 样本数 + 字段数 + 难度档位总说明(不写具体比例)
- Signal: AGENT2-SAMPLES-README-DONE

【红线】
只动 data/mock/agent2-samples/ + docs/
不动 agent_*/web/evaluation/shared/
零答案字段:不写 labels.json / optimal_dsl.yaml / difficulty_answer.csv
每 Task 独立 commit · 带对应 Signal trailer

【Final】
3 Task 全绿 + 10 硬指标自检通过 → commit trailer `Signal: READY-FOR-DATA-FOUNDATION-B3-REVIEW`

开干。
```

---

## ② code-arch · Batch 3 · Agent2 adapter 硬化

```
你是 code-arch worker · Batch 3 · Agent2 硬化。

【Step 0 · ACK】
先一句话 ACK 进入 Batch 3 + 理解要做的事,禁止直接写代码。

【强制前置】
1) cd 到 worktree root (若用 demo-code-arch worktree 则 cd 该路径;worktree 在 Batch 2 closeout 已清 · 新 session 建议在 main worktree 操作 feat/code-arch-b3 分支 · 主 CLI 会确认路径)
2) git fetch upstream && git status(干净 + 正确分支)
3) 读 docs/handoff/decisions-log.md Q-030/Q-031
4) 读 docs/onboarding/batch-3-code-arch-agent2-hardening.md 全文
5) 读 agent_riskctrl/ 全目录了解现状(357 agent.py + 239 rule_engine.py + 304 backtesting.py + 236 metrics.py + 147 evidence_pipeline.py + 3 domain)
6) 读 evaluation/runner/adapters/agent2_riskctrl.py 了解现有 adapter
7) 读 evaluation/runner/adapters/agent1_channel.py + agent5_compliance.py 了解 stub → deterministic 升级目标
8) 确认 DEEPSEEK_API_KEY 在项目 .env(LLM-judge 用 · 无 key 走降级分支)

【执行顺序】
Task A → B → C → D 顺序,每 Task 独立 commit:
- Task A: Agent2 adapter 2 探针 → Signal: AGENT2-ADAPTER-PROBES-DONE
- Task B: baseline_ruleset 5 条固定规则 + 集成 backtesting → Signal: AGENT2-BASELINE-RULESET-DONE
- Task C: shared/llm_judge/ 模块 + rule_interpretability judge → Signal: AGENT2-LLM-JUDGE-DONE
- Task D: integration test + Agent1/5 stub → deterministic 升级 → Signal: AGENT2-INTEGRATION-TEST-DONE

每 Task 完成前必须:
(a) pytest 对应 tests/ 绿
(b) git diff --name-only 自查 scope 收敛(红线)
(c) commit 英文说明 why + 影响面

【红线】
只动 agent_riskctrl/ + shared/llm_judge/(新) + evaluation/runner/adapters/agent{1,2,5}* + tests/
不动 financial_analyzer.py / quality_scorer.py / truth_fill.py / web/ / v16_*.py / evaluation/runner/base_evaluator.py / cli.py / data/mock/
baseline_ruleset 不随样本变 · 硬编码
judge 不覆盖 deterministic 指标 · 只补 manual
judge 失败降级不 crash

【Final】
4 Task Signal 全打完 · 12 硬指标自检通过 → commit trailer `Signal: READY-FOR-CODE-ARCH-B3-REVIEW`
body 附 4 Task SHA + git diff --name-only + 硬指标自检结论

开干。
```

---

## ③ evaluation · Batch 3 · Agent2 5 pending 跑真 + Agent1/5 升级

```
你是 evaluation worker · Batch 3。Agent2 5 pending 指标跑真 + Agent1/5 stub → deterministic。

【Step 0 · ACK】
读 AGENT_IDENTITY.md + 里面列的所有文件 · resume 状态。本轨 onboarding:
docs/onboarding/batch-3-evaluation-agent2-metrics.md

【时序硬约束】
本轨是 Batch 3 最下游。
- 硬依赖 data-foundation Task A/B 合入 chore/l0-infra(loans.csv + field_dictionary.md)
- 硬依赖 code-arch Task A/B/C 合入 chore/l0-infra(adapter 探针 + baseline_ruleset + llm_judge)
- 上游未合前 ACK + 读 onboarding + 等待,不预跑

【执行】
3 Task 顺序:
- Task A: Agent2 real baseline 重跑(用 loans.csv + code-arch 新探针/对照组/judge) → Signal: AGENT2-REAL-BASELINE-DONE
- Task B: agent2_riskctrl.yaml 精修(5 pending 切 actual method) → Signal: AGENT2-RUBRIC-UPDATED-DONE
- Task C: 全 6 Agent 总览表 + Phase 3 closeout 建议 + Agent1/5 deterministic 确认 → Signal: AGENT2-FINAL-REPORT-DONE

【红线】
只动 evaluation/
不动 agent_*/shared/data/mock/web/v16_*.py/runner base+cli(A-024 路径)
Agent6 v16 跑分不得漂移 ≥ 1%
rubric yaml 保留 Agent6 老 desc/target 字段(A-025 兼容)

【Final】
3 Task 全绿 + 10 硬指标自检通过 → commit trailer `Signal: READY-FOR-EVALUATION-B3-REVIEW`

Resume 完汇报 · 当前 phase + 上游合流状态 + 准备先做哪个 Task + 有无 blocker · 然后停下等主 CLI GO。
```

---

## 尾部说明

- **签名**：Batch 3 kickoff · 2026-04-25 · 主 CLI
- **粘发顺序**：data-foundation + code-arch 并行粘(Batch 3 dispatch commit 落 main 后)· evaluation 等两轨都合流后才粘 GO
- **预计工期**：
  - data-foundation：~2.5 天
  - code-arch：~3 天
  - evaluation：~2 天实做 + 等上游合流时间
  - Batch 3 全部完结：~5-6 天

- **Signal 索引**：
  - **ACK × 3**：`PRODUCT-HARDENING-BATCH-3-DF-P3-ACK` / `BATCH-3-CA-ACK` / `BATCH-3-EV-ACK`
  - **Task done**:
    - data-foundation：`AGENT2-SAMPLES-LOANS-DONE` / `AGENT2-SAMPLES-DICT-DONE` / `AGENT2-SAMPLES-README-DONE`
    - code-arch：`AGENT2-ADAPTER-PROBES-DONE` / `AGENT2-BASELINE-RULESET-DONE` / `AGENT2-LLM-JUDGE-DONE` / `AGENT2-INTEGRATION-TEST-DONE`
    - evaluation：`AGENT2-REAL-BASELINE-DONE` / `AGENT2-RUBRIC-UPDATED-DONE` / `AGENT2-FINAL-REPORT-DONE`
  - **收尾 READY × 3**：`READY-FOR-DATA-FOUNDATION-B3-REVIEW` / `READY-FOR-CODE-ARCH-B3-REVIEW` / `READY-FOR-EVALUATION-B3-REVIEW`

- **Batch 3 合流前提**：3 个 READY trailer 齐 + 3 个 ACK 收齐,主 CLI review 通过后合流 main。任一 REJECT 走 V2 返工。
- **Phase 4 启动**：Batch 3 全 APPROVED 合流后,主 CLI 启动 Phase 4 · 前端整合 + 3 worker(agent1/3/6)漏合处置。
