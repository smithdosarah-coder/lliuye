# -*- coding: utf-8 -*-
"""tests/shared/test_sse_envelope.py — Phase A worker-A2 (M8 of 9).

Coverage:
  · Constants  · 4 EVENT_* + 5 DATA_SOURCE_* + CHANNEL_PANEL_KEYS shape
  · make_stage / make_section / make_done / make_error / make_error_from_exception
  · validate_panels (full / missing / None)
  · encode_event format (data: ...\\n\\n)
  · AGENT_PANEL_KEYS_RECOMMENDED 6 agent
"""
from __future__ import annotations

import json

import pytest

from shared.sse_envelope import (
    AGENT_PANEL_KEYS_RECOMMENDED,
    CHANNEL_PANEL_KEYS,
    DATA_SOURCE_CACHED,
    DATA_SOURCE_LIVE,
    DATA_SOURCE_MOCK,
    DATA_SOURCE_MOCK_FALLBACK,
    DATA_SOURCE_MOCK_FORCED,
    EVENT_DONE,
    EVENT_ERROR,
    EVENT_SECTION,
    EVENT_STAGE,
    encode_event,
    make_done,
    make_error,
    make_error_from_exception,
    make_section,
    make_stage,
    validate_panels,
)


# ============================================================================
# Constants
# ============================================================================


def test_event_constants():
    assert EVENT_STAGE == "stage"
    assert EVENT_SECTION == "section"
    assert EVENT_DONE == "done"
    assert EVENT_ERROR == "error"


def test_data_source_constants():
    assert DATA_SOURCE_LIVE == "live"
    assert DATA_SOURCE_MOCK == "mock"
    assert DATA_SOURCE_MOCK_FORCED == "mock_forced"
    assert DATA_SOURCE_MOCK_FALLBACK == "mock_fallback"
    assert DATA_SOURCE_CACHED == "cached"


def test_channel_panel_keys_canonical():
    """workspace-state-protocol §4 Channel canonical 8 keys (V3 加 conversation)."""
    expected = {
        "candidates", "signals", "radar", "funnel",
        "match_dimensions", "product_recommendations", "pitch_scripts",
        "conversation",
    }
    assert set(CHANNEL_PANEL_KEYS) == expected


def test_agent_panel_keys_6_agent():
    """6 agent recommended panel sets · A4 worker spec 后调."""
    assert set(AGENT_PANEL_KEYS_RECOMMENDED) == {
        "channel", "credit", "alert", "compliance", "riskctrl", "report",
    }
    # 每 agent 至少 4 panel
    for agent, keys in AGENT_PANEL_KEYS_RECOMMENDED.items():
        assert len(keys) >= 4, f"{agent} panel set too few"


# ============================================================================
# make_stage
# ============================================================================


def test_make_stage_minimal():
    s = make_stage("intent", "running")
    assert s == {"event": "stage", "stage": "intent", "status": "running"}


def test_make_stage_with_message():
    s = make_stage("intent", "done", "意图解析完成")
    assert s["message"] == "意图解析完成"


def test_make_stage_with_extras():
    s = make_stage("rank", "done", count=10, progress=1.0)
    assert s["count"] == 10
    assert s["progress"] == 1.0


def test_make_stage_no_message_when_empty():
    """空 message 不进 dict (节省 SSE bandwidth)."""
    s = make_stage("intent", "running", "")
    assert "message" not in s


# ============================================================================
# make_section
# ============================================================================


def test_make_section_shape():
    s = make_section("chapter_1", "一、企业背景", "正文...")
    assert s["event"] == "section"
    assert s["section"]["id"] == "chapter_1"
    assert s["section"]["title"] == "一、企业背景"
    assert s["section"]["content"] == "正文..."


def test_make_section_with_extras():
    s = make_section("ch1", "T", "C", evidence_count=5, audit_pass=True)
    assert s["section"]["evidence_count"] == 5
    assert s["section"]["audit_pass"] is True


# ============================================================================
# make_done
# ============================================================================


def test_make_done_empty_raises():
    """V2 fix issue 2 · 空 payload (无 panels/metrics/downstream/session_id/extras) → raise."""
    with pytest.raises(ValueError, match="at least one of"):
        make_done()


def test_make_done_data_source_alone_still_raises():
    """仅 data_source 不算 payload · 仍 raise (V2)."""
    with pytest.raises(ValueError):
        make_done(data_source=DATA_SOURCE_LIVE)


def test_make_done_session_id_only_ok():
    """有 session_id 即算非空 payload · 通过 (V2 边界)."""
    d = make_done(session_id="sess_x")
    assert d["session_id"] == "sess_x"


def test_make_done_metrics_only_ok():
    """有 metrics 即算非空 payload · 通过 (V2 边界)."""
    d = make_done(metrics={"final": 5})
    assert d["metrics"] == {"final": 5}


def test_make_done_extras_only_ok():
    """仅 extras (旧 done shape · e.g. report_docx_url) · 通过."""
    d = make_done(report_docx_url="/x.docx")
    assert d["report_docx_url"] == "/x.docx"


def test_make_done_full_channel_panels():
    """workspace-state-protocol §4 · Channel done shape."""
    panels = {k: f"<{k}>" for k in CHANNEL_PANEL_KEYS}
    d = make_done(
        panels=panels,
        metrics={"signalTotal": 50, "final": 10},
        data_source=DATA_SOURCE_LIVE,
        session_id="sess_abc",
    )
    assert d["event"] == "done"
    assert d["session_id"] == "sess_abc"
    assert d["data_source"] == "live"
    assert d["metrics"] == {"signalTotal": 50, "final": 10}
    # panels 展开到顶层 (与 evt.candidates / evt.radar 直读兼容)
    for k in CHANNEL_PANEL_KEYS:
        assert d[k] == f"<{k}>"


def test_make_done_with_downstream():
    """Agent6→Agent3 / Agent3→Agent4 cross-agent handoff payload."""
    d = make_done(downstream={"target": "agent3", "payload": {"x": 1}})
    assert d["downstream"] == {"target": "agent3", "payload": {"x": 1}}


def test_make_done_extras_passthrough():
    """旧 done event 字段 (e.g. report_docx_url) 通过 **extras 兼容."""
    d = make_done(report_docx_url="/downloads/x.docx", enterprise_profile={"name": "X"})
    assert d["report_docx_url"] == "/downloads/x.docx"
    assert d["enterprise_profile"] == {"name": "X"}


def test_make_done_data_source_mock_fallback():
    """Tavily key 缺 silent fallback 用 DATA_SOURCE_MOCK_FALLBACK · 前端 banner 触发.

    V2 fix issue 2 · 必带 payload (此处用 metrics 占非空) · 前端 banner 仍只看 data_source.
    """
    d = make_done(metrics={"final": 0}, data_source=DATA_SOURCE_MOCK_FALLBACK)
    assert d["data_source"] == "mock_fallback"


# ============================================================================
# make_error / make_error_from_exception
# ============================================================================


def test_make_error_minimal():
    e = make_error("boom")
    assert e == {"event": "error", "message": "boom"}


def test_make_error_full():
    e = make_error("boom", traceback="trace...", code="LLM_TIMEOUT")
    assert e["code"] == "LLM_TIMEOUT"
    assert e["traceback"] == "trace..."


def test_make_error_from_exception():
    try:
        raise ValueError("test boom")
    except ValueError as exc:
        err = make_error_from_exception(exc, code="VAL_ERR")
        assert err["event"] == "error"
        assert "ValueError: test boom" in err["message"]
        assert err["code"] == "VAL_ERR"
        # traceback 取尾 2000 字符
        assert isinstance(err.get("traceback", ""), str)


def test_make_error_from_exception_no_traceback():
    try:
        raise RuntimeError("x")
    except RuntimeError as exc:
        err = make_error_from_exception(exc, include_traceback=False)
        assert "traceback" not in err


# ============================================================================
# validate_panels
# ============================================================================


def test_validate_panels_full():
    panels = {k: [] for k in CHANNEL_PANEL_KEYS}
    ok, missing = validate_panels(panels, CHANNEL_PANEL_KEYS)
    assert ok is True
    assert missing == []


def test_validate_panels_missing():
    panels = {"candidates": []}
    ok, missing = validate_panels(panels, CHANNEL_PANEL_KEYS)
    assert ok is False
    assert "radar" in missing
    assert "funnel" in missing
    # candidates 已有 · 不 missing
    assert "candidates" not in missing


def test_validate_panels_none():
    ok, missing = validate_panels(None, CHANNEL_PANEL_KEYS)
    assert ok is False
    assert len(missing) == len(CHANNEL_PANEL_KEYS)


def test_validate_panels_empty_dict():
    ok, missing = validate_panels({}, CHANNEL_PANEL_KEYS)
    assert ok is False
    assert len(missing) == len(CHANNEL_PANEL_KEYS)


# ============================================================================
# encode_event
# ============================================================================


def test_encode_event_format():
    """SSE encoded format: data: <json>\\n\\n."""
    enc = encode_event({"event": "done"})
    assert enc.startswith("data: ")
    assert enc.endswith("\n\n")
    body = enc[len("data: "):-2]
    assert json.loads(body) == {"event": "done"}


def test_encode_event_chinese():
    """中文 message · ensure_ascii=False (api_utils.sse_encode 行为)."""
    enc = encode_event({"event": "stage", "message": "解析意图"})
    assert "解析意图" in enc


def test_encode_event_to_jsonable():
    """to_jsonable 兜 dataclass / 自定义对象 · 例 ProviderResult."""
    from shared.llm_caller import ProviderResult  # noqa: PLC0415
    r = ProviderResult(content="x", provider_name="deepseek", region="cn")
    enc = encode_event({"event": "done", "result": r})
    assert "deepseek" in enc


# ============================================================================
# Round trip · stage + done + encode
# ============================================================================


def test_round_trip_stage_done_encode():
    """模拟 generator yield 序列 · 都 encode 成 SSE."""
    events = [
        make_stage("intent", "running", "解析..."),
        make_stage("intent", "done"),
        make_stage("scan", "running"),
        make_done(
            panels={k: [] for k in CHANNEL_PANEL_KEYS},
            metrics={"final": 0},
            data_source=DATA_SOURCE_MOCK_FORCED,
            session_id="s1",
        ),
    ]
    encoded = [encode_event(e) for e in events]
    assert all(s.startswith("data: ") and s.endswith("\n\n") for s in encoded)
    # 末 event 是 done · 含 candidates 顶层字段
    last_body = encoded[-1][len("data: "):-2]
    last = json.loads(last_body)
    assert last["event"] == "done"
    assert "candidates" in last
    assert last["data_source"] == "mock_forced"
