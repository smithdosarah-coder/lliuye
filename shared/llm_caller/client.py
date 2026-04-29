# -*- coding: utf-8 -*-
"""shared.llm_caller.client — top-level LLMCaller facade (M5 of 5).

Phase A worker-A2 · 2026-04-29 · 串 provider + retry + audit + prompts.

API:
    LLMCaller(agent_id, endpoint, chain=None, audit_enabled=True)
        .chat(system, user, ...)       · → ProviderResult · 走 fallback chain + 可选 audit
        .chat_json(system, user, ...)   · → ProviderResult.json_payload · 同上 JSON mode
    chat(system, user, ...)             · 模块级便捷入口 · 走默认 chain · 不 audit
    chat_json(system, user, ...)        · 同上 · JSON mode

设计目标:
  · 6 agent 后续迁移 (A4 worker) 的 SSOT caller · 替代:
    - root from llm import LLMClient(provider=...).simple_chat / chat_json   (caller 1 直用)
    - agent_riskctrl/llm_judge LLMJudge 基类 (caller 3)
    - agent_report._build_llm_caller / _build_simple_llm_caller 裸 OpenAI() (caller 4)
    - agent_alert/compliance/riskctrl 直 LLMClient init (caller 5)

Migration path (供 A4 worker · 不在本任务执行):
  · caller 3 (llm_judge):
        from shared.llm_caller import LLMCaller
        caller = LLMCaller(agent_id="riskctrl", endpoint="judge")
        result = caller.chat(prompt['system'], prompt['user'])
  · caller 4 (agent_report._build_llm_caller):
        caller = LLMCaller(agent_id="report", endpoint="/api/report/v16/fill")
        # def caller_fn(system, user): return caller.chat(system, user).content
  · caller 5 (alert/compliance/riskctrl 直 LLMClient):
        caller = LLMCaller(agent_id="<id>", endpoint="<route>")
        result = caller.chat_json(system, user, schema_hint=...)

Boundary:
  · 不在本 commit 改 agent_*/api.py · A4 worker 后续迁
  · 走 fallback chain (DEFAULT="deepseek","dashscope" · PIPL 境内优先)
  · audit 仅 agent_id 非空 + audit_enabled=True 时启用 · silent fail
"""
from __future__ import annotations

from shared.llm_caller.audit import with_audit
from shared.llm_caller.provider import ProviderResult
from shared.llm_caller.retry import (
    chat_json_with_fallback,
    chat_with_fallback,
)


class LLMCaller:
    """Top-level facade · 6 agent 后续迁此入口.

    通过组合 retry (fallback chain) + audit (silent-fail hook) + provider 接口 ·
    上层只见 chat / chat_json · 底层 SDK 隔离 + 跨境识别 + 留痕 全自动.
    """

    def __init__(
        self,
        *,
        agent_id: str = "",
        endpoint: str = "",
        chain: list[str] | None = None,
        audit_enabled: bool = True,
    ) -> None:
        """Args:
            agent_id:     channel/credit/report/alert/compliance/riskctrl · 空串 → 不 audit
            endpoint:     端点或 caller 标识 · 进 audit log
            chain:        覆盖默认 fallback chain · 默认 None = (deepseek, dashscope)
            audit_enabled: True 且 agent_id 非空时启 audit · silent-fail
        """
        self.agent_id = agent_id
        self.endpoint = endpoint
        self.chain = chain
        # audit 仅 agent_id 非空 + audit_enabled=True 时启用
        self._audit = bool(audit_enabled and agent_id)

    def chat(
        self,
        system: str,
        user: str,
        *,
        temperature: float | None = None,
        api_key: str = "",
        user_id: str | None = None,
    ) -> ProviderResult:
        """普通 chat · 走 fallback chain · 可选 audit log."""
        if self._audit:
            with with_audit(
                agent_id=self.agent_id,
                endpoint=self.endpoint,
                user_id=user_id,
            ) as audit:
                result = chat_with_fallback(
                    system, user,
                    temperature=temperature,
                    api_key=api_key,
                    chain=self.chain,
                )
                audit.attach(result)
                return result
        return chat_with_fallback(
            system, user,
            temperature=temperature,
            api_key=api_key,
            chain=self.chain,
        )

    def chat_json(
        self,
        system: str,
        user: str,
        *,
        schema_hint: str = "",
        temperature: float | None = None,
        api_key: str = "",
        user_id: str | None = None,
    ) -> ProviderResult:
        """JSON mode · 走 fallback chain · 可选 audit log."""
        if self._audit:
            with with_audit(
                agent_id=self.agent_id,
                endpoint=self.endpoint,
                user_id=user_id,
            ) as audit:
                result = chat_json_with_fallback(
                    system, user,
                    schema_hint=schema_hint,
                    temperature=temperature,
                    api_key=api_key,
                    chain=self.chain,
                )
                audit.attach(result)
                return result
        return chat_json_with_fallback(
            system, user,
            schema_hint=schema_hint,
            temperature=temperature,
            api_key=api_key,
            chain=self.chain,
        )


# ---------------------------------------------------------------------------
# Module-level convenience (无 audit · 无 agent_id binding)
# ---------------------------------------------------------------------------


def chat(
    system: str,
    user: str,
    *,
    temperature: float | None = None,
    api_key: str = "",
    chain: list[str] | None = None,
) -> ProviderResult:
    """模块级 chat · 走默认 fallback chain · 不 audit (脚本 / dev 用)."""
    return chat_with_fallback(
        system, user,
        temperature=temperature,
        api_key=api_key,
        chain=chain,
    )


def chat_json(
    system: str,
    user: str,
    *,
    schema_hint: str = "",
    temperature: float | None = None,
    api_key: str = "",
    chain: list[str] | None = None,
) -> ProviderResult:
    """模块级 chat_json · 同上 · JSON mode."""
    return chat_json_with_fallback(
        system, user,
        schema_hint=schema_hint,
        temperature=temperature,
        api_key=api_key,
        chain=chain,
    )


__all__ = [
    "LLMCaller",
    "chat",
    "chat_json",
]
