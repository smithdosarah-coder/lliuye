# -*- coding: utf-8 -*-
"""liuye_service.adapters._sse_v1_parser — SSE v1 line parser.

Extracted from ``channel.py:_iter_sse_v1`` to end the lateral-import
anti-pattern (``credit.py:266`` and ``report.py:258`` both did
``from liuye_service.adapters.channel import _iter_sse_v1``, which
coupled credit/report to channel internals and made the symbol look
private even though it was de-facto shared).

Step 1 (ROI #2) introduces this module; Step 2 rewrites channel.py to
import from here and deletes the in-channel definition, then credit /
report stop importing from channel. After Step 2-3 the lateral-import
chain is fully gone.

Wire form per ``docs/contracts/sse-envelope.md`` §1.5::

    event: <name>
    data: <single-line JSON>
    \\n

We deliberately keep the parser minimal — the legacy 6 agents already
emit well-formed UTF-8 NDJSON lines, so a full SSE parser is overkill.
``event`` inside the JSON ``data`` payload overrides the wire
``event:`` line when both are present (some agents put it both
places).
"""
from __future__ import annotations

import json as _json
from typing import Any, AsyncIterator

import httpx


async def iter_sse_v1(response: httpx.Response) -> AsyncIterator[dict[str, Any]]:
    """Yield decoded v1 event dicts from an httpx streaming response.

    Public name: ``iter_sse_v1`` (no leading underscore) — this is the
    shared parser surface that all three Cowork adapters call through
    ``CoworkHttpAdapter._run_live``. The legacy underscore-prefixed
    alias ``_iter_sse_v1`` is intentionally NOT exported here; Step 2
    deletes that name from channel.py.

    The parser is line-oriented and tolerates:

    - blank lines as event separators (flush buffer)
    - ``event:`` header (sets buffer["event"])
    - ``data:`` line with JSON body (merged into buffer; if the JSON
      itself carries an ``event`` key and the wire ``event:`` header
      was absent, the JSON wins)
    - malformed JSON → keep raw text under ``_raw_data`` so the
      translator can decide what to do
    - SSE ``id:`` lines and comment lines (``:`` prefix) → ignored
    """
    buffer: dict[str, Any] = {}
    async for raw_line in response.aiter_lines():
        line = raw_line.rstrip("\r")
        if not line:
            if buffer:
                yield buffer
                buffer = {}
            continue
        if line.startswith("event:"):
            buffer["event"] = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_text = line[len("data:"):].strip()
            try:
                parsed = _json.loads(data_text) if data_text else {}
                if isinstance(parsed, dict):
                    buffer.update(parsed)
                    # ``event`` field inside payload overrides the
                    # SSE wire ``event:`` line when both are present
                    # (some agents put it both places).
                    if "event" not in buffer and "event" in parsed:
                        buffer["event"] = parsed["event"]
            except _json.JSONDecodeError:
                buffer["_raw_data"] = data_text
        # SSE comment lines (``:`` prefix) or ``id:`` lines are ignored.
    if buffer:
        yield buffer


__all__ = ["iter_sse_v1"]
