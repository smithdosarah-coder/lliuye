# -*- coding: utf-8 -*-
"""liuye_service.adapters — agent adapters + SSE v1→liuye wire translation.

Per W1-backend brief §3 file 9-13 + ``liuye_service/CLAUDE.md`` §3 + §4.

This package intentionally exports **nothing** from ``__init__``. Each adapter
sub-module owns its own surface and consumers must import explicitly:

    from liuye_service.adapters.channel import ChannelAdapter
    from liuye_service.adapters.sse_v1_to_liuye import SseV1ToLiuyeAdapter

Keeping the package empty enforces the W1 file checklist (one adapter per
agent) and avoids accidental circular imports between the SSE translator
and the per-agent HTTP clients.

Layering (per ``liuye_service/CLAUDE.md`` §2.2 + §3):

- ``base.py``               · ``AgentAdapter`` Protocol + seq counter +
                              fixtures loader (Cowork/Managed shared base)
- ``sse_v1_to_liuye.py``    · 7 SSE v1 events → 11 liuye events (one v1
                              event MAY emit 0..N liuye events) · dedup +
                              seq injection + degraded ``turn.error``
- ``channel.py``            · Cowork · HTTP ``/api/channel/run``
- ``credit.py``             · Cowork · HTTP ``/api/credit/run``
- ``report.py``             · Cowork · HTTP ``/api/report/v16/fill``
- ``riskctrl.py``           · Managed · Phase 2 stub (raises NotImplementedError)
- ``alert.py``              · Managed · Phase 2 stub
- ``compliance.py``         · Managed · Phase 2 stub
"""
from __future__ import annotations

__all__: list[str] = []
