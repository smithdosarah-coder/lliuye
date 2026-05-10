# -*- coding: utf-8 -*-
"""Phase B.2 §10 (PM 2026-05-10) · channel /handoff + /conversion ledger 上链 tests.

Per CLAUDE.md §3.7.5 BE7:
  - channel | retention default = "short" (90d · 候选/推荐非决策)
  - jurisdiction default = HQ
  - subject_id 必 hash (PII safe)
  - silent-fail · 不破 decision 主路径

落地点 (Phase B.2):
  - /api/channel/handoff   · RM 显式决策移交 candidate → credit · 必上链
  - /api/channel/conversion · RM 标记 won/lost/contacted · 必上链
"""
from __future__ import annotations

import os
import tempfile
import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _isolate_ledger_db(monkeypatch):
    """每 test 用独立 sqlite path · 无污染."""
    db_path = tempfile.mktemp(suffix=".sqlite")
    monkeypatch.setenv("LIUYE_LEDGER_DB_PATH", db_path)
    # default_ledger 是 module-level singleton · reset 让 path 生效
    import shared.decision_ledger.store as store_mod
    from shared.decision_ledger import DecisionLedger, set_default_ledger
    monkeypatch.setattr(store_mod, "_default_ledger", None)
    # 显式注入 fresh ledger w/ tmp path (env path 路径 resolve 由 default_ledger() 拿)
    set_default_ledger(DecisionLedger(db_path))
    yield
    set_default_ledger(None)
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass


def test_handoff_writes_ledger_entry():
    """/api/channel/handoff 后 ledger 必有 channel agent · /handoff endpoint 条目."""
    from agent_channel.api import app
    from shared.decision_ledger import query_agent

    client = TestClient(app)
    sid = str(uuid.uuid4())
    resp = client.post(
        "/api/channel/handoff",
        json={
            "session_id": sid,
            "candidates": [
                {"name": "海康威视", "uscc": "91330185711315925G", "matchScore": 88},
                {"name": "大华股份", "matchScore": 75},  # 无 USCC · 走 name hash
            ],
            "business_line": "corporate",
        },
    )
    assert resp.status_code == 200, resp.text

    recs = query_agent("channel", limit=10)
    handoff_recs = [r for r in recs if r.get("endpoint") == "/api/channel/handoff"]
    assert len(handoff_recs) == 2, f"应 2 条 handoff ledger (per candidate) · got {len(handoff_recs)}"

    # 验 retention default = short (per §3.7.5 channel row)
    for r in handoff_recs:
        assert r.get("retention_class") == "short", (
            f"channel default retention 必 short · got {r.get('retention_class')!r}"
        )
    # 验 jurisdiction default = HQ
    for r in handoff_recs:
        assert r.get("jurisdiction") == "HQ", (
            f"default jurisdiction HQ · got {r.get('jurisdiction')!r}"
        )
    # 验 subject_id 是 hash (16 hex prefix · 不是 raw USCC)
    for r in handoff_recs:
        sid_field = r.get("subject_id") or ""
        if sid_field:
            assert len(sid_field) == 16 and all(c in "0123456789abcdef" for c in sid_field), (
                f"subject_id 必 16 hex hash · got {sid_field!r}"
            )


def test_conversion_writes_ledger_entry():
    """/api/channel/conversion 后 ledger 必有 channel agent · /conversion endpoint 条目."""
    from agent_channel.api import app
    from shared.decision_ledger import query_agent

    client = TestClient(app)
    resp = client.post(
        "/api/channel/conversion",
        json={
            "candidate_id": "uscc_91330185711315925G",
            "rm_id": "u_test_rm",
            "stage": "contacted",
            "notes": "客户经理已电话联系",
            "amount_yuan": 0,
            "next_action": "约访",
        },
    )
    assert resp.status_code == 200, resp.text

    recs = query_agent("channel", limit=10)
    conv_recs = [r for r in recs if r.get("endpoint") == "/api/channel/conversion"]
    assert len(conv_recs) == 1, f"应 1 条 conversion ledger · got {len(conv_recs)}"
    rec = conv_recs[0]
    assert rec.get("retention_class") == "short"
    assert rec.get("jurisdiction") == "HQ"


def test_handoff_ledger_failure_does_not_break_response(monkeypatch):
    """ledger 写入失败时 · /handoff 主路径不 break (silent-fail per §3.7.5)."""
    from agent_channel.api import app

    # patch record_decision raise
    import shared.decision_ledger as dl_mod

    def boom(*_args, **_kwargs):
        raise RuntimeError("ledger db locked simulation")

    monkeypatch.setattr(dl_mod, "record_decision", boom)

    client = TestClient(app)
    sid = str(uuid.uuid4())
    # 不应 500 · ledger 失败 silent
    resp = client.post(
        "/api/channel/handoff",
        json={
            "session_id": sid,
            "candidates": [{"name": "海康威视", "uscc": "91330185711315925G"}],
            "business_line": "corporate",
        },
    )
    assert resp.status_code == 200, (
        f"ledger 失败时 handoff 主路径必 200 · got {resp.status_code} · body={resp.text[:200]}"
    )
    # 主路径返回 schema 完整
    body = resp.json()
    assert "session_id" in body and "profile_ids" in body
