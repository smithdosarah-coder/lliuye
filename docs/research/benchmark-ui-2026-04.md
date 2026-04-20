# Bank AI 产品 UI 对标（2026-04）

> 调研窗口：2026-04-20 · 信息源：6 款产品官网 / 官方 solution sheet / 厂商白皮书 / 中国日报网 / 知乎 / 搜狐 / 21 财经 / FICO Blog / Moody's Events / 新华日报 / CSDN 转载新闻稿
> 调研限制：国内厂商普遍不在公网挂 SaaS 截图（银行私有化部署为主，登录墙卡死 demo），海外厂商以 marketing 图 / GUI sheet 为主。
> 下文中"界面推断"均基于文字描述 + 同类产品交叉验证，不足处明示"未找到公开截图"。

## 1. 目的

为即将定型的**信贷 AI 平台 shell v2**（4 view + 6 Agent tile + 4 主题）建立外部锚点：
- 验证自己的 IA（Today / Dispatch / Archive / Warroom）是否与市场主流产品"撞形"或"偏离"
- 找到**证据/溯源呈现**、**规则 DSL 编辑**、**审批队列**、**智能体编排**四个场景可借鉴的既有 pattern
- 识别银行 AI 产品的普遍"反模式"（堆砌 dashboard / 深菜单 / 无证据 KPI），在 shell v2 落地前规避

## 2. 关键发现（横向规律 5 条）

1. **"左导航 + 右工作台"仍是银行 AI 主流骨架**：壹账通、同盾、FICO Falcon、Moody's CreditLens 全部采用"左侧业务域菜单（信贷/反欺诈/催收/规则管理）+ 右侧卡片流或列表"。极少产品采用类 Slack IM 式的对话驱动骨架——我们选的 Dispatch（对话）view 是**明显的非主流选择**，要么赢在体验，要么败在认知成本，两头都要押。
2. **"证据/审计"的呈现一律走"审计日志 + 旁边字段对比"而非"气泡回链"**：Moody's CreditLens 官方表述是 holistic audit trail that logs every action and input；同盾天策"将存疑进件的本次进件信息与历史关联进件信息一并展示"——都是**双栏对照 + 时间线 log**，而不是我们规划的"每个 claim 带 footnote hover"。两种都有合理性，我们的做法更细粒度但认知负担更高。
3. **"规则编辑"几乎统一用"拖拽 / 流程图 / 画布"**：同盾天策"页面拖拽配置即可完成业务指标、规则创建 / 支持分流、回测等决策流模式"；壹账通智能体平台四大模块之一就是 **Workflow 工作流**；FICO Falcon 7.0 强调"Business Rules Engine 快速定义、测试、部署"。我们 Agent2 风控的 DSL 目前是纯文本 + 回测表格，缺**可视化画布**，这是明显 gap。
4. **"案件/审批队列"是 Falcon 7.0 的 7.0 最大改版——tile-based + 每个 case 内部 tab 化**：从一页"全展开"到"前台 transaction grid + 后台 tab 展开 case details + 色码 disposition 状态"，这是被 70% 受访买家按头投票出来的升级方向。我们 Agent3 授信、Agent6 报告的 workspace 可以直接借鉴。
5. **"智能体平台"厂商普遍走低代码 + 插件库 + RAG 三件套**：壹账通（Agent + Workflow + Plug-in + RAG）、百融 CybotStar（三层架构 百基/百工/百汇）、同盾诸葛（智能决策引擎 + 知识构建 + 内容生成 + 风控特征挖掘）都在对齐**Agent Builder**范式。我们的 6 Agent 是**垂直成品**而不是**通用 Builder**——这是差异化也是风险：客户可能问"能不能按我的流程改"。

## 3. 逐产品拆解

### 3.1 金融壹账通 Smart Lender / 智能面审（对标 Agent6 报告助手）

**来源**：官网 `ocft.com`、官方核心产品页 `solution/gamma`、中国日报网 2025-03 采访稿、新华日报 2024-09、CSDN 转载新闻稿（142132297、143043198）、21 财经 2020 深度。**未找到公开正面 UI 截图**，以下基于公开文字描述推测。

**信息架构**：壹账通没有独立叫"Smart Lender"的产品线，最接近的是 **数智银行一站式 AI 平台**（300+ 金融 AI API）+ **智能面审解决方案**+2025 新推的 **智能体平台**。智能体平台 4 大模块：Agent 智能体 / Workflow 工作流 / Plug-in 插件库 / RAG 知识检索。银行对公信贷场景里落地的是"智能资料审核产品 + 智能面审 + 智能审单"——**纵向按业务域切，横向按能力层切**。

**典型交互流**（智能面审场景，7×24 数字人全自助分支）：
- 客户扫码 / 进小程序 → SDK / H5 / 小程序三选一接入层 → 数字人虚拟坐席对话（ASR / TTS） → 声形同步 + 微表情 + 相似背景三路反欺诈判定 → 70%+ 自动审批直接走，可疑件转人工坐席接管
- 银行侧审贷员看到的是一个**视频双栏界面**：左侧客户视频实时流 + 右侧 OCR 结构化字段 + 反欺诈得分；数字人 / 人工切换无缝

**证据/溯源呈现**：壹账通强调"AI 替代人工审核 70%+ 通过率"，没有公开强调 claim-level 证据链，审计走**业务日志**+**视频/语音原文回放**。这是欺诈场景的惯例（要庭审举证，需要原始介质不能只有摘要）。

**UI 关键 pattern（ASCII 推断，基于文字描述）**：
```
+---------------------------+-------------------------------+
| 客户视频流（主视场）       | 结构化字段（OCR 结果）          |
|                           |  姓名:  张三         ✓        |
|  [数字人 / 客户双视角]     |  身份证: 41*** 2345  ✓        |
|                           |  申请金额: 50,000    ✓        |
|                           |                               |
|                           +-------------------------------+
|                           | 反欺诈信号（视觉风控）          |
|                           |  声形同步 98.2%      绿        |
|                           |  微表情异常 低       绿        |
|                           |  相似背景命中  无     绿        |
|                           |  群伙图计算 无       绿        |
+---------------------------+-------------------------------+
|  [ 转人工 ]  [ 通过 ]  [ 驳回 ]   审批耗时 47s             |
+---------------------------------------------------------+
```

**可借鉴**：双栏（原始证据左 + 结构化结论右）+ 分维度风控信号灯+ 整体倒计时。对 Agent6 报告助手的"左材料预览 / 右字段表格"是直接印证。
**需避免**：壹账通对公业务最后的**信贷报告**并未公开，推测仍是 Word 导出为主，无 IM 式多轮共创——这正是我们 v2 要拉开身位的点。

---

### 3.2 金融壹账通 Gamma 加马平台（对标 Agent3 授信 + 跨域能力）

**来源**：`ocft.com/solution/gamma`、`ocft.com/website/solution/gamma-platform/znsj/`、雷峰网 2019、上海证券报 2019、凤凰网 2021。

**信息架构**（官网直出的一级导航）：
- **智能语音**：Intelligent Customer Service / Collections / Marketing / Robot Platform
- **智能视觉**：Face Review / Material Verification / Real-person Auth / Evidence Auth
- **开放数据平台**：Integrated Big Data / Mobile Integration / **Gamma Foresight Analytics** / Smart Business
- **智慧管理**：Smart Supervision / Government-Enterprise Ecosystem

**典型交互流**（信贷审批线）：Gamma Foresight → 多源数据拉取（征信 + 税务 + 水电）→ 反欺诈规则命中 → 自动审批引擎打分 → 阈值外转人工 → 放款/拒贷回写。

**证据/溯源呈现**：Gamma 的"一站式全域数据中心"+"可视化智能数据洞察工具"对应的就是传统 BI dashboard + 钻取，**没有公开 claim-level 回指证据**的呈现方式。这是**我们 v2 可能优于 Gamma 的点**——Evidence-First Protocol 是更年轻的做法。

**UI 关键 pattern（ASCII 推断，典型授信驾驶舱）**：
```
+----------+-------------------------------------------+
| 左导航    | 授信驾驶舱 Dashboard                        |
|  信贷    | +---------+ +---------+ +---------+       |
|  反欺诈  | | 当月放款  | | 不良率   | | 审批通过率 |       |
| >授信    | | 1.2 亿   | | 0.8%    | | 72%      |       |
|  风控    | +---------+ +---------+ +---------+       |
|  催收    |                                           |
|  营销    | [ 行业分布饼图 ]   [ 额度段柱图 ]           |
|          |                                           |
|          | 待审批队列（72 条）                         |
|          | ┌─────┬──────┬──────┬──────┐             |
|          | │客户名 │金额   │风险   │操作   │             |
|          | │...   │500W  │中    │[进入]│             |
+----------+-------------------------------------------+
```

**可借鉴**：一级导航按业务域而非按 Agent 分；KPI 卡片 + 待审批队列 + 行业分布图——这是银行高管拿去汇报的标准品，我们 Today view 应该有一个 persona = 支行长 的分支。
**需避免**：Gamma 把 8 大类产品全部堆在一个导航里（智能语音 / 智能视觉 / 开放数据 / 智慧管理），入口 tab 至少 4 层深，**信息密度失控**是银行 SaaS 的通病。我们 shell v2 顶栏 4 tab + Archive tile 聚合 6 Agent 的做法更轻，保持住。

---

### 3.3 同盾科技 诸葛 + 天策（对标 Agent2 风控 + Agent4 预警）

**来源**：`tongdun.cn` 首页、`tongdun.cn/product/credit`（天策信贷版产品页）、知乎专栏 `zhuanlan.zhihu.com/p/1970162403053401853`、新浪财经 2025-02 / 2026-01、中华网 2025-12、金融界 2019。**天策产品页有"视频介绍"入口但 CDN 需登录**，未拿到视频截帧。

**信息架构**：
- **诸葛®**（垂类大模型，2025 新品）：智能决策引擎 / 知识构建 / 内容生成 / 风控特征挖掘 四大能力 + 智能体管理平台 + MCP 工具管理 + 数据集管理
- **智策®-Archer2.0**（底座）：规则引擎 + 策略引擎 + 工作流引擎 + 流式实时计算引擎
- **天策**（三版本：信贷 / 交易 / 商户）：9 大功能模块——风险评估 / 统计报表 / 规则指标管理 / 决策流管理 / 模型管理 / 名单管理 / 外部数据管理 / 存疑人工复核 / 监控预警

**典型交互流**（天策信贷版一个决策流的生命周期）：
1. **规则/指标创建**：运营人员在"规则指标管理"页拖拽组件 → 阈值设定 → 行业标准规则库一键调用
2. **决策流编排**：在"决策流管理"页拖拉分流节点 / 回测节点 / 冠军挑战者节点 → 保存为版本
3. **上线回测**：历史数据回灌 → KS / 通过率 / 捕获率报表
4. **存疑人工复核**：可疑件进入"人工复核队列" → 左历史关联进件 + 右本次进件 双栏对照 → 审核员裁决

**证据/溯源呈现**：天策"存疑进件 + 历史关联进件 并列展示"是典型**对照视图**；诸葛的"预警归因分析 + 策略量化调优"是**归因报告**形态。

**UI 关键 pattern（ASCII 推断，天策决策流画布）**：
```
+------------------------------------------------------+
| 决策流: 信贷_申请反欺诈_v2.3   [保存] [回测] [上线]   |
+------------------------------------------------------+
|  [起点] ──┐                                          |
|            ↓                                         |
|       ┌─────────┐                                    |
|       │规则组 R1│─── Y ──┐                           |
|       │黑名单   │         │                          |
|       └─────────┘         ↓                          |
|            │N         ┌────────┐                     |
|            ↓          │ 拒绝   │                     |
|       ┌──────────┐    └────────┘                     |
|       │评分卡 M2 │                                   |
|       │申请评分  │                                   |
|       └──────────┘                                   |
|            │                                         |
|            ├── <600 ──→ 人工复核                     |
|            └── ≥600 ──→ 通过                          |
|                                                      |
|  右键节点: 编辑条件 / 查看历史命中 / 冠军挑战者       |
+------------------------------------------------------+
```

**可借鉴**：**决策流画布** 是 Agent2 风控最大缺口——目前只有 DSL 文本 + 回测表格，客户视觉上理解不了。加一个只读版 canvas 即能显著提升体验；分流 / 回测 / 冠军挑战者三种节点也可直接复用术语（客户已认）。
**需避免**：天策把 9 个功能模块平铺，新用户进来不知从哪开始——这就是我们**Today view 的存在理由**：给任务入口，不给模块清单。

---

### 3.4 百融云创 CybotStar / 百工（对标 Agent1 获客 + 平台化方向）

**来源**：官网 `brgroup.com`、`baironginc.com/solution/consfinance`（CDP 访问 403）、搜狐转金融界 2024-11 报道、新浪财经 2025-03 年报、Morningstar PR Newswire 2025-11 / 2025-12、prnewswire.com 2025-12、知乎专栏 1966797197359186619。**未找到 CybotStar 编排画布的公开截图**（Agent Builder 类产品的画布界面普遍靠官网 demo 视频/PPT 挡在登录后），以下基于文字描述推测。

**信息架构**：百融 RaaS（Results-as-a-Service）战略下的三层：
- Layer 1 **百基 Baiji**：计算基座 + 推理引擎 + 领域 AI 模型（含 BR-LLM 大模型）
- Layer 2 **百工 CybotStar**：企业级智能体 OS / Agent Builder 平台（已通过网信办备案）
- Layer 3 **百汇 Baihui**：Agent Store / AI 智能体员工商店

CybotStar 本体 4 要素：可视化工作流编排 + 专属知识库 + 插件库（按业务场景匹配）+ 多分发渠道（微信小程序 / APP / 大屏 ≥10 个端）。定位："用户无需掌握编码知识，只需说清工作流"——是**典型 Dify / Coze 类产品**的金融垂直版。

**典型交互流**（客户经理创建一个"潜客匹配 Agent"的推测路径）：
1. 进 CybotStar 管理台 → 新建 Agent → 选模板（潜客挖掘）
2. 配置专属知识库（行业白名单 / 产品册 / 授信政策）
3. 画布拖拽节点：数据源取数 → 画像匹配 → LLM 生成话术 → 结果写回 CRM
4. 在线调试 → 发布到微信小程序/大屏

**证据/溯源呈现**：CybotStar 对外强调"真实业务场景准确率 ≥ 98%"，没公开溯源 UI。推测走"RAG 引擎的 citation"做法——哪个文档出的哪个答案，这是 Dify 系产品的惯例。

**UI 关键 pattern（ASCII 推断，智能体编排画布）**：
```
+----------------------------------------------------+
| Agent: 潜客匹配助手 v1.2    [运行] [发布] [调试]   |
+----------------------------------------------------+
|  [起始] ─→ [数据源] ─→ [画像匹配] ─→ [LLM 节点]    |
|   用户        企查查        知识库       话术生成    |
|   输入        外部 API      RAG 检索     prompt     |
|                                 │                  |
|                                 ↓                  |
|                            [条件分支]              |
|                             /      \               |
|                         高意向     低意向          |
|                           ↓         ↓              |
|                       [写 CRM]  [Excel 沉淀]       |
|                                                    |
|  右侧节点属性面板: 模型选择 / prompt / 输入输出变量 |
+----------------------------------------------------+
```

**可借鉴**：如果我们未来要对外讲"平台化能力"，必须有类似 Builder；现阶段先保留**按域拆 6 Agent tile + 每个 Agent 内部跑固化 workflow**的做法，**不上 Builder**，避免陷入"又一个 Dify"。
**需避免**：CybotStar 核心卖点是"无代码"，但落地到银行时仍需要产品经理画流程，**"无代码"本质是转移了复杂度不是消灭了复杂度**。我们 CLAUDE.md 交互原则里的"系统承担复杂性"比这更强。

---

### 3.5 FICO Falcon Fraud Manager 7.0（对标 Agent4 预警 + Agent3 授信的 case 化）

**来源**：`fico.com/en/products/fico-falcon-fraud-manager`、`fico.com/en/latest-thinking/solution-sheet/fico-falcon-fraud-manager-introducing-falcon-7-0`、`fico.com/blogs/improving-case-management-and-fraud-decisioning-while-protecting-cx`（2024-01 Debbie Cobb VP Product Mgmt 署名博文，内容即 Falcon 7.0 官方 UI 改版说明）、FICO Fraud Expert 帮助页 `fraud.sia.eu`、IBM 转售 solution description PDF。**未拿到带水印的公开截图**（FICO marketing 图都在 gated PDF 里），但官方博文把 UI 改版逐条写明。

**信息架构**：Falcon 7.0 五大模块：
- **Case Management**（重点升级）
- **Business Rules Engine**
- **Reporting and Governance**（dashboard 入口）
- **Contextual Fraud Analytics**（打分引擎底座）
- **Multichannel Interactive Fraud Resolution**（客户触达闭环）

**典型交互流**（反欺诈分析师日常）：
1. 登录 → **新首页 tile-based 布局**（FICO 原话："new intuitive, categorized tile-based layout provides easier navigation to the most-used functionality; Administrators can easily customize the tiles based on role"）
2. 进 Case Manager → **工作流按 analyst 审阅顺序重排**，transaction grid 置顶（这笔钱本身）→ disposition 区在下 → case details 用 tab 展开节省空间
3. Disposition 阶段使用**色码状态分类**（绿/黄/红），filter 化一键结案
4. Dashboard 走**point-and-click 过滤**，不跳页

**证据/溯源呈现**：Falcon 的 case detail 是把触发规则 / 评分结果 / 历史交易 / 关联账户全部 tab 化，每一项都是**"为什么系统判这笔可疑"的证据槽**。审计维度强，UI 没有 footnote 回指但有**完整 transaction 溯源**。

**UI 关键 pattern（ASCII 基于官方博文描述）**：
```
+------------------------------------------------------+
| Falcon 7.0 Home                         [Admin] [?] |
+------------------------------------------------------+
|  [ My Cases ]  [ Alerts Queue ]  [ Rules ]  [ ... ] |
|     342 open        1,203           82             |
|                                                      |
|  [ Dashboards ] [ Reports ]  [ Admin ] [ Investig. ] |
|     role-based                                       |
+------------------------------------------------------+

Case Detail View:
+------------------------------------------------------+
| Case #482771  Alan Wong  $18,420  CNP e-commerce    |
|  status: ● Under review  (color-coded)               |
+------------------------------------------------------+
| [Transaction Grid 置顶]                              |
| 10:02  -$2,103  Amazon UK      device: new iOS      |
| 10:05  -$5,200  WesternUnion   device: new iOS      |
| 10:11  -$11,117 unknown POS    geo: Malta            |
+------------------------------------------------------+
| Tabs: [Summary] [Rules Hit] [Customer History]      |
|       [Device] [Geo] [Related Cases] [Notes]        |
+------------------------------------------------------+
| Disposition:  ● Fraud  ○ Legit  ○ Pending  ○ Escal.  |
|               (colour-coded one-click)               |
+------------------------------------------------------+
```

**可借鉴**：tile 主页 + 角色可配置 + transaction grid 置顶 + tab-based case details + 色码 disposition——这是**Agent4 预警 workspace 近乎现成的 blueprint**。我们已经有红黄绿分级，把 case detail 层加上 tab 化。
**需避免**：Falcon 的 Admin / Investigator / 三种 dashboard 有多种角色视图分裂（后台 / 调查员 / 主管），**角色切换成本高**。我们 shell v2 的 persona 切换机制（"王哲·客户经理·华东"live badge）要保证同一入口 dynamic 适配，而不是给每个角色做独立页面。

---

### 3.6 Moody's CreditLens / Lending Suite（对标 Agent3 授信 + Agent6 信贷报告）

**来源**：`moodysanalytics.com/product-list/creditlens`（CDP 超时，间接读）、`moodyscre.com/products/creditlens-cre/`（CDP 拿到全文）、`moodys.com/web/en/us/solutions/lending/loan-origination/spreading-scoring.html`（CDP 拿到全文）、Business Wire 2017 发布稿、AWS 博客 Serverless 迁移架构稿、YouTube "Exploring CreditLens: Automated spreading by QUIQspread"（未看视频，以描述为准）、events.moodys.com（用户年会议程页）。**未找到带完整 UI 截图的公开页面**（Moody's marketing 图普遍在 gated brochure PDF 里），以下 UI 细节基于官方文字描述推断。

**信息架构**（CRE 版产品页的三角色视图直给）：
- **Lender 视图**：deal pipeline / deal-screening memo / term sheet drafting / pre-qualification / deal sizing & scenarios
- **Underwriter 视图**：subject property analysis / tenant risk / NOI / PD·LGD·EL（integrated rating model） / credit memo / deal decisioning
- **Portfolio & Risk Manager 视图**：covenant auto-test / pre-populated reports / periodic deal review / portfolio performance

Lending Suite 通用能力：**financial spreading grid**（导入+行业模板）+ QUIQspread（AI 自动 spreading）+ **holistic audit trail**（"logs every action and input"）+ dual risk rating + recommended views + 自定义 dashboard。

**典型交互流**（一笔商业房地产贷款从 deal 到 booking）：
1. 创建 deal → 从 CRE 数据库 pre-qualify → deal sizing 多场景
2. 进 spreading：导入财报 → grid 化展开 → QUIQspread 自动填数 → 人工 review
3. 打 PD / LGD / EL → 生成 credit memo（模板化）→ 提交审批
4. 审批通过 → covenant 自动跟踪 → 定期 review 触发

**证据/溯源呈现**：CreditLens 的杀手锏是 **audit trail** ——"logs every action and input, supporting transparency for regulatory authorities"。这是**监管友好型**溯源：每个字段改了啥、谁改的、什么时间、基于什么数据源，全部记录。不是"为数字加 footnote"，而是"整条操作历史可回溯"。

**UI 关键 pattern（ASCII 推断，spreading 页典型双栏对比）**：
```
+------------------------------------------------------+
| Deal: Acme Office Tower LLC — Loan #4821             |
|   Spreading  |  Rating  |  Credit Memo  |  Covenants |
+------------------------------------------------------+
|  Year            2023     2024     2025(Proj)        |
|  Revenue       $12.4M   $13.2M   $14.0M              |
|  EBITDA         $3.1M    $3.6M    $4.1M              |
|  DSCR            1.35     1.42     1.55              |
|   ...                                                 |
|  [+] add row   [✎] edit template   [AI] QUIQspread    |
+------------------------------------------------------+
| Audit Trail (right panel, collapsible)               |
|  2026-04-18 14:02  J.Smith  Revenue 2024 12.8→13.2  |
|  2026-04-18 13:45  QUIQspread auto-filled 27 rows    |
|  2026-04-17 10:20  J.Smith  Imported 10-K PDF        |
+------------------------------------------------------+
|  Dual Rating: PD 2.3%  LGD 35%  EL 0.8%              |
|  Model: Moody's CRE Rating v4.2 + Internal Overlay   |
+------------------------------------------------------+
```

**可借鉴**：**右侧可收起 Audit Trail 面板** + **spreading grid 里每个数字带编辑历史** + **顶栏 4 tab 走完整个 deal 生命周期**——这是 Agent3 授信 + Agent6 报告的**合体版蓝图**。我们的 Evidence-First Protocol 可以把"每个数字带 footnote 回指证据"注入到这种审计面板里，是**CreditLens 的升级版**而不是另起一套。
**需避免**：CreditLens 功能极重（lender / underwriter / risk manager 3 种角色 + spreading / rating / memo / covenant 4 大模块），新用户上手需要培训——Moody's events 页甚至专门开了 "User Forum" 年会带训。我们交付银行客户的时候**初期只推一个 persona + 一个任务流**，不要一开门就拉 3 角色 + 4 模块。

## 4. 对我们平台的启示（≤10 条 actionable）

1. **IA 不撞车的代价要承受**：Today / Dispatch（IM） / Archive（Agent tile） / Warroom（看板）的 4 view 在外部**完全没有对标**——壹账通、同盾、Falcon、CreditLens 全部是"左导航 + 右工作台 + KPI 驾驶舱"。我们 Dispatch 走 IM 风是明牌的豪赌，用户认就赢，不认就要退回左导航。**shell v2 锁定前必须做一轮客户测试**。
2. **Agent2 风控补画布**：同盾天策"决策流拖拽 + 分流 + 冠军挑战者 + 回测"是银行客户**已认的视觉语言**。即便我们技术栈坚持 DSL 文本，UI 层也必须给一个**只读版 canvas** 做"所见即所得"，否则对客户演示时会被问"你们怎么没有流程图"。
3. **Agent3/Agent6 共用 Evidence Panel**：借 CreditLens 的 **右侧可收起 Audit Trail** 形态 + 我们的 Evidence-First 证据链——做成"**每个字段既有 footnote 回指，又在右栏 audit log 汇总**"。这是比 Moody's 还前一步的做法，属于**可以当卖点讲的差异化**。
4. **Agent4 预警 workspace = Falcon 7.0 Case Manager**：直接抄 tile 主页 + transaction grid 置顶 + tab-based case details + 色码 disposition。我们已有红黄绿分级，再加 tab 化 case detail 即可。不要再自己发明。
5. **Archive view 内 6 Agent tile 是对的**：Gamma 把智能语音 / 智能视觉 / 开放数据 / 智慧管理 4 大类 + 16 个子产品堆一个导航栏——**入口爆炸**。我们 4 tab + 6 tile 的聚合比它轻，不要退回"按模块铺导航"。
6. **persona badge 要比 Falcon 的角色切换更轻**：Falcon 把 admin / investigator / 主管做成多套页面，切换成本高。我们 shell v2 顶栏"王哲·客户经理·华东"badge + 内容 dynamic 适配，是更现代的做法，保持。
7. **"Builder" 是 v3+ 话题，不是 v2**：百融 CybotStar、壹账通智能体平台都走通用 Builder——我们**不入这个战场**，6 Agent 的垂直固化是锚点。但要准备一个说法："我们不是 Builder，我们是开箱即用的 6 个 copilot"。
8. **视频/语音资产在预警 case 里要能直接回放**：壹账通智能面审场景里，审贷员看的是客户视频流 + 结构化字段双栏。Agent4 如果某条预警来自客户电话回访，case detail 里必须能**点播回放片段**而不是只看文本 transcript。
9. **"monthly review / covenant tracking" 是 Moody's 明牌，我们 Agent4 的边界要更硬**：CreditLens 把 portfolio-level 定期复核做进产品里——这和我们 Agent5（合规，政策事件驱动）Agent4（预警，客户行为驱动）**共存**是合理的。不要因为看到 CreditLens 有这个就去动 Agent5 的触发源边界。
10. **"解释性 + 归因" 用同盾诸葛的术语**：诸葛把模型输出解释叫"预警归因分析 + 策略量化调优"。我们 v2 前端里给 Agent3 授信做解释 UI 时，直接复用"归因 / 量化建议"术语，客户已认——不要自造名词。

## 5. 开放问题（未验证 / 待后续）

1. **真实 UI 截图仍缺**：除 CreditLens CRE 官网产品页外，其他 5 款都没拿到带产品水印的正面 UI 截图（银行私有化部署 + gated content）。**建议路径**：①去询价阶段要 demo 账号；②用户侧通过行业会议/年报图抠截图；③对金融壹账通联系售前要一份 solution deck。本文中的 ASCII 都是文字描述推断，未与真实 UI 像素级比对。
2. **百融 CybotStar 编排画布**形态只能推断，是否用 DAG / block-based 未证实。官方演示视频都在 gated 里。
3. **FICO Falcon 7.0 发布于 2023-2024**，我们引用的 Debbie Cobb 博文是 2024-01。最新的 Falcon 8 / Falcon X 之间关系 solution sheet 里有提，但未展开看。
4. **CreditLens 在国内银行的落地深度**：Moody's Analytics 在国内主要通过合作方落地，国内银行实际用的是 CreditLens 还是本地 OEM 版，需要产品侧询问。
5. **我们 v2 的 IM 化 Dispatch view 是否真有外部锚点**：本次调研未找到。下一轮可以看 Salesforce Slack Financial Services Cloud / Microsoft Dynamics 365 + Teams 的银行版——跨行业的 **IM + 工单**融合产品可能是我们真正的同形态对标。

---

**调研执行**：Claude Opus 4.7 via web-access skill（CDP proxy + WebSearch + WebFetch，6 并发 tab）
**工时**：约 25 分钟
**下一步建议**：①约一个壹账通 / 同盾的售前 demo，补真实 UI 截图；②在 shell v2 锁定前，把"Agent2 画布 / Agent3+6 audit panel / Agent4 tab-case"三个对标点先做 mockup 验证；③单独起一篇 `benchmark-IM-shell.md` 调研 Salesforce Financial Services Cloud + Slack + Teams 的银行配置，验证我们 Dispatch view 的外部支持度。
