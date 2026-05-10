# -*- coding: utf-8 -*-
"""FeedbackWatcher · 后台拉 ledger feedback event + 派发 subscriber callback.

per cross-agent-feedback-protocol.md §4 (M2 · last_read_id 持久化 + 故障恢复).

设计:
- 启动时 SELECT last_read_id FROM feedback_watcher_state WHERE consumer_agent = ?
- 每次 poll: ledger.query_feedback_after(last_read_id, consumer_agent, limit=100)
- 成功消费一批 → UPDATE last_read_id
- subscriber raise → log error · 继续后续 event (per-event 错误不阻塞 stream)
- watcher 挂 → 重启续读 (last_read_id 持久化在独立 sqlite)
"""
from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Callable, Optional

from .events import FeedbackEvent, FeedbackType

logger = logging.getLogger(__name__)

# 6 agent 白名单 (per CLAUDE.md §11)
_ALLOWED_AGENTS = frozenset({"channel", "report", "credit", "alert", "compliance", "riskctrl"})

# Watcher state sqlite (per consumer · last_read_id 持久化 · M2)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_DB = PROJECT_ROOT / "data" / "ledger" / "feedback_watcher_state.sqlite"

_STATE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS watcher_state (
  consumer_agent  TEXT PRIMARY KEY,
  last_read_id    TEXT,
  last_poll_ts    TEXT,
  total_polls     INTEGER NOT NULL DEFAULT 0,
  total_events    INTEGER NOT NULL DEFAULT 0
);
"""

# Subscriber callback type
SubscriberCallback = Callable[[FeedbackEvent], None]


class FeedbackWatcher:
    """consumer agent 端的 watcher · 后台 cron 拉 ledger + 派发 subscriber.

    Usage (consumer agent 启动时):

        watcher = FeedbackWatcher(consumer_agent="riskctrl")

        @watcher.subscribe(FeedbackType.APPROVAL_OVERRIDE)
        def on_approval_override(evt: FeedbackEvent):
            ...  # riskctrl 自实现 · 触 false_positive_explainer

        @watcher.subscribe(FeedbackType.LOAN_OUTCOME)
        def on_loan_outcome(evt: FeedbackEvent):
            ...

        watcher.start()  # asyncio task

        # 关 (e.g. uvicorn shutdown)
        await watcher.stop()
    """

    DEFAULT_POLL_SEC = 300  # 5 min · production
    DEFAULT_BATCH_LIMIT = 100
    BACKOFF_SECONDS = (5, 15, 60, 300)  # 失败 backoff 序列 · max 300s

    def __init__(
        self,
        consumer_agent: str,
        *,
        ledger: Optional[Any] = None,
        state_db_path: Optional[Path] = None,
        poll_seconds: Optional[int] = None,
        batch_limit: int = DEFAULT_BATCH_LIMIT,
    ) -> None:
        if consumer_agent not in _ALLOWED_AGENTS:
            raise ValueError(f"consumer_agent {consumer_agent!r} 不在 6 agent 白名单")
        self.consumer_agent = consumer_agent
        self.batch_limit = batch_limit

        # poll interval · env override per RFC §4
        env_poll = os.environ.get("LIUYE_FEEDBACK_POLL_SEC", "").strip()
        if poll_seconds is not None:
            self.poll_seconds = poll_seconds
        elif env_poll:
            try:
                self.poll_seconds = int(env_poll)
            except ValueError:
                self.poll_seconds = self.DEFAULT_POLL_SEC
        else:
            self.poll_seconds = self.DEFAULT_POLL_SEC

        # state db (last_read_id 持久化 · M2)
        self.state_db_path = state_db_path or DEFAULT_STATE_DB
        self.state_db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_state_schema()

        # ledger (lazy · 不强 import 启动时)
        self._ledger = ledger

        # subscriber map: FeedbackType → list[callback]
        self._subscribers: dict[FeedbackType, list[SubscriberCallback]] = {}

        # asyncio state
        self._task: Optional[asyncio.Task] = None
        self._stop_event: Optional[asyncio.Event] = None

    # ---- state persistence ----

    def _init_state_schema(self) -> None:
        try:
            with sqlite3.connect(self.state_db_path) as conn:
                conn.executescript(_STATE_SCHEMA_SQL)
                conn.commit()
        except sqlite3.Error as e:
            logger.warning("[feedback_watcher] state schema init failed: %s", e)

    def get_last_read_id(self) -> Optional[str]:
        try:
            with sqlite3.connect(self.state_db_path) as conn:
                row = conn.execute(
                    "SELECT last_read_id FROM watcher_state WHERE consumer_agent = ?",
                    (self.consumer_agent,),
                ).fetchone()
        except sqlite3.Error as e:
            logger.warning("[feedback_watcher] get_last_read_id failed: %s", e)
            return None
        return row[0] if row else None

    def set_last_read_id(self, last_id: str, *, events_count: int = 0) -> None:
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        try:
            with sqlite3.connect(self.state_db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO watcher_state (consumer_agent, last_read_id, last_poll_ts, total_polls, total_events)
                    VALUES (?, ?, ?, 1, ?)
                    ON CONFLICT(consumer_agent) DO UPDATE SET
                      last_read_id = excluded.last_read_id,
                      last_poll_ts = excluded.last_poll_ts,
                      total_polls = total_polls + 1,
                      total_events = total_events + excluded.total_events
                    """,
                    (self.consumer_agent, last_id, ts, events_count),
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.warning("[feedback_watcher] set_last_read_id failed: %s", e)

    def get_state(self) -> dict[str, Any]:
        """introspect state · monitor / debug 用."""
        try:
            with sqlite3.connect(self.state_db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM watcher_state WHERE consumer_agent = ?",
                    (self.consumer_agent,),
                ).fetchone()
        except sqlite3.Error:
            return {"consumer_agent": self.consumer_agent, "last_read_id": None}
        return dict(row) if row else {"consumer_agent": self.consumer_agent, "last_read_id": None}

    # ---- subscriber ----

    def subscribe(self, feedback_type: FeedbackType) -> Callable[[SubscriberCallback], SubscriberCallback]:
        """Decorator · register callback for a feedback type.

        Example:
            @watcher.subscribe(FeedbackType.LOAN_OUTCOME)
            def my_handler(evt: FeedbackEvent): ...
        """
        def decorator(fn: SubscriberCallback) -> SubscriberCallback:
            self._subscribers.setdefault(feedback_type, []).append(fn)
            return fn
        return decorator

    def unsubscribe_all(self) -> None:
        self._subscribers.clear()

    def list_subscribers(self) -> dict[str, int]:
        return {ft.value: len(cbs) for ft, cbs in self._subscribers.items()}

    # ---- poll loop ----

    def _ledger_instance(self) -> Any:
        if self._ledger is not None:
            return self._ledger
        from shared.decision_ledger import default_ledger
        return default_ledger()

    def poll_once(self) -> int:
        """同步 · 单次 poll · 返本次消费的 event 数. 单测 / debug 友好.

        失败隔离:
        - subscriber raise → log + continue 下一 event
        - last_read_id 仅在 batch 全消费完后前进 (失败时退回上一次稳定点)
        - sqlite 错误 → log + 返 0 · 不 raise
        """
        last_id = self.get_last_read_id()
        ledger = self._ledger_instance()
        try:
            rows = ledger.query_feedback_after(
                last_decision_id=last_id,
                consumer_agent=self.consumer_agent,
                limit=self.batch_limit,
            )
        except Exception as e:  # broad · poll 失败不破 watcher
            logger.warning("[feedback_watcher] query_feedback_after raised: %s", e)
            return 0

        if not rows:
            return 0

        consumed = 0
        new_last_id = last_id
        for row in rows:
            try:
                evt = self._row_to_event(row)
            except (ValueError, KeyError) as e:
                logger.warning("[feedback_watcher] skip malformed entry %s: %s", row.get("decision_id"), e)
                # 仍前进 last_read_id (避免循环卡)
                new_last_id = row.get("decision_id", new_last_id)
                consumed += 1
                continue

            callbacks = self._subscribers.get(evt.feedback_type, [])
            for cb in callbacks:
                try:
                    cb(evt)
                except Exception as e:
                    # subscriber raise 不阻塞其他 subscriber + 后续 event
                    logger.error(
                        "[feedback_watcher] subscriber %s raised on %s: %s",
                        cb.__name__, evt.event_id, e,
                    )
            new_last_id = evt.event_id
            consumed += 1

        if new_last_id and new_last_id != last_id:
            self.set_last_read_id(new_last_id, events_count=consumed)
        return consumed

    @staticmethod
    def _row_to_event(row: dict[str, Any]) -> FeedbackEvent:
        """Ledger row → FeedbackEvent · feedback_meta 已被 store 反序列化."""
        meta = row.get("feedback_meta")
        if not isinstance(meta, dict):
            raise ValueError("feedback_meta missing or malformed")
        return FeedbackEvent(
            feedback_type=FeedbackType(meta["feedback_type"]),
            producer_agent=row["agent_id"],
            consumer_agents=list(meta.get("consumer_agents", [])),
            original_decision_id=meta.get("original_decision_id", ""),
            subject_entity_key=meta.get("subject_entity_key", ""),
            payload=dict(meta.get("payload", {})),
            event_id=row["decision_id"],
            ts=row.get("ts", ""),
        )

    async def _poll_loop(self) -> None:
        """async 后台拉 · backoff on failure."""
        backoff_idx = 0
        while not self._stop_event.is_set():
            try:
                consumed = self.poll_once()
                if consumed > 0:
                    logger.debug(
                        "[feedback_watcher] %s consumed %d event",
                        self.consumer_agent, consumed,
                    )
                backoff_idx = 0  # reset on success
                # wait poll_seconds OR stop_event (whichever first)
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_seconds)
                except asyncio.TimeoutError:
                    pass  # continue loop
            except asyncio.CancelledError:
                break
            except Exception as e:  # broad · 单 poll 失败不破 watcher
                wait = self.BACKOFF_SECONDS[min(backoff_idx, len(self.BACKOFF_SECONDS) - 1)]
                logger.warning(
                    "[feedback_watcher] poll loop error: %s · backoff %ds",
                    e, wait,
                )
                backoff_idx += 1
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=wait)
                except asyncio.TimeoutError:
                    pass

    def start(self) -> asyncio.Task:
        """启动 watcher · 在当前 event loop 创建 task."""
        if self._task and not self._task.done():
            return self._task
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._poll_loop())
        return self._task

    async def stop(self, *, timeout: float = 5.0) -> None:
        """优雅 stop · 调用方 await."""
        if not self._task:
            return
        if self._stop_event:
            self._stop_event.set()
        try:
            await asyncio.wait_for(self._task, timeout=timeout)
        except asyncio.TimeoutError:
            self._task.cancel()
        self._task = None
