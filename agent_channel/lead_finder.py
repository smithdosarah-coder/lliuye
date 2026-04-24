# -*- coding: utf-8 -*-
"""LookAlikeMatcher: 基于 SimilarityScorer 的 look-alike 匹配器 + 查询生成器。

设计要点：
- 确定性打分，不依赖 LLM
- 两阶段融合：画像相似度 (60%) + 样本锚相似度 (40%)
- 证据链：列出 Top3 样本锚 + 命中的画像维度
"""
from __future__ import annotations

import re
from typing import Iterable

from shared.kb_scan.matcher import Matcher, SimilarityScorer
from shared.kb_scan.models import (
    CompanyProfile,
    Evidence,
    HitItem,
    IdealProfile,
    RiskLevel,
    RuleItem,
    ScanTarget,
    SignalEvent,
)
from shared.kb_scan.search_provider import SearchProvider


def generate_search_queries(ideal: IdealProfile, max_queries: int = 4) -> list[str]:
    """根据画像生成 3-5 条外网搜索 query（region + industry + tag 组合）。"""
    queries: list[str] = []
    regions = ideal.target_regions or [""]
    industries = ideal.target_industries or [""]
    tags = ideal.must_have_tags + ideal.nice_to_have_tags
    # region × industry 交叉
    for region in regions[:3]:
        for industry in industries[:2]:
            tag_snippet = " ".join(tags[:2]) if tags else ""
            q = f"{region} {industry} {tag_snippet}".strip()
            q = " ".join(q.split())
            if q and q not in queries:
                queries.append(q)
            if len(queries) >= max_queries:
                break
        if len(queries) >= max_queries:
            break
    if not queries:
        # 兜底一个宽 query
        queries.append(" ".join(filter(None, [industries[0] if industries else "制造业", tags[0] if tags else ""])))
    return queries


class LeadSearcher:
    """把"画像 → 外网搜索 → 候选企业池"这段黑盒封装。"""

    def __init__(self, provider: SearchProvider):
        self.provider = provider

    def search_candidates(
        self,
        ideal: IdealProfile,
        per_query_limit: int = 50,
        max_total: int = 200,
    ) -> tuple[list[CompanyProfile], list[dict]]:
        """返回 (去重后的候选列表, 每条 query 的执行 meta)。"""
        queries = generate_search_queries(ideal)
        seen: dict[str, CompanyProfile] = {}
        metas = []
        for q in queries:
            # 注意：filters 只传"强约束"，地域 / 规模软匹配交给打分层，避免过早剪枝把 Top 给筛掉
            filters: dict = {}
            results: list[CompanyProfile] = []
            try:
                results = self.provider.search_companies(q, filters=filters, limit=per_query_limit)
            except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError) as e:
                metas.append({"query": q, "status": "error", "error": str(e)[:120], "count": 0})
                continue
            new_count = 0
            for c in results:
                key = c.company_id or c.company_name
                if key and key not in seen:
                    seen[key] = c
                    new_count += 1
                    if len(seen) >= max_total:
                        break
            metas.append({"query": q, "status": "ok", "count": len(results), "new": new_count})
            if len(seen) >= max_total:
                break
        return list(seen.values()), metas


class LookAlikeMatcher(Matcher):
    """Agent1 的 look-alike 匹配器。

    不使用 rules 参数（保留以满足 Matcher 基类签名），核心走 SimilarityScorer。
    """

    def __init__(self, scorer: SimilarityScorer | None = None,
                 profile_weight: float = 0.6, anchor_weight: float = 0.4):
        self.scorer = scorer or SimilarityScorer()
        self.profile_weight = profile_weight
        self.anchor_weight = anchor_weight

    # ---- Matcher 接口 ----

    def match_one(self, target: ScanTarget, rules: list[RuleItem]) -> HitItem | None:
        """Matcher 基类抽象方法 — 单 target 场景下退化为只算画像。

        实际业务走 match_all_against_ideal，这里保留一个最小实现以满足基类。
        """
        try:
            cand = CompanyProfile.model_validate(target.payload)
        except (ValueError, TypeError, AttributeError):
            return None
        return HitItem(
            hit_id=f"LEAD_{cand.company_id or cand.company_name}",
            level=RiskLevel.GREEN,
            score=0.0,
            target=target,
        )

    # ---- Agent1 专用接口 ----

    def match_all_against_ideal(
        self,
        candidates: list[CompanyProfile],
        ideal: IdealProfile,
        anchors: list[CompanyProfile],
        top_anchor_k: int = 3,
    ) -> list[HitItem]:
        hits: list[HitItem] = []
        for cand in candidates:
            profile_score = self._score_against_profile(cand, ideal)
            anchor_top = self._top_k_anchors(cand, anchors, k=top_anchor_k)
            if anchor_top:
                anchor_avg = sum(s for _, s in anchor_top) / len(anchor_top)
            else:
                anchor_avg = 0.0

            final = round(
                self.profile_weight * profile_score
                + self.anchor_weight * anchor_avg,
                2,
            )

            # 细分维度分（用于前端 radar 展示）
            dims = self._dimension_scores(cand, ideal)

            reasons = self._build_reasons(cand, ideal, anchor_top, dims)
            evidences = self._build_evidences(cand, anchor_top)

            target = ScanTarget(
                target_id=cand.company_id or cand.company_name,
                target_type="company",
                payload=cand.model_dump(),
            )
            hit = HitItem(
                hit_id=f"LEAD_{target.target_id}",
                level=RiskLevel.GREEN,   # 由 HitRanker 覆盖
                score=final,
                target=target,
                reasons=reasons,
                evidences=evidences,
                extras={
                    "profile_score": profile_score,
                    "anchor_score": round(anchor_avg, 2),
                    "top_anchors": [
                        {"name": a.company_name, "score": round(s, 2)}
                        for a, s in anchor_top
                    ],
                    "fit_dimensions": dims,
                },
            )
            hits.append(hit)
        return hits

    # ---- 打分子模块 ----

    def _score_against_profile(self, cand: CompanyProfile, ideal: IdealProfile) -> float:
        """候选企业与 IdealProfile 的匹配分（0-100）。"""
        s = 0.0
        w = self.scorer.weights

        # 行业
        if ideal.target_industries:
            if any(ti in (cand.industry or "") or (cand.industry or "") in ti for ti in ideal.target_industries):
                s += w.get("industry", 0.3)

        # 细分行业
        if ideal.target_sub_industries:
            if any(tsi in (cand.sub_industry or "") for tsi in ideal.target_sub_industries):
                s += w.get("sub_industry", 0.15)

        # 地域（省/市部分匹配）
        if ideal.target_regions:
            cand_region = cand.region or ""
            matched = False
            for tr in ideal.target_regions:
                tr2 = tr[:2]
                if tr and (tr in cand_region or (tr2 and tr2 in cand_region)):
                    matched = True
                    break
            if matched:
                s += w.get("region", 0.15)

        # 规模
        if ideal.scale_range and cand.scale in ideal.scale_range:
            s += w.get("scale", 0.10)

        # 标签（must_have_tags 必须有一个，nice_to_have 加分）
        cand_tagset = set((cand.tags or []) + (cand.qualifications or []) + (cand.keywords or []))
        must = set(ideal.must_have_tags or [])
        nice = set(ideal.nice_to_have_tags or [])

        if must:
            if self._tags_overlap(cand_tagset, must):
                s += w.get("keywords", 0.2) * 0.8
        if nice:
            hit_nice = sum(1 for n in nice if self._tag_hit(cand_tagset, n))
            # nice_to_have 满命中给满权重
            s += w.get("keywords", 0.2) * 0.4 * min(1.0, hit_nice / max(1, len(nice)))

        # 资质匹配（如果画像中必备资质也出现在 qualifications）
        cand_q = set(cand.qualifications or [])
        if must and cand_q:
            if self._tags_overlap(cand_q, must):
                s += w.get("qualifications", 0.1)

        # 排除标签 → 扣分
        if ideal.exclude_tags and self._tags_overlap(cand_tagset, set(ideal.exclude_tags)):
            s -= 0.25

        # 营收范围
        if ideal.revenue_range:
            rv = self._parse_revenue_wan(cand.revenue_latest)
            lo, hi = ideal.revenue_range
            if rv is not None and lo <= rv <= hi:
                s += 0.05

        return round(max(0.0, min(s, 1.0)) * 100, 2)

    def _dimension_scores(self, cand: CompanyProfile, ideal: IdealProfile) -> dict:
        """各维度 0-100 分，用于前端展示。"""
        out = {"industry": 0, "region": 0, "scale": 0, "tags": 0}
        if ideal.target_industries and any(
            ti in (cand.industry or "") or (cand.industry or "") in ti
            for ti in ideal.target_industries
        ):
            out["industry"] = 95
        elif cand.industry:
            out["industry"] = 40

        cand_region = cand.region or ""
        if ideal.target_regions:
            for tr in ideal.target_regions:
                if tr and (tr in cand_region or tr[:2] in cand_region):
                    out["region"] = 90
                    break
            else:
                out["region"] = 30

        if ideal.scale_range:
            out["scale"] = 90 if cand.scale in ideal.scale_range else 40

        must = set(ideal.must_have_tags or [])
        nice = set(ideal.nice_to_have_tags or [])
        cand_tagset = set((cand.tags or []) + (cand.qualifications or []) + (cand.keywords or []))
        tag_hit_must = sum(1 for m in must if self._tag_hit(cand_tagset, m))
        tag_hit_nice = sum(1 for n in nice if self._tag_hit(cand_tagset, n))
        if must:
            base = 60 * (tag_hit_must / max(1, len(must)))
            out["tags"] = int(min(100, base + 10 * tag_hit_nice))
        else:
            out["tags"] = min(100, 40 + 10 * tag_hit_nice)
        return out

    def _top_k_anchors(
        self,
        cand: CompanyProfile,
        anchors: Iterable[CompanyProfile],
        k: int = 3,
    ) -> list[tuple[CompanyProfile, float]]:
        scored = [(a, self.scorer.score(a, cand)) for a in anchors]
        scored.sort(key=lambda x: x[1], reverse=True)
        # 过滤 0 分
        scored = [x for x in scored if x[1] > 0]
        return scored[:k]

    def _build_reasons(
        self,
        cand: CompanyProfile,
        ideal: IdealProfile,
        anchor_top: list[tuple[CompanyProfile, float]],
        dims: dict,
    ) -> list[str]:
        reasons: list[str] = []

        if dims.get("industry", 0) >= 80 and ideal.target_industries:
            reasons.append(
                f"行业命中目标画像（{cand.industry}），与'{'/'.join(ideal.target_industries[:2])}'一致"
            )
        if dims.get("region", 0) >= 80 and ideal.target_regions:
            reasons.append(f"地域命中政策扶持区（{cand.region}）")
        if dims.get("scale", 0) >= 80:
            reasons.append(f"规模匹配画像（{cand.scale}）")

        cand_tagset = set((cand.tags or []) + (cand.qualifications or []) + (cand.keywords or []))
        hit_must = [m for m in (ideal.must_have_tags or []) if self._tag_hit(cand_tagset, m)]
        hit_nice = [n for n in (ideal.nice_to_have_tags or []) if self._tag_hit(cand_tagset, n)]
        if hit_must:
            reasons.append(f"命中必备标签：{', '.join(hit_must[:3])}")
        if hit_nice:
            reasons.append(f"命中加分标签：{', '.join(hit_nice[:3])}")

        if anchor_top:
            anchor_names = "、".join(a.company_name for a, _ in anchor_top[:3])
            reasons.append(f"与已有客户「{anchor_names}」高度相似")

        # 排除标签命中提示
        if ideal.exclude_tags and self._tags_overlap(cand_tagset, set(ideal.exclude_tags)):
            reasons.append("⚠️ 触发排除标签，已扣分")

        return reasons[:6]

    def _build_evidences(
        self,
        cand: CompanyProfile,
        anchor_top: list[tuple[CompanyProfile, float]],
    ) -> list[Evidence]:
        out: list[Evidence] = []
        for a, s in anchor_top[:3]:
            out.append(Evidence(
                source=f"已有客户锚·{a.company_name}",
                snippet=f"行业={a.industry} / 规模={a.scale} / 相似度={s:.1f}",
            ))
        return out

    # ---- 小工具 ----

    @staticmethod
    def _tags_overlap(a: set[str], b: set[str]) -> bool:
        for x in a:
            for y in b:
                if LookAlikeMatcher._tag_hit({x}, y):
                    return True
        return False

    @staticmethod
    def _tag_hit(tagset: set[str], needle: str) -> bool:
        """支持"A|B"语法（其中一个命中即可）以及子串包含。"""
        if not needle:
            return False
        alts = [x.strip() for x in needle.replace("，", ",").replace("/", "|").split("|") if x.strip()]
        for alt in alts:
            for t in tagset:
                if not t:
                    continue
                if alt in t or t in alt:
                    return True
        return False

    @staticmethod
    def _parse_revenue_wan(s: str) -> float | None:
        if not s:
            return None
        s = str(s).replace(",", "").strip()
        try:
            if "亿" in s:
                return float(s.replace("亿", "").strip()) * 10000
            if "万" in s:
                return float(s.replace("万", "").strip())
            num = float(s)
            return num / 10000 if num > 100000 else num
        except (ValueError, TypeError):
            return None


# ---------------------------------------------------------------------------
# Batch 2 · Router 接入层(Tavily / enterprise_info 真搜)
# ---------------------------------------------------------------------------

_COMPANY_NAME_RE = re.compile(
    r"([一-龥A-Za-z0-9·（）()]{2,30}?"
    r"(?:股份有限公司|有限责任公司|有限公司|集团公司|集团|公司|合作社|分公司))"
)


class RouterLeadSearcher:
    """走 shared.sources.Router 的真搜入口(Batch 2 · CLAUDE.md §3.5 环境边界)。

    两条腿:
      1. Router.query("agent_channel.enterprise_info", ...) → 偏好链 enterprise_info→tavily
         消费结构化工商字段(上市走 akshare,非上市 Tavily+LLM 严抽)
      2. 直接 Tavily news query(company_name) → 拼信号时间线 SignalEvent

    上层调用保持和 LeadSearcher.search_candidates 同样签名风格:返回
    (list[CompanyProfile], metas)。不抛异常,失败时单条 meta 标 error。

    无 TAVILY_API_KEY / 偏好链全挂 → candidates 为空 + metas 暴露 error,
    degraded 信息由 QueryResult.degraded 透传到 meta 里。
    """

    def __init__(self, router=None, ensure_bootstrap: bool = True):
        self._router = router
        self._ensure_bootstrap = ensure_bootstrap

    def _get_router(self):
        if self._router is not None:
            return self._router
        from shared.sources.router import Router
        if self._ensure_bootstrap:
            try:
                from shared.sources import bootstrap
                bootstrap()
            except (ImportError, RuntimeError, ValueError, TypeError):
                pass
        self._router = Router()
        return self._router

    # ---- query → candidate 解析 ----

    def _extract_company_names(self, snippet: str, title: str) -> list[str]:
        names: list[str] = []
        for text in (title, snippet):
            if not text:
                continue
            for m in _COMPANY_NAME_RE.finditer(text):
                name = m.group(1).strip()
                if len(name) > 30:
                    continue
                if name not in names:
                    names.append(name)
                if len(names) >= 3:
                    break
        return names

    def search_candidates(
        self,
        queries: list[str],
        per_query_limit: int = 10,
        max_total: int = 30,
    ) -> tuple[list[CompanyProfile], list[dict]]:
        """对每条 query 发一次 Router.query;解析 items 为 CompanyProfile。"""
        from shared.sources.base import QueryRequest
        from shared.kb_scan.models import Evidence as KBEvidence

        router = self._get_router()
        seen: dict[str, CompanyProfile] = {}
        metas: list[dict] = []

        for q in queries:
            if len(seen) >= max_total:
                break
            req = QueryRequest(
                query=q,
                query_type="research",     # Tavily 支持 research/news/company_info/generic
                filters={"search_depth": "advanced"},
                limit=per_query_limit,
            )
            try:
                result = router.query("agent_channel.enterprise_info", req)
            except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError) as e:
                metas.append({
                    "query": q, "status": "error",
                    "error": f"{type(e).__name__}: {e}", "count": 0,
                })
                continue
            if not result.ok:
                metas.append({
                    "query": q, "status": "error",
                    "error": result.error or "router returned ok=False",
                    "degraded": result.degraded, "source_name": result.source_name,
                    "count": 0,
                })
                continue

            new_count = 0
            for item in result.items:
                # item shape: {title, url, snippet, score} for Tavily;
                # enterprise_info (akshare path) 会塞 company_name/industry 等字段
                title = item.get("title", "") or ""
                url = item.get("url", "") or item.get("source_url", "") or ""
                snippet = item.get("snippet", "") or item.get("content", "") or ""

                candidate_names: list[str] = []
                if item.get("company_name"):
                    candidate_names = [item["company_name"]]
                else:
                    candidate_names = self._extract_company_names(snippet, title)

                for cname in candidate_names or ([title[:40]] if title else []):
                    key = cname.strip()
                    if not key or key in seen:
                        continue
                    cp = CompanyProfile(
                        company_name=key,
                        industry=item.get("industry", "") or "",
                        region=item.get("region", "") or "",
                        scale=item.get("scale", "") or "",
                        revenue_latest=item.get("revenue_latest", "") or "",
                        main_business=item.get("business_scope", "") or "",
                        registered_capital=item.get("registered_capital", "") or "",
                        establishment_date=item.get("establishment_date", "") or "",
                        keywords=[q],
                        evidence=[
                            KBEvidence(
                                source=result.source_name or "router",
                                snippet=(snippet or title)[:400],
                                url=url,
                            )
                        ],
                        extras={
                            "seed_query": q,
                            "degraded": bool(result.degraded),
                            "source_tier": result.source_name,
                        },
                    )
                    seen[key] = cp
                    new_count += 1
                    if len(seen) >= max_total:
                        break
                if len(seen) >= max_total:
                    break

            metas.append({
                "query": q, "status": "ok", "count": len(result.items),
                "new": new_count, "degraded": bool(result.degraded),
                "source_name": result.source_name,
            })

        return list(seen.values()), metas

    # ---- 信号时间线(裸 Tavily news) ----

    def fetch_signal_timeline(
        self,
        company_name: str,
        months: int = 12,
        limit: int = 5,
    ) -> list[SignalEvent]:
        """对 company_name 发一次 Tavily news query,组装近 N 月信号事件。

        走裸 TavilySource(不用 Router),保证 news query_type 直达;
        Tavily 无 key 时返回空 list(调用侧决定是否暴露 degraded)。
        """
        from shared.sources.registry import get, has
        from shared.sources.base import QueryRequest

        if not company_name or not has("tavily"):
            return []
        source = get("tavily")
        if not source.health():
            return []
        req = QueryRequest(
            query=f'"{company_name}" 最近 {months} 个月 新闻',
            query_type="news",
            filters={"search_depth": "basic"},
            limit=max(1, limit),
        )
        try:
            result = source.query(req)
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError):
            return []
        if not result.ok:
            return []
        events: list[SignalEvent] = []
        for item in result.items[:limit]:
            events.append(SignalEvent(
                event_type="news",
                title=(item.get("title") or "")[:120],
                source_url=item.get("url", "") or "",
                snippet=(item.get("snippet") or item.get("content") or "")[:300],
            ))
        return events
