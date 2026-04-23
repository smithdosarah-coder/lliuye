# code-arch (架构对齐重构) Phase 1 Onboarding

**状态**：APPROVED
**发布日期**：2026-04-23
**Signal 入口**：`PRODUCT-HARDENING-BATCH-1-DISPATCHED`
**前置**：
- 代码审计（Q-023 中一览）已完成
- 与 code-urgent 并行，互不干扰（分不同分支）

---

## 你是谁

你是 **code-arch** worker CLI，负责把 5 个 Agent（除 Agent6，它已达标）**按 CLAUDE.md §3.2 / §3.3 / §6 重构到架构规范**。你是架构升级手，不做紧急补漏（那是 code-urgent 的事）。

- Worktree：`D:/claude code/demo-code-arch`
- 分支：`feat/code-arch`（从 `chore/l0-infra` 分出）
- Upstream remote：`D:/claude code/credit_report_agent_work`

---

## 本批次任务

### 🏗️ Task A — 5 Agent 工具域按 §3.2 重拆

**目标**：5 个 Agent 当前工具扁平堆叠，违反 §3.2 "按业务子域组织"。按 CLAUDE.md 第 3.2 节表格列出的子域边界重命名 + 重组。

| Agent | 应有子域 |
|---|---|
| Agent1 channel | 信号搜索域 / 企业画像域 / 匹配评分域 / 产品推荐域 |
| Agent3 credit | 画像消费域 / 评分计算域（对公/对私双模型）/ 红线检查域 / 案例召回域 |
| Agent4 alert | 外部扫描域 / 内部交易域 / 双路交叉域 / 处置建议域 |
| Agent5 compliance | 政策解析域 / 业务矩阵域 / 违规判定域 / 缺陷分类域 |
| Agent2 riskctrl | DSL 生成域 / 回测域 / 指标分析域 |

**命名约定**：`<域名>_<动作>`（如 `signal_search_by_keyword` / `profile_extract_from_url`）

**模块路径**：
- 修改：各 `agent_<name>/` 下 py 文件重命名 + 工具函数重组（按子域分 module）
- 新建：各 `agent_<name>/domains/<domain>.py` 或类似组织方式
- 更新：各 `agent_<name>/__init__.py` 导出路径

**指标/验证**：
- 每 Agent 目录 tree 能清晰看到子域划分
- grep `def ` 工具函数命名 90%+ 遵循 `<域>_<动作>` 约定
- 跨域协作只走 Agent 编排层，不在域内直接调用其他域内部实现

**工作量**：L（3 天，5 Agent × 0.5-1 天）
**完成信号**：`Signal: TOOL-DOMAIN-SPLIT-DONE`

---

### 🏗️ Task B — 5 Agent Evidence-First 三阶段协议

**目标**：§3.3 要求所有 LLM 生成内容走"证据汇集 → Grounded 生成 → 自审"三阶段。目前只 Agent6 有实现（`section_generator.py`）。抽出基类，5 个 Agent 各自继承实现。

**模块路径**：
- 新建：`shared/evidence/protocol.py`（基类 `EvidenceFirstPipeline`，定义 `collect()` / `generate_grounded()` / `self_audit()` 三阶段抽象方法）
- 修改：`agent_report/section_generator.py` 继承基类（不改行为，只做结构对齐）
- 新建：`agent_channel/evidence_pipeline.py` / `agent_credit/evidence_pipeline.py` / `agent_alert/evidence_pipeline.py` / `agent_compliance/evidence_pipeline.py` / `agent_riskctrl/evidence_pipeline.py` 各自继承
- 每个 Agent 的 generate 入口改为走 pipeline

**指标/验证**：
- 每 Agent 生成一条输出，附带 `evidence_trail: [{source, snippet, ref_id}, ...]` 结构化字段
- 自审阶段能检出并标记"未能自动填写"（字段级）
- tests 覆盖每 Agent 至少一个 case

**工作量**：L（3-4 天）
**完成信号**：`Signal: EVIDENCE-PROTOCOL-5AGENTS-DONE`

---

### 🏗️ Task C — 数据飞轮第 4 环 feedback_to_fewshot 脚本

**目标**：§6 第 4 环"从 feedback 提取 few-shot 示例注入 prompts.py"当前**完全手工**。写脚本自动化。

**模块路径**：
- 新建：`scripts/feedback_to_fewshot.py`（读 `data/feedback/*.jsonl` → 按 agent 聚合 → 抽 top-N 高频修改模式 → 生成 few-shot 片段）
- 新建：`scripts/inject_fewshot_to_prompts.py`（把片段 merge 到 `agent_*/prompts.py` 的 `FEW_SHOT_EXAMPLES` 常量）
- 文档：`docs/runbook/feedback-flywheel.md`（PM 操作 SOP：多久跑一次、人工 review 哪些节点）

**指标/验证**：
- 预埋 10 条 `data/feedback/2026-04-23.jsonl` 样本，脚本跑完在某 Agent prompts.py 能看到新增 few-shot 段
- PM review 后可手动撤销（dry-run + review 模式）

**工作量**：M（1.5 天）
**完成信号**：`Signal: FEEDBACK-FEWSHOT-PIPELINE-DONE`

---

## 完成后

所有 Task 做完：`Signal: READY-FOR-CODE-ARCH-REVIEW`

## 红线

- ❌ 不动 Agent6 现有行为（只做结构对齐，确保 v16 pipeline 跑分数字不变）
- ❌ 不动 `financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py`（Agent6 的确定性基础，只读消费）
- ❌ 不动 `web/**`（前端不是本批次范围）
- ❌ 不碰 code-urgent 的地盘（§3.1 修复、占位符 QC、Agent2/4 api.py = 他的 task）
- ❌ 不碰 data-foundation / evaluation 的地盘
- ✅ 5 个 Agent 的目录结构重构你负责
- ✅ `shared/evidence/` 新增你负责
- ✅ `scripts/feedback_to_fewshot.py` 和 `inject_fewshot_to_prompts.py` 新增你负责

## ACK 协议

1. Resume → commit doc-only，trailer `Signal: PRODUCT-HARDENING-BATCH-1-ACK`
2. Task A → B → C 顺序，每 Task 独立 commit 带对应 signal
3. 全 Task 完成 → `READY-FOR-CODE-ARCH-REVIEW`

**维护者**：主 CLI
**下次更新触发**：主 CLI APPROVE 或 REJECT
