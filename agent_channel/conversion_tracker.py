# -*- coding: utf-8 -*-
"""Agent1 候选 → 转化追踪 — Phase B Sprint 3 BE1 Step 4 (2026-05-05).

per CLAUDE.md §6 数据飞轮 第 3 环 (动态经验 · `data/feedback/`):
- 与 `/api/feedback` (Agent6 audit modify · per worker-B1 BE10) 业务隔离
- 本模块只追踪 Agent1 候选 → 实际成单 conversion 链路
- jsonl 写入路径: `data/feedback/<RM>/<candidate_id>.jsonl` (per onboarding · BE1 Step 4)

stage 枚举 (RM 决策候选后的真实成单进度):
- contacted  · RM 已联系
- quoted     · 已发报价 / 授信意向
- approved   · 授信通过 (Agent3 接 handoff 后)
- won        · 真成单 (放款落地)
- lost       · 客户流失 / 拒贷
- on_hold    · 暂搁置

per Q-052 #2 永不 multi-tenant + 银行客户全本地化部署 · jsonl 走本地文件.
per CLAUDE.md §3.7.5 · subject_id (即 candidate_id) 是 hash · 不存 plain PII.
"""
from __future__ import annotations

import datetime
import json
import re
from pathlib import Path
from typing import Any, Literal, TypedDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_FEEDBACK_ROOT = PROJECT_ROOT / "data" / "feedback"

# RM ID 命名约束 · 防 path traversal · 仅允许 [A-Za-z0-9_-]
_RM_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
# candidate_id 同样约束 · UUID v4 / hash prefix 都 OK
_CAND_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")

ConversionStage = Literal[
    "contacted", "quoted", "approved", "won", "lost", "on_hold",
]
_VALID_STAGES: frozenset[str] = frozenset({
    "contacted", "quoted", "approved", "won", "lost", "on_hold",
})


class ConversionEvent(TypedDict, total=False):
    """单条 conversion event jsonl 记录."""

    candidate_id:   str                      # 候选企业 ID
    rm_id:          str                      # RM (客户经理) ID
    stage:          ConversionStage          # 当前 stage
    timestamp:      str                      # ISO 时间戳
    notes:          str                      # 备注 · ≤ 500 char
    amount_yuan:    int                      # 实际放款金额 (won stage 必填)
    next_action:    str                      # 下一步动作 (≤ 100 char)
    metadata:       dict[str, Any]           # 附加信息 (如 product_sku / 沟通渠道)


class ConversionValidationError(ValueError):
    """conversion event 校验失败."""


def _validate(event: dict[str, Any]) -> None:
    """校验 ConversionEvent · 不通过抛 ConversionValidationError."""
    candidate_id = event.get("candidate_id")
    rm_id = event.get("rm_id")
    stage = event.get("stage")
    if not candidate_id or not _CAND_ID_RE.match(str(candidate_id)):
        raise ConversionValidationError(
            f"candidate_id invalid: {candidate_id!r} · 必须 [A-Za-z0-9_-]+",
        )
    if not rm_id or not _RM_ID_RE.match(str(rm_id)):
        raise ConversionValidationError(
            f"rm_id invalid: {rm_id!r} · 必须 [A-Za-z0-9_-]+",
        )
    if stage not in _VALID_STAGES:
        raise ConversionValidationError(
            f"stage invalid: {stage!r} · 必须 ∈ {sorted(_VALID_STAGES)}",
        )
    if stage == "won":
        amount = event.get("amount_yuan")
        if not amount or not isinstance(amount, int) or amount <= 0:
            raise ConversionValidationError(
                "won stage 必须含 amount_yuan > 0 (实际放款金额)",
            )


def record_conversion(event: dict[str, Any]) -> dict[str, Any]:
    """落 conversion event 到 data/feedback/<rm_id>/<candidate_id>.jsonl.

    Args:
        event: 含 candidate_id / rm_id / stage 三个必填字段 · 其他字段可选.

    Returns:
        {"path": "<relative_path>", "rm_id": ..., "candidate_id": ..., "stage": ..., "timestamp": ...}

    Raises:
        ConversionValidationError: 校验失败.
        OSError: 文件 IO 失败.

    per Q-052 #2 永不 multi-tenant · 客户全本地化部署 · jsonl 走本地.
    """
    _validate(event)

    candidate_id = str(event["candidate_id"])
    rm_id = str(event["rm_id"])
    stage = str(event["stage"])

    # auto-fill timestamp (UTC ISO)
    ts = event.get("timestamp")
    if not ts:
        ts = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"

    record: ConversionEvent = {
        "candidate_id": candidate_id,
        "rm_id":        rm_id,
        "stage":        stage,  # type: ignore[typeddict-item]
        "timestamp":    str(ts),
    }
    # 透传可选字段
    for opt in ("notes", "amount_yuan", "next_action", "metadata"):
        if event.get(opt) is not None:
            record[opt] = event[opt]  # type: ignore[literal-required]

    rm_dir = _FEEDBACK_ROOT / rm_id
    rm_dir.mkdir(parents=True, exist_ok=True)
    out_path = rm_dir / f"{candidate_id}.jsonl"
    line = json.dumps(record, ensure_ascii=False)
    with out_path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")

    # Path 跨盘符 (临时目录 / 测试) 时 relative_to 抛 ValueError · fallback 绝对 posix
    try:
        rel = out_path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        rel = out_path.as_posix()
    return {
        "path":         rel,
        "rm_id":        rm_id,
        "candidate_id": candidate_id,
        "stage":        stage,
        "timestamp":    ts,
    }


def list_conversions(rm_id: str, candidate_id: str) -> list[ConversionEvent]:
    """读单候选的 conversion 链 · 按 jsonl 行序 (插入序).

    Returns:
        list of ConversionEvent · 文件不存在或空返 [].
        invalid line silent skip · 不抛.
    """
    if not _RM_ID_RE.match(rm_id) or not _CAND_ID_RE.match(candidate_id):
        return []
    path = _FEEDBACK_ROOT / rm_id / f"{candidate_id}.jsonl"
    if not path.exists():
        return []
    out: list[ConversionEvent] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except (json.JSONDecodeError, ValueError):
                    continue
    except OSError:
        return []
    return out
