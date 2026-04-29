# SSE Envelope Contract v1.0

**Status**: 🟢 RATIFIED · spec-only · helper 实现由 Phase A worker-A2 落地 (`shared/sse_envelope.py`)
**Owner**: 主 CLI · 修改走 RFC
**生效**: Phase A worker-A2 落 helper + 6 Agent backend 迁移后强制
**Author**: Phase A worker-A1 · 2026-04-29

---

## 0. 为什么有这份契约

走歪诊断 (`docs/audit/conflict-register-v1.md` Cat 4 · 6 entries): 6 Agent backend 的 SSE `done` event 形态各异:

| Agent | file:line | 现状 |
|---|---|---|
| Channel | `agent_channel/realtime_stream.py:229` | done 含 `candidates / metrics / data_source` · 缺 radar/signals/funnel/match_dimensions/product_recommendations/pitch_scripts |
| Alert | `agent_alert/api.py:107-112` | done 空 payload · stage event 无 stage 名 |
| Credit | `agent_credit/api.py:387` | mock 路完整 payload · live 路 `{"event":"done"}` 空 · 不对称 |
| Compli | `agent_compliance/api.py:121` | done 空 payload |
| Report | `agent_report/api.py:16-19` | 事件名注释标 "V14-B 约定" (旧版命名) · 实现已 v16 · contract 名漂 |
| Riskctrl | `agent_riskctrl/api.py:50` | 显式 "非 SSE" · 前端 `web/src/lib/api/riskctrl.ts:44` 期待 SSE · 全栈分裂 |

无 envelope 共形 · 前端各自手写 reader (audit Cat 3 · ChannelWorkspace + CreditWorkspace + ReportWorkspace 内联 SSE 解析 · 不用 shared `_live.ts streamSse`)。任何 panel 切 live 都要再写一遍 normalize 函数。本 doc = SSE done event 的**唯一权威 schema**。

---

## 1. 适用范围 + Layered scope

本协议**不重复**定义 wire-level 已锁的字段 · 仅锁 `done` envelope + per-agent payload tail:

| 层 | 已锁文档 (authoritative source · DO NOT duplicate) | 本协议覆盖 |
|---|---|---|
| Wire format (`event:` / `data:` lines · `\n\n` 分隔) | RFC EventStream · `field-naming.md` §6 | — |
| SSE event 枚举值 (7 events) | `field-naming.md` §3.6 | mirror only · §1.5 normative table for forward-compat |
| `stage` event payload (`stage` / `progress` / `message`) | `field-naming.md` §6 | — |
| `done` event envelope (top-level keys + per-agent payload tail) | — | ✅ 本协议 §2 |
| Per-agent payload tail schema | `workspace-state-protocol.md` §10 (AgentSession tail) | ✅ 本协议 §3 cross-ref |

**不动的层**: stream / stage / tool_call 等 event payload 形态由各 Agent 在 spec 内定义 (`agent-*-spec.md` § "事件流") · 本协议只锁 `done` event 形态。

### 1.5 Event 名 normative table (mirror · authoritative = field-naming.md §3.6)

> ⚠️ **Mirror 关系**: 本表 verbatim 镜像 `field-naming.md` v1.0 §3.6 SSEEvent enum · 本契约**不引入新 event 名**。当 field-naming.md §3.6 修改时 (升 minor / major) · 本表必须**同 commit** sync · 否则 lint 拒 (Phase A worker-A2 落 lint 后)。
>
> **为什么镜像在这**: 让 6 Agent backend 实现者打开 sse-envelope.md 即看到全部合法 event 名 · 不必跳读 field-naming.md。但**当本表与 field-naming.md §3.6 矛盾时** · 以 field-naming.md 为准 (per `docs/arch/instruction-source-of-truth.md` §1.1 · 同 Tier 1 contracts · 取早立者)。

| event 名 | 用途 | payload schema 出处 | 6 Agent 必发 |
|---|---|---|---|
| `profile_loaded` | 画像加载完成 (Agent1 / Agent6 入参就绪) | `agent-*-spec.md` § "事件流" | optional (per agent · Channel/Report 用 · 其他 N/A) |
| `stage` | 进入新阶段 | `field-naming.md` §6 (stage / progress / message) | ✅ 必发 (≥ 1 stage event) |
| `stream` | LLM 流式 token | `agent-*-spec.md` § "事件流" (text 字段) | optional (LLM 调用时发) |
| `tool_call` | 工具调用 | `agent-*-spec.md` § "事件流" (tool_name / args) | optional (有工具调用时发) |
| `tool_result` | 工具结果 | `agent-*-spec.md` § "事件流" (tool_name / result / ok) | optional (与 tool_call 配对) |
| `done` | 任务结束 (本契约 §2 envelope) | **本契约 §2** (`event` / `version` / `agent` / `session_id` / `ok` / `ts` / `duration_ms` / `metrics` / `payload` / `warnings` / `errors` / `trace_id`) | ✅ 必发 (终态 · 单次) |
| `error` | 错误 | `field-naming.md` §五 ErrorResponse + 本契约 §2.1 ErrorEntry | optional (致命错误另起 event · 否则走 done.errors[]) |

**Wire form 通用约束** (per field-naming.md §6):

```
event: <name>
data: <json · single line · UTF-8>

```
- `event` 名取自上表
- `data` 是单行 JSON · 不允许换行 (NDJSON style)
- 双 `\n` 分隔事件
- `progress` 是 0-1 浮点 (不是 0-100) · `_at` ISO 8601 · 其余字段命名规则见 field-naming.md §2

**Forward-compat 规则** (本契约扩 event 时):
- ✅ 加新 event 名 (consumer 容忍未识别 event) → minor bump (本契约 + field-naming.md §3.6 同步)
- ❌ 改现有 event 名 / 改 wire 分隔符 → major bump (breaking · 6 Agent 同步迁)
- ❌ 一次只改本契约 §1.5 不动 field-naming.md §3.6 (违 mirror 一致性 · CI lint 拒)

---

## 2. Done Event Envelope (共形头 · 6 Agent 必含)

### 2.1 顶层 schema

```typescript
interface DoneEnvelope<TPayload> {
  event: "done";              // 固定值 (per field-naming §3.6)
  version: "1.0";             // envelope 协议版本 · 用于 forward-compat
  agent: AgentId;             // SSOT agent_id (channel/report/credit/alert/compli|compliance/riskctrl)
  session_id: string;         // UUID v4 · per field-naming §四 (服务端生成 · 整链路一致)
  ok: boolean;                // true = 正常完成 · false = 业务级失败 (含 partial · payload 仍有部分数据)
  ts: string;                 // ISO 8601 · per field-naming §2.2 _at 后缀语义
  duration_ms: number;        // 整 SSE 流耗时 · 从首 stage 到 done
  metrics: Record<string, number | string>;  // header 卡片数据 · agent-specific 但 type narrow
  payload: TPayload;          // agent-specific tail · 见 §3
  warnings: string[];         // 非 fatal 提示 (e.g. "live SSE Tavily quota fallback to mock")
  errors: ErrorEntry[];       // ok=false 时必填 · ok=true 时可空
  trace_id: string;           // UUID v4 · cross-agent handoff 链路追踪 (per field-naming §四 correlation_id 同义 · 名称对齐: trace_id)
}

interface ErrorEntry {
  code: string;       // SNAKE_CASE · per field-naming §五
  message: string;    // 用户可见中文
  field?: string;     // 字段级错误时填
  retryable: boolean; // true = 可重试 · false = 配置/权限类
}
```

### 2.2 Field 约束细则

| 字段 | 必填 | 默认 | 校验 |
|---|---|---|---|
| `event` | ✅ | "done" | 必须等于 "done" |
| `version` | ✅ | "1.0" | semver-like · breaking change 升 major |
| `agent` | ✅ | — | 必须在 `agent-naming-ssot.md` §1 列里 |
| `session_id` | ✅ | — | UUID v4 regex · per field-naming §四 |
| `ok` | ✅ | — | bool · 不允许 truthy/falsy 混用 |
| `ts` | ✅ | server now | ISO 8601 with Z (UTC) |
| `duration_ms` | ✅ | — | non-negative int |
| `metrics` | ✅ | `{}` | 仅原子值 · 不嵌套对象 |
| `payload` | ✅ | — | per-agent schema (§3) · live + mock + demo 三模式必同 shape |
| `warnings` | ⚠️ | `[]` | 字符串数组 · 中文 |
| `errors` | ⚠️ | `[]` | ok=false 时 ≥1 entry · ok=true 时**也允许**有 warnings 提示 |
| `trace_id` | ✅ | — | UUID v4 · cross-agent handoff 必传递 |

### 2.3 mode-symmetry 硬线 (audit Cat 4 fix)

**反模式** (audit Cat 4 现状): `agent_credit/api.py:387` mock 路返完整 payload · live 路返 `{"event":"done"}` 空。

**强制**: 同一 agent 的 `live` / `mock` / `demo` 三路 done event payload 必须 shape 一致 (字段集 + 类型一致 · 值可不同)。差异仅在 `warnings` (e.g. live 失败回退 mock 时填 warning · payload 形态不变)。

---

## 3. Per-Agent Payload Tail (cross-ref workspace-state §10)

每 Agent 的 `payload` 是 `workspace-state-protocol.md` §10 `AgentSession.<agent-tail>` 的 wire 形态 (snake_case). `setLiveData(envelope.payload)` 后前端 panel 直接消费。

### 3.1 Channel (Agent1 获客)

```typescript
interface ChannelPayload {
  candidates: Candidate[];          // Top N 候选 · 含 industry/geo/scale/similarity (per Q-041 active rule)
  radar: RadarDimension[];          // 8 维 P50 对标
  signals: SignalSource[];          // 8 信号源状态 (status / hits / coverage)
  funnel: FunnelStage[];            // 5 阶段扫描漏斗
  match_dimensions: MatchDimension[];        // 候选 vs IdealProfile 维度命中
  product_recommendations: ProductRec[];     // Top3 产品推荐 + score
  pitch_scripts: PitchScript[];              // 切入话术
  ideal_profile?: IdealProfile;              // B.6b LLM 抽画像 (可选 · 仅 KB-mode)
  data_source: "live" | "mock" | "demo";     // mode 标识 · 前端 banner 用
}
```

`metrics`: `{ signal_total: number, companies_found: number, final: number, kb_files_used: number }`

### 3.2 Report (Agent6 报告)

```typescript
interface ReportPayload {
  report_json: ReportJSON;            // v16 主输出 · ReportJSON schema 由 agent-handoff-schemas.md (worker-A6) 定义
  uploaded_files: UploadedFile[];     // 文件列表 + 元数据
  kb_hits: KbHit[];                   // KB 引用 + 置信度
  extracted_fields: ExtractedField[]; // 字段抽取结果 (含 prefilled / llm_filled / unfilled 三态)
  draft_sections: DraftSection[];     // 段落生成产物
  qc_result: QCResult;                // 9 维度评分 + pass/block
  unfilled_marker_count: number;      // "未能自动填写" 标记数
  data_source: "live" | "mock" | "demo";
}
```

`metrics`: `{ field_completeness: number, evidence_rate: number, qc_score: number, hallucination_rate: number }` (per CLAUDE.md §5.1)

### 3.3 Credit (Agent3 授信)

```typescript
interface CreditPayload {
  score_radar: ScoreRadar;            // 4 维评分 (per CLAUDE.md §11 · 对公/普惠/对私 三板块)
  red_lines: RedLineHit[];            // 红线触发点 · 含 severity (per field-naming §3.3)
  stage_tabs: StageTab[];             // 阶段 tab 数据 (3 stage × 子维)
  decision_letter: DecisionLetter;    // 审批意见书 (含 amount_yuan + term_months · per field-naming §2.2)
  evidence_trail: EvidenceTrailEntry[];      // 证据链 (Batch 2 持续保留)
  decision_verdict: DecisionVerdict;  // per field-naming §3.4 enum
  segment: Segment;                   // per field-naming §3.2 enum (corporate/retail)
  data_source: "live" | "mock" | "demo";
}
```

`metrics`: `{ score_total: number, red_line_count: number, evidence_count: number }`

### 3.4 Alert (Agent4 预警)

```typescript
interface AlertPayload {
  hitlist: HitlistEntry[];            // 红/黄/绿榜单 (per field-naming §3.3 severity enum)
  signal_map: SignalMapNode[];        // 信号源映射
  drill_detail: DrillDetail | null;   // 单客深查 (selectedCandidate 触发后填)
  scan_summary: ScanSummary;          // 扫描范围 + 命中率
  data_source: "live" | "mock" | "demo";
}
```

`metrics`: `{ red_count: number, yellow_count: number, green_count: number, scanned_total: number }`

### 3.5 Compli (Agent5 合规) · 字段名按 PM 拍板 agent_id 定 (`agent-naming-ssot.md` §3)

```typescript
interface ComplianceOrCompliPayload {  // 类型名跟 PM 选项变
  policy_diff: PolicyDiff[];          // 政策原文 vs 业务制度对照
  matrix_scan: MatrixScanResult[];    // 业务矩阵扫描
  conflict_points: ConflictPoint[];   // 违规冲突点明细
  draft_revision: DraftRevision[];    // 修订意见
  policy_event: PolicyEvent;          // 触发本次扫描的政策事件
  data_source: "live" | "mock" | "demo";
}
```

`metrics`: `{ conflict_count: number, severity_red: number, severity_yellow: number, policies_scanned: number }`

### 3.6 Riskctrl (Agent2 风控) · 🟡 SSE 化决议 pending

**当前现状** (audit Cat 4 + Cat 3 镜像): `agent_riskctrl/api.py:50` 显式标 "非 SSE" · 但 `web/src/lib/api/riskctrl.ts:44` 期待 SSE。全栈分裂。

**Phase A 决议**:
- (a) **Riskctrl 全 SSE 化** (推荐 · 与 5 Agent 共形 · worker-A4-riskctrl 接) — 后端补 SSE wrapper · `dsl_gen` / `backtest` / `sample_dist` 三 endpoint 流式输出 · 前端 `riskctrl.ts` 复用 `streamSse`
- (b) Riskctrl 保留 sync REST + 前端 `riskctrl.ts` 改 fetch — 偏离共形 · **不推荐**

主 CLI 倾向 (a) · PM 默认追认 unless override · 在 SSE 化 done 后 payload 形态:

```typescript
interface RiskctrlPayload {
  dsl_draft: DslRule[];              // 生成的 DSL 规则
  backtest: BacktestResult;          // KS / AUC / 通过率 (per agent-forge-spec)
  sample_distribution: SampleDist;   // 样本分布
  rule_interpretability: Likert[];   // 3-dim Likert (per Phase 3 final 轨 8b)
  data_source: "live" | "mock" | "demo";
}
```

`metrics`: `{ ks: number, auc: number, pass_rate: number, max_rows: number }` (max_rows 反映 Q-040 active rule · 默认 50000)

**SSE 化 commit 后** 本 §3.6 的 🟡 移除 + bump envelope 到 v1.1。

---

## 4. Helper API (worker-A2 实现 · spec-only here)

### 4.1 Backend helper

```python
# shared/sse_envelope.py (worker-A2 实装)

from typing import TypedDict, TypeVar, Generic, Literal

T = TypeVar("T")

class DoneEnvelope(TypedDict, Generic[T]):
    event: Literal["done"]
    version: Literal["1.0"]
    agent: str
    session_id: str
    ok: bool
    ts: str
    duration_ms: int
    metrics: dict
    payload: T
    warnings: list[str]
    errors: list[dict]
    trace_id: str


def build_done_envelope(
    *,
    agent: str,
    session_id: str,
    payload: T,
    metrics: dict,
    started_at: float,           # time.time() at SSE 流开头
    ok: bool = True,
    warnings: list[str] | None = None,
    errors: list[dict] | None = None,
    trace_id: str | None = None,
) -> DoneEnvelope[T]:
    """构建 done event envelope · 6 Agent 一律调此函数 · 不允许各自拼 dict."""
    ...
```

### 4.2 Frontend consumer

```typescript
// web/src/lib/api/_live.ts (现有 streamSse 升级)

export interface DoneEnvelope<T> { /* §2.1 schema */ }

export async function* streamSse<TDone>(
  url: string,
  init?: RequestInit,
): AsyncGenerator<SseEvent | { event: "done"; envelope: DoneEnvelope<TDone> }> {
  // 解析 done event 时自动 wrap 成 envelope · type narrow 给 TDone
  ...
}
```

6 Workspace 用法:

```tsx
for await (const evt of streamSse<ChannelPayload>("/api/channel/run")) {
  if (evt.event === "done") {
    setLiveData(evt.envelope.payload);  // ChannelPayload type-checked
    setMetrics(evt.envelope.metrics);
    if (!evt.envelope.ok) {
      showBanner(evt.envelope.errors[0].message);
    }
  }
}
```

---

## 5. Migration Path (per Agent · 6 step)

每 Agent backend 迁本 envelope 步骤:

1. import `shared.sse_envelope.build_done_envelope`
2. 收集 payload (per §3 该 Agent schema)
3. 调 `build_done_envelope(...)` 构 envelope
4. SSE 写出: `yield f"event: done\ndata: {json.dumps(envelope, ensure_ascii=False)}\n\n"`
5. `live` / `mock` / `demo` 三路必跑同 helper · 保 mode-symmetry (§2.3)
6. 前端 Workspace `setLiveData(envelope.payload)` (而非自己拼 normalize)

worker-A4 5 子 worker 各跑一遍 · A3 Channel pilot 先跑通 · 5 Agent 复用模板。

---

## 6. Versioning + Forward-compat

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-04-29 | Initial · envelope 顶层 schema + 6 agent payload tail · §3.6 Riskctrl SSE 化 PM-pending 留 placeholder |

**Breaking change** (升 major v2.0): envelope 顶层字段重命名 / 删除 · `agent` 列改值 · `version` 字段语义变。

**Non-breaking** (升 minor v1.x): payload tail 加字段 · `metrics` 加 key · `warnings` / `errors` 拓展 · 新 agent 加入 (consumer 容忍未识别字段)。

**Riskctrl SSE 化** 后 bump v1.1 · §3.6 placeholder 移除。

---

## 7. Cross-reference

- `field-naming.md` v1.0 · §3.6 (SSE event names) + §6 (wire format) + §四 (UUID/trace_id)
- `workspace-state-protocol.md` v1.1 · §10 AgentSession tail · 本协议 §3 是其 wire 形态
- `agent-naming-ssot.md` v1.0 · §1 agent_id · 本协议 envelope.agent 必从 SSOT 取
- `llm-prompt-contract.md` (本批 #4) · output-schema 段定义 LLM JSON schema · payload 内 LLM-生成字段须符合
- 6 Agent spec doc · 本协议是各 spec § "事件流 / SSE" 的统一规则

---

## 8. 验收 (Phase A 硬线)

- ✅ envelope 顶层 schema 锁 (§2)
- ✅ 6 Agent payload tail 定 (§3 · Riskctrl 留 PM)
- ✅ helper API spec 给 worker-A2 (§4)
- ✅ migration path 6 步 (§5)
- ⏳ worker-A2 落 `shared/sse_envelope.py` 实装 + tests
- ⏳ worker-A3 (Channel pilot) + A4 (5 子) 6 Agent 全迁
- ⏳ Riskctrl SSE 化 PM 拍板 → bump v1.1
