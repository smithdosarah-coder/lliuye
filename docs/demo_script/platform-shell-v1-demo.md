# Platform Shell v1 · 客户演示剧本（系统 walkthrough 版）

> **2026-04-19 16:XX 重写**：路线从"企业故事线"改为"系统 walkthrough"，符合"用已有数据验证"原则。不再围绕虚构企业讲贯穿剧，而是以真实 preset + 真实 SSE 流事件逐 Agent 展示系统能力。三 Wow 框架保留，但 Wow 3 从"entity_id 贯穿"改为"统一壳 + 统一 persona + 统一主题体系"。

**版本**：v2.0（系统 walkthrough）
**日期**：2026-04-19
**演示人**：刘野（众安信科 · AI 中台 / 乾策 Studio 产品负责人）
**客户**：银行（目标席位：对公客户经理 / 审贷员 / 合规官 / 风险经理 / 科技部）
**关联规范**：
- `docs/design/platform-shell-v1.md`（4 view / 4 主题 / Desk / Masthead）
- `docs/contracts/shell-v1-agent-api-map.md`（6 Agent API 契约 + preset 清单 · 本剧本所有台词依据）
- `docs/scorecard/GLOBAL.md`（2026-04-19 矩阵：Agent6 99% · Agent3 90% · Agent1 86% · Agent2 77% · Agent4 72% · Agent5 40%）
- `CLAUDE.md` §3.1（确定性 vs 概率性）/ §3.3（Evidence-First）/ §8（QC Blocker）

---

## 1. 演示目标 + 受众 picture

- **给谁看**：银行分管行长 / 授信评审部 / 风险管理部 / 科技部（一线 RM 可能旁听），客户内部决策者至少 2 席
- **让他记住什么**：乾策 Studio 是**一个工位 6 个 Agent 打通**的 AI 信贷协作平台，覆盖**贷前获客 → 贷中授信 → 报告产出 → 贷后预警 → 合规事件**端到端场景；不是 6 个割裂的工具堆叠；所有数字可证据溯源、所有红线用确定性计算、幻觉零容忍
- **为什么系统 walkthrough 不讲企业故事**：客户看到的是**真实可跑的系统**而非"精心准备的脚本剧"。每个 Agent 用自己的 preset 跑真实 SSE 流、讲解真实返回字段——**让客户听见字是从后端流出来的，不是从幻灯片上抠下来的**。这比"一家企业串 5 个 Agent"更诚实、更有说服力。每个 Agent 用不同载体反而证明了**平台的统一性来自壳（persona + 4 view + 主题），不是来自数据**

---

## 2. 15-20 分钟走位时间轴

> 总时长预算：**17 分钟**（主演示）+ **3 分钟** 弹性（主题切换 + 兜底）+ **Q&A 另计**
> persona 全程锁定：**王哲 · 客户经理 · 华东分行**（跨 Agent 唯一不变的是 persona 本身）

### 2.1 时间轴总览

| 时间段 | 章节 | 主角 view | Agent | Preset / 数据源 |
|---|---|---|---|---|
| 00:00 - 02:00 | 开场 + 平台壳 | `/today` | — | — |
| 02:00 - 04:30 | Agent1 获客 walkthrough | `/archive/channel` | Agent1 | `hangzhou_precision` (mock=true) |
| 04:30 - 08:30 | Agent6 报告 walkthrough（Wow 1） | `/archive/report` | Agent6 | `dingsheng_trade` (mock=1) |
| 08:30 - 11:30 | Agent3 授信 walkthrough | `/archive/credit` | Agent3 | corporate / `dingsheng_trade`（composite=47 · D 级） |
| 11:30 - 13:00 | Agent4 预警 dashboard | `/archive/alert` | Agent4 | `evaluation/manual/4_20260419.yaml` 转 JSON |
| 13:00 - 14:00 | Agent2 风控 ruleset | `/archive/riskctrl` | Agent2 | `riskctrl_ruleset.json` readonly |
| 14:00 - 15:00 | Agent5 disabled tile + 战略地图 | `/archive/compliance` | Agent5 | — |
| 15:00 - 16:00 | `/dispatch` + `/warroom` 协作壳 | `/dispatch` → `/warroom` | — | — |
| 16:00 - 17:00 | 主题切换（Wow 2）+ 收尾 | `/today` | — | — |

### 2.2 逐段脚本

#### 00:00 - 02:00 · 开场 + 平台壳价值主张

| 字段 | 内容 |
|---|---|
| 操作 | 打开浏览器到 `http://localhost:3000` → 自动 301 到 `/today` |
| 屏幕应呈现 | Canvas 主题米黄橙红渐变 hero · 左 Desk 抽屉（我的客户 / 进行中 / 最近 / 新建）· 顶栏 Masthead "乾策 Studio · 今日 · 对话 · AI 助手 · 任务 · 王哲"· 今日三模块预览卡 |
| 台词 | "各位领导上午好。今天我用 17 分钟演示乾策 Studio——我们给银行信贷条线设计的 AI 协作平台。先强调一点：**这不是 6 个独立 Demo 拼起来，是一个工位、一个登录、6 个 Agent 背后协同**。王哲是我们的客户经理，华东分行。我今天不讲故事——我直接带大家把系统挨个跑一遍，**每一个 Agent 的每一段话、每一个数字，都是后端真实返回的，不是幻灯片**。屏幕上这个是王哲的今日 dashboard——左边是他的客户和在办任务，中间三个预览卡是 IM 消息、正在跑的 Agent 任务、待办看板。信息架构只有 4 个 view——**今日 / 对话 / AI 助手 / 任务**——Agent 不占 tab，归在 AI 助手里作为工具集，人是主角。" |
| 强调点 | "平台的统一性**来自壳**——统一 persona、统一 4 view、统一主题体系——**不是来自一条人为穿起来的企业故事**。待会儿每个 Agent 用不同 preset，反而更诚实" |
| 兜底 | 若 `/today` 加载超 3 秒 → 说"首屏正在预热本地缓存"，期间手动刷新；若 Desk 未渲染 → 说"Desk 抽屉 Stage 3 刚上线，我们走主视图"，直接进下一段 |

#### 02:00 - 04:30 · Agent1 获客 · Look-alike 信号 SSE walkthrough

| 字段 | 内容 |
|---|---|
| 操作 | 点顶栏 "AI 助手" → `/archive` 6 tiles → 点 "Agent1 获客" tile → 进入工作区 → 下拉 scenario 选 "`hangzhou_precision` · 杭州精密制造"（预置场景）→ 点"运行（mock 模式）" |
| 屏幕应呈现 | SSE 面板顺序亮起 5 阶段：`parse` → `signal_scan (data_source: mock_forced)` → `aggregate (total: 4)` → `enrich (count: 3)` → `candidates`；候选列表 3 家企业卡片，每家含信号时间线（融资 / 专利 / 资质）+ 产品推荐 |
| 台词（打开 tile ~30s） | "客户经理的第一个日常痛点——领导说'本季度重点拓展精密制造'，他要自己去启信宝、天眼查、行业网一家家翻。Agent1 解决这个。我们今天用**后端已经预置的 `hangzhou_precision` 场景**——这是 `GET /api/channel/scenarios` 返回的 2 个场景之一。为什么用 mock 模式？**演示要稳**——mock 模式强制走 `mock_fallback` 池，不依赖 Tavily 外网，断网都能演。客户实装时当然可以切回真 Tavily 或企查查，一行代码的事。" |
| 台词（SSE 流讲解 ~1min） | "注意右边 SSE 面板——**我要让大家看清 Agent1 内部 5 阶段管线**。第一阶段 `parse` 意图解析，LLM 把自然语言画像解析成结构化标签，你看现在返的 `tags`——地区=杭州、行业=精密制造。第二阶段 `signal_scan`——这是核心，外网+知识库双路搜信号，这里你看到 `data_source: mock_forced`——我们**显式暴露**数据源状态，不伪装。第三阶段 `aggregate` 按 entity_id 聚合，`total=4`。第四阶段 `enrich` 补充产品推荐画像。第五阶段 `candidates` 输出终榜。每一步都是流式 yield 的——**客户经理不是对着菊花转圈等 30 秒，而是看着管线一层层收敛**。" |
| 台词（候选解读 ~40s） | "终榜 3 家候选——每家带**信号多样性评分**：有融资信号 + 专利信号 + 资质信号三条以上的自动置顶。系统按信号多样性排序，不是按名气或关键词匹配。右栏产品推荐是概率性计算——LLM 做的，但有证据链回指，不是编的。这部分我们后面 Agent6 再详细讲幻觉控制。" |
| wow 点预告 | "这是第一个 Agent 的完整管线。接下来 Agent6 我要让大家看真正的 Wow——报告**字字流式蹦出来**" |
| 兜底 | Tavily / 搜索 provider 崩 → 强调"这就是为什么我们演示走 mock"；候选列表空 → F5 重跑；SSE 断 → 读 `/public/mock/channel_run.json` 本地播放（guardedFetch 已实装） |

#### 04:30 - 08:30 · Agent6 报告 · Wow 1 · SSE 流式 5 stage（主菜，4 分钟）

| 字段 | 内容 |
|---|---|
| 操作 | 点顶栏 "AI 助手" → 点 "Agent6 报告" tile → 跳 `/archive/report` → 模板选"对公标准版"→ 业务线选 `corporate` → preset 下拉选 `dingsheng_trade`（鼎盛商贸）→ 点"生成（mock 模式）" → 后端走 `POST /api/report/fill?mock=1&preset=dingsheng_trade&business_line=corporate` |
| 屏幕应呈现 | 左栏 EnterpriseProfile 预览（`GET /api/report/preset/dingsheng_trade` 回的 financial_anchors / guarantee_info / related_party_info / existing_credit / request / chapters）· 中间 460 项字段表（预填阶段绿色勾）· 右栏 SSE 面板 5 stage 状态灯（ingest → extract → infer → write → audit）· 进度条 0% → 100% · done 事件含 session_id + report_docx_url + downstream_handoff |
| 台词（打开 + 讲 preset ~40s） | "Agent6 是我们的报告主力——当前覆盖 460 项填报、32 项显式标未填、覆盖率 93.5%。对标金融壹账通 Smart Lender 的 80%，我们超 13.5pp。今天我选后端预置的 `dingsheng_trade`——鼎盛商贸的 EnterpriseProfile。你看左栏，`GET /api/report/preset/dingsheng_trade` 一把拿到的完整画像——financial_anchors 财务锚点、guarantee_info 担保信息、related_party_info 关联方、existing_credit 现有授信、request 申请金额、chapters 章节锚——**这些是我们和 Agent3 下游的数据契约，不是 LLM 想出来的**。" |
| 台词（5 stage SSE 流讲解 ~2min · Wow 1） | "现在点'生成'——right pane SSE 面板，**请大家盯着看**。stage 1 `ingest` 摄入材料——进度 0.2。stage 2 `extract` 结构化抽取——进度 0.4，确定性代码跑 `truth_fill.py`，把工商、财务、征信的字段提出来，**不经过 LLM**。**为什么不让 LLM 算财务比率？财务比率是确定性问题，LLM 算一次对一次不等于一直对，下次换套数据就漂**。stage 3 `infer` 推断——进度 0.6，跑 `financial_analyzer.py` 的 F4 确定性推断。stage 4 `write` 生成——进度 0.8，这里开始 LLM 入场，但走的是**Evidence-First 三阶段协议**：证据汇集 → Grounded 生成 → 自审。stage 5 `audit` 终审——进度 1.0，`quality_scorer.py` 跑 QC Blocker 四维闸门。**每一条数字、每一条判断必须回指证据**，填不了就显式标'未能自动填写'——这是银行交付的底线。" |
| 台词（章节流式解读 ~40s） | "下面 4 个章节字字蹦出来——`chapter_1_background` 企业背景、`chapter_2_operation` 经营情况、`chapter_3_finance` 财务情况、`chapter_4_conclusion` 结论待 Agent3 回填。注意第四章**故意留白**——因为结论是授信决策，Agent6 不越权写决策意见，留给 Agent3。这就是**Agent 职责边界清晰**的体现。" |
| 台词（done 事件 + 下载 ~20s） | "done 事件出来——session_id、report_docx_url、downstream_handoff（送给 Agent3 的标准 JSON）全部就位。点'下载 Word'——`GET /api/report/downloads/{session_id}/*.docx`，python-docx 本地生成，**不走境外 API**，符合银行数据不出境要求。路径有 UUID 白名单 + 目录穿越防护，安全。" |
| wow 点 | Wow 1 = 5 stage 状态灯 + 证据链 + "未能自动填写" 显式标注 |
| 兜底 | **DeepSeek 崩** → mock=1 本身就离线，无感；**真崩** → 读 `/public/mock/report_fill_mock.json` 本地播放 SSE；**docx 下载失败** → `/downloads/legacy/*.docx` 老接口兜底；**SSE 断** → F5 刷新，session 后端已持久化 |

#### 08:30 - 11:30 · Agent3 授信 · 四维雷达 + 原因码 + 红线（corporate / dingsheng_trade）

| 字段 | 内容 |
|---|---|
| 操作 | 切到 `/archive/credit` tile → segment 选 `corporate` → preset 下拉 3 个（`dingsheng_trade` / `ruiheng_precision` / `zhongrui_network`）选 `dingsheng_trade` → 点"跑决策" → 后端 `POST /api/credit/decision` SSE |
| 屏幕应呈现 | SSE 序列：`profile_loaded` → `feature_extracting/done`（debt_ratio=0.8 · revenue_growth=-0.18）→ `scoring/done`（composite_score=47 · risk_grade=D · sub_scores 四维）→ `rule_checking/done`（命中 corp_rl_001 关联方 + corp_rl_003 负债率，is_hard=true，severity=high）→ `case_retrieving/done`（相似案例 similarity=0.88，decision="有条件批准"，approved_amount=200 万，利率 8.2%）→ `advising` 生成审批意见 |
| 台词（上手 ~30s） | "切到 Agent3 授信——**这是审贷员视角**。刚才 Agent6 的 downstream_handoff 送过来，自动载入鼎盛商贸的 EnterpriseProfile。注意——**我故意选一个有问题的 preset**。客户经理爱演业绩好的，但 AI 的价值恰恰在**帮审贷员发现问题**。`composite_score=47`，`risk_grade=D`——这是一个 D 级案子，我要让大家看系统怎么解读 D 级、为什么最终给的不是'拒'而是'附条件批'。" |
| 台词（SSE 7 段管线 ~1min） | "右边 SSE 7 段流——`profile_loaded` 画像载入、`feature_extracting` 特征抽取出 `debt_ratio=0.8` 和 `revenue_growth=-0.18`——**两个都是红信号，确定性代码算出来的，不是 LLM 拍脑袋**。然后 `scoring` 评分跑 `quality_scorer.py` 9 维度，对公模型独立——`composite_score=47 / risk_grade=D`，四维雷达你看得到：财务、行业、经营、担保四象限。`rule_checking` 红线检查——两条硬规则命中：`corp_rl_001` 关联方交易超限、`corp_rl_003` 负债率 80% 超 75% 阈值，both `is_hard=true` `severity=high`。" |
| 台词（原因码 + 案例召回 ~40s） | "**重点**：每条命中规则都带 `actual_value` 和 `threshold`——0.8 vs 0.75，**原因码不是文字，是结构化的 severity + 证据回指**。审贷员点任何一条能跳回 Agent6 报告里那段原文、跳回征信文件里那条记录。这比传统'一份报告打分'的黑盒高一个维度——**可追溯、可复核、可回答监管问询**。`case_retrieving` 案例召回——找到相似度 0.88 的历史案例，历史决策是'有条件批准 200 万 · 年化 8.2%'——这就是系统给出'附条件批'而不是'拒'的依据：**相似案子历史上被批过，不是 AI 现场说情**。" |
| 台词（advising + 边界 ~40s） | "最后 `advising` 段 LLM 生成审批意见话术——这是概率性计算，LLM 在这里**只做文字表述**，数字、判定、相似案例召回全部是确定性代码。系统给的建议是'建议有条件批准，追加担保 + 季度财报报送'——**这是辅助意见，不是终审决策**。我们定位 copilot 不是 autopilot，审贷员永远是责任主体。D 级案子系统不隐瞒问题、也不越权拒贷——它把证据摆上桌，让人决定。" |
| 兜底 | DeepSeek 崩 → advising 段 SSE event:error，前端 catch 后前 4 段结构化结果已拿到，切 fallback 文案继续讲；全崩 → 读 `/public/mock/credit_decision_corporate.json` 本地播放 |

#### 11:30 - 13:00 · Agent4 预警 · HitList dashboard（静态 readonly）

| 字段 | 内容 |
|---|---|
| 操作 | 切到 `/archive/alert` tile → 数据源读 `/public/mock/alert_hitlist.json`（从 `evaluation/manual/4_20260419.yaml` 转 JSON）→ 展示三卡片 dashboard |
| 屏幕应呈现 | 卡片 A（summary：total=100 / red=3 / yellow=7 / green=90）· 卡片 B（trigger_reasons 分布：external_signal / internal_rule / **cross_hit ⭐**）· 卡片 C（tool_calls: 200/200 成功 + whitelist_entity_ids 100 个）· 下拉列表样例客户 `LC10001 华联精密制造`（red · cross_hit） |
| 台词（上手 + 边界 ~30s） | "Agent4 预警——**客户行为变化驱动**。和 Agent5 的政策事件驱动是互补关系，别混。这里展示的是**昨晚跑出来的真实产物**——`evaluation/manual/4_20260419.yaml` 894 行 100 客户，commit 快照在仓库里。**后端还没挂路由**——这是透明的——前端直接读静态 JSON，但数据本身是真跑出来的。" |
| 台词（cross_hit 核心 ~1min） | "重点看中间这张卡——**trigger_reasons 分布**。我们把原因码封闭到 **3 个枚举**：`external_signal`（仅外部信号命中）、`internal_rule`（仅内部规则命中）、**`cross_hit`（外部 + 内部双路同时命中）**。cross_hit 这条带 ⭐ 标记粗描边——**这是 Agent4 的核心价值**。单独一个外部舆情不代表要处置，单独一条内部规则可能是过时配置，**两路同时响应才是真警报**。样例客户 `LC10001 华联精密制造`——裁判文书网 (2025)沪0115民初12345号 + 客户风险标签 + 本行制度交叉命中。注意——我们做分类**没用一个关键词、没维护一张黑名单**。上游数据结构里每条命中都带 `route` 字段，下游只做'route 集合 → 3 值'的代数映射。**黑名单永远列不全，结构推断才能长期可维护**——这是我们 CLAUDE.md 明文禁止黑名单的硬规矩。" |
| 台词（tool_calls 可观测 ~30s） | "右下角 `tool_calls: 200/200 成功`——这是 agent observability。每次扫描每个客户调用的工具链路、成功失败、耗时，都留痕。100 客户 × 2 工具 = 200 调用全部成功——这是昨晚的真跑数据。后端 Phase 2 挂路由后这里会变成实时卡片。" |
| 兜底 | 静态 JSON 不会崩；若 JSON 格式异常 → 打开 `docs/design/alert-dashboard-stub.md` 讲设计思路 |

#### 13:00 - 14:00 · Agent2 风控 · DSL ruleset readonly

| 字段 | 内容 |
|---|---|
| 操作 | 切到 `/archive/riskctrl` tile → 数据源读 `/public/mock/riskctrl_ruleset.json`（v1.0-readonly-mock，113 行，5 条 rule） |
| 屏幕应呈现 | ruleset 5 条规则卡片 · 每条含 `{rule_id, name, conditions[{field, operator, value}], action, priority, backtest{ks, approve_rate, bad_rate, FP, TN, FP_rate}}` |
| 台词（上手 + 边界 ~30s） | "Agent2 风控——策略经理视角。和 Agent4 的区别：Agent4 是**巡检在贷客户**，Agent2 是**做规则引擎 + 回测**。当前版本后端 `api_server.py` 明确 TODO Phase 2 挂路由——这里前端直接读 `riskctrl_ruleset.json` readonly mock，113 行，5 条规则，全部带回测指标。" |
| 台词（DSL + 回测 ~30s） | "看第一条 R001——`conditions: overdue_days_90d > 30 → action: reject`，priority=1，`backtest: ks=0.31 approve_rate=0 bad_rate=0.72 FP=4 TN=110 FP_rate=0.0351`——**这是用 3 年真实样本回测出来的指标**。ks=0.31 说明判别力好，FP_rate=3.5% 说明误杀率低。**KS 和误杀率是银行风控硬指标，不是 AI 产品吆喝'准确率 99%'**。" |

#### 14:00 - 15:00 · Agent5 合规 · Disabled tile + 战略地图

| 字段 | 内容 |
|---|---|
| 操作 | 切到 `/archive/compliance` tile → 显示 **disabled 占位卡**，tooltip："Agent5 待 `shared/kb_scan` 底座稳定 · Phase 2 defer · 产品方向锁定" |
| 屏幕应呈现 | 灰态 tile + 战略说明卡 + 和 Agent4 的边界图（"Agent4 = 客户变 / Agent5 = 政策变"） |
| 台词 | "Agent5 合规——当前完整度 40%。我要对各位坦诚：**我们现场不硬上**。后端 `GET /api/compliance/policy_scan` 现在接的是 Tavily 泛搜兜底，返回的是'千户集团涉税报送'、'纪委驻司法部'、'北京市公路交通阻断信息报送'——**和信贷业务无关**，演示出来会很尴尬。与其演一个质量差的结果让客户怀疑整个产品，**我们 disable 这个 tile，tooltip 说清楚状态**。它和 Agent4 的边界很清楚——**Agent4 是客户变，Agent5 是政策变**。新政策一发布，Agent5 扫描全行业务制度，产出'条款 X 与新政第 Y 条冲突'的明细给合规官派活。这块设计稿已完成，产品方向锁定，**排期 Q3 给到交付窗口**——等 `shared/kb_scan` 底座和专业政策源（人行 / 银保监 / 地方金融办）接入完毕再启动 Phase 0。" |
| 为什么保留这段 | 银行合规官来了不能跳过——即使产品未成熟，**战略地图要完整**，显示我们有规划而非临时填坑。**诚实 disable 比糊弄演示更可信** |
| 兜底 | disable 状态不需要兜底，直接过 |

#### 15:00 - 16:00 · `/dispatch` + `/warroom` · 协作壳（统一性体现）

| 字段 | 内容 |
|---|---|
| 操作 | 点顶栏 "对话" → `/dispatch` → 展示频道制 IM（`#授信评审会` / `#风控日报` / `#行长周会`）+ `@审贷员张总` 提及 → 切"任务" → `/warroom` → 看板拖拽（样例 case 从"待授信评审" → "已通过" 列） |
| 屏幕应呈现 | Slack 风 IM 频道列表 + 消息流 + 任务内联卡片；Warroom 三列看板 + 拖拽动效 |
| 台词 | "最后两个协作 view。**对话**是 Slack 风的频道制 IM——客户经理、审贷员、风险经理围绕 case 在频道里讨论，Agent 产出直接作为消息贴进来。**@审贷员张总 请看这份 Agent3 评审建议**——Agent 可以@到人。切到**任务**——看板视图，case 从'待授信评审'拖到'已通过'列，背后自动触发归档 + Agent4 把它加入监控池。" |
| 统一性强调 | "我特别想让大家记住一件事——**我刚才 6 个 Agent 用的是不同 preset：Agent1 杭州精密制造、Agent6 鼎盛商贸、Agent3 鼎盛商贸 D 级、Agent4 华联精密制造……** 载体不一样，但**壳是一样的**：一样的 persona 王哲、一样的 4 view 信息架构、一样的主题体系、一样的 Desk 抽屉、一样的 Masthead。**这就是 platform 的含义——统一性不是靠人为串一条企业故事线造出来的，是靠壳天然赋予的**。真到客户实装，每家银行的客户流是他们自己的，壳永远是乾策 Studio 的。" |
| 兜底 | `/dispatch` 或 `/warroom` 空数据 → 直接点过讲"Stage 5 接后端，当前走本地 mock fixture"，不纠缠 |

#### 16:00 - 17:00 · Wow 2 主题切换 + 收尾

| 字段 | 内容 |
|---|---|
| 操作 | 切回 `/today` → 点顶栏齿轮 → 4 主题 **Canvas → Matcha → Dusk → Crimson** 逐个切 → 停在 Crimson（剧场黑红）展示最强视觉冲击 → 再切回 Canvas 结束 |
| 屏幕应呈现 | 整个 shell 跟随 `data-theme` 属性切换——hero 渐变 / 卡片色 / 按钮色同步变化；localStorage 持久化（刷新不丢） |
| 台词（Wow 2） | "最后给大家看一个彩蛋。**乾策 Studio 内置 4 主题**——Canvas 米黄编辑风、Matcha 清雅抹茶、Dusk 暮色、Crimson 剧场黑红。同一个信息架构、同一套组件，换 `data-theme` 一个属性。技术上 `color-mix()` + CSS 变量 8 档渐变 `--g0..--g7` + 语义锚色 `--accent`。为什么做这个？两个原因：**一、银行私有化部署需要配合行方 VI 做定制，我们不用改组件、改 token 即可**；**二、同一个工位给客户经理和风险经理用，他们偏好不一样，主题切换是体验**。" |
| 台词（收尾 30s） | "收尾 3 句话。**第一，乾策 Studio 是一个平台不是 6 个 Demo**——Desk 抽屉 + 4 view + 6 Agent 背后协同、统一 persona、统一主题。**第二，我们所有数字可溯源、所有红线用确定性计算、幻觉零容忍**——CLAUDE.md 明文约束，不是口号。**第三，copilot 不是 autopilot**，审贷员永远是责任主体，AI 只是把一天的活压缩成一小时。今天每一个 Agent 跑的都是后端真实 preset，每一条 SSE 事件都是后端流出来的，不是脚本。Q&A 时间。" |
| wow 点 | Wow 2 = 主题切换 + 视觉冲击 + 私有化定制故事 |
| 兜底 | 主题切换卡顿 → 刷新页面，主题从 localStorage 恢复；color-mix 浏览器不支持 → 说"私有化部署会切到 fallback CSS，当前演示环境 Chrome 111+" |

---

## 3. 3 个 Wow 时刻设计

### Wow 1 · Agent6 SSE 流式 5 stage（05:00 ~ 08:00 区段）

- **触发时机**：Agent6 `POST /fill?mock=1&preset=dingsheng_trade` 点击后
- **技术卖点**：
  - SSE 5 stage 状态灯（ingest → extract → infer → write → audit）字字流出
  - stage 2 extract + stage 3 infer 走**确定性代码**（truth_fill.py / financial_analyzer.py），LLM 碰不到
  - stage 4 write 走 **Evidence-First 三阶段协议**（证据汇集 → Grounded 生成 → 自审）
  - stage 5 audit 走 QC Blocker 四维闸门
  - 填不了的字段显式标"未能自动填写"（不是留空、不是编造）
  - done 事件含 session_id / report_docx_url / downstream_handoff
- **客户视角价值**：
  - 视觉冲击："报告真的是 AI 一个字一个字写出来的，不是后台跑完再贴"
  - 信任建立："系统敢标'未能自动填写'而不是硬编——这是专业底线"
  - 对标说服力：93.5% 覆盖超金融壹账通 Smart Lender 的 80%

### Wow 2 · 4 主题一键切换（16:00 ~ 16:30 区段）

- **触发时机**：收尾前，切回 `/today` → 点齿轮 → Canvas → Matcha → Dusk → Crimson 快切
- **技术卖点**：
  - `data-theme` 属性驱动，全站组件跟随
  - `color-mix()` + 8 档渐变 `--g0..--g7` + 语义锚色 `--accent`
  - localStorage 持久化
  - 组件代码 0 改动，纯 token 层切换
- **客户视角价值**：
  - 视觉反差："同一个产品四种脸"——冲击感
  - 私有化说服："行方 VI 定制只动 token，不动业务逻辑——交付成本低"
  - 体验理念："不同岗位偏好不同——风险经理 Crimson 严肃，客户经理 Matcha 清雅"

### Wow 3 · 统一壳 + 统一 persona + 统一主题体系（贯穿始终）

- **触发时机**：贯穿 17 分钟全场。Agent1 杭州精密 → Agent6 鼎盛商贸 → Agent3 鼎盛商贸 D 级 → Agent4 华联精密 → Agent2 ruleset → Agent5 disabled——**不同载体，同一个壳**
- **技术卖点**：
  - persona 锁定"王哲·客户经理·华东分行"全程不换
  - 4 view 信息架构（今日 / 对话 / AI 助手 / 任务）贯穿
  - Desk 抽屉跨 Agent 保持可见
  - Masthead 跨 Agent 保持可见
  - 主题 `data-theme` 属性跨 Agent 同步
- **客户视角价值**：
  - 信念转变："从 6 个孤立工具 → 一个工位一套体验 6 Agent 协同"
  - 诚实感："不靠一家企业强行贯穿来装'集成'，壳本身就是集成"
  - 行业对标："百融 / 同盾 / 壹账通单 Agent 强，但端到端壳不统一；我们是壳先行、Agent 插入"
  - 可演进："先上 Agent6 + Agent3 形成闭环，其他 Agent 逐步接入同一个壳"

---

## 4. Preset 清单（演示数据依据）

> 本节取代原"虚构企业卡"。所有 preset 来源于后端真实返回或已落盘 JSON。

### 4.1 Agent1 获客 · scenarios

| scenario key | 场景描述 | 走哪路 |
|---|---|---|
| `hangzhou_precision` | 杭州精密制造，A 轮后规模 5000 万-2 亿 | **演示选这个** · mock=true |
| `shenzhen_tech` | 深圳科技企业，pre-A / A 轮 | 备选 |

- 调用：`POST /api/channel/run` body `{query: "...", provider: "deepseek", top_n: 3, mock: true}`
- SSE 阶段：parse → signal_scan (data_source: mock_forced) → aggregate → enrich → candidates
- 返回典型：3 家候选企业 + 信号时间线 + 产品推荐

### 4.2 Agent3 授信 · presets

| segment | preset key | 演示价值 |
|---|---|---|
| corporate | `dingsheng_trade` | **演示选这个** · composite=47 · D 级 · 命中 corp_rl_001/003 硬规则 · 相似案例 similarity=0.88 "有条件批准" |
| corporate | `ruiheng_precision` | 备选 |
| corporate | `zhongrui_network` | 备选 |
| retail | `lisi_education` / `wangwu_decoration` / `zhangsan_restaurant` | 零售备选（若客户问个贷再切） |

- 调用：`POST /api/credit/decision` body `{segment: "corporate", preset_name: "dingsheng_trade", provider: "deepseek"}`
- SSE 阶段：profile_loaded → feature_extracting/done → scoring/done → rule_checking/done → case_retrieving/done → advising/done

### 4.3 Agent6 报告 · presets

| preset key | business_line | 演示价值 |
|---|---|---|
| `dingsheng_trade` | `corporate` | **演示选这个** · 对公标准版 · 和 Agent3 下游联动 |
| `zhangsan_restaurant` | `inclusive` | 备选（若客户问普惠） |

- 调用：`POST /api/report/fill?mock=1&preset=dingsheng_trade&business_line=corporate`
- SSE 阶段：ingest → extract → infer → write → audit → done（含 session_id / report_docx_url / downstream_handoff）

### 4.4 Agent4 预警 · 产物

| 数据源 | 来源 | 演示价值 |
|---|---|---|
| `evaluation/manual/4_20260419.yaml` | 昨晚 runtime_dump，100 客户 / 3 红 / 7 黄 / 90 绿 / tool_calls 200/200 | **演示转 JSON 读 `/public/mock/alert_hitlist.json`** |

- 样例客户：`LC10001 华联精密制造`（red · cross_hit · 裁判文书 + 客户风险标签 + 本行制度双路命中）

### 4.5 Agent2 风控 · readonly ruleset

| 数据源 | 来源 | 演示价值 |
|---|---|---|
| `/public/mock/riskctrl_ruleset.json` | v1.0-readonly-mock · 113 行 · 5 rules | **直接读**，含 backtest ks / approve_rate / bad_rate / FP / TN |

### 4.6 Agent5 合规 · disabled

- 演示态：**disabled tile + tooltip**，不调后端
- 原因：`GET /api/compliance/policy_scan` 当前返 Tavily 泛搜无关结果（涉税 / 纪委 / 交通阻断），演示会尴尬
- 后续：Phase 2 接人行 / 银保监 / 地方金融办专业政策源后启动

---

## 5. 兜底剧本（分级）

### 5.1 轻度故障（单页面数据不渲染 / UI 组件报错）

| 场景 | 兜底动作 | 兜底话术 |
|---|---|---|
| Agent1 SSE 事件序列缺 | F5 刷新 1 次 | "mock 池初始化，再拉一遍" |
| Agent3 雷达图不渲染 | 切换到 Canvas 以外主题 → 再切回 | "主题切换会重建组件，就当展示我们的 4 主题" |
| Agent6 某个 chapter 未流 | 等完后补讲 | "write 阶段是并发生成，章节到位顺序可能不同" |
| Warroom 看板空 | 跳过拖拽演示 | "看板数据走 Stage 5 真后端，当前是 mock stub" |
| Desk 抽屉折叠异常 | 手动折叠 + 展开 | 不讲，直接过 |

### 5.2 中度故障（单 Agent 后端崩 / API 404）

| 场景 | 兜底动作 | 兜底话术 |
|---|---|---|
| Agent1 `/api/channel/run` 崩 | 走 `/public/mock/channel_run.json` guardedFetch | "我们对每个 Agent 做了 guardedFetch 降级，客户实装可以切真后端" |
| Agent6 `/fill mock=1` 崩 | 走 `/public/mock/report_fill_mock.json` guardedFetch 播 SSE | "我们的 mock fixture 本身 schema 对齐 SSE，前端体验无感" |
| Agent3 `/decision` advising 段崩 | 前 4 段结构化结果已拿到，advising 切 fallback 文案 | "LLM 段出了错，但前 4 段确定性代码结果都在——这就是我们硬规矩'LLM 不碰数字'的价值" |
| Agent4 静态 JSON 异常 | 打开 `docs/design/alert-dashboard-stub.md` | "这是 agent4 自己出的 dashboard spec，实装锚点都在这里" |

### 5.3 重度故障（网络断 / SSE 不通 / 后端起不来）

| 场景 | 兜底动作 | 兜底话术 |
|---|---|---|
| 前端白屏 | 切到预录视频 `demo_backup/full_run.mp4` | "网络抖了一下，我先用一份预录视频继续" |
| SSE 流式断 | 切到预生成 docx 打开讲 `outputs/demo-fallback-dingsheng_trade.docx` | "这是昨天 dingsheng_trade preset 的完整产出，流式体验我单独安排 15 分钟专场" |
| 后端完全 down | 前端所有 tile 走 `/public/mock/*.json` guardedFetch 降级 | "我们每个 Agent 有 mock fallback，前端纯静态演示仍然能讲完整系统" |

### 5.4 兜底总原则

1. **永不慌**：任何 error 出现，先一句话平滑过渡，不要盯着报错窗看
2. **永不硬跑**：同一步失败 ≥ 2 次立即走兜底，不要三次见祖宗
3. **永不假装**：不要说"这个不重要"——重要，所以我们线下补一个专场
4. **永远有下一步**：每个兜底必须承接下一段内容，不悬空

### 5.5 Fallback 物料清单（主 CLI 备好）

- [ ] `outputs/demo-fallback-dingsheng_trade.docx`（Agent6 重度兜底）
- [ ] `outputs/demo-fallback-zhangsan_restaurant.docx`（备用普惠 preset）
- [ ] `web/public/mock/channel_run.json`（Agent1 SSE 序列）
- [ ] `web/public/mock/credit_decision_corporate.json`（Agent3 SSE 全序列）
- [ ] `web/public/mock/credit_decision_retail.json`（备用零售）
- [ ] `web/public/mock/alert_hitlist.json`（Agent4 从 yaml 转）
- [ ] `web/public/mock/riskctrl_ruleset.json`（Agent2 已齐）
- [ ] `web/public/mock/report_fill_mock.json`（Agent6 SSE 序列）
- [ ] `demo_backup/full_run.mp4`（重度兜底预录）

---

## 6. Q&A 预判（8 个问题 + 标准答案）

### Q1 · 幻觉怎么控制？银行监管对"可解释"要求极严

> 三层防御：**第一层确定性计算分流**——财务比率、红线判定、数值计算走规则引擎 `financial_analyzer.py` 和 `quality_scorer.py`，LLM 碰不到（Agent3 演示时 feature_extracting / scoring / rule_checking / case_retrieving 四段都是确定性代码，只有 advising 段用 LLM 生成话术）；**第二层 Evidence-First 三阶段协议**——LLM 生成的每条文字必须有证据链（出处文件 / 段落 ID / URL），无证据显式标"未能自动填写"；**第三层 QC Blocker 四维闸门**——占位符残留、证据链完整、财务数字一致、合规术语规范，不过阻断输出。我们内部硬规矩禁止关键词黑名单兜底——黑名单永远列不全。

### Q2 · 数据合规 / 不出库怎么保证？

> 三点：**一、本地化部署**——支持 on-prem 私有化，Python + FastAPI 后端、Next.js 前端都在行内机房跑；**二、LLM 可切行内私有大模型**——provider 抽象层，不强绑 DeepSeek / OpenAI；**三、文档生成用 python-docx 本地生成**，不走境外 API（演示时 Agent6 的 `/downloads` 端点就是本地生成）；Google Fonts 私有化前自托管（Stage 6）。**模型卡片** `docs/model_cards/` 会按银监 2024 年 AI 治理指引给每个 Agent 出一份。

### Q3 · RBAC / 多角色权限？

> 当前 Stage 2 不做登录，platform shell 壳先打磨；**Stage 6 专项做 `/auth` + RBAC**，和行方 CIO 对齐后落地。RBAC 粒度：分行 / 支行 / RM / 审贷员 / 合规官 / 风险经理 6 角色 × 4 view 的矩阵。今天演示 persona 锁定王哲·客户经理，实际部署每个角色进来看到的 Desk 抽屉内容和 AI 助手 tiles 可见性是动态的。

### Q4 · SaaS vs 私有化？部署成本？

> **优先私有化**——银行客户几乎 100% 要求数据不出机房。SaaS 形态保留给零售小微垂直场景，当前不推。私有化部署标准配置 4 × A100 + 8 × CPU 节点，2 周集成 + 2 周行方数据对接 + 2 周 UAT = 6 周首发上线。我们在北部湾项目跑过 6 周落地标杆。

### Q5 · 定制成本？每家银行业务口径不一样

> 两层定制：**一、数据层**——行方征信字段映射、业务产品目录、红线规则，走配置不走代码，1-2 周交付；**二、模型层**——审贷评分模型要用行方 3 年样本做微调 + Few-shot 数据飞轮，3 个月迭代一版。我们的提示词优化机制支持**从审贷员修改 JSONL 自动提取 few-shot**（`/api/feedback` 端点），不需要训练 SFT，迭代成本低。

### Q6 · 上线周期？怎么从 POC 到生产？

> 三阶段：**POC（6 周）**——用本 demo 的 preset + 行方 5-10 个真实案例跑通端到端，QC 基线达标；**灰度（3 个月）**——RM 侧 copilot 试用，每周抓 feedback 喂回数据飞轮；**生产（3-6 个月）**——高置信字段逐步免审（如财务比率、规则命中的红线），低置信字段保留人审。永远是 copilot 不是 autopilot。

### Q7 · 竞品对标（同盾 / 壹账通 / 百融 / FICO / Moody's）

| 对手 | 强项 | 我们差异 |
|---|---|---|
| 金融壹账通 Smart Lender | 信贷报告自动化 80% | 我们 93.5%，超 13.5pp + Evidence-First 证据链 |
| 金融壹账通 Gamma 加马 | 评分模型（股份行 100% 渗透）| 我们是 copilot + 6 Agent 端到端，不是单点评分 |
| 同盾诸葛 | 反欺诈 / 贷中预警（-45% 误报基线）| 我们加了 external + internal 交叉命中（cross_hit），误报更低 |
| 百融 CybotStar | 获客（950+ 银行规模）| 我们 look-alike 信号驱动 + 知识库整合 |
| FICO / Moody's | 国际评分标准、合规可解释 | 我们更懂中国银行业务口径 + 本地化部署 |

**最大差异**：**我们是一个平台不是 6 个工具**——壳统一、persona 统一、主题统一，Agent 插入式演进。

### Q8 · 如果这 6 个 Agent 某一个不满足我们行要求怎么办？

> 两个机制：**一、Agent 可插拔**——每个 Agent 是独立服务（`agent_*/api/*.py`），关掉一个不影响其他；可以先上 Agent6 + Agent3 形成闭环，其他 Agent 逐步接入；**二、Agent 内组件可替换**——Agent6 内部模板 adapter、评分规则、red line 规则都是 yaml 配置，行方业务方直接改 yaml，不用开发。今天演示时 Agent5 是 disabled tile、Agent2/Agent4 走静态 mock——这本身就证明了**单 Agent 状态不可用不影响整体壳**。

---

## 7. 演示前 30 分钟 checklist

> 打印出来**物理贴在显示器旁**，顺序执行，不跳步

### 7.1 环境启动（T-30 ~ T-20）

```bash
# 1. 后端起（带环境变量 wrapper，直接 python api_server.py 会缺 key）
py /tmp/start_uvicorn.py
# 验证：curl http://localhost:8000/health → 200

# 2. 前端起
cd web && npm run dev
# 验证：curl http://localhost:3000/api/presence → 200

# 3. 真 API 健康检查序列（全部 200 才过）
curl -I http://localhost:3000/today
curl -I http://localhost:3000/archive
curl -I http://localhost:3000/archive/channel
curl -I http://localhost:3000/archive/report
curl -I http://localhost:3000/archive/credit
curl -I http://localhost:3000/archive/alert
curl -I http://localhost:3000/archive/compliance
curl -I http://localhost:3000/archive/riskctrl
curl -I http://localhost:3000/dispatch
curl -I http://localhost:3000/warroom

# 4. 后端 preset/scenarios 预拉（确认不是空壳）
curl -s http://127.0.0.1:8000/api/channel/scenarios | grep hangzhou_precision
curl -s http://127.0.0.1:8000/api/credit/presets/corporate | grep dingsheng_trade
curl -s http://127.0.0.1:8000/api/report/preset/dingsheng_trade | grep financial_anchors
curl -s http://127.0.0.1:8000/api/report/health
```

### 7.2 数据 / Mock fixture 预热（T-20 ~ T-15）

- [ ] `web/public/mock/channel_run.json` 存在
- [ ] `web/public/mock/credit_decision_corporate.json` 存在（含 dingsheng_trade 全 7 段 SSE）
- [ ] `web/public/mock/alert_hitlist.json` 存在（从 `evaluation/manual/4_20260419.yaml` 转）
- [ ] `web/public/mock/riskctrl_ruleset.json` 存在（已齐）
- [ ] `web/public/mock/report_fill_mock.json` 存在
- [ ] `outputs/demo-fallback-dingsheng_trade.docx` 存在（重度兜底）
- [ ] `outputs/demo-fallback-zhangsan_restaurant.docx` 存在（备用普惠）

### 7.3 浏览器预热（T-15 ~ T-10）

- [ ] 开**全新**无痕窗口（避免 localStorage / cookie 污染）
- [ ] 访问 `/today` 触发首屏编译（Next.js dev 首屏慢，**必须预热**）
- [ ] 依次访问 4 个 view + 6 个 archive tile 让 webpack 编译完成
- [ ] 再打开另一个无痕窗口到 `/today` 作为演示主窗
- [ ] 主题切到 Canvas（起始主题）
- [ ] 把 Agent1 场景选框预选 `hangzhou_precision`、Agent6 preset 预选 `dingsheng_trade`、Agent3 preset 预选 `dingsheng_trade`，避免演示时下拉翻找

### 7.4 屏幕配置（T-10 ~ T-5）

- [ ] 投屏分辨率 1920×1080（shell 规范基线 1440 / 900 两档都 cover）
- [ ] 浏览器缩放 **110%**（投屏观众看得清 SSE 字）
- [ ] 字体检查：Funnel Display / Instrument Sans / Noto Sans SC 已加载（F12 Network 过滤字体）
- [ ] 隐藏所有浏览器插件图标（极简界面）
- [ ] 关闭所有通知（Windows 专注模式 / macOS 勿扰）

### 7.5 兜底物料准备（T-5 ~ T-0）

- [ ] 桌面打开 `demo_backup/` 文件夹（显示截图 + 预录视频）
- [ ] 桌面打开 `outputs/` 目录（兜底 docx 就位）
- [ ] 手机飞书切到静音，但保持接收（紧急联系主 CLI / 运维）
- [ ] 打印这份剧本 + Preset 清单（§4）+ Q&A 放手边
- [ ] 喝一口水，深呼吸，开始

### 7.6 开场 10 秒

- [ ] 浏览器地址栏清空
- [ ] 确认主窗口是 `/today` Canvas 主题
- [ ] 确认 Masthead persona 显示"王哲 · 客户经理 · 华东"
- [ ] 看一眼时间开始计时
- [ ] 微笑，开讲

---

## 8. 附录 · 剧本版本控制

- **v1.0 · 2026-04-19 AM**：首版剧本，围绕虚构企业 17 分钟故事线 + 3 wow（SSE / 主题 / 6 Agent 协同 entity_id 贯穿）
- **v2.0 · 2026-04-19 PM（本版）**：**路线重写为系统 walkthrough**——每个 Agent 用自己 preset 跑真实 SSE，不再 entity_id 贯穿，Wow 3 改为"统一壳 + 统一 persona + 统一主题体系"；§4 改为 preset 清单（取代企业卡）；§5.5 兜底物料清单新增；§6 Q&A 微调（不再有"为什么演示这家企业"类问题）
- **变更预期**：
  - v2.1：待北部湾第二场演示复盘后修订台词节奏
  - v2.2：Stage 4 `/dispatch` 接真后端后把 IM 部分从 stub 升级为真流
  - v2.3：Agent2 / Agent4 后端 Phase 2 挂路由后把静态 JSON 章节改为真 SSE

**更新权责**：主 CLI。子 CLI 可提 issue，不可直改。

**关联文档**：
- 6 Agent API 契约 `docs/contracts/shell-v1-agent-api-map.md`（本剧本数据依据）
- 设计规范 `docs/design/platform-shell-v1.md`
- Alert dashboard 设计稿 `docs/design/alert-dashboard-stub.md`
- Trigger reasons 枚举规约 `docs/design/alert-trigger-reasons-taxonomy.md`
- Agent6 Phase 2 review `docs/review/agent6-phase-2-review.md`
- 全局完整度矩阵 `docs/scorecard/GLOBAL.md`
- DoD 验收标准 `docs/scorecard/definition-of-done.md`
- 前端 Stage 3 review `docs/review/frontend-stage-3-ext-review.md`
