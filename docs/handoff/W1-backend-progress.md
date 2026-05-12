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
- **commit SHA**: <填写于 commit 后>
