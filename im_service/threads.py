# -*- coding: utf-8 -*-
"""IM service · sqlite store for threads + messages (Stage D.3 · onboarding W-D2-A3).

Schema 严格按 docs/contracts/im-protocol.md §3.1:
- threads (id, title, customer_id, kind, participants JSON array, last_message_at, unread_count, created_at)
- messages (id, thread_id, from_id, kind, content, refs JSON, created_at)

CRUD funcs · sqlite stdlib (无第三方 dep) · 单线程 demo · 多 worker 后续 PG 迁移。
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "im" / "threads.db"

# 允许测试 monkeypatch 改 DB_PATH (替代全局 const · 仍可读)
_db_path: Path = DEFAULT_DB_PATH
_lock = threading.Lock()


def configure_db_path(path: str | Path) -> None:
    """切换 sqlite 文件路径（测试用 / 隔离 tmp_path）."""
    global _db_path
    _db_path = Path(path)
    _db_path.parent.mkdir(parents=True, exist_ok=True)


def get_db_path() -> Path:
    return _db_path


# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

DDL = """
CREATE TABLE IF NOT EXISTS threads (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  customer_id TEXT,
  kind TEXT NOT NULL DEFAULT 'group',
  participants TEXT NOT NULL,
  last_message_at TEXT NOT NULL,
  unread_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  thread_id TEXT NOT NULL REFERENCES threads(id),
  from_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  content TEXT NOT NULL,
  refs TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_thread_at
  ON messages(thread_id, created_at);

CREATE INDEX IF NOT EXISTS idx_threads_last_at
  ON threads(last_message_at);
"""


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    """thread-safe 连接上下文 · 确保 schema 存在 · WAL 模式利于多读单写."""
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        conn = sqlite3.connect(str(_db_path), isolation_level=None, timeout=10.0)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.executescript(DDL)
            yield conn
        finally:
            conn.close()


def init_schema() -> None:
    """显式初始化 · idempotent (DDL 用 IF NOT EXISTS)."""
    with _conn():
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """microseconds 精度 · 避免 1 秒内多消息 created_at 撞 (resync / sort 都依赖 ASC 严格序)."""
    return datetime.now().isoformat(timespec="microseconds")


def _new_thread_id(kind: str) -> str:
    prefix = "dm" if kind == "dm" else "thr"
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _new_message_id() -> str:
    return f"msg_{uuid.uuid4().hex[:14]}"


def _row_to_thread(row: sqlite3.Row) -> dict[str, Any]:
    try:
        participants = json.loads(row["participants"])
    except (TypeError, ValueError):
        participants = []
    return {
        "id": row["id"],
        "title": row["title"],
        "customer_id": row["customer_id"],
        "kind": row["kind"],
        "participants": participants,
        "last_message_at": row["last_message_at"],
        "unread_count": row["unread_count"],
        "created_at": row["created_at"],
    }


def _row_to_message(row: sqlite3.Row) -> dict[str, Any]:
    refs_raw = row["refs"]
    refs: Any = None
    if refs_raw:
        try:
            refs = json.loads(refs_raw)
        except (TypeError, ValueError):
            refs = None
    return {
        "id": row["id"],
        "thread_id": row["thread_id"],
        "from_id": row["from_id"],
        "kind": row["kind"],
        "content": row["content"],
        "refs": refs,
        "created_at": row["created_at"],
    }


# ---------------------------------------------------------------------------
# Thread CRUD
# ---------------------------------------------------------------------------


def create_thread(
    *,
    title: str,
    participants: list[str],
    kind: str = "group",
    customer_id: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> dict[str, Any]:
    if not participants:
        raise ValueError("participants 至少 1 人")
    if kind not in ("group", "dm"):
        raise ValueError(f"kind must be 'group' or 'dm', got {kind!r}")

    tid = (thread_id or "").strip() or _new_thread_id(kind)
    now = _now_iso()
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO threads (id, title, customer_id, kind, participants,
                                 last_message_at, unread_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (tid, title, customer_id, kind, json.dumps(sorted(set(participants))), now, now),
        )
    return get_thread(tid)


def get_thread(thread_id: str) -> dict[str, Any]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM threads WHERE id=?", (thread_id,),
        ).fetchone()
    if not row:
        raise KeyError(f"thread {thread_id} not found")
    return _row_to_thread(row)


def list_threads_for_user(user_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """列 currentUser 在 participants 里的 thread · 按 last_message_at desc."""
    if not user_id:
        return []
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM threads
            ORDER BY last_message_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    out = []
    for row in rows:
        thread = _row_to_thread(row)
        if user_id in thread["participants"]:
            out.append(thread)
    return out


def thread_has_participant(thread_id: str, user_id: str) -> bool:
    try:
        thread = get_thread(thread_id)
    except KeyError:
        return False
    return user_id in (thread["participants"] or [])


def mark_thread_read(thread_id: str, user_id: str) -> dict[str, Any]:
    """用户已读 · unread_count 清零 · 实际 per-user unread 简化为 thread-level."""
    thread = get_thread(thread_id)
    if user_id not in thread["participants"]:
        raise PermissionError(f"user {user_id} not in thread {thread_id}")
    with _conn() as conn:
        conn.execute(
            "UPDATE threads SET unread_count=0 WHERE id=?",
            (thread_id,),
        )
    return get_thread(thread_id)


# ---------------------------------------------------------------------------
# Message CRUD
# ---------------------------------------------------------------------------


VALID_MESSAGE_KINDS = {
    "text",
    "system_event",
    "handoff_card",
    "file",
    "agent_output",
    "pin_ref",
}


def insert_message(
    *,
    thread_id: str,
    from_id: str,
    kind: str = "text",
    content: str = "",
    refs: Optional[dict] = None,
    bump_unread: bool = True,
) -> dict[str, Any]:
    if kind not in VALID_MESSAGE_KINDS:
        raise ValueError(f"kind must be one of {sorted(VALID_MESSAGE_KINDS)}, got {kind!r}")
    # 验 thread 存在
    get_thread(thread_id)

    mid = _new_message_id()
    now = _now_iso()
    refs_json = json.dumps(refs) if refs else None

    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO messages (id, thread_id, from_id, kind, content, refs, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (mid, thread_id, from_id, kind, content, refs_json, now),
        )
        # update thread last_message_at + unread (除非 system 自身或显式不 bump)
        unread_delta = 1 if (bump_unread and kind != "system_event" and from_id != "system") else 0
        conn.execute(
            """
            UPDATE threads
            SET last_message_at=?, unread_count=unread_count+?
            WHERE id=?
            """,
            (now, unread_delta, thread_id),
        )

    return {
        "id": mid,
        "thread_id": thread_id,
        "from_id": from_id,
        "kind": kind,
        "content": content,
        "refs": refs,
        "created_at": now,
    }


def list_messages(
    thread_id: str,
    *,
    before: Optional[str] = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """按 created_at ASC 列 · before 是 cursor (created_at) · limit 默认 50."""
    limit = max(1, min(int(limit or 50), 500))
    with _conn() as conn:
        if before:
            rows = conn.execute(
                """
                SELECT * FROM messages
                WHERE thread_id=? AND created_at < ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (thread_id, before, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM messages
                WHERE thread_id=?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (thread_id, limit),
            ).fetchall()
    return [_row_to_message(r) for r in rows]


def list_messages_since(thread_id: str, since: str) -> list[dict[str, Any]]:
    """resync · 取 since 之后的所有消息 · ASC 顺序."""
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM messages
            WHERE thread_id=? AND created_at > ?
            ORDER BY created_at ASC
            """,
            (thread_id, since),
        ).fetchall()
    return [_row_to_message(r) for r in rows]


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------


def reset_for_tests() -> None:
    """测试用 · 清空 schema · 不 prod 调用."""
    with _conn() as conn:
        conn.execute("DELETE FROM messages")
        conn.execute("DELETE FROM threads")


def stats() -> dict[str, int]:
    with _conn() as conn:
        thread_n = conn.execute("SELECT COUNT(*) FROM threads").fetchone()[0]
        msg_n = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    return {"threads": int(thread_n), "messages": int(msg_n)}
