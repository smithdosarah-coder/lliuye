# -*- coding: utf-8 -*-
"""auth_service.users — 5 fixed user store with bcrypt password hashes.

Spec: auth-protocol.md §2 · 5 fixed accounts (preserve current shape).
现状 frontend `web/src/app/login/_components/LoginForm.tsx:35-41` PASSWORD_MAP 硬编明文 ·
本模块把密码移到 backend bcrypt hash · frontend Stage D.1 frontend 后续 worker 改用
`POST /api/auth/login` 走真验证 · 不再 view-source 明文。

Demo 期 password 仍取 user 名拼音 (用户 2026-04-27 决议 · 见 LoginForm.tsx:33 注释)。
Production 期换强密码后 bcrypt rehash · 不影响 spec / 不需改代码。
"""
from __future__ import annotations

import os
from typing import Any

import bcrypt

# ----------------------------------------------------------------------------
# bcrypt helpers
# ----------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    """bcrypt hashpw · 12 rounds default cost."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time bcrypt verify · 防 timing attack."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ----------------------------------------------------------------------------
# 5 fixed user · 与 web/src/lib/store/auth-store.ts:14-50 镜像
# ----------------------------------------------------------------------------

# 启动时算一次 bcrypt hash · process-lifetime cache · demo 性能 OK
# Production: 把 hash 落库 (sqlite/pg) · USERS dict 改为 query
def _build_users() -> dict[str, dict[str, Any]]:
    raw: list[tuple[str, str, str, str, str, str]] = [
        # (id, name, role, team, avatar, plain_password)
        ("u_wangzhe", "王哲",  "rm",                 "华东·上海第一支行", "哲", "wangzhe"),
        ("u_lihua",   "李华",  "credit_officer",     "华东·授信审查部",   "华", "lihua"),
        ("u_zhoumin", "周敏",  "compliance_officer", "总部·合规管理部",   "敏", "zhoumin"),
        ("u_chenkai", "陈凯",  "risk_manager",       "总部·风险管理部",   "凯", "chenkai"),
        ("u_liuye",   "刘野",  "admin",              "AI 中台",          "野", "liuye"),
    ]
    return {
        uid: {
            "id": uid,
            "name": name,
            "role": role,
            "team": team,
            "avatar": avatar,
            "password_hash": hash_password(plain),
        }
        for (uid, name, role, team, avatar, plain) in raw
    }


USERS: dict[str, dict[str, Any]] = _build_users()

# Dummy hash for constant-time authenticate (when user_id 不存在 时仍跑一次 verify 防 timing leak).
# 启动时算一次 · 与真 hash 同 cost (12 rounds) · checkpw 必返 False.
_DUMMY_BCRYPT_HASH = hash_password("__dummy_password_never_match__")


def get_user(user_id: str) -> dict[str, Any] | None:
    """Return user dict (含 password_hash) or None if not exist."""
    return USERS.get(user_id)


def get_user_public(user_id: str) -> dict[str, Any] | None:
    """Return user dict 不含 password_hash · 用于 /me / /login response."""
    u = USERS.get(user_id)
    if not u:
        return None
    return {k: v for k, v in u.items() if k != "password_hash"}


def list_user_ids() -> list[str]:
    return list(USERS.keys())


def authenticate(user_id: str, password: str) -> dict[str, Any] | None:
    """Return public user dict on success · None on failure (constant-time)."""
    u = USERS.get(user_id)
    if not u:
        # 仍跑一次真 bcrypt verify · 防 timing attack reveal user_id 存在性
        verify_password(password, _DUMMY_BCRYPT_HASH)
        return None
    if not verify_password(password, u["password_hash"]):
        return None
    return get_user_public(user_id)


def rehash_for_test(user_id: str, plain: str) -> None:
    """Test helper · 替换 user password (in-memory only · process restart 还原)."""
    if user_id in USERS:
        USERS[user_id]["password_hash"] = hash_password(plain)
