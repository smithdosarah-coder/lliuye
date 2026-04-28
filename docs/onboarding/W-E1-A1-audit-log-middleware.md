# Worker A1 (Stage E 第 1 批) · LLM Audit Log Middleware · Onboarding

> Worker CLI 在 `D:/claude code/work-A1-inventory` (branch
> `feat/inventory-expand-A1`) · 复用 worktree。
> 上批 Stage D.5 shared/kb_scan (`b296a59`) 已 cherry-pick MERGED (`a97dc49`) ·
> 本批 Stage E.1 启动 (production hardening 入门)。

## Goal

实装 master plan §E.1 — LLM Audit Log middleware ·
**banking 合规必修** (PIPL + 银保监监管要求 LLM 决策可追溯)。

每个 LLM call 留痕:
- timestamp · user_id (from JWT cookie · 复用 D.1 auth) · agent_id · endpoint
- request prompt · response · tokens (input/output) · cost (CNY)
- latency · error / timeout · model name (DeepSeek-Chat / GPT-4 / etc.)
- 持久化 sqlite `data/audit/llm_calls.db`

## Acceptance

- [ ] **必读** `auth_service/dependencies.py` (D.1 require_user · 拿 user_id) ·
      `shared/kb_scan/router.py` (D.5 ScannerRouter · 加 audit hook 位置)
- [ ] **新建** `audit_service/` module:
  - `recorder.py` (sqlite store + LLMCall dataclass)
  - `middleware.py` (FastAPI middleware · 每 LLM endpoint pre/post hook)
  - `decorators.py` (`@audit_llm_call` · 简化 endpoint mark)
  - `tests/test_*.py`
- [ ] **6 Agent backend** 加 `@audit_llm_call` decorator 到所有 LLM endpoint
      (`/api/channel/run` · `/api/credit/decision` · `/api/report/v16/fill` ·
      `/api/alert/scan` · `/api/compliance/policy_scan` · `/api/riskctrl/dsl_gen`)
- [ ] **GET `/api/audit/llm_calls`** (admin only · `require_user` + role check) ·
      paginated · filterable by user_id / agent_id / date range
- [ ] sqlite schema:
  ```sql
  CREATE TABLE llm_calls (
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL,            -- ISO 8601
    user_id TEXT,                -- nullable (system call)
    agent_id TEXT NOT NULL,      -- channel/credit/report/...
    endpoint TEXT NOT NULL,      -- /api/channel/run
    model TEXT NOT NULL,         -- deepseek-chat / gpt-4
    prompt TEXT,                 -- request prompt (truncated to 4KB)
    response TEXT,               -- LLM response (truncated to 8KB)
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_cny REAL,               -- 估算成本
    latency_ms INTEGER,
    error TEXT                   -- nullable
  );
  CREATE INDEX idx_user_ts ON llm_calls(user_id, ts);
  CREATE INDEX idx_agent_ts ON llm_calls(agent_id, ts);
  ```
- [ ] curl 测各 agent endpoint 触发 LLM call · 验 `data/audit/llm_calls.db` 真写入
- [ ] pytest `audit_service/tests/` ≥ 8 case (record · query · pagination ·
      role guard · truncate · cost calc · 6 Agent integration)
- [ ] commit trailer:
  ```
  Signal: WORKER-A1-STAGE-E1-AUDIT-LOG-DONE
  RECOVER-FROM: b296a59 (D.5 shared/kb_scan done · 本批接续)
  NEW-MODULE: audit_service/{recorder,middleware,decorators,tests}
  NEW-ENDPOINT: GET /api/audit/llm_calls (admin)
  HARDENING: 6 Agent LLM endpoint 加 audit decorator
  ```

## Boundary

- **改**: 6 Agent `agent_*/api.py` (加 decorator · surgical · 不改业务) +
  `api_server.py` (mount /api/audit/llm_calls)
- **加**: `audit_service/{recorder,middleware,decorators,__init__}.py` +
  `audit_service/tests/test_*.py` + `data/audit/.gitkeep`
- **不动**: `web/*` (frontend audit dashboard 后续 Stage E.2) · `shared/kb_scan/` ·
  `auth_service/` · CLAUDE.md · RFC

## Dependencies

- master plan §E.1 (Stage E hardening 入门 · 银保监合规 P0)
- `auth_service/dependencies.py` (D.1 cherry-pick a97dc49 · require_user)
- DeepSeek client / Tavily client (各 agent_*/ 内部 LLM call · 无需改 SDK)
- sqlite (Python stdlib)

## Method

1. Read `auth_service/dependencies.py` (require_user / require_agent · cookie 拿 user_id)
2. 设计 sqlite schema · DDL 在 recorder.py
3. 设计 `@audit_llm_call(agent_id, endpoint)` decorator · pre/post hook
4. middleware: 调用 LLM 前 record start · 调用后 record end + tokens + cost
5. 6 Agent endpoint 加 decorator (不改业务逻辑 · 包装外层)
6. /api/audit/llm_calls admin endpoint
7. pytest 8+ case + curl 验

## Trailer protocol

```
Signal: WORKER-A1-STAGE-E1-AUDIT-LOG-DONE
RECOVER-FROM: b296a59
NEW-MODULE: audit_service/{recorder,middleware,decorators,tests}
NEW-ENDPOINT: GET /api/audit/llm_calls (admin)
HARDENING: 6 Agent LLM endpoint 加 audit decorator
```

## On completion

1. `git add audit_service/ agent_*/ api_server.py data/audit/.gitkeep` + commit + push
2. main CLI auto-patrol → review (curl trigger LLM + sqlite verify + admin role
   guard + pytest cumulative) → cherry-pick → push origin

## Estim

5-7 hr (sqlite + decorator + 6 Agent integration · 测试 careful · 不破坏现有)

## NB

- decorator 不阻塞 LLM 主路径 · 失败时 silent log warning (不让 audit 拖慢业务)
- prompt / response 长度 truncate (4KB / 8KB) · 避免 sqlite 膨胀
- cost_cny 简单估算: `tokens * 0.0001 RMB` (各 model 单价后续 config 化)
- audit 数据保留 90 天 · cleanup cron 后续 Stage E.2 加
- 银保监合规要求: 所有自动决策可追溯 · 留痕 = 满足合规底线
