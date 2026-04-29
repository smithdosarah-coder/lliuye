# -*- coding: utf-8 -*-
"""ChannelSignalScannerAdapter freshness filter 单测 · Bug-5 (2026-04-28).

user 报 Channel "原因" 链接出现 2012 年文件 · 完全没时效性。
本套测试锁定 ``_filter_signals_by_freshness`` + adapter scan 入口的过滤行为。

Coverage:
  1. 5 信号 (3 fresh + 2 stale) → filter 留 3
  2. 全 stale → warning + keep all (避空) + 标 stale
  3. 缺 publish_date → LLM eval mock 路径 (fresh / stale / 无效)
  4. LLM eval timeout / fail → degrade keep all + log
  5. adapter scan 端到端 · stale signal drop · extras.freshness_filter 元数据
  6. 上游 router 入口 freshness_llm 注入

Author: Worker (Bug-5 fix · 2026-04-28)
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.kb_scan import bootstrap_scanners  # noqa: E402
from shared.kb_scan.base import ScanRequest  # noqa: E402
from shared.kb_scan.impls.channel_signal import (  # noqa: E402
    FRESHNESS_WINDOW_DAYS,
    MIN_FRESH_SIGNALS,
    ChannelSignalScannerAdapter,
    _filter_signals_by_freshness,
    _parse_signal_date,
)
from shared.kb_scan.registry import clear  # noqa: E402
from shared.kb_scan.router import ScannerRouter, clear_preferences  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures · 隔离 registry / preferences
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _isolate_kb_scan_state():
    clear()
    clear_preferences()
    yield
    clear()
    clear_preferences()


def _now() -> datetime:
    return datetime(2026, 4, 28)


def _signal(date: str, *, title: str = "中标", url: str = "https://x.test/y") -> dict:
    return {
        "signal_type": "bidding",
        "signal_title": title,
        "signal_detail": title + " 详情",
        "signal_date": date,
        "signal_source": "test_source",
        "source_url": url,
    }


# ---------------------------------------------------------------------------
# _parse_signal_date · helper sanity
# ---------------------------------------------------------------------------

def test_parse_signal_date_iso():
    assert _parse_signal_date("2026-04-15") == datetime(2026, 4, 15)


def test_parse_signal_date_slash():
    assert _parse_signal_date("2025/12/01") == datetime(2025, 12, 1)


def test_parse_signal_date_year_only():
    assert _parse_signal_date("2012") == datetime(2012, 1, 1)


def test_parse_signal_date_empty_or_invalid():
    assert _parse_signal_date("") is None
    assert _parse_signal_date(None) is None  # type: ignore[arg-type]
    assert _parse_signal_date("无") is None


# ---------------------------------------------------------------------------
# Case 1 · 3 fresh + 2 stale → filter 留 3
# ---------------------------------------------------------------------------

def test_freshness_filter_keeps_only_fresh_signals():
    """3 fresh + 2 stale (2012 / 2018) · 留 3 fresh · drop 2 stale."""
    now = _now()
    fresh_date_1 = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    fresh_date_2 = (now - timedelta(days=120)).strftime("%Y-%m-%d")
    fresh_date_3 = (now - timedelta(days=300)).strftime("%Y-%m-%d")
    signals = [
        _signal(fresh_date_1, title="近期中标 A"),
        _signal("2012-06-01", title="2012 老中标"),
        _signal(fresh_date_2, title="近期中标 B"),
        _signal("2018-08-15", title="2018 老中标"),
        _signal(fresh_date_3, title="近期中标 C"),
    ]

    result = _filter_signals_by_freshness(signals, llm_fn=None, now=now)

    assert len(result) == 3
    titles = {s["signal_title"] for s in result}
    assert titles == {"近期中标 A", "近期中标 B", "近期中标 C"}
    assert "2012 老中标" not in titles
    assert "2018 老中标" not in titles


# ---------------------------------------------------------------------------
# Case 2 · 全 stale → keep all + warning + 标 stale (避空)
# ---------------------------------------------------------------------------

def test_freshness_filter_all_stale_keeps_all_with_warning(caplog):
    """全 5 条 > 1 年老 · 过滤后 0 < min_keep · keep all + warn log."""
    signals = [
        _signal("2012-01-01", title="A 老"),
        _signal("2014-05-15", title="B 老"),
        _signal("2018-11-30", title="C 老"),
        _signal("2020-03-01", title="D 老"),
        _signal("2022-07-20", title="E 老"),
    ]

    with caplog.at_level(logging.WARNING, logger="shared.kb_scan.impls.channel_signal"):
        result = _filter_signals_by_freshness(signals, llm_fn=None, now=_now())

    # 全留 (避空)
    assert len(result) == 5
    # warning 记录
    warns = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any("only 0 fresh signals" in r.message for r in warns), (
        f"expected stale warn log · got {[r.message for r in warns]}"
    )


# ---------------------------------------------------------------------------
# Case 3 · 缺 publish_date → LLM eval 路径
# ---------------------------------------------------------------------------

def test_freshness_filter_missing_date_uses_llm_fresh_verdict():
    """无日期 · LLM 判 fresh → 留."""
    signals = [
        _signal("", title="无日期但近期"),
        _signal("2026-04-01", title="有日期 fresh"),
        _signal("", title="无日期但 LLM 判 stale"),
    ]
    # LLM stub:第一条返 fresh · 第三条返 stale (按 title 区分)
    calls: list[str] = []

    def llm_stub(system: str, user: str) -> str:
        calls.append(user)
        if "无日期但近期" in user:
            return "fresh"
        if "无日期但 LLM 判 stale" in user:
            return "stale"
        return ""

    # 加 min_keep 兜底场景:用更小 min_keep 避免触发 keep-all
    result = _filter_signals_by_freshness(
        signals, llm_fn=llm_stub, now=_now(), min_keep=1,
    )

    titles = {s["signal_title"] for s in result}
    assert "无日期但近期" in titles, "LLM 判 fresh 应保留"
    assert "有日期 fresh" in titles
    assert "无日期但 LLM 判 stale" not in titles, "LLM 判 stale 应 drop"
    # LLM 被调 2 次 (仅无日期的)
    assert len(calls) == 2


def test_freshness_filter_missing_date_llm_invalid_response_keeps():
    """LLM 返不可解析字符串 (None verdict) → keep (don't block)."""
    signals = [_signal("", title="无日期且 LLM 返乱码")]

    def llm_garbage(system: str, user: str) -> str:
        return "maybe? possibly fresh-ish"

    result = _filter_signals_by_freshness(
        signals, llm_fn=llm_garbage, now=_now(), min_keep=1,
    )
    assert len(result) == 1, "LLM 返不可解析时应 keep · 不阻塞"


# ---------------------------------------------------------------------------
# Case 4 · LLM eval 抛异常 → degrade keep all + log
# ---------------------------------------------------------------------------

def test_freshness_filter_llm_timeout_keeps_signal_with_log(caplog):
    """LLM 抛 TimeoutError → fallback keep + warn log · 不阻塞."""
    signals = [_signal("", title="LLM 超时")]

    def llm_timeout(system: str, user: str) -> str:
        raise TimeoutError("simulated llm timeout")

    with caplog.at_level(logging.WARNING, logger="shared.kb_scan.impls.channel_signal"):
        result = _filter_signals_by_freshness(
            signals, llm_fn=llm_timeout, now=_now(), min_keep=1,
        )

    assert len(result) == 1, "LLM 超时不应阻塞主路径"
    warns = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any("LLM eval failed" in r.message for r in warns), (
        f"expected LLM-fail warn · got {[r.message for r in warns]}"
    )


def test_freshness_filter_llm_runtime_error_degrades_keep():
    """LLM 抛 RuntimeError (常见 provider err) → keep · 不抛."""
    signals = [_signal("", title="provider 异常")]

    def llm_bomb(system: str, user: str) -> str:
        raise RuntimeError("provider explosion")

    result = _filter_signals_by_freshness(
        signals, llm_fn=llm_bomb, now=_now(), min_keep=1,
    )
    assert len(result) == 1


def test_freshness_filter_no_llm_keeps_undated_signals():
    """llm_fn=None · 无日期信号无法判 stale → keep (don't block)."""
    signals = [
        _signal("", title="无日期"),
        _signal("2025-12-01", title="有日期 fresh"),
    ]
    result = _filter_signals_by_freshness(
        signals, llm_fn=None, now=_now(), min_keep=1,
    )
    titles = {s["signal_title"] for s in result}
    assert titles == {"无日期", "有日期 fresh"}


# ---------------------------------------------------------------------------
# Case 5 · adapter scan 端到端 · 验 extras.freshness_filter 元数据
# ---------------------------------------------------------------------------

def test_adapter_scan_drops_stale_and_records_filter_meta():
    """adapter.scan() 路径 · 注入混合信号 · 验过滤后 enrich + extras 元数据."""
    fresh_date = (_now() - timedelta(days=10)).strftime("%Y-%m-%d")
    item = {
        "company_name": "测试精密公司",
        "signals": [
            _signal(fresh_date, title="近期中标 1500 万"),
            _signal("2012-06-01", title="2012 远古中标 · 完全没时效性"),
            _signal("2015-08-15", title="2015 老中标"),
        ],
        "qcc": {
            "industry": "精密零部件",
            "registered_address": "浙江省杭州市",
        },
        "matchTags": [],
        "recommendedProducts": [],
        "pitch": "您好",
    }
    tags = [
        {"category": "行业", "value": "精密零部件"},
        {"category": "区域", "value": "浙江"},
    ]

    adapter = ChannelSignalScannerAdapter()
    request = ScanRequest(
        scope="candidate_enrich",
        query="浙江 精密零部件",
        filters={
            "item": item,
            "tags": tags,
            "freshness_llm": None,  # 不调 LLM · 仅按日期过滤
        },
    )
    result = adapter.scan(request)

    assert result.ok, result.error
    assert result.hits, "应至少 1 条 hit"
    extras = result.hits[0].extras
    fresh_meta = extras.get("freshness_filter")
    assert fresh_meta is not None, "extras.freshness_filter 应存在"
    assert fresh_meta["input"] == 3
    # 1 fresh kept (2012 / 2015 < 365 天 cutoff · drop)
    # 但因 kept (1) < min_keep (3) → keep all 兜底
    assert fresh_meta["kept"] == 3, (
        f"fresh-only 1 < min_keep 3 → keep all 兜底 · got kept={fresh_meta['kept']}"
    )
    assert fresh_meta["window_days"] == FRESHNESS_WINDOW_DAYS


def test_adapter_scan_drops_stale_when_enough_fresh_remain():
    """fresh 信号 ≥ min_keep · stale 真 drop · kept < input."""
    now = _now()
    fresh_dates = [
        (now - timedelta(days=10)).strftime("%Y-%m-%d"),
        (now - timedelta(days=60)).strftime("%Y-%m-%d"),
        (now - timedelta(days=150)).strftime("%Y-%m-%d"),
        (now - timedelta(days=200)).strftime("%Y-%m-%d"),
    ]
    item = {
        "company_name": "测试公司 B",
        "signals": [
            _signal(fresh_dates[0], title="近期 1"),
            _signal(fresh_dates[1], title="近期 2"),
            _signal(fresh_dates[2], title="近期 3"),
            _signal(fresh_dates[3], title="近期 4"),
            _signal("2012-01-01", title="2012 老"),
            _signal("2015-05-01", title="2015 老"),
        ],
        "qcc": {"industry": "建材"},
        "matchTags": [],
        "recommendedProducts": [],
        "pitch": "",
    }

    adapter = ChannelSignalScannerAdapter()
    # 注: scan 内部用真实 datetime.now() · 这里造的"fresh"日期实际相对真实今天
    # 也都在 365 天内 (用 _now()=2026-04-28 作生成基准 · 真今天必更靠近)
    request = ScanRequest(
        scope="candidate_enrich",
        query="建材",
        filters={"item": item, "tags": [], "freshness_llm": None},
    )
    result = adapter.scan(request)
    assert result.ok
    fresh_meta = result.hits[0].extras["freshness_filter"]
    assert fresh_meta["input"] == 6
    # 4 fresh ≥ min_keep 3 · 真 drop 2 stale → kept = 4
    assert fresh_meta["kept"] == 4, (
        f"4 fresh ≥ min_keep 3 · 应 drop stale · got kept={fresh_meta['kept']}"
    )


# ---------------------------------------------------------------------------
# Case 6 · 上游 router 入口 freshness_llm 注入 (集成)
# ---------------------------------------------------------------------------

def test_router_passes_freshness_llm_through_filters():
    """bootstrap + router 路由 · freshness_llm callable 透传到 adapter."""
    bootstrap_scanners()
    calls: list[str] = []

    def llm_stub(system: str, user: str) -> str:
        calls.append(user)
        return "fresh"

    router = ScannerRouter()
    item = {
        "company_name": "路由测试公司",
        "signals": [
            _signal("", title="无日期 1"),
            _signal("", title="无日期 2"),
            _signal("", title="无日期 3"),
        ],
        "qcc": {"industry": "SaaS"},
        "matchTags": [],
        "recommendedProducts": [],
        "pitch": "",
    }
    result = router.scan(
        "agent_channel.candidate_enrich",
        ScanRequest(
            scope="candidate_enrich",
            query="SaaS",
            filters={"item": item, "tags": [], "freshness_llm": llm_stub},
        ),
    )

    assert result.ok, result.error
    # 3 个无日期 · 各调一次 LLM
    assert len(calls) == 3, (
        f"3 无日期 signal · 应触发 3 次 LLM eval · 实 {len(calls)}"
    )


# ---------------------------------------------------------------------------
# 常量 sanity (防被改坏)
# ---------------------------------------------------------------------------

def test_freshness_constants_sane_defaults():
    """FRESHNESS_WINDOW_DAYS / MIN_FRESH_SIGNALS 保持业务约定."""
    assert FRESHNESS_WINDOW_DAYS == 365
    assert MIN_FRESH_SIGNALS == 3
