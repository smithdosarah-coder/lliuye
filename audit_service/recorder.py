# -*- coding: utf-8 -*-
"""audit_service.recorder — sqlite store + LLMCall dataclass + cost / truncate utils.

Schema (per W-E1-A1 onboarding):
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
      error TEXT
    );
    CREATE INDEX idx_user_ts ON llm_calls(user_id, ts);
    CREATE INDEX idx_agent_ts ON llm_calls(agent_id, ts);

Truncate: prompt 4 KB · response 8 KB · 防 sqlite 膨胀。
Cost 估算: tokens × 0.0001 RMB (各 model 单价后续 config 化)。
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

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
  error TEXT
);
CREATE INDEX IF NOT EXISTS idx_user_ts ON llm_calls(user_id, ts);
CREATE INDEX IF NOT EXISTS idx_agent_ts ON llm_calls(agent_id, ts);
"""


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
            conn.commit()

    def record(self, call: LLMCall) -> int:
        """插入一条审计记录 · 返 row id · 失败返 -1 (不抛)."""
        # 应用 truncate (调用方可能传超长 prompt/response)
        prompt = truncate_text(call.prompt, PROMPT_MAX_BYTES)
        response = truncate_text(call.response, RESPONSE_MAX_BYTES)
        # 自动算 cost (若 caller 没填 + tokens 已知)
        cost_cny = call.cost_cny
        if cost_cny is None and (call.input_tokens or call.output_tokens):
            cost_cny = estimate_cost_cny(
                call.input_tokens, call.output_tokens, model=call.model,
            )
        try:
            with self._lock, sqlite3.connect(self.db_path) as conn:
                cur = conn.execute(
                    """
                    INSERT INTO llm_calls (
                      ts, user_id, agent_id, endpoint, model,
                      prompt, response,
                      input_tokens, output_tokens, cost_cny,
                      latency_ms, error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        call.ts, call.user_id, call.agent_id, call.endpoint,
                        call.model, prompt, response,
                        call.input_tokens, call.output_tokens, cost_cny,
                        call.latency_ms, call.error,
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
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """查询审计记录 · 默认按 ts desc · paginated."""
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

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = (
            f"SELECT id, ts, user_id, agent_id, endpoint, model, prompt, response, "
            f"input_tokens, output_tokens, cost_cny, latency_ms, error "
            f"FROM llm_calls {where} "
            f"ORDER BY ts DESC, id DESC LIMIT ? OFFSET ?"
        )
        params_with_paging = params + [int(limit), int(offset)]

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(sql, params_with_paging).fetchall()
            return [dict(r) for r in rows]
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
    limit: int = 100,
    offset: int = 0,
    recorder: AuditRecorder | None = None,
) -> dict[str, Any]:
    """admin endpoint 用 · 返 ``{items, total, limit, offset}`` shape."""
    rec = recorder or default_recorder()
    items = rec.query(
        user_id=user_id, agent_id=agent_id,
        since=since, until=until,
        limit=limit, offset=offset,
    )
    total = rec.count(
        user_id=user_id, agent_id=agent_id,
        since=since, until=until,
    )
    return {
        "items": items,
        "total": total,
        "limit": int(limit),
        "offset": int(offset),
    }


__all__ = [
    "AuditRecorder",
    "DEFAULT_DB_PATH",
    "LLMCall",
    "PROMPT_MAX_BYTES",
    "RESPONSE_MAX_BYTES",
    "default_recorder",
    "estimate_cost_cny",
    "query_calls",
    "set_default_recorder",
    "truncate_text",
]
