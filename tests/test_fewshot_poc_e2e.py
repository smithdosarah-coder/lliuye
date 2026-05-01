# -*- coding: utf-8 -*-
"""Phase B BE10 PoC · few-shot 注入端到端冒烟.

数据飞轮第 4 环全链路:
  feedback jsonl → feedback_to_fewshot.py → candidates json
  → inject_fewshot_to_prompts.py (PoC: agent_credit only)
  → import agent_credit.prompts → FEW_SHOT_EXAMPLES non-empty
  → build_system_prompt(base) 输出含 few-shot block

unit test: build_system_prompt 与 _format_fewshot_block 行为
e2e test:  scripts 真跑 + 注入真 prompts.py + revert 兜底
"""
from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_PATH = PROJECT_ROOT / "agent_credit" / "prompts.py"


# ---------------------------------------------------------------------------
# Unit: build_system_prompt 行为 (无 IO · 直接 stub FEW_SHOT_EXAMPLES)
# ---------------------------------------------------------------------------

def test_build_system_prompt_empty_returns_base(monkeypatch):
    monkeypatch.setenv("LIUYE_FEWSHOT_POC_ENABLED", "1")
    from agent_credit import prompts as credit_prompts
    importlib.reload(credit_prompts)
    assert credit_prompts.FEW_SHOT_EXAMPLES == []
    base = "你是审贷员。"
    assert credit_prompts.build_system_prompt(base) == base


def test_build_system_prompt_with_examples_appends_block(monkeypatch):
    monkeypatch.setenv("LIUYE_FEWSHOT_POC_ENABLED", "1")
    from agent_credit import prompts as credit_prompts
    importlib.reload(credit_prompts)
    monkeypatch.setattr(credit_prompts, "FEW_SHOT_EXAMPLES", [
        {
            "reason": "现金流余量足以支撑更长期限",
            "sample_input": {"额度建议": 500, "期限": "12 月"},
            "preferred_output": {"额度建议": 600, "期限": "18 月"},
            "diff_summary": "额度建议: 500 → 600; 期限: 12 月 → 18 月",
        },
    ])
    base = "你是审贷员。"
    out = credit_prompts.build_system_prompt(base)
    assert out.startswith(base)
    assert "few-shot" in out
    assert "现金流余量足以支撑更长期限" in out
    assert "审贷员偏好输出" in out


def test_build_system_prompt_skips_malformed_entries(monkeypatch):
    monkeypatch.setenv("LIUYE_FEWSHOT_POC_ENABLED", "1")
    from agent_credit import prompts as credit_prompts
    importlib.reload(credit_prompts)
    monkeypatch.setattr(credit_prompts, "FEW_SHOT_EXAMPLES", [
        {"reason": "", "sample_input": {}, "preferred_output": {}},  # missing all
        {"reason": "ok", "sample_input": {"a": 1}, "preferred_output": {"a": 2}},
    ])
    out = credit_prompts.build_system_prompt("BASE")
    # 一条有效条目 → 块出现一次
    assert out.count("反馈原因: ok") == 1


# ---------------------------------------------------------------------------
# V2 Codex review fix · feature flag + PII redaction
# ---------------------------------------------------------------------------

def test_poc_flag_default_off_returns_base(monkeypatch):
    """Production 默认 LIUYE_FEWSHOT_POC_ENABLED 未设 → build 必返 base · 即使 examples 非空."""
    monkeypatch.delenv("LIUYE_FEWSHOT_POC_ENABLED", raising=False)
    from agent_credit import prompts as credit_prompts
    importlib.reload(credit_prompts)
    monkeypatch.setattr(credit_prompts, "FEW_SHOT_EXAMPLES", [
        {"reason": "should NOT leak", "sample_input": {"a": 1},
         "preferred_output": {"a": 2}, "diff_summary": "a:1→2"},
    ])
    out = credit_prompts.build_system_prompt("BASE")
    assert out == "BASE"
    assert "few-shot" not in out
    assert "should NOT leak" not in out


def test_poc_flag_explicit_zero_returns_base(monkeypatch):
    monkeypatch.setenv("LIUYE_FEWSHOT_POC_ENABLED", "0")
    from agent_credit import prompts as credit_prompts
    importlib.reload(credit_prompts)
    monkeypatch.setattr(credit_prompts, "FEW_SHOT_EXAMPLES", [
        {"reason": "X", "sample_input": {"a": 1}, "preferred_output": {"a": 2}},
    ])
    assert credit_prompts.build_system_prompt("BASE") == "BASE"


def test_pii_redaction_masks_phone_idcard_bankcard_email(monkeypatch):
    monkeypatch.setenv("LIUYE_FEWSHOT_POC_ENABLED", "1")
    from agent_credit import prompts as credit_prompts
    importlib.reload(credit_prompts)
    monkeypatch.setattr(credit_prompts, "FEW_SHOT_EXAMPLES", [
        {
            "reason": "联系电话 13812345678 客户邮箱 zhang@example.com 身份证 110101199001011234",
            "sample_input": {
                "phone": "18900001111",
                "id_card": "11010119800101567X",
                "bank_card": "6222021234567890123",
                "name": "张三",  # 姓名不 mask
            },
            "preferred_output": {
                "remark": "客户身份证 110101199001011234 已核实, 银行卡 6222021234567890123",
            },
            "diff_summary": "remark 加身份核实",
        },
    ])
    out = credit_prompts.build_system_prompt("BASE")
    # 原值不应出现
    assert "13812345678" not in out
    assert "18900001111" not in out
    assert "zhang@example.com" not in out
    assert "110101199001011234" not in out
    assert "6222021234567890123" not in out
    assert "11010119800101567X" not in out
    # mask token 应出现
    assert "<MOBILE>" in out
    assert "<EMAIL>" in out
    assert "<ID-CARD>" in out
    assert "<BANK-CARD>" in out
    # 非 PII 字段保留
    assert "张三" in out


# ---------------------------------------------------------------------------
# E2E: 真跑 scripts + 注入真 prompts.py + 必 revert
# ---------------------------------------------------------------------------

@pytest.fixture
def fewshot_e2e_sandbox(tmp_path: Path):
    """真注入 agent_credit/prompts.py · finally 必 revert (避免污染仓库)."""
    fb_dir = tmp_path / "feedback"
    fewshot_dir = tmp_path / "fewshot"
    fb_dir.mkdir(parents=True)
    fewshot_dir.mkdir(parents=True)

    # 2 条相似 feedback (聚类 min-count=2 命中)
    jsonl = fb_dir / "2026-05-01.jsonl"
    records = [
        {
            "timestamp": "2026-05-01T10:00:00",
            "agent": "credit",
            "session_id": "sess-A",
            "user_id": "rm-001",
            "original_output": {"额度建议": 500, "期限": "12 月"},
            "user_correction": {"额度建议": 700, "期限": "24 月"},
            "correction_reason": "现金流余量足够",
        },
        {
            "timestamp": "2026-05-01T11:00:00",
            "agent": "credit",
            "session_id": "sess-B",
            "user_id": "rm-002",
            "original_output": {"额度建议": 400, "期限": "12 月"},
            "user_correction": {"额度建议": 600, "期限": "18 月"},
            "correction_reason": "现金流余量足够",
        },
    ]
    with jsonl.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    original_prompts_text = PROMPTS_PATH.read_text(encoding="utf-8")
    yield fb_dir, fewshot_dir, jsonl

    # 兜底 revert: 即使 inject script revert 失败也恢复原文
    PROMPTS_PATH.write_text(original_prompts_text, encoding="utf-8")


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, *cmd],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        env=env,
    )


def test_e2e_feedback_to_fewshot_to_inject_to_prompt(fewshot_e2e_sandbox, monkeypatch):
    monkeypatch.setenv("LIUYE_FEWSHOT_POC_ENABLED", "1")
    fb_dir, fewshot_dir, _ = fewshot_e2e_sandbox

    # Step 1: aggregate feedback → candidates
    rc1 = _run([
        "scripts/feedback_to_fewshot.py",
        "--feedback-dir", str(fb_dir),
        "--out-dir", str(fewshot_dir),
        "--min-count", "2",
        "--top-n", "3",
    ])
    assert rc1.returncode == 0, f"feedback_to_fewshot failed: {rc1.stderr}"
    candidates_path = fewshot_dir / "credit-candidates.json"
    assert candidates_path.exists(), f"candidates missing: {list(fewshot_dir.iterdir())}"
    payload = json.loads(candidates_path.read_text(encoding="utf-8"))
    assert payload["agent"] == "credit"
    assert len(payload["examples"]) >= 1

    # Step 2: inject (真改 agent_credit/prompts.py · finally revert)
    rc2 = _run([
        "scripts/inject_fewshot_to_prompts.py",
        "--agent", "credit",
        "--fewshot-dir", str(fewshot_dir),
    ])
    assert rc2.returncode == 0, f"inject failed: {rc2.stderr}"

    # Step 3: reload prompts module · 应看到 marker 块 + FEW_SHOT_EXAMPLES non-empty
    prompts_text = PROMPTS_PATH.read_text(encoding="utf-8")
    assert "FEW_SHOT_EXAMPLES · auto-injected" in prompts_text
    assert "现金流余量足够" in prompts_text

    from agent_credit import prompts as credit_prompts
    importlib.reload(credit_prompts)
    assert len(credit_prompts.FEW_SHOT_EXAMPLES) >= 1

    # Step 4: build_system_prompt 真把 examples 拼进 base
    final = credit_prompts.build_system_prompt("BASE_SYSTEM_PROMPT")
    assert final.startswith("BASE_SYSTEM_PROMPT")
    assert "few-shot" in final
    assert "现金流余量足够" in final

    # Step 5: revert (脚本能力验)
    rc3 = _run([
        "scripts/inject_fewshot_to_prompts.py",
        "--agent", "credit",
        "--revert",
    ])
    assert rc3.returncode == 0
    after_revert = PROMPTS_PATH.read_text(encoding="utf-8")
    assert "FEW_SHOT_EXAMPLES · auto-injected" not in after_revert

    # 重 reload · FEW_SHOT_EXAMPLES 回到默认 []
    importlib.reload(credit_prompts)
    assert credit_prompts.FEW_SHOT_EXAMPLES == []
