# -*- coding: utf-8 -*-
"""auth_service · Stage D.1 backend auth + RBAC.

Spec: docs/contracts/auth-protocol.md v1.0 (W-A2-contracts-bootstrap · `4e8310b`).
Onboarding: docs/onboarding/W-D1-A2-auth-rbac-backend.md.

模块:
  users.py        — 5 fixed user · bcrypt password hash store · DEMO_USERS shape 镜像 frontend
  jwt_util.py     — HS256 sign / verify · 24h exp · JWT_SECRET_KEY from env
  rbac.py         — ACCESS matrix 镜像 web/src/lib/store/auth-store.ts:61-67
  dependencies.py — FastAPI Depends factory: require_user / require_agent

入口走 api_server.py 3 endpoint: POST /api/auth/login · GET /api/auth/me · POST /api/auth/logout.
"""
from __future__ import annotations

__all__ = ["users", "jwt_util", "rbac", "dependencies"]
