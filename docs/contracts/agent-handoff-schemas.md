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

**目的**: Agent3 授信决策出 (approved / approved_with_conditions) → 模拟放款 → 客户进入"在贷池" → Agent4 把客户纳入后续每次知识库驱动批量扫描的范围 · 这是 north-star §1.4 闭环路径的第 3 跳: `Agent3 授信决策 → 模拟放款 → Agent4 在贷监控`。

**核心边界 (north-star §1.3 reaffirm)**: Agent4 是**客户行为变化**驱动 (不是单点查询 / 也不是定期巡检) — 本契约定义"放款"作为客户进入 pool 的初始信号 · 后续 trigger 由 Agent4 自身规则引擎决定。

### 3.1 触发与时序

| # | 谁 | UI 动作 | 服务端 | 落地 |
|---|---|---|---|---|
| 1 | Agent3 | SSE 事件流走到 `advising_done` (per `agent_credit/api.py` `_mock_decision_events`) | — | 缓存 `decision_id` (TTL 30 min · `_DECISION_CACHE`) |
| 2 | RM | 在 `/archive/credit` workspace 看决策结果 → 点 "执行模拟放款" button (Phase A 是模拟 · Phase B 接真核心系统) | — | — |
| 3 | frontend | `POST /api/alert/client_pool/admit` (新 endpoint · spec 仅 · A4-alert 子 worker 实装) | Agent4 接收 payload | — |
| 4 | Agent4 | 把客户写入 `data/handoff/credit_to_alert/<client_id>.json` + 加入 in-memory client pool | 200 + `{client_id, pool_position, next_scan_at}` | — |
| 5 | Agent4 | 后续每次 `POST /api/alert/scan` 跑批 (RM 在 `/archive/alert` 触发 / Phase B 由 cron / event) 时 · 客户被纳入扫描范围 | SSE `hitlist` event 含该 client_id | 持久化 `data/handoff/alert/<session_id>/hitlist.json` |

**同步 / 异步**: `POST /api/alert/client_pool/admit` HTTP 同步 — 仅入池 · 不跑扫描。后续 scan 是另一条流 (`POST /api/alert/scan` SSE)。

**失败回退**:
- 4xx: frontend banner 显失败原因 + `[重试]`
- 客户已在 pool (重复入池): 200 idempotent + `{warning: "already_in_pool"}`

### 3.2 传输信封

```http
POST /api/alert/client_pool/admit HTTP/1.1
Content-Type: application/json
Cookie: <RM session cookie>

{
  "schema_version": "1.0",
  "signal_type": "credit_approved_admit",
  "source_agent": "credit",
  "target_agent": "alert",
  "decision": { /* DecisionSignal · §3.3 */ },
  "trigger_at": "2026-04-29T13:45:00Z",
  "rm_user_id": "<RM 工号>"
}
```

### 3.3 payload schema · `DecisionSignal`

| 字段 | 类型 | required | 来源 | 说明 |
|---|---|---|---|---|
| `decision_id` | str | ✓ | Agent3 `_DECISION_CACHE` key (`"dec_" + uuid hex12`) | 决策缓存 ID · 用于 Agent4 回查 / 复跑 |
| `client_id` | str (UUID v4) | ✓ | 服务端生成 (Agent3 模拟放款时铸) | Agent4 后续以此追踪 · 与 channel `profile_id` 不同 (放款后客户身份升级) |
| `profile_id` | str (UUID v4) | ✓ | 链路 2 `report_json.profile_id` 透传 | 溯源 Agent6 报告 |
| `company_name` | str | ✓ | 链路 2 `report_json.company_name` | |
| `unified_credit_code` | Optional[str] | — | 链路 2 `report_json.unified_credit_code` | |
| `business_line` | enum | ✓ | 链路 2 `report_json.business_line` | per `field-naming.md` §3.1 |
| `stage_tab` | enum | ✓ | Agent3 `decision_input.stage_tab` | `"corporate" \| "small_business" \| "retail"` |
| **`decision_verdict`** | enum | ✓ | Agent3 advising_done | per `field-naming.md` §3.4 · 见 §3.4 命名钉死 |
| **`risk_grade`** | str | ✓ | Agent3 advising_done payload | 见 §3.5 grade 命名 |
| `composite_score` | int / float | ✓ | Agent3 advising_done payload | 0-100 (corporate/small_business) / 0-850 (retail) |
| `score_max` | int | ✓ | Agent3 (`100` for corp/sb · `850` for retail) | 与 composite_score 配套 · 用于 Agent4 范围归一化 |
| `approved_amount_yuan` | int | ✓ | Agent3 advising_done · **单位元** (per `field-naming.md` §2.2 钉死) | Agent3 内部 `approved_amount: 万元` 必转元 |
| `approved_term_months` | Optional[int] | — | Agent3 advising_done | |
| `interest_rate` | Optional[float] | — | Agent3 advising_done | 0-1 浮点 (e.g., 0.065) |
| `triggered_red_lines` | list[dict] | — | Agent3 rule_done payload | 见 §3.6 红线信号传递 |
| `conditions` | Optional[list[str]] | — | Agent3 advising_done payload | 批准条件 (有条件批准 / 待复核时必填) |
| `disbursed_at` | str (ISO 8601) | ✓ | 模拟放款时间戳 | Phase A 是模拟 · Phase B 由真核心系统盖戳 |
| `monitoring_config` | Optional[dict] | — | RM 可定制 / 默认按 business_line | `{frequency_days: 30, alert_threshold: "yellow"}` |

### 3.4 命名 SSOT · `decision_verdict` 钉死 (中英文映射)

`field-naming.md` v1.0 §3.4 钉死 `decision_verdict` enum 为**英文**:

```
"approved" | "approved_with_conditions" | "rejected" | "pending_review" | "insufficient_info"
```

`agent_credit/api.py` 当前实装返回**中文** ("建议批准" / "有条件批准" / "建议拒绝" / "建议人工复核") — 这是 spec vs impl 漂。

**本契约 v1.0 钉死**: handoff payload 的 `decision_verdict` 字段**必须**是英文 enum · Agent3 在 SSE `advising_done` 触发模拟放款 → `client_pool/admit` 时**做映射**:

| Agent3 中文 | handoff `decision_verdict` |
|---|---|
| 建议批准 | `approved` |
| 有条件批准 | `approved_with_conditions` |
| 建议拒绝 | `rejected` (注: `rejected` 不入 client pool · 链路 3 不触发) |
| 建议人工复核 | `pending_review` (Phase A 不入 pool · 待人审决议) |
| 建议人工复核 (材料严重不足) | `insufficient_info` (Phase A 不入 pool) |

**入池条件**: 仅 `approved` / `approved_with_conditions` 触发链路 3 · 其他不入。这是 Phase A 简化 · Phase B 商业化推进 (`docs/reset/phase-b-charter.md`) 时可能扩 (e.g., `pending_review` 也入 watch-only pool)。

`agent_credit/api.py` 修复责任**不在本契约 scope** · 由 Phase A worker-A4-credit (5 子 worker 之一) 在 `WORKER-A4-CREDIT-DONE` 内同步对齐。

### 3.5 命名 SSOT · `risk_grade` 三命名漂 (Cat 5)

`docs/audit/sub-agent-step2-round1/data.md` §Cat 5 指出 alert agent 内部 `grade` 三命名漂:

| 面 | 字段名 | 取值 |
|---|---|---|
| frontend mock | `tier` | `"red" \| "yellow" \| "green"` (信号灯) |
| 后端 export | `risk_level` | `"high" \| "medium" \| "low"` |
| Agent3 runtime | `risk_grade` | 字母 `"A" \| "B" \| "C" \| "D"` (corp/sb) / 中文 `"优" \| "中优" \| "良好" \| "边界" \| "拒"` (retail) |

**handoff payload 钉死** (本契约 v1.0):

- `decision.risk_grade` (本字段名 · 复用 Agent3 字段) — 字母制 / 中文制按 stage_tab 区分:
  - corporate / small_business: `"A" | "B" | "C" | "D"` (Agent3 现有取值不变)
  - retail: `"优" | "中优" | "良好" | "边界" | "拒"` (Agent3 现有取值不变)
- Agent4 接收后**自行**映射到自己的 hitlist `tier` 字段 (red/yellow/green) · 映射规则见下表 · 不污染 Agent3 字段:

| stage_tab | risk_grade | Agent4 tier |
|---|---|---|
| corporate / small_business | `"A"` | `"green"` |
| corporate / small_business | `"B"` | `"green"` (默认) · 触发红线 ≥ 1 → `"yellow"` |
| corporate / small_business | `"C"` | `"yellow"` |
| corporate / small_business | `"D"` | (不入 pool) |
| retail | `"优" / "中优"` | `"green"` |
| retail | `"良好"` | `"green"` (默认) · 触发红线 ≥ 1 → `"yellow"` |
| retail | `"边界"` | `"yellow"` |
| retail | `"拒"` | (不入 pool) |

`severity` 字段在本链路**不出现**于 handoff payload — `severity` 是 §1 `field-naming.md` §3.3 在 SSE event payload 内的字段 (red/yellow/green 信号灯) · 与 `risk_grade` 不混。

### 3.6 红线信号传递

`triggered_red_lines` 是**摘要**传递 (不传完整规则元数据) · 字段:

```typescript
type TriggeredRedLine = {
  rule_id: string;          // Agent3 内部规则 ID (e.g., "corp_rl_023")
  rule_name: string;        // 中文规则名
  severity: "red" | "yellow" | "green";  // per field-naming.md §3.3
  is_hard: boolean;         // hard 阻断 / soft 软警告
  actual_value: number | string;  // 实际触发值
  threshold: number | string;     // 阈值
  can_waive: boolean;       // 可豁免否
  waiver_conditions?: string[];   // 豁免条件 (有条件批准时填)
};
```

Agent4 消费规则:
- ✓ 把 `triggered_red_lines` 写入 client pool 入池记录 · 后续监控规则匹配时优先关注
- ✓ `severity == "red" && is_hard == true` 但 `decision_verdict == "approved_with_conditions"` 时 → 入池 tier 自动 = `"yellow"` (覆盖 §3.5 默认映射)
- ❌ 不在 Agent4 端重新评判红线是否合理 (那是 Agent3 的职责)

### 3.7 fixture · `data/mock/handoff/agent3-to-4.json`

见 §6 fixture index · 一份 "杭州智云工业软件" 经 Agent3 决策 (有条件批准 · risk_grade B · 1 条 yellow 红线) 后给 Agent4 的入池信号 · 与链路 1/2 fixture 同企业。

## 4. 链路 4 · Agent5.policy_event → Agent4 / Agent6

**目的**: Agent5 检测到新政策违规事件 (政策事件驱动 · 非定期巡检) → 双路扇出 · (a) 通知 Agent4 对在贷池中受影响客户做重扫 · (b) 通知 Agent6 在该客户后续报告中追加合规章节 · 这是 north-star §1.4 闭环路径的第 4 跳: `Agent5 合规扫描 (政策事件触发) → Agent4 重扫 + Agent6 报告补充`。

**核心边界 (north-star §1.3 reaffirm)**: Agent5 是**政策事件驱动** (新政策发布 / 监管处罚出 / 行业自查通报) — 不是定期巡检。

**当前 repo 状态 (audit Cat 0)**: Agent5 → Agent4 / Agent6 当前**无直接 API** · 本契约定义的是 spec · A4-alert / A4-report / A4-compli 子 worker 实装时按本 spec 接代码。

### 4.1 触发与时序

链路 4 是 **fan-out** (1 → 2 接收方) · 时序:

```
Agent5 检出政策事件
    │
    ├──→ POST /api/alert/policy_event (Agent4 接收)  · 重扫触发
    │       └─ Agent4 拉受影响 client 子集 → 入 `/api/alert/scan` 重跑 → 更新 hitlist
    │
    └──→ POST /api/report/policy_event (Agent6 接收)  · 报告补充触发
            └─ Agent6 在受影响 report_id 列表的下次 v16 pipeline 中 inject 合规章节
```

| # | 谁 | 动作 | 服务端 | 落地 |
|---|---|---|---|---|
| 1 | Agent5 | `POST /api/compliance/policy_scan` SSE 跑完 (4 阶段 · 当前已实装) | 持久化 `data/compliance/sessions/<scan_id>.json` | — |
| 2 | Agent5 后台 | scan 完毕 + 检出 `events` (违规事件) → 自动 fan-out 两个 webhook | — | — |
| 2a | Agent5 → Agent4 | `POST /api/alert/policy_event` (新 endpoint · spec 仅 · A4-alert 子 worker 实装) | Agent4 接收 + 自动启 scan 重跑 | 落 `data/handoff/compliance_to_alert/<event_id>.json` |
| 2b | Agent5 → Agent6 | `POST /api/report/policy_event` (新 endpoint · spec 仅 · A4-report 子 worker 实装) | Agent6 接收 + 标记受影响 report_ids | 落 `data/handoff/compliance_to_report/<event_id>.json` |
| 3 | RM | (异步 · 可能数小时后) 在 `/archive/alert` 看到红标新事件 + 在 `/archive/report` 看到 "合规事件待处理" 卡片 | — | — |

**同步 / 异步**: 两个 fan-out POST **异步** — Agent5 不等 Agent4/Agent6 响应 · 仅 retry 3 次失败后写 `data/handoff/compliance_unreachable/` deadletter。

**RM 触发 vs 自动触发**: Phase A 实装时 fan-out 由 Agent5 后台自动 — RM 不感知 (per north-star §1.3 "政策事件驱动" 的 spirit)。Phase B-3 demo 时可让 RM 在 `/archive/compliance` 手动 ack + dispatch (UI 见 dispatcher 看板)。

**失败回退**:
- Agent4 / Agent6 任一不可达: Agent5 retry 3 次 (exponential backoff 1s / 5s / 30s) · 最终失败写 deadletter · UI 在 `/today` 显警告卡 (Phase B-3)
- payload 校验失败: 5xx · 同上 deadletter

### 4.2 传输信封 (双 endpoint 同 payload schema)

```http
POST /api/alert/policy_event HTTP/1.1     ← Agent4 端
POST /api/report/policy_event HTTP/1.1    ← Agent6 端
Content-Type: application/json
X-Source-Agent: compliance
X-Idempotency-Key: <event_id · 服务端 dedup>

{
  "schema_version": "1.0",
  "signal_type": "policy_event_fanout",
  "source_agent": "compliance",
  "target_agent": "alert" | "report",   /* 视 endpoint 而定 · payload 同 */
  "event": { /* PolicyEvent · §4.3 */ },
  "trigger_at": "2026-04-29T15:00:00Z"
}
```

**幂等性**: `X-Idempotency-Key` 使用 `event.event_id` · Agent4 / Agent6 端 dedup (24h 窗口) · 防 retry 重复入。

### 4.3 payload schema · `PolicyEvent`

| 字段 | 类型 | required | 来源 | 说明 |
|---|---|---|---|---|
| `event_id` | str (UUID v4) | ✓ | Agent5 服务端生成 | 幂等键 / 跨 Agent 追踪 |
| `scan_id` | str | ✓ | Agent5 `/api/compliance/policy_scan` 持久化 ID | 溯源 Agent5 完整产物 |
| `policy_meta` | dict | ✓ | Agent5 `policy_meta` 透传 | `{title, source_url, issuing_body, issued_at, fetched_at}` |
| `policy_category` | enum | ✓ | Agent5 抽规则后归类 | `"prudential" \| "consumer_protection" \| "anti_money_laundering" \| "credit_risk" \| "data_security" \| "industry_specific" \| "other"` |
| `severity` | enum | ✓ | per `field-naming.md` §3.3 | `"red" \| "yellow" \| "green"` |
| `affected_business_lines` | list[enum] | ✓ | Agent5 矩阵比对结果 | 子集: `business_line` 4 enum (per §3.1) |
| `affected_industries` | Optional[list[str]] | — | Agent5 行业关键词命中 | 国标行业 (e.g., `"批发零售"` / `"工业软件"`) · null 表示全行业 |
| `affected_regions` | Optional[list[str]] | — | Agent5 地域关键词命中 | 省份 (e.g., `["浙江", "江苏"]`) · null 表示全国 |
| `triggered_rules` | list[dict] | ✓ | Agent5 抽规则结果 | 见 §4.4 PolicyRule schema |
| `violation_events` | Optional[list[dict]] | — | Agent5 矩阵比对命中事件 (Agent4 主用) | 见 §4.5 ViolationEvent schema |
| `recommended_actions` | list[dict] | ✓ | Agent5 修订意见生成 | `[{action_type: "amend"|"supplement"|"strengthen", target_doc, content, severity}]` |
| `affected_client_ids` | Optional[list[str]] | — | Agent4 端必填 (Agent6 端可空) | Agent5 直接给受影响 client_id 子集 · 为空时 Agent4 自行用 affected_business_lines/industries 筛 pool |
| `affected_report_ids` | Optional[list[str]] | — | Agent6 端必填 (Agent4 端可空) | Agent5 直接给受影响 report_id 子集 · 为空时 Agent6 自行用 affected_business_lines 筛 |
| `effective_at` | str (ISO 8601) | ✓ | 政策生效日期 | Agent4 / Agent6 据此排序优先级 |

### 4.4 PolicyRule schema (triggered_rules 元素)

| 字段 | 类型 | required | 说明 |
|---|---|---|---|
| `rule_id` | str | ✓ | Agent5 内部规则 ID (e.g., `"POL-PBC-2026-04-027"`) |
| `article` | str | ✓ | 政策原文条款 (verbatim · 含原条款编号) |
| `category` | str | ✓ | per §4.3 `policy_category` enum |
| `condition` | str | ✓ | 触发条件 (Agent5 LLM 抽出的中文表述) |
| `threshold` | dict | ✓ | 量化阈值 (e.g., `{"min_capital_yuan": 50000000}`) · 无量化则 `{}` |
| `severity_hint` | enum | ✓ | per `field-naming.md` §3.3 (`"red" \| "yellow" \| "green"`) |

(注: agent_compliance/api.py 现有字段名 `severity_hint` 而非 `severity` — 这是 Agent5 内部规则 metadata 字段 · 与 §4.3 的 event-level `severity` 不同 · 本契约保留 · 不强行统一)

### 4.5 ViolationEvent schema (violation_events 元素 · Agent4 主消费)

| 字段 | 类型 | required | 说明 |
|---|---|---|---|
| `event_inner_id` | str | ✓ | 单次违规事件 ID (Agent5 mat_check 生成) |
| `client_id` | Optional[str] | — | Agent4 client pool 的 client_id · 命中时填 |
| `report_id` | Optional[str] | — | Agent6 report 的 report_id · 命中时填 |
| `rule_id` | str | ✓ | 触发的 PolicyRule.rule_id |
| `evidence_excerpt` | str | ✓ | 业务文档原文摘录 (≤ 500 char) |
| `evidence_source` | str | ✓ | 来源文档名 |
| `severity` | enum | ✓ | per `field-naming.md` §3.3 |
| `confidence` | float | ✓ | 0-1 · Agent5 LLM 置信度 |

### 4.6 双消费方约束

#### Agent4 (`/api/alert/policy_event`) 消费

1. ✓ 解析 `affected_client_ids`:
   - 不为 null → 仅扫这些 client (精准模式)
   - 为 null → 用 `affected_business_lines` + `affected_industries` + `affected_regions` 筛 pool 产生候选 client list
2. ✓ 把候选 client list 入 `/api/alert/scan` reuse 现有 SSE flow · `scenario_key = f"policy_event_{event_id}"`
3. ✓ 将 `triggered_rules` 注入 scan rule context · 让规则引擎能匹配新政策条款
4. ✓ scan 跑完后写 `data/handoff/compliance_to_alert/<event_id>.json` 含 `{event_id, scan_session_id, hit_count, processed_at}`
5. ❌ 不做政策合规判定 (那是 Agent5 的职责) · Agent4 只做 "客户行为是否触发新规则" 的扫描

#### Agent6 (`/api/report/policy_event`) 消费

1. ✓ 解析 `affected_report_ids`:
   - 不为 null → 在这些 report 上标记 "合规章节待补"
   - 为 null → 用 `affected_business_lines` 筛 (Agent6 不维护 industry / region 索引 · 所以前者不用)
2. ✓ 标记后**不**自动重跑 v16 pipeline (会消耗大量 LLM 资源) — 仅在 RM 下次打开该 report 时显 "合规事件 1 条待补" 提示 + 提供 "追加合规章节" button
3. ✓ RM 点 button 触发 v16 pipeline 局部重跑 (仅 chapter 5 合规章节 · 现有 v16 不含 ch5 · 这是 v17 扩展 · Phase B-3 启动)
4. ✓ 写 `data/handoff/compliance_to_report/<event_id>.json` 含 `{event_id, marked_report_ids, marked_at}`
5. ❌ 不在 ReportJSON 顶层强加 `policy_events` 字段 (会破坏 §2 enterprise_profile.md frozen schema) · 用 `agent_outputs.compliance_appendix` 子结构承载 (Phase B v17 扩展)

### 4.7 fixture · `data/mock/handoff/agent5-to-4-6.json`

见 §6 fixture index · 一份 "应收账款融资风控指引" 政策事件触发的 fan-out 样例 · `affected_client_ids` 含链路 3 的 `0a1b9c4d-...` (智云工业软件 client_id) · `affected_report_ids` 含链路 2 的 `report_zhiyun_industrial_1745922000` · 端到端串联。

## 5. Export Contract 共形 spec (Cat 13)

**目的**: 6 Agent 任意 workspace 都要给 RM 提供 "导出" 能力 (本地下载 docx / xlsx / pdf 给客户经理后续邮件 / 打印 / 留档) · 当前 6 Agent 各自实装 endpoint / 字段 / button wire / fallback banner 严重不共形 (audit Cat 13 5 entries) — 本节钉死共形规范。

**audit 引用**: `docs/audit/sub-agent-step2-round1/production-shape.md` Cat 13 verdict: "6 Agent 各自只做了 1-2 种格式 · 字段 / 落盘命名 / button wire 三方分裂 · fallback banner 4 个 agent 缺"。

### 5.1 当前 repo 状态盘点 (2026-04-29)

| Agent | docx | xlsx | pdf | 备注 |
|---|---|---|---|---|
| Agent1 (channel) | ✓ `POST /api/channel/export_docx` | ✓ `POST /api/channel/export_xlsx` | ✗ | docx 候选线索报告 · xlsx 候选清单 |
| Agent6 (report) | ✓ `POST /api/report/export_docx` | ✗ | ✗ | 报告主输出格式是 docx |
| Agent3 (credit) | ✓ `POST /api/credit/export_docx` | ✗ | ✗ | 决策建议书 |
| Agent4 (alert) | ✓ `POST /api/alert/export_docx` | ✗ | ✗ | 命中清单 |
| Agent5 (compliance) | ✓ `POST /api/compliance/export_docx` | ✗ | ✗ | 修订意见书 (改/补/强) |
| Agent2 (riskctrl) | ✗ | ✗ | ✗ | 当前**无任何 export endpoint** · 应至少补 docx (DSL + 回测报告) |

**漂的表现** (Cat 13):

1. **format 不齐**: 6 agent 仅 1 个 (channel) 有 xlsx · 0 个有 pdf · 1 个 (riskctrl) 完全缺
2. **field 命名漂**: channel `unified_social_credit_code` 表头 vs report / credit / compliance 内部用 `unified_credit_code` (Cat 5 命名漂的具体表现之一 · 跨 agent 一致性需钉)
3. **button wire 漂**: frontend 部分 workspace export button 是 dead link (`live-fallback-banner-spec.md` §3 规则 3 已点出)
4. **fallback banner 缺**: 部分 workspace export 失败时静默 fallback 到本地 mock · 无 banner (违 `live-fallback-banner-spec.md` §2 规则 1)
5. **filename 命名漂**: channel `agent1_candidates_<session>.xlsx` vs report `<report_id>_<company>_<ts>.docx` 命名风格不一

### 5.2 共形 endpoint 矩阵 (本契约 v1.0 钉死)

每个 Agent 必须实装以下 endpoint 子集 — `必` 表示 Phase A 验收硬线 · `应` 表示 Phase B-3 demo chain 启动前补 · `可` 表示按业务场景判断可选:

| Agent | docx | xlsx | pdf | 内容 |
|---|---|---|---|---|
| Agent1 channel | 必 | 必 | 应 | docx: 候选线索完整报告 · xlsx: 候选清单 (现状已对) · pdf: 简版 1 页摘要 |
| Agent6 report | 必 | 应 | 应 | docx: 完整尽调报告 (现状已对) · xlsx: ReportJSON 结构化导出 (字段 → 列) · pdf: 高保真打印版 |
| Agent3 credit | 必 | 应 | 应 | docx: 决策建议书 (现状已对) · xlsx: 红线触发清单 · pdf: 给审贷会的简版 |
| Agent4 alert | 必 | 必 | 应 | docx: 命中清单 + 处置建议 (现状已对) · xlsx: 在贷池全量监控明细 · pdf: 简版 |
| Agent5 compliance | 必 | 应 | 应 | docx: 修订意见书 改/补/强 (现状已对) · xlsx: N×M 矩阵全量比对结果 · pdf: 给合规官的简版 |
| Agent2 riskctrl | 必 | 应 | 可 | docx: DSL + 回测报告 (**当前缺** · 必补) · xlsx: 回测明细数据 · pdf: 可选 |

### 5.3 共形 endpoint 命名 + 路径 + 输入

**endpoint 路径模板**:

```
POST /api/<agent_id>/export_<format>
```

`<agent_id>` per §0.2 SSOT (channel / report / credit / alert / compliance / riskctrl) · `<format>` ∈ {`docx`, `xlsx`, `pdf`}。

**输入信封 (统一)**:

```http
POST /api/<agent_id>/export_<format> HTTP/1.1
Content-Type: application/json
Cookie: <RM session cookie · 必带>

{
  "schema_version": "1.0",
  "session_id": "<UUID v4 · agent 内部 session>",
  "filters": { /* agent-specific · 见 §5.5 */ },
  "options": {
    "include_evidence": true,        /* 是否含证据链段落 · default true */
    "include_metadata": true,        /* 是否含 _meta · default true */
    "watermark": "训练演示数据"        /* mock 路径强制水印 · 真路径可空 */
  }
}
```

**响应**: HTTP 200 + `Content-Type: application/<format>` + 二进制 stream (per `agent_*/api.py` 现有 export 端点 pattern · 不变)。

**响应 header (统一)**:

```http
HTTP/1.1 200 OK
Content-Type: application/<vnd-mime>
Content-Disposition: attachment; filename="<filename>"
X-Export-Source: <"live" | "mock">     ← 必带 · frontend banner 据此判
X-Export-Schema-Version: 1.0
X-Export-Generated-At: 2026-04-29T15:30:00Z
```

**MIME type 约定**:
- docx: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- xlsx: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- pdf: `application/pdf`

### 5.4 filename 命名共形

```
<agent_id>_<artifact_kind>_<scope_id>_<ts>.<format>
```

| 部分 | 取值 |
|---|---|
| `agent_id` | per §0.2 SSOT (`channel` / `report` / `credit` / etc.) |
| `artifact_kind` | per §5.2 (`candidates` / `report` / `decision` / `hitlist` / `revision` / `dsl_backtest`) |
| `scope_id` | session_id 短前缀 (前 8 位 UUID) 或 report_id 等 · 不含特殊字符 |
| `ts` | Unix 时间戳 (秒) |

**示例**:

- `channel_candidates_7f4c7a2d_1745928000.xlsx` (链路 1 fixture session 的候选清单)
- `report_zhiyun_industrial_1745922000.docx` (Agent6 报告 · 注: 已有 v16 命名 · 不强行改 · 保留兼容)
- `credit_decision_dec_8a3f7b2c_1745928922.docx` (链路 3 fixture decision_id)
- `alert_hitlist_evt_pol_2026_04_29_1745930000.xlsx` (链路 4 fixture event 触发的扫描)
- `compliance_revision_scan_compli_20260429_1430_8e7c.docx` (链路 4 fixture scan_id)
- `riskctrl_dsl_backtest_<rule_set_id>_<ts>.docx` (Agent2 待补)

### 5.5 filters 字段 (agent-specific)

| Agent | filters schema |
|---|---|
| channel | `{candidate_ids?: string[], business_line?: enum, min_match_score?: int}` |
| report | `{report_id: string, sections?: ("background" \| "operation" \| "finance" \| "conclusion")[]}` |
| credit | `{decision_id: string, include_rejected_rules?: boolean}` |
| alert | `{session_id: string, tier?: ("red" \| "yellow" \| "green"), client_ids?: string[]}` |
| compliance | `{scan_id: string, action_types?: ("amend" \| "supplement" \| "strengthen")[]}` |
| riskctrl | `{rule_set_id: string, include_charts?: boolean}` |

### 5.6 button wire + fallback banner 一致性 (Cat 13 + live-fallback-banner-spec.md)

每个 workspace export button 必须满足以下 4 点 (per `docs/contracts/live-fallback-banner-spec.md` §2 + §3):

1. **button wire 真触发**: `onClick` → `POST /api/<agent>/export_<format>` · **禁止** placeholder UI
2. **failed → banner**: 4xx / 5xx / network → `live-fallback-banner-spec.md` §2 规则 1 banner: `⚠️ 后端 /api/<agent>/export_<format> 调用失败 (<status>) · 当前显 fallback 演示数据 · [重试]`
3. **mock 路径显式 banner**: 当请求来自 mock dropdown / `mock=true` 时 · 服务端响应 header `X-Export-Source: mock` · frontend 据此显示 banner: `示例数据 (training mode) · 切真实输入 → [按钮]`
4. **filename mock 区分**: mock 路径下载文件 filename 前缀加 `mock_` (e.g., `mock_channel_candidates_<ts>.xlsx`) · 防 RM 把 mock 文件误用作真实材料

### 5.7 字段共形钉死 (跨 agent export 字段名)

跨 Agent 共有字段必须用统一名称 (per `field-naming.md` v1.0):

| 概念 | 统一字段名 | 现状漂 |
|---|---|---|
| 统一社会信用代码 | `unified_credit_code` | channel xlsx 表头 `unified_social_credit_code` ⚠️ 必修 |
| 企业名 | `company_name` | channel xlsx `enterprise_name` ⚠️ 必修 |
| 业务条线 | `business_line` (per §3.1) | 一致 ✓ |
| 金额单位 | `amount_yuan` (元) / `amount_wan` (万元) 二选一带后缀 (per §2.2) | 各 agent 现状混用 ⚠️ 必修 |
| 决策动词 | `decision_verdict` (英文 enum) | 见 §3.4 钉死 |
| 严重等级 | `severity` (red/yellow/green) | 一致 ✓ |
| ID | `<resource>_id` 单字段 (e.g., `report_id` / `decision_id` / `scan_id`) | 一致 ✓ |

`field-naming.md` v1.0 是 SSOT · 任何冲突回到 SSOT 解决 · 不在本契约重定义。

### 5.8 实装责任分配

本节定义 spec · 实装由 Phase A 5 子 worker (A4-credit / A4-alert / A4-compli / A4-riskctrl / A4-report) + worker-A3 (channel pilot 已含 export) 各自完成:

| Worker | 责任 | DONE signal |
|---|---|---|
| worker-A3 (channel pilot) | channel 现有 docx + xlsx 字段 SSOT 修齐 (`enterprise_name` → `company_name` / `unified_social_credit_code` → `unified_credit_code`) + button wire + banner | `WORKER-A3-CHANNEL-PILOT-DONE` |
| worker-A4-report | report 补 xlsx + pdf | `WORKER-A4-REPORT-DONE` |
| worker-A4-credit | credit 补 xlsx + pdf | `WORKER-A4-CREDIT-DONE` |
| worker-A4-alert | alert 补 xlsx + pdf | `WORKER-A4-ALERT-DONE` |
| worker-A4-compli | compliance 补 xlsx + pdf | `WORKER-A4-COMPLI-DONE` |
| worker-A4-riskctrl | riskctrl 补 docx + xlsx (从零) | `WORKER-A4-RISKCTRL-DONE` |

CI 共形 lint 由 worker-A1 SSOT lint 同步加规则:

- ✓ 6 agent_*/api.py 至少 1 个 `@app.post("/api/.+/export_docx")`
- ✓ filename 输出符合 §5.4 正则
- ✓ response header `X-Export-Source` 必带

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
