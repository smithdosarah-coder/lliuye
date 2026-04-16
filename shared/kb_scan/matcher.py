# -*- coding: utf-8 -*-
"""Matcher: 目标 × 规则 → 命中项。

通用基类 + 三个 Agent 自己实现 match_one。
附带 SimilarityScorer（look-alike 用，确定性计算不依赖 LLM）。
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Callable, Iterable

from .models import (
    ScanTarget, RuleItem, HitItem, RiskLevel, CompanyProfile, Evidence,
)


class Matcher(ABC):
    """三个 Agent 的匹配引擎都继承这个基类。"""

    @abstractmethod
    def match_one(self, target: ScanTarget, rules: list[RuleItem]) -> HitItem | None:
        """对单个 target 跑匹配。返回 None 表示完全不命中。"""
        ...

    def match_all(
        self,
        targets: list[ScanTarget],
        rules: list[RuleItem],
        progress_cb: Callable[[int, int], None] | None = None,
    ) -> list[HitItem]:
        hits: list[HitItem] = []
        total = len(targets)
        for i, t in enumerate(targets):
            hit = self.match_one(t, rules)
            if hit and hit.score > 0:
                hits.append(hit)
            if progress_cb:
                progress_cb(i + 1, total)
        return hits


# ========== SimilarityScorer：Agent1 look-alike 用 ==========

class SimilarityScorer:
    """基于 CompanyProfile 计算两家企业的相似度。不依赖 LLM。"""

    def __init__(self, weights: dict | None = None):
        self.weights = weights or {
            "industry": 0.30,
            "sub_industry": 0.15,
            "region": 0.15,
            "scale": 0.10,
            "keywords": 0.20,
            "qualifications": 0.10,
        }

    def score(self, anchor: CompanyProfile, candidate: CompanyProfile) -> float:
        s = 0.0
        if anchor.industry and candidate.industry and anchor.industry == candidate.industry:
            s += self.weights.get("industry", 0.3)
        if anchor.sub_industry and candidate.sub_industry and anchor.sub_industry == candidate.sub_industry:
            s += self.weights.get("sub_industry", 0.15)
        if anchor.region and candidate.region:
            if anchor.region == candidate.region:
                s += self.weights.get("region", 0.15)
            elif anchor.region[:2] == candidate.region[:2]:
                s += self.weights.get("region", 0.15) * 0.5
        if anchor.scale and candidate.scale and anchor.scale == candidate.scale:
            s += self.weights.get("scale", 0.10)

        # 关键词 Jaccard
        a_kw = set(anchor.keywords or []) | set(anchor.tags or [])
        c_kw = set(candidate.keywords or []) | set(candidate.tags or [])
        if a_kw and c_kw:
            jac = len(a_kw & c_kw) / max(1, len(a_kw | c_kw))
            s += self.weights.get("keywords", 0.2) * jac

        # 资质重合
        a_q = set(anchor.qualifications or [])
        c_q = set(candidate.qualifications or [])
        if a_q and c_q:
            qscore = len(a_q & c_q) / max(1, len(a_q))
            s += self.weights.get("qualifications", 0.1) * qscore

        return round(min(s, 1.0) * 100, 2)

    def rank_candidates(
        self,
        anchor: CompanyProfile,
        candidates: Iterable[CompanyProfile],
        top_n: int = 10,
    ) -> list[tuple[CompanyProfile, float]]:
        scored = [(c, self.score(anchor, c)) for c in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_n]


# ========== 通用辅助：关键词规则打分器 ==========

def keyword_match_rule(rule: RuleItem, text: str) -> float:
    """最朴素的规则命中：关键词/触发条件在文本中出现则算命中。
    子类 Matcher 可以直接用或扩展。
    返回 0~1 的命中强度。
    """
    t = (text or "").lower()
    # 优先看 trigger_condition
    if rule.trigger_condition:
        tc = rule.trigger_condition.lower()
        tokens = [tok for tok in tc.replace("，", " ").replace(",", " ").split() if len(tok) >= 2]
        if tokens:
            hit = sum(1 for tok in tokens if tok in t)
            if hit >= max(1, len(tokens) // 2):
                return min(1.0, hit / max(1, len(tokens)))
    # 再看 title
    if rule.title:
        tl = rule.title.lower()
        if tl in t:
            return 0.8
    return 0.0


def level_from_score(score: float, thresholds: tuple[float, float] = (70.0, 40.0)) -> RiskLevel:
    """score 0-100 → 红/黄/绿。阈值按 Agent 可调。"""
    hi, mid = thresholds
    if score >= hi:
        return RiskLevel.RED
    if score >= mid:
        return RiskLevel.YELLOW
    return RiskLevel.GREEN
