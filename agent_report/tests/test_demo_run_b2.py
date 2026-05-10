# -*- coding: utf-8 -*-
"""Phase B.2 · POST /api/report/demo/run typed error contract E2E.

per dispatch §"错误降级" Step 5 + §"不可 GO 条件" #1 (/demo/run 不再 yield fixture):
  - sample_id 白名单 + 路径穿越防御 (400 SAMPLE_ID_INVALID)
  - sample_dir 不存在 → 404 SAMPLE_DIR_MISSING
  - DEEPSEEK_API_KEY 未配 → 503 DEEPSEEK_KEY_MISSING (拒 silent fallback mock)
  - classifier cache 缺失 → 503 DEMO_CLASSIFIER_MISSING
  - 默认对公模板缺失 → 503 DEMO_TEMPLATE_MISSING

PM 真意 reframe (2026-05-10): 演示 = 上传 sample 跑真后端 · 不切假数据 ·
demo/run 旧 yield fixture event (Phase A worker-A4 scenario_id easy/medium/hard) 已废.

测试策略:
  - 不依赖真 DEEPSEEK_API_KEY (CI/local 通用)
  - 用 monkeypatch + 临时目录构造各种错误前置条件
  - 验证 typed error response shape: {detail: {error: {code, message}}}
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_report.api import app  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)


def _parse_typed_error(resp) -> dict:
    """从 HTTPException response 抽 {code, message} · 支持 detail.error 嵌套."""
    body = resp.json()
    detail = body.get("detail", {})
    if isinstance(detail, dict) and "error" in detail:
        return detail["error"]
    return {"code": "UNKNOWN", "message": str(detail)}


# ============================================================================
# 1. sample_id 白名单 + 路径穿越防御 (400 SAMPLE_ID_INVALID)
# ============================================================================


def test_sample_id_invalid_empty(client):
    """空 sample_id → 400 · code=SAMPLE_ID_INVALID."""
    resp = client.post("/api/report/demo/run", json={"sample_id": ""})
    assert resp.status_code == 400
    err = _parse_typed_error(resp)
    assert err["code"] == "SAMPLE_ID_INVALID"


def test_sample_id_invalid_format(client):
    """命名不符 ^DP\\d{3}_<name>$ → 400."""
    bad_ids = ["easy", "DP01_test", "DPXXX_test", "DP001-test", "MockSample"]
    for sid in bad_ids:
        resp = client.post("/api/report/demo/run", json={"sample_id": sid})
        assert resp.status_code == 400, f"{sid}: 应 400 实 {resp.status_code}"
        err = _parse_typed_error(resp)
        assert err["code"] == "SAMPLE_ID_INVALID", f"{sid}: code 应 SAMPLE_ID_INVALID 实 {err['code']}"


def test_sample_id_path_traversal_blocked(client):
    """路径穿越尝试 → 400 (regex match fail · 不到 dir 校验)."""
    bad_ids = ["DP001_../etc", "DP001_/absolute", "DP001_~/home"]
    for sid in bad_ids:
        resp = client.post("/api/report/demo/run", json={"sample_id": sid})
        assert resp.status_code == 400, f"{sid}: 路径穿越应阻 实 {resp.status_code}"


# ============================================================================
# 2. sample_dir 不存在 (404 SAMPLE_DIR_MISSING)
# ============================================================================


def test_sample_dir_missing(client):
    """合法格式但 dir 不存在 → 404 SAMPLE_DIR_MISSING."""
    resp = client.post("/api/report/demo/run", json={"sample_id": "DP999_NotExist"})
    assert resp.status_code == 404
    err = _parse_typed_error(resp)
    assert err["code"] == "SAMPLE_DIR_MISSING"
    # actionable hint 应给客户经理 actionable 选项
    assert "DP001" in err["message"], "404 message 应提示客户经理可选 DP001-DP005"


# ============================================================================
# 3. DEEPSEEK_API_KEY 缺失 (503 DEEPSEEK_KEY_MISSING)
# ============================================================================


def test_deepseek_key_missing(client, monkeypatch):
    """sample dir 存在但无 DEEPSEEK_API_KEY → 503 · 拒 silent fallback mock."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    resp = client.post("/api/report/demo/run", json={"sample_id": "DP001_龙峰精工"})
    assert resp.status_code == 503
    err = _parse_typed_error(resp)
    assert err["code"] == "DEEPSEEK_KEY_MISSING"
    # PM 真意 reframe 标 (red line 1 · silent fallback mock 拒)
    assert "真" in err["message"] or "real" in err["message"].lower()


def test_deepseek_key_empty_string(client, monkeypatch):
    """DEEPSEEK_API_KEY 设为空字符串 (whitespace strip) → 同样 503."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "  ")
    resp = client.post("/api/report/demo/run", json={"sample_id": "DP001_龙峰精工"})
    assert resp.status_code == 503
    err = _parse_typed_error(resp)
    assert err["code"] == "DEEPSEEK_KEY_MISSING"


# ============================================================================
# 4. classifier cache 缺失 (503 DEMO_CLASSIFIER_MISSING)
# ============================================================================


def test_classifier_cache_missing(client, monkeypatch, tmp_path):
    """有 DEEPSEEK_API_KEY 但 outputs/v16_llm_classified.json 不存在 → 503."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-fake-for-test")
    # patch _DEFAULT_CLASSIFIED_JSON 指 nonexistent 路径
    fake_classified = tmp_path / "nonexistent_v16_llm_classified.json"
    with patch("agent_report.api._DEFAULT_CLASSIFIED_JSON", fake_classified):
        resp = client.post("/api/report/demo/run", json={"sample_id": "DP001_龙峰精工"})
    assert resp.status_code == 503
    err = _parse_typed_error(resp)
    assert err["code"] == "DEMO_CLASSIFIER_MISSING"
    # actionable hint: 提示 admin 一次性预跑
    assert "v16_classifier" in err["message"], "应提示 admin 跑 v16_classifier"


# ============================================================================
# 5. 默认对公模板缺失 (503 DEMO_TEMPLATE_MISSING)
# ============================================================================


def test_template_missing(client, monkeypatch, tmp_path):
    """source_docx 默认模板不存在 → 503 (理论场景 · 实际 samples/ 应入 git)."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-fake-for-test")
    # 预跑 cache mock 为存在 (skip cache check) · template 缺
    fake_classified = tmp_path / "fake_cache.json"
    fake_classified.write_text("{}", encoding="utf-8")
    fake_template_rel = "samples/this_template_does_not_exist.docx"
    with patch("agent_report.api._DEFAULT_CLASSIFIED_JSON", fake_classified), \
         patch("agent_report.api._DEFAULT_DEMO_SOURCE_DOCX", fake_template_rel):
        resp = client.post("/api/report/demo/run", json={"sample_id": "DP001_龙峰精工"})
    assert resp.status_code == 503
    err = _parse_typed_error(resp)
    assert err["code"] == "DEMO_TEMPLATE_MISSING"


# ============================================================================
# 6. 反模式回归防御 (Phase A worker-A4 scenario_id 接口已废)
# ============================================================================


def test_no_scenario_id_accepted(client):
    """旧接口 scenario_id (easy/medium/hard) 不再被接受 · 视作 SAMPLE_ID_INVALID
    (空 sample_id default · 不命中正则)."""
    # 客户端发旧字段 · 后端用 sample_id default · 旧字段 ignore
    resp = client.post("/api/report/demo/run", json={"scenario_id": "easy"})
    # default sample_id = "DP001_龙峰精工" · 但缺 DEEPSEEK_KEY_MISSING (合理 503) ·
    # 关键: 不会因 scenario_id="easy" 走旧 fixture 路径
    if "DEEPSEEK_API_KEY" in os.environ and os.environ["DEEPSEEK_API_KEY"].strip():
        # 真 env 时跳 (避免触发真 LLM)
        pytest.skip("real DEEPSEEK_API_KEY env · skip to avoid real LLM call")
    assert resp.status_code in {503, 400}, "旧 scenario_id 不再触发任何 fixture · 仅 default sample_id 走真路径"


# ============================================================================
# 7. 已废 fixture path 验证 (data/mock/workspace/report/scenarios/ 仅保留 material_gap_inputs)
# ============================================================================


def test_scenario_fixtures_stripped():
    """3 fixture 仅保留 material_gap_inputs · 不再含 sections/qc/stats/profile demo 答案字段."""
    sd = PROJECT_ROOT / "data" / "mock" / "workspace" / "report" / "scenarios"
    forbidden_keys = {"sections", "qc", "stats", "profile", "stage_messages", "pending_questions"}
    for sid in ("easy", "medium", "hard"):
        path = sd / f"{sid}.json"
        assert path.exists(), f"{sid}.json 应保留 (test_material_gap consumer)"
        data = json.loads(path.read_text("utf-8"))
        present = forbidden_keys & set(data.keys())
        assert not present, (
            f"{sid}.json 含 demo 答案字段: {present} · "
            f"违反 dispatch §'禁止用' (反 5 原则 §3.5 #5) · "
            f"修: 仅保留 material_gap_inputs (test_material_gap consumer)"
        )
        # material_gap_inputs 必须保留 (test_material_gap 单测消费)
        assert "material_gap_inputs" in data, f"{sid}.json 缺 material_gap_inputs · test_material_gap 会破"
