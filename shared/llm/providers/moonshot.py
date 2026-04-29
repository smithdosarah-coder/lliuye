# -*- coding: utf-8 -*-
"""shared.llm.providers.moonshot — re-export shim · 实际定义见 shared.llm_caller.provider.

Phase A worker-A2 · 2026-04-29 · Stage E.3 → llm_caller 收编.
"""
from __future__ import annotations

from shared.llm_caller.provider import MoonshotProvider

__all__ = ["MoonshotProvider"]
