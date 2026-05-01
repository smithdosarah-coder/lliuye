# -*- coding: utf-8 -*-
"""Phase B Sprint 2 BE10-enrich · /api/feedback admin filter + export helpers.

Scope (per WORKER-B1-SPRINT-2-SPEC-DECISIONS · 决策 1):
  - JSONL 流式扫 data/feedback/*.jsonl (不一次加载内存 · 大数据集安全)
  - 4 filter: agent_id / date_from / date_to / rating CSV / user_id
  - cursor pagination: created_at desc + id tiebreak (id = "{date}:{lineno}")
  - export zip: per-agent 1 jsonl

Auth: api_server.py 路由层套 require_user + admin role 校验
      (复用 audit_service.api._check_admin pattern · 不新建 RBAC role)。

形态硬线: feedback_admin 不写盘 · 不改 jsonl 文件 · 只读。
"""
from __future__ import annotations

import io
import json
import logging
import zipfile
from collections.abc import Generator, Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ALLOWED_AGENTS = {"channel", "credit", "alert", "compliance", "report", "riskctrl"}


def _parse_iso_date(s: str | None) -> datetime | None:
    if not s:
        return None
    # 容忍纯日期 "2026-05-01" + ISO datetime "2026-05-01T10:00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError as e:
        raise ValueError(f"invalid date '{s}' (need ISO 8601)") from e


def _parse_rating_csv(s: str | None) -> set[int] | None:
    """rating CSV: '4,5' → {4,5}; None / '' → None (no filter)."""
    if not s:
        return None
    out: set[int] = set()
    for chunk in s.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            v = int(chunk)
        except ValueError as e:
            raise ValueError(f"rating CSV must be ints: '{chunk}'") from e
        if not (1 <= v <= 5):
            raise ValueError(f"rating must be 1-5, got {v}")
        out.add(v)
    return out or None


def _iter_jsonl(
    feedback_dir: Path,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> Generator[tuple[str, int, dict[str, Any]], None, None]:
    """流式 yield (date_stem, lineno, record). 按文件名日期升序."""
    if not feedback_dir.exists():
        return
    for path in sorted(feedback_dir.glob("*.jsonl")):
        stem = path.stem
        try:
            file_date = datetime.strptime(stem, "%Y-%m-%d")
        except ValueError:
            continue
        if date_from and file_date.date() < date_from.date():
            continue
        if date_to and file_date.date() > date_to.date():
            continue
        try:
            with path.open("r", encoding="utf-8") as f:
                for lineno, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError as e:
                        logger.warning(
                            "skip malformed line %s:%d: %s", path.name, lineno, e,
                        )
                        continue
                    yield stem, lineno, rec
        except OSError as e:
            logger.warning("skip unreadable %s: %s", path, e)
            continue


def _matches_filters(
    rec: dict[str, Any],
    *,
    agent_id: str | None,
    user_id: str | None,
    ratings: set[int] | None,
) -> bool:
    if agent_id and rec.get("agent") != agent_id:
        return False
    if user_id and rec.get("user_id") != user_id:
        return False
    if ratings is not None:
        rating = rec.get("rating")
        if rating not in ratings:
            return False
    return True


def query_feedback(
    feedback_dir: Path,
    *,
    agent_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    rating: str | None = None,
    user_id: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Admin filter API · 返 {items, next_cursor, has_more}.

    cursor 编码 = "{date}:{lineno}" · 标识 last seen item · created_at desc 顺序消费。
    """
    if agent_id is not None and agent_id not in ALLOWED_AGENTS:
        raise ValueError(f"agent must be one of {sorted(ALLOWED_AGENTS)}")
    if not (1 <= int(limit) <= 200):
        raise ValueError("limit must be 1-200")

    df = _parse_iso_date(date_from)
    dt = _parse_iso_date(date_to)
    ratings = _parse_rating_csv(rating)

    # 读全集 (filter 后 sort) · jsonl 体量在 PoC 阶段几千行级 · 不需 streaming sort
    candidates: list[tuple[str, int, dict[str, Any]]] = []
    for stem, lineno, rec in _iter_jsonl(feedback_dir, date_from=df, date_to=dt):
        if _matches_filters(rec, agent_id=agent_id, user_id=user_id, ratings=ratings):
            candidates.append((stem, lineno, rec))

    # created_at desc + id (date:lineno) tiebreak desc · 同时间多条按文件靠后优先
    candidates.sort(
        key=lambda t: (t[2].get("timestamp") or t[0], t[0], t[1]),
        reverse=True,
    )

    # cursor pagination: 跳过 last seen
    start = 0
    if cursor:
        try:
            cur_date, cur_line = cursor.split(":", 1)
            cur_lineno = int(cur_line)
        except ValueError as e:
            raise ValueError(f"invalid cursor '{cursor}'") from e
        for i, (stem, lineno, _) in enumerate(candidates):
            if stem == cur_date and lineno == cur_lineno:
                start = i + 1
                break

    page = candidates[start : start + limit]
    has_more = (start + limit) < len(candidates)
    next_cursor: str | None = None
    if page:
        last = page[-1]
        next_cursor = f"{last[0]}:{last[1]}" if has_more else None

    items = []
    for stem, lineno, rec in page:
        items.append({
            "id": f"{stem}:{lineno}",
            "date": stem,
            **rec,
        })

    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": has_more,
        "page_size": len(items),
    }


def build_export_zip(
    feedback_dir: Path,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    agents: Iterable[str] | None = None,
) -> bytes:
    """打 per-agent 1 jsonl 的 zip · 返 bytes (FastAPI Response 直接写)."""
    df = _parse_iso_date(date_from)
    dt = _parse_iso_date(date_to)
    target_agents = set(agents) if agents else set(ALLOWED_AGENTS)
    bad = target_agents - ALLOWED_AGENTS
    if bad:
        raise ValueError(f"unknown agents: {sorted(bad)}")

    by_agent: dict[str, list[str]] = {a: [] for a in target_agents}
    for _stem, _ln, rec in _iter_jsonl(feedback_dir, date_from=df, date_to=dt):
        agent = rec.get("agent")
        if agent not in by_agent:
            continue
        by_agent[agent].append(json.dumps(rec, ensure_ascii=False))

    buf = io.BytesIO()
    df_label = (df.date().isoformat() if df else "all")
    dt_label = (dt.date().isoformat() if dt else "all")
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for agent, lines in by_agent.items():
            if not lines:
                continue
            zf.writestr(
                f"{agent}_{df_label}_to_{dt_label}.jsonl",
                "\n".join(lines) + "\n",
            )
    return buf.getvalue()


__all__ = [
    "ALLOWED_AGENTS",
    "build_export_zip",
    "query_feedback",
]
