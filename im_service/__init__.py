"""IM service package · Stage D.2 + D.3 (onboarding W-D2-A3).

按 docs/contracts/im-protocol.md v1.0 实装:
- threads.py · sqlite schema + CRUD (data/im/threads.db)
- schemas.py · Pydantic types (ImThread / ImMessage / ws / REST)
- auth.py    · JWT decode helper (D.1 dep stub · 兼容 auth_service 后续接入)
- websocket.py · /ws/im FastAPI WebSocket + ConnectionManager broadcast
"""
