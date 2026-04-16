# PRD：合规巡检智能体 v1.0

**版本**：v1.0（Demo改造版）
**日期**：2026-04-13
**作者**：刘野
**文档性质**：产品需求文档（面向Demo交付）
**所属**：众安信科 · 信贷AI智能体矩阵 — Agent5

---

## 1. 产品定位

合规巡检智能体是信贷AI智能体矩阵中的第5个子Agent，定位为**银行信贷业务全流程合规自动审查工具**。

**核心能力**：输入监管政策文件 + 银行实际业务记录，自动逐条比对，输出合规检查报告（含通过/未通过/部分通过明细）、缺陷分级、分阶段整改计划，并支持Word导出。

**目标用户**：
- **主要用户**：银行合规部门人员、风险管理岗
- **次要用户**：业务部门负责人（接收整改要求）、内审人员

**核心价值**：

| 痛点 | 现状 | 产品解决方案 |
|------|------|-------------|
| 政策条款多、比对耗时 | 一份管理办法几十条，人工逐条核对需1-2天 | LLM自动解析政策条款树，逐条比对业务记录 |
| 合规检查标准不统一 | 不同人员对同一条款理解不同，判断结果有偏差 | 统一的检查逻辑，相同输入产出一致结果 |
| 整改计划缺乏优先级 | 发现问题后不知道先改什么 | 缺陷自动分级（critical/major/minor），输出分阶段整改计划 |
| 政策更新后无法快速响应 | 新政策发布后需重新人工梳理检查项 | 上传新政策文件即可自动生成新的检查清单 |

---

## 2. Demo目标

### 2.1 演示定位

面向银行客户的产品能力展示，重点传达三个信息：
1. **自动化**：上传政策+业务记录，全自动输出检查报告
2. **专业性**：政策条款结构化解析，逐条有据可查
3. **可执行**：不止发现问题，还给出分阶段整改计划

### 2.2 演示效果标准

| 指标 | 目标 |
|------|------|
| 端到端耗时 | 预置场景 < 60秒完成全量检查 |
| 合规检查覆盖率 | 政策全部条款均有对应检查结果 |
| 缺陷检出率 | mock数据中埋入的5处不合规项全部检出 |
| 报告导出 | 一键导出结构化Word报告 |

---

## 3. 演示场景设计

### 3.1 场景1：商业银行互联网贷款管理暂行办法（主场景）

**背景**：银保监会2020年发布《商业银行互联网贷款管理暂行办法》，是互联网贷款业务的核心监管文件，共7章56条。银行需定期自查业务是否符合该办法要求。

**输入**：
- 政策文件：《商业银行互联网贷款管理暂行办法》全文（公开文件）
- 业务记录：某商业银行互联网贷款业务操作记录（mock）

**mock业务记录中故意埋入的5处不合规项**：

| # | 违规点 | 对应条款 | 严重程度 | 违规描述 |
|---|--------|---------|---------|---------|
| 1 | 贷款期限超限 | 第6条（期限不超过1年） | critical | mock中存在期限为18个月的个人消费贷款 |
| 2 | 风控模型未独立验证 | 第18条（风险模型管理） | critical | 风控模型上线记录显示未经独立第三方验证 |
| 3 | 联合贷款出资比例不足 | 第51条（出资比例不低于30%） | major | 联合贷款中银行出资比例仅为20% |
| 4 | 贷后管理频次不足 | 第31条（贷后管理） | major | 部分贷款超过6个月未进行贷后检查 |
| 5 | 信息披露不完整 | 第26条（信息披露） | minor | 贷款产品页面未披露年化综合资金成本 |

**预期输出**：
- 政策条款树：7章56条结构化展示
- 合规检查清单：56条均有检查结果，5条标记为不合规
- 合规率：约91%（51/56通过）
- 缺陷汇总：2个critical + 2个major + 1个minor
- 整改计划：分3阶段（立即整改/30天内/90天内）

### 3.2 场景2：个人信息保护法 vs 客户信息管理（可选场景）

**背景**：《个人信息保护法》2021年施行，银行在客户信息采集、存储、使用等环节需全面合规。

**输入**：
- 政策文件：《个人信息保护法》（重点章节摘录）
- 业务记录：某银行客户信息管理操作记录（mock）

**mock中故意埋入的不合规项**：

| # | 违规点 | 对应条款 | 严重程度 |
|---|--------|---------|---------|
| 1 | 超范围采集信息 | 第6条（最小必要原则） | critical |
| 2 | 未经同意向第三方提供 | 第23条（第三方提供） | critical |
| 3 | 数据保留期限过长 | 第19条（存储期限） | major |

---

## 4. 前端交互设计

### 4.1 整体布局

```
┌──────────────────────────────────────────────────────────────┐
│  合规巡检智能体                           [导出报告] [重新检查] │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌── 合规率仪表盘 ──────────────────────────────────────┐   │
│  │  [环形图 91%]   通过: 51  |  未通过: 3  |  部分通过: 2  │   │
│  │                 不适用: 0  |  总计: 56                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ 政策条款树 ─┐  ┌─ 合规检查清单 ─────────────────────┐   │
│  │ 📋 第一章     │  │                                    │   │
│  │   第1条      │  │ ✅ 第1条 贷款定义 — 通过            │   │
│  │   第2条      │  │ ✅ 第2条 适用范围 — 通过            │   │
│  │ 📋 第二章     │  │ ❌ 第6条 期限超限 — 未通过          │   │
│  │   第3条      │  │    └ 详情: 存在18月期限贷款...      │   │
│  │   第4条      │  │ ⚠️ 第18条 模型管理 — 部分通过       │   │
│  │   ...        │  │    └ 详情: 缺少独立验证记录...      │   │
│  │ 📋 第三章     │  │ ✅ 第20条 授信额度 — 通过           │   │
│  │   ...        │  │ ...                                │   │
│  └──────────────┘  └────────────────────────────────────┘   │
│                                                              │
│  ┌── 缺陷汇总 + 整改计划 ──────────────────────────────┐   │
│  │ [Critical] 2项  [Major] 2项  [Minor] 1项              │   │
│  │                                                        │   │
│  │ 阶段一（立即整改，7天内）:                               │   │
│  │   1. 暂停发放期限>1年的互联网贷款                        │   │
│  │   2. 启动风控模型独立验证流程                            │   │
│  │ 阶段二（30天内）:                                       │   │
│  │   3. 调整联合贷款出资比例至30%以上                       │   │
│  │   4. 建立贷后管理定期检查机制                            │   │
│  │ 阶段三（90天内）:                                       │   │
│  │   5. 完善贷款产品信息披露页面                            │   │
│  └────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 组件详细设计

#### 4.2.1 合规率仪表盘（顶部）

| 元素 | 说明 |
|------|------|
| 环形图 | 中心显示合规率百分比（大字号），环形按通过/未通过/部分通过三色分段 |
| 颜色规则 | 通过=绿色(#52C41A)，未通过=红色(#FF4D4F)，部分通过=橙色(#FAAD14) |
| 统计数字 | 4个计数器（通过/未通过/部分通过/不适用），点击可筛选下方清单 |

#### 4.2.2 政策条款树（左侧，宽度30%）

| 元素 | 说明 |
|------|------|
| 树结构 | 章→条 两级，可展开/折叠 |
| 条款状态标记 | 每条前显示状态图标（绿勾/红叉/橙色感叹号） |
| 点击联动 | 点击某条款，右侧清单自动滚动到对应检查项 |
| 搜索框 | 顶部搜索框，支持按关键词过滤条款 |

#### 4.2.3 合规检查清单（右侧，宽度70%）

| 元素 | 说明 |
|------|------|
| 清单项 | 每条一行，含：状态图标 + 条款编号 + 条款摘要 + 检查结论 |
| 展开详情 | 点击某项展开：原文引用 + 业务记录证据 + 判断依据 + 建议措施 |
| 筛选 | 支持按状态筛选（全部/未通过/部分通过/通过） |
| 排序 | 默认按条款顺序，可切换为按严重程度排序 |

#### 4.2.4 缺陷汇总表 + 整改计划（底部）

| 元素 | 说明 |
|------|------|
| 分级统计 | Critical(红)/Major(橙)/Minor(黄) 三色徽章+计数 |
| 缺陷表格 | 列：编号、关联条款、缺陷描述、严重程度、整改建议、整改期限 |
| 整改计划 | 按阶段分组（立即/30天/90天），每阶段列出具体整改项 |
| 导出按钮 | 右上角"导出报告"按钮，生成Word文档 |

### 4.3 交互流程

```
用户进入合规巡检Tab
  │
  ├── [一键演示] 点击预置场景按钮
  │     └── 自动加载政策文件+业务记录 → 触发检查流程
  │
  └── [自定义] 上传政策文件 + 业务文件
        └── 点击"开始检查" → 触发检查流程

检查流程启动
  │
  ├── Step 1: 文件分类（LLM识别文件类型）
  │     └── 前端显示：文件列表 + 分类标签（政策/业务记录）
  │
  ├── Step 2: 政策解析（分段处理，不截断）
  │     └── 前端显示：政策条款树逐步展开
  │
  ├── Step 3: 合规对比（逐条检查）
  │     └── 前端显示：检查清单逐项出现，状态图标实时更新
  │
  ├── Step 4: 缺陷分级 + 整改计划
  │     └── 前端显示：仪表盘数字刷新 + 缺陷表展开
  │
  └── Step 5: 完成
        └── 前端显示：全部就绪，"导出报告"按钮高亮
```

### 4.4 Gradio实现方案

| 组件 | Gradio组件类型 |
|------|---------------|
| 仪表盘 | `gr.HTML`（内嵌ECharts环形图） |
| 政策条款树 | `gr.HTML`（内嵌树形组件，可用纯CSS折叠或Treant.js） |
| 检查清单 | `gr.Dataframe` 或 `gr.HTML`（推荐HTML，交互更灵活） |
| 缺陷表 | `gr.Dataframe` |
| 整改计划 | `gr.Markdown`（支持分阶段格式化） |
| 导出按钮 | `gr.Button` + `gr.File`（下载链接） |
| 场景选择 | `gr.Radio` 或 `gr.Dropdown` |

---

## 5. 后端架构

### 5.1 现有模块（保留）

| 模块 | 文件 | 职责 | 改造计划 |
|------|------|------|---------|
| ComplianceAgent | `agent.py` | 主Agent，编排全流程 | 保留核心流程，增加事件协议输出 |
| policy_parser.py | `policy_parser.py` | LLM解析政策→PolicyDocument | 保留，改造为分段处理 |
| compliance_checker.py | `compliance_checker.py` | LLM逐条对比→ComplianceReport | 保留，不改动 |
| defect_classifier.py | `defect_classifier.py` | 纯规则缺陷分级 | 保留规则逻辑，新增LLM辅助通道 |
| prompts.py | `prompts.py` | 系统提示词 | 保留现有，新增2条 |

### 5.2 改造项

#### 5.2.1 文件分类：关键词启发式 → LLM分类

**现状**：基于文件名+内容关键词匹配判定文件类型，对非标文件名（如"文档1.pdf"）分类失败。

**改造方案**：

```python
# 新增 prompts.py 中的提示词
SYSTEM_FILE_CLASSIFY = """
你是一个文件分类专家。根据文件内容前2000字，判断文件属于以下哪种类型：
- policy: 监管政策、管理办法、规章制度
- business_record: 业务操作记录、审批记录、贷后检查记录
- financial: 财务报表、审计报告
- other: 其他

输出JSON: {"file_type": "policy|business_record|financial|other", "confidence": 0.0-1.0, "reason": "判断依据"}
"""
```

**改造位置**：`agent.py` 中的文件分类阶段。

**降级策略**：LLM分类失败（超时/异常）时，回退到现有关键词逻辑。

#### 5.2.2 政策文本处理：截断12000字 → 分段摘要

**现状**：`policy_parser.py` 将政策全文截断为前12000字送入LLM，导致后半部分条款丢失。

**改造方案**：

```
政策全文（可能5万字）
  │
  ├── Step 1: 按"章"分段（正则匹配"第X章"）
  │     └── 每章独立为一个文本块
  │
  ├── Step 2: 逐章送入LLM解析
  │     └── 每章提取PolicyRequirement列表
  │
  └── Step 3: 合并为完整PolicyDocument
        └── 章节编号去重 + 条款排序
```

**分段策略**：
- 优先按章分段
- 单章超过8000字时，按条进一步细分
- 每段送入LLM时附带全文目录摘要（提供上下文）

**改造文件**：`policy_parser.py`，新增 `_split_by_chapters()` 和 `_parse_chapter()` 方法。

#### 5.2.3 缺陷分级：纯规则 → 规则 + LLM混合

**现状**：`defect_classifier.py` 用关键词规则判定缺陷严重程度，逻辑为：
- 含"资金""安全""违法"→ critical
- 含"记录""流程""管理"→ major
- 其余 → minor

**问题**：关键词无法理解语义，如"信息披露不完整"被错误归为major。

**改造方案**：

```
检查结果 (CheckItem, status=fail/partial)
  │
  ├── 规则引擎初判（保留现有逻辑，0延迟）
  │     └── 输出：initial_severity
  │
  ├── LLM辅助复判（仅对initial_severity有争议或边界case）
  │     └── 输入：条款原文 + 违规描述 + 行业惯例
  │     └── 输出：adjusted_severity + reason
  │
  └── 最终分级 = LLM结果优先，LLM超时则用规则结果
```

**触发LLM复判的条件**：
- 规则结果为minor但条款涉及金额/期限（可能低估）
- 规则结果为critical但违规描述含"部分""轻微"（可能高估）
- 规则引擎无法匹配任何关键词（未覆盖场景）

**改造文件**：`defect_classifier.py`，新增 `_llm_reclassify()` 方法。

### 5.3 新建模块

#### 5.3.1 合规报告Word导出（`report_exporter.py`）

**导出内容**：

```
合规检查报告 — [政策名称]
═══════════════════════════════
检查日期：2026-04-13
检查范围：[政策文件名] vs [业务记录文件名]

一、合规概况
  合规率：91.1%（51/56条通过）
  缺陷统计：Critical 2 | Major 2 | Minor 1

二、逐条检查明细
  第1条 [条款摘要] ..................... ✅ 通过
  第2条 [条款摘要] ..................... ✅ 通过
  ...
  第6条 [条款摘要] ..................... ❌ 未通过
    违规描述：存在期限为18个月的个人消费贷款...
    政策原文：互联网贷款期限不超过一年...
    建议措施：立即停止发放超期限贷款...

三、缺陷清单
  [表格：编号/条款/描述/级别/整改建议]

四、整改计划
  阶段一（立即，7天内）：...
  阶段二（短期，30天内）：...
  阶段三（中期，90天内）：...
```

**技术实现**：基于 `python-docx`，复用项目已有的 `word_export.py` 中的Word生成能力。

#### 5.3.2 预置场景加载器（`scenario_loader.py`）

**职责**：从 `demo_data/agent_compliance/` 目录加载预置场景数据。

```python
class ScenarioLoader:
    def load_scenario(self, scenario_id: str) -> dict:
        """加载预置场景，返回 {policy_file, business_files, expected_output}"""

    def list_scenarios(self) -> list[dict]:
        """返回可用场景列表 [{id, name, description}]"""
```

**场景数据目录结构**：

```
demo_data/agent_compliance/
├── scenario_internet_loan/
│   ├── scenario.json              # 场景元信息（名称、描述）
│   ├── input/
│   │   ├── policy.txt             # 《商业银行互联网贷款管理暂行办法》全文
│   │   └── business_records.json  # mock业务记录（含5处违规）
│   └── expected_output.json       # 预期检查结果（用于验收比对）
└── scenario_personal_info/
    ├── scenario.json
    ├── input/
    │   ├── policy.txt             # 《个人信息保护法》重点章节
    │   └── business_records.json  # mock客户信息管理记录
    └── expected_output.json
```

### 5.4 流程编排（agent.py改造）

```
ComplianceAgent.run(files)
  │
  ├── emit("thinking", "正在分类上传文件...")
  ├── classify_files(files)                    # 改造：LLM分类
  │     └── emit("tool_result", {file_classes})
  │
  ├── emit("thinking", "正在解析政策文件...")
  ├── parse_policy(policy_file)                # 改造：分段处理
  │     └── emit("tool_result", {policy_tree})
  │
  ├── emit("thinking", "正在逐条合规检查...")
  ├── check_compliance(policy, records)        # 保留
  │     └── emit("tool_result", {check_items}) # 逐条emit进度
  │
  ├── emit("thinking", "正在分析缺陷等级...")
  ├── classify_defects(failed_items)           # 改造：规则+LLM
  │     └── emit("tool_result", {defects, remediation_plan})
  │
  └── emit("done", {compliance_report})
```

---

## 6. 数据模型

### 6.1 PolicyDocument（政策文档）

```python
class PolicyRequirement(BaseModel):
    """单条政策要求"""
    article_id: str          # 条款编号，如"第6条"
    chapter: str             # 所属章节，如"第二章 风险管理"
    title: str               # 条款标题/摘要
    content: str             # 条款原文
    keywords: list[str]      # 关键词标签
    requirement_type: str    # "mandatory"(强制) | "recommended"(建议) | "prohibitive"(禁止)

class PolicyDocument(BaseModel):
    """解析后的政策文档"""
    name: str                           # 政策名称
    issuer: str                         # 发布机构
    effective_date: str | None          # 生效日期
    chapters: list[str]                 # 章节列表
    requirements: list[PolicyRequirement]  # 全部条款
    total_articles: int                 # 条款总数
    source_file: str                    # 来源文件名
```

### 6.2 ComplianceReport（合规报告）

```python
class CheckItem(BaseModel):
    """单条检查结果"""
    article_id: str                # 对应条款编号
    article_summary: str           # 条款摘要
    status: str                    # "pass" | "fail" | "partial" | "not_applicable"
    evidence: str                  # 业务记录中的证据引用
    finding: str                   # 检查发现描述
    recommendation: str            # 建议措施（status为fail/partial时）

class ComplianceReport(BaseModel):
    """完整合规检查报告"""
    policy_name: str               # 检查依据的政策名称
    check_date: str                # 检查日期
    total_items: int               # 检查项总数
    pass_count: int
    fail_count: int
    partial_count: int
    na_count: int
    compliance_rate: float         # 合规率 = pass / (total - na)
    items: list[CheckItem]         # 全部检查项
```

### 6.3 Defect（缺陷）

```python
class Defect(BaseModel):
    """单个缺陷"""
    defect_id: str                 # 缺陷编号，如"DEF-001"
    article_id: str                # 关联条款
    description: str               # 缺陷描述
    severity: str                  # "critical" | "major" | "minor"
    severity_reason: str           # 分级依据
    remediation: str               # 整改建议
    remediation_phase: int         # 整改阶段（1=立即/2=30天/3=90天）
    remediation_deadline: str      # 整改期限描述

class RemediationPlan(BaseModel):
    """整改计划"""
    defects: list[Defect]
    phase_1: list[str]             # 立即整改项（7天内）
    phase_2: list[str]             # 短期整改项（30天内）
    phase_3: list[str]             # 中期整改项（90天内）
    summary: str                   # 整改计划概述
```

---

## 7. LLM调用设计

### 7.1 调用清单

| # | 调用点 | 提示词 | 输入 | 输出 | 状态 |
|---|--------|--------|------|------|------|
| 1 | 政策解析 | `SYSTEM_POLICY_PARSE` | 政策文本（分段） | PolicyRequirement列表 | **现有，保留** |
| 2 | 合规对比 | `SYSTEM_COMPLIANCE_CHECK` | 单条PolicyRequirement + 业务记录 | CheckItem | **现有，保留** |
| 3 | 文件分类 | `SYSTEM_FILE_CLASSIFY` | 文件内容前2000字 | 文件类型+置信度 | **新增** |
| 4 | 缺陷分析 | `SYSTEM_DEFECT_ANALYSIS` | 条款原文+违规描述 | 调整后severity+理由 | **新增** |

### 7.2 新增提示词设计

#### SYSTEM_FILE_CLASSIFY（文件分类）

```
你是银行合规文件分类专家。根据文件内容判断文件类型。

文件类型定义：
- policy: 监管政策文件（法律法规、管理办法、通知、指引等，特征：含"第X条""第X章"、发文机关、施行日期）
- business_record: 业务操作记录（贷款审批记录、放款记录、贷后检查记录等，特征：含日期、金额、客户名、审批意见）
- financial: 财务报表文件
- other: 其他

输出格式（JSON）:
{"file_type": "...", "confidence": 0.95, "reason": "..."}

注意：置信度低于0.7时，标记file_type为"unknown"。
```

#### SYSTEM_DEFECT_ANALYSIS（缺陷分析）

```
你是银行合规缺陷分析专家。根据以下信息判断缺陷的严重程度。

严重程度定义：
- critical: 违反强制性规定，可能导致监管处罚、业务暂停或重大资金损失
- major: 违反管理性规定，存在合规风险但短期内不会引发严重后果
- minor: 违反建议性规定或信息披露要求，影响范围有限

输入：
- 条款原文: {article_content}
- 条款类型: {requirement_type} (mandatory/recommended/prohibitive)
- 违规描述: {finding}

输出格式（JSON）:
{"severity": "critical|major|minor", "reason": "判断依据，引用具体条款和违规事实"}
```

### 7.3 Token消耗估算

| 调用 | 单次Token（输入+输出） | 场景1调用次数 | 总Token |
|------|----------------------|-------------|---------|
| 文件分类 | ~2500 | 2次 | ~5K |
| 政策解析（分段） | ~4000 | 7次（7章） | ~28K |
| 合规对比 | ~3000 | 56次 | ~168K |
| 缺陷分析 | ~2000 | 5次 | ~10K |
| **合计** | | | **~211K** |

**成本估算**：以DeepSeek为例，约 0.5-1.0 元人民币/次完整检查。

---

## 8. Mock数据规格

### 8.1 政策文件：《商业银行互联网贷款管理暂行办法》

**来源**：中国银保监会官网公开文件（银保监会令〔2020〕第9号）

**全文结构**：
- 第一章 总则（第1-5条）
- 第二章 风险管理（第6-21条）
- 第三章 风险数据和风险模型管理（第22-25条）
- 第四章 信息披露与消费者保护（第26-30条）
- 第五章 贷后管理（第31-37条）
- 第六章 监督管理（第38-50条）
- 第七章 附则（第51-56条）

**处理方式**：全文以TXT/PDF格式存储，不截断。

### 8.2 Mock业务记录：互联网贷款业务操作流水

**格式**：JSON，结构如下：

```json
{
  "bank_name": "XX商业银行",
  "report_period": "2025-01-01 ~ 2025-12-31",
  "loan_products": [
    {
      "product_name": "e贷通",
      "product_type": "个人消费贷款",
      "channel": "手机银行APP",
      "max_amount": 200000,
      "max_term_months": 18,          // ❌ 违规：超过12个月
      "interest_rate_range": "4.35%-14.6%",
      "annual_cost_disclosed": false   // ❌ 违规：未披露年化成本
    }
  ],
  "risk_model_records": [
    {
      "model_name": "信用评分模型V3",
      "launch_date": "2025-03-15",
      "independent_validation": false, // ❌ 违规：未独立验证
      "validation_report": null
    }
  ],
  "joint_loan_records": [
    {
      "partner": "XX消费金融公司",
      "bank_funding_ratio": 0.20,     // ❌ 违规：低于30%
      "total_balance": 50000000
    }
  ],
  "post_loan_reviews": [
    {
      "loan_id": "LOAN-2025-001234",
      "last_review_date": "2025-01-10",
      "next_review_due": "2025-04-10",
      "actual_review_date": null,      // ❌ 违规：超期未检查
      "overdue_days": 270
    }
  ],
  "compliance_training": {
    "last_training_date": "2025-06-15",
    "coverage_rate": 0.95
  },
  "customer_complaint_records": {
    "total_complaints": 23,
    "resolved_within_15days": 21,
    "resolution_rate": 0.913
  }
}
```

**设计原则**：
- 大部分字段合规，只在5个明确位置埋入违规项
- 违规项覆盖不同严重程度（2 critical + 2 major + 1 minor）
- 数据格式模拟真实银行系统导出格式
- 包含足够上下文使LLM能正确判断

### 8.3 场景2 Mock数据（可选）

客户信息管理记录，含3处违规：超范围采集（收集了与业务无关的宗教信仰字段）、未经同意向第三方征信公司提供数据、客户注销后数据保留5年未删除。

---

## 9. 与其他Agent的数据接口

### 9.1 数据消费（合规巡检作为消费方）

| 来源Agent | 数据对象 | 接口形式 | 用途 |
|-----------|---------|---------|------|
| 报告生成助手(Agent6) | EnterpriseProfile JSON | 文件/API | 获取企业基本信息作为检查上下文 |
| 风控策略运营(Agent2) | 规则集 + 回测结果 | JSON | 检查风控规则是否符合监管要求 |
| 贷中风险预警(Agent4) | 预警记录 | JSON | 检查贷后管理是否及时响应预警 |

### 9.2 数据生产（合规巡检作为生产方）

| 消费Agent | 数据对象 | 接口形式 | 说明 |
|-----------|---------|---------|------|
| 所有Agent | 合规状态 | `ComplianceStatus` JSON | 通过/未通过 + 不合规条目数 |
| 授信决策辅助(Agent3) | 合规风险标签 | JSON | 影响授信决策的合规风险提示 |
| Portal仪表盘 | 合规率 | 数值 | 顶层仪表盘展示 |

### 9.3 接口数据结构

```python
# 合规巡检 → 其他Agent 的标准输出
class ComplianceStatus(BaseModel):
    """合规状态摘要（跨Agent共享）"""
    enterprise_id: str | None       # 关联企业ID（如有）
    policy_name: str                # 检查依据政策
    check_date: str
    is_compliant: bool              # 总体是否合规（无critical缺陷）
    compliance_rate: float
    critical_count: int
    major_count: int
    minor_count: int
    blocking_issues: list[str]      # 阻断性问题描述（critical级）
    report_file: str | None         # 导出报告文件路径
```

### 9.4 Demo阶段接口策略

Demo阶段不做实时跨Agent调用，采用以下方式模拟：
- 合规巡检输出 `ComplianceStatus` JSON文件到 `outputs/` 目录
- 其他Agent通过读取该文件获取合规状态
- Portal仪表盘通过轮询文件变更刷新合规率展示

---

## 10. 验收标准

### 10.1 功能验收

| # | 验收项 | 验收标准 | 优先级 |
|---|--------|---------|--------|
| 1 | 预置场景一键运行 | 点击"互联网贷款管理办法"场景，无需额外操作，自动完成全流程 | P0 |
| 2 | 政策全文解析 | 《暂行办法》56条全部被识别和结构化，无遗漏 | P0 |
| 3 | 合规检查完整性 | 56条均有检查结果（pass/fail/partial/not_applicable） | P0 |
| 4 | 缺陷全部检出 | mock数据中埋入的5处违规全部被标记为fail或partial | P0 |
| 5 | 缺陷分级准确 | 5处违规的severity与预期一致（2C+2M+1m） | P0 |
| 6 | 整改计划输出 | 输出分3阶段的整改计划，每项有明确期限和建议 | P0 |
| 7 | Word报告导出 | 点击"导出报告"生成.docx文件，内容完整可读 | P0 |
| 8 | 仪表盘展示 | 环形图+统计数字正确反映检查结果 | P1 |
| 9 | 政策条款树 | 左侧树形结构可展开折叠，点击联动右侧清单 | P1 |
| 10 | 文件LLM分类 | 上传非标文件名的政策文件，能正确识别为policy类型 | P1 |
| 11 | 场景2可运行 | 个人信息保护法场景可运行并输出结果 | P2 |

### 10.2 性能验收

| 指标 | 标准 |
|------|------|
| 场景1端到端耗时 | < 90秒（含所有LLM调用） |
| 单条合规对比耗时 | < 3秒/条 |
| Word导出耗时 | < 5秒 |
| 页面首次加载 | < 3秒 |

### 10.3 质量验收

| 指标 | 标准 |
|------|------|
| 误报率 | 将合规项误判为不合规的比例 < 5% |
| 漏报率 | 将不合规项误判为合规的比例 = 0%（对mock数据） |
| 分级准确率 | 缺陷严重程度与预期一致率 >= 80% |

### 10.4 不在本版本范围

- 多政策同时检查（v2.0）
- 历史检查结果对比和趋势分析（v2.0）
- 自动关联银行内部制度文件（v2.0）
- 检查结果自动推送到合规系统（v2.0）
- 自定义检查规则编辑器（v2.0）

---

## 附录

### A. 文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `agent.py` | 改造 | ComplianceAgent主流程，增加事件协议+LLM文件分类 |
| `policy_parser.py` | 改造 | 分段解析政策文本，不截断 |
| `compliance_checker.py` | 保留 | 逐条合规对比，不改动 |
| `defect_classifier.py` | 改造 | 新增LLM辅助分级通道 |
| `prompts.py` | 改造 | 新增SYSTEM_FILE_CLASSIFY + SYSTEM_DEFECT_ANALYSIS |
| `report_exporter.py` | **新建** | Word报告导出 |
| `scenario_loader.py` | **新建** | 预置场景数据加载 |
| `app.py` | **重写** | Gradio前端，政策树+清单+仪表盘布局 |

### B. 依赖

| 依赖 | 用途 | 版本 |
|------|------|------|
| python-docx | Word导出 | >=0.8.11 |
| gradio | 前端UI | >=4.0 |
| pydantic | 数据模型 | >=2.0 |
| echarts（CDN） | 环形图渲染 | 5.x |
