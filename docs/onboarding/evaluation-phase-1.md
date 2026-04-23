# evaluation (6 Agent 评估基线) Phase 1 Onboarding

**状态**：APPROVED
**发布日期**：2026-04-23
**Signal 入口**：`PRODUCT-HARDENING-BATCH-1-DISPATCHED`
**前置**：
- 代码审计（Q-023）发现：Agent6 有 v16 pipeline 跑分，其他 5 Agent 无基线
- `docs/contracts/rfc/20260418-evaluation-runner.md` 已立 RFC（base_evaluator + per-agent adapter 形态）
- 首轮基线跑在**现有 samples**（data-foundation Batch 1 结果不成为本批次依赖——我们接受第一轮基线会"偏乐观"，Batch 2 拿真脏数据重跑做对比）

---

## 你是谁

你是 **evaluation** worker CLI，负责把 6 Agent 评估从"只有 Agent6 有数字"做到"6 Agent 都有可比基线"。你是 PM 产品决策的数字来源——没有你，PM 说"Agent5 合规好不好"只能靠感觉。

- Worktree：`D:/claude code/demo-evaluation`
- 分支：`feat/evaluation`（从 `chore/l0-infra` 分出）
- Upstream remote：`D:/claude code/credit_report_agent_work`

---

## 本批次任务

### 📋 Task A — 6 × rubric YAML

**目标**：为每个 Agent 产一份 `evaluation/<agent>.yaml`，10 条指标 = 5 通用（§5.1）+ 5 领域（§5.2 变体）。

**5 通用指标**（每 Agent 统一）：
- `field_completeness`（字段填充率）
- `evidence_rate`（证据溯源率）
- `hallucination_rate`（幻觉检出率）
- `tool_success_rate`（工具调用正确率）
- `task_completion_rate`（任务完成度）

**5 领域指标**（每 Agent 定制）：
- Agent1 channel：画像匹配精度 / 信号多样性 / NDCG@10 / 检索召回率 / 候选去重率
- Agent2 riskctrl：KS 值 / 通过率 / per_rule_fpr_spread / DSL 语法正确率 / 回测一致性
- Agent3 credit：财务比率正确率 / 红线判定准确率 / 评分一致率 / 术语规范率 / 额度建议合理度
- Agent4 alert：漏报率 / 误报率 / 信号多样性 / 分级准确率 / 处置建议命中率
- Agent5 compliance：政策覆盖率 / 冲突识别召回 / 缺陷分类准确率 / 术语规范率 / 证据完整性
- Agent6 report：保持 v16 pipeline 现有 unfilled_marker / halluc / evidence 等指标

每条指标需字段：
```yaml
- name: portrait_match_precision
  description: Top10 候选中匹配画像条件的比例
  method: top10_matches_criteria / 10
  baseline_target: 0.7
  blocker_threshold: 0.5  # 低于此分阻断发布
```

**模块路径**：
- 新建：`evaluation/agent1_channel.yaml` / `evaluation/agent2_riskctrl.yaml` / `evaluation/agent3_credit.yaml` / `evaluation/agent4_alert.yaml` / `evaluation/agent5_compliance.yaml`
- 更新：`evaluation/agent6_report.yaml`（已存在，对齐格式）
- 新建：`evaluation/README.md`（rubric 设计规范）

**指标/验证**：
- 6 份 YAML 用 `yamllint` 通过
- 10 条指标全部有 `method` 和 `baseline_target`

**工作量**：M（1.5 天，PM 协作定 baseline_target）
**完成信号**：`Signal: EVAL-RUBRIC-YAML-6AGENT-DONE`

---

### 🏗️ Task B — base_evaluator + 6 per-agent adapter

**目标**：按 RFC `20260418-evaluation-runner.md` 的形态抽出 `evaluation/base_evaluator.py`（复用 Agent6 v16 pipeline 经验），6 个 per-agent adapter 各自实现领域逻辑。

**模块路径**：
- 新建：`evaluation/base_evaluator.py`（BaseEvaluator 基类：load_rubric / run_cases / score / report）
- 新建：`evaluation/adapters/agent1_adapter.py` / `agent2` / `agent3` / `agent4` / `agent5` / `agent6` × 6
- 复用：Agent6 的 `v16_pipeline.py` 作为 base 的底层执行参考（不要改它，只借鉴结构）
- 新建：`evaluation/cli.py`（命令行入口：`py evaluation/cli.py --agent channel --rubric evaluation/agent1_channel.yaml --samples samples/ --out evaluation/baselines/`）

**指标/验证**：
- `py evaluation/cli.py --agent report --rubric evaluation/agent6_report.yaml` 跑出的数字与 v16_pipeline.py 跑出的一致（误差 < 1%，验证基类不破坏 Agent6 行为）
- 其他 5 Agent 都能跑出首轮数字（数字不一定达标，本任务只要求"能跑出")

**工作量**：L（3 天）
**完成信号**：`Signal: EVAL-RUNNER-BASE-DONE`

---

### 📈 Task C — 首轮基线跑分

**目标**：用现有 `samples/` + `customer/`（不等 data-foundation Batch 1）跑 6 Agent 首轮基线，产出数字。

**模块路径**：
- 新建：`evaluation/baselines/2026-04-23-first-run.json`（6 Agent × 10 指标的 JSON）
- 新建：`evaluation/baselines/2026-04-23-first-run.md`（人读版，含 gap 最大的 3 条每 Agent + 改进建议）
- 更新：`evaluation/README.md` 加"如何读基线"小节

**指标/验证**：
- 6 Agent 全部跑完，无 crash
- JSON 数字可被任何图表工具读取
- markdown 报告 PM 10 分钟内能读完

**工作量**：S（0.5 天，大头在 Task B 已做完）
**完成信号**：`Signal: EVAL-BASELINE-FIRST-RUN`

---

## 完成后

所有 Task 做完：`Signal: READY-FOR-EVALUATION-B1-REVIEW`

**警示**：第一轮基线分数会"偏乐观"（因为 mock 数据太简单，见 PM 判断）。Batch 2 等 data-foundation Batch 2 的真脏数据落地后重跑，对比看真实 gap。本轮数字作为"参照起点"，不作为产品达标证据。

## 红线

- ❌ 不改 `v16_pipeline.py` / `v16_generator.py` 等 Agent6 核心文件（只借鉴结构，不动行为）
- ❌ 不改 `agent_*/` 的业务代码（那是 code-urgent / code-arch 的地盘，评估只消费产出）
- ❌ 不碰 data-foundation 的 `data/mock/` 目录
- ✅ `evaluation/` 全权你负责
- ✅ 可以 read 所有 Agent 代码 + Agent6 v16 pipeline 实现作为参考
- ✅ 需要改 Agent 输出接口时（为了让 evaluator 更好消费），**开 RFC 给主 CLI**，不要自己动

## ACK 协议

1. Resume → commit doc-only，trailer `Signal: PRODUCT-HARDENING-BATCH-1-ACK`
2. Task A → B → C 顺序，每 Task 独立 commit 带对应 signal
3. 全 Task 完成 → `READY-FOR-EVALUATION-B1-REVIEW`

**维护者**：主 CLI
**下次更新触发**：主 CLI APPROVE B1 或下发 B2（B2 = 真脏数据重跑）
