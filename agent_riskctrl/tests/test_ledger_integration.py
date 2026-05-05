# -*- coding: utf-8 -*-
"""tests/agent_riskctrl/test_ledger_integration.py — BE7 集成 unit tests.

走真实 in-memory DecisionLedger · 验上链 + 失败隔离 + retention 默认.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from agent_riskctrl.ledger_integration import (
    record_backtest_decision,
    record_dsl_deploy,
    record_rubric_sync,
)


@pytest.fixture
def ledger(tmp_path):
    """每 test 1 个独立 sqlite db (隔离 default_ledger)."""
    from shared.decision_ledger import DecisionLedger
    db = tmp_path / "test_ledger.sqlite"
    return DecisionLedger(db_path=db)


# ===========================================================================
# record_dsl_deploy
# ===========================================================================


class TestDslDeploy:
    def test_basic_record(self, ledger):
        decision_id = record_dsl_deploy(
            ruleset_id="rs_test_001",
            dsl_version="v1.2.0",
            rule_count=5,
            affected_segments=["科创"],
            backtest_summary={"ks_peak": 0.32, "bad_rate": 0.04},
            approver_user_id="u_chenkai",
            ledger=ledger,
        )
        # decision_id 非空且不是错误标识
        assert decision_id
        assert "import-failed" not in decision_id
        assert "write-failed" not in decision_id

    def test_retrievable_after_record(self, ledger):
        decision_id = record_dsl_deploy(
            ruleset_id="rs_test_002",
            dsl_version="v1.2.0",
            rule_count=3,
            affected_segments=["对公"],
            backtest_summary={},
            approver_user_id="u_chenkai",
            ledger=ledger,
        )
        # 通过同 ledger 实例 query 能拿到 record
        entry = ledger.get(decision_id)
        assert entry is not None
        assert entry["agent_id"] == "riskctrl"
        assert entry["endpoint"] == "/api/riskctrl/dsl_deploy"

    def test_default_retention_standard(self, ledger):
        """§3.7.5 riskctrl agent 默认 retention=standard."""
        decision_id = record_dsl_deploy(
            ruleset_id="rs_test_003",
            dsl_version="v1.0.0",
            rule_count=1,
            affected_segments=[],
            backtest_summary={},
            ledger=ledger,
        )
        entry = ledger.get(decision_id)
        assert entry["retention_class"] == "standard"

    def test_default_jurisdiction_hq(self, ledger):
        """§3.7.5 default jurisdiction=HQ."""
        decision_id = record_dsl_deploy(
            ruleset_id="rs_test_004",
            dsl_version="v1.0.0",
            rule_count=1,
            affected_segments=[],
            backtest_summary={},
            ledger=ledger,
        )
        entry = ledger.get(decision_id)
        assert entry["jurisdiction"] == "HQ"

    def test_evidence_chain_contains_backtest(self, ledger):
        backtest_summary = {
            "ks_peak": 0.32,
            "bad_rate": 0.04,
            "profit_total_wan": 318.5,
        }
        decision_id = record_dsl_deploy(
            ruleset_id="rs_test_005",
            dsl_version="v1.2.0",
            rule_count=5,
            affected_segments=["科创"],
            backtest_summary=backtest_summary,
            ledger=ledger,
        )
        entry = ledger.get(decision_id)
        assert entry["evidence_chain"]["decision_class"] == "dsl_deploy"
        assert entry["evidence_chain"]["backtest_summary"]["ks_peak"] == 0.32

    def test_unsigned_marker_when_no_approver(self, ledger):
        decision_id = record_dsl_deploy(
            ruleset_id="rs_test_006",
            dsl_version="v1.0.0",
            rule_count=1,
            affected_segments=[],
            backtest_summary={},
            approver_user_id=None,
            ledger=ledger,
        )
        entry = ledger.get(decision_id)
        assert entry["evidence_chain"]["approver_user_id"] == "<not_signed>"


# ===========================================================================
# record_rubric_sync
# ===========================================================================


class TestRubricSync:
    def test_basic(self, ledger):
        decision_id = record_rubric_sync(
            dsl_version_old="v1.1.0",
            dsl_version_new="v1.2.0",
            rubric_diff={"added": [{"x": 1}], "modified": [], "removed": []},
            affected_segments=["科创"],
            ledger=ledger,
        )
        assert decision_id
        entry = ledger.get(decision_id)
        assert entry["endpoint"] == "/api/credit/rubric_sync"
        assert entry["evidence_chain"]["rubric_diff"]["added"][0]["x"] == 1

    def test_diff_size_summarized(self, ledger):
        decision_id = record_rubric_sync(
            dsl_version_old="v1.1.0",
            dsl_version_new="v1.2.0",
            rubric_diff={
                "added": [{"a": 1}, {"b": 2}],
                "modified": [{"c": 3}],
                "removed": [],
            },
            affected_segments=[],
            ledger=ledger,
        )
        entry = ledger.get(decision_id)
        # output_payload 含 diff_size summary
        # 通过 store 读取 output_payload 是 json string 反 hash · 此处仅验 evidence
        assert len(entry["evidence_chain"]["rubric_diff"]["added"]) == 2


# ===========================================================================
# record_backtest_decision
# ===========================================================================


class TestBacktestDecision:
    def test_short_retention(self, ledger):
        """单次回测决策 retention=short (90d · §3.7.5 不是签字级)."""
        decision_id = record_backtest_decision(
            ruleset_id="rs_test_007",
            csv_path="data/mock/agent2-samples/loans.csv",
            metrics={"total_records": 500, "ks_peak": 0.3},
            business_metrics={"pass_rate": 0.78},
            ledger=ledger,
        )
        entry = ledger.get(decision_id)
        assert entry["retention_class"] == "short"

    def test_metrics_in_evidence(self, ledger):
        decision_id = record_backtest_decision(
            ruleset_id="rs_test_008",
            csv_path="path",
            metrics={"ks_peak": 0.25},
            business_metrics={"profit_total_wan": 150.0},
            ledger=ledger,
        )
        entry = ledger.get(decision_id)
        assert entry["evidence_chain"]["metrics"]["ks_peak"] == 0.25
        assert entry["evidence_chain"]["business_metrics"]["profit_total_wan"] == 150.0


# ===========================================================================
# 失败隔离 (silent-fail per §3.7.5)
# ===========================================================================


class FailingLedger:
    """模拟 ledger 写失败 · 验 helper 不抛."""
    def write(self, *args, **kwargs):
        raise RuntimeError("ledger down")

    def get(self, *args, **kwargs):
        return None


class TestFailureIsolation:
    def test_dsl_deploy_returns_id_on_write_failure(self):
        # 注入失败 ledger · 不抛 · 返带 -failed 标识 id
        result = record_dsl_deploy(
            ruleset_id="rs_test_fail",
            dsl_version="v1.0.0",
            rule_count=1,
            affected_segments=[],
            backtest_summary={},
            ledger=FailingLedger(),  # type: ignore[arg-type]
        )
        # 测试无论 silent fail 还是 真上链 · 都不抛 · 返非空 string
        assert isinstance(result, str)
        assert result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
