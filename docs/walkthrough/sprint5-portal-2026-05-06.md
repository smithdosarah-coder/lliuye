# Sprint 5 RM Portal 串联 walkthrough

> 验收日 · 2026-05-06
> Production · `https://liuye.me/login`
> 4+1 角色 × 6 Agent · row-level RBAC + ActionGate (Sprint 3 ship)

## 5 fixed users (per Q-052 商务团队负责)

| 角色 | 用户名 | 路径 priority |
|---|---|---|
| 客户经理 (RM) | 王哲 | channel → report → credit |
| 审贷员 | 李华 | report → credit → alert |
| 合规官 | 周敏 | compliance → report → alert |
| 风险经理 | 陈凯 | riskctrl → alert → credit |
| admin (PM) | 刘野 | 全 6 Agent 任意切 |

## RM 王哲 walkthrough · 90 秒拓客 → 90 分钟成单

### 步骤 1 · 登录 → /today (~5 秒)

1. 访问 `https://liuye.me/login`
2. 输入 `wangzhe / wangzhe123` (RM 角色)
3. 自动跳转 `/today` · RmHome view 显示
4. 看到 "拓客 → 尽调 → 授信 闭环" CrossAgentWorkflowCard · 3 CTA

### 步骤 2 · 拓客 (Agent1 channel · 90 秒)

1. 点 CrossAgentWorkflow CTA "→ 拓客 (Agent1)" 或 顶栏 ARCHIVE → channel
2. `/archive/channel` workspace · 输入 query "苏州工业园区 · 制造业 · 注册资本 ≥ 5000 万"
3. 点 "开始扫描" CTA · ScanCTA 进度条 5 阶段 (~30 秒)
4. **Top N 候选企业** (Sprint 5 marker) 显示 · 全部可点击 · SignalTimeline dropdown 切换
5. 点选第 N 家候选 → CandidateDetailDrawer 弹 · 看 4 维度证据链 (industry/scale/region/signal)
6. 点 BE12 personal_insight (Sprint 3 ship) · LLM grounded talking_points (opener / key_messages / objection / closing)
7. 90 秒内: 5 候选 + 信号 + 话术 全齐

### 步骤 3 · 尽调 (Agent6 report · 5 分钟)

1. CrossAgentWorkflow CTA "→ 尽调 (Agent6)" · 或 archive → report
2. `/archive/report` workspace · 上传材料文件夹 (mock: 3 docx + 2 xlsx + 1 pdf)
3. ScanCTA 5 阶段 · v16 主管线 (classifier → generator → QC gate)
4. **Truth-First drawer** (Sprint 5 D3 ship) · 审贷员核对哪些字段是 Python 计算 (5 项) vs LLM grounded (3 项)
5. ReportLiveSections 显示分章节 · onRefine 单段重生
6. 导出 docx / pdf · 文件落 RM 桌面

### 步骤 4 · 授信 (Agent3 credit · 5 分钟)

1. CrossAgentWorkflow CTA "→ 授信 (Agent3)"
2. `/archive/credit` workspace · 输入 ReportJSON (Agent6 上一步生成)
3. 看 PrimaryProfileHero · DashboardBand · 决策建议
4. 点 "↩ 回写 Agent6 报告" CTA (Sprint 4 D1 Atomic 4 ship · placeholder)
5. 看 4 维度评分 + 红线 + 案例对比

总耗时: ~10 分钟内 走完拓客 → 尽调 → 授信主链路。

## 审贷员 李华 walkthrough

1. 登录 `lihua / lihua123` · 跳 `/today` CreditOfficerHome view
2. CrossAgentWorkflow CTA "→ 审报告 (Agent6)"
3. `/archive/report` 看 RM 提的报告 + Truth-First drawer 核对确定性字段
4. CTA "→ 决策 (Agent3)" · 看 Agent3 评分 + 红线
5. CTA "→ 跟踪贷后 (Agent4)" · 看 alert 信号灯

## 合规官 周敏 walkthrough · D3 重排后路径

1. 登录 `zhoumin / zhoumin123` · 跳 `/today` ComplianceOfficerHome view
2. CrossAgentWorkflow CTA "→ 政策 (Agent5)"
3. `/archive/compliance` workspace **新三栏布局** (Sprint 4 D3 Atomic A ship):
   - 顶部 ComplianceStatsBar: 违规数 / 命中率 / 严重度分布 / 业务单号数 + 三视角 tabs
   - 折叠 "扫描设置" (上传 + 政策 + 制度 + 流水 + 最近会话)
   - 三栏: ViolationListPanel (left · 自动选首条 high-severity) + ViolationDetailPanel (mid · 5 字段证据链) + RevisionPanel (right · 一键下发 RM disabled hook)
   - 折叠 "深入分析" (矩阵 / 漏斗 / 时间线)
4. 选中违规 → 中栏看 5 字段 (业务单号 / 政策摘录 / 业务摘录 / AI 理由 / source row id)
5. 右栏整改建议 → 点 "↗ 一键下发 RM" (disabled · Sprint 5 后端实装) · 替代 manual 转交

## 风险经理 陈凯 walkthrough

1. 登录 `chenkai / chenkai123` · 跳 `/today` RiskManagerHome view
2. CrossAgentWorkflow CTA "→ DSL (Agent2)"
3. `/archive/riskctrl` · IM 风格 DSL 协作 (riskctrl 不动 · IM 是 DSL 协作核心 · per Sprint 4 决议)
4. 输入自然语言 "对公制造业 · 资产负债率 > 70 拒绝" → AI 生成 DSL
5. 5 万行回测 (Q-040 MAX_ROWS=50000) · 看 KS / 通过率 / 坏账率 / 利润影响
6. CTA "→ 回测 (Agent2)" · 上线决策上链 ledger
7. CTA "→ 预警监控 (Agent4)" · 看实时 alert 信号灯

## admin (刘野) walkthrough

- ArchiveGrid (Sprint 4 D2 d ship) · 6 tile 任意点击 · 5 角色优先排序 dynamic
- 任意 Agent workspace 全权访问

## 验收 checklist

| Item | 验收标准 | 当前状态 |
|---|---|---|
| 5 用户登录 | 5 用户 · 各 home view 正确 | ✅ Sprint 3 ship |
| RBAC enforce | 角色不可调越权 endpoint | ✅ ACCESS_V2 enforce |
| 跨 Agent 链路 CTA | RmHome 等 4 RoleHome 显示 CrossAgentWorkflow | ✅ Sprint 4 D2 Atomic 5 |
| Agent5 三栏 | settings fold + List+Detail+Revision + OutputPanel fold | ✅ Sprint 4 D3 Atomic A |
| Agent5 stats bar | 4 metrics + 三视角 tabs | ✅ Sprint 4 D3 Atomic B+C |
| Agent5 证据链 5 字段 | 业务单号/政策摘录/业务摘录/AI 理由/source row id | ✅ Sprint 4 D3 Atomic D |
| Agent5 一键下发 RM | disabled hook · title fallback | ✅ Sprint 4 D3 Atomic E |
| Agent5 上传收敛 | UploadRail 进 settings fold | ✅ Sprint 4 D3 Atomic F |
| Agent4 mid 列 | 删 IM · 进度 placeholder | ✅ Sprint 4 D4 |
| Agent6 Truth-First drawer | 8 字段清单 (5 truth + 3 LLM) · CLAUDE.md §3.1 引证 | ✅ Sprint 5 D3 |
| Agent1 Top10 affordance | 全候选可点 + 90 秒 hint | ✅ Sprint 5 D1-2 |
| ECS production live | https://liuye.me/login HTTP 200 | ⚠️ 5fcbbea+765ab96 ship · 8afa192+ 待 deploy (github timeout) |

## Sprint 5 后续 (post-验收)

- 一键下发 RM endpoint (RBAC + dispatch event audit)
- Conflict schema normalized envelope (D4 backend RFC)
- BE12 千人千面话术 LLM A/B 数据
- Top10 fixed count + confidence score 后端调优
- 跨 Agent ledger query 分析 (decision_ledger + handoff)

## 关键文档引证

- `CLAUDE.md` §3.1 确定性 vs 概率性 · §3.2 MCP 域拆分 · §3.5 反结果导向 5 原则 · §3.7.5 BE7 决策账本
- `docs/contracts/llm-prompt-contract.md` v1.0 · 8 段 SSOT
- `docs/contracts/decision-ledger.md` v1.0 · sqlite + PII hash
- `docs/contracts/agent-naming-ssot.md` v1.1 · 8 维度命名
- `docs/poc_landable_2026-05-06.xlsx` · 4 维度 12 指标 47% → 78% 落地版
