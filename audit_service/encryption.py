# -*- coding: utf-8 -*-
"""audit_service.encryption — AES-GCM at-rest encryption for prompt/response.

Stage E.3 PIPL 合规 (W-E3-A2 · 2026-04-28):
  audit log 含 LLM prompt / response · 可能含 PII (用户姓名 / 企业 USCC / 财务数字).
  PIPL 要求"必要性 · 最小化 · 加密存储". 本模块提供透明加密层.

设计:
  - AES-GCM 256-bit · cryptography.hazmat.primitives.ciphers.aead.AESGCM
  - Key from env AUDIT_ENCRYPTION_KEY (32-byte base64) · 缺则 ENCRYPT_AT_REST=false 走明文 (dev)
  - 每条 record 独立 12-byte nonce · 与 ciphertext 一起 base64 存 (单字段 "<nonce>.<ciphertext>")
  - 解密失败 → 返 "[decrypt failed: ...]" placeholder · 不抛 (admin query 不阻)
  - 启动时 ENCRYPT_AT_REST=true 而 key 缺 · raise · 防 production 配置漏

Audit log 字段:
  prompt / response 仍 TEXT (sqlite) · 内容是 base64-encoded "{nonce}.{ct}" 或 plain (取决 ENCRYPT_AT_REST).
  encryption_marker 字段 (additive · 新加 · _SCHEMA_SQL 兼容旧 row 不强制) 标 "aes-gcm-256" / null (plain).
"""
from __future__ import annotations

import base64
import logging
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

ENCRYPTION_MARKER = "aes-gcm-256"
NONCE_SIZE_BYTES = 12  # AES-GCM 推荐 96-bit nonce
KEY_SIZE_BYTES = 32   # AES-256


class EncryptionError(RuntimeError):
    """加密层 fatal error (config 错 / key 缺) · production 启动阻断."""


def _is_enabled() -> bool:
    """ENCRYPT_AT_REST=true 才启用 · 默认 false (dev / 兼容已有数据)."""
    return os.environ.get("ENCRYPT_AT_REST", "").lower() in ("1", "true", "yes")


def _load_key() -> bytes | None:
    """env AUDIT_ENCRYPTION_KEY (base64-encoded 32 byte) · 失败 raise."""
    raw = os.environ.get("AUDIT_ENCRYPTION_KEY", "").strip()
    if not raw:
        return None
    try:
        decoded = base64.b64decode(raw, validate=True)
    except (ValueError, base64.binascii.Error) as e:
        raise EncryptionError(
            f"AUDIT_ENCRYPTION_KEY 不是合法 base64: {e}",
        ) from e
    if len(decoded) != KEY_SIZE_BYTES:
        raise EncryptionError(
            f"AUDIT_ENCRYPTION_KEY 解码后必须 {KEY_SIZE_BYTES} bytes (AES-256) · 实际 {len(decoded)}",
        )
    return decoded


def assert_config_valid() -> None:
    """启动时调 · ENCRYPT_AT_REST=true 但 key 缺 → raise (production 阻断)."""
    if _is_enabled():
        key = _load_key()
        if key is None:
            raise EncryptionError(
                "ENCRYPT_AT_REST=true 但 AUDIT_ENCRYPTION_KEY 未配 · "
                "PIPL 合规要求加密 at-rest · production 阻断启动",
            )


def encrypt(plain: str | None) -> tuple[str | None, str | None]:
    """加密 plain → (cipher_b64, marker).

    Return:
        (None, None)              if plain is None
        (plain, None)             if ENCRYPT_AT_REST=false (兼容 dev / 已存明文)
        (cipher_b64, MARKER)      if ENCRYPT_AT_REST=true · key 已配
    """
    if plain is None:
        return None, None
    if not _is_enabled():
        return plain, None
    key = _load_key()
    if key is None:
        # ENCRYPT_AT_REST=true 但 key 缺 · assert_config_valid 应已阻断启动
        # 此处兜底 fail-safe: 落明文 + warn (不阻当前调用)
        logger.error(
            "[audit/encryption] ENCRYPT_AT_REST=true 但 key 缺 · 落明文 fallback (production 应该已阻断启动)",
        )
        return plain, None
    aesgcm = AESGCM(key)
    nonce = os.urandom(NONCE_SIZE_BYTES)
    plaintext_bytes = plain.encode("utf-8")
    ct = aesgcm.encrypt(nonce, plaintext_bytes, None)
    # base64 编码 nonce + ciphertext 一起存 · 解密时 split
    nonce_b64 = base64.b64encode(nonce).decode("ascii")
    ct_b64 = base64.b64encode(ct).decode("ascii")
    return f"{nonce_b64}.{ct_b64}", ENCRYPTION_MARKER


def decrypt(stored: str | None, marker: str | None) -> str | None:
    """解密 stored → plain · marker=None 视作明文直返.

    解密失败返 "[decrypt failed: <error>]" placeholder · 不抛 · admin 仍能 query.
    """
    if stored is None:
        return None
    if marker != ENCRYPTION_MARKER:
        # 明文 (旧数据 / ENCRYPT_AT_REST=false 时存的)
        return stored
    key = _load_key()
    if key is None:
        return f"[decrypt failed: AUDIT_ENCRYPTION_KEY 未配 · 已加密内容无法解密]"
    try:
        nonce_b64, ct_b64 = stored.split(".", 1)
        nonce = base64.b64decode(nonce_b64)
        ct = base64.b64decode(ct_b64)
        aesgcm = AESGCM(key)
        pt = aesgcm.decrypt(nonce, ct, None)
        return pt.decode("utf-8")
    except (ValueError, InvalidTag, base64.binascii.Error) as e:
        logger.warning("[audit/encryption] decrypt failed: %s", e)
        return f"[decrypt failed: {type(e).__name__}]"


def generate_key_b64() -> str:
    """开发 / 部署时生成新 key · py -c 'from audit_service.encryption import generate_key_b64; print(generate_key_b64())'."""
    return base64.b64encode(os.urandom(KEY_SIZE_BYTES)).decode("ascii")


__all__ = [
    "ENCRYPTION_MARKER",
    "EncryptionError",
    "assert_config_valid",
    "decrypt",
    "encrypt",
    "generate_key_b64",
]
