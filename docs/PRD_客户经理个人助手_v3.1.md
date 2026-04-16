# PRD：客户经理个人助手 v3.1

**版本**：v3.1（产品定位修正版，替代 v3.0）
**日期**：2026-04-13
**作者**：刘野
**文档性质**：产品需求文档（总纲 + 版本索引）

---

## 1. 产品定位

客户经理个人助手是一套部署在众安信科 AI 中台（乾策平台 / X-Nexus）上的多 Agent 系统，整合 6 个专业子 Agent，覆盖银行信贷业务从获客、授信、风控到合规的全链条。

**v3.1 核心变化**：在 v3.0 "可演示产品矩阵"基础上，做**产品定位修正**——将 Agent1/4/5 从"单查工具"统一升级为"**知识库扫描雷达**"；将 Agent3 从"读材料出评估"重新定位为 Agent6 下游的**决策引擎**，并拓展为对公 / 对私双板块。

---

## 2. 版本演进

| 版本 | 时间 | 里程碑 |
|------|------|--------|
| v1.0 | 2026-03-23 | 报告生成助手 MVP 启动 |
| v2.0 | 2026-04-09 | 报告生成助手五项架构改造完成 |
| v2.1 | 2026-04-09 | 5 个 Agent 方向确定，规划文档输出 |
| v3.0 | 2026-04-13（上午）| 5 个 Agent 代码原型完成，Demo 改造方案定稿 |
| **v3.1** | **2026-04-13（下午）** | **产品定位修正：知识库扫描范式 + Agent3 重新定位** |

### v3.1 修正背景

v3.0 完成后进行客户视角检验，发现 3 个 Agent 存在**产品定位与真实工作场景脱节**的问题：

| Agent | v3.0 问题 | v3.1 修正 |
|-------|----------|---------|
| Agent1 获客 | 输入单企业 → 推荐信贷产品（本质是产品推荐，不是获客） | 上传知识库 → look-alike 搜相似新客户 + 附带推荐产品 |
| Agent4 贷中预警 | 输入单企业名 → 查这一家（单查工具）| 上传知识库 → 批量扫全量客户 → 分级榜单 |
| Agent5 合规巡检 | 单份政策 + 单份业务 → 查这一份 | 上传知识库 → 批量矩阵扫描 → 违规榜单 |
| Agent3 授信 | 读材料出评估（与 Agent6 功能重复）| 消费 Agent6 报告 + 多源信息 → 决策引擎（对公 + 对私）|

**修正原则**：产品定位服从客户真实工作场景，不为"可演示"牺牲产品生产形态。

详见：`docs/改造方案_信贷AI智能体矩阵_v2.0.md`

---

## 3. 产品架构

### 3.1 四层架构

```
┌─────────────────────────────────────────────────┐
│ 用户界面层：Portal 统一入口 + 各 Agent 差异化页面     │
├─────────────────────────────────────────────────┤
│ 编排层：主 Agent（意图路由）+ 6 个子 Agent            │
├─────────────────────────────────────────────────┤
│ 业务逻辑层：规则引擎 / 评分模型 / 分析流水线           │
├─────────────────────────────────────────────────┤
│ 共享层（v3.1 新增）：SearchProvider / KnowledgeBase / │
│                     RuleExtractor / Matcher     │
├─────────────────────────────────────────────────┤
│ 共享数据层：EnterpriseProfile + 知识库 + Mock 数据     │
└─────────────────────────────────────────────────┘
```

### 3.2 六大子 Agent（v3.1 定位）

| # | Agent | 业务环节 | v3.1 核心定位 | 代码状态 | Demo 状态 |
|---|-------|---------|--------------|---------|---------|
| 1 | 全渠道流量匹配 | 贷前 / 获客 | **Look-alike 获客引擎**：知识库驱动搜相似新客户 + 产品推荐 | 🔄 需重写 | ❌ v3.1 改造 |
| 2 | 风控策略运营 | 贷中 / 风控 | 自然语言→规则 DSL + 回测 + 差错分析（定位不变）| ✅ 后端完成 | ❌ v3.0 改造 |
| 3 | 授信决策辅助 | 贷中 / 审批 | **决策引擎（对公 + 对私双板块）**：消费 Agent6 报告 → 出决策 | 🔄 需重写 | ❌ v3.1 改造 |
| 4 | 贷中风险预警 | 贷后 / 监控 | **批量扫描雷达**：全量客户 × 外 / 内双路 → 分级榜单 | 🔄 需重写 | ❌ v3.1 改造 |
| 5 | 合规巡检 | 全流程 | **批量扫描雷达**：政策 × 业务事件 矩阵比对 → 违规榜 | 🔄 需重写 | ❌ v3.1 改造 |
| 6 | 报告生成助手 | 贷前 / 尽调 | 自动生成授信调查报告（定位不变，增加"送 Agent3"入口）| ✅ 核心引擎成熟 | ✅ 可演示 |

### 3.3 Agent 协同模式

v3.1 将 6 个 Agent 分为两类：

**批量扫描类（Agent1 / 4 / 5）**：共享"知识库扫描范式"架构

```
KnowledgeBase → RuleExtractor → ScanTargets → Matcher → HitList
```

**深度决策类（Agent3 / 6）**：串联 Agent6 → Agent3

```
企业材料 → Agent6（报告）→ Agent3（消费报告 + 决策）→ 决策意见回写
```

**独立工具类（Agent2）**：与其他 Agent 解耦，基于 Agent3 历史数据优化策略

### 3.4 Agent 间数据流（v3.1 更新）

```
┌──────────────┐          ┌──────────────┐
│ Agent1 获客   │──新线索──▶│ 人工（CRM）   │
│ (look-alike) │          └──────┬───────┘
└──────────────┘                 ▼
                          ┌──────────────┐
                          │ Agent6 报告   │──ReportJSON──▶┐
                          │ (调查报告)    │                │
                          └──────────────┘                ▼
                                                    ┌──────────────┐
                                                    │ Agent3 决策   │
                                                    │ (对公 / 对私)  │
                                                    └──────┬───────┘
                                                           │决策意见
                                                           ▼
                                                    ┌──────────────┐
                                                    │ Agent6 报告   │
                                                    │ (回写审批意见)│
                                                    └──────────────┘
                              放款后
                          ┌──────────────┐        ┌──────────────┐
                          │ Agent4 预警   │        │ Agent5 合规   │
                          │ (批量扫描)    │        │ (批量扫描)    │
                          └──────┬───────┘        └──────────────┘
                                 │决策数据反馈
                                 ▼
                          ┌──────────────┐
                          │ Agent2 风控   │
                          │ (策略优化)    │
                          └──────────────┘
```

**关键数据对象**：

| 数据对象 | 生产者 | 消费者 | 格式 |
|---------|-------|-------|------|
| KnowledgeBase | 客户上传 | Agent1 / 4 / 5 | 多文件 + 分类元数据 |
| IdealProfile | Agent1 画像抽取 | Agent1 搜索模块 | Pydantic |
| CompanyProfile | SearchProvider | Agent1 / 4 匹配 | Pydantic，统一企业数据结构 |
| ReportJSON | Agent6 | Agent3 | 结构化报告字段 |
| DecisionAdvice | Agent3 | Agent6 回写 / 审批流 | Pydantic |
| RiskLedger | Agent4 | 贷后经理 | 分级榜单 + 明细 |
| ComplianceLedger | Agent5 | 合规官 | 分级违规 + 明细 |

---

## 4. Portal 统一入口

> Portal 基础框架在 v3.0 已完成，v3.1 仅调整 Tab 内 Demo 场景卡和交互范式。

### 4.1 各 Tab 布局更新（v3.1）

| Tab | v3.0 布局 | v3.1 布局 |
|-----|----------|----------|
| 获客匹配 | 企业表单 + 渠道卡片流 | **知识库上传 + 画像卡 + 线索榜单 + 产品推荐** |
| 风控策略 | 规则编辑器 + 回测图表 | 不变 |
| 授信决策 | 材料清单 + 对话 + 报告 | **对公 / 对私 Tab 切换 + 决策 Dashboard + 雷达图 / 评分卡** |
| 贷中预警 | 信号灯 + 时间线 | **知识库上传 + 扫描进度 + 分级榜单 + 客户详情 + 处置建议** |
| 合规巡检 | 政策树 + 清单 | **知识库上传（政策 / 制度 / 业务）+ 扫描进度 + 违规榜单 + 整改建议** |

### 4.2 UI 范式一致性

批量扫描类 Agent（1 / 4 / 5）共享 UI 骨架：

```
┌────────────────────────────────────────┐
│  知识库上传区                             │
├────────────────────────────────────────┤
│  扫描进度 + 实时 tick                     │
├────────────────────────────────────────┤
│  分级榜单 │ 详情面板 │ 处置 / 整改建议      │
├────────────────────────────────────────┤
│  统计汇总 / 导出按钮                       │
└────────────────────────────────────────┘
```

---

## 5. Demo 演示体系

### 5.1 v3.1 预置场景升级

| Agent | v3.0 场景 | v3.1 场景 |
|-------|----------|----------|
| Agent1 | 单企业获客（制造 / 科创）| **制造业知识库 Look-alike / 科创知识库 Look-alike**（每个 KB 含 20+ 家已有客户）|
| Agent2 | 3 个场景（不变）| 不变 |
| Agent3 | 单企业评估 | **对公场景（福建中锐，串联 Agent6）+ 对私场景（个体工商户经营贷）** |
| Agent4 | 3 个单企业（红 / 黄 / 绿）| **2 个组合扫描（小微信贷 100 家 / 供应链 100 家）** |
| Agent5 | 单份政策 + 单份业务 | **2 个合规巡检（互联网贷款办法 / 反洗钱办法）** |
| Agent6 | 1 个完整报告 | 1 个完整报告（+ 新增"送 Agent3 做决策"按钮）|

### 5.2 跨 Agent 演示剧本（v3.1，约 8 分钟）

| 时间 | Agent | 动作 | 台词要点 |
|------|-------|------|---------|
| 0:00-1:00 | Agent1 获客 | 上传制造业知识库 → 搜到 10 家新线索 | "把客户经理的'找客户'变成 AI 被动收线索" |
| 1:00-2:00 | Agent1 | 点击某条线索 → 看推荐产品 + 切入话术 | "线索直接带产品匹配，一步到位" |
| 2:00-3:00 | Agent6 报告 | 上传该企业材料 → 生成调查报告 | "1.5 万字报告 10 分钟内自动生成" |
| 3:00-4:30 | Agent3 决策 | 点击"送决策" → 消费报告 → Dashboard | "决策支持，不是报告再造" |
| 4:30-5:30 | Agent4 预警 | 上传在贷客户知识库 → 批量扫描 | "100 家揪出 3 家红灯，客户经理早上 9 点打开就知道盯谁" |
| 5:30-6:30 | Agent5 合规 | 上传合规知识库 → 矩阵扫描 | "条款 × 业务矩阵比对，违规精确到单号" |
| 6:30-7:30 | Agent2 风控 | 基于 Agent3 历史数据回测策略 | "闭环，策略可迭代" |
| 7:30-8:00 | 收尾 | 统一 Portal 展示 | "6 Agent 闭环，覆盖信贷全链路" |

### 5.3 Demo 数据结构（v3.1）

```
demo_data/
├── agent_channel/                         # v3.1 改造
│   ├── manufacturing_kb/                  # 制造业知识库场景
│   │   ├── scenario.json
│   │   ├── existing_customers.xlsx        # 20+ 家已有客户
│   │   ├── policy_2026.pdf                # 政策导向文件
│   │   ├── industry_guide.docx            # 行业指引
│   │   └── mock_external_pool.json        # 50 家外网 mock 企业池
│   └── tech_kb/
│       └── ...
├── agent_credit/                          # v3.1 改造
│   ├── corp_fujian_zhongrui/              # 对公场景
│   │   ├── scenario.json
│   │   ├── enterprise_profile.json
│   │   ├── agent6_report.json             # Agent6 预置报告输出
│   │   └── similar_cases.json             # 同业案例库
│   └── retail_zhangsan/                   # 对私场景
│       └── ...
├── agent_alert/                           # v3.1 改造
│   ├── microloan_scan/                    # 小微扫描场景
│   │   ├── scenario.json
│   │   ├── customers_100.xlsx             # 100 家在贷客户
│   │   ├── alert_rules.json               # 20+ 预警规则
│   │   └── internal_policy.docx           # 管理制度
│   └── supply_chain_scan/
│       └── ...
└── agent_compliance/                      # v3.1 改造
    ├── internet_loan_compliance/          # 互联网贷款巡检
    │   ├── scenario.json
    │   ├── policy_bank_2021.pdf
    │   ├── internal_rules.docx
    │   └── business_records_100.xlsx      # 100 条业务数据
    └── aml_compliance/
        └── ...
```

---

## 6. 技术架构

### 6.1 共享层（v3.1 新增 / 扩展）

| 模块 | 文件 | 职责 |
|------|------|------|
| SearchProvider | `shared/search_provider.py` | 对外部搜索的抽象接口（Mock + Web）|
| KnowledgeBase | `shared/knowledge_base.py` | 多文件上传 + 分类 + 解析 |
| RuleExtractor | `shared/rule_extractor.py` | LLM 从非结构化文档抽规则 |
| Matcher | `shared/matcher.py` | 通用打分 + 分级 |
| ScanModels | `shared/scan_models.py` | 共用 Pydantic 模型 |
| BaseAgent | `shared/base_agent.py` | 事件协议 + LLM 封装（v3.0 已有）|
| EnterpriseProfile | `shared/enterprise_profile.py` | 企业画像（v3.0 已有）|
| LLMClient | `llm.py` | 统一 LLM 调用（v3.0 已有）|

### 6.2 各 Agent 后端（v3.1 更新）

| Agent | 保留模块 | 重写模块 | 新建模块 |
|-------|---------|---------|---------|
| agent_channel | channel_rules.py, scoring.py | agent.py, prompts.py | knowledge_base.py, profile_extractor.py, lead_finder.py, product_recommender.py |
| agent_riskctrl | 全部保留 | 无 | 无 |
| agent_credit | risk_classifier.py, rating_engine.py, approval_engine.py | agent.py, prompts.py | decision_engine.py, scoring_model_corp.py, scoring_model_retail.py, case_retriever.py, advisor_formatter.py |
| agent_alert | alert_engine.py, disposition.py, trend_analyzer.py | agent.py, prompts.py | customer_scanner.py, rule_extractor.py, cross_matcher.py |
| agent_compliance | policy_parser.py, compliance_checker.py, defect_classifier.py | agent.py, prompts.py | knowledge_base.py, rule_set_builder.py, event_extractor.py, matrix_matcher.py |

### 6.3 前端（v3.1 改造）

| 文件 | v3.0 状态 | v3.1 改造 |
|------|----------|----------|
| portal_app.py | ✅ 完成（众安蓝 Header + 全局 API Key + 6 Tab）| 仅更新 Tab 内的 Demo 场景卡 |
| agent_channel/app_demo.py | v3.0 实现（场景卡 + chatbot）| **重写**：KB 上传 + 画像卡 + 线索榜单 + 产品推荐 |
| agent_credit/app_demo.py | v3.0 实现 | **重写**：对公 / 对私 Tab 切换 + 决策 Dashboard |
| agent_alert/app_demo.py | v3.0 实现（信号灯 + 三栏）| **重写**：KB 上传 + 扫描进度 + 分级榜单 |
| agent_compliance/app_demo.py | v3.0 实现 | **重写**：KB 上传（三类分组）+ 扫描进度 + 违规榜 |
| agent_riskctrl/app_demo.py | v3.0 实现 | 不变 |

---

## 7. 知识库设计

### 7.1 通用知识库（平台级）

| 知识库 | 内容 | 更新频率 |
|-------|------|---------|
| 行业模板库 | 各类银行报告模板 | 按需 |
| 行业知识库 | 行业分类、特征、风险 | 季度 |
| 政策法规库 | 监管政策文件 | 实时 |
| 财务基准库 | 行业财务指标基准值 | 年度 |

### 7.2 客户私有知识库（v3.1 强化）

Agent1 / 4 / 5 的核心输入，必须做好设计：

| 知识库 | 面向 Agent | 内容 |
|-------|-----------|------|
| 已有客户名录 | Agent1 | Excel / CSV，至少含企业名 + 行业 + 规模 |
| 政策导向文件 | Agent1 / 5 | Word / PDF，可多份 |
| 行业指引文件 | Agent1 | Word / PDF / TXT |
| 预警规则库 | Agent4 | JSON / 可配置表单 |
| 在贷客户名录 | Agent4 | Excel / CSV，全量客户 |
| 内部管理制度 | Agent4 / 5 | Word / PDF |
| 监管政策库 | Agent5 | PDF / Word，可多份 |
| 业务运行数据 | Agent5 | Excel / CSV，审批台账 / 合同 / 放款 |
| 白 / 黑名单 | Agent3 / 4 | Excel |

### 7.3 共享数据载体

- EnterpriseProfile：企业画像 Pydantic 模型，40+ 字段（v3.0 已有）
- ReportJSON：Agent6 → Agent3 数据接口（v3.1 新增规范）
- DecisionAdvice：Agent3 → Agent6 回写字段（v3.1 新增规范）
- CompanyProfile：SearchProvider 统一输出（v3.1 新增规范）

---

## 8. 排期规划（v3.1 更新）

| 阶段 | 时间 | 内容 | 状态 |
|------|------|------|------|
| P1 报告引擎 | 3.23-4.12 | 报告生成助手 MVP + 架构改造 | ✅ 完成 |
| P2 Agent 原型 | 4.13 | 5 个 Agent 后端代码 | ✅ 完成 |
| P3 PRD + 方案 v1.0 | 4.13（上午）| 5 个 PRD + 改造方案 v1.0 | ✅ 完成 |
| **P3.1 PRD 修正 v2.0** | **4.13（下午）** | **共享架构 + 4 份 v2.0 PRD + 改造方案 v2.0** | **🔄 本轮** |
| P4 共享层开发 | 4.14-4.15 | SearchProvider / KnowledgeBase / Matcher 等 | 待启动 |
| P4.1 Agent 重写 | 4.16-4.22 | Agent1 / 3 / 4 / 5 重写 + Mock 数据 | 待启动 |
| P4.2 Demo 整合 | 4.23-4.26 | Portal 场景更新 + 串联演示 | 待启动 |
| P5 平台适配 | 4.27-5.10 | API 化 + 知识库对接 + Agent 配置 | 待启动 |
| P6 客户交付 | 5.11-5.17 | 集成测试 + 客户演示 | 待启动 |

---

## 9. 风险与应对（v3.1 更新）

| 风险 | 级别 | 应对 |
|------|------|------|
| Agent1 / 3 / 4 / 5 重写工作量大 | **高** | 并行开发 + 共享层先行（共享层做完 Agent 层能快速堆） |
| 真搜索 API 不稳定（裁判文书反爬）| 中 | Demo 用 MockProvider，生产再接；接口已隔离 |
| LLM 规则抽取准确度不够 | 中 | Schema 校验 + 人工审核兜底；抽完规则可人工修订 |
| 批量扫描耗时长（100 家 × 双路）| 中 | 并发 + 进度条 + 分段展示；UI 不阻塞 |
| 对公 / 对私模型差异大强行整合 | 中 | 双板块各自独立 Scoring Model，只共享上层接口和 UI 骨架 |
| Mock 数据真实性不足 | 中 | 真实行业名 + 合理数字区间 + 场景卡说明"mock 演示" |
| 客户质疑 Demo vs 生产差异 | 中 | 用 SearchProvider 抽象明确讲解"一行代码切换"的架构 |

---

## 10. 资源需求（v3.1 更新）

| 角色 | 人数 | 职责 |
|------|------|------|
| 产品（刘野）| 1 | PRD、方案、Demo 脚本、质量把关 |
| 后端 | 1-2 | 共享层 + 4 个 Agent 重写 + 数据流 |
| 前端 | 1 | 5 个 Agent 差异化 UI（Portal 已完成）|
| AI 工程 | 1 | Mock 数据、提示词调优、LLM 接入 |

v3.1 比 v3.0 工作量约增加 50%，建议后端加一人并行。

---

## 附录

### A. 子 Agent 独立 PRD（v3.1 更新）

| Agent | 当前 PRD 版本 | 状态 |
|-------|--------------|------|
| Agent1 全渠道流量匹配 | v2.0 | 本轮产出 |
| Agent2 风控策略运营 | v1.0 | 不变 |
| Agent3 授信决策辅助 | v2.0 | 本轮产出 |
| Agent4 贷中风险预警 | v2.0 | 本轮产出 |
| Agent5 合规巡检 | v2.0 | 本轮产出 |

### B. 相关文档

- 改造方案：`docs/改造方案_信贷AI智能体矩阵_v2.0.md`（v1.0 已被替代）
- 共享架构：`docs/共享架构_知识库扫描范式_v1.0.md`
- 报告生成：`docs/PRD_报告生成助手.md`（不变）

### C. 飞书同步清单

本次 v3.1 的文档需要同步到飞书「人人都是TMD产品经理」知识库，包括：
1. PRD_客户经理个人助手_v3.1.md（本文档）
2. 改造方案_信贷AI智能体矩阵_v2.0.md
3. 共享架构_知识库扫描范式_v1.0.md
4. PRD_全渠道流量匹配智能体_v2.0.md
5. PRD_授信决策辅助智能体_v2.0.md
6. PRD_贷中风险预警助手_v2.0.md
7. PRD_合规巡检智能体_v2.0.md

---

**文档结束**
