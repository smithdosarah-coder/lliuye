# PRD: 授信决策辅助智能体 v2.0 — 双板块决策支持引擎

> **版本**: v2.0（完全替换 v1.0）
> **日期**: 2026-04-14
> **作者**: 众安信科 AI 中台 / 乾策平台（X-Nexus）
> **产品线**: 信贷 AI 智能体矩阵 · Agent3
> **状态**: Demo 改造 PRD — 重新定位 + 对公/对私双板块拓展
> **取代版本**: PRD\_授信决策辅助智能体\_v1.0.md（直接覆盖，v1.0 内容全部作废）

---

## 0. 变更摘要（Executive Summary）

v1.0 把 Agent3 定位为 "读企业画像 JSON → 出四维评分 + 额度建议 + 审批意见书"。这个定位和 Agent6（报告生成助手）功能重叠——Agent6 的输出里本身就含有风险章节、担保章节、审批意见章节。两个 Agent 同时摆在客户面前会出现"同样一份材料，出了两份结论"的尴尬局面。

v2.0 做了三件事：

1. **重新定位**：Agent3 不再和 Agent6 抢"写报告"的活。Agent3 的输入不是客户原始材料，也不是 EnterpriseProfile JSON，**而是 Agent6 产出的授信调查报告本身**，再叠加多源外部信息（行业基准/历史案例/内部指引/征信），输出一份**决策 Dashboard**，面向审贷会主席/分管行长/风控主管，证明"同一份材料能不能授信、额度给多少、期限多长、利率多少、有没有触发红线"。
2. **双板块拓展**：把 Agent3 拆成**对公板块**（企业授信，50 万-5000 万）和**对私板块**（个人/零售授信，5 万-500 万），两个板块共享决策引擎、红线规则库、案例库、Dashboard UI 骨架，但在数据源、评分模型、审批流、合规要求、可视化重点上做差异化。
3. **串联演示**：Agent6 Word 报告生成完毕后，在 Agent6 的 UI 上加一颗"送 Agent3 做决策"按钮，点击后跳转到 Agent3 的对公 Dashboard，直接消费 Agent6 刚才生成的 ReportJSON，做到"报告生成 → 决策接力"的闭环演示；Agent3 的决策意见反过来可回写到 Agent6 报告的"审批意见"章节。

本 PRD 给出的是**可交付 Demo** 的完整 PRD，篇幅 18000-22000 字，包含产品定位、与 v1.0 的差异对照、Demo 目标、双场景设计、前端交互、后端架构、数据模型、LLM 调用、Mock 数据、Agent6↔Agent3 接口、验收标准、风险偏好配置 共 12 章和附录。

---

## 1. 产品定位

### 1.1 一句话定位

> **Agent3 是授信决策支持引擎（对公 + 对私双板块）。它不生产授信报告，它消费授信报告；它不代替审贷会拍板，它把审贷会 1 小时才能看完的材料压缩成一张 90 秒看懂的决策 Dashboard，并把批/不批、额度、期限、利率、触发红线的建议一次性摆在桌上。**

### 1.2 与 Agent6 的上下游关系

这是 v2.0 最重要的一条边界。**Agent6 = 文书自动化；Agent3 = 决策支持。** 两者的分工、输入、输出、受众、度量各不相同：

| 维度 | Agent6 报告生成助手 | Agent3 授信决策辅助 |
|------|----------------------|----------------------|
| 本质 | 文书自动化（Document Automation） | 决策支持（Decision Support） |
| 输入 | 客户原始材料（PDF/Word/Excel/图片） | Agent6 产出的 ReportJSON + 多源补充信息 |
| 核心工作 | 解析 → 分类 → 章节撰写 → 锚点校验 | 特征抽取 → 评分 → 规则判定 → 案例检索 → 决策格式化 |
| 产出形态 | 15000 字的 Word 授信调查报告 | 一张决策 Dashboard + 一张决策卡片 |
| 面向受众 | 审批委员会成员、监管、归档 | 审贷会主席、分管领导、风控主管、零售个贷审批员 |
| 衡量指标 | 填写覆盖率、锚点一致性、自然度 | 决策速度、一致性、可回溯性、红线命中率 |
| 时效 | 分钟级（5-10 分钟出 Word） | 对公分钟级、对私秒级 |
| 是否产生数字结论 | 否（陈述事实） | 是（批/额度/期限/利率） |

### 1.3 上下游数据流（核心图）

```
┌─────────────────┐    ┌──────────────────┐    ┌────────────────────────┐
│ 客户原始材料    │ →  │ Agent6 报告生成  │ →  │ 授信调查报告 Word       │
│ (PDF/Word/Excel)│    │ (文书自动化)     │    │ + ReportJSON (结构化) │
└─────────────────┘    └──────────────────┘    └───────────┬────────────┘
                                                           │
                                                           │ ReportJSON 送入
                                                           ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │                       Agent3 授信决策辅助                        │
  │                                                                  │
  │   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
  │   │ 行业基准 │  │ 内部指引 │  │ 历史案例 │  │ 征信数据 │  多源  │
  │   │ (Mock)   │  │ (Mock)   │  │ (Mock)   │  │ (Mock)   │  补充  │
  │   └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
  │                           ↓                                      │
  │   FeatureExtractor → ScoringModel → RuleEngine → CaseRetriever  │
  │                           ↓                                      │
  │                    AdvisorFormatter                              │
  └───────────────────────────────┬──────────────────────────────────┘
                                  │
                                  ▼
  ┌────────────────────────────────────────────────────────────────┐
  │ 决策 Dashboard                                                 │
  │ ┌────────────────────────────────────────────────────────┐     │
  │ │ 决策结论: 批 / 不批 / 有条件批                          │     │
  │ │ 建议额度: 300 万                                        │     │
  │ │ 期限: 3 年                                              │     │
  │ │ 利率: 6.5%                                              │     │
  │ │ 触发红线: 2 条                                          │     │
  │ └────────────────────────────────────────────────────────┘     │
  └────────────────────────────┬───────────────────────────────────┘
                               │ DecisionAdvice 可回写
                               ▼
                      Agent6 报告的"审批意见"章节
```

### 1.4 不套"知识库扫描范式"

Agent1（全渠道流量匹配）、Agent4（贷中预警）、Agent5（合规巡检）本质上都是**一对多批量扫描**——在 N 个候选里筛出若干个 Top。Agent3 不是。**Agent3 是一对多维深入**：对**一个**申请（一家企业或一个自然人），做 N 个维度的判断（财务、行业、经营、担保，或者偿债、意愿、稳定、抵押），每个维度都要有可追溯、可解释的证据链。

因此 Agent3 的架构核心不是"检索 + 排序"，而是一条**流水线**：

```
DecisionEngine =
    FeatureExtractor              (从 ReportJSON + 多源数据抽特征)
  + ScoringModel(对公/对私可切换)  (打分——对公用四维风险，对私用评分卡)
  + RuleEngine                    (红线规则判定)
  + CaseRetriever                 (历史案例检索对比)
  + AdvisorFormatter              (决策意见生成 + LLM 自然语言包装)
```

这条流水线里，"打分"这一步根据板块切换：对公→`ScoringModel_对公`（四维风险加权）；对私→`ScoringModel_对私`（评分卡多项加权 + 等级映射）。其他四个环节（抽特征、红线、案例、格式化）是板块共享的。

### 1.5 双板块设计（用户计划内）

```
┌─────────────────────────────────────────────────────────────────┐
│                  Agent3 授信决策辅助（共享底座）                │
│   决策引擎 / 红线规则库 / 案例库 / Dashboard UI 骨架            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
      ┌────────────────────┴─────────────────────┐
      ▼                                          ▼
┌──────────────────┐                    ┌──────────────────┐
│ 🏢 对公板块      │                    │ 👤 对私板块      │
│ (企业授信)       │                    │ (个人/零售)      │
├──────────────────┤                    ├──────────────────┤
│ 输入:            │                    │ 输入:            │
│ - 企业材料       │                    │ - 身份信息       │
│ - Agent6 报告    │                    │ - 收入证明       │
│ - 工商/征信      │                    │ - 人行征信       │
│ - 财报           │                    │ - 银行流水       │
│                  │                    │ - 社保公积金     │
│                  │                    │ - 抵押估值       │
├──────────────────┤                    ├──────────────────┤
│ 评分模型:        │                    │ 评分模型:        │
│ 四维风险         │                    │ 评分卡 (FICO-式) │
│ (财务/行业/      │                    │ 偿债/意愿/       │
│  经营/担保)      │                    │ 稳定/抵押        │
├──────────────────┤                    ├──────────────────┤
│ 输出:            │                    │ 输出:            │
│ - 批/不批        │                    │ - 评分 300-850   │
│ - 额度 50万-5000万│                   │ - 批/不批        │
│ - 期限           │                    │ - 额度 5万-500万 │
│ - 利率           │                    │ - 利率档位       │
│ - 红线清单       │                    │ - 评分卡明细     │
└──────────────────┘                    └──────────────────┘
```

### 1.6 板块差异对照（必读）

| 维度 | 对公板块 | 对私板块 |
|------|-----------|-----------|
| 决策速度 | 分钟级（评审会讨论用，等得起分钟级） | 秒级（零售场景，秒级才可用） |
| 主要数据源 | 多源复杂（财报、工商、税务、发票、供应链） | 征信中心为主（银联、社保、公积金、抵押估值） |
| 审批流 | 三级审批（客户经理→分管行长→审贷会） | 评分卡自动决策 + 人工抽查 |
| 合规要求 | 尽职调查、反洗钱、关联交易核查 | 个人隐私合规、征信合规、《个人信息保护法》 |
| 可视化重点 | 风险矩阵 + 财务雷达 + 同业对标 | 评分构成 + 征信快照 + 评分卡分档 |
| 决策因子数 | 4 维 × 若干子项 | 评分卡通常 15-25 个变量 |
| Demo 示例额度区间 | 50 万-5000 万 | 5 万-500 万 |
| LLM 参与度 | 中（解读、意见生成） | 低（自动化为主，仅边界案例用 LLM 解释） |
| 风险容忍 | 高（每笔金额大，需深度尽调） | 低（靠量补差，依赖评分卡与规则） |
| 拒绝成本 | 高（流失一个大客户） | 低（拒掉一笔可再找一笔） |

### 1.7 两个板块如何共存于一个 Agent

**顶部 Tab 切换**：UI 第一眼就是两个 Tab：`🏢 对公`、`👤 对私`。切换 Tab 时：
- 左侧输入区变化（对公是"选择企业" + "加载 Agent6 报告"；对私是"选择个人 Profile"）
- 右侧 Dashboard 变化（对公显示雷达图+同业；对私显示评分卡+征信）
- 底部决策卡片变化（对公侧重额度/期限；对私侧重评分档位/利率档位）

**后端共享**：底层的 `DecisionEngine`、`RuleEngine`、`CaseRetriever`、`AdvisorFormatter`、`RiskAppetiteConfig` 是板块无关的；只有 `ScoringModel` 按板块切换 (`ScoringModel_对公` / `ScoringModel_对私`)。

### 1.8 核心价值

- **对公**：把 1 小时读报告、对比同业、查红线的过程压缩到 2 分钟，输出决策级别的 Dashboard，不替代审贷会但缩短到会前准备时间；
- **对私**：把普惠小微个人经营贷的批核从 T+1 压到 10 秒内，评分卡透明可审计，争议案件可降到人工复核；
- **矩阵协同**：Agent6 → Agent3 闭环演示（文书自动化 → 决策支持）展示平台价值，不是单点工具拼盘。

---

## 2. 与 v1.0 的差异对照

### 2.1 定位差异（核心变化）

| 项 | v1.0 | v2.0 |
|----|------|------|
| 核心定位 | 读 EnterpriseProfile JSON → 出四维评分 + 额度建议 + 审批意见书 | **消费 Agent6 报告 + 多源信息 → 出决策 Dashboard（对公+对私双板块）** |
| 与 Agent6 关系 | 解耦（JSON 消费） | **上下游串联**（Agent6 → Agent3 一键接力 + 决策回写） |
| 板块覆盖 | 仅对公 | **对公 + 对私双板块** |
| 核心产出 | 审批意见书（文本） | **决策 Dashboard + 决策卡片（批/额度/期限/利率/红线）** |
| 与 Agent6 功能是否重复 | **重复**（都在写审批意见） | 不重复（Agent6 写报告，Agent3 出决策） |
| 适用演示场景 | 单 Agent 演示（孤立） | 单 Agent 演示 + 矩阵闭环演示 |

### 2.2 代码层差异（保留/重写/新建清单）

基于现有 `agent_credit/` 目录的代码现状（v1.0 阶段已写了 `risk_classifier.py` / `rating_engine.py` / `approval_engine.py` / `agent.py` / `app.py` / `app_demo.py` / `prompts.py`）：

| 文件 | v1.0 状态 | v2.0 动作 | 说明 |
|------|-----------|-----------|------|
| `agent_credit/risk_classifier.py` | 已有（5 维风险分类） | **保留 + 改造** | 4 维框架复用到对公板块（去掉"管理风险"维度，与 v2.0 对公四维一致，或作为子项并入"经营风险"） |
| `agent_credit/rating_engine.py` | 已有（A-E 评级） | **保留 + 复用** | 对公板块的风险等级 A/B/C/D 直接复用，对私用另一套评分卡等级 |
| `agent_credit/approval_engine.py` | 已有（规则驱动审批） | **保留 + 改造** | 规则引擎骨架可复用到 v2.0 的 `RuleEngine`，但需扩展红线规则库 + 可配置化 |
| `agent_credit/agent.py` | 已有（Agent6 壳式调用） | **重写** | 改为 `CreditDecisionAgent`，不再调用 `form_filler`，改为消费 ReportJSON |
| `agent_credit/app.py` | 已有（简单对话界面） | **重写** | 重写为双板块 Tab + Dashboard 可视化 |
| `agent_credit/app_demo.py` | 已有 | **重写** | 合并到 `app.py` 里，作为 Demo 入口 |
| `agent_credit/prompts.py` | 已有（风险评估/评级/审批 prompt） | **重写** | 替换为"决策解读/案例匹配/红线解释/决策说明"四组 prompts，对公/对私各一套 |
| `shared/base_agent.py` | 已有 | **保留** | BaseAgent 骨架不动 |
| `shared/enterprise_profile.py` | 已有（Pydantic 模型） | **保留 + 扩展** | 扩展 `risk_tags`、新增 `agent_outputs.agent6_report_json` 字段承载 Agent6 报告 |
| `shared/demo_ui.py` | 已有 | **保留 + 扩展** | Dashboard 共用组件抽象到这里 |
| `decision_engine.py` | 无 | **新建** | Agent3 v2.0 的流水线总调度器 |
| `feature_extractor.py` | 无 | **新建** | 从 ReportJSON + 多源数据抽取特征 |
| `scoring_model_对公.py`（`scoring_model_corporate.py`） | 无 | **新建** | 对公评分模型（四维风险加权，调用 `risk_classifier`） |
| `scoring_model_对私.py`（`scoring_model_retail.py`） | 无 | **新建** | 对私评分卡模型 |
| `rule_engine_v2.py` | 无 | **新建** | 红线规则引擎（可配置 JSON 规则库） |
| `case_retriever.py` | 无 | **新建** | 历史案例检索（Mock 50 条对公案例） |
| `advisor_formatter.py` | 无 | **新建** | 决策意见格式化器（调 LLM） |
| `risk_appetite_config.py` | 无 | **新建** | 风险偏好配置（红线规则 + 权重可自定义） |
| `mock_data/corporate_profiles/` | 无 | **新建** | 3-5 个预置企业 + 同业案例 50 条 |
| `mock_data/retail_profiles/` | 无 | **新建** | 3-5 个预置个人 Profile + 评分卡基准 |
| `mock_data/red_line_rules.json` | 无 | **新建** | 红线规则库（对公 30 条 / 对私 20 条） |
| `mock_data/industry_baselines_v2.json` | 无 | **新建** | 行业基准数据（扩展 v1.0 的版本） |

### 2.3 v1.0 中要**明确作废**的内容

v1.0 中以下几块内容在 v2.0 里直接作废，不再作为 Demo 设计约束：

1. **v1.0 第 2 章的单 Agent Demo 目标**——过于局限在"四维评分 + 额度建议"这个动作上，v2.0 重新定义 Demo 目标为"决策支持 + 矩阵串联"；
2. **v1.0 第 3 章的场景 1/2**——瑞恒精密/鼎盛商贸两个企业画像本身可以复用到 v2.0 的对公场景，但场景**流程**必须换成"消费 Agent6 报告"而不是"加载 EnterpriseProfile JSON"；
3. **v1.0 第 4 章的三栏式布局**——被 v2.0 的"顶部双板块 Tab + 三栏布局"替代，UI 交互流程要重画；
4. **v1.0 第 9 章"接口 2: 完整评估报告 → 审批系统"**——这是"独立 Agent 输出给外部审批系统"的接口，v2.0 改为"Agent3 → Agent6 回写"；
5. **v1.0 附录 A 的代码映射表**——v2.0 的代码清单已在上文 2.2 节全面覆盖，作废。

保留可复用的：
- v1.0 场景 1/2 的企业画像数据（瑞恒、鼎盛）——对公 Mock 数据继续用；
- v1.0 第 5.4 节的四维评分公式表（分段线性插值）——对公 `ScoringModel` 直接照搬；
- v1.0 第 5.5 节的四种额度测算方法（营收法/净资产法/现金流法/担保法）——作为对公额度推荐的子能力保留；
- v1.0 第 8.2-8.3 节的同业对标 / 行业基准 Mock 数据——直接用在对公的 `CaseRetriever`；
- v1.0 第 7 章的 LLM 调用策略（两次调用上限）——对公保持相同约束，对私减为 0-1 次。

---

## 3. Demo 目标

### 3.1 给谁看

| 受众 | 关注点 | 对应板块 |
|------|--------|----------|
| **审贷会主席 / 授信评审总经理** | 决策一致性、决策效率、可追溯性 | 对公 |
| **分管行长（信贷业务）** | 风险/收益平衡、额度合理性、同业对标 | 对公 |
| **风控主管 / 首席风险官** | 红线规则可配置、决策偏差归因、合规 | 两者 |
| **零售个贷审批团队负责人** | 批核速度、评分卡透明、合规人工抽查可行性 | 对私 |
| **银行科技部门负责人** | 与现有授信系统集成成本、数据安全 | 两者 |
| **众安信科商务团队** | 差异化卖点（VS 同方/邦盛/星环） | 两者 |

### 3.2 证明什么

1. **证明"决策速度可缩短到秒/分钟级"**——对公场景 2 分钟出 Dashboard，对私 10 秒出评分；
2. **证明"决策有证据链、可回溯"**——每一条结论都能点进去看到：来源于 Agent6 报告的哪一段、来自哪一条红线规则、匹配了哪一个历史案例；
3. **证明"红线规则可配置"**——演示现场可以动态修改红线（比如把"关联交易占比>30%"改成>20%），立刻重算决策；
4. **证明"矩阵协同（Agent6 → Agent3 串联）"**——Agent6 生成报告后一键送入 Agent3，决策结果回写到报告的"审批意见"章节；
5. **证明"对公/对私双板块一体化"**——同一个 Agent 能同时支持企业授信和个人授信，底座复用而不是两个独立系统拼接。

### 3.3 Demo 核心量化指标

| 指标 | 目标值 | 板块 |
|------|--------|------|
| 对公端到端决策耗时（点击"做决策"→ Dashboard 完整展示） | < 2 分钟 | 对公 |
| 对私端到端决策耗时（选择 Profile → 评分展示） | < 10 秒 | 对私 |
| 对公 LLM 调用次数 | ≤ 2 次（决策说明 1 次 + 红线解释 1 次） | 对公 |
| 对私 LLM 调用次数 | ≤ 1 次（仅边界案例 / 决策说明） | 对私 |
| 红线规则可配置性 | 演示时可在 UI 上改红线阈值并立即生效 | 两者 |
| Agent6 → Agent3 串联耗时（从点击"送 Agent3"到 Dashboard 打开） | < 3 秒 | 对公 |
| 决策回写耗时（Agent3 决策 → Agent6 报告更新） | < 2 秒 | 对公 |

### 3.4 Demo 交付物清单

- 可运行的 Gradio 前端（对公+对私双 Tab，Dashboard 可视化）
- 对公预置 3 个企业 Profile（含 Agent6 生成的 ReportJSON）——福建中锐网络、瑞恒精密、鼎盛商贸
- 对私预置 3 个个人 Profile（含征信/流水/抵押）——张三（餐饮）、李四（教培）、王五（装修）
- 对公同业案例库 50 条（Mock）
- 对私评分卡基准数据 + 10 条相似案例
- 红线规则库（对公 30 条 + 对私 20 条，JSON 可编辑）
- Agent6 → Agent3 一键串联演示视频脚本

---

## 4. 演示场景设计

### 4.1 场景卡 A（对公）🏢 — 福建中锐网络 · Agent6→Agent3 闭环演示

#### 企业背景

- 企业名称：福建中锐网络科技有限公司
- 行业：I65 互联网与相关服务（软件开发+SaaS）
- 成立年限：6 年
- 员工数：87 人
- 申请额度：300 万元流动资金贷款
- 期限：3 年

#### 演示流程（完整串联，7 个 Step）

```
Step 0 — 前置：Agent6 已生成报告
  • 客户经理在 Agent6 上传福建中锐网络的材料（财报、工商、流水）
  • Agent6 自动生成 15000 字授信调查报告 Word + ReportJSON
  • 报告中"审批意见"章节暂时留空，等待 Agent3 反填

Step 1 — Agent6 → Agent3 串联触发
  • Agent6 完成页面右下角弹出按钮："送 Agent3 做决策"
  • 用户点击
  • 系统跳转到 Agent3 对公 Tab，自动加载 Agent6 的 ReportJSON

Step 2 — Agent3 对公 Dashboard 加载
  • 顶部横幅："已从 Agent6 加载 [福建中锐网络] 报告（报告生成于 YYYY-MM-DD HH:MM）"
  • 左侧面板展示报告摘要（企业画像、财务锚点、担保安排、申请事项）

Step 3 — 特征抽取（< 3 秒）
  • FeatureExtractor 从 ReportJSON 抽取 60+ 特征
    - 财务（资产负债率、营收增长、利润率等 20 项）
    - 行业（景气度、集中度、周期性等 8 项）
    - 经营（成立年限、员工规模、现金流覆盖等 15 项）
    - 担保（抵押物覆盖率、类型、保证人等 10 项）
    - 外部（工商异常、税务评级、关联交易等 7 项）
  • 左侧面板显示"已抽取特征：60 项"

Step 4 — 确定性计算（< 5 秒，无 LLM）
  • 四维风险评分（复用 v1.0 的四维评分算法）
  • 红线规则判定（遍历 30 条对公红线，命中 2 条）
  • 额度计算（营收法/净资产法/现金流法/担保法 四种取交集）
  • 同业对标（从 50 条案例库中检索最相似 5 家）
  • 中间结果在 Dashboard 上实时渲染（雷达图/条形图/表格）

Step 5 — LLM 生成决策意见（1 次调用，< 20 秒）
  • 输入：四维评分 + 红线清单 + 案例对比 + 申请事项
  • 输出：决策意见（批/不批/有条件批 + 额度 + 期限 + 利率 + 附加条件 + 理由）
  • 展示在右侧决策卡片

Step 6 — LLM 红线解释（1 次调用，< 10 秒）
  • 输入：命中的红线 + 企业画像关键特征
  • 输出：每条红线为什么命中、严重程度、是否可豁免、豁免条件
  • 展示在决策卡片下方"红线提示"区域

Step 7 — 决策回写 Agent6
  • Dashboard 右下角按钮："回写到 Agent6 报告"
  • 用户点击
  • Agent3 将决策意见（批 / 300 万 / 3 年 / 6.5% / 2 条红线）写入 Agent6 报告的
    "四、授信结论 — 审批意见"章节
  • 用户切回 Agent6 Tab，看到报告已更新
```

#### 预期输出

```
┌─────────────────────────────────────────────────────┐
│ 决策结论: 有条件批准                                 │
│ 风险等级: B (良好，70 分)                           │
│ 建议额度: 300 万元 (申请额度 300 万元，全额批准)    │
│ 期限: 3 年 (申请 3 年，维持)                        │
│ 利率: 6.5% (LPR + 85BP)                             │
│ 触发红线: 2 条                                      │
│   1. 关联交易占比 32%（阈值 30%）                   │
│   2. 应收账款周转天数 140 天（阈值 120 天）         │
│ 豁免条件:                                           │
│   - 关联交易提供审计说明                            │
│   - 每季度提交应收账款账龄表                        │
└─────────────────────────────────────────────────────┘
```

### 4.2 场景卡 B（对私）👤 — 张三餐饮个体工商户经营贷

#### 个人背景

- 姓名：张三
- 年龄：42 岁
- 职业：餐饮店主（一家 120㎡ 的家常菜馆，4 年经营）
- 征信：无逾期，近 2 年有 3 笔正常还清的经营贷
- 月收入（流水均值）：6.5 万
- 抵押物：自有住房（评估值 200 万，无其他抵押）
- 申请额度：50 万
- 期限：36 个月
- 用途：扩大经营（装修 + 采购设备）

#### 演示流程（5 个 Step，秒级完成）

```
Step 1 — 选择 Profile
  • 对私 Tab → 左侧下拉菜单选择"张三 - 餐饮个体户"
  • 系统自动加载 profile_zhangsan.json
  • 左侧展示基础画像 + 征信摘要

Step 2 — 特征抽取（< 1 秒）
  • 从 Profile 抽取 22 个评分卡变量
  • 分为四大类：偿债能力（6 项）/ 还款意愿（5 项）/ 稳定性（6 项）/ 抵押估值（5 项）

Step 3 — 评分卡计算（< 1 秒，无 LLM）
  • 评分卡加权得分（300-850 区间）
  • 各子项得分明细
  • 评分档位映射（ 优<700 / 良 700-759 / 中 760-799 / 优 800+ ）
  • 红线规则判定（20 条对私红线，命中 0 条）

Step 4 — 决策规则 + 额度/利率档位（< 1 秒）
  • 根据评分档位查决策表 → 批 / 不批 / 人工复核
  • 额度上限 = min(评分档位额度上限, 抵押物 70%, 月收入 × 20)
  • 利率档位映射（评分越高利率越低）

Step 5 — 可选 LLM 决策说明（0-1 次调用）
  • 如果是边界案例（评分在 695-705 之间）或命中红线，调用 LLM 解释
  • 否则直接用模板化说明
  • 展示在决策卡片
```

#### 预期输出

```
┌─────────────────────────────────────────────┐
│ 个人信用评分: 720                           │
│ 档位: 良好 (700-759)                        │
│ 决策: 批准                                  │
│ 建议额度: 50 万元 (申请 50 万，全额批准)    │
│ 利率: 5.8% (LPR + 20BP)                     │
│ 触发红线: 无                                │
│                                             │
│ 评分卡构成:                                 │
│   偿债能力    780  (权重 30%)               │
│   还款意愿    750  (权重 25%)               │
│   稳定性      680  (权重 25%)               │
│   抵押估值    700  (权重 20%)               │
└─────────────────────────────────────────────┘
```

### 4.3 串联演示脚本（20 分钟全链路）

| 时间 | 动作 | Agent | 目的 |
|------|------|-------|------|
| 00:00-02:00 | 开场，介绍乾策平台 5 个 Agent 矩阵 | Portal | 铺垫 |
| 02:00-06:00 | Agent6 上传福建中锐材料，生成 Word 报告 | Agent6 | 证明文书自动化能力 |
| 06:00-06:30 | 点击"送 Agent3 做决策"，一键跳转 | Agent6 → Agent3 | 证明矩阵串联 |
| 06:30-10:00 | Agent3 对公 Dashboard 加载 → 特征抽取 → 评分 → 红线 → 额度 → 同业 → 决策 | Agent3 对公 | 证明决策支持能力 |
| 10:00-10:30 | 现场修改红线（把关联交易阈值从 30% 调到 20%），重算 | Agent3 对公 | 证明规则可配置 |
| 10:30-11:00 | 点击"回写到 Agent6 报告"，决策写入审批意见章节 | Agent3 → Agent6 | 证明闭环 |
| 11:00-11:30 | 切回 Agent6 Tab，看到报告已更新 | Agent6 | 验证闭环结果 |
| 11:30-12:30 | 切到对私 Tab，展示张三案例，秒级出评分 | Agent3 对私 | 证明双板块 |
| 12:30-14:00 | 介绍对公/对私差异（速度/数据源/合规） | Agent3 | 升华设计理念 |
| 14:00-20:00 | 其余 Agent（1/2/4/5）快速过一遍 | Portal | 完整矩阵 |

---

## 5. 前端交互设计

### 5.1 整体布局（顶部双 Tab + 三栏）

```
┌────────────────────────────────────────────────────────────────────────────┐
│ 众安信科 · 信贷AI智能体矩阵          Agent3 授信决策辅助    [⚙ 风险偏好]  │
├────────────────────────────────────────────────────────────────────────────┤
│ [🏢 对公授信 (企业)]   [👤 对私授信 (个人/零售)]       (Tab 切换)          │
├──────────────────┬─────────────────────────────────┬───────────────────────┤
│ 左侧面板 (280px) │ 中间主区域 (自适应)             │ 右侧面板 (380px)      │
│ 输入 / 状态      │ Dashboard 可视化区             │ 决策卡片 + 红线       │
│                  │                                 │                       │
│ ┌──────────────┐ │                                 │ ┌───────────────────┐ │
│ │ 选择申请     │ │                                 │ │ 决策结论          │ │
│ ├──────────────┤ │                                 │ │ ════════════════  │ │
│ │ • 中锐网络   │ │    (板块差异化内容)             │ │ 批 / 不批 /       │ │
│ │ • 瑞恒精密   │ │                                 │ │   有条件批        │ │
│ │ • 鼎盛商贸   │ │                                 │ │                   │ │
│ │              │ │                                 │ │ 额度: 300 万      │ │
│ │ [从Agent6加载]│ │                                 │ │ 期限: 3 年        │ │
│ └──────────────┘ │                                 │ │ 利率: 6.5%        │ │
│                  │                                 │ │                   │ │
│ ┌──────────────┐ │                                 │ │ 触发红线 (2)      │ │
│ │ 企业画像摘要 │ │                                 │ │ ════════════════  │ │
│ │ - 行业: I65  │ │                                 │ │ 1. 关联交易 32%   │ │
│ │ - 营收: 2.8亿│ │                                 │ │ 2. 应收账款 140d  │ │
│ │ - 员工: 87   │ │                                 │ │                   │ │
│ │ - 抵押: 房产 │ │                                 │ │ [豁免条件]        │ │
│ └──────────────┘ │                                 │ └───────────────────┘ │
│                  │                                 │                       │
│ ┌──────────────┐ │                                 │ ┌───────────────────┐ │
│ │ 状态指示     │ │                                 │ │ 相似历史案例      │ │
│ │ ✓ 报告加载   │ │                                 │ │ - 华鼎科技 (批)   │ │
│ │ ✓ 特征抽取   │ │                                 │ │ - 启明软件 (批)   │ │
│ │ ✓ 评分完成   │ │                                 │ │ - 云端数据 (拒)   │ │
│ │ ✓ 红线判定   │ │                                 │ └───────────────────┘ │
│ │ ✓ 案例检索   │ │                                 │                       │
│ │ ✓ 决策生成   │ │                                 │                       │
│ └──────────────┘ │                                 │                       │
├──────────────────┴─────────────────────────────────┴───────────────────────┤
│ [导出决策报告 PDF] [导出 JSON] [回写到 Agent6] [重新计算] [风险偏好调参]   │
└────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 对公 Dashboard（中间主区域）

对公场景下，中间主区域从上到下四个模块：

#### 5.2.1 四维风险雷达图

```
          财务风险 (72)
              *
           / . \
         /  .   \
   担保(82)--+--(65)行业
         \  .   /
           \ . /
              *
          经营风险 (78)

  图例: ━━━ 本企业  - - - 风险阈值  - - - 行业均值
```

- 企业得分：实线（品牌蓝 #1677FF 半透明填充）
- 风险阈值：虚线红色（60 分警戒线）
- 行业均值：虚线灰色（从 Mock 数据读取）
- 低于阈值的维度标红并加叹号
- 鼠标悬停显示子指标明细

#### 5.2.2 行业基准对比条形图

```
资产负债率     本企业 ████████▌ 45%       |
               行业中位 ███████▎ 41%      [领先/落后]
               
营收增长率     本企业 █████████▌ 22%      [领先]
               行业中位 ████▍ 8%          

应收账款天数   本企业 █████████████ 140d  [落后] ⚠
               行业中位 █████████▌ 95d    

净利率         本企业 ██████▊ 7%          [领先]
               行业中位 ████▌ 4.5%
```

#### 5.2.3 相似案例展示（最多 5 条）

| 企业 | 行业 | 营收 | 申请额度 | 综合评分 | 最终决策 | 理由 |
|------|------|------|----------|----------|----------|------|
| **[本企业] 福建中锐** | I65 | 2.8 亿 | 300 万 | 70 | 有条件批 | 关联交易触发 |
| 启明软件（相似度 92%） | I65 | 3.1 亿 | 400 万 | 74 | 批 | 无异常 |
| 华鼎科技（相似度 87%） | I65 | 2.5 亿 | 250 万 | 72 | 批 | 无异常 |
| 云端数据（相似度 85%） | I65 | 2.6 亿 | 500 万 | 58 | 拒 | 应收账款超标 |

#### 5.2.4 额度测算条形图

```
营收法       [───300───]
净资产法     [────350────]
现金流法     [──250──]
担保法       [──────420──────]

综合区间     [─ 250 ████ 300 ████ 420 ─]
                          ▲
                       申请 300 (命中区间)
```

### 5.3 对私 Dashboard（中间主区域）

对私场景下，中间主区域从上到下四个模块：

#### 5.3.1 评分卡构成条形图（各子项得分）

```
偿债能力        ████████████████▊ 780
  月收入稳定    ████████████████ 800
  债务收入比    ████████████▌ 720
  流水平均值    ████████████████▎ 810
  ...
  
还款意愿        ███████████████▎ 750
  征信查询次数  ████████████████▌ 820
  历史逾期      ████████████████████ 850
  ...
  
稳定性          █████████████ 680
  职业年限      █████████████▌ 690
  居住年限      ████████████▌ 670
  ...
  
抵押估值        ██████████████▎ 700
  抵押物类型    ████████████████ 800 (房产)
  LTV          ████████████ 650
  ...
                                   ──────
综合评分: 720 (良好 700-759)
```

#### 5.3.2 征信快照

```
┌──────────────────────────────────────────┐
│ 人行征信报告摘要 (查询日期 2026-04-12)   │
├──────────────────────────────────────────┤
│ 当前贷款笔数: 2 (正常)                   │
│ 当前信用卡: 3 张 (利用率 45%)            │
│ 24 个月查询次数: 4 次 (正常)             │
│ 历史逾期: 无                             │
│ 担保笔数: 1                              │
│ 账龄: 7.5 年                             │
└──────────────────────────────────────────┘
```

#### 5.3.3 抵押估值明细

```
┌──────────────────────────────────────────┐
│ 抵押物: 住宅 120m² (中心区)              │
│ 评估值: 200 万元                         │
│ 产权证: 已核验                           │
│ 抵押次数: 0 (首押)                       │
│ LTV: 25% (50 万 / 200 万)                │
│ 估值来源: 第三方估值公司 + 同小区对比    │
└──────────────────────────────────────────┘
```

#### 5.3.4 评分档位映射表

| 档位 | 评分区间 | 决策 | 利率档位 | 额度上限 | 本客户 |
|------|----------|------|----------|----------|--------|
| 优 | 800-850 | 批 + 优先 | LPR-10BP | 500 万 | |
| 中优 | 760-799 | 批 | LPR | 300 万 | |
| **良好** | **700-759** | **批** | **LPR+20BP** | **100 万** | **✓ (720)** |
| 边界 | 680-699 | 人工复核 | LPR+50BP | 50 万 | |
| 拒绝 | < 680 | 拒 | - | - | |

### 5.4 决策卡片（右侧面板，两个板块共用）

```
┌──────────────────────────────────────┐
│ 🎯 决策结论                          │
├──────────────────────────────────────┤
│                                      │
│ 结论:  有条件批准                    │
│ 风险等级:  B (良好，70 分)           │
│                                      │
│ ═══════════════════════════════      │
│                                      │
│ 建议额度:  300 万元                  │
│ 期限:      3 年                      │
│ 利率:      6.5% (LPR+85BP)           │
│                                      │
│ ═══════════════════════════════      │
│                                      │
│ 🚨 触发红线 (2 条)                   │
│  1. 关联交易占比 32% (阈值 30%)      │
│     严重度: 中                        │
│     可豁免: 是 (需审计说明)           │
│  2. 应收账款周转 140d (阈值 120d)    │
│     严重度: 低                        │
│     可豁免: 是 (季度监控)             │
│                                      │
│ ═══════════════════════════════      │
│                                      │
│ ✅ 豁免条件 / 附加条件                │
│  • 关联交易审计说明                  │
│  • 季度应收账款账龄表                │
│  • 每半年复查一次                    │
│                                      │
│ ═══════════════════════════════      │
│                                      │
│ 📊 相似案例 (Top 3)                  │
│  启明软件 92% → 批                    │
│  华鼎科技 87% → 批                    │
│  云端数据 85% → 拒                    │
│                                      │
└──────────────────────────────────────┘
```

### 5.5 交互流程（对公场景，7 个步骤的 UI 响应）

#### Step 1: Agent6 → Agent3 跳转（或手动选择企业）

**从 Agent6 跳转**：

```
┌──────────────────────────────────────────────────┐
│ ℹ 检测到从 Agent6 传入的授信调查报告:            │
│                                                  │
│ 📄 福建中锐网络科技有限公司                      │
│    行业: I65-互联网与相关服务                    │
│    报告生成时间: 2026-04-14 11:25               │
│    报告字数: 15,234                              │
│    申请额度: 300 万                              │
│    申请期限: 36 个月                             │
│                                                  │
│ [✓ 加载并决策]   [重新选择企业]                   │
└──────────────────────────────────────────────────┘
```

**手动选择**（从预置企业里挑）：

```
┌──────────────────────────────────────────────────┐
│ 选择企业:                                        │
│ ○ 福建中锐网络（有条件批案例）                   │
│ ○ 瑞恒精密制造（批准案例）                       │
│ ○ 鼎盛商贸（拒绝案例）                           │
│                                                  │
│ [加载并决策]                                     │
└──────────────────────────────────────────────────┘
```

#### Step 2-6: 状态灯实时更新

左侧状态指示逐步点亮：

```
○ 报告加载中...                    →  ✓ 报告已加载
○ 特征抽取中...                    →  ✓ 已抽取 60 项特征
○ 评分计算中...                    →  ✓ 四维评分完成 (70)
○ 红线判定中...                    →  ✓ 命中 2 条红线
○ 案例检索中...                    →  ✓ 匹配 5 条相似案例
○ 决策生成中（LLM调用）...         →  ✓ 决策已生成
```

每个状态变化时，右侧对应区域的组件渐进式淡入（progressive reveal）。

#### Step 7: 决策回写 Agent6

用户点击"回写到 Agent6 报告"按钮，弹出确认框：

```
┌──────────────────────────────────────────────────┐
│ 即将回写以下决策意见到 Agent6 报告:              │
│                                                  │
│ 目标章节: 四、授信结论 — 审批意见                │
│                                                  │
│ 结论: 有条件批准                                 │
│ 额度: 300 万元                                   │
│ 期限: 3 年                                       │
│ 利率: 6.5%                                       │
│ 附加条件: 3 条                                   │
│                                                  │
│ [✓ 确认回写]  [编辑后回写]  [取消]                │
└──────────────────────────────────────────────────┘
```

### 5.6 风险偏好配置抽屉（⚙ 按钮）

点击右上角 ⚙ 按钮，从右侧滑出配置抽屉：

```
┌──────────────────────────────────────────────────┐
│ ⚙ 风险偏好配置                          [x 关闭]  │
├──────────────────────────────────────────────────┤
│ 【板块】 [● 对公]  [○ 对私]                      │
│                                                  │
│ 【维度权重】                                     │
│   财务风险    [────●──] 35%                      │
│   行业风险    [─●────] 15%                       │
│   经营风险    [──●───] 25%                       │
│   担保风险    [──●───] 25%                       │
│                                                  │
│ 【红线规则】 (共 30 条)                          │
│  ┌────────────────────────────────────────────┐  │
│  │ ✓ 关联交易占比 > [30 ]%                    │  │
│  │ ✓ 应收账款周转 > [120] 天                  │  │
│  │ ✓ 资产负债率 > [75 ]%                      │  │
│  │ ✓ 单笔贷款 / 净资产 > [50 ]%               │  │
│  │ ○ 实控人股权质押 > [70 ]%                  │  │
│  │ ... (展开查看全部)                          │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│ 【评分等级门槛】                                 │
│   A 级门槛  [80]  B 级 [65]  C 级 [50]           │
│                                                  │
│ [保存配置]  [重置默认]  [导出 JSON]  [导入]      │
└──────────────────────────────────────────────────┘
```

- 现场修改阈值，点"保存配置" → Dashboard 实时重算；
- 配置保存在 `config/risk_appetite_{client_id}.json`，不同银行客户可保存不同偏好。

---

## 6. 后端架构

### 6.1 模块总览

```
agent_credit/                       (v2.0 改造后)
├── __init__.py
├── agent.py                        (重写) CreditDecisionAgent v2.0
├── app.py                          (重写) 双板块 Tab + Dashboard
├── decision_engine.py              (新建) 决策流水线总调度
├── feature_extractor.py            (新建) ReportJSON → 特征
├── scoring_model_corporate.py      (新建) 对公评分模型
├── scoring_model_retail.py         (新建) 对私评分卡
├── rule_engine_v2.py               (新建) 红线规则引擎
├── case_retriever.py               (新建) 相似案例检索
├── advisor_formatter.py            (新建) 决策意见格式化
├── risk_appetite_config.py         (新建) 风险偏好配置
├── prompts.py                      (重写) 4 组 prompts (对公/对私 × 决策/红线)
├── risk_classifier.py              (保留) 被 scoring_model_corporate 调用
├── rating_engine.py                (保留) 对公等级映射
├── approval_engine.py              (保留) 规则骨架被 rule_engine_v2 复用
└── mock_data/
    ├── corporate_profiles/
    │   ├── zhongrui_network.json   (福建中锐)
    │   ├── ruiheng_precision.json  (瑞恒精密, 复用 v1.0)
    │   └── dingsheng_trade.json    (鼎盛商贸, 复用 v1.0)
    ├── retail_profiles/
    │   ├── zhangsan_restaurant.json
    │   ├── lisi_education.json
    │   └── wangwu_decoration.json
    ├── corporate_cases.json        (50 条对公历史案例)
    ├── retail_cases.json           (10 条对私案例)
    ├── red_line_rules_corporate.json (30 条对公红线)
    ├── red_line_rules_retail.json  (20 条对私红线)
    ├── industry_baselines_v2.json  (行业基准 15 个行业)
    ├── scorecard_weights.json      (对私评分卡权重)
    └── risk_appetite_default.json  (默认风险偏好)
```

### 6.2 模块依赖关系图

```
                    ┌───────────────────┐
                    │ CreditDecisionAgent│  (agent.py)
                    └─────────┬──────────┘
                              │ 调用
                              ▼
                    ┌───────────────────┐
                    │ DecisionEngine    │  (decision_engine.py)
                    │  .run(profile,    │
                    │       segment)    │
                    └─────────┬──────────┘
                              │
          ┌───────────┬───────┼────────┬──────────────┐
          ▼           ▼       ▼        ▼              ▼
  ┌─────────────┐ ┌────────┐ ┌──────┐ ┌────────────┐ ┌──────────────┐
  │ Feature    │ │Scoring │ │Rule  │ │ Case       │ │ Advisor     │
  │ Extractor  │ │Model   │ │Engine│ │ Retriever  │ │ Formatter   │
  └─────┬──────┘ └───┬────┘ └──┬───┘ └─────┬──────┘ └──────┬──────┘
        │            │         │          │               │
        ▼            ▼         ▼          ▼               ▼
  ┌─────────────────────────────────────────────────────────────┐
  │            Mock Data Layer (corporate / retail)              │
  └─────────────────────────────────────────────────────────────┘

  Scoring Model 按 segment 切换:
    segment="corporate" → scoring_model_corporate.py → risk_classifier (保留)
    segment="retail"    → scoring_model_retail.py   (评分卡)
```

### 6.3 DecisionEngine（新建，总调度）

```python
# decision_engine.py
from dataclasses import dataclass
from typing import Literal

Segment = Literal["corporate", "retail"]

@dataclass
class DecisionPipelineResult:
    features: dict                    # 抽取的特征
    scoring_result: ScoringResult
    rule_hits: list[RedLineHit]
    case_matches: list[CaseMatch]
    advice: DecisionAdvice

class DecisionEngine:
    """决策流水线总调度器
    
    流水线:
      1. FeatureExtractor: ReportJSON + 多源 → 特征向量
      2. ScoringModel (按 segment 分派): 特征 → 评分
      3. RuleEngine: 特征 → 红线命中列表
      4. CaseRetriever: 特征 → Top-K 相似案例
      5. AdvisorFormatter: 以上 4 步结果 → 自然语言决策意见
    
    设计原则:
      - 前 4 步无 LLM 调用 (确定性计算)
      - 第 5 步 1-2 次 LLM 调用
      - 支持流式 (yield 中间结果) 供前端状态灯实时刷新
    """
    
    def __init__(self, 
                 llm_client,
                 risk_appetite: RiskAppetiteConfig = None):
        self.llm = llm_client
        self.feature_extractor = FeatureExtractor()
        self.rule_engine = RuleEngineV2(risk_appetite)
        self.case_retriever = CaseRetriever()
        self.advisor = AdvisorFormatter(llm_client)
        # 评分模型按板块懒加载
        self._scoring_models = {}
    
    def _get_scoring_model(self, segment: Segment):
        if segment not in self._scoring_models:
            if segment == "corporate":
                from .scoring_model_corporate import CorporateScoringModel
                self._scoring_models[segment] = CorporateScoringModel()
            else:
                from .scoring_model_retail import RetailScoringModel
                self._scoring_models[segment] = RetailScoringModel()
        return self._scoring_models[segment]
    
    def run_stream(self, 
                   profile: dict,            # 对公=EnterpriseProfile+ReportJSON，对私=PersonalProfile
                   segment: Segment):
        """流式执行，每完成一步 yield (stage, partial_result)"""
        # Phase 1 — Feature
        yield "feature_extracting", None
        features = self.feature_extractor.extract(profile, segment)
        yield "feature_done", features
        
        # Phase 2 — Scoring
        yield "scoring", None
        scoring_model = self._get_scoring_model(segment)
        scoring_result = scoring_model.score(features)
        yield "scoring_done", scoring_result
        
        # Phase 3 — Rule Engine
        yield "rule_checking", None
        rule_hits = self.rule_engine.check(features, segment)
        yield "rule_done", rule_hits
        
        # Phase 4 — Case Retrieval
        yield "case_retrieving", None
        case_matches = self.case_retriever.retrieve(features, segment, top_k=5)
        yield "case_done", case_matches
        
        # Phase 5 — Advisor (LLM 调用)
        yield "advising", None
        advice = self.advisor.format(
            segment=segment,
            profile=profile,
            scoring=scoring_result,
            rules=rule_hits,
            cases=case_matches,
        )
        yield "advising_done", advice
        
        yield "all_done", DecisionPipelineResult(
            features=features,
            scoring_result=scoring_result,
            rule_hits=rule_hits,
            case_matches=case_matches,
            advice=advice,
        )
    
    def run(self, profile, segment):
        """同步模式"""
        result = None
        for stage, data in self.run_stream(profile, segment):
            if stage == "all_done":
                result = data
        return result
```

### 6.4 FeatureExtractor（新建）

```python
# feature_extractor.py
class FeatureExtractor:
    """从 ReportJSON / PersonalProfile + 多源数据抽取特征向量
    
    对公: 抽取约 60 个特征, 分为财务/行业/经营/担保/外部 5 类
    对私: 抽取约 22 个评分卡变量, 分为偿债/意愿/稳定/抵押 4 类
    """
    
    def extract(self, profile: dict, segment: str) -> dict:
        if segment == "corporate":
            return self._extract_corporate(profile)
        else:
            return self._extract_retail(profile)
    
    def _extract_corporate(self, profile: dict) -> dict:
        """从 Agent6 ReportJSON + EnterpriseProfile 抽取对公特征
        
        输入字段来源:
          - profile["agent6_report_json"]: Agent6 产出
          - profile["financial_anchors"]: 财务锚点
          - profile["industry"]: 行业代码
          - profile["guarantee_info"]: 担保安排
          - 补充 multi_source: industry_baselines, credit_history, 
                                related_party_txn, tax_rating
        
        输出 feature dict 示例:
          {
            "financial.debt_ratio": 0.45,
            "financial.revenue_growth": 0.22,
            "financial.net_margin": 0.07,
            "financial.ar_turnover_days": 140,
            ...
            "industry.prosperity_index": 68,
            "industry.cyclicality": "medium",
            ...
            "operational.established_years": 6,
            "operational.employee_count": 87,
            ...
            "guarantee.coverage_ratio": 1.8,
            "guarantee.collateral_type": "房产土地",
            ...
            "external.related_party_pct": 0.32,  # 从报告中提取
            "external.tax_rating": "B",
            ...
          }
        """
        ...
    
    def _extract_retail(self, profile: dict) -> dict:
        """从 PersonalProfile 抽取评分卡变量 (约 22 项)"""
        ...
```

### 6.5 ScoringModel_对公（新建）

```python
# scoring_model_corporate.py
from .risk_classifier import RiskAssessment, classify_risks  # 保留复用

@dataclass
class CorporateScoringResult:
    financial_score: int       # 0-100
    industry_score: int
    operational_score: int
    guarantee_score: int
    composite_score: int       # 加权综合
    risk_grade: str            # A/B/C/D
    sub_scores: dict           # 各子项明细
    industry_peer_percentiles: dict  # 分位数

class CorporateScoringModel:
    """对公四维评分模型
    
    复用 v1.0 的分段线性插值算法和四维权重框架
    (v1.0 第 5.4 节的算法直接照搬, 具体公式见附录A)
    """
    
    DIMENSION_WEIGHTS = {
        "financial": 0.35,
        "industry": 0.15,
        "operational": 0.25,
        "guarantee": 0.25,
    }
    
    GRADE_THRESHOLDS = [
        (80, "A"), (65, "B"), (50, "C"), (0, "D"),
    ]
    
    def score(self, features: dict) -> CorporateScoringResult:
        # 用 v1.0 的 FinancialRiskScorer / IndustryRiskScorer / 
        # OperationalRiskScorer / GuaranteeRiskScorer 实现
        ...
```

### 6.6 ScoringModel_对私（新建）

```python
# scoring_model_retail.py

@dataclass
class RetailScoringResult:
    fico_score: int            # 300-850
    grade: str                 # 优/中优/良好/边界/拒绝
    sub_scores: dict           # 各大类 + 子项得分
    approved_limit: float      # 建议额度 (万元)
    rate_tier: str             # 利率档位

class RetailScoringModel:
    """对私评分卡模型 (FICO-式)
    
    4 大类 × 若干子项:
      1. 偿债能力 (30%): 月收入稳定性 / 债务收入比 / 流水均值 / 历史还款能力 / 月均还款额 / 现金盈余
      2. 还款意愿 (25%): 征信查询次数 / 历史逾期 / 信用卡利用率 / 征信历史长度 / 社保公积金
      3. 稳定性   (25%): 职业年限 / 居住年限 / 婚姻状况 / 学历 / 家庭结构 / 年龄
      4. 抵押估值 (20%): 抵押物类型 / LTV / 产权清晰度 / 抵押次数 / 估值来源
    
    每个子项有独立的评分函数 (见 scorecard_weights.json)
    各子项得分 → 加权到大类得分 (300-850)
    大类得分 → 加权到总分 (300-850)
    """
    
    WEIGHTS = {
        "repayment_capacity": 0.30,
        "repayment_willingness": 0.25,
        "stability": 0.25,
        "collateral": 0.20,
    }
    
    GRADE_MAP = [
        (800, "优", "LPR-10BP", 500),
        (760, "中优", "LPR", 300),
        (700, "良好", "LPR+20BP", 100),
        (680, "边界", "LPR+50BP", 50),
        (0, "拒绝", None, 0),
    ]
    
    def score(self, features: dict) -> RetailScoringResult:
        ...
```

### 6.7 RuleEngineV2（新建）

```python
# rule_engine_v2.py

@dataclass
class RedLineHit:
    rule_id: str
    rule_name: str
    threshold: float
    actual_value: float
    severity: str               # "high" / "medium" / "low"
    is_hard: bool               # 硬性红线 (命中必拒) vs 软性红线 (命中警告)
    can_waive: bool             # 是否可豁免
    waiver_conditions: list[str]
    description: str

class RuleEngineV2:
    """红线规则引擎 (可配置 JSON)
    
    规则来源: mock_data/red_line_rules_{segment}.json
    支持风险偏好覆盖 (RiskAppetiteConfig 里的 threshold 优先于默认值)
    """
    
    def __init__(self, appetite: RiskAppetiteConfig = None):
        self.appetite = appetite or RiskAppetiteConfig.default()
        self._rules_cache = {}
    
    def check(self, features: dict, segment: str) -> list[RedLineHit]:
        rules = self._load_rules(segment)
        hits = []
        for rule in rules:
            # 用 appetite 里的阈值覆盖默认阈值
            threshold = self.appetite.get_threshold(rule["id"], rule["default_threshold"])
            actual = self._eval_expression(rule["feature_expr"], features)
            if self._check_condition(actual, rule["operator"], threshold):
                hits.append(RedLineHit(
                    rule_id=rule["id"],
                    rule_name=rule["name"],
                    threshold=threshold,
                    actual_value=actual,
                    severity=rule["severity"],
                    is_hard=rule["is_hard"],
                    can_waive=rule["can_waive"],
                    waiver_conditions=rule.get("waiver_conditions", []),
                    description=rule["description"],
                ))
        return hits
```

### 6.8 CaseRetriever（新建）

```python
# case_retriever.py

@dataclass
class CaseMatch:
    case_id: str
    company_name: str
    similarity: float            # 0-1
    features_summary: dict
    decision: str                # "批" / "有条件批" / "拒"
    approved_amount: float
    approved_term: int
    rate: float
    decision_reason: str
    hit_red_lines: list[str]

class CaseRetriever:
    """历史案例检索器
    
    Mock 50 条对公案例 + 10 条对私案例
    相似度算法:
      - 对公: 行业匹配 (权重 0.3) + 营收规模匹配 (0.2) + 
              四维评分接近度 (0.3) + 申请额度接近度 (0.2)
      - 对私: 评分档位匹配 (0.4) + 抵押物类型 (0.2) + 
              申请额度接近度 (0.2) + 职业相似 (0.2)
    """
    
    def retrieve(self, features: dict, segment: str, top_k: int = 5) -> list[CaseMatch]:
        cases = self._load_cases(segment)
        scored = [(c, self._similarity(features, c, segment)) for c in cases]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [self._to_match(c, sim) for c, sim in scored[:top_k]]
```

### 6.9 AdvisorFormatter（新建）

```python
# advisor_formatter.py

@dataclass
class DecisionAdvice:
    decision: str               # "批准" / "有条件批准" / "拒绝"
    approved_amount: float      # 建议额度 (万元)
    approved_term: int          # 期限 (月)
    interest_rate: float        # 利率 (小数)
    rate_benchmark: str         # "LPR+85BP"
    risk_grade: str             # A/B/C/D (对公) 或 优/中优/良好/边界/拒绝 (对私)
    composite_score: int        # 综合评分
    conditions: list[str]       # 附加条件
    red_line_explanations: list[dict]  # 每条红线的解释
    decision_reason: str        # 决策理由 (LLM 生成的自然语言)
    similar_cases_summary: str  # 相似案例结论摘要

class AdvisorFormatter:
    """决策意见格式化器
    
    对公: 2 次 LLM 调用 (决策说明 + 红线解释)
    对私: 0-1 次 LLM 调用 (仅边界案例或红线命中时用)
    """
    
    def __init__(self, llm_client):
        self.llm = llm_client
    
    def format(self, segment, profile, scoring, rules, cases) -> DecisionAdvice:
        # 1. 确定性规则: 决定 decision / amount / term / rate
        base = self._deterministic_decision(segment, profile, scoring, rules)
        
        # 2. LLM 调用: 生成决策理由和红线解释
        if segment == "corporate":
            base.decision_reason = self._llm_decision_reason(
                profile, scoring, rules, cases)
            base.red_line_explanations = self._llm_redline_explain(rules, profile)
        else:
            # 对私: 仅边界或红线时用 LLM
            if scoring.grade == "边界" or rules:
                base.decision_reason = self._llm_decision_reason_retail(
                    profile, scoring, rules, cases)
            else:
                base.decision_reason = self._template_decision_reason(scoring)
        
        return base
```

### 6.10 RiskAppetiteConfig（新建）

```python
# risk_appetite_config.py

@dataclass
class RiskAppetiteConfig:
    """风险偏好配置 (可被客户自定义)
    
    存储:
      - 维度权重 (对公四维权重)
      - 评分等级门槛 (A/B/C/D 分界点)
      - 红线规则阈值覆盖 (rule_id → custom_threshold)
      - 利率档位映射
    
    持久化: config/risk_appetite_{client_id}.json
    """
    
    segment: str                         # "corporate" / "retail"
    dimension_weights: dict              # 维度权重
    grade_thresholds: list[tuple]        # 等级门槛
    rule_threshold_overrides: dict       # rule_id → threshold
    rate_tier_map: dict                  # 等级 → 利率档位
    
    @classmethod
    def default(cls):
        ...
    
    @classmethod
    def load(cls, client_id: str, segment: str):
        ...
    
    def save(self, client_id: str):
        ...
```

### 6.11 与 Agent6 的主 Agent 交互点

Agent6 的 `agent.py` (根目录) 有一个 `CreditReportAgent`，其 `process_form_fill` / `process_message` 方法最终产出 `output_path`（Word 文件）。v2.0 阶段需要在 Agent6 额外产出一份结构化 ReportJSON：

```python
# agent.py (Agent6 改造)
# 在填写/生成报告结束时, 额外导出一份 ReportJSON
report_json_path = output_path.replace(".docx", "_report.json")
report_json = {
    "enterprise_profile": self.enterprise_profile.dict(),  # EnterpriseProfile
    "financial_anchors": self.financial_anchors,
    "chapters": self.chapters,                # 各章节文本
    "guarantee_info": self.guarantee_info,
    "related_party_info": ...,                # 从材料里提取的关联交易信息
    "source_files": self.uploaded_files,
    "generated_at": datetime.now().isoformat(),
    "version": "v7.5",
}
with open(report_json_path, "w", encoding="utf-8") as f:
    json.dump(report_json, f, ensure_ascii=False, indent=2)
```

Agent3 通过约定路径（或 Gradio state 传参）读取 ReportJSON。

---

## 7. 数据模型

### 7.1 输入模型

#### 7.1.1 EnterpriseProfile（对公，复用 shared/enterprise_profile.py）

已在 `shared/enterprise_profile.py` 定义，v2.0 无需改模型，但需在 `agent_outputs` 字段里塞入 Agent6 ReportJSON：

```python
class EnterpriseProfile(BaseModel):
    # ... 原有字段
    agent_outputs: dict = Field(default_factory=dict)
    # agent_outputs["agent6_report_json"] = {..}  <-- Agent3 消费此字段
```

#### 7.1.2 PersonalProfile（对私，新建 Pydantic 模型）

```python
# shared/personal_profile.py (新建)
class PersonalProfile(BaseModel):
    """个人画像, 对私板块标准载体"""
    
    # 身份信息
    name: str = ""
    id_card: str = ""               # 脱敏 (仅后 4 位)
    age: int = 0
    gender: str = ""
    marital_status: str = ""
    education: str = ""
    
    # 职业与收入
    occupation: str = ""            # 职业类型 (个体户/受薪/自由职业)
    business_type: str = ""         # 如果是个体户, 具体行业
    years_in_current_job: int = 0
    monthly_income: float = 0        # 月收入 (元)
    monthly_income_stability: str = ""  # "stable" / "fluctuating" / "seasonal"
    
    # 征信信息
    credit_report: dict = Field(default_factory=dict)
    # {
    #   "current_loans_count": 2,
    #   "current_credit_cards": 3,
    #   "credit_card_utilization": 0.45,
    #   "query_count_24m": 4,
    #   "overdue_history": [],
    #   "guarantee_count": 1,
    #   "account_age_years": 7.5
    # }
    
    # 银行流水
    bank_statement: dict = Field(default_factory=dict)
    # {
    #   "avg_balance_6m": 50000,
    #   "monthly_inflow_avg": 65000,
    #   "monthly_outflow_avg": 58000,
    #   "large_amount_events": []
    # }
    
    # 社保公积金
    social_security: dict = Field(default_factory=dict)
    # {
    #   "months_paid": 48,
    #   "monthly_contribution": 1200
    # }
    
    # 抵押物
    collateral: dict = Field(default_factory=dict)
    # {
    #   "type": "住宅",
    #   "area_sqm": 120,
    #   "location": "中心区",
    #   "appraised_value": 2000000,
    #   "ltv": 0.25,
    #   "mortgage_count": 0,
    #   "title_verified": true,
    #   "valuation_source": "第三方估值"
    # }
    
    # 居住稳定性
    residence: dict = Field(default_factory=dict)
    # {
    #   "years_at_address": 5,
    #   "housing_type": "self_owned"
    # }
    
    # 申请信息
    request: dict = Field(default_factory=dict)
    # {
    #   "amount": 500000,
    #   "term_months": 36,
    #   "purpose": "扩大经营"
    # }
    
    # 元信息
    profile_id: str = ""
    created_at: str = ""
```

### 7.2 中间模型

```python
# 特征
RiskFeatures = dict[str, Any]    # 扁平化 key 如 "financial.debt_ratio"

# 评分 (板块差异化)
ScoringResult = Union[CorporateScoringResult, RetailScoringResult]

# 红线命中
class RedLineHit: ...             # 见 6.7

# 案例匹配
class CaseMatch: ...              # 见 6.8
```

### 7.3 输出模型: DecisionAdvice（两板块共用）

```python
@dataclass
class DecisionAdvice:
    """决策意见 (对公/对私共用)"""
    
    # 基础元数据
    advice_id: str                    # UUID
    segment: str                      # "corporate" / "retail"
    subject_name: str                 # 企业名或个人名
    decision_time: str                # ISO 8601
    
    # 核心决策字段
    decision: str                     # "批准" / "有条件批准" / "拒绝"
    approved_amount: float            # 建议额度 (万元)
    approved_term: int                # 期限 (月)
    interest_rate: float              # 利率 (小数，如 0.065 表示 6.5%)
    rate_benchmark: str               # "LPR+85BP" 等可读说明
    
    # 评分 (按板块类型略有不同)
    composite_score: int              # 对公: 0-100; 对私: 300-850
    risk_grade: str                   # 对公 A/B/C/D, 对私 优/中优/良好/边界/拒绝
    
    # 附加条件和红线
    conditions: list[str]             # 附加授信条件
    red_line_hits: list[RedLineHit]   # 触发的红线清单
    red_line_explanations: list[dict] # {rule_id, explanation, is_blocker}
    
    # 解释与证据
    decision_reason: str              # LLM 生成的决策理由
    similar_cases_summary: str        # 相似案例摘要
    
    # 可追溯
    features_snapshot: dict           # 入参特征快照
    scoring_snapshot: dict            # 评分快照
    
    # 回写 Agent6 所需
    approval_section_text: str        # 可直接插入 Agent6 报告"审批意见"章节的文本
    
    def to_json(self) -> str: ...
    def to_agent6_writeback(self) -> dict: 
        """输出回写 Agent6 的结构化数据"""
        return {
            "target_section": "四、授信结论 - 审批意见",
            "text": self.approval_section_text,
            "structured_fields": {
                "decision": self.decision,
                "amount": self.approved_amount,
                "term_months": self.approved_term,
                "interest_rate": self.interest_rate,
                "conditions": self.conditions,
            }
        }
```

---

## 8. LLM 调用设计

### 8.1 调用点清单

| 板块 | 调用点 | 次数 | 用途 |
|------|--------|------|------|
| 对公 | Prompt 1: 决策说明生成 | 1 | 基于评分/红线/案例，生成决策理由（5 段文字） |
| 对公 | Prompt 2: 红线解释 | 1 | 针对每条触发的红线，解释含义、严重程度、豁免条件 |
| 对私 | Prompt 3: 对私决策说明（仅边界/红线时） | 0-1 | 对评分卡边界案例或触发红线时给出决策说明 |
| 对私 | （无常规 LLM 调用） | 0 | 正常案例走模板化说明 |

### 8.2 Prompt 1: 对公决策说明（对应 prompts.py::CORPORATE_DECISION_SYSTEM）

```python
CORPORATE_DECISION_SYSTEM = """你是一名资深银行对公授信审批专家。你的任务是基于量化决策结果，
撰写结构化、简洁、专业的授信决策意见（供审贷会参考）。

【铁律】
1. 所有数字必须来自下方输入，不得编造
2. 决策字段（批/不批/有条件批/额度/期限/利率）必须与输入一致，你的任务是"解释为什么是这个决策"
3. 决策理由要联系红线命中情况和相似历史案例
4. 语言风格对标银行内部审贷会材料（简洁、专业、不使用口语）
5. 禁止使用"可能""或许""大概"等含糊措辞
"""

CORPORATE_DECISION_USER = """
## 企业基本情况
{company_summary}

## 申请事项
- 申请额度: {requested_amount} 万元
- 申请期限: {requested_term} 个月
- 用途: {purpose}

## 评分结果
- 财务风险: {financial_score}/100
- 行业风险: {industry_score}/100
- 经营风险: {operational_score}/100
- 担保风险: {guarantee_score}/100
- 综合: {composite_score}/100 (等级 {risk_grade})

## 触发的红线 ({red_line_count} 条)
{red_line_detail}

## 额度测算
- 营收法: {revenue_method} 万
- 净资产法: {netasset_method} 万
- 现金流法: {cashflow_method} 万
- 担保法: {collateral_method} 万
- 综合建议: {suggested_amount_range} 万

## 相似历史案例 (Top 3)
{similar_cases_summary}

## 确定性决策
- 决策: {decision}
- 批复额度: {approved_amount} 万
- 期限: {approved_term} 个月
- 利率: {interest_rate} ({rate_benchmark})
- 附加条件: {conditions}

---
请按以下结构输出决策意见 (控制在 500 字以内):

### 一、客户基本情况
(2-3 句话概述企业和申请事项)

### 二、评分结论
(综合评分、等级、关键风险点 3-5 句话)

### 三、决策说明
(为什么给出这个决策，要联系红线命中和案例对比)

### 四、额度与利率依据
(额度和利率的测算逻辑)

### 五、附加条件
(附加的授信条件，列表式)
"""
```

参数：`temperature=0.2`，`max_tokens=1200`。

### 8.3 Prompt 2: 对公红线解释（对应 prompts.py::CORPORATE_REDLINE_SYSTEM）

```python
CORPORATE_REDLINE_SYSTEM = """你是一名银行风险合规专家。
请针对每条触发的红线，简明解释:
  1. 这条红线的含义 (1 句话)
  2. 本案例触发的具体原因和数据
  3. 严重程度判断 (高/中/低)
  4. 是否可豁免、豁免条件是什么

【铁律】
- 一次只解释一条红线，用 150 字以内
- 必须引用具体数字
- 不使用含糊措辞
"""

CORPORATE_REDLINE_USER = """
## 企业画像
{company_summary}

## 触发的红线
{hit_rules_detail}

请按以下 JSON 结构输出, 每条红线一个对象:
[
  {{"rule_id": "...", "explanation": "...", "severity": "...", "waiver_advice": "..."}},
  ...
]
"""
```

### 8.4 Prompt 3: 对私决策说明（边界/红线场景，对应 prompts.py::RETAIL_DECISION_SYSTEM）

```python
RETAIL_DECISION_SYSTEM = """你是一名银行零售信贷审批员。
请基于评分卡结果和红线判定，给出简明的决策说明 (面向个贷审批岗，200 字以内)。

【铁律】
1. 不得编造数字
2. 语言面向个贷岗，不使用对公审批术语
3. 如果是边界案例 (评分 680-699), 明确说"建议人工复核"
4. 如果触发红线, 明确指出是哪条
"""

RETAIL_DECISION_USER = """
## 客户画像摘要
{customer_summary}

## 评分卡结果
- 综合评分: {fico_score} ({grade} 档)
- 偿债能力: {repayment_capacity}
- 还款意愿: {repayment_willingness}
- 稳定性: {stability}
- 抵押估值: {collateral}

## 红线命中 ({count} 条)
{red_line_detail}

## 确定性决策
- 决策: {decision}
- 额度: {approved_amount} 万
- 利率: {interest_rate}

---
请在 200 字以内给出决策说明，结构: 一句话结论 + 主要理由 (2-3 点) + 附加说明 (若有红线或边界)
"""
```

参数：`temperature=0.3`，`max_tokens=400`。

### 8.5 降级策略

| 异常场景 | 降级方式 |
|----------|----------|
| LLM 超时 (>30s) | 使用模板化说明："综合评分 {score}，{grade} 级，{decision}。额度 {amount} 万，期限 {term} 个月。详细分析因系统繁忙暂不可用。" |
| LLM 返回空或异常 | 重试 1 次，仍失败走模板 |
| LLM 编造数字 | 前端展示时交叉校验（与确定性输出比对），不一致则标红提示 + 走模板 |
| LLM 输出结构不完整 | 接受部分输出，缺失段落标注"[此部分生成异常，请人工补充]" |

### 8.6 LLM 成本估算（单次完整决策）

| 调用 | Input tokens | Output tokens | DeepSeek 成本 |
|------|--------------|---------------|---------------|
| 对公决策说明 | ~1,800 | ~900 | ~0.004 元 |
| 对公红线解释 | ~1,200 | ~600 | ~0.002 元 |
| **对公合计** | **~3,000** | **~1,500** | **~0.006 元** |
| 对私决策说明（边界） | ~800 | ~300 | ~0.001 元 |
| **对私合计（常规案例）** | **0** | **0** | **0 元（走模板）** |

---

## 9. Mock 数据规格

### 9.1 对公预置 Profile（3-5 个）

#### 9.1.1 福建中锐网络（新建，主演示场景）

```json
{
  "profile_id": "corp_zhongrui_001",
  "company_name": "福建中锐网络科技有限公司",
  "unified_credit_code": "91350000MA8EXAMPLE",
  "industry": "I65-互联网与相关服务",
  "establishment_date": "2020-05-18",
  "registered_capital": "5000",
  "employee_count": 87,
  "region": "福建省福州市",
  "main_business": "企业级 SaaS + 定制软件开发",
  "financial_anchors": {
    "revenue_latest": 28000,
    "revenue_prev": 22950,
    "net_profit_latest": 1960,
    "net_profit_prev": 1380,
    "total_assets": 18500,
    "total_liabilities": 8325,
    "net_assets": 10175,
    "accounts_receivable": 10740,
    "inventory": 0,
    "operating_cash_flow": 1500,
    "short_term_borrowing": 3500,
    "ebitda": 2400,
    "period": "2025年度"
  },
  "guarantee_info": {
    "type": "抵押+保证",
    "collateral": "商业办公楼一层 (评估值 540 万)",
    "collateral_value": 540,
    "collateral_type": "房产土地",
    "guarantor": "法人连带责任保证 + 母公司担保"
  },
  "related_party_info": {
    "related_party_revenue_pct": 0.32,
    "related_party_txn_desc": "与母公司中锐集团存在 SaaS 服务供应关系，年度交易额 8960 万"
  },
  "existing_credit": {
    "total_approved": 500,
    "total_used": 450,
    "overdue_history": "无"
  },
  "request": {
    "amount": 300,
    "purpose": "补充流动资金（扩展研发团队）",
    "term_months": 36
  },
  "agent_outputs": {
    "agent6_report_json": "(此处占位，实际运行时由 Agent6 填充)"
  }
}
```

#### 9.1.2 瑞恒精密制造（复用 v1.0 场景 1）

直接复用 v1.0 PRD 第 3 章场景 1 的 JSON，无变更。用作"批准案例"。

#### 9.1.3 鼎盛商贸（复用 v1.0 场景 2）

直接复用 v1.0 PRD 场景 2 的 JSON。用作"拒绝案例"。

### 9.2 对私预置 Profile（3-5 个）

#### 9.2.1 张三·餐饮个体户（主演示场景）

```json
{
  "profile_id": "retail_zhangsan_001",
  "name": "张三",
  "id_card_tail": "3214",
  "age": 42,
  "gender": "男",
  "marital_status": "已婚",
  "education": "大专",
  "occupation": "个体工商户",
  "business_type": "餐饮业",
  "years_in_current_job": 4,
  "monthly_income": 65000,
  "monthly_income_stability": "stable",
  "credit_report": {
    "current_loans_count": 2,
    "current_credit_cards": 3,
    "credit_card_utilization": 0.45,
    "query_count_24m": 4,
    "overdue_history": [],
    "guarantee_count": 1,
    "account_age_years": 7.5
  },
  "bank_statement": {
    "avg_balance_6m": 52000,
    "monthly_inflow_avg": 65000,
    "monthly_outflow_avg": 58000,
    "large_amount_events": []
  },
  "social_security": {
    "months_paid": 48,
    "monthly_contribution": 1200
  },
  "collateral": {
    "type": "住宅",
    "area_sqm": 120,
    "location": "中心区",
    "appraised_value": 2000000,
    "ltv": 0.25,
    "mortgage_count": 0,
    "title_verified": true,
    "valuation_source": "第三方估值"
  },
  "residence": {
    "years_at_address": 5,
    "housing_type": "self_owned"
  },
  "request": {
    "amount": 500000,
    "term_months": 36,
    "purpose": "扩大经营（装修 + 采购设备）"
  }
}
```

#### 9.2.2 李四·教培从业者（边界案例，评分 695）

关键特征：教培行业政策风险、月收入波动、无抵押物仅信用贷款→ 触发评分卡边界，需要人工复核。

#### 9.2.3 王五·装修包工头（拒绝案例，评分 650）

关键特征：多次征信查询、流水大进大出、职业不稳定→评分卡不通过。

### 9.3 对公案例库（Mock 50 条）

`corporate_cases.json`：50 条历史已决案例，字段：

```json
{
  "case_id": "case_corp_001",
  "company_name": "启明软件科技有限公司",
  "industry": "I65",
  "revenue": 31000,
  "debt_ratio": 0.42,
  "net_margin": 0.068,
  "ar_turnover_days": 82,
  "financial_score": 78,
  "industry_score": 68,
  "operational_score": 80,
  "guarantee_score": 85,
  "composite_score": 78,
  "risk_grade": "B",
  "requested_amount": 400,
  "approved_amount": 400,
  "approved_term_months": 36,
  "interest_rate": 0.063,
  "decision": "批准",
  "hit_red_lines": [],
  "decision_reason": "各维度评分均衡，担保充分"
}
```

50 条按行业分布：I65 互联网 10 条、C34 设备制造 10 条、F51 批发 10 条、C39 计算机 5 条、C26 化工 5 条、其他 10 条。

### 9.4 对私案例库（10 条）

`retail_cases.json`：10 条历史已决个人贷案例，字段类似但简化。

### 9.5 红线规则库

#### 9.5.1 对公红线（30 条）

```json
{
  "segment": "corporate",
  "rules": [
    {
      "id": "corp_rl_001",
      "name": "关联交易占比过高",
      "category": "financial",
      "feature_expr": "external.related_party_pct",
      "operator": ">",
      "default_threshold": 0.30,
      "severity": "medium",
      "is_hard": false,
      "can_waive": true,
      "waiver_conditions": ["提供关联交易审计说明", "设置单一客户额度上限"],
      "description": "关联交易占总营收比例超过 30%，存在利益输送风险"
    },
    {
      "id": "corp_rl_002",
      "name": "应收账款周转过长",
      "category": "financial",
      "feature_expr": "financial.ar_turnover_days",
      "operator": ">",
      "default_threshold": 120,
      "severity": "low",
      "is_hard": false,
      "can_waive": true,
      "waiver_conditions": ["季度提交应收账款账龄表", "约定单笔应收账款超过 180 天触发预警"],
      "description": "应收账款周转天数超过 120 天，资金占用严重"
    },
    {
      "id": "corp_rl_003",
      "name": "资产负债率过高",
      "category": "financial",
      "feature_expr": "financial.debt_ratio",
      "operator": ">",
      "default_threshold": 0.75,
      "severity": "high",
      "is_hard": true,
      "can_waive": false,
      "description": "资产负债率超过 75%，偿债能力严重不足"
    },
    ...（另 27 条，涵盖行业限制、实控人股权质押、税务异常、
         工商异常、司法诉讼、环保处罚等）
  ]
}
```

30 条分类：财务类（10）、行业/政策类（5）、经营异常类（8）、担保类（4）、外部合规类（3）。

#### 9.5.2 对私红线（20 条）

包括：征信历史逾期超过 90 天、近 12 月查询超过 10 次、信用卡利用率超过 90%、抵押物已有 2 次以上抵押、月收入不稳定且无抵押、申请用途不符合普惠金融、社保公积金断缴超过 6 个月等 20 条。

### 9.6 评分卡权重（对私）

`scorecard_weights.json`：

```json
{
  "segment": "retail",
  "category_weights": {
    "repayment_capacity": 0.30,
    "repayment_willingness": 0.25,
    "stability": 0.25,
    "collateral": 0.20
  },
  "sub_variable_weights": {
    "repayment_capacity": {
      "monthly_income_stability": 0.25,
      "dti_ratio": 0.25,
      "avg_balance_6m": 0.15,
      "historical_repayment": 0.15,
      "monthly_repay_amount": 0.10,
      "cash_surplus": 0.10
    },
    "repayment_willingness": {
      "query_count_24m": 0.20,
      "overdue_history": 0.35,
      "cc_utilization": 0.15,
      "credit_history_length": 0.15,
      "social_security_months": 0.15
    },
    "stability": {
      "years_in_job": 0.25,
      "years_at_address": 0.20,
      "marital_status": 0.15,
      "education": 0.15,
      "family_structure": 0.10,
      "age": 0.15
    },
    "collateral": {
      "collateral_type": 0.30,
      "ltv": 0.30,
      "title_verified": 0.15,
      "mortgage_count": 0.15,
      "valuation_source": 0.10
    }
  },
  "score_maps": {
    "dti_ratio": [
      [0.0, 850], [0.30, 800], [0.45, 750], [0.60, 680], [0.75, 600], [1.0, 400]
    ],
    "overdue_history": [
      ["无", 850], ["M1_once", 720], ["M2_once", 620], ["M3_once", 500], ["M6+", 300]
    ]
    ...（共 22 个变量的评分表）
  },
  "grade_thresholds": [
    [800, "优", "LPR-10BP", 500],
    [760, "中优", "LPR", 300],
    [700, "良好", "LPR+20BP", 100],
    [680, "边界（人工复核）", "LPR+50BP", 50],
    [0, "拒绝", null, 0]
  ]
}
```

---

## 10. 与 Agent6 的数据接口

### 10.1 Agent6 → Agent3：ReportJSON 结构

Agent6 在生成 Word 报告的同时导出一份 JSON，Agent3 直接消费此 JSON。

**文件路径约定**：
```
outputs/{company_name}_{timestamp}_filled.docx       # Word 报告
outputs/{company_name}_{timestamp}_report.json       # ReportJSON（Agent3 消费）
```

**ReportJSON 结构**（v7.5+）：

```json
{
  "meta": {
    "agent": "agent6_credit_report",
    "version": "v7.5",
    "generated_at": "2026-04-14T11:25:00",
    "company_name": "福建中锐网络科技有限公司",
    "source_files": ["财报.xlsx", "工商资料.pdf", ...]
  },
  "enterprise_profile": {
    "company_name": "福建中锐网络科技有限公司",
    "unified_credit_code": "91350000MA8EXAMPLE",
    "industry": "I65-互联网与相关服务",
    "establishment_date": "2020-05-18",
    "registered_capital": "5000",
    "employee_count": 87,
    "region": "福建省福州市",
    "controller_name": "张总",
    "controller_share_pct": "65%",
    "main_business": "..."
  },
  "financial_anchors": {
    "revenue_latest": 28000,
    "revenue_prev": 22950,
    "net_profit_latest": 1960,
    "total_assets": 18500,
    "total_liabilities": 8325,
    "accounts_receivable": 10740,
    "operating_cash_flow": 1500,
    "period": "2025年度"
  },
  "guarantee_info": {
    "type": "抵押+保证",
    "collateral_value": 540,
    "collateral_type": "房产土地",
    "guarantor": "法人连带责任保证 + 母公司担保"
  },
  "related_party_info": {
    "related_party_revenue_pct": 0.32,
    "related_party_desc": "与母公司中锐集团..."
  },
  "request": {
    "amount": 300,
    "purpose": "补充流动资金",
    "term_months": 36
  },
  "chapters": {
    "chapter_1_background": "企业背景章节全文...",
    "chapter_2_operation": "经营情况章节全文...",
    "chapter_3_finance": "财务分析章节全文...",
    "chapter_4_conclusion": "(待 Agent3 回填审批意见)"
  },
  "anchors_index": [
    {"anchor_id": "a001", "chapter": 3, "text": "营业收入 28,000 万元", "source_file": "财报.xlsx"},
    ...
  ]
}
```

**Agent3 消费时的字段映射**：

| ReportJSON 字段 | Agent3 使用方式 |
|------------------|------------------|
| `enterprise_profile.*` | 填充左侧面板企业画像摘要 |
| `financial_anchors.*` | 送入 FeatureExtractor 抽取财务特征 |
| `guarantee_info.*` | 送入 FeatureExtractor 抽取担保特征 |
| `related_party_info.*` | 送入 FeatureExtractor 抽取外部特征 |
| `request.*` | 作为申请事项显示在顶部横幅 |
| `chapters.chapter_3_finance` | （可选）作为 LLM 生成决策说明的补充上下文 |

### 10.2 Agent3 → Agent6：决策回写

Agent3 完成决策后，用户点击"回写到 Agent6 报告"按钮，Agent3 调用 Agent6 的回写接口。

**回写数据结构**（`DecisionAdvice.to_agent6_writeback()`）：

```json
{
  "target_section": "四、授信结论 - 审批意见",
  "anchor_pattern": "【审批意见】",
  "structured_fields": {
    "decision": "有条件批准",
    "approved_amount": 300,
    "approved_term_months": 36,
    "interest_rate": 0.065,
    "rate_benchmark": "LPR+85BP",
    "risk_grade": "B",
    "composite_score": 70,
    "conditions": [
      "关联交易提供审计说明",
      "每季度提交应收账款账龄表",
      "每半年复查一次"
    ],
    "red_line_hits": [
      {"rule_id": "corp_rl_001", "severity": "medium"},
      {"rule_id": "corp_rl_002", "severity": "low"}
    ]
  },
  "text": "## 四、授信结论\n\n### 审批意见\n\n综合考量企业财务、行业、经营和担保四维评分..."
}
```

**Agent6 端接收接口**（`agent.py` 里新增方法）：

```python
# agent.py (Agent6)
class CreditReportAgent:
    def apply_decision_writeback(self, writeback: dict) -> str:
        """接收 Agent3 的决策回写, 更新报告的审批意见章节
        
        返回更新后的 Word 文件路径
        """
        # 1. 从 writeback["text"] 构造 docx 段落
        # 2. 定位 Word 文档的"四、授信结论"章节
        # 3. 替换/插入审批意见段落
        # 4. 保存为新的 docx 文件 ({original_name}_decided.docx)
        # 5. 同步更新 ReportJSON 的 chapters.chapter_4_conclusion
```

### 10.3 串联触发方式

**Agent6 UI 改造**：

- 在 Agent6 报告生成完成后，在 UI 右下角显示一颗按钮：
  ```
  [📤 送 Agent3 做决策]
  ```
- 点击该按钮触发 `handle_send_to_agent3()`：
  ```python
  def handle_send_to_agent3():
      report_json_path = ...       # 刚生成的 ReportJSON 路径
      # 方式 1: 同进程 Gradio, 通过 gr.State 共享数据
      return gr.update(selected=2), {"report_json_path": report_json_path}
      # Tab 索引 2 = Agent3, selected=2 切换到该 Tab
  ```
- Agent3 Tab 监听 state 变化，若检测到 `report_json_path`，自动加载 + 触发决策。

**Agent3 UI 改造**：

- Agent3 对公 Tab 顶部加一个 "从 Agent6 接收" 横幅：
  ```
  ℹ 检测到从 Agent6 传入的授信调查报告：福建中锐网络（11:25 生成）
  [✓ 加载并决策]   [取消]
  ```

### 10.4 接口版本管理

- ReportJSON 版本号：`meta.version`（当前 v7.5）
- 决策回写版本号：`writeback.version`（当前 v2.0）
- Agent3 在消费 ReportJSON 时校验 `meta.version`，不兼容版本给出清晰的错误提示
- 向后兼容策略：新增字段不影响旧版，删除字段需经过一个 deprecation 周期

---

## 11. 验收标准

### 11.1 功能验收

| 编号 | 验收项 | 通过条件 |
|------|--------|----------|
| F-01 | 对公板块·报告加载 | 从 Agent6 一键传入后，左侧企业摘要正确显示 |
| F-02 | 对公板块·特征抽取 | ReportJSON → 60+ 特征，关键字段无缺失 |
| F-03 | 对公板块·四维评分 | 中锐网络场景四维评分均在合理区间，综合分 65-75 |
| F-04 | 对公板块·红线判定 | 中锐网络触发 ≥ 2 条红线（关联交易 + 应收账款） |
| F-05 | 对公板块·额度计算 | 营收/净资产/现金流/担保四种测算结果齐全，综合区间合理 |
| F-06 | 对公板块·案例检索 | 返回 3-5 条同行业相似案例，相似度 > 80% |
| F-07 | 对公板块·决策生成 | 输出 DecisionAdvice，字段完整 |
| F-08 | 对公板块·高风险识别 | 鼎盛商贸案例综合分 < 50，决策"拒绝" |
| F-09 | 对公板块·Dashboard 渲染 | 雷达图/条形图/案例表格/决策卡片完整显示 |
| F-10 | 对公板块·2 分钟内完成 | 从点击"加载并决策"到决策卡片就绪 < 120 秒 |
| F-11 | 对私板块·Profile 加载 | 张三案例左侧展示画像 + 征信摘要 |
| F-12 | 对私板块·评分卡计算 | 张三评分 720 ± 5，落在"良好"档 |
| F-13 | 对私板块·决策输出 | 输出评分、档位、额度、利率、红线 |
| F-14 | 对私板块·10 秒内完成 | 从选择 Profile 到决策卡片就绪 < 10 秒 |
| F-15 | 板块切换 | 切换 Tab 后 Dashboard 完全刷新，互不影响 |
| F-16 | 风险偏好配置 | 现场修改红线阈值（30%→20%），重算后决策变化 |
| F-17 | 风险偏好持久化 | 保存的配置重启后仍生效 |
| F-18 | Agent6 → Agent3 串联 | 从 Agent6 一键跳转 < 3 秒，Dashboard 正确加载 |
| F-19 | Agent3 → Agent6 回写 | 回写后 Agent6 报告的审批意见章节可见更新内容 |
| F-20 | 红线可配置化 | red_line_rules_*.json 可 JSON 编辑，重启后生效 |

### 11.2 性能验收

| 编号 | 验收项 | 通过条件 |
|------|--------|----------|
| P-01 | 对公·确定性计算耗时 | Feature + Scoring + Rule + Case 全部 < 5 秒 |
| P-02 | 对公·LLM 调用耗时 | 两次 LLM 调用合计 < 30 秒 |
| P-03 | 对公·端到端 | < 120 秒 |
| P-04 | 对私·确定性计算耗时 | < 2 秒 |
| P-05 | 对私·端到端 | < 10 秒 |
| P-06 | 对公·LLM 次数 | ≤ 2 次 |
| P-07 | 对私·LLM 次数 | ≤ 1 次 |
| P-08 | Tab 切换延迟 | < 1 秒 |
| P-09 | 红线修改响应 | 修改阈值 → 重算完成 < 2 秒 |

### 11.3 可视化验收

| 编号 | 验收项 | 通过条件 |
|------|--------|----------|
| V-01 | 对公雷达图 | 四维评分清晰可读，低于 60 分标红 |
| V-02 | 对公额度条形图 | 四种测算 + 综合区间 + 申请额度标记完整 |
| V-03 | 对公同业表格 | 5 条案例，相似度降序，本企业高亮 |
| V-04 | 对私评分卡 | 四大类 + 子项分条形图展示 |
| V-05 | 对私征信快照 | 7 项征信指标清晰展示 |
| V-06 | 对私档位表 | 5 档评分映射表，本客户档位高亮 |
| V-07 | 决策卡片 | 两板块共用，结论/额度/利率/红线/条件清晰 |
| V-08 | 状态指示灯 | 6 步流水线状态灯实时更新 |

### 11.4 接口验收

| 编号 | 验收项 | 通过条件 |
|------|--------|----------|
| I-01 | ReportJSON 消费 | 合法 ReportJSON 可被完整解析 |
| I-02 | ReportJSON 缺失字段容错 | 关键字段缺失时给出清晰错误提示，非 hard fail |
| I-03 | DecisionAdvice JSON 导出 | `to_json()` 输出合法 JSON |
| I-04 | 回写 Agent6 | `to_agent6_writeback()` 输出字段齐全 |
| I-05 | Agent6 回写接口 | `apply_decision_writeback()` 正确更新报告 |
| I-06 | 风险偏好 JSON | 可导出/导入，兼容校验 |

### 11.5 边界条件验收

| 编号 | 验收项 | 通过条件 |
|------|--------|----------|
| E-01 | 对公·空 ReportJSON | 给出"数据不足"提示，不崩溃 |
| E-02 | 对公·极端财务（资产负债率>100%） | 评分为 0，不报错 |
| E-03 | 对私·征信查询次数 = 0 | 正常计算，不报错 |
| E-04 | 对私·无抵押物 | 抵押估值类自动置 0，整体评分正常 |
| E-05 | LLM 超时 | 降级到模板输出 |
| E-06 | 未知行业代码（对公） | 用 DEFAULT 基准，前端提示 |
| E-07 | 未知职业类型（对私） | 稳定性子项给默认中等分 |
| E-08 | 红线规则 JSON 格式错误 | 加载时校验失败提示，不影响其他规则 |

---

## 12. 风险偏好配置（可自定义）

### 12.1 可配置项清单

| 配置类别 | 可配置项 | 默认值 | 范围 |
|----------|----------|--------|------|
| 维度权重（对公） | 财务/行业/经营/担保四维权重 | 0.35/0.15/0.25/0.25 | 和 = 1.0 |
| 评分门槛（对公） | A/B/C/D 级分界点 | 80/65/50 | 10-100 |
| 评分门槛（对私） | 优/中优/良好/边界/拒 分界点 | 800/760/700/680 | 300-850 |
| 红线规则（对公 30 条） | 每条规则的 threshold、severity、is_hard、can_waive | 见 red_line_rules_corporate.json | 规则特定 |
| 红线规则（对私 20 条） | 同上 | 见 red_line_rules_retail.json | 规则特定 |
| 利率档位 | 每个评分档位的基准利率 | 见 rate_tier_map | LPR ± 200BP |
| 评分卡子项权重（对私） | 22 个子项各自权重 | 见 scorecard_weights.json | 大类内和 = 1 |
| 额度上限 | 每个评分档位的额度上限 | 500/300/100/50/0 万 | 1-10000 万 |

### 12.2 配置存储方式

- **默认配置**：打包在 `mock_data/risk_appetite_default.json`
- **客户自定义**：存于 `config/risk_appetite_{client_id}.json`，按客户 ID 区分
- **运行时加载**：Agent 启动时按 `client_id` 加载；找不到则回退到 default

### 12.3 配置界面交互（已在第 5.6 节给出）

点击右上角 ⚙ 按钮 → 抽屉式配置面板 → 修改后点"保存配置" → Dashboard 自动重算。

### 12.4 合规审计（重要）

- 每次配置修改都记录在 `config/audit_log.json`：谁改的、改了哪个字段、改之前和之后的值、修改时间
- 重要字段修改需二次确认（如把"关联交易 > 30%"改成"关联交易 > 50%"属于风险偏好放宽，需弹窗确认）
- 演示场景允许宽松模式，生产环境加角色权限控制

---

## 附录 A：评分公式速查表

### A.1 对公四维评分公式（复用 v1.0）

```
# 财务风险
F_financial = 0.25*S(debt_ratio) + 0.15*S(current_ratio) + 0.20*S(revenue_growth)
            + 0.15*S(net_margin) + 0.15*S(cashflow_quality) + 0.10*S(ar_turnover)

# 行业风险
F_industry = 0.30*S(prosperity_index) + 0.20*S(concentration)
           + 0.25*S(policy_sensitivity) + 0.25*S(cyclicality)

# 经营风险
F_operational = 0.20*S(established_years) + 0.20*S(revenue_scale)
              + 0.25*S(cashflow_coverage) + 0.15*S(customer_concentration)
              + 0.20*S(inventory_efficiency)

# 担保风险
F_guarantee = 0.40*S(coverage_ratio) + 0.25*S(collateral_type)
            + 0.20*S(guarantor_strength) + 0.15*S(combination_completeness)

# 综合
C_score = 0.35*F_financial + 0.15*F_industry + 0.25*F_operational + 0.25*F_guarantee

# 等级
Grade = "A" if C_score ≥ 80 else
        "B" if C_score ≥ 65 else
        "C" if C_score ≥ 50 else "D"
```

### A.2 对私评分卡公式

```
# 大类得分
S_capacity  = Σ (w_i × S(v_i)) for v_i in 偿债能力子项
S_willing   = Σ (w_i × S(v_i)) for v_i in 还款意愿子项
S_stability = Σ (w_i × S(v_i)) for v_i in 稳定性子项
S_collateral = Σ (w_i × S(v_i)) for v_i in 抵押估值子项

# 综合 FICO 分
FICO = 0.30*S_capacity + 0.25*S_willing + 0.25*S_stability + 0.20*S_collateral

# 档位
Grade = "优" if FICO ≥ 800 else
        "中优" if FICO ≥ 760 else
        "良好" if FICO ≥ 700 else
        "边界" if FICO ≥ 680 else "拒绝"
```

### A.3 对公额度测算公式

```
# 四种方法
M_revenue    = min(revenue × coef_upper, revenue × coef_lower × 1.5)  # 中值
M_netasset   = net_assets × leverage_limit(grade)
M_cashflow   = operating_cash_flow × coverage_multiple(term_months)
M_collateral = collateral_value × collateral_rate(type)

# 综合区间
valid = [m for m in [M_revenue, M_netasset, M_cashflow, M_collateral] if m.is_binding]
lower = percentile(valid, 25)
upper = percentile(valid, 75)
recommended = weighted_mean(valid)
```

---

## 附录 B：现有 agent_credit 代码的 v2.0 映射

| 现有文件 | 现有功能 | v2.0 动作 | 对应模块 |
|----------|----------|-----------|----------|
| `risk_classifier.py` | 5 维风险分类 (LLM 驱动) | **保留 + 作为对公评分模型底座** | 被 `scoring_model_corporate.py` 调用 |
| `rating_engine.py` | A-E 评级 | **保留** | 对公 grade 映射直接用 |
| `approval_engine.py` | 规则审批 (LLM 兜底) | **保留骨架 + 扩展** | 规则逻辑并入 `rule_engine_v2.py` |
| `agent.py` | 串联调用以上三者 + Agent6 壳 | **重写** | 变为 `CreditDecisionAgent v2.0`, 不再调用 Agent6 |
| `app.py` | 简单对话界面 | **重写** | 双板块 Tab + Dashboard |
| `app_demo.py` | 简化入口 | **合并到 app.py** | 不再独立存在 |
| `prompts.py` | 3 套 LLM prompts | **重写** | 改为 4 套（对公决策/对公红线/对私决策/对私红线） |

---

## 附录 C：术语表

| 术语 | 含义 |
|------|------|
| **Agent6** | 报告生成助手（文书自动化） |
| **Agent3** | 授信决策辅助（本 PRD 对象） |
| **ReportJSON** | Agent6 产出的结构化报告数据 |
| **DecisionAdvice** | Agent3 产出的决策意见 |
| **DecisionEngine** | Agent3 的决策流水线总调度器 |
| **ScoringModel** | 评分模型（对公 4 维 / 对私评分卡） |
| **RuleEngine** | 红线规则引擎 |
| **CaseRetriever** | 相似案例检索器 |
| **AdvisorFormatter** | 决策意见格式化器（调 LLM） |
| **RiskAppetiteConfig** | 风险偏好配置（可自定义） |
| **RedLineHit** | 红线命中对象 |
| **LTV** | Loan-to-Value，贷款价值比（抵押贷款行话） |
| **DTI** | Debt-to-Income，债务收入比 |
| **FICO** | 美国零售信贷通用评分区间（300-850） |
| **LPR** | Loan Prime Rate，贷款市场报价利率 |
| **BP** | Basis Point，基点（1 BP = 0.01%） |
| **对公板块** | 企业授信业务线 |
| **对私板块** | 个人/零售授信业务线 |

---

*文档结束 — PRD\_授信决策辅助智能体\_v2.0*
