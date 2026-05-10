# -*- coding: utf-8 -*-
"""候选 unique id 接入 helper · per candidate-identity-contract.md.

6 agent realtime_stream / api.py 在 emit candidate / customer / record 时,
调本模块的 wrapper 自动加 id 字段 + verify uniqueness.

设计:
- ensure_candidate_id: 单条 dict · 缺 id 时按 make_unique_id 派生
- ensure_list_unique_ids: list[dict] · 全条加 id + verify 同 list unique
- candidate_id_decorator: SSE event payload 装饰器 · 自动入 candidate.id

PM 2026-05-08 痛点真根因 fix · channel commit c074d43 推广.
"""
from __future__ import annotations

from typing import Any, Iterable

from .resolver import make_unique_id


def ensure_candidate_id(
    candidate: dict[str, Any],
    *,
    idx: int = 0,
    name_field: str = "name",
    uscc_field: str = "uscc",
    id_field: str = "id",
    strict: bool = False,
) -> dict[str, Any]:
    """单条 candidate dict · 缺 id 时按 make_unique_id 派生 · 不破坏现有 id.

    Args:
        candidate: 候选 dict (会被 in-place 改 · 也返回供链式调用)
        idx: list 中位置 · 兜底用
        name_field: 公司名所在字段 (默认 "name")
        uscc_field: USCC 所在字段 (默认 "uscc")
        id_field: id 输出字段 (默认 "id")
        strict: True 时 USCC 必过 GB 32100 校验码

    Returns: 修改后的 candidate (in-place + return)

    Raises:
        ValueError: 现有 id 字段值为空字符串 / "未获取" / "[object Object]" 等典型 regression
    """
    existing_id = candidate.get(id_field)
    if existing_id and existing_id not in {"", "未获取", "[object Object]", None, "null", "undefined"}:
        return candidate

    name = str(candidate.get(name_field, "") or "")
    uscc = str(candidate.get(uscc_field, "") or "")

    candidate[id_field] = make_unique_id(
        name=name,
        uscc=uscc,
        idx=idx,
        strict=strict,
    )
    return candidate


def ensure_list_unique_ids(
    candidates: list[dict[str, Any]],
    *,
    name_field: str = "name",
    uscc_field: str = "uscc",
    id_field: str = "id",
    strict: bool = False,
) -> list[dict[str, Any]]:
    """list[dict] 全条加 id + verify 同 list unique.

    冲突处理:
    - 同 list 内出现 2 个相同 id (e.g. 都派生到同一 name md5)
    - 后面的加 "_<idx>" 后缀 ensure unique (per candidate-identity-contract §5)
    - 不 raise (主 CLI 接受 silent 修复 · log warn 不阻断 emit)

    Args:
        candidates: list of candidate dicts (会被 in-place 改)

    Returns: 修改后的 list (in-place + return)
    """
    seen: set[str] = set()
    for idx, candidate in enumerate(candidates):
        ensure_candidate_id(
            candidate,
            idx=idx,
            name_field=name_field,
            uscc_field=uscc_field,
            id_field=id_field,
            strict=strict,
        )
        cid = candidate[id_field]
        if cid in seen:
            # 冲突 · 加 idx 后缀 ensure unique
            candidate[id_field] = f"{cid}_{idx}"
        seen.add(candidate[id_field])
    return candidates


def verify_candidate_ids(candidates: Iterable[dict[str, Any]], *, id_field: str = "id") -> list[str]:
    """验证 list 内 id 字段合规 (用于 unit test / CI guard).

    Returns: 违规说明 list · 空 list 表示全合规
    """
    violations: list[str] = []
    seen: set[str] = set()
    for idx, c in enumerate(candidates):
        cid = c.get(id_field)
        if not cid:
            violations.append(f"[{idx}] 缺 id 字段")
            continue
        if cid in {"未获取", "[object Object]", "null", "undefined"}:
            violations.append(f"[{idx}] id 是 regression 占位 ({cid!r})")
            continue
        if not isinstance(cid, str):
            violations.append(f"[{idx}] id 不是 str (got {type(cid).__name__})")
            continue
        if cid in seen:
            violations.append(f"[{idx}] id {cid!r} 重复")
            continue
        seen.add(cid)
    return violations
