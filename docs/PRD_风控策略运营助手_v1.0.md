# PRD：风控策略运营助手 v1.0

**版本**：v1.0（Demo改造版）
**日期**：2026-04-13
**作者**：刘野
**文档性质**：子Agent产品需求文档（面向Demo交付）
**所属矩阵**：众安信科 · 信贷AI智能体矩阵 — Agent #2

---

## 1. 产品定位

风控策略运营助手是一个支持自然语言配策略、自动回测评估、差错案件诊断的风控智能体，让风控运营人员无需编写代码即可完成策略全生命周期管理。

---

## 2. Demo目标

| 维度 | 目标 |
|------|------|
| 核心价值 | 3分钟内完成"策略描述→规则生成→回测评估→报告输出"的完整闭环 |
| 演示对象 | 银行风控部门负责人、策略运营岗 |
| 演示时长 | 单Agent演示5-8分钟，矩阵联动演示中占3-5分钟 |
| 体验标准 | 预置场景一键启动，图表可视化呈现，结果可导出PDF |
| 后端原则 | 现有agent.py、rule_engine.py、backtesting.py、metrics.py、prompts.py全部保留，只做接入改造和图表层新建 |

---

## 3. 演示场景设计

### 场景1：小微信用贷策略回测

**用户故事**：风控运营人员想评估一套小微信用贷准入策略在历史数据上的表现。

**操作流程**：

| 步骤 | 用户操作 | 系统响应 |
|------|---------|---------|
| 1 | 点击"小微信用贷回测"预置场景按钮 | 自动加载100条mock授信数据CSV + 预置规则集JSON |
| 2 | 查看已加载的规则集（DSL代码块展示） | 展示3条规则：负债率>70%拒绝、注册资本<50万拒绝、成立年限<2年拒绝 |
| 3 | 点击"执行回测" | 调用backtesting.py执行规则命中，调用metrics.py计算指标 |
| 4 | 查看回测结果 | 展示：通过率/拒绝率圆环图、规则命中分布条形图、KS曲线、混淆矩阵热力图 |
| 5 | LLM生成分析报告 | 自动生成策略效果总结（精确率/召回率解读、策略松紧建议） |
| 6 | 点击"导出PDF" | 下载包含图表和分析文本的回测报告 |

**演示要点**：
- 强调"无需手动上传数据，一键启动"
- KS值、精确率/召回率等指标要有业务含义解读，不是纯数字堆砌
- 展示metrics.py的完整能力（KS/PSI/混淆矩阵/F1）

### 场景2：差错案件诊断

**用户故事**：风控运营人员发现近期误杀率上升，需要定位哪条规则导致问题并给出优化建议。

**操作流程**：

| 步骤 | 用户操作 | 系统响应 |
|------|---------|---------|
| 1 | 点击"差错案件诊断"预置场景按钮 | 加载50条mock差错案件数据（含误杀30条、漏杀20条） |
| 2 | 查看差错数据概览 | 展示：误杀/漏杀数量对比柱状图、差错案件行业分布饼图 |
| 3 | 系统自动执行诊断 | 逐条回放规则命中过程，标记每条差错被哪条规则误判 |
| 4 | 查看诊断结果 | 展示：规则级别差错归因表（哪条规则贡献了多少误杀/漏杀）、阈值敏感性分析 |
| 5 | LLM生成优化建议 | 输出具体优化方案："建议将负债率阈值从70%调整至75%，预计减少12条误杀，漏杀增加2条" |
| 6 | 一键应用优化建议 | 修改规则参数后立即执行对比回测，展示新旧策略对比视图 |

**演示要点**：
- 强调从"发现问题"到"定位原因"到"给出方案"的完整诊断链路
- 新旧策略对比是核心亮点，调用compare_strategies()
- 优化建议要具体到阈值数值，不能只给方向

### 场景3：自然语言配策略

**用户故事**：风控运营人员用自然语言描述一条新策略，系统自动转化为可执行规则并即时回测。

**操作流程**：

| 步骤 | 用户操作 | 系统响应 |
|------|---------|---------|
| 1 | 在输入框输入"拒绝负债率超过80%的企业" | LLM解析意图，识别为策略配置场景 |
| 2 | — | LLM调用SYSTEM_RULE_PARSER提示词，生成RuleCondition DSL |
| 3 | 查看生成的规则DSL | 代码块展示：`{"field": "debt_ratio", "operator": ">", "value": 0.8, "action": "reject"}` |
| 4 | 确认规则或修改 | 用户可直接编辑DSL，也可继续用自然语言"再加一条：成立不满1年的也拒绝" |
| 5 | 点击"即时回测" | 用预置100条数据执行回测，展示该规则的通过率/拒绝率/命中分布 |
| 6 | 追加复合条件 | 输入"营收低于500万且负债率高于60%的，标记为高风险" |
| 7 | 查看完整规则集 | 展示包含3条规则的完整RuleSet，含优先级排序 |

**演示要点**：
- 自然语言→DSL的转换是核心卖点，要展示LLM的理解能力
- 支持多轮追加规则，不是一次性生成
- 即时回测体现"配完即测"的敏捷体验

---

## 4. 前端交互设计

### 4.1 页面布局

```
┌──────────────────────────────────────────────────────────────────┐
│  ⚡ 众安信科 · 风控策略运营助手                     [⚙ Settings]  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─ 规则编辑区 ───────────────────────────────────────────────┐ │
│  │                                                            │ │
│  │  ┌─ 对话输入 ──────────────┐  ┌─ 规则DSL展示 ──────────┐ │ │
│  │  │ > 拒绝负债率超过80%的... │  │ {                      │ │ │
│  │  │                         │  │   "rules": [           │ │ │
│  │  │ [预置场景快捷按钮]       │  │     { "field": "...",  │ │ │
│  │  │ [小微回测] [差错诊断]    │  │       "operator": ">", │ │ │
│  │  │ [自然语言配策略]         │  │       "value": 0.8 }   │ │ │
│  │  │                         │  │   ]                    │ │ │
│  │  └─────────────────────────┘  └────────────────────────┘ │ │
│  │                                                            │ │
│  │  [执行回测]  [策略对比]  [导出PDF]                          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─ 数据图表区 ───────────────────────────────────────────────┐ │
│  │                                                            │ │
│  │  ┌─ 通过/拒绝 ─┐ ┌─ 规则命中分布 ─┐ ┌─ KS曲线 ────────┐ │ │
│  │  │    圆环图    │ │    条形图      │ │   折线图         │ │ │
│  │  │  通过: 67%   │ │ 规则1: ██ 23  │ │                  │ │ │
│  │  │  拒绝: 33%   │ │ 规则2: ███ 8  │ │  KS=0.42        │ │ │
│  │  └──────────────┘ │ 规则3: █ 2    │ │                  │ │ │
│  │                    └───────────────┘ └──────────────────┘ │ │
│  │                                                            │ │
│  │  ┌─ LLM分析报告 ──────────────────────────────────────┐  │ │
│  │  │ 策略整体精确率83.2%，召回率76.5%。规则1（负债率>70%）│  │ │
│  │  │ 贡献了69.7%的拒绝量，建议关注该阈值的敏感性...       │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 组件规格

| 组件 | 实现方式 | 规格 |
|------|---------|------|
| 对话输入框 | Gradio Textbox + Button | 支持多轮输入，Enter发送 |
| 预置场景按钮 | Gradio Button x3 | 蓝底白字，hover高亮，点击后自动填入场景数据 |
| 规则DSL展示 | Gradio Code（language="json"） | 只读/可编辑模式切换，语法高亮 |
| 通过/拒绝圆环图 | Plotly Pie（hole=0.5） | 品牌蓝#1677FF + 警告红#FF4D4F |
| 规则命中分布条形图 | Plotly Bar（horizontal） | 按命中数降序排列，每条规则一个色块 |
| KS曲线 | Plotly Line | TPR/FPR双线 + KS值标注线 |
| 混淆矩阵热力图 | Plotly Heatmap | 2x2矩阵，标注TP/FP/TN/FN数值 |
| 新旧策略对比视图 | Gradio Dataframe + Plotly GroupedBar | 双列对比：指标名/旧值/新值/变化量 |
| LLM分析报告 | Gradio Markdown | 流式输出，支持加粗/列表/表格 |
| 导出PDF按钮 | Gradio DownloadButton | 点击后生成含图表的PDF，自动下载 |

### 4.3 交互状态

| 状态 | 视觉表现 |
|------|---------|
| 空闲 | 图表区显示占位图+引导文案"选择预置场景或输入策略描述开始" |
| 加载中 | 图表区显示骨架屏（Skeleton），对话区显示"正在分析..."动画 |
| 回测完成 | 图表区渲染完整图表，LLM分析区流式输出 |
| 对比模式 | 图表区左右分栏，左旧右新，变化指标用红绿色标注 |
| 错误状态 | 红色Toast提示具体错误原因（如"CSV格式异常"），不中断流程 |

---

## 5. 后端架构

### 5.1 模块清单

| 分类 | 模块 | 文件 | 改造动作 |
|------|------|------|---------|
| **保留** | 主Agent | agent.py | 不改。意图检测分流（策略配置/回测/差错分析）保持原有逻辑 |
| **保留** | 规则引擎 | rule_engine.py | 不改。RuleCondition/StrategyRule/RuleSet三层模型 + 8种操作符 + 优先级命中即停 |
| **保留** | 回测引擎 | backtesting.py | 不改。CSV/Excel多编码自动检测加载、数据摘要生成、回测执行 |
| **保留** | 指标计算 | metrics.py | 不改核心逻辑。KS/PSI/混淆矩阵/精确率/召回率/F1算法保留 |
| **保留** | 提示词 | prompts.py | 不改。SYSTEM_RULE_PARSER + SYSTEM_BACKTEST_ANALYSIS + SYSTEM_ERROR_ANALYSIS |
| **改造** | 指标接入 | metrics.py调用层 | 在回测主流程中调用metrics.py的全部指标函数，输出结构化MetricsReport |
| **改造** | 策略对比接入 | backtesting.py调用层 | 在差错诊断流程中调用compare_strategies()，输出ComparisonResult |
| **改造** | 数据加载 | backtesting.py数据层 | 支持从预置mock数据路径自动加载，不强制用户上传 |
| **新建** | 图表生成 | chart_generator.py | 基于Plotly生成6种图表（圆环图/条形图/KS曲线/混淆矩阵/对比图/敏感性图） |
| **新建** | PDF导出 | report_exporter.py | 将图表+LLM分析文本组装为PDF报告 |
| **新建** | Mock数据 | demo_data/agent_riskctrl/ | 预置CSV + 差错数据 + 规则集JSON |

### 5.2 改造详细设计

#### 5.2.1 metrics.py接入回测主流程

**现状**：metrics.py中的`calculate_ks()`、`calculate_psi()`、`confusion_matrix()`、`precision_recall_f1()`四个函数已实现，但回测主流程只返回通过/拒绝计数，未调用这些函数。

**改造方案**：

```
回测执行流程（改造后）：
backtesting.run_backtest()
  → 逐条匹配规则，记录命中结果
  → 生成 predictions[] 和 labels[]
  → 调用 metrics.calculate_ks(predictions, labels) → ks_value
  → 调用 metrics.confusion_matrix(predictions, labels) → cm
  → 调用 metrics.precision_recall_f1(cm) → precision, recall, f1
  → 调用 metrics.calculate_psi(train_dist, test_dist) → psi（仅对比场景）
  → 封装为 MetricsReport 返回
```

**接入点**：在backtesting.py的`run_backtest()`函数返回前，增加metrics调用层。不修改metrics.py内部逻辑。

#### 5.2.2 compare_strategies()接入对比功能

**现状**：backtesting.py中`compare_strategies(rule_set_a, rule_set_b, data)`已实现，接受两个RuleSet和数据集，返回对比结果。但Agent的差错诊断流程中未调用。

**改造方案**：

```
差错诊断流程（改造后）：
agent.handle_error_analysis()
  → 加载差错数据
  → 执行当前策略回测，得到 baseline_result
  → LLM分析差错原因，生成优化建议（含新阈值）
  → 将优化建议转为 new_rule_set
  → 调用 compare_strategies(old_rule_set, new_rule_set, data)
  → 输出 ComparisonResult（含新旧指标对比）
```

**接入点**：在agent.py的差错分析handler中，在LLM生成优化建议后，增加compare_strategies调用。

### 5.3 新建模块设计

#### 5.3.1 chart_generator.py

**职责**：接收结构化数据，生成Plotly图表对象，供前端渲染或PDF导出。

**函数清单**：

| 函数 | 输入 | 输出 | 说明 |
|------|------|------|------|
| `plot_approval_rejection_donut(pass_count, reject_count)` | 通过数、拒绝数 | Plotly Figure | 圆环图，中心显示总数 |
| `plot_rule_hit_distribution(rule_hits: dict)` | 规则名→命中数映射 | Plotly Figure | 水平条形图，按命中数降序 |
| `plot_ks_curve(tpr, fpr, ks_value)` | TPR数组、FPR数组、KS值 | Plotly Figure | 双线+KS标注线 |
| `plot_confusion_matrix(cm: dict)` | TP/FP/TN/FN | Plotly Figure | 2x2热力图 |
| `plot_strategy_comparison(old_metrics, new_metrics)` | 两组指标字典 | Plotly Figure | 分组柱状图，新旧对比 |
| `plot_error_attribution(rule_errors: dict)` | 规则名→误杀/漏杀数 | Plotly Figure | 堆叠条形图 |

**设计约束**：
- 统一配色：品牌蓝#1677FF、通过绿#52C41A、拒绝红#FF4D4F、警告橙#FAAD14
- 所有图表支持`to_html()`和`to_image(format="png")`双输出
- 图表标题、轴标签使用中文

#### 5.3.2 report_exporter.py

**职责**：将回测结果、图表、LLM分析文本组装为可下载的PDF报告。

**报告结构**：

```
风控策略回测报告
├── 1. 报告摘要（策略名称、数据量、回测日期、核心指标一览）
├── 2. 策略规则说明（规则DSL的可读化展示）
├── 3. 回测结果
│   ├── 3.1 通过/拒绝分布（圆环图）
│   ├── 3.2 规则命中分析（条形图 + 明细表）
│   ├── 3.3 模型评估指标（KS曲线 + 混淆矩阵 + 精确率/召回率/F1）
│   └── 3.4 PSI稳定性分析（仅对比场景）
├── 4. AI分析与建议（LLM生成的策略解读）
└── 5. 附录：数据样本摘要
```

**技术选型**：使用`reportlab`或`weasyprint`生成PDF，图表以PNG嵌入。

---

## 6. 数据模型

### 6.1 现有模型（保留）

#### RuleCondition

```
RuleCondition:
  field: str          # 字段名，如"debt_ratio"
  operator: str       # 操作符，8种：>, <, >=, <=, ==, !=, in, not_in
  value: Any          # 阈值
```

#### StrategyRule

```
StrategyRule:
  name: str           # 规则名称，如"高负债率拒绝"
  conditions: list[RuleCondition]   # 条件列表（AND关系）
  action: str         # 动作：reject / approve / review
  priority: int       # 优先级，数值越小优先级越高
```

#### RuleSet

```
RuleSet:
  name: str           # 策略集名称
  rules: list[StrategyRule]   # 规则列表，按priority排序，命中即停
  version: str        # 版本号
  description: str    # 策略描述
```

### 6.2 新增模型

#### MetricsReport

```
MetricsReport:
  total_samples: int          # 总样本数
  pass_count: int             # 通过数
  reject_count: int           # 拒绝数
  pass_rate: float            # 通过率
  reject_rate: float          # 拒绝率
  rule_hits: dict[str, int]   # 规则名→命中数
  ks_value: float             # KS值
  precision: float            # 精确率
  recall: float               # 召回率
  f1_score: float             # F1分数
  confusion_matrix: dict      # {"TP": int, "FP": int, "TN": int, "FN": int}
  psi_value: float | None     # PSI值（仅对比场景有值）
```

#### ComparisonResult

```
ComparisonResult:
  old_metrics: MetricsReport  # 旧策略指标
  new_metrics: MetricsReport  # 新策略指标
  delta: dict[str, float]     # 指标变化量：{"pass_rate": +0.05, "precision": -0.02, ...}
  improved_metrics: list[str] # 改善的指标名列表
  degraded_metrics: list[str] # 恶化的指标名列表
```

#### BacktestReport（PDF导出用）

```
BacktestReport:
  report_id: str              # 报告唯一ID
  generated_at: datetime      # 生成时间
  strategy: RuleSet           # 使用的策略
  data_summary: dict          # 数据集摘要（行数、字段、分布）
  metrics: MetricsReport      # 回测指标
  comparison: ComparisonResult | None  # 对比结果（可选）
  llm_analysis: str           # LLM生成的分析文本
  charts: dict[str, bytes]    # 图表名→PNG字节
```

---

## 7. LLM调用设计

本Agent共4个LLM调用点，均使用DeepSeek/Kimi等已接入模型。

### 调用点1：意图检测与分流

| 项目 | 内容 |
|------|------|
| 触发时机 | 用户输入任意自然语言 |
| 提示词 | agent.py中的意图识别prompt |
| 输入 | 用户输入文本 |
| 输出 | 意图分类：`strategy_config` / `backtest` / `error_analysis` |
| 期望延迟 | <2秒 |
| 缓存策略 | 预置场景的意图识别结果可硬编码，跳过LLM调用 |

### 调用点2：自然语言→规则DSL

| 项目 | 内容 |
|------|------|
| 触发时机 | 意图检测为`strategy_config`时 |
| 提示词 | prompts.py中的SYSTEM_RULE_PARSER |
| 输入 | 用户策略描述文本 + 可用字段列表 |
| 输出 | 结构化JSON：RuleCondition/StrategyRule格式 |
| 期望延迟 | <3秒 |
| 关键约束 | 必须输出合法的RuleCondition JSON，operator必须在8种之内 |
| 容错 | JSON解析失败时重试1次，仍失败则展示原文并提示用户手动调整 |

### 调用点3：回测结果分析

| 项目 | 内容 |
|------|------|
| 触发时机 | 回测执行完成，MetricsReport生成后 |
| 提示词 | prompts.py中的SYSTEM_BACKTEST_ANALYSIS |
| 输入 | MetricsReport JSON + 规则集描述 + 数据摘要 |
| 输出 | Markdown格式分析报告（500-800字） |
| 期望延迟 | <5秒（流式输出） |
| 输出要求 | 必须包含：指标解读、策略松紧判断、具体优化建议（含数值） |

### 调用点4：差错诊断与优化建议

| 项目 | 内容 |
|------|------|
| 触发时机 | 差错数据加载并完成归因分析后 |
| 提示词 | prompts.py中的SYSTEM_ERROR_ANALYSIS |
| 输入 | 差错归因表 + 原规则集 + 差错案件样本 |
| 输出 | 诊断报告 + 优化后的RuleSet JSON |
| 期望延迟 | <5秒（流式输出） |
| 关键约束 | 优化建议必须输出可执行的新RuleSet（用于compare_strategies调用），不能只给文字建议 |

---

## 8. Mock数据规格

### 8.1 授信数据CSV（100条）

**文件**：`demo_data/agent_riskctrl/scenario_backtest/input/credit_data.csv`

**字段规格**：

| 字段名 | 中文名 | 类型 | 取值范围 | 分布 |
|--------|-------|------|---------|------|
| enterprise_id | 企业ID | string | ENT_001 ~ ENT_100 | 唯一 |
| enterprise_name | 企业名称 | string | XX有限公司 | 随机生成，含行业关键词 |
| industry | 行业 | string | 制造业/批发零售/科技服务/建筑/餐饮 | 制造业40%、批发零售25%、科技15%、建筑12%、餐饮8% |
| registered_capital | 注册资本（万元） | float | 10 ~ 5000 | 对数正态分布，中位数200万 |
| debt_ratio | 资产负债率 | float | 0.15 ~ 0.95 | 正态分布，均值0.55，标准差0.15 |
| annual_revenue | 年营收（万元） | float | 50 ~ 20000 | 对数正态分布，中位数800万 |
| years_established | 成立年限 | int | 0 ~ 25 | 右偏分布，均值5年 |
| employee_count | 员工数 | int | 5 ~ 500 | 对数正态分布，中位数30人 |
| has_mortgage | 有无抵押物 | bool | true/false | 40% true |
| credit_score | 内部信用评分 | int | 300 ~ 900 | 正态分布，均值650 |
| result_label | 结果标签 | string | good/bad | good 75%、bad 25%（模拟真实违约率） |

**数据质量要求**：
- 字段间存在合理相关性（如高负债率的企业credit_score偏低）
- bad标签的企业在debt_ratio、years_established等维度有统计学显著差异
- 保证KS值在0.3-0.5之间（模拟中等区分度的真实场景）

### 8.2 差错案件数据（50条）

**文件**：`demo_data/agent_riskctrl/scenario_error/input/error_cases.csv`

**字段规格**：

| 字段名 | 中文名 | 类型 | 说明 |
|--------|-------|------|------|
| case_id | 案件ID | string | ERR_001 ~ ERR_050 |
| enterprise_name | 企业名称 | string | 与授信数据命名风格一致 |
| industry | 行业 | string | 同上 |
| debt_ratio | 资产负债率 | float | 差错案件的实际值 |
| annual_revenue | 年营收（万元） | float | 差错案件的实际值 |
| years_established | 成立年限 | int | 差错案件的实际值 |
| rule_triggered | 触发规则 | string | 导致误判的规则名 |
| model_decision | 模型决策 | string | reject/approve |
| actual_result | 实际结果 | string | good/bad |
| error_type | 差错类型 | string | false_positive（误杀）/ false_negative（漏杀） |
| error_reason | 差错原因 | string | 可读文本，如"负债率71%仅略超阈值70%，实际经营正常" |

**数据分布**：
- 误杀（false_positive）30条：主要由负债率阈值过严导致（18条）、注册资本阈值过严（8条）、年限阈值过严（4条）
- 漏杀（false_negative）20条：主要由单一规则覆盖不足导致（如高营收掩盖了高负债）

### 8.3 预置规则集JSON

**文件**：`demo_data/agent_riskctrl/scenario_backtest/input/preset_rules.json`

```
{
  "name": "小微信用贷准入策略v1",
  "version": "1.0",
  "description": "适用于小微企业信用贷款的基础准入规则集",
  "rules": [
    {
      "name": "高负债率拒绝",
      "conditions": [{"field": "debt_ratio", "operator": ">", "value": 0.7}],
      "action": "reject",
      "priority": 1
    },
    {
      "name": "注册资本不足拒绝",
      "conditions": [{"field": "registered_capital", "operator": "<", "value": 50}],
      "action": "reject",
      "priority": 2
    },
    {
      "name": "新设企业拒绝",
      "conditions": [{"field": "years_established", "operator": "<", "value": 2}],
      "action": "reject",
      "priority": 3
    }
  ]
}
```

### 8.4 场景配置文件

**文件**：`demo_data/agent_riskctrl/scenario_backtest/scenario.json`

```
{
  "scenario_id": "riskctrl_backtest_01",
  "name": "小微信用贷策略回测",
  "description": "使用100条小微企业授信数据，评估基础准入策略的效果",
  "input_files": {
    "data": "input/credit_data.csv",
    "rules": "input/preset_rules.json"
  },
  "auto_run": true,
  "expected_highlights": [
    "通过率约65-70%",
    "规则1（高负债率）命中最多",
    "KS值约0.35-0.45",
    "精确率>80%"
  ]
}
```

---

## 9. 与其他Agent的数据接口

### 9.1 数据消费（入方向）

| 来源Agent | 数据对象 | 用途 | 接口格式 |
|-----------|---------|------|---------|
| 报告生成助手（Agent6） | 财务锚点 | 获取企业真实财务指标（资产负债率、营收等），用于策略回测的真实数据补充 | JSON：`{"debt_ratio": 0.65, "annual_revenue": 1200, ...}` |
| 授信决策辅助（Agent3） | 风险标签集 | 获取企业风险等级和标签，作为策略规则的参考维度 | JSON：`{"risk_level": "medium", "tags": ["industry_concentration", "short_history"]}` |

### 9.2 数据生产（出方向）

| 消费Agent | 数据对象 | 内容 | 接口格式 |
|-----------|---------|------|---------|
| 授信决策辅助（Agent3） | 策略命中结果 | 该企业是否命中拒绝规则、命中了哪条、风控建议 | JSON：`{"hit": true, "triggered_rules": ["高负债率拒绝"], "suggestion": "建议人工复核"}` |
| 贷中风险预警（Agent4） | 策略阈值配置 | 当前生效的规则集，供预警模块判断企业是否接近触发阈值 | JSON：RuleSet格式 |
| 合规巡检（Agent5） | 策略变更记录 | 规则修改历史，供合规模块审计策略变更是否经过审批 | JSON：`{"change_id": "CHG_001", "old_rule": {...}, "new_rule": {...}, "changed_at": "...", "reason": "..."}` |

### 9.3 Demo阶段实现方式

Demo阶段不做实时Agent间调用，采用预置JSON文件模拟：
- 入方向：在mock数据中内嵌来自其他Agent的预置数据
- 出方向：输出结构化JSON到`outputs/`目录，供其他Agent的Demo场景读取
- 未来接通：预留`AgentBus`接口，方法签名已定义但内部走本地文件读写

---

## 10. 验收标准

### 10.1 功能验收

| # | 验收项 | 验收条件 | 优先级 |
|---|-------|---------|-------|
| F1 | 预置场景加载 | 点击3个预置场景按钮，数据在2秒内加载完成，规则DSL正确展示 | P0 |
| F2 | 回测执行 | 100条数据回测在3秒内完成，返回完整MetricsReport | P0 |
| F3 | 指标计算完整性 | 回测结果包含KS/精确率/召回率/F1/混淆矩阵全部指标 | P0 |
| F4 | 圆环图渲染 | 通过率/拒绝率圆环图正确显示，数值与回测结果一致 | P0 |
| F5 | 规则命中条形图 | 展示每条规则的命中数量，按降序排列 | P0 |
| F6 | KS曲线 | TPR/FPR双线正确绑定，KS值标注位置准确 | P0 |
| F7 | 混淆矩阵热力图 | 4格数值之和等于总样本数 | P1 |
| F8 | LLM分析报告 | 流式输出，包含指标解读和具体优化建议 | P0 |
| F9 | 自然语言配策略 | 输入"拒绝负债率>80%的企业"，3秒内生成合法RuleCondition JSON | P0 |
| F10 | 多轮规则追加 | 连续输入3条规则描述，累积生成完整RuleSet | P1 |
| F11 | 差错诊断 | 加载差错数据后，正确归因到具体规则，误杀/漏杀分类准确 | P0 |
| F12 | 策略对比 | 新旧策略对比视图展示，指标变化量计算正确 | P0 |
| F13 | PDF导出 | 导出报告包含所有图表和分析文本，格式整齐可读 | P1 |
| F14 | 自定义数据上传 | 用户可上传自有CSV替代预置数据，格式校验通过后正常回测 | P2 |

### 10.2 性能验收

| # | 验收项 | 验收条件 |
|---|-------|---------|
| P1 | 回测速度 | 100条数据 + 3条规则，回测完成 < 3秒 |
| P2 | 图表渲染 | 全部6种图表渲染完成 < 2秒 |
| P3 | LLM响应 | 首token < 2秒，完整输出 < 8秒 |
| P4 | PDF生成 | 完整报告PDF生成 < 5秒 |
| P5 | 页面加载 | 首次打开页面 < 3秒 |

### 10.3 体验验收

| # | 验收项 | 验收条件 |
|---|-------|---------|
| E1 | 零配置演示 | 演示者打开页面后，无需配置API Key或上传文件即可完成3个场景演示 |
| E2 | 视觉一致性 | 配色方案统一使用品牌色，图表风格一致 |
| E3 | 错误提示 | 任何异常都有中文友好提示，不出现英文堆栈或空白页 |
| E4 | 流式体验 | LLM输出为逐字流式展示，回测过程有进度指示 |
| E5 | 演示连贯性 | 3个场景按顺序演示，场景间状态不冲突，无需刷新页面 |

---

## 附录

### A. 术语表

| 术语 | 含义 |
|------|------|
| DSL | Domain Specific Language，领域特定语言，此处指规则描述的JSON格式 |
| KS值 | Kolmogorov-Smirnov统计量，衡量模型/规则区分好坏客户的能力，0-1之间，越大越好 |
| PSI | Population Stability Index，群体稳定性指标，衡量策略在不同数据集上的稳定性 |
| 误杀 | False Positive，好客户被错误拒绝 |
| 漏杀 | False Negative，坏客户被错误通过 |
| 命中即停 | 规则按优先级排序，一旦命中某条规则即执行其动作，不再继续匹配后续规则 |

### B. 相关文档

- PRD_客户经理个人助手_v3.0.md — 矩阵整体PRD
- PRD_报告生成助手_v2.1.md — Agent6详细PRD
- 改造方案_信贷AI智能体矩阵_v1.0.md — 技术改造方案
