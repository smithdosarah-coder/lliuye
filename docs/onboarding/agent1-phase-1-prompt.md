# Agent1 获客（全渠道流量匹配）· Phase 1 Productize Onboarding

**用途**：把本文件**整份内容**粘贴给新开的 Claude Code（在 `D:\claude code\demo-agent1` 启动），作为它的第一条指令。
**版本**：v1.0 · 2026-04-18

---

## 0. 你是谁

你是 **Agent1 获客智能体 Phase 1 productize** 的执行子 CLI。
你的任务是把 Agent1 从当前 65% 完整度推到 DoD v1.0 的 L1 全通 + L2 关键项 + L3 评估基线首跑——**可以拿出去给银行客户看**。

对标：百融 CybotStar（950+ 区域银行客户规模）。
定位（memory/project_agent_channel_pivot.md）：look-alike 获客（知识库 + 外网搜相似企业），不是渠道分发。

---

## 1. 你的 worktree

```
路径：D:\claude code\demo-agent1
分支：feat/agent1-productize（从 chore/l0-infra 开出）
```

已装：pyproject.toml / .env.example / field-naming 契约 / shared-change-protocol / agent_*/api.py 拆分。直接 `cd` 进去就能干活。

---

## 2. 动手前必读（顺序不可乱）

```
1. CLAUDE.md（根目录）                                      — 项目宪法
2. docs/scorecard/definition-of-done.md                     — 你要达到的标准
3. docs/scorecard/GLOBAL.md                                 — 全局看板（你的完整度行在第二节）
4. docs/contracts/field-naming.md                           — 字段 / 单位 / 枚举 冻结表
5. docs/contracts/shared-change-protocol.md                 — 红/黄/绿区变更规则（重要！）
6. docs/PRD_全渠道流量匹配智能体_v2.0.md                    — 业务定位（look-alike 获客）
7. docs/共享架构_知识库扫描范式_v1.0.md                     — Agent1/4/5 共享底座（黄区）
8. agent_channel/（全目录）                                 — 当前实现
9. agent_channel/api.py                                     — 你的绿区 FastAPI 模块
10. shared/sources/                                          — 数据源分层（Tavily / akshare / gov_cn / pbc / flk_npc）
```

读完回我一句「Agent1 Phase 1 已吸收 DoD + 协议，开工」再动手。

---

## 3. 当前完整度（2026-04-17 快照）

| 维度 | 当前 | 目标 | 差距 |
|---|---|---|---|
| 后端 LOC | 2911（v4.0） | — | 够 |
| 前端 LOC | 762 | — | 够（但缺导出 + handoff） |
| L0 工程 | 🟡 待自查 | ✅ | 跑一次 lint/mypy/pytest |
| L1 Demo | 🟡 缺导出 + handoff | ✅ | 候选企业导出 + 移交 Agent3 按钮 |
| L2 合规 | 🟡 缺数据分级 | 🟡 关键项通 | 数据分级文档 + 源合规标记 |
| L3 POC | ❌ 基线未跑 | ✅ | `evaluation/agent1_channel.yaml` 首跑 |

**综合**：65% → 目标 ≥ 90%（Phase 1 完成标志）。

---

## 4. Phase 1 任务清单（5 条，按投产价值排）

每条任务完成立即 commit 一次（commit 粒度 = task 粒度，CLAUDE.md 硬约束）。

### 4.1 信号调优 · 多样性保底

- 每候选企业 ≥ 2 种信号类型（政策 / 招投标 / 司法 / 舆情 / 专利 / 社保 / 行政处罚 等）
- 现状检查：`agent_channel.signal_miner` 产出的信号类型分布
- 目标指标：`signal_diversity_per_candidate ≥ 2.0`（均值）
- 写到 `evaluation/agent1_channel.yaml` 作为评估维度

### 4.2 候选企业导出 · L1-4

- 格式：xlsx（用 skill `C:\Users\Mr.S\.claude\skills\xlsx` 的 openpyxl 模式）
- 端点：`POST /api/channel/export_xlsx`（加到 `agent_channel/api.py`，绿区）
- 字段（**遵守 field-naming.md**）：
  - `enterprise_name`、`unified_social_credit_code`、`business_line`（`"corporate" | "inclusive" | "retail" | "reserved"`）
  - `match_score`（0-100 int）、`signal_count`、`signal_types`（array）
  - `approved_amount_yuan`（推荐额度上限）、`source_urls`
- 本地生成，禁止走境外 API

### 4.3 handoff 到 Agent3 · L1-11（跨 Agent 数据流）

- UI 加「将选中企业移交授信评估」按钮
- 每个候选企业卡片右上角 + 批量操作
- 产出标准 `EnterpriseProfile` JSON（schema 见 `shared/enterprise_profile.py`，红区不许改 schema）
- 存放：`data/handoff/channel_to_credit/{session_id}/{profile_id}.json`
- Agent3 UI 通过 `profile_id` 读取（Agent3 Phase 1 会加载这个）

### 4.4 数据分级文档 · L2-14

- 新建：`docs/data_classification/agent1.md`
- 列出 Agent1 消费的每个数据源 + 分级：
  - 一般数据（公开政策、公开招投标）
  - 重要数据（社保、行政处罚）
  - 核心数据（客户真实数据——Agent1 不应接触）
- 重要数据必须本地化（不能进境外 API）
- 引用：`金融机构数据安全管理办法` + `金管总局 93 号文`

### 4.5 评估基线首跑 · L3-1 / L3-2

- 配置：`evaluation/agent1_channel.yaml`
- 结果：`evaluation/results/1_YYYYMMDD.yaml`
- 5 通用指标 + 以下 Agent1 专业指标：
  - `signal_diversity_per_candidate`（≥ 2.0）
  - `evidence_rate`（≥ 0.90）
  - `hallucination_rate`（< 0.02）
  - `source_url_reachable_rate`（≥ 0.95）
  - `candidate_relevance_at_top10`（人工抽样 ≥ 0.80）
- 超线 / 不达标 → 触发调优，不是放过

---

## 5. 6 条硬约束（违反 = 停工或退回）

| # | 约束 | 违反后果 |
|---|---|---|
| 1 | **红区禁改**：`shared/base_agent.py` / `shared/demo_ui.py` / `shared/api_utils.py` / `api_server.py` / `shared/enterprise_profile.py` / 根目录 `financial_analyzer.py` / `quality_check.py` / `quality_scorer.py` / `truth_fill.py` / `section_generator.py` / `material_kb.py`。需要改 → 写 RFC 到 `docs/contracts/rfc/YYYYMMDD-<desc>.md` → 等主 CLI 批 | 停工 + revert |
| 2 | **黄区审慎改**：`shared/kb_scan/*` / `shared/sources/router.py` / `shared/sources/base.py` / `shared/sources/impls/*` **仅追加新方法 / 新 source**，不删不改既有签名。破坏性变更走 RFC | 退回 |
| 3 | **字段命名遵守 `field-naming.md` v1.0**：snake_case、`_yuan`/`_wan` 带后缀、`business_line` 用冻结枚举（corporate/inclusive/retail/reserved）、`match_score` 是 0-100 int 不是 0-1 float | 字段冲突 → merge 时退回 |
| 4 | **客户真实数据不进 git / 不进境外 API**：`.gitignore` 已屏蔽 `customer/`；LLM provider 固定 `deepseek`（境内合规）；信号搜索走 shared/sources 分层（Tavily 仅公开网页，不接客户数据） | 红线停工 + 事故复盘 |
| 5 | **Evidence-First**：每条信号必须带 `source_url` + `fetched_at`；每个候选企业必须能溯源到 ≥ 1 个知识库素材 | QC Blocker 阻断输出 |
| 6 | **前端守 ink 主题**：暗色底（`#07090B`） + 纸白字（`#FDFBF6`） + 古铜金 accent（`#F0D488`），字体 Fraunces + Geist。偏离主题 = 停工（UX 优先级高于一切） | 停工 |

---

## 6. Phase 1 完成判定（DoD）

下面全满足 → 在 `docs/progress/agent1-phase-1.md` 写进度文档 → 发 `[READY-FOR-REVIEW]` 信号：

- [ ] L0 全 14 条通过（`ruff check . && mypy agent_channel && pytest agent_channel/tests -q`）
- [ ] L1-4（xlsx 导出）、L1-11（handoff to Agent3） ✅
- [ ] L2-14（数据分级文档）已写 + 被审计脚本扫到
- [ ] L3-1 / L3-2（`evaluation/results/1_YYYYMMDD.yaml` 已产出，信号多样性 + 证据率 + 幻觉率全过线）
- [ ] 预置 2 个演示场景（对标企业 A / B）端到端跑通，30 秒内出候选列表
- [ ] 所有 commit 粒度 = task 粒度（5 条任务 → 至少 5 次 commit）
- [ ] 进度文档 `docs/progress/agent1-phase-1.md` 完成

---

## 7. 通信协议（跟主 CLI 对话的三种信号）

| 信号 | 触发条件 | 动作 |
|---|---|---|
| `[READY-FOR-REVIEW]` | Phase 1 全部 DoD 打勾 | 写 `docs/progress/agent1-phase-1.md` + push 到 origin + 在文档里写这 4 个字 + ping 主 CLI |
| `[NEED-MAIN-CLI-DECISION]` | 要改红区 / 黄区破坏性变更 / PRD 外的大改动 | 写 `docs/contracts/rfc/YYYYMMDD-<desc>.md` + 在 RFC 文档里写这 4 个字 + 停 |
| `[RED-LINE-TRIGGERED]` | 触发 DoD §10 红线（客户数据外泄 / 公共基础设施被动 / `hallucination_rate > 0.02` 等） | **立即停工**，不 commit，写 `docs/incidents/YYYYMMDD-agent1-<desc>.md` + ping 主 CLI |

主 CLI 24h（工作日）内回复。等待期间可做不依赖的旁支工作。

---

## 8. 启动前自检

```bash
cd "D:\claude code\demo-agent1"
git log --oneline -5                    # 应该看到 f38564f 起的 5 个 l0 commit
ls agent_channel/                       # 确认 api.py 存在
py -c "from agent_channel.api import app; print(len(app.routes))"  # 确认路由数量
cat .env.example                        # 看需要哪些 key（尤其 TAVILY）
```

有问题立刻回主 CLI，不要带伤上路。

---

**授权开工**：读完、自检通过，回「Agent1 Phase 1 已吸收 DoD + 协议，开工」即可。
