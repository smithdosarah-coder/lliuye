# -*- coding: utf-8 -*-
"""shared.policy_registry.store — sqlite-backed PolicyRegistry.

Mirrors the threading + silent-fail pattern of
`shared.decision_ledger.store` so the policy_scan path never crashes
because the registry is unavailable. Failure isolation is the same:
every method returns a sentinel (None / [] / False) on sqlite error.

Schema (single sqlite db):
- ``policies``           one row per policy_id family
- ``policy_versions``    one row per immutable revision
- ``policy_clauses``     one row per segmented clause
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .hashing import body_sha as compute_body_sha
from .hashing import clause_id as compute_clause_id
from .hashing import policy_id as compute_policy_id
from .hashing import version_id as compute_version_id
from .schema import (
    POLICY_REGISTRY_SCHEMA_VERSION,
    PolicyClause,
    PolicyDocument,
    PolicyVersion,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "policy_registry" / "policies.sqlite"

# Bound the inline body_text per row · keeps sqlite rows reasonable.
BODY_TEXT_MAX_BYTES = 256 * 1024  # 256 KB

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS policies (
  policy_id     TEXT PRIMARY KEY,
  title         TEXT NOT NULL,
  issuer        TEXT NOT NULL,
  category      TEXT NOT NULL DEFAULT '',
  description   TEXT NOT NULL DEFAULT '',
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS policy_versions (
  version_id     TEXT PRIMARY KEY,
  policy_id      TEXT NOT NULL,
  effective_date TEXT NOT NULL DEFAULT '',
  fetched_at     TEXT NOT NULL,
  body_sha       TEXT NOT NULL,
  source_url     TEXT NOT NULL DEFAULT '',
  body_text      TEXT NOT NULL DEFAULT '',
  clause_count   INTEGER NOT NULL DEFAULT 0,
  superseded_by  TEXT,
  created_at     TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (policy_id) REFERENCES policies(policy_id)
);
CREATE INDEX IF NOT EXISTS idx_versions_policy
  ON policy_versions(policy_id, effective_date);

CREATE TABLE IF NOT EXISTS policy_clauses (
  clause_id        TEXT PRIMARY KEY,
  version_id       TEXT NOT NULL,
  article          TEXT NOT NULL DEFAULT '',
  paragraph_index  INTEGER NOT NULL DEFAULT 0,
  text             TEXT NOT NULL,
  category         TEXT NOT NULL DEFAULT '其他',
  keywords         TEXT NOT NULL DEFAULT '[]',
  threshold        TEXT NOT NULL DEFAULT '{}',
  severity_hint    TEXT NOT NULL DEFAULT 'major',
  created_at       TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (version_id) REFERENCES policy_versions(version_id)
);
CREATE INDEX IF NOT EXISTS idx_clauses_version
  ON policy_clauses(version_id);
CREATE INDEX IF NOT EXISTS idx_clauses_article
  ON policy_clauses(version_id, article, paragraph_index);
"""


def _truncate_text(text: str, max_bytes: int) -> str:
    encoded = (text or "").encode("utf-8")
    if len(encoded) <= max_bytes:
        return text or ""
    return encoded[:max_bytes].decode("utf-8", errors="ignore") + "\n... [truncated]"


@dataclass
class RegisterResult:
    policy_id: str
    version_id: str
    persisted: bool
    is_new_version: bool
    error: str | None = None


class PolicyRegistry:
    """sqlite-backed versioned policy + clause registry.

    Thread-safe via per-call connection + per-instance write lock.
    Silent-fails on sqlite errors so a registry outage never cascades
    into the policy-scan flow.
    """

    schema_version: str = POLICY_REGISTRY_SCHEMA_VERSION

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(_SCHEMA_SQL)
                conn.commit()
        except sqlite3.Error as e:  # pragma: no cover · disk failure
            logger.warning("[policy_registry] schema init failed: %s", e)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def register_version(
        self,
        *,
        title: str,
        issuer: str,
        body_text: str,
        clauses: list[PolicyClause | dict],
        effective_date: str = "",
        fetched_at: str | None = None,
        source_url: str = "",
        category: str = "",
        description: str = "",
    ) -> RegisterResult:
        """Idempotently register a (policy, version, clauses) bundle.

        Computes deterministic policy_id / version_id / clause_id from
        the provided text — re-importing the same policy text returns
        the existing ids without dup rows.

        Returns RegisterResult; never raises sqlite errors upward.
        """
        pid = compute_policy_id(issuer, title)
        bsha = compute_body_sha(body_text)
        vid = compute_version_id(pid, effective_date, bsha)
        fetched = fetched_at or PolicyVersion.now_iso()

        # Hydrate clause dataclasses with computed clause_id when missing.
        normalized_clauses: list[PolicyClause] = []
        for idx, c in enumerate(clauses or []):
            if isinstance(c, PolicyClause):
                normalized_clauses.append(c)
                continue
            if not isinstance(c, dict):
                continue
            article = str(c.get("article") or "")
            # paragraph_index=0 is valid; only fall back to enumerate idx
            # when the key is missing/None (truthy-or would lose 0).
            raw_pi = c.get("paragraph_index")
            para_idx = int(raw_pi if raw_pi is not None else idx)
            text = str(c.get("text") or "").strip()
            if not text:
                continue
            cid = c.get("clause_id") or compute_clause_id(vid, article, para_idx)
            normalized_clauses.append(PolicyClause(
                clause_id=cid,
                version_id=vid,
                article=article,
                paragraph_index=para_idx,
                text=text,
                category=str(c.get("category") or "其他"),
                keywords=list(c.get("keywords") or []),
                threshold=dict(c.get("threshold") or {}),
                severity_hint=str(c.get("severity_hint") or "major"),
            ))

        body_blob = _truncate_text(body_text or "", BODY_TEXT_MAX_BYTES)
        try:
            with self._lock, sqlite3.connect(self.db_path) as conn:
                # policies — INSERT OR IGNORE preserves first-seen metadata.
                conn.execute(
                    """
                    INSERT OR IGNORE INTO policies
                      (policy_id, title, issuer, category, description)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (pid, title, issuer or "", category or "", description or ""),
                )
                # Detect whether this version already existed.
                row = conn.execute(
                    "SELECT 1 FROM policy_versions WHERE version_id = ?",
                    (vid,),
                ).fetchone()
                is_new_version = row is None

                conn.execute(
                    """
                    INSERT OR REPLACE INTO policy_versions (
                      version_id, policy_id, effective_date, fetched_at,
                      body_sha, source_url, body_text, clause_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        vid, pid, effective_date or "", fetched,
                        bsha, source_url or "", body_blob,
                        len(normalized_clauses),
                    ),
                )
                # Replace clauses for this version (idempotent re-import).
                conn.execute(
                    "DELETE FROM policy_clauses WHERE version_id = ?",
                    (vid,),
                )
                conn.executemany(
                    """
                    INSERT INTO policy_clauses (
                      clause_id, version_id, article, paragraph_index,
                      text, category, keywords, threshold, severity_hint
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            c.clause_id, c.version_id, c.article,
                            c.paragraph_index, c.text, c.category,
                            json.dumps(c.keywords, ensure_ascii=False),
                            json.dumps(c.threshold, ensure_ascii=False),
                            c.severity_hint,
                        )
                        for c in normalized_clauses
                    ],
                )
                conn.commit()
            return RegisterResult(
                policy_id=pid, version_id=vid,
                persisted=True, is_new_version=is_new_version,
            )
        except (sqlite3.Error, OSError, ValueError) as exc:
            logger.warning(
                "[policy_registry] register_version failed for %s/%s: %s",
                pid, vid, exc,
            )
            return RegisterResult(
                policy_id=pid, version_id=vid,
                persisted=False, is_new_version=False,
                error=f"{type(exc).__name__}: {exc}",
            )

    def mark_superseded(self, *, old_version_id: str, new_version_id: str) -> bool:
        """Link old → new for diff/audit. Returns True on update success."""
        try:
            with self._lock, sqlite3.connect(self.db_path) as conn:
                cur = conn.execute(
                    "UPDATE policy_versions SET superseded_by = ? "
                    "WHERE version_id = ? AND (superseded_by IS NULL OR superseded_by = '')",
                    (new_version_id, old_version_id),
                )
                conn.commit()
                return cur.rowcount > 0
        except sqlite3.Error as exc:
            logger.warning("[policy_registry] mark_superseded failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_policy(self, policy_id_: str) -> dict[str, Any] | None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM policies WHERE policy_id = ?",
                    (policy_id_,),
                ).fetchone()
            return dict(row) if row else None
        except sqlite3.Error as exc:
            logger.warning("[policy_registry] get_policy failed: %s", exc)
            return None

    def get_version(self, version_id_: str) -> dict[str, Any] | None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM policy_versions WHERE version_id = ?",
                    (version_id_,),
                ).fetchone()
            return dict(row) if row else None
        except sqlite3.Error as exc:
            logger.warning("[policy_registry] get_version failed: %s", exc)
            return None

    def list_versions(self, policy_id_: str) -> list[dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM policy_versions WHERE policy_id = ? "
                    "ORDER BY effective_date DESC, fetched_at DESC",
                    (policy_id_,),
                ).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error as exc:
            logger.warning("[policy_registry] list_versions failed: %s", exc)
            return []

    def latest_version(self, policy_id_: str) -> dict[str, Any] | None:
        rows = self.list_versions(policy_id_)
        return rows[0] if rows else None

    def get_clauses(self, version_id_: str) -> list[dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM policy_clauses WHERE version_id = ? "
                    "ORDER BY paragraph_index ASC, clause_id ASC",
                    (version_id_,),
                ).fetchall()
        except sqlite3.Error as exc:
            logger.warning("[policy_registry] get_clauses failed: %s", exc)
            return []
        out: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            for k in ("keywords", "threshold"):
                v = d.get(k)
                if isinstance(v, str):
                    try:
                        d[k] = json.loads(v)
                    except (ValueError, TypeError):
                        d[k] = [] if k == "keywords" else {}
            out.append(d)
        return out


# ============================================================================
# Default registry (singleton-ish · per process · mirrors decision_ledger)
# ============================================================================

_default_registry: PolicyRegistry | None = None
_default_lock = threading.Lock()


def default_registry() -> PolicyRegistry:
    """Lazy singleton. Env override: ``LIUYE_POLICY_REGISTRY_DB_PATH``."""
    global _default_registry
    if _default_registry is not None:
        return _default_registry
    with _default_lock:
        if _default_registry is not None:
            return _default_registry
        env_path = os.environ.get("LIUYE_POLICY_REGISTRY_DB_PATH")
        path = Path(env_path) if env_path else DEFAULT_DB_PATH
        _default_registry = PolicyRegistry(path)
        return _default_registry


def set_default_registry(registry: PolicyRegistry | None) -> None:
    """Test helper — inject or reset the process-wide default registry."""
    global _default_registry
    with _default_lock:
        _default_registry = registry


# ============================================================================
# Façade · used by callers (agent_compliance, evaluation, ledger)
# ============================================================================


def register_policy_version(
    *,
    title: str,
    issuer: str,
    body_text: str,
    clauses: list[PolicyClause | dict],
    effective_date: str = "",
    fetched_at: str | None = None,
    source_url: str = "",
    category: str = "",
    description: str = "",
    registry: PolicyRegistry | None = None,
) -> RegisterResult:
    target = registry or default_registry()
    return target.register_version(
        title=title, issuer=issuer, body_text=body_text, clauses=clauses,
        effective_date=effective_date, fetched_at=fetched_at,
        source_url=source_url, category=category, description=description,
    )


def get_policy(policy_id_: str, *, registry: PolicyRegistry | None = None) -> dict[str, Any] | None:
    return (registry or default_registry()).get_policy(policy_id_)


def get_version(version_id_: str, *, registry: PolicyRegistry | None = None) -> dict[str, Any] | None:
    return (registry or default_registry()).get_version(version_id_)


def list_versions(policy_id_: str, *, registry: PolicyRegistry | None = None) -> list[dict[str, Any]]:
    return (registry or default_registry()).list_versions(policy_id_)


def latest_version(policy_id_: str, *, registry: PolicyRegistry | None = None) -> dict[str, Any] | None:
    return (registry or default_registry()).latest_version(policy_id_)


def get_clauses(version_id_: str, *, registry: PolicyRegistry | None = None) -> list[dict[str, Any]]:
    return (registry or default_registry()).get_clauses(version_id_)


def mark_superseded(
    *, old_version_id: str, new_version_id: str,
    registry: PolicyRegistry | None = None,
) -> bool:
    return (registry or default_registry()).mark_superseded(
        old_version_id=old_version_id, new_version_id=new_version_id,
    )


__all__ = [
    "DEFAULT_DB_PATH",
    "PolicyRegistry",
    "RegisterResult",
    "default_registry",
    "get_clauses",
    "get_policy",
    "get_version",
    "latest_version",
    "list_versions",
    "mark_superseded",
    "register_policy_version",
    "set_default_registry",
]
