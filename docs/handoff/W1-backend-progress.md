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
