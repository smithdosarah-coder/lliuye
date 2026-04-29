# -*- coding: utf-8 -*-
"""shared.llm_caller.prompts — prompt composition primitives (M4 of 5).

Phase A worker-A2 · 2026-04-29 · 纯字符串组装 · 不含业务 prompt 内容.

API:
    build_chat_messages(system, user)         · → list[dict] for OpenAI-compat chat
    with_json_schema_hint(system, schema_hint) · → str · system + schema 强约束尾巴
    with_few_shot(system, examples)            · → str · system + few-shot 示例尾巴
    truncate_for_context(text, max_chars)      · → str · 超长 prompt 截断 + 省略号

Boundary:
  · 本模块仅 string assembly utilities · 无业务 prompt 文本 (角色/citation/evidence-first)
  · 业务 prompt 文本去 shared/prompts/contract.py (M7 · 8 段 spec · A1 worker spec)
  · root prompts.py · agent_*/prompts.py · section_generator inline prompts 不动 (A4)

Use cases:
  - LLMCaller.chat() 内部组 messages
  - shared/prompts/contract.py 的 assemble() 末端组装 chat messages
  - tests 拼测试 prompt
"""
from __future__ import annotations


def build_chat_messages(
    system: str,
    user: str,
) -> list[dict[str, str]]:
    """OpenAI 兼容 chat messages · [system, user] 顺序.

    Args:
        system: system prompt · 角色 + 约束
        user:   user content · 实际 query / data

    Returns:
        [{"role": "system", "content": ...}, {"role": "user", "content": ...}]
    """
    return [
        {"role": "system", "content": system or ""},
        {"role": "user", "content": user or ""},
    ]


def with_json_schema_hint(system: str, schema_hint: str) -> str:
    """system + 输出格式强约束 (兼容非 supports_json_mode provider).

    用于无 response_format json_object 支持的 provider · 只能 prompt 强约束.
    匹配 root llm.LLMClient.chat_json 的 prompt 拼接风格 (一致性).

    Args:
        system:      原 system prompt
        schema_hint: JSON schema 描述 / 示例 · 空串则不附加

    Returns:
        合成后的 system prompt str.
    """
    if not schema_hint:
        return system or ""
    base = system or ""
    return (
        f"{base}\n\n【输出格式】\n{schema_hint}\n\n"
        "必须输出严格合法 JSON,不要 markdown 代码围栏,不要任何解释文字。"
    )


def with_few_shot(
    system: str,
    examples: list[dict] | None,
    *,
    max_n: int = 3,
    section_title: str = "【参考示例】",
) -> str:
    """system + few-shot 示例段尾巴 · 缺示例时 no-op.

    Args:
        system:        原 system prompt
        examples:      [{input, output, ...}] · 每条 dict 至少含 input + output
        max_n:         最多注入条数 (避免 prompt 爆)
        section_title: 段落标题 · 默认"【参考示例】"

    Returns:
        合成后的 system prompt str · 无示例返原 system.
    """
    if not examples:
        return system or ""
    items = examples[:max_n]
    if not items:
        return system or ""

    lines = ["", section_title]
    for i, ex in enumerate(items, start=1):
        inp = str(ex.get("input", "")).strip()
        out = str(ex.get("output", "")).strip()
        if not (inp or out):
            continue
        lines.append(f"示例 {i}")
        if inp:
            lines.append(f"  输入: {inp}")
        if out:
            lines.append(f"  输出: {out}")
        # 可选 reason 字段 (与 root prompts.py 反馈飞轮风格对齐)
        reason = str(ex.get("reason", "")).strip()
        if reason:
            lines.append(f"  原因: {reason}")
    block = "\n".join(lines)
    return f"{system or ''}\n{block}"


def truncate_for_context(text: str, max_chars: int) -> str:
    """超长 prompt 截断 + 省略号 · 防 context window 爆.

    Args:
        text:      原文
        max_chars: 字符上限 (≤0 时返原文)

    Returns:
        截断后字符串 · 末尾追加 "…(已截断)" 标记便于 audit / debug.
    """
    if not text:
        return ""
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[:max_chars] + "…(已截断)"


__all__ = [
    "build_chat_messages",
    "truncate_for_context",
    "with_few_shot",
    "with_json_schema_hint",
]
