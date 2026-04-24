# -*- coding: utf-8 -*-
"""§3.2 工具域冒烟测试 —— 每个 Agent 的 `domains` 子包能 import、公开 API 完整、命名符合 `<域>_<动作>`。"""

from __future__ import annotations

import importlib
import re

import pytest


AGENTS = [
    (
        "agent_channel",
        ["signal_search", "profile", "match_score", "product_recommend"],
        {"signal", "profile", "match", "product"},
    ),
    (
        "agent_credit",
        ["profile_consume", "scoring_calc", "redline_check", "case_retrieve"],
        {"profile", "scoring", "redline", "case"},
    ),
    (
        "agent_alert",
        ["external_scan", "internal_txn", "cross_match", "disposition"],
        {"external", "internal", "cross", "disposition"},
    ),
    (
        "agent_compliance",
        ["policy_parse", "business_matrix", "violation_check", "defect_classify"],
        {"policy", "business", "violation", "defect"},
    ),
    (
        "agent_riskctrl",
        ["dsl_gen", "backtest", "metrics_analyze"],
        {"dsl", "backtest", "metrics"},
    ),
]


@pytest.mark.parametrize("agent,domain_files,prefixes", AGENTS)
def test_domain_package_imports(agent: str, domain_files: list[str], prefixes: set[str]) -> None:
    pkg = importlib.import_module(f"{agent}.domains")
    all_exports = set(getattr(pkg, "__all__", []))
    assert all_exports, f"{agent}.domains.__all__ 不能为空"

    for domain in domain_files:
        module = importlib.import_module(f"{agent}.domains.{domain}")
        exported = [
            name for name in dir(module)
            if not name.startswith("_") and callable(getattr(module, name))
        ]
        assert exported, f"{agent}.domains.{domain} 未导出任何 public 符号"


@pytest.mark.parametrize("agent,domain_files,prefixes", AGENTS)
def test_domain_api_naming_convention(agent: str, domain_files: list[str], prefixes: set[str]) -> None:
    """domains/<域>.py 里的公开 def 必须以子域前缀开头（<域>_<动作>）。"""
    pkg = importlib.import_module(f"{agent}.domains")
    pattern = re.compile(r"^(" + "|".join(sorted(prefixes)) + r")_[a-z0-9_]+$")

    offenders: list[str] = []
    for name in getattr(pkg, "__all__", []):
        if not pattern.match(name):
            offenders.append(name)

    assert not offenders, (
        f"{agent}.domains 公开符号不符合 `<域>_<动作>` 命名："
        + ", ".join(offenders)
    )


def test_no_cross_domain_internal_imports() -> None:
    """domains/ 之间禁止直接 import（跨域走 agent.py 编排层）。"""
    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent
    offenders: list[str] = []
    for agent, domain_files, _ in AGENTS:
        dom_root = root / agent / "domains"
        if not dom_root.exists():
            continue
        for py in dom_root.glob("*.py"):
            if py.name == "__init__.py":
                continue
            text = py.read_text(encoding="utf-8")
            for other in domain_files:
                if other == py.stem:
                    continue
                if re.search(rf"from \.{other} import", text):
                    offenders.append(f"{py.relative_to(root)} → .{other}")

    assert not offenders, "domains 间直接 import（违反 §3.2 跨域走编排层）：\n" + "\n".join(offenders)
