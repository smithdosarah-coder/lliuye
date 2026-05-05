# -*- coding: utf-8 -*-
"""Conftest for tests/agent_channel/ · auto-set admin auth cookie on TestClient.

Phase B Sprint 3 sub-PR 2 V2-FIX (2026-05-05):
  - 6 agent endpoint 加 require_action(...) gate (per Q-052 #8)
  - channel /run /handoff /export_docx /export_xlsx 全 require_action gated
  - 现有 channel tests 用 TestClient(app) 不带 cookie · 改 401 fail
  - 此 conftest autouse fixture 自动注 admin cookie (admin 全 6 agent × 5 action 全权)
  - 业务测试不关心 auth · 注 admin cookie 是 cleanest skip-auth path

Note: 不改 require_action contract · 仍真 enforce · 只是测试场景 bypass.
RBAC matrix 全覆盖 test 在 auth_service/tests/test_users_jwt_rbac.py (5×6×5=150).
RM 403 endpoint test 在 tests/agent_compliance/test_policy_diff_endpoint.py +
agent_riskctrl/tests/test_llm_dsl_gen.py.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _autoinject_admin_cookie(monkeypatch):
    """Patch TestClient.__init__ to auto-set admin auth cookie on every instance.

    Effect: 任何 tests/agent_channel/ 内 `TestClient(app)` instance 都自动带 admin cookie ·
    pass require_action(channel, *) gate · 业务断言不变.
    """
    from auth_service.dependencies import COOKIE_NAME
    from auth_service.jwt_util import issue

    original_init = TestClient.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        # admin role · ACCESS_V2 全 action 全 agent · pass require_action gate
        self.cookies.set(COOKIE_NAME, issue("u_test", "admin"))

    monkeypatch.setattr(TestClient, "__init__", patched_init)
