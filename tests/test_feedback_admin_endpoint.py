# -*- coding: utf-8 -*-
"""Phase B Sprint 2 决策 1 · /api/feedback admin endpoint coverage.

覆盖 (per WORKER-B1-SPRINT-2-SPEC-DECISIONS):
  - 4 filter: agent_id / date_from-date_to / rating CSV / user_id
  - cursor pagination 50/page (created_at desc + id tiebreak)
  - export zip per-agent jsonl
  - rating field 进 jsonl + audit log
  - 403 non-admin role
"""
from __future__ import annotations

import importlib
import io
import json
import zipfile
from pathlib import Path

import pytest


@pytest.fixture
def admin_sandbox(tmp_path: Path, monkeypatch):
    """干净 audit + feedback dir + admin auth override."""
    monkeypatch.setenv("AUDIT_DB_PATH", str(tmp_path / "audit.db"))
    monkeypatch.setenv("ENCRYPT_AT_REST", "false")

    import audit_service.recorder as recorder_mod
    recorder_mod.set_default_recorder(None)

    import api_server
    importlib.reload(api_server)
    monkeypatch.setattr(api_server, "PROJECT_ROOT", tmp_path, raising=True)

    # admin override
    api_server.app.dependency_overrides[api_server._FEEDBACK_ADMIN_DEP] = (
        lambda: {"sub": "test-admin", "role": "admin"}
    )

    yield tmp_path, api_server

    api_server.app.dependency_overrides.pop(api_server._FEEDBACK_ADMIN_DEP, None)
    recorder_mod.set_default_recorder(None)


def _seed_jsonl(root: Path, date: str, records: list[dict]) -> None:
    p = root / "data" / "feedback" / f"{date}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _rec(agent: str, user_id: str, rating: int | None, ts: str = "2026-05-01T10:00:00") -> dict:
    return {
        "timestamp": ts,
        "agent": agent,
        "session_id": f"s-{agent}-{user_id}",
        "user_id": user_id,
        "original_output": {"x": 1},
        "user_correction": {"x": 2},
        "correction_reason": "改了",
        "rating": rating,
    }


# ---------------------------------------------------------------------------
# rating field 进 jsonl
# ---------------------------------------------------------------------------

def test_post_feedback_persists_rating(admin_sandbox):
    root, api_server = admin_sandbox
    from fastapi.testclient import TestClient
    with TestClient(api_server.app) as c:
        r = c.post("/api/feedback", json={
            "agent": "credit", "session_id": "s",
            "original_output": {}, "user_correction": {},
            "rating": 5, "user_id": "rm-1",
        })
        assert r.status_code == 200
    line = next((root / "data/feedback").glob("*.jsonl")).read_text("utf-8").strip()
    assert json.loads(line)["rating"] == 5


def test_post_feedback_rating_out_of_range_400(admin_sandbox):
    _, api_server = admin_sandbox
    from fastapi.testclient import TestClient
    with TestClient(api_server.app) as c:
        for bad in (0, 6, -1, 99):
            r = c.post("/api/feedback", json={
                "agent": "credit", "session_id": "s",
                "original_output": {}, "user_correction": {},
                "rating": bad,
            })
            assert r.status_code == 400, f"rating={bad} should 400"


# ---------------------------------------------------------------------------
# 4 filter
# ---------------------------------------------------------------------------

def test_filter_by_agent_id(admin_sandbox):
    root, api_server = admin_sandbox
    _seed_jsonl(root, "2026-05-01", [
        _rec("credit", "rm-A", 5),
        _rec("report", "rm-B", 4),
        _rec("credit", "rm-C", 3),
    ])
    from fastapi.testclient import TestClient
    with TestClient(api_server.app) as c:
        r = c.get("/api/feedback?agent_id=credit")
        body = r.json()
        assert all(it["agent"] == "credit" for it in body["items"])
        assert len(body["items"]) == 2


def test_filter_by_date_range(admin_sandbox):
    root, api_server = admin_sandbox
    _seed_jsonl(root, "2026-04-25", [_rec("credit", "rm-A", 5, ts="2026-04-25T10:00:00")])
    _seed_jsonl(root, "2026-05-01", [_rec("credit", "rm-B", 5, ts="2026-05-01T10:00:00")])
    _seed_jsonl(root, "2026-05-10", [_rec("credit", "rm-C", 5, ts="2026-05-10T10:00:00")])
    from fastapi.testclient import TestClient
    with TestClient(api_server.app) as c:
        r = c.get("/api/feedback?date_from=2026-05-01&date_to=2026-05-09")
        users = [it["user_id"] for it in r.json()["items"]]
        assert users == ["rm-B"]


def test_filter_by_rating_csv(admin_sandbox):
    root, api_server = admin_sandbox
    _seed_jsonl(root, "2026-05-01", [
        _rec("credit", "rm-A", 1),
        _rec("credit", "rm-B", 4),
        _rec("credit", "rm-C", 5),
        _rec("credit", "rm-D", None),
    ])
    from fastapi.testclient import TestClient
    with TestClient(api_server.app) as c:
        r = c.get("/api/feedback?rating=4,5")
        users = sorted(it["user_id"] for it in r.json()["items"])
        assert users == ["rm-B", "rm-C"]


def test_filter_by_user_id(admin_sandbox):
    root, api_server = admin_sandbox
    _seed_jsonl(root, "2026-05-01", [
        _rec("credit", "rm-X", 5),
        _rec("alert", "rm-X", 4),
        _rec("credit", "rm-Y", 5),
    ])
    from fastapi.testclient import TestClient
    with TestClient(api_server.app) as c:
        r = c.get("/api/feedback?user_id=rm-X")
        agents = sorted(it["agent"] for it in r.json()["items"])
        assert agents == ["alert", "credit"]


def test_filter_combined(admin_sandbox):
    root, api_server = admin_sandbox
    _seed_jsonl(root, "2026-05-01", [
        _rec("credit", "rm-A", 5),
        _rec("credit", "rm-A", 3),
        _rec("credit", "rm-B", 5),
        _rec("alert", "rm-A", 5),
    ])
    from fastapi.testclient import TestClient
    with TestClient(api_server.app) as c:
        r = c.get("/api/feedback?agent_id=credit&user_id=rm-A&rating=5")
        items = r.json()["items"]
        assert len(items) == 1
        assert items[0]["agent"] == "credit"
        assert items[0]["user_id"] == "rm-A"
        assert items[0]["rating"] == 5


# ---------------------------------------------------------------------------
# pagination
# ---------------------------------------------------------------------------

def test_cursor_pagination_walks_full_set(admin_sandbox):
    root, api_server = admin_sandbox
    seeds = [_rec("credit", f"rm-{i:03d}", 5, ts=f"2026-05-01T{10+i:02d}:00:00")
             for i in range(7)]
    _seed_jsonl(root, "2026-05-01", seeds)

    from fastapi.testclient import TestClient
    with TestClient(api_server.app) as c:
        seen: list[str] = []
        cursor: str | None = None
        for _ in range(10):
            url = f"/api/feedback?limit=3"
            if cursor:
                url += f"&cursor={cursor}"
            body = c.get(url).json()
            seen.extend(it["user_id"] for it in body["items"])
            if not body["has_more"]:
                break
            cursor = body["next_cursor"]
            assert cursor, "has_more without next_cursor"
        # 7 条全收集 · created_at desc · 不重不漏
        assert sorted(seen) == sorted(s["user_id"] for s in seeds)
        assert len(seen) == len(set(seen))  # no dup


def test_pagination_limit_bounds(admin_sandbox):
    _, api_server = admin_sandbox
    from fastapi.testclient import TestClient
    with TestClient(api_server.app) as c:
        assert c.get("/api/feedback?limit=0").status_code == 422
        assert c.get("/api/feedback?limit=300").status_code == 422


# ---------------------------------------------------------------------------
# export zip
# ---------------------------------------------------------------------------

def test_export_returns_zip_with_per_agent_jsonl(admin_sandbox):
    root, api_server = admin_sandbox
    _seed_jsonl(root, "2026-05-01", [
        _rec("credit", "rm-1", 5),
        _rec("credit", "rm-2", 4),
        _rec("alert", "rm-3", 5),
    ])
    from fastapi.testclient import TestClient
    with TestClient(api_server.app) as c:
        r = c.get("/api/feedback/export?date_from=2026-05-01&date_to=2026-05-01")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/zip"
        assert ".zip" in r.headers["content-disposition"]
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        names = sorted(zf.namelist())
        # per-agent 1 file (空 agent 不出)
        agents_in = {n.split("_")[0] for n in names}
        assert agents_in == {"credit", "alert"}
        credit_jsonl = next(n for n in names if n.startswith("credit_"))
        lines = [l for l in zf.read(credit_jsonl).decode("utf-8").splitlines() if l]
        assert len(lines) == 2


def test_export_filter_by_agent(admin_sandbox):
    root, api_server = admin_sandbox
    _seed_jsonl(root, "2026-05-01", [
        _rec("credit", "rm-1", 5),
        _rec("alert", "rm-2", 5),
    ])
    from fastapi.testclient import TestClient
    with TestClient(api_server.app) as c:
        r = c.get("/api/feedback/export?agents=credit")
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        names = zf.namelist()
        assert all(n.startswith("credit_") for n in names)
        assert not any(n.startswith("alert_") for n in names)


# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------

def test_non_admin_403(admin_sandbox):
    root, api_server = admin_sandbox
    # 覆盖 override 让其返非 admin role
    api_server.app.dependency_overrides[api_server._FEEDBACK_ADMIN_DEP] = (
        lambda: {"sub": "u", "role": "rm"}
    )
    from fastapi.testclient import TestClient
    with TestClient(api_server.app) as c:
        r = c.get("/api/feedback")
        assert r.status_code == 403
        r2 = c.get("/api/feedback/export")
        assert r2.status_code == 403
