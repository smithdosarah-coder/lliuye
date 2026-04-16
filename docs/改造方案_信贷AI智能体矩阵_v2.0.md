# 信贷 AI 智能体矩阵改造方案 v2.0

**版本**：v2.0（替代 v1.0）
**日期**：2026-04-13
**作者**：众安信科 AI 中台团队
**文档性质**：内部交付改造方案（重大方向修正版）
**所属平台**：众安信科 · 乾策平台（X-Nexus）

---

## 0. v2.0 是什么 · 为什么要出

### 0.1 v1.0 做了什么

v1.0（2026-04-13 上午）解决了一个问题：**从"技术原型"变成"可演示产品"**。核心工作是统一 Portal、品牌视觉、预置 Demo 数据、报告导出。后端业务逻辑全部保留。

### 0.2 v1.0 漏了什么

v1.0 按原有 5 个 Agent 的既定形态做前端包装，**没有回到产品定位问题的原点**：这些 Agent 到底解决客户什么痛点？演示场景和生产场景是不是同一件事？

客户视角的本质检验是：

> **客户坐在会议室打开 Demo，能不能一眼看出这是一个"生产形态"的产品，而不是"演示形态"的玩具？**

v1.0 下 3 个 Agent（1/4/5）都没过这道关——演示时写死几个单企业场景卡，生产用法完全不是这样。客户会觉得"你们这 Demo 是专门搭出来糊弄我的"。

### 0.3 v2.0 修什么

v2.0 解决的是**产品定位**，不是 UI 和 Demo 数据。核心动作：

- **Agent1、Agent4、Agent5**：统一用"知识库扫描范式"重新定义——从"单查工具"改为"批量扫描雷达"
- **Agent3**：与 Agent6 解耦重新定位——从"读材料出评估"改为"消费报告 + 多源信息 → 出决策"，新增对公 / 对私双板块
- **Agent2**：保持 v1.0 定位，不调整
- **Agent6**：保持原有产品能力，作为 Agent3 的上游数据源

v2.0 是 v1.0 的**定位修正版**，不替代 v1.0 的前端改造成果（Portal、品牌色、Mock 数据体系、导出等 v1.0 的工作在 v2.0 下继续有效）。

---

## 1. 执行摘要

### 1.1 核心变更

| 维度 | v1.0 定位 | v2.0 定位 |
|------|----------|----------|
| Agent1 获客 | 输入单企业 → 推荐银行信贷产品 | **上传知识库 → 外网搜相似新客户 + 顺带推产品** |
| Agent2 风控 | 规则编辑 + 回测 + 差错分析 | 不变 |
| Agent3 授信 | 读材料出评估（与 Agent6 重复） | **消费 Agent6 报告 + 多源信息 → 决策引擎（对公 + 对私）** |
| Agent4 预警 | 输入单企业名 → 出信号灯 | **上传知识库 → 批量扫全量客户 → 分级榜单** |
| Agent5 合规 | 单份政策 + 单份业务 → 出缺陷 | **上传知识库 → 批量矩阵扫描 → 违规榜单** |
| Agent6 报告 | 独立生成 1.5 万字报告 | **不变，额外新增 Agent3 串联入口** |

### 1.2 贯穿 v2.0 的三个核心决策

**决策 1：知识库扫描范式**（Agent1/4/5 共享架构）

客户上传知识库 → Agent 抽取规则/画像 → 遍历扫描目标池 → 输出分级命中清单。

这个范式覆盖了银行客户经理 / 贷后经理 / 合规官的真实工作形态——**被动收预警、批量看榜单**，不再逐户手工查。

**决策 2：搜索优先架构**（核心约束）

基础框架围绕"真实搜索"设计，Mock 只是接口下的一个实现层：

```
SearchProvider (interface)
  ├─ MockProvider (Demo 用，读预置池)
  └─ WebProvider (生产用，调真 API)
```

切换只靠一行代码：`provider = MockProvider() if demo_mode else WebProvider()`。所有下游模块只接触抽象接口，不准 if-else 分支判 mock/web。

**决策 3：Agent3 重新定位为决策引擎（对公 + 对私双板块）**

Agent3 不再做"读材料出评估"（与 Agent6 重复），而是：

- 消费 Agent6 的报告输出
- 补充多源信息（行业基准、历史案例、内部审贷指引、征信）
- 输出决策 Dashboard（批否 / 额度 / 期限 / 利率 / 红线）
- 覆盖对公（企业授信 50 万 - 5000 万）和对私（个人零售 5 万 - 500 万）两条业务线

---

## 2. 共享架构：知识库扫描范式

### 2.1 为什么需要共享架构

Agent1、Agent4、Agent5 虽然业务领域不同，但**底层都是同一个形态**：

| Agent | 知识库（用户上传的锚）| 扫描目标 | 命中输出 |
|-------|---------------------|---------|---------|
| Agent1 获客 | 已有客户名录 + 政策导向 + 行业指引 | 外网企业池 | 相似新客户线索 |
| Agent4 贷中预警 | 预警规则 + 在贷客户名录 + 管理制度 | 全量在贷客户 × 外部/内部双路 | 分级风险客户榜 |
| Agent5 合规巡检 | 监管政策库 + 内部制度 + 业务数据 | 政策条款 × 业务事件 | 分级违规清单 |

抽象出来的范式：

```
KnowledgeBase (客户上传的锚)
      ↓ 抽取
RuleSet / IdealProfile / PolicyClauses
      ↓ 驱动扫描
ScanTargets (被扫描的对象池)
      ↓ 匹配
Matcher / HitRanker
      ↓
HitList (分级命中清单：红 / 黄 / 绿)
```

### 2.2 共享组件（3 个 Agent 共用）

| 组件 | 作用 | 共享实现 |
|------|------|---------|
| `SearchProvider` | 抽象外部搜索（企业信息 / 诉讼 / 舆情 / 政策）| Mock + Web 双实现 |
| `KnowledgeBase` | 客户知识库抽象（多文件上传 + 分类） | 通用文件解析器 |
| `RuleExtractor` | LLM 从非结构化文档抽结构化规则 | 统一 Prompt 模板 + Pydantic schema |
| `Matcher / HitRanker` | 打分分级（红 / 黄 / 绿） | 可配置权重 |

**组件定义见**：`docs/共享架构_知识库扫描范式_v1.0.md`（单独文档详细说明接口 + 数据模型 + Mock 规格）

### 2.3 Agent3 为什么不套这个范式

Agent1/4/5 = "一对多批量扫描"（从 N 里筛）
Agent3 = "一对多维深入"（对 1 做 N 维判断）

两种范式不能混。Agent3 的架构核心：

```
DecisionEngine
  ├─ FeatureExtractor（从材料抽特征）
  ├─ ScoringModel（对公模型 / 对私模型，可切换）
  ├─ RuleEngine（硬红线触发）
  ├─ CaseRetriever（从历史案例库捞相似案例）
  └─ AdvisorFormatter（决策卡片生成器）
```

**组件定义见**：`docs/PRD_授信决策辅助智能体_v2.0.md`

---

## 3. v2.0 各 Agent 改造清单

### 3.1 保留 / 重写 / 新建矩阵

| Agent | 保留模块 | 重写模块 | 新建模块 |
|-------|---------|---------|---------|
| **Agent1 获客** | channel_rules.py（产品库）、scoring.py（产品评分）| agent.py、prompts.py、app_demo.py | knowledge_base.py、search_provider.py、profile_extractor.py、lead_finder.py、product_recommender.py |
| **Agent3 授信** | risk_classifier.py、rating_engine.py、approval_engine.py | agent.py、prompts.py、app_demo.py | decision_engine.py、scoring_model_corp.py、scoring_model_retail.py、case_retriever.py、advisor_formatter.py |
| **Agent4 预警** | alert_engine.py、disposition.py、trend_analyzer.py（单客户风险打分逻辑）| agent.py、prompts.py、app_demo.py | customer_scanner.py、rule_extractor.py、cross_matcher.py |
| **Agent5 合规** | policy_parser.py、compliance_checker.py、defect_classifier.py（部分）| agent.py、prompts.py、app_demo.py | knowledge_base.py、rule_set_builder.py、event_extractor.py、matrix_matcher.py |
| **Agent2 风控** | 全部保留（v1.0 定位不变） | 无 | 无 |
| **Agent6 报告** | 全部保留 | 无 | 增加"送 Agent3 做决策"入口按钮 |

### 3.2 共享模块新建清单（Agent1/4/5 共用）

| 模块 | 路径 | 内容 |
|------|------|------|
| SearchProvider | `shared/search_provider.py` | 抽象接口 + MockProvider + WebProvider |
| KnowledgeBase | `shared/knowledge_base.py` | 多文件上传 + 分类 + 解析 |
| RuleExtractor | `shared/rule_extractor.py` | LLM 抽规则 + Schema 校验 |
| Matcher | `shared/matcher.py` | 通用打分 + 分级 |
| DataModels | `shared/scan_models.py` | 共用 Pydantic：`CompanyProfile` / `RuleItem` / `HitItem` / `RiskLevel` |

### 3.3 前端 UI 范式统一

Agent1/4/5 的 `app_demo.py` 遵循同一个"扫描雷达"UI 骨架：

```
┌────────────────────────────────────────────┐
│  知识库上传区（多文件分类）                   │
├────────────────────────────────────────────┤
│  扫描进度条 + 实时 tick                      │
├────────────────────────────────────────────┤
│  ┌────────┬────────────┬────────────┐     │
│  │ 分级榜单 │ 命中详情    │ 处置/建议    │    │
│  │ 🔴 X 家 │ 点击切换     │ 行动卡片     │    │
│  │ 🟡 Y 家 │ 证据链       │ 责任方       │    │
│  │ 🟢 Z 家 │ 双路来源     │ 下次跟进     │    │
│  └────────┴────────────┴────────────┘     │
├────────────────────────────────────────────┤
│  顶部统计 / 导出按钮                         │
└────────────────────────────────────────────┘
```

Agent3 UI 单独设计（对公 / 对私 Tab + 雷达图 + 评分卡），见其 PRD。

### 3.4 Demo 场景升级

| Agent | v1.0 场景卡 | v2.0 场景卡 |
|-------|------------|------------|
| Agent1 | 单企业获客（制造 / 科创）| **Look-alike 场景**（制造业知识库 / 科创企业知识库），每个 KB 含已有客户 20+ 家 + 政策 + 指引 |
| Agent3 | 单企业授信评估 | **对公场景**（福建中锐，串联 Agent6 报告）+ **对私场景**（个体工商户经营贷）|
| Agent4 | 3 个单企业（红 / 黄 / 绿）| **2 个组合扫描**（小微信贷 100 家 / 供应链 100 家），扫出榜单 |
| Agent5 | 单份政策 + 单份业务 | **2 个合规扫描**（互联网贷款办法 / 反洗钱办法），各含多份政策 + 本行制度 + 100 条业务 |

---

## 4. 数据流：6 Agent 全链路串联

### 4.1 整体数据流

```
Agent1（获客）──→ 新客户线索卡
                  ↓ 客户落地后
Agent6（报告）──→ 授信调查报告 Word
                  ↓ 决策触发
Agent3（决策）──→ 批否 + 额度 + 期限 + 利率
                  ↓ 放款后
Agent4（预警）──→ 批量监控 → 榜单
Agent5（合规）──→ 批量合规 → 榜单
Agent2（风控）──→ 策略优化 ← 反馈到 Agent3
```

### 4.2 关键接口

| 接口 | 生产方 | 消费方 | 数据载体 |
|------|-------|-------|---------|
| 新线索 → 客户档案 | Agent1 | 人工（CRM）| LeadCard JSON |
| 企业材料 → 调查报告 | Agent6 | Agent3 | ReportJSON + Word |
| 调查报告 → 决策建议 | Agent3 | 审批流 / Agent6 回写 | DecisionAdvice |
| 放款客户 → 贷中监控 | 人工（台账）| Agent4 | 客户名录 Excel |
| 审批记录 → 合规扫描 | 人工（台账）| Agent5 | 业务数据 Excel |

### 4.3 Demo 串联演示脚本（8 分钟）

| 时间 | 动作 | 亮点 |
|------|------|------|
| 0:00-1:00 | Agent1：上传制造业知识库 → 搜到 10 家新线索 | Look-alike 画像抽取可视化 |
| 1:00-2:00 | Agent1：点击某条线索 → 看推荐产品 + 切入话术 | 获客 + 产品推荐一体化 |
| 2:00-3:00 | Agent6：上传该企业材料 → 生成调查报告 | 1.5 万字报告瞬间生成 |
| 3:00-4:30 | Agent3：点击"送决策" → 消费报告 + 出 Dashboard | 四维雷达 + 决策卡片 |
| 4:30-5:30 | Agent4：上传在贷客户知识库 → 批量扫描 → 榜单 | 100 家揪出 3 家红灯 |
| 5:30-6:30 | Agent5：上传合规知识库 → 矩阵扫描 → 违规榜 | 条款 × 事件可追溯 |
| 6:30-7:30 | Agent2：基于 Agent3 历史数据 → 策略回测 | KS/PSI 指标可视化 |
| 7:30-8:00 | 收尾：6 Agent 闭环已展示 | 统一 Portal 品牌感 |

---

## 5. 交付物清单（v2.0）

### 5.1 文档

| 文档 | 状态 |
|------|------|
| 改造方案_信贷AI智能体矩阵_v2.0.md（本文档）| ✅ |
| 共享架构_知识库扫描范式_v1.0.md | 🔄 本轮产出 |
| PRD_全渠道流量匹配智能体_v2.0.md | 🔄 本轮产出 |
| PRD_授信决策辅助智能体_v2.0.md | 🔄 本轮产出 |
| PRD_贷中风险预警助手_v2.0.md | 🔄 本轮产出 |
| PRD_合规巡检智能体_v2.0.md | 🔄 本轮产出 |
| PRD_风控策略运营助手_v1.0.md | ✅（不变） |
| PRD_客户经理个人助手_v3.1.md | 🔄 本轮产出（小幅更新） |
| PRD_报告生成助手.md | ✅（不变） |

### 5.2 代码

| 模块 | 交付 |
|------|------|
| shared/search_provider.py | 🔨 新建 |
| shared/knowledge_base.py | 🔨 新建 |
| shared/rule_extractor.py | 🔨 新建 |
| shared/matcher.py | 🔨 新建 |
| shared/scan_models.py | 🔨 新建 |
| agent_channel/* | 🔨 重写 agent.py + 新建 4 个模块 |
| agent_credit/* | 🔨 重写 agent.py + 新建 5 个模块 |
| agent_alert/* | 🔨 重写 agent.py + 新建 3 个模块 |
| agent_compliance/* | 🔨 重写 agent.py + 新建 4 个模块 |

### 5.3 Mock 数据

| 目录 | 内容 |
|------|------|
| demo_data/agent_channel/ | 2 个 Look-alike 场景（各含 20+ 家 mock 客户 + 政策 + 指引）+ 50 家 mock 外部企业池 |
| demo_data/agent_credit/ | 对公 3 家 + 对私 3 家 + 同业案例库 50 条 |
| demo_data/agent_alert/ | 2 个组合扫描场景（各 100 家 mock 客户）+ 20 条预警规则 + 管理制度 mock |
| demo_data/agent_compliance/ | 2 套政策 + 本行制度 + 各 100 条业务数据 |

---

## 6. 实施顺序

### 阶段 1：PRD 定稿（本轮）

- 共享架构文档
- 4 份 v2.0 PRD（Agent1/3/4/5）
- 改造方案 v2.0（本文档）
- 总 PRD v3.1 更新

### 阶段 2：共享模块开发（2 天）

优先写共享层 —— 所有 Agent 依赖它：

- `shared/search_provider.py` + `MockProvider` + `WebProvider` 骨架
- `shared/knowledge_base.py` 通用解析
- `shared/scan_models.py` Pydantic 数据模型

### 阶段 3：Agent 重写（并行，5 天）

- Agent1 / Agent4 / Agent5 并行重写（都基于共享层）
- Agent3 单独重写（决策引擎独立架构）
- Mock 数据同步准备

### 阶段 4：Demo 整合 + 串联演示（2 天）

- Portal 更新场景卡
- 串联演示脚本
- 验收标准复核

### 阶段 5：飞书文档同步（0.5 天）

- 所有 v2.0 文档同步到飞书 wiki 「人人都是TMD产品经理」知识库

---

## 7. 与 v1.0 的关系

### 7.1 v1.0 工作成果在 v2.0 下是否有效

| v1.0 工作项 | v2.0 状态 |
|------------|----------|
| Portal 统一入口 | ✅ 继续有效，只改 Tab 内的 Demo 场景卡 |
| 众安蓝品牌色 + CSS | ✅ 继续有效 |
| shared/demo_ui.py 工具层 | ✅ 继续有效 |
| 全局 API Key 抽屉 | ✅ 继续有效 |
| 导出功能（Agent4）| ✅ 继续有效，扩展到其他 Agent |
| Agent4 信号灯动画 | ⚠️ 部分复用（单客户详情面板保留） |
| Agent4 旧场景卡（华联/盛达/顺通）| ❌ 废弃，改为组合扫描场景 |
| Agent1/5 旧场景卡 | ❌ 废弃，改为知识库扫描场景 |
| Agent3 当前 Demo | ❌ 废弃，重新定位 |

### 7.2 为什么不彻底推翻 v1.0

- Portal、品牌、CSS、数据模型、Mock 数据体系这些"工程基础设施"的工作 v1.0 已经做完，不重复
- v2.0 是**产品定位修正**，不是工程重做
- Agent2 / Agent6 定位正确，v1.0 下保持不变

---

## 8. 风险与取舍

### 8.1 已识别风险

| 风险 | 应对 |
|------|------|
| 真外网搜索 API 不稳定（裁判文书网反爬）| Demo 阶段用 MockProvider，生产阶段再接；SearchProvider 接口已隔离此风险 |
| LLM 规则抽取准确度不够 | 配合 schema 校验 + 人工审核兜底；抽完规则落库可人工修订 |
| 批量扫描耗时长（100 家 × 双路）| 并发控制 + 进度条 + 分段展示；UI 不阻塞 |
| 对公 / 对私模型差异大，共享底座强行整合 | 双板块各自独立 Scoring Model，只共享上层接口和 UI 骨架 |
| 客户演示时 Mock 数据看起来真实性不足 | 预置数据做到真实感（真实行业名 + 合理数字区间），场景卡说明"以 mock 数据演示" |

### 8.2 不做什么

- **不做**真搜索 API 接入（留给生产阶段）
- **不做**实时监控和告警推送（超出 Demo 范围）
- **不做**登录鉴权和多租户（Demo 期不需要）
- **不做**Agent2（风控策略）定位调整（v1.0 方向正确）

---

## 9. 验收标准

### 9.1 整体

- 6 Agent 全在统一 Portal 内运行
- 任意 Agent 可独立演示（<2 分钟）
- 串联演示可 8 分钟内完整跑通
- 所有文档同步至飞书知识库

### 9.2 单 Agent（v2.0 关键项）

| Agent | 验收关键 |
|-------|---------|
| Agent1 | 上传知识库 → 2 分钟内出 10 条线索卡 + 每条含 Top 3 产品 + 话术 |
| Agent3 | 对公场景 2 分钟出决策 Dashboard / 对私场景 10 秒出评分 / 可串联 Agent6 |
| Agent4 | 上传 100 家客户 → 2 分钟扫完 → 榜单分级 + 证据链可追溯 |
| Agent5 | 上传 N 份政策 + 100 条业务 → 3 分钟扫完 → 违规明细到条款号 + 业务单号 |

---

## 附录 A：术语表

| 术语 | 定义 |
|------|------|
| Look-alike 获客 | 用已有客户特征反向在外部找相似新客户 |
| 知识库扫描范式 | 客户上传知识库 → Agent 批量扫描 → 输出分级榜单的产品形态 |
| SearchProvider | 对外部搜索（企业信息 / 诉讼 / 舆情 / 政策）的统一抽象接口 |
| MockProvider / WebProvider | SearchProvider 的两种实现：前者读预置数据（Demo），后者接真 API（生产）|
| 对公板块 | 企业授信业务（B2B）|
| 对私板块 | 个人 / 零售授信业务（B2C）|
| 红 / 黄 / 绿分级 | 预警或合规扫描结果的风险等级 |

## 附录 B：文档索引

- 本文档（改造方案 v2.0）
- 共享架构：`docs/共享架构_知识库扫描范式_v1.0.md`
- 各 Agent PRD v2.0（Agent1/3/4/5）
- 总 PRD：`docs/PRD_客户经理个人助手_v3.1.md`
- 未变更的 PRD：Agent2（v1.0）/ Agent6（原报告生成 PRD）

---

**文档结束**
