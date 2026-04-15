# -*- coding: utf-8 -*-
"""
industry_cards — 行业/政策参考卡片库

用途:根据客户主营业务关键词自动匹配若干"行业卡片",把典型毛利率区间、
账期、政策、趋势等预先准备好的结构化知识注入到 LLM prompt,让外因分析
有具体的行业数据可引用,杜绝 LLM 凭空编造"同行业平均""政策东风"等空话。

卡片来源:
  - 公开行业研报 / 国家统计局口径 / Wind 上市公司中位数
  - 每张卡 source 字段标注;若无确切来源,写"公开行业研究 / 国统局口径"

关键 API:
  find_cards(keywords: list[str], top_k: int = 3) -> list[IndustryCard]
    大小写不敏感,关键词任一命中 match_keywords 即算该卡命中;
    top_k 按命中数排序返回。

卡片文件:本目录下每张卡片 <industry_name>.json。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

_HERE = os.path.dirname(os.path.abspath(__file__))


@dataclass
class IndustryCard:
    industry: str
    industry_code: str = ""
    match_keywords: list[str] = field(default_factory=list)
    benchmarks: dict[str, str] = field(default_factory=dict)
    key_policies: list[str] = field(default_factory=list)
    industry_trends: str = ""
    peer_benchmark: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "industry": self.industry,
            "industry_code": self.industry_code,
            "match_keywords": list(self.match_keywords),
            "benchmarks": dict(self.benchmarks),
            "key_policies": list(self.key_policies),
            "industry_trends": self.industry_trends,
            "peer_benchmark": self.peer_benchmark,
            "source": self.source,
        }

    def format_block(self) -> list[str]:
        """格式化为 prompt 中卡片小节的若干行(不含外层标题)。"""
        lines: list[str] = []
        head = f"  ▸ 卡片: {self.industry}"
        if self.industry_code:
            head += f" ({self.industry_code})"
        lines.append(head)
        for metric, rng in self.benchmarks.items():
            lines.append(f"      - {metric}: {rng}")
        for pol in self.key_policies:
            lines.append(f"      - 政策: {pol}")
        if self.industry_trends:
            lines.append(f"      - 趋势: {self.industry_trends}")
        if self.peer_benchmark:
            lines.append(f"      - 同业中位数: {self.peer_benchmark}")
        if self.source:
            lines.append(f"      - 来源: {self.source}")
        return lines


def _load_all_cards() -> list[IndustryCard]:
    cards: list[IndustryCard] = []
    if not os.path.isdir(_HERE):
        return cards
    for fname in sorted(os.listdir(_HERE)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(_HERE, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            card = IndustryCard(
                industry=data.get("industry", fname.rsplit(".", 1)[0]),
                industry_code=data.get("industry_code", ""),
                match_keywords=list(data.get("match_keywords") or []),
                benchmarks=dict(data.get("benchmarks") or {}),
                key_policies=list(data.get("key_policies") or []),
                industry_trends=data.get("industry_trends", ""),
                peer_benchmark=data.get("peer_benchmark", ""),
                source=data.get("source", ""),
            )
            cards.append(card)
        except Exception:
            continue
    return cards


def find_cards(keywords, top_k: int = 3) -> list[IndustryCard]:
    """按关键词匹配卡片,返回命中数最多的 top_k 张。

    keywords: 可迭代的字符串集合,如 ['软件', '信息技术', 'SaaS']。
              大小写不敏感;任一关键词作为子串在卡片 match_keywords 任一条目
              中出现即命中该条目(+1 分)。反向也匹配(卡片关键词作为子串
              出现在用户关键词中也算命中)。
    top_k: 返回命中数最高的前若干张。按命中数降序、industry_code 升序稳定排序。

    返回:若无任何命中则返回空列表。
    """
    if not keywords:
        return []
    user_kws = [str(k).strip().lower() for k in keywords if str(k).strip()]
    if not user_kws:
        return []

    cards = _load_all_cards()
    scored: list[tuple[int, IndustryCard]] = []
    for card in cards:
        ck = [k.strip().lower() for k in card.match_keywords if k and k.strip()]
        if not ck:
            continue
        hits = 0
        for ukw in user_kws:
            for ckw in ck:
                if ukw in ckw or ckw in ukw:
                    hits += 1
                    break
        if hits > 0:
            scored.append((hits, card))
    scored.sort(key=lambda x: (-x[0], x[1].industry_code or "zzz"))
    return [c for _, c in scored[:top_k]]


__all__ = ["IndustryCard", "find_cards"]
