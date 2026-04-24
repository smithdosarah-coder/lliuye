# -*- coding: utf-8 -*-
"""feedback_to_fewshot.py --dry-run 覆盖（HOLDING-CA · H-A）

验证：
1. dry-run 路径：不落盘，日志含 "[dry-run] would write"
2. 正常路径：落盘，日志含 "wrote"
3. 幂等性：同一批 feedback 连跑两次 --dry-run 结果（stdout/stderr + 目标目录）一致
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def sandbox(tmp_path: Path) -> tuple[Path, Path]:
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


def test_dry_run_does_not_write(sandbox: tuple[Path, Path]) -> None:
    fb_dir, out_dir = sandbox
    assert not out_dir.exists()

    res = _run([
        "scripts/feedback_to_fewshot.py",
        "--feedback-dir", str(fb_dir),
        "--out-dir", str(out_dir),
        "--min-count", "2",
        "--dry-run",
    ])
    assert res.returncode == 0, res.stderr

    assert not out_dir.exists() or list(out_dir.iterdir()) == [], (
        f"dry-run 不应产生任何文件，却写了: {list(out_dir.iterdir()) if out_dir.exists() else []}"
    )

    combined = res.stdout + res.stderr
    assert "[dry-run] would write" in combined
    assert "wrote" not in combined.replace("[dry-run]", "").replace("would write", "")


def test_normal_run_writes_files(sandbox: tuple[Path, Path]) -> None:
    fb_dir, out_dir = sandbox

    res = _run([
        "scripts/feedback_to_fewshot.py",
        "--feedback-dir", str(fb_dir),
        "--out-dir", str(out_dir),
        "--min-count", "2",
    ])
    assert res.returncode == 0

    files = list(out_dir.glob("*-candidates.json"))
    assert files, "正常模式应落盘"
    combined = res.stdout + res.stderr
    assert "wrote" in combined
    assert "[dry-run]" not in combined


def test_dry_run_idempotent(sandbox: tuple[Path, Path]) -> None:
    """同一批 feedback 连跑两次 --dry-run，输出一致（时间戳字段只在真写时生成）。"""
    fb_dir, out_dir = sandbox

    def _dry_lines() -> list[str]:
        res = _run([
            "scripts/feedback_to_fewshot.py",
            "--feedback-dir", str(fb_dir),
            "--out-dir", str(out_dir),
            "--min-count", "2",
            "--dry-run",
        ])
        assert res.returncode == 0
        combined = res.stdout + res.stderr
        # 只保留含 "[dry-run]" 或 "loaded" 的行，排除因 log 配置变化引入的噪声
        return sorted(
            line.strip()
            for line in combined.splitlines()
            if "[dry-run]" in line or line.startswith("loaded")
        )

    first = _dry_lines()
    second = _dry_lines()

    assert first == second, (
        "--dry-run 连跑两次输出应一致（幂等）\n"
        f"first:\n{chr(10).join(first)}\nsecond:\n{chr(10).join(second)}"
    )
    assert first, "至少应出现一条 [dry-run] 日志"
    # 目录仍为空
    assert not out_dir.exists() or list(out_dir.iterdir()) == []
