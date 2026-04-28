# -*- coding: utf-8 -*-
"""Pytest for message insert/list · 6 kind + ordering + cursor pagination."""
from __future__ import annotations

import pytest

from im_service import threads as db


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    test_db = tmp_path / "im_test.db"
    monkeypatch.setattr(db, "_db_path", test_db)
    db.init_schema()
    yield test_db


@pytest.fixture
def sample_thread(fresh_db):
    return db.create_thread(title="t1", participants=["u_a", "u_b"])


# ---------------------------------------------------------------------------
# Insert
# ---------------------------------------------------------------------------


def test_insert_text_message(sample_thread):
    msg = db.insert_message(
        thread_id=sample_thread["id"],
        from_id="u_a",
        kind="text",
        content="hello",
    )
    assert msg["id"].startswith("msg_")
    assert msg["thread_id"] == sample_thread["id"]
    assert msg["kind"] == "text"
    assert msg["content"] == "hello"
    assert msg["refs"] is None


def test_insert_all_six_kinds(sample_thread):
    """im-protocol §5.3 列 6 个 kind · 都应 insert OK."""
    kinds = ["text", "system_event", "handoff_card", "file", "agent_output", "pin_ref"]
    for k in kinds:
        msg = db.insert_message(
            thread_id=sample_thread["id"],
            from_id="u_a" if k != "system_event" else "system",
            kind=k,
            content=f"sample-{k}",
            refs={"k": k},
        )
        assert msg["kind"] == k
        assert msg["refs"] == {"k": k}


def test_insert_invalid_kind_raises(sample_thread):
    with pytest.raises(ValueError):
        db.insert_message(thread_id=sample_thread["id"], from_id="u_a", kind="invalid")


def test_insert_missing_thread_raises(fresh_db):
    with pytest.raises(KeyError):
        db.insert_message(thread_id="no-such", from_id="u_a", content="x")


def test_insert_bumps_unread(sample_thread):
    db.insert_message(thread_id=sample_thread["id"], from_id="u_a", content="m1")
    db.insert_message(thread_id=sample_thread["id"], from_id="u_a", content="m2")
    refreshed = db.get_thread(sample_thread["id"])
    assert refreshed["unread_count"] == 2


def test_system_event_does_not_bump_unread(sample_thread):
    """system event / from='system' 不算 unread 计数（per protocol §5.3）."""
    db.insert_message(
        thread_id=sample_thread["id"], from_id="system",
        kind="system_event", content="Agent1 已启动",
    )
    refreshed = db.get_thread(sample_thread["id"])
    assert refreshed["unread_count"] == 0


# ---------------------------------------------------------------------------
# List · ordering + pagination
# ---------------------------------------------------------------------------


def test_list_messages_ascending(sample_thread):
    """messages 按 created_at ASC · 与 protocol §3.1 idx 一致."""
    import time

    for i in range(5):
        db.insert_message(thread_id=sample_thread["id"], from_id="u_a", content=f"m{i}")
        time.sleep(0.01)

    msgs = db.list_messages(sample_thread["id"])
    assert len(msgs) == 5
    for i, m in enumerate(msgs):
        assert m["content"] == f"m{i}"


def test_list_messages_pagination_before_cursor(sample_thread):
    import time

    inserted = []
    for i in range(8):
        m = db.insert_message(thread_id=sample_thread["id"], from_id="u_a", content=f"m{i}")
        inserted.append(m)
        time.sleep(0.01)

    cursor = inserted[5]["created_at"]
    older = db.list_messages(sample_thread["id"], before=cursor, limit=3)
    # 取 cursor 之前的 m3 / m4 (created_at < cursor) · ASC 顺序 · 限 3 → 取 3 条
    assert len(older) <= 3
    for m in older:
        assert m["created_at"] < cursor


def test_list_messages_limit_clamped(sample_thread):
    """limit 超 500 上限要被 clamp."""
    msgs = db.list_messages(sample_thread["id"], limit=10000)
    # 没 message · 但函数不该崩
    assert msgs == []


def test_list_messages_since_resync(sample_thread):
    """resync · since cursor 之后的 messages."""
    import time

    db.insert_message(thread_id=sample_thread["id"], from_id="u_a", content="old")
    time.sleep(0.01)
    cutoff_msg = db.insert_message(thread_id=sample_thread["id"], from_id="u_a", content="cutoff")
    time.sleep(0.01)
    db.insert_message(thread_id=sample_thread["id"], from_id="u_a", content="new1")
    time.sleep(0.01)
    db.insert_message(thread_id=sample_thread["id"], from_id="u_a", content="new2")

    after = db.list_messages_since(sample_thread["id"], since=cutoff_msg["created_at"])
    contents = [m["content"] for m in after]
    assert contents == ["new1", "new2"]


def test_refs_serialization_roundtrip(sample_thread):
    """refs JSON 字段 roundtrip 不丢字段."""
    refs = {"agentId": "channel", "fullText": "hi", "thumbDataUrl": "data:..."}
    db.insert_message(
        thread_id=sample_thread["id"], from_id="u_a",
        kind="pin_ref", content="title", refs=refs,
    )
    msgs = db.list_messages(sample_thread["id"])
    assert msgs[0]["refs"] == refs
