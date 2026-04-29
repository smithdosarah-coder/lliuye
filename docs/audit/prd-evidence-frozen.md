---
sub-agent: prd-evidence
date: 2026-04-29
round: 1 (Step 2 并行启)
飞书 PRD: found · 众安信科 wiki space_id=7583213987240627145 · R6IywYWfSiECkek1Gq6cnQDBnbb 下 7 个 Agent 子目录均在 · 附 node_token · fallback 本地 docs/PRD_*.md 用于文本抽取
---

# PRD Evidence Frozen · Step 3 取证 (Step 2 中并行)

## Section 1: Original Intent (飞书 PRD · 6 Agent each)

### Agent1 全渠道流量匹配 / 获客

- **飞书源**: https://fcntbrvzmfph.feishu.cn/wiki/QOzbwMgyciBkfWko5Z3cmIfhnhf (node: `QOzbwMgyciBkfWko5Z3cmIfhnhf` · "01 · 全渠道流量匹配智能体")
- **本地 fallback 文本**: `docs/PRD_全渠道流量匹配智能体_v2.0.md`
- **Original Intent**: 客户经理上传"已有优质客户名录 + 政策文件"三类知识库，Agent 抽出**理想客户画像**并遍历外网企业池，找出与画像最相似的 Top10 新客户线索，每条线索附匹配理由 + Top3 产品推荐。核心隐喻：**look-alike 获客引擎**，不是单查工具或产品推荐表。

### Agent2 风控策略运营

- **飞书源**: https://fcntbrvzmfph.feishu.cn/wiki/CQfMwbT9NiTk2pksMqXcunMPnWd (node: `CQfMwbT9NiTk2pksMqXcunMPnWd` · "07 · 风控策略运营助手")
- **本地 fallback 文本**: `docs/PRD_风控策略运营助手_v1.0.md`
- **Original Intent**: 支持自然语言配策略、自动回测评估、差错案件诊断，让风控运营人员无需编写代码即可完成策略全生命周期管理（DSL 生成 → 回测 KS/通过率/坏账率 → PDF 报告）。

### Agent3 授信决策辅助

- **飞书源**: https://fcntbrvzmfph.feishu.cn/wiki/OOTtwSlD5iOzIlkNwMYc84JTnVb (node: `OOTtwSlD5iOzIlkNwMYc84JTnVb` · "05 · 授信决策辅助智能体")
- **本地 fallback 文本**: `docs/PRD_授信决策辅助智能体_v2.0.md`
- **Original Intent**: 消费 Agent6 产出的 ReportJSON + 多源补充信息（行业基准/历史案例/征信），输出一张 90 秒看懂的**决策 Dashboard**（批/不批 + 额度 + 期限 + 利率 + 红线），面向审贷会主席/风控主管；对公（50 万-5000 万）/ 对私（5 万-500 万）双板块，共享决策引擎和红线规则库。

### Agent4 贷中风险预警

- **飞书源**: https://fcntbrvzmfph.feishu.cn/wiki/YrjDwayKIi6BqJkpfgncb1Qvn5c (node: `YrjDwayKIi6BqJkpfgncb1Qvn5c` · "06 · 贷中风险预警助手")
- **本地 fallback 文本**: `docs/PRD_贷中风险预警助手_v2.0.md`
- **Original Intent**: 客户上传"在贷客户池 + 预警规则库 + 内部制度"三类知识库，Agent 批量遍历全量客户，双路交叉命中（外部扫描域 + 内部交易域），吐出分级榜单（红/黄/绿）。核心隐喻：**知识库驱动的批量贷中预警雷达**，不是单企业查询工具。

### Agent5 合规巡检

- **飞书源**: https://fcntbrvzmfph.feishu.cn/wiki/ZMeywAaEJi7ALEkwb9uc4cFnnqc (node: `ZMeywAaEJi7ALEkwb9uc4cFnnqc` · "02 · 合规巡检智能体")
- **本地 fallback 文本**: `docs/PRD_合规巡检智能体_v2.0.md`
- **Original Intent**: 客户上传"监管政策库 + 内部制度 + 业务数据"三类知识库，Agent 把政策拆成规则集、业务拆成事件集，做 N×M 矩阵比对，吐出违规榜单（严重/一般/观察）精确到业务单号级。触发源：**政策发布事件驱动**，不是定期巡检。

### Agent6 报告生成

- **飞书源**: https://fcntbrvzmfph.feishu.cn/wiki/E9z8wJnDRiaI4ckmeH1cYcQknXc (node: `E9z8wJnDRiaI4ckmeH1cYcQknXc` · "04 · 报告生成助手") + `docs/PRD_报告生成助手_规划版_v2.3`（node: `JY93w1r0aibCeXkSEoLcs8F7nTw`）
- **本地 fallback 文本**: `docs/PRD_报告生成助手.md` (v1.0)
- **Original Intent**: 客户经理上传企业原始材料（PDF/Word/Excel/扫描件）+ 模板，自动生成一份可直接提交审批的 15000 字授信调查报告（Word）。Evidence-First 三层信息框架：材料事实（Python 精确计算）→ 行业上下文 → 分析推断；输出 ReportJSON 供 Agent3 下游消费。

---

## Section 2: Current Repo State (per agent · 2-4 句)

### Agent1 获客 (channel)

- **实际 deliverable** (`agent_channel/api.py:1-10`): 暴露 5 端点——`GET /api/channel/scenarios`、`POST /api/channel/run`（SSE look-alike 搜索）、`POST /api/channel/export_xlsx`、`POST /api/channel/export_docx`、`POST /api/channel/handoff`（移交 Agent3）；前端 `ChannelWorkspace.tsx` (F-005) 标注"NEVER CORRECTLY DELIVERED · 产品定位错 · 待重做"，QueryBar 仍实现为 look-alike KB matcher 而非自由搜索标签。
- **缺口 vs Original Intent**: 前端 UI 与 PRD 产品形态错位——PRD 要"上传知识库 → 外网遍历 → Top10 线索"，前端 F-005 被实现为"标杆客户名描述画像"自由搜索，不是 KB 文件上传驱动；`docs/features-inventory.md:64-69` 明确标注为 regression 待重做。

### Agent2 风控 (riskctrl)

- **实际 deliverable** (`agent_riskctrl/api.py:1-40`): 暴露 2 端点——`POST /api/riskctrl/dsl_gen`（自然语言→RuleSet JSON）、`POST /api/riskctrl/backtest`（RuleSet + CSV → KS/通过率/坏账率 metrics）；mock=true 切 fixture RuleSet；CLAUDE.md §11 标记 v3.1。
- **缺口 vs Original Intent**: PRD 要求 PDF 导出完整回测报告，当前端点无 export_pdf/export_docx；差错案件诊断（case_diagnosis）端点缺失；PRD 3 场景（小微信用贷 / 消费金融 / 担保圈）中只预置 1 个 fixture RuleSet。

### Agent3 授信 (credit)

- **实际 deliverable** (`agent_credit/api.py:1-23`): 暴露 4 端点——`GET /api/credit/presets/{segment}`、`POST /api/credit/decision`（SSE 3 板块 corporate/small_business/retail）、`POST /api/credit/export_docx`、`GET /api/credit/handoff/demo/{segment}`；前端 F-015~F-019 实装对公/普惠/对私三模式 tab + 四维 Radar + Gauge + 案例 + ScoreRing；CLAUDE.md §11 v3.1。
- **缺口 vs Original Intent**: Agent6 → Agent3 handoff 按钮（PRD 要"Agent6 UI 上加'送 Agent3 做决策'按钮"）当前为 demo stub 路径（`/handoff/demo/{segment}`），不是真 session 串联；决策意见回写 Agent6 报告"审批意见"章节功能未实现。

### Agent4 预警 (alert)

- **实际 deliverable** (`agent_alert/api.py:1-20`): 暴露 5 端点——`POST /api/alert/scan`（SSE 批量扫描）、`POST /api/alert/export_docx`、`GET /api/alert/hitlist`（红/黄/绿榜单持久化）、`GET /api/alert/drill/{cid}`（单客户 drill + LLM 处置建议）、`GET /api/alert/health`；CLAUDE.md §11 v3.1。
- **缺口 vs Original Intent**: Tavily 实搜路径有 401 fallback（`W-C3-A3`），但实际外部信号源（企查查/企信宝）未接；PRD 双路交叉（外部扫描域 + 内部交易域）中内部交易域依赖客户上传流水数据，当前仅 KB_DEMO 解锁模式；前端 AlertWorkspace 已建 F-020~F-023 + F-049/F-055（features-inventory.md:227-260, 589-651），但 4 gate state 模型缺（conflict-register Cat 2-1）。

### Agent5 合规 (compliance)

- **实际 deliverable** (`agent_compliance/api.py:1-22`): 暴露 5 端点——`POST /api/compliance/policy_scan`（SSE 4 阶段：抽规则→抽事件→N×M 矩阵→改/补/强修订）、`POST /api/compliance/matrix_check`（同步矩阵比对）、`POST /api/compliance/export_docx`、`GET /api/compliance/scan`、`GET /api/compliance/health`；合规修订书 3 类型（改/补/强）已实现；CLAUDE.md §11 v3.1。
- **缺口 vs Original Intent**: PRD 要触发源是"政策发布事件驱动"，当前 `policy_scan` 端点为手动上传触发，无事件订阅/推送机制；前端 ComplianceWorkspace 已建 F-024~F-027（features-inventory.md:271-310），违规榜单 UI 业务单号级粒度待验（F-026 冲突矩阵 doc × clause 是否对接业务单号未审）。

### Agent6 报告 (report)

- **实际 deliverable** (`agent_report/api.py:1-23`): 暴露完整 8 端点——v16 主管线 SSE（classifier→generator→QC）、材料上传解析、章节重写、docx 导出、下载等；前端 F-009~F-014 全量实装（ScanCTA 5 步流程 / 模板面板 / 材料上传 grid / 时间流 / A4 预览 + FieldChip 3 态 / 工具栏 5 操作）；CLAUDE.md §11 v16 · 主管线 `v16_pipeline.py`。
- **缺口 vs Original Intent**: 旧 Gradio 单机版归档（`legacy_gradio/`），前端 export_pdf / 生成只读分享链接 / 版本时光机 3 个工具栏按钮为 mock hook 未接真后端；F-014 smoke test pending。

---

## Section 3: 待 worker-A7 决议 (列出来 · 不决策)

以下 N=10 个 gap · 让 worker-A7 后续逐条 Keep / Revert / Rewrite:

| # | Agent | Gap 描述 | Original Intent | Current State |
|---|-------|---------|----------------|--------------|
| G-01 | Agent1 | 前端 QueryBar 产品形态错位 | KB 文件上传 → 外网遍历 → Top10 线索 | 自由搜索输入框 · F-005 标"NEVER CORRECTLY DELIVERED" |
| G-02 | Agent1 | 外网企业池真实遍历 | SearchProvider 实搜 Tavily/企查查 50+ 家 | KB_DEMO mock · 实搜是否启用待验 |
| G-03 | Agent2 | 回测报告导出 | PDF 含图表 + 分析文本 | 无 export_pdf/docx 端点 |
| G-04 | Agent2 | 差错案件诊断场景 | 3 Demo 场景全覆盖 | 仅 1 个 fixture RuleSet · 其余两场景缺 |
| G-05 | Agent3 | Agent6→Agent3 真 session 串联 | Agent6 UI 上"送 Agent3 做决策"按钮接真 ReportJSON | 当前 handoff/demo/{segment} 为 stub fixture |
| G-06 | Agent3 | 决策意见回写 Agent6 报告 | Agent3 决策意见可回写 Agent6 审批意见章节 | 未实现 |
| G-07 | Agent4 | 内部交易域真实数据接入 | 客户上传流水 → 双路交叉命中 | 仅 KB_DEMO 解锁 · 流水上传未接 |
| G-08 | Agent5 | 政策事件订阅驱动 | 新政策发布自动触发巡检（事件驱动） | 手动上传触发 · 无事件推送机制 |
| G-09 | Agent5 | 违规榜单 UI 精度 | 精确到放款业务单号级 | F-026 冲突矩阵 doc × clause · 业务单号粒度待验 |
| G-10 | Agent6 | 工具栏 3 功能接真后端 | PDF 导出 / 分享链接 / 版本时光机可用 | mock hook · 点击不调后端 |

---

## Section 4: Drift Table v1 · 5 列 per gap (worker-A7 · 2026-04-29)

> 升级 Section 3 G-XX list → 5 列 (Original Intent / Current Repo State / Recommendation [Keep/Revert/Rewrite] / Evidence / Owner+Deadline+Acceptance)。
> Recommendation 为 worker-A7 **建议** · 🟡 标 PM 裁决项 · 🟢 标低争议直接可推。
> Owner 列指派遵 phase-a-charter §2-3 worker 边界 + naming-ssot consumer 表。
> Deadline 默认 = Phase A end (per 硬线 #7 master+sub PRD) 或 Phase B-3 (per PM 拍板 #2 推延项)。

### 4.1 Agent1 · 全渠道流量匹配 / 获客 (channel)

| Gap | Original Intent (PRD) | Current Repo State | KRR | Evidence | Owner / Deadline / Acceptance |
|-----|-----------------------|--------------------|-----|----------|-------------------------------|
| G-01 | KB 文件上传（已成交客户名录 + 政策 + 产品目录）→ 抽画像 → 外网遍历 → Top10 look-alike 线索 + 匹配理由 + Top3 产品推荐（飞书 wiki QOzbwMgyciBkfWko5Z3cmIfhnhf · 本地 PRD_全渠道流量匹配_v2.0.md） | F-005 ChannelWorkspace QueryBar 实装为"自由搜索标签"输入 · features-inventory.md:62-68 标 "NEVER CORRECTLY DELIVERED · 产品定位错 · 待重做" · 无 KB grid 上传 + 无 Top3 产品 panel | 🟢 **Rewrite** · 产品形态错位 · 必须改 KB 文件上传驱动 · MVP 路径不可妥协 | 飞书 PRD §1-2 · `web/src/app/archive/channel/_components/ChannelWorkspace.tsx` (F-005) · `docs/features-inventory.md:62-68` · conflict-register Cat 0-行 4 | A4-channel (依赖 A3 channel pilot 完) / Phase A end / KB 上传 grid + 外网遍历 SSE + Top10 候选 panel + Top3 产品 panel · F-005 inventory 改 RECOVERED · Playwright smoke pass |
| G-02 | SearchProvider 实搜外网企业池 50+ 家 (Tavily / 企查查 / 企信宝) · 候选含 industry/geo/scale/similarity 4 字段 (Q-041) · 候选不足时显式标 blocked_by_env · 不 silent mock | KB_DEMO mock 路径仍存 · `agent_channel/realtime_stream.py:339` Tavily key 缺时 silent mock_fallback (conflict-register Cat 11-4) · banner-spec 规则 2 未实装 | 🟢 **Rewrite** · silent fallback 违 banner-spec § 3.5 形态硬线 + bank delivery DoD 体验红线 | `agent_channel/realtime_stream.py:339` · banner-spec.md · `decisions-log.md` Q-041 · `shared/sources/impls/enterprise_info.py` | A3 (channel pilot · banner-spec 实装) + A4-channel (实搜接通) / Phase A end / Tavily key 缺时显 banner ＋ 50+ 候选返 ＋ 4 字段全 ＋ smoke `web/tests/regression/channel-pilot-4gate.spec.ts` 含 banner case |

### 4.2 Agent2 · 风控策略运营 (riskctrl)

| Gap | Original Intent (PRD) | Current Repo State | KRR | Evidence | Owner / Deadline / Acceptance |
|-----|-----------------------|--------------------|-----|----------|-------------------------------|
| G-03 | 回测完成后输出 PDF 报告含 KS/AUC/通过率/坏账率图表 + 自然语言分析 (飞书 wiki CQfMwbT9NiTk2pksMqXcunMPnWd · 本地 PRD_风控策略运营_v1.0.md) | `agent_riskctrl/api.py:1-39` 仅 2 端点 (dsl_gen + backtest) · **无 export_docx / export_pdf** · 前端 RiskctrlWorkspace 已调（conflict-register Cat 13-1 · 404 on prod） | 🟢 **Rewrite** · 端点缺 = 前端 dead button · 银行客户报告导出是核心 PRD 锚 | `agent_riskctrl/api.py:1-39` · `web/src/lib/api/riskctrl.ts:7` (404 容忍 stub) · 飞书 PRD §3 (PDF 报告需求) | A4-riskctrl + A6 (export contract) / Phase A end / `/api/riskctrl/export_docx` + `/api/riskctrl/export_pdf` 通 + 前端按钮调 + smoke pass |
| G-04 | PRD 3 demo 场景全覆盖 (小微信用贷 / 消费金融 / 担保圈) + case_diagnosis 端点 (差错案件诊断) | `agent_riskctrl/` 仅 1 fixture RuleSet · **无 case_diagnosis 端点** · 前端 F-028~F-031 仅消费 1 场景 (features-inventory.md:315-348) | 🟢 **Rewrite** · 1/3 场景 + 缺核心端点 = 不可演示完整生命周期 | `agent_riskctrl/api.py` · 飞书 PRD §2 (3 场景) · `docs/features-inventory.md:315-348` (F-028~F-031) | A4-riskctrl / Phase A end / 3 fixture 解锁 + `/api/riskctrl/case_diagnosis` 通 + F-028~F-031 三场景切换 smoke pass |

### 4.3 Agent3 · 授信决策辅助 (credit)

| Gap | Original Intent (PRD) | Current Repo State | KRR | Evidence | Owner / Deadline / Acceptance |
|-----|-----------------------|--------------------|-----|----------|-------------------------------|
| G-05 | Agent6 报告 UI 上"送 Agent3 做决策"按钮直接传 ReportJSON · Agent3 90 秒决策 dashboard 真消费 (飞书 wiki OOTtwSlD5iOzIlkNwMYc84JTnVb · 本地 PRD_授信决策辅助_v2.0.md) | `/api/credit/handoff/demo/{segment}` stub fixture · 真 session 串联未实现 (conflict-register Cat 0-行 4 + 行 5) · F-015~F-019 自跑独立 state 不消费 ReportJSON | 🟡 **Rewrite (PM 拍板归属)** · 属 A6 handoff schema (定字段) + A4-credit + A4-report (consumer 真接) · 不属 A7 PRD 单独项 · codex 反对 PRD 越界占用 schema 设计 | `agent_credit/api.py` (stub handoff) · `web/src/app/archive/credit/_components/CreditWorkspace.tsx:1568-1635` (EmptyState 注释 Agent6 handoff onClick 不真消费) · 飞书 PRD §4 | A6 (定 schema · Agent6.report_json → Agent3.decision_input) + A4-credit + A4-report (真接) / Phase A end (schema) + Phase B-3 (真接 e2e) / handoff schema doc + e2e smoke `report → credit handoff` 真过 |
| G-06 | Agent3 决策意见可回写 Agent6 报告"审批意见"章节 (双向闭环) | 未实现 (conflict-register cat 0 派生) | 🟡 **Rewrite (PM 拍板归属)** · 同 G-05 逻辑 · 双向 schema + 双 consumer | 飞书 PRD §5 双向 · `agent_credit/api.py` 无 writeback endpoint · `agent_report/api.py` 无 inbound 章节注入 | A6 (schema 加 decision → report writeback row) + A4-credit (产出 writeback) + A4-report (回写章节) / Phase B-3 / 双向 schema doc + e2e smoke `decision → report 章节注入` 真过 |

### 4.4 Agent4 · 贷中风险预警 (alert)

| Gap | Original Intent (PRD) | Current Repo State | KRR | Evidence | Owner / Deadline / Acceptance |
|-----|-----------------------|--------------------|-----|----------|-------------------------------|
| G-07 | 客户上传"在贷客户池 + 内部流水 + 预警规则库"3 类知识库 → 双路交叉命中 (外部扫描域 + 内部交易域) → 红/黄/绿榜单 (飞书 wiki YrjDwayKIi6BqJkpfgncb1Qvn5c · 本地 PRD_贷中风险预警_v2.0.md) | F-020~F-023 + F-049/F-055 三灯墙 + 队列 + drill 已实装 (features-inventory.md:227-260, 589-651) · 但内部交易域**仅 KB_DEMO 解锁** · 流水 upload + 解析 endpoint 未接 | 🟢 **Rewrite** · 内部交易域是 PRD 核心能力 (双路交叉非单路) · 不接流水 = 半 Agent · 违 §3.5 形态硬线 (mock 不替 Agent 做"本该外搜的工作") | `agent_alert/api.py:1-20` · CLAUDE.md §3.5 表 row 5 (Agent4 多表 mock) · 飞书 PRD §3 双路 | A4-alert + (data-foundation worker per Q-028 5 原则 · 多表 csv 形态) / Phase A end (流水 upload + 解析) + Phase B-3 (双路 cross e2e) / 流水 upload endpoint + 解析 + 跨域 hit list smoke pass |

### 4.5 Agent5 · 合规巡检 (compliance · per PM Cat 8 拍板)

| Gap | Original Intent (PRD) | Current Repo State | KRR | Evidence | Owner / Deadline / Acceptance |
|-----|-----------------------|--------------------|-----|----------|-------------------------------|
| G-08 | 触发源 = **政策发布事件驱动** (新政策发布自动 push 触发巡检 · 不是定期巡检) (飞书 wiki ZMeywAaEJi7ALEkwb9uc4cFnnqc · 本地 PRD_合规巡检_v2.0.md) | `agent_compliance/api.py:1-22` policy_scan 端点为**手动上传触发** · 无事件订阅 / webhook / cron | 🟡 **PM 拍板** · 事件驱动 vs 手动上传是 Agent5 与 Agent4 边界本质 (CLAUDE.md §4 触发列) · 但事件订阅工程量大 · MVP 路径建议: Phase A 保留手动 + Phase B 接事件源 (银保监 RSS / 央行公告 webhook 模拟) | `agent_compliance/api.py:1-22` · CLAUDE.md §4 row 5 (Agent5 触发源 = 政策事件) · 飞书 PRD §1 触发源 | TBD per PM 决: (a) Phase A 真接事件 → A4-compli + 主 CLI fix-forward · (b) Phase A 仅文档 acceptance "手动允许 · 事件待 B" → 飞书 PRD 标 deferred / Phase B end (若选 b) / 事件订阅 cron 或 webhook 真触 OR PRD 文档 deferred 标记落 |
| G-09 | 违规榜单 UI 精度 = 精确到放款业务单号级 (而非合同级 / 客户级粗粒度) | F-026 冲突矩阵 doc × clause 已实装 · 业务单号粒度**待验** (features-inventory.md:291-300) · Drawer 对照纸是否含业务单号 cell click 未审 | 🟡 **验后决** · 主 CLI 跑真路径看 F-026 cell · 若已对接业务单号 = Keep · 若仅 doc/clause 粗粒度 = Rewrite | `web/src/app/archive/compliance/_components/ComplianceWorkspace.tsx` · F-026 (features-inventory.md:291-300) · 飞书 PRD §4 榜单粒度 | A4-compli (验后决 Keep / Rewrite) / Phase A end (验) + Phase B-3 (Rewrite 时落地) / F-026 cell click 显业务单号 OR PRD 显式 acceptance 落"合同级" |

### 4.6 Agent6 · 报告生成 (report)

| Gap | Original Intent (PRD) | Current Repo State | KRR | Evidence | Owner / Deadline / Acceptance |
|-----|-----------------------|--------------------|-----|----------|-------------------------------|
| G-10 | F-014 工具栏 5 操作 (Word / PDF / 分享 / 版本 / 打印) 全接真后端 (飞书 wiki E9z8wJnDRiaI4ckmeH1cYcQknXc + JY93w1r0aibCeXkSEoLcs8F7nTw · 本地 PRD_报告生成助手.md v1.0 + 规划版 v2.3) | F-014 工具栏 5 操作 · Word / 打印 已通后端 · **PDF / 分享链接 / 版本时光机 3 功能 mock hook · 不调后端** (features-inventory.md:159-170) · F-014 smoke pending | 🟢 **Rewrite** · 工具栏 mock = dead button · 违 bank delivery DoD 体验红线 (用户触碰每一层必须丝滑) · F-014 smoke 也 pending | `web/src/app/archive/report/_components/ReportWorkspace.tsx` (F-014) · features-inventory.md:159-170 · `agent_report/api.py:1-23` (无 export_pdf / share / version 端点) | A4-report / Phase A end / `/api/report/export_pdf` + `/api/report/share` + `/api/report/version` 三端点通 + 前端调 + F-014 smoke pass |

### 4.7 Drift Coverage Summary

| Source | 数量 | A7 接手处理 |
|---|---|---|
| 飞书 7 PRD doc (Agent1-6 + 报告 v2.3 规划版) | 7 | ✅ Section 1 已 intent extraction · 4.1-4.6 cite |
| 本地 fallback `docs/PRD_*.md` | 12+ (v1.0/v2.0/v3.0/v3.1) | ✅ 选最新 v 版交叉验证 (本表 Evidence 列) |
| Repo 实际 state | 5 agent_*/api.py + 6 workspace.tsx | ✅ Section 2 + 4.x 全 cite file:line |
| 新增 PRD-level gap | 0 (无新发现 · 10 G-XX 已穷举飞书 7 doc + 本地 vs repo 对比) | n/a |
| 跨 cat 派生 gap | Cat 0 部分 (workbench 形态) → 已归 Phase B-3 (PM 拍板 #2) · 不再为 PRD 单独项 | 已 ackn |

---

## Section 5: PM 裁决候选清单 (worker-A7 不自决 · 提建议给 PM)

> 用法: PM 逐条 Keep / Revert / Rewrite 拍板 · 拍板后 worker-A7 进 master + 6 sub-PRD draft (Signal: WORKER-A7-PRD-MASTER-DONE 才 fire)。
> 🟢 = worker-A7 建议低争议可推 · 🟡 = PM 拍板归属 / 范围 / 时点。

| Gap | Agent | 我建议 KRR | Rationale (≤120 char) | 拍板项 | 拍板后 owner |
|-----|-------|-----------|----------------------|--------|--------------|
| G-01 | Agent1 | 🟢 Rewrite | 产品形态错位 · 自由搜索 vs KB 上传 → look-alike 是 PRD 核心隐喻 · 不可妥协 | 默认追认 | A4-channel |
| G-02 | Agent1 | 🟢 Rewrite | silent fallback 违 banner-spec + bank delivery DoD · 必须真搜 + banner | 默认追认 | A3 + A4-channel |
| G-03 | Agent2 | 🟢 Rewrite | 端点缺 = 前端 dead button · 银行客户 PDF 报告需求是核心 | 默认追认 | A4-riskctrl + A6 |
| G-04 | Agent2 | 🟢 Rewrite | 1/3 场景 + 缺 case_diagnosis = 不可完整演示 · 客户走访前必补 | 默认追认 | A4-riskctrl |
| G-05 | Agent3 | 🟡 Rewrite (归属决) | 真 session 串联属 A6 schema + 双 consumer 实接 · 不属 PRD 单独 backlog (codex dissent) | 拍 (a) PRD 锚 + A6 schema 双线推 / (b) 仅 A6 schema doc · e2e 推 Phase B-3 | A6 (schema) + A4-credit/report (consumer) |
| G-06 | Agent3 | 🟡 Rewrite (归属决) | 同 G-05 · 双向闭环属 A6 双向 schema + 双 consumer · 不属 PRD 范围 | 拍 (a) (b) 同 G-05 | 同 G-05 |
| G-07 | Agent4 | 🟢 Rewrite | 内部交易域是 Agent4 核心能力 · 不接流水 = 半 Agent · 违 §3.5 mock 形态硬线 | 默认追认 | A4-alert + data-foundation |
| G-08 | Agent5 | 🟡 PM 拍板 | 事件驱动 vs 手动上传是 Agent5 与 Agent4 触发源边界本质 · 但事件订阅工程量大 | 拍 (a) Phase A 真接 / (b) Phase A 手动 + Phase B 接事件 (建议 b) | (a) A4-compli + 主 CLI / (b) A4-compli (Phase A doc) + B-3 (实装) |
| G-09 | Agent5 | 🟡 验后决 | F-026 业务单号粒度待主 CLI 跑真路径看 cell · 不能盲拍 | 拍 (a) 验后 Keep · (b) 验后 Rewrite · (c) 退合同级 acceptance | A4-compli |
| G-10 | Agent6 | 🟢 Rewrite | 工具栏 mock = dead button · 违 bank delivery DoD 体验红线 + F-014 smoke pending | 默认追认 | A4-report |

### 5.1 PM 裁决批量 GO 路径 (省 PM 逐条 review)

per RESET_MASTER_PLAN §6 + STEP-2-PM-RULED 范式 (PM 不逐条 87 entries · 默认按 worker 建议跑) · A7 申请: PM 一句"剩下的 GO" → 8 个 🟢 + 2 个 🟡 中 (G-08 / G-09) 默认采**worker-A7 建议路径** (G-08 = 选 b 推 Phase B-3 · G-09 = 选 a-验后 Keep 优先) · 仅 G-05 / G-06 (双 🟡 归属决) 必拍归属 (a vs b)。

PM 拍板 commit signal 建议: `WORKER-A7-PRD-DRIFT-PM-RULED` (与 Step 2 PM-RULED 同 pattern)。

### 5.2 飞书双写流程 (拍板后)

per A7 onboarding §1.1 row 6 + codex draft Block A:
1. `lark-cli wiki spaces get_node` 取每个飞书 PRD wiki node 的 `obj_token` (7 doc · URL 已在 Section 1)
2. `lark-cli docs update` (覆盖 / 追加 / 替换 per `docs/prd/{master, agentN-*}-v1.md` 内容)
3. commit 信飞书 doc token + 本地 commit hash 双向链接 (per state-snapshot 硬规)
4. PRD 双写 log 落 `docs/prd/master-2026-04-29.md` 末尾 § "Feishu Double-Write Log"

---

## Section 6: 我新发现的 PRD-level gap (worker-A7 · 2026-04-29 · 0 新发现)

通过对比飞书 7 doc + 本地 PRD v2.0/v3.0/v3.1 fallback vs repo 实际 state · **未发现新 PRD-level gap** (产品功能形态层面)。Section 3 G-01..G-10 已穷举。

A7 owner 范围内的其他 cat (12 evaluation drift / 16 角色 drift / 11 legacy_gradio / 部分 1 active rule) 不属 PRD 产品形态 gap · 走 §1.2 + §1.3 单独 commit (verbatim 在 onboarding §1.2 + §1.3) · 不混入本 drift table。

---

**Author**: worker-A7 · 2026-04-29
**Status**: drift table v1 (10 G-XX 5 列) + PM 裁决候选 ready · 等 PM 拍板 cycle (signal: `WORKER-A7-PRD-DRIFT-PM-RULED`)
**Next**: PM 拍板后 (per §5.1 批量 GO 或逐条) → master + 6 sub-PRD draft + 飞书双写 → signal: `WORKER-A7-PRD-MASTER-DONE`
