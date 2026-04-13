# -*- coding: utf-8 -*-
"""
配置文件 v7
新增：网络搜索配置、自省参数、max_tokens提升
"""
import os

MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "deepseek")

MODEL_CONFIG = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "max_tokens": 8192,
        "temperature": 0.3,
    },
    "kimi-k2.5": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "model": "moonshotai/kimi-k2.5",
        "max_tokens": 16384,
        "temperature": 0.3,
    },
    "minimax": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "model": "minimaxai/minimax-m2.5",
        "max_tokens": 8192,
        "temperature": 0.3,
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "max_tokens": 8192,
        "temperature": 0.3,
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 8192,
        "temperature": 0.3,
    },
}

MAX_AGENT_STEPS = 18          # ★ v7: 增加步数上限，留出搜索+自省的空间
TOOL_CALL_TIMEOUT = 120
MEMORY_DIR = os.getenv("MEMORY_DIR", "./memory_store")
MAX_CONVERSATION_HISTORY = 50
MAX_REPORT_MEMORY = 100
SUPPORTED_FILE_TYPES = [".txt", ".docx", ".doc", ".pdf", ".xlsx", ".xls"]

# ★ v7: 网络搜索配置
SEARCH_ENABLED = True          # 是否启用网络搜索工具
SEARCH_MAX_RESULTS = 5         # 每次搜索返回的最大结果数
SEARCH_TIMEOUT = 15            # 搜索超时（秒）

# ★ v7: 自省配置
SELF_REFLECT_ENABLED = True    # 写完后自动自省
