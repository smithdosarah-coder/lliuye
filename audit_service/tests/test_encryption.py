# -*- coding: utf-8 -*-
"""audit_service.encryption tests · AES-GCM + recorder integration."""
from __future__ import annotations

import base64
import os
import sqlite3
from pathlib import Path

import pytest

from audit_service.encryption import (
    ENCRYPTION_MARKER,
    EncryptionError,
    assert_config_valid,
    decrypt,
    encrypt,
    generate_key_b64,
)


@pytest.fixture
def fresh_key_env(monkeypatch):
    """Set valid 32-byte AES key + ENCRYPT_AT_REST=true."""
    key = generate_key_b64()
    monkeypatch.setenv("AUDIT_ENCRYPTION_KEY", key)
    monkeypatch.setenv("ENCRYPT_AT_REST", "true")
    return key


@pytest.fixture
def disabled_env(monkeypatch):
    monkeypatch.setenv("ENCRYPT_AT_REST", "")
    monkeypatch.delenv("AUDIT_ENCRYPTION_KEY", raising=False)


def test_encrypt_disabled_returns_plain(disabled_env):
    """ENCRYPT_AT_REST=false → 落明文 · marker None."""
    cipher, marker = encrypt("hello world")
    assert cipher == "hello world"
    assert marker is None


def test_encrypt_decrypt_roundtrip(fresh_key_env):
    """加密解密 round-trip · plain == decrypt(encrypt(plain))."""
    plain = "客户经理 王哲 · 营收 5000 万"
    cipher, marker = encrypt(plain)
    assert marker == ENCRYPTION_MARKER
    assert cipher != plain
    assert "." in cipher  # nonce.ct format
    recovered = decrypt(cipher, marker)
    assert recovered == plain


def test_encrypt_none_returns_none(fresh_key_env):
    cipher, marker = encrypt(None)
    assert cipher is None
    assert marker is None


def test_decrypt_plain_returns_as_is(disabled_env):
    """marker=None 视作明文 · 直返."""
    assert decrypt("plain text", None) == "plain text"


def test_decrypt_corrupted_returns_placeholder(fresh_key_env):
    """坏数据解密 fail → 返 [decrypt failed: ...] placeholder · 不抛."""
    bad = "not-real-base64.also-bad"
    result = decrypt(bad, ENCRYPTION_MARKER)
    assert result is not None
    assert "decrypt failed" in result


def test_assert_config_valid_strict_no_key_raises(monkeypatch):
    """ENCRYPT_AT_REST=true 但 AUDIT_ENCRYPTION_KEY 缺 → raise EncryptionError."""
    monkeypatch.setenv("ENCRYPT_AT_REST", "true")
    monkeypatch.delenv("AUDIT_ENCRYPTION_KEY", raising=False)
    with pytest.raises(EncryptionError, match="未配"):
        assert_config_valid()


def test_assert_config_valid_disabled_passes(disabled_env):
    """ENCRYPT_AT_REST=false · 不 require key · pass."""
    assert_config_valid()  # 不抛即 pass


def test_invalid_key_size_raises(monkeypatch):
    """key 长度不对 → EncryptionError on _load_key."""
    bad_key = base64.b64encode(b"too-short").decode("ascii")
    monkeypatch.setenv("AUDIT_ENCRYPTION_KEY", bad_key)
    monkeypatch.setenv("ENCRYPT_AT_REST", "true")
    with pytest.raises(EncryptionError, match="bytes"):
        encrypt("test")


def test_recorder_e2e_with_encryption(fresh_key_env, tmp_path):
    """recorder.record + recorder.query · encrypted at rest · query 自动解密."""
    from audit_service.recorder import AuditRecorder, LLMCall, set_default_recorder

    db_path = tmp_path / "audit_test.db"
    recorder = AuditRecorder(db_path=db_path)
    set_default_recorder(None)  # reset singleton

    secret = "用户 王哲 询问 中锐网络 财务红线"
    call = LLMCall(
        agent_id="credit",
        endpoint="/api/credit/decision",
        model="deepseek-chat",
        prompt=secret,
        response="评分 72 / 建议有条件批准",
        input_tokens=100,
        output_tokens=50,
    )
    rid = recorder.record(call)
    assert rid > 0

    # 直查 sqlite · 应 encrypted (cipher 含 nonce.ct format)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT prompt, response, encryption_marker FROM llm_calls WHERE id = ?",
            (rid,),
        ).fetchone()
    raw_prompt, raw_response, marker = row
    assert marker == ENCRYPTION_MARKER
    assert raw_prompt != secret  # encrypted
    assert "." in raw_prompt    # nonce.ct
    assert raw_response != "评分 72 / 建议有条件批准"

    # 走 recorder.query · 自动解密
    items = recorder.query(agent_id="credit")
    assert len(items) == 1
    assert items[0]["prompt"] == secret
    assert items[0]["response"] == "评分 72 / 建议有条件批准"
    assert items[0]["encryption_marker"] == ENCRYPTION_MARKER


def test_recorder_e2e_without_encryption(disabled_env, tmp_path):
    """ENCRYPT_AT_REST=false · 落明文 · marker null · query 直返."""
    from audit_service.recorder import AuditRecorder, LLMCall, set_default_recorder

    db_path = tmp_path / "audit_plain.db"
    recorder = AuditRecorder(db_path=db_path)
    set_default_recorder(None)

    call = LLMCall(
        agent_id="channel",
        endpoint="/api/channel/run",
        model="deepseek-chat",
        prompt="plain text query",
        response="plain text response",
    )
    rid = recorder.record(call)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT prompt, encryption_marker FROM llm_calls WHERE id = ?",
            (rid,),
        ).fetchone()
    assert row[0] == "plain text query"  # plain
    assert row[1] is None  # marker null

    items = recorder.query(agent_id="channel")
    assert items[0]["prompt"] == "plain text query"
