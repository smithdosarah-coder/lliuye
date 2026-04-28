# -*- coding: utf-8 -*-
"""Alert rules engine (Stage E.2 · onboarding W-E2-A3).

按 onboarding · 3 核心规则 (rules.yaml 含):
- llm_provider_down (LLM 5min 0 success)
- high_error_rate (5xx > 5% in 5min)
- tavily_401_burst (10 fail in 1min)

设计:
- rules.yaml 是 Prometheus AlertManager 兼容格式 · 方便 production 直接喂
- 本模块同时实现简化版本地 evaluate() · cron / external monitor 调
- 不强制 prometheus_client / yaml dep · 失败 NoOp

Usage:
    from monitoring_service.alerts import load_rules, AlertRule
    rules = load_rules()
    for rule in rules:
        if rule.name == "llm_provider_down":
            ...
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = Path(__file__).resolve().parent / "rules.yaml"


# ---------------------------------------------------------------------------
# Data shape
# ---------------------------------------------------------------------------


@dataclass
class AlertRule:
    """单条 alert rule · Prometheus AlertManager 兼容字段子集."""

    name: str
    group: str
    expr: str
    for_window: str = "5m"
    severity: str = "warning"
    component: str = ""
    summary: str = ""
    description: str = ""
    runbook: str = ""
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)


@dataclass
class AlertEvaluation:
    """evaluate() 返回 · 表示某 rule 在当前样本上的结果."""

    rule_name: str
    fired: bool
    value: float
    threshold: float
    reason: str = ""


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def _try_load_yaml(path: Path) -> Optional[dict[str, Any]]:
    """尝试用 PyYAML 加载 · 失败返 None 让 caller fallback."""
    try:
        import yaml  # type: ignore[import]
    except ImportError:
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, RuntimeError):
        return None


def _bare_yaml_parse(text: str) -> Optional[dict[str, Any]]:
    """fallback yaml parser · 仅支持本 rules.yaml 的简单 structure ·
    不通用 · production 应装 PyYAML.

    解析的 minimum schema 已 hardcode 在文件 (groups → rules) · 失败返 None."""
    # 仅最简兜底 · 解析失败时返 hardcoded fallback rules
    return None


def _hardcoded_fallback_groups() -> list[dict[str, Any]]:
    """Last-resort hardcoded rules · 与 rules.yaml 内容一致 · 防 yaml/pyyaml 都缺."""
    return [
        {
            "name": "llm_provider_health",
            "rules": [{
                "alert": "llm_provider_down",
                "expr": ('sum(rate(llm_calls_total{provider="deepseek"}[5m])) '
                         '- sum(rate(llm_errors_total{provider="deepseek"}[5m])) == 0'),
                "for": "5m",
                "labels": {"severity": "critical", "component": "llm"},
                "annotations": {
                    "summary": "DeepSeek LLM 5 分钟 0 成功调用",
                    "description": "近 5 分钟所有 DeepSeek 调用失败 · 检查 API key / 服务状态",
                    "runbook": "docs/ops/runbook-llm-down.md",
                },
            }],
        },
        {
            "name": "http_error_rate",
            "rules": [{
                "alert": "high_error_rate",
                "expr": ('sum(rate(http_requests_total{status=~"5.."}[5m])) '
                         '/ sum(rate(http_requests_total[5m])) > 0.05'),
                "for": "5m",
                "labels": {"severity": "critical", "component": "api"},
                "annotations": {
                    "summary": "HTTP 5xx 错误率 > 5% (5min 窗口)",
                    "description": "近 5 分钟 5xx 比例超 5% · 检查 traceback / Sentry 看根因",
                    "runbook": "docs/ops/runbook-5xx-burst.md",
                },
            }],
        },
        {
            "name": "external_provider_health",
            "rules": [{
                "alert": "tavily_401_burst",
                "expr": ('increase(llm_errors_total{provider="tavily", error_type="401"}[1m]) > 10'),
                "for": "1m",
                "labels": {"severity": "warning", "component": "external_api"},
                "annotations": {
                    "summary": "Tavily 401 1 分钟内 > 10 次",
                    "description": "Tavily key 可能失效 / 配额耗尽",
                    "runbook": "docs/ops/runbook-tavily-401.md",
                },
            }],
        },
        {
            "name": "ws_connection_health",
            "rules": [{
                "alert": "im_ws_connections_drop",
                "expr": "im_ws_connections_active < 1",
                "for": "5m",
                "labels": {"severity": "warning", "component": "im"},
                "annotations": {
                    "summary": "IM WebSocket 5 分钟 0 活跃连接",
                    "description": "可能 WS handler 崩 / nginx 阻 ws upgrade",
                    "runbook": "docs/ops/runbook-ws-drop.md",
                },
            }],
        },
    ]


def load_rules(path: Optional[Path] = None) -> list[AlertRule]:
    """加载 rules.yaml · pyyaml 不可用时回退 hardcoded · 始终返 ≥4 rules."""
    p = path or RULES_PATH
    raw = _try_load_yaml(p) if p.exists() else None
    if not raw or not isinstance(raw, dict):
        groups = _hardcoded_fallback_groups()
    else:
        groups = raw.get("groups") or []

    out: list[AlertRule] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        gname = str(group.get("name", "default"))
        for r in (group.get("rules") or []):
            if not isinstance(r, dict):
                continue
            name = str(r.get("alert") or r.get("name") or "")
            if not name:
                continue
            labels = dict(r.get("labels") or {})
            annotations = dict(r.get("annotations") or {})
            out.append(AlertRule(
                name=name,
                group=gname,
                expr=str(r.get("expr", "")),
                for_window=str(r.get("for", "5m")),
                severity=str(labels.get("severity", "warning")),
                component=str(labels.get("component", "")),
                summary=str(annotations.get("summary", "")),
                description=str(annotations.get("description", "")),
                runbook=str(annotations.get("runbook", "")),
                labels=labels,
                annotations=annotations,
            ))
    return out


# ---------------------------------------------------------------------------
# Local evaluate · 简化版 · 接受 sample dict 不调真 Prometheus
# ---------------------------------------------------------------------------


def evaluate(rule: AlertRule, samples: dict[str, float]) -> AlertEvaluation:
    """简化版 rule eval · 只支持核心 3 规则 + ws_drop · 复杂 PromQL 留 production AlertManager.

    samples 字典 keys (per onboarding):
        llm_success_5m       · LLM 5min 成功调用数
        llm_error_5m         · LLM 5min 失败数
        http_5xx_rate_5m     · 5xx 比率 (0.0-1.0)
        tavily_401_1m        · Tavily 401 1min 计数
        im_ws_active         · 当前活跃 WebSocket 连接数
    """
    name = rule.name
    if name == "llm_provider_down":
        success = float(samples.get("llm_success_5m", 0))
        return AlertEvaluation(
            rule_name=name, fired=success == 0, value=success, threshold=0,
            reason=f"llm_success_5m={success} · should be > 0",
        )
    if name == "high_error_rate":
        rate = float(samples.get("http_5xx_rate_5m", 0))
        return AlertEvaluation(
            rule_name=name, fired=rate > 0.05, value=rate, threshold=0.05,
            reason=f"http_5xx_rate_5m={rate:.4f} · threshold=0.05",
        )
    if name == "tavily_401_burst":
        count = float(samples.get("tavily_401_1m", 0))
        return AlertEvaluation(
            rule_name=name, fired=count > 10, value=count, threshold=10,
            reason=f"tavily_401_1m={count} · threshold=10",
        )
    if name == "im_ws_connections_drop":
        active = float(samples.get("im_ws_active", 0))
        return AlertEvaluation(
            rule_name=name, fired=active < 1, value=active, threshold=1,
            reason=f"im_ws_active={active} · should be ≥ 1",
        )
    # Unknown rule · 不报错 · 返 not-fired
    return AlertEvaluation(
        rule_name=name, fired=False, value=0, threshold=0,
        reason="rule has no local evaluator (production AlertManager only)",
    )


def evaluate_all(samples: dict[str, float],
                 rules: Optional[list[AlertRule]] = None) -> list[AlertEvaluation]:
    """对所有 rules 跑 evaluate · 用于 cron / health 综合上报."""
    actual_rules = rules if rules is not None else load_rules()
    return [evaluate(r, samples) for r in actual_rules]


def fired_alerts(samples: dict[str, float],
                 rules: Optional[list[AlertRule]] = None) -> list[AlertEvaluation]:
    """仅返 fired=True 的 alerts."""
    return [e for e in evaluate_all(samples, rules) if e.fired]


def to_alertmanager_payload(evaluations: list[AlertEvaluation],
                            rules: list[AlertRule]) -> list[dict[str, Any]]:
    """转 alerts 为 Prometheus Alertmanager-compatible payload (POST 用)."""
    rule_by_name = {r.name: r for r in rules}
    out = []
    for ev in evaluations:
        if not ev.fired:
            continue
        rule = rule_by_name.get(ev.rule_name)
        if rule is None:
            continue
        out.append({
            "labels": {**rule.labels, "alertname": rule.name},
            "annotations": {
                **rule.annotations,
                "value": str(ev.value),
                "threshold": str(ev.threshold),
                "reason": ev.reason,
            },
        })
    return out


# ---------------------------------------------------------------------------
# Persistence · last fired alerts 写盘 · 让外部 monitor 可拉
# ---------------------------------------------------------------------------


ALERTS_FIRED_PATH = PROJECT_ROOT / "data" / "monitoring" / "fired_alerts.json"


def persist_fired_alerts(evaluations: list[AlertEvaluation]) -> Path:
    """落盘 fired alerts · 给外部 cron 抓."""
    ALERTS_FIRED_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fired": [
            {
                "rule_name": e.rule_name,
                "value": e.value,
                "threshold": e.threshold,
                "reason": e.reason,
            }
            for e in evaluations if e.fired
        ],
    }
    ALERTS_FIRED_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    return ALERTS_FIRED_PATH
