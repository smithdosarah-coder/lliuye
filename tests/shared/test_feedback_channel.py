# -*- coding: utf-8 -*-
"""shared.feedback_channel 单测.

per cross-agent-feedback-protocol.md v1.0 · Phase A.5 · 2026-05-09.
覆盖 FeedbackEvent / FeedbackType / FeedbackWatcher / emit_feedback /
resolve_feedback_retention (M1) / last_read_id 持久化 (M2).
"""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

from shared.decision_ledger import (
    DecisionLedger,
    RETENTION_LONG,
    RETENTION_SHORT,
    RETENTION_STANDARD,
)
from shared.feedback_channel import (
    FeedbackEvent,
    FeedbackType,
    FeedbackWatcher,
    emit_feedback,
    resolve_feedback_retention,
)


@pytest.fixture
def tmp_ledger(tmp_path):
    """isolated DecisionLedger · 每个 test 独立 sqlite."""
    return DecisionLedger(db_path=tmp_path / "test.sqlite")


@pytest.fixture
def tmp_watcher_state(tmp_path):
    return tmp_path / "watcher_state.sqlite"


_DEFAULT_CONSUMERS = ["riskctrl"]


def _sample_event(
    feedback_type=FeedbackType.LOAN_OUTCOME,
    producer="alert",
    consumers=_DEFAULT_CONSUMERS,
    original_id="dec_orig_xyz",
    payload=None,
):
    # 注意 · consumers=[] 应直接传 [] · 触 ValueError (不 fallback)
    return FeedbackEvent(
        feedback_type=feedback_type,
        producer_agent=producer,
        consumer_agents=consumers,
        original_decision_id=original_id,
        subject_entity_key="uscc_91440300708461136T",
        payload=payload or {"loan_id": "L000001", "days_past_due": 90, "outcome": "default"},
    )


class TestFeedbackType:
    def test_4_types_locked(self):
        # ABI lock · 4 值不许改
        assert FeedbackType.APPROVAL_OVERRIDE.value == "approval_override"
        assert FeedbackType.LOAN_OUTCOME.value == "loan_outcome"
        assert FeedbackType.POLICY_VIOLATION.value == "policy_violation"
        assert FeedbackType.SCORE_DRIFT.value == "score_drift"

    def test_string_lookup(self):
        assert FeedbackType("loan_outcome") == FeedbackType.LOAN_OUTCOME


class TestFeedbackEvent:
    def test_minimal_event(self):
        evt = _sample_event()
        assert evt.event_id.startswith("fb_")
        assert evt.feedback_type == FeedbackType.LOAN_OUTCOME

    def test_invalid_producer_raises(self):
        with pytest.raises(ValueError, match="不在 6 agent 白名单"):
            _sample_event(producer="hacker")

    def test_invalid_consumer_raises(self):
        with pytest.raises(ValueError, match="不在 6 agent 白名单"):
            _sample_event(consumers=["unknown"])

    def test_empty_consumers_raises(self):
        with pytest.raises(ValueError, match="≥ 1"):
            _sample_event(consumers=[])

    def test_missing_original_decision_id(self):
        with pytest.raises(ValueError, match="original_decision_id"):
            _sample_event(original_id="")

    def test_missing_entity_key(self):
        with pytest.raises(ValueError):
            FeedbackEvent(
                feedback_type=FeedbackType.LOAN_OUTCOME,
                producer_agent="alert",
                consumer_agents=["riskctrl"],
                original_decision_id="dec_x",
                subject_entity_key="",
                payload={},
            )

    def test_to_dict_serializes_enum(self):
        evt = _sample_event()
        d = evt.to_dict()
        assert d["feedback_type"] == "loan_outcome"


class TestResolveRetention:
    """M1 · feedback retention = MAX(consumer retention)."""

    def test_single_riskctrl_standard(self):
        assert resolve_feedback_retention(["riskctrl"]) == RETENTION_STANDARD

    def test_single_alert_short(self):
        assert resolve_feedback_retention(["alert"]) == RETENTION_SHORT

    def test_single_report_long(self):
        assert resolve_feedback_retention(["report"]) == RETENTION_LONG

    def test_max_across_consumers(self):
        # credit (standard) + report (long) → long
        assert resolve_feedback_retention(["credit", "report"]) == RETENTION_LONG
        # riskctrl + credit (both standard) → standard
        assert resolve_feedback_retention(["riskctrl", "credit"]) == RETENTION_STANDARD
        # alert + riskctrl (short + standard) → standard
        assert resolve_feedback_retention(["alert", "riskctrl"]) == RETENTION_STANDARD


class TestEmitFeedback:
    def test_emit_persists_to_ledger(self, tmp_ledger):
        evt = _sample_event()
        result = emit_feedback(evt, ledger=tmp_ledger)
        assert result["ok"]
        assert result["event_id"] == evt.event_id
        assert result["retention_class"] == RETENTION_STANDARD  # consumer riskctrl

    def test_emit_retains_consumer_long(self, tmp_ledger):
        # consumer = report (long retention)
        evt = _sample_event(
            feedback_type=FeedbackType.POLICY_VIOLATION,
            producer="compliance",
            consumers=["credit", "report"],
        )
        result = emit_feedback(evt, ledger=tmp_ledger)
        assert result["retention_class"] == RETENTION_LONG

    def test_emit_then_query(self, tmp_ledger):
        evt = _sample_event()
        emit_feedback(evt, ledger=tmp_ledger)
        rows = tmp_ledger.query_feedback_after(
            last_decision_id=None,
            consumer_agent="riskctrl",
            limit=10,
        )
        assert len(rows) == 1
        assert rows[0]["decision_id"] == evt.event_id
        assert rows[0]["is_feedback"] == 1
        assert rows[0]["feedback_meta"]["feedback_type"] == "loan_outcome"

    def test_query_filters_by_consumer(self, tmp_ledger):
        # event 给 riskctrl · 但 query consumer=alert · 应空
        evt = _sample_event(consumers=["riskctrl"])
        emit_feedback(evt, ledger=tmp_ledger)
        rows = tmp_ledger.query_feedback_after(
            last_decision_id=None, consumer_agent="alert", limit=10,
        )
        assert rows == []


class TestFeedbackWatcher:
    def test_watcher_invalid_consumer(self, tmp_watcher_state):
        with pytest.raises(ValueError):
            FeedbackWatcher(consumer_agent="hacker", state_db_path=tmp_watcher_state)

    def test_watcher_initial_state_empty(self, tmp_ledger, tmp_watcher_state):
        w = FeedbackWatcher(
            consumer_agent="riskctrl",
            ledger=tmp_ledger,
            state_db_path=tmp_watcher_state,
        )
        assert w.get_last_read_id() is None

    def test_subscribe_decorator(self, tmp_ledger, tmp_watcher_state):
        w = FeedbackWatcher(
            consumer_agent="riskctrl",
            ledger=tmp_ledger,
            state_db_path=tmp_watcher_state,
        )

        @w.subscribe(FeedbackType.LOAN_OUTCOME)
        def my_handler(evt):
            pass

        assert w.list_subscribers() == {"loan_outcome": 1}

    def test_poll_once_no_events(self, tmp_ledger, tmp_watcher_state):
        w = FeedbackWatcher(
            consumer_agent="riskctrl",
            ledger=tmp_ledger,
            state_db_path=tmp_watcher_state,
        )
        assert w.poll_once() == 0

    def test_poll_once_dispatches(self, tmp_ledger, tmp_watcher_state):
        w = FeedbackWatcher(
            consumer_agent="riskctrl",
            ledger=tmp_ledger,
            state_db_path=tmp_watcher_state,
        )
        received = []

        @w.subscribe(FeedbackType.LOAN_OUTCOME)
        def collect(evt):
            received.append(evt)

        emit_feedback(_sample_event(), ledger=tmp_ledger)
        emit_feedback(_sample_event(payload={"loan_id": "L2"}), ledger=tmp_ledger)
        consumed = w.poll_once()
        assert consumed == 2
        assert len(received) == 2
        assert received[0].feedback_type == FeedbackType.LOAN_OUTCOME

    def test_last_read_id_persisted(self, tmp_ledger, tmp_watcher_state):
        """M2 · poll 后 last_read_id 应持久化 · 重启续读不重复."""
        w1 = FeedbackWatcher(
            consumer_agent="riskctrl",
            ledger=tmp_ledger,
            state_db_path=tmp_watcher_state,
        )

        @w1.subscribe(FeedbackType.LOAN_OUTCOME)
        def _h1(evt): pass

        emit_feedback(_sample_event(), ledger=tmp_ledger)
        emit_feedback(_sample_event(payload={"loan_id": "L2"}), ledger=tmp_ledger)
        w1.poll_once()
        last_id = w1.get_last_read_id()
        assert last_id is not None

        # 模拟重启 · 新 watcher 同 state_db
        w2 = FeedbackWatcher(
            consumer_agent="riskctrl",
            ledger=tmp_ledger,
            state_db_path=tmp_watcher_state,
        )
        received_after_restart = []

        @w2.subscribe(FeedbackType.LOAN_OUTCOME)
        def _h2(evt):
            received_after_restart.append(evt)

        # 没新 event · 不应 re-fire
        consumed = w2.poll_once()
        assert consumed == 0
        assert len(received_after_restart) == 0

        # emit 新 event · 应只拉新的
        emit_feedback(_sample_event(payload={"loan_id": "L3"}), ledger=tmp_ledger)
        consumed = w2.poll_once()
        assert consumed == 1
        assert received_after_restart[0].payload["loan_id"] == "L3"

    def test_subscriber_raise_does_not_block(self, tmp_ledger, tmp_watcher_state):
        """Failure isolation · subscriber raise 不阻塞后续 event + last_read_id 仍前进."""
        w = FeedbackWatcher(
            consumer_agent="riskctrl",
            ledger=tmp_ledger,
            state_db_path=tmp_watcher_state,
        )
        good = []

        @w.subscribe(FeedbackType.LOAN_OUTCOME)
        def bad_handler(evt):
            raise RuntimeError("simulated subscriber failure")

        @w.subscribe(FeedbackType.LOAN_OUTCOME)
        def good_handler(evt):
            good.append(evt.event_id)

        emit_feedback(_sample_event(), ledger=tmp_ledger)
        consumed = w.poll_once()
        assert consumed == 1
        assert len(good) == 1
        assert w.get_last_read_id() is not None

    def test_only_dispatches_subscribed_type(self, tmp_ledger, tmp_watcher_state):
        w = FeedbackWatcher(
            consumer_agent="riskctrl",
            ledger=tmp_ledger,
            state_db_path=tmp_watcher_state,
        )
        loan_received = []

        @w.subscribe(FeedbackType.LOAN_OUTCOME)
        def _h(evt):
            loan_received.append(evt)

        # emit LOAN_OUTCOME + APPROVAL_OVERRIDE · only LOAN_OUTCOME 触 callback
        emit_feedback(_sample_event(feedback_type=FeedbackType.LOAN_OUTCOME), ledger=tmp_ledger)
        emit_feedback(
            _sample_event(
                feedback_type=FeedbackType.APPROVAL_OVERRIDE,
                producer="credit",
                payload={"ruleset_id": "rs_x"},
            ),
            ledger=tmp_ledger,
        )
        consumed = w.poll_once()
        assert consumed == 2  # 都消费 (last_read_id 前进)
        assert len(loan_received) == 1  # 但 callback 只触 1 次

    def test_get_state(self, tmp_ledger, tmp_watcher_state):
        w = FeedbackWatcher(
            consumer_agent="riskctrl",
            ledger=tmp_ledger,
            state_db_path=tmp_watcher_state,
        )
        # 启动前
        s = w.get_state()
        assert s["consumer_agent"] == "riskctrl"
        assert s["last_read_id"] is None

        emit_feedback(_sample_event(), ledger=tmp_ledger)

        @w.subscribe(FeedbackType.LOAN_OUTCOME)
        def _h(evt): pass

        w.poll_once()
        s = w.get_state()
        assert s["last_read_id"] is not None
        assert s["total_polls"] == 1
        assert s["total_events"] == 1


class TestPollEnvOverride:
    def test_env_poll_seconds(self, tmp_ledger, tmp_watcher_state, monkeypatch):
        monkeypatch.setenv("LIUYE_FEEDBACK_POLL_SEC", "30")
        w = FeedbackWatcher(
            consumer_agent="riskctrl",
            ledger=tmp_ledger,
            state_db_path=tmp_watcher_state,
        )
        assert w.poll_seconds == 30

    def test_explicit_overrides_env(self, tmp_ledger, tmp_watcher_state, monkeypatch):
        monkeypatch.setenv("LIUYE_FEEDBACK_POLL_SEC", "30")
        w = FeedbackWatcher(
            consumer_agent="riskctrl",
            ledger=tmp_ledger,
            state_db_path=tmp_watcher_state,
            poll_seconds=10,
        )
        assert w.poll_seconds == 10

    def test_default_300(self, tmp_ledger, tmp_watcher_state):
        w = FeedbackWatcher(
            consumer_agent="riskctrl",
            ledger=tmp_ledger,
            state_db_path=tmp_watcher_state,
        )
        assert w.poll_seconds == 300


class TestAsyncStartStop:
    @pytest.mark.asyncio
    async def test_start_stop(self, tmp_ledger, tmp_watcher_state):
        w = FeedbackWatcher(
            consumer_agent="riskctrl",
            ledger=tmp_ledger,
            state_db_path=tmp_watcher_state,
            poll_seconds=1,  # short for test
        )

        @w.subscribe(FeedbackType.LOAN_OUTCOME)
        def _h(evt): pass

        task = w.start()
        assert task is not None
        # short sleep to let one poll cycle run
        await asyncio.sleep(0.1)
        await w.stop(timeout=2.0)
        assert task.done()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
