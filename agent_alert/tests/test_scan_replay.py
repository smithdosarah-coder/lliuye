# -*- coding: utf-8 -*-
"""Agent4 BE5.5 · /api/alert/scan/replay/{scan_id} 锁盘测试 (Phase B Sprint 2 · 2026-05-04).

锁定:
- 历史 session 找得到 → SSE 流出 5 stage + done event with cached + replay
- 历史 session 找不到 → SSE error event (HITLIST_NOT_FOUND)
- replay 不调 LLM / KB / SearchProvider · 100% 确定性
- done envelope 复刻原 panels + replayed_at + original_generated_at
- fallback banner 标 replay info severity (透明告知用户在看历史)
- mode_label="replay" · data_source="cached"

audit 需求场景:
- 监管复核某客户最初触发预警时的完整证据链 (合规底线 § 信任模型)
- 客户经理对比当前扫描差异 (operational efficiency)
- 培训用历史 case 重放 · 不消耗 quota (cost control)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent_alert.api import app
from agent_alert.scan_engine import SESSIONS_DIR, persist_hitlist
from auth_service.dependencies import COOKIE_NAME
from auth_service.jwt_util import issue


def _make_client() -> TestClient:
    """TestClient with admin cookie · pass require_action gate.

    Phase B.1 fix (2026-05-09): /api/alert/scan/replay/{scan_id} 加 require_action("alert", "invoke") ·
    旧 test 没 cookie 返 401 · admin 跨 action 跨 agent OK · 与 test_export_docx_endpoint 一致.
    """
    c = TestClient(app)
    c.cookies.set(COOKIE_NAME, issue("u_test", "admin"))
    return c


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def replay_session(tmp_path, monkeypatch):
    """创建临时 session · 隔离 SESSIONS_DIR · 不污染真实 data/alert."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("agent_alert.scan_engine.SESSIONS_DIR", sessions_dir)
    monkeypatch.setattr("agent_alert.scan_engine.LATEST_POINTER", tmp_path / "latest.json")

    sid = "replay-test-001"
    payload = {
        "session_id": sid,
        "generated_at": "2026-04-15T10:00:00",
        "scenario_key": "fixture_replay",
        "mode": "web_live",
        "hit_list": {
            "hits": [
                {
                    "hit_id": "C001",
                    "level": "red",
                    "score": 0.92,
                    "matched_rules": ["LAW-002", "FIN-002", "POL-001"],
                    "reasons": ["失信被执行", "净利润转负", "贷款逾期"],
                    "target": {
                        "target_id": "C001",
                        "target_type": "loan_customer",
                        "payload": {
                            "company_name": "测试公司A",
                            "credit_balance": 5000000,
                        },
                    },
                    "evidences": [
                        {"source": "裁判文书网", "snippet": "失信案号", "url": ""},
                        {"source": "本行制度", "snippet": "POL-001", "url": ""},
                    ],
                    "extras": {
                        "trigger_reasons": ["cross_hit"],
                        "signal_kinds": ["legal_signal", "financial_signal", "internal_policy"],
                    },
                },
                {
                    "hit_id": "C002",
                    "level": "yellow",
                    "score": 0.55,
                    "matched_rules": ["FIN-001"],
                    "reasons": ["营收下降"],
                    "target": {
                        "target_id": "C002",
                        "target_type": "loan_customer",
                        "payload": {"company_name": "测试公司B", "credit_balance": 2000000},
                    },
                    "evidences": [],
                    "extras": {"trigger_reasons": ["external_signal"], "signal_kinds": ["financial_signal"]},
                },
            ],
            "red_count": 1,
            "yellow_count": 1,
            "green_count": 0,
            "total_scanned": 2,
        },
        "dispositions": {
            "测试公司A": {"advice": "加快贷后跟进 + 发函催收"},
        },
    }
    out_path = sessions_dir / f"{sid}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return sid


# ---------------------------------------------------------------------------
# Replay endpoint behavior
# ---------------------------------------------------------------------------


class TestScanReplayEndpoint:
    def test_replay_invalid_scan_id_400(self):
        client = _make_client()
        # 含特殊字符 · 路径参数验证拒
        r = client.post("/api/alert/scan/replay/.\\..\\evil")
        assert r.status_code in (400, 404)

    def test_replay_nonexistent_session_returns_error_event(self, tmp_path, monkeypatch):
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr("agent_alert.scan_engine.SESSIONS_DIR", sessions_dir)
        monkeypatch.setattr("agent_alert.scan_engine.LATEST_POINTER", tmp_path / "latest.json")

        client = _make_client()
        r = client.post("/api/alert/scan/replay/missing-xyz")
        assert r.status_code == 200  # SSE 200 OK · error 在 stream 内
        body = r.text
        assert "HITLIST_NOT_FOUND" in body or "missing-xyz" in body

    def test_replay_existing_session_streams_done(self, replay_session):
        client = _make_client()
        r = client.post(f"/api/alert/scan/replay/{replay_session}")
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]

        body = r.text
        # 5 stage events 全在
        for stage in ("kb_load", "external_scan", "internal_match", "cross", "summary"):
            assert stage in body, f"stage {stage} missing in stream"

        # done event 含 cached data_source + replay mode
        assert '"event": "done"' in body
        assert "cached" in body  # data_source
        assert "replay" in body  # mode

    def test_replay_done_event_contains_panels(self, replay_session):
        client = _make_client()
        r = client.post(f"/api/alert/scan/replay/{replay_session}")
        body = r.text
        assert "测试公司A" in body
        assert "测试公司B" in body
        assert "失信被执行" in body  # reasons
        assert "加快贷后跟进" in body  # disposition 复刻

    def test_replay_includes_replayed_at_marker(self, replay_session):
        client = _make_client()
        r = client.post(f"/api/alert/scan/replay/{replay_session}")
        body = r.text
        assert "replayed_at" in body
        assert "original_generated_at" in body
        assert "2026-04-15T10:00:00" in body  # 原 generated_at 复刻

    def test_replay_fallback_banner_replay_severity(self, replay_session):
        client = _make_client()
        r = client.post(f"/api/alert/scan/replay/{replay_session}")
        body = r.text
        assert "scan_replay" in body  # banner reason
        assert "历史扫描重放" in body  # banner message

    def test_replay_metrics_match_original(self, replay_session):
        client = _make_client()
        r = client.post(f"/api/alert/scan/replay/{replay_session}")
        body = r.text
        # 1 red + 1 yellow + 0 green 复刻
        assert '"red": 1' in body
        assert '"yellow": 1' in body

    def test_replay_does_not_call_llm_or_provider(self, replay_session, monkeypatch):
        """硬线: replay 必 100% 不调 LLM / SearchProvider · audit 路径不能 expose 外部."""
        # 任何对 LLMClient / build_search_provider 的导入都视为 violation
        called = {"llm": False, "provider": False, "kb": False}

        def _fake_llm(*a, **kw):
            called["llm"] = True

        def _fake_provider(*a, **kw):
            called["provider"] = True

        def _fake_kb(*a, **kw):
            called["kb"] = True

        monkeypatch.setattr("shared.llm_caller.client.LLMCaller.chat", _fake_llm, raising=False)
        monkeypatch.setattr(
            "shared.kb_scan.search_provider.build_search_provider", _fake_provider, raising=False,
        )
        monkeypatch.setattr(
            "agent_alert.knowledge_base.AlertKnowledgeBase.from_scenario", _fake_kb, raising=False,
        )

        client = _make_client()
        r = client.post(f"/api/alert/scan/replay/{replay_session}")
        assert r.status_code == 200
        assert called["llm"] is False, "replay 不应调 LLM"
        assert called["provider"] is False, "replay 不应调 SearchProvider"
        assert called["kb"] is False, "replay 不应装 KB"
