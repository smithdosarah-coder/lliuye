# W1-backend Progress (append-only)

> 接力 sub-agent 必读 · main session 监控源 · sub-agent checkpoint 每次 append 一段

<!-- 第一棒 sub-agent 在此 append 第一段 -->

## 2026-05-12 · checkpoint 0 (scope verify · 第 1 棒起手)

- **完成文件** (0/18):
  - 无 (本棒仅 scope verify · 不写 18 文件 · 留下一棒)
- **关键决策** (我理解 W1 backend scope · ≤ 200 字):
  - `liuye_service/` 是新前端 `credit_matrix_next/` 唯一后端入口 · in-process 调 `shared/*` (llm_caller / decision_ledger / audit_service / kb_scan / sources / sse_envelope / evidence_freshness / data_tiers / recommendation_schema / auth_service.dependencies) · HTTP 调 6 老 agent (`agent_*/api.py` · 走各 adapter) · **禁** import `agent_*` 内部. SSE v1→liuye **11 event** adapter (`adapters/sse_v1_to_liuye.py`) 是唯一 wire 兼容层 · 老 v1.0 不废 · seq 重生 · dedup_key 去重 · 转换失败转 `turn.error SSE_ADAPTER_FAILED`. Cowork (channel/credit/report < 5s SLA SSE 实做 adapter) vs Managed (riskctrl/alert/compliance Phase 1 stub `NotImplementedError("Phase 2")` · Phase 2 走 job_id + poll). decision_ledger in-process (`record_decision` · subject_id 16-hex hash · plain PII 禁 · jurisdiction=HQ default · retention per agent 表 · silent-fail · outbox 60s 5 retry 60/120/240/480/960s backoff · 超 5 写 dead-letter · systemd 部署). LLM 走 `shared.llm_caller.LLMCaller(agent_id="liuye")` · `DEFAULT_FALLBACK_CHAIN=("deepseek","dashscope")` 全境内 (PIPL) · moonshot 仅 `LLM_PROVIDER=moonshot` 显式. PermissionRequest 3 风险 (low inline / medium modal / high drawer with reason · 不可逆动作必带 `idempotency_key`) · PM 2026-05-11 ratify 加 11th event `permission.request` 由 `permissions.py::emit_permission_request` 直接 emit · **不经 adapter 转换** · medium blocking 期业务 event (message.delta / tool.progress / artifact.patch / evidence.attached) 暂停 · heartbeat 15s 续 · grant REST `POST /api/liuye/permissions/{id}/grant` 后 `orchestrator.py::resume_turn(turn_id)` seq+1 续 · deny REST 后 `abort_turn(turn_id, 'PERMISSION_DENIED')` 推 turn.error + turn.completed ok=false 收尾. LedgerEntry v1.1.0 加 optional `parent_turn_id` (跨 mode 父子 turn link · 仅 Cowork→Managed 场景填 · 单 mode None) · `audit.py / ledger_review.py` 调 `record_decision` 时 Agent2 Cowork DSL→Managed backtest 场景必填. **禁** 建 `liuye_service/prompts/` 新目录 (root §3.7.7 prompt SSOT 灰度 · `liuye_service` 不持有 system prompt · BFF 级辅助 prompt 走 `shared.llm_caller` + `orchestrator.py` 内 inline string).
- **下一棒 file checklist** (skeleton 8 文件 · 30-45 min 估时):
  - `liuye_service/__init__.py` (空 + version)
  - `liuye_service/config.py` (env LIUYE_ENABLED / LIUYE_DEMO_MODE / LIUYE_LEDGER_JURISDICTION / LIUYE_FIXTURES_PATH · 3.10 dataclass)
  - `liuye_service/trace.py` (liuye_session_id ↔ trace_id 关联 helper)
  - `liuye_service/schemas.py` (Pydantic 5 协议 + LedgerReviewEvent + PermissionRequest + ValidationIssue · 引 `protocols/generated.py` re-export)
  - `liuye_service/permissions.py` (3 风险分级 + `emit_permission_request` 直接 emit 11th event + grant/deny REST handler · idempotency_key 防重)
  - `liuye_service/audit.py` (包 audit_service.decorators.audit_llm_call + shared.decision_ledger.record_decision · silent-fail + outbox enqueue 接口)
  - `liuye_service/orchestrator.py` (Cowork SSE 编排骨架 · resume_turn / abort_turn / range messages endpoint · permission hold state)
  - `liuye_service/api.py` (FastAPI router · §3.5 endpoint inventory 10 REST + 1 SSE 挂点 · `register_liuye_routes(app)` 入口)
- **blocker** (or "无"):
  - 无
- **v3 spec 内部一致性 (Read 时发现)**:
  - SSE matrix §3 Q1-Q3 解与 v3 §2.1 line 44 (11 event 含 `permission.request`) 一致 · matrix v1.1 已 PM ratify · §3 Q3 已完全重写 · 旧借 `tool.progress.payload.permission_request` 自决方案已 deprecated · 与 v3 spec §2.1.5 line 107 + 附录 A.1 一致
  - ToolStatus 8 态命名 (`queued/connecting/running/streaming/idle_timeout/completed/failed/aborted`) v3 §2.3 + SSE matrix §1 一致 · `permission.request` 触发时切 `connecting` · grant → `running` · deny → `aborted` · idle 60s → `idle_timeout` (per v3 附录 A.3)
  - Cowork SLA < 5s vs Managed job_id 边界 (root §3.1.1 + liuye CLAUDE.md §4) 一致 · Cowork agent 不可跑超 5s · Managed 不可强 SSE 假装实时 · `adapters/riskctrl.py / alert.py / compliance.py` Phase 1 stub 留 `NotImplementedError("Phase 2")`
  - ProgressMessage.percent 口径: 老 v1 是 0-1 浮点 (sse-envelope.md §1.5) · liuye 是 0-100 整数 (v3 §2.3) · adapter `* 100` 转换 · SSE matrix §2 备注与 §4 mapping 表一致
  - LedgerEntry v1.1.0 (`shared/decision_ledger/schema.py:22` LEDGER_SCHEMA_VERSION = "1.1.0") 加 optional `parent_turn_id` (PM 2026-05-11 ratify perfect-check-6) · 与本棒接到的 PM 决议一致
- **ELAPSED min**: ~25 (起手 7 件事 read · 无写代码)
- **commit SHA**: 715dd09baea416ac36928525ed3e4a19b387fc84

## 2026-05-12 · checkpoint 2 (skeleton 8 文件 · 第 2 棒)

- **完成文件** (8/18):
  - `liuye_service/__init__.py` (28 行 · version constant `__version__ = "0.1.0"` 与 contracts.lock schema_version 一致 · 不 export 任何 symbol)
  - `liuye_service/config.py` (129 行 · `Settings` frozen dataclass + `from_env()` + `get_settings()`/`set_default_settings()` 单例 · 4 env var: `LIUYE_ENABLED` / `LIUYE_DEMO_MODE` / `LIUYE_LEDGER_JURISDICTION` / `LIUYE_FIXTURES_PATH` · 复用 `shared.decision_ledger.schema.ALLOWED_JURISDICTIONS` + `DEFAULT_JURISDICTION` · fixtures default 项目根 `tests/fixtures/` per W1-backend §4.10)
  - `liuye_service/trace.py` (138 行 · `LiuyeTraceContext` frozen dataclass `trace_id` / `liuye_session_id` / `turn_id` / `tool_call_id` · helper `new_trace_context` / `from_request_headers` / `to_response_headers` + `with_turn` / `with_tool_call` 派生 · 4 HTTP header constant `X-Trace-Id` / `X-Liuye-Session-Id` / `X-Liuye-Turn-Id` / `X-Liuye-Tool-Call-Id` · 无 framework 依赖)
  - `liuye_service/schemas.py` (288 行 · re-export 5 核心协议 from `liuye_service.protocols.generated` (`Artifact` / `ArtifactPatch` / `EvidenceRef` / `KBDoc` / `LiuyeChatEvent` / `ProgressMessage` / `ToolCall` / `PermissionRequestEventPayload` / `TurnErrorPayload`) · 5 BFF 横切协议: `LedgerReviewEvent` / `PermissionRequest` / `ValidationIssue` / `ArtifactAction` / `TokenBudgetState` · 全用 `_LiuyeBaseModel(populate_by_name=True, extra='forbid')` 与 generated.py 一致 · 严禁 shadowing 5 SSOT 协议)
  - `liuye_service/permissions.py` (349 行 · `ACTION_RISK_TIER` 14 action registry (low 4 / medium 5 / high 5) + `IDEMPOTENCY_REQUIRED_ACTIONS` frozenset · `risk_tier_for()` / `requires_idempotency_key()` lookup · `emit_permission_request(request, sse_writer, *, trace_id)` 直接 emit 11th event PM 2026-05-11 Q2 ratify · 走 `model_dump(mode='json')` 映射 `id`→`request_id` 与 `PermissionRequestEventPayload` 一致 · `grant()`/`deny()` handler 验 idempotency_key + required_persona + role · 调 `orchestrator.resume_turn`/`abort_turn` + 写 `LedgerReviewEvent` via 可注入 `ReviewWriter` · 用 Protocol `SSEWriter`/`OrchestratorHandle` 保持可测)
  - `liuye_service/audit.py` (206 行 · `record_liuye_decision()` wrapper 包 `shared.decision_ledger.record_decision` · 用 `hash_subject_id` defensive double-hash · `_enqueue_outbox()` 写 `data/liuye/outbox/{decision_id}.json` 用 silent-fail · parent_turn_id Q3 ratify 走 `evidence_chain._meta.parent_turn_id` (因 shared.record_decision 当前 façade 不暴露 parent_turn_id kwarg · LedgerEntry v1.1.0 schema 字段已建 · 不破坏向后兼容) · re-export `audit_llm_call` stub fallback)
  - `liuye_service/orchestrator.py` (360 行 · `CoworkOrchestrator` class · `start_turn` / `dispatch_message` / `resume_turn` / `abort_turn` / `register_permission_hold` / `get_permission_hold` / `clear_permission_hold` / `next_seq` · `TurnState` dataclass per turn (turn_id / trace_id / persona / agent_id / seq / parent_turn_id / closed / held_by_permission) · `_permission_holds: dict[turn_id, PermissionRequest]` + `_holds_by_request: dict[request_id, turn_id]` 双向 index · `asyncio.Lock` 序列化 mutation 避 deadlock event loop · `HEARTBEAT_INTERVAL_SECONDS = 15.0` 常量 per matrix §3 Q3 · `default_orchestrator()`/`set_default_orchestrator()` 单例 mirror `decision_ledger.default_ledger`)
  - `liuye_service/api.py` (521 行 · `register_liuye_routes(app)` 3-6 行 mount point · `LIUYE_ENABLED` env gate (False 时 skip mount + return False · True 时 mount 11 endpoint + return True) · 11 endpoint 全挂 verbatim per §3.5: health (anonymous) / sessions POST 201 / sessions/{turn_id}/messages POST 202 fire-and-forget asyncio.create_task / tools/{tool_id}/invoke POST 501 Phase 2 stub / permissions/{request_id}/grant + deny / ledger/decisions/{id}/review_events POST 201 (skeleton echo · sqlite write 留 ledger_review.py) / ledger/decisions/{id} GET 走 `shared.decision_ledger.get_decision` (review_chain 留 ledger_review.py) / kb/upload + kb/search Phase 2 501 stub / sessions/{turn_id}/stream GET SSE (`_stream_skeleton` emit turn.started + 15s heartbeat · 真 adapter bridge 留下一棒) · `Depends(require_user)` 复用 `auth_service.dependencies` (lazy import stub 兜底 local dev))
- **关键决策** (skeleton 取舍):
  - **schemas.py 严守 SSOT**: 仅 re-export `protocols/generated.py` · 不 shadow 5 核心协议 · 5 BFF 横切协议明确标 v3 §2.5 非 contract worker scope
  - **audit.py parent_turn_id 走 evidence_chain._meta**: `shared.decision_ledger.record_decision` façade 当前不暴露 parent_turn_id kwarg · LedgerEntry schema 已升 v1.1.0 但 façade 待升级 · 我用 evidence_chain._meta.parent_turn_id 保留信息 + 向后兼容 · 下一棒 ledger_review.py 落 sqlite 时可直接 store 层调 record + parent_turn_id (绕过 façade) 或推 shared façade 升级 PR (recommend 后者 · 见 hidden gotcha)
  - **orchestrator.py asyncio.Lock 不 threading.Lock**: FastAPI async handler 在 single event-loop thread · threading.Lock + await 组合会死锁 loop · asyncio.Lock 安全 · 多 worker 部署 permission state per-worker · scale-out 用 Redis (Phase 1 in-memory 满足 demo)
  - **api.py SSE skeleton 仅 turn.started + heartbeat**: 真 SSE v1→liuye 10 event bridge 走 `adapters/sse_v1_to_liuye.py` (下一棒) · skeleton 留 contract 可加载 · frontend 集成可起手 · 不阻塞下游
  - **emit_permission_request 直接 emit 不经 adapter**: per PM 2026-05-11 Q2 ratify · `permissions.py::emit_permission_request` 直接调 `sse_writer.emit(event='permission.request', payload=...)` · NOT 经 `adapters/sse_v1_to_liuye.py` (该 adapter 是 v1→liuye wire 兼容 · permission.request 无 v1 antecedent · 是 control-plane 信号)
  - **LIUYE_ENABLED gate 返 bool**: `register_liuye_routes` 返 True/False · caller (api_server.py 下一棒接入) 可 log 到 state-snapshot.md · 老 6 agent 路径不受影响
- **下一棒 file checklist** (5 adapter + 3 Managed stub · 30-45 min 估时):
  - `liuye_service/adapters/__init__.py` (空)
  - `liuye_service/adapters/base.py` (CoworkAdapter abstract base · httpx.AsyncClient session 管理 · 复用 orchestrator.CoworkAdapter Protocol)
  - `liuye_service/adapters/channel.py` (Cowork SSE · HTTP 调 `/api/channel/run` · 走 sse_v1_to_liuye 转译)
  - `liuye_service/adapters/credit.py` (Cowork SSE · HTTP 调 `/api/credit/decision`)
  - `liuye_service/adapters/report.py` (Cowork SSE · HTTP 调 `/api/report/v16/fill`)
  - `liuye_service/adapters/sse_v1_to_liuye.py` (**10 event** mapping verbatim per v3 附录 A.1 · seq 单调递增 · `dedup_key = (event, data_hash)` · 失败转 `turn.error SSE_ADAPTER_FAILED fallback_available=true` · `permission.request` 不在此 adapter 覆盖范围 · 由 `permissions.py::emit_permission_request` 直接 emit)
  - `liuye_service/adapters/riskctrl.py` (Managed stub · `NotImplementedError("Phase 2")`)
  - `liuye_service/adapters/alert.py` (Managed stub · `NotImplementedError("Phase 2")`)
  - `liuye_service/adapters/compliance.py` (Managed stub · `NotImplementedError("Phase 2")`)
- **blocker** (or "无"):
  - 无
- **hidden gotcha** (下一棒注意):
  - `shared.decision_ledger.record_decision` façade 未暴露 `parent_turn_id` kwarg · 当前我用 `evidence_chain._meta.parent_turn_id` 绕过 · 下一棒 ledger_review.py 落 sqlite 应推 façade 升级 PR (在 `shared/decision_ledger/store.py:612` 加 `parent_turn_id` kwarg · 转发到 LedgerEntry 构造 · `record` method 同步加) · 否则 v1.1.0 schema 字段长期沉默
  - FastAPI 11 endpoint registration 顺序: `health` 在最前 · 不带 `Depends(require_user)` · 探针流量不触发 auth · 其余 10 endpoint 全带 require_user · 后续 register_liuye_routes 调用要在其他 register_*_routes 之后挂 (避免 LIUYE_ENABLED=false 时影响老路由)
  - Pydantic v2 alias 与 generated.py 一致: 所有 BFF 横切 model 都 `populate_by_name=True` + `extra='forbid'` · frontend Zod camelCase 输入会被 alias 接住 (后续 PR 升级 alias_generator 时统一加)
  - orchestrator permission hold state 多 worker 部署 per-worker · Phase 1 单 worker per host 满足 demo · scale-out 时换 Redis backend (interface 已是 dict-shaped · 不破坏调用方)
  - SSE stream skeleton 用 `id: {turn_id}:{seq}` format · 一行带俩 id · EventSource Last-Event-ID 自动 carry · 下一棒 adapter 实现真重连时直接读 last_event_id parse 出 turn_id + seq · 不需 frontend 额外送
- **ELAPSED min**: ~40 (含 7 件 read + 8 文件 write + 2 smoke test + progress append)
- **commit SHA**: 6da4fe74c34aa9699eb8085da8c191e9b56228da

## 2026-05-12 · checkpoint 3 (5 adapter + 3 Managed stub · 第 3 棒)

- **完成文件** (17/18):
  - `liuye_service/adapters/__init__.py` (27 行 · 空 export · 包级 docstring 说明 7 子模块各自职责 + W1 file checklist 一文件一 adapter 硬线)
  - `liuye_service/adapters/base.py` (240 行 · `AgentAdapter` Protocol (start_turn / dispatch_message / abort_turn · cowork/managed_readonly boundary 字段) + 共享 utility `_make_seq(turn_id)` (`threading.Lock` 序列化 · 1-based · multi-worker Redis 未来扩展点) + `reset_seq()` 测试 helper + LIUYE_FIXTURES_PATH loader (`fixtures_root()` / `load_fixture(name)` · path component 拒入 · `FixtureLoadError` 用于 turn.error code=DEMO_FIXTURE_MISSING) + `envelope()` helper (schema_version='1' + 单调 seq + tool_call_id/artifact_id/message_id optional 注入))
  - `liuye_service/adapters/sse_v1_to_liuye.py` (425 行 · `SseV1ToLiuyeAdapter` class 实做 8 v1 event handler: `_on_profile_loaded` / `_on_stage` / `_on_stream` / `_on_tool_call` / `_on_tool_result` / `_on_done` / `_on_error` / `_on_heartbeat` · dedup `(event, sha256(canonical_json(payload)))` set 去重 · v1 progress 0-1 float → liuye percent 0-100 int round() 转换 · ToolCall context inheritance (stage 自动继承最近 tool_call 的 `_current_tool_call_id`) · stream 首帧 emit `message.created` · delta 走 SSE comment line (非事件 · API 层处理) · 7 v1 → 7 liuye 直接映射 + heartbeat 透传 · `_V1_HANDLERS` dispatch table · ANY handler exception → 单条 `turn.error code=SSE_ADAPTER_FAILED fallback_available=true human_hint='事件流转换失败 · 已切换至完整快照模式'` · 11th event `permission.request` 不在本 adapter scope · `artifact.patch` / `evidence.attached` 由 BFF 直接 emit)
  - `liuye_service/adapters/channel.py` (380 行 · `ChannelAdapter` agent_id='channel' boundary='cowork' · `httpx.AsyncClient` Timeout(5.0, read=30.0) · backend_url default `http://localhost:8001` (mock-test SSE port) · DEMO_MODE 走 `load_fixture("channel_5candidates")` → `_synthesise_channel_v1_frames` (matrix §2.1 Scenario A · profile_loaded → tool_call(signal_search) → 3 stage → tool_result → done) · live 模式 `client.stream("POST", url, json=body)` + `_iter_sse_v1(response)` parser · timeout → `turn.error code=ADAPTER_TIMEOUT human_hint='获客 Agent 暂时不可用 · 已切换至降级模式'` · `record_turn_decision()` retention=short 90d per §3.7.5 · 调 `audit.record_liuye_decision()`)
  - `liuye_service/adapters/credit.py` (336 行 · `CreditAdapter` agent_id='credit' boundary='cowork' · backend_url default `http://localhost:8002` · DEMO_MODE 走 `credit_decision_PASS` fixture → matrix §2.2 Scenario A 4-dim PASS frames (reuse_report_json → 4dim_scoring → red_line_check → peer_gap_evidence) · `parent_tool_call_id` 透传 (Report → Credit handoff lineage · v3 §2.1 + 必修 #51) · `record_turn_decision()` retention=standard 5y per §3.7.5 银保监 archive · 复用 `channel._iter_sse_v1` SSE 解析 (DRY))
  - `liuye_service/adapters/report.py` (370 行 · `ReportAdapter` agent_id='report' boundary='cowork' · `httpx.Timeout(5.0, read=60.0)` (报告 SLA 30s · headroom 60s) · backend_url default `http://localhost:8003` · DEMO_MODE 走 `report_v16_PARTIAL` fixture → matrix §2.3 Scenario A 5-stage v16 (classifier → truth_fill → generator → evidence_link → qc_gate) · `record_turn_decision()` retention=long 10y per §3.7.5 审贷会 底稿 · fixture 缺失时 emit `DEMO_FIXTURE_MISSING` 不编 (Evidence-First §3.3))
  - `liuye_service/adapters/riskctrl.py` (105 行 · `RiskctrlAdapter` agent_id='riskctrl' boundary='managed_readonly' Phase 2 stub · `NotImplementedError("agent=riskctrl is Managed (job_id + poll · ≥ 1 min backtest) · Phase 1 BFF does not implement live dispatch · see root §3.1.1 + matrix §2.6 + W1-backend §11 · ships Phase 2 (Q4 2026 · shared/job_runtime)")` · docstring 写清触发源 (策略诉求 + 历史样本回测) / 响应 SLA (≥ 1 min · 50000 行 KS per Q-040) / 持久化 (本地 JSON + decision_ledger) / Phase 2 起点)
  - `liuye_service/adapters/alert.py` (87 行 · `AlertAdapter` agent_id='alert' boundary='managed_readonly' Phase 2 stub · 同结构 · docstring 写清触发源 (客户行为变化 batch cron) / SLA (分钟 ~ 数小时) / 持久化 (job_id + status + retry + artifact + decision_ledger short 90d · red severity 升 standard))
  - `liuye_service/adapters/compliance.py` (89 行 · `ComplianceAdapter` agent_id='compliance' boundary='managed_readonly' Phase 2 stub · 同结构 · docstring 写清触发源 (政策发布事件 · 银保监 / 央行 / 内规变更) / SLA (分钟 ~ 数小时) / 持久化 (decision_ledger standard 5y 银保监 archive) · 命名 SSOT `compliance` 全栈 per Q-042.B + Stage 4 ratify)
- **关键决策** (skeleton 取舍):
  - **SSE v1→liuye 转换走 dispatch table + dedup set**: `_V1_HANDLERS: dict[str, str]` table 把 v1 event name 映射到 handler method name · 任何 handler 抛 exception 进入 `try/except` 统一转 `turn.error code=SSE_ADAPTER_FAILED` (matrix §4.2 rule 5 verbatim) · dedup_key `(event, sha256(canonical_json(payload)))` 防 v1 re-delivery · forward-compat: unknown v1 event silent skip (per `sse-envelope.md` §1.5 容忍未识别 event)
  - **percent 0-1 float → 0-100 int 转换** (matrix §3 Q1): `int(round(float(progress) * 100))` 在 `_on_stage` 实施 · clamp 0-100 范围 · 也支持 v1 已是 0-100 整数的 backwards compat (`percent` 字段直接 round)
  - **`_current_tool_call_id` context inheritance**: v1 `stage` event 不带 tool_call_id · liuye `tool.progress` 必带 (per v3 §2.3 + matrix §1) · 翻译器 stateful 记最近 `tool_call` 的 id · `stage` 自动继承 · 这是 SSE matrix §1 + §4 没明说但 SSE matrix §2 实际 cell 表达的语义
  - **stream → message.created 仅首帧**: per matrix §4 row 3 · subsequent token delta 走 SSE `comment:` 行 (非事件 · API 层 `_stream_skeleton` 处理) · 翻译器只 emit 一次 `message.created` 守 `self._message_started`
  - **3 Cowork adapter 同结构 · 不抽 base 实做**: per CLAUDE.md "前端一线必丝滑 + 后端可复杂"但**这是后端 adapter 中间层** · 显式重复让 Phase 2 加 per-agent 特化 (e.g. 报告大 artifact chunked patch · credit 调 peer_gap subtool) 时不互相影响 · base.py 只共享 Protocol + utility · 不强制继承
  - **Managed stub `NotImplementedError` 带完整 Phase 2 message**: 触发源 / 响应 SLA / 持久化 / Phase 2 milestone 全写 docstring · 任何 worker 触到 stub 都能立刻读懂为什么 stop · 不必跳读 root §3.1.1 + matrix §2.4-2.6
  - **httpx SSE 解析 `_iter_sse_v1` 放 channel.py 共享**: credit/report import 复用 (DRY) · 不抽 base 因 base 是 framework-free (Protocol + utility · 不引 httpx · 测试 easier)
  - **fixture 路径不允许 path component**: `load_fixture(name)` 若 `name` 含 `/` 或 `\\` 或 `..` 直接抛 FixtureLoadError · 防 path traversal · 调用方只能传 stem name (e.g. `channel_5candidates`)
- **下一棒 file checklist** (5 文件 · 30-45 min 估时):
  - `liuye_service/workers/outbox_retry.py` (60s 扫 `data/liuye/outbox/` · 5 retry · backoff 60/120/240/480/960s · 超 5 写 `data/liuye/dead-letter/` + Sentry alert · idempotency_key 防重 · systemd unit 部署)
  - `liuye_service/ledger_review.py` (`POST /api/liuye/ledger/decisions/{id}/review_events` handler 实做 · append-only · idempotency_key 防重 · 调 `shared.decision_ledger` store 写 sqlite review chain · 推 façade upgrade PR 加 `parent_turn_id` kwarg 到 `shared/decision_ledger/store.py:612` 与 `record_decision`)
  - `liuye_service/tests/__init__.py` + `liuye_service/tests/test_contracts.py` (5 协议 Pydantic schema validate)
  - `liuye_service/tests/test_sse_adapter.py` (7 v1 → liuye 11 event mapping · dedup · percent · degraded fallback · seq monotonic 单调 · 含 demo fixture replay 集成测试)
  - `liuye_service/tests/test_outbox.py` (outbox worker retry + dead-letter + idempotency)
- **blocker** (or "无"):
  - 无
- **hidden gotcha** (下一棒注意):
  - **`shared.decision_ledger.record_decision` façade 仍未暴露 `parent_turn_id` kwarg** · 我延续上一棒走 `evidence_chain._meta.parent_turn_id` (audit.py) · 但 `audit.record_liuye_decision(parent_turn_id=...)` 接 kwarg 已能完整 forward · 下一棒 `ledger_review.py` 强烈建议落 façade upgrade PR: 在 `shared/decision_ledger/store.py:612` 加 `parent_turn_id` kwarg 转发 + façade `record_decision` 同步加 · 否则 v1.1.0 schema 字段长期沉默 (PR 单独开 · 不动 shared/ 是 shared scope · 在 audit.py 端 PR 我已显式准备好 parent_turn_id 形参 forward 即可)
  - **httpx async streaming 边角**: `client.stream("POST", url, json=body)` async context manager 必须 await · 我用 `async with`正确 · DEMO_MODE 完全绕过 httpx 直接生成 v1 frames list · 不存在 streaming 状态泄漏 · live 模式 `_iter_sse_v1` 是 async generator · 按 SSE line spec 解析 (`event:` / `data:` / empty line 分隔事件 · `:` comment 行忽略)
  - **dedup_key 实际生成**: `_dedup_key(event, payload)` = `event::sha256(canonical_json(payload))` · canonical_json 用 `sort_keys=True ensure_ascii=False default=str` 让 datetime / UUID 等也能稳定 hash · 同一 v1 event 重发 (老 agent 重试 / 网络 redelivery) 1.6KB v1 payload 也只占 64 byte hash · 单 turn 数十 event 量 set 占内存可忽略
  - **parent_tool_call_id Report→Credit handoff 实做**: `credit.py:_synthesise_credit_v1_frames` 接 `parent_tool_call_id` kwarg · 若调用 dispatch 时 payload 含此字段 (从 `tool_call` v1 event 透传) · adapter 在 `tool_call_payload` 加 `parent_tool_call_id` · 翻译器 `_on_tool_call` 把它 passthrough 到 liuye `tool.started.payload.parent_tool_call_id` · 客户端可还原 Report → Credit 的 audit lineage
  - **`api.py` 接 9 adapter mount 还没做**: 当前 `api.py:register_liuye_routes` 仅 mount 11 endpoint · adapter 实例化 + `orchestrator.register_adapter(ChannelAdapter())` 等绑定逻辑留下一棒接 (顺序: outbox_retry → ledger_review → tests · adapter wiring 在 tests 之后 single PR 接 · 否则未测代码 bind 入 api_server 风险大)
  - **SSE bridge (orchestrator → SSE stream queue) 还没实做**: 当前 `_stream_skeleton` 只 emit turn.started + heartbeat · 真的 emit→stream 桥接还需要 (i) 一个 per-turn `asyncio.Queue` (ii) `_dispatch_via_adapter` 把 adapter 输出 `await queue.put(evt)` (iii) `_stream_skeleton` 改 `await queue.get()` 推 wire · 这是下一棒 + 下下一棒 (test_sse_adapter 集成测试时也需要 fake queue)
- **adapter import smoke check 结果**: 9 文件 import clean · `AgentAdapter` Protocol / `SseV1ToLiuyeAdapter` / `ChannelAdapter` / `CreditAdapter` / `ReportAdapter` / `RiskctrlAdapter` / `AlertAdapter` / `ComplianceAdapter` 全 import OK · agent_id + boundary 字段 verify (3 cowork + 3 managed_readonly)

## 2026-05-12 · checkpoint 4 (workers + ledger_review + 3 test + façade upgrade + wire-up · 第 4 棒 · W1-backend DONE 18/18)

- **完成文件** (18/18 · 含 façade upgrade · 4 wire-up 文件改动):
  - `liuye_service/workers/__init__.py` (24 行 · 空 export · 包级 docstring 写清 outbox_retry 子模块职责 + systemd 部署关系)
  - `liuye_service/workers/outbox_retry.py` (536 行 · `OutboxWorker` class · `from_env()` 从 systemd Environment= 读 4 var + fallback default · `run()` 60s loop + `asyncio.Event` stop signal · `_scan_pass()` glob outbox dir + 调 `process_entry()` per entry · `process_entry(path)`: load envelope → parse JSON / corrupt → dead-letter / 检查 `next_attempt_at` cadence gate / idempotency_key 防重 / dead-letter 检查 (retry > 5 即 graduate) / 调 `record_decision()` / 成功 unlink / 失败 increment retry + reschedule + atomic rewrite · `_is_dead_letter(retry_count) -> bool` (> max_retry 即 dead) · `_backoff_for_retry(n)` 返 60/120/240/480/960s (clamp at last) · `_graduate_to_deadletter()` 移文件 + Sentry alert log (`extra={"sentry.alert": True}`) · CLI entry `python -m liuye_service.workers.outbox_retry` 走 `_main()` + signal handlers (SIGTERM/SIGINT))
  - `liuye_service/ledger_review.py` (294 行 · `record_review_event()` 公共 façade · 新 sqlite 表 `ledger_review_events` 与 `decisions` 同库 (`data/ledger/decisions.sqlite`) · 全 append-only (never mutate decision) · 3 索引: `idx_review_decision` / `idx_review_idempotency` (decision_id, idempotency_key) / `idx_review_reviewer` · idempotency_key 防重 (same (decision_id, idempotency_key) 返已存 row · 走 race 也 fallback existing) · `list_review_events(decision_id)` 列表查 review chain · `_resolve_db_path()` 复用 `default_ledger().db_path` 共表 · `_row_to_event()` rehydrate Pydantic LedgerReviewEvent · 老 `/api/ledger/{id}/review` 标 @deprecated v1 兼容保留)
  - `liuye_service/tests/__init__.py` (24 行 · 包级 docstring 写清 3 test 模块边界 + 跑 cmd `py -m pytest liuye_service/tests/ -v`)
  - `liuye_service/tests/test_contracts.py` (389 行 · 19 test · 11 event enum lock + 8 status enum lock + 5 协议 Pydantic round-trip · `EXPECTED_11_EVENTS` + `EXPECTED_8_STATUSES` 常量锁 · 验 `permission.request` 是 11th 事件 · 验 `streaming` + `aborted` status · 验 Artifact 5-enum type lock 拒 unknown · 验 ToolCall boundary 2-enum lock · 验 LiuyeChatEvent RootModel union 拒 unknown event · 5 fixture 全部 round-trip via `model_dump_json(by_alias=True)` · KBDoc 合成最小 payload 验 5 个枚举字段)
  - `liuye_service/tests/test_sse_adapter.py` (390 行 · 20 test · 7 v1 → 7 liuye event mapping (profile_loaded/stage/stream/tool_call/tool_result/done/error) + heartbeat 透传 · dedup_key `(event::sha256(canonical_json))` 重发 0 emit · percent 边界 0.0/0.42/1.0 → 0/42/100 int + 73 int passthrough · degraded missing 'event' → SSE_ADAPTER_FAILED `fallback_available=true` · unknown event silent skip (forward-compat) · `parent_tool_call_id` Report→Credit handoff passthrough · stage 自动继承最近 tool_call_id context · seq strictly increasing)
  - `liuye_service/tests/test_outbox.py` (421 行 · 20 test · `_is_dead_letter` 边界 (= max_retry 不 dead · > max_retry dead) · 自定义 max_retry · backoff schedule v3 spec lock (60/120/240/480/960) · `_backoff_for_retry` index 1-5 + clamp at last + zero-edge · `_parse_backoff_csv` valid/missing/malformed fallback · `process_entry` 成功 unlink + 验 kwarg forward · 失败 reschedule (retry_count=1 + next_attempt_at + 保 idempotency_key) · dead-letter graduation (retry=5 又失败 → move dead-letter + reason="max_retry_exceeded") · already-max skip attempt 直接 graduate · idempotency_key 同 key 跑 2 次 → 1 ledger 调用 · corrupt JSON 直接 dead-letter · future `next_attempt_at` 跳过本 pass · `run()` loop 收 stop signal 退出 · `from_env` systemd override + 默认 + invalid fallback)
  - `shared/decision_ledger/store.py` (façade upgrade · `record()` method 加 `parent_turn_id: str | None = None` kwarg 转发 LedgerEntry · `record_decision()` façade 同步加 kwarg · INSERT SQL 加 `parent_turn_id` 列 + value · sqlite schema 用现有 ALTER TABLE migration · 端到端 verify 走过 (`record_decision(parent_turn_id='t-001')` → ledger.get(did)['parent_turn_id'] == 't-001'))
  - `shared/decision_ledger/schema.py` (Q3 ratify pre-existing · 已加 `parent_turn_id: str | None = None` 字段到 `LedgerEntry` v1.1 · `LEDGER_SCHEMA_VERSION = "1.1.0"` · 不动 字段 · 同 commit 入库以让 store.py façade 升级生效)
  - `liuye_service/api.py` (wire-up · 自己第 2 棒文件 · 改 6 处: (i) import `list_review_events` / `record_review_event` / `register_default_adapters` (ii) `register_liuye_routes` 内 idempotent 绑 6 adapter (`register_default_adapters(orch)` · 已注册 channel/credit/report 时跳过) (iii) `_default_review_writer` closure 走 `record_review_event` · 注入 grant/deny `review_writer=_default_review_writer` (iv) append_review_event POST 端点真正调 `record_review_event` 不再返 `persisted=False` stub · 验 ValueError → 400 / RuntimeError → 500 (v) GET decision endpoint 加 `review_chain` from `list_review_events()` (vi) `_dispatch_via_adapter` 真桥接 emit → 走 `orchestrator.get_or_create_sse_queue(turn_id)` `queue.put(evt)` · finally 推 None sentinel `_stream_skeleton` 改 race `queue.get()` vs `wait_for(timeout=HEARTBEAT_INTERVAL_SECONDS)` · `evt is None` → break · finally `orchestrator.close_sse_queue(turn_id)`)
  - `liuye_service/orchestrator.py` (wire-up · 自己第 2 棒文件 · 改 5 处: (i) `_sse_queues: dict[str, asyncio.Queue]` per-turn bounded (maxsize=256) (ii) `get_or_create_sse_queue(turn_id, maxsize=256)` lazy create · `close_sse_queue(turn_id)` 推 None sentinel + pop (iii) `abort_turn` 同步调 `close_sse_queue` clean exit (iv) `dispatch_message` detect 2 adapter surface · `hasattr(adapter, 'dispatch_message') and not hasattr(adapter, 'dispatch')` 走 AsyncIterator + forward emit · 否则 fallback 老 `dispatch(emit=...)` callable surface · 异常 → `abort_turn(code='ADAPTER_DISPATCH_FAILED')` (v) `register_default_adapters(orch=None)` 函数 lazy import 6 adapter class + bind · 失败 silent log)
  - `liuye_service/audit.py` (façade upgrade clean-up · 改 2 处: (i) 删 `evidence_chain._meta.parent_turn_id` hack · 改走 `_record_decision(parent_turn_id=parent_turn_id)` 真 kwarg forward (ii) 失败 outbox enqueue payload 加 `idempotency_key=fallback_id` 防 retry worker 重复跑同 decision_id)
- **关键决策** (skeleton 取舍):
  - **façade upgrade 同 commit · 不另开 PR**: 上一棒 hidden gotcha 标 `shared.decision_ledger.record_decision` 不暴露 `parent_turn_id` kwarg · 本棒 ledger_review.py 直接需要 schema field 与 façade kwarg · 同 commit 加 store.py façade kwarg + 把 schema.py 一起入库 (schema.py Q3 ratify 已在 working tree · 是 store.py façade 的依赖 · 不入库会让 LedgerEntry(parent_turn_id=...) 抛 TypeError)
  - **audit.py 改走真 kwarg · 删 evidence_chain._meta hack**: 之前用 `evidence_chain._meta.parent_turn_id` 是临时绕过 · 现在 façade 升级后改走真 kwarg · sqlite `decisions.parent_turn_id` 列直接写 · queryable via `idx_parent_turn` 索引 · `evidence_chain` 不再被污染
  - **ledger_review_events 新 sqlite 表 · 与 decisions 同库**: 不另开 sqlite 文件 · 复用 `data/ledger/decisions.sqlite` · ops 备份单一 db 文件 · 通过 `default_ledger().db_path` resolve · 任何 ENV `LIUYE_LEDGER_DB_PATH` override 自动一致 · review_chain 与 decision row 始终同库可 join · `_ensure_schema` 用 module-level set 防重复初始化
  - **idempotency_key dedup 走 (decision_id, idempotency_key) 复合键 · 不走 PRIMARY KEY**: event_id 是 uuid4 primary key · idempotency_key 是逻辑 dedup key · `idx_review_idempotency` 索引 + SELECT before INSERT · INSERT race 时 fallback existing row · 返同样的 Pydantic model · REST endpoint 收到的总是 idempotent
  - **OutboxWorker `_is_dead_letter(retry_count) > max_retry`**: 严格大于 · `retry_count == max_retry` 仍 alive 给最后一次机会 · 第 6 次 (retry=6 > 5) 才 graduate · 严格 v3 §5.x verbatim (5 次 retry · 第 6 次失败转 dead-letter)
  - **OutboxWorker idempotency_key 仅 in-process · 不持久化**: 跨进程重启 outbox 文件还在 · retry_count 持久化在 envelope · idempotency_key in-process 只防同 worker 同 run 内重复 · 重启后从 retry_count 继续 (不丢精度)
  - **adapter dispatch 2 surface 兼容**: 已有 `AgentAdapter` Protocol (adapters/base.py) 是 AsyncIterator surface · 老 `CoworkAdapter` Protocol (orchestrator.py) 是 emit-callback surface · `dispatch_message()` 检 `hasattr(adapter, 'dispatch_message') and not hasattr(adapter, 'dispatch')` 走新走老 · 兼容 stub adapter + 测试 mock
  - **SSE queue maxsize=256 + put backpressure**: 客户端断连后 adapter 继续 emit 不会 OOM · `asyncio.Queue.put` 在 full 时 await · 推不动就停 (adapter 反向卡住 · acceptable behavior · timeout / abort 自动清队列)
- **blocker** (or "无"):
  - 无
- **pytest run 结果**: 59 PASS / 0 FAIL
  - `test_contracts.py` 19 PASS · `test_sse_adapter.py` 20 PASS · `test_outbox.py` 20 PASS
- **façade upgrade end-to-end smoke**: `py -c "from shared.decision_ledger import record_decision; record_decision(..., parent_turn_id='t-001')"` → `ledger.get(did)['parent_turn_id'] == 't-001'` ✅
- **hidden gotcha** (后续 codex review 关注):
  - **60s loop 测试用 asyncio.Event + tight loop interval**: 不能用 `mock time.time()` 因为 `asyncio.wait_for(self._stopping.wait(), timeout=...)` 内部走 event loop 自己时钟 · 用 `scan_interval_sec=0.01` + `asyncio.create_task(_stop_soon)` 0.02s 后调 worker.stop() · 真生产 60s 测试用 systemd 自身重启 + journalctl
  - **ledger sqlite ALTER TABLE 多次跑 silent-skip**: schema.py `_SCHEMA_MIGRATIONS` 在 `_init_schema` 跑 · sqlite `OperationalError` (duplicate column name) 被 catch · 多次启动 worker / 测试 fresh db 都 OK · 但 deploy/liuye-outbox.service 起子进程时同样 `DecisionLedger.__init__` 会触发一次 migration · 不影响主进程
  - **API auth_service Depends 顺序**: `register_liuye_routes` 内 `Depends(require_user)` 是 per-endpoint 不是 router-wide · health 端点未加 auth 是 anonymous probe path · permissions/grant 端点的 user.get("role", "") 走 stub 时是 "rm" 默认 (auth_service 缺时 fallback · pragma no cover)
  - **orchestrator asyncio.Queue per-turn 生命周期**: queue 在 `get_or_create_sse_queue` 第一次访问时建 · `close_sse_queue` 在 (a) `abort_turn` (b) SSE stream `finally` (c) `_dispatch_via_adapter` finally None sentinel · 3 路径任一关闭 · 客户端断连 -> SSE generator cancelled -> finally close · adapter 还在跑 -> queue.put 阻塞 -> 反压 (acceptable)
  - **httpx async streaming + queue 异步桥**: `_dispatch_via_adapter` `async for evt in adapter.dispatch_message(...)` 是 `AsyncIterator` · 内部 `await queue.put(evt)` 不会触发 backpressure 死锁 (queue maxsize=256 大于通常单 turn event 数 < 50)
  - **review_writer 失败 silent-fail 不阻 grant/deny**: `_default_review_writer` 返 bool · `grant`/`deny` 内 `await review_writer(...)` 不检查返值 · ledger 写失败时 silent log + 继续 · audit chain 不破 (per BE7 hard line)
- **ELAPSED min**: ~42 (含 8 件 read + 10 文件 write/edit + façade upgrade + pytest 跑 + progress append)
- **commit SHA**: (本 commit 落地后填)
- **SSE v1→liuye mapping smoke 结果** (verify 7+1 v1 → 7+1 liuye 直接映射):
  - `v1.profile_loaded` → `liuye.turn.started` seq=1 ✅
  - `v1.tool_call`      → `liuye.tool.started` seq=2 ✅
  - `v1.stage`          → `liuye.tool.progress` seq=3 ✅
  - `v1.stream`         → `liuye.message.created` seq=4 ✅
  - `v1.tool_result`    → `liuye.tool.completed` seq=5 ✅
  - `v1.done`           → `liuye.turn.completed` seq=6 ✅
  - `v1.error`          → `liuye.turn.error` seq=7 ✅
  - `v1.heartbeat`      → `liuye.heartbeat` seq=8 ✅
  - dedup: 同 v1 event 再 translate 0 emit (1st=1 / 2nd=0) ✅
  - percent: v1 progress=0.42 → liuye percent=42 (int) ✅
  - degraded: missing `event` field → `turn.error code=SSE_ADAPTER_FAILED fallback_available=true` ✅
- **demo fixture replay smoke 结果** (LIUYE_DEMO_MODE=1):
  - ChannelAdapter 用 `channel_5candidates.json` fixture · emit 7 liuye event (turn.started → tool.started → 3 tool.progress → tool.completed → turn.completed) ✅
  - CreditAdapter 用 `credit_decision_PASS.json` fixture · emit 8 liuye event (turn.started → tool.started → 4 tool.progress → tool.completed → turn.completed) ✅
  - ReportAdapter 用 `report_v16_PARTIAL.json` fixture (W1-mock-test worker 已 ship · 不是缺失) · emit 5-stage v16 序列 ✅
- **SSE 7→11 mapping 一致性 verify** (与 matrix §4 + v3 附录 A.1):
  - 7 老 v1 event 全部覆盖 (profile_loaded / stage / stream / tool_call / tool_result / done / error) ✅
  - heartbeat v1→liuye 透传 (matrix §4 表行) ✅
  - 3 新 liuye event 明确不在 adapter scope: `artifact.patch` / `evidence.attached` 由 BFF 监听 mutate 直接 emit · `permission.request` 由 `permissions.py::emit_permission_request` 直接 emit (PM 2026-05-11 Q2 ratify · matrix §3 Q3 verbatim · 与 §4.1 表 11th event 行一致)
- **ELAPSED min**: ~38 (含 7 件 read + 9 文件 write + 4 smoke test 类型 + progress append)
- **commit SHA**: 041d645
