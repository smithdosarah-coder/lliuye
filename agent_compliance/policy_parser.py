# -*- coding: utf-8 -*-
"""Agent5 合规巡检 - 政策要求提取

从政策文件文本中解析出结构化的监管要求列表。
"""

from __future__ import annotations

import json
import re
from typing import Callable
from pydantic import BaseModel, Field

from .prompts import SYSTEM_POLICY_PARSE


class PolicyRequirement(BaseModel):
    """单条监管要求"""
    req_id: str = Field(default="", description="要求编号，如 REQ-001")
    category: str = Field(default="", description="类别，如 信息披露、风险管理")
    description: str = Field(default="", description="要求描述")
    source_clause: str = Field(default="", description="来源条款原文")
    severity: str = Field(default="mandatory", description="严格程度: mandatory/recommended/optional")
    keywords: list[str] = Field(default_factory=list, description="关键词列表")


class PolicyDocument(BaseModel):
    """政策文件解析结果"""
    title: str = Field(default="", description="政策标题")
    issuer: str = Field(default="", description="发布机构")
    effective_date: str = Field(default="", description="生效日期")
    requirements: list[PolicyRequirement] = Field(default_factory=list, description="监管要求列表")


def parse_policy(policy_text: str, llm_fn: Callable) -> PolicyDocument:
    """用LLM从政策文本中提取结构化的监管要求。

    Args:
        policy_text: 政策文件的纯文本内容
        llm_fn: LLM调用回调，签名为 llm_fn(system, user, model_class, retries) -> BaseModel

    Returns:
        PolicyDocument: 结构化的政策文档对象
    """
    # 截断过长的文本，保留前后部分
    max_len = 12000
    if len(policy_text) > max_len:
        keep_start = int(max_len * 0.7)
        keep_end = max_len - keep_start - 60
        policy_text = (
            policy_text[:keep_start]
            + f"\n\n... (省略约{len(policy_text) - max_len}字) ...\n\n"
            + policy_text[-keep_end:]
        )

    user_prompt = (
        "请解析以下政策文件，提取所有监管要求：\n\n"
        f"{policy_text}"
    )

    try:
        result = llm_fn(SYSTEM_POLICY_PARSE, user_prompt, PolicyDocument, retries=3)
        if isinstance(result, PolicyDocument):
            # 确保每条要求都有编号
            for i, req in enumerate(result.requirements):
                if not req.req_id:
                    req.req_id = f"REQ-{i + 1:03d}"
            return result
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError):
        pass

    # 兜底：返回空文档
    return PolicyDocument(title="(解析失败)", issuer="", effective_date="", requirements=[])


def categorize_requirements(requirements: list[PolicyRequirement]) -> dict[str, list[PolicyRequirement]]:
    """按类别对监管要求进行分组。

    Args:
        requirements: 监管要求列表

    Returns:
        dict: {类别名称: [该类别下的要求列表]}
    """
    groups: dict[str, list[PolicyRequirement]] = {}
    for req in requirements:
        category = req.category or "未分类"
        if category not in groups:
            groups[category] = []
        groups[category].append(req)
    return groups
