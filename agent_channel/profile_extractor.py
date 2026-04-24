# -*- coding: utf-8 -*-
"""ProfileExtractor: LLM 从 KnowledgeBase 抽取 IdealProfile。

设计要点：
- 优先走 LLM，失败时有确定性兜底（从客户统计取 TOP 字段 + 政策关键词）
- 兜底策略在 LLM 不可用时仍能产出可用画像，不阻断 Demo
"""
from __future__ import annotations

import uuid
from collections import Counter
from typing import Any

from shared.kb_scan.models import IdealProfile
from agent_channel.knowledge_base import ChannelKnowledgeBase
from agent_channel.prompts import (
    PROFILE_EXTRACT_SYSTEM,
    PROFILE_EXTRACT_PROMPT,
)


class ProfileExtractor:
    """画像抽取器。"""

    def __init__(self, llm_caller=None):
        """llm_caller: 签名为 (system, user) -> dict | None 的可调用对象；
        推荐传入 BaseAgent.llm_json。为 None 时直接走兜底。"""
        self.llm_caller = llm_caller

    def extract(self, kb: ChannelKnowledgeBase) -> IdealProfile:
        stats = self._aggregate_customer_stats(kb.companies)
        policy = kb.policy_text(max_chars=3500)
        industry_guide = kb.industry_guide_text(max_chars=2000)

        data: dict[str, Any] | None = None
        if self.llm_caller is not None:
            try:
                user = PROFILE_EXTRACT_PROMPT.format(
                    customer_stats=stats,
                    policy_rules=policy or "（未上传政策文件）",
                    industry_guide=industry_guide or "（未上传行业指引）",
                )
                data = self.llm_caller(PROFILE_EXTRACT_SYSTEM, user)
                if isinstance(data, dict) and "pitches" in data:
                    data = None  # 误判，走兜底
            except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError):
                data = None

        if not isinstance(data, dict):
            return self._fallback_profile(kb)

        # 补默认值并构造 IdealProfile
        data.setdefault("profile_id", f"IP_{uuid.uuid4().hex[:8]}")
        data.setdefault("name", "自动生成的理想客户画像")
        for key in ["target_industries", "target_sub_industries", "target_regions",
                    "scale_range", "must_have_tags", "nice_to_have_tags", "exclude_tags"]:
            data.setdefault(key, [])
        data.setdefault("policy_context", "")
        data.setdefault("reasoning", "")
        # revenue_range 容错
        rr = data.get("revenue_range")
        if not (isinstance(rr, (list, tuple)) and len(rr) == 2):
            data["revenue_range"] = None
        else:
            try:
                data["revenue_range"] = (float(rr[0]), float(rr[1]))
            except (ValueError, TypeError, IndexError):
                data["revenue_range"] = None

        try:
            return IdealProfile.model_validate(data)
        except (ValueError, TypeError, AttributeError):
            return self._fallback_profile(kb)

    # ---- 统计聚合 ----

    def _aggregate_customer_stats(self, companies) -> str:
        if not companies:
            return "（未提供客户名录）"
        industries = Counter((c.industry or "未知") for c in companies)
        sub_industries = Counter((c.sub_industry or "未知") for c in companies if c.sub_industry)
        regions = Counter(self._region_province(c.region) for c in companies if c.region)
        scales = Counter((c.scale or "未知") for c in companies)
        tags = Counter()
        for c in companies:
            for t in (c.tags or []):
                tags[t] += 1
            for q in (c.qualifications or []):
                tags[q] += 1

        total = len(companies)
        def _fmt(counter, topn=5):
            items = counter.most_common(topn)
            return ", ".join(f"{k} {v}家({v*100//total}%)" for k, v in items)

        lines = [
            f"- 客户总数: {total} 家",
            f"- 行业 TOP5: {_fmt(industries)}",
            f"- 细分行业 TOP5: {_fmt(sub_industries) or '（无数据）'}",
            f"- 规模分布: {_fmt(scales)}",
            f"- 地域 TOP5: {_fmt(regions) or '（无数据）'}",
            f"- 共性标签 TOP5: {_fmt(tags) or '（无数据）'}",
        ]
        return "\n".join(lines)

    @staticmethod
    def _region_province(region: str) -> str:
        """粗略取省/直辖市前缀用于地域统计。"""
        if not region:
            return ""
        for kw in ["北京", "上海", "天津", "重庆"]:
            if region.startswith(kw):
                return kw + "市"
        # 省份
        if region[:2] in {"浙江", "江苏", "广东", "山东", "福建", "安徽",
                          "湖北", "湖南", "四川", "河南", "河北", "陕西",
                          "辽宁", "吉林", "山西", "云南", "贵州", "甘肃",
                          "江西", "海南", "青海", "西藏", "新疆", "宁夏",
                          "广西", "内蒙"}:
            return region[:3] if region[2] == "省" or region[2] == "市" else region[:2]
        return region[:4]

    # ---- 兜底 ----

    def _fallback_profile(self, kb: ChannelKnowledgeBase) -> IdealProfile:
        companies = kb.companies
        top_industries = [k for k, _ in Counter(c.industry for c in companies if c.industry).most_common(3)] or ["制造业"]
        top_regions = [self._region_province(c.region) for c in companies if c.region]
        top_regions = [k for k, _ in Counter(top_regions).most_common(3)] or ["浙江省"]
        top_scales = [k for k, _ in Counter(c.scale for c in companies if c.scale).most_common(2)] or ["小型", "微型"]
        tag_ctr = Counter()
        for c in companies:
            for t in (c.tags or []):
                tag_ctr[t] += 1
            for q in (c.qualifications or []):
                tag_ctr[q] += 1
        top_tags = [k for k, _ in tag_ctr.most_common(5)]
        must = [t for t in top_tags if "专精特新" in t or "高新" in t][:2]
        nice = [t for t in top_tags if t not in must][:3]

        # 营收范围
        revs = []
        for c in companies:
            rv = c.revenue_latest or ""
            num = self._parse_revenue_wan(rv)
            if num:
                revs.append(num)
        if revs:
            revs.sort()
            lo = max(1000.0, revs[0] * 0.6)
            hi = min(50000.0, revs[-1] * 1.4)
        else:
            lo, hi = 1000.0, 50000.0

        return IdealProfile(
            profile_id=f"IP_{uuid.uuid4().hex[:8]}",
            name=f"{top_industries[0]} look-alike 画像",
            target_industries=top_industries,
            target_sub_industries=[],
            target_regions=top_regions,
            scale_range=top_scales,
            revenue_range=(lo, hi),
            must_have_tags=must or ["高新技术企业"],
            nice_to_have_tags=nice,
            exclude_tags=["房地产", "高污染"],
            policy_context=(kb.policy_text(600) or "")[:300] or "当前政策环境聚焦科技创新与专精特新培育",
            reasoning=(
                "规则兜底：基于已有客户的行业 / 地域 / 规模 / 标签频率，"
                f"锁定 {top_industries[0]}。LLM 画像抽取不可用时自动生成。"
            ),
        )

    @staticmethod
    def _parse_revenue_wan(s: str) -> float | None:
        """把'4200万'/'1.2亿'/'2000'之类的字符串解析成"万元"浮点数。"""
        if not s:
            return None
        s = str(s).replace(",", "").strip()
        try:
            if "亿" in s:
                num = float(s.replace("亿", "").strip())
                return num * 10000
            if "万" in s:
                num = float(s.replace("万", "").strip())
                return num
            num = float(s)
            # 认为是"元"
            if num > 100000:
                return num / 10000
            return num
        except (ValueError, TypeError):
            return None
