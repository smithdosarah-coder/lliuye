# Phase 3-Final · 轨 1 · agent6 解冻 + 合流 Onboarding

**状态**：Phase 3-Final GO（待 user dispatch）
**发布日期**：2026-04-25
**Signal 入口**：`PHASE-3-FINAL-T1-ACK`
**前置**：commit `4f2132e ORCHESTRATOR-HANDOFF-PHASE-3-FINAL-PLANNED` + Q-032（Phase 3-F 总规划 · 推翻 Q-031 档 2/3 冻结 · 激活 agent6 branch 20 commit）
**参照决策**：`docs/handoff/decisions-log.md` Q-030（Batch 2 closeout）/ Q-031（Mesh 大清理 · 已被 Q-032 部分推翻）/ Q-032（Phase 3-F 8 轨规划） + `docs/handoff/session-2026-04-25-phase-3-final-handoff.md` §2.1 + §4.1 + `docs/scorecard/dod-current-status-2026-04-24.md` + `docs/scorecard/definition-of-done.md` v1.0
**worker 建议**：新建 worktree `code-agent6-unfreeze`（fork from `feat/agent6-v16` · 不在原 demo-agent6 worktree 上原地动 · 隔离 rebase 风险）

---

## 1. 背景与目标

agent6 branch（`feat/agent6-v16` · tip `4bf8361`）有 **20 commit 未合**，跨 Phase 1 + Phase 2 两个迭代周期。最近一次同步 main 是 `3fd57df merge: upstream/chore/l0-infra for A-013 α kernel`（α kernel 时代），期间 main 已前进 Batch 1 code-arch（EvidenceFirstPipeline 基类拆分）+ Batch 2（4 worker 全 APPROVED · code-urgent 前端 EvidenceTrail · data-foundation Phase 2 alert-pool · evaluation 真 baseline）。

**Q-031 档 2/3 把 agent6 冻结**，本任 Q-032 推翻——20 commit 含 L2/L3 对外交付级别的核心资产，**冻结 = 损失**：

| 价值档 | commit 数 | 解 DoD 条目 |
|---|---|---|
| 🔴 极高（Phase 1 finalize） | 10 | L2-12 审计日志 / L2-13 合作机构 / L2-14 数据分级 / L3-8 飞轮 E2E / L3-11 Agent6 模型卡 / L3-12 Agent6 演示脚本 |
| 🟡 中（Phase 2 硬化） | 10 | L2-4 QC Blocker 四维强化 / Phase 2 Task C 模板扩展 +2 脱敏样本（**预期缓解 Batch 2 baseline Agent6 FAIL 的 template_leakage 0.775**） |

**DoD 当前打分** post-Batch 2：L2 75% / L3 45%。本轨目标：通过 agent6 branch 合流将 L2 推到 ~85%、L3 拉到 ~60%。

**硬边界**：本轨**只做 rebase + 解冲突 + 回归**，不做新功能。所有 20 commit 内容已在 branch 内，worker 只负责让它们安全落 main。**红区禁动**：`financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py`——这三个文件是 v16 确定性计算 + QC 终审的核心，agent6 branch 若历史改过其中任意一个文件，必须停下 askout（Q-033），不要自行 force-resolve。

---

## 2. Task 清单

### Task A · rebase + 解冲突

**目标**：把 agent6 branch 20 commit 干净地 rebase 到 `origin/chore/l0-infra` 当前 tip（`4f2132e`）。

**步骤**：
1. 在新 worktree `code-agent6-unfreeze`（fork from `feat/agent6-v16`）执行
2. `git fetch origin chore/l0-infra`
3. `git rebase origin/chore/l0-infra`
4. 解冲突时**保留双方价值**：
   - **保留 main 侧**：Batch 1 code-arch 引入的 `EvidenceFirstPipeline` 基类继承（`agent_report/evidence_pipeline.py` / `section_generator.py` 的 base class 切换）+ Batch 2 code-urgent 的 EvidenceTrail 前端挂载 + Batch 2 evaluation 的 adapter 改动
   - **保留 agent6 侧**：audit_log hook（`8f1cd84`）/ 模型卡 + 演示脚本（`33d6295`）/ 合作机构 + 数据分级（`e12805c`）/ 飞轮 E2E（`ee936fe` / `a41bf33`）/ QC 四维强化（`2691875`）/ 模板扩展 +2 脱敏样本（`fe567f4`）

**主要冲突面预测**（按 handoff §2.1）：
- `agent_report/section_generator.py`（Batch 1 EvidenceFirstPipeline 基类 vs agent6 改动）
- `evaluation/runner/adapters/agent6_report.py`（H-A 时改过 + agent6 branch 也碰过 + Batch 2 evaluation 重写）
- `agent_report/evidence_pipeline.py`（Batch 1 新建 vs agent6 可能在旧路径上改）

**约束**：
- 冲突文件数 ≤ 4 · 超过立即停 + Q-033 askout，**不要 force-resolve**
- 红区文件 0 漂移：rebase 前后 `git diff origin/chore/l0-infra -- financial_analyzer.py quality_scorer.py truth_fill.py` 必须空
- rebase 用 `--rebase-merges` 还是线性 rebase 由 worker 视冲突复杂度决定 · 倾向线性

**完成信号**：commit message trailer `Signal: AGENT6-REBASE-CLEAN`

---

### Task B · v16 pipeline 回归

**目标**：rebase 后跑 v16 主管线，对比 Batch 2 baseline 确认跑分漂移 < 1%。

**步骤**：
1. 跑 `py v16_pipeline.py --source samples/经纬测绘_对公成稿A.docx --material samples`
2. 取 `quality_score_total` 数值
3. 对比 `evaluation/baselines/2026-04-26-real-run.md` 中 Agent6 报告的 `quality_score_total: 68.6`
4. 漂移计算：`abs(new - 68.6) / 68.6 < 0.01`

**约束**：
- 漂移 > 1% → **立即 abort**（`git rebase --abort` 或 `git reset --hard` 回 rebase 前），Q-033 askout 报告漂移幅度 + 怀疑 commit
- 不动样本文件本身（`samples/` 是测试基线 · 改了等于换了对照组）
- v16 跑通的同时若 Phase 2 Task C 模板扩展（`fe567f4`）确实**降低**了 template_leakage_rate（baseline 0.775 → 新值 < 0.775），在 final commit body 单独标注 · 这是预期受益

**完成信号**：commit message trailer `Signal: AGENT6-V16-REGRESSION-OK`

---

### Task C · pytest 全绿

**目标**：跑 `pytest tests/agent_report/ -v` 全绿。

**步骤**：
1. `cd` 到 rebase 后的 worktree
2. `pytest tests/agent_report/ -v`
3. 失败用例**先看是不是 rebase 解冲突时漏吸收 agent6 branch 的 fixture / 工厂方法**——若是，回到 Task A 补吸收
4. 失败若是真业务回归 → Q-033 askout

**约束**：
- 不删测试用例规避失败
- 不 mock 掉真实业务路径（Batch 1/2 的 EvidenceTrail / EvidenceFirstPipeline 测试必须真跑通）
- 红区相关测试（涉及 financial_analyzer / quality_scorer / truth_fill）必须全过 · 一个挂表示红区被动

**完成信号**：commit message trailer `Signal: AGENT6-PYTEST-GREEN`（可与 Task B 合并 commit）

---

### Task D · READY signal + 自检

**目标**：最终 commit 把 20 commit SHA + diff 白名单 + 解 DoD 条目自检全部塞进 body，主 CLI 据此 pre-review。

**body 必含**：
1. **20 commit SHA 清单**（按 handoff §2.1 表格分组 · 🔴10 + 🟡10 标注哪些 commit 在 rebase 中触发过冲突）
2. **`git diff origin/chore/l0-infra...HEAD --name-only`** 全列表（用于白名单校验）
3. **解 DoD 条目自检**（6 项 ✓/✗ 表格）：
   - L2-12 审计日志 jsonl
   - L2-13 合作机构清单
   - L2-14 数据分级标签
   - L3-8 反馈飞轮 E2E
   - L3-11 Agent6 模型卡
   - L3-12 Agent6 演示脚本
4. **红区 0 漂移声明**：`git diff origin/chore/l0-infra...HEAD -- financial_analyzer.py quality_scorer.py truth_fill.py` 输出（应为空）
5. **v16 跑分对比**：baseline 68.6 vs new XX.X · 漂移 X.X%（< 1%）
6. **template_leakage 受益**（如有）

**完成信号**：commit message trailer `Signal: READY-FOR-AGENT6-UNFREEZE-REVIEW`

---

## 3. 验收硬指标（T1-1 ~ T1-12 · 12 项）

| # | 指标 | 阈值 | 判定 |
|---|---|---|---|
| T1-1 | 4 段 Signal trailer 齐 | AGENT6-REBASE-CLEAN / AGENT6-V16-REGRESSION-OK / AGENT6-PYTEST-GREEN / READY-FOR-AGENT6-UNFREEZE-REVIEW（B+C 可合并 · 至少 3 个 commit） | `git log` grep |
| T1-2 | rebase 冲突文件数 ≤ 4 | 4 个文件以内可由 worker 自决 · 超过即 Q-033 | rebase log + worker 报告 |
| T1-3 | 红区 0 漂移 | `financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py` 三文件 diff 全空 | `git diff origin/chore/l0-infra...HEAD -- <files>` |
| T1-4 | v16 **rebase mechanic** drift < 1% | pre-rebase tip vs post-rebase HEAD 同 DP `quality_score_total` 偏差 < 1%（**NOT** vs 历史 baseline 68.6 · Phase 2 design-intent drop 不计 · 详见 Q-035） | `py v16_pipeline.py` pre-rebase + post-rebase 各跑一次 |
| T1-5 | pytest 全绿 | `pytest tests/agent_report/ -v` 0 fail / 0 error | pytest exit code 0 |
| T1-6 | 解 DoD 条目齐 6 项 | L2-12 / L2-13 / L2-14 / L3-8 / L3-11 / L3-12 全在 final body 自检 ✓ | body grep |
| T1-7 | 20 commit SHA 全列 | final commit body 含 20 个 SHA + 分组 + 冲突标注 | body grep |
| T1-8 | diff 白名单合规 | `--name-only` 输出限于：`agent_report/` / `tests/agent_report/` / `docs/model_cards/` / `docs/demo_script/` / `docs/compliance/` / `evaluation/runner/adapters/agent6_report.py` / `evaluation/rubrics/agent6_*` / `samples/` / `data/feedback/` 域内 _(illustrative · 不穷举 · 如有合理新路径 final body 备注即可 · 不阻 ready)_ | diff 校验 |
| T1-9 | A-024 路径规范 | `evaluation/runner/base_evaluator.py` / `cli.py` 未改 | stat 0 |
| T1-10 | 不 git push | worker 在自分支 commit 即可 · 不 push 到 origin | worker 自证 |
| T1-11 | EvidenceFirstPipeline 基类继承保留 | `agent_report/section_generator.py` 仍继承 Batch 1 引入的基类 | grep + 读代码 |
| T1-12 | template_leakage 受益声明 | 若 baseline 0.775 在 rebase 后 v16 跑出有变化 · final body 标注新值 + 是否归因到 `fe567f4` 模板扩展 | body 校验 · 允许"无显著变化"为合规答案 |

---

## 4. 红线

### ❌ 不动

- ❌ **红区 3 文件**：`financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py` —— v16 确定性计算 + QC 终审核心。agent6 branch 若历史改过任意一个文件，必须停 + Q-033，**不要自行 force-resolve**
- ❌ **rebase 冲突 > 4 文件**：立即停 + Q-033 askout，不强行解。冲突复杂度过高说明 agent6 branch 偏离 main 太远 · 主 CLI 决策是降级到 cherry-pick 还是分批 rebase
- ❌ **v16 rebase mechanic drift > 1%**（pre-rebase tip vs post-rebase HEAD 同 DP 比对）：立即 `git rebase --abort` 或 `git reset --hard` 回滚 · 报告漂移幅度 + 怀疑 commit。**注意**：post-rebase HEAD vs 历史 baseline 68.6 偏差是 Phase 2 design-intent drop（QC 四维强化 + 模板扩展使 score 自然变化）· **不在本红线范围**。详见 Q-035 决策档语义重新解读
- ❌ **不 git push**：worker 用 commit 在自分支汇报 · push 由主 CLI merge 后做
- ❌ **不改 `evaluation/runner/base_evaluator.py` / `cli.py`**：A-024 路径规范，agent6 branch 若改过必须 revert 改动
- ❌ **不删测试 / 不 mock 真实路径**：pytest 失败查根因，禁规避

### ✅ 必做

- ✅ 新 worktree `code-agent6-unfreeze`（fork from `feat/agent6-v16`） · 不在 demo-agent6 原地动
- ✅ 每 Task 独立 commit · trailer 单行 Signal（B+C 可合并一个 commit · 4 段 trailer 拆 4 个 commit 也可）
- ✅ Final commit body 必含：20 commit SHA + 分组 + 冲突标注 + diff --name-only + 解 DoD 6 项自检 + 红区 0 漂移声明 + v16 跑分对比
- ✅ 保留 Batch 1 code-arch `EvidenceFirstPipeline` 基类继承 + Batch 2 code-urgent EvidenceTrail 挂载
- ✅ 红区文件被冲突牵连时 Q-033 askout · 等主 CLI 裁决再继续

---

## 5. 工期

- Task A · rebase + 解冲突 · 1-1.5 天（视冲突复杂度）
- Task B · v16 回归 · 0.5 天（含跑 + 对比 + 写报告）
- Task C · pytest · 0.25 天（顺利情况；有 fixture 漏吸收回 A 修补则加 0.5 天）
- Task D · final commit + 自检 · 0.25 天
- 合计 **2-3 天**
- **允许 REJECT-V2 一轮返工**（rebase 复杂度高 / v16 漂移触线 / pytest 漏吸收三类典型返工原因）
