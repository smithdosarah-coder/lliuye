# -*- coding: utf-8 -*-
"""tests/auth_service/test_demo_mode.py · Phase A.6 hotfix · 2026-05-09.

per PM spec · 6 case 矩阵覆盖:
  1. admin + env=1   → demoModeAvailable True
  2. admin + env=0   → False (env 默认 production 安全)
  3. RM + env=1      → False (role 不在 DEMO_ELIGIBLE_ROLES)
  4. RM + env=0      → False
  5. demo_user + env=1 → True
  6. 未登录            → False (require_user 401 · 无法到 demoModeAvailable 判定)

附加: can_action("demo") + require_action("demo") + require_demo() 行为验证
"""
from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import pytest

from auth_service.dependencies import (
    COOKIE_NAME,
    require_action,
    require_demo,
    require_user,
)
from auth_service.jwt_util import issue
from auth_service.rbac import (
    DEMO_ELIGIBLE_ROLES,
    can_action,
    demo_mode_visible,
)


# ============================================================================
# Unit · demo_mode_visible(user, env) helper · 6 case 矩阵
# ============================================================================


def _user(role: str, sub: str = "u_x") -> dict:
    """模拟 JWT payload."""
    return {"sub": sub, "role": role}


class TestDemoModeVisible:
    """6 case matrix per PM spec."""

    def test_admin_env_1_visible(self):
        # case 1: admin + env=1 → True
        result = demo_mode_visible(_user("admin"), env={"DEMO_MODE_VISIBLE": "1"})
        assert result is True

    def test_admin_env_0_hidden(self):
        # case 2: admin + env=0 → False (production 默认 safe)
        result = demo_mode_visible(_user("admin"), env={"DEMO_MODE_VISIBLE": "0"})
        assert result is False

    def test_rm_env_1_role_denied(self):
        # case 3: RM + env=1 → False (role 不在 DEMO_ELIGIBLE_ROLES · 即使 env 开)
        result = demo_mode_visible(_user("rm"), env={"DEMO_MODE_VISIBLE": "1"})
        assert result is False

    def test_rm_env_0_hidden(self):
        # case 4: RM + env=0 → False (双重否决)
        result = demo_mode_visible(_user("rm"), env={"DEMO_MODE_VISIBLE": "0"})
        assert result is False

    def test_demo_user_env_1_visible(self):
        # case 5: demo_user + env=1 → True
        result = demo_mode_visible(_user("demo_user"), env={"DEMO_MODE_VISIBLE": "1"})
        assert result is True

    def test_anonymous_no_user(self):
        # case 6: 未登录 → False (user=None)
        assert demo_mode_visible(None, env={"DEMO_MODE_VISIBLE": "1"}) is False
        assert demo_mode_visible(None, env={"DEMO_MODE_VISIBLE": "0"}) is False


class TestDemoModeVisibleEdge:
    """边界 · default env / 默认 production safe / 其他 role / 非 dict user."""

    def test_demo_user_env_0_hidden(self):
        # demo_user + env=0 → False (env 否决)
        assert demo_mode_visible(_user("demo_user"), env={"DEMO_MODE_VISIBLE": "0"}) is False

    def test_credit_officer_denied(self):
        assert demo_mode_visible(_user("credit_officer"), env={"DEMO_MODE_VISIBLE": "1"}) is False

    def test_compliance_officer_denied(self):
        assert demo_mode_visible(_user("compliance_officer"), env={"DEMO_MODE_VISIBLE": "1"}) is False

    def test_risk_manager_denied(self):
        assert demo_mode_visible(_user("risk_manager"), env={"DEMO_MODE_VISIBLE": "1"}) is False

    def test_unknown_role_denied(self):
        assert demo_mode_visible(_user("hacker"), env={"DEMO_MODE_VISIBLE": "1"}) is False

    def test_missing_role_denied(self):
        # user dict 缺 role 字段
        assert demo_mode_visible({"sub": "u_x"}, env={"DEMO_MODE_VISIBLE": "1"}) is False

    def test_env_default_production_safe(self):
        # env 不传 → 走 os.environ · 测试场景下默认 0
        # (CI / 本地测试都不应有 DEMO_MODE_VISIBLE=1)
        import os
        # 显式清除 env (如果碰巧设了)
        os.environ.pop("DEMO_MODE_VISIBLE", None)
        assert demo_mode_visible(_user("admin")) is False

    def test_env_string_other_values(self):
        # 只 "1" 才 True · "true" / "yes" / "TRUE" 都 False (避免 ambiguous)
        assert demo_mode_visible(_user("admin"), env={"DEMO_MODE_VISIBLE": "true"}) is False
        assert demo_mode_visible(_user("admin"), env={"DEMO_MODE_VISIBLE": "yes"}) is False
        assert demo_mode_visible(_user("admin"), env={"DEMO_MODE_VISIBLE": "TRUE"}) is False
        assert demo_mode_visible(_user("admin"), env={"DEMO_MODE_VISIBLE": " 1 "}) is True  # strip

    def test_demo_eligible_roles_locked(self):
        # ABI · DEMO_ELIGIBLE_ROLES 锁定 admin / demo_user
        assert DEMO_ELIGIBLE_ROLES == frozenset({"admin", "demo_user"})


# ============================================================================
# Unit · can_action("demo") · special-case 验证
# ============================================================================


class TestCanActionDemo:
    def test_admin_demo_all_agents(self, monkeypatch):
        # Phase B.1 fix #2 · can_action("demo") 现需 env DEMO_MODE_VISIBLE=1
        monkeypatch.setenv("DEMO_MODE_VISIBLE", "1")
        for ag in ("channel", "report", "credit", "alert", "compliance", "riskctrl"):
            assert can_action("admin", ag, "demo") is True

    def test_admin_demo_denied_when_env_disabled(self, monkeypatch):
        # Phase B.1 fix #2 · admin 无 env 也拒绝 (双控)
        monkeypatch.setenv("DEMO_MODE_VISIBLE", "0")
        assert can_action("admin", "credit", "demo") is False

    def test_demo_user_demo_all_agents(self, monkeypatch):
        monkeypatch.setenv("DEMO_MODE_VISIBLE", "1")
        for ag in ("channel", "report", "credit", "alert", "compliance", "riskctrl"):
            assert can_action("demo_user", ag, "demo") is True

    def test_demo_user_denied_when_env_disabled(self, monkeypatch):
        monkeypatch.setenv("DEMO_MODE_VISIBLE", "0")
        assert can_action("demo_user", "credit", "demo") is False

    def test_demo_user_no_other_action(self):
        # demo_user 仅 demo 权限 · 不 invoke 不 read 不 export 不 handoff 不 approve
        for ag in ("channel", "report", "credit", "alert", "compliance", "riskctrl"):
            for act in ("invoke", "read", "export", "handoff", "approve"):
                assert can_action("demo_user", ag, act) is False, f"{ag}/{act} should be False"

    def test_rm_demo_denied(self):
        assert can_action("rm", "channel", "demo") is False

    def test_credit_officer_demo_denied(self):
        assert can_action("credit_officer", "credit", "demo") is False

    def test_unknown_role_demo_denied(self):
        assert can_action("hacker", "channel", "demo") is False


# ============================================================================
# Integration · /api/auth/me payload demoModeAvailable · TestClient
# ============================================================================


@pytest.fixture(scope="module")
def client():
    from api_server import app
    return TestClient(app)


def _login(client, uid: str, pwd: str) -> str:
    """Login helper · 返 cookie."""
    resp = client.post("/api/auth/login", json={"user_id": uid, "password": pwd})
    assert resp.status_code == 200, resp.text
    return resp.cookies.get(COOKIE_NAME)


class TestAuthMeDemoModeAvailable:
    """/api/auth/me payload 加 demoModeAvailable 字段 · per Phase A.6 spec."""

    def test_admin_env_1_payload_true(self, client, monkeypatch):
        monkeypatch.setenv("DEMO_MODE_VISIBLE", "1")
        cookie = _login(client, "u_liuye", "liuye")  # admin
        resp = client.get("/api/auth/me", cookies={COOKIE_NAME: cookie})
        assert resp.status_code == 200
        assert resp.json()["demoModeAvailable"] is True

    def test_admin_env_0_payload_false(self, client, monkeypatch):
        monkeypatch.setenv("DEMO_MODE_VISIBLE", "0")
        cookie = _login(client, "u_liuye", "liuye")  # admin
        resp = client.get("/api/auth/me", cookies={COOKIE_NAME: cookie})
        assert resp.status_code == 200
        assert resp.json()["demoModeAvailable"] is False

    def test_rm_env_1_payload_false(self, client, monkeypatch):
        monkeypatch.setenv("DEMO_MODE_VISIBLE", "1")
        cookie = _login(client, "u_wangzhe", "wangzhe")  # rm
        resp = client.get("/api/auth/me", cookies={COOKIE_NAME: cookie})
        assert resp.status_code == 200
        assert resp.json()["demoModeAvailable"] is False

    def test_anonymous_401(self, client):
        # 清前面 test 残留 cookie (TestClient module-scope 共享)
        client.cookies.clear()
        resp = client.get("/api/auth/me")
        # 未登录 · require_user 401 · payload 永不返
        assert resp.status_code == 401

    def test_payload_keeps_existing_fields(self, client, monkeypatch):
        # backward compat · existing fields 不破
        monkeypatch.setenv("DEMO_MODE_VISIBLE", "0")
        cookie = _login(client, "u_wangzhe", "wangzhe")
        resp = client.get("/api/auth/me", cookies={COOKIE_NAME: cookie})
        data = resp.json()
        assert "user" in data
        assert "roles" in data
        assert "accessibleAgents" in data
        assert "demoModeAvailable" in data  # 新加


# ============================================================================
# Integration · require_action("demo") + require_demo() 401 行为 · TestClient
# ============================================================================


@pytest.fixture(scope="module")
def app_with_demo_route():
    """构造测试 app · 挂 demo-only endpoint 验 require_action/demo 行为."""
    from api_server import app as base_app
    test_app = FastAPI()

    # 复用 base_app 的 login endpoint 派 cookie
    for route in base_app.routes:
        if getattr(route, "path", "") in {"/api/auth/login"}:
            test_app.routes.append(route)

    @test_app.post("/api/test/demo_only")
    async def demo_only(user=Depends(require_demo())):
        return {"ok": True, "role": user.get("role")}

    @test_app.post("/api/test/require_action_demo")
    async def require_action_demo(
        user=Depends(require_action("channel", "demo")),
    ):
        return {"ok": True, "role": user.get("role")}

    return test_app


@pytest.fixture
def demo_client(app_with_demo_route):
    return TestClient(app_with_demo_route)


class TestRequireDemoEndpoint:
    def test_admin_allowed(self, demo_client):
        cookie = _login(demo_client, "u_liuye", "liuye")
        resp = demo_client.post("/api/test/demo_only", cookies={COOKIE_NAME: cookie})
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

    def test_rm_forbidden_401(self, demo_client):
        # PM spec · RM invoke "demo" → 401
        cookie = _login(demo_client, "u_wangzhe", "wangzhe")
        resp = demo_client.post("/api/test/demo_only", cookies={COOKIE_NAME: cookie})
        assert resp.status_code == 401
        body = resp.json()
        assert body["detail"]["error"]["code"] == "AUTH_DEMO_FORBIDDEN"

    def test_credit_officer_forbidden_401(self, demo_client):
        # PM spec · 审贷员 invoke "demo" → 401
        cookie = _login(demo_client, "u_lihua", "lihua")
        resp = demo_client.post("/api/test/demo_only", cookies={COOKIE_NAME: cookie})
        assert resp.status_code == 401

    def test_no_cookie_401(self, demo_client):
        resp = demo_client.post("/api/test/demo_only")
        assert resp.status_code == 401
        assert resp.json()["detail"]["error"]["code"] == "AUTH_MISSING"

    def test_require_action_demo_rm_returns_401(self, demo_client):
        # require_action("channel", "demo") · RM 走 can_action 拒 · 返 401
        cookie = _login(demo_client, "u_wangzhe", "wangzhe")
        resp = demo_client.post("/api/test/require_action_demo", cookies={COOKIE_NAME: cookie})
        assert resp.status_code == 401  # demo action 拒 = 401 (per dependencies.py)
        body = resp.json()
        assert body["detail"]["error"]["code"] == "AUTH_DEMO_FORBIDDEN"

    def test_require_action_demo_admin_allowed(self, demo_client, monkeypatch):
        # Phase B.1 fix #2 · can_action("demo") 现需 env DEMO_MODE_VISIBLE=1
        monkeypatch.setenv("DEMO_MODE_VISIBLE", "1")
        cookie = _login(demo_client, "u_liuye", "liuye")
        resp = demo_client.post("/api/test/require_action_demo", cookies={COOKIE_NAME: cookie})
        assert resp.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
