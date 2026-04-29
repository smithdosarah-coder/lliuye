# -*- coding: utf-8 -*-
"""IM service · auth dep helper (Stage D.2 · onboarding W-D2-A3 §Dependencies).

D.1 已 land · 本模块作 multi-source resolver:

  1. **cookie path** (生产 · W-FIX2 · zhongan_auth httpOnly cookie):
     `decode_jwt_cookie(token)` 走 auth_service.jwt_util.verify · 严格 HS256
  2. **Authorization Bearer / query token path** (legacy · 含 demo fallback):
     `decode_token(token)` 优先 D.1 verify · 失败回退 demo decoder

Demo token 格式 (legacy 路径 / e2e 测试用):
  - "demo-<user_id>"           e.g. "demo-u_wangzhe"
  - "demo-<user_id>.<extras>"  允许后缀扩展但 verify 时只看 user_id

protocol §4.1: ws connect 时 query param `token=<jwt>` · REST 通过 cookie 或
Authorization header 都 OK · 本模块统一接 raw token str 返 user_id。

W-FIX2-A2-im-cookie-auth (2026-04-29):
  - bug 根因: frontend `web/src/lib/api/im.ts` 读 `auth_token` cookie · 但 D.1 真
    cookie 名 `zhongan_auth` + httpOnly (JS 不可读) · resolve 全 fall to demo
  - 修法: backend 各 IM endpoint 加 `zhongan_auth: str | None = Cookie(...)` ·
    优先 cookie · 走 D.1 jwt_util.verify · 失败再退 Authorization / query token
"""
from __future__ import annotations

from typing import Optional


# 5 user 固定账号 (per im-protocol.md §2)
DEMO_USERS = {
    "u_wangzhe":  "客户经理 · 王哲",
    "u_lihua":    "审贷官 · 李华",
    "u_zhoumin":  "合规官 · 周敏",
    "u_chenkai":  "风险经理 · 陈凯",
    "u_liuye":    "admin · 刘野",
}


class TokenInvalidError(ValueError):
    """token 解析失败 / 用户不存在."""


def _try_real_auth_service(token: str) -> Optional[str]:
    """尝试调 D.1 worker 实装的 auth_service · 失败返 None 让 fallback 接."""
    try:
        from auth_service import decode_token  # type: ignore

        result = decode_token(token)
        if isinstance(result, dict):
            uid = result.get("user_id") or result.get("sub")
        elif isinstance(result, str):
            uid = result
        else:
            uid = None
        if uid and uid in DEMO_USERS:
            return uid
        return uid
    except (ImportError, ModuleNotFoundError, AttributeError, ValueError, RuntimeError, OSError):
        return None


def _demo_decode(token: str) -> Optional[str]:
    """fallback decoder · "demo-u_wangzhe" → "u_wangzhe"."""
    if not token:
        return None
    if not token.startswith("demo-"):
        return None
    rest = token[len("demo-"):]
    # 容忍 "demo-u_wangzhe.signature" 格式
    user_id = rest.split(".", 1)[0]
    if user_id in DEMO_USERS:
        return user_id
    return None


def decode_token(token: str) -> str:
    """主入口 · 返 user_id · 失败抛 TokenInvalidError.

    优先尝试真 auth_service (生产) · 失败回退 demo decoder。
    """
    if not token or not isinstance(token, str):
        raise TokenInvalidError("token 不能为空")

    real_uid = _try_real_auth_service(token)
    if real_uid:
        return real_uid

    demo_uid = _demo_decode(token)
    if demo_uid:
        return demo_uid

    raise TokenInvalidError(f"token 解析失败: {token[:16]}...")


def issue_demo_token(user_id: str) -> str:
    """测试 / smoke / 文档用 · 给 5 user 中任一 issue demo token."""
    if user_id not in DEMO_USERS:
        raise ValueError(f"unknown user {user_id} · valid: {sorted(DEMO_USERS)}")
    return f"demo-{user_id}"


# ---------------------------------------------------------------------------
# W-FIX2-A2 · Cookie-based JWT path (zhongan_auth · D.1 jwt_util)
# ---------------------------------------------------------------------------


def decode_jwt_cookie(zhongan_auth: Optional[str]) -> Optional[str]:
    """从 D.1 zhongan_auth cookie 解 JWT 返 user_id (sub) · 失败返 None.

    本 path 严格走 auth_service.jwt_util.verify · 不接受 demo token 格式 ·
    cookie 必须是真 HS256 JWT。Caller 在 None 时应 fallback Authorization /
    query token path (decode_token) 或抛 401。
    """
    if not zhongan_auth or not isinstance(zhongan_auth, str):
        return None
    try:
        from auth_service.jwt_util import JWTError, verify  # type: ignore
    except (ImportError, ModuleNotFoundError):
        return None
    try:
        payload = verify(zhongan_auth)
    except JWTError:
        return None
    sub = payload.get("sub") if isinstance(payload, dict) else None
    if not isinstance(sub, str) or not sub:
        return None
    return sub
