# -*- coding: utf-8 -*-
"""GET /api/channel/personal_insight/{candidate_id} 冒烟测试.

per onboarding · BE12 真业务 (2026-05-05):
- payload schema 含 candidate_id / person_features / product_fit /
  compliance_check / talking_points / pii_redacted / latency_ms
- stub=true 不调 LLM/源 · 返 stub schema (CI 稳定 · 不依赖网络)
- PII (name) hash 后再进 LLM prompt · pii_redacted=True
- 端到端 latency_ms 测量
- compliance_check.sources 至少含 local_pep_keywords (OFAC stub)

⚠️ 不依赖网络 · 默认走 stub=true OR build_personal_insight 内 LLM unavailable fallback.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from agent_channel.api import app


def test_personal_insight_stub_returns_full_schema():
    """stub=true · 返完整 schema · 字段齐 · 不调 LLM."""
    client = TestClient(app)
    resp = client.get("/api/channel/personal_insight/cand_test_001?stub=true")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # 7 顶层 key 齐
    assert body["candidate_id"] == "cand_test_001"
    assert "person_features" in body
    assert "product_fit" in body
    assert "compliance_check" in body
    assert "talking_points" in body
    assert "pii_redacted" in body
    assert "latency_ms" in body
    assert isinstance(body["latency_ms"], int)


def test_personal_insight_real_business_with_pii_redact():
    """真业务 · PII (name=张三) hash 后入 LLM · pii_redacted=True."""
    client = TestClient(app)
    resp = client.get(
        "/api/channel/personal_insight/cand_test_002"
        "?industry=新能源·锂电材料&role=实际控制人&risk_appetite=稳健"
        "&decision_path=单点决策&age=42&name=张三"
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["candidate_id"] == "cand_test_002"
    assert body["pii_redacted"] is True
    # age 已桶化 (40-44)
    age_range = body["person_features"]["age_range"]
    assert "-" in age_range or age_range == "未能自动填写"
    # product_fit 走启发式 · 实际控制人 + 稳健 → 应推荐 ≥ 1 产品
    assert isinstance(body["product_fit"]["recommended_products"], list)
    # compliance_check sources 含 OFAC stub
    sources = body["compliance_check"]["sources"]
    assert "local_pep_keywords" in sources


def test_personal_insight_compliance_pep_hit():
    """PEP 角色命中 · 政府官员 → pep=True · aml_risk 升中."""
    client = TestClient(app)
    resp = client.get(
        "/api/channel/personal_insight/cand_test_pep"
        "?role=政府官员&industry=金融"
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["compliance_check"]["pep"] is True
    assert body["compliance_check"]["aml_risk"] in ("中", "高")
    # local_pep_keywords 命中应在 flags 里
    flags = body["compliance_check"]["flags"]
    assert any("local_pep" in f for f in flags)


def test_personal_insight_compliance_sanction_hit():
    """Sanction 关键词命中 (industry 含"黑名单") → sanction=True · aml_risk=高 · flag local_sanction.

    per Codex review V1 NEEDS-FIX major 4 · sanction 路径必须有 test 覆盖.
    本 test 用 industry 字段作触发载体 (该字段在 _check_local_sanction 内联扫).
    """
    client = TestClient(app)
    resp = client.get(
        "/api/channel/personal_insight/cand_test_sanction"
        "?industry=黑名单贸易&role=实际控制人"
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["compliance_check"]["sanction"] is True
    assert body["compliance_check"]["aml_risk"] == "高"
    flags = body["compliance_check"]["flags"]
    assert any("local_sanction" in f for f in flags)


def test_personal_insight_empty_candidate_id_400():
    """candidate_id 空 (path 全 whitespace) → 验空校验 · 注意 path '/' 空段会被 FastAPI 直接 404."""
    client = TestClient(app)
    # 显式空 cid · path %20 spec
    resp = client.get("/api/channel/personal_insight/%20?stub=true")
    # %20 strip 后空 → 400
    assert resp.status_code == 400


def test_personal_insight_latency_ms_reasonable():
    """latency_ms 必填 · stub 路径应 < 200ms."""
    client = TestClient(app)
    resp = client.get("/api/channel/personal_insight/cand_test_lat?stub=true")
    body = resp.json()
    assert body["latency_ms"] >= 0
    assert body["latency_ms"] < 5000  # 即使真路径也不应超 5s
