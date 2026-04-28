# -*- coding: utf-8 -*-
"""auth_service.jwt_util — HS256 sign / verify with 24h expiry.

Spec: auth-protocol.md §4 JWT Configuration.
JWT_SECRET_KEY 走 env (.env) · demo 期可 fallback default · production 必填强随机.
"""
from __future__ import annotations

import datetime
import os
from datetime import timedelta, timezone

import jwt as pyjwt

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------

# Demo fallback (Stage E.3 · 2026-04-28 · PIPL 合规收紧)
# - DEV_MODE=true (or 未设 + JWT_SECRET_KEY 缺) → 仍允许 demo secret · dev 体验保留
# - production (DEV_MODE 未设 + JWT_SECRET_KEY 必填) → 缺则 raise · 启动阻断
# - is_demo_secret() health check 仍标 production 配置漏洞
_DEFAULT_DEMO_SECRET = (
    "zhongan-demo-jwt-secret-do-not-use-in-prod-2026-04-28"
)
JWT_ALG = "HS256"
JWT_EXP_HOURS = 24


class JWTConfigError(RuntimeError):
    """production 启动 · JWT_SECRET_KEY 缺 · 阻断."""


def _is_dev_mode() -> bool:
    """DEV_MODE=true 才允许 demo secret fallback."""
    return os.environ.get("DEV_MODE", "").lower() in ("1", "true", "yes")


def _secret() -> str:
    s = os.environ.get("JWT_SECRET_KEY", "").strip()
    if s:
        return s
    if _is_dev_mode():
        return _DEFAULT_DEMO_SECRET
    # production · key 缺 · 但 _secret() 仍要返个 string (不抛 · sign/verify 调用方需要)
    # 实际启动时应调 assert_jwt_config_valid() 阻断 · 此处兜底返 demo secret + log
    import logging
    logging.getLogger(__name__).error(
        "[auth/jwt] JWT_SECRET_KEY 缺 + DEV_MODE 未设 · "
        "production 应阻断启动 · 当前 fallback demo secret (不安全)",
    )
    return _DEFAULT_DEMO_SECRET


def assert_jwt_config_valid() -> None:
    """启动时调 · production (DEV_MODE 未设) 但 JWT_SECRET_KEY 缺 → raise."""
    if _is_dev_mode():
        return
    if not os.environ.get("JWT_SECRET_KEY", "").strip():
        raise JWTConfigError(
            "production 启动 (DEV_MODE 未设) 但 JWT_SECRET_KEY 缺 · "
            "PIPL 合规要求强随机密钥 · 阻断启动 · "
            "生成 key: py -c \"import secrets; print(secrets.token_urlsafe(32))\"",
        )


def is_demo_secret() -> bool:
    """True 时 production health check 应告警."""
    return _secret() == _DEFAULT_DEMO_SECRET


# ----------------------------------------------------------------------------
# Sign / verify
# ----------------------------------------------------------------------------


class JWTError(Exception):
    """统一抛 · endpoint 转 401."""


def issue(user_id: str, role: str, hours: int = JWT_EXP_HOURS) -> str:
    """Return signed JWT string · payload {sub, role, iat, exp}."""
    now = datetime.datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=hours)).timestamp()),
    }
    token = pyjwt.encode(payload, _secret(), algorithm=JWT_ALG)
    # PyJWT 2.x 返 str · 1.x 返 bytes · 兼容
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def verify(token: str) -> dict:
    """Decode + verify signature + exp · raise JWTError on failure."""
    if not token:
        raise JWTError("token 为空")
    try:
        payload = pyjwt.decode(token, _secret(), algorithms=[JWT_ALG])
    except pyjwt.ExpiredSignatureError as e:
        raise JWTError("token 已过期") from e
    except pyjwt.InvalidTokenError as e:
        raise JWTError(f"token 无效: {e}") from e
    if "sub" not in payload or "role" not in payload:
        raise JWTError("token payload 缺 sub/role")
    return payload


def issue_expired(user_id: str, role: str) -> str:
    """Test helper · 签发已过期 token (用于 expired test case)."""
    now = datetime.datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": int((now - timedelta(hours=48)).timestamp()),
        "exp": int((now - timedelta(hours=24)).timestamp()),
    }
    token = pyjwt.encode(payload, _secret(), algorithm=JWT_ALG)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token
