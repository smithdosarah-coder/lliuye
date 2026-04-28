# -*- coding: utf-8 -*-
"""Pytest for WebSocket /ws/im 入口 + ConnectionManager 单元测试.

注: starlette TestClient 的 WebSocket portal 在双 client 并发 receive 上
会卡死 (单 portal 串行 receive · 不支持真并发 broadcast 验证)。
broadcast / typing / resync 走 ConnectionManager 单元测试 (mock WebSocket) ·
真 client 验证留 Stage D 主 CLI 用 websocat 跑。
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketState


# ---------------------------------------------------------------------------
# /ws/im endpoint · auth + greeting + simple inbound
# ---------------------------------------------------------------------------


@pytest.fixture
def client(tmp_path, monkeypatch):
    from im_service import threads as db
    monkeypatch.setattr(db, "_db_path", tmp_path / "im_ws.db")
    db.init_schema()
    import api_server  # noqa: WPS433
    return TestClient(api_server.app)


def test_ws_invalid_token_closes(client):
    """无效 token · WebSocket 应直接 close (1008)."""
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/im?token=garbage"):
            pass


def test_ws_connect_with_demo_token_succeeds(client):
    """demo token connect → 收到 system greeting."""
    with client.websocket_connect("/ws/im?token=demo-u_wangzhe") as ws:
        greet_raw = ws.receive_text()
        greet = json.loads(greet_raw)
        assert greet["type"] == "system"
        assert greet["user_id"] == "u_wangzhe"


def test_ws_subscribe_acks(client):
    """subscribe inbound · 收到 ack."""
    resp = client.post(
        "/api/im/threads",
        headers={"Authorization": "Bearer demo-u_wangzhe"},
        json={"title": "ws-test", "kind": "group", "participants": ["u_lihua"]},
    )
    assert resp.status_code == 200
    tid = resp.json()["id"]

    with client.websocket_connect("/ws/im?token=demo-u_wangzhe") as ws:
        ws.receive_text()  # greeting
        ws.send_text(json.dumps({"type": "subscribe", "thread_id": tid}))
        ack_raw = ws.receive_text()
        ack = json.loads(ack_raw)
        assert ack["type"] == "ack"
        assert ack["ack_for"] == "subscribe"
        assert ack["thread_id"] == tid


def test_ws_unknown_event_type_returns_error(client):
    with client.websocket_connect("/ws/im?token=demo-u_wangzhe") as ws:
        ws.receive_text()  # greeting
        ws.send_text(json.dumps({"type": "weird-event"}))
        evt_raw = ws.receive_text()
        evt = json.loads(evt_raw)
        assert evt["type"] == "error"
        assert evt["code"] == "UNKNOWN_TYPE"


def test_ws_invalid_json_returns_parse_error(client):
    with client.websocket_connect("/ws/im?token=demo-u_wangzhe") as ws:
        ws.receive_text()  # greeting
        ws.send_text("this-is-not-json{{")
        evt_raw = ws.receive_text()
        evt = json.loads(evt_raw)
        assert evt["type"] == "error"
        assert evt["code"] == "PARSE_ERROR"


# ---------------------------------------------------------------------------
# ConnectionManager 单元测试 · 不依赖 TestClient WebSocket
# ---------------------------------------------------------------------------


def _make_mock_ws(name: str = "ws"):
    """构造一个 mock WebSocket · client_state=CONNECTED · send_text 录用."""
    ws = MagicMock(name=name)
    ws.client_state = WebSocketState.CONNECTED
    ws.send_text = AsyncMock(return_value=None)
    return ws


@pytest.mark.asyncio
async def test_manager_register_and_disconnect(tmp_path, monkeypatch):
    from im_service import threads as db
    monkeypatch.setattr(db, "_db_path", tmp_path / "mgr1.db")
    db.init_schema()
    from im_service.websocket import ConnectionManager

    m = ConnectionManager()
    ws_a = _make_mock_ws("a")
    await m.connect(ws_a, "u_wangzhe")
    assert m.is_online("u_wangzhe")
    assert m.online_users() == ["u_wangzhe"]

    m.disconnect(ws_a, "u_wangzhe")
    assert not m.is_online("u_wangzhe")
    assert m.online_users() == []


@pytest.mark.asyncio
async def test_manager_send_to_user_calls_send_text(tmp_path, monkeypatch):
    from im_service import threads as db
    monkeypatch.setattr(db, "_db_path", tmp_path / "mgr2.db")
    db.init_schema()
    from im_service.websocket import ConnectionManager

    m = ConnectionManager()
    ws_a1 = _make_mock_ws("a1")
    ws_a2 = _make_mock_ws("a2")
    await m.connect(ws_a1, "u_wangzhe")
    await m.connect(ws_a2, "u_wangzhe")

    n = await m.send_to_user("u_wangzhe", {"type": "test", "msg": "hi"})
    assert n == 2
    assert ws_a1.send_text.await_count == 1
    assert ws_a2.send_text.await_count == 1


@pytest.mark.asyncio
async def test_manager_broadcast_to_thread_filters_participants(tmp_path, monkeypatch):
    from im_service import threads as db
    monkeypatch.setattr(db, "_db_path", tmp_path / "mgr3.db")
    db.init_schema()
    from im_service.websocket import ConnectionManager

    thread = db.create_thread(title="t", participants=["u_wangzhe", "u_lihua"])

    m = ConnectionManager()
    ws_wang = _make_mock_ws("wang")
    ws_li = _make_mock_ws("li")
    ws_intruder = _make_mock_ws("intruder")
    await m.connect(ws_wang, "u_wangzhe")
    await m.connect(ws_li, "u_lihua")
    await m.connect(ws_intruder, "u_chenkai")  # 非 thread 参与者

    stats = await m.broadcast_to_thread(thread["id"], {"type": "test"})
    assert "u_wangzhe" in stats
    assert "u_lihua" in stats
    assert "u_chenkai" not in stats
    assert ws_wang.send_text.await_count == 1
    assert ws_li.send_text.await_count == 1
    assert ws_intruder.send_text.await_count == 0


@pytest.mark.asyncio
async def test_manager_broadcast_excludes_user(tmp_path, monkeypatch):
    from im_service import threads as db
    monkeypatch.setattr(db, "_db_path", tmp_path / "mgr4.db")
    db.init_schema()
    from im_service.websocket import ConnectionManager

    thread = db.create_thread(title="t", participants=["u_a", "u_b"])

    m = ConnectionManager()
    ws_a = _make_mock_ws("a")
    ws_b = _make_mock_ws("b")
    await m.connect(ws_a, "u_a")
    await m.connect(ws_b, "u_b")

    stats = await m.broadcast_to_thread(thread["id"], {"type": "x"}, exclude_user="u_a")
    assert "u_a" not in stats
    assert "u_b" in stats
    assert ws_a.send_text.await_count == 0
    assert ws_b.send_text.await_count == 1


@pytest.mark.asyncio
async def test_manager_broadcast_unknown_thread_returns_empty(tmp_path, monkeypatch):
    from im_service import threads as db
    monkeypatch.setattr(db, "_db_path", tmp_path / "mgr5.db")
    db.init_schema()
    from im_service.websocket import ConnectionManager

    m = ConnectionManager()
    stats = await m.broadcast_to_thread("no-such-thread", {"type": "x"})
    assert stats == {}


@pytest.mark.asyncio
async def test_manager_send_to_user_skips_disconnected_socket(tmp_path, monkeypatch):
    from im_service import threads as db
    monkeypatch.setattr(db, "_db_path", tmp_path / "mgr6.db")
    db.init_schema()
    from im_service.websocket import ConnectionManager

    m = ConnectionManager()
    ws_dead = _make_mock_ws("dead")
    ws_dead.client_state = WebSocketState.DISCONNECTED
    ws_alive = _make_mock_ws("alive")
    await m.connect(ws_dead, "u_a")
    await m.connect(ws_alive, "u_a")

    n = await m.send_to_user("u_a", {"type": "x"})
    assert n == 1  # 只 alive 那一个收到
    assert ws_dead.send_text.await_count == 0
    assert ws_alive.send_text.await_count == 1
