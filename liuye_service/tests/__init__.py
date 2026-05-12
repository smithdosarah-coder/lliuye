# -*- coding: utf-8 -*-
"""liuye_service.tests — W1-backend test suite (3 modules · 18 file checklist).

Per W1-backend brief §5 DoD + ``liuye_service/CLAUDE.md`` §11 (W1 file
checklist files 16-18). Three test modules with hermetic fixtures:

- ``test_contracts.py``    · 5 protocol Pydantic vs JSON Schema 1:1 ·
                              11 event enum lock + 8 status enum lock
- ``test_sse_adapter.py``  · 7 v1 → 11 liuye event mapping · dedup ·
                              percent conversion · degraded fallback ·
                              parent_tool_call_id passthrough
- ``test_outbox.py``       · OutboxWorker.run + process_entry +
                              _is_dead_letter · 5 retry backoff ·
                              dead-letter graduation · idempotency_key

Each module is fully self-contained · uses ``pytest.MonkeyPatch`` /
``tmp_path`` / ``unittest.mock.patch`` instead of relying on global
state. Tests run via ``py -m pytest liuye_service/tests/ -v`` from
project root.
"""
from __future__ import annotations

__all__: list[str] = []
