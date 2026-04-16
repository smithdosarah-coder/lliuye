# -*- coding: utf-8 -*-
"""Agent1（全渠道流量匹配）数据源偏好配置。

由 shared.sources.bootstrap() 自动调用 init()——不在这里手工 import。

domain 命名约定：`agent_channel.<capability>`，调用方在 realtime_stream.py
里通过 Router().query("agent_channel.enterprise_info", ...) 触发降级链。

降级哲学：
    enterprise_info（上市走 akshare，非上市走 Tavily+LLM 严抽）
        ↓ 失败
    tavily（裸 web 搜索，作最后兜底）
"""
from __future__ import annotations

from shared.sources.router import register_preference


def init() -> None:
    """注册 Agent1 所有 domain 的偏好链。bootstrap() 中以 try/except 包裹。"""
    register_preference(
        "agent_channel.enterprise_info",
        ["enterprise_info", "tavily"],
    )
