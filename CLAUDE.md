# 信贷 AI 智能体项目 · 架构规范

## 1. 产品定位

6 个 Agent 组成的 AI 助手矩阵，面向银行客户经理 / 审贷员 / 合规官 / 风险经理，覆盖贷前获客、授信决策、贷中预警、贷后合规的全流程。初期做 copilot（AI 辅助、人审核），成熟后逐步向 autopilot 过渡。

## 2. 启动方式

- **后端**：`py scripts/start_uvicorn.py`（自动从项目根 `.env` 加载 TAVILY / DEEPSEEK / PROXY 等 env，校验缺失 key 后调 uvicorn；首次部署 `cp .env.example .env` 填值即可。直接 `python api_server.py` 会缺 key）
- **前端**：`cd web && npm run dev`（Next.js 16，路由拓扑见 §7 canon vs legacy）
- **Agent6 主管线（v16）**：`py v16_pipeline.py --source samples/<模板>.docx --material samples`（classifier → generator → QC gate 全链路 · 项目根 10 个 `v16_*.py` 实现 · 见 `docs/contracts/rfc/20260418-v16-llm-abstraction-upgrade.md`）
- **旧版 Gradio 报告助手**：已归档至 `legacy_gradio/`（2026-04-29）· 如需 fallback 演示从 archive 恢复

## 3. 架构原则

### 3.1 确定性 vs 概率性（核心决策框架）

参考字节《资金 AI Agent 建设思考规划》对计算类型的划分——**两种计算适用不同任务，边界不可混**：

- **确定性计算**：财务比率、清算规则、红线阈值、同比环比、账龄周转 → 用 Python / 规则引擎，禁止让 LLM 现场算
- **概率性计算**：行业分析、风险意见、匹配推荐、话术生成、政策解读 → 用 LLM + 证据链
- **硬隔离手段**：
  - **预填层**：`truth_fill.py` 做结构化字段/复选框预填（入口 `prefill_labeled_fields_from_kb`），LLM 只补预填留白处
  - **prompt 注入层**：LLM 只消费三件套的 `format_for_prompt()` 输出 —— `financial_analyzer.py`（确定性财务指标 + 趋势短语）/ `industry_benchmark.py`（行业基准卡）/ `material_anchor.py`（材料锚定 + 行业政策卡），见 `section_generator.py` 三阶段调用
  - **QC 终审层**：`quality_scorer.py` 做 9 维度评分（QC 闸门，结果不进 prompt，只判通过/阻断）

**反模式**：把 xlsx 甩给 LLM 现场算比率、让 LLM 判定红线是否触发、用 prompt 硬编黑名单规避幻觉。这些在多轮迭代里被证明是循环打补丁。

### 3.2 MCP 按业务域拆分工具

每个 Agent 内部工具按业务子域组织，不要扁平堆叠；命名统一 `<域名>_<动作>`：

- **Agent1 获客**：信号搜索域 / 企业画像域 / 匹配评分域 / 产品推荐域
- **Agent3 授信**：画像消费域 / 评分计算域（对公/对私双模型）/ 红线检查域 / 案例召回域
- **Agent4 预警**：外部扫描域 / 内部交易域 / 双路交叉域 / 处置建议域
- **Agent5 合规**：政策解析域 / 业务矩阵域 / 违规判定域 / 缺陷分类域
- **Agent6 报告**：材料解析域 / 字段抽取域 / 段落生成域（三阶段 Evidence 协议）/ QC 终审域
- **Agent2 风控**：DSL 生成域 / 回测域 / 指标分析域

新增工具必须归入一个域；跨域协作走 Agent 编排层，不在域内直接调用其他域的内部实现。

### 3.3 Evidence-First Protocol（证据优先）

所有 LLM 生成内容走三阶段：**证据汇集 → Grounded 生成 → 自审**。每条数字、判断、结论必须带证据链（出处文件 / 段落 ID / URL）。无证据项标「未能自动填写」，比编一个看起来对的更有价值。实现见 `section_generator.py` 和 `truth_fill.py` 的 `prefill_labeled_fields_from_kb`。

**LLM Prompt 8 段 SSOT**: 6 Agent system prompt 全部按 `docs/contracts/llm-prompt-contract.md` v1.0 (Phase A worker-A1 ratified · 2026-04-29) 8 段顺序拼装 — `[safety] → [evidence-first] → [agent-role] → [tool-use] → [output-schema] → [self-check] → [few-shot] → [evaluation-hook]`。helper `shared/prompts/contract.py` 由 worker-A2 落地后 · 6 Agent inline `SYSTEM_*` 常量全部替换为 `build_system_prompt(agent_id, task_type, ...)` 调用 (audit Cat 6 fix)。Agent2 riskctrl DSL 生成是 [evidence-first] 的唯一例外 (回测仍走确定性 backtest engine · 不让 LLM 现场算 KS/AUC)。

### 3.4 Search Provider 抽象（可切换）

Agent1 / Agent4 / Agent5 共享 `SearchProvider` 接口（Mock / Tavily / 企查查实现），切换来源一行代码。下游统一消费 `CompanyProfile` / `ScanResult` 结构，不准依赖数据来源细节。

### 3.5 反结果导向 5 原则（mock 数据约束 · 决定落地）

信贷 Agent 矩阵所有 mock 数据必须同时满足以下 5 条，违反即返工。适用场景：data-foundation worker 产出、Agent 自测数据、任何外部搜索 mock。本节与 §3.1 互补——§3.1 管**运行时计算归属**，本节管**训练 / 评估时数据归属**。

| # | 原则 | 意思 | 反面案例 |
|---|---|---|---|
| 1 | **盲测** | PM 设计埋坑与 worker 实现物理分离，worker 不预知埋坑答案 | worker 同时设计数据 + 填埋坑清单 |
| 2 | **难度分层** | 覆盖简单 20% / 中等 50% / 困难 20% / 极端 10% | 全堆极端档以显"数据硬" |
| 3 | **真实来源锚定** | 参考 A 股年报 / 央行模板 / 银保监处罚公告的真实形态 | 凭空编企业名和数字 |
| 4 | **脱敏再造** | 不直接用真实存续企业数据；改名字改数字保量级 | 抄真实公司材料直接入库 |
| 5 | **环境边界** | mock 给 Agent "稳态内部 context"，**不替它做"本该外搜的工作"** | 把 Agent1 / Agent5 的外部候选 / 新政策也 mock 掉，使 Agent 只做 dict lookup 不做真检索 |

**环境边界具体落地（per Agent · 数据归属分割线）**：

| Agent | 内部 mock（稳态 context · 要建的库） | 外部不 mock（Agent 自搜 · 核心能力） |
|---|---|---|
| Agent6 报告 | 客户提交材料包（文件夹 + pdf / xlsx / docx / 扫描件混合）| — |
| Agent3 授信 | 复用 Agent6 材料 + ReportJSON | — |
| Agent1 获客 | 银行已成交客户画像 + 营销倾向性文件 + 产品目录 | 外部企业候选（SearchProvider 实搜 Tavily / 企查查）|
| Agent5 合规 | 银行业务制度库（SOP / 准入 / KYC / 风偏 / 审查清单）| 外部新政策（SearchProvider 实搜银保监 / 央行）|
| Agent4 预警 | 在贷客户池 + 内部流水 + 外部信号流（可全 mock，核心能力是跨源交叉）| — |
| Agent2 风控 | 历史贷款样本 CSV + 字段字典（内部建模）| — |

**形态硬线**：mock 不可以是"pre-extracted key-value yaml"，必须保留真实消费形态（Agent6/3 = 文件夹异构文件 · Agent1/5 = 文档库 · Agent4 = 多表 · Agent2 = CSV），含命名混乱 / 扫描件 / 多年跨度 / 数字合理矛盾等噪声；**绝不含答案字段**（difficulty / match_score / risk_level / conflict_points / optimal_dsl 等），Agent 自己算。

本 5 原则沉淀于 Q-028/A-028（2026-04-24）· data-foundation Batch 1 REJECT-V2 复盘。

### 3.6 LLM Caller 唯一化 + PIPL 合规 fallback chain

Phase A worker-A2（2026-04-29）落地：6 Agent 任何 LLM 调用走 `shared/llm_caller/` 单一抽象层 · 替代历史 4+1 套并行 caller。

- **5 模块**：`shared/llm_caller/{client, retry, audit, provider, prompts}.py`
  - `provider.py`：`LLMProvider` Protocol + `ProviderResult` + 4 providers (`DeepSeek` / `DashScope` / `Qwen` / `Moonshot`) + `_REGISTRY` + `get_provider()`
  - `retry.py`：`DEFAULT_FALLBACK_CHAIN = ("deepseek", "dashscope")` + `chat_with_fallback` / `chat_json_with_fallback` + 主 fail 自动切下一个
  - `audit.py`：`with_audit(...)` ctx 包 single LLM call · 与 `audit_service.decorators.audit_llm_call` (FastAPI 路由级) + `stream_helpers.audit_stream_event` (SSE 内) 三层互补 · 全 silent-fail
  - `prompts.py`：`build_chat_messages` / `with_json_schema_hint` / `with_few_shot` / `truncate_for_context` 4 个 string-assembly utility（无业务 prompt 文本）
  - `client.py`：`LLMCaller(agent_id, endpoint, chain, audit_enabled).chat() / .chat_json()` 顶层 facade · 6 agent 迁此入口
- **PIPL 合规底线**：默认 fallback chain 全境内（`deepseek` 主 + `dashscope` 备）；`moonshot` 标 `region="overseas"`，仅 `LLM_PROVIDER=moonshot` 显式才走；audit log 含 `region` 字段，跨境调用可追溯。
- **底层 backing 不动**：root `llm.py:LLMClient` 保留为 caller 1（6+ production import）；`shared/llm_caller/provider._LLMClientWrapper` 委托它做实际 API 调用，复用 cache + provider config。
- **向下兼容**：`shared/llm/{base, router, providers/*}` 保留为 re-export shim，`shared/kb_scan/impls/channel_signal.py:311` 的 1 production import 不破。
- **Deprecation 路径**（A4 worker 5 子分别迁，本 worker 不动 agent_*/api.py）：
  - caller 3 `agent_riskctrl/llm_judge.py` LLMJudge 基类 → 迁 `LLMCaller(agent_id="riskctrl", endpoint="judge").chat()`
  - caller 4 `agent_report/api.py:_build_llm_caller` 裸 `OpenAI(base_url=...)` → 迁 `LLMCaller(agent_id="report", endpoint="/api/report/v16/fill")`
  - caller 5 `agent_alert/api.py` + `agent_compliance/scan_engine.py` + `agent_riskctrl/api.py` 直 `LLMClient(provider=...)` → 同上 · 各 agent 自有 `LLMCaller` 实例
- **环境变量**：`LLM_PROVIDER`（默认 provider，不强制） / `LLM_FALLBACK_CHAIN`（覆盖默认 chain · e.g. `deepseek,qwen,dashscope`） / 各 provider 的 `*_API_KEY`（`DEEPSEEK_API_KEY` / `DASHSCOPE_API_KEY` / `NVIDIA_API_KEY`）。

依据：Phase A 验收硬线 #2（`docs/reset/phase-a-charter.md` §1）+ Cat 7 conflict register（4+1 套并行 caller）+ Stage E.3（2026-04-28）PIPL 境内优先决议。

## 4. 6 Agent 功能边界（不可跨界）

| Agent | 触发 | 输入 | 产出 | 不做 |
|---|---|---|---|---|
| Agent1 获客 | 客户经理发起 | 画像描述 + 知识库 | 候选企业 + 信号时间线 + 产品推荐 | 授信决策 |
| Agent2 风控 | 风险经理发起 | 策略诉求 + 样本 CSV | DSL 规则 + KS / 通过率回测 | 个案决策 |
| Agent3 授信 | 审贷会发起 | Agent6 ReportJSON + 材料 | 四维评分 + 额度 / 期限建议 + 红线 | 写报告 |
| Agent4 预警 | **客户行为变化**驱动 | 在贷客户池 + 规则库 | 红/黄/绿分级客户榜单 | 单点手动查询 |
| Agent5 合规 | **政策发布事件**驱动 | 新政策 + 业务制度库 | 违规冲突点明细清单 | 定期巡检 / 财务审计 |
| Agent6 报告 | 客户经理发起 | 企业材料 + 模板 | ReportJSON + Word | 决策意见 |

Agent4 vs Agent5 的边界是**触发源**（客户变 vs 政策变），不是对内对外；共享 `shared/kb_scan/` 矩阵扫描底座，不合并。

**命名 SSOT**: 6 Agent × 8 维度 (id / 中文 / 业务名 / UI brand / route / 色彩 token / RBAC role / eval baseline) 单源在 `docs/contracts/agent-naming-ssot.md` v1.0 (Phase A worker-A1 ratified · 2026-04-29) · 任何 agent 相关 consumer 文件 (`web/src/lib/agents.ts` / `auth_service/rbac.py` / `evaluation/agent*.yaml` / `agent_*/api.py`) 一律 read-only 引用 · 修改走 RFC (`shared-change-protocol.md`)。`compli` vs `compliance` 单 id 选项见 SSOT §3 (PM 待拍板)。

## 5. 评估框架（双轨制）

### 5.1 通用评估（每次迭代跑基线）

- `field_completeness` 字段填充率
- `evidence_rate` 证据溯源率
- `hallucination_rate` 幻觉检出率
- `tool_success_rate` 工具调用正确率
- `task_completion_rate` 任务完成度

### 5.2 信贷专业评估（领域特有）

- 财务比率计算正确率（vs Python 确定性结果 ≥ 99%）
- 红线判定准确率
- 合规术语规范率
- 内部评分与人工复核一致率
- 信号多样性（每候选客户 ≥ 2 种信号类型）

配置在 `evaluation/` 目录（每个 Agent 一份 YAML）。质量问题先建 rubric、跑基线、找最大 gap，再改代码——拒绝无基线迭代。

## 6. 数据飞轮（提示词驱动，无 SFT）

四环闭环（本项目用 few-shot 注入替代字节方案里的 Fornax SFT）：

1. **静态知识**：`customer/`、`demo_data/`、`industry_cards/` + 规则库
2. **模型评估**：第 5 节评估框架跑基线
3. **动态经验**：`/api/feedback` 端点收审贷员对 Agent 输出的修改，写 `data/feedback/YYYY-MM-DD.jsonl`
4. **提示词优化**：定期从 feedback 提取 few-shot 示例，注入 `prompts.py`

## 7. 前端设计系统（platform shell v2）

**规范源**：`docs/design/platform-shell-v2.md`（主 CLI 唯一可写；v1 归档备查，不再迭代）
**设计 mockup**：`design_mockups/rm-assistant-final-2026-04-19.html`（2026-04-20 post-purge · sha256 `25155e74...` · 视觉 1:1 复刻源；原 Letterpress/crimson 已在 2026-04-20 下架）

**交付约束**：**视觉 1:1 复刻 + 实际对应**——CSS tokens / DOM 结构 / 动画 keyframe / SVG 符号 / JS 交互必须与 mockup 逐像素一致；端口 / 路由 / 实时时钟 / mock 数据 shape 按实际前端实现对齐，不硬编 mockup 里的字面值。

- **信息架构**：4 view——**今日**(`/today`) / **对话**(`/dispatch` · Slack 风 IM) / **AI 助手**(`/archive` · 6 Agent tile 聚合) / **任务**(`/warroom` · 4 列 kanban)。Agent 不在顶栏，是 Archive view 内 6 tile；tile 点击跳转既有 `/archive/[agent]` workspace
- **路由拓扑**（legacy 顶层 6 路由已于 2026-04 清完 · git history 可查）：
  - **canon**（shell v2 唯一入口）：`/today` / `/dispatch` / `/archive` + `/archive/[agent]` 动态路由（`archive/[agent]/page.tsx` + `WORKSPACES` map 覆盖 6 Agent）/ `/warroom`；辅助 `/login` / `/audit` / `/customer` / `/403`（D.1 RBAC 拒绝跳转 · `web/src/app/403/page.tsx`） / `/api/*`（Next.js API routes proxy · `web/src/app/api/credit/mock-session/route.ts` 等）
  - **前端改动红线**：所有 Agent workspace 只走 `/archive/[agent]` 下的 `_components/*Workspace.tsx`·**不允许重新引入顶层 `/channel` `/credit` 等 legacy 路由**·Letterpress / crimson / `--color-brass` / `--color-ink` / `ink-brush-hr` 等老 tokens 已下架·不允许复活（**2026-04-29 Phase A5 verified**：`web/src` 硬线 grep `--color-brass\|--color-ink\|letterpress\|ink-brush-hr` 0 命中（注释 / docs 例外不计）· `globals.css` 390→84 行 · 11 consumer 全迁 shell-v2 · Playwright `letterpress-purge.spec.ts` hermetic 全 pass）
- **共享壳**：左抽屉 Desk（客户 / 进行中 / 最近 / 新建 · hover-from-edge < 22px 触发 · pin / Esc / ⌘K）+ 顶栏 Masthead（logo + 4 tab + persona 王哲·客户经理·华东 + live clock 20s tick） + 右下 Float-badge（4 主题各一 SVG 符号） + 主题切换器（4 按钮全部可见）
- **主题**：`data-theme` 4 套——**Canvas**（默认，米黄→橙红→墨绿） / **Matcha**（抹茶） / **Dusk**（暮粉桃花） / **Ink**（水墨 · 宣纸→深墨 · 2026-04-20 替换 v1 Letterpress 黑红方案，用户判"黑红读老 DEMO"），每主题 8 档渐变 `--g0..--g7` + `--g0b` + ink/chalk opacity ramps + `--accent` 功能色
- **6 Agent 功能色**：`--t-report` 棕赭 / `--t-alert` 赭红 / `--t-compli` 墨绿 / `--t-credit` 青蓝 / `--t-riskctrl` 绛紫 / `--t-channel` 青绿
- **Float-badge SVG**：落日(Canvas) / 禅圆 enso(Matcha) / 桃花(Dusk) / 太极(Ink)
- **字体栈**：Funnel Display（display） + Instrument Sans/Serif（body/italic） + Noto Sans/Serif SC（中文） + JetBrains Mono（数字）
- **圆角**：`--r-md: 18px` / `--r-lg: 26px` 全局统一
- **动画**：`bodyBreath` 22s（body 背景呼吸） / `drift` 38s（SVG 噪声漂移） / `breathe` 8.5s（card 边缘光晕） / `glyph-rise` 按字 stagger / `rise` / `card-rise` / `bar-in` / `case-in` / `bar-flow` / `wait-slide` / `blip`
- **JS 交互**：staggerH1 glyph-rise（React effect 化）/ tab 切换 / live clock `setInterval(20s)` / 主题切换器 / Desk hover-from-edge + pin + Esc
- **浏览器基线**：`color-mix()` 要求 Chrome/Edge 111+ / Safari 16.4+（银行内网兼容待产品决策）

交付银行/金融客户，体验 > 架构优雅度。后端可复杂，用户触碰的每一层必须丝滑。任何前端改动先读 spec 再动手，spec 与 mockup 不一致时**以 mockup 为准**，再更 spec。

## 8. 质量闸门（QC Blocker）

所有 AI 生成内容输出前终审：

- 企业名占位符、数字占位符残留检查
- 证据链完整性检查（每条 claim 必须回指到证据）
- 财务数字与 `financial_analyzer` 计算结果一致性校验
- 不通过则阻断输出并显式标「未能自动填写」

## 9. 渐进式落地

- **copilot 期（当前）**：AI 填报告 / 推荐候选 / 出评分，审贷员审核后才用
- **autopilot 期（未来）**：高置信字段（如财务比率、规则命中的红线）免审，低置信字段（如行业意见、话术）保留人工补

## 10. 关键文件

- `agent_channel/` `agent_credit/` `agent_alert/` `agent_compliance/` `agent_report/` `agent_riskctrl/` — 6 个 Agent 的后端实现
- `shared/kb_scan/` — Agent1/4/5 共享的知识库扫描范式
- `web/` — Next.js 16 前端（6 路由）
- `api_server.py` — FastAPI 总线，SSE 流式事件
- `financial_analyzer.py` — 确定性财务指标计算层
- `quality_scorer.py` — 9 维度评分基线
- `section_generator.py` — Evidence-First 三阶段生成
- `truth_fill.py` — 结构化预填（字段 + 复选框）
- `material_kb.py` — 材料解析与 KB 构建
- `evaluation/` — 评估配置（每 Agent 一份 YAML）
- `data/feedback/` — 动态经验沉淀（审贷员修改 JSONL）
- `legacy_gradio/` — 已归档 · v15 form_filler + narrative_pipeline + Gradio v7.5/v9 (`app.py` / `portal_app.py`) + run_form_fill_cli (2026-04-29 归档)
- `v16_pipeline.py` / `v16_generator.py` / `v16_classifier.py` + 其他 7 个 `v16_*.py` — **Agent6 主管线 v16**（classifier → generator → QC gate · CLI 入口 `py v16_pipeline.py`）
- `docs/contracts/rfc/20260418-v16-llm-abstraction-upgrade.md` / `20260418-evaluation-runner.md` — v16 LLM 抽象层 + evaluation runner 两份 RFC
- `/tmp/start_uvicorn.py` — 带环境变量的启动 wrapper
- `shared/sources/` — 分层数据源架构（BaseSource 协议 + Router + Degrader）
- `shared/sources/impls/` — 6 个源实现（Tavily / akshare / gov_cn / pbc_gov / flk_npc / enterprise_info · 后者用于 Agent1 工商信息上市/非上市分层抓取）
- `shared/llm_caller/` — **Phase A worker-A2 (2026-04-29) · LLM caller 唯一化层** · 5 模块: `provider.py` (Protocol + 4 providers + registry) · `client.py` (LLMCaller facade · `simple_chat` / `make_text_caller` / `make_json_caller` legacy adapter) · `retry.py` (fallback chain · 显式 `api_key` bypass env check) · `audit.py` (per-call hook) · `prompts.py` (string utilities) · 详 §3.6
- `shared/llm/` — Stage E.3 (2026-04-28) 旧目录 · Phase A 后改 re-export shim · 1 production import 不破 (`shared/kb_scan/impls/channel_signal.py:311`) · 新代码用 `from shared.llm_caller import ...`
- `shared/sse_envelope.py` — Phase A worker-A2 · backend SSE event 共形 helper (make_stage / make_section / make_done / make_error / encode_event + `CHANNEL_PANEL_KEYS` per workspace-state-protocol §4 · `make_done` 拒空 payload) · spec 见 `docs/contracts/sse-envelope.md` v1.0 · 解决 audit Cat 4 · 6 agent A4 worker 后续迁此入口
- `shared/prompts/contract.py` — Phase A worker-A2 · 8 段 LLM prompt template skeleton (safety/evidence/role/tools/schema/self-check/few-shot/eval-hook · `_PENDING_A1_SPEC` placeholder strict-only) · spec 见 `docs/contracts/llm-prompt-contract.md` v1.0 · 解决 audit Cat 6
- `tests/shared/test_llm_caller.py` + `test_sse_envelope.py` — Phase A worker-A2 pytest coverage (69 tests · 含 backward-compat shim 验证)
- `agent_*/sources_config.py` — 各 Agent 域的源偏好链配置
- `test_sources_smoke.py` — 新架构冒烟测试

## 11. 当前版本

- Agent1 获客 v4.0（信号驱动搜索，2026-04-16 · candidate metadata 4 字段 `industry / geo / scale / similarity` per Q-041 · B.5 dispatch 时注入）
- Agent3 授信 v3.1（对公 / 普惠 / 对私三板块）
- Agent4 预警 v3.1（知识库驱动批量扫描）
- Agent5 合规 v3.1（政策事件驱动）
- Agent6 报告 **v16**（classifier → generator → QC gate 主管线，`v16_pipeline.py` 为 CLI 入口；`agent_report/` 为 API wrapper 层 unreleased，消费 v16 产出；旧 Gradio 单机版 v7.5/v9.0 已归档至 `legacy_gradio/` · 2026-04-29）
- Agent2 风控 v3.1（DSL + 回测 · 回测 `MAX_ROWS=50000` per Q-040 fix-forward 2026-04-29）

## 12. 开发约束

- 不让 LLM 做可确定性计算的事（回到第 3.1 条）
- 不写关键词 / 正则黑名单兜底幻觉（治本用证据链 + QC Blocker）
- 字段填不了就标「未能自动填写」，绝不编
- 新工具必须归入某个业务域（第 3.2 条）
- 新维度先定评估指标再改代码（第 5 节）

## 13. ECS / Production 同步纪律（防回档强约束）

production = ECS（IP 139.196.30.69）跑 `main` 分支 · **single source of truth**。任何改动必须遵守：

1. **禁 scp 直接编辑 ECS 文件** — 前任 CLI 直接 scp 修复 LoginForm 是回档隐患源 · 一律禁止
2. **改动流程**：本地 commit → push GitHub `main` → ECS `git pull origin main` → restart systemd service
3. **ECS git tree 必须 clean** — 任何 modified / untracked 文件视作 dirty · 立刻 fix-forward 或 commit · 不允许长期脏
4. **每天 morning sync**：dev 分支（`chore/l0-infra`）首次开工前 · `git fetch && git diff main` 看有无未同步 commit · 有则 push / pull 对齐
5. **回档防护 trailer**：worker 改 `web/` 必须 attach trailer 列保留的 inventory features：
   ```
   PRESERVES: F-001, F-005, F-012     ← 列保留 id
   NEW-DOM: data-testid="..."         ← 新增 selector
   SMOKE-PASS: <spec>.spec.ts         ← 跑通的 smoke test
   ```
   缺 trailer 视作未读 inventory · review 阻断 · merge 阻断
6. **Inventory 源**：`docs/features-inventory.md` 是 worker 改 `web/` 前必读 contract · 破坏已列 feature 视作 regression · 主 CLI 阻断 commit / 阻断 deploy

违反任意条 = 回档源责任人 · 主 CLI / dispatcher 必须立刻 stop the line。

### 13.1 main CLI 默认行为 · 改完即部署 (不等 user 触发)

main CLI 改 `web/` + commit 后**自动**跑完整 push → ECS pull → build → restart 流程。**不要每次问 user "要不要 push / 要不要部署"** — 默认开干 · user 只在出错时介入。

**触发判断**:
- 改 `web/` (任何 .tsx / .ts / .css) → 完整流程 (含 npm build · 5-10 min)
- 改 `.py` / `api_server.py` / `agent_*/` → `--skip-build` (仅 backend restart)
- 改仅 `docs/` / `CLAUDE.md` / `scripts/` → push GitHub 即可 · 不需 ECS 部署

**执行**:
```bash
bash scripts/deploy_to_ecs.sh           # 完整 (含 build)
bash scripts/deploy_to_ecs.sh --skip-build  # 后端改 · 跳 build
```

脚本封装 stash + pull + build + restart + healthcheck 全流程 · 失败 abort 不 silent fail。

**例外** (必须问 user):
- production hot-fix 影响线上演示 (客户走访期间 / user 在演示)
- 涉及 ECS systemd service 配置 / cloudflared tunnel / nginx vhost 改动
- 涉及 LLM key / .env / 凭证类改动

## 14. 新 session / compression 后必读 (Reset 长周期工程专用)

**当前项目处于"全新出发"reset 长周期工程阶段** (起于 2026-04-29) · 主 CLI 任何 fresh session / compression 触发后 · **第一件事是按本节 顺序读完 5 份文档 · 写出"我理解当前状态" commit (Signal: NEW-MAIN-CLI-RESUMED) 等 PM verify · 再做任何决策**。

**必读顺序 (6 份文档 · ~12 min)**:

1. `RESET_MASTER_PLAN.md` (项目根 · umbrella 索引页)
2. `docs/reset/north-star.md` (产品形态 north star + 走歪表征 + 修正方向)
3. `docs/reset/phase-a-charter.md` (Phase A 7 worker 拆分 · 验收硬线)
4. `docs/reset/step2-conflict-scan-charter.md` (Step 2 17 类 + flow + schema · self-contained)
5. `docs/reset/codex-mesh-protocol.md` (Codex 4 插入点 · 命令 verbatim · prompt template)
6. `docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_<latest>.md` (最新 handoff · 含 PM 已拍板事项 + 待启 + dissent)

**附加(深入用)**:
- `docs/reset/state-snapshot.md` (当前已完 / 在跑 / 待启 三段)
- `docs/reset/phase-b-charter.md` (Phase B 商业化 charter)
- `docs/reset/anti-bias-rules.md` (4 anti-bias 硬规)
- `docs/handoff/decisions-log.md` 末 50 行 (最近 PM 决策)
- `docs/handoff/mesh.json` + scoreboard (worker 状态)

**写"我理解当前状态" commit 模板**:
```
chore(resume): NEW-MAIN-CLI-RESUMED · 我理解当前状态

产品 north star: <verbatim 复述>
6 Agent 闭环路径: <verbatim 复述>
走歪表征 (top 5): <list>
当前 Phase: <Phase A · Week N · 在哪步>
待启 worker: <list>
PM 已拍板 5 件: <list>
我下一步动作: <具体 1-2 条>

Signal: NEW-MAIN-CLI-RESUMED
```

PM 看 commit 内容 verify · 没漂 → GO · 漂了 → 退回让我重读。

**Compression 中段触发的恢复协议**:
任何 CLI 觉察 compression 后 (system reminder 提示 / 突然不记得最近上下文) · 立即:
1. 重读上面 5 份文档
2. `git log --oneline -30 --all` 还原最近活动
3. `py scripts/orchestrator/scoreboard.py` 看 mesh state
4. 写一段 "我恢复后理解" 给 PM verify
5. 不再凭"模糊印象"做决策

**这条规则与 §13 ECS 同步纪律同等优先级 · 不可跳过**。

### 14.1 状态文档实时更新硬规 (PM 2026-04-29 加)

**Reset 工程任何迭代 · 无论大小 · 必须同步更新 `docs/reset/state-snapshot.md`**。

**触发**:
- 任何 worker DONE signal cherry-pick → 主 CLI 同 commit 加 state-snapshot.md timestamped 段
- 任何 codex review 出 verdict → 主 CLI 写 audit doc 时同更 state-snapshot
- 任何 PM 拍板 / decisions-log Q-NNN → 主 CLI 写 decisions-log 时同更 state-snapshot
- 任何阶段转换 (Phase A → Phase B / Week N → Week N+1)

**段格式**:
```markdown
## YYYY-MM-DD HH:MM · <事件>

### What happened
- <list>

### Triggered by
- <PM / worker-XX / codex review / scheduled checkpoint>

### State change (delta)
- <key change · old → new>

### Next
- <implied next 1-2 step>
```

**违反 = stop the line**: 任何 commit 触动产品 / 架构 / 决策但**未同步** state-snapshot · 主 CLI 必须立刻 amend commit (或新 commit 补上)。

**意义**: compression / 新 CLI / 未来的我 都靠 state-snapshot 还原 "我们现在到底在哪"。state-snapshot 漂 = reset 工程整体迷失。

## 15. 指令 SSOT 优先级 (Phase A worker-A1 立 · 2026-04-29 · V2 codex review fix · 5 tier + 1 meta)

任何文档 / 代码 / decisions-log 之间冲突时 · 按 `docs/arch/instruction-source-of-truth.md` v1.0 阶梯裁决 · **数字小者赢**:

| Tier | 来源 |
|---|---|
| Meta (例外 · ladder 之外) | `docs/arch/instruction-source-of-truth.md` (本 SSOT 自身 · 改它仅 PM 可批) |
| 1 | `docs/contracts/*.md` (接口契约 · 红区 · RFC 改) |
| 2 | root `CLAUDE.md` (本文件 · 工程行为 + 全局规则) · 其他 `docs/arch/*.md` (e.g. `platform-contracts.md`) sit here as supporting · 与 root CLAUDE.md 冲突时 root 赢 |
| 3 | scoped child `CLAUDE.md` (e.g. `agent_*/CLAUDE.md` · narrower-only · 当前 0 个) |
| 4 | `docs/onboarding/*.md` (worker 任务 brief · 一次性) |
| 5 | `docs/handoff/decisions-log.md` (Q/A 历史 · active rule 必回写到 Tier 1-2) |

**Meta 例外**: 本 SSOT 自身定义 Tier 1-5 排序 · 不允许 Tier 内文件改本 SSOT (循环依赖) · 是 ladder 之外的元规则 · 见 SSOT §1.0。

**Active decision 回写硬规** (PM 2026-04-29 拍板 #3): 任何改变 future worker 行为的决议必须在**同 commit 或 ≤ 24 小时**内回写到 Tier 1-2 · commit trailer 列 `ACTIVE-DECISIONS-BACK-WRITTEN: <count>`。违反 = stop the line。

**Stale marker**: Tier 1-2 文档 stale 时不允许默默留着 · 标 `> ⚠️ **STALE** (since YYYY-MM-DD): ...` + Fix-forward owner · 见 SSOT §4。

详细规则 / 冲突解决 3 步 / 子域 CLAUDE.md 规范 / 当前积压回写任务 → 见 `docs/arch/instruction-source-of-truth.md`。
