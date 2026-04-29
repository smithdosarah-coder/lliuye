# Product North Star · 走歪诊断 + 修正方向

> reset 工程产品形态校准锚点 · 任何前后端架构决策都要先对齐本文。

---

## 1. 原始设计意图 (memory + CLAUDE.md §1-§4 + decisions-log 提取)

### 1.1 产品定位

银行客户经理 / 审贷员 / 合规官 / 风险经理 用的 **AI 助手矩阵** · 覆盖贷前获客 / 授信决策 / 贷中预警 / 贷后合规 全流程。初期 copilot (人审核) · 成熟后 autopilot 过渡。

### 1.2 6 Agent 边界 (verbatim CLAUDE.md §4)

| Agent | 触发 | 输入 | 产出 | 不做 |
|---|---|---|---|---|
| Agent1 获客 | 客户经理发起 | 画像描述 + 知识库 | 候选企业 + 信号时间线 + 产品推荐 | 授信决策 |
| Agent2 风控 | 策略经理发起 | 策略诉求 + 样本 CSV | DSL 规则 + KS / 通过率回测 | 个案决策 |
| Agent3 授信 | 审贷会发起 | Agent6 ReportJSON + 材料 | 四维评分 + 额度 / 期限建议 + 红线 | 写报告 |
| Agent4 预警 | **客户行为变化驱动** | 在贷客户池 + 规则库 | 红/黄/绿分级客户榜单 | 单点手动查询 |
| Agent5 合规 | **政策发布事件驱动** | 新政策 + 业务制度库 | 违规冲突点明细清单 | 定期巡检 / 财务审计 |
| Agent6 报告 | 客户经理发起 | 企业材料 + 模板 | ReportJSON + Word | 决策意见 |

### 1.3 关键 pivot (memory · 不在 CLAUDE.md 但 PM 早决议)

- **Agent1 = look-alike 获客** · 不是"全渠道流量匹配" · 基于已成交客户 + 外网搜相似企业
- **Agent3 = Agent6 下游决策引擎** · 含对公+对私双板块 · 不是独立打分
- **Agent4 = 知识库驱动批量扫描** · 外/内双路交叉命中 · 不是单点查询
- **Agent5 = 政策事件驱动** · 不是定期巡检
- **Agent6 = Evidence-First 三阶段 + QC blocker** · 财务确定性计算 + LLM 消费 · 不让 LLM 现场算

### 1.4 6 Agent 闭环路径 (业务流程串)

```
RM (客户经理)
  → Agent1 拓客 (look-alike) 找候选
  → Agent6 出尽调报告 (材料解析 → 字段抽取 → 段落生成 → QC)
  → Agent3 授信决策 (四维评分 + 红线)
  → 模拟放款
  → Agent4 在贷监控 (客户行为变化触发)
  → Agent5 合规扫描 (政策事件触发)
```

这是真正的"产品形态" · 不是 6 个孤岛页面。

---

## 2. 走歪表征 (Step 2 conflict scan 已发现)

### 2.1 产品形态层 (核心 · 走歪本质)

- **6 单页 showroom · 没有 RM workbench**: `web/src/app/today/` 不是工作台 · 是 dashboard · 6 Agent 各自跳转 · 无 cross-agent handoff
- **Agent1 look-alike pivot 没真实装**: features-inventory.md F-005 标 "NEVER CORRECTLY DELIVERED"
- **Agent6 → Agent3 handoff 数据流没串**: Agent3 workspace 不消费 Agent6 ReportJSON · 自跑独立打分

### 2.2 架构层

- **6 workspace 0 个真 4 gate**: `liveData` 字段全 repo 0 命中 (Codex Round 1 sub-agent 找到)
- **3 套 LLM caller 并行**: root `llm.LLMClient` (5 agent 用) + `shared/llm/` (Stage E.3 已建 · 0 agent 用) + `agent_report._build_llm_caller` (硬编 OpenAI · 第 4 套)
- **frontend SSE 客户端漂**: `_live.ts streamSse` 应唯一 · 但 ChannelWorkspace + CreditWorkspace + ReportWorkspace 各自手写 reader (打补丁版)
- **backend SSE done event 6 套**: 各 agent stage 名 / payload 字段不共形

### 2.3 命名 / 角色层

- **`compliance` vs `compli` dual-id 全栈分裂**: web AgentKey "compliance" vs RBAC "compli" · `web/src/lib/auth/agent-id.ts` 是补丁映射
- **CLAUDE.md §1 4 角色 vs §4 5th "策略经理" 文案漂**: backend `risk_manager` 是真 · "策略经理" 是文案漂
- **`/design` 在 §7 canon 但目录未建**

### 2.4 设计层

- **Letterpress legacy color 仍活**: `web/src/lib/agents.ts:46-47,49,73,86,113` 用 `--color-ink` `--color-brass` · 违 §7 红线
- **6 spec doc 都标 "workspace-state-protocol.md (待 A2 worker 产出)"**: 协议文件不存在 · 6 spec 全 stale

### 2.5 文档层

- **CLAUDE.md §3.1 写 "shared/ 没 llm_caller"**: 但 Stage E.3 (2026-04-28) 已落地 · §3.1 stale
- **decisions-log Q-040 / Q-041 active 决议未回写 root CLAUDE.md**: PM 改 MAX_ROWS · demo 弱密码 TODO · 等

---

## 3. 修正方向 (Phase A 验收硬线)

### 3.1 产品形态 (本质修正)

- **`/today` 改为真 RM workbench**: 整合"客户管线" + "今日待办" + "跨 agent 调用入口" · 而非 dashboard
- **6 agent 收为 workbench 内"能力 tile"**: `/archive` 不再是 portal · 是工作台内 secondary nav
- **Agent6 → Agent3 真 handoff data flow**: ReportJSON schema 定义 · Agent3 输入消费

### 3.2 架构层

- **workspace 4 gate 真实装** (Phase A worker A3 · pilot Channel): `started / selectedSession / liveData / selectedCandidate`
- **shared LLM caller 唯一化** (Phase A worker A2): `shared/llm_caller/` core + agent thin adapter · 6 agent 全迁
- **SSE envelope 后端共形** (Phase A worker A2): `shared/sse_envelope.py` event 名 + done payload 共形 · 6 agent 用
- **frontend `_live.ts` streamSse 唯一**: 6 workspace 全走

### 3.3 命名 / 角色

- **8 列 SSOT 词典** (Phase A worker A1): `docs/contracts/agent-naming-ssot.md`
- **`compli` 全栈统一** OR `compliance` 全栈统一 (PM 选一个)
- **CLAUDE.md §1 + §4 角色统一** ("策略经理"漂消除)

### 3.4 设计层

- **Letterpress 12 consumer 真迁** (Phase A worker A5)
- **4 themes 一致** (canvas / matcha / dusk / ink) · 删 globals.css legacy 段

### 3.5 文档层

- **指令 SSOT 树** (Phase A worker A1): root `CLAUDE.md` 工程行为 / `docs/contracts/*` 接口契约 / `shared/prompts/` LLM system message · 加 `docs/arch/instruction-source-of-truth.md` 优先级
- **active decision 回写** (本次 §14 已立规)

---

## 4. 反校准 (避免改歪到另一边)

- ❌ 不要把 6 Agent **业务**合并 · 只合并外壳 (envelope / state model / caller core)
- ❌ 不要为 RM workbench 一刀砍掉 `/archive/[agent]` 路由 · 是 workspace 重组 · 不是删页面
- ❌ 不要用 LLM 现场算财务比率 (CLAUDE.md §3.1 红线)
- ❌ 不要前端 inline 大坨 mock (CLAUDE.md 反 §3.5)
- ❌ 不要复活 `/channel` `/credit` 等顶层 legacy route
- ❌ 不要写关键词 / 正则黑名单兜底幻觉

---

## 5. 北极星检查清单

任何 Phase A worker 完工前必自查:

1. 这次改是否让 RM workbench 更集中 · 还是又造了 1 个 showroom?
2. 这次改是否让 6 Agent handoff 更流畅 · 还是制造了新孤岛?
3. 这次改是否唯一化了某种实现 · 还是又造了一种新版本?
4. 这次改是否守住了 §3.1 确定性 vs 概率性边界?
5. 这次改是否守住了 §3.5 反 5 原则 (mock 数据约束)?

5 个全 yes · 才算合格 reset commit。
