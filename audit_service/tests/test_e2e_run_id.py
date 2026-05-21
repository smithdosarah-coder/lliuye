# -*- coding: utf-8 -*-
"""audit_service · ROI #5 (2026-05-21) E2E 证据链 unit tests.

锁定:
  - LLMCall.e2e_run_id 字段 + dataclass roundtrip
  - sqlite schema 加 e2e_run_id 列 + idx_e2e_run_id 索引 (向后兼容老 db)
  - record() 从 contextvar 自动拿 e2e_run_id (LLMCall.e2e_run_id 优先)
  - AuditRecorder.query / count 支持 e2e_run_id 过滤
  - query_by_run_id helper 返 envelope (count / agents_hit / errors / total_cost_cny)
  - AuditLogMiddleware 解 X-Liuye-E2E-Run-Id header → 写 e2e_run_id 列
  - 老 audit 行 (无 header) → e2e_run_id=NULL · 向后兼容
  - GET /api/audit/by_run_id/{run_id} admin role gate + payload shape
  - 非 admin role → 403
  - 非法 run_id (空 / 过长 / 特殊字符) → sanitize / 400
"""
from __future__ import annotations

import asyncio
import sqlite3
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from audit_service.recorder import (  # noqa: E402
    AuditRecorder,
    LLMCall,
    e2e_run_id_var,
    query_by_run_id,
    set_default_recorder,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def isolated_recorder(tmp_path: Path):
    """Per-test sqlite · 不污染 default recorder."""
    db = tmp_path / "llm_calls.db"
    rec = AuditRecorder(db)
    set_default_recorder(rec)
    yield rec
    set_default_recorder(None)


@pytest.fixture(autouse=True)
def reset_e2e_run_id_var():
    """Per-test reset contextvar (防测试间污染)."""
    token = e2e_run_id_var.set(None)
    yield
    try:
        e2e_run_id_var.reset(token)
    except Exception:
        pass


# ============================================================================
# Schema · sqlite 加 e2e_run_id 列
# ============================================================================

def test_schema_includes_e2e_run_id_column(isolated_recorder):
    """新 db schema 必须含 e2e_run_id 列."""
    with sqlite3.connect(isolated_recorder.db_path) as conn:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(llm_calls)").fetchall()]
    assert "e2e_run_id" in cols, f"e2e_run_id missing in schema: {cols}"


def test_schema_includes_e2e_run_id_index(isolated_recorder):
    """新 db schema 必须含 idx_e2e_run_id 索引 (查询性能 · 避免全表扫)."""
    with sqlite3.connect(isolated_recorder.db_path) as conn:
        indexes = [row[1] for row in conn.execute("PRAGMA index_list(llm_calls)").fetchall()]
    assert "idx_e2e_run_id" in indexes, f"idx_e2e_run_id missing: {indexes}"


def test_migration_from_old_db_without_e2e_run_id(tmp_path):
    """老 db (Stage E.1/E.3 schema · 无 e2e_run_id 列) → ALTER TABLE 加列 · 不丢老数据."""
    db = tmp_path / "old.db"
    # 模拟旧 schema (Stage E.3 之前 · 含 encryption_marker 但无 e2e_run_id)
    with sqlite3.connect(db) as conn:
        conn.executescript("""
            CREATE TABLE llm_calls (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              ts TEXT NOT NULL,
              user_id TEXT,
              agent_id TEXT NOT NULL,
              endpoint TEXT NOT NULL,
              model TEXT NOT NULL,
              prompt TEXT,
              response TEXT,
              input_tokens INTEGER,
              output_tokens INTEGER,
              cost_cny REAL,
              latency_ms INTEGER,
              error TEXT,
              encryption_marker TEXT
            );
        """)
        conn.execute(
            "INSERT INTO llm_calls(ts, agent_id, endpoint, model) VALUES (?, ?, ?, ?)",
            ("2026-04-01T10:00:00", "channel", "/api/channel/run", "deepseek-chat"),
        )
        conn.commit()

    # 用 AuditRecorder 接管 · 触发 migration
    rec = AuditRecorder(db)

    # 老数据保留 · e2e_run_id 列加上 · 老行 e2e_run_id = NULL
    with sqlite3.connect(db) as conn:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(llm_calls)").fetchall()]
        rows = conn.execute("SELECT agent_id, e2e_run_id FROM llm_calls").fetchall()
    assert "e2e_run_id" in cols
    assert len(rows) == 1
    assert rows[0][0] == "channel"
    assert rows[0][1] is None  # 老行 NULL · 向后兼容

    # 新 record 应能写 e2e_run_id
    rec.record(LLMCall(agent_id="credit", endpoint="/x", model="m", e2e_run_id="run-123"))
    items = rec.query(e2e_run_id="run-123")
    assert len(items) == 1
    assert items[0]["agent_id"] == "credit"


# ============================================================================
# LLMCall dataclass · e2e_run_id 字段
# ============================================================================

def test_llmcall_e2e_run_id_default_none():
    call = LLMCall(agent_id="channel", endpoint="/x", model="m")
    assert call.e2e_run_id is None


def test_llmcall_e2e_run_id_roundtrip(isolated_recorder):
    """LLMCall.e2e_run_id 显式注入 · 写 + 查 round-trip."""
    call = LLMCall(
        agent_id="channel", endpoint="/x", model="m",
        e2e_run_id="gh-run-12345",
    )
    isolated_recorder.record(call)
    rows = isolated_recorder.query()
    assert len(rows) == 1
    assert rows[0]["e2e_run_id"] == "gh-run-12345"


# ============================================================================
# Contextvar · record() 从 contextvar 取 e2e_run_id
# ============================================================================

def test_record_picks_up_contextvar_when_llmcall_field_missing(isolated_recorder):
    """LLMCall.e2e_run_id=None 时 record() 从 contextvar 取."""
    # cleanup 由 autouse fixture reset_e2e_run_id_var 处理
    e2e_run_id_var.set("ctx-run-42")
    isolated_recorder.record(LLMCall(agent_id="alert", endpoint="/x", model="m"))
    rows = isolated_recorder.query()
    assert rows[0]["e2e_run_id"] == "ctx-run-42"


def test_llmcall_field_overrides_contextvar(isolated_recorder):
    """LLMCall.e2e_run_id 显式注入 · 覆盖 contextvar."""
    e2e_run_id_var.set("ctx-run-A")
    isolated_recorder.record(LLMCall(
        agent_id="alert", endpoint="/x", model="m",
        e2e_run_id="explicit-run-B",
    ))
    rows = isolated_recorder.query()
    assert rows[0]["e2e_run_id"] == "explicit-run-B"


def test_record_writes_null_when_no_contextvar_and_no_field(isolated_recorder):
    """LLMCall.e2e_run_id=None + contextvar=None → 写 NULL · 老 audit 行向后兼容."""
    isolated_recorder.record(LLMCall(agent_id="channel", endpoint="/x", model="m"))
    rows = isolated_recorder.query()
    assert rows[0]["e2e_run_id"] is None


# ============================================================================
# Query · e2e_run_id 过滤
# ============================================================================

def test_query_filter_by_e2e_run_id(isolated_recorder):
    """e2e_run_id 过滤 · 拿单次 cron run 的全部 audit."""
    isolated_recorder.record(LLMCall(agent_id="channel", endpoint="/c", model="m", e2e_run_id="run-A"))
    isolated_recorder.record(LLMCall(agent_id="credit", endpoint="/d", model="m", e2e_run_id="run-A"))
    isolated_recorder.record(LLMCall(agent_id="alert", endpoint="/a", model="m", e2e_run_id="run-B"))
    isolated_recorder.record(LLMCall(agent_id="report", endpoint="/r", model="m"))  # NULL

    rows_a = isolated_recorder.query(e2e_run_id="run-A")
    assert len(rows_a) == 2
    assert {r["agent_id"] for r in rows_a} == {"channel", "credit"}

    rows_b = isolated_recorder.query(e2e_run_id="run-B")
    assert len(rows_b) == 1
    assert rows_b[0]["agent_id"] == "alert"


def test_count_filter_by_e2e_run_id(isolated_recorder):
    for i in range(3):
        isolated_recorder.record(LLMCall(agent_id="channel", endpoint=f"/c{i}", model="m", e2e_run_id="run-X"))
    isolated_recorder.record(LLMCall(agent_id="credit", endpoint="/d", model="m", e2e_run_id="run-Y"))

    assert isolated_recorder.count(e2e_run_id="run-X") == 3
    assert isolated_recorder.count(e2e_run_id="run-Y") == 1
    assert isolated_recorder.count(e2e_run_id="run-Z") == 0


# ============================================================================
# query_by_run_id helper · envelope shape
# ============================================================================

def test_query_by_run_id_returns_envelope(isolated_recorder):
    """envelope 含 count / agents_hit / endpoints_hit / errors / total_cost_cny / has_more."""
    isolated_recorder.record(LLMCall(
        agent_id="channel", endpoint="/api/channel/run", model="m",
        e2e_run_id="run-1", input_tokens=100, output_tokens=200,
    ))
    isolated_recorder.record(LLMCall(
        agent_id="credit", endpoint="/api/credit/decision", model="m",
        e2e_run_id="run-1", input_tokens=50, output_tokens=100,
    ))
    isolated_recorder.record(LLMCall(
        agent_id="alert", endpoint="/api/alert/scan", model="m",
        e2e_run_id="run-1", error="ValueError: bad input",
    ))

    out = query_by_run_id("run-1")
    assert out["run_id"] == "run-1"
    assert out["count"] == 3
    assert out["total"] == 3
    assert set(out["agents_hit"]) == {"channel", "credit", "alert"}
    assert set(out["endpoints_hit"]) == {
        "/api/channel/run", "/api/credit/decision", "/api/alert/scan",
    }
    assert len(out["errors"]) == 1
    assert out["errors"][0]["agent_id"] == "alert"
    # cost = (100+200)*0.0001 + (50+100)*0.0001 = 0.03 + 0.015 = 0.045
    assert out["total_cost_cny"] == pytest.approx(0.045, abs=0.001)
    assert out["has_more"] is False


def test_query_by_run_id_empty_returns_zero_envelope(isolated_recorder):
    """无任何 run · empty envelope (不抛)."""
    out = query_by_run_id("nonexistent-run")
    assert out["run_id"] == "nonexistent-run"
    assert out["count"] == 0
    assert out["total"] == 0
    assert out["agents_hit"] == []
    assert out["errors"] == []
    assert out["has_more"] is False


def test_query_by_run_id_pagination_has_more(isolated_recorder):
    """records > limit → has_more=True."""
    for i in range(10):
        isolated_recorder.record(LLMCall(
            agent_id="channel", endpoint=f"/x{i}", model="m", e2e_run_id="run-P",
        ))
    out = query_by_run_id("run-P", limit=5, offset=0)
    assert out["count"] == 5
    assert out["total"] == 10
    assert out["has_more"] is True

    out2 = query_by_run_id("run-P", limit=5, offset=5)
    assert out2["count"] == 5
    assert out2["total"] == 10
    assert out2["has_more"] is False  # 5+5=10 不大于 10


# ============================================================================
# AuditLogMiddleware · 解 X-Liuye-E2E-Run-Id header → contextvar
# ============================================================================

def _run_middleware(scope, recorder):
    """Helper · 跑 middleware 一次 · 模拟 ASGI 调用."""
    from audit_service.middleware import AuditLogMiddleware

    async def fake_app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})
        # 模拟 endpoint 内 audit (LLMCall.e2e_run_id 未填 · 应从 ctxvar 拿)
        recorder.record(LLMCall(
            agent_id="channel", endpoint=scope["path"], model="m",
        ))

    mw = AuditLogMiddleware(fake_app)
    sent = []

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(msg):
        sent.append(msg)

    asyncio.run(mw(scope, receive, send))
    return sent


def test_middleware_extracts_e2e_run_id_header(isolated_recorder):
    """middleware 解 X-Liuye-E2E-Run-Id header → contextvar → record 写入."""
    scope = {
        "type": "http",
        "path": "/api/channel/run",
        "headers": [(b"x-liuye-e2e-run-id", b"gh-run-99999")],
    }
    _run_middleware(scope, isolated_recorder)

    rows = isolated_recorder.query()
    # 2 行: 一行是 endpoint 内 record (e2e_run_id 由 ctxvar 拿) ·
    #       一行是 middleware 自己的 record (audit_paths 命中 · 也由 ctxvar 拿)
    assert len(rows) >= 1
    e2e_ids = {r["e2e_run_id"] for r in rows}
    assert "gh-run-99999" in e2e_ids


def test_middleware_no_header_writes_null(isolated_recorder):
    """无 X-Liuye-E2E-Run-Id header → e2e_run_id=NULL · 老路径向后兼容."""
    scope = {
        "type": "http",
        "path": "/api/channel/run",
        "headers": [(b"content-type", b"application/json")],
    }
    _run_middleware(scope, isolated_recorder)

    rows = isolated_recorder.query()
    assert len(rows) >= 1
    for r in rows:
        assert r["e2e_run_id"] is None


def test_middleware_sanitizes_e2e_run_id_special_chars(isolated_recorder):
    """header 含非法字符 (空格 / SQL 关键字) → sanitize 仅留 alphanumeric + - _ ."""
    scope = {
        "type": "http",
        "path": "/api/channel/run",
        "headers": [(b"x-liuye-e2e-run-id", b"run-123' OR 1=1--")],
    }
    _run_middleware(scope, isolated_recorder)

    rows = isolated_recorder.query()
    e2e_ids = {r["e2e_run_id"] for r in rows if r["e2e_run_id"]}
    # 仅留 alphanum + - · 空格 / 引号 / 等号 / SQL syntax 全 strip
    for v in e2e_ids:
        assert all(ch.isalnum() or ch in "-_." for ch in v), f"unsanitized: {v}"


def test_middleware_truncates_long_e2e_run_id(isolated_recorder):
    """header value 超 64 chars → 截断 64."""
    long_value = "x" * 200
    scope = {
        "type": "http",
        "path": "/api/channel/run",
        "headers": [(b"x-liuye-e2e-run-id", long_value.encode())],
    }
    _run_middleware(scope, isolated_recorder)

    rows = isolated_recorder.query()
    e2e_ids = {r["e2e_run_id"] for r in rows if r["e2e_run_id"]}
    for v in e2e_ids:
        assert len(v) <= 64


def test_middleware_non_audit_path_still_sets_contextvar(isolated_recorder):
    """非 audit_paths 路径 (e.g. /api/auth/login) 也 set contextvar · 防 endpoint 内 decorator 拿不到."""
    scope = {
        "type": "http",
        "path": "/api/auth/login",  # 非 audit_paths
        "headers": [(b"x-liuye-e2e-run-id", b"run-auth-1")],
    }
    _run_middleware(scope, isolated_recorder)

    rows = isolated_recorder.query()
    e2e_ids = {r["e2e_run_id"] for r in rows if r["e2e_run_id"]}
    assert "run-auth-1" in e2e_ids


# ============================================================================
# admin endpoint · GET /api/audit/by_run_id/{run_id}
# ============================================================================

def test_api_by_run_id_returns_envelope_for_admin(monkeypatch, isolated_recorder):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    def _fake_resolver():
        async def _stub() -> dict:
            return {"sub": "u_admin", "role": "admin"}
        return _stub

    monkeypatch.setattr("audit_service.api._resolve_require_user", _fake_resolver)

    isolated_recorder.record(LLMCall(
        agent_id="channel", endpoint="/api/channel/run", model="m", e2e_run_id="run-API-1",
    ))
    isolated_recorder.record(LLMCall(
        agent_id="credit", endpoint="/api/credit/run", model="m", e2e_run_id="run-API-1",
    ))

    app = FastAPI()
    from audit_service.api import register_audit_routes
    register_audit_routes(app)

    client = TestClient(app)
    resp = client.get("/api/audit/by_run_id/run-API-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["run_id"] == "run-API-1"
    assert data["count"] == 2
    assert set(data["agents_hit"]) == {"channel", "credit"}
    assert data["has_more"] is False


def test_api_by_run_id_403_for_non_admin(monkeypatch, isolated_recorder):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    def _fake_resolver():
        async def _stub() -> dict:
            return {"sub": "u_rm", "role": "rm"}
        return _stub

    monkeypatch.setattr("audit_service.api._resolve_require_user", _fake_resolver)

    app = FastAPI()
    from audit_service.api import register_audit_routes
    register_audit_routes(app)

    client = TestClient(app)
    resp = client.get("/api/audit/by_run_id/run-X")
    assert resp.status_code == 403


def test_api_by_run_id_empty_returns_200_not_404(monkeypatch, isolated_recorder):
    """run_id 不存在 → 200 + count=0 · 不返 404 · 防 workflow curl 卡死."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    def _fake_resolver():
        async def _stub() -> dict:
            return {"sub": "u_admin", "role": "admin"}
        return _stub

    monkeypatch.setattr("audit_service.api._resolve_require_user", _fake_resolver)

    app = FastAPI()
    from audit_service.api import register_audit_routes
    register_audit_routes(app)

    client = TestClient(app)
    resp = client.get("/api/audit/by_run_id/nonexistent-run-zzz")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


def test_api_by_run_id_supports_pagination(monkeypatch, isolated_recorder):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    def _fake_resolver():
        async def _stub() -> dict:
            return {"sub": "u_admin", "role": "admin"}
        return _stub

    monkeypatch.setattr("audit_service.api._resolve_require_user", _fake_resolver)

    for i in range(7):
        isolated_recorder.record(LLMCall(
            agent_id="channel", endpoint=f"/x{i}", model="m", e2e_run_id="run-P",
        ))

    app = FastAPI()
    from audit_service.api import register_audit_routes
    register_audit_routes(app)

    client = TestClient(app)
    resp = client.get("/api/audit/by_run_id/run-P?limit=3&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 3
    assert data["total"] == 7
    assert data["has_more"] is True


# ============================================================================
# Backward compat · 老 llm_calls endpoint 也支持 e2e_run_id 过滤
# ============================================================================

def test_llm_calls_endpoint_supports_e2e_run_id_filter(monkeypatch, isolated_recorder):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    def _fake_resolver():
        async def _stub() -> dict:
            return {"sub": "u_admin", "role": "admin"}
        return _stub

    monkeypatch.setattr("audit_service.api._resolve_require_user", _fake_resolver)

    isolated_recorder.record(LLMCall(agent_id="channel", endpoint="/c", model="m", e2e_run_id="r1"))
    isolated_recorder.record(LLMCall(agent_id="credit", endpoint="/d", model="m", e2e_run_id="r2"))
    isolated_recorder.record(LLMCall(agent_id="alert", endpoint="/a", model="m"))  # NULL

    app = FastAPI()
    from audit_service.api import register_audit_routes
    register_audit_routes(app)

    client = TestClient(app)
    resp = client.get("/api/audit/llm_calls?e2e_run_id=r1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["agent_id"] == "channel"
    assert data["items"][0]["e2e_run_id"] == "r1"
