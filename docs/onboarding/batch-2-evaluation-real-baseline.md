# evaluation Batch 2 · 真基线重跑 + EV-12 跨 Agent 一致性

**状态**：DISPATCHED
**发布日期**：2026-04-24
**Signal 入口**：`BATCH-2-DISPATCHED`
**完成信号**：`READY-FOR-EVALUATION-B2-REVIEW`
**前置依赖**：
- Batch 1 已完成（`EVAL-RUBRIC-YAML-6AGENT-DONE` / `EVAL-RUNNER-BASE-DONE` / `EVAL-BASELINE-FIRST-RUN` 全部绿）
- HOLDING H-A 已合流（agent6 adapter 接 `v16_pipeline_summary.json` auto parse）
- data-foundation Batch 2 v2（`data/mock/deep-pillar/DP001-005` + `channel-kb/` + `compliance-kb/`）并行起，本批次真跑时节点需落地

---

## 1 · 背景与目标

### 现状

2026-04-24 首轮 baseline (`evaluation/baselines/2026-04-24-first-run.json/.md`) 跑完，md 开头明确挂警示：

> **本轮基线偏乐观**——mock 数据简单 / pending 指标占比高 / agent6 artifact 退化自比。本轮数字作"起点参照"，**非客户证据**。

首轮 verdict 分布：PASS 1 / PARTIAL 4 / FAIL 1。其中：

- agent1 channel / agent5 compliance：**全量 pending**，0/10 实算，红线闸门 🟡 N/A（无 runtime dump）
- agent3 credit：6/10 实算但 `credit_limit_reasonability = 0.0`（target ≤ 0.20），批准 case 的 requested==approved **没有额度调整**是 mock 偏乐观铁证
- agent6 report：`template_leakage_rate = 1.0` 是骨架自比伪阳性，非真实 gap
- **EV-12 `ratio_calc_consistency`**：Batch 1 标注 pending，原因是 Agent3 mock cases 里 `debt_ratio` 是预填静态值，**无 runtime 比率运算**——需等 code-urgent §3.1 `financial_analyzer` runtime 接入 Agent3 后才能对照。该接入已在 code-urgent H-A 合流。

### 目标

1. **换真脏数据**：Agent6 / Agent1 / Agent5 的 artifact 生成路径，从老 `samples/` 换到 data-foundation v2 的 `data/mock/deep-pillar/DP001-005` + 两个 KB。
2. **出 Batch 2 真基线**：`evaluation/baselines/2026-04-26-real-run.json/.md`，md 移除"偏乐观"警示，补"对比首轮差值"表——真数比首轮低多少，就是首轮估高多少 lift，这是**给 PM 的客户证据**。
3. **解锁 EV-12**：`ratio_calc_consistency` 从 pending 变实算，跑 Agent6 管线 + Agent3 决策链对同一家企业的 `financial_analyzer` 字段做 ≥99% 一致性校验，任一企业低于 99% → blocker_threshold 阻断发布。

---

## 2 · 你是谁 · 作业环境

你是 **evaluation** worker CLI。

- **Worktree**：`D:/claude code/demo-evaluation`
- **分支**：`feat/evaluation`（从 `chore/l0-infra` 分出）
- **Upstream remote**：`D:/claude code/credit_report_agent_work`
- **身份文件**：`AGENT_IDENTITY.md`（本地非 checked-in，resume 窗口用）

**你是 PM 产品决策的数字来源**。Batch 2 真基线是"能不能对外讲 Agent 效果"的唯一客观证据，"首轮偏乐观" 警示必须在本批次撤掉。

---

## 3 · Task 清单

### Task A · 6 Agent 真 baseline 重跑 · Signal `BASELINE-REAL-DONE`

**目标**：用 data-foundation v2 的真脏数据包 + 两个 KB 重跑 6 Agent 基线，产 `evaluation/baselines/2026-04-26-real-run.json/.md`。

**执行策略**（按 Agent 分层）：

| Agent | 数据源 | 执行方式 | 备注 |
|---|---|---|---|
| agent6 report | `data/mock/deep-pillar/DP001-005/<企业>.docx` × 5 | `py v16_pipeline.py --source data/mock/deep-pillar/DP00X/<doc>.docx --material data/mock/deep-pillar/DP00X/` 逐家跑 | artifact 入 `outputs/` 留档；adapter 靠 `v16_pipeline_summary.json` 自动读数（H-A 路径） |
| agent1 channel | `data/mock/channel-kb/` + SearchProvider 真搜 | `agent_channel.api.py` 搜索 endpoint 启 runtime dump；Tavily 无 key 时降级 `MockSearchProvider`（明确 md 标注） | 本批次先解 runtime dump 4 条指标，不追 NDCG |
| agent5 compliance | `data/mock/compliance-kb/` + 真搜 | `agent_compliance.api.py` scan endpoint 启 runtime dump，conflict_items + extracted_clauses 写 `evaluation/manual/5_latest.json` | 同上降级策略 |
| agent3 credit / agent4 alert / agent2 riskctrl | 保留老 `samples/` | 不动 fixture 路径，沿用 Batch 1 结果 | Batch 2 Phase 2 才扩，本轮只改 Agent6/1/5 |

**产出**：
- `evaluation/baselines/2026-04-26-real-run.json`：6 Agent × 10 指标 JSON，schema 与首轮一致
- `evaluation/baselines/2026-04-26-real-run.md`：人读版，必须包含——
  - **移除**首轮 md 的"偏乐观"警示段（不留残影）
  - **新增**"对比 2026-04-24 首轮差值"表：每 Agent 实算指标逐条对比首轮 → 本轮，diff 用 +/- 标绝对差值 + 百分比 lift
  - **新增**"首轮高估幅度"结论段：哪些 Agent / 指标在首轮被高估、幅度多少、说明首轮 mock 数据简单到什么程度
  - 保留 verdict / 红线闸门 / 实算/pending 分布 / gap top 3 结构

**验收**：
- `py -m evaluation.runner --all` 全 6 Agent 无 crash
- agent6 对 DP001-005 5 家企业都跑出真 v16 summary JSON（不再是骨架自比）
- agent1 / agent5 的 pending 条数从 10/10 降到 ≤ 6/10（解 runtime dump 相关 4 条）
- md 中"对比首轮差值"表至少覆盖 18 项实算指标（6 Agent × 平均 3 项）

**工作量**：L（2 天）

---

### Task B · EV-12 ratio_calc_consistency 实现 · Signal `EV-12-RATIO-CONSISTENCY-DONE`

**目标**：跨 Agent6 报告管线 + Agent3 决策链对同一企业做 `financial_analyzer` 字段一致性校验，解锁首轮 pending 的 `ratio_calc_consistency` 指标。

**实现点**：

1. **adapter 落地**（两处）：
   - `evaluation/runner/adapters/agent3_credit.py`：新增 `_extract_financial_ratios(case_id)` 方法，从 Agent3 决策链调用 `financial_analyzer` 抽取 `current_ratio` / `debt_ratio` / `roe` / `gross_margin` 4 个关键比率
   - `evaluation/runner/adapters/agent6_report.py`：新增同名 `_extract_financial_ratios(doc_id)` 方法，从 Agent6 `v16_pipeline_summary.json` 或旁路 `financial_analyzer` 直调抽取相同 4 个字段

2. **一致性判定逻辑**（新建 `evaluation/runner/cross_agent/ratio_consistency.py`）：
   ```python
   def check_ratio_consistency(enterprise_id: str, tolerance: float = 0.01) -> RatioConsistencyResult:
       """
       对同一企业（DP001-005）喂 Agent3 决策链 + Agent6 报告管线
       抽 financial_analyzer 产出的 4 个比率字段
       逐项对比，允许 ≤1% 浮点误差
       返回 { ratio_name: (agent3_value, agent6_value, match_bool, abs_diff, pct_diff) }
       """
   ```
   - 对每家 DP00X 企业独立算一次，5 家全部聚合为 `ratio_calc_consistency = 匹配项数 / 总项数`
   - 目标：≥ 99%（允许 5×4=20 项里最多 0 项严格 > 1% 误差，浮点边界放宽到 1.0% 含）
   - blocker_threshold：< 99% 阻断本批次发布

3. **挂 baseline**：
   - agent3 credit + agent6 report 两份 baseline JSON 各新增 `ratio_calc_consistency` 字段，method 标 `deterministic_cross_agent`
   - agent3 的 `agent3_credit.yaml` 把 `ratio_calc_consistency` 的 pending 豁免撤掉，`blocker_threshold: 0.99`
   - agent6 的 `agent6_report.yaml` 里 `financial_ratio_consistency` 改名为同一语义（若未改则 adapter 补映射），`blocker_threshold: 0.99`

**验收**：
- 对 DP001-005 5 家跑完 `ratio_calc_consistency`，得出单一数字
- 数字 ≥ 99% → Task 通过；< 99% → 作为 blocker 上报主 CLI，不要自动 revert，交 PM 裁决（可能是 `financial_analyzer` 实现漂移了，得先修代码再重跑）
- `ratio_consistency.py` 有单测 `tests/runner/test_ratio_consistency.py` 覆盖：完全一致 / 1% 边界 / 超出 1% / 单边缺字段 4 个 case

**红线**：跨 Agent 调用**只读不改**——adapter 侧调 `financial_analyzer` 是消费，**不改 `financial_analyzer.py` / `agent_credit/` / `agent_report/` / `v16_*.py` 任何业务代码**。若消费路径不通（如 Agent3 决策链没暴露 financial_analyzer 字段），开 RFC 给主 CLI 要求 code-urgent 补出口，不要自己下手。

**工作量**：M（1.5 天）

---

### Task C · Agent1 / Agent5 召回率精确度指标 · Signal `AGENT1-5-METRICS-DONE`

**目标**：接 code-arch Batch 2 产出的 Agent1/5 外搜 integration test oracle 标注，把 Agent1 的 `precision@10` / `recall@10` 和 Agent5 的 `coverage` / `false_positive_rate` 从 pending 变实算。

**实现点**：

1. **agent1 channel adapter**（`evaluation/runner/adapters/agent1_channel.py`）：
   - 新增方法 `_load_oracle_annotations(source: str = "code-arch-b2")` 读 code-arch 交付的 `evaluation/manual/1_oracle.json`（预期格式：每条查询 × Top20 候选 × is_match bool 标注）
   - 新增指标计算：`precision_at_10 = hit@10 / 10`，`recall_at_10 = hit@10 / total_gold`
   - 接入 rubric：`agent1_channel.yaml` 已有占位的 `precision_at_k` / `recall_at_k` 两条 pending 指标，撤 pending

2. **agent5 compliance adapter**（`evaluation/runner/adapters/agent5_compliance.py`）：
   - 类似地读 `evaluation/manual/5_oracle.json`（预期格式：每条政策 × 已知冲突点 × detect_or_not）
   - 新增 `policy_coverage = detected_conflicts / total_gold_conflicts`，`false_positive_rate = false_alarms / all_detections`
   - 接入 rubric：`agent5_compliance.yaml` 里 `policy_coverage` / `conflict_recall` 撤 pending

3. **stub 路径（若 code-arch Batch 2 未完）**：
   - oracle 文件不存在时，adapter 走 stub 分支，返回预定值（precision=0.5 / recall=0.5 / coverage=0.5 / fp_rate=0.2），method 标 `stub_awaiting_code_arch_b2`
   - baseline md 标注 "code-arch B2 未到位，本轮用 stub 值，待合流后重跑"

**验收**：
- code-arch B2 到位：oracle JSON 存在时 adapter 真跑出数
- code-arch B2 未到位：stub 值写入 baseline，标注清晰，**不以 stub 数谎称真基线**
- Agent1/5 pending 条数从 10/10 进一步降至 ≤ 4/10（Task A 解 4 条 + Task C 解 2 条）

**工作量**：S（0.5 天实做 + 0.5 天等 code-arch 同步或补 stub）

---

## 4 · 红线（硬约束）

- **只动 `evaluation/` + `evaluation/baselines/`** ——Task A/B/C 所有代码改动、产出 JSON/MD 全在此两目录内。
- **不动 `v16_pipeline.py` / `v16_generator.py` / 所有 `v16_*.py`**——Agent6 主管线代码是 code-urgent / code-arch 地盘，本批次只消费产出。
- **不动 `agent_*/` 业务代码**——Agent3/6 的 `ratio_calc_consistency` 是跨 Agent 消费，adapter 侧调 `financial_analyzer` 为只读，业务代码一行不改。
- **不动 `data/mock/`**——data-foundation Batch 2 的地盘，evaluation 只读。若发现 DP00X 材料字段缺失或格式异常，**开 issue / RFC 给主 CLI**，不要自己动手补数据。
- **不动 rubric YAML schema**——`agent1_channel.yaml` 到 `agent6_report.yaml` 6 份 schema 不变，**只允许**把已有 pending 豁免的指标撤 pending（因为本批次解开了它们），或改 `blocker_threshold` 值（如 EV-12 的 0.99）。**不新增指标**，新加指标走 Batch 3。
- **依赖 code-arch Batch 2 Task C 是软依赖**：code-arch 未完时 Task C 走 stub 分支推进，不卡 Task A/B。若 code-arch 完了再回跑一次 Task C 即可。
- **每 Task 独立 commit**：A → B → C 顺序，每个 Task 标完成立即 commit 带对应 Signal trailer（`BASELINE-REAL-DONE` / `EV-12-RATIO-CONSISTENCY-DONE` / `AGENT1-5-METRICS-DONE`），不要攒到最后打一个大 commit。全 3 Task 完 → 最终 commit 带 `READY-FOR-EVALUATION-B2-REVIEW`。

---

## 5 · 硬指标（验收清单）

| # | 指标 | 目标 | 检查方法 |
|---|---|---|---|
| 1 | `evaluation/baselines/2026-04-26-real-run.json` 存在 | ✅ | 文件存在且 JSON 合法 |
| 2 | 真基线覆盖 6 Agent 60 数值槽 | ≥ 54 槽有真数（剩余 ≤ 6 槽可 pending，标注原因） | JSON grep `method: deterministic*` 计数 |
| 3 | EV-12 跨 Agent 财务比率一致性 | ≥ 99%（DP001-005 5 家 × 4 比率 = 20 项） | `ratio_consistency.py` 输出 |
| 4 | Agent1/5 精确度/召回 plug-in 代码存在且可跑 | ✅（可 stub 值） | adapter import + 单测过 |
| 5 | baseline md "对比 2026-04-24 差值"表 | 存在且 ≥ 18 项对比 | MD 表行数 |
| 6 | baseline md "首轮高估幅度"结论段 | 存在且指名道姓（Agent / 指标 / lift） | MD 有 "首轮高估" 关键段 |
| 7 | 首轮 md 的"偏乐观"警示在本轮 md 中移除 | ✅ | 本轮 md 不含"偏乐观"字样 |
| 8 | 每 Task 独立 commit 带 Signal trailer | 3 个 Signal commit | `git log --grep Signal` |

---

## 6 · ACK 协议

1. **Resume**：读 `AGENT_IDENTITY.md` → commit doc-only ACK，trailer `Signal: BATCH-2-ACK`
2. **Task A** → commit `Signal: BASELINE-REAL-DONE`（含 JSON + MD）
3. **Task B** → commit `Signal: EV-12-RATIO-CONSISTENCY-DONE`（含 cross_agent 模块 + 单测 + baseline 更新）
4. **Task C** → commit `Signal: AGENT1-5-METRICS-DONE`（含 adapter 改动 + stub/真跑分支）
5. **全 Task 完** → 最终收尾 commit `Signal: READY-FOR-EVALUATION-B2-REVIEW`（baseline md 终稿 + 3 Task 合璧）

**Blocker 喊停条件**：
- data-foundation Batch 2 的 `data/mock/deep-pillar/` 真未到位 → 等；不要自己造数
- EV-12 跑出数字 < 99% → 上报主 CLI，可能是 `financial_analyzer` 漂移，不自己修
- code-arch Batch 2 oracle 未到位 → Task C 走 stub 分支，不等

**维护者**：主 CLI
**下次更新触发**：主 CLI APPROVE B2 或下发 B3

---

## 7 · Kickoff Prompt（新窗口 resume 用 · 复制粘贴）

```
你是 evaluation worker CLI。worktree 在 D:/claude code/demo-evaluation，分支 feat/evaluation。
请读 AGENT_IDENTITY.md 和里面列的所有文件（onboarding / decisions-log / contracts / 最近
signal commit）resume 状态。本批次进 Batch 2，onboarding 单是：
docs/onboarding/batch-2-evaluation-real-baseline.md

总目标：用 data-foundation v2 真脏数据（data/mock/deep-pillar/DP001-005 + channel-kb/
+ compliance-kb/）重跑 6 Agent 基线 + 解锁 EV-12 跨 Agent 财务比率一致性 + Agent1/5 精
确度召回指标。3 个 Task 顺序跑，每 Task 独立 commit 带 Signal trailer。

红线：只动 evaluation/ 和 evaluation/baselines/，不动 v16_* / agent_*/ / data/mock/ / rubric
schema。EV-12 跨 Agent 是消费 financial_analyzer 只读不改。依赖 code-arch Batch 2
oracle 若未到位，Task C 走 stub 分支推进，不卡 Task A/B。

全部 Task 完成后 commit Signal: READY-FOR-EVALUATION-B2-REVIEW。

Resume 完汇报：当前 phase / 已理解的 3 Task 范围 / 准备先跑哪个 Task / 有无 blocker，
然后停下等我 GO。
```
