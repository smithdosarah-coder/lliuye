# -*- coding: utf-8 -*-
"""Tests for POST /api/riskctrl/backtest (v4.0 JSON · 真跑 loans.csv).

Coverage:
  - 真跑 data/mock/agent2-samples/loans.csv 子集 (head 200) · 验 metrics 完整
  - 含 KS / approval_rate / bad_rate / rule_stats per-rule
  - csv_path 不存在 → 400
  - ruleset 空 → 400
  - 标签列不存在场景 (label_column 显式给) → bad_rate / ks 为 None 或软降级

不依赖 LLM (真 backtest 是确定性计算).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOANS_CSV = PROJECT_ROOT / "data" / "mock" / "agent2-samples" / "loans.csv"


@pytest.fixture(scope="module")
def client():
    from agent_riskctrl.api import app
    return TestClient(app)


_DEMO_RULESET = {
    "rules": [
        {
            "rule_id": "R001",
            "name": "高负债拒",
            "description": "负债率 > 0.7 拒绝",
            "conditions": [{"field": "debt_ratio", "operator": ">", "value": 0.7}],
            "action": "reject",
            "priority": 1,
        },
        {
            "rule_id": "R002",
            "name": "查询过频转人工",
            "description": "近 3 月查询 > 5 次转人工",
            "conditions": [{"field": "query_times_3m", "operator": ">", "value": 5}],
            "action": "manual_review",
            "priority": 5,
        },
        {
            "rule_id": "R003",
            "name": "新成立企业转人工",
            "description": "成立年限 < 2 年转人工",
            "conditions": [{"field": "company_age_years", "operator": "<", "value": 2}],
            "action": "manual_review",
            "priority": 10,
        },
    ],
    "description": "test 3-rule demo",
}


# ----------------------------------------------------------------------------
# 真跑 loans.csv (Q-040 fix MAX_ROWS=50000 · 7500 行 · 全跑也 OK · 这里用 head 200 子集快)
# ----------------------------------------------------------------------------


def test_backtest_real_loans_csv(client, tmp_path):
    """真跑 head 200 行 loans.csv · 验 metrics 完整."""
    if not LOANS_CSV.exists():
        pytest.skip(f"loans.csv 不在 {LOANS_CSV} (data-foundation worker 产出 · 缺则跳)")

    # 取 head 200 行写到 tmp · 加快测试
    import pandas as pd
    df_full = pd.read_csv(LOANS_CSV, encoding="utf-8")
    sample = df_full.head(200)
    sub_csv = tmp_path / "loans_head200.csv"
    sample.to_csv(sub_csv, index=False, encoding="utf-8")

    resp = client.post(
        "/api/riskctrl/backtest",
        json={
            "ruleset": _DEMO_RULESET,
            "csv_path": str(sub_csv),
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_records"] == 200
    assert data["approved"] + data["rejected"] + data["manual_review"] <= 200
    assert 0.0 <= data["approval_rate"] <= 1.0
    assert data["label_column_used"] == "days_past_due"
    assert data["bad_rate"] is not None
    assert 0.0 <= data["bad_rate"] <= 1.0
    assert data["ks"] is not None
    assert 0.0 <= data["ks"] <= 1.0
    # rule_stats 每条规则有 hit_count / FP / TN / FP_rate (per_rule_fpr_spread A-019)
    assert len(data["rule_stats"]) == 3
    for stat in data["rule_stats"]:
        assert "rule_id" in stat
        assert "hit_count" in stat
        assert "FP" in stat
        assert "TN" in stat
        assert "FP_rate" in stat
        # reject 规则才有 FP/TN 数据 (A-019 N/A 语义)
        if stat["action"] == "reject":
            assert stat["FP"] >= 0
            assert stat["TN"] >= 0


# ----------------------------------------------------------------------------
# 错误路径
# ----------------------------------------------------------------------------


def test_backtest_csv_not_exist(client):
    resp = client.post(
        "/api/riskctrl/backtest",
        json={
            "ruleset": _DEMO_RULESET,
            "csv_path": "data/mock/this_does_not_exist.csv",
        },
    )
    assert resp.status_code == 400
    assert "不存在" in resp.json()["detail"]


def test_backtest_empty_ruleset(client, tmp_path):
    csv = tmp_path / "tiny.csv"
    csv.write_text("debt_ratio\n0.5\n0.9\n", encoding="utf-8")
    resp = client.post(
        "/api/riskctrl/backtest",
        json={
            "ruleset": {"rules": []},
            "csv_path": str(csv),
        },
    )
    assert resp.status_code == 400
    assert "rules" in resp.json()["detail"]


def test_backtest_ruleset_invalid(client, tmp_path):
    csv = tmp_path / "tiny.csv"
    csv.write_text("debt_ratio\n0.5\n", encoding="utf-8")
    resp = client.post(
        "/api/riskctrl/backtest",
        json={
            "ruleset": {"rules": "not a list"},
            "csv_path": str(csv),
        },
    )
    assert resp.status_code == 400


def test_backtest_no_label_column_soft_degrade(client, tmp_path):
    """csv 无 label/days_past_due 列 → bad_rate/ks 为 None · 不抛."""
    import pandas as pd
    csv = tmp_path / "no_label.csv"
    pd.DataFrame([
        {"debt_ratio": 0.5, "company_age_years": 3.0, "query_times_3m": 1},
        {"debt_ratio": 0.9, "company_age_years": 0.5, "query_times_3m": 12},
        {"debt_ratio": 0.3, "company_age_years": 5.0, "query_times_3m": 2},
    ]).to_csv(csv, index=False, encoding="utf-8")

    resp = client.post(
        "/api/riskctrl/backtest",
        json={
            "ruleset": _DEMO_RULESET,
            "csv_path": str(csv),
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_records"] == 3
    assert data["bad_rate"] is None
    assert data["ks"] is None
    assert data["label_column_used"] is None
