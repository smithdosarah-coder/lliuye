# -*- coding: utf-8 -*-
"""ChannelSignalScannerAdapter — 包装 ``agent_channel`` 候选 enrich.

D.5 · BaseScanner 接口实装 · 让 ``shared/kb_scan/Router`` 可路由 Agent1 候选丰
富 (sse_extras.enrich_candidate · B.5 deliverable)。

Scope: ``candidate_enrich`` (or ``default``) — 接收单候选 dict · 返带
match_dimensions / radar_8axis / product_recommendations / pitch_scripts 的
HitList shape (供 Router 统一调用方消费)。

注: 这是「单候选 enrich」用法 · 不替代 ``run_channel_search_stream`` SSE 主管线。

Bug-5 (2026-04-28) · freshness filter:
  user 报 Channel "原因" 链接出现 2012 年文件 · 完全没时效性。
  在 enrich 之前 / 之后均跑 ``_filter_signals_by_freshness`` ·
  - 留 ``signal_date`` 在近 ``FRESHNESS_WINDOW_DAYS`` 内的 (默认 365)
  - ``signal_date`` 缺 → LLM staleness eval (返 fresh / stale)
  - LLM unavailable / fail → keep (不阻塞主路径)
  - 过滤后 < ``MIN_FRESH_SIGNALS`` (默认 3) 时 keep all + warn log
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from ..base import BaseScanner, ScanRequest, ScanRunResult
from ..models import (
    Evidence,
    HitItem,
    HitList,
    RiskLevel,
    ScanTarget,
)

logger = logging.getLogger(__name__)

# 时效窗口 · 12 月内视为 fresh (>1 年的历史长尾排除)
FRESHNESS_WINDOW_DAYS = 365
# 过滤后剩余信号下限 · 不足时 keep all 避空
MIN_FRESH_SIGNALS = 3
# LLM staleness eval prompt
_STALENESS_SYSTEM = (
    "你是新闻时效性评判助手。判断给定企业信号文本描述的事件是否在最近 1 年内发生。"
    "只返回 fresh 或 stale (单个英文词) · 不要任何其他文字。"
)


def _parse_signal_date(raw: str) -> datetime | None:
    """解析常见日期 string · 返 datetime 或 None.

    支持: ``YYYY-MM-DD`` / ``YYYY/MM/DD`` / ``YYYY.MM.DD`` / ``YYYY-MM`` /
    ``YYYY/MM`` / 仅 ``YYYY`` (兜底视作 1 月 1 日)。
    """
    if not raw or not isinstance(raw, str):
        return None
    raw = raw.strip()[:10]
    if len(raw) < 4:
        return None
    # 仅年份兜底 (优先判 · "2012" 不入 strptime)
    if len(raw) == 4 and raw.isdigit():
        try:
            return datetime(int(raw), 1, 1)
        except ValueError:
            return None
    if len(raw) < 7:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y-%m", "%Y/%m"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _llm_eval_freshness(signal: dict, llm_fn: Any) -> bool | None:
    """LLM 兜底判 fresh/stale · 返 True (fresh) / False (stale) / None (失败).

    llm_fn 接受 (system, user) → text · 失败抛任意异常 (吞掉返 None)。
    """
    if not callable(llm_fn):
        return None
    title = (signal.get("signal_title") or "")[:80]
    detail = (signal.get("signal_detail") or "")[:200]
    source = signal.get("signal_source") or ""
    url = signal.get("source_url") or ""
    user = (
        f"信号标题:{title}\n"
        f"信号详情:{detail}\n"
        f"来源:{source}\n"
        f"URL:{url}\n\n"
        "判 fresh (近 1 年内) 或 stale (>1 年)。"
    )
    try:
        raw = llm_fn(_STALENESS_SYSTEM, user)
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError,
            KeyError, TimeoutError, ConnectionError) as e:
        logger.warning(
            "[channel_signal.freshness] LLM eval failed · drop to keep · %s: %s",
            type(e).__name__, e,
        )
        return None
    if not isinstance(raw, str):
        return None
    v = raw.strip().lower().strip(".").strip("。").strip("`").strip()
    if v.startswith("fresh"):
        return True
    if v.startswith("stale"):
        return False
    return None


def _filter_signals_by_freshness(
    signals: list[dict],
    *,
    llm_fn: Any = None,
    now: datetime | None = None,
    window_days: int = FRESHNESS_WINDOW_DAYS,
    min_keep: int = MIN_FRESH_SIGNALS,
) -> list[dict]:
    """按时效过滤信号列表 · 返过滤后 list (永不为空 if 输入非空).

    规则:
      1. ``signal_date`` 解析成功 → 在 ``window_days`` 内留 · 老的 drop
      2. ``signal_date`` 缺 / 解析失败 → 调 ``llm_fn`` staleness eval
      3. LLM 返 None (失败 / unavailable) → keep (不阻塞)
      4. 过滤后 < ``min_keep`` · keep all + warn log

    注: 决策优先级 — 已知 stale 直接 drop · 未知态 (无 date + LLM fail) keep。
    """
    if not signals:
        return []

    now = now or datetime.now()
    cutoff = now - timedelta(days=window_days)

    fresh: list[dict] = []
    dropped_stale = 0
    for s in signals:
        date_raw = (s.get("signal_date") or "").strip()
        parsed = _parse_signal_date(date_raw)
        if parsed is not None:
            if parsed >= cutoff:
                fresh.append(s)
            else:
                dropped_stale += 1
                logger.debug(
                    "[channel_signal.freshness] drop stale signal · "
                    "date=%s url=%s", date_raw, s.get("source_url", ""),
                )
            continue
        # 无日期 → LLM eval
        verdict = _llm_eval_freshness(s, llm_fn)
        if verdict is True:
            fresh.append(s)
        elif verdict is False:
            dropped_stale += 1
            logger.debug(
                "[channel_signal.freshness] drop stale (LLM-judged) · url=%s",
                s.get("source_url", ""),
            )
        else:
            # LLM 失败 / 未配 / 返不可解析 → keep (don't block)
            fresh.append(s)

    # 兜底:过滤后 < min_keep · keep all + warn (避免空结果毁了 enrich)
    if len(fresh) < min_keep and dropped_stale > 0:
        logger.warning(
            "[channel_signal.freshness] only %d fresh signals < min_keep=%d · "
            "keep all %d (含 %d stale) · 上游需放宽 query 时效",
            len(fresh), min_keep, len(signals), dropped_stale,
        )
        return list(signals)

    return fresh


class ChannelSignalScannerAdapter(BaseScanner):
    """单候选 enrich 适配 · 把 sse_extras 输出归入 HitList shape."""

    name = "channel_signal"
    agent_key = "channel"
    cost = "free"
    supported_scopes = {"candidate_enrich", "default"}

    def health(self) -> bool:
        try:
            from agent_channel import sse_extras  # noqa: F401
        except ImportError:
            return False
        return True

    def scan(self, request: ScanRequest) -> ScanRunResult:
        try:
            from agent_channel.sse_extras import enrich_candidate
        except ImportError as e:
            return ScanRunResult(
                ok=False, scanner_name=self.name,
                error=f"channel sse_extras import failed: {e}",
            )

        # filters 期望:
        #   {"item": {...candidate dict...},  # 必填
        #    "tags": [{"category": "行业", "value": "..."}, ...],
        #    "llm": <opt LLM caller · 同 enrich_candidate 接口>,
        #    "freshness_llm": <opt 仅 freshness eval 用 callable(system,user)→str>}
        item: dict[str, Any] = request.filters.get("item") or {}
        tags = request.filters.get("tags") or []
        llm = request.filters.get("llm")
        if not item:
            return ScanRunResult(
                ok=False, scanner_name=self.name,
                error="filters.item (candidate dict) required",
            )

        # ===== Bug-5 freshness filter · enrich 前先净化 signals =====
        freshness_llm = request.filters.get("freshness_llm") or _build_default_freshness_llm()
        original_signals = list(item.get("signals") or [])
        if original_signals:
            filtered_signals = _filter_signals_by_freshness(
                original_signals, llm_fn=freshness_llm,
            )
            if len(filtered_signals) != len(original_signals):
                # 不 mutate 调用方 dict · shallow copy + 替换 signals
                item = dict(item)
                item["signals"] = filtered_signals

        try:
            extras = enrich_candidate(item, query=request.query, tags=tags, llm=llm)
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError,
                KeyError) as e:
            return ScanRunResult(
                ok=False, scanner_name=self.name,
                error=f"{type(e).__name__}: {e}",
            )

        # 单候选 → 单 HitItem
        company_name = item.get("company_name") or item.get("name") or "未知公司"
        similarity = float(extras.get("similarity") or 0.0)
        level = (
            RiskLevel.RED if similarity >= 0.7
            else RiskLevel.YELLOW if similarity >= 0.4
            else RiskLevel.GREEN
        )
        hit = HitItem(
            hit_id=f"channel_signal_{company_name[:24]}",
            rank=1,
            level=level,
            score=similarity,
            target=ScanTarget(
                target_id=company_name,
                target_type="company",
                payload={
                    "name": company_name,
                    "industry": extras.get("industry"),
                    "geo": extras.get("geo"),
                    "scale": extras.get("scale"),
                },
            ),
            reasons=[
                m.get("hit_evidence", "")
                for m in (extras.get("match_dimensions") or [])
            ],
            evidences=[
                Evidence(
                    source=src.get("source_name", "")
                    if isinstance(src, dict) else str(src),
                    snippet=str(src.get("hit_evidence", "")) if isinstance(src, dict) else "",
                    url="",
                )
                for src in (extras.get("match_dimensions") or [])[:3]
            ],
            extras={
                "radar_8axis": extras.get("radar_8axis"),
                "match_dimensions": extras.get("match_dimensions"),
                "product_recommendations": extras.get("product_recommendations"),
                "pitch_scripts": extras.get("pitch_scripts"),
                "freshness_filter": {
                    "input": len(original_signals),
                    "kept": len(item.get("signals") or []),
                    "window_days": FRESHNESS_WINDOW_DAYS,
                },
            },
        )

        hit_list = HitList(
            list_id=f"channel_signal_{company_name[:16]}",
            agent_name="channel",
            kb_summary="",
            scan_summary=f"候选 enrich · {company_name} · similarity={similarity:.2f}",
            total_scanned=1,
            hits=[hit],
        )
        hit_list.recount()

        return ScanRunResult(
            ok=True,
            scanner_name=self.name,
            hits=[hit],
            hit_list=hit_list,
            summary=hit_list.scan_summary,
        )


def _build_default_freshness_llm() -> Any:
    """构造 default freshness LLM caller · 调 ``shared.llm.router.chat_with_fallback``.

    返 callable(system, user) → str · 任何 import / 调用失败返 None (跳过 LLM eval)。
    """
    try:
        from shared.llm.router import chat_with_fallback
    except ImportError:
        return None

    def _call(system: str, user: str) -> str:
        try:
            res = chat_with_fallback(system, user, temperature=0.0)
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError,
                KeyError, TimeoutError, ConnectionError) as e:
            logger.warning(
                "[channel_signal.freshness] default LLM caller failed · %s: %s",
                type(e).__name__, e,
            )
            raise
        return res.content or ""

    return _call


__all__ = [
    "ChannelSignalScannerAdapter",
    "FRESHNESS_WINDOW_DAYS",
    "MIN_FRESH_SIGNALS",
    "_filter_signals_by_freshness",
    "_parse_signal_date",
]
