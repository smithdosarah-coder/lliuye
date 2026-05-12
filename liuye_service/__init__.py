# -*- coding: utf-8 -*-
"""liuye_service — Liuye Phase 1 BFF for the new ``credit_matrix_next/`` frontend.

This module is the **only** backend entry point for the new frontend. It
translates the 5 Liuye contract protocols (LiuyeChatEvent / Artifact /
ToolCall / KBDoc / EvidenceRef) into HTTP / SSE calls against the existing
6 backend agents (channel / credit / report + riskctrl / alert / compliance).

Layering (per `liuye_service/CLAUDE.md` §1):

- **in-process** calls into ``shared/*`` + ``audit_service/*`` + ``auth_service/*``
- **HTTP** calls into ``agent_*/api.py`` via ``adapters/{agent}.py``
- **forbidden**: any direct ``from agent_* import ...`` of internal modules
  (HTTP isolation hardline · breaks Cowork/Managed boundary)

This file intentionally exports **no** public symbols — consumers must
import explicitly from sub-modules (``liuye_service.api`` /
``liuye_service.schemas`` / ``liuye_service.config`` / ...). This keeps
the import graph readable and makes the W1 file checklist enforceable.

Author: W1-backend worker · 2026-05-12 · checkpoint 2/N (skeleton)
"""
from __future__ import annotations

# Schema version (matches shared/contracts/liuye/contracts.lock.json schema_version)
__version__ = "0.1.0"

__all__ = ["__version__"]
