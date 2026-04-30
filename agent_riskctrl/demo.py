# -*- coding: utf-8 -*-
"""agent_riskctrl.demo — 纯 mock SSE 演示流 · Phase A worker-A4 · 2026-04-29.

物理隔离 endpoint · 不复用 api.py 的 _dsl_gen_stream / _backtest_stream ·
避免 prod 路径被误改污染 · prod fail 时不 silent fallback (live-fallback-banner-spec
§1.5 + reset 工程反 5 原则 §3.5 环境边界).

Scenarios (反 5 原则 §3.5 难度分层 · 与 web/src/lib/mock/agent-riskctrl-sessions.ts 1:1):
  · credit_v15  · 新客户首贷 v1.5    · KS 0.42 (绿区 · 简单)
  · aml_kyc     · AML/KYC v2.3       · KS 0.31 (关注 · 中等)
  · fraud_high  · 欺诈拦截 v0.7      · KS 0.28 (红区 · 极端)

Fixtures: data/mock/workspace/riskctrl/scenarios/*.json (3 文件).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCENARIO_DIR = PROJECT_ROOT / "data" / "mock" / "workspace" / "riskctrl" / "scenarios"

VALID_SCENARIOS: tuple[str, ...] = ("credit_v15", "aml_kyc", "fraud_high")


def list_scenarios() -> list[dict[str, str]]:
    """枚举可用 scenario · 给前端 dropdown 用 (label 取 fixture json 的 .label).

    Falls back to id 如 fixture 缺 label 字段.
    """
    items: list[dict[str, str]] = []
    if not SCENARIO_DIR.exists():
        return items
    for sid in VALID_SCENARIOS:
        path = SCENARIO_DIR / f"{sid}.json"
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text("utf-8"))
            label = str(data.get("label", sid))
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            label = sid
        items.append({"key": sid, "label": label})
    return items


def load_scenario(scenario_id: str) -> dict[str, Any]:
    """加载单 scenario fixture · 抛 FileNotFoundError / json.JSONDecodeError 由 caller catch."""
    path = SCENARIO_DIR / f"{scenario_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"scenario fixture not found: {path}")
    return json.loads(path.read_text("utf-8"))
