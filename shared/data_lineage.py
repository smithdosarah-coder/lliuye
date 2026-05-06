"""数据血缘 · 跨决策 → 字段 → 来源系统/表/字段 追溯

per Phase C charter Track B · B1 · 数据血缘模型 (PM 拍板 2026-05-06):

设计:
- 每条 decision_id 关联多条 lineage record
- 每 lineage record: decision_id / field_path / source_system / source_table / source_field /
                    fetched_at / effective_date / transformation / data_tier
- sqlite store · 表 data_lineage (类 ledger pattern · BE7)
- silent fail · 写入失败不阻 main flow (per CLAUDE.md §3.7.5)

证据链 (Codex R3 final 5 联):
    source_field → lineage_id → decision_id → audit_event_id → export_id

使用:
    from shared.data_lineage import LineageRecord, get_lineage_store

    store = get_lineage_store()
    lid = store.record(LineageRecord(
        decision_id="dec-...",
        field_path="customer.income_monthly",
        source_system="crm",
        source_table="t_customer_master",
        source_field="month_income",
        fetched_at="2026-05-06T03:00:00",
        effective_date="2026-04-15",
        transformation="ROUND(月收入_元, 0)",
        data_tier="internal_authoritative",
    ))

    rows = store.query_by_decision("dec-...")
"""
from __future__ import annotations

import sqlite3
import threading
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "ledger" / "data_lineage.sqlite"
DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class LineageRecord:
    """一条字段血缘记录."""

    decision_id: str
    field_path: str  # e.g. "customer.income_monthly" or "advice.recommended_product[0]"
    source_system: str  # "crm" / "ledger" / "agent6_report" / "tavily" / "internal"
    source_table: str = ""  # e.g. "t_customer_master" / 报告 ID
    source_field: str = ""  # 来源字段原名 e.g. "month_income"
    fetched_at: str = ""  # 我们抓取时间 ISO
    effective_date: str = ""  # 数据生效时间 (业务时间) ISO
    transformation: str = ""  # 转换公式/规则 e.g. "ROUND(x,0)" 或 "static mapping"
    data_tier: str = ""  # DataTier 值
    lineage_id: str = field(default_factory=lambda: f"ln-{uuid.uuid4().hex[:12]}")
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class LineageStore:
    """sqlite 血缘存储 · 类 BE7 ledger pattern."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._lock = threading.RLock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS data_lineage (
                    lineage_id TEXT PRIMARY KEY,
                    decision_id TEXT NOT NULL,
                    field_path TEXT NOT NULL,
                    source_system TEXT NOT NULL,
                    source_table TEXT,
                    source_field TEXT,
                    fetched_at TEXT,
                    effective_date TEXT,
                    transformation TEXT,
                    data_tier TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_lineage_decision ON data_lineage(decision_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_lineage_field ON data_lineage(field_path)"
            )
            conn.commit()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path))
        try:
            yield conn
        finally:
            conn.close()

    def record(self, record: LineageRecord) -> str:
        """记录一条血缘 · silent fail · 返 lineage_id."""
        try:
            with self._lock, self._connect() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO data_lineage
                    (lineage_id, decision_id, field_path, source_system, source_table,
                     source_field, fetched_at, effective_date, transformation,
                     data_tier, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.lineage_id, record.decision_id, record.field_path,
                        record.source_system, record.source_table, record.source_field,
                        record.fetched_at, record.effective_date, record.transformation,
                        record.data_tier, record.created_at,
                    ),
                )
                conn.commit()
            return record.lineage_id
        except (sqlite3.Error, OSError, ValueError, TypeError):
            return record.lineage_id  # silent fail per BE7

    def record_many(self, records: list[LineageRecord]) -> list[str]:
        """批量记录."""
        return [self.record(r) for r in records]

    def query_by_decision(self, decision_id: str) -> list[dict]:
        """查询一笔决策的所有血缘 record."""
        try:
            with self._lock, self._connect() as conn:
                cur = conn.execute(
                    "SELECT * FROM data_lineage WHERE decision_id = ? ORDER BY created_at",
                    (decision_id,),
                )
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        except (sqlite3.Error, OSError):
            return []

    def query_by_field(self, field_path: str, *, limit: int = 100) -> list[dict]:
        """查询一字段路径的最近血缘 (跨多决策)."""
        try:
            with self._lock, self._connect() as conn:
                cur = conn.execute(
                    "SELECT * FROM data_lineage WHERE field_path = ? ORDER BY created_at DESC LIMIT ?",
                    (field_path, limit),
                )
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        except (sqlite3.Error, OSError):
            return []

    def stats(self) -> dict:
        """全局统计."""
        try:
            with self._lock, self._connect() as conn:
                total = conn.execute("SELECT COUNT(*) FROM data_lineage").fetchone()[0]
                by_tier = dict(conn.execute(
                    "SELECT data_tier, COUNT(*) FROM data_lineage GROUP BY data_tier"
                ).fetchall())
                by_system = dict(conn.execute(
                    "SELECT source_system, COUNT(*) FROM data_lineage GROUP BY source_system"
                ).fetchall())
                return {
                    "total": total,
                    "by_tier": by_tier,
                    "by_system": by_system,
                }
        except (sqlite3.Error, OSError):
            return {"total": 0}


# 单例
_default_store: Optional[LineageStore] = None
_default_lock = threading.Lock()


def get_lineage_store() -> LineageStore:
    """获取默认 LineageStore 单例."""
    global _default_store
    with _default_lock:
        if _default_store is None:
            _default_store = LineageStore()
        return _default_store


__all__ = [
    "LineageRecord",
    "LineageStore",
    "get_lineage_store",
]
