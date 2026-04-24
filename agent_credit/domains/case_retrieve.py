# -*- coding: utf-8 -*-
"""案例召回域 —— 历史相似案例检索 + 同业对标。"""

from __future__ import annotations

from ..case_retriever import CaseRetriever


def case_retrieve_similar(features: dict, segment: str = "corporate", *, top_k: int = 5, **kwargs):
    """基于特征向量做相似历史案例召回（案例召回域：主入口）。

    薄包装 `CaseRetriever().retrieve(features, segment, top_k=top_k)`。
    """
    return CaseRetriever().retrieve(features, segment, top_k=top_k, **kwargs)
