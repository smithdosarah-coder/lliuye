# 信贷 AI 智能体矩阵 · Definition of Done (DoD)

**版本**：v1.0
**日期**：2026-04-17
**作者**：刘野（众安信科 AI 中台 / 乾策平台 X-Nexus）
**文档性质**：交付硬标准（sign off 唯一依据）
**覆盖范围**：Agent1 获客 / Agent2 风控 / Agent3 授信 / Agent4 预警 / Agent5 合规 / Agent6 报告

---

## 0. 这份文档为什么要严谨到这个程度

之前的 v1 DoD 是 9 条扁平 checklist（预置场景 / 三区块 / 可视化 / 导出 / handoff / 证据链 / QC / 评估基线 / E2E），问题是：**扁平 checklist 对抗不了银行 RFP 的审阅视角**。银行采购 AI 不是看演示效果，是看 5 方博弈——业务 / 科技 / 合规 / 数据管理 / 采购——**任意一方否决，合同签不下**。

这份 DoD 基于以下三层证据重构：

### 证据 1：市场基线（2025）

| 对标锚 | 数据 | 含义 |
|---|---|---|
| 金融壹账通 Smart Lender | 报告自动化率 **80%**、审批 **1 日**、客户经理效能 **6 倍** | Agent6 的定价/功能对标 |
| 金融壹账通 Gamma | 国有大行 100% / 股份行 100% / 城商行 99% 渗透 | Agent3 市场容量 |
| 同盾诸葛金融大模型 | 风险识别 78%→94%、误报 -45%、人工误判 -72% | Agent2/4 性能基线 |
| 百融 CybotStar | 950+ 区域银行 | Agent1 竞品密度 |
| 拓尔思拓天大模型 | 签约合同约 **2000 万/单** | 价格锚 |
| 2025 银行业大模型中标 | 290 个 / **15.06 亿** | 市场规模锚 |

### 证据 2：银行采购 TOP6 验收指标（2025 招投标抽样）

1. 召回准确率
2. **P95 首字延时**
3. 数据安全合规
4. 多模态推理
5. 跨系统协同
6. 长任务收敛度

### 证据 3：监管强制要求（2025 升级，从指导性 → 强制性）

| 文件 | 强制条款 |
|---|---|
| 金管总局《助贷新规》2025-10 | 合作机构**备案**强制、总行建动态合作机构名录 |
| CAC《人工智能安全治理框架 2.0》2025-09 | 可解释性 AI **强制**、安全设计内嵌研发全流程 |
| 《商业银行互联网贷款管理暂行办法》2025 | 自主风控（核心风控模型不得外包）、合作机构不得代替银行实质审批 |
| 《金融机构数据安全管理办法》+ 金管总局 93 号文 | 数据分级（一般/重要/核心），重要数据本地化 |
| 金管总局 2025 官方表态 | "AI 现阶段只能辅助，不能替代"（copilot-only 明文依据） |
| 人行行标 JR/T《人工智能算法金融应用信息披露指南》 | 训练数据、特征口径、性能指标、偏见测试**强制可披露** |

**违规后果**：罚款（百万至千万）→ 暂停业务资质 → 吊销。最高可处上年度营业额 5%（《数据安全法》《个保法》）。

### 证据 4：银行真实关切（调研提炼）

> 银行对 Agent 的买点**不是**"能不能做"，**是**"**出错谁负责**"。
> —— 这决定了 DoD 必须覆盖 Evidence-First + QC Blocker + 审贷员修改回流，缺一不可。

---

## 1. 五层验收模型（递进式，越往下越严）

```
L0 工程基础    ─ 能运行吗？            （给开发看）
L1 Demo 完整   ─ 客户能一眼看懂吗？     （给销售看）
L2 金融合规    ─ 合规官能放行吗？       （给合规 / 审计看）
L3 客户 POC    ─ 真实数据能跑出合理结果吗？（给银行科技部 / 业务部看）
L4 商业交付    ─ 能签合同落地吗？        （给采购 / 法务看，可选）
```

**规则**：
- 任何 agent 未通过 **L0** → 不能 commit 到 main
- 任何 agent 未通过 **L1** → 不能对外演示
- 任何 agent 未通过 **L2** → 不能对外声称"满足金融合规"
- 任何 agent 未通过 **L3** → 不能启动 POC
- **L4 按客户定制**，但主 CLI 必须为每个 agent 预填可行性评估

---

## 2. L0 · 工程基础（14 条）

对应问题：**能运行吗？**

| # | 条目 | 判定方法 |
|---|---|---|
| L0-1 | 代码通过 lint（ruff）+ type check（mypy / pyright） | CI 绿灯 |
| L0-2 | 核心模块单测覆盖率 ≥ 70% | `pytest --cov` 报告 |
| L0-3 | 无硬编码 API Key / Token / 密码 / 客户名 | `grep -r "sk-\\|tvly-\\|身份证" src/` 0 命中 |
| L0-4 | 所有外部调用有超时 + 降级路径 | 代码静态扫描 + 单测 |
| L0-5 | 无裸 `except:` / 无沉默吞异常 | ruff E722 / BLE001 = 0 |
| L0-6 | 日志不打印敏感信息（身份证 / 电话 / 金额明细） | 日志扫描正则 |
| L0-7 | `.env.example` 齐全，本地 `.env` 不进 git | `git ls-files .env` 为空 |
| L0-8 | `requirements.txt` 版本锁定 | 无 `>=` 仅 `==` |
| L0-9 | `CHANGELOG.md` / commit message 可追溯 | 每个阶段必须有新 commit，message 说"why" |
| L0-10 | 启动命令单行可跑（`py /tmp/start_uvicorn.py`） | 新机克隆后 10 分钟内启起来 |
| L0-11 | 健康检查端点 `/api/{agent}/health` 返回 200 + `llm_connected` 状态 | curl 验证 |
| L0-12 | P95 接口响应时间（健康检查 + 首字节）≤ 1s | 本地 load test 100 次采样 |
| L0-13 | 运维文档齐全：起 / 停 / 监控 / 回滚 4 个脚本或命令 | `docs/ops/{agent}.md` 存在 |
| L0-14 | 新增模块归属到 CLAUDE.md §3.2 声明的业务域，不扁平堆叠 | code review 人工检查 |

---

## 3. L1 · Demo 完整度（12 条）

对应问题：**客户坐会议室能一眼看懂吗？**

| # | 条目 | 判定方法 |
|---|---|---|
| L1-1 | 预置场景 ≥ 2 个 / Agent，点击即跑 | UI 有场景卡片 |
| L1-2 | 首屏 3 区块布局（输入 / 过程 / 产出），不得再是纯 chatbot | 截屏验证 |
| L1-3 | 核心可视化 ≥ 1 个（雷达图 / 信号灯 / 图表 / 进度条），非纯数字 | 截屏验证 |
| L1-4 | 导出格式 ≥ 1 种（docx / pdf / xlsx），下载链接可用 | 点击下载 → 文件打得开 |
| L1-5 | 30 秒内看到有效中间态（否则 progress bar 必须说明阶段） | 秒表 |
| L1-6 | 从 `demo.liuye.me` 跨机器访问全流程可跑通 | 另一台电脑 smoke test |
| L1-7 | 页面视觉符合 CLAUDE.md §7 设计系统（暗色 ink 主题、Fraunces+Geist、古铜金 accent） | 截屏 + 主题色 hex 比对 |
| L1-8 | 所有文案中文、无技术 jargon 泄露（Tavily / LangChain / SegmentedControl 等都是红旗） | grep + 人工 |
| L1-9 | LLM 未连接 / 搜索超时 / key 缺失 → UI 给**明确降级提示**，非弹一个技术栈报错 | 主动断网 / 拔 key 验证 |
| L1-10 | Mock 模式独立可跑，断外网可演示 | 本地拔网线验证 |
| L1-11 | 跨 Agent 联动：Agent6 handoff 能在 Agent3/4/5 UI 里"一键预填" | 点击验证 |
| L1-12 | 所有场景在 demo 数据下结果稳定（重复跑 3 次结果一致或差异可解释） | 3 次重试 diff |

---

## 4. L2 · 金融合规（15 条，最硬的一层）

对应问题：**合规官 / 审计能放行吗？**

### 4.1 零幻觉与证据链（6 条）

| # | 条目 | 判定方法 |
|---|---|---|
| L2-1 | 每条数字 / 关键判断挂证据（URL / 段落 ID / 材料文件名） | `evidence_rate ≥ 0.95` |
| L2-2 | 无证据项**必须**标"未能自动填写"，不得 LLM 编数 | `hallucination_rate ≤ 0.01` |
| L2-3 | **确定性计算走 Python**（财务比率 / 红线阈值 / 同环比 / 账龄），LLM 不得现场算 | 代码 review + 抽样计算一致率 ≥ 0.99 |
| L2-4 | QC Blocker 在输出前终审：placeholder 残留 / 证据缺失 / 数字与 `financial_analyzer` 结果不一致 → 阻断 | quality_check.py 扩展 + 单测 |
| L2-5 | **占位符残留** 0 容忍（张 XX / 区间数字 / 模板指导文字 / 示例行业词） | quality_check.py 现有规则全绿 |
| L2-6 | 生成内容中的每个"结论"可人工 30 秒内追到原始材料 | 抽样 10 条人工复核 |

### 4.2 可解释性 · Reason Code（3 条，对标 Zest/Upstart AAN）

| # | 条目 | 判定方法 |
|---|---|---|
| L2-7 | **每个分数 / 决策附 Top-3 到 Top-5 标准原因码**（适用 Agent3/4/5） | 输出字段 `reason_codes: []` |
| L2-8 | 原因码字典固定、可枚举、覆盖全部负面结论（对标 FCRA AAN） | `docs/reason_codes/{agent}.yaml` 存在 |
| L2-9 | 拒绝 / 红灯 / 违规结论**必须**输出"为什么 + 怎么改" | UI 展示文案 + 结构化字段 |

### 4.3 人在回路 · 数据治理（6 条）

| # | 条目 | 判定方法 |
|---|---|---|
| L2-10 | **所有 Agent 输出标"建议"而非"决定"**，UI 醒目标识 | 截屏验证文案 |
| L2-11 | 必须有"审批人 / 复核人"字段 & 电子签章位（占位即可，Demo 阶段） | UI 组件存在 |
| L2-12 | **审计日志**：session_id + timestamp + 用户 ID + 输入 hash + 输出 hash 落盘 | `data/audit/*.jsonl` 有结构化记录 |
| L2-13 | **合作机构清单**（Tavily / DeepSeek / akshare / gov_cn / pbc / flk_npc）：文档化 + 数据分类 + 境内/境外标签 | `docs/partners/third-party-services.md` 存在 |
| L2-14 | **数据分级标签**：每个字段 / 外部源标一般 / 重要 / 核心，核心数据**禁止出境** | `docs/data-classification.md` 存在 |
| L2-15 | 客户材料（企业报表 / 身份证 / 授信记录）在本地处理，不走境外 API | DeepSeek（境内）可，Claude / OpenAI（境外）禁用于客户数据 |

---

## 5. L3 · 客户 POC（12 条）

对应问题：**给一份真实数据，能跑出合理结果吗？**

### 5.1 评估基线（4 条）

| # | 条目 | 判定方法 |
|---|---|---|
| L3-1 | `evaluation/agent{N}_*.yaml` 跑过 baseline，结果落盘 `evaluation/results/` | 文件存在 + 时间戳 |
| L3-2 | 通用指标达标：`task_completion ≥ 0.95` / `evidence ≥ 0.95` / `hallucination ≤ 0.02` / `tool_success ≥ 0.90` | 结果 YAML |
| L3-3 | 领域指标达标（见 §7 Agent 差异化） | 结果 YAML |
| L3-4 | **基线回归**：每次 merge 前重跑一次，结果不得倒退 > 2% | CI 对比脚本 |

### 5.2 工程能力（4 条）

| # | 条目 | 判定方法 |
|---|---|---|
| L3-5 | P95 首字延时 ≤ 1.5s（SSE 首条 event 到达时间） | load test |
| L3-6 | **Mock / Web 双模切换**靠配置（SearchProvider 抽象，不允许 if-else 判 mock/web 分支） | 代码审查 |
| L3-7 | 多客户数据隔离（session_id 隔离，不互串） | 并发压测验证 |
| L3-8 | 反馈飞轮：`/api/feedback` 端点可用，审贷员修改落盘 `data/feedback/YYYY-MM-DD.jsonl` | 端到端测试 |

### 5.3 E2E 验证（4 条）

| # | 条目 | 判定方法 |
|---|---|---|
| L3-9 | Playwright E2E 覆盖 3 个关键路径（预置场景 / 真数据 / 导出） | 脚本 + 通过率 100% |
| L3-10 | 3 张关键截屏留证（起点 / 过程 / 终点） | `docs/screens/{agent}/*.png` |
| L3-11 | 模型卡片（model card）文档：算法 / 输入 / 输出 / 准确率 / 局限 | `docs/model_cards/{agent}.md` |
| L3-12 | 演示脚本（sales playbook）：从首页到 sign off 的话术 | `docs/demo_script/{agent}.md` |

---

## 6. L4 · 商业交付（8 条，可选，按客户启用）

对应问题：**能签合同部署吗？**

| # | 条目 | 判定方法 |
|---|---|---|
| L4-1 | 私有化部署包（Docker / 离线安装脚本） | 打包产物存在 |
| L4-2 | 信创兼容路径说明（鲲鹏 / 曙光 / 麒麟）：即使 Demo 不跑通，规划文档要有 | `docs/信创兼容路径.md` |
| L4-3 | SLA 承诺书：可用性 ≥ 99.5% / 故障响应时间 | `docs/sla.md` |
| L4-4 | 等保 2.0 三级符合性自检清单 | `docs/compliance/等保自检.md` |
| L4-5 | 合作机构备案材料（对接银行合规部，进其动态合作机构名录） | `docs/partners/备案材料.md` |
| L4-6 | 完整 API 文档（OpenAPI / Postman collection） | 文件存在 + 可导入 |
| L4-7 | 交接文档（KT）+ 运维手册 + 应急预案 | `docs/handover/{agent}-kt.md` |
| L4-8 | 定价与计费方案：项目买断 + 年维护 / MaaS 调用量 双模可选 | `docs/pricing.md` |

---

## 7. Agent 差异化附加标准

### 7.1 Agent1 获客 · look-alike（对标 百融 CybotStar / 拓尔思拓天）

- **L3 领域指标**：
  - 信号多样性 ≥ 2 种 / 候选客户（CLAUDE.md §5.2）
  - 候选企业召回率：知识库每 10 家锚点客户能召回 ≥ 30 家新候选
  - 幻觉企业（搜不到实体）占比 ≤ 0.02
- **特殊**：必须支持知识库多文件上传（名录 + 政策 + 行业指引）
- **导出**：候选清单 xlsx（含 URL + 匹配理由 + 推荐产品）

### 7.2 Agent2 风控 DSL（对标 同盾天策 / 顶象 Dinsight）

- **L3 领域指标**：
  - 规则 DSL 生成可执行率 ≥ 0.95
  - 回测 KS 指标计算与 scikit-learn 一致率 ≥ 0.99
  - 冠军/挑战者 A/B 对比功能可用
- **特殊**：规则编辑器 UI（非 chatbot）、KS/PSI/混淆矩阵可视化
- **导出**：回测报告 pdf + 规则 DSL json

### 7.3 Agent3 授信决策（对标 金融壹账通 Gamma / Zest AAN）

- **L3 领域指标**：
  - 四维评分（财务 / 行业 / 经营 / 担保）一致率 ≥ 0.95（复测稳定性）
  - **Top-5 标准拒贷原因码覆盖率 = 100%**（对公 + 对私两套字典）
  - 红线触发准确率 ≥ 0.99（vs 人工裁定）
- **特殊**：必须消费 Agent6 `EnterpriseProfile` handoff
- **导出**：决策意见书 docx（含四维雷达图、额度建议、原因码清单）

### 7.4 Agent4 预警（对标 同盾诸葛 / 冰鉴）

- **L3 领域指标**：
  - 客户池扫描完成率（100 家客户全量跑通）≥ 0.95
  - 红灯客户精准率 ≥ 0.80（抽样 20 家人工复核）
  - 误报率 ≤ 0.15（对标同盾 -45% 优化后基线）
- **特殊**：外部事件 + 内部交易双路交叉、红黄绿仪表盘
- **导出**：预警台账 xlsx

### 7.5 Agent5 合规（对标 恒生反洗钱 / RegTech）

- **L3 领域指标**：
  - 政策条款解析准确率 ≥ 0.95（vs 人工标注）
  - 违规冲突点召回率 ≥ 0.90
  - 条款引用错误率 ≤ 0.01
- **特殊**：政策事件驱动扫描（非定期）、政策-业务矩阵 UI
- **导出**：合规检查报告 docx（条款级溯源）

### 7.6 Agent6 报告（基线，已达标；守住不退）

- 保持 `field_completeness ≥ 0.93` / `evidence_rate ≥ 0.95` / `quality_score_total ≥ 65`
- 新增 L3-11 模型卡片、L3-12 演示脚本
- 新增 L2-12 审计日志（现有 session_store 扩展）

---

## 8. 硬断言清单（sign off 前自动跑）

一键脚本 `scripts/sign_off_check.sh <agent>`，跑完必须全绿才允许 merge：

```bash
# 1. 代码质量
ruff check agent_{N}/
mypy agent_{N}/
pytest agent_{N}/tests/ --cov --cov-fail-under=70

# 2. 安全扫描
grep -rE "sk-[a-zA-Z0-9]{20,}|tvly-[a-zA-Z0-9]{20,}|password\s*=\s*['\"]" agent_{N}/ web/ && exit 1 || true

# 3. 评估基线
python -m evaluation.run --agent {N} --output evaluation/results/{N}_$(date +%Y%m%d).yaml

# 4. QC Blocker 单测
pytest tests/quality/ -k "test_agent{N}"

# 5. E2E
cd web && npx playwright test tests/e2e/{agent}.spec.ts

# 6. 证据链抽检
python tools/evidence_audit.py --agent {N} --sample 20
```

---

## 9. sign off 流程

```
子 CLI 完成阶段
  ↓ 产出
  ├─ 代码（commit 到 feat/agentN-*）
  ├─ docs/progress/agentN-phase-M.md（进度）
  ├─ docs/scorecard/agentN-self.md（自评，逐条 yes/no + 证据）
  └─ evaluation/results/N_YYYYMMDD.yaml（基线）

子 CLI 通知主 CLI
  ↓
主 CLI 执行 review
  ├─ 拉 worktree, git log + diff
  ├─ 起服务, 按 progress.md 的"如何验证"**亲自跑一遍**（不许口头过）
  ├─ 跑 scripts/sign_off_check.sh N
  ├─ 逐条 L0→L3 打分 → docs/review/agentN-phase-M-review.md
  └─ verdict: APPROVED | CHANGES_REQUESTED

主 CLI 更新 docs/scorecard/GLOBAL.md

任一条 L0 / L1 未过 → CHANGES_REQUESTED（不许带伤合并）
```

---

## 10. 红线（触发立即停工 + 主 CLI 介入）

| 事件 | 后果 |
|---|---|
| 子 CLI 自评 "导出实现" 但主 CLI 点击 404 | **停工**，信任链断 |
| 前端主题偏离 ink 主题（颜色 / 字体错） | **停工**，UX 优先级高于一切 |
| 动到公共基础设施（`truth_fill.py` / `section_generator.py` / `quality_check.py` / `financial_analyzer.py`）未通知主 CLI | **停工**，须走主 CLI 评审 |
| `data/feedback/*.jsonl` 格式被改 | **停工**，飞轮协议稳定性 |
| 客户真实数据（企业名 / 身份证 / 金额）进 git 或境外 API | **停工 + 事故复盘** |
| `hallucination_rate > 0.02` 或 `evidence_rate < 0.90` | **停工**，触发根因分析 |

---

## 11. 监管引用索引（客户 RFP 可直接引用）

1. 《商业银行互联网贷款管理暂行办法》（2020 / 2022 修 / 2025 新规，银保监 / 金管总局）
2. 《金融机构数据安全管理办法》（金管总局）+ 93 号文
3. 《人工智能安全治理框架》1.0（CAC 2024-09）/ 2.0（CAC 2025-09）
4. 《生成式人工智能服务管理办法》（2023-08）
5. 人行行标 JR/T《人工智能算法金融应用评价规范》/《信息披露指南》
6. 《数据安全法》《个人信息保护法》
7. 金管总局 2025-10《关于加强商业银行互联网助贷业务管理的通知》

---

## 12. 本文档更新规则

- **变更必须经主 CLI 批准**，子 CLI 无权修改
- 每季度复核一次（对标最新监管 + 最新市场基线）
- 版本号升级触发：监管新规 / 市场基线变化 / 重大事故后根因修订

**当前版本**：v1.0 — 2026-04-17
**下次预期复核**：2026-07-01（三季度监管口径确认后）
