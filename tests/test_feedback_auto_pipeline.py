# -*- coding: utf-8 -*-
"""Phase B Sprint 2 决策 2 · few-shot 自动 pipeline 覆盖.

覆盖:
  - quality 4 必要条件 (rating>=4 / len>=100 / has_diff / within window) 各单独失败 case
  - per-agent top N 取
  - similarity dedup > 0.85 真合并
  - _redact_pii / _redact_value 复用 (PII 不漏)
  - dry-run 不写盘
  - no-inject 写 candidates 但不调 inject
  - 全链路 e2e: 真跑 pipeline → candidates → inject → revert
"""
from __future__ import annotations

import importlib
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def pipeline_sandbox(tmp_path: Path):
    fb = tmp_path / "feedback"
    fs = tmp_path / "fewshot"
    fb.mkdir()
    return fb, fs


def _write_jsonl(fb_dir: Path, date_str: str, records: list[dict]) -> None:
    p = fb_dir / f"{date_str}.jsonl"
    with p.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _today_iso(offset_days: int = 0) -> str:
    return (datetime.now() - timedelta(days=offset_days)).isoformat(timespec="seconds")


def _today_date(offset_days: int = 0) -> str:
    return (datetime.now() - timedelta(days=offset_days)).date().isoformat()


def _good_record(agent="credit", rating=5, ts: str | None = None,
                 user_id: str = "rm-X", session: str = "s") -> dict:
    """合 quality 4 条件的 baseline record · combined len ≥ 100 chars."""
    return {
        "timestamp": ts or _today_iso(0),
        "agent": agent,
        "session_id": session,
        "user_id": user_id,
        "original_output": {"额度": 500, "期限": "12 月", "remark": "需复核流水"},
        "user_correction": {
            "额度": 700,
            "期限": "24 月",
            "remark": "现金流足以支撑更长期限和更高额度建议复核",
        },
        "correction_reason": (
            "现金流余量经反复核算可支撑更长期限和更高额度建议复核后调高·"
            "客户经营稳定连续 3 年盈利无重大风险点"
        ),
        "rating": rating,
    }


# ---------------------------------------------------------------------------
# quality 4 必要条件 单独失败 case
# ---------------------------------------------------------------------------

def test_quality_filter_rating_below_4_excluded(pipeline_sandbox):
    fb, fs = pipeline_sandbox
    _write_jsonl(fb, _today_date(0), [
        _good_record(rating=3),
        _good_record(rating=5, user_id="rm-Y"),
    ])
    from scripts.feedback_auto_pipeline import aggregate_for_agent, _scan_feedback
    records = _scan_feedback(fb, agent="credit", window_days=30)
    examples = aggregate_for_agent(records, window_days=30)
    assert len(examples) == 1


def test_quality_filter_short_feedback_excluded(pipeline_sandbox):
    fb, fs = pipeline_sandbox
    short = _good_record()
    short["correction_reason"] = "好"
    short["user_correction"] = {"x": 1}
    _write_jsonl(fb, _today_date(0), [short, _good_record(user_id="rm-LONG")])
    from scripts.feedback_auto_pipeline import aggregate_for_agent, _scan_feedback
    records = _scan_feedback(fb, agent="credit", window_days=30)
    assert len(aggregate_for_agent(records, window_days=30)) == 1


def test_quality_filter_no_diff_excluded(pipeline_sandbox):
    fb, fs = pipeline_sandbox
    no_diff = _good_record()
    no_diff["user_correction"] = no_diff["original_output"]  # thumbs-up
    _write_jsonl(fb, _today_date(0), [no_diff, _good_record(user_id="rm-DIFF")])
    from scripts.feedback_auto_pipeline import aggregate_for_agent, _scan_feedback
    records = _scan_feedback(fb, agent="credit", window_days=30)
    assert len(aggregate_for_agent(records, window_days=30)) == 1


def test_quality_filter_outside_window_excluded(pipeline_sandbox):
    fb, fs = pipeline_sandbox
    old = _good_record(ts=_today_iso(60))
    fresh = _good_record(ts=_today_iso(5), user_id="rm-FRESH")
    _write_jsonl(fb, _today_date(60), [old])
    _write_jsonl(fb, _today_date(5), [fresh])
    from scripts.feedback_auto_pipeline import aggregate_for_agent, _scan_feedback
    records = _scan_feedback(fb, agent="credit", window_days=30)
    examples = aggregate_for_agent(records, window_days=30)
    assert len(examples) == 1
    assert examples[0]["sample_input"]  # the fresh one


# ---------------------------------------------------------------------------
# top N
# ---------------------------------------------------------------------------

def test_top_n_per_agent_caps_at_10(pipeline_sandbox):
    fb, fs = pipeline_sandbox
    # 12 条全 quality + 各不相似 (correction_reason 各异)
    records = []
    for i in range(12):
        r = _good_record(user_id=f"rm-{i:03d}", session=f"s{i}", ts=_today_iso(i % 7))
        r["correction_reason"] = f"reason-{i}-需要更长" + ("a" * (100 + i))  # uniqueness
        r["user_correction"] = {"额度": 500 + i * 10, "期限": f"{12+i} 月"}
        records.append(r)
    _write_jsonl(fb, _today_date(0), records)
    from scripts.feedback_auto_pipeline import aggregate_for_agent, _scan_feedback
    scanned = _scan_feedback(fb, agent="credit", window_days=30)
    examples = aggregate_for_agent(scanned, window_days=30)
    assert len(examples) <= 10


# ---------------------------------------------------------------------------
# similarity dedup
# ---------------------------------------------------------------------------

def test_similarity_dedup_collapses_near_duplicates(pipeline_sandbox):
    fb, fs = pipeline_sandbox
    # 2 条几乎一样 + 1 条独立
    a = _good_record(user_id="rm-A")
    b = _good_record(user_id="rm-B")
    b["correction_reason"] = a["correction_reason"]  # 完全相同 reason 内容
    b["user_correction"] = a["user_correction"]
    c = _good_record(user_id="rm-C")
    c["correction_reason"] = "另一类完全不同的反馈描述客户经营和征信材料关系" + "b" * 80
    c["user_correction"] = {"分类": "对私", "remark": "不一样的字段"}
    _write_jsonl(fb, _today_date(0), [a, b, c])
    from scripts.feedback_auto_pipeline import aggregate_for_agent, _scan_feedback
    records = _scan_feedback(fb, agent="credit", window_days=30)
    examples = aggregate_for_agent(records, window_days=30)
    # a/b 合并 → 2 条
    assert len(examples) == 2


# ---------------------------------------------------------------------------
# PII redaction 复用
# ---------------------------------------------------------------------------

def test_pii_redacted_in_examples(pipeline_sandbox):
    fb, fs = pipeline_sandbox
    rec = _good_record()
    rec["correction_reason"] = "请联系客户 13812345678 邮箱 zhang@example.com 复核相关流水后再调高额度否则风险偏高"
    rec["user_correction"] = {
        "额度": 700,
        "phone": "18900001111",
        "id_card": "110101199001011234",
        "bank_card": "6222021234567890123",
    }
    rec["original_output"]["phone"] = "13912340000"
    _write_jsonl(fb, _today_date(0), [rec])
    from scripts.feedback_auto_pipeline import aggregate_for_agent, _scan_feedback
    records = _scan_feedback(fb, agent="credit", window_days=30)
    examples = aggregate_for_agent(records, window_days=30)
    body = json.dumps(examples, ensure_ascii=False)
    # 原 PII 不应出现
    assert "13812345678" not in body
    assert "zhang@example.com" not in body
    assert "18900001111" not in body
    assert "110101199001011234" not in body
    assert "13912340000" not in body
    assert "6222021234567890123" not in body
    # mask token 出现
    assert "<MOBILE>" in body
    assert "<EMAIL>" in body
    assert "<ID-CARD>" in body
    assert "<BANK-CARD>" in body


# ---------------------------------------------------------------------------
# dry-run / no-inject
# ---------------------------------------------------------------------------

def test_dry_run_writes_nothing(pipeline_sandbox):
    fb, fs = pipeline_sandbox
    _write_jsonl(fb, _today_date(0), [_good_record()])
    from scripts.feedback_auto_pipeline import run_pipeline
    rc = run_pipeline(agents=["credit"], feedback_dir=fb, fewshot_dir=fs,
                      window_days=30, dry_run=True)
    assert rc == 0
    assert not fs.exists() or not list(fs.iterdir())


def test_no_inject_writes_candidates_only(pipeline_sandbox, monkeypatch):
    fb, fs = pipeline_sandbox
    _write_jsonl(fb, _today_date(0), [_good_record()])
    from scripts.feedback_auto_pipeline import run_pipeline
    rc = run_pipeline(agents=["credit"], feedback_dir=fb, fewshot_dir=fs,
                      window_days=30, dry_run=False, no_inject=True)
    assert rc == 0
    assert (fs / "credit-candidates.json").exists()


# ---------------------------------------------------------------------------
# e2e
# ---------------------------------------------------------------------------

def test_e2e_pipeline_to_inject_to_prompts(pipeline_sandbox):
    """run_pipeline 真改 agent_credit/prompts.py · finally revert."""
    fb, fs = pipeline_sandbox
    _write_jsonl(fb, _today_date(0), [_good_record(), _good_record(user_id="rm-Z", session="sZ")])
    prompts_path = PROJECT_ROOT / "agent_credit" / "prompts.py"
    baseline = prompts_path.read_text(encoding="utf-8")
    try:
        from scripts.feedback_auto_pipeline import run_pipeline
        rc = run_pipeline(agents=["credit"], feedback_dir=fb, fewshot_dir=fs,
                          window_days=30)
        assert rc == 0
        after = prompts_path.read_text(encoding="utf-8")
        assert "auto-injected" in after
        assert "现金流余量" in after
    finally:
        prompts_path.write_text(baseline, encoding="utf-8")


def test_window_days_clamps_zero_returns_2(pipeline_sandbox):
    from scripts.feedback_auto_pipeline import main
    rc = main(["--window-days", "0"])
    assert rc == 2
