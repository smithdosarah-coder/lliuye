# -*- coding: utf-8 -*-
"""Unit tests for compliance canonical input mapper (W1 Phase C).

Per codex R3 R3.2 default design (2026-05-21):

- canonical signature detection (含 ``client_metadata`` layer → canonical 路径)
- backward compat (raw payload 不含 ``client_metadata`` → passthrough 不变)
- CanonicalInput → CompliancePolicyScanRequest shape mapping
- business_docs 派生: material_facts 长叙述聚合 → list[dict]
- ComplianceAdapter import + boundary 验证
"""
from __future__ import annotations

import pytest

from liuye_service.adapters.compliance import (
    ComplianceAdapter,
    COMPLIANCE_AGENT_ID,
    COMPLIANCE_ENDPOINT,
    _canonical_to_compliance_input,
)


class TestComplianceAdapterClass:
    """ComplianceAdapter 类层 · boundary + agent_id."""

    def test_agent_id(self):
        assert ComplianceAdapter.agent_id == "compliance"
        assert COMPLIANCE_AGENT_ID == "compliance"

    def test_boundary_managed(self):
        # Phase C 保留 managed_readonly
        assert ComplianceAdapter.boundary == "managed_readonly"

    def test_endpoint(self):
        # Phase C · /api/compliance/policy_scan live endpoint
        assert COMPLIANCE_ENDPOINT == "/api/compliance/policy_scan"

    def test_can_instantiate(self):
        adapter = ComplianceAdapter()
        assert adapter.agent_id == "compliance"
        assert adapter.boundary == "managed_readonly"

    def test_no_longer_raises_on_init(self):
        adapter = ComplianceAdapter(backend_url="http://test-only:9999")
        assert adapter.backend_url == "http://test-only:9999"


class TestCanonicalToComplianceInput:
    """`_canonical_to_compliance_input` mapper · backward compat + canonical."""

    def test_backward_compat_raw_payload(self):
        """Raw payload (无 ``client_metadata`` key) → passthrough 不变."""
        raw = {
            "policy_doc": "央行 2025-001 号文 · 个人贷款管理办法",
            "business_docs": [{"name": "客户A", "loan": "200 万"}],
            "force_mock": False,
        }
        result = _canonical_to_compliance_input(raw)
        assert result == raw

    def test_backward_compat_with_policy_meta(self):
        raw = {
            "policy_doc": "政策原文",
            "business_docs": [],
            "policy_meta": {"title": "央行 X 号文", "source_url": "http://x.cn"},
            "force_mock": True,
        }
        result = _canonical_to_compliance_input(raw)
        assert result["policy_meta"]["title"] == "央行 X 号文"
        assert result["force_mock"] is True

    def test_canonical_derives_business_docs_from_material_facts(self):
        """Canonical material_facts 长叙述 → business_docs[0] 派生."""
        canonical = {
            "client_metadata": {
                "CLIENT_FULL_NAME": "鼎盛商贸",
                "CLIENT_USCC": "91310000XXXXXXXXXX",
            },
            "material_facts": {
                "BUSINESS_HISTORY_DESC": "8 年深耕电子商务",
                "INDUSTRY_ANALYSIS": "批零行业景气稳定",
                "REPAYMENT_ABILITY_ASSESSMENT": "现金流充足",
            },
            "policy_doc": "央行 2025-001 号文",
        }
        result = _canonical_to_compliance_input(canonical)
        assert result["policy_doc"] == "央行 2025-001 号文"
        assert len(result["business_docs"]) == 1
        doc = result["business_docs"][0]
        assert doc["subject_name"] == "鼎盛商贸"
        assert doc["uscc"] == "91310000XXXXXXXXXX"
        assert "8 年深耕电子商务" in doc["content"]
        assert "批零行业景气稳定" in doc["content"]
        assert "现金流充足" in doc["content"]
        assert doc["source"] == "canonical.material_facts"

    def test_canonical_passthrough_business_docs_wins(self):
        """passthrough.business_docs 显式覆盖 material_facts 派生."""
        canonical = {
            "client_metadata": {
                "CLIENT_FULL_NAME": "鼎盛",
            },
            "material_facts": {
                "BUSINESS_HISTORY_DESC": "应被覆盖",
            },
            "business_docs": [
                {"name": "Explicit doc", "content": "wins"},
            ],
            "policy_doc": "P",
        }
        result = _canonical_to_compliance_input(canonical)
        assert result["business_docs"] == [{"name": "Explicit doc", "content": "wins"}]

    def test_canonical_empty_material_facts_returns_empty_docs(self):
        """material_facts 完全空 → business_docs=[] · 不爆 · backend 走 400 VALIDATION_FAILED."""
        canonical = {
            "client_metadata": {"CLIENT_FULL_NAME": "客户"},
            "policy_doc": "政策文",
        }
        result = _canonical_to_compliance_input(canonical)
        assert result["business_docs"] == []
        assert result["policy_doc"] == "政策文"

    def test_canonical_no_policy_doc_empty_string(self):
        """passthrough 无 policy_doc → 空字符串 (backend 会 400 验证 fail · 不静默兜底)."""
        canonical = {
            "client_metadata": {"CLIENT_FULL_NAME": "客户"},
        }
        result = _canonical_to_compliance_input(canonical)
        assert result["policy_doc"] == ""

    def test_canonical_invalid_fallback_raw(self):
        """canonical pydantic validation fail · fallback raw."""
        canonical = {
            "client_metadata": {
                # CLIENT_FULL_NAME 缺 · pydantic raise
                "CLIENT_USCC": "91XXX",
            },
            "policy_doc": "fallback-policy",
        }
        result = _canonical_to_compliance_input(canonical)
        # raw 透传 · policy_doc 保留
        assert result["policy_doc"] == "fallback-policy"

    def test_non_dict_returns_empty(self):
        assert _canonical_to_compliance_input(None) == {}  # type: ignore[arg-type]
        assert _canonical_to_compliance_input("not a dict") == {}  # type: ignore[arg-type]
