# -*- coding: utf-8 -*-
"""Agent1 v2.0: ChannelMatchAgent — look-alike 获客引擎（知识库驱动）。

5 阶段流水线：
  ① KB 装载 → ② 画像抽取 → ③ 外网搜索 → ④ 匹配打分 → ⑤ 产品推荐 + 话术
"""
from __future__ import annotations

import os
import sys
import uuid
from typing import Generator

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.base_agent import BaseAgent
from shared.kb_scan.hit_ranker import HitRanker
from shared.kb_scan.models import HitList, IdealProfile, RiskLevel
from shared.kb_scan.search_provider import build_search_provider

from agent_channel.knowledge_base import ChannelKnowledgeBase
from agent_channel.profile_extractor import ProfileExtractor
from agent_channel.lead_finder import LeadSearcher, LookAlikeMatcher
from agent_channel.product_recommender import ProductRecommender


# ---------------------------------------------------------------------------
# 事件辅助（Agent1 专用 event types）
# ---------------------------------------------------------------------------

def _event(etype: str, **payload) -> dict:
    return {"type": etype, **payload}


class ChannelMatchAgent(BaseAgent):
    """全渠道流量匹配 Agent — v2.0 knowledge-base 扫描范式"""

    agent_name = "channel"
    agent_title = "全渠道流量匹配"

    # 扫描参数（默认值，可通过 process_message 的 scan_scope 覆盖）
    DEFAULT_TOP_N = 10
    DEFAULT_PER_QUERY_LIMIT = 50
    DEFAULT_MAX_CANDIDATES = 200

    # 红/黄分级阈值（兼容 look-alike 语义：≥80 强匹配 / 65-79 中匹配 / <65 弱匹配）
    LEVEL_THRESHOLDS = (80.0, 65.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 依赖底层（Mock/Web 由环境变量 / 参数切换）
        self.provider = build_search_provider(demo_mode=True)
        self.matcher = LookAlikeMatcher()
        self.ranker = HitRanker(agent_name=self.agent_name)
        self.lead_searcher = LeadSearcher(self.provider)
        self._last_hit_list: HitList | None = None

    # ---- 统一入口（给 Gradio / portal 调用） ----

    def process_message(
        self,
        user_message: str = "",
        uploaded_files: list[str] | None = None,
        *,
        top_n: int | None = None,
    ) -> Generator[dict, None, None]:
        """以 uploaded_files 作为 KB 三类文件（客户名录 + 政策 + 行业指引）。"""
        files = uploaded_files or []
        top_n = top_n or self.DEFAULT_TOP_N

        # ① KB 装载
        yield self._thinking("装载知识库文件...")
        kb = ChannelKnowledgeBase()
        metas = kb.load_mixed_files(files)
        for m in metas:
            if m.get("status") == "ok":
                info_parts = []
                if "added_companies" in m:
                    info_parts.append(f"客户 {m['added_companies']} 家")
                if "added_clauses" in m:
                    info_parts.append(f"政策条款 {m['added_clauses']} 条")
                if "added_rules" in m:
                    info_parts.append(f"规则 {m['added_rules']} 条")
                if "note" in m and "industry_guide" in m.get("note", ""):
                    info_parts.append(f"行业指引 {len(m.get('raw_text',''))} 字")
                info = " / ".join(info_parts) or m.get("type", "?")
                yield self._tool_result("load_kb", f"✓ {os.path.basename(m.get('path',''))} · {info}")
            else:
                yield self._tool_result("load_kb", f"✗ {os.path.basename(m.get('path',''))} · {m.get('error') or m.get('reason','未知错误')}")
        if not kb.companies and not kb.clauses and not kb.industry_guide_texts:
            yield self._message("⚠️ 未从上传文件中解析出有效的客户名录/政策/行业指引，请检查文件格式。")
            yield self._done("KB 装载失败")
            return
        yield self._message(f"**知识库摘要**：{kb.summary()}")

        # ② 画像抽取
        yield self._thinking("LLM 抽取理想客户画像（可能 10-20 秒）...")
        extractor = ProfileExtractor(llm_caller=self._safe_llm_json)
        ideal = extractor.extract(kb)
        yield _event("profile", profile=ideal.model_dump())
        yield self._message(
            f"**画像已生成**：{ideal.name}\n"
            f"- 目标行业：{', '.join(ideal.target_industries) or '（不限）'}\n"
            f"- 目标地域：{', '.join(ideal.target_regions) or '（不限）'}\n"
            f"- 规模范围：{', '.join(ideal.scale_range) or '（不限）'}\n"
            f"- 必备标签：{', '.join(ideal.must_have_tags) or '（无）'}\n"
            f"- 加分标签：{', '.join(ideal.nice_to_have_tags) or '（无）'}\n"
            f"- 排除标签：{', '.join(ideal.exclude_tags) or '（无）'}\n"
            f"- 画像依据：{ideal.reasoning}"
        )

        # ③ 外网搜索
        yield self._thinking("基于画像搜索候选企业池...")
        candidates, search_metas = self.lead_searcher.search_candidates(
            ideal,
            per_query_limit=self.DEFAULT_PER_QUERY_LIMIT,
            max_total=self.DEFAULT_MAX_CANDIDATES,
        )
        for m in search_metas:
            if m.get("status") == "ok":
                yield self._tool_result(
                    "search_companies",
                    f"query='{m['query']}' · 命中 {m['count']} 家，新增 {m['new']} 家",
                )
            else:
                yield self._tool_result("search_companies", f"query='{m['query']}' · 失败: {m.get('error','')}")
        yield self._message(f"**搜索完成**：累计候选 {len(candidates)} 家（已去重）")
        if not candidates:
            yield self._message("⚠️ 未命中任何候选企业，建议放宽画像筛选条件。")
            yield self._done("无候选企业")
            return

        # ④ 匹配打分
        yield self._thinking(f"对 {len(candidates)} 家候选做 look-alike 打分...")
        hits = self.matcher.match_all_against_ideal(
            candidates=candidates,
            ideal=ideal,
            anchors=kb.companies,
            top_anchor_k=3,
        )

        hit_list = self.ranker.build(
            hits,
            kb_summary=kb.summary(),
            scan_summary=f"扫描 {len(candidates)} 家候选",
            total_scanned=len(candidates),
            level_thresholds=self.LEVEL_THRESHOLDS,
        )
        # 覆盖 ranker 默认 level 推断（match_one 阶段 hits 全都预设为 GREEN，
        # 在 ranker.build 中会被视为"已定级"跳过；这里强制按阈值重新定级）
        hi, mid = self.LEVEL_THRESHOLDS
        for h in hit_list.hits:
            if h.score >= hi:
                h.level = RiskLevel.RED
            elif h.score >= mid:
                h.level = RiskLevel.YELLOW
            else:
                h.level = RiskLevel.GREEN
        # 只保留 Top N
        hit_list.hits = hit_list.hits[:top_n]
        hit_list.recount()
        yield self._message(
            f"**Top{len(hit_list.hits)} 筛选完成**：🔴{hit_list.red_count} / 🟡{hit_list.yellow_count} / 🟢{hit_list.green_count}"
        )

        # ⑤ 产品推荐 + 话术
        yield self._thinking("为每条线索匹配 Top3 产品并批量生成话术...")
        recommender = ProductRecommender(
            llm_chat=self._safe_llm_chat,
            llm_json=self._safe_llm_json,
        )
        for h in hit_list.hits:
            recommender.enrich_hit(h, ideal, top_n=3)
        pitches = recommender.batch_generate_pitches(hit_list.hits, ideal)
        for h in hit_list.hits:
            h.extras["pitch_script"] = pitches.get(h.hit_id, "")

        # 输出线索榜（结构化事件 + 可读 markdown）
        self._last_hit_list = hit_list
        yield _event("hit_list", list_id=hit_list.list_id,
                     hits=[h.model_dump() for h in hit_list.hits])
        yield self._message(self._render_markdown(hit_list, ideal))
        yield self._done(f"look-alike 扫描完成：Top{len(hit_list.hits)}")

    # ---- 外部可取最后一次 HitList（给导出按钮用） ----
    def get_last_hit_list(self) -> HitList | None:
        return self._last_hit_list

    # ---- LLM 调用安全包装 ----

    def _safe_llm_json(self, system: str, user: str) -> dict | None:
        try:
            out = self.llm_json(system=system, user=user)
            if isinstance(out, dict):
                return out
            return None
        except Exception:
            return None

    def _safe_llm_chat(self, system: str, user: str) -> str:
        try:
            return self.llm_chat(system=system, user=user) or ""
        except Exception:
            return ""

    # ---- Markdown 渲染 ----

    @staticmethod
    def _render_markdown(hl: HitList, ideal: IdealProfile) -> str:
        lvl_emoji = {RiskLevel.RED: "🔴", RiskLevel.YELLOW: "🟡",
                     RiskLevel.GREEN: "🟢", RiskLevel.INFO: "ℹ️"}
        lvl_label = {RiskLevel.RED: "强匹配", RiskLevel.YELLOW: "中匹配",
                     RiskLevel.GREEN: "弱匹配", RiskLevel.INFO: "提示"}
        lines = [
            "---",
            f"## look-alike 线索榜 Top{len(hl.hits)}\n",
            f"- 画像：**{ideal.name}**",
            f"- 共扫描候选：{hl.total_scanned} 家",
            f"- 分级：🔴{hl.red_count} · 🟡{hl.yellow_count} · 🟢{hl.green_count}",
            "",
        ]
        for h in hl.hits:
            p = h.target.payload or {}
            products = h.extras.get("recommended_products") or []
            anchors = h.extras.get("top_anchors") or []
            lines.append(
                f"### #{h.rank} {lvl_emoji.get(h.level,'·')} "
                f"[{lvl_label.get(h.level,'')} {h.score:.1f}分] {p.get('company_name','')}"
            )
            lines.append(
                f"- 行业：{p.get('industry','')}（{p.get('sub_industry','')}）"
                f" · 地域：{p.get('region','')}"
                f" · 规模：{p.get('scale','')}"
                f" · 营收：{p.get('revenue_latest','')}"
            )
            if h.reasons:
                lines.append("- 匹配理由：")
                for r in h.reasons[:5]:
                    lines.append(f"  - {r}")
            if anchors:
                lines.append("- 相似样本锚：" + "、".join(
                    f"{a.get('name','')}({a.get('score',0):.1f})"
                    for a in anchors[:3]
                ))
            if products:
                lines.append("- 推荐产品 Top3：")
                for p_i in products[:3]:
                    lines.append(
                        f"  - [{p_i.get('category','')}] {p_i.get('channel_name','')}"
                        f" · {p_i.get('score',0)}分 · 额度{p_i.get('max_amount','')}"
                    )
            pitch = h.extras.get("pitch_script") or ""
            if pitch:
                lines.append(f"- 切入话术：> {pitch}")
            lines.append("")
        return "\n".join(lines)
