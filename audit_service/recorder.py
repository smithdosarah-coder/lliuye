# -*- coding: utf-8 -*-
"""audit_service.recorder — sqlite store + LLMCall dataclass + cost / truncate utils.

Schema (per W-E1-A1 onboarding · ROI #5 2026-05-21 加 e2e_run_id 列):
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
      cost_cny REAL,
      latency_ms INTEGER,
      error TEXT,
      encryption_marker TEXT,      -- Stage E.3 PIPL · null=plain · "aes-gcm-256"=encrypted
      e2e_run_id TEXT              -- ROI #5 · GitHub Actions run_id 串联证据链 · null=非 CI 流量
    );
    CREATE INDEX idx_user_ts ON llm_calls(user_id, ts);
    CREATE INDEX idx_agent_ts ON llm_calls(agent_id, ts);
    CREATE INDEX idx_e2e_run_id ON llm_calls(e2e_run_id) WHERE e2e_run_id IS NOT NULL;

Truncate: prompt 4 KB · response 8 KB · 防 sqlite 膨胀。
Cost 估算: tokens × 0.0001 RMB (各 model 单价后续 config 化)。

ROI #5 (2026-05-21 · E2E 证据链):
  e2e_run_id ContextVar 由 AuditLogMiddleware 从 ``X-Liuye-E2E-Run-Id`` HTTP header
  设置 · ``record()`` 若 LLMCall.e2e_run_id 未填则自动从 contextvar 取 · daily-visual
  workflow 用 ``GET /api/audit/by_run_id/{run_id}`` 拉证据链 artifact.
"""
from __future__ import annotations

import contextvars
import logging
import os
import sqlite3
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# ROI #5 · GitHub Actions run_id contextvar (跨 middleware/decorator/stream_helpers 共享)
# - Middleware (AuditLogMiddleware) 解 X-Liuye-E2E-Run-Id header 后 set
# - record() 默认从这里取 (LLMCall.e2e_run_id 优先 · 显式注入覆盖 ctx)
# - 非 CI 流量 (header 缺) → None → 写 NULL · 老 audit 行向后兼容
e2e_run_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "audit_e2e_run_id", default=None,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "audit" / "llm_calls.db"

PROMPT_MAX_BYTES = 4 * 1024
RESPONSE_MAX_BYTES = 8 * 1024
DEFAULT_TOKEN_RATE_CNY = 0.0001  # 元/token · 粗估 · 各 model 单价后续 config 化

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS llm_calls (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  user_id TEXT,
  agent_id TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  model TEXT NOT NULL,
  prompt TEXT,
  response TEXT,
  input_tokens INTEGER,
  output_tokens INTEGER,
  cost_cny REAL,
  latency_ms INTEGER,
  error TEXT,
  encryption_marker TEXT,  -- Stage E.3 PIPL · null=plain · "aes-gcm-256"=encrypted
  e2e_run_id TEXT          -- ROI #5 · GitHub Actions run_id · null=非 CI 流量
);
CREATE INDEX IF NOT EXISTS idx_user_ts ON llm_calls(user_id, ts);
CREATE INDEX IF NOT EXISTS idx_agent_ts ON llm_calls(agent_id, ts);
-- idx_e2e_run_id 在 ALTER TABLE 之后单独建 · 避免老 db 走 _SCHEMA_SQL 时
-- table 已存在但 e2e_run_id 列没加上 · CREATE INDEX 立即抓 no such column 炸
"""

# Stage E.3 PIPL · 兼容已存在 db (不含 encryption_marker 列) · ALTER TABLE ADD COLUMN
_MIGRATE_ADD_ENCRYPTION_MARKER = (
    "ALTER TABLE llm_calls ADD COLUMN encryption_marker TEXT"
)

# ROI #5 (2026-05-21) · 兼容已存在 db (不含 e2e_run_id 列) · ALTER TABLE ADD COLUMN
# sqlite ADD COLUMN 不锁全表 · 即跑即就绪 · 老行 e2e_run_id=NULL 向后兼容
_MIGRATE_ADD_E2E_RUN_ID = (
    "ALTER TABLE llm_calls ADD COLUMN e2e_run_id TEXT"
)


@dataclass
class LLMCall:
    """单次 LLM 调用审计记录."""

    ts: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    user_id: str | None = None
    agent_id: str = "unknown"
    endpoint: str = ""
    model: str = "unknown"
    prompt: str | None = None
    response: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_cny: float | None = None
    latency_ms: int | None = None
    error: str | None = None
    # ROI #5 · GitHub Actions run_id (X-Liuye-E2E-Run-Id header) · null=非 CI 流量
    e2e_run_id: str | None = None
    id: int | None = None  # set by sqlite after insert

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def truncate_text(s: str | None, max_bytes: int) -> str | None:
    """utf-8 截断 + 末尾标 · 防 sqlite 膨胀."""
    if s is None:
        return None
    if not isinstance(s, str):
        s = str(s)
    encoded = s.encode("utf-8")
    if len(encoded) <= max_bytes:
        return s
    # 二分截断到 utf-8 边界
    return encoded[:max_bytes].decode("utf-8", errors="ignore") + "…[truncated]"


def estimate_cost_cny(
    input_tokens: int | None,
    output_tokens: int | None,
    model: str = "deepseek-chat",
    rate: float = DEFAULT_TOKEN_RATE_CNY,
) -> float | None:
    """简单线性估算 · 不知 token 数返 None."""
    if input_tokens is None and output_tokens is None:
        return None
    total = (input_tokens or 0) + (output_tokens or 0)
    if total == 0:
        return 0.0
    return round(total * rate, 4)


class AuditRecorder:
    """sqlite-backed audit log store.

    线程安全: 每次调用打开独立 connection (sqlite3 不允许跨线程共享 conn ·
    open_per_call 简单可靠 · 写入压力高时再换 pool)。
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(_SCHEMA_SQL)
            # 兼容已存在 db (Stage E.1 创的 · 不含 encryption_marker)
            try:
                conn.execute(_MIGRATE_ADD_ENCRYPTION_MARKER)
            except sqlite3.OperationalError:
                # 列已存在 · ignore
                pass
            # ROI #5 · 兼容已存在 db (Stage E.1/E.3 创的 · 不含 e2e_run_id)
            try:
                conn.execute(_MIGRATE_ADD_E2E_RUN_ID)
            except sqlite3.OperationalError:
                # 列已存在 · ignore
                pass
            # ROI #5 · 兼容已存在 db · idx_e2e_run_id 即跑即就绪
            try:
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_e2e_run_id "
                    "ON llm_calls(e2e_run_id)",
                )
            except sqlite3.OperationalError:
                pass
            conn.commit()

    def record(self, call: LLMCall) -> int:
        """插入一条审计记录 · 返 row id · 失败返 -1 (不抛).

        Stage E.3 PIPL · ENCRYPT_AT_REST=true 时 prompt/response 走 AES-GCM 加密 ·
        encryption_marker 标 'aes-gcm-256' · query() 自动解密.

        ROI #5 · LLMCall.e2e_run_id 未填时从 contextvar 取 (middleware 已 set).
        """
        # 应用 truncate (调用方可能传超长 prompt/response)
        prompt = truncate_text(call.prompt, PROMPT_MAX_BYTES)
        response = truncate_text(call.response, RESPONSE_MAX_BYTES)
        # Stage E.3 · 加密 (ENCRYPT_AT_REST 控 · 默认 false 走明文兼容旧数据)
        from audit_service.encryption import encrypt  # noqa: PLC0415
        prompt_stored, marker_p = encrypt(prompt)
        response_stored, marker_r = encrypt(response)
        # 两边 marker 必同步 (同时启用 / 同时关闭) · 取非空者
        encryption_marker = marker_p or marker_r
        # 自动算 cost (若 caller 没填 + tokens 已知)
        cost_cny = call.cost_cny
        if cost_cny is None and (call.input_tokens or call.output_tokens):
            cost_cny = estimate_cost_cny(
                call.input_tokens, call.output_tokens, model=call.model,
            )
        # ROI #5 · e2e_run_id 优先级: LLMCall.e2e_run_id (显式注入) > contextvar (middleware set)
        e2e_run_id = call.e2e_run_id
        if e2e_run_id is None:
            try:
                e2e_run_id = e2e_run_id_var.get()
            except LookupError:
                e2e_run_id = None
        try:
            with self._lock, sqlite3.connect(self.db_path) as conn:
                cur = conn.execute(
                    """
                    INSERT INTO llm_calls (
                      ts, user_id, agent_id, endpoint, model,
                      prompt, response,
                      input_tokens, output_tokens, cost_cny,
                      latency_ms, error, encryption_marker, e2e_run_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        call.ts, call.user_id, call.agent_id, call.endpoint,
                        call.model, prompt_stored, response_stored,
                        call.input_tokens, call.output_tokens, cost_cny,
                        call.latency_ms, call.error, encryption_marker,
                        e2e_run_id,
                    ),
                )
                conn.commit()
                row_id = cur.lastrowid or -1
                call.id = row_id
                return row_id
        except (sqlite3.Error, OSError) as e:
            logger.warning("[audit_service] sqlite record failed: %s", e)
            return -1

    def query(
        self,
        *,
        user_id: str | None = None,
        agent_id: str | None = None,
        since: str | None = None,
        until: str | None = None,
        e2e_run_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """查询审计记录 · 默认按 ts desc · paginated.

        ROI #5 · e2e_run_id 过滤: 拿单次 GitHub Actions run 的全部 audit (含 6 agent).
        """
        clauses: list[str] = []
        params: list[Any] = []
        if user_id is not None:
            clauses.append("user_id = ?")
            params.append(user_id)
        if agent_id is not None:
            clauses.append("agent_id = ?")
            params.append(agent_id)
        if since is not None:
            clauses.append("ts >= ?")
            params.append(since)
        if until is not None:
            clauses.append("ts < ?")
            params.append(until)
        if e2e_run_id is not None:
            clauses.append("e2e_run_id = ?")
            params.append(e2e_run_id)

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = (
            f"SELECT id, ts, user_id, agent_id, endpoint, model, prompt, response, "
            f"input_tokens, output_tokens, cost_cny, latency_ms, error, "
            f"encryption_marker, e2e_run_id "
            f"FROM llm_calls {where} "
            f"ORDER BY ts DESC, id DESC LIMIT ? OFFSET ?"
        )
        params_with_paging = params + [int(limit), int(offset)]

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(sql, params_with_paging).fetchall()
            # Stage E.3 · 自动解密 prompt/response (encryption_marker 控制)
            from audit_service.encryption import decrypt  # noqa: PLC0415
            decoded: list[dict[str, Any]] = []
            for r in rows:
                d = dict(r)
                marker = d.get("encryption_marker")
                d["prompt"] = decrypt(d.get("prompt"), marker)
                d["response"] = decrypt(d.get("response"), marker)
                decoded.append(d)
            return decoded
        except sqlite3.Error as e:
            logger.warning("[audit_service] sqlite query failed: %s", e)
            return []

    def count(
        self,
        *,
        user_id: str | None = None,
        agent_id: str | None = None,
        since: str | None = None,
        until: str | None = None,
        e2e_run_id: str | None = None,
    ) -> int:
        """同 query · 仅返 count."""
        clauses: list[str] = []
        params: list[Any] = []
        if user_id is not None:
            clauses.append("user_id = ?")
            params.append(user_id)
        if agent_id is not None:
            clauses.append("agent_id = ?")
            params.append(agent_id)
        if since is not None:
            clauses.append("ts >= ?")
            params.append(since)
        if until is not None:
            clauses.append("ts < ?")
            params.append(until)
        if e2e_run_id is not None:
            clauses.append("e2e_run_id = ?")
            params.append(e2e_run_id)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT COUNT(*) AS n FROM llm_calls {where}"
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(sql, params).fetchone()
            return int(row[0]) if row else 0
        except sqlite3.Error as e:
            logger.warning("[audit_service] sqlite count failed: %s", e)
            return 0


# ============================================================================
# Default recorder (singleton-ish · per process)
# ============================================================================

_default_recorder: AuditRecorder | None = None
_default_lock = threading.Lock()


def default_recorder() -> AuditRecorder:
    """惰性初始化 · 测试可用 ``set_default_recorder`` 覆盖.

    支持环境变量 ``AUDIT_DB_PATH`` 改路径 (测试 / 多 instance 隔离用)。
    """
    global _default_recorder
    if _default_recorder is not None:
        return _default_recorder
    with _default_lock:
        if _default_recorder is not None:
            return _default_recorder
        env_path = os.environ.get("AUDIT_DB_PATH")
        path = Path(env_path) if env_path else DEFAULT_DB_PATH
        _default_recorder = AuditRecorder(path)
        return _default_recorder


def set_default_recorder(recorder: AuditRecorder | None) -> None:
    """测试 helper · 注入或重置 default recorder."""
    global _default_recorder
    with _default_lock:
        _default_recorder = recorder


# ============================================================================
# Query helper (admin endpoint 用)
# ============================================================================

def query_calls(
    *,
    user_id: str | None = None,
    agent_id: str | None = None,
    since: str | None = None,
    until: str | None = None,
    e2e_run_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    recorder: AuditRecorder | None = None,
) -> dict[str, Any]:
    """admin endpoint 用 · 返 ``{items, total, limit, offset}`` shape."""
    rec = recorder or default_recorder()
    items = rec.query(
        user_id=user_id, agent_id=agent_id,
        since=since, until=until,
        e2e_run_id=e2e_run_id,
        limit=limit, offset=offset,
    )
    total = rec.count(
        user_id=user_id, agent_id=agent_id,
        since=since, until=until,
        e2e_run_id=e2e_run_id,
    )
    return {
        "items": items,
        "total": total,
        "limit": int(limit),
        "offset": int(offset),
    }


# ============================================================================
# ROI #5 · E2E 证据链 export helper (daily-visual workflow 调)
# ============================================================================

def query_by_run_id(
    run_id: str,
    *,
    limit: int = 1000,
    offset: int = 0,
    recorder: AuditRecorder | None = None,
) -> dict[str, Any]:
    """按 GitHub Actions run_id 拉单次 cron run 的全部 audit 记录.

    Args:
        run_id: ``X-Liuye-E2E-Run-Id`` header (= ``${{ github.run_id }}``)
        limit: 单次最多返 ≤ 5000 (防 artifact 爆 · admin E2E 14 spec × 6 agent
            × ~5 call ≈ 420 record · 加 SSE 中间记录撑死 ~2000 · 5000 留 buffer)
        offset: 分页

    Returns:
        ``{
            run_id, count, agents_hit, endpoints_hit, session_ids,
            errors, total_cost_cny, items,
            limit, offset, has_more
        }``
        · ``count`` = 本次返回行数 (≤ limit)
        · ``agents_hit`` = 出现过的 agent_id 去重 list (用于 Issue 评论提要)
        · ``has_more`` = total > offset+limit (有 next page)
    """
    rec = recorder or default_recorder()
    items = rec.query(e2e_run_id=run_id, limit=limit, offset=offset)
    total = rec.count(e2e_run_id=run_id)

    agents_hit = sorted({r.get("agent_id") for r in items if r.get("agent_id")})
    endpoints_hit = sorted({r.get("endpoint") for r in items if r.get("endpoint")})
    errors = [
        {"endpoint": r.get("endpoint"), "agent_id": r.get("agent_id"), "error": r.get("error")}
        for r in items if r.get("error")
    ]
    total_cost = round(sum((r.get("cost_cny") or 0.0) for r in items), 4)

    return {
        "run_id": run_id,
        "count": len(items),
        "total": total,
        "agents_hit": agents_hit,
        "endpoints_hit": endpoints_hit,
        "session_ids": [],  # 当前 LLMCall schema 无 session_id · 留空 placeholder
        "errors": errors,
        "total_cost_cny": total_cost,
        "items": items,
        "limit": int(limit),
        "offset": int(offset),
        "has_more": total > (int(offset) + len(items)),
    }


__all__ = [
    "AuditRecorder",
    "DEFAULT_DB_PATH",
    "LLMCall",
    "PROMPT_MAX_BYTES",
    "RESPONSE_MAX_BYTES",
    "default_recorder",
    "e2e_run_id_var",
    "estimate_cost_cny",
    "query_by_run_id",
    "query_calls",
    "set_default_recorder",
    "truncate_text",
]
