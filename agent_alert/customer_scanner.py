# -*- coding: utf-8 -*-
"""Agent4 — 批量扫描编排引擎

对 KB 内全部在贷客户逐家跑 CrossMatcher，实时回调进度/命中信号，
最终组装成 HitList 返回。

关键设计：
- 同步逐家扫描即可满足 100 家 < 2 秒（不依赖 LLM），避免 asyncio 和 Gradio 的生成器冲突
- 提供 scan() 生成器接口：每处理一家 yield 一次进度事件，由上层 agent/app 转译为 tick 流
- 扩展：如需接真实 SearchProvider（带网络 IO），只需在 per-customer 处把 match_customer
  包成 asyncio.to_thread + Semaphore(8)，接口不变
"""

from __future__ import annotations
import time
from typing import Generator, Callable, Any

from shared.kb_scan.models import (
    HitItem, HitList, RiskLevel, CompanyProfile, ScanTarget,
)
from shared.kb_scan.hit_ranker import HitRanker
from shared.kb_scan.search_provider import SearchProvider

from .knowledge_base import AlertKnowledgeBase
from .cross_matcher import CrossMatcher


class ScanProgress:
    """进度事件。"""

    def __init__(
        self,
        kind: str,
        index: int = 0,
        total: int = 0,
        customer_name: str = "",
        level: RiskLevel | None = None,
        hit: HitItem | None = None,
        message: str = "",
    ):
        self.kind = kind                # "start" | "tick" | "hit" | "done"
        self.index = index
        self.total = total
        self.customer_name = customer_name
        self.level = level
        self.hit = hit
        self.message = message


class CustomerScanner:
    """贷中批量扫描引擎。"""

    def __init__(
        self,
        kb: AlertKnowledgeBase,
        search_provider: SearchProvider,
        matcher: CrossMatcher | None = None,
    ):
        self.kb = kb
        self.provider = search_provider
        self.matcher = matcher or CrossMatcher(search_provider)

    # ------------------------------------------------------------------
    # 同步扫描：一次返回 HitList（供简单调用）
    # ------------------------------------------------------------------
    def scan_all(self) -> HitList:
        hits: list[HitItem] = []
        for evt in self.scan():
            if evt.kind == "hit" and evt.hit is not None:
                hits.append(evt.hit)
        return self._build_hitlist(hits)

    # ------------------------------------------------------------------
    # 生成器扫描：供 agent 转译成事件流
    # ------------------------------------------------------------------
    def scan(self) -> Generator[ScanProgress, None, HitList]:
        customers = self._resolve_customers()
        total = len(customers)
        yield ScanProgress(kind="start", total=total,
                           message=f"开始批量扫描 {total} 家在贷客户")

        rules = self.kb.rules
        hits: list[HitItem] = []
        t0 = time.time()

        for i, profile in enumerate(customers, 1):
            try:
                hit = self.matcher.match_customer(profile, rules)
            except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError) as e:
                # 单家失败不阻断全流程
                yield ScanProgress(
                    kind="tick", index=i, total=total,
                    customer_name=profile.company_name,
                    message=f"扫描异常：{e}",
                )
                continue
            hits.append(hit)
            yield ScanProgress(
                kind="tick",
                index=i, total=total,
                customer_name=profile.company_name,
                level=hit.level,
            )
            if hit.level in (RiskLevel.RED, RiskLevel.YELLOW):
                yield ScanProgress(
                    kind="hit",
                    index=i, total=total,
                    customer_name=profile.company_name,
                    level=hit.level,
                    hit=hit,
                )
            else:
                # 仍把绿灯视为 hit 放入列表（但不推送 tick 的 hit 事件）
                yield ScanProgress(
                    kind="hit",
                    index=i, total=total,
                    customer_name=profile.company_name,
                    level=hit.level,
                    hit=hit,
                )

        duration = time.time() - t0
        hit_list = self._build_hitlist(hits, duration=duration)
        yield ScanProgress(
            kind="done",
            index=total, total=total,
            message=(f"扫描完成：🔴 {hit_list.red_count} 🟡 {hit_list.yellow_count} "
                     f"🟢 {hit_list.green_count} · 用时 {duration:.1f}s"),
        )
        return hit_list

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _resolve_customers(self) -> list[CompanyProfile]:
        """客户名录优先从 KB；若 KB 未上传，从 SearchProvider.iter_loan_customers 兜底。

        说明：KB 从 Excel 上传时，extras 的 key 可能是中文表头（"风险标签"等），
        匹配器只认英文 key。所以此处强制叠加 provider 侧的英文 extras
        （profit_latest/debt_ratio/narrative/risk_tags），保证下游统一消费英文字段。

        ALL IN Phase B step 6 (2026-05-09 · per CLAUDE.md §11 alert 边界 + entity-resolution-contract v1.1 §4):
        - provider_loans 索引由 company_name → EntityKey · USCC 优先 (uscc_X · confidence 1.0) · name fallback (name_md5)
        - 防同客户多源命名差异 (e.g. "腾讯" vs "腾讯科技深圳") 当 2 家
        - 在贷客户池归一 · 与 credit 决策对象 1:1 (跨 agent handoff 主键稳定)
        - dedupe 在 KB customers 内: 同 EntityKey 出现 2 次只保留首条
        """
        from shared.entity_resolver import resolve_entity

        def _key_of(c: CompanyProfile):
            return resolve_entity(name=c.company_name, uscc=c.unified_credit_code)

        if self.kb.companies:
            kb_customers = list(self.kb.companies)
            # KB 内同 EntityKey dedup · 防同客户多预警 (per §11)
            seen_keys: set = set()
            customers: list[CompanyProfile] = []
            for c in kb_customers:
                k = _key_of(c)
                if k in seen_keys:
                    continue  # 同实体已收 · 跳重复
                seen_keys.add(k)
                customers.append(c)

            # provider_loans 索引 EntityKey · 不再 string-eq company_name
            provider_loans = {
                _key_of(c): c for c in self.provider.iter_loan_customers()
            }
            for c in customers:
                pl = provider_loans.get(_key_of(c))
                if pl is None:
                    continue
                # 合并 extras：provider 侧（英文 key + narrative/risk_tags）为准，
                # KB 侧（中文表头）作为补充，避免丢失名录里独有的字段
                merged = {**(c.extras or {}), **(pl.extras or {})}
                c.extras = merged
                # risk_tags：优先 provider extras，其次 provider tags
                rt_from_extras = merged.get("risk_tags") or []
                if rt_from_extras:
                    c.risk_tags = list(rt_from_extras)
                elif pl.tags:
                    c.risk_tags = list(pl.tags)
            return customers
        # fallback：走 provider 全量 · 也按 EntityKey dedup
        provider_customers = list(self.provider.iter_loan_customers())
        seen_keys = set()
        deduped: list[CompanyProfile] = []
        for c in provider_customers:
            k = _key_of(c)
            if k in seen_keys:
                continue
            seen_keys.add(k)
            deduped.append(c)
        return deduped

    def _build_hitlist(self, hits: list[HitItem], duration: float = 0.0) -> HitList:
        ranker = HitRanker(agent_name="alert")
        hl = ranker.build(
            hits=hits,
            kb_summary=self.kb.summary(),
            scan_summary=(
                f"全量在贷客户 × 双路（外部：裁判文书/舆情 · 内部：管理制度）交叉扫描"
                + (f" · 用时 {duration:.1f}s" if duration else "")
            ),
            total_scanned=len(hits),
        )
        return hl
