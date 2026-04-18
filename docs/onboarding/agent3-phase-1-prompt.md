# Agent3 授信决策辅助 · Phase 1 Productize Onboarding

**用途**：把本文件**整份内容**粘贴给新开的 Claude Code（在 `D:\claude code\demo-agent3` 启动），作为它的第一条指令。
**版本**：v1.0 · 2026-04-18

---

## 0. 你是谁

你是 **Agent3 授信决策辅助 Phase 1 productize** 的执行子 CLI。
你的任务是把 Agent3 从当前 70% 完整度推到 DoD v1.0 的 L1 全通 + L2 关键项 + L3 评估基线首跑——**可以拿出去给银行客户看**。

对标：金融壹账通 Gamma 加马平台（股份行 100% 渗透）。
差异化：copilot（人审核），不是 autopilot（监管红线，人行明文禁止）。

---

## 1. 你的 worktree

```
路径：D:\claude code\demo-agent3
分支：feat/agent3-productize（从 chore/l0-infra 开出）
```

已装：pyproject.toml / .env.example / field-naming 契约 / shared-change-protocol / agent_*/api.py 拆分。直接 `cd` 进去就能干活。

---

## 2. 动手前必读（顺序不可乱）

```
1. CLAUDE.md（根目录）                                      — 项目宪法
2. docs/scorecard/definition-of-done.md                     — 你要达到的标准
3. docs/scorecard/GLOBAL.md §六（Agent3 productize 路线）   — 你本阶段的 5 个任务
4. docs/contracts/field-naming.md                           — 字段 / 单位 / 枚举 冻结表
5. docs/contracts/shared-change-protocol.md                 — 红/黄/绿区变更规则（重要！）
6. docs/PRD_授信决策辅助智能体_v2.0.md                      — 业务定位
7. agent_credit/（全目录）                                  — 当前实现
8. agent_credit/api.py                                      — 你的绿区 FastAPI 模块
```

读完回我一句「Agent3 Phase 1 已吸收 DoD + 协议，开工」再动手。

---

## 3. 当前完整度（2026-04-17 快照）

| 维度 | 当前 | 目标 | 差距 |
|---|---|---|---|
| 后端 LOC | 3860 | — | 够 |
| 前端 LOC | 1011 | — | 够（但缺雷达图 + 导出 UI） |
| L0 工程 | 🟡 待自查 | ✅ | 跑一次 lint/mypy/pytest |
| L1 Demo | 🟡 缺可视化 + 导出 | ✅ | 四维雷达 + docx 导出 + handoff 按钮 |
| L2 合规 | ❌ 缺原因码 | 🟡 关键项通 | 对公+对私原因码 YAML + 确定性红线 |
| L3 POC | ❌ 基线未跑 | ✅ | `evaluation/agent3_credit.yaml` 首跑 |

**综合**：70% → 目标 ≥ 90%（Phase 1 完成标志）。

---

## 4. Phase 1 任务清单（5 条，按投产价值排）

来源：`docs/scorecard/GLOBAL.md §六`。每条任务完成立即 commit 一次（commit 粒度 = task 粒度，CLAUDE.md 硬约束）。

### 4.1 接通 Agent6 handoff 入口 · L1-11

- UI 加「从报告助手加载企业画像」按钮
- 读 `shared/report_handoff.py` 产出的 `EnterpriseProfile` JSON
- 演示数据：预置 2 家企业画像（1 家对公 + 1 家对私）在 `demo_data/agent_credit/` 下
- 前端组件：`web/src/app/credit/components/HandoffButton.tsx`

### 4.2 四维风险雷达图 · L1-3

- 财务 / 行业 / 经营 / 担保 四维，0-100 分
- 用 recharts 或 react-chartjs-2（查 web/package.json 已装哪个）
- 数据来源：`agent_credit.scoring` 模块产出
- 组件：`web/src/app/credit/components/RiskRadar.tsx`

### 4.3 标准拒贷原因码字典 · L2-7 / L2-8

新建：
```
docs/reason_codes/agent3-corporate.yaml   # 对公
docs/reason_codes/agent3-retail.yaml      # 对私
```

每个分数 / 决策必须输出 **Top-5 原因码**，每个原因码含：
- `code`: 短编码（如 `FIN_001`）
- `severity`: `red` / `yellow` / `green`（遵守 field-naming.md §3.3）
- `title`: 中文短标题（≤ 12 字）
- `detail`: 详细说明
- `evidence_path`: 指向证据（字段 / 段落 ID）

原因码必须**枚举闭合**——LLM 不得生成词典外的 code。

### 4.4 决策意见书 docx 导出 · L1-4 / L2-15

- **本地 docx 生成**，禁止走境外 API（监管红线：客户真实数据不进境外）
- 用本仓库 skill: `C:\Users\Mr.S\.claude\skills\docx`（docx-js 模式）
- 端点：`POST /api/credit/export_docx`（加到 `agent_credit/api.py`，绿区）
- 内容：四维评分 + 雷达图截图 + Top-5 原因码 + 额度建议 + 红线检查

### 4.5 评估基线首跑 · L3-1 / L3-2

- 配置：`evaluation/agent3_credit.yaml`（遵照 Agent6 已有格式）
- 结果：`evaluation/results/3_YYYYMMDD.yaml`
- 5 通用指标 + 5 信贷专业指标（见 CLAUDE.md §5）
- 必须满足：`hallucination_rate < 0.02`、`evidence_rate ≥ 0.90`（红线，超线停工）

---

## 5. 6 条硬约束（违反 = 停工或退回）

| # | 约束 | 违反后果 |
|---|---|---|
| 1 | **红区禁改**：`shared/base_agent.py` / `shared/demo_ui.py` / `shared/api_utils.py` / `api_server.py` / `shared/enterprise_profile.py` / `agent_report/enterprise_profile.py` / 根目录 `financial_analyzer.py` / `quality_check.py` / `quality_scorer.py` / `truth_fill.py` / `section_generator.py` / `material_kb.py`。需要改 → 写 RFC 到 `docs/contracts/rfc/YYYYMMDD-<desc>.md` → 等主 CLI 批 | 停工 + revert |
| 2 | **确定性计算走 Python**：财务比率 / 红线阈值 / 同环比 / 账龄周转**不许让 LLM 现场算**。用 `financial_analyzer` 的 `format_for_prompt()` 喂 LLM | L2-3 不通过 |
| 3 | **字段命名遵守 `field-naming.md` v1.0**：snake_case、`_yuan`/`_wan` 带后缀、`is_` 前缀布尔、`severity` 用 `red/yellow/green` 不用 `hard/soft/info` | 字段冲突 → merge 时退回 |
| 4 | **客户真实数据不进 git / 不进境外 API**：`.gitignore` 已屏蔽 `customer/*.docx/.xlsx/.pdf`；LLM provider 固定 `deepseek`（境内合规）；OpenAI / Claude 只能用于 demo_data 脱敏数据 | 红线停工 + 事故复盘 |
| 5 | **Evidence-First**：每个数字 / 结论 / 评分必须带证据链（字段 ID / 段落引用 / 原因码）。无证据字段**标「未能自动填写」**，绝不编 | QC Blocker 阻断输出 |
| 6 | **前端守 ink 主题**：暗色底（`#07090B`） + 纸白字（`#FDFBF6`） + 古铜金 accent（`#F0D488`），字体 Fraunces + Geist。偏离主题 = 停工（UX 优先级高于一切） | 停工 |

---

## 6. Phase 1 完成判定（DoD）

下面全满足 → 在 `docs/progress/agent3-phase-1.md` 写进度文档 → 发 `[READY-FOR-REVIEW]` 信号：

- [ ] L0 全 14 条通过（运行 `ruff check . && mypy agent_credit && pytest agent_credit/tests -q`）
- [ ] L1-3（四维雷达）、L1-4（docx 导出）、L1-11（handoff 按钮） ✅
- [ ] L2-3（确定性计算）、L2-7 / L2-8（原因码） ✅
- [ ] L3-1 / L3-2（`evaluation/results/3_YYYYMMDD.yaml` 已产出，`hallucination_rate < 0.02`、`evidence_rate ≥ 0.90`）
- [ ] 2 家预置企业（1 对公 + 1 对私）端到端跑通，30 秒内出完整结果
- [ ] 所有 commit 粒度 = task 粒度（5 条任务 → 至少 5 次 commit）
- [ ] 进度文档 `docs/progress/agent3-phase-1.md` 完成

---

## 7. 通信协议（跟主 CLI 对话的三种信号）

| 信号 | 触发条件 | 动作 |
|---|---|---|
| `[READY-FOR-REVIEW]` | Phase 1 全部 DoD 打勾 | 写 `docs/progress/agent3-phase-1.md` + push 到 origin + 在文档里写这 4 个字 + ping 主 CLI |
| `[NEED-MAIN-CLI-DECISION]` | 要改红区 / 黄区破坏性变更 / PRD 外的大改动 | 写 `docs/contracts/rfc/YYYYMMDD-<desc>.md` + 在 RFC 文档里写这 4 个字 + 停 |
| `[RED-LINE-TRIGGERED]` | 触发 DoD §10 红线（客户数据外泄 / 公共基础设施被动 / `hallucination_rate > 0.02` 等） | **立即停工**，不 commit，写 `docs/incidents/YYYYMMDD-agent3-<desc>.md` + ping 主 CLI |

主 CLI 24h（工作日）内回复。等待期间可做不依赖的旁支工作。

---

## 8. 启动前自检

```bash
cd "D:\claude code\demo-agent3"
git log --oneline -5                    # 应该看到 f38564f 起的 5 个 l0 commit
ls agent_credit/                        # 确认 api.py 存在
py -c "from agent_credit.api import app; print(len(app.routes))"  # 确认路由数量
cat .env.example                        # 看需要哪些 key
```

有问题立刻回主 CLI，不要带伤上路。

---

**授权开工**：读完、自检通过，回「Agent3 Phase 1 已吸收 DoD + 协议，开工」即可。
