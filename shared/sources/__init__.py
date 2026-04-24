# -*- coding: utf-8 -*-
"""Tiered Data Sources 架构入口。

调用 bootstrap() 一次性完成：
  1. 注册所有具体源（tavily / akshare / gov_cn / pbc_gov / flk_npc）
  2. 加载各 agent 的源偏好链（agent_*/sources_config.init()）

默认**不自动启用**——需要 api_server / agent_report.api 启动时显式调用：
    from shared.sources import bootstrap
    bootstrap()
"""
from __future__ import annotations

from .base import BaseSource, Evidence, QueryRequest, QueryResult, SourceTier

__all__ = [
    "BaseSource",
    "Evidence",
    "QueryRequest",
    "QueryResult",
    "SourceTier",
    "bootstrap",
]


def bootstrap() -> dict[str, bool]:
    """幂等：多次调用安全。返回各步骤状态字典，调用方可打日志。

    步骤按「源注册失败不影响 agent 偏好注册」排布：某个 source import 失败
    （akshare 未装、httpx 版本怪异等）只会跳过该源，其他正常。
    """
    status: dict[str, bool] = {}

    # --- 注册所有具体 source ---
    for mod_name, src_cls in [
        ("tavily", "TavilySource"),
        ("akshare", "AkshareSource"),
        ("gov_cn", "GovCnSource"),
        ("pbc_gov", "PbcGovSource"),
        ("flk_npc", "FlkNpcSource"),
        ("enterprise_info", "EnterpriseInfoSource"),
    ]:
        try:
            module = __import__(
                f"shared.sources.impls.{mod_name}", fromlist=[src_cls]
            )
            cls = getattr(module, src_cls)
            from .registry import register
            register(cls())
            status[f"source.{mod_name}"] = True
        except (ImportError, ModuleNotFoundError, AttributeError, RuntimeError, ValueError, TypeError) as e:
            status[f"source.{mod_name}"] = False
            status[f"source.{mod_name}.err"] = f"{type(e).__name__}: {e}"  # type: ignore[assignment]

    # --- 调用各 agent 的偏好注册 ---
    for agent_mod in ["agent_compliance", "agent_credit", "agent_report", "agent_channel"]:
        try:
            module = __import__(
                f"{agent_mod}.sources_config", fromlist=["init"]
            )
            module.init()
            status[f"prefs.{agent_mod}"] = True
        except ModuleNotFoundError:
            # 没有 sources_config.py 是允许的，不报错
            status[f"prefs.{agent_mod}"] = False
        except (ImportError, AttributeError, RuntimeError, ValueError, TypeError) as e:
            status[f"prefs.{agent_mod}"] = False
            status[f"prefs.{agent_mod}.err"] = f"{type(e).__name__}: {e}"  # type: ignore[assignment]

    return status
