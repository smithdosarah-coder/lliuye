# -*- coding: utf-8 -*-
"""画像消费域 —— 读取 Agent6 ReportJSON / EnterpriseProfile 并抽取决策所需特征。"""

from __future__ import annotations

from typing import Any

from ..feature_extractor import FeatureExtractor
from ..profile_enhancer import enhance_enterprise_profile as _enhance_enterprise_profile


def profile_consume_features(profile: dict, segment: str = "corporate") -> dict:
    """抽取决策所需特征（画像消费域：特征抽取入口）。

    薄包装 `FeatureExtractor().extract(profile, segment)`。
    """
    return FeatureExtractor().extract(profile, segment)


def profile_consume_enhance(profile: Any, *, llm_fn=None) -> tuple[dict, list[dict]]:
    """用 LLM 对画像做补全（画像消费域：画像增强）。

    返回 (增强后 profile dict, 增强补丁列表)。
    """
    return _enhance_enterprise_profile(profile, llm_fn=llm_fn)
