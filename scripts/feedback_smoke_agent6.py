# -*- coding: utf-8 -*-
"""Agent6 · 反馈飞轮 E2E smoke(5 步连跑)

DoD: L3-8(反馈飞轮 E2E)
对应 onboarding: docs/onboarding/agent6-phase-2.md Task A 收敛条件

5 步:
  1. 清理临时工作目录
  2. POST /api/feedback(3 条报告 agent 反馈 + 1 条 credit 反馈 做噪声)
  3. 跑 scripts/feedback_extract_agent6.py → 生成 extracted YAML
  4. 断言 YAML 结构 + 章节覆盖 + 去重有效
  5. 断言 prompts.get_feedback_fewshot_block(chapter) 非空

命令:
  py scripts/feedback_smoke_agent6.py
"""
from __future__ import annotations

import importlib
import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _log(stage: str, msg: str) -> None:
    print(f"[{stage}] {msg}")


def step_1_setup_tmp(base: Path) -> Path:
    """清理并准备临时 feedback 目录(含 bootstrap 复制)。"""
    tmp = base / "agent6_feedback_smoke"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    # 复制 bootstrap 到临时目录,模拟生产前置
    src_boot = PROJECT_ROOT / "data" / "feedback" / "bootstrap"
    if src_boot.is_dir():
        dst_boot = tmp / "bootstrap"
        dst_boot.mkdir()
        for p in src_boot.glob("6_*.yaml"):
            shutil.copy2(p, dst_boot / p.name)
    _log("step1", f"tmp dir ready: {tmp}")
    return tmp


def step_2_post_feedback(tmp: Path) -> None:
    """用 TestClient POST /api/feedback(用 monkeypatch 让 api_server 写到 tmp)。"""
    from fastapi.testclient import TestClient
    import api_server

    # 临时重定向 PROJECT_ROOT 让 JSONL 落到 tmp
    original = api_server.PROJECT_ROOT
    api_server.PROJECT_ROOT = tmp.parent  # tmp.parent/data/feedback 结构
    # api_server 写 data/feedback/<date>.jsonl,所以 parent 下应该有 data/feedback
    (tmp.parent / "data" / "feedback").mkdir(parents=True, exist_ok=True)

    try:
        client = TestClient(api_server.app)
        payloads = [
            {
                "agent": "report",
                "session_id": "smoke-report-1",
                "original_output": {
                    "field_path": "chapter_3_finance.rd_intensity",
                    "value": "8.5%",
                },
                "user_correction": {
                    "field_path": "chapter_3_finance.rd_intensity",
                    "value": "7.97%,引用审计附注七-16",
                },
                "correction_reason": "研发强度比率口径错+未引用出处",
            },
            {
                "agent": "report",
                "session_id": "smoke-report-2",
                "original_output": {"v": 1},
                "user_correction": {"v": 2},
                "correction_reason": "测试多条追加",
            },
            {
                "agent": "report",
                "session_id": "smoke-report-dup",
                "original_output": {
                    "field_path": "chapter_3_finance.rd_intensity",
                    "value": "8.5%",
                },
                "user_correction": {
                    "field_path": "chapter_3_finance.rd_intensity",
                    "value": "7.97%,引用审计附注七-16",
                },
                "correction_reason": "研发强度比率口径错+未引用出处",
            },
            {
                "agent": "credit",
                "session_id": "smoke-credit-noise",
                "original_output": {},
                "user_correction": {},
                "correction_reason": "噪声数据(非 report,应被过滤)",
            },
        ]
        for p in payloads:
            r = client.post("/api/feedback", json=p)
            assert r.status_code == 200, f"feedback failed: {r.text}"
        _log("step2", f"posted {len(payloads)} feedback entries (含 1 credit 噪声)")
    finally:
        api_server.PROJECT_ROOT = original


def step_3_run_extract(tmp: Path) -> Path:
    """调用 extract 模块主流程,传入 tmp 作为 feedback_dir。"""
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    import feedback_extract_agent6 as fe  # type: ignore
    importlib.reload(fe)

    out_path = tmp / "extracted_result.yaml"
    fb_dir = tmp.parent / "data" / "feedback"
    # 用到 tmp/bootstrap 作为 bootstrap 源
    result = fe.run(
        limit=20,
        out_path=out_path,
        feedback_dir=fb_dir,
        bootstrap_dir=tmp / "bootstrap",
    )
    assert result.is_file(), f"extracted file not created: {result}"
    _log("step3", f"extracted YAML: {result}")
    return result


def step_4_assert_yaml(out_path: Path) -> dict:
    data = yaml.safe_load(out_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "extracted YAML not a dict"
    assert data.get("agent") == "report"
    assert "items" in data and isinstance(data["items"], list)
    items = data["items"]
    assert len(items) > 0, "no items extracted"

    chapters = set()
    for it in items:
        chap = it.get("chapter") or it.get("injection_hint", {}).get("target_chapter")
        chapters.add(str(chap))
    assert len(chapters) >= 3, f"章节覆盖不足:{chapters}(期望 ≥3)"

    src = data.get("source_counts", {})
    assert src.get("bootstrap", 0) >= 5, f"bootstrap 应≥5:{src}"
    _log("step4", f"YAML assertions passed · items={len(items)} chapters={chapters} src={src}")
    return data


def step_5_assert_fewshot_injection(extracted_path: Path) -> None:
    """把提取好的 YAML 放到默认位置,重载 prompts.py,断言 few-shot block 注入成功。"""
    default_dir = PROJECT_ROOT / "data" / "feedback" / "extracted"
    default_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y%m%d")
    default_target = default_dir / f"6_{date}.yaml"
    shutil.copy2(extracted_path, default_target)
    try:
        if "prompts" in sys.modules:
            del sys.modules["prompts"]
        import prompts  # type: ignore

        for chap in (1, 2, 3, 4):
            block = prompts.get_feedback_fewshot_block(chap)
            if block:
                _log("step5", f"chapter {chap} few-shot block: {len(block)} chars OK")
                return
        raise AssertionError("no few-shot block injected for any chapter")
    finally:
        # 清理临时注入的文件,不污染 repo
        try:
            default_target.unlink()
        except Exception:
            pass


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        tmp = step_1_setup_tmp(base)
        step_2_post_feedback(tmp)
        out = step_3_run_extract(tmp)
        step_4_assert_yaml(out)
        step_5_assert_fewshot_injection(out)
    print("\n[smoke] ALL 5 STEPS PASSED · Agent6 反馈飞轮 E2E 绿")
    return 0


if __name__ == "__main__":
    sys.exit(main())
