# -*- coding: utf-8 -*-
"""V2 fix (codex review critical 3) · SSE event-stream parser helper.

Phase A worker-A4 已把 /api/riskctrl/dsl_gen + /api/riskctrl/backtest
迁 SSE (StreamingResponse · text/event-stream).

V1 test 仍按 v4.0 JSON 形态写 → 10 fail (resp.json() 解 SSE blob 报错).
V2 fix 把 test 改 parse SSE 形态 · 仍验证业务断言.

SSE format (per shared.sse_envelope):
    data: {"event": "stage", "stage": "...", "status": "...", ...}\n\n
    data: {"event": "done", "panels": {...}, "metrics": {...}, ...}\n\n
    data: {"event": "error", "message": "...", "code": "..."}\n\n
"""
from __future__ import annotations

import json
from typing import Any


def parse_sse_events(text: str) -> list[dict]:
    """Parse SSE event-stream text → list of event dicts.

    Args:
        text: response.text · 含多行 'data: {json}\\n\\n' blocks

    Returns:
        list of parsed event dicts (filter empty / non-data lines)
    """
    events: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data: "):
            continue
        payload = line[len("data: "):].strip()
        if not payload:
            continue
        try:
            obj = json.loads(payload)
            events.append(obj)
        except json.JSONDecodeError:
            continue
    return events


def find_done_event(text: str) -> dict | None:
    """Pull the 'done' event from SSE stream (last one wins · 一般只 1 个)."""
    for ev in parse_sse_events(text):
        if ev.get("event") == "done":
            return ev
    return None


def find_error_event(text: str) -> dict | None:
    """Pull the 'error' event."""
    for ev in parse_sse_events(text):
        if ev.get("event") == "error":
            return ev
    return None


def find_stages(text: str) -> list[dict]:
    """Pull all 'stage' events."""
    return [ev for ev in parse_sse_events(text) if ev.get("event") == "stage"]


def assert_sse_done(resp, msg: str = "") -> dict:
    """Assert SSE response 含 done event · 返 done payload.

    Replaces the legacy:
        assert resp.status_code == 200
        data = resp.json()
    pattern.
    """
    assert resp.status_code == 200, f"{msg}: status={resp.status_code} text={resp.text[:300]}"
    done = find_done_event(resp.text)
    assert done is not None, f"{msg}: no done event in SSE stream · text={resp.text[:300]}"
    return done


def assert_sse_error(resp, expected_code: str | None = None) -> dict:
    """Assert SSE response 含 error event · 返 error payload.

    Replaces the legacy:
        assert resp.status_code == 400
    pattern.

    Note: SSE 的 error 仍 走 200 response (StreamingResponse) · 业务错误在 event payload 里.
    """
    # SSE error 有时也走 200 · 也可能走 400 (e.g. csv_path 不存在 早期 yield 后 stream 关)
    assert resp.status_code in (200, 400, 422, 500), f"unexpected status: {resp.status_code}"
    err = find_error_event(resp.text)
    assert err is not None, f"no error event · text={resp.text[:300]}"
    if expected_code is not None:
        assert err.get("code") == expected_code, (
            f"error.code={err.get('code')} != {expected_code}"
        )
    return err


def get_panel(done_ev: dict, panel_name: str) -> Any:
    """Extract panel from done event.

    Per shared.sse_envelope.make_done · panels 字段展开到 done 顶层
    (e.g. panels={'ruleset': X} → done['ruleset'] · 非 done['panels']['ruleset']).
    本 helper 兼容两种情况 (顶层优先 · 嵌套 fallback).
    """
    if not done_ev:
        return None
    if panel_name in done_ev:
        return done_ev[panel_name]
    return done_ev.get("panels", {}).get(panel_name)


def get_metric(done_ev: dict, metric_name: str) -> Any:
    """Extract top-level metric from done event.

    Per shared.sse_envelope.make_done · metrics 字段不展开 · 走 done['metrics'][k].
    """
    return (done_ev or {}).get("metrics", {}).get(metric_name)


__all__ = [
    "assert_sse_done",
    "assert_sse_error",
    "find_done_event",
    "find_error_event",
    "find_stages",
    "get_metric",
    "get_panel",
    "parse_sse_events",
]
