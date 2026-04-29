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

**目的**: RM 在 Agent1 ("拓客") workspace 选中一个候选企业 → 点 "起尽调报告" → Agent6 接收 `upload_intent` 创建 report 容器 → 在 RM 端打开 "上传材料" UI · 这是 north-star §1.4 闭环路径的第 1 跳: `Agent1 拓客 → Agent6 出尽调报告`。

### 1.1 触发与时序

| # | 谁 | UI 动作 | 服务端 | 落地 |
|---|---|---|---|---|
| 1 | RM | 在 `/archive/channel` 候选清单点 "起尽调报告" button | — | `CandidateProfile` 已存在 (Agent1 上一步落 `data/handoff/channel/<session>/<profile_id>.json`) |
| 2 | frontend | `POST /api/report/upload_intent` (新 endpoint · spec 仅 · A4-report 子 worker 实装) | Agent6 接收 payload | — |
| 3 | Agent6 | 校验 payload → 创建 `report_id` + 初始化 v16 pipeline 容器 | 200 + `{report_id, upload_url}` | 写 `data/handoff/channel_to_report/<report_id>.json` (Agent6 端 archive) |
| 4 | frontend | 接 `report_id` → 切到 `/archive/report` workspace · 进入 `materials` 4 gate state · 触发 file picker | — | — |

**同步 / 异步**: HTTP 同步 (非 SSE) — 仅创容器 · 不跑 LLM 生成。生成走后续的 `/api/report/v16/fill` SSE。

**失败回退**:
- 4xx (校验失败): frontend 显 `live-fallback-banner-spec.md` §2 规则 1 banner · 不静默 fallback mock
- 5xx / network: 同上 + 显 `[重试]` button

### 1.2 传输信封

```http
POST /api/report/upload_intent HTTP/1.1
Content-Type: application/json
Cookie: <RM session cookie · 必带>

{
  "schema_version": "1.0",
  "intent_type": "candidate_to_report",
  "source_agent": "channel",
  "target_agent": "report",
  "session_id": "<UUID v4 · Agent1 channel session>",
  "candidate": { /* CandidateUploadIntent · §1.3 */ },
  "trigger_at": "2026-04-29T10:30:00Z",
  "rm_user_id": "<RM 工号 · ≤64 char>"
}
```

**ID 约定** (per `field-naming.md` §四):
- `session_id`: 严格 UUID v4 (Agent1 服务端 `/api/channel/run` 起的 channel session)
- `report_id` (响应): 不在请求里 · 由 Agent6 生成 · 格式 `report_<company_slug>_<unix_ts>` (现有 v16 pipeline 约定 · `agent_report/api.py` L360)

### 1.3 payload schema · `CandidateUploadIntent`

| 字段 | 类型 | required | 来源 | 说明 |
|---|---|---|---|---|
| `profile_id` | str (UUID v4) | ✓ | `CandidateProfile.profile_id` | Agent1 候选企业 ID · 用于回溯 channel session |
| `company_name` | str | ✓ | `CandidateProfile.enterprise_profile.company_name` | 工商注册全名 |
| `unified_credit_code` | Optional[str] | — | `CandidateProfile.uscc` | 18 位 USCC · 可空 (Agent1 mock / Tavily 来源可能未抓到) |
| `business_line` | enum | ✓ | `CandidateProfile.business_line` | `"corporate" \| "inclusive" \| "retail" \| "reserved"` (per `field-naming.md` §3.1) |
| **`match_score`** | int (0-100) | ✓ | `CandidateProfile.match_score` | **Cat 5 命名 SSOT · 钉死字段名** · 见 §1.4 |
| `signal_count` | Optional[int] | — | `CandidateProfile.signal_count` | Agent1 信号总条数 (RM 选 candidate 时的判断依据 · Agent6 不消费) |
| `signal_types` | Optional[list[str]] | — | `CandidateProfile.signal_types` | 去重排序信号类型 |
| `industry` | Optional[str] | — | `CandidateProfile.industry` | 国标行业 / Agent1 抓的行业 |
| `region` | Optional[str] | — | `CandidateProfile.region` | 经营地区 / 省份 |
| `recommended_products` | Optional[list[str]] | — | `CandidateProfile.recommended_products` | Agent1 产品推荐 (informational · Agent6 不消费 · Agent3 后链消费) |
| `data_sources` | Optional[list[str]] | — | `CandidateProfile.data_sources` | 来源标签 (e.g., `"内部 Mock 客户库"` / `"Tavily"`) |

**字段不消费规则**:
- Agent6 消费: `profile_id` / `company_name` / `unified_credit_code` / `business_line` / `industry` / `region` (用于初始化 report 容器 + KB 优先级)
- Agent6 **不**消费: `match_score` / `signal_count` / `signal_types` / `recommended_products` / `data_sources` (这些是 Agent1 内部判断 · 留给 Agent3 后链)
- `match_score` 仅作 metadata 存于 `data/handoff/channel_to_report/<report_id>.json` · 在最终 `report_json` 落 `report_json.metadata.upstream_match_score` (供 Agent3 在 §2 决策时回看 Agent1 信号强度)

### 1.4 命名 SSOT · `match_score` vs `similarity` 对齐 (Cat 5)

`docs/audit/sub-agent-step2-round1/data.md` §Cat 5 指出三方分裂:

| 面 | 字段名 | 类型 | 范围 | 来源 |
|---|---|---|---|---|
| backend Python | `match_score` | int | 0-100 | `agent_channel/candidate_profile.py:78` |
| frontend mock TS | `similarity` | number (float) | 0.0-1.0 | `web/src/lib/mock/agent-channel-sessions.ts:53,132,297+` |
| frontend ScoutCandidate type | `similarity` | number (float) | 0.0-1.0 | 同上 |

**统一方案** (本契约 v1.0 钉死):

1. **handoff payload 字段名 = `match_score` (int 0-100)** — 跨 Agent 边界一律用此
2. frontend cosmetic 显示可保留 `similarity` 0-1 表达 · 但**只在 UI 展示层** · 计算公式: `similarity = match_score / 100.0`
3. frontend mock fixture (`agent-channel-sessions.ts`) 在 unified platform pivot 后续清理时 **必须迁** 为 `match_score: int` 字段 · 由 worker-A3 (Channel pilot) 在 `WORKER-A3-CHANNEL-PILOT-DONE` 内同步处理 · 不属本契约 scope
4. CI lint (worker-A1 SSOT lint 已建): grep `\bsimilarity\s*:` 在 handoff JSON / `data/handoff/` / `data/mock/handoff/` 命中 → 报错

**为什么选 match_score 而非 similarity**: backend 真实计算 (`_signal_score_to_match` `agent_channel/candidate_profile.py:139` 的归一化逻辑) 落地是 int 0-100 · 是 source of truth · frontend `similarity 0-1 float` 是 cosmetic artifact (从早期 mock 留下的浮点风格) · 反向同步成本更低。

### 1.5 与已有 `channel_to_credit_handoff.md` v1.0 的关系

`docs/contracts/channel_to_credit_handoff.md` v1.0 (2026-04-18) 定义的是 **Agent1 → Agent3 直跳** (绕过 Agent6) · 这本身违 north-star §1.4 闭环路径 (Agent1 → Agent6 → Agent3) · 是产品形态走歪的产物。

**本契约 (v1.0) 的处理**:

| 场景 | 主路径 (本契约链路 1) | fast-path (channel_to_credit_handoff.md) |
|---|---|---|
| RM 给候选企业起新尽调 | ✓ Agent1 → Agent6 → Agent3 (闭环) | ✗ |
| RM 已有现成 ReportJSON · 复跑授信打分 | ✗ | ✓ Agent1 → Agent3 (跳过 Agent6) |
| RM 候选数据已含全部 Agent6 必需字段 (≥ M1 完整度) | ✗ | ⚠️ 仅 demo 场景 · 不推荐生产 |

`channel_to_credit_handoff.md` 在 Phase B 商业化推进期可能被 **deprecated** · 由本契约 §1 + §2 双跳替代 · 但当前 (2026-04-29) **保留** 作 Phase A 现状。Phase B-3 端到端 demo chain 启动前 · 主 CLI 决策是否 deprecate · 走 `docs/contracts/shared-change-protocol.md` RFC 流程。

### 1.6 消费侧约束 (Agent6)

Agent6 接 `POST /api/report/upload_intent` 必须:

1. ✓ 校验 `profile_id` 是合法 UUID v4 (regex per `field-naming.md` §四)
2. ✓ 校验 `company_name` 非空 (≥ 2 char)
3. ✓ 校验 `business_line` 在 4 enum 内 · 不在则 `VALIDATION_FAILED`
4. ✓ 检查 `data/handoff/channel/<session_id>/<profile_id>.json` 存在 (溯源 Agent1 上游) · 不存在则 `NOT_FOUND` 但**不**阻断 (allowlist: 直接来自 mock dropdown 的 demo session 可绕过)
5. ✓ 创建 `report_id` 并响应 `{schema_version: "1.0", report_id: "...", upload_url: "/archive/report?report_id=..."}`
6. ✓ 落 `data/handoff/channel_to_report/<report_id>.json` (含原 `CandidateUploadIntent` payload + `created_at` 时间戳 · 用于 Phase B-3 demo chain 复盘)
7. ❌ 不读 `match_score` / `signal_count` / `recommended_products` 用于报告生成 — 严防 Agent6 受 Agent1 启发式分污染

**降级**: 上述 4 (溯源检查) 失败 → log warning · 不阻断;1/2/3 失败 → `VALIDATION_FAILED` 400。

### 1.7 fixture · `data/mock/handoff/agent1-to-6.json`

见 §1.7 配套 fixture · 一个 "海钻智造科技 · 工业软件 SaaS" 真实形态样例 (脱敏再造 · 满足 §6 反结果导向 5 原则)。

## 2. 链路 2 · Agent6.report_json → Agent3.decision_input

**目的**: Agent6 v16 pipeline 跑完 (材料解析 → 字段抽取 → 段落生成 → QC 终审) 输出 ReportJSON · 作为 Agent3 授信决策的 input · 这是 north-star §1.4 闭环路径的第 2 跳: `Agent6 出尽调报告 → Agent3 授信决策`。

**核心 handoff** — Cat 0 audit (`docs/audit/sub-agent-step2-round1/production-shape.md`) 直指: "EmptyState 注释说'来自 Agent6 handoff'·但实际 onClick 直调独立 `/api/credit/decision` · 不消费 ReportJSON" — 本契约钉死 Agent3 必须真消费 ReportJSON · 不允许走旁路。

### 2.1 直接 reference: Agent6 ReportJSON schema = `enterprise_profile.md` v1.0

ReportJSON 的字段定义已由 `docs/contracts/enterprise_profile.md` v1.0 (2026-04-18) **frozen** · 本契约**不重写** · 直接 reference:

- 顶层结构: 21 字段 (2 必填 + 19 Optional) + 7 子结构 + 3 元数据
- 7 子结构: `FinancialAnchors` / `GuaranteeInfo` / `RelatedPartyInfo` / `ExistingCredit` / `CreditRequest` / `Chapters` / `AgentOutputs`
- 详见 `enterprise_profile.md` §一 ~ §六

**重要**: `enterprise_profile.md` §〇 已澄清 — ReportJSON 是嵌套 Python dict / JSON payload · **不等同于** `shared/enterprise_profile.py` 的 Pydantic 实例 (该 Pydantic 类是 Agent6 内部扁平画像 · 不参与跨 Agent handoff)。Agent3 / Agent1 / Agent5 消费时**禁止**用 `from shared.enterprise_profile import EnterpriseProfile` 反序列化。

### 2.2 触发与时序

| # | 谁 | UI 动作 | 服务端 | 落地 |
|---|---|---|---|---|
| 1 | Agent6 | v16 pipeline 跑完 (含 QC blocker 通过) | — | 写 `data/handoff/report_to_credit/<report_id>.json` (Agent6 端 archive · 含完整 ReportJSON) |
| 2 | RM (在 `/archive/report` workspace) | 看到 "尽调完成" status → 点 "送审授信" button | — | — |
| 3 | frontend | `POST /api/credit/decision` (现有 SSE endpoint · `agent_credit/api.py:269`) `body.report_json = <Agent6 ReportJSON>` | Agent3 接收 · 验 schema · 启 SSE | — |
| 4 | Agent3 | SSE 事件流: `profile_loaded` → `feature_extracting` → `feature_done` → `scoring` → `scoring_done` → `rule_checking` → `rule_done` → `case_retrieving` → `case_done` → `advising` → `advising_done` → `done` | — | 缓存 `decision_id` (TTL 30 min · `_DECISION_CACHE`) · 后续 §3 链路 3 消费 |

**同步 / 异步**: SSE 流式 (Agent3 现有 `POST /api/credit/decision` 已实装 · per `agent_credit/api.py`) — 完整跑 ~30-60 sec。

**失败回退**:
- 4xx (ReportJSON schema 不合法): `VALIDATION_FAILED` · frontend banner (per §5)
- 5xx / SSE 中断: frontend 显 banner + `[重试]` · 不静默 fallback mock
- ReportJSON 缺关键字段 (e.g., `financial_anchors.revenue_latest` 全 None): Agent3 降级 → SSE 事件流加 `event: warning` 提示 RM "材料不足 · 将以保守评分推进"

### 2.3 Agent3 消费契约 · `decision_input`

`decision_input` 是 Agent3 在 `agent_credit/api.py` `DecisionRequestV4` 接收的 payload · 字段清单:

| 字段 | 类型 | required | 来源 | 说明 |
|---|---|---|---|---|
| `schema_version` | str | ✓ | 顶层 metadata | 必为 `"1.0"` (向前兼容判断) |
| `stage_tab` | enum | ✓ | RM 在 frontend 选 | `"corporate" \| "small_business" \| "retail"` (Agent3 三板块 · 注意**与 `business_line` 不互通**) |
| `report_json` | dict | ✓ | Agent6 v16 pipeline 输出 | 全量 ReportJSON · 嵌套 schema 见 `enterprise_profile.md` §一 |
| `materials` | Optional[list[dict]] | — | Agent6 → Agent3 透传 | 客户提交材料元数据 · `[{material_id, type, parsed_at, evidence_count}]` |
| `preset_name` | Optional[str] | — | RM demo 模式 fallback | `report_json` 缺失时 fallback 到 `mock_data/{seg}_profiles/<preset_name>.json` |
| `appetite_config` | Optional[dict] | — | 风险偏好覆盖 | 当前 default `None` · Phase B 启用 |
| `provider` | Optional[str] | — | LLM 选择 | per `field-naming.md` §3.5 · 默认 `"deepseek"` |
| `mock` | bool | — | demo 路径 | default false · `true` → 跑 fixture SSE 不调 LLM |

### 2.4 Agent3 必读字段映射 (ReportJSON → 四维评分 / 红线)

Agent3 必读字段 — 任一缺失走 §2.5 降级:

#### 对公 / 小微 (stage_tab = corporate / small_business)

| 维度 | 必读 ReportJSON 字段路径 | 用途 |
|---|---|---|
| 经营财务 (`financial`) | `financial_anchors.revenue_latest` / `revenue_prev` / `net_profit_latest` / `total_assets` / `total_liabilities` / `operating_cash_flow` | 计算资产负债率 / 营收增速 / 现金流覆盖等 7 个比率 |
| 行业前景 (`industry`) | `industry` (顶层) + `chapters.chapter_2_operation` | LLM 概率性消费 (per §3.1 确定性 vs 概率性边界) |
| 经营管理 (`operational`) | `establishment_date` / `controller_name` / `controller_share_pct` / `chapters.chapter_2_operation` | 实控人稳定性 + 经营年限 + 主营业务集中度 |
| 担保条件 (`guarantee`) | `guarantee_info.type` / `collateral` / `collateral_value` / `guarantor` | 担保完整性校验 |
| 红线规则 (`red_lines`) | `existing_credit.overdue_history` / `related_party_info.related_party_revenue_pct` / `financial_anchors.*` | 30 条 (corporate) / 20 条 (small_business) 红线 |

#### 零售 / 对私 (stage_tab = retail)

| 维度 | 必读 ReportJSON 字段路径 | 用途 |
|---|---|---|
| 偿债能力 (`ability`) | (零售场景 ReportJSON shape 不同 · 见 §2.6) | 月还款比 / 负债率 |
| 还款意愿 (`willingness`) | `existing_credit.overdue_history` (复用对公字段) | 历史逾期 |
| 工作稳定 (`stability`) | (零售自定字段 · 详见 enterprise_profile.md 零售扩展) | 工作年限 / 单位性质 |
| 抵押 / 担保 (`collateral`) | `guarantee_info.collateral` / `collateral_value` | 同对公复用 |

### 2.5 缺失降级策略

| 场景 | Agent3 行为 | SSE 事件 |
|---|---|---|
| `financial_anchors.revenue_latest` 缺 | 评分 financial 维度 → 0 (而非编造) · risk_grade 自动降一档 | `event: warning, payload.field: "financial_anchors.revenue_latest", payload.action: "missing_zero"` |
| `guarantee_info.collateral` 缺 (零售/小微) | 红线 "无抵押" 触发 (severity: yellow) · 不阻断 | 同上 |
| `chapters.chapter_3_finance` 缺 | LLM 用 `financial_anchors.*` 自生段落 (per Agent3 v3.1 现有 fallback) | 同上 |
| ReportJSON 顶层 `schema_version` ≠ `"1.0"` | `VALIDATION_FAILED` 400 阻断 | — |
| `report_json` 与 `preset_name` 都缺 | `VALIDATION_FAILED` 400 阻断 | — |

**禁止**: Agent3 用 prompt LLM 现场算财务比率 (per `CLAUDE.md` §3.1 确定性 vs 概率性 · 这条是底线)。所有 `financial.*` 比率必须经 `financial_analyzer.py` 算 · LLM 仅消费结果。

### 2.6 零售场景 ReportJSON 扩展

零售场景 (`stage_tab = retail`) 当前 `enterprise_profile.md` schema 是按对公设计的 · 零售客户的 ReportJSON 需扩展字段 (e.g., `monthly_income_yuan` / `employer_name` / `work_years`) · 这部分**待 Phase B Agent6 v17 (零售扩展)** 定义 · 不在本契约 v1.0 范围。

当前 (Phase A) 的 retail 走 fallback: `report_json = None` + `preset_name = <retail_preset>` · 走 `mock_data/retail_profiles/` 现有 mock。Phase B-3 端到端 demo chain 启动前需补 retail ReportJSON spec。

### 2.7 fixture · `data/mock/handoff/agent6-to-3.json`

见 §6 fixture index · 一份 "杭州智云工业软件" 经 Agent6 v16 跑完后的 ReportJSON 真实形态样例 (与链路 1 fixture 同企业 · 串联 demo chain)。

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
