# -*- coding: utf-8 -*-
"""liuye_service.workers — background workers for outbox retry + cleanup.

Per W1-backend brief §3 file 14 + ``liuye_service/CLAUDE.md`` §7 + v3 §5.x.

Sub-modules:
- ``outbox_retry`` — 60s loop · scans ``data/liuye/outbox/`` · 5 retries
  with exponential backoff (60/120/240/480/960s) · ledger write silent-fail
  recovery · dead-letter on permanent failure.

Deployed as a systemd service (``deploy/liuye-outbox.service``) running
``python -m liuye_service.workers.outbox_retry`` in a separate process
from the FastAPI app. This isolates retry loops from request handling
and survives FastAPI worker restarts without losing events.
"""
from __future__ import annotations

__all__: list[str] = []
