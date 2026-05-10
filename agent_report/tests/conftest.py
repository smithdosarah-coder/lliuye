# -*- coding: utf-8 -*-
"""Conftest for agent_report/tests/ · auto-set admin auth cookie on TestClient.

ALL IN Phase B (per AGENT_IDENTITY-report.md §6 step 3 · 2026-05-09):
  - /api/report/v16/fill / export_docx / export_pdf / v16/inject 全 require_action gated
  - 现有 endpoint test 用 TestClient(app) 不带 cookie · 改 401 fail (pre-existing 问题)
  - 此 conftest autouse fixture 自动注 admin cookie · pass require_action(report, *) gate
  - 复用 tests/agent_channel/conftest.py 同款 pattern (Phase B Sprint 3 V2-FIX)
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _autoinject_admin_cookie(monkeypatch):
    """Patch TestClient.__init__ to auto-set admin auth cookie on every instance."""
    from auth_service.dependencies import COOKIE_NAME
    from auth_service.jwt_util import issue

    original_init = TestClient.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.cookies.set(COOKIE_NAME, issue("u_test", "admin"))

    monkeypatch.setattr(TestClient, "__init__", patched_init)
