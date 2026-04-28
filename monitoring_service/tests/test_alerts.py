# -*- coding: utf-8 -*-
"""Pytest for monitoring_service.alerts · load + evaluate + persist."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from monitoring_service import alerts


def test_load_rules_returns_4_rules():
    rules = alerts.load_rules()
    names = {r.name for r in rules}
    expected = {
        "llm_provider_down",
        "high_error_rate",
        "tavily_401_burst",
        "im_ws_connections_drop",
    }
    assert expected.issubset(names), f"missing rules: {expected - names}"


def test_load_rules_fallback_when_yaml_missing(tmp_path, monkeypatch):
    """rules.yaml 不在时 · 走 hardcoded fallback."""
    monkeypatch.setattr(alerts, "RULES_PATH", tmp_path / "no_such.yaml")
    rules = alerts.load_rules()
    assert len(rules) >= 4


def test_evaluate_llm_provider_down_fires():
    rules = alerts.load_rules()
    rule = next(r for r in rules if r.name == "llm_provider_down")
    ev = alerts.evaluate(rule, {"llm_success_5m": 0})
    assert ev.fired is True
    assert ev.value == 0


def test_evaluate_llm_provider_down_not_fired():
    rules = alerts.load_rules()
    rule = next(r for r in rules if r.name == "llm_provider_down")
    ev = alerts.evaluate(rule, {"llm_success_5m": 5})
    assert ev.fired is False


def test_evaluate_high_error_rate():
    rules = alerts.load_rules()
    rule = next(r for r in rules if r.name == "high_error_rate")
    ev_fire = alerts.evaluate(rule, {"http_5xx_rate_5m": 0.10})
    ev_ok = alerts.evaluate(rule, {"http_5xx_rate_5m": 0.02})
    assert ev_fire.fired is True
    assert ev_ok.fired is False


def test_evaluate_tavily_401_burst():
    rules = alerts.load_rules()
    rule = next(r for r in rules if r.name == "tavily_401_burst")
    ev_fire = alerts.evaluate(rule, {"tavily_401_1m": 15})
    ev_ok = alerts.evaluate(rule, {"tavily_401_1m": 5})
    assert ev_fire.fired is True
    assert ev_ok.fired is False


def test_evaluate_unknown_rule_does_not_throw():
    """未知 rule (无 local evaluator) · 返 not-fired · 不报错."""
    rule = alerts.AlertRule(name="custom_unknown", group="test", expr="x > 1")
    ev = alerts.evaluate(rule, {"x": 100})
    assert ev.fired is False
    assert "no local evaluator" in (ev.reason or "").lower()


def test_evaluate_all_returns_per_rule():
    samples = {
        "llm_success_5m": 0,            # fires llm_provider_down
        "http_5xx_rate_5m": 0.10,       # fires high_error_rate
        "tavily_401_1m": 5,             # safe
        "im_ws_active": 3,              # safe
    }
    evals = alerts.evaluate_all(samples)
    assert len(evals) >= 4
    fired = [e for e in evals if e.fired]
    fired_names = {e.rule_name for e in fired}
    assert "llm_provider_down" in fired_names
    assert "high_error_rate" in fired_names


def test_fired_alerts_filters_correctly():
    samples = {"llm_success_5m": 5, "http_5xx_rate_5m": 0.01,
               "tavily_401_1m": 50, "im_ws_active": 5}
    fired = alerts.fired_alerts(samples)
    names = {f.rule_name for f in fired}
    assert "tavily_401_burst" in names
    assert "llm_provider_down" not in names


def test_to_alertmanager_payload_includes_labels():
    rules = alerts.load_rules()
    samples = {"llm_success_5m": 0}
    evals = alerts.evaluate_all(samples, rules)
    payload = alerts.to_alertmanager_payload(evals, rules)
    assert any("alertname" in p["labels"] for p in payload)


def test_persist_fired_alerts_writes_json(tmp_path, monkeypatch):
    target = tmp_path / "monitoring" / "fired_alerts.json"
    monkeypatch.setattr(alerts, "ALERTS_FIRED_PATH", target)

    samples = {"llm_success_5m": 0, "http_5xx_rate_5m": 0.0,
               "tavily_401_1m": 0, "im_ws_active": 5}
    evals = alerts.evaluate_all(samples)
    written = alerts.persist_fired_alerts(evals)
    assert written.is_file()
    body = json.loads(target.read_text(encoding="utf-8"))
    assert "fired" in body
    fired_names = {f["rule_name"] for f in body["fired"]}
    assert "llm_provider_down" in fired_names
