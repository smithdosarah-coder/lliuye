# -*- coding: utf-8 -*-
"""ledger_service — REST surface for the cross-agent decision ledger (BE7).

The actual store lives in `shared/decision_ledger/`. This package wraps
it in admin-only FastAPI endpoints for ledger queries + audit export +
reviewer signature.

Mounted from `api_server.py` via::

    from ledger_service.api import register_ledger_routes
    register_ledger_routes(app)
"""

from __future__ import annotations

from .api import register_ledger_routes

__all__ = ["register_ledger_routes"]
