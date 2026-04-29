# -*- coding: utf-8 -*-
"""shared.llm_caller.client — top-level LLMCaller facade (M5 of 5).

Phase A worker-A2 · 2026-04-29 · 串 provider + retry + audit + prompts.
V2 fix issue 3: 加 simple_chat / make_text_caller / make_json_caller legacy adapters.

API:
    LLMCaller(agent_id, endpoint, chain=None, audit_enabled=True)
        .chat(system, user, ...)        · → ProviderResult · 走 fallback chain + 可选 audit
        .chat_json(system, user, ...)    · → ProviderResult.json_payload · 同上 JSON mode
        .simple_chat(system, user, ...)  · → str (legacy adapter · 匹配 root LLMClient.simple_chat)
    chat(system, user, ...)              · 模块级便捷入口 · 走默认 chain · 不 audit
    chat_json(system, user, ...)         · 同上 · JSON mode
    make_text_caller(*, agent_id, ...)   · → Callable[[str, str], str] · 失败返 ""
    make_json_caller(*, agent_id, ...)   · → Callable[[str, str, str], dict|list|None] · 失败返 None

设计目标:
  · 6 agent 后续迁移 (A4 worker) 的 SSOT caller · 替代:
    - root from llm import LLMClient(provider=...).simple_chat / chat_json   (caller 1 直用)
    - agent_riskctrl/llm_judge LLMJudge 基类 (caller 3)
    - agent_report._build_llm_caller / _build_simple_llm_caller 裸 OpenAI() (caller 4)
    - agent_alert/compliance/riskctrl 直 LLMClient init (caller 5)

Legacy adapter (V2 issue 3 · 给 A4 worker 机械迁老 caller fn):
    现有 agent_report._build_simple_llm_caller / agent_compliance.scan_engine.
    build_llm_caller / build_llm_json_caller 都返 closure (system, user) -> str | dict
    形态 · make_text_caller / make_json_caller 直接产同形 closure 替换.

Migration path (供 A4 worker):
  · caller 3 (llm_judge):
        caller = LLMCaller(agent_id="riskctrl", endpoint="judge")
        text = caller.simple_chat(prompt['system'], prompt['user'])  # str
  · caller 4 (agent_report._build_simple_llm_caller):
        caller_fn = make_text_caller(agent_id="report", endpoint="/api/report/v16/fill")
        # caller_fn(system, user) -> str · 直接替换原函数返回值
  · caller 5 (alert/compliance/riskctrl 直 LLMClient):
        caller = LLMCaller(agent_id="<id>", endpoint="<route>")
        result = caller.chat_json(system, user, schema_hint=...)
        # OR: json_fn = make_json_caller(...); json_fn(system, user, schema_hint)

Boundary:
  · 不在本 commit 改 agent_*/api.py · A4 worker 后续迁
  · 走 fallback chain (DEFAULT="deepseek","dashscope" · PIPL 境内优先)
  · audit 仅 agent_id 非空 + audit_enabled=True 时启用 · silent fail
"""
from __future__ import annotations

from typing import Any, Callable

from shared.llm_caller.audit import with_audit
from shared.llm_caller.provider import ProviderResult, ProviderUnavailableError
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

    def simple_chat(
        self,
        system: str,
        user: str,
        *,
        temperature: float | None = None,
        api_key: str = "",
        user_id: str | None = None,
    ) -> str:
        """Legacy adapter · 返 str (not ProviderResult) · 匹配 root llm.LLMClient.simple_chat 签名.

        V2 fix issue 3 · 给 caller 3 (llm_judge.LLMJudge._get_client().simple_chat) 直接替换路径.
        失败抛 ProviderUnavailableError · 调用者 catch (与 LLMClient.simple_chat 异常行为一致).
        """
        result = self.chat(
            system, user,
            temperature=temperature, api_key=api_key, user_id=user_id,
        )
        return result.content or ""


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


# ---------------------------------------------------------------------------
# Legacy adapters (V2 fix issue 3 · 给 A4 worker 机械迁现有 caller fn)
# ---------------------------------------------------------------------------


def make_text_caller(
    *,
    agent_id: str = "",
    endpoint: str = "",
    chain: list[str] | None = None,
    audit_enabled: bool = True,
    temperature: float | None = None,
    api_key: str = "",
) -> Callable[[str, str], str]:
    """构 (system, user) -> str closure · 匹配 agent_report._build_simple_llm_caller /
    agent_compliance.scan_engine.build_llm_caller 等现有 caller fn 签名.

    Args:
        agent_id / endpoint / chain / audit_enabled: 透传 LLMCaller
        temperature: 默认温度 (caller fn 调用方不再传 temp · 一次绑定)
        api_key:     默认 api_key (BYOK 场景 · 一次绑定)

    Returns:
        Callable[[str, str], str] · 失败时返 "" (与 LLMClient.simple_chat 失败时
        现有 caller fn pattern 对齐 · agent_report._build_simple_llm_caller 现状即如此)

    Usage (A4 worker 替换 agent_report/api.py 内 _build_simple_llm_caller):
        # before:
        #   client = OpenAI(api_key=..., base_url="https://api.deepseek.com")
        #   def caller(system, user):
        #       try:    return client.chat.completions.create(...).choices[0].message.content or ""
        #       except: return ""
        # after:
        caller = make_text_caller(agent_id="report", endpoint="/api/report/v16/fill")
    """
    inner = LLMCaller(
        agent_id=agent_id,
        endpoint=endpoint,
        chain=chain,
        audit_enabled=audit_enabled,
    )

    def text_fn(system: str, user: str) -> str:
        try:
            return inner.simple_chat(
                system, user,
                temperature=temperature,
                api_key=api_key,
            )
        except ProviderUnavailableError:
            return ""

    return text_fn


def make_json_caller(
    *,
    agent_id: str = "",
    endpoint: str = "",
    chain: list[str] | None = None,
    audit_enabled: bool = True,
    temperature: float | None = None,
    api_key: str = "",
) -> Callable[..., Any]:
    """构 (system, user, schema_hint="") -> dict|list|None closure · 匹配
    agent_compliance.scan_engine.build_llm_json_caller 现有签名.

    Returns:
        Callable[[str, str, str], dict | list | None] · 失败返 None
        (与 build_llm_json_caller 现有 fail-silent pattern 对齐).

    Usage (A4 worker 替换 build_llm_json_caller):
        # before:
        #   client = LLMClient(provider="deepseek", api_key=key)
        #   def caller(system, user, schema_hint=""):
        #       try:    return client.chat_json(system, user, schema_hint=schema_hint)
        #       except: return None
        # after:
        caller = make_json_caller(agent_id="compliance", endpoint="/api/compliance/scan")
    """
    inner = LLMCaller(
        agent_id=agent_id,
        endpoint=endpoint,
        chain=chain,
        audit_enabled=audit_enabled,
    )

    def json_fn(
        system: str,
        user: str,
        schema_hint: str = "",
    ) -> dict | list | None:
        try:
            result = inner.chat_json(
                system, user,
                schema_hint=schema_hint,
                temperature=temperature,
                api_key=api_key,
            )
            return result.json_payload
        except ProviderUnavailableError:
            return None

    return json_fn


__all__ = [
    "LLMCaller",
    "chat",
    "chat_json",
    "make_json_caller",
    "make_text_caller",
]
