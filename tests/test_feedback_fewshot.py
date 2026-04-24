# -*- coding: utf-8 -*-
"""飞轮第 4 环 scripts 冒烟测试。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def sandbox(tmp_path: Path) -> tuple[Path, Path]:
    """把真实 data/feedback/2026-04-23.jsonl 拷到临时目录，避免污染仓库。"""
    fb_dir = tmp_path / "feedback"
    fb_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(
        PROJECT_ROOT / "tests" / "fixtures" / "feedback" / "2026-04-23.jsonl",
        fb_dir / "2026-04-23.jsonl",
    )
    out_dir = tmp_path / "fewshot"
    return fb_dir, out_dir


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


def test_feedback_to_fewshot_aggregation(sandbox: tuple[Path, Path]) -> None:
    fb_dir, out_dir = sandbox
    res = _run([
        "scripts/feedback_to_fewshot.py",
        "--feedback-dir", str(fb_dir),
        "--out-dir", str(out_dir),
        "--min-count", "2",
        "--top-n", "5",
    ])
    assert res.returncode == 0, res.stderr

    # 预埋 4 agent 各含 2 条聚类，min-count=2 应产出 4 个 candidates 文件
    expected_agents = {"credit", "alert", "channel", "compliance"}
    produced = {p.stem.replace("-candidates", "") for p in out_dir.glob("*-candidates.json")}
    assert produced == expected_agents, (produced, expected_agents)

    cred = json.loads((out_dir / "credit-candidates.json").read_text(encoding="utf-8"))
    assert cred["agent"] == "credit"
    assert cred["examples"], "credit 应至少一个 example"
    for ex in cred["examples"]:
        assert ex["count"] >= 2
        assert ex["cluster_id"]
        assert "preferred_output" in ex


def test_feedback_to_fewshot_respects_min_count(sandbox: tuple[Path, Path]) -> None:
    fb_dir, out_dir = sandbox
    res = _run([
        "scripts/feedback_to_fewshot.py",
        "--feedback-dir", str(fb_dir),
        "--out-dir", str(out_dir),
        "--min-count", "99",  # 拉高阈值，无人入选
    ])
    assert res.returncode == 0
    assert list(out_dir.glob("*-candidates.json")) == []


def test_inject_fewshot_roundtrip(sandbox: tuple[Path, Path], tmp_path: Path) -> None:
    """aggregate → inject → revert 全链路走通，prompts.py 最终回到原样。"""
    fb_dir, out_dir = sandbox

    # Step 1: 聚合
    _run([
        "scripts/feedback_to_fewshot.py",
        "--feedback-dir", str(fb_dir),
        "--out-dir", str(out_dir),
        "--min-count", "2",
    ])

    # Step 2: 拷贝 prompts.py 做 baseline（测试完恢复原样）
    agent = "credit"
    prompts_path = PROJECT_ROOT / f"agent_{agent}" / "prompts.py"
    baseline = prompts_path.read_text(encoding="utf-8")

    try:
        # Step 3: inject
        inject_res = _run([
            "scripts/inject_fewshot_to_prompts.py",
            "--agent", agent,
            "--fewshot-dir", str(out_dir),
        ])
        assert inject_res.returncode == 0, inject_res.stderr

        after = prompts_path.read_text(encoding="utf-8")
        assert "FEW_SHOT_EXAMPLES" in after
        assert "auto-injected" in after
        assert after != baseline

        # Step 4: revert
        revert_res = _run([
            "scripts/inject_fewshot_to_prompts.py",
            "--agent", agent,
            "--fewshot-dir", str(out_dir),
            "--revert",
        ])
        assert revert_res.returncode == 0
        reverted = prompts_path.read_text(encoding="utf-8")
        assert "FEW_SHOT_EXAMPLES" not in reverted
        assert "auto-injected" not in reverted
    finally:
        # 始终恢复原 prompts.py，哪怕断言失败
        prompts_path.write_text(baseline, encoding="utf-8")


def test_inject_dry_run_does_not_modify(sandbox: tuple[Path, Path]) -> None:
    fb_dir, out_dir = sandbox
    _run([
        "scripts/feedback_to_fewshot.py",
        "--feedback-dir", str(fb_dir),
        "--out-dir", str(out_dir),
        "--min-count", "2",
    ])

    agent = "alert"
    prompts_path = PROJECT_ROOT / f"agent_{agent}" / "prompts.py"
    baseline = prompts_path.read_text(encoding="utf-8")
    res = _run([
        "scripts/inject_fewshot_to_prompts.py",
        "--agent", agent,
        "--fewshot-dir", str(out_dir),
        "--dry-run",
    ])
    assert res.returncode == 0
    assert prompts_path.read_text(encoding="utf-8") == baseline
