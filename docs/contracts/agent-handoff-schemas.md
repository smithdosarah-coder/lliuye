# 6 Agent Handoff Data Contract · v1.0

**版本**: v1.0
**发布日期**: 2026-04-29
**作者**: worker-A6 (Phase A · Week 2-3)
**适用范围**: 6 Agent 跨域数据流 / handoff 载荷 / export 契约共形
**主 CLI dispatch signal**: `PHASE-A-A6-DISPATCHED` (commit b19c139)
**phase A 验收硬线 #6** (`docs/reset/phase-a-charter.md` §1):
> 6 Agent handoff data contract · `docs/contracts/agent-handoff-schemas.md` 定义清楚 (不要求自动跑通 · 仅 schema 定)。

---

## 0. 为什么有这份契约 (north-star §1.4 reaffirm)

`docs/reset/north-star.md` §1.4 钉死的 6 Agent 闭环路径:

```
RM (客户经理)
  → Agent1 拓客 (look-alike) 找候选
  → Agent6 出尽调报告 (材料解析 → 字段抽取 → 段落生成 → QC)
  → Agent3 授信决策 (四维评分 + 红线)
  → 模拟放款
  → Agent4 在贷监控 (客户行为变化触发)
  → Agent5 合规扫描 (政策事件触发)
```

> 这是真正的"产品形态" · 不是 6 个孤岛页面。

Step 2 conflict scan (`docs/audit/conflict-register-v1.md`) Cat 0 验证 6 Agent 当前是 6 个 showroom · 没有 RM workbench · Agent1/Agent6/Agent3 之间真 dataflow 没串。本契约的目的是**先把 4 条主链路的 schema 钉死** · 让 Phase B 商业化推进 (`docs/reset/phase-b-charter.md`) 时有 ground truth 可引 · 而不是每个 worker 自己拍脑袋。

**本契约仅 spec · 不实装**: schema 定义 + sample fixture · 真实接代码是 Phase A worker-A3 (Channel pilot) + Phase A 子 workers (Credit/Alert/Compli/Riskctrl/Report adapter) 各自的工作。

---

## 0.1 范围声明

**本文档 spec 4 条主链路 + 1 个 export 共形契约**:

| # | 链路 | 触发方 | 消费方 | 节 |
|---|---|---|---|---|
| 1 | `Agent1.candidate_company → Agent6.upload_intent` | RM 在 Agent1 选候选 → 起报告 | Agent6 (报告生成入口) | §1 |
| 2 | `Agent6.report_json → Agent3.decision_input` | Agent6 报告生成完毕 | Agent3 (授信决策) | §2 |
| 3 | `Agent3.decision → Agent4.client_pool_signal` | Agent3 决策出 (含模拟放款) | Agent4 (在贷预警) | §3 |
| 4 | `Agent5.policy_event → Agent4 / Agent6` | Agent5 检出新政策违规 | Agent4 重扫 + Agent6 报告补充 | §4 |
| Cat 13 | export contract 共形 | 6 Agent 任意 | 客户/审贷员下载 | §5 |

**不在本文档范围**:

- ❌ `/today` RM workbench 重写 (PM 拍板推 Phase B-3 端到端 demo chain)
- ❌ Workspace 4 gate state 实装 (worker-A3 + 5 子 worker 干)
- ❌ shared LLM caller 接管 (worker-A2 干)
- ❌ Agent2 (riskctrl · DSL + 回测) handoff — Agent2 是策略经理面向的工具 · 不在 6 Agent 闭环路径中
- ❌ Agent5 巡检 / Agent4 单点查询 — 已在 north-star §1.3 钉死 Agent5 = 政策事件驱动 / Agent4 = 客户变化驱动
- ❌ 反向链 (Agent3 → Agent1 / Agent4 → Agent3 / etc.) — 反向流另开契约

---

## 0.2 命名 / 单位 / 类型 SSOT 引用

本契约**不重复定义**字段命名 / 单位 / 类型 / SSE event payload 结构 — 全部沿用:

- `docs/contracts/field-naming.md` v1.0 — 字段命名 / enum / ID 正则 / SSE payload
- `docs/contracts/agent-naming-ssot.md` (worker-A1 产出) — 6 agent canonical id 8 列表
- `docs/contracts/sse-envelope.md` (worker-A1) — SSE 事件信封
- `docs/contracts/workspace-state-protocol.md` (worker-A1 / worker-A2) — 4 gate state machine

**6 Agent canonical id (per PM 拍板 2026-04-29 · `docs/handoff/decisions-log.md`)**:

| canonical_id | 中文 | 业务子域 | 参考 |
|---|---|---|---|
| `channel` | 全渠道获客 (look-alike) | Agent1 | `agent_channel/` |
| `report` | 信贷报告助手 | Agent6 | `agent_report/` + `v16_*.py` |
| `credit` | 授信决策辅助 | Agent3 | `agent_credit/` |
| `alert` | 贷中风险预警 | Agent4 | `agent_alert/` |
| `compliance` | 合规巡检 (政策事件驱动) | Agent5 | `agent_compliance/` |
| `riskctrl` | 风控策略运营 (DSL + 回测) | Agent2 | `agent_riskctrl/` |

**重要**: PM 拍板 compliance vs compli 二选一 → 选 `compliance` (canonical id)。原代码中 `agent_compliance/` 路径名保留 · RBAC role / API mount 路径要在 worker-A1 SSOT 8 列里同步对齐。本契约引用统一用 `compliance`。

---

## 0.3 与现有 contract 的关系 (避免重写已 frozen 的契约)

| 现有 contract | 状态 | 本契约的处理 |
|---|---|---|
| `docs/contracts/channel_to_credit_handoff.md` v1.0 (2026-04-18) | Agent1 → **Agent3** 直跳 (绕过 Agent6) | **fast-path bypass · 违 north-star §1.4 闭环**。本契约链路 1 spec Agent1 → Agent6 主路径 · channel_to_credit 被定义为 fallback 场景 (RM 已有现成报告 / 跳过尽调直接走快批) · 见 §1.5 |
| `docs/contracts/enterprise_profile.md` v1.0 (2026-04-18) | Agent6 ReportJSON schema (frozen) | **直接 reference · 不重写**。本契约链路 2 在 §2 引用 ReportJSON schema · 补 Agent3.decision_input 消费契约 (哪些字段必读 / 哪些 Optional / 缺失降级) |
| `docs/contracts/field-naming.md` v1.0 | 字段命名 / enum SSOT | reference · 本契约所有字段名严格遵守 |
| `docs/contracts/live-fallback-banner-spec.md` v1.0 | live failed → banner | 本契约 §5 export contract 与之同源 · 共形约束 |
| `docs/contracts/workspace-state-protocol.md` | 4 gate state machine | reference · 本契约 fixture 产出符合 4 gate 命名 |
| `docs/contracts/empty-state-design-protocol.md` | mock dropdown / banner UI | reference · §5 banner UI 共形依据 |

---

## 0.4 schema 表述约定

每条链路按以下 5 段统一表述:

1. **触发与时序** — 谁在什么 UI 操作触发 / 是同步还是异步 / 失败回退到哪
2. **传输信封** — 是 HTTP POST / SSE event payload / disk JSON 文件落 `data/handoff/<chain>/`
3. **payload schema** — 表格形式列字段 (字段名 / 类型 / required/optional / 来源 / 说明)
4. **消费侧约束** — 接收方必读字段 / Optional 缺失降级策略 / 验证清单
5. **fixture 路径** — `data/mock/handoff/<chain>.json` · 一个真实形态样例

**类型记法** (per `field-naming.md`): Python 后端用 snake_case · TypeScript 前端 1:1 复用 (不做 camelCase 转换)。Optional 字段在表中标 `Optional[T]`。

---

## 0.5 schema_version + 演进规则

每条 handoff payload 顶层**必须**含 `schema_version: str`:

- v1.0: 本文档定义的所有字段 (2026-04-29)
- 破坏性变更 (字段删除 / 类型变更 / required 字段新增): 升 major (v2.0) · 主 CLI 在 `docs/review/contract-changes.md` 发公告 · 下游 3 工作日内评估
- 非破坏性追加 (新增 Optional 字段): 升 minor · 自由 · 下游可不响应

**4 链 fixture 内 `schema_version` 全部为 `"1.0"`**。

---

## 1. 链路 1 · Agent1.candidate_company → Agent6.upload_intent

**TBD · §1 在 Signal: `WORKER-A6-CHAIN-1-SPECCED` commit 中补充。**

## 2. 链路 2 · Agent6.report_json → Agent3.decision_input

**TBD · §2 在 Signal: `WORKER-A6-CHAIN-2-SPECCED` commit 中补充。**

## 3. 链路 3 · Agent3.decision → Agent4.client_pool_signal

**TBD · §3 在 Signal: `WORKER-A6-CHAIN-3-SPECCED` commit 中补充。**

## 4. 链路 4 · Agent5.policy_event → Agent4 / Agent6

**TBD · §4 在 Signal: `WORKER-A6-CHAIN-4-SPECCED` commit 中补充。**

## 5. Export Contract 共形 spec (Cat 13)

**TBD · §5 在 Signal: `WORKER-A6-EXPORT-CONTRACT-SPECCED` commit 中补充。**

---

## 6. Fixture index

每条链路 1 个真实形态 fixture · 落 `data/mock/handoff/`:

| 链路 | 文件 | 状态 |
|---|---|---|
| 1 | `data/mock/handoff/agent1-to-6.json` | TBD |
| 2 | `data/mock/handoff/agent6-to-3.json` | TBD |
| 3 | `data/mock/handoff/agent3-to-4.json` | TBD |
| 4 | `data/mock/handoff/agent5-to-4-6.json` | TBD |

Fixture 必须符合 §3.5 反结果导向 5 原则 (`CLAUDE.md` §3.5):

1. 盲测: PM 不预知 fixture 内坑
2. 难度分层: 简单 / 中等 / 困难混合
3. 真实来源锚定: 参考 A 股年报 / 央行模板 / 银保监公告真实形态
4. 脱敏再造: 不直接用真实存续企业数据
5. 环境边界: 给"内部稳态 context"不替 Agent 做"本该外搜的工作"

---

## 7. 维护与变更

- **维护人**: 主 CLI (本契约属 contract-5 — `docs/contracts/instruction-source-of-truth.md` SSOT 优先级见 worker-A1 v1.0)
- **下次审查**: 2026-05-29 (Phase B-3 端到端 demo chain 启动前必看)
- **下游 worker 必读**: A3 (Channel pilot · 链路 1 触发端) / 5 子 worker (Credit / Alert / Compli / Riskctrl / Report adapter · 链路 2/3/4 消费端)

---

**Author**: worker-A6 · 2026-04-29
**Phase A Week 2-3 · 与 A5 + A7 并行**
