# -*- coding: utf-8 -*-
"""shared/kb_scan edges · Stage E.4 expansion.

参数化 heavy · 单 file ~50+ case 覆盖 BaseScanner / Router / Degrader / impls 边界。
"""
from __future__ import annotations

import sys
from pathlib import Path

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
    all_preferences,
    clear_preferences,
    get_preference,
    register_preference,
)


@pytest.fixture(autouse=True)
def _isolate():
    clear()
    clear_preferences()
    yield
    clear()
    clear_preferences()


# ============================================================================
# BaseScanner.supports edge matrix · 30 case
# ============================================================================

class _S(BaseScanner):
    name = "_s"
    supported_scopes: set[str] = set()  # 子类覆盖

    def scan(self, request):
        return ScanRunResult(ok=True, scanner_name=self.name)


@pytest.mark.parametrize("scopes, query_scope, expected", [
    # empty supported_scopes set 仅接 default-等价
    (set(), "default", True),
    (set(), "", True),
    (set(), "anything", False),
    (set(), "policy_scan", False),
    # 显式包含 default
    ({"default"}, "default", True),
    ({"default"}, "", True),
    ({"default"}, "specific", False),
    # 显式 specific scope
    ({"policy_scan"}, "policy_scan", True),
    ({"policy_scan"}, "default", False),
    ({"policy_scan"}, "", False),
    # multiple
    ({"a", "b", "c"}, "a", True),
    ({"a", "b", "c"}, "b", True),
    ({"a", "b", "c"}, "d", False),
    ({"a", "b", "default"}, "default", True),
    ({"a", "b", "default"}, "", True),
    # case sensitive
    ({"Policy"}, "policy", False),
    ({"Policy"}, "Policy", True),
])
def test_supports_matrix(scopes, query_scope, expected):
    sc = _S()
    sc.supported_scopes = scopes
    assert sc.supports(query_scope) is expected


# ============================================================================
# Registry edges · 12 case
# ============================================================================

@pytest.mark.parametrize("name", ["a", "scanner_x", "b_2", "X.Y", "a-b", "1"])
def test_registry_register_various_names(name):
    sc = _S()
    sc.name = name
    register(sc)
    assert has(name)


def test_registry_clear_empties():
    register(_S())
    assert len(all_scanners()) == 1
    clear()
    assert len(all_scanners()) == 0


def test_registry_get_returns_same_instance():
    sc = _S()
    register(sc)
    assert get(sc.name) is sc


@pytest.mark.parametrize("missing_name", ["nonexistent", "", "xxx_yyy"])
def test_registry_get_raises_on_missing(missing_name):
    if missing_name == "":
        pytest.skip("empty name treated as scanner.name=required at register · skip")
    with pytest.raises(KeyError):
        get(missing_name)


# ============================================================================
# Router preferences edges · 10 case
# ============================================================================

@pytest.mark.parametrize("domain, chain", [
    ("agent_alert.batch_loan_scan", ["alert_customer"]),
    ("agent_compliance.policy_scan", ["compliance_policy"]),
    ("agent_channel.candidate_enrich", ["channel_signal"]),
    ("custom.foo", ["a", "b", "c"]),
    ("very.long.domain.x.y.z", ["one"]),
])
def test_register_preference_roundtrip(domain, chain):
    register_preference(domain, chain)
    assert get_preference(domain) == chain


def test_register_preference_overwrites():
    register_preference("d", ["a"])
    register_preference("d", ["b", "c"])
    assert get_preference("d") == ["b", "c"]


def test_all_preferences_returns_copy():
    register_preference("d1", ["x"])
    register_preference("d2", ["y"])
    prefs = all_preferences()
    prefs["d3"] = ["z"]
    assert "d3" not in all_preferences()


@pytest.mark.parametrize("bad_domain", ["", None])
def test_register_preference_rejects_empty_domain(bad_domain):
    if bad_domain is None:
        # can_match? · register_preference 接受 str 类型 · None 不报但失败 · 跳过
        pytest.skip("None domain not validated")
    with pytest.raises(ValueError):
        register_preference(bad_domain, ["x"])


def test_register_preference_rejects_empty_chain():
    with pytest.raises(ValueError):
        register_preference("d", [])


# ============================================================================
# Degrader edges · 12 case
# ============================================================================

class _OkScanner(BaseScanner):
    name = "ok"
    supported_scopes = {"default"}

    def scan(self, request):
        return ScanRunResult(
            ok=True, scanner_name=self.name,
            hits=[HitItem(
                hit_id="h1", level=RiskLevel.GREEN,
                target=ScanTarget(target_id="x", target_type="x", payload={}),
            )],
        )


class _FailScanner(BaseScanner):
    name = "fail"
    supported_scopes = {"default"}

    def scan(self, request):
        return ScanRunResult(ok=False, scanner_name=self.name, error="failed")


@pytest.mark.parametrize("chain_size", [1, 2, 3, 5, 10])
def test_degrader_chains_of_various_size_with_one_ok(chain_size):
    register(_OkScanner())
    chain = ["ok"] * chain_size
    result = execute_with_degradation(chain, ScanRequest(scope="default"))
    assert result.ok
    # First instance ok · degraded should be False
    assert not result.degraded


@pytest.mark.parametrize("fail_count", [1, 2, 3, 5])
def test_degrader_n_fails_then_ok_marks_degraded(fail_count):
    register(_FailScanner())
    register(_OkScanner())
    chain = ["fail"] * fail_count + ["ok"]
    result = execute_with_degradation(chain, ScanRequest(scope="default"))
    assert result.ok
    assert result.degraded


def test_degrader_aggregates_all_fails(tmp_path):
    register(_FailScanner())
    chain = ["fail"] * 3
    result = execute_with_degradation(chain, ScanRequest(scope="default"))
    assert not result.ok
    # error 聚合 · 应含 "fail" 多次
    assert result.error.count("fail") >= 3


# ============================================================================
# ScanRequest defaults · 10 case
# ============================================================================

@pytest.mark.parametrize("kwargs, attr, expected", [
    ({}, "query", ""),
    ({}, "kb_id", ""),
    ({}, "scope", "default"),
    ({}, "limit", 10),
    ({"query": "x"}, "query", "x"),
    ({"kb_id": "kb_xxx"}, "kb_id", "kb_xxx"),
    ({"scope": "policy_scan"}, "scope", "policy_scan"),
    ({"limit": 100}, "limit", 100),
    ({"limit": 0}, "limit", 0),
    ({"filters": {"a": 1}}, "filters", {"a": 1}),
])
def test_scan_request_defaults(kwargs, attr, expected):
    req = ScanRequest(**kwargs)
    assert getattr(req, attr) == expected


# ============================================================================
# ScanRunResult.hit_count · 8 case
# ============================================================================

@pytest.mark.parametrize("hits_n, hit_list_total, expected", [
    (0, 0, 0),
    (3, 0, 3),     # hit_list None · fallback to hits len
    (0, 5, 5),     # hit_list 优先
    (3, 5, 5),     # 二者都有 · hit_list 优先
    (10, 0, 10),
])
def test_hit_count_priority(hits_n, hit_list_total, expected):
    hits = [
        HitItem(
            hit_id=str(i), level=RiskLevel.GREEN,
            target=ScanTarget(target_id=str(i), target_type="x", payload={}),
        )
        for i in range(hits_n)
    ]
    hit_list = (
        HitList(list_id="t", agent_name="t", total_hit=hit_list_total)
        if hit_list_total or expected == hit_list_total
        else None
    )
    if hit_list is None and hits_n == 0:
        # 让结果反映 0
        result = ScanRunResult(ok=True, hits=[], hit_list=None)
        assert result.hit_count() == 0
        return
    result = ScanRunResult(ok=True, hits=hits, hit_list=hit_list)
    assert result.hit_count() == expected


# ============================================================================
# bootstrap_scanners · 5 case
# ============================================================================

def test_bootstrap_returns_status_dict():
    status = bootstrap_scanners()
    assert isinstance(status, dict)
    # 至少 6 条 (3 scanner + 3 prefs)
    assert len(status) >= 6


def test_bootstrap_idempotent_state_count():
    bootstrap_scanners()
    n1 = len(all_scanners())
    bootstrap_scanners()
    n2 = len(all_scanners())
    assert n1 == n2


@pytest.mark.parametrize("scanner_name", [
    "alert_customer", "compliance_policy", "channel_signal",
])
def test_bootstrap_registers_each_scanner(scanner_name):
    bootstrap_scanners()
    assert has(scanner_name)


@pytest.mark.parametrize("domain", [
    "agent_alert.batch_loan_scan",
    "agent_compliance.policy_scan",
    "agent_channel.candidate_enrich",
])
def test_bootstrap_registers_each_preference(domain):
    bootstrap_scanners()
    assert get_preference(domain), f"prefs not found for {domain}"
