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
- **缺口 vs Original Intent**: Tavily 实搜路径有 401 fallback（`W-C3-A3`），但实际外部信号源（企查查/企信宝）未接；PRD 双路交叉（外部扫描域 + 内部交易域）中内部交易域依赖客户上传流水数据，当前仅 KB_DEMO 解锁模式；前端 AlertWorkspace 状态待 features-inventory 补录（无 F-XXX 条目）。

### Agent5 合规 (compliance)

- **实际 deliverable** (`agent_compliance/api.py:1-22`): 暴露 5 端点——`POST /api/compliance/policy_scan`（SSE 4 阶段：抽规则→抽事件→N×M 矩阵→改/补/强修订）、`POST /api/compliance/matrix_check`（同步矩阵比对）、`POST /api/compliance/export_docx`、`GET /api/compliance/scan`、`GET /api/compliance/health`；合规修订书 3 类型（改/补/强）已实现；CLAUDE.md §11 v3.1。
- **缺口 vs Original Intent**: PRD 要触发源是"政策发布事件驱动"，当前 `policy_scan` 端点为手动上传触发，无事件订阅/推送机制；前端 ComplianceWorkspace 无 F-XXX 条目，违规榜单 UI 的精确到业务单号级是否实现待验。

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
| G-09 | Agent5 | 违规榜单 UI 精度 | 精确到放款业务单号级 | 前端 ComplianceWorkspace 无 F-XXX 条目 · 待验 |
| G-10 | Agent6 | 工具栏 3 功能接真后端 | PDF 导出 / 分享链接 / 版本时光机可用 | mock hook · 点击不调后端 |
