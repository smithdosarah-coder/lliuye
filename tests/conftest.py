# -*- coding: utf-8 -*-
"""Shared pytest fixtures for all `tests/*`.

Batch 2 新增:function-scope snapshot/restore of shared.sources registry +
preferences,避免 bootstrap/register 状态跨 test 泄漏(典型泄漏后果:
Agent1/5 integration 的 bootstrap 把 enterprise_info 注册进 registry,
下游 agent_credit 测试的 feature_extractor.extract() 因此真调 LLM 路径,
在 DeepSeek key 无效的环境里抛 openai.AuthenticationError 并 fail)。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 确保 repo 根在 sys.path —— 历史上 tests 子目录(如 tests/agent_channel/)
# 没有 __init__.py 时,pytest 不会自动把 repo 根插入。
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _isolate_shared_sources_state():
    """为每个 test snapshot + restore shared.sources 的全局状态。

    不触发 import 副作用:只在实际有模块加载时才 snapshot,避免拖慢无关测试。
    """
    try:
        from shared.sources import registry as registry_mod, router as router_mod
    except ImportError:
        yield
        return

    reg_snap = dict(getattr(registry_mod, "_registry", {}))
    pref_snap = {k: list(v) for k, v in router_mod.all_preferences().items()}
    try:
        yield
    finally:
        if hasattr(registry_mod, "_registry"):
            registry_mod._registry.clear()
            registry_mod._registry.update(reg_snap)
        router_mod.clear_preferences()
        for k, v in pref_snap.items():
            router_mod.register_preference(k, v)
