# -*- coding: utf-8 -*-
"""shared/kb_scan/ Router + Degrader + Registry + impls 单测.

D.5 共享底座 · 锁定:
  - BaseScanner Protocol (name/agent_key/supported_scopes/scan)
  - registry register/get/has/clear
  - degrader: 第 1 个 ok 直返 / 后续 ok 标 degraded / 全失败聚合 error /
    不接 scope 跳过 / health 失败跳过 / 异常不中断链
  - ScannerRouter: domain → 偏好链 → degrader
  - bootstrap_scanners: 注册 3 impls + 3 agent prefs
  - per-Agent adapter: alert_customer / compliance_policy / channel_signal

Author: Worker A1 (Stage D 第 1 批) · 2026-04-28
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.kb_scan import bootstrap_scanners  # noqa: E402
from shared.kb_scan.base import (  # noqa: E402
    BaseScanner,
    ScanRequest,
    ScanRunResult,
)
from shared.kb_scan.degrader import execute_with_degradation  # noqa: E402
from shared.kb_scan.models import HitItem, HitList, RiskLevel, ScanTarget  # noqa: E402
from shared.kb_scan.registry import (  # noqa: E402
    all_scanners,
    clear,
    get,
    has,
    register,
)
from shared.kb_scan.router import (  # noqa: E402
    ScannerRouter,
    clear_preferences,
    register_preference,
)


# ---------------------------------------------------------------------------
# Test fixtures · 假 scanner
# ---------------------------------------------------------------------------

class _FakeOkScanner(BaseScanner):
    name = "fake_ok"
    agent_key = "test"
    supported_scopes = {"default", "test_scope"}

    def scan(self, request: ScanRequest) -> ScanRunResult:
        return ScanRunResult(
            ok=True,
            scanner_name=self.name,
            hits=[
                HitItem(
                    hit_id="t1",
                    rank=1,
                    level=RiskLevel.GREEN,
                    score=0.5,
                    target=ScanTarget(
                        target_id="t1", target_type="company", payload={},
                    ),
                ),
            ],
            summary="fake ok",
        )


class _FakeFailScanner(BaseScanner):
    name = "fake_fail"
    agent_key = "test"
    supported_scopes = {"default"}

    def scan(self, request: ScanRequest) -> ScanRunResult:
        return ScanRunResult(
            ok=False, scanner_name=self.name, error="simulated fail",
        )


class _FakeRaiseScanner(BaseScanner):
    name = "fake_raise"
    agent_key = "test"
    supported_scopes = {"default"}

    def scan(self, request: ScanRequest) -> ScanRunResult:
        raise RuntimeError("scan threw")


class _FakeUnhealthyScanner(BaseScanner):
    name = "fake_unhealthy"
    agent_key = "test"
    supported_scopes = {"default"}

    def health(self) -> bool:
        return False

    def scan(self, request: ScanRequest) -> ScanRunResult:
        return ScanRunResult(ok=True, scanner_name=self.name)


@pytest.fixture(autouse=True)
def _isolate_registry():
    """每个 test 用一份独立 registry / preferences."""
    clear()
    clear_preferences()
    yield
    clear()
    clear_preferences()


# ---------------------------------------------------------------------------
# BaseScanner Protocol
# ---------------------------------------------------------------------------

def test_base_scanner_supports_default_when_scope_set_includes_default():
    s = _FakeOkScanner()
    assert s.supports("default")
    assert s.supports("test_scope")
    assert not s.supports("nonexistent_scope")


def test_base_scanner_supports_default_when_supported_scopes_empty():
    class _NoScopeScanner(BaseScanner):
        name = "no_scope"

        def scan(self, request):
            return ScanRunResult(ok=True, scanner_name=self.name)

    s = _NoScopeScanner()
    assert s.supports("default")
    assert s.supports("")
    assert not s.supports("specific_scope")


def test_scan_run_result_hit_count_uses_hit_list_when_present():
    hl = HitList(list_id="test", agent_name="test", total_hit=7)
    res = ScanRunResult(ok=True, hit_list=hl)
    assert res.hit_count() == 7

    res_no_list = ScanRunResult(
        ok=True,
        hits=[
            HitItem(
                hit_id=str(i), level=RiskLevel.GREEN,
                target=ScanTarget(target_id=str(i), target_type="company", payload={}),
            ) for i in range(3)
        ],
    )
    assert res_no_list.hit_count() == 3


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def test_registry_register_get_has():
    s = _FakeOkScanner()
    register(s)
    assert has("fake_ok")
    assert get("fake_ok") is s
    with pytest.raises(KeyError):
        get("nonexistent")


def test_registry_register_requires_name():
    class _NamelessScanner(BaseScanner):
        name = ""

        def scan(self, request):
            return ScanRunResult(ok=True)

    with pytest.raises(ValueError):
        register(_NamelessScanner())


def test_registry_all_scanners_returns_copy():
    register(_FakeOkScanner())
    register(_FakeFailScanner())
    lst = all_scanners()
    assert len(lst) == 2
    lst.clear()  # 不应影响内部
    assert len(all_scanners()) == 2


# ---------------------------------------------------------------------------
# Degrader
# ---------------------------------------------------------------------------

def test_degrader_first_ok_returns_no_degraded():
    register(_FakeOkScanner())
    register(_FakeFailScanner())
    result = execute_with_degradation(
        ["fake_ok", "fake_fail"], ScanRequest(scope="default"),
    )
    assert result.ok
    assert result.degraded is False
    assert result.scanner_name == "fake_ok"


def test_degrader_second_ok_marks_degraded():
    register(_FakeFailScanner())
    register(_FakeOkScanner())
    result = execute_with_degradation(
        ["fake_fail", "fake_ok"], ScanRequest(scope="default"),
    )
    assert result.ok
    assert result.degraded is True
    assert result.scanner_name == "fake_ok"


def test_degrader_all_fail_returns_aggregated_error():
    register(_FakeFailScanner())
    register(_FakeRaiseScanner())
    result = execute_with_degradation(
        ["fake_fail", "fake_raise"], ScanRequest(scope="default"),
    )
    assert not result.ok
    assert result.degraded is True
    assert "fake_fail" in result.error
    assert "fake_raise" in result.error
    assert "RuntimeError" in result.error


def test_degrader_skips_unsupported_scope():
    register(_FakeOkScanner())
    result = execute_with_degradation(
        ["fake_ok"], ScanRequest(scope="some_other_scope"),
    )
    assert not result.ok
    assert "unsupported scope" in result.error


def test_degrader_skips_unhealthy_scanner():
    register(_FakeUnhealthyScanner())
    register(_FakeOkScanner())
    result = execute_with_degradation(
        ["fake_unhealthy", "fake_ok"], ScanRequest(scope="default"),
    )
    assert result.ok
    assert result.degraded is True


def test_degrader_skips_unregistered_name():
    register(_FakeOkScanner())
    result = execute_with_degradation(
        ["nonexistent", "fake_ok"], ScanRequest(scope="default"),
    )
    assert result.ok
    assert result.degraded is True


def test_degrader_empty_chain_returns_error():
    result = execute_with_degradation([], ScanRequest(scope="default"))
    assert not result.ok
    assert "empty" in result.error.lower()


# ---------------------------------------------------------------------------
# ScannerRouter
# ---------------------------------------------------------------------------

def test_router_unregistered_domain_returns_error():
    router = ScannerRouter()
    result = router.scan("nonexistent.domain", ScanRequest(scope="default"))
    assert not result.ok
    assert "no preference" in result.error.lower()


def test_router_registered_domain_routes_through_chain():
    register(_FakeOkScanner())
    register_preference("test.domain", ["fake_ok"])
    router = ScannerRouter()
    result = router.scan("test.domain", ScanRequest(scope="default"))
    assert result.ok
    assert result.scanner_name == "fake_ok"


def test_router_chain_with_fallback():
    register(_FakeFailScanner())
    register(_FakeOkScanner())
    register_preference("test.domain", ["fake_fail", "fake_ok"])
    router = ScannerRouter()
    result = router.scan("test.domain", ScanRequest(scope="default"))
    assert result.ok
    assert result.degraded is True


# ---------------------------------------------------------------------------
# bootstrap + impls
# ---------------------------------------------------------------------------

def test_bootstrap_registers_3_impls_and_3_prefs():
    status = bootstrap_scanners()
    # 3 scanner impls 全成功
    assert status.get("scanner.alert_customer") is True
    assert status.get("scanner.compliance_policy") is True
    assert status.get("scanner.channel_signal") is True
    # 3 agent prefs 全成功
    assert status.get("prefs.agent_alert") is True
    assert status.get("prefs.agent_compliance") is True
    assert status.get("prefs.agent_channel") is True
    # 3 scanner 都注册到 registry
    assert has("alert_customer")
    assert has("compliance_policy")
    assert has("channel_signal")


def test_bootstrap_is_idempotent():
    status1 = bootstrap_scanners()
    status2 = bootstrap_scanners()
    assert status1 == status2
    # registry 仍然只有 3 个 (覆盖式 register)
    assert len(all_scanners()) == 3


def test_channel_signal_adapter_enrich_via_router():
    bootstrap_scanners()
    router = ScannerRouter()
    result = router.scan(
        "agent_channel.candidate_enrich",
        ScanRequest(
            scope="candidate_enrich",
            query="浙江 精密零部件",
            filters={
                "item": {
                    "company_name": "测试精密公司",
                    "signals": [
                        {
                            "signal_type": "bidding",
                            "signal_title": "中标 1500 万",
                            "signal_detail": "浙江 精密机械装备",
                        },
                    ],
                    "qcc": {
                        "industry": "精密零部件",
                        "registered_address": "浙江省杭州市",
                    },
                    "matchTags": [],
                    "recommendedProducts": [],
                    "pitch": "您好",
                },
                "tags": [
                    {"category": "行业", "value": "精密零部件"},
                    {"category": "区域", "value": "浙江"},
                ],
            },
        ),
    )
    assert result.ok, result.error
    assert result.scanner_name == "channel_signal"
    assert result.hits, "expected at least 1 hit"
    extras = result.hits[0].extras
    # B.5 sse_extras 全字段进 extras
    assert "radar_8axis" in extras
    assert "match_dimensions" in extras
    assert "product_recommendations" in extras
    assert "pitch_scripts" in extras
    # 8 维 radar 全 0-100 int
    radar = extras["radar_8axis"]
    assert len(radar) == 8
    for axis, score in radar.items():
        assert 0 <= score <= 100, f"{axis}={score} out of range"


def test_channel_signal_adapter_missing_item_returns_error():
    bootstrap_scanners()
    router = ScannerRouter()
    result = router.scan(
        "agent_channel.candidate_enrich",
        ScanRequest(scope="candidate_enrich", filters={}),
    )
    assert not result.ok
    assert "item" in result.error.lower()


def test_compliance_policy_adapter_health_when_module_present():
    bootstrap_scanners()
    sc = get("compliance_policy")
    assert sc.health() is True
    assert sc.supports("policy_scan")
    assert sc.supports("default")
    assert not sc.supports("batch_loan_customers")


def test_compliance_policy_adapter_returns_hit_list_when_scan_returns_items():
    """patch ``scan_latest_policies`` 返 fake items · 验 adapter HitList shape."""
    bootstrap_scanners()
    fake_items = [
        {
            "raw_item": {"title": "金融监管新规", "content": "合规要点 · 截至 2026"},
            "source_url": "https://gov.cn/policy/x",
            "fetched_at": "2026-04-28",
            "source_name": "gov_cn",
            "policy_doc": None,
        },
        {
            "raw_item": {"title": "消保政策", "content": "信贷消保细则"},
            "source_url": "https://pbc.gov.cn/p/y",
            "fetched_at": "2026-04-28",
            "source_name": "pbc_gov",
            "policy_doc": None,
        },
    ]
    with patch(
        "agent_compliance.policy_scanner.scan_latest_policies",
        return_value=fake_items,
    ):
        router = ScannerRouter()
        result = router.scan(
            "agent_compliance.policy_scan",
            ScanRequest(scope="policy_scan", query="金融监管", limit=10),
        )
    assert result.ok, result.error
    assert result.scanner_name == "compliance_policy"
    assert result.hit_list is not None
    assert result.hit_list.total_hit == 2
    assert result.hit_list.agent_name == "compliance"
    # 每条 hit 含 source_url + source_name
    for hit in result.hit_list.hits:
        assert hit.target.payload.get("source_url") in (
            "https://gov.cn/policy/x", "https://pbc.gov.cn/p/y",
        )


def test_alert_customer_adapter_health_returns_bool():
    bootstrap_scanners()
    sc = get("alert_customer")
    # health 实际依赖 KB / SearchProvider 装载 · 不抛异常即可
    h = sc.health()
    assert isinstance(h, bool)
    assert sc.supports("batch_loan_customers")
    assert sc.supports("default")
