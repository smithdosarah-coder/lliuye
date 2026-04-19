# Agent6 报告 · Phase 2 Productize Onboarding（97% → L3 Bank Delivery）

**对应 worktree**：`D:\claude code\demo-agent6`（`feat/agent6-v16`）
**发布日期**：2026-04-19
**前置**：已读 `AGENT_IDENTITY.md` + `CLAUDE.md` + 本文 + `docs/review/agent6-phase-1-finalize-review.md` + `docs/handoff/decisions-log.md`（尤其 A-012.D / A-013 / A-009）
**目标**：把 Agent6 从「97% / Phase 1 Finalize APPROVED」推到「**Phase 2 APPROVED · L3 bank delivery ready**」（scorecard ≥ 99%，L3 12 条全绿）。

---

## 0. 背景（3 行速读）

今天 Phase 1 Finalize APPROVED（`5acb74b` / Signal `AGENT6-PHASE-1-FINALIZE-READY-FOR-REVIEW`）——**全局 scorecard 97%，6 Agent 里最高**，离 L3 bank delivery 只差临门一脚。同日 Agent1 Phase 1 APPROVED 带出两套可复用契约：A-013 `baseline.pending_metrics` 豁免机制（kernel 已落）+ A-012.D SHA 不可变。本 Phase 2 的硬任务：**补齐 L3 层 12 条里尚挂的 4 类尾巴——审贷员反馈 round-trip、QC Blocker 四维强化、≥2 银行真实模板样本、pending 语义对齐 A-013**——让 Agent6 获得「可推北部湾客户 POC」的 L3 验收。

---

## 1. 范围 & 不做什么

### L3 bank delivery 定义（对齐 `memory/project_bank_delivery_dod.md`）

| 层 | 本 Phase 交付项 | 当前状态 |
|---|---|---|
| L0 工程基础 | 能跑、密钥外置、P95 ≤ 1s、日志脱敏 | ✅ Phase 0 已达成 |
| L1 Demo 完整 | ≥ 2 场景、三区块布局、可视化、导出、ink 主题 | ✅ Phase 1 骨架期已达成 |
| L2 金融合规 | 证据链 / 零幻觉 / 确定性 Python 算 / 审计日志 / 合作机构 / 数据分级 | ✅ Phase 1 Finalize 补齐（`8f1cd84` / `e12805c`） |
| **L3 客户 POC** | **evaluation baseline 回归 + Mock/Web 双模 + 反馈飞轮 + 模型卡 + 演示脚本 + 真人样本 round-trip** | ⚠️ 部分达成（模型卡 / 演示脚本 / E2E 已通；真人样本 round-trip + Blocker 四维 + 模板扩展未完）→ **本 Phase 做** |
| L4 商业交付 | 私有化包、信创、SLA、等保、备案、定价 | ❌ 本 Phase **不做**（商业 BD 触发） |

本 Phase 2 = 「L3 12 条里剩下的 4 条一次性补齐 + 让 L3 绿透」。

### 不做什么（明确排除，防 scope creep）

- ❌ **不做 autopilot**：仍 copilot——审贷员审核后才用，不下自动授信/放款决策（对齐 CLAUDE.md §9）
- ❌ **不做 SFT / fine-tune**：走 few-shot 注入 + feedback loop 飞轮（CLAUDE.md §6），对齐 Agent1 Phase 1 D2 方案
- ❌ **不做 L4 商业交付**：私有化包 / SLA / 等保自检推 Phase 3，依赖外部合规批文
- ❌ **不动 Evidence-First 三阶段**：`section_generator.py` 的 evidence assembly → grounded → self-audit 协议是红线（CLAUDE.md §3.3），Task B 只在**协议之外**加 Blocker 闸门，不改三阶段流程
- ❌ **不动 v16 pipeline 内核**：`v16_classifier.py` / `v16_generator.py` / `v16_op_handlers.py` 仍属质量线红区（`memory/project_v16_pipeline_architecture.md`），Rule 17 unfilled_marker 0.625 gap 等外部触发
- ❌ **不做前端 Shell 接入**：等前端 Stage 3 解耦，本 Phase 只保 API 形态
- ❌ **不跨 Agent 编排**：Agent6 边界止于 `ReportJSON` + Word 导出（CLAUDE.md §4），不触发 Agent3 决策

---

## 2. 前置条件

- 主 CLI HEAD：Phase 1 Finalize APPROVED 之后（`5acb74b` 或后续 Phase 2 onboarding commit）
- worker 起点：`feat/agent6-v16` @ `5acb74b`（Phase 1 Finalize READY-FOR-REVIEW tip）
- `git fetch upstream && git rebase upstream/chore/l0-infra` 拿到本 onboarding 再开工
- **A-013 runtime 就绪**：`evaluation/runner/base_evaluator.py` L96 已支持 `baseline.pending_metrics` 白名单豁免，Agent6 yaml 直接用，不需改 kernel
- Phase 1 Finalize 基线（不许倒退）：
  - `pytest agent_report/tests/test_feedback_e2e.py -v` = **5 passed**
  - `py -m evaluation.runner --agent report` 当前 verdict 受限于 Phase A stub（`financial_ratio_consistency` 等 passed=None），本 Phase 要把它改 PASS
  - `data/audit/*.jsonl` 可落盘 / `/api/feedback` 可写 `data/feedback/*.jsonl`
  - `docs/model_cards/agent6.md` 155 行 + `docs/demo_script/agent6.md` 176 行已落

---

## 3. Task 清单（4 Task，预计 2.5-3.5 工时，比 Phase 1 Finalize 重）

### Task A · 审贷员反馈 round-trip（对齐 Agent1 Phase 1 D2 模式 · L3-8 深化）

**goal**：把 Phase 1 已打通的「`/api/feedback` 能写盘」升级成「**能回注到 prompt**」——审贷员修改 → `data/feedback/6_*.jsonl` → 抽取脚本 → `prompts.py` sentinel 块 few-shot 注入 → 下一次报告生成体现。这是 L3-8 反馈飞轮的**第 4 环闭环**（对齐 CLAUDE.md §6 第 4 环"提示词优化"）。

**modules**：
- `scripts/feedback_extract_agent6.py`（新建）：从 `data/feedback/6_*.jsonl` 读取 `{user_correction, correction_reason}`，聚类成 few-shot 示例；输出到中间产物 `data/feedback/extracted/6_YYYYMMDD.yaml`
- `prompts.py`（worker 可改，非红区）：在 `CHAPTER_PROMPTS` 上方插 `# <AGENT6_FEEDBACK_FEWSHOT:BEGIN>` / `:END>` sentinel 块，里面放 **≤ 5 条** bootstrap few-shot 示例；运行时注入 `AGENT_SYSTEM_PROMPT` 尾部
- `scripts/feedback_smoke_agent6.py`（新建）：端到端冒烟——`POST /api/feedback` 写 jsonl → 调 extract 脚本 → grep 出 sentinel 块 diff → 跑一次 `/api/report/fill` mock 确认 prompt 包含 feedback 指引
- **bootstrap 样本 5 条**（worker 先过一版，业务方二审后续）：
  1. **科创贷**（科技型企业知识产权出质、研发人员占比）
  2. **小微**（经营稳定性、纳税记录、水电气流水）
  3. **对私**（个人经营贷、家庭收入、征信查询次数）
  4. **涉农**（土地流转、农户联保、季节性现金流）
  5. **普惠**（小微批量白名单、快速审批话术）
- 每条样本结构：`{scenario, original_output, corrected_output, correction_reason, injection_hint}`；存 `data/feedback/bootstrap/6_{scenario}.yaml`

**deliverables**：
- 抽取脚本 ≥ 150 行，含 dedup（同 field_path 同 reason 取最新一条）
- prompts.py sentinel 块 diff 可见、注入点明确、不破坏 `AGENT_SYSTEM_PROMPT` 原意
- 5 bootstrap 样本 yaml 落盘
- `feedback_smoke_agent6.py` 5 步冒烟脚本（Phase 1 Task D 的 pytest 只到"写盘"，本 Phase 跑通到"prompt diff"）
- 在 `docs/progress/agent6-phase-2-feedback-loop.md` 记录一次**闭环 demo**：假造 1 条 correction → 证据链显示下一次生成确实引用了 few-shot → 贴 diff

**DoD**：
- [ ] `py scripts/feedback_smoke_agent6.py` 全绿（5 步 5 ✓）
- [ ] `git diff prompts.py` 在 sentinel 块内可见注入、块外零改动（`grep -c "AGENT6_FEEDBACK_FEWSHOT" prompts.py` = 2）
- [ ] `data/feedback/bootstrap/` 5 scenario yaml 全部 ≥ 6 行有效字段（non-empty `corrected_output` + `correction_reason`）
- [ ] 抽取脚本单测 ≥ 3 条（dedup / empty input / 格式不对）
- [ ] 红线闸门不倒退：`pytest agent_report/tests/test_feedback_e2e.py` = 5 passed

---

### Task B · QC Blocker 四维强化（对应 CLAUDE.md §8 · L2-15 深化到 L3）

**goal**：当前 `quality_check.py` 只覆盖两维（占位符残留、模板示例行业）；CLAUDE.md §8 要求**四维**——占位符 + 证据链完整性 + 财务数字与 `financial_analyzer` 一致 + 合规术语规范。本 Task 把四维硬闸集中到 `agent_report/quality_blocker.py`（新建），不通过**阻断输出**并显式标「未能自动填写」，零绕过。

**modules**：
- `agent_report/quality_blocker.py`（新建，≥ 200 行）：
  - `check_placeholder_residue(text)` —— 复用 `quality_check.py` 现有 regex 扩展（企业名占位符 `XX` / 数字占位符 `____` / 模板区间 `65-70%`）
  - `check_evidence_chain(sections)` —— 每条含数字的 claim 必须挂 `evidence_id`；无则判 `MISSING_EVIDENCE`
  - `check_financial_consistency(text, analyzer_output)` —— 正则抽取报告里的"同比/环比/营收/负债率"等数字，与 `financial_analyzer.format_for_prompt()` 输出比对，偏差 > 0.5pp 判 `NUM_MISMATCH`
  - `check_compliance_terms(text)` —— 合规术语白名单（"授信额度"/"还款来源"/"第一还款来源"）+ 违规黑名单（"肯定能"/"保证"/"承诺收益"）
  - `QualityBlocker.verify(report) -> BlockerResult`：4 维聚合，`blocked: bool` + `violations: list[{dim, code, snippet, evidence}]`
- `section_generator.py`（红区内**新增调用点**，不改三阶段协议）：Phase 3 self-audit 结束后追加一次 `QualityBlocker.verify`；不通过 → 该段文本替换为「未能自动填写（因 {dim}/{code}）」占位，不裸抛 exception（阻断输出语义 = 人可见的占位，不是 500）
- `agent_report/tests/test_quality_blocker.py`（新建）：**反向测试** 3 类失败用例 + 4 类正常用例，共 7 case

**deliverables**：
- `quality_blocker.py` 四维规则各自独立函数（便于单测）
- `section_generator.py` 新增 `if BLOCKER_ENABLED:` 调用块（diff ≤ 15 行，不动三阶段主流程）
- **反向测试**必须手工构造 3 类失败用例全部被拦：
  1. 故意把段落里留一个 `65-70%` 模板区间 → 应被 `PLACEHOLDER_RESIDUE` 拦
  2. 故意把 `evidence_id` 清空 → 应被 `MISSING_EVIDENCE` 拦
  3. 故意把营收数字改成 `financial_analyzer` 没有的 → 应被 `NUM_MISMATCH` 拦
- `grep -rn "override_blocker\|skip_blocker\|force=True" agent_report/` = 0（零绕过）
- 在 `docs/progress/agent6-phase-2-blocker.md` 记录：触发 blocker 时的用户可见信息是什么（不许裸 500，必须"这段因 XX 原因未能自动填写"）

**DoD**：
- [ ] `py -m pytest agent_report/tests/test_quality_blocker.py -v` = 7 passed
- [ ] 3 类反向用例全部被拦（测试里显式断言 `result.blocked is True`）
- [ ] `grep -rEn "override|skip|force_pass" agent_report/quality_blocker.py` = 0（零后门）
- [ ] 正常路径跑 `py -m evaluation.runner --agent report` 不倒退（Blocker 不误杀正常样本）
- [ ] 用户可见信息是「未能自动填写（因…）」占位，不是 exception stacktrace（手动验 1 个失败样本）

---

### Task C · 模板扩展 ≥ 2 个真实样本（L3 bank delivery 硬条件）

**goal**：当前 460 项基于 `samples/普惠申报书_骨架型.docx` 单模板；L3 要求「≥ 2 银行真实样本 round-trip」。本 Task 扩 ≥ 2 个真实脱敏模板 + 建立**适配层** `template_adapter.py`，让 v16 pipeline 不感知模板差异；每模板独立 baseline 落盘。

**modules**：
- `samples/`（可写，非红区）：
  - 保留现有 `普惠申报书_骨架型.docx` / `兴业资管_对公成稿B.docx` / `经纬测绘_对公成稿A.docx` 3 个
  - 新增 **≥ 2 脱敏模板**——worker ACK 时问主 CLI 哪 2 个场景优先（推荐：**科创贷模板** + **小微对私模板**，对齐 Task A bootstrap 覆盖）
  - 脱敏来源：`_backup_v723/` 里可能有历史样本、或从 `demo_data/` 改造；**无客户真实材料入 git**（CLAUDE.md §12 红线）
- `agent_report/template_adapter.py`（新建，≥ 150 行）：
  - 吸收模板间差异（章节编号不同、表格列名不同、勾选项子集不同）
  - 核心方法 `TemplateAdapter.detect(docx_path) -> TemplateProfile`：输出 `{template_id, chapter_schema, required_fields, optional_sections}`
  - `TemplateAdapter.normalize(raw_sections) -> NormalizedReport`：把 v16 pipeline 产物对齐到统一 schema
  - **不改** v16 内核 / `section_generator.py` 三阶段协议 —— adapter 只在 pipeline 入口和出口做 map
- `evaluation/agent6_report.yaml`（可写）：
  - 新增 `coverage_by_template` 指标段 + 每模板独立 `baseline_by_template: {template_id: {last_run, commit, result}}`
- `evaluation/runner/adapters/agent6_report.py`（**红区——worker 不可改**）：
  - 如需扩多模板消费，发 `Q-014` 请主 CLI 亲操
  - 初版可用：worker 先在 yaml 加配置，adapter 改动本 Phase 留给主 CLI 后续 Phase 3 处理

**deliverables**：
- `samples/` 至少 5 个 docx（原 3 + 新 2）
- `template_adapter.py` + 单测（每模板 ≥ 2 条 detect/normalize case）
- yaml `coverage_by_template` 字段落盘，每模板独立 baseline
- 跑 `py -m evaluation.runner --agent report --artifact samples/<每个模板跑一次>.docx`，每模板结果落 `evaluation/results/6_YYYYMMDD_{template_id}.yaml`
- `docs/progress/agent6-phase-2-templates.md` 列：每模板 P95 latency / QC Blocker 通过率 / unfilled_marker 值

**DoD**：
- [ ] ≥ 5 `samples/*.docx`（原 3 + 新 2）
- [ ] `template_adapter.py` 单测 = 4 passed（2 template × detect/normalize）
- [ ] 每模板跑 runner → `evaluation/results/6_*.yaml` ≥ 5 份落盘，**每份 verdict = PASS 或显式 pending**（不许 FAIL）
- [ ] yaml `coverage_by_template` 指标可 `yq` / grep 检索命中
- [ ] **不碰** `evaluation/runner/adapters/agent6_report.py` 红区（如需改动 Q-014）

---

### Task D · `pending_metrics` 语义对齐 A-013（Phase 2 级人工指标）

**goal**：Agent6 yaml 目前 5 个 domain + 5 个 common 指标，其中 `financial_ratio_consistency` / `section_length_calibration` / `quality_score_total` / `evidence_rate` / `hallucination_rate` 在 Phase A adapter 里都 `passed=None`（stub）。Phase 2 里我们有能力补 `quality_score_total`（`quality_scorer.py` runtime 可接）和 `evidence_rate`（Task B 后 Blocker 可顺手算），但 `hallucination_rate` / `section_length_calibration` 需要 **审贷员人工标注**——本 Phase 先走 pending 白名单让 runner verdict=PASS，真实标注推 Phase 3。

**modules**：
- `evaluation/agent6_report.yaml`（可写）：
  - `baseline` 段新增 `pending_metrics: [hallucination_rate, section_length_calibration]`
  - `pending_reason: "Phase-3 审贷员人工标注 round-trip"`
- `evaluation/runner/adapters/agent6_report.py`（**红区**）：
  - 无需改——A-013 kernel 已在 `base_evaluator.py` L96 消费 yaml `pending_metrics`；adapter 仍 emit `passed=None + note="Phase-3 pending human annotation"` 即可
  - 若 Task B 能接通 `quality_scorer.py` runtime，把 `quality_score_total` 从 stub 改 `passed=True/False`——worker 可在 adapter 里加，但**只加不删现有行**（A-009 add-only 自决授权）；如动 adapter 结构改动，发 Q-014

**deliverables**：
- yaml 加 `pending_metrics` + `pending_reason` 两行
- 若能接通 Task B 的 Blocker 副产物，把 `evidence_rate` 从 stub 改实值（可选，不 block DoD）
- `docs/progress/agent6-phase-2-pending.md` 记录：哪些指标 pending、为什么、什么场景触发 Phase 3 人工标注

**DoD**：
- [ ] `py -m evaluation.runner --agent report` verdict = **PASS**（不是 PARTIAL 也不是 FAIL）
- [ ] yaml `grep "pending_metrics"` 命中 2 行指标
- [ ] pending 指标仍 emit 到 `evaluation/results/6_*.yaml`（可见性保留）
- [ ] 若 Task B / Task C 产物让更多指标可实算，顺手改 `passed=True` —— **但不强制**，不改照过

---

## 4. 红区 & 硬规则

### 红区字面枚举（字面，含 Phase 1 / Phase 2 新增）

❌ 以下路径 worker **不得改动**；遇冲突只许保 upstream + abort + Q：

- `shared/**`
- `docs/contracts/**`
- `api_server.py`
- `agent_*/api/**`
- `evaluation/runner/__init__.py`
- `evaluation/runner/adapters/__init__.py`
- `evaluation/runner/base_evaluator.py`
- `evaluation/runner/registry.py`
- `evaluation/runner/cli.py`
- `evaluation/runner/__main__.py`
- **`evaluation/runner/adapters/agent6_report.py`**（Phase A 已稳，adapter 级扩展归主 CLI Phase 3 动）
- `docs/handoff/decisions-log.md`
- **确定性计算层**（CLAUDE.md §3.1 禁止 LLM 现场算，改动必 Q）：
  - `financial_analyzer.py`
  - `material_kb.py`
  - `truth_fill.py`
- **v16 内核**（`memory/project_v16_pipeline_architecture.md` 质量线专属）：
  - `v16_classifier.py`
  - `v16_generator.py`
  - `v16_op_handlers.py`
  - `v16_pipeline.py`
- **Evidence-First 三阶段协议主干**（CLAUDE.md §3.3，本 Phase 只在协议**外**加 Blocker 闸门）：
  - `section_generator.py` 的三阶段主流程——**可新增 ≤ 15 行 blocker 调用点，不动 evidence assembly / grounded / self-audit 逻辑**
- `quality_scorer.py` 9 维度打分逻辑（质量线红区）

允许 worker 动：

- ✅ `agent_report/**`（新建 `quality_blocker.py` / `template_adapter.py` / tests，不含 `api/` 子目录）
- ✅ `prompts.py`（sentinel 块方式注入 few-shot，diff 边界明确）
- ✅ `evaluation/agent6_report.yaml`（新增 pending_metrics / coverage_by_template 字段）
- ✅ `evaluation/results/6_*.yaml`（runner 产物）
- ✅ `scripts/feedback_extract_agent6.py` / `scripts/feedback_smoke_agent6.py`（新建）
- ✅ `samples/*.docx`（新增 ≥ 2 脱敏模板）
- ✅ `data/feedback/bootstrap/*.yaml` + `data/feedback/extracted/*.yaml`
- ✅ `docs/progress/agent6-phase-2-*.md`（worker 进度文档）
- ✅ `.gitignore`（add-only 扩展，A-009 授权 worker 自决）

### 硬规则

- **R-A smoke-must-test**（A-006）：每 Task commit message 声称跑过的冒烟命令，必须在**提交分支当前 HEAD** 上实测过再入 commit。违反 → review 自动 CONDITIONAL
- **R-B 一 commit 一 Signal**（A-006）：`git log --format='%b' HEAD -1` 自检 trailer 数量 = 1
- **R-C cherry-pick amend trailer**（A-006）：本 Phase worker 不会 cherry-pick，但若真遇到则必须 amend 从 worker signal 改主 CLI 视角
- **A-012.D SHA 不可变**：已被主 CLI review 文档引用过的 commit SHA 不可 rebase/amend/force-push，纠错用新 commit
- **Signal await semantics**（`memory/feedback_signal_await_semantics.md`）：每个 `READY-FOR-REVIEW` / `NEED-DECISION` = **隐式 await-proceed gate**，停下等主 CLI GO；不许自己一路推到底
- **Evidence-First 三阶段不许绕**（CLAUDE.md §3.3）：Task B 的 Blocker 在 Phase 3 self-audit 之**后**追加一次闸门，不能把 evidence assembly / grounded generation / self-audit 任意一阶段合并或跳过
- **无基线不改码**（CLAUDE.md §5.2）：所有质量类动作都要对标 runner 产物 `evaluation/results/6_*.yaml` 里的数字
- **字段填不了标「未能自动填写」**（CLAUDE.md §12）：Task B Blocker 触发时必须用这个字面，不是 "N/A" / "—" / "暂缺"

---

## 5. Signal 流程

| 时点 | Signal |
|---|---|
| 读完 onboarding | `AGENT6-PHASE-2-ACK` |
| Task A 完成 | `AGENT6-PHASE-2-TASK-A-DONE` |
| Task B 完成 | `AGENT6-PHASE-2-TASK-B-DONE` |
| Task C 完成 | `AGENT6-PHASE-2-TASK-C-DONE` |
| Task D 完成 | `AGENT6-PHASE-2-TASK-D-DONE` |
| 全部 ready | `AGENT6-PHASE-2-READY-FOR-REVIEW` |
| Review 通过收工 | `WINDOW-CLOSED-CLEAN` |
| 有疑问 | `NEED-DECISION Q-NNN`（下一个可用 **Q-014**，与 agent2/4 Phase 1 共享编号空间）|

ACK 命令：

```bash
git commit --allow-empty -m "ack(agent6): Phase 2 onboarding absorbed" -m "" -m "Signal: AGENT6-PHASE-2-ACK"
```

ACK commit 里顺手问：Task C 新增 2 模板选什么场景（推荐科创贷 + 小微对私）、Task D 是否顺手把 `quality_score_total` 从 stub 升实值。

---

## 6. DoD 汇总 / L3 达成度预期

### 全 Phase 终态

- [ ] runner `py -m evaluation.runner --agent report` verdict = **PASS**（A-013 pending 机制落地后应达成）
- [ ] `data/feedback/bootstrap/6_*.yaml` ≥ 5 scenario 全部落盘，每条 ≥ 6 行有效字段
- [ ] `prompts.py` sentinel 块可 grep 命中 `<AGENT6_FEEDBACK_FEWSHOT:BEGIN>` + `:END>` 各 1 次
- [ ] `py scripts/feedback_smoke_agent6.py` 全绿（5 步 5 ✓）
- [ ] `py -m pytest agent_report/tests/test_quality_blocker.py -v` = 7 passed
- [ ] `grep -rEn "override|skip|force_pass" agent_report/quality_blocker.py` = 0
- [ ] `samples/` ≥ 5 个 docx；每模板 `evaluation/results/6_*_{template_id}.yaml` 落盘
- [ ] `agent6_report.yaml` 含 `baseline.pending_metrics` + `coverage_by_template`
- [ ] 红线闸门不倒退：
  - `pytest agent_report/tests/test_feedback_e2e.py` = 5 passed（Phase 1 Finalize 基线）
  - `unfilled_marker_accuracy` ≥ 0.625（Phase A 基线，不许倒退；Rule 17 回归另一条线单独推）
  - `template_leakage_rate` ≤ 0.20（Phase A 基线 0.75-0.875 是骨架型复用特性，本 Phase 新增模板不许超 0.20）
- [ ] scorecard ≥ 99%（主 CLI review 更新 `docs/scorecard/GLOBAL.md`）
- [ ] **L3 客户 POC 12 条全绿**（主 CLI 逐条打分落 `docs/review/agent6-phase-2-review.md`）

### 任一红线不过

→ 写 `docs/progress/agent6-phase-2-gap.md` 记录 gap 原因，**不要**强改 adapter / fixture 让指标达标（CLAUDE.md §12）。

---

## 7. 时限 & 推进顺序

- 建议 **2.5-3.5 工时**（Phase 2 比 Phase 1 Finalize 重约 1 倍；Task C 模板脱敏是主要工作量）
- 顺序：**A → B → C → D → READY-FOR-REVIEW**
- Task A（反馈 round-trip）与 Task B（Blocker）无强依赖，可并行起草；但 A 先过，B 的反向测试能复用 A 的 bootstrap 样本
- Task C（模板扩展）依赖 B 的 Blocker 闸门对新模板正常路径不误杀 —— B 先绿 C 再开工
- Task D（pending 对齐）是 B+C 的 yaml 收尾，放最后
- 每 Task DONE 后主 CLI 可能发 mid-review 指令，worker 停等 GO 再进下一个 Task

---

## 8. Q/A

疑问 → `docs/handoff/decisions-log.md` append `## [Q-NNN]`（下一个可用 **Q-014**，与 agent2/4 Phase 1 共享编号空间）→ trailer `Signal: NEED-DECISION Q-NNN` → 等主 CLI append `### [A-NNN]`。

**特别注意**：
- 红区冲突（含新增的 `evaluation/runner/adapters/agent6_report.py` / `financial_analyzer.py` / `material_kb.py` / `truth_fill.py` / v16 内核 / `quality_scorer.py`）**立即 abort + Q**
- Task C 新增模板场景选择可在 ACK commit 里顺便问 Q-014
- Task B 的 `section_generator.py` 新增 blocker 调用点**本身**就是红区动作——本 onboarding 已预批 **≤ 15 行 add-only 调用** 作为唯一豁免，超出必须先 Q；任何三阶段协议语义修改即使 1 行也先 Q
- 若 Task D 发现 adapter 需改（如把 `quality_score_total` 从 stub 升实值但 emit 形态变化），发 Q-014/Q-015 请主 CLI 亲操 adapter 红区

---

## 9. L3 Bank Delivery 达成度预判

| L3 条目（12 条）| 当前状态 | 本 Phase 动作 | Phase 2 后预期 |
|---|---|---|---|
| L3-1 evaluation YAML 跑 baseline 落盘 | ✅ Phase A | Task D 升 PASS verdict | ✅ |
| L3-2 baseline 回归机制 | ✅ | 不动 | ✅ |
| L3-3 Mock/Web 双模 | ✅ | 不动 | ✅ |
| L3-4 Playwright E2E | 前端另一条线 | 不动 | — |
| L3-8 反馈飞轮 E2E | ✅ Phase 1 至"写盘" | **Task A 推到"回注 prompt"** | ✅ 全环 |
| L3-9 QC Blocker 零绕过 | ⚠️ 2 维 | **Task B 四维强化** | ✅ |
| L3-10 真实样本 round-trip ≥ 2 | ❌ | **Task C 新增 ≥ 2 模板** | ✅ |
| L3-11 模型卡 | ✅ Phase 1 Finalize | 不动 | ✅ |
| L3-12 演示脚本 | ✅ Phase 1 Finalize | 不动 | ✅ |
| L3-其它 | ✅ 或 Phase 3 | — | — |

**Phase 2 APPROVED 条件**：L3 12 条里本 Phase 动的 4 条（L3-1 verdict / L3-8 回注 / L3-9 Blocker / L3-10 模板）全绿 + 红线闸门不倒退 + 零红区越界。

---

## 附：参考文件速查

- Review 依据：`docs/review/agent6-phase-1-finalize-review.md`（Phase 1 Finalize APPROVED 详情）
- 契约基线：`docs/handoff/decisions-log.md` A-006 / A-009 / A-012.D / A-013（pending 机制 kernel 已落）
- 对齐模板：`docs/onboarding/agent1-phase-1.md`（Phase 1 格式 · 本 Phase 2 结构对标）
- L3 定义：`docs/scorecard/definition-of-done.md` v1.0 + `memory/project_bank_delivery_dod.md`
- 全局看板：`docs/scorecard/GLOBAL.md`
- Evidence-First 协议：`memory/project_evidence_first_protocol.md` + `section_generator.py` 三阶段
- v16 架构（不改，仅参考）：`memory/project_v16_pipeline_architecture.md`
- CLAUDE.md：§3.1（确定性/概率性）/ §3.3（Evidence-First）/ §5（评估）/ §8（QC Blocker）/ §12（开发约束）
- Runner framework（红区，只读）：`evaluation/runner/base_evaluator.py` L96 pending 白名单消费点
- Phase 1 Finalize 产物（基线不许倒退）：`agent_report/tests/test_feedback_e2e.py` / `docs/model_cards/agent6.md` / `docs/demo_script/agent6.md` / `docs/compliance/partners.md` / `docs/compliance/data-grading.md`
