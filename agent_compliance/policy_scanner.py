# -*- coding: utf-8 -*-
"""主动政策扫描 (Agent5) — 事件驱动的合规巡检入口。

定位：原 ComplianceRadarAgent 是用户上传政策文件被动触发的；本模块给它
增加「主动从 gov.cn / pbc / flk_npc 拉最新政策、转成候选清单」的能力。

设计要点（CLAUDE.md 约束）：
  - 仅返回候选清单 (raw_item + source_url + fetched_at)，不强制 LLM 解析
    （让上层 / UI 决定要不要 parse_policy 进 PolicyDocument，节省 token）
  - 失败优雅降级 → 返回空 list，绝不打断现有 process_message 流程
  - 每条候选必须带 source_url + fetched_at（Evidence-First）
"""
from __future__ import annotations

from typing import Any

from shared.sources.base import QueryRequest
from shared.sources.router import Router


def scan_latest_policies(query: str = "", limit: int = 10, llm_fn=None) -> list[dict]:
    """从 gov.cn / pbc / flk / tavily 偏好链按域 agent_compliance.policy_scan 拉政策。

    Args:
        query: 关键字过滤；空字符串走默认（"金融监管"）以确保有结果。
        limit: 候选条数上限。
        llm_fn: 预留——若上层要立即把 raw_item 解析成 PolicyDocument，可以传入。

    Returns:
        list of {
            raw_item: dict,                    # 原始源返回
            source_url: str,
            fetched_at: str,
            source_name: str,
            policy_doc: PolicyDocument | None  # 当前一律 None；按需 lazy parse
        }
    """
    results: list[dict] = []
    router = Router()
    try:
        r = router.query(
            "agent_compliance.policy_scan",
            QueryRequest(
                query=query or "金融监管",
                # 多个源的 supported_query_types 不一致：gov_cn/pbc 是 news；
                # flk_npc 是 law；tavily 兜底是 generic。这里走最广义的 policy。
                # 注：degrader 会按 supports() 跳过不接的源。
                query_type="policy",
                limit=max(1, int(limit)),
            ),
        )
        if not r.ok:
            # 主链路没接 policy？退回到各源各自的「自然」查询类型
            for qt in ("news", "law", "generic"):
                r = router.query(
                    "agent_compliance.policy_scan",
                    QueryRequest(
                        query=query or "金融监管",
                        query_type=qt,
                        limit=max(1, int(limit)),
                    ),
                )
                if r.ok:
                    break
        if r.ok:
            evidence = list(r.evidence)
            for idx, item in enumerate(r.items):
                ev = evidence[idx] if idx < len(evidence) else None
                results.append({
                    "raw_item": item,
                    "source_url": (ev.source_url if ev else item.get("url", "")),
                    "fetched_at": (ev.fetched_at if ev else r.fetched_at),
                    "source_name": (ev.source_name if ev else r.source_name),
                    # 不立即 parse_policy：节省 LLM token，让上层按需触发
                    "policy_doc": None,
                })
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError):
        # 优雅降级：扫描失败返回空 list，不打断既有 process_message
        pass
    return results
