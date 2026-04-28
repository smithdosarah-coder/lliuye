# -*- coding: utf-8 -*-
"""Pytest for REST endpoints (FastAPI TestClient) · /api/im/threads + /messages."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """整 FastAPI app · 隔离 sqlite db 到 tmp_path · 复用 demo token."""
    from im_service import threads as db
    test_db = tmp_path / "im_rest.db"
    monkeypatch.setattr(db, "_db_path", test_db)

    import api_server  # noqa: WPS433
    return TestClient(api_server.app)


WANG = "demo-u_wangzhe"
LIHUA = "demo-u_lihua"
ZHOU = "demo-u_zhoumin"


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_threads_requires_auth(client):
    resp = client.get("/api/im/threads")
    assert resp.status_code == 401
    assert resp.json()["detail"]["error"]["code"] == "MISSING_TOKEN"


def test_threads_rejects_invalid_token(client):
    resp = client.get("/api/im/threads", headers=_h("garbage"))
    assert resp.status_code == 401
    assert resp.json()["detail"]["error"]["code"] == "TOKEN_INVALID"


# ---------------------------------------------------------------------------
# Create + list threads
# ---------------------------------------------------------------------------


def test_create_thread_includes_self(client):
    resp = client.post(
        "/api/im/threads",
        headers=_h(WANG),
        json={"title": "审贷会", "kind": "group", "participants": ["u_lihua", "u_zhoumin"]},
    )
    assert resp.status_code == 200
    t = resp.json()
    assert "u_wangzhe" in t["participants"]
    assert "u_lihua" in t["participants"]
    assert "u_zhoumin" in t["participants"]
    assert t["kind"] == "group"


def test_list_threads_filters_by_caller(client):
    """u_wangzhe 创 thread · u_chenkai 列应不含."""
    client.post(
        "/api/im/threads",
        headers=_h(WANG),
        json={"title": "wang only", "kind": "group", "participants": []},
    )
    resp_wang = client.get("/api/im/threads", headers=_h(WANG))
    assert resp_wang.status_code == 200
    titles = [t["title"] for t in resp_wang.json()["threads"]]
    assert "wang only" in titles

    resp_chen = client.get("/api/im/threads", headers=_h("demo-u_chenkai"))
    titles_chen = [t["title"] for t in resp_chen.json()["threads"]]
    assert "wang only" not in titles_chen


# ---------------------------------------------------------------------------
# Send message + persistence + list
# ---------------------------------------------------------------------------


def test_send_message_persisted_and_listed(client):
    create = client.post(
        "/api/im/threads",
        headers=_h(WANG),
        json={"title": "t-send", "kind": "group", "participants": ["u_lihua"]},
    )
    tid = create.json()["id"]

    send = client.post(
        "/api/im/messages",
        headers=_h(WANG),
        json={"thread_id": tid, "content": "hello", "kind": "text"},
    )
    assert send.status_code == 200, send.text
    body = send.json()
    assert body["ack"] == "stored"
    assert body["message"]["content"] == "hello"
    assert body["message"]["from_id"] == "u_wangzhe"

    # list
    resp = client.get(f"/api/im/threads/{tid}/messages", headers=_h(WANG))
    assert resp.status_code == 200
    msgs = resp.json()["messages"]
    assert len(msgs) == 1
    assert msgs[0]["content"] == "hello"


def test_send_message_403_when_not_participant(client):
    """u_chenkai send 非自己的 thread 应 403."""
    create = client.post(
        "/api/im/threads",
        headers=_h(WANG),
        json={"title": "wang-only", "kind": "group", "participants": []},
    )
    tid = create.json()["id"]

    send = client.post(
        "/api/im/messages",
        headers=_h("demo-u_chenkai"),
        json={"thread_id": tid, "content": "intrude"},
    )
    assert send.status_code == 403
    assert send.json()["detail"]["error"]["code"] == "NOT_IN_THREAD"


def test_messages_list_403_when_not_participant(client):
    create = client.post(
        "/api/im/threads",
        headers=_h(WANG),
        json={"title": "wang-only-2", "kind": "group", "participants": []},
    )
    tid = create.json()["id"]
    resp = client.get(f"/api/im/threads/{tid}/messages", headers=_h("demo-u_chenkai"))
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# read marker
# ---------------------------------------------------------------------------


def test_mark_thread_read(client):
    create = client.post(
        "/api/im/threads",
        headers=_h(WANG),
        json={"title": "t-read", "kind": "group", "participants": ["u_lihua"]},
    )
    tid = create.json()["id"]

    client.post(
        "/api/im/messages",
        headers=_h(WANG),
        json={"thread_id": tid, "content": "msg-1"},
    )
    client.post(
        "/api/im/messages",
        headers=_h(WANG),
        json={"thread_id": tid, "content": "msg-2"},
    )

    # u_lihua 标记已读
    resp = client.post(f"/api/im/threads/{tid}/read", headers=_h(LIHUA))
    assert resp.status_code == 200
    assert resp.json()["unread_count"] == 0


# ---------------------------------------------------------------------------
# pin_ref kind (im-protocol §7)
# ---------------------------------------------------------------------------


def test_send_pin_ref_kind_persists_refs(client):
    create = client.post(
        "/api/im/threads",
        headers=_h(WANG),
        json={"title": "t-pin", "kind": "group", "participants": ["u_lihua"]},
    )
    tid = create.json()["id"]

    refs = {"agentId": "channel", "href": "/archive/channel", "fullText": "扫描快照"}
    send = client.post(
        "/api/im/messages",
        headers=_h(WANG),
        json={"thread_id": tid, "content": "看这块", "kind": "pin_ref", "refs": refs},
    )
    assert send.status_code == 200
    assert send.json()["message"]["kind"] == "pin_ref"
    assert send.json()["message"]["refs"] == refs

    # list 验
    resp = client.get(f"/api/im/threads/{tid}/messages", headers=_h(WANG))
    msgs = resp.json()["messages"]
    assert msgs[0]["kind"] == "pin_ref"
    assert msgs[0]["refs"] == refs
