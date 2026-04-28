# -*- coding: utf-8 -*-
"""audit_service 单测 · Stage E.1.

锁定:
  - LLMCall dataclass + truncate_text + estimate_cost_cny
  - AuditRecorder · sqlite schema · record + query + count + pagination + filter
  - audit_llm_call decorator · 同步 + 异步 · pre/post hook · 异常 silent
  - role guard (admin only) on GET /api/audit/llm_calls (via TestClient)
  - 6 Agent decorator integration smoke (import + 装饰后函数仍能调用)

Author: Worker A1 (Stage E 第 1 批) · 2026-04-28
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from audit_service.decorators import audit_llm_call  # noqa: E402
from audit_service.recorder import (  # noqa: E402
    PROMPT_MAX_BYTES,
    RESPONSE_MAX_BYTES,
    AuditRecorder,
    LLMCall,
    estimate_cost_cny,
    query_calls,
    set_default_recorder,
    truncate_text,
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


# ============================================================================
# truncate_text
# ============================================================================

def test_truncate_none_returns_none():
    assert truncate_text(None, 100) is None


def test_truncate_short_string_unchanged():
    assert truncate_text("short", 100) == "short"


def test_truncate_long_utf8_string_appends_marker():
    long_text = "x" * 10000
    truncated = truncate_text(long_text, 100)
    assert truncated is not None
    assert truncated.endswith("…[truncated]")
    # utf-8 截断到 ≤ 100 字节 (主体 · 不含 marker)
    assert len(truncated.encode("utf-8")) < 200


def test_truncate_handles_chinese_unicode_boundary():
    """中文 utf-8 3 字节/字符 · 截断不应出现破碎字符."""
    chinese = "测试中文截断" * 100  # ~600 chars · 1800+ bytes
    truncated = truncate_text(chinese, 50)
    # 应可正常 utf-8 解码 · 不抛
    assert truncated is not None
    truncated.encode("utf-8").decode("utf-8")


# ============================================================================
# estimate_cost_cny
# ============================================================================

def test_cost_returns_none_when_no_tokens():
    assert estimate_cost_cny(None, None) is None


def test_cost_zero_when_zero_tokens():
    assert estimate_cost_cny(0, 0) == 0.0


def test_cost_linear_in_total_tokens():
    cost = estimate_cost_cny(1000, 2000)
    # 3000 * 0.0001 = 0.3
    assert cost == pytest.approx(0.3, abs=0.0001)


# ============================================================================
# AuditRecorder · sqlite store
# ============================================================================

def test_recorder_creates_db_with_schema(isolated_recorder, tmp_path):
    assert isolated_recorder.db_path.exists()
    # schema 校验 · 可查 (空) 表
    rows = isolated_recorder.query()
    assert rows == []


def test_recorder_record_and_query_roundtrip(isolated_recorder):
    call = LLMCall(
        ts="2026-04-28T10:00:00",
        user_id="u_wangzhe",
        agent_id="channel",
        endpoint="/api/channel/run",
        model="deepseek-chat",
        prompt="test prompt",
        response="test response",
        input_tokens=100,
        output_tokens=200,
        latency_ms=350,
    )
    row_id = isolated_recorder.record(call)
    assert row_id > 0
    assert call.id == row_id  # in-place set

    rows = isolated_recorder.query()
    assert len(rows) == 1
    r = rows[0]
    assert r["agent_id"] == "channel"
    assert r["endpoint"] == "/api/channel/run"
    assert r["user_id"] == "u_wangzhe"
    assert r["latency_ms"] == 350
    # cost 自动算 · 300 tokens × 0.0001 = 0.03
    assert r["cost_cny"] == pytest.approx(0.03, abs=0.0001)


def test_recorder_truncates_long_prompt_and_response(isolated_recorder):
    call = LLMCall(
        agent_id="report",
        endpoint="/api/report/v16/fill",
        model="deepseek-chat",
        prompt="a" * (PROMPT_MAX_BYTES * 2),
        response="b" * (RESPONSE_MAX_BYTES * 2),
    )
    isolated_recorder.record(call)
    rows = isolated_recorder.query()
    assert len(rows[0]["prompt"]) < PROMPT_MAX_BYTES * 2
    assert rows[0]["prompt"].endswith("…[truncated]")
    assert len(rows[0]["response"]) < RESPONSE_MAX_BYTES * 2
    assert rows[0]["response"].endswith("…[truncated]")


def test_recorder_query_filter_by_user_id(isolated_recorder):
    isolated_recorder.record(LLMCall(agent_id="channel", endpoint="/x", model="m", user_id="u_a"))
    isolated_recorder.record(LLMCall(agent_id="channel", endpoint="/y", model="m", user_id="u_b"))
    isolated_recorder.record(LLMCall(agent_id="channel", endpoint="/z", model="m", user_id="u_a"))

    rows_a = isolated_recorder.query(user_id="u_a")
    assert len(rows_a) == 2
    rows_b = isolated_recorder.query(user_id="u_b")
    assert len(rows_b) == 1
    assert rows_b[0]["endpoint"] == "/y"


def test_recorder_query_filter_by_agent_id(isolated_recorder):
    isolated_recorder.record(LLMCall(agent_id="channel", endpoint="/c", model="m"))
    isolated_recorder.record(LLMCall(agent_id="credit", endpoint="/d", model="m"))
    isolated_recorder.record(LLMCall(agent_id="report", endpoint="/r", model="m"))

    rows = isolated_recorder.query(agent_id="credit")
    assert len(rows) == 1
    assert rows[0]["agent_id"] == "credit"


def test_recorder_query_filter_by_date_range(isolated_recorder):
    isolated_recorder.record(LLMCall(ts="2026-04-26T10:00:00", agent_id="c", endpoint="/x", model="m"))
    isolated_recorder.record(LLMCall(ts="2026-04-27T10:00:00", agent_id="c", endpoint="/y", model="m"))
    isolated_recorder.record(LLMCall(ts="2026-04-28T10:00:00", agent_id="c", endpoint="/z", model="m"))

    rows = isolated_recorder.query(since="2026-04-27T00:00:00", until="2026-04-28T00:00:00")
    assert len(rows) == 1
    assert rows[0]["endpoint"] == "/y"


def test_recorder_query_pagination(isolated_recorder):
    for i in range(15):
        isolated_recorder.record(
            LLMCall(
                ts=f"2026-04-28T{i:02d}:00:00",
                agent_id="channel", endpoint=f"/x{i}", model="m",
            ),
        )
    page1 = isolated_recorder.query(limit=10, offset=0)
    page2 = isolated_recorder.query(limit=10, offset=10)
    assert len(page1) == 10
    assert len(page2) == 5
    # ts desc 排序
    assert page1[0]["ts"] > page1[-1]["ts"]


def test_recorder_count_matches_query(tmp_path):
    """count 数与 query 结果数应一致."""
    rec = AuditRecorder(tmp_path / "x.db")
    for i in range(5):
        rec.record(LLMCall(agent_id="channel", endpoint=f"/x{i}", model="m"))
    for i in range(3):
        rec.record(LLMCall(agent_id="credit", endpoint=f"/d{i}", model="m"))
    assert rec.count() == 8
    assert rec.count(agent_id="channel") == 5
    assert rec.count(agent_id="credit") == 3


def test_query_calls_helper_returns_pagination_shape(isolated_recorder):
    for i in range(7):
        isolated_recorder.record(LLMCall(agent_id="report", endpoint=f"/r{i}", model="m"))
    out = query_calls(agent_id="report", limit=5, offset=0)
    assert out["total"] == 7
    assert len(out["items"]) == 5
    assert out["limit"] == 5
    assert out["offset"] == 0


# ============================================================================
# audit_llm_call decorator
# ============================================================================

def test_decorator_records_sync_function_success(isolated_recorder):
    @audit_llm_call(agent_id="channel", endpoint="/api/channel/run")
    def handler(req, user=None):
        return {"ok": True}

    result = handler({"q": "x"}, user={"sub": "u_test", "role": "rm"})
    assert result == {"ok": True}

    rows = isolated_recorder.query()
    assert len(rows) == 1
    assert rows[0]["agent_id"] == "channel"
    assert rows[0]["user_id"] == "u_test"
    assert rows[0]["endpoint"] == "/api/channel/run"
    assert rows[0]["error"] is None
    assert rows[0]["latency_ms"] is not None


def test_decorator_records_async_function_success(isolated_recorder):
    @audit_llm_call(agent_id="report", endpoint="/api/report/v16/fill")
    async def handler(req, user=None):
        await asyncio.sleep(0.01)
        return {"ok": True}

    asyncio.run(handler({}, user={"sub": "u_async"}))
    rows = isolated_recorder.query()
    assert len(rows) == 1
    assert rows[0]["agent_id"] == "report"
    assert rows[0]["user_id"] == "u_async"
    assert rows[0]["error"] is None


def test_decorator_records_exception_and_reraises(isolated_recorder):
    @audit_llm_call(agent_id="credit", endpoint="/api/credit/decision")
    def handler():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        handler()

    rows = isolated_recorder.query()
    assert len(rows) == 1
    assert "ValueError" in rows[0]["error"]
    assert "boom" in rows[0]["error"]


def test_decorator_silent_when_audit_recorder_breaks(monkeypatch, tmp_path):
    """recorder.record 抛异常 · decorator 必须 silent · 业务返值不丢."""
    # 用 broken recorder · record 抛
    class _BrokenRecorder:
        def record(self, call):
            raise RuntimeError("disk full")

    monkeypatch.setattr(
        "audit_service.recorder._default_recorder",
        _BrokenRecorder(),
    )

    @audit_llm_call(agent_id="alert", endpoint="/api/alert/scan")
    def handler():
        return "business_ok"

    # 业务正常返 · decorator 吞 record 异常
    assert handler() == "business_ok"


# ============================================================================
# 6 Agent integration · decorator 装饰后函数仍正常 import + 调用
# ============================================================================

def test_6_agent_endpoint_modules_import_cleanly():
    """import 6 agent api module · 不抛 · 决议 audit decorator 兼容性."""
    import importlib

    for mod_name in [
        "agent_channel.api",
        "agent_credit.api",
        "agent_report.api",
        "agent_alert.api",
        "agent_compliance.api",
        "agent_riskctrl.api",
    ]:
        m = importlib.import_module(mod_name)
        assert hasattr(m, "app"), f"{mod_name} has no `app`"


def test_6_agent_endpoints_have_audit_decorator_marker():
    """6 个 LLM endpoint 函数应带 functools.wraps 痕迹 · 不丢 __name__.

    Stage C 后 HEAD endpoint 函数名:
    - credit_decision → credit_decision_v4 (v4.0 stage_tab 3 板块拆分)
    - compliance_policy_scan → compliance_policy_scan_get (GET/POST 分流后 GET handler)
    """
    from agent_channel.api import channel_run
    from agent_credit.api import credit_decision_v4
    from agent_report.api import report_v16_fill
    from agent_alert.api import alert_scan
    from agent_compliance.api import compliance_policy_scan_get
    from agent_riskctrl.api import riskctrl_dsl_gen

    assert channel_run.__name__ == "channel_run"
    assert credit_decision_v4.__name__ == "credit_decision_v4"
    assert report_v16_fill.__name__ == "report_v16_fill"
    assert alert_scan.__name__ == "alert_scan"
    assert compliance_policy_scan_get.__name__ == "compliance_policy_scan_get"
    assert riskctrl_dsl_gen.__name__ == "riskctrl_dsl_gen"


# ============================================================================
# admin endpoint role guard (TestClient)
# ============================================================================

def test_admin_endpoint_returns_data_for_admin_role(monkeypatch, isolated_recorder):
    """admin 角色 · 应能拿数据."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    def _fake_resolver():
        async def _stub() -> dict:
            return {"sub": "u_admin", "role": "admin"}
        return _stub

    monkeypatch.setattr("audit_service.api._resolve_require_user", _fake_resolver)

    isolated_recorder.record(LLMCall(agent_id="channel", endpoint="/x", model="m"))
    isolated_recorder.record(LLMCall(agent_id="report", endpoint="/y", model="m"))

    app = FastAPI()
    from audit_service.api import register_audit_routes
    register_audit_routes(app)

    client = TestClient(app)
    resp = client.get("/api/audit/llm_calls?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 2


def test_admin_endpoint_403_for_non_admin_role(monkeypatch, isolated_recorder):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    # mock require_user 返 rm user (不是 admin)
    def _fake_resolver():
        async def _stub() -> dict:
            return {"sub": "u_test", "role": "rm"}
        return _stub

    monkeypatch.setattr("audit_service.api._resolve_require_user", _fake_resolver)

    app = FastAPI()
    from audit_service.api import register_audit_routes
    register_audit_routes(app)

    client = TestClient(app)
    resp = client.get("/api/audit/llm_calls")
    assert resp.status_code == 403
    detail = resp.json().get("detail") or {}
    assert detail.get("error", {}).get("code") == "ACCESS_DENIED"


def test_admin_endpoint_supports_filters_and_pagination(monkeypatch, isolated_recorder):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    def _fake_resolver():
        async def _stub() -> dict:
            return {"sub": "u_admin", "role": "admin"}
        return _stub

    monkeypatch.setattr("audit_service.api._resolve_require_user", _fake_resolver)

    for i in range(5):
        isolated_recorder.record(LLMCall(agent_id="channel", endpoint=f"/c{i}", model="m"))
    for i in range(3):
        isolated_recorder.record(LLMCall(agent_id="credit", endpoint=f"/d{i}", model="m"))

    app = FastAPI()
    from audit_service.api import register_audit_routes
    register_audit_routes(app)

    client = TestClient(app)
    resp = client.get("/api/audit/llm_calls?agent_id=channel&limit=3")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5  # filtered total
    assert len(data["items"]) == 3
    for item in data["items"]:
        assert item["agent_id"] == "channel"
