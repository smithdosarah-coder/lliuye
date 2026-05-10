# -*- coding: utf-8 -*-
"""SourceHealth · 数据源健康检查 component."""
from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SourceRegistration:
    """source 注册元信息 · 启动时填一次."""

    source_id: str           # e.g. "tavily" / "gsxt" / "pbc_cn"
    tier: int                # 1-4 (per shared.data_tiers)
    sla_p99_ms: int          # SLA 目标 · p99 latency 上限
    auth_method: str         # "api_key" / "cookie" / "none" / "internal"
    auth_expiry: Optional[float] = None  # epoch · None = 永不过期
    description: str = ""


@dataclass
class _CallRecord:
    ts: float
    latency_ms: float
    success: bool
    error_code: str = ""


@dataclass
class HealthReport:
    """check(source_id) 返此报告."""

    source_id: str
    healthy: bool          # 综合 · True iff 满足所有阈值
    score: float           # 0-100 综合分
    last_call_ts: Optional[float]
    seconds_since_last_call: Optional[float]
    total_calls_24h: int
    success_rate_24h: float  # 0.0-1.0
    p50_latency_ms: Optional[float]
    p99_latency_ms: Optional[float]
    sla_p99_target_ms: int
    sla_p99_breached: bool
    auth_status: str       # "ok" / "expired" / "missing"
    tier: int
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "healthy": self.healthy,
            "score": round(self.score, 2),
            "last_call_ts": self.last_call_ts,
            "seconds_since_last_call": self.seconds_since_last_call,
            "total_calls_24h": self.total_calls_24h,
            "success_rate_24h": round(self.success_rate_24h, 4),
            "p50_latency_ms": round(self.p50_latency_ms, 2) if self.p50_latency_ms else None,
            "p99_latency_ms": round(self.p99_latency_ms, 2) if self.p99_latency_ms else None,
            "sla_p99_target_ms": self.sla_p99_target_ms,
            "sla_p99_breached": self.sla_p99_breached,
            "auth_status": self.auth_status,
            "tier": self.tier,
            "notes": list(self.notes),
        }


class SourceHealth:
    """6 agent 共享数据源健康检查.

    Usage:

        health = default_health()

        # 启动时注册
        health.register(SourceRegistration(
            source_id="tavily",
            tier=4,
            sla_p99_ms=3000,
            auth_method="api_key",
            description="Tavily 公开 web 搜索",
        ))

        # 各 agent 调用 source 后 record
        try:
            t0 = time.time()
            result = tavily.search(...)
            health.record_call("tavily", latency_ms=(time.time()-t0)*1000, success=True)
        except Exception as e:
            health.record_call("tavily", latency_ms=0, success=False, error_code=type(e).__name__)

        # 主 CLI dashboard
        report = health.check("tavily")
        all_reports = health.check_all()
    """

    HEALTH_WINDOW_SECONDS = 24 * 3600  # 24h
    MIN_SUCCESS_RATE = 0.9              # < 90% 即不健康
    STALE_THRESHOLD_SECONDS = 6 * 3600  # > 6h 没调用 · 警告
    MAX_CALL_RECORDS = 1000             # per source · 防内存涨

    def __init__(self) -> None:
        self._registrations: dict[str, SourceRegistration] = {}
        self._calls: dict[str, list[_CallRecord]] = {}

    def register(self, reg: SourceRegistration) -> None:
        """启动时注册 source · 重复 register 覆盖 (允许配置 reload)."""
        if not reg.source_id or reg.tier not in (1, 2, 3, 4):
            raise ValueError(f"invalid registration: {reg}")
        self._registrations[reg.source_id] = reg
        self._calls.setdefault(reg.source_id, [])

    def record_call(
        self,
        source_id: str,
        *,
        latency_ms: float,
        success: bool,
        error_code: str = "",
    ) -> None:
        """每次 source 调用后 record · silent skip 未注册 source."""
        if source_id not in self._registrations:
            return  # silent · 不破上游业务 flow
        records = self._calls.setdefault(source_id, [])
        records.append(_CallRecord(
            ts=time.time(),
            latency_ms=max(0.0, latency_ms),
            success=success,
            error_code=error_code,
        ))
        # 超过 MAX 时切尾 (FIFO)
        if len(records) > self.MAX_CALL_RECORDS:
            self._calls[source_id] = records[-self.MAX_CALL_RECORDS:]

    def check(self, source_id: str) -> HealthReport:
        """实时 health 报告."""
        reg = self._registrations.get(source_id)
        if reg is None:
            raise KeyError(f"source {source_id!r} 未注册")

        now = time.time()
        all_calls = self._calls.get(source_id, [])
        # 24h 窗口内的 call
        recent = [c for c in all_calls if now - c.ts < self.HEALTH_WINDOW_SECONDS]

        last_call_ts = all_calls[-1].ts if all_calls else None
        seconds_since = (now - last_call_ts) if last_call_ts else None

        total = len(recent)
        success_count = sum(1 for c in recent if c.success)
        success_rate = success_count / total if total else 1.0  # 0 call 视作 1.0 (没出错过)

        latencies = [c.latency_ms for c in recent if c.success]
        p50 = statistics.median(latencies) if latencies else None
        p99 = (
            statistics.quantiles(latencies, n=100)[98]
            if len(latencies) >= 100
            else (max(latencies) if latencies else None)
        )

        sla_breached = bool(p99 and p99 > reg.sla_p99_ms)
        auth_status = self._auth_status(reg, now)

        notes: list[str] = []
        if seconds_since and seconds_since > self.STALE_THRESHOLD_SECONDS:
            notes.append(f"已 {int(seconds_since/3600)}h 未被调用 · 可能僵死")
        if total > 0 and success_rate < self.MIN_SUCCESS_RATE:
            notes.append(f"24h 成功率 {success_rate:.1%} < 90% · 不健康")
        if sla_breached:
            notes.append(f"p99 延迟 {p99:.0f}ms > SLA {reg.sla_p99_ms}ms")
        if auth_status != "ok":
            notes.append(f"认证状态 {auth_status}")

        # 综合分 0-100
        score = 100.0
        if total > 0:
            score *= success_rate
        if sla_breached:
            score *= 0.7
        if auth_status != "ok":
            score *= 0.5
        if seconds_since and seconds_since > self.STALE_THRESHOLD_SECONDS:
            score *= 0.8

        healthy = (
            success_rate >= self.MIN_SUCCESS_RATE
            and not sla_breached
            and auth_status == "ok"
        )

        return HealthReport(
            source_id=source_id,
            healthy=healthy,
            score=score,
            last_call_ts=last_call_ts,
            seconds_since_last_call=seconds_since,
            total_calls_24h=total,
            success_rate_24h=success_rate,
            p50_latency_ms=p50,
            p99_latency_ms=p99,
            sla_p99_target_ms=reg.sla_p99_ms,
            sla_p99_breached=sla_breached,
            auth_status=auth_status,
            tier=reg.tier,
            notes=notes,
        )

    def check_all(self) -> dict[str, HealthReport]:
        """全部已注册 source 的 health 报告 · 主 CLI dashboard 用."""
        return {sid: self.check(sid) for sid in self._registrations}

    def list_unhealthy(self) -> list[str]:
        """快查 unhealthy source id list (CI / monitor 用)."""
        return [sid for sid, rpt in self.check_all().items() if not rpt.healthy]

    def list_registered(self) -> list[str]:
        return list(self._registrations.keys())

    @staticmethod
    def _auth_status(reg: SourceRegistration, now: float) -> str:
        if reg.auth_method == "none" or reg.auth_method == "internal":
            return "ok"
        if reg.auth_expiry is None:
            return "ok"
        if now >= reg.auth_expiry:
            return "expired"
        return "ok"


_DEFAULT: SourceHealth | None = None


def default_health() -> SourceHealth:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = SourceHealth()
    return _DEFAULT
