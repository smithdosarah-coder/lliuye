# -*- coding: utf-8 -*-
"""IM service · /ws/im FastAPI WebSocket handler (Stage D.2 · onboarding W-D2-A3).

按 docs/contracts/im-protocol.md §4:
- URL: ws://.../ws/im?token=<jwt>
- inbound: subscribe / typing / ack_read / resync
- outbound: message / typing / agent_progress / agent_output / error
- 重连: client 端 backoff (1→30s) · server 端 idle 60s ping/pong (FastAPI/WS 自带)

ConnectionManager:
- 维护 user_sockets[user_id] = list[WebSocket]
- broadcast_to_thread(thread_id, payload) · 查 thread.participants · 推所有在线 socket
- 单进程 demo 级 · 多 worker 后续 Redis pub/sub

不调真 LLM · LLM tool calling 是 D.4 后续 worker · 本批 WebSocket 只做"广播 + 持久化"。
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

from fastapi import WebSocket, WebSocketDisconnect, WebSocketException, status
from starlette.websockets import WebSocketState

from . import threads as threads_db
from .auth import TokenInvalidError, decode_token


class ConnectionManager:
    """单进程 in-memory connection registry."""

    def __init__(self) -> None:
        self._user_sockets: dict[str, list[WebSocket]] = {}
        self._broadcast_lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """websocket.accept() 已在外层调过 · 仅注册."""
        self._user_sockets.setdefault(user_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        sockets = self._user_sockets.get(user_id) or []
        if websocket in sockets:
            sockets.remove(websocket)
        if not sockets:
            self._user_sockets.pop(user_id, None)

    def online_users(self) -> list[str]:
        return sorted(self._user_sockets.keys())

    def is_online(self, user_id: str) -> bool:
        return bool(self._user_sockets.get(user_id))

    async def send_to_user(self, user_id: str, payload: dict) -> int:
        """向指定 user 所有 socket 推 payload · 返成功 send 次数."""
        sockets = list(self._user_sockets.get(user_id) or [])
        n = 0
        for ws in sockets:
            if ws.client_state != WebSocketState.CONNECTED:
                continue
            try:
                await ws.send_text(json.dumps(payload, ensure_ascii=False, default=str))
                n += 1
            except (RuntimeError, WebSocketDisconnect, ConnectionError):
                # 连接已断 · 清理但不阻断其他 socket
                self.disconnect(ws, user_id)
        return n

    async def broadcast_to_thread(
        self,
        thread_id: str,
        payload: dict,
        *,
        exclude_user: Optional[str] = None,
    ) -> dict[str, int]:
        """查 thread.participants · 给所有非 exclude_user 在线 user 推 payload."""
        async with self._broadcast_lock:
            try:
                thread = threads_db.get_thread(thread_id)
            except KeyError:
                return {}
            participants = thread.get("participants") or []
            stats: dict[str, int] = {}
            for uid in participants:
                if exclude_user and uid == exclude_user:
                    continue
                n = await self.send_to_user(uid, payload)
                if n:
                    stats[uid] = n
            return stats


# Module-level singleton (单进程 demo)
manager = ConnectionManager()


# ---------------------------------------------------------------------------
# WebSocket endpoint handler
# ---------------------------------------------------------------------------


async def im_websocket_endpoint(websocket: WebSocket, token: str = "") -> None:
    """主 endpoint · 由 FastAPI 路由调用.

    - query token 解 user_id · 失败 close 1008 (policy violation)
    - accept · 注册 connection
    - loop receive json · dispatch by `type`
    - WebSocketDisconnect → cleanup
    """
    try:
        user_id = decode_token(token)
    except TokenInvalidError:
        # 拒绝连接前必须 accept · 然后 close · 或直接 raise WebSocketException
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    await manager.connect(websocket, user_id)
    try:
        # greeting (per protocol · 让前端确认 server 状态)
        await websocket.send_text(json.dumps({
            "type": "system",
            "message": "connected",
            "user_id": user_id,
        }, ensure_ascii=False))

        while True:
            raw = await websocket.receive_text()
            try:
                evt = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "code": "PARSE_ERROR",
                    "message": "invalid json",
                }))
                continue

            await _handle_inbound(websocket, user_id, evt)
    except WebSocketDisconnect:
        pass
    except (RuntimeError, ConnectionError):
        pass
    finally:
        manager.disconnect(websocket, user_id)


async def _handle_inbound(websocket: WebSocket, user_id: str, evt: dict) -> None:
    """dispatch by evt.type · subscribe / typing / ack_read / resync."""
    etype = evt.get("type")
    thread_id = evt.get("thread_id") or ""

    if etype in {"subscribe", "ack_read"}:
        # subscribe / ack_read 不真持久 (read 走 REST POST /threads/{id}/read 主线)
        # 仅校验 thread 存在性 + 用户参与权
        if not _check_membership(websocket, user_id, thread_id):
            return
        await websocket.send_text(json.dumps({
            "type": "ack",
            "ack_for": etype,
            "thread_id": thread_id,
        }))
        return

    if etype == "typing":
        if not _check_membership(websocket, user_id, thread_id):
            return
        # broadcast typing to other participants (排除自己)
        await manager.broadcast_to_thread(
            thread_id,
            {"type": "typing", "thread_id": thread_id, "user_id": user_id},
            exclude_user=user_id,
        )
        return

    if etype == "resync":
        if not _check_membership(websocket, user_id, thread_id):
            return
        since = str(evt.get("since") or "")
        msgs = threads_db.list_messages_since(thread_id, since=since) if since else []
        await websocket.send_text(json.dumps({
            "type": "resync",
            "thread_id": thread_id,
            "messages": msgs,
        }, ensure_ascii=False, default=str))
        return

    # 未知 type
    await websocket.send_text(json.dumps({
        "type": "error",
        "code": "UNKNOWN_TYPE",
        "message": f"unknown event type: {etype}",
    }))


def _check_membership(websocket: WebSocket, user_id: str, thread_id: str) -> bool:
    """同步校验 · 失败立即 send 错误 · 返 False 让 caller 跳过广播."""
    if not thread_id:
        return False
    if not threads_db.thread_has_participant(thread_id, user_id):
        # 不 await 这里 · 用 asyncio.create_task 也可 · 简化先同步 close 不阻断
        # 但 send_text 是 coro · caller 已是 async · 我们这里需要发 error
        # 改为返 False · 让 caller 忽略
        return False
    return True
