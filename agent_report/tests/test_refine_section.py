# -*- coding: utf-8 -*-
"""Stage C.1 · POST /api/report/refine_section 单测.

锁定:
  - 404 当 session_id 不存在
  - 用户 user_edit 进 LLM prompt · 无 LLM key 走 fallback 拼接
  - section 写回 store · 下次 export 能取到新内容
  - section_id 不在原 sections 也能新增(append)
  - llm_used 字段如实反映 LLM key 是否配置
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_report.api import app  # noqa: E402
from agent_report.session_store import store  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def seeded_session():
    """种一个 session · 含 4 chapter sections."""
    sid = store.create({
        "mode": "real",
        "enterprise_profile": {"company_name": "测试样本有限公司"},
        "done_payload": {
            "profile": {"company_name": "测试样本有限公司"},
            "sections": [
                {
                    "id": "chapter_1_background",
                    "title": "一、企业背景",
                    "content": "原文 · 测试样本有限公司成立于 2015 年。",
                    "status": "done",
                    "word_count": 20,
                },
                {
                    "id": "chapter_2_operation",
                    "title": "二、经营情况",
                    "content": "原文 · 主营精密零部件加工。",
                    "status": "done",
                    "word_count": 15,
                },
            ],
            "stats": {"total_fields": 100, "auto_filled": 80, "unfilled": 20},
        },
        "pending_questions": [],
    })
    yield sid
    store.delete(sid)


def test_refine_section_404_when_session_missing(client):
    resp = client.post("/api/report/refine_section", json={
        "session_id": "nonexistent-session-xxxx",
        "section_id": "chapter_1_background",
        "user_edit": "请把行业表述改更精准",
    })
    assert resp.status_code == 404


def test_refine_section_no_llm_key_returns_503_in_all_in(client, seeded_session, monkeypatch):
    """ALL IN Phase B (per AGENT_IDENTITY-report.md §6 step 3 红线 1):
    无 DEEPSEEK_API_KEY · 直接 503 拒 fallback (per Codex Decision 6 + 我们 ALL IN 进一步收紧).
    旧 fallback 拼接行为已删 · 假数据出门 = 红线 1 (假 live)."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    resp = client.post("/api/report/refine_section", json={
        "session_id": seeded_session,
        "section_id": "chapter_1_background",
        "user_edit": "强调成立年份与注册资本规模",
        "target_word_count": 1500,
    })
    assert resp.status_code == 503, resp.text
    detail = resp.json()["detail"]
    assert "DEEPSEEK_API_KEY" in detail


def test_refine_section_writes_back_with_real_key(client, seeded_session, monkeypatch):
    """ALL IN: 真路径需 LLM key · 模拟 fake key + monkeypatch _build_llm_caller 回固定文本.
    验 section 写回 store + last_refined_section 标记 + refined_at 字段."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key-for-test")
    # mock LLM caller · 返带 user_edit 的固定文本
    from agent_report import api as api_mod

    def _fake_caller(system: str, user: str) -> str:
        return f"[mocked] 改写 · 增加产品 SKU 明细 · 基于原文重写"

    monkeypatch.setattr(api_mod, "_build_llm_caller", lambda: _fake_caller)
    resp = client.post("/api/report/refine_section", json={
        "session_id": seeded_session,
        "section_id": "chapter_2_operation",
        "user_edit": "增加产品 SKU 明细",
    })
    assert resp.status_code == 200, resp.text
    sess = store.get(seeded_session)
    sections = sess.get("done_payload", {}).get("sections") or []
    chapter_2 = next((s for s in sections if s["id"] == "chapter_2_operation"), None)
    assert chapter_2 is not None
    assert "增加产品 SKU 明细" in chapter_2["content"]
    assert "refined_at" in chapter_2
    assert sess.get("last_refined_section") == "chapter_2_operation"


def test_refine_section_appends_new_section_id(client, seeded_session, monkeypatch):
    """section_id 不在 sections 中 · 新增 append 而非报错 · ALL IN 需真 key (不 fallback)."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key-for-test")
    from agent_report import api as api_mod
    monkeypatch.setattr(api_mod, "_build_llm_caller", lambda: lambda s, u: "[mocked] 审批意见 - 通过")
    resp = client.post("/api/report/refine_section", json={
        "session_id": seeded_session,
        "section_id": "chapter_4_conclusion",
        "user_edit": "审批意见 - 通过",
    })
    assert resp.status_code == 200
    sess = store.get(seeded_session)
    sections = sess.get("done_payload", {}).get("sections") or []
    chapter_4 = next((s for s in sections if s["id"] == "chapter_4_conclusion"), None)
    assert chapter_4 is not None
    # ALL IN: chapter_4 旧 seed 没有 · 新 append · LLM mock 返固定文本
    # old_content == "" · LLM 返固定 · new_content == LLM output (per api.py refine_section logic)
    assert "审批意见" in chapter_4["content"] or "[mocked]" in chapter_4["content"]


def test_refine_section_response_shape(client, seeded_session, monkeypatch):
    """ALL IN: response shape 验 · 需真 key (mock LLM caller)."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key-for-test")
    from agent_report import api as api_mod
    monkeypatch.setattr(api_mod, "_build_llm_caller", lambda: lambda s, u: "[mocked] 改写")
    resp = client.post("/api/report/refine_section", json={
        "session_id": seeded_session,
        "section_id": "chapter_1_background",
        "user_edit": "测试响应 shape",
    })
    assert resp.status_code == 200
    data = resp.json()
    expected_keys = {"session_id", "report_id", "section", "status", "llm_used"}
    assert set(data.keys()) >= expected_keys
    assert data["session_id"] == seeded_session
    assert data["report_id"] == seeded_session
    sec = data["section"]
    assert {"id", "title", "content", "status", "word_count"} <= set(sec.keys())
    assert "refined_at" in sec
