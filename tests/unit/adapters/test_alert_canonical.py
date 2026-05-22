# -*- coding: utf-8 -*-
"""Unit tests for alert canonical input mapper (W1 Phase C).

Per codex R3 R3.2 default design (2026-05-21):

- canonical signature detection (含 ``client_metadata`` layer → canonical 路径)
- backward compat (raw payload 不含 ``client_metadata`` → passthrough 不变)
- CanonicalInput → AlertScanRequest shape mapping
- scenario_key 推断: passthrough.scenario_key > client_metadata.company_name > ""
- AlertAdapter import + boundary 验证
"""
from __future__ import annotations

import pytest

from liuye_service.adapters.alert import (
    AlertAdapter,
    ALERT_AGENT_ID,
    ALERT_ENDPOINT,
    _canonical_to_alert_input,
)


class TestAlertAdapterClass:
    """AlertAdapter 类层 · boundary + agent_id + 不再 raise NotImplementedError."""

    def test_agent_id(self):
        assert AlertAdapter.agent_id == "alert"
        assert ALERT_AGENT_ID == "alert"

    def test_boundary_managed(self):
        # Phase C 保留 managed_readonly · 仍是 Managed agent 语义
        assert AlertAdapter.boundary == "managed_readonly"

    def test_endpoint(self):
        # Phase C · stub 501 → /api/alert/scan live endpoint
        assert ALERT_ENDPOINT == "/api/alert/scan"

    def test_can_instantiate(self):
        # Phase 1 stub 接受任意 kwargs 但不实际工作 · Phase C 可正常 instantiate
        adapter = AlertAdapter()
        assert adapter.agent_id == "alert"
        assert adapter.boundary == "managed_readonly"

    def test_no_longer_raises_on_init(self):
        # Phase 1 stub init() OK · 但 dispatch raise · Phase C dispatch live HTTP
        # 此处仅验 init 不 raise · 真正 HTTP 测试由 integration test 覆盖
        adapter = AlertAdapter(backend_url="http://test-only:9999")
        assert adapter.backend_url == "http://test-only:9999"


class TestCanonicalToAlertInput:
    """`_canonical_to_alert_input` mapper · backward compat + canonical 两条路径."""

    def test_backward_compat_raw_payload(self):
        """Raw payload (无 ``client_metadata`` key) → passthrough 不变."""
        raw = {
            "scenario_key": "micro_credit_100",
            "uploaded_files": ["/tmp/clients.csv"],
            "force_mock": False,
        }
        result = _canonical_to_alert_input(raw)
        assert result == raw

    def test_backward_compat_preserves_legacy_fields(self):
        """Raw payload 含 legacy 字段 (provider/api_key/parent_tool_call_id) → 透传."""
        raw = {
            "scenario_key": "alert-pool",
            "provider": "deepseek",
            "api_key": "sk-xxx",
            "parent_tool_call_id": "tc_credit_handoff",
        }
        result = _canonical_to_alert_input(raw)
        assert result["scenario_key"] == "alert-pool"
        assert result["provider"] == "deepseek"
        assert result["parent_tool_call_id"] == "tc_credit_handoff"

    def test_canonical_scenario_key_from_company_name(self):
        """Canonical → scenario_key 从 company_name 派生 (单客 drill 入口)."""
        canonical = {
            "client_metadata": {
                "CLIENT_FULL_NAME": "鼎盛商贸有限公司",
                "CLIENT_USCC": "91310000XXXXXXXXXX",
            },
        }
        result = _canonical_to_alert_input(canonical)
        assert result["scenario_key"] == "鼎盛商贸有限公司"
        assert result["force_mock"] is False

    def test_canonical_passthrough_scenario_key_wins(self):
        """passthrough.scenario_key 显式覆盖 company_name."""
        canonical = {
            "client_metadata": {
                "CLIENT_FULL_NAME": "鼎盛",
            },
            "scenario_key": "alert-pool",
        }
        result = _canonical_to_alert_input(canonical)
        # passthrough wins · 不退到 company_name
        assert result["scenario_key"] == "alert-pool"

    def test_canonical_force_mock_passthrough(self):
        """passthrough.force_mock=True → mock 路径 (Tavily 缺 key 显式 mock_fallback 走此)."""
        canonical = {
            "client_metadata": {"CLIENT_FULL_NAME": "测试客户"},
            "force_mock": True,
        }
        result = _canonical_to_alert_input(canonical)
        assert result["force_mock"] is True

    def test_canonical_invalid_fallback_raw(self):
        """canonical 含 ``client_metadata`` 但 pydantic 验证 fail · fallback raw."""
        canonical = {
            "client_metadata": {
                # CLIENT_FULL_NAME 缺 · pydantic 必 raise · mapper fallback raw
                "CLIENT_USCC": "91XXX",
            },
            "scenario_key": "fallback-scen",
        }
        result = _canonical_to_alert_input(canonical)
        # fallback path: 原 raw 透传 · scenario_key 保留
        assert result["scenario_key"] == "fallback-scen"

    def test_canonical_uploaded_files_passthrough(self):
        """passthrough.uploaded_files 透传 (alert 名录上传场景)."""
        canonical = {
            "client_metadata": {"CLIENT_FULL_NAME": "客户"},
            "uploaded_files": ["/tmp/list.csv", "/tmp/list2.xlsx"],
        }
        result = _canonical_to_alert_input(canonical)
        assert result["uploaded_files"] == ["/tmp/list.csv", "/tmp/list2.xlsx"]

    def test_non_dict_returns_empty(self):
        assert _canonical_to_alert_input(None) == {}  # type: ignore[arg-type]
        assert _canonical_to_alert_input("not a dict") == {}  # type: ignore[arg-type]
