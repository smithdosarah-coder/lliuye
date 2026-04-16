# PRD：贷中风险预警助手 v2.0（知识库扫描雷达重构版）

**版本**：v2.0（完全替换 v1.0）
**日期**：2026-04-14
**作者**：刘野（众安信科 AI 中台 / 乾策平台产品负责人）
**文档性质**：子 Agent 产品需求文档（面向 Demo 交付 + 生产线落地）
**所属平台**：众安信科 · 乾策平台（X-Nexus）
**所属矩阵**：信贷 AI 智能体矩阵 — Agent #4
**架构共性**：本 PRD 与 Agent #1（全渠道流量匹配）、Agent #5（合规巡检）共用同一套「**知识库扫描范式**」，**接口定义、数据流协议、通用模块清单见《共享架构_知识库扫描范式_v1.0.md》**，本文档只描述 Agent4 特有的部分。

---

## 0. 背景：为什么要重写 v1.0

### 0.1 v1.0 的致命问题

v1.0 设计为「单企业深度分析工具」：客户输入一个企业名 → 搜索舆情 → 规则打分 → 红黄绿信号灯 → 输出处置建议。

**演示中客户一眼看穿**：
- 这就是一个「企查查 + GPT 摘要」的套壳工具，我自己能做
- 我要的不是查一家企业，是**管理 1 万家在贷客户的风险组合**
- 你这个工具一次只能看一家，我一个贷后岗每天要看 200 家，你这东西解决不了我的核心痛点
- 而且你的「信号灯动画」是装饰，不是产品逻辑——去掉这个 UI，你的价值在哪？

**产品定位错误的本质**：v1.0 把工具逻辑（单查）伪装成了雷达逻辑（批量扫描），但前端、后端、数据模型全都是单查的骨架。演示时客户看一家→看两家→问「能一次扫完我 1 万家吗」→产品哑火。

### 0.2 v2.0 的根本转变

| 维度 | v1.0（错） | v2.0（对） |
|------|-----------|-----------|
| 输入单位 | 单企业名 | 知识库（全量在贷客户名录 + 规则库 + 管理制度） |
| 核心动作 | 一次查一家 | 批量遍历 + 双路交叉命中 |
| 输出形态 | 单企业预警报告 | 分级榜单（红 N 家 / 黄 N 家 / 绿 N 家） + 单客户详情切换 |
| 视觉主体 | 红黄绿信号灯动画 | 分级榜单 + 客户详情 + 处置建议卡片 |
| 用户场景 | 贷后岗抽查某家客户 | 贷后岗每日晨会批量扫描全组合 / 风险委员会月度组合体检 |
| 产品隐喻 | 体检报告 | 雷达屏 |

**一句话重定位**：v2.0 是**知识库驱动的批量贷中预警扫描雷达**，客户上传「在贷客户池 + 预警规则库 + 内部制度」三份知识库，Agent 自动批量扫完，吐出分级榜单。

### 0.3 与 Agent1 / Agent5 的共性

三个 Agent 共用一套「知识库扫描范式」：

```
KnowledgeBase（客户上传的锚）
      ↓
RuleExtractor（规则/事件抽取器，LLM 驱动）
      ↓
ScanTargets（扫描目标集合）
      ↓
Matcher（外部信号 × 内部规则 交叉匹配）
      ↓
HitList（命中清单 → 分级榜单）
```

**共享接口**：`SearchProvider` / `KnowledgeBase` / `RuleExtractor` / `Matcher` — **定义和实现规范见《共享架构_知识库扫描范式_v1.0.md》**，本 PRD 不重复定义。

**一致的前端雷达范式**：分级榜单（左） + 客户详情切换（中） + 处置建议卡片（右） + 顶部统计条。

---

## 1. 产品定位

### 1.1 一句话定位

**知识库驱动的批量贷中预警扫描雷达**——上传在贷客户池，Agent 批量扫完并分级，揪出红灯客户给出处置建议。

### 1.2 与 v1.0 的差异对照

| 项 | v1.0 保留 | v1.0 重写 | v2.0 新建 |
|----|----------|----------|----------|
| `alert_engine.py`（22 条规则 + 红黄绿分级） | ✅ 保留（单客户评估内核） | — | — |
| `disposition.py`（LLM + 模板处置建议） | ✅ 保留（批量调用时复用） | — | — |
| `trend_analyzer.py`（财务趋势） | ✅ 保留（可选补充信号） | — | — |
| `prompts.py`（SYSTEM_RISK_SCAN / SYSTEM_TREND / SYSTEM_DISPOSITION） | ✅ 保留，新增批量专用 Prompt | — | — |
| `agent.py` | — | 🔁 重写为批量编排器 | — |
| `app_demo.py`（Gradio 前端） | — | 🔁 重写为雷达 UI | — |
| `customer_scanner.py`（批量扫描引擎） | — | — | 🆕 新建 |
| `rule_extractor.py`（管理制度 → 结构化规则） | — | — | 🆕 新建（共享接口 `RuleExtractor` 的 Agent4 实现） |
| `cross_matcher.py`（外部信号 × 内部规则交叉命中） | — | — | 🆕 新建 |
| `knowledge_base.py`（KB 装配器） | — | — | 🆕 新建（共享接口 `KnowledgeBase` 的 Agent4 实现） |
| `ledger_exporter.py`（榜单 Excel 导出） | — | — | 🆕 新建 |
| `mock_data/`（100 家客户 + 规则库 + 制度 mock） | — | — | 🆕 新建 |

### 1.3 差异化视觉

v1.0 的红黄绿信号灯动画**退场**——它是单客户场景的产物，和雷达场景不匹配。v2.0 的视觉主体是「**分级榜单**」，具体差异化元素见第 4 章。

### 1.4 目标用户

| 用户 | 场景 | 价值 |
|------|------|------|
| 银行贷后管理岗 | 每日晨会，批量扫描分管组合的风险变化 | 把「抽查式贷后」升级为「全量雷达式贷后」 |
| 分行风险委员会 | 月度/季度风险组合体检 | 输出红黄绿榜单，用于会议决策与处置分派 |
| 总行风险管理部 | 对全行组合做专项扫描（如供应链贷款、小微贷款分池） | 用知识库直接切分池扫描，不用逐笔查 |
| 金融科技子公司 | 对合作机构放贷组合做回溯风险扫描 | 快速生成处置清单交付合作方 |

### 1.5 核心价值主张

- **从「一户一查」到「全池一扫」**：100 家客户 2 分钟内扫完，传统人工需 3-5 个工作日。
- **双路命中**：外部路径（裁判文书 / 工商 / 舆情 / 失信）× 内部路径（本行制度 / 限额 / 白黑名单）交叉确认，避免单路径噪声误报。
- **处置直达**：不止发现风险，每条红灯直接给出可执行处置建议（紧急度 + 责任方 + 时限）。
- **证据链可追溯**：每个命中都能追溯到原始数据（某条判决书 / 某条工商记录 / 某条制度条款），客户经理可直接凭证走流程。

---

## 2. Demo 目标

### 2.1 演示目标

| 维度 | 目标 |
|------|------|
| 演示时长 | 单场景 4-6 分钟，双场景完整演示 10-12 分钟 |
| 演示对象 | 银行风险管理部负责人、贷后管理岗、分行行长、总行科技部 |
| 证明什么 | AI 可对整个在贷客户池做**批量并发**风险扫描，输出可直接上会的分级榜单 + 处置清单 |
| 核心展示 | 扫描进度条 + 榜单实时刷新 + 红灯客户详情切换 + 处置建议卡片 + Excel 榜单导出 |
| 预置场景 | 2 个，覆盖小微信贷组合和供应链贷款组合 |
| 导出能力 | 分级榜单一键导出 Excel，单客户详情一键导出 PDF |
| 体验标准 | 100 家客户扫描 ≤ 2 分钟，实时进度可见，过程中已扫出的红灯立刻出现在榜单 |

### 2.2 反「伪雷达」体验硬指标（客户识别度）

客户演示中判定「这是真雷达」的 3 条硬线：
1. **上传的必须是知识库（多文件多类型）**，不是一个企业名或一个文件。
2. **扫描过程必须有批量并发观感**：进度条动、tick 刷、榜单实时增长。
3. **输出必须是榜单形态**，且客户可以在榜单里切换不同客户看不同证据链——这件事单查工具做不到。

---

## 3. 演示场景设计

### 3.1 场景 1：「小微信贷组合体检」（红灯场景）

**业务背景**：某城商行小微信贷事业部，管理 100 家小微企业授信客户（授信余额 5000 万 - 3000 万/家），贷后岗每日需上会汇报异动。

**用户操作**：
1. 打开 Agent4，左侧场景卡片点击「小微信贷组合体检」，自动加载知识库。
2. 界面中部显示 KB 概览：「100 家在贷客户 · 20 条预警规则 · 1 份本行小微信贷风险管理办法（4200 字）」。
3. 点击「开始扫描」，进度条启动：`已扫 0 / 100`。
4. 进度滚动过程中，榜单左栏实时出现红灯/黄灯客户条目，顶部统计 `🔴 0 → 1 → 2 → 3`。
5. 约 1 分 40 秒扫完，弹出完成提示。

**扫描结果（预设）**：
- 🔴 红灯：3 家
- 🟡 黄灯：7 家
- 🟢 绿灯：90 家

**红灯样例客户详情**（点击榜单条目切换）：

```
【华联精密制造有限公司】授信余额 3200 万 / 贷款到期 2026-06
─────────────────────────────
命中等级：🔴 红
命中规则（交叉 3 条）：
  [外部 × FIN-002] 净利润转负（财报显示 2025Q4 亏损 680 万）
  [外部 × LAW-001] 涉诉 1200 万（中国裁判文书网 2025-11）
  [内部 × POL-003] 触发本行《小微信贷风险管理办法》第 14 条——
                  关联方重整触发强制预警线（主要客户占营收 35% 进入重整）

证据链：
  · 外部信号 1：企业 2025Q4 财报利润表截图 / 链接
  · 外部信号 2：裁判文书 (2025) 沪 0115 民初 12345 号
  · 内部命中 3：本行制度 Art.14 原文引用
  · 舆情补充：财经媒体 2025-11-15 报道「华联精密核心客户流失」

处置建议：
  [紧急] 48h 内现场核查经营状况   责任方：客户经理
  [紧急] 启动诉讼资产保全评估     责任方：法务部
  [高优] 要求追加抵押物           责任方：客户经理
  [常规] 下调内评为关注类         责任方：风险管理部
```

### 3.2 场景 2：「供应链贷款组合体检」（黄灯为主场景）

**业务背景**：某股份制银行供应链金融部，对某汽车主机厂上下游 100 家供应商提供应收账款融资。

**差异点**：
- 行业集中度高（全在汽车零部件行业），需关注**行业下行信号**。
- 核心企业（主机厂）动向对整个组合有传染性风险。
- 规则库中追加 `IND-001 行业景气下行` / `REL-003 核心企业动向` 两条专属规则。

**扫描结果（预设）**：
- 🔴 红灯：1 家（已发生诉讼）
- 🟡 黄灯：12 家（行业景气下行 + 应收账款周转恶化叠加）
- 🟢 绿灯：87 家

**黄灯样例客户详情**：

```
【恒达汽配有限公司】授信余额 800 万 / 应收账款池 1500 万
─────────────────────────────
命中等级：🟡 黄
命中规则（交叉 2 条）：
  [外部 × FIN-003] 应收账款周转天数从 45 天升至 78 天
  [内部 × POL-007] 触发本行供应链金融制度第 9 条——
                  核心企业产销同比下降 20% 需全量体检关联供应商

证据链：
  · 外部信号 1：2025 年报应收账款周转率
  · 内部命中 2：本行制度 Art.9 原文引用
  · 行业补充：中汽协 2026-01 乘用车销量数据

处置建议：
  [高优] 约谈恒达核实主要客户结构       责任方：客户经理
  [高优] 评估保理池应收账款真实性       责任方：风险管理部
  [常规] 贷后检查频率由季度调整为月度   责任方：客户经理
```

### 3.3 两场景对比要点（演示脚本）

| 维度 | 场景 1 | 场景 2 |
|------|--------|--------|
| 命中模式 | 单客户多路径叠加 | 全池同一风险因子传染 |
| 规则库特色 | 通用 20 条 | 通用 20 条 + 供应链专属 2 条 |
| 内部制度文档 | 小微信贷风险管理办法 | 供应链金融业务管理制度 |
| 主打卖点 | 红灯深度 + 处置建议精准度 | 组合视角 + 行业风险传染识别 |

---

## 4. 前端交互设计

### 4.1 整体布局（雷达屏范式）

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 顶部导航：[Portal]  贷中风险预警雷达  [场景切换]  [Settings]           │
├──────────────────────────────────────────────────────────────────────────┤
│ 顶部统计条：                                                             │
│   本次扫描 100 家 · 🔴 3  🟡 7  🟢 90   · 扫描用时 01:42 · [导出榜单]   │
├──────────────────────────────────────────────────────────────────────────┤
│ 上传区（未扫描时显示 / 扫描后折叠为缩略条）：                            │
│   [📁 客户名录.xlsx]  [📁 预警规则库.json]  [📁 本行制度.pdf]           │
│   [场景 1] [场景 2] [自定义上传]    [▶ 开始扫描]                         │
├──────────────────────────────────────────────────────────────────────────┤
│ 扫描中区域：                                                             │
│   进度条 ▓▓▓▓▓▓▓▓░░░░░░░░ 63 / 100                                       │
│   实时 tick 流：                                                         │
│     [01:15] 🔴 华联精密制造 命中 FIN-002 / LAW-001 / POL-003             │
│     [01:08] 🟡 瑞丰五金 命中 FIN-003 / BIZ-001                           │
│     [00:52] 🟡 恒达汽配 命中 FIN-003 / POL-007                           │
├──────────────────────────────────────────────────────────────────────────┤
│ ┌── 左：分级榜单 ──┬── 中：客户详情 ──┬── 右：处置建议卡片 ──┐          │
│ │ 🔴 高风险 (3)   │  华联精密制造    │  [紧急] 48h 核查       │          │
│ │   · 华联精密 🔥 │  授信 3200 万    │  [紧急] 诉讼保全评估   │          │
│ │   · 兴业通达    │  贷款到期 26-06  │  [高优] 追加抵押物     │          │
│ │   · 德昌五金    │                  │  [常规] 下调内评       │          │
│ │                 │  命中规则：      │                        │          │
│ │ 🟡 中风险 (7)   │  [外×FIN-002]    │  责任分派：            │          │
│ │   · 恒达汽配    │  [外×LAW-001]    │  · 客户经理            │          │
│ │   · 瑞丰五金    │  [内×POL-003]    │  · 法务部              │          │
│ │   · ...（7）    │                  │  · 风险管理部          │          │
│ │                 │  证据链（可展开）│                        │          │
│ │ 🟢 低风险 (90)▶ │  ...             │  [导出处置单 PDF]      │          │
│ │ （默认折叠）    │                  │                        │          │
│ └─────────────────┴──────────────────┴────────────────────────┘          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 4.2 上传区（知识库多文件上传）

| 元素 | 说明 |
|------|------|
| 三槽位分区上传 | 「客户名录」/「预警规则库」/「内部制度」三槽位，每槽位可拖拽多文件 |
| 文件识别提示 | 每个上传槽位显示识别预览：「100 家客户 · 12 个字段」「20 条规则 · 6 类别」「4200 字制度 · 推测抽出 15 条规则」 |
| 场景快捷按钮 | 两个 Demo 场景按钮，一键加载预置 KB |
| 状态标示 | 每槽位：未上传（灰）/ 解析中（蓝旋转）/ 就绪（绿 ✓） |
| 开始按钮 | 三槽就绪后「▶ 开始扫描」变亮 |

### 4.3 扫描中区域（动态实时感）

| 元素 | 说明 |
|------|------|
| 进度条 | `已扫 X / Y`，百分比 + 预计剩余时间 |
| 当前阶段文字 | 「正在扫描第 X 家：某某公司（调用外部搜索 / 匹配内部规则）」 |
| 实时 tick 流 | 发现命中时在流区插入一条（时间戳 + 企业名 + 命中等级 + 命中规则 ID） |
| 滚动条自动追尾 | 新 tick 自动滚入视窗 |
| 取消按钮 | 扫描中可中止，保留已扫描结果 |

### 4.4 结果页 - 左侧分级榜单

| 元素 | 说明 |
|------|------|
| 三段分组 | 🔴 高风险 / 🟡 中风险 / 🟢 低风险，默认红黄展开、绿折叠 |
| 条目设计 | 企业名 + 授信额 + 命中规则数 + 最高级别图标 |
| 排序 | 默认按「命中规则数 × 级别权重」综合排序，支持切换为按授信余额排序 |
| 搜索过滤 | 顶部搜索框，支持企业名模糊搜索 |
| 多选批量 | 支持勾选批量导出部分条目 |
| 选中联动 | 点击条目 → 中间客户详情切换 → 右侧处置建议刷新 |

### 4.5 结果页 - 中间客户详情

| 区块 | 说明 |
|------|------|
| 客户画像卡 | 企业名、统一社会信用代码、授信额、贷款余额、到期日、客户经理 |
| 命中规则清单 | 按「外部信号」「内部规则」分组展示，每条：规则 ID / 规则名 / 证据摘要 / 级别图标 |
| 证据链区块 | 可折叠展开，展示原始证据：搜索命中的判决书 URL / 工商变更原文 / 舆情 URL / 制度条款原文 |
| 趋势小图 | （可选）财务指标趋势迷你图（复用 trend_analyzer） |
| 双路来源标注 | 每条证据标明来自「外部 SearchProvider」还是「内部 RuleMatcher」 |

### 4.6 结果页 - 右侧处置建议卡片

| 元素 | 说明 |
|------|------|
| 建议卡片列表 | 每条建议一张卡片（紧急度标签 + 行动描述 + 责任方 + 时限） |
| 紧急度配色 | `[紧急]` 红底 / `[高优]` 橙底 / `[常规]` 灰底 |
| 责任方标签 | 客户经理 / 风险管理部 / 法务部 / 合规部 |
| 勾选状态 | 支持勾选「已执行」「已忽略」，仅前端状态（Demo 用） |
| 导出按钮 | 「导出处置单 PDF」按钮，生成单客户处置建议 PDF |

### 4.7 顶部统计条 & 导出

| 元素 | 说明 |
|------|------|
| 扫描总数 | 本次扫描 N 家，用时 MM:SS |
| 分级统计 | 🔴 X  🟡 Y  🟢 Z |
| 导出榜单 | 一键导出全部榜单 Excel（含每家命中规则、处置建议） |
| 重新扫描 | 清空结果，回到上传区 |

### 4.8 Gradio 组件映射

| 功能区 | Gradio 组件 |
|--------|------------|
| 上传槽位 | `gr.File(file_count="multiple")` × 3 + 文件识别提示 `gr.HTML` |
| 场景按钮 | `gr.Button` × 2 |
| 进度条 | `gr.HTML`（自定义进度动画） |
| Tick 流 | `gr.HTML`（append 模式） |
| 分级榜单 | `gr.HTML`（自定义卡片列表，支持 click 事件回调） |
| 客户详情 | `gr.HTML` + `gr.Accordion`（证据链折叠） |
| 处置建议卡片 | `gr.HTML`（支持勾选状态） |
| 导出 | `gr.Button` + `gr.File`（下载） |

---

## 5. 后端架构

### 5.1 模块总览

```
agent_alert/
├── agent.py                 # 🔁 AlertMonitorAgent → AlertRadarAgent（重写）
├── alert_engine.py          # ✅ 保留：单客户规则引擎 + AlertSignal/AlertReport
├── disposition.py           # ✅ 保留：单客户处置建议（批量调用复用）
├── trend_analyzer.py        # ✅ 保留：财务趋势（可选补充）
├── prompts.py               # ✅ 保留 + 追加批量专用 Prompt
├── app_demo.py              # 🔁 重写：雷达 UI
├── knowledge_base.py        # 🆕 Agent4 的 KnowledgeBase 实现
├── rule_extractor.py        # 🆕 管理制度 → 结构化规则
├── customer_scanner.py      # 🆕 批量扫描编排引擎（核心）
├── cross_matcher.py         # 🆕 外部信号 × 内部规则 交叉命中
├── ledger_exporter.py       # 🆕 分级榜单 Excel/PDF 导出
└── mock_data/
    ├── scenario_micro_credit/    # 场景 1 预置 KB
    │   ├── customers.xlsx        # 100 家小微客户
    │   ├── rules.json            # 20 条预警规则
    │   └── policy.md             # 本行小微信贷风险管理办法
    ├── scenario_supply_chain/    # 场景 2 预置 KB
    │   ├── customers.xlsx
    │   ├── rules.json
    │   └── policy.md
    └── cache/                    # 预扫描 LLM 响应缓存（演示秒出用）
```

**共享架构引用**：
- `knowledge_base.py` 实现《共享架构》中 `KnowledgeBase` 接口。
- `rule_extractor.py` 实现 `RuleExtractor` 接口。
- `cross_matcher.py` 实现 `Matcher` 接口（双路命中版本）。
- 外部信号统一走 `shared/search_provider.py` 的 `SearchProvider`（Demo 阶段用 `MockProvider`，生产可切 `TianyanchaProvider` / `BaiduNewsProvider` 等）。

### 5.2 核心新建模块

#### 5.2.1 `knowledge_base.py` — 客户知识库装配器

```python
class AlertKnowledgeBase(KnowledgeBase):
    """贷中预警 Agent 的知识库装配器

    实现《共享架构》的 KnowledgeBase 接口，针对贷中场景装配：
    - customers: list[CustomerRecord]   # 在贷客户名录（Excel/CSV 解析）
    - rules:     list[AlertRule]        # 预警规则（JSON / YAML / Excel）
    - policies:  list[PolicyClause]     # 内部管理制度（Word/PDF → LLM 抽取）
    """

    @classmethod
    def from_uploads(cls,
                     customer_files: list[str],
                     rule_files: list[str],
                     policy_files: list[str]) -> 'AlertKnowledgeBase': ...

    @classmethod
    def from_scenario(cls, scenario_id: str) -> 'AlertKnowledgeBase': ...

    def summary(self) -> str:
        """供前端展示的知识库概览文本"""
        return f"{len(self.customers)} 家在贷客户 · {len(self.rules)} 条规则 · {len(self.policies)} 条内部条款"
```

**数据模型（Pydantic）**：

```python
class CustomerRecord(BaseModel):
    customer_id: str
    name: str
    credit_line: float              # 授信额度（万元）
    outstanding: float              # 贷款余额
    due_date: str                   # 贷款到期日
    industry: str
    region: str
    manager: str                    # 客户经理
    internal_rating: str            # 内评
    extras: dict[str, Any] = {}     # 行业特定字段

class AlertRule(BaseModel):          # 复用 / 扩展自 alert_engine.ALERT_RULES
    rule_id: str                     # FIN-001 / LAW-001 / POL-003 等
    category: str                    # 财务恶化 / 法律诉讼 / 内部制度 / ...
    trigger: str                     # 自然语言触发条件
    threshold: dict[str, Any]        # 阈值参数
    level: str                       # red/yellow

class PolicyClause(BaseModel):       # 从内部制度 Word/PDF 抽出
    clause_id: str                   # POL-003 / POL-007 等
    article_no: str                  # 第 14 条
    condition: str                   # 自然语言触发条件
    consequence: str                 # 该条款规定的后果/动作
    source_document: str
    source_text: str                 # 条款原文片段
```

#### 5.2.2 `rule_extractor.py` — 管理制度 → 规则

从 Word/PDF 的本行管理制度中，用 LLM 抽取结构化 `PolicyClause` 列表。

```python
class InternalPolicyExtractor(RuleExtractor):
    """实现《共享架构》RuleExtractor 接口

    输入：制度全文（string）
    输出：list[PolicyClause]

    处理策略：
    1. 按「第 X 章」/「第 X 条」正则切分
    2. 每段送入 LLM，提取 clause_id / condition / consequence
    3. 条款原文保留用于证据链
    """

    SYSTEM_PROMPT = SYSTEM_INTERNAL_POLICY_EXTRACT  # 新增 Prompt

    def extract(self, policy_text: str) -> list[PolicyClause]: ...
```

#### 5.2.3 `customer_scanner.py` — 批量扫描引擎（核心）

```python
class CustomerScanner:
    """批量并发扫描器

    输入：AlertKnowledgeBase
    输出：list[CustomerScanJob]（每家客户一个扫描作业）

    关键能力：
    - 并发 ≤ 8 的 asyncio 扫描（避免 LLM/搜索 API 限流）
    - 进度回调（供前端 tick 流）
    - 取消支持
    - LLM 响应缓存（演示场景提速）
    """

    def __init__(self,
                 kb: AlertKnowledgeBase,
                 search_provider: SearchProvider,
                 matcher: CrossMatcher,
                 max_concurrency: int = 8,
                 on_progress: Callable = None,
                 on_hit: Callable = None): ...

    async def scan_all(self) -> RiskLedger: ...
```

#### 5.2.4 `cross_matcher.py` — 双路交叉命中

```python
class CrossMatcher(Matcher):
    """外部信号 × 内部规则 交叉命中器"""

    def match_customer(self,
                       customer: CustomerRecord,
                       external_signals: list[AlertSignal],
                       internal_clauses: list[PolicyClause],
                       alert_rules: list[AlertRule]) -> CustomerScanJob:
        """
        处理流程：
        1. 外部路径：external_signals 由 SearchProvider 返回 + alert_engine 规则打分
        2. 内部路径：逐条 PolicyClause → LLM 判断客户是否命中该条款
        3. 交叉合并：同一类别 外 × 内 都命中 → 置信度提升 → 红灯
                     仅外或仅内命中 → 黄灯
                     都未命中 → 绿灯
        4. 证据链拼接
        """
```

#### 5.2.5 `ledger_exporter.py` — 榜单导出

- 全量榜单 → Excel（openpyxl，多 sheet：高风险 / 中风险 / 低风险 / 规则清单 / 制度条款）
- 单客户处置单 → PDF（reportlab，含企业画像 + 证据链 + 处置建议）

### 5.3 保留模块（单客户评估内核）

| 模块 | 保留职责 | 与 v2.0 整合方式 |
|------|---------|----------------|
| `alert_engine.py` | 22 条规则 + 红黄绿评级 + AlertSignal/AlertReport 数据结构 | `CustomerScanner` 对每家客户调用 `evaluate_alerts()` 作为外部路径打分 |
| `disposition.py` | LLM + 模板混合处置建议生成 | 仅对红/黄灯客户批量调用，生成 `DispositionPlan` |
| `trend_analyzer.py` | 财务指标趋势 | 作为外部信号的可选补充 |
| `prompts.py` | 单客户扫描 Prompt | 保留，新增批量场景 Prompt |

### 5.4 编排流程图（v2.0）

```
用户上传知识库（3 槽位） / 选择预置场景
           │
           ▼
AlertKnowledgeBase.from_uploads() / from_scenario()
    · 解析 customers Excel
    · 加载 rules JSON
    · rule_extractor.extract() 抽取 policy clauses
           │
           ▼
CustomerScanner.scan_all()  ── 异步并发 ──┐
           │                              │
  对每家 customer：                        │
     ├── search_provider.query()  → 外部信号原始数据
     ├── alert_engine.evaluate_alerts() → 外部 AlertSignal
     ├── cross_matcher.match_internal() → LLM 判断内部条款命中
     ├── cross_matcher.cross() → CustomerScanJob（交叉命中）
     └── disposition.generate() → DispositionPlan（仅红/黄）
           │                              │
           ▼                              │
RiskLedger { red[], yellow[], green[] } ◀┘
           │
           ▼
前端渲染 + ledger_exporter 导出
```

---

## 6. 数据模型

### 6.1 核心数据流

```
KnowledgeBase
  ├── customers: list[CustomerRecord]
  ├── rules:     list[AlertRule]
  └── policies:  list[PolicyClause]

           ↓（扫描）↓

CustomerScanJob  （每家客户一条）
  ├── customer: CustomerRecord
  ├── external_signals: list[AlertSignal]      # 来自外部 SearchProvider + alert_engine
  ├── internal_hits:    list[PolicyHit]        # 来自内部 PolicyClause × LLM 判定
  ├── level: "red" | "yellow" | "green"        # 交叉后综合级别
  ├── evidence_chain:   list[EvidenceItem]     # 证据链
  └── disposition:      DispositionPlan | None # 处置建议（红/黄才有）

           ↓（聚合）↓

RiskLedger
  ├── red:    list[CustomerScanJob]
  ├── yellow: list[CustomerScanJob]
  ├── green:  list[CustomerScanJob]
  └── stats:  ScanStats (total, duration, timestamp)
```

### 6.2 Pydantic 定义

```python
class PolicyHit(BaseModel):
    clause_id: str
    clause_article: str          # 第 14 条
    clause_source: str           # 《本行小微信贷风险管理办法》
    match_reason: str            # LLM 给出的匹配理由
    source_text: str             # 原文片段

class EvidenceItem(BaseModel):
    source_type: str             # "external" | "internal"
    provider: str                # "TianyanchaProvider" / "BaiduNews" / "InternalPolicy"
    title: str
    snippet: str
    url: str = ""                # 外部证据的 URL
    timestamp: str = ""

class CustomerScanJob(BaseModel):
    customer: CustomerRecord
    external_signals: list[AlertSignal] = []
    internal_hits:    list[PolicyHit]   = []
    level: str = "green"
    evidence_chain: list[EvidenceItem] = []
    disposition: Optional[DispositionPlan] = None
    llm_narrative: str = ""      # LLM 解读的人话描述

class ScanStats(BaseModel):
    total: int
    red_count: int
    yellow_count: int
    green_count: int
    duration_seconds: float
    timestamp: str

class RiskLedger(BaseModel):
    red:    list[CustomerScanJob] = []
    yellow: list[CustomerScanJob] = []
    green:  list[CustomerScanJob] = []
    stats:  ScanStats
```

---

## 7. LLM 调用规划

### 7.1 LLM 调用点清单

| 调用点 | 所属模块 | 输入 | 输出 | Prompt 名 |
|--------|---------|------|------|-----------|
| 管理制度条款抽取 | rule_extractor | 制度文本分段 | list[PolicyClause] | `SYSTEM_INTERNAL_POLICY_EXTRACT`（新增） |
| 单客户风险扫描 | alert_engine（保留） | 客户财务 + 舆情 | AlertReport | `SYSTEM_RISK_SCAN`（保留） |
| 单客户财务趋势 | trend_analyzer（可选） | 财务时序 | TrendItem 列表 | `SYSTEM_TREND_ANALYSIS`（保留） |
| 内部条款命中判定 | cross_matcher | 客户信息 + PolicyClause | PolicyHit（命中 or 不命中 + 理由） | `SYSTEM_CLAUSE_MATCH`（新增） |
| 证据链人话解读 | cross_matcher | 外部信号原文 + 内部命中 | 客户级 narrative | `SYSTEM_EVIDENCE_NARRATIVE`（新增） |
| 批量处置建议 | disposition（改造） | list[CustomerScanJob] | 批量 DispositionPlan | `SYSTEM_DISPOSITION_BATCH`（新增） |

### 7.2 成本控制

- **100 家客户扫描的 LLM 总调用预算**：
  - 规则抽取：1 次（全量制度一次性抽）
  - 单客户风险扫描：1 次 / 家 = 100 次
  - 内部条款命中判定：批量判定（每家 1 次，含全部条款） = 100 次
  - 处置建议生成：仅红/黄灯（约 10 家） = 10 次
  - **合计：约 211 次 LLM 调用**
- **预置场景缓存**：第一次扫完把每家的 LLM 响应缓存到 `mock_data/cache/`，演示重播秒出。
- **并发控制**：`asyncio.Semaphore(8)`，避免触发 API rate limit。

### 7.3 新增 Prompt 样例（`SYSTEM_CLAUSE_MATCH`）

```
你是一名银行风险管理专家。请判断给定客户是否触发了给定的内部管理条款。

输入：
- 客户画像（含授信、财务、舆情、工商等）
- 一条内部条款（condition + consequence + source_text）

输出 JSON：
{
  "hit": true/false,
  "confidence": 0.0-1.0,
  "match_reason": "客户的 X 字段满足条款中 Y 条件",
  "evidence_snippet": "客户资料中的原文片段"
}

判断原则：
- hit 必须有客观证据支撑，不得臆测
- 若信息不足，返回 hit=false, confidence<0.3, match_reason="信息不足"
- 证据片段必须来自输入，不得杜撰
```

---

## 8. Mock 数据规格

### 8.1 两个场景各自的 KB 数据

#### 场景 1：小微信贷组合

| 文件 | 规格 |
|------|------|
| `customers.xlsx` | 100 家客户，字段：客户 ID / 企业名 / 统一社会信用代码 / 授信额度 / 贷款余额 / 到期日 / 行业 / 地区 / 客户经理 / 内评 / 注册资本 / 成立日期 / 最近财报利润 / 最近财报营收 |
| `rules.json` | 20 条规则（覆盖 FIN-001～008 / LAW-001～004 / BIZ-001～004 / NEW-001～002 / REL-001～002） |
| `policy.md` | 本行《小微信贷风险管理办法》4200 字，含 18 条条款 |
| 预埋信号 | 3 家红灯 + 7 家黄灯，其余 90 家干净 |

#### 场景 2：供应链贷款组合

| 文件 | 规格 |
|------|------|
| `customers.xlsx` | 100 家供应链上下游客户（汽车零部件行业），字段在场景 1 基础上追加：主机厂名 / 应收账款池规模 / 近期订单量同比 |
| `rules.json` | 20 条通用规则 + 2 条专属（IND-001 / REL-003） |
| `policy.md` | 本行《供应链金融业务管理制度》3800 字 |
| 预埋信号 | 1 家红灯 + 12 家黄灯（多为行业下行传染） |

### 8.2 SearchProvider Mock 响应

- 每个场景在 `mock_data/scenario_xxx/mock_search/` 下预置 N 个客户的搜索响应 JSON（裁判文书 / 工商变更 / 舆情）。
- 覆盖红灯/黄灯客户的关键证据（场景 1 的华联精密、恒达汽配等）。
- 绿灯客户返回空结果或无关噪声，验证 Agent 的「无噪声误报」能力。

### 8.3 客户知识库替换接口

Demo 结束后切到真实生产时，客户只需：
1. 将自家客户名录 Excel 按指定字段模板导出。
2. 把本行制度 PDF 上传。
3. 选用现有或自定义规则 JSON。

代码层面不需要改动——三个文件都走 `KnowledgeBase.from_uploads()`。

---

## 9. 验收标准

### 9.1 功能验收

| 项 | 标准 |
|----|------|
| 知识库加载 | 100 家客户 Excel + 20 条规则 + 4000 字制度 解析 ≤ 10 秒 |
| 制度条款抽取 | 从 4200 字 Word 中抽出 ≥ 15 条 PolicyClause，字段完整率 100% |
| 批量扫描时效 | 100 家客户全量扫完 ≤ 2 分钟（使用缓存 ≤ 10 秒） |
| 命中检出率 | 预埋的 3 红 + 7 黄（场景 1）/ 1 红 + 12 黄（场景 2）全部检出 |
| 命中解释准确 | 每条命中规则的 match_reason 必须与证据一致，不得幻觉（审查 20 条抽样） |
| 证据链可追溯 | 每条命中至少 1 条证据，外部证据带 URL，内部证据带条款原文 |
| 处置建议个性化 | 同一规则的不同客户，建议文本应有差异化（体现客户名/授信额/到期日等） |
| Excel 导出 | 榜单导出 Excel 含 4 个 sheet，可在 Office 365 打开无错 |
| PDF 导出 | 单客户处置单 PDF 含画像 + 证据链 + 建议，格式可读 |

### 9.2 体验验收

| 项 | 标准 |
|----|------|
| 零配置启动 | 点击场景卡片即可启动，无需填 API Key、无需手工上传 |
| 扫描过程可见 | 进度条顺畅推进，tick 流持续刷新，无长时间卡顿（单家客户扫描 ≤ 3 秒） |
| 榜单交互流畅 | 点击客户切换详情 ≤ 500ms，证据链展开无延迟 |
| 取消响应 | 扫描中点取消 ≤ 2 秒内停止并保留已扫结果 |
| 错误容忍 | 单家客户扫描失败不影响整体扫描，失败家数显示在状态区 |
| 视觉一致性 | 与 Agent1 / Agent5 共用雷达范式，品牌色/间距/字体统一 |

### 9.3 反「伪雷达」验收（客户识别度）

| 项 | 标准 |
|----|------|
| 上传形态 | 必须是「客户池 + 规则库 + 制度」三类 KB 文件，单企业名不被接受为输入（会给出明确引导） |
| 批量观感 | 扫描过程必须看到数字连续变化（已扫 X/Y）和实时命中 tick |
| 榜单形态 | 最终输出必须是榜单，不是「一家企业的报告」 |
| 双路标注 | 每条命中必须清晰区分来自外部 or 内部（UI 上有色块/图标） |

---

## 10. 非功能需求

### 10.1 性能

| 项 | 目标 |
|----|------|
| 100 家扫描 P95 | ≤ 2 分钟（含 LLM + 搜索） |
| 单客户详情切换 | ≤ 500ms |
| Excel 导出 100 家 | ≤ 3 秒 |
| 内存占用 | 峰值 ≤ 512MB |

### 10.2 可靠性

- 单家扫描失败自动重试 1 次，仍失败则标记为「扫描失败」但不阻断全流程。
- LLM 响应不合 schema 自动重试（已在 BaseAgent 实现）。
- 取消扫描时正确回收并发任务，不产生僵尸请求。

### 10.3 可扩展性

- 规则库支持用户自定义追加，只需符合 `AlertRule` schema。
- `SearchProvider` 可插拔：生产环境切换到天眼查 API 或本行内部数据源。
- 并发度 `max_concurrency` 可配置，大行可调至 32 + 本地 LLM。

### 10.4 合规与安全

- 客户数据不出本机（Demo 阶段 mock，生产部署在客户本地）。
- LLM 调用走客户自配 API Key（支持 DeepSeek / Kimi / MiniMax / OpenAI）。
- 证据链永久保留在扫描结果文件中，供合规审计回溯。

---

## 11. 排期建议

| 里程碑 | 内容 | 工期 |
|-------|------|------|
| M1 | 数据模型 + KnowledgeBase + rule_extractor 完成并单测 | 3 天 |
| M2 | customer_scanner + cross_matcher 完成并跑通小样本（10 家） | 3 天 |
| M3 | 场景 1 预置 KB + mock search + 缓存全跑通 | 2 天 |
| M4 | 雷达 UI 前端完成（Gradio HTML/Callback） | 3 天 |
| M5 | 场景 2 预置 KB + 导出 Excel/PDF | 2 天 |
| M6 | Demo 全链路彩排 + 性能调优 + 文档 | 2 天 |
| **合计** | | **15 工作日** |

---

## 12. 风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| 100 家客户扫描 LLM 调用超预算 | 演示超时 | 预置场景全量缓存，演示走缓存路径 |
| LLM 幻觉导致误报红灯 | 客户信任度下降 | Prompt 加「证据必须来自输入」硬约束 + 反审 + 不确定时默认输出黄灯 |
| 搜索 API 限流 / 故障 | 扫描中断 | MockProvider 托底，生产侧 provider 加熔断降级 |
| 前端榜单条目多卡顿 | 体验崩塌 | 虚拟滚动 + 绿灯默认折叠 + 懒加载详情 |
| 内部制度 PDF 抽取质量不稳 | 规则抽错 → 误报 | 抽取后置审核 UI，用户可修正 PolicyClause 后重扫 |
| 客户质疑"我看你还是查单家的" | 演示翻车 | 开场即展示 KB 多文件上传和 100/100 进度条，先让批量观感落地 |

---

## 13. 附录：与 Agent1 / Agent5 的一致性清单

| 维度 | Agent1 获客 | Agent4 贷中 | Agent5 合规 |
|------|------------|-------------|-------------|
| 输入 | 客户池 + 渠道库 + 行业政策 | 客户池 + 规则库 + 内部制度 | 政策库 + 内部制度 + 业务数据 |
| 扫描对象 | 企业 × 渠道 | 企业 × 双路规则 | 条款 × 事件 |
| 输出榜单 | 推荐渠道 Top 榜 | 红黄绿客户榜 | 严重/一般/观察违规榜 |
| 详情切换 | 企业详情 + 渠道适配矩阵 | 客户详情 + 证据链 | 违规详情 + 条款原文 |
| 建议卡片 | 营销建议 | 处置建议 | 整改建议 |
| 共享接口 | KnowledgeBase / Matcher / SearchProvider | KnowledgeBase / Matcher / RuleExtractor / SearchProvider | KnowledgeBase / Matcher / RuleExtractor |
| 视觉范式 | 分级榜单 + 详情 + 建议 | 分级榜单 + 详情 + 建议 | 分级榜单 + 详情 + 建议 |

**结论**：三个 Agent 在「雷达范式」这个抽象层完全一致，只是领域对象不同。这就是客户买单的理由——不是 5 个独立工具，而是**一套可复制的银行 AI 雷达方法论**。
