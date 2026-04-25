"""Agent1 · 数据飞轮 E2E smoke（第 3 + 4 环）。

流程：
    1. 初始 JSONL 行数 / prompts.py 哈希快照
    2. POST /api/feedback（in-process TestClient）— agent=channel payload
    3. 验证当日 JSONL 行数 +1
    4. 跑 scripts/extract_feedback_fewshots.py（程序调用）
    5. 验证 prompts.py sentinel 块内容变化、PITCH_FEWSHOT_EXAMPLES 含新样本

用法：
    py scripts/feedback_smoke.py
    # exit 0 = PASS, exit 1 = FAIL

注意：
- TestClient 直接打 api_server.app，不起 uvicorn、不占端口
- smoke 后不 rollback prompts.py — 由 commit 层面控制（git diff 能看到）
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from api_server import app  # noqa: E402
from scripts.extract_feedback_fewshots import extract_and_inject  # noqa: E402


PROMPTS_PATH = PROJECT_ROOT / "agent_channel" / "prompts.py"
FEEDBACK_DIR = PROJECT_ROOT / "data" / "feedback"

PAYLOAD = {
    "agent": "channel",
    "session_id": "smoke-e2e-20260419",
    "original_output": {
        "pitch": "您好，我们银行有贷款产品，利率很低，可以了解一下。",
    },
    "user_correction": {
        "pitch": (
            "王总您好，注意到贵司刚拿了专精特新，我行配套科创贷最高 3000 万、"
            "LPR 减点 30bp，这两周新批的客户平均 5 个工作日放款。"
            "想请教您近期研发资金节奏？"
        ),
    },
    "correction_reason": "原话术客套冗长、无具体产品、无数字锚点、无政策切入点",
    "user_id": None,
}


def _count_lines(p: Path) -> int:
    if not p.exists():
        return 0
    return sum(1 for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip())


def _hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def main() -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    jsonl_path = FEEDBACK_DIR / f"{today}.jsonl"

    # Step 1: baseline snapshot
    pre_lines = _count_lines(jsonl_path)
    pre_hash = _hash(PROMPTS_PATH)
    print(f"[smoke] pre: jsonl_lines={pre_lines} prompts_hash={pre_hash}")

    # Step 2: POST /api/feedback
    with TestClient(app) as client:
        resp = client.post("/api/feedback", json=PAYLOAD)
    if resp.status_code != 200:
        print(f"[smoke] FAIL: POST /api/feedback → {resp.status_code} {resp.text}")
        return 1
    print(f"[smoke] POST ok: {resp.json()}")

    # Step 3: verify JSONL +1
    post_lines = _count_lines(jsonl_path)
    if post_lines != pre_lines + 1:
        print(f"[smoke] FAIL: jsonl lines expected {pre_lines + 1}, got {post_lines}")
        return 1
    print(f"[smoke] jsonl +1 ok: {jsonl_path.name} = {post_lines} lines")

    # Step 4: extract + inject
    summary = extract_and_inject(agent_id="channel", max_n=3)
    print(f"[smoke] extract summary: {json.dumps(summary, ensure_ascii=False)}")

    # Step 5: verify prompts.py changed and contains new good pitch snippet
    post_hash = _hash(PROMPTS_PATH)
    content = PROMPTS_PATH.read_text(encoding="utf-8")
    expected_marker = "LPR 减点 30bp"
    if pre_hash == post_hash:
        print(f"[smoke] FAIL: prompts.py unchanged (hash={post_hash})")
        return 1
    if expected_marker not in content:
        print(f"[smoke] FAIL: expected marker {expected_marker!r} not in prompts.py")
        return 1
    print(f"[smoke] prompts.py changed: {pre_hash} → {post_hash}")
    print(f"[smoke] marker {expected_marker!r} present in sentinel block")

    print("[smoke] PASS: feedback E2E loop intact (POST → JSONL → extract → prompts.py)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
