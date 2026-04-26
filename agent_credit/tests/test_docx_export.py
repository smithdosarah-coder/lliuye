"""decision_letter_docx 本地渲染测试 (旧名 docx_export · rename per Wave 2 housekeeping #2 · Q-033 follow-up)。"""
from __future__ import annotations

import io
import zipfile

from agent_credit.decision_letter_docx import build_filename, export


def _make_advice() -> dict:
    return {
        "advice_id": "test001234",
        "segment": "corporate",
        "subject_name": "测试样本有限公司",
        "decision_time": "2026-04-18T10:00:00",
        "decision": "有条件批准",
        "approved_amount": 500,
        "approved_term_months": 12,
        "interest_rate": 0.0475,
        "rate_benchmark": "LPR+150BP",
        "composite_score": 72,
        "risk_grade": "B",
        "conditions": ["提供审计财报", "半年复查"],
        "decision_reason": "样本评分 72，建议有条件批准。",
        "top_reason_codes": [
            {"code": "R_CORP_DEBT_HIGH", "title": "资产负债率过高", "severity": "red",
             "evidence_path": "financial.debt_ratio", "evidence_value": 0.75,
             "threshold": 0.70, "description": "杠杆超阈"},
        ],
        "red_line_hits": [
            {"rule_id": "corp_rl_001", "rule_name": "客户集中度",
             "severity": "yellow", "actual_value": 0.42, "threshold": 0.40,
             "description": "客户集中度超阈"},
        ],
        "amount_methods": {"revenue_method": 500, "netasset_method": 420},
        "similar_cases_summary": "案例 A / 案例 B",
    }


def test_render_produces_valid_docx_zip():
    data = export(_make_advice())
    assert len(data) > 3000
    # docx 本质是 zip
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
    assert "word/document.xml" in names
    assert "[Content_Types].xml" in names


def test_filename_uses_subject_and_id():
    fn = build_filename(_make_advice())
    assert "测试样本有限公司" in fn
    assert "test001234" in fn
    assert fn.endswith(".docx")


def test_filename_strips_illegal_chars():
    fn = build_filename({"subject_name": "客户/有\\限?公司", "advice_id": "x"})
    for bad in r'\/:*?"<>|':
        assert bad not in fn


def test_render_tolerates_minimal_payload():
    data = export({"subject_name": "X", "decision": "拒绝"})
    assert len(data) > 2000
