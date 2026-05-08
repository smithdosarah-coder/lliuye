# 6 Agent ALL IN 真产品最终执行方案 · 100% KT

> **新 CLI 接手时第一句指令**:
> 「读 `AGENT_IDENTITY.md` 和里面列的所有文件 · resume 状态后等我指令」

> **本文档定位**: PM 2026-05-08 ratify 的最终方案 · 主 CLI Claude Opus 4.7 + Codex gpt-5.5 xhigh 真辩论 R1+R2+R3 收敛 · 用于新 CLI session 100% 接手

---

## 0. 一句话定位

6 agent 信贷矩阵 · 5 个还在 mock 的 agent (报告/授信/预警/风控/合规) **全 ALL IN 真产品化** · 用 mesh 7 cmd 并行干 · 估 2-2.5 天完成 (vs 串行 4-5 天).

---

## 1. 项目背景 (新 CLI 必看)

### 1.1 6 Agent 矩阵 + 5 角色

| Agent | 中文 | 用户 | 当前状态 (2026-05-08 audit) |
|---|---|---|---|
| channel 获客 | Scout | RM 客户经理 (王哲) | ✅ ALL IN 改造完 (本 session 实战) |
| report 报告 | Report Press | RM | 🔴 全 mock · 7 处 mock 字眼 + 全套 mock UI |
| credit 授信 | (3 板块: 对公/普惠/对私) | 审贷员 | 🔴 全 mock · 47 分 D 级固定 |
| alert 预警 | (双路交叉 · 客户行为驱动) | 风险经理 | 🔴 全 mock · 3+7+90=100 户标准 mock |
| riskctrl 风控 | Forge | 量化 | 🔴 全 mock · ModePill+history+preset 残留 |
| compliance 合规 | (政策事件驱动) | 合规官 | 🔴 全 mock · 历史 session 下拉 |

### 1.2 5 角色 RBAC

| 角色 | 主调 | read |
|---|---|---|
| RM | channel + report | credit + alert |
| credit_officer 审贷员 | credit | report + alert |
| compliance_officer 合规官 | compliance | report + alert |
| risk_manager 风险经理 | riskctrl + alert | credit |
| admin 总行审计 | 全 6 | 全 6 |

### 1.3 业务全链路

```
RM 输入诉求 (channel) → 找候选 → handoff → report 写尽调 → handoff →
credit 审贷决策 → handoff → 上线 → alert 持续预警 (风险经理) →
合规官 compliance 政策扫 → 量化 riskctrl 上线策略
```

---

## 2. 已完成 (本 session 实战)

### 2.1 channel 单 agent ALL IN 改造 (6 step + 真根因 fix)

| Step | Commit | 干啥 |
|---|---|---|
| 1+1.5 | `de79725` `1c6aa34` | 删 mock UI (ModePill/历史 session/DEMO 难度) + EMPTY_SESSION + empty state 文案 |
| 2.1 | `ef5ba13` | 字段级溯源 evidence drawer (前端消费后端 dataSources) |
| 2.2 | `707a8ad` | 实体归一基础设施 shared/entity_resolver/ + 21 单测 |
| 2.3 | `4d5ab20` | 切真生产 web 搜索器 (demo_mode=False · 真接 TAVILY) |
| 2.4a | `1161028` | 雷达图按候选切换 (前端消费后端 radar_8axis dict) |
| **真根因** | `c074d43` | **候选企业 unique id (USCC/md5/idx 派生)** · find 命中错误根因 fix |

### 2.2 channel ALL IN 真锚点 (用作 ROI 基线)

- UI 改造 ~2 天
- 后端 candidate id 修 30 min
- 实体归一 PoC 2 小时 (21 单测)
- per-candidate radar 1 小时
- **单 agent 总: ~3-4 天**

### 2.3 nginx cache 修 (cross-agent · production live)

- HTML `Cache-Control: no-cache, no-store, must-revalidate` (用户每次拿新版)
- chunk JS (带 hash) `public, max-age=31536000, immutable`
- 客户经理无需 F12/隐身模式排查 cache · 普通刷新即新版

---

## 3. ALL IN 5 Agent 改造方案 (R3 融合)

### 3.1 改造路线 (按优先级 · 串行)

| 顺序 | Agent | 工时粒度 | 关键交付 |
|---|---|---|---|
| 1 | report | 短 | LiveShell 成稿 + 引证抽屉 + 时效徽章 |
| 2 | credit | 中 | 决策账本 + 证据链评分 · 可追审批包 |
| 3 | alert | 中 | watch 事件驱动 · 预警队列 |
| 4 | riskctrl | 长 | 吃贷后 + 审批反馈 · 策略闭环 |
| 5 | compliance | 中 | 监管版本追责 · 变更台账 |

### 3.2 共性架构 (3 个新 + 4 个已有推广)

**新 3 个**:
- `LiveShell`: 6 agent 统一 "启动→流式→操作" 框架 · 接口 `start(flow,user,ctx)→run_id` / `stream(run_id)→SSE` / `action(run_id,cmd)`
- `EvidenceDrawer`: 统一证据展示 · `attach(claim,源,定位,版本,hash)→evidence_id`
- `SourceHealth`: 数据源健康检查 · `check(源)→新鲜度/SLA/认证/血缘/分数`

**已有 4 个推广** (现只 1-2 agent 用):
- `DecisionLedger` 决策账本 (Q-055 已有 · 现 credit 用)
- `EntityResolver` 实体归一 (本 session PoC 已有 · 21 单测)
- `FreshnessBadge` 时效徽章 (后端 ready · 前端没消费)
- `RiskRadar` 风险雷达 (channel 在用 · sse_extras.build_radar_8axis)

### 3.3 数据 phase 策略

**Phase 1 公开** (现做): 政府公示 · 银保监 RSS · Wind 公开 · v16 解析 (标 stub) · 公开司法工商 · 监管原文
**Phase 2 行内** (PM 谈): 央行征信 · 行内交易 · 行内授信 · 贷后系统 · 审批反馈

**硬线**: v16 标 stub · phase 2 必替换真源 · 凡需 verify 主体/工商/司法/征信场景

### 3.4 业务流真闭环 wire (5 角色 × 6 agent · 三态)

- **RM**: channel 实时 → report 实时 → credit 异步 → watch 异步 → riskctrl 定时 → compliance 定时
- **审贷员**: credit 实时 → 证据抽屉 → 决策账本异步 → riskctrl 异步
- **合规官**: compliance 定时/实时 → report/credit 异步
- **风险经理**: watch 定时/异步 → alert 实时 → riskctrl 异步
- **量化**: riskctrl 定时 → 回测异步 → credit/report 反馈

### 3.5 5 角色用户体验目标 (量化)

| 角色 | 提升 |
|---|---|
| RM 客户经理 | 写 1 份报告 **2h → 20min** · 每段可追源 |
| 审贷员 | 审 1 笔 **30min → 5min** |
| 合规官 | 政策追版 **月度 → T+1 自动比对** |
| 风险经理 | 贷后异常 **周报 → 事件级推送** |
| 量化 | 策略回测 **3 天 → 半天复现** |

### 3.6 Stop-the-line 10 条红线 (任一触发即 abort)

1. 假 live (silent fallback mock)
2. 假分 (无证据评分)
3. 无证据 claim (AI 输出无溯源)
4. v16 stub 冒充真源
5. 无决策账本版本
6. 无源健康检查
7. 评分无回测
8. 监管条款无原文 hash
9. 审批/贷后反馈丢链路
10. SSE 展示与落库不一致

---

## 4. 执行方式 (Mesh 三阶段)

### 4.1 Phase A · common worker 冻结共性 (Gate: 5 worker 只读通过)

- 1 个 common worker (worktree `mesh/common`)
- 干啥: 冻结 实体/候选/权限/UI shell/API 合同 · 写 3 核心 contract
- 产出:
  - `docs/contracts/entity-resolution-contract.md`
  - `docs/contracts/candidate-identity-contract.md`
  - `docs/contracts/signal-commit-contract.md`
  - LiveShell + EvidenceDrawer + SourceHealth 共性代码 (shared/)
  - lark-base dashboard schema
  - 6 resume 脚本 contract
- Gate: 5 agent worker 各自 read-through 通过 · 没异议
- 工时锚点: ~0.5 天

### 4.2 Phase B · 5 agent worker 并行改造 (Gate: READY-FOR-REVIEW + 证据)

- 5 个 worker (worktree `mesh/{report,credit,alert,riskctrl,compliance}`)
- 各自只改授权域 · import Phase A 共性
- 完成时 fire signal commit `chore(mesh): signal worker <X> ready for mesh merge ALLIN`
- 工时锚点: 1-1.5 天 (并行 wall-clock)

### 4.3 Phase C · 主 CLI 整合 (Gate: 跨 agent 集成通过)

- 主 CLI 收 5 worker signal · cherry-pick 入 main · 跑总验收
- 不串验 (用 mesh signal commit 自动整合 · per Q-054 protocol)
- 部署 + 真测 (Playwright 6 agent 跑一遍)
- 工时锚点: ~0.5 天

### 4.4 总 ROI 锚点 (真锚 · 不喊倍数)

| 路径 | 真估 |
|---|---|
| 现 channel 单 agent 实战 | ~3-4 天 |
| 5 agent 串行 | **4-5 天** |
| mesh 并行 | **2-2.5 天** |
| 加速比 | ~2x (用 signal 时间戳 + 验收日志复盘验证) |

---

## 5. Skill 选型最终清单

**必用 5 个**:
- `multi-cli-mesh` 管 6 窗 · worktree · signal · resume
- `make-plan` 固化 Phase / DoD / gate
- `do` (executing-plans) 执行冻结计划
- `lark-doc` 维护主 PRD
- `lark-base` 维护 handoff/红线/证据 dashboard

**条件用 4 个**:
- `web-access` 仅查外部实时资料
- `browser-automation` + `webapp-testing` 仅验 UI
- `github` 仅 PR/CI
- `smart-explore` 仅大代码结构检索

**不用**: dispatching-parallel-agents (主并行走 mesh) · 视觉/艺术类

---

## 6. 飞书 PRD 双层结构

### 6.1 lark-doc 主 PRD

- 标题: "信贷 6 Agent ALL IN PRD v3 · 2026-05-08"
- 章节: 目标 / 范围 / 角色 / 核心流程 / 非目标 / Phase A/B/C / 验收口径 / 发布风险
- 主 CLI 写 · worker 只评论

### 6.2 lark-base dashboard

- 字段 schema:
  | 字段 | 类型 | 说明 |
  |---|---|---|
  | agent | text | report/credit/alert/riskctrl/compliance |
  | owner | person | 该 worker CLI 责任人 |
  | worktree | text | 路径 |
  | scope | text | 写域 (e.g. agent_report/) |
  | redline | text | 该 agent 必守的红线 |
  | input_contract | text | 依赖的合同 (entity-resolution / candidate-identity / signal-commit) |
  | output_contract | text | 产出 (报告/决策/预警等) |
  | latest_signal | text | 最新 signal commit hash |
  | evidence_url | url | 证据/截图/日志 |
  | blocked_by | text | 阻塞依赖 |
  | status | select | doing / ready / merged / blocked |
  | updated_at | datetime | 最后更新 |
- worker signal 后更新自己行
- 主 CLI 审核 redline + evidence

---

## 7. 桌面脚本 (`launch-all-LIUYE.bat`)

启 7 cmd 窗口:
1. **主 CLI orchestrator** (cwd `D:/claude code/credit_report_agent_work`)
2. **common worker** (cwd `mesh/common`) → 跑 `resume-common.ps1`
3. **report worker** (cwd `mesh/report`) → 跑 `resume-report.ps1`
4. **credit worker** (cwd `mesh/credit`) → 跑 `resume-credit.ps1`
5. **alert worker** (cwd `mesh/alert`) → 跑 `resume-alert.ps1`
6. **riskctrl worker** (cwd `mesh/riskctrl`) → 跑 `resume-riskctrl.ps1`
7. **compliance worker** (cwd `mesh/compliance`) → 跑 `resume-compliance.ps1`

每窗启动后自动:
- cd 到对应 worktree
- 启 claude code CLI
- 第一句指令 "读 AGENT_IDENTITY.md 和里面列的所有文件 · resume 状态后等我指令"

---

## 8. 6 个 resume 脚本契约

### 8.1 `.mesh-launcher/resume-common.ps1`

```ps1
# 读: AGENT_IDENTITY.md + 3 核心 contract + base 行
# 首句: "COMMON resume: freezing shared contracts"
```

### 8.2 `.mesh-launcher/resume-{report,credit,alert,riskctrl,compliance}.ps1`

```ps1
# 读: AGENT_IDENTITY.md + 3 核心 contract + agent onboarding + base 本行 + git log -20 + status
# 首句: "<AGENT> resume: scope locked, checking signals"
```

---

## 9. KT 5 文件 (新 CLI 必读 · 15 min)

新 CLI 接手时**只读这 5 个** (其他 docs 按需):

1. `AGENT_IDENTITY.md` (本 worktree · 身份 + 边界)
2. `docs/contracts/entity-resolution-contract.md` (统一企业实体归一)
3. `docs/contracts/candidate-identity-contract.md` (候选 unique id 标准)
4. `docs/contracts/signal-commit-contract.md` (worker signal commit 模板)
5. `docs/handoff/phase-r3-worker-runbook.md` (Phase A/B/C 操作手册)

---

## 10. AGENT_IDENTITY 模板 (微调要点)

### 10.1 common worker 必加

- 你拥有 shared contract 冻结权
- 任何 shared/API/schema 改动必须先写合同再 signal
- 冻结后只收 RFC · 不直接改 worker 域

### 10.2 5 agent worker 必加

- 你的写域 (e.g. `agent_report/`)
- 禁改域 (`shared/` 不可改)
- 必读 KT 5 文件
- base 行 ID
- 完成信号名 (e.g. `signal worker report ready for mesh merge ALLIN`)
- 证据要求 (Playwright 截图 + commit hash + base 字段更新)
- 遇 shared 合同缺口只提 Q/RFC · 不本地绕开

---

## 11. 已踩坑清单 (新 CLI 必看 · 防再踩)

per `feedback_4_chronic_errors_2026_05_07.md` + `feedback_5_blackspeak_self_check_failed_2026_05_07.md`:

1. **demo 摇摆错** · 反复回 demo 思维 · 必先 grep memory 确认业务阶段
2. **代码当设计意图错** · ModePill 没 onToggle 答"只读" · 实际 bug · 默认 bug 不是 feature
3. **memory 不 internalize 错** · 接 agent 任务先复述用户场景给 PM confirm
4. **估时套人天错** · 不再给小时/天数 · 用"短/中/长"
5. **黑话错** · 输出前必 self-check · 中英混杂 / 编号 / 工具命令 / 角色名都加翻译
6. **后端 silent fallback mock 漏** · WebSearchProvider NotImplementedError 时 realtime_stream 仍可能 fallback Mock · ALL IN 时必清
7. **浏览器 cache 误判** · nginx HTML 默认 s-maxage=31536000 (1 年) · 已修 (no-cache + chunk 长 cache)
8. **候选 id 字段缺失** · 后端 candidate dict 没 id → 前端 find 命中错误 · ALL IN 各 agent 必 verify entity unique id

---

## 12. 新 CLI 接手第一组动作 (resume 后)

1. 读 KT 5 文件 (≤ 15 min)
2. 跑 `git log --oneline -10` 看最近 commit
3. 跑 `py "C:/Users/Mr.S/.claude/skills/multi-cli-mesh/scripts/orchestrator/scoreboard.py"` 看 mesh 状态
4. 看 `docs/handoff/decisions-log.md` tail -50 最近 PM 决策
5. 写 NEW-MAIN-CLI-RESUMED commit (per CLAUDE.md §14 模板)
6. 等 PM verify GO 后正式接手 ALL IN 协调

---

## 13. PM 已拍板 (本 session)

- ✅ Channel ALL IN 路线 (a 选项 · 不 b 不 c)
- ✅ 6 agent 全 ALL IN (R3 方案 a)
- ✅ Mesh 三阶段执行 (R3 收敛)
- ✅ 飞书 PRD 双层 (lark-doc + lark-base)
- ✅ KT 100% + 桌面脚本 + 新 CLI 接手

---

## 14. 待新 CLI 干 (本 session 没做 · KT 标 placeholder)

- [ ] 写 3 核心 contract 真内容 (本文档只列名字 · contract 占位文件由新 CLI Phase A common worker 写)
- [ ] 写 phase-r3-worker-runbook 真内容
- [ ] 创建 6 个 mesh worktree (`mesh/common` + 5 agent)
- [ ] 创建 6 个 AGENT_IDENTITY.md (本文档只给模板)
- [ ] 飞书 PRD 同步 (lark-doc 主 + lark-base dashboard)
- [ ] 写 Phase A common worker 实施计划 (LiveShell + EvidenceDrawer + SourceHealth 抽取)
- [ ] 5 agent worker 各自 onboarding 文档

---

## 15. 关键文件路径速查

### 15.1 本 KT
- `docs/working/allin-final-exec-2026-05-08.md` (本文件)

### 15.2 已有 infrastructure
- `shared/entity_resolver/` (本 session 加 · 21 单测)
- `shared/decision_ledger/` (Q-055 BE7)
- `shared/evidence_freshness.py` (FRESHNESS_SLA_DAYS)
- `shared/data_tiers.py` (4 Tier)
- `shared/recommendation_schema.py`
- `shared/sources/` (Router + 8 source impl)
- `agent_channel/sse_extras.py:build_radar_8axis` (RiskRadar 推广用)
- `shared/sse_envelope.py` (Phase A worker-A2)

### 15.3 桌面脚本 (待更新)
- `C:/Users/Mr.S/Desktop/launch-all-LIUYE.bat` (现 4 cmd · 待扩 7 cmd)
- `C:/Users/Mr.S/Desktop/.mesh-launcher/launch-r3v2.ps1` (现 3 worker · 历史)

### 15.4 mesh 现状
- `D:/claude code/credit_report_agent_work_mesh/{a,b,c}` (R3v2 P0 mesh 用过 · 可清理)
- 待建: `mesh/{common,report,credit,alert,riskctrl,compliance}` (6 个新 worktree)

---

## 16. 来源

- Claude Opus 4.7 + Codex gpt-5.5 xhigh 真双辩论
- Round 1 (74s): 7 题独立方案
- Round 2 (~85s): 双方互挑刺 6+6 处 (codex 接受 6/6 · 主 CLI 接 codex 7/7)
- Round 3 (50s): 7 题最终融合
- PM 2026-05-08 verbatim: "方案通过, 支持 a" + "结合 skill 看怎么完整高效解决" + "辩论方案沿用 (R1 独立 + R2 互挑 + R3 融合)" + "落实 100% KT + 更新桌面脚本 + 新 CLI 执行"

---

**Author**: 主 CLI Claude Opus 4.7 · 2026-05-08
**Status**: PM ratify · 等新 CLI 接手 Phase A common worker 启动
