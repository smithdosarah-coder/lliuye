# -*- coding: utf-8 -*-
"""Tests for POST /api/compliance/policy_diff endpoint contract (B5 sub-PR 1).

per Codex post-DONE review B5 contract verdict NEEDS-FIX major issue:
- 200 SSE stage + done
- 400 old_policy / new_policy empty
- (auth 403 deferred to sub-PR 2 wire require_action)
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from agent_compliance.api import app


client = TestClient(app)


def test_policy_diff_200_stage_and_done():
    """200 SSE stream · stage event + done event with stub payload."""
    resp = client.post(
        "/api/compliance/policy_diff",
        json={"old_policy": "old policy text", "new_policy": "new policy text", "scope": "对公授信"},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    body = resp.text
    # stage event: stage=diff status=running
    assert '"event":"stage"' in body or '"event": "stage"' in body
    assert '"stage":"diff"' in body or '"stage": "diff"' in body
    assert '"status":"running"' in body or '"status": "running"' in body
    # done event with stub payload
    assert '"event":"done"' in body or '"event": "done"' in body
    assert '"status":"stub"' in body or '"status": "stub"' in body


def test_policy_diff_200_without_scope():
    """200 SSE · scope optional."""
    resp = client.post(
        "/api/compliance/policy_diff",
        json={"old_policy": "a", "new_policy": "b"},
    )
    assert resp.status_code == 200


def test_policy_diff_400_empty_old_policy():
    """400 VALIDATION_FAILED · old_policy 不能为空."""
    resp = client.post(
        "/api/compliance/policy_diff",
        json={"old_policy": "", "new_policy": "new"},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["error"]["code"] == "VALIDATION_FAILED"
    assert "old_policy" in detail["error"]["message"]


def test_policy_diff_400_whitespace_old_policy():
    """400 · old_policy 全空白."""
    resp = client.post(
        "/api/compliance/policy_diff",
        json={"old_policy": "   ", "new_policy": "new"},
    )
    assert resp.status_code == 400


def test_policy_diff_400_empty_new_policy():
    """400 VALIDATION_FAILED · new_policy 不能为空."""
    resp = client.post(
        "/api/compliance/policy_diff",
        json={"old_policy": "old", "new_policy": ""},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["error"]["code"] == "VALIDATION_FAILED"
    assert "new_policy" in detail["error"]["message"]


def test_policy_diff_payload_includes_lengths():
    """done payload 含 old_policy_length + new_policy_length (sub-PR 1 stub debug)."""
    resp = client.post(
        "/api/compliance/policy_diff",
        json={"old_policy": "abc", "new_policy": "abcde"},
    )
    assert resp.status_code == 200
    body = resp.text
    assert '"old_policy_length":3' in body or '"old_policy_length": 3' in body
    assert '"new_policy_length":5' in body or '"new_policy_length": 5' in body
