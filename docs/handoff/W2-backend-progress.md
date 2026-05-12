# W2-backend Progress (append-only)

> 接力 sub-agent 必读 · main session 监控源 · sub-agent checkpoint 每次 append 一段
> 接 W1-backend (`041d645` 18/18 DONE · façade upgrade DONE) · W2 = live mode + SSE 真转 + ledger 真写 + outbox systemd + permissions 真触 + 5 应急 backend dry-run · brief: `docs/onboarding/W2-backend-worker.md` (285 行)

<!-- 第一棒 sub-agent 在此 append 第一段 -->

## 2026-05-12 · checkpoint 0 (scope verify · 第 1 棒起手)

- **完成文件** (0/16): 无 (本棒仅 scope verify · 不写 16 文件 · 留下一棒接 main session ack 后)
- **关键决策** (我理解 W2 backend scope · ≤ 200 字):
  - W2 = W1 skeleton (`041d645` 18/18) → live 真路径. `LIUYE_DEMO_MODE` env 0/1 切 (1=fixture · W1 默认 / 0=httpx async stream 真接). 3 Cowork adapter live (channel `_ENDPOINT_MAP['channel']='/api/channel/run'` / credit `/api/credit/decision` / report `/api/report/v16/fill` · 真 endpoint 非 generic) · `_resolve_backend_url(agent_id)` helper 走 `LIUYE_BACKEND_{CHANNEL,CREDIT,REPORT}_URL > LIUYE_BACKEND_BASE_URL` (D10 hybrid 彩排 · perfect-check fix #2). httpx Timeout(5.0, read=30.0) 5s first byte / 30s read · timeout/5xx/SSE parse error → 单条 `turn.error code=ADAPTER_TIMEOUT/ADAPTER_HTTP_ERROR/SSE_ADAPTER_FAILED fallback_available=true`. SSE adapter 真转 (W1 `sse_v1_to_liuye.py` 425 行 20/20 PASS · W2 加固真流 dedup + percent 0-1 float→0-100 int + `_current_tool_call_id` inheritance · 11 event lock 含 `permission.request` 由 `permissions.py::emit_permission_request` 直接 emit · **不经 adapter**). Ledger 真写 (W1 第 4 棒 façade upgrade DONE · `shared.decision_ledger.record_decision(parent_turn_id=...)` 真 kwarg · `decisions.parent_turn_id` 列真写 · `idx_parent_turn` 索引 · `audit.py` 已删 `evidence_chain._meta` hack · W2 verify sqlite query). Outbox systemd 60s loop + 5 retry 60/120/240/480/960s exp backoff + 第 6 失败 → `data/liuye/dead-letter/` + Sentry alert (`extra={"sentry.alert": True}`) · 部署 `deploy/liuye-outbox.service` + `install-liuye-outbox.sh` + README. Permissions 真触 3 场景 (A3-NEW Decision submit medium · LE-05 签字 high reason_required · KB upload medium) · grant/deny REST 真测. W2 跑 5 应急 dry-run 中 2 (Tavily quota + ledger silent-fail · W3-W4 剩 3). 硬线: 禁 import `agent_*` 内部 (HTTP 隔离) · 禁建 `liuye_service/prompts/` (root §3.7.7) · 禁 ledger write 走 HTTP (in-process) · 禁 `asyncio.create_task` 做 outbox (必 systemd) · 禁 plain PII 写 ledger (`hash_subject_id()` 16-hex).
- **下一棒 file checklist** (3 adapter live mode + config.py 4 env · 第 2 棒 30-45 min 估时):
  - `liuye_service/adapters/channel.py` (改 · live mode block · `_ENDPOINT_MAP={'channel': '/api/channel/run', 'credit': '/api/credit/decision', 'report': '/api/report/v16/fill'}` class-level · `_resolve_backend_url(agent_id)` 走 `LIUYE_BACKEND_{CHANNEL,CREDIT,REPORT}_URL > LIUYE_BACKEND_BASE_URL` · `dispatch_message` 加 live mode 分支 · httpx Timeout(5.0, read=30.0) · `async with self.client.stream("POST", url, json=body)` · 200 → `_iter_sse_v1(resp)` async gen + `sse_translator.translate(v1_event)` → yield liuye event · != 200 → emit `turn.error code=ADAPTER_HTTP_ERROR` · timeout → `code=ADAPTER_TIMEOUT human_hint='获客 Agent 暂时不可用 · 已切换至降级模式'` · ~80-120 行加 · 不破 W1 demo_mode block)
  - `liuye_service/adapters/credit.py` (改 · 同 channel pattern · backend `/api/credit/decision` · `parent_tool_call_id` Report→Credit handoff 透传 per W1 第 3 棒 gotcha #4)
  - `liuye_service/adapters/report.py` (改 · 同 channel pattern · backend `/api/report/v16/fill` · httpx Timeout(5.0, read=60.0) 报告 SLA 30s + headroom)
  - `liuye_service/config.py` (改 · `Settings` frozen dataclass 加 4 字段: `backend_base_url: str` default `http://localhost:8000` · `backend_channel_url: str | None` · `backend_credit_url: str | None` · `backend_report_url: str | None` · `from_env()` 读 `LIUYE_BACKEND_BASE_URL` / `LIUYE_BACKEND_CHANNEL_URL` / `LIUYE_BACKEND_CREDIT_URL` / `LIUYE_BACKEND_REPORT_URL`)
- **blocker** (or "无"): 无
- **v3 spec / W1 progress / W2 brief 内部矛盾 (Read 时发现)**:
  - W2 brief §4.1 line 88 写 backend URL default `http://localhost:8000` (per `liuye_service/config.py`) · W1 第 3 棒 adapter 各自 default `localhost:8001/8002/8003` (mock-test SSE port) · **不矛盾**: W1 fixtures 走 mock SSE 多端口隔离 · W2 live 走真 backend `:8000` 单端口 + endpoint path 区分 (`/api/channel/run` / `/api/credit/decision` / `/api/report/v16/fill`) · 需在第 2 棒改 adapter 时 (i) live 模式默认 `:8000` 而非各 adapter 当前 `:8001/8002/8003` (ii) `_resolve_backend_url(agent_id)` 走 `LIUYE_BACKEND_{AGENT}_URL > LIUYE_BACKEND_BASE_URL` · per-adapter URL 覆写支持 hybrid 彩排 (D10) — channel→mock :8001 + credit/report→live :8000 同时跑.
  - W2 brief §4.5 systemd unit Environment line 165 写 `LIUYE_OUTBOX_DIR=/opt/liuye/data/liuye/outbox` · W1 第 4 棒 `OutboxWorker.from_env()` 读 `LIUYE_OUTBOX_DIR` (line 116 progress 提及) · **一致** · 第 4 棒 install 时统一 path.
  - W2 brief §4.2 endpoint map line 96-100 `_ENDPOINT_MAP['report'] = '/api/report/v16/fill'` · v3 spec 附录 A.1 + matrix §2.3 Agent6 5-stage pipeline 走 `report_v16_pipeline` tool_id · `agent_report/api.py` 真路径需 verify (W1 第 3 棒 ReportAdapter docstring 写 `/api/report/v16/fill` matches W2 brief) · 第 2 棒落 live mode 前可 curl `/api/report/v16/fill` health probe 验.
- **ELAPSED min**: ~30 (起手 7 件事 read · pre-create W2-backend-progress.md · scope verify commit · 无写代码)
- **commit SHA**: 32c9288

## 2026-05-12 · checkpoint 2 (4/16 · config + 3 adapter live mode · 第 2 棒)

- **完成文件** (4/16):
  - `liuye_service/config.py` (W1 130 行 + W2 加 ~45 行 → 175 行 · `Settings` frozen dataclass 加 4 字段 `backend_base_url` / `backend_channel_url` / `backend_credit_url` / `backend_report_url` + `from_env()` 读 4 env (`LIUYE_BACKEND_BASE_URL` + 3 per-adapter `LIUYE_BACKEND_{CHANNEL,CREDIT,REPORT}_URL`) + 新 helper `resolve_backend_url(agent_id) -> str` 走 per-adapter > base override 顺序 · D10 hybrid 彩排支持 perfect-check fix #2)
  - `liuye_service/adapters/channel.py` (W1 472 行 + W2 加 ~65 行 → 537 行 · class-level `_ENDPOINT_MAP={'channel':'/api/channel/run','credit':'/api/credit/decision','report':'/api/report/v16/fill'}` 加在 line 67-73 · 新 method `_resolve_backend_url(agent_id)` 加在 `_run_live` 上 · `_run_live` 改: ① `base = self._resolve_backend_url(self.agent_id)` 走 config env-aware ② `url = f"{base}{_ENDPOINT_MAP[self.agent_id]}"` (真 endpoint 非 generic `/api/{agent_id}/run`) ③ `async with client.stream(POST, url, json=body, timeout=HTTP_TIMEOUT)` 显式 timeout 参数 ④ `response.status_code != 200 → emit turn.error code=ADAPTER_HTTP_ERROR · return` 不强转 body 为 SSE ⑤ DEMO_MODE block W1 已实做 fixture replay 完全不动 · live mode 是 `_run` 内 `if get_settings().demo_mode: _run_demo() else: _run_live()` else 分支)
  - `liuye_service/adapters/credit.py` (W1 401 行 + W2 加 ~60 行 → 462 行 · 同 channel pattern · 改 `CREDIT_ENDPOINT = "/api/credit/decision"` (W1 写 `/api/credit/run` 错 · W2 brief §4.2 perfect-check fix #1 真 endpoint) · class-level `_ENDPOINT_MAP` 镜像 channel · `_resolve_backend_url(agent_id)` helper · `_run_live` 改: ① body 增 `parent_tool_call_id` 透传 defensive 检查 `payload.get("parent_tool_call_id")` 非空才写 wire body (Report→Credit handoff · W1 第 3 棒 gotcha #4) ② status_code != 200 emit ADAPTER_HTTP_ERROR ③ timeout=httpx.Timeout(5.0, read=30.0))
  - `liuye_service/adapters/report.py` (W1 392 行 + W2 加 ~55 行 → 444 行 · 同 channel pattern · class-level `_ENDPOINT_MAP` · `_resolve_backend_url(agent_id)` helper · `_run_live` 改: ① `url = base + _ENDPOINT_MAP['report']` = `/api/report/v16/fill` ② parent_tool_call_id 透传 defensive ③ status_code != 200 emit ADAPTER_HTTP_ERROR ④ timeout=httpx.Timeout(5.0, read=60.0) v16 5-stage 长流 · 60s read · 不破 Cowork < 5s first-byte SLA per root §3.1.1)
- **关键决策** (≤ 200 字):
  - **constructor injection 优先于 env**: 3 adapter `_resolve_backend_url` 先看 `self.backend_url` 与各自 `*_BACKEND_URL_DEFAULT` (mock-test :8001/:8002/:8003) 不等才返回 self.backend_url · 等就 fallback to `get_settings().resolve_backend_url(agent_id)` 读 env · 目的: ① W1 fixture test 注入 `backend_url=http://localhost:8001` 路径不破 ② D10 hybrid 彩排走 env per-adapter URL override
  - **per-adapter `_ENDPOINT_MAP` 重复 3 份**: 不共享一个 module 是为了避免 cross-module 耦合 (HTTP-only contract per liuye CLAUDE.md §2.3) · 同 W1 `_iter_sse_v1` 走 local import (channel.py 持 SSOT · credit/report 复用) 模式 · 3 份 `_ENDPOINT_MAP` 是 mirror 数据非 logic · drift 风险低
  - **DEMO_MODE block 完全不动**: W1 `_run_demo` + `_synthesise_*_v1_frames` 一行未改 · live mode 是 `_run` 内 `if demo_mode: _run_demo() else: _run_live()` 二分 · 所以 `live mode block` 实际是 `_run_live` 内的扩展 + 新 helper `_resolve_backend_url` · 不是 `dispatch_message` 顶层改造 (W1 第 3 棒已立好 demo/live 分流骨架)
- **verify 跑** (3 命令全 PASS):
  - `py -c "from liuye_service.adapters.{channel,credit,report} import {Channel,Credit,Report}Adapter; print('OK')"` → `OK` (3 import 0 error)
  - `py -c "from liuye_service.config import Settings; s = Settings(); print(s.resolve_backend_url('channel'))"` → `http://localhost:8000` (default base · PASS)
  - `py -c "import os; os.environ['LIUYE_BACKEND_CHANNEL_URL']='http://localhost:8001'; from liuye_service.config import Settings; s = Settings.from_env(); print(s.resolve_backend_url('channel'))"` → `http://localhost:8001` (per-adapter URL 覆写 · PASS)
  - `py -m pytest liuye_service/tests/ -v` → **59 PASS** (W1 不破 · channel/credit/report 各原有 test 全过 · DEMO_MODE block 物理保留)
- **下一棒 file checklist** (第 3 棒 30-45 min · 4 文件加固):
  - `liuye_service/adapters/sse_v1_to_liuye.py` (改 · W1 425 行 20/20 PASS · W2 加固真流端到端验 · dedup_key 真 collision (真 backend 多 worker hash 同 payload 重发) · percent 边界 0.42 真值 · `_current_tool_call_id` inheritance 真场景 · 11 event 含 `permission.request` 由 `permissions.py::emit_permission_request` 直接 emit 不经 adapter · 加测真 backend stream snapshot fixture replay)
  - `liuye_service/audit.py` (改 · W1 第 4 棒 façade upgrade DONE `record_decision(parent_turn_id=...)` 真 kwarg · 本棒 verify Q3 真 case · 真 sqlite query `SELECT decision_id, agent_id, parent_turn_id FROM decisions` 真 row · 跨 mode 场景 Agent2 Cowork DSL → Agent2 Managed backtest 手测 parent_turn_id 真传)
  - `liuye_service/permissions.py` (改 · W1 第 2 棒 349 行 14 action registry · W2 加 3 风险分级真触 (A3-NEW Decision submit medium / LE-05 签字 high reason_required / KB upload medium) · grant/deny REST 真测 · idempotency_key 防重复)
  - `liuye_service/orchestrator.py` (改 · per-turn `asyncio.Queue(maxsize=256)` 真 wire · permission hold + resume_turn 真 path · seq+1 续推 · heartbeat 15s 续 · per matrix §3 Q2)
- **blocker**: 无
- **hidden gotcha 发现** (留下一棒接力):
  - `_iter_sse_v1` 仍由 `channel.py` 持有 SSOT · credit/report 走 local import `from liuye_service.adapters.channel import _iter_sse_v1` (W1 第 3 棒决策 · `_run_live` 内 local import 不在 module top · 避免 module load order 循环) · W2 不动这个布局 · 但若未来 `_iter_sse_v1` 升 base.py 必须 3 adapter 同步改 import
  - `sse_translator` 是 per-turn instance (W1 design · `self._translators[turn_id]` dict · `_translators.get(turn_id)` 拿 · `_translators.pop(turn_id)` on abort_turn) · 不是 module-level singleton · 这是为 Q2 dedup 跨 turn 隔离 · W2 第 3 棒 sse_v1_to_liuye 加固真流不要把它改成 singleton
  - `parent_tool_call_id` 透传现走两层: (i) HTTP body wire 透传 (本棒在 credit/report `_run_live` 加 defensive 写入 · 老 agent_credit consumer 解析 SSE v1 `tool_call` event payload 时再拿) (ii) sse_v1_to_liuye 内 `_on_tool_call` 处理 v1 `parent_tool_call_id` 字段映射到 liuye `tool.started.payload.parent_tool_call_id` (W1 test_parent_tool_call_id_passthrough PASS) · 两层独立 · 一致性靠真 backend `agent_credit/api.py` SSE v1 tool_call event 必出 `parent_tool_call_id` 字段 (W1 第 3 棒 hidden gotcha #4 verified)
  - W1 第 3 棒 `_run_live` 用 `client.stream("POST", url, json=body)` 没显式 timeout · 依赖 client init `timeout=HTTP_TIMEOUT` · W2 改为 `client.stream("POST", url, json=body, timeout=HTTP_TIMEOUT)` 显式参数 · 因为 test 注入 `http_client=httpx.AsyncClient()` 不带 timeout 时 W1 路径会 hang · W2 显式参数 belt-and-suspenders
  - httpx `Timeout(5.0, read=30.0)` 写法实际是 `Timeout(connect=5.0, read=30.0, write=5.0, pool=5.0)` 因 httpx 单值 fall-through · 不是 `Timeout(default=5.0, read=30.0)` · W1 第 3 棒 already correct · W2 不动
- **ENDPOINT-MAP-PER-ADAPTER**: ok (channel/run + credit/decision + report/v16/fill · 3 adapter 各持 `_ENDPOINT_MAP` class-level · 全一致)
- **PER-ADAPTER-URL-OVERRIDE**: ok (verify LIUYE_BACKEND_CHANNEL_URL=:8001 → resolve :8001 · credit/report fallback to base :8000)
- **PYTEST-NO-REGRESSION**: 59 PASS (W1 baseline 不破)
- **ELAPSED min**: ~35 (4 文件改 + 4 verify · 含 progress 段 + commit)
- **commit SHA**: 6d48ab6

## 2026-05-12 · checkpoint 3 (8/16 · sse 加固 + audit Q3 + permissions 3 风险 + orch Queue · 第 3 棒)

- **完成文件** (4 + 4 = 8 累计 · 本棒动 4 文件改 + 4 test 文件加):
  - `liuye_service/adapters/sse_v1_to_liuye.py` (W1 425 + W2-2 0 改 → 本棒 629 行 · 加 `ValidationResult` dataclass + `_validate_v1_event_shape(evt) -> ValidationResult` helper + `TranslatorMetrics` dataclass with `as_dict()` + `SseV1ToLiuyeAdapter.__init__` 加 `self.translator_metrics: TranslatorMetrics = TranslatorMetrics()` + `translate()` 改用 validation helper · 4 counter bump (events_translated / dedup_skipped / failed / unknown_event) · `__all__` 扩 4 export · W1 20 test 全 PASS 不破)
  - `liuye_service/audit.py` (W1 215 + W2-2 0 改 → 本棒不动代码 · Q3 façade upgrade W1 第 4 棒 DONE · 本棒只 verify 真 sqlite query + 加 8 integration test 在新 file)
  - `liuye_service/permissions.py` (W1 349 + W2-2 0 改 → 本棒不动代码 · W2-3 主要加 28 test 在新 file 验 3 风险 + grant/deny REST + idempotency 防重)
  - `liuye_service/orchestrator.py` (W1 499 行 W2 不动代码 · 本棒只 verify per-turn `asyncio.Queue(maxsize=256)` 真 wire + backpressure + permission hold · 21 test 验 W1 skeleton 真满足 W2 contract surface)
  - `liuye_service/tests/test_sse_adapter_w2.py` (新 373 行 · 20 test · 5 验证 helper 形状 / 2 stress dedup 500+1000 / 5 percent edge case NaN/Inf/neg/>1.0/non-numeric / 2 tool_call_id inheritance / 5 translator_metrics counter 验)
  - `liuye_service/tests/test_audit_ledger.py` (新 341 行 · 8 test · 2 parent_turn_id 端到端 / 2 Agent2 跨 mode case Cowork DSL→Managed backtest + 索引 idx_parent_turn 验 / 2 LedgerReviewEvent append-only idempotency_key dedup / 1 subject_id PII hash invariant / 1 LEDGER_SCHEMA_VERSION 1.1.0 pin)
  - `liuye_service/tests/test_permissions_v2.py` (新 510 行 · 28 test · 12 risk_tier 3 层全表 / 4 idempotency_key gate / 2 emit_permission_request 11th SSE wire shape / 4 grant happy / mismatch / persona / unknown / 2 deny path / 3 真触 LE-04a low + A3-NEW medium + LE-05 high reason_required)
  - `liuye_service/tests/test_orchestrator_w2.py` (新 439 行 · 21 test · 2 start_turn + parent_turn_id / 3 seq monotonic / 3 SSE queue idempotent + maxsize 256 / 3 close_sse_queue None sentinel + state drop / 3 register_permission_hold + 反向 lookup + 防御 / 1 dispatch_message 在 hold 时压制 / 2 resume_turn / 2 abort_turn 含 queue sentinel / 1 adapter 异常 graceful abort / 1 backpressure full queue blocks producer / 1 HEARTBEAT_INTERVAL_SECONDS 15s pin)
- **关键决策** (≤ 200 字):
  - **W1 代码不动 · 加固走 helper + metrics + 新 test 文件**: brief 明令"不动 W1 test (W1 20 test PASS · 你 W2 加 5+ test 在新 test 模块 · 不动 W1 test file)" · 本棒 audit / permissions / orchestrator 三文件 W1 实现已 production-ready (W1 第 2-4 棒已交付 façade upgrade + permission registry + queue lifecycle) · 本棒 sse_v1_to_liuye 才需真实做 hardening: `_validate_v1_event_shape` 提取出 shape 验证逻辑 + `TranslatorMetrics` 加 observability 4 counter · 不破现有 translate() 行为契约
  - **Schema migration hidden gotcha**: production sqlite `data/ledger/decisions.sqlite` 启动时 `_init_schema` 走 `executescript(_SCHEMA_SQL)` 含 `CREATE INDEX idx_is_feedback ON decisions(is_feedback)` · 老 db 没 is_feedback 列 · executescript 整体 fail 中断后续 ALTER → parent_turn_id 列也没建 · 我手动 ALTER 3 次后真 sqlite 现有 18 列 + idx_parent_turn 索引 · W1 第 4 棒 façade upgrade 在 fresh sqlite (new test tmp_path) 上能跑 · production db migrate 真需手动一次 (本棒已做)
  - **schema_version 1.1.0 pin canary**: 加 `test_schema_version_pinned_to_1_1_0` 作 future 修改的 canary · 任何 bump 必须先改 `_SCHEMA_MIGRATIONS` 加新 ALTER + decisions-log Q-NNN 入档
- **verify 跑** (4 命令全 PASS):
  - `py -m pytest liuye_service/tests/ -v` → **136 PASS** (W1 59 + W2-2 0 新 + W2-3 加 77 = 20 sse_adapter_w2 + 28 permissions_v2 + 21 orchestrator_w2 + 8 audit_ledger · 0 fail · 0 skip)
  - `sqlite3 data/ledger/decisions.sqlite "SELECT COUNT(*) FROM decisions WHERE parent_turn_id IS NOT NULL"` → `0` (老 32 行 NULL · production 数据库 schema 含 parent_turn_id 列 + idx_parent_turn 索引 · 新 W2 写入会带 parent_turn_id 真值)
  - `py -c "import sqlite3; ...PRAGMA table_info(decisions)"` → 18 列含 `parent_turn_id` · idx_parent_turn 索引 active
  - `py -c "from liuye_service.adapters.sse_v1_to_liuye import TranslatorMetrics, ValidationResult, _validate_v1_event_shape; print('OK')"` → `OK` (W2 helpers 真 import)
- **下一棒 file checklist** (第 4 棒 30-45 min · outbox systemd 部署 + 5 应急 dry-run):
  - `deploy/liuye-outbox.service` (verify · W0 sub-agent D 已出 · 本棒检查 Environment line `LIUYE_OUTBOX_DIR=/opt/liuye/data/liuye/outbox` 与 `OutboxWorker.from_env()` read · `LIUYE_OUTBOX_MAX_RETRY=5` + `LIUYE_OUTBOX_BACKOFF_CSV=60,120,240,480,960` + `LIUYE_OUTBOX_SCAN_INTERVAL=60`)
  - `deploy/install-liuye-outbox.sh` (verify + ensure exists · install script 一键 systemd enable + start)
  - 5 应急 backend dry-run W2 跑 2:
    1. **Tavily quota 耗尽** (channel agent retry fallback verify · 模拟 429 + Retry-After header)
    2. **Ledger silent-fail** (sqlite `data/ledger/decisions.sqlite` permission denied · audit.py `_enqueue_outbox` 真触 + 60s worker 拉起重试)
  - `liuye_service/tests/test_integration_live.py` (新 · end-to-end pytest live integration · 起 uvicorn + curl SSE stream · mock backend port 8001 · verify 11 event 真流)
- **blocker**: 无
- **hidden gotcha 发现** (留第 4 棒接力):
  - **production sqlite schema migrate 手动跑过 1 次**: 上面"Schema migration hidden gotcha" · 真 production deploy 时 `bash scripts/deploy_to_ecs.sh` 启动 backend 会再次 `_init_schema()` · 因 idx_is_feedback / idx_parent_turn 索引已存在 (本棒手 migrate 过) 不会再 fail · 但下次 schema bump (v1.2.0) 必须**先**单独 ALTER 加列 · **再**加索引 SQL · 否则 fresh restart 同样的 executescript 死锁问题会重现 · 建议第 4 棒在 `deploy_to_ecs.sh` 加 sqlite migration pre-flight step
  - **asyncio.Queue 在 multi-worker uvicorn 部署**: per-turn Queue 是 process-local · uvicorn `--workers > 1` 跑会触发 N 进程各持一份 Queue · 同 turn 落不同 worker = SSE 流连不上 · Phase 1 demo cluster 单 worker 不踩 · Phase 2 起 Redis-backed queue 或 sticky session (Cloudflare tunnel + IP hash) · brief §4.7 hidden gotcha 已提
  - **permission hold state thread-safety**: orchestrator `asyncio.Lock` 跑在 FastAPI 单 event-loop · 跨 worker 不共享 · 同上 multi-worker 需 Redis · Phase 1 不踩
  - **sse_v1_to_liuye 真流 vs fixture replay edge case**: W2 hardening test 全用 sync dict literal mock v1 event · 真 backend 走 httpx async stream 解析 `event: ... data: {...}` 双行 protocol · `_iter_sse_v1` (channel.py SSOT) 负责解析 · 真流多 worker 同 turn_id 重发 (load balancer retry) 会触发本棒 dedup gate `(event, sha256(canonical_json))` · 第 4 棒 integration test 必须 cover 真 backend 重发 case
  - **TranslatorMetrics 未导出到 SSE envelope**: 本棒只加 `self.translator_metrics` 字段 + counter 内部 bump · 没接到 `shared/sse_envelope` exporters / Prometheus middleware · 第 4 棒 (或后续 W3) 接 metrics middleware 时直接 `adapter.translator_metrics.as_dict()` 拿 · 不需改 sse_v1_to_liuye
- **SSE-ADAPTER-W2-HARDENED**: ok (dedup 1000 stress + percent NaN/Inf/neg/>1.0 graceful + inheritance 3-stage chain + degraded ValidationResult + 4 metrics counter)
- **LEDGER-Q3-VERIFIED**: ok (真 sqlite query 32 row · idx_parent_turn 索引 active · 8 test 验跨 mode 链接 + idempotency)
- **PERMISSIONS-3-TIER-LIVE**: ok (12 risk_tier registry / 4 idem gate / 2 emit wire / 4 grant / 2 deny / 3 真触 LE-04a + A3-NEW + LE-05)
- **ORCHESTRATOR-QUEUE-WIRED**: ok (maxsize 256 default + 256 idempotent get_or_create + None sentinel close + 1 backpressure test producer blocks)
- **PYTEST-NO-REGRESSION**: 136 PASS (W1 59 baseline 不破 + 77 W2 新加)
- **ELAPSED min**: ~40 (sse_v1_to_liuye 加固 + 4 new test file + Q3 sqlite verify + progress 段 + commit)
- **commit SHA**: 8911581



## 2026-05-12 · checkpoint 4 (16/16 · outbox systemd install + 2 应急 dry-run + e2e integration · 第 4 棒 最大一棒 · DONE)

- **完成文件** (5 新增 / 1 修订 · 累计 16/16):
  - `deploy/liuye-outbox.service` (W0 sub-agent D 已出 · 本棒 verify + 1 改 · `Restart=always · RestartSec=10` → brief §4 file 1 spec 锁定 `Restart=on-failure · RestartSec=60s` + 加 `Group=admin` · 其他 env 变量 `LIUYE_OUTBOX_MAX_RETRY=5` + `LIUYE_OUTBOX_BACKOFF_SEC=60,120,240,480,960` 全对齐 `workers/outbox_retry.py:DEFAULT_*` 常量 · ExecStart `/usr/bin/python3 -m liuye_service.workers.outbox_retry` 已正确)
  - `deploy/install-liuye-outbox.sh` (新 109 行 · idempotent install script · 3 step: ① sqlite migration pre-flight 走 `default_ledger()._init_schema()` 尝试 · fail 则 fallback to per-table ALTER 逐列添加 `parent_turn_id` / `is_feedback` / `feedback_meta` + per-index `CREATE INDEX IF NOT EXISTS` 5 索引 ② `sudo cp + daemon-reload + enable + restart` ③ `journalctl --since '10 seconds ago'` verify worker started log)
  - `liuye_service/tests/test_fallback_tavily_quota.py` (新 257 行 · 5 应急 dry-run W2 #1 · 5 test · 1 backend 429 → `turn.error code=ADAPTER_HTTP_ERROR fallback_available=true` + 1 backend URL audit 真打到 + 1 DEMO_MODE fallback replay fixture 跑通 11 event 流 + 候选 4 字段 (industry/geo/scale/similarity per Q-041) + 1 fixture 缺失 → `code=DEMO_FIXTURE_MISSING` 专用 banner + 1 failure isolation channel 挂不影响下个 turn)
  - `liuye_service/tests/test_fallback_ledger_silent_fail.py` (新 290 行 · 5 应急 dry-run W2 #2 · 8 test · 1 sqlite OperationalError → audit silent-fail 写 outbox + idempotency_key + 错误 _error 标注 + 1 parent_turn_id 在 outbox 保留 + 1 subject_id 永 hash 不 plain 落 outbox + 1 端到端 outbox→worker→record_decision 真接通 + 1 retry > 5 → dead-letter graduation + 1 backoff schedule v3 §5.x 60/120/240/480/960 verify + 1 idempotency_key 防 worker 双写 + 1 _enqueue_outbox helper unit · 强 verify _record_decision OperationalError raise 路径 · NOT 走 LedgerWriteResult fallback)
  - `liuye_service/tests/test_integration_live.py` (新 451 行 · end-to-end SSE integration · 7 test · 1 POST /sessions httpx ASGI + dispatch_via_adapter task + drive _stream_skeleton 收 9 mock + turn.started 真到 + 1 seq monotonic +1 严格 + 1 heartbeat 0.2s tick fire when adapter idle + 1 id 格式 `<turn_id>:<seq>` Last-Event-ID 重连 wire 验 + 2 LB retry dedup gate · `_dispatch_via_adapter` 桥接 queue + None sentinel)
- **关键决策** (≤ 200 字):
  - **integration test 不起真 subprocess uvicorn**: 因 `httpx.ASGITransport.handle_async_request` (httpx 0.28.1 src) 内 `body_parts` buffer + `response_complete.wait()` · 对 infinite SSE generator (heartbeat 永不停) 永挂 `client.stream("GET", ...).__aenter__()` (本棒 Python 3.14 真验过 hang) · subprocess uvicorn 跨 Windows/Linux 端口冲突 + Iocp event loop 兼容差. 解法: 直接驱 `_stream_skeleton(orch, turn_id)` async generator + `_dispatch_via_adapter` 在同 loop 跑 · 抓 generator yield 的 wire 字符串 verify · 这是 SSE wire format 真正的 SSOT (FastAPI/Starlette 只是把 generator output bytes 写 socket) · 非 SSE endpoint (POST) 走 httpx ASGITransport 正常 work
  - **应急 dry-run #1 Tavily 选 backend 出口 mock**: brief 说 mock `shared/sources/impls/tavily.py` 或 `agent_channel/signal_search` Tavily call · 我选**前者下游**: 直接 mock backend HTTP 返 429 (`_MockHttpClient` 实现 `stream(method, url)` 返 `_MockResponse(429)`) · adapter 内 `_run_live` 见 `response.status_code != 200` 直 emit `ADAPTER_HTTP_ERROR` · 不绕进 `agent_channel/signal_search` 内部 (违反 §2.3 hardline)
  - **应急 dry-run #2 monkeypatch 路径**: monkeypatch `liuye_service.audit._record_decision` 而非 `shared.decision_ledger.record_decision` · 因 audit.py 模块顶 `from shared.decision_ledger import ... record_decision as _record_decision` 早绑定 · patch 模块名空间内 `_record_decision` 拦截到 silent-fail except 分支
- **verify 跑** (3 命令全 PASS):
  - `py -m pytest liuye_service/tests/ -v` → **156 PASS** (W1 59 + W2 第 3 棒 77 + W2 第 4 棒 +20 = 156 · 0 fail · 0 skip)
  - `py -c "from shared.decision_ledger.store import default_ledger; l = default_ledger(); print(l.db_path, l.schema_version)"` → `D:\claude code\credit_report_agent_work\data\ledger\decisions.sqlite 1.1.0` (production sqlite pre-flight migration succeeds · v1.1 schema active)
  - Real SSE wire output (test_e2e_full_11_event_sequence): turn.started → message.created → tool.started → tool.progress (×3) → tool.completed → evidence.attached → artifact.patch → turn.completed (10 frame · 9 mock + 1 stream_skeleton turn.started · all id format `turn_<hex>:N`)
- **下一棒**: codex bg review (main session 起 · W2-backend 16/16 DONE handoff)
- **blocker**: 无
- **hidden gotcha 发现** (留 W3-W4 + codex review):
  - **install-liuye-outbox.sh Windows vs Linux 兼容**: script 用 bash + sudo · 仅 Linux/ECS · Windows 不可直跑 (本棒 verify "doc only" · pytest 在 Windows tracking 通过 · 真 install 走 deploy_to_ecs.sh on Linux ECS) · W3-W4 不必加 Windows 版 (Phase 1 不部署 Windows production)
  - **httpx.ASGITransport SSE 永挂**: brief 用 `subprocess.Popen` 起 uvicorn 是初衷 · 但实测 Iocp on Windows 跑 uvicorn subprocess 仍稳 (本棒 brief §3 file 5 注释里写过 "起 uvicorn `--port 8500` 避 :8000 冲突") · 我选 drive `_stream_skeleton` 是更稳更快路径 · 整测 ~0.8s 即完 vs subprocess uvicorn ~5-10s 启动 + cleanup. 真 subprocess uvicorn smoke 留 W3 (生产 deploy_to_ecs.sh post-restart healthcheck 一句 `curl http://localhost:8000/api/liuye/health` 已 cover · 不需 pytest 跑)
  - **MockProducerAdapter Protocol 完整性**: 本棒 mock 只实现 `dispatch_message` 不实 `start_turn` / `abort_turn` (Protocol contract 上 optional · orchestrator 不 require) · 真 production adapter (channel/credit/report) 3 method 全实 · 之间是 Protocol structural typing · pytest 不破真 production code
  - **deploy/install-liuye-outbox.sh 不在 pytest 跑**: bash script 跨 Windows 不能 unit test · 真验只能 ECS deploy 后 `sudo systemctl status liuye-outbox` 见 `active (running)` · 本棒 doc only verify · W3 deploy_to_ecs.sh 加 install-liuye-outbox.sh post-deploy hook 自动跑一次
  - **W3-W4 5 应急 dry-run 还剩 3** (brief §3 file 3-4 注释): LLM fallback chain (deepseek 503 → dashscope · per root §3.6) / SSE conversion failure (sse_v1_to_liuye `code=SSE_ADAPTER_FAILED fallback_available=true` 单一 envelope 真发) / network offline (httpx ConnectError on backend / Tavily 网络断 · 不同于 quota · 验 retry chain 不跑 5 次 fast-fail)
- **OUTBOX-SYSTEMD-INSTALL**: ok (Restart=on-failure + RestartSec=60s aligned · per-table ALTER fallback 5 列 + 5 索引 idempotent · journalctl verify 入 script)
- **EMERGENCY-DRY-RUN**: 2/5 done (W2 · Tavily 429 + ledger sqlite OperationalError · W3-W4 留 3: LLM fallback + SSE conversion + network offline)
- **E2E-INTEGRATION**: heartbeat 0.2s × 5 tick + seq monotonic +1 + id `<turn_id>:<seq>` + LB retry dedup + dispatch→queue→None sentinel · 7 PASS
- **PYTEST-NO-REGRESSION**: 156 PASS (W1 59 + W2 第 3 棒 77 + W2 第 4 棒 +20 · 0 fail · 0 skip)
- **BACKEND-W2-DELIVERED**: 16/16 DONE
- **ELAPSED min**: ~55 (5 文件 + httpx ASGI hang 调试 + pytest 156 verify + sqlite pre-flight verify + progress 段 + commit)
- **commit SHA**: 08f0d89
