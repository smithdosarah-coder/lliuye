# -*- coding: utf-8 -*-
"""
evaluation.runner.registry — adapter 懒加载注册表

设计目标:
  - Phase A 只有 agent6_report adapter 实现, 其他 5 个在 Phase B 补齐
  - import registry 时不能因为缺某 adapter 而 fail
  - 用 @register_evaluator("<agent_id>") 装饰类自动入表
"""

from __future__ import annotations

import importlib
from typing import Callable, TypeVar

from .base_evaluator import BaseEvaluator


T = TypeVar("T", bound=BaseEvaluator)

_REGISTRY: dict[str, type[BaseEvaluator]] = {}

# 各 Agent adapter 模块路径 (懒加载, ImportError 静默)
_LAZY_MODULES = {
    "channel": "evaluation.runner.adapters.agent1_channel",
    "riskctrl": "evaluation.runner.adapters.agent2_riskctrl",
    "credit": "evaluation.runner.adapters.agent3_credit",
    "alert": "evaluation.runner.adapters.agent4_alert",
    "compliance": "evaluation.runner.adapters.agent5_compliance",
    "report": "evaluation.runner.adapters.agent6_report",
}


def register_evaluator(agent_id: str) -> Callable[[type[T]], type[T]]:
    def decorator(cls: type[T]) -> type[T]:
        if agent_id in _REGISTRY:
            # idempotent: allow re-registration on reload
            pass
        _REGISTRY[agent_id] = cls
        return cls
    return decorator


def _lazy_import(agent_id: str) -> None:
    mod_path = _LAZY_MODULES.get(agent_id)
    if not mod_path:
        return
    try:
        importlib.import_module(mod_path)
    except ImportError:
        # adapter 未实现 (Phase B 未落), 静默
        return


def get_evaluator(agent_id: str) -> BaseEvaluator:
    if agent_id not in _REGISTRY:
        _lazy_import(agent_id)
    cls = _REGISTRY.get(agent_id)
    if cls is None:
        raise NotImplementedError(
            f"Adapter for agent_id={agent_id!r} not registered. "
            f"Phase A 只实现 report; 其他 agent 待 Phase B 补 adapter."
        )
    return cls()


def list_registered() -> list[str]:
    # force lazy load of all so the caller sees current registry state
    for agent_id in _LAZY_MODULES:
        if agent_id not in _REGISTRY:
            _lazy_import(agent_id)
    return sorted(_REGISTRY.keys())
