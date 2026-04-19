# Stage 5 · 6 Workspace 功能需求规范

> **致设计 CC**：本文档只讲**功能点、数据字段、交互行为、后端端点、工程现状**。不包含任何布局、配色、动画、字体、icon 相关建议——这些由你基于 `design_mockups/rm-assistant-final-2026-04-19.html` 的 tokens 自主设计。
> **输出物**：6 份独立 HTML mockup，放 `design_mockups/` 目录，每份命名 `workspace-<agent>-YYYY-MM-DD.html`。
> **Tokens 源**：`design_mockups/rm-assistant-final-2026-04-19.html`（字体栈 / 圆角 / 5 主题渐变 / 6 功能色 / 动画 keyframe / Desk / Masthead / Float-badge 完全继承，不要重画壳）。

---

## 0. 通用约定（6 workspace 共同遵守）

### 0.1 进入路径
6 workspace 通过 `/archive` 6 tile 点击进入，路由 `/archive/{agent}`，agent ∈ `{report, channel, credit, alert, compliance, riskctrl}`。

### 0.2 顶部区（已由外壳 `ArchiveAgentShell` 提供，你复用）
- Eyebrow：`{code} · {eyebrowLabel}`（如 `M01 · 信贷报告助手`）
- H1：中文 agent 名（如 `信贷报告助手`）
- Lede：角色一句话描述
- 右上：`← 返回助手目录` 跳 `/archive`

### 0.3 功能色（已在 `--t-*` tokens 定义）
- Agent6 报告：`--t-report` 棕赭
- Agent1 获客：`--t-channel` 青绿
- Agent3 授信：`--t-credit` 青蓝
- Agent4 预警：`--t-alert` 赭红
- Agent5 合规：`--t-compli` 墨绿
- Agent2 风控：`--t-riskctrl` 绛紫

### 0.4 异步反馈（所有 workspace 必须实现）
- 上传：进度百分比 + 文件名 + 成功/失败 toast
- SSE 流：阶段性事件流，每事件一条可读进度行
- Loading：骨架屏（非 spinner）
- Error：toast + 详细错误面板（可复制）
- 降级：显式「未能自动填写」标签、fallback 下载兜底

### 0.5 工程现状诚实标注
Agent4 预警、Agent2 风控 **当前尚无 FastAPI 端点**（以 Gradio/模块代码存在），mockup 先按"已有 mock fixture"做演示态，后端接入是下一阶段。其他 4 个 agent 有真实 API 端点可调。

### 0.6 通用 preset 企业池（演示主力）
- 对公（corporate）：`dingsheng_trade`（鼎盛商贸·建材批发）、`ruiheng_precision`（锐恒精密·制造）、`zhongrui_network`（中睿网络·互联网）
- 普惠/对私（inclusive / private）：`lisi_education`（李四·教培）、`wangwu_decoration`（王五·装修）
- 获客 look-alike：`hangzhou_precision`（杭州精密制造锚点）、`shenzhen_tech`（深圳科创锚点）

---

## 1. Agent6 · 信贷报告助手 · `/archive/report`

### 1.1 角色定位
客户经理把企业材料 + 模板丢进来，10 分钟产出银行信贷申报书初稿（Word）。460 项字段填写，32 项显式标未填；覆盖率 93.5%。替代审贷员手工粘贴 2 小时的工作。

### 1.2 必须包含的 UI 模块

#### 模块 A · 材料上传区
- **功能**：同时上传多份企业材料文件 + 一份申报书模板
- **输入字段**：
  - `files[]`：**多文件上传**，支持 `.pdf .docx .xlsx .txt`，单文件 ≤ 20MB，总 ≤ 200MB
  - `template_file`：**单文件上传可选**，支持 `.docx`；不传则用业务线对应的内置默认模板
- **业务线下拉** `business_line`：`corporate`（对公）/ `inclusive`（普惠）/ `private`（对私）
- **预置案例下拉**（演示用）`preset`：从上文 preset 企业池中选一个，点击后自动填充材料（跳过上传）
- **Mock 开关** `mock`：默认 0；toggle 到 1 走预置 fixture，5 段假进度+done，不跑真 LLM
- **后端端点**：`POST /api/report/fill?mock={0|1}&preset={key}&business_line={key}`（multipart/form-data 传 files 和 template_file）

#### 模块 B · 生成进度 SSE 流区
- **功能**：订阅报告生成过程的三阶段 Evidence 协议事件，实时展示
- **SSE 事件** 3 阶段：
  1. `evidence_assembly`（证据组装）：LLM 逐数据点在 4 个材料源查找，流式输出 `✓ 数据点: 值 [来源]` 或 `✗ 未找到`
  2. `grounded_generation`（锚定撰写）：LLM 仅用证据清单写正文，缺失数据按"需补充 X"具体列项
  3. `self_audit_gate`（自审门控）：验证数字出处、检测重复/矛盾
- **每阶段状态**：pending / running / done / error
- **事件数据 shape**（参考 `web/public/mock/report_fill_mock.json`）：`{stage, step, msg, section?, field?}`
- **Done 事件**：`{session_id, report_docx_url, enterprise_profile, pending_questions[]}`

#### 模块 C · 生成结果展示区
- **功能**：done 后展示企业画像 + 报告预览 + 下载
- **展示数据**：
  - `enterprise_profile`：企业名、注册资本、行业、实控人、主营业务等结构化卡片（读 `/api/report/preset/{key}` 返回的 shape）
  - 字段填写覆盖率：`填写 N 项 / 未填 M 项 / 覆盖率 93.5%`（标"未能自动填写"的字段单独列出）
  - `report_docx_url`：下载按钮 → `GET /api/report/downloads/{session_id}/{filename}`
- **兜底**：DeepSeek 崩时，下载端点切到 `GET /api/report/downloads/legacy/fallback_dingsheng_trade.docx`（预生成 fallback，63KB valid docx）

#### 模块 D · 外因追问（refine）区
- **功能**：报告生成后若有 `pending_questions[]`，展示追问卡片；客户经理补答后局部重跑
- **输入字段**：`answers[]: [{id, value}]`
- **后端端点**：`POST /api/report/refine`（body: `{session_id, answers[]}`），SSE 流式返回，只重跑 external_factor 相关 section
- **现状**：后端当前是 stub，只推 write/audit 两个假事件 + 返回原 profile（演示中可用）

#### 模块 E · 状态灯
- **功能**：页面顶部/角落一盏灯，显示 LLM 是否配置可用
- **后端端点**：`GET /api/report/health` → 返回布尔
- **视觉反馈**：绿（可用） / 黄（降级 mock） / 红（不可用）

### 1.3 非功能要求
- 中文 IME 输入稳定（上传文件名含中文不乱码）
- SSE 断线自动重连，已推事件不重复
- `files[]` 删除/替换单文件（上传队列可编辑）
- 全流程超时保护：材料上传 60s、SSE 生成总时长 ≤ 15min

---

## 2. Agent1 · 智能获客助手 · `/archive/channel`

### 2.1 角色定位
客户经理给一段画像描述（"找浙江做精密制造的小微"），Agent1 从知识库 + 外网搜相似企业（look-alike），返回候选企业清单 + 信号时间线 + 产品推荐。

### 2.2 必须包含的 UI 模块

#### 模块 A · 场景选择区
- **功能**：选一个预置获客场景作为起点（比自然语言更结构化）
- **后端端点**：`GET /api/channel/scenarios`
- **当前场景池**（仅 2 个，后端现状）：
  1. `hangzhou_precision`：杭州精密制造 look-alike（浙江精密制造小微 + 专精特新小巨人政策）
  2. `shenzhen_tech`：深圳/长三角科创 look-alike（科技型中小企业 + A 轮融资阶段）
- **交互**：场景卡片点击选中；选中后下面画像描述 textarea 自动填充场景默认 query

#### 模块 B · 画像描述输入
- **输入字段**：
  - `query`：**多行文本**，自然语言画像描述（必填，≤ 500 字）
  - `top_n`：返回候选数量（默认 8，范围 1-20）
  - `provider`：LLM provider（默认 `deepseek`，下拉或隐藏）
  - `api_key`：provider key（可选，留空用后端 env）
  - `mock`：bool，切预置 fixture

#### 模块 C · 实时扫描 SSE 流区
- **功能**：订阅全渠道获客扫描的阶段事件
- **后端端点**：`POST /api/channel/run`（body: ChannelRunRequest）
- **事件数据 shape**（参考 `web/public/mock/channel_run.json`）：`{stage, msg, candidate?, signal?}`
- **典型阶段**：知识库匹配 → 外网搜索（Tavily）→ 相似度排序 → 信号汇总
- **无 TAVILY_KEY 自动降级 mock_fallback**

#### 模块 D · 候选企业清单
- **Done 事件**：`{candidates[], metrics{}}`
- **每条候选展示**：
  - 企业名、统一社会信用代码、注册资本、主营业务
  - 相似度评分
  - 信号标签：政策驱动 / 融资事件 / 供应链上下游 / 地理邻近 / 资质合规 等（多标签可叠加）
  - 推荐产品：匹配该企业的信贷产品名 + 额度建议
- **交互**：点企业名展开信号时间线（近 12 月事件按时间排序，每事件含标题 / 时间 / 来源链接）；可单选/多选加入"意向池"

#### 模块 E · 候选导出
- **功能**：导出选中企业为 CSV 或直接下派到 Agent3 授信
- **交互**：批量勾选 + 两个 action 按钮

---

## 3. Agent3 · 授信决策助手 · `/archive/credit`

### 3.1 角色定位
审贷会现场用。Agent6 产出的 ReportJSON（或手动选 preset）进来，出四维评分 + 额度/期限建议 + 红线命中清单。对公 / 普惠 / 对私三板块同结构不同评分模型。

### 3.2 必须包含的 UI 模块

#### 模块 A · 板块 + 案例选择
- **板块选择** `segment`：`corporate`（对公）/ `inclusive`（普惠）/ `private`（对私）
- **预置案例下拉** `preset_name`：
  - **后端端点**：`GET /api/credit/presets/{segment}`
  - 对公 3 个：`dingsheng_trade` / `ruiheng_precision` / `zhongrui_network`
  - 对私 2 个：`lisi_education` / `wangwu_decoration`
- **交互**：选板块后案例下拉 lazy load；选案例后自动 fetch 该企业的档案预览

#### 模块 B · 四维评分触发
- **触发按钮** 「生成授信决策」：
  - **后端端点**：`POST /api/credit/decision`
  - Body：`{segment, preset_name, provider?, api_key?}`
  - 返回 SSE 流式事件

#### 模块 C · 四维评分展示
- **对公四维**（权重）：
  1. `financial_score` 财务 (35%)：资产负债率、营收增长、净利率、流动比率、应收周转、现金流质量
  2. `industry_score` 行业 (15%)：行业景气度、政策敏感性、周期性、黑名单
  3. `operational_score` 经营 (25%)：成立年限、营收规模、现金流覆盖、客户集中度、员工规模
  4. `guarantee_score` 担保 (25%)：覆盖率、担保物类型、担保人强度
- **对私四维**（权重）：
  1. `repayment_capacity` 还款能力 (30%)
  2. `repayment_willingness` 还款意愿 (25%)
  3. `stability` 稳定性 (25%)
  4. `collateral` 担保品 (20%)
- **每维展示**：维度名 + 分值 (0-100) + 子项明细 + 贡献度
- **综合分** `composite`：加权总分 (0-100) + 等级（A/B/C/D）

#### 模块 D · 红线命中清单
- **数据**：`hits[]: [{rule_id, rule_name, evidence, severity}]`
- **规则**：corp_rl_001 / corp_rl_002 ... 每条有 id / 名称 / 触发证据
- **视觉**：红线数字化徽章（如"命中 2 条红线"），展开看每条详情

#### 模块 E · 建议区
- **数据**：建议额度 / 期限 / 利率浮动、匹配产品名
- **案例召回**：历史相似案例（含结果）3-5 条

**Mock fixture**：`web/public/mock/credit_decision_corporate.json`（271 行，含完整 SSE 事件流 + 评分 shape）

---

## 4. Agent4 · 贷中预警助手 · `/archive/alert`

### 4.1 角色定位
在贷客户行为变化驱动。每日批量扫全量在贷客户，按红/黄/绿三级分级，推"今日关注榜单"。外部（舆情/公示/法院）+ 内部（交易异常）双路交叉命中。

### 4.2 工程现状诚实标注
**当前无 FastAPI 端点**。核心流程以 Gradio Demo 形态存在（`agent_alert/app.py`）。API 接入是下一阶段。Mockup 完全基于 `web/public/mock/alert_hitlist.json` 做演示态。

### 4.3 必须包含的 UI 模块

#### 模块 A · 扫描批次触发
- **输入字段**：
  - `scenario`：客户场景名（如 `micro_credit_100` — 100 个小微在贷客户）
  - `ruleset_version`：规则库版本（下拉，选定版或 draft）
- **触发按钮**「启动扫描」：启动批量扫描流程
- **后端状态**：待开发（先做 mock fixture 驱动的假扫描）

#### 模块 B · 扫描进度流区
- **SSE 事件**：`{stage, customer_count_scanned, hits_so_far}`
- **典型阶段**：加载客户池 → 外部信号扫描 → 内部交易扫描 → 交叉命中判定 → 分级汇总

#### 模块 C · 三级分级榜单（主视图）
- **Summary 顶部条** (`alert_hitlist.json` → summary)：
  - total / red / yellow / green 数字
  - 环比上一批次增减
- **主 list**：每条客户含：
  - 客户名 + 客户 ID
  - `grade`：红 / 黄 / 绿
  - `trigger_reasons[]`：命中的规则 ID 列表（如 FIN-001 财务恶化 / LAW-001 法律诉讼 / BIZ-001 经营异常 / IND-001 行业风险）
  - 信号时间戳（最近一次触发时间）
  - 处置建议（disposition plan）

#### 模块 D · 规则库（预设）
- **22 条预设规则** 4 大类：
  1. 财务恶化 `FIN-001~004`：流动比率恶化、应收激增、营收下滑、毛利跳水
  2. 法律诉讼 `LAW-001~002`：被执行、失信
  3. 经营异常 `BIZ-001~002`：股权冻结、高管离职
  4. 行业风险 `IND-*`：行业景气度骤降等
- **交互**：规则卡片可展开看条件 DSL（只读）；支持按分类筛选

#### 模块 E · 单客户详情页
- **点击榜单任意客户**：弹侧边栏或跳 detail view
- **数据**：overall_level / signals[] 详情（每信号含：来源 / 时间 / 原文 / 权重）/ trigger_reasons / disposition plan（AI 建议处置动作）
- **操作**：批量标记已处理、分派给客户经理、忽略/申诉

---

## 5. Agent5 · 合规扫描助手 · `/archive/compliance`

### 5.1 角色定位
政策发布事件驱动（不是定期巡检）。新政策下来，Agent5 比对银行现有业务制度库，返回违规冲突点明细清单，供合规官 review。

### 5.2 必须包含的 UI 模块

#### 模块 A · 政策候选扫描
- **输入字段**：
  - `query`：政策关键词（可选，默认空 = 取最新全量）
  - `limit`：返回数量（默认 10）
- **触发按钮**「拉取最新政策」：
  - **后端端点**：`GET /api/compliance/policy_scan?query={q}&limit={n}`
  - 返回：政策候选清单 `[{title, source, url, publish_date, summary}]`
  - 失败优雅降级返回空 list + error

#### 模块 B · 政策选择
- **主政策源**：人民银行 / 银保监会 / 外汇局 / 财政部 / 地方金融监管局 等（多来源筛选 tab）
- **交互**：政策卡片列表（标题 / 来源 / 发布日期 / 摘要）；点卡片选中进入比对

#### 模块 C · 业务制度库选择
- **功能**：选择要比对的银行内部制度文件（多选）
- **输入字段**：
  - 制度文件多选（从预置的银行业务制度库 JSON 选，首期用 mock）
  - 支持上传新制度文件 `.pdf .docx`（未来）

#### 模块 D · 比对触发
- **触发按钮**「开始冲突扫描」：跑 LLM 比对
- **后端现状**：policy_scan 端点已通；比对端点（policy_compliance_compare）待开发

#### 模块 E · 冲突点明细清单（主输出）
- **每条冲突展示**：
  - 政策条款（原文 + 出处段号）
  - 制度条款（原文 + 文件名 + 段号）
  - 冲突类型：遗漏 / 矛盾 / 过时 / 权限错位
  - 严重度：高 / 中 / 低
  - 建议改法（AI 拟句）
- **交互**：按严重度筛选；点冲突项展开双栏对照（左政策右制度）；每条可标记「已处理」/「转法务复核」

---

## 6. Agent2 · 风控规则助手 · `/archive/riskctrl`

### 6.1 角色定位
策略经理面向工具。描述策略诉求（"拒绝多头借贷 + 高 DTI 客户"），Agent2 生成 DSL 规则 + 基于历史样本回测 KS / 通过率 / 坏账率。不做个案决策。

### 6.2 工程现状诚实标注
**当前无 FastAPI 端点**。核心模块 `rule_engine.py` 支持 DSL 生成和回测，以代码级模块存在。API 接入下一阶段。Mockup 基于 `web/public/mock/riskctrl_ruleset.json` 做演示态。

### 6.3 必须包含的 UI 模块

#### 模块 A · 策略诉求输入
- **输入字段**：
  - `strategy_goal`：策略目标多行文本（必填，自然语言，如"拒绝多头借贷 + 高 DTI 客户，保通过率 ≥ 60%，坏账率 ≤ 3%"）
  - `sample_csv`：**样本文件上传**，支持 `.csv`，字段包含申请人特征 + label（好坏账）
  - `target_ks` / `target_approval_rate` / `target_bad_rate`：三个 KPI 数值输入框（可选约束）

#### 模块 B · DSL 规则生成
- **触发按钮**「生成规则集」：LLM 输出 DSL 规则集
- **DSL 结构**：`StrategyRule = {rule_id, name, priority, conditions[], action, severity}`
- **RuleCondition**：`{field, operator, value}`，支持 6 种操作符：`>` `<` `>=` `<=` `==` `!=` `in` `not_in`
- **Action 5 层优先级**：拒绝 > 人工复核 > 快速通过（priority 1-5）

#### 模块 C · 规则集展示区（主视图）
- **按优先级分组**：每条规则卡片显示：
  - rule_id / 名称 / 优先级
  - 条件 DSL（代码块形式，只读可复制）
  - action 标签（拒绝/复核/放行）
  - 5 个回测指标：KS / 通过率 / 坏账率 / FP（假阳）/ TN（真阴）

#### 模块 D · 回测汇总
- **规则集级指标**：总通过率、总坏账率、KS、AUC、Lift
- **分 bin 视图**：按分数段的通过率 + 坏账率曲线（表格或数据点列出，不要求画图表——设计 CC 决定视觉形式）

#### 模块 E · 规则编辑与迭代
- **交互**：任一规则卡片可 edit（改条件 / 改阈值 / 改 action）→ 单独回测（「重算此规则」按钮）
- **对比视图**：原始 vs 调整后，三指标差值

#### 模块 F · 规则集保存/发布
- **按钮**「保存草稿」/「发布上线」
- 后端状态：待开发

---

## 7. 附：可复用的 Mock Fixture（5 份已产出）

所有 fixture 在 `web/public/mock/` 下，设计 CC 写 mockup 时直接 `<script>` 嵌入或 iframe + fetch 演示：

| 文件 | 字段骨架 | 用于 |
|------|---------|------|
| `report_fill_mock.json` | `preset / business_line / stages[] / sections[] / done{}` | Agent6 模块 B+C |
| `credit_decision_corporate.json` | `segment / preset_name / run_mock_events[] / scoring{financial/industry/operational/guarantee}` | Agent3 模块 B+C+D |
| `channel_run.json` | `scenario / scenarios[] / run_mock_events[] / done{candidates[], metrics{}}` | Agent1 模块 C+D |
| `alert_hitlist.json` | `version / source / summary{total/red/yellow/green} / customers[]` | Agent4 模块 C+E |
| `riskctrl_ruleset.json` | `version / ruleset{rules[{rule_id, conditions[], action, backtest{}}]}` | Agent2 模块 C+D |

---

## 8. 交付清单（你产出 6 份 HTML 时的 checklist）

每份 workspace HTML mockup 必须：
- [ ] 继承 rm-assistant-final 的 tokens（字体栈 / 圆角 / 渐变 / 5 主题切换 / 动画）
- [ ] 复用外壳（Masthead / Desk / Float-badge / 顶部 eyebrow+h1+lede）
- [ ] 本 workspace 对应功能色 `--t-*` 作为 accent
- [ ] 覆盖本文档列出的**所有**模块（A/B/C/...），每模块用真实字段名而非占位文字
- [ ] 所有实际可调用的端点用 openapi 路径（Agent6/3/1/5），无端点的（Agent4/2）标"待后端接入 · 演示用 fixture"
- [ ] 不产出 fallback 设计建议（颜色/间距/icon 选型），保持纯功能骨架

交付后 main CLI 会据此拆 Stage 5 派单方案，单 worker 串行重写 6 workspace（不并行，避免合并冲突，沿用 Stage 4 成功模式）。
