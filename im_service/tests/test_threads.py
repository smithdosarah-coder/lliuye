# -*- coding: utf-8 -*-
"""Pytest for im_service.threads · sqlite schema + CRUD (Stage D.3)."""
from __future__ import annotations

import pytest

from im_service import threads as db


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """每个 test 独立 sqlite · tmp_path 隔离."""
    test_db = tmp_path / "im_test.db"
    monkeypatch.setattr(db, "_db_path", test_db)
    db.init_schema()
    yield test_db


# ---------------------------------------------------------------------------
# Thread CRUD
# ---------------------------------------------------------------------------


def test_init_schema_idempotent(fresh_db):
    db.init_schema()
    db.init_schema()
    assert db.stats() == {"threads": 0, "messages": 0}


def test_create_thread_group(fresh_db):
    t = db.create_thread(
        title="审贷会 · 中锐网络",
        participants=["u_wangzhe", "u_lihua", "u_zhoumin"],
        kind="group",
        customer_id="cust_zhongrui",
    )
    assert t["id"].startswith("thr_")
    assert t["title"] == "审贷会 · 中锐网络"
    assert sorted(t["participants"]) == ["u_lihua", "u_wangzhe", "u_zhoumin"]
    assert t["kind"] == "group"
    assert t["customer_id"] == "cust_zhongrui"
    assert t["unread_count"] == 0


def test_create_thread_dm(fresh_db):
    t = db.create_thread(
        title="王哲 ↔ 李华",
        participants=["u_wangzhe", "u_lihua"],
        kind="dm",
    )
    assert t["id"].startswith("dm_")
    assert t["kind"] == "dm"


def test_create_thread_validates_kind(fresh_db):
    with pytest.raises(ValueError):
        db.create_thread(title="x", participants=["u_a"], kind="invalid")


def test_create_thread_requires_participants(fresh_db):
    with pytest.raises(ValueError):
        db.create_thread(title="x", participants=[])


def test_get_thread_not_found(fresh_db):
    with pytest.raises(KeyError):
        db.get_thread("no-such-thread")


def test_list_threads_filtered_by_user(fresh_db):
    """list_threads_for_user 仅返 user 在 participants 里的."""
    db.create_thread(title="t-A", participants=["u_a", "u_b"])
    db.create_thread(title="t-B", participants=["u_b", "u_c"])
    db.create_thread(title="t-C", participants=["u_a", "u_c"])

    a_threads = db.list_threads_for_user("u_a")
    assert {t["title"] for t in a_threads} == {"t-A", "t-C"}

    b_threads = db.list_threads_for_user("u_b")
    assert {t["title"] for t in b_threads} == {"t-A", "t-B"}

    # unknown user → 空
    assert db.list_threads_for_user("u_unknown") == []


def test_list_threads_sorted_by_last_message_at(fresh_db):
    """新消息触发 last_message_at update · list 应按 desc."""
    import time

    t1 = db.create_thread(title="first", participants=["u_a"])
    time.sleep(0.01)
    t2 = db.create_thread(title="second", participants=["u_a"])
    time.sleep(0.01)
    db.insert_message(thread_id=t1["id"], from_id="u_a", content="bump-first")

    threads = db.list_threads_for_user("u_a")
    # t1 最新消息 → 应在最前
    assert threads[0]["id"] == t1["id"]
    assert threads[1]["id"] == t2["id"]


def test_thread_has_participant(fresh_db):
    t = db.create_thread(title="x", participants=["u_a", "u_b"])
    assert db.thread_has_participant(t["id"], "u_a")
    assert db.thread_has_participant(t["id"], "u_b")
    assert not db.thread_has_participant(t["id"], "u_c")
    assert not db.thread_has_participant("nope", "u_a")


def test_mark_thread_read_clears_unread(fresh_db):
    t = db.create_thread(title="x", participants=["u_a", "u_b"])
    db.insert_message(thread_id=t["id"], from_id="u_a", content="hi")
    db.insert_message(thread_id=t["id"], from_id="u_a", content="hi2")
    refreshed = db.get_thread(t["id"])
    assert refreshed["unread_count"] == 2

    after_read = db.mark_thread_read(t["id"], "u_b")
    assert after_read["unread_count"] == 0


def test_mark_thread_read_403_when_not_participant(fresh_db):
    t = db.create_thread(title="x", participants=["u_a"])
    with pytest.raises(PermissionError):
        db.mark_thread_read(t["id"], "u_outsider")
