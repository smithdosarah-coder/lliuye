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
        "api_key_env": "DEEPSEEK_API_KEY",
        "supports_json_mode": True,
    },
    "deepseek-reasoner": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-reasoner",
        "max_tokens": 8192,
        "temperature": 0.3,
        "api_key_env": "DEEPSEEK_API_KEY",
        "supports_json_mode": True,
    },
    "qwen_cloud": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-max",
        "max_tokens": 8192,
        "temperature": 0.3,
        "api_key_env": "DASHSCOPE_API_KEY",
        "supports_json_mode": True,
    },
    "glm_cloud": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-plus",
        "max_tokens": 8192,
        "temperature": 0.3,
        "api_key_env": "ZHIPU_API_KEY",
        "supports_json_mode": True,
    },
    "local_vllm": {
        "base_url": os.getenv("LOCAL_VLLM_BASE_URL", "http://127.0.0.1:8000/v1"),
        "model": os.getenv("LOCAL_VLLM_MODEL", "Qwen2.5-72B-Instruct"),
        "max_tokens": 8192,
        "temperature": 0.3,
        "api_key_env": "LOCAL_VLLM_API_KEY",
        "supports_json_mode": True,
    },
    "kimi-k2.5": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "model": "moonshotai/kimi-k2.5",
        "max_tokens": 16384,
        "temperature": 0.3,
        "api_key_env": "NVIDIA_API_KEY",
        "supports_json_mode": False,
    },
    "minimax": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "model": "minimaxai/minimax-m2.5",
        "max_tokens": 8192,
        "temperature": 0.3,
        "api_key_env": "NVIDIA_API_KEY",
        "supports_json_mode": False,
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "max_tokens": 8192,
        "temperature": 0.3,
        "api_key_env": "OPENAI_API_KEY",
        "supports_json_mode": True,
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 8192,
        "temperature": 0.3,
        "api_key_env": "ANTHROPIC_API_KEY",
        "supports_json_mode": False,
    },
}

# 分类任务推荐用低温度,确保稳定
CLASSIFIER_PROVIDER = os.getenv("CLASSIFIER_PROVIDER", "deepseek")
CLASSIFIER_TEMPERATURE = 0.0

# 生成任务使用默认 provider
GENERATOR_PROVIDER = os.getenv("GENERATOR_PROVIDER", MODEL_PROVIDER)

# 审核任务(Auditor)— 银行场景用较稳的模型,语义审可另行配
AUDITOR_PROVIDER = os.getenv("AUDITOR_PROVIDER", MODEL_PROVIDER)

# LLM 调用缓存目录
LLM_CACHE_DIR = os.getenv("LLM_CACHE_DIR", ".cache/llm")

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
