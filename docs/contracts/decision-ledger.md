# Cross-Agent Decision Ledger · v1.0 (Phase B-3 · BE7 · 2026-05-01)

> **Source**: `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` BE7 + Codex R2 加补 game-changer
> **Pain root**: 4 角色 verbatim — "银行用户不敢信 · 不敢签 · 不敢追责"
> **Owner**: worker-B4-credit (`feat/phase-b4-credit-be7`)
> **Tier**: 1 · per CLAUDE.md §15 instruction SSOT
> **Distinct from**: `audit_service.LLMCall` (LLM-call audit, prompt/response/cost · Stage E.1+E.3)
> **Relationship**: ledger = 决策级账本 (which decisions were made, by whom, with what evidence chain) · audit_service = LLM 调用流水 · 两层互补不重叠

---

## 0. Why this exists

> Codex R2 verbatim (BACKEND-DEEP-WORK-V2-1-FINAL §2): "后端真痛不是缺 ML / embedding / batch analytics — 这些都是手段。真痛是 4 角色对 AI 输出的**信任 + 可复核 + 可追责**。"

decision_ledger 是 **跨 Agent 决策追责账本**。它解决:

1. **不敢信** → 每个决策可被外部审计员追溯到原始 evidence chain (BE2 graph / BE3 supplement chain / BE4 alert / BE5 violation)
2. **不敢签** → reviewer_id 字段把人审签字钉在决策上 · 谁批的就是谁的责任
3. **不敢追责** → input_hash + output_hash 让事后篡改可被检测 · jurisdiction 字段把"这条决策归哪个监管口径管"明确化 (银/保/证/总行/分行)

不是 LLM 调用流水 (那是 audit_service)。是**决策事件流水** · 颗粒度 = 一次完整决策。

---

## 1. Schema

### 1.1 SQLite table

```sql
CREATE TABLE IF NOT EXISTS decisions (
  decision_id      TEXT PRIMARY KEY,         -- UUID4 · 由 record_decision() 生成或调用方传入
  agent_id         TEXT NOT NULL,            -- credit | report | alert | compliance | channel | riskctrl
  endpoint         TEXT NOT NULL,            -- e.g. /api/credit/decision · 用于按业务路径筛
  ts               TEXT NOT NULL,            -- ISO 8601 (timespec=seconds) · 决策完成时刻
  input_hash       TEXT NOT NULL,            -- SHA-256 over canonicalized input JSON (sorted keys, no whitespace)
  output_hash      TEXT NOT NULL,            -- SHA-256 over canonicalized output JSON
  evidence_chain   TEXT NOT NULL,            -- JSON blob · BE2 decision_graph 或 Agent6 section_supplement chain 或 alert evidence_pipeline
  reviewer_id      TEXT,                     -- nullable · 人审签字后 PATCH 填入 (人审 endpoint 当前仅占位 · Phase C 真接 RBAC)
  reviewer_action  TEXT,                     -- nullable · approve | reject | request_changes
  reviewer_ts      TEXT,                     -- nullable · 人审动作时刻
  jurisdiction     TEXT NOT NULL,            -- 银 | 保 | 证 | HQ | BRANCH (per CLAUDE.md §3.7.5 active rule)
  retention_class  TEXT NOT NULL,            -- short (90d) | standard (5y) | long (10y) (per §1.3)
  subject_name     TEXT,                     -- nullable · 决策主体名 (企业名 / 个人名) · 便于按主体筛
  subject_id       TEXT,                     -- nullable · 主体 id (统一社会信用代码 / 身份证号 hash)
  created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_agent_ts        ON decisions(agent_id, ts);
CREATE INDEX IF NOT EXISTS idx_jurisdiction_ts ON decisions(jurisdiction, ts);
CREATE INDEX IF NOT EXISTS idx_subject         ON decisions(subject_id) WHERE subject_id IS NOT NULL;
```

### 1.2 Python dataclass `LedgerEntry`

```python
@dataclass
class LedgerEntry:
    decision_id: str
    agent_id: str
    endpoint: str
    ts: str                       # ISO 8601
    input_hash: str               # sha256 hex
    output_hash: str              # sha256 hex
    evidence_chain: dict          # JSON-serializable
    jurisdiction: str = "HQ"      # default per §3.7.5
    retention_class: str = "standard"
    subject_name: str | None = None
    subject_id: str | None = None
    reviewer_id: str | None = None
    reviewer_action: str | None = None
    reviewer_ts: str | None = None
```

### 1.3 retention_class defaults (active rule per CLAUDE.md §3.7.5)

| agent_id | retention_class | rationale |
|---|---|---|
| `credit` | `standard` (5y) | 银保监 archive 要求 (per Phase B-3 dispatch) |
| `report` | `long` (10y) | Agent6 ReportJSON 是审贷会底稿 · 长留 |
| `alert` | `short` (90d) | 预警事件多 · routine 留 90d · serious (red severity) → standard |
| `compliance` | `standard` (5y) | 合规违规判定 · 银保监 archive |
| `channel` | `short` (90d) | 候选 / 推荐 · 非决策 · routine 留存 |
| `riskctrl` | `standard` (5y) | DSL 上线决策 · 银保监 archive |

Override: `record_decision(retention_class=...)` 显式参数。

### 1.4 jurisdiction values (active rule per CLAUDE.md §3.7.5)

允许枚举: `银` (银行业) · `保` (保险业) · `证` (证券业) · `HQ` (总行 / 集团总部) · `BRANCH` (分行 / 分公司)

默认: 环境变量 `LIUYE_LEDGER_JURISDICTION` (process-wide) > `record_decision(jurisdiction=...)` 显式参数 > `HQ` (兜底)

**未来 Phase C**: 多租户上线后改为 per-tenant config · 当前单租户全 `HQ`。

---

## 2. Public API (`shared.decision_ledger`)

```python
from shared.decision_ledger import (
    LedgerEntry,
    record_decision,        # write · silent-fail · returns decision_id
    get_decision,           # query by decision_id · returns dict | None
    query_agent,            # query by agent + date range · returns list[dict]
    query_jurisdiction,     # query by jurisdiction + date range
    export_jurisdiction,    # zip dump per-jurisdiction (audit handoff)
    record_review,          # PATCH reviewer_id/action/ts · 人审签字
    canonical_hash,         # public hashing helper · for callers that pre-hash
    DEFAULT_DB_PATH,
    DecisionLedger,         # store class (test-injectable)
    default_ledger,         # process-wide singleton
    set_default_ledger,     # test override
)
```

### 2.1 `record_decision(...)` signature

```python
def record_decision(
    *,
    agent_id: str,
    endpoint: str,
    input_payload: dict,
    output_payload: dict,
    evidence_chain: dict,
    decision_id: str | None = None,        # default: uuid4
    jurisdiction: str | None = None,       # default: env or "HQ"
    retention_class: str | None = None,    # default: per-agent table §1.3
    subject_name: str | None = None,
    subject_id: str | None = None,
    ledger: DecisionLedger | None = None,  # test injection
) -> str:
    """Returns decision_id (even on silent-fail · so caller can echo to client).

    Failure isolated per BE7 hard line: a sqlite write error MUST NOT
    break the decision flow. Mirrors Agent3 BE2 graph wrapper pattern.
    Returns the decision_id even when the underlying insert fails so
    callers can still surface the id to clients (frontend) and retry
    via /api/ledger/replay (Phase C).
    """
```

### 2.2 Hash determinism

`input_hash` / `output_hash` = `canonical_hash(payload)`:

```python
def canonical_hash(payload: dict) -> str:
    blob = json.dumps(
        payload, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), default=str,
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()
```

Same payload → same hash, regardless of dict insertion order. Enables tamper-detection in audit replay.

---

## 3. REST endpoints (`ledger_service.api`)

| Method | Path | Purpose | Access |
|---|---|---|---|
| GET | `/api/ledger/decision/{decision_id}` | Single decision lookup | admin |
| GET | `/api/ledger/agent/{agent_id}` | List decisions by agent · `from`/`to`/`limit`/`offset` | admin |
| GET | `/api/ledger/jurisdiction/{jurisdiction}` | List decisions by jurisdiction | admin |
| GET | `/api/ledger/audit_export` | Zip stream · `?jurisdiction=&from=&to=` | admin |
| POST | `/api/ledger/{decision_id}/review` | PATCH reviewer_id / action / ts | admin |

Access: 复用 `audit_service.api._resolve_require_user()` 同模式 · `auth_service.dependencies.require_user` lazy import + admin role check · 缺时 stub allow-all (本地 dev 友好)。

---

## 4. Wiring per agent

### 4.1 Agent3 (this sprint · in scope)

`DecisionEngine.run_stream()` 在 `graph_done` 之后新增:

```python
yield "ledger_persisting", None
try:
    decision_id = record_decision(
        agent_id="credit",
        endpoint="/api/credit/decision",
        input_payload=profile,
        output_payload=advice.to_dict(),
        evidence_chain=advice.decision_graph,    # BE2 graph as evidence chain
        subject_name=advice.subject_name,
        # subject_id, jurisdiction, retention_class use defaults
    )
    advice.advice_id = decision_id   # 1:1 reuse · advice_id == ledger decision_id
    yield "ledger_done", {"decision_id": decision_id}
except Exception as exc:
    yield "ledger_done", {"error": f"{type(exc).__name__}: {exc}"}
```

(In practice `record_decision` itself is silent-fail, so the outer try/except is a defensive belt-and-suspenders.)

### 4.2 Agent6 (BE3 sprint · hook ready not wired)

When BE3 lands, `agent_report.api` calls `record_decision(agent_id="report", endpoint="/api/report/v16/fill", evidence_chain=section_supplement_chain, ...)`.

### 4.3 Agent4 / Agent5 (selective)

Optional · only when a decision-grade event happens (`alert.severity == "red"` · `compliance.violation == "blocking"`). Routine scans skip the ledger.

### 4.4 Agent1 / Agent2

Selective per spec. Out of scope for Sprint 2.

---

## 5. Boundaries · 不动 · 不引入

- ❌ **Not LLM-call audit** — that's `audit_service.LLMCall`. Two layers complement, never merge.
- ❌ **Not blocking** — ledger 是观察层不是阻塞层 · 写入失败 silent-fail · decision flow 不破 (per Agent3 BE2 wrapper pattern · per BE7 task brief 红线)
- ❌ **No PII leak** — `subject_id` 必须是 hash (统一社会信用代码 / 身份证号 → SHA-256 truncated 前 16 chars) · plain id 禁入
- ❌ **No ML / embedding** — pure sqlite + canonical hash · same red line as BE2
- ❌ **No new auth surface** — 复用 `auth_service.require_user` · 不重写权限层
- ❌ **No retention enforcement in v1.0** — `retention_class` 字段记录但**不自动清理** · Phase C 加 cron job

---

## 6. Storage location

- Default: `data/ledger/decisions.sqlite`
- Override: env `LIUYE_LEDGER_DB_PATH`
- `.gitignore`: `data/ledger/*.db` + `*.db-journal` + `*.db-wal` (本 sprint 加)
- Backup (Phase C): rsync to S3-compat · daily snapshot

---

## 7. Versioning

- `LEDGER_SCHEMA_VERSION` constant (1.0.0) · breaking schema change → bump major + ALTER TABLE migration
- `LedgerEntry.evidence_chain` 内嵌 `schema_version` (e.g. BE2 graph 1.0.0) — 上层 schema 版本独立追踪

---

## 8. Done criteria (本 sprint)

- [ ] `shared/decision_ledger/{__init__,schema,store,hashing}.py` 实装
- [ ] `ledger_service/api.py` 5 endpoints + `register_ledger_routes(app)` mount
- [ ] `api_server.py` mount call
- [ ] Agent3 `DecisionEngine.run_stream()` ledger_persisting / ledger_done stage
- [ ] `data/ledger/.gitkeep` + `.gitignore` 加 `data/ledger/*.db`
- [ ] `tests/shared/test_decision_ledger.py` 单元测试 (schema / hash / sqlite / silent-fail / jurisdiction filter)
- [ ] `tests/agent_credit/test_decision_engine_ledger.py` 集成测试 (decision flow → ledger entry)
- [ ] CLAUDE.md §3.7.5 active-rule back-write (jurisdiction default + retention class table)
- [ ] CLAUDE.md §10 关键文件 update (`shared/decision_ledger/`, `ledger_service/`)
- [ ] DONE signal `WORKER-B4-CREDIT-BE7-LEDGER-DONE` · trailer `REVIEW-MODE: manual` + `REASONING-EFFORT: medium` + `ELAPSED`
