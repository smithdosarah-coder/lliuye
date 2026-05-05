# -*- coding: utf-8 -*-
"""Tests for POST /api/riskctrl/backtest (SSE form · V2 fix codex critical 3).

V1 (worker-A4 SSE 化前): JSON response · resp.json() · status 400 on errors
V2 (current · post Phase A SSE migration): SSE event-stream · error 通过 event
    payload 而非 HTTP 4xx (StreamingResponse 已开 · 早期 yield 后 stream 关).

Coverage:
  - 真跑 data/mock/agent2-samples/loans.csv 子集 (head 200) · 验 metrics 完整 + V2 双轨
  - 含 KS / AUC (V2 fix · 实装 deterministic AUC) / approval_rate / bad_rate
    / rule_stats per-rule / business_metrics / collision (V2 added panels)
  - csv_path 不存在 → SSE error event (code=CSV_NOT_FOUND)
  - ruleset 空 → SSE error event (code=RULESET_EMPTY)
  - 标签列不存在场景 → bad_rate / ks 为 None 或软降级

不依赖 LLM (真 backtest 是确定性计算).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent_riskctrl.tests._sse_helper import (
    assert_sse_done,
    assert_sse_error,
    get_metric,
    get_panel,
)


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
    """真跑 head 200 行 loans.csv · 验 metrics 完整 + V2 BE6.4 双轨 + AUC 实装."""
    if not LOANS_CSV.exists():
        pytest.skip(f"loans.csv 不在 {LOANS_CSV}")

    import pandas as pd
    df_full = pd.read_csv(LOANS_CSV, encoding="utf-8")
    sample = df_full.head(200)
    sub_csv = tmp_path / "loans_head200.csv"
    sample.to_csv(sub_csv, index=False, encoding="utf-8")

    resp = client.post(
        "/api/riskctrl/backtest",
        json={"ruleset": _DEMO_RULESET, "csv_path": str(sub_csv)},
    )
    done = assert_sse_done(resp, msg="real loans.csv backtest")

    # ===== 顶层 metrics =====
    assert get_metric(done, "total_records") == 200
    approved = get_metric(done, "approved")
    rejected = get_metric(done, "rejected")
    manual = get_metric(done, "manual_review")
    assert approved + rejected + manual <= 200
    assert 0.0 <= get_metric(done, "approval_rate") <= 1.0
    assert get_metric(done, "label_column_used") == "days_past_due"
    assert get_metric(done, "bad_rate") is not None
    assert 0.0 <= get_metric(done, "bad_rate") <= 1.0

    # ===== ks panel =====
    ks_panel = get_panel(done, "ks")
    assert ks_panel is not None
    assert 0.0 <= ks_panel["ksPeak"] <= 1.0
    # V2 fix: AUC 实装 · 不再硬编 0.0 (有 label 时 AUC > 0)
    assert ks_panel["auc"] >= 0.0
    # 实装后真 backtest 应有非零 AUC (有真信号)
    if ks_panel["ksPeak"] > 0:
        assert ks_panel["auc"] > 0.0, (
            f"AUC 不应再是占位 0.0 · ks={ks_panel['ksPeak']}, auc={ks_panel['auc']}"
        )

    # ===== rule_stats =====
    rule_stats = get_panel(done, "rule_stats")
    assert rule_stats is not None
    assert len(rule_stats) == 3
    for stat in rule_stats:
        assert "rule_id" in stat
        assert "fp" in stat or "FP" in stat
        assert "tn" in stat or "TN" in stat

    # ===== V2 BE6.4 业务双轨 panel =====
    biz = get_panel(done, "business_metrics")
    assert biz is not None
    assert "pass_rate" in biz
    assert "bad_rate" in biz
    assert "profit_total_wan" in biz
    assert "nim" in biz

    # ===== V2 BE6.3 collision panel =====
    coll = get_panel(done, "collision")
    assert coll is not None
    assert "shadows" in coll
    assert "contradictions" in coll
    assert "total_rules" in coll


# ----------------------------------------------------------------------------
# 错误路径 → SSE error event
# ----------------------------------------------------------------------------


def test_backtest_csv_not_exist(client):
    resp = client.post(
        "/api/riskctrl/backtest",
        json={
            "ruleset": _DEMO_RULESET,
            "csv_path": "data/mock/this_does_not_exist.csv",
        },
    )
    err = assert_sse_error(resp, expected_code="CSV_NOT_FOUND")
    assert "不存在" in err.get("message", "")


def test_backtest_empty_ruleset(client, tmp_path):
    csv = tmp_path / "tiny.csv"
    csv.write_text("debt_ratio\n0.5\n0.9\n", encoding="utf-8")
    resp = client.post(
        "/api/riskctrl/backtest",
        json={"ruleset": {"rules": []}, "csv_path": str(csv)},
    )
    err = assert_sse_error(resp, expected_code="RULESET_EMPTY")
    assert "rules" in err.get("message", "")


def test_backtest_ruleset_invalid(client, tmp_path):
    csv = tmp_path / "tiny.csv"
    csv.write_text("debt_ratio\n0.5\n", encoding="utf-8")
    resp = client.post(
        "/api/riskctrl/backtest",
        json={"ruleset": {"rules": "not a list"}, "csv_path": str(csv)},
    )
    # FastAPI Pydantic body 校验失败 · 走 422 (不进 SSE)
    # OR 早期校验 yield error event · 都接受
    if resp.status_code == 422:
        # body schema fail · OK
        return
    err = assert_sse_error(resp)
    assert err.get("code") in ("RULESET_INVALID", "RULESET_EMPTY", "BACKTEST_FAILED")


def test_backtest_no_label_column_soft_degrade(client, tmp_path):
    """csv 无 label/days_past_due 列 → bad_rate/ks 为 None · 不抛 (软降级)."""
    import pandas as pd
    csv = tmp_path / "no_label.csv"
    pd.DataFrame([
        {"debt_ratio": 0.5, "company_age_years": 3.0, "query_times_3m": 1},
        {"debt_ratio": 0.9, "company_age_years": 0.5, "query_times_3m": 8},
    ]).to_csv(csv, index=False, encoding="utf-8")

    resp = client.post(
        "/api/riskctrl/backtest",
        json={"ruleset": _DEMO_RULESET, "csv_path": str(csv)},
    )
    done = assert_sse_done(resp, msg="no label soft degrade")
    # 无 label · bad_rate 应是 None
    assert get_metric(done, "bad_rate") is None
    # ks 也应 None or 0.0 (软降级)
    ks_peak = get_metric(done, "ks_peak")
    assert ks_peak is None or ks_peak == 0.0
