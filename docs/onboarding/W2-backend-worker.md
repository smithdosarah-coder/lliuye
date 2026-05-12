# W2 Backend Worker · Onboarding Brief

> **worker 代号**: `claude-W2-backend`
> **任务**: W2 Phase 1 端到端 demo path · 3 Cowork adapter live mode + SSE adapter 真转 + ledger 真写 + outbox systemd + permissions emit 真触 + 5 应急 backend dry-run + live integration pytest (16 文件改 + 新)
> **依据**: `_temp/w2-plan.md` §3.1 + v3 spec §5 (BFF) + §6.3 (demo path) + 附录 C (3 fallback) + 老仓 root `CLAUDE.md` §3.1.1 / §3.6 / §3.7.5
> **估时**: ~10-12 工时 (W2 D6 ~ D10 · 14-18 sub-agent 棒 30-45 min/棒)
> **版本**: v1.0 (W2 brief writer 写 · 2026-05-12)

---

## 1. 身份 + 起手

**你是**: W2 backend worker · 3 worker 并行第一棒 · 你把 W1 backend skeleton 升级为 live 真路径.

**依赖**:
- W1 backend 18/18 DONE (`liuye_service/` skeleton + adapter stub + SSE adapter + outbox + ledger_review + 3 test)
- W1 contract 14/14 DONE (5 schema + Zod + 5 fixture + lock + sync/verify · schema_hash `d79ddfdcf6d3b381...`)
- W2 frontend 同 W2 并行 (你出 live SSE 真流 · frontend 真消费)
- W2 mock-test 同 W2 并行 (复用 3 mock SSE :8001/:8002/:8003 跑 live integration · 真 backend 起 `py scripts/start_uvicorn.py`)

**第一件事 (开工前必做)**:
1. 读 `D:\claude code\_temp\w2-plan.md` (W2 plan 全 · 8 章 + 12 必修 + D6-D10)
2. 读 `D:\claude code\credit_report_agent_work\docs\onboarding\W1-backend-worker.md` (W1 brief 模板源)
3. 读 `D:\claude code\credit_report_agent_work\docs\handoff\W1-backend-progress.md` (W1 backend 4 棒累积 hidden gotcha · 重点第 3 棒 + 第 4 棒)
4. 读 `D:\claude code\_temp\liuye-final-spec-v3.md` §5 (BFF · v3 line 460-512) + §6.3 (demo path 70s) + 附录 C (3 fallback) + §2.1 (11 event)
5. 读 `D:\claude code\credit_report_agent_work\liuye_service\CLAUDE.md` (BFF scoped 工作纪律 · §4 Cowork/Managed + §5 ledger + §8 PermissionRequest)
6. 读 老仓 root `CLAUDE.md` §3.1.1 (Cowork/Managed) + §3.6 (LLM PIPL fallback chain) + §3.7.5 (BE7 ledger jurisdiction/retention) + §13 (ECS 同步纪律)
7. **读 `docs/onboarding/W1-worker-handoff-protocol.md` §2 + §5** · W2 沿用 · 你不是 10-12h 单 session · 是接力赛 · 每 30 min 必 checkpoint + 写 `docs/handoff/W2-backend-progress.md`
8. 写 "我理解 W2 backend scope" 一段 (≤ 200 字) 给 main session verify · 没漂再开干

## 2. 输入文件清单

| 文件 | 用途 | 必读章节 |
|---|---|---|
| `_temp/w2-plan.md` | W2 plan SSOT | §3.1 W2-backend worker scope + §5 risk + §6 DoD |
| `docs/onboarding/W1-backend-worker.md` | W1 brief 模板源 | 全 (你的 brief 是它的 W2 延伸) |
| `docs/handoff/W1-backend-progress.md` | W1 backend 4 棒累积 gotcha | 第 3 棒 (adapter) + 第 4 棒 (façade upgrade + wire-up · SHA `041d645`) |
| `_temp/liuye-final-spec-v3.md` | v3 spec | §5 (BFF) + §6.3 (demo path) + 附录 C (3 fallback) + §2.1 (11 event) |
| `liuye_service/CLAUDE.md` | BFF scoped | §4 Cowork/Managed + §5 ledger + §8 PermissionRequest |
| `docs/contracts/liuye-architecture.md` | Tier 1 SSOT | 全 |
| `docs/contracts/liuye-sse-event-matrix.md` v1.1 | 11 event × 6 Agent × scenario matrix | §3 Q1/Q2/Q3 + §4 mapping table |
| `docs/contracts/decision-ledger.md` v1.1 | BE7 schema · Q3 ratify | §1 LedgerEntry parent_turn_id 字段 |
| `shared/contracts/liuye/schemas/*.json` | 5 协议 (你 Pydantic 与之一致) | 全 5 文件 |
| `shared/llm_caller/*` | LLM caller 单一抽象 | retry.py `DEFAULT_FALLBACK_CHAIN` |
| `shared/decision_ledger/*` | BE7 决策账本 · façade upgrade DONE | store.py + schema.py v1.1 |
| 老仓 root `CLAUDE.md` | 全局工程纪律 | §3.1.1 / §3.6 / §3.7.4 / §3.7.5 / §3.7.7 / §13 |
| 真 backend 6 agent (`agent_*/api.py`) | live mode 真接 source | `/api/channel/run` + `/api/credit/decision` + `/api/report/v16/fill` |

## 3. W2 file checklist (16 文件 · 改 8 + 新 8)

### 3.1 改 8 W1 文件 (live mode 实做)

```
credit_report_agent_work/liuye_service/adapters/channel.py     (DEMO_MODE → live httpx async stream)
credit_report_agent_work/liuye_service/adapters/credit.py      (DEMO_MODE → live · parent_tool_call_id 真透传)
credit_report_agent_work/liuye_service/adapters/report.py      (DEMO_MODE → live · v16 5 stage 真流)
credit_report_agent_work/liuye_service/adapters/sse_v1_to_liuye.py  (真流验 · dedup/percent/inheritance 真场景)
credit_report_agent_work/liuye_service/audit.py                (façade parent_turn_id 真 kwarg forward · 删 evidence_chain._meta hack · 已在 W1 第 4 棒 DONE · W2 仅 verify 真 sqlite query path)
credit_report_agent_work/liuye_service/permissions.py          (emit_permission_request 真触 3 场景 · A3-NEW / LE-05 / KB upload)
credit_report_agent_work/liuye_service/orchestrator.py         (SSE bridge wire-up 真消费 · permission hold + resume_turn 真 path)
credit_report_agent_work/liuye_service/api.py                  (live mode env switch · LIUYE_DEMO_MODE=0 走真 backend)
```

### 3.2 新 8 文件 (live integration test + systemd + deploy)

```
credit_report_agent_work/liuye_service/tests/test_live_channel.py    (live channel adapter 集成测试)
credit_report_agent_work/liuye_service/tests/test_live_credit.py     (live credit adapter 集成测试 · parent_tool_call_id 透传验)
credit_report_agent_work/liuye_service/tests/test_live_report.py     (live report adapter 集成测试 · v16 5 stage 真流)
credit_report_agent_work/liuye_service/tests/test_permissions_live.py (3 场景 emit_permission_request + grant/deny REST 真测)
credit_report_agent_work/liuye_service/tests/test_outbox_systemd.py  (systemd unit 集成 · journalctl + sqlite ledger silent-fail outbox)
credit_report_agent_work/deploy/liuye-outbox.service                  (systemd unit · 60s loop + 5 retry exp backoff)
credit_report_agent_work/deploy/install-liuye-outbox.sh               (安装脚本 · systemctl enable + start)
credit_report_agent_work/deploy/README.md                             (部署说明 + journalctl 操作 + Sentry alert 验)
```

## 4. 关键纪律

### 4.1 live mode 切换协议 (LIUYE_DEMO_MODE env)

**env switch**:
- `LIUYE_DEMO_MODE=1` (W1 默认) → adapter 走 `tests/fixtures/*.json` 经 `LIUYE_FIXTURES_PATH` 加载
- `LIUYE_DEMO_MODE=0` (W2 新加) → adapter 走 httpx async stream 真接 `/api/{channel,credit,report}/*`
- 失败 fallback: live 模式 5s first byte timeout / 30s read timeout → emit `turn.error code=ADAPTER_TIMEOUT human_hint='Agent 暂时不可用 · 已切换至降级模式'` → orchestrator 自动重试 DEMO_MODE 1 次 (前端 banner 显「Demo 模式」灰 badge)

**硬线**:
- live 模式 backend URL 走 env `LIUYE_BACKEND_BASE_URL` (default `http://localhost:8000`) · 不硬编 (per `liuye_service/config.py`)
- 端口分配: real backend uvicorn :8000 (per `py scripts/start_uvicorn.py`) · mock SSE :8001/:8002/:8003 (W1 mock-test) · 真 backend live mode 走 :8000 + path · 不混 mock 端口
- **per-adapter URL 覆写** (D10 hybrid 彩排支持 · perfect-check fix #2): env `LIUYE_BACKEND_CHANNEL_URL` / `LIUYE_BACKEND_CREDIT_URL` / `LIUYE_BACKEND_REPORT_URL` 优先于 `LIUYE_BACKEND_BASE_URL` · 用于 hybrid 模式 (e.g. channel→mock :8001 + credit/report→live :8000) · `_resolve_backend_url(agent_id)` helper 实做 (`os.environ.get(f'LIUYE_BACKEND_{agent_id.upper()}_URL') or self.backend_url`)

### 4.2 3 Cowork adapter live 实做 (v3 §5)

**通用结构** (channel / credit / report 同 pattern):
```python
# W2 新加: per-adapter endpoint map (perfect-check fix #1 · 真 endpoint 不是 generic /api/{agent_id}/run)
_ENDPOINT_MAP = {
    "channel": "/api/channel/run",
    "credit":  "/api/credit/decision",
    "report":  "/api/report/v16/fill",
}

async def dispatch_message(self, *, persona, agent_id, content, parent_tool_call_id=None):
    if self.config.demo_mode:
        async for evt in self._synthesise_frames():  # W1 已实做 · 不动
            yield evt
        return

    # W2 新加: live mode · per-adapter endpoint + URL 覆写
    base = self._resolve_backend_url(agent_id)  # 走 LIUYE_BACKEND_{AGENT}_URL > LIUYE_BACKEND_BASE_URL
    url = f"{base}{self._ENDPOINT_MAP[agent_id]}"  # 真 endpoint per W1 spec §5 + root CLAUDE.md §2
    body = {"persona": persona, "content": content, "parent_tool_call_id": parent_tool_call_id}
    timeout = httpx.Timeout(connect=5.0, read=30.0)  # Cowork SLA < 5s first byte
    async with self.client.stream("POST", url, json=body, timeout=timeout) as resp:
        if resp.status_code != 200:
            yield envelope(event="turn.error", payload=TurnErrorPayload(code="ADAPTER_HTTP_ERROR", ...))
            return
        async for v1_event in self._iter_sse_v1(resp):  # W1 已实做 · 复用
            for liuye_event in self.sse_translator.translate(v1_event):
                yield liuye_event
```

**关键**:
- `_iter_sse_v1(resp)` 是 W1 backend 第 3 棒已实做 (channel.py:380 行) · credit/report 复用
- live 模式失败 (timeout / 5xx / SSE parse error) → 单条 `turn.error code=ADAPTER_TIMEOUT/ADAPTER_HTTP_ERROR/SSE_ADAPTER_FAILED fallback_available=true` · 客户端走 fallback (前端 banner)
- httpx `client.stream("POST", url, json=body)` 必 `async with` (per W1 backend 第 3 棒 gotcha #2)
- `parent_tool_call_id` Report → Credit handoff 透传 (per W1 backend 第 3 棒 hidden gotcha #4)

### 4.3 SSE adapter 真转 (v3 §2.1.5 + 附录 A · PM 2026-05-11 ratify)

W1 backend 第 3 棒已实做 `SseV1ToLiuyeAdapter` (425 行 · 8 v1 handler · dedup + percent + inheritance · 20/20 test PASS).

**W2 加固** (真流端到端验):
- 真 backend SSE 流 (live mode 调 `/api/channel/run`) → adapter 解析 → emit 11 event → orchestrator queue → API SSE response → frontend EventSource → store dispatch → UI 渲染
- 真断网测试: kill backend uvicorn → adapter 收 `httpx.ConnectError` → emit `turn.error code=BACKEND_OFFLINE retryable=true` → frontend reconnect 走 mock fallback
- 真 percent 转: backend `agent_channel/api.py` SSE v1 event `stage` payload `progress: 0.42` → adapter `_on_stage` 真转 `liuye.tool.progress.percent=42` (int round)
- 真 tool_call_id inheritance: backend emit `tool_call` 后连发多个 `stage` 不带 tool_call_id → adapter `_current_tool_call_id` stateful 续填 → liuye `tool.progress.tool_call_id` 真有

### 4.4 ledger 真写 + parent_turn_id 真 path

W1 backend 第 4 棒已 façade upgrade DONE (`shared.decision_ledger.record_decision(parent_turn_id=...)` 真 kwarg forward · sqlite `decisions.parent_turn_id` 列真写).

**W2 verify**:
- 真 sqlite query: `sqlite3 data/ledger/decisions.sqlite "SELECT decision_id, agent_id, parent_turn_id FROM decisions ORDER BY created_at DESC LIMIT 10"` 看真 row
- 跨 mode 场景: Agent2 (Cowork DSL) → Agent2 backtest (Managed) · DSL decision 写 ledger A · backtest Managed job 完后写 ledger B 含 `parent_turn_id=A.turn_id` · 验 `ledger.get(B.decision_id)['parent_turn_id'] == A.turn_id` (W2 不上 Phase 2 真 Managed pipeline · 但 audit.py 接 parent_turn_id 真 kwarg 可手测)
- LedgerReviewEvent append-only: `POST /api/liuye/ledger/decisions/{id}/review_events` 真测 · 同 idempotency_key 调 2 次返 1 row (per W1 backend 第 4 棒 `ledger_review.py`)

### 4.5 outbox systemd 跑通 (v3 §5.x · P1-12)

W1 backend 第 4 棒已实做 `workers/outbox_retry.py` (536 行 · 20/20 test PASS · CLI entry `python -m liuye_service.workers.outbox_retry`).

**W2 新加 systemd 部署**:
- `deploy/liuye-outbox.service` systemd unit:
  ```ini
  [Unit]
  Description=Liuye decision ledger outbox retry worker
  After=network.target

  [Service]
  Type=simple
  User=liuye
  WorkingDirectory=/opt/liuye/credit_report_agent_work
  Environment="PYTHONPATH=/opt/liuye/credit_report_agent_work"
  Environment="LIUYE_OUTBOX_DIR=/opt/liuye/data/liuye/outbox"
  Environment="LIUYE_DEADLETTER_DIR=/opt/liuye/data/liuye/dead-letter"
  Environment="LIUYE_OUTBOX_MAX_RETRY=5"
  Environment="LIUYE_OUTBOX_BACKOFF_CSV=60,120,240,480,960"
  ExecStart=/opt/liuye/venv/bin/python -m liuye_service.workers.outbox_retry
  Restart=on-failure
  RestartSec=10s
  StandardOutput=journal
  StandardError=journal

  [Install]
  WantedBy=multi-user.target
  ```
- 部署: `sudo cp deploy/liuye-outbox.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable liuye-outbox && sudo systemctl start liuye-outbox`
- 验: `systemctl status liuye-outbox` active · `journalctl -u liuye-outbox -f` 看 60s loop · 模拟 ledger silent-fail (写 `data/liuye/outbox/test.json`) · 等 60s 看 retry · 第 6 次失败转 dead-letter

### 4.6 permissions.py emit_permission_request 真触 3 场景

W1 backend 第 2 棒已实做 `permissions.py::emit_permission_request` (349 行 · 14 action registry + risk_tier_for + grant/deny handler).

**W2 真触场景**:

| 场景 | action_id | risk_tier | idempotency_key | required_persona |
|---|---|---|---|---|
| A3-NEW Decision submit | `credit_decision_submit` | medium | uuid4 | `['reviewer']` |
| LE-05 签字 | `ledger_review_signature` | high | uuid4 | `['compliance_officer']` · reason_required=true |
| KB upload | `kb_doc_upload` | medium | uuid4 | `['rm', 'reviewer']` |

**测试** (`test_permissions_live.py`):
- 真 SSE flow: 客户经理触 A3-NEW Decision submit → orchestrator 收 `dispatch_message` → 到 review checkpoint 调 `permissions.emit_permission_request(...)` → 11th event `permission.request` emit 到 SSE queue → orchestrator hold business event (message.delta / tool.progress / artifact.patch / evidence.attached 暂停 · heartbeat 15s 续 · per matrix §3 Q2)
- grant REST `POST /api/liuye/permissions/{request_id}/grant` body `{user_id, idempotency_key}` → 验 idempotency_key + role check → `orchestrator.resume_turn(turn_id)` seq+1 续推 → `ledger_review.record_review_event(decision_id, action='approve', ...)` append-only
- deny REST `POST /api/liuye/permissions/{request_id}/deny` body `{user_id, reason, idempotency_key}` → `orchestrator.abort_turn(turn_id, code='PERMISSION_DENIED')` → push `turn.error code=PERMISSION_DENIED retryable=false` + `turn.completed ok=false` + stream 收尾

### 4.7 5 应急流程 backend dry-run (附录 C.2 · W2 跑 2)

W2 必跑:

**(1) Tavily quota mock fallback**: `LIUYE_DEMO_MODE=mock` env switch · channel adapter live 模式 catch `TavilyQuotaExceededError` → 自动 retry once DEMO_MODE → emit `tool.completed` w/ artifact `_meta.data_source='mock'` · 前端 banner 「Demo 模式」灰 badge.

**(2) ledger silent-fail outbox**: `audit.record_liuye_decision(...)` sqlite write fail (mock `sqlite3.OperationalError`) → silent-fail (`_enqueue_outbox()` 写 `data/liuye/outbox/{decision_id}.json` · audit chain 保完整) → systemd outbox worker 60s loop 扫到 retry 5 次 · 第 6 次写 `data/liuye/dead-letter/` + Sentry alert log `extra={"sentry.alert": True}` · 前端 confirm modal 显「已提交 · 上链中」乐观更新

W3-W4 跑剩 3 (LLM provider fallback / SSE conversion failed / network offline cached snapshot · 留 W3-W4 dry-run).

### 4.8 边界硬线 (W1 backend 沿用)

- **禁** import `agent_*` 内部函数 (HTTP 隔离硬线 · 任何 `from agent_channel.signal_search import ...` 视作 regression)
- **禁** 改 SSE v1.0 协议 (`docs/contracts/sse-envelope.md` 是 SSOT)
- **禁** 建 `liuye_service/prompts/` 新目录 (root §3.7.7 prompt 灰度)
- **禁** ledger write 走 HTTP (in-process · `shared.decision_ledger`)
- **禁** 用 `asyncio.create_task` 做 outbox 重试 (进程重启即丢 · 必走 systemd)
- **禁** 把 plain PII 写 ledger (subject_id 必须 hash · `hash_subject_id()`)
- **禁** 跳 codex review (root §3.7.4)

## 5. 输出 DoD (Definition of Done)

- ✓ 16 文件全 Write/Edit 完成 · path 与 §3 1:1 一致
- ✓ 3 Cowork adapter live mode 跑通 (`pytest liuye_service/tests/test_live_*.py -v` 全 pass)
- ✓ SSE adapter 真转 (live channel adapter → sse_v1_to_liuye → emit 11 event · dedup + percent + tool_call_id inheritance 真验)
- ✓ ledger 真写 verify (`sqlite3 data/ledger/decisions.sqlite "SELECT decision_id, parent_turn_id FROM decisions"` 真 row · parent_turn_id 真 kwarg path · `ledger_review_events` 真 chain)
- ✓ outbox systemd 跑通 (`systemctl status liuye-outbox` active · `journalctl -u liuye-outbox` 看 60s loop · 模拟 ledger silent-fail outbox enqueue → 5 retry → dead-letter)
- ✓ permissions.py emit_permission_request 真触 3 场景 (A3-NEW / LE-05 / KB upload · grant/deny REST 真测)
- ✓ 5 应急流程 W2 跑 2 dry-run (Tavily quota + ledger silent-fail)
- ✓ end-to-end pytest live integration (`test_live_channel.py` + `test_live_credit.py` + `test_live_report.py` + `test_permissions_live.py` + `test_outbox_systemd.py` 全 pass)
- ✓ commit trailer 含 `BACKEND-W2-DELIVERED: 16/16` + `SSE-LIVE-VERIFIED: ok` + `LEDGER-PARENT-TURN-ID: VERIFIED` + `OUTBOX-SYSTEMD: ACTIVE` + `PERMISSIONS-LIVE: 3/3` + `EMERGENCY-DRY-RUN: 2/5`
- ✓ codex independent review 通过 (root §3.7.4 protocol v2)

## 6. W2 末 sign-off 流程

1. **PR 创建**: `feat/liuye-W2-backend` 分支 → PR to `main` · title `[W2-backend] live mode + SSE 真转 + ledger 真写 + outbox systemd + 5 应急 backend dry-run`
2. **codex review** (root §3.7.4):
   ```
   codex exec -c 'model_reasoning_effort="medium"' \
     --search \
     "Review W2 backend worker PR for liuye_service. Check 1) 3 Cowork adapter live mode httpx async stream 2) SSE adapter 真转 dedup + percent + inheritance 真场景 3) ledger 真写 parent_turn_id kwarg path 4) outbox systemd unit + journalctl 60s loop + dead-letter 5) permissions.py 3 场景真触 + grant/deny REST 6) 5 应急 dry-run 2/5 (Tavily quota + ledger silent-fail). Verdict: GO / NO-GO."
   ```
3. **commit trailer** (root §13.5):
   ```
   BACKEND-W2-DELIVERED: 16/16
   SSE-LIVE-VERIFIED: ok
   LEDGER-PARENT-TURN-ID: VERIFIED
   OUTBOX-SYSTEMD: ACTIVE
   PERMISSIONS-LIVE: 3/3
   EMERGENCY-DRY-RUN: 2/5
   REVIEW-MODE: codex
   REASONING-EFFORT: medium
   ELAPSED: <min>
   ```
4. **PM ack**: PM 看 codex verdict + 真 sqlite query verify + journalctl 截图 · ack 后 W3 才能开工

## 7. 估时 + 风险点 (file-level)

| 文件 | 估时 | 风险点 |
|---|---|---|
| `adapters/{channel,credit,report}.py` live mode 改 | 3h | httpx async stream + `_iter_sse_v1` 真流解析 (W1 单 test pass 但真 backend 流可能有边界) · timeout 5s/30s 配置错 |
| `adapters/sse_v1_to_liuye.py` 真流加固 | 1.5h | dedup_key 真 collision (真 backend 多 worker 时 sha256 hash 同 payload 重发) · percent 边界 0.42 真值 |
| `audit.py` + `permissions.py` 真触 | 1.5h | parent_turn_id 真 kwarg path · 3 场景 risk_tier 误标 · idempotency_key 真重复防 |
| `orchestrator.py` SSE bridge wire-up | 1h | per-turn queue 真背压 (256 maxsize) · permission hold + resume_turn race condition |
| `api.py` live mode env switch | 0.5h | LIUYE_DEMO_MODE env 0/1 切换 · LIUYE_BACKEND_BASE_URL 配置 |
| `tests/test_live_*.py` 4 文件 | 2h | mock SSE :8001/:8002/:8003 起停 + respx httpx mock · 真 backend health probe optional |
| `deploy/liuye-outbox.service` + install + README | 1h | systemd Environment var · WorkingDirectory · User=liuye · journalctl 验 |
| `tests/test_outbox_systemd.py` | 1h | systemd 集成测试 (mock systemctl or 真起) · 跨平台 (Win 跑 WSL · macOS skip · Linux 真起) |

**风险 mitigation**:
- D6 第一件事: backend uvicorn 起着 (`py scripts/start_uvicorn.py`) + curl `/api/agents/health` 200 · 不通 = D6 plan-only 模式
- live 模式真测前: 先用 W1 mock SSE :8001 起 + DEMO_MODE=0 + LIUYE_BACKEND_BASE_URL=http://localhost:8001 跑通 · 再切真 backend :8000
- outbox systemd: 跨平台兼容 · Win 跑用 WSL · macOS 用 launchd 替代 (deploy README 写两种) · Linux 是 production target

## 8. 不准做 / 别越界

- ❌ 不准 import `agent_*` 内部函数 (HTTP 隔离硬线)
- ❌ 不准动 `agent_*/api.py` 6 agent backend (那是老 worker 维护)
- ❌ 不准改 SSE v1.0 协议 (`docs/contracts/sse-envelope.md` 是 SSOT)
- ❌ 不准建 `liuye_service/prompts/` 新目录 (root §3.7.7)
- ❌ 不准动 5 schema (W1 contract 14/14 已 lock · schema_hash `d79ddfdcf6d3b381...` · 漂移 = stop the line)
- ❌ 不准 ledger write 走 HTTP (in-process)
- ❌ 不准用 `asyncio.create_task` 做 outbox 重试 (必走 systemd)
- ❌ 不准把 plain PII 写 ledger (subject_id hash)
- ❌ 不准做 messages 38 子类完整 / VirtualMessageList / 完整 PermissionRequest 15 子组件 / 3 compact (这是 W3-W4)
- ❌ 不准跳过 codex review (root §3.7.4)
- ❌ 不准跑超 5s SLA 的任务在 Cowork adapter (per §3.1.1 Cowork hardline · 拆 Managed pipeline)

## 9. 引用 SSOT

| Tier | 文件 |
|---|---|
| 1 | `docs/contracts/liuye-architecture.md` |
| 1 | `_temp/liuye-final-spec-v3.md` (§5 + §6.3 + 附录 C + §2.1) |
| 1 | `docs/contracts/sse-envelope.md` v1.0 |
| 1 | `docs/contracts/liuye-sse-event-matrix.md` v1.1 |
| 1 | `docs/contracts/decision-ledger.md` v1.1 |
| 2 | 老仓 root `CLAUDE.md` (§3.1.1 / §3.6 / §3.7.4 / §3.7.5 / §3.7.7 / §13) |
| 3 | `liuye_service/CLAUDE.md` (BFF scoped) |
| 4 | W1-backend-worker brief (模板源) |
| 4 | **本文件** (W2-backend brief) |
| 5 | `docs/handoff/W1-backend-progress.md` (W1 4 棒累积 hidden gotcha · 重点第 3-4 棒) |
| 5 | `_temp/w2-plan.md` §3.1 (W2-backend scope SSOT) |
| 上游 input | W1 contract 14/14 DONE (schema_hash `d79ddfdcf6d3b381...`) · W1 backend 18/18 DONE (`041d645`) |
