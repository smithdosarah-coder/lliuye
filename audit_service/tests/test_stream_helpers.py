# -*- coding: utf-8 -*-
"""audit_service.stream_helpers 单测 · Stage W-FIX2 (修 bug #11).

锁定:
  - audit_stream_event 在 generator finally 调用 · 落 1 audit row
  - latency_ms 从 t0 (传入) 到 _record_safe 调用 · 含真实 stream 时延
  - error 字段写入 sqlite (异常类型 + msg)
  - extras (model / prompt / response / tokens / cost_cny) 注入路径
  - silent fail · audit 异常不抛
  - SSE generator 集成 smoke (yield 全 chunk + finally 一次 audit)

Author: Worker A1 (Stage W-FIX2 · bug #11) · 2026-04-29
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from audit_service.recorder import AuditRecorder, set_default_recorder  # noqa: E402
from audit_service.stream_helpers import audit_stream_event  # noqa: E402


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def isolated_recorder(tmp_path):
    """Per-test sqlite · 不污染 default recorder."""
    db = tmp_path / "stream_audit.db"
    rec = AuditRecorder(db)
    set_default_recorder(rec)
    yield rec
    set_default_recorder(None)


# ============================================================================
# Basic call · 1 row
# ============================================================================

def test_audit_stream_event_writes_one_row(isolated_recorder):
    """generator finally 内调一次 · 写 1 audit row."""
    t0 = time.time()
    audit_stream_event(
        agent_id="alert",
        endpoint="/api/alert/scan",
        model="deepseek-chat",
        t0=t0,
    )
    rows = isolated_recorder.query()
    assert len(rows) == 1
    r = rows[0]
    assert r["agent_id"] == "alert"
    assert r["endpoint"] == "/api/alert/scan"
    assert r["model"] == "deepseek-chat"
    assert r["error"] is None


def test_audit_stream_event_default_model_recorded(isolated_recorder):
    """显式 model 字段写入 sqlite (不取默认 fallback)."""
    audit_stream_event(
        agent_id="report", endpoint="/api/report/v16/fill",
        model="claude-3-opus", t0=time.time(),
    )
    rows = isolated_recorder.query()
    assert len(rows) == 1
    assert rows[0]["model"] == "claude-3-opus"


# ============================================================================
# Latency · t0 → 落 audit 时点
# ============================================================================

def test_audit_stream_event_latency_reflects_t0(isolated_recorder):
    """latency_ms 含 t0 ~ now 时间差 (≥ 50ms 模拟 generator 跑一会)."""
    t0 = time.time() - 0.05  # 50ms 前 = 模拟 stream 跑过 50ms
    audit_stream_event(
        agent_id="channel", endpoint="/api/channel/run",
        model="deepseek-chat", t0=t0,
    )
    rows = isolated_recorder.query()
    assert len(rows) == 1
    # latency 应 ≥ 50ms (t0 偏移) · 容忍 ≤ 1000ms (CI noisy)
    assert rows[0]["latency_ms"] >= 50
    assert rows[0]["latency_ms"] < 1000


def test_audit_stream_event_latency_from_zero_t0(isolated_recorder):
    """t0 ~= now → latency_ms 接近 0 (generator 立即结束 case)."""
    audit_stream_event(
        agent_id="riskctrl", endpoint="/api/riskctrl/dsl_gen",
        model="deepseek-chat", t0=time.time(),
    )
    rows = isolated_recorder.query()
    assert len(rows) == 1
    # < 100ms (单线程 record 极快)
    assert rows[0]["latency_ms"] < 100


# ============================================================================
# Error · 异常类型 + msg 写入 sqlite
# ============================================================================

def test_audit_stream_event_error_field(isolated_recorder):
    """error 参数 · 写入 sqlite error 列."""
    audit_stream_event(
        agent_id="alert", endpoint="/api/alert/scan",
        model="deepseek-chat", t0=time.time(),
        error="RuntimeError: LLM timeout after 30s",
    )
    rows = isolated_recorder.query()
    assert len(rows) == 1
    assert rows[0]["error"] == "RuntimeError: LLM timeout after 30s"


def test_audit_stream_event_error_none_when_success(isolated_recorder):
    """无 error 参数 · sqlite error 列为 NULL."""
    audit_stream_event(
        agent_id="credit", endpoint="/api/credit/decision",
        model="deepseek-chat", t0=time.time(),
    )
    rows = isolated_recorder.query()
    assert len(rows) == 1
    assert rows[0]["error"] is None


# ============================================================================
# user_id 透传
# ============================================================================

def test_audit_stream_event_user_id_passed(isolated_recorder):
    """user_id 来自 require_user payload · 写入 sqlite."""
    audit_stream_event(
        agent_id="report", endpoint="/api/report/v16/fill",
        model="deepseek-chat", t0=time.time(),
        user_id="u_wangzhe",
    )
    rows = isolated_recorder.query()
    assert len(rows) == 1
    assert rows[0]["user_id"] == "u_wangzhe"


def test_audit_stream_event_user_id_optional(isolated_recorder):
    """无 user_id (未登录) · NULL."""
    audit_stream_event(
        agent_id="alert", endpoint="/api/alert/scan",
        model="deepseek-chat", t0=time.time(),
    )
    rows = isolated_recorder.query()
    assert len(rows) == 1
    assert rows[0]["user_id"] is None


# ============================================================================
# extras 注入 · prompt / response / tokens / cost_cny / model
# ============================================================================

def test_audit_stream_event_extras_prompt_response(isolated_recorder):
    """extras dict 注入 prompt + response · 写入 sqlite."""
    audit_stream_event(
        agent_id="channel", endpoint="/api/channel/run",
        model="deepseek-chat", t0=time.time(),
        extras={"prompt": "test prompt", "response": "test response"},
    )
    rows = isolated_recorder.query()
    assert len(rows) == 1
    assert rows[0]["prompt"] == "test prompt"
    assert rows[0]["response"] == "test response"


def test_audit_stream_event_extras_tokens(isolated_recorder):
    """extras tokens · cost_cny 自动算 (300 tokens × 0.0001 = 0.03)."""
    audit_stream_event(
        agent_id="riskctrl", endpoint="/api/riskctrl/dsl_gen",
        model="deepseek-chat", t0=time.time(),
        extras={"input_tokens": 100, "output_tokens": 200},
    )
    rows = isolated_recorder.query()
    assert len(rows) == 1
    assert rows[0]["input_tokens"] == 100
    assert rows[0]["output_tokens"] == 200
    assert rows[0]["cost_cny"] == pytest.approx(0.03, abs=0.0001)


def test_audit_stream_event_extras_model_override(isolated_recorder):
    """extras 内 model 覆盖 positional model 参数 (decorator 同行为)."""
    audit_stream_event(
        agent_id="report", endpoint="/api/report/v16/fill",
        model="deepseek-chat", t0=time.time(),
        extras={"model": "gpt-4"},
    )
    rows = isolated_recorder.query()
    assert len(rows) == 1
    assert rows[0]["model"] == "gpt-4"


# ============================================================================
# Silent fail · 异常不阻塞
# ============================================================================

def test_audit_stream_event_silent_when_recorder_fails(monkeypatch, tmp_path):
    """recorder.record 抛异常 · audit_stream_event 不应抛 (silent fail)."""
    bad_db = tmp_path / "no_perm.db"

    class FailingRecorder(AuditRecorder):
        def record(self, call):
            raise RuntimeError("simulated sqlite fail")

    rec = FailingRecorder(bad_db)
    set_default_recorder(rec)
    try:
        # 不应抛
        audit_stream_event(
            agent_id="alert", endpoint="/api/alert/scan",
            model="deepseek-chat", t0=time.time(),
        )
    finally:
        set_default_recorder(None)


def test_audit_stream_event_silent_when_extras_malformed(isolated_recorder):
    """extras 非 dict (e.g. list) · _record_safe guard · 不抛 · 仍写一行."""
    audit_stream_event(
        agent_id="alert", endpoint="/api/alert/scan",
        model="deepseek-chat", t0=time.time(),
        extras="not-a-dict",  # type: ignore[arg-type]
    )
    rows = isolated_recorder.query()
    assert len(rows) == 1


# ============================================================================
# SSE generator 集成 smoke · finally 一次 audit
# ============================================================================

def test_audit_stream_event_generator_finally_once(isolated_recorder):
    """模拟 SSE generator try/finally · finally 调一次 · 1 audit row."""
    def fake_sse_gen(should_fail: bool):
        t0 = time.time()
        err: str | None = None
        try:
            yield "evt1"
            yield "evt2"
            if should_fail:
                raise RuntimeError("LLM 502")
            yield "done"
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            yield f"error:{err}"
        finally:
            audit_stream_event(
                agent_id="channel", endpoint="/api/channel/run",
                model="deepseek-chat", t0=t0, error=err,
            )

    chunks = list(fake_sse_gen(should_fail=False))
    assert chunks == ["evt1", "evt2", "done"]
    rows = isolated_recorder.query()
    assert len(rows) == 1
    assert rows[0]["error"] is None


def test_audit_stream_event_generator_error_path(isolated_recorder):
    """generator 抛异常 · finally 仍调一次 · audit row error 字段写入."""
    def fake_sse_gen():
        t0 = time.time()
        err: str | None = None
        try:
            yield "evt1"
            raise RuntimeError("LLM timeout")
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            yield f"error:{err}"
        finally:
            audit_stream_event(
                agent_id="alert", endpoint="/api/alert/scan",
                model="deepseek-chat", t0=t0, error=err,
            )

    chunks = list(fake_sse_gen())
    assert chunks[0] == "evt1"
    assert chunks[1].startswith("error:RuntimeError")
    rows = isolated_recorder.query()
    assert len(rows) == 1
    assert "RuntimeError" in (rows[0]["error"] or "")
    assert "LLM timeout" in (rows[0]["error"] or "")
