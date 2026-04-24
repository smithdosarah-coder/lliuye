# -*- coding: utf-8 -*-
"""Look-alike KB matcher — 从 data/mock/channel-kb/historical-clients/*.{md,docx}
确定性装载"已成交客户锚",对外部 candidate 做三维 Jaccard 打分。

约束 (Batch 2 · §3.1 + §3.5):
    - 打分全走 Python / set-Jaccard,不走 LLM
    - 三维独立打分 → 加权合成 match_score ∈ [0, 1]
    - 和 lead_finder.LookAlikeMatcher(画像锚相似度)并存:
        * lead_finder 走 ideal-profile vs candidate 规则打分(画像驱动)
        * 本模块走 historical-client vs candidate Jaccard(银行侧稳态 KB 驱动)
        * 两者合成发生在上层 pipeline (ChannelMatchAgent 可任选一条)

文件格式约定:
    .md 结构: ## 基本信息 → - 行业: xxx / - 区域: xxx / - 规模: xxx
             ## 业务特征 → bullets
             ## 成交情况 → - 首次成交: ... / - 授信额度: ...
    .docx 结构相同,段落扁平化
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path


# 规模档:映射 candidate/client 的"规模"描述到 3 档
_SCALE_BUCKETS = {
    "微型": "S", "小微": "S", "小型": "S",
    "中型": "M",
    "大型": "L", "巨型": "L", "大": "L",
}

# 资质关键词(和 seed_query_builder 的 _QUAL_PATTERNS 同源;独立维护避免耦合)
_QUAL_TOKENS = [
    "专精特新", "高新技术", "科技型中小",
    "专利", "ISO", "AAA",
    "省级", "国家级", "规上",
]

# 行业归一化:粗粒度桶,避免 "先进制造业" vs "装备制造" 之间 0 overlap
_INDUSTRY_CANON = {
    "制造": "制造业",
    "装备": "制造业",
    "机械": "制造业",
    "精密": "制造业",
    "电子": "电子信息",
    "半导体": "电子信息",
    "软件": "信息技术",
    "信息": "信息技术",
    "SaaS": "信息技术",
    "物流": "物流",
    "运输": "物流",
    "医疗": "医疗器械",
    "医药": "医疗器械",
    "生鲜": "农食",
    "食品": "农食",
    "家纺": "纺织",
    "纺织": "纺织",
    "建材": "建材",
    "培训": "教育",
    "教育": "教育",
}


@dataclass
class HistoricalClient:
    """一家已成交客户锚。"""
    source_doc: str
    company_name: str = ""
    industry: str = ""
    region: str = ""
    scale: str = ""
    qualifications: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class MatchBreakdown:
    industry: float = 0.0
    scale: float = 0.0
    qualifications: float = 0.0


def _canon_industry_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    if not text:
        return tokens
    for key, canon in _INDUSTRY_CANON.items():
        if key in text:
            tokens.add(canon)
    # 原词也加入,做 substring-fallback
    for seg in re.split(r"[/,，、]", text):
        seg = seg.strip()
        if 2 <= len(seg) <= 8:
            tokens.add(seg)
    return tokens


def _scale_bucket(scale_text: str, revenue_text: str = "") -> str:
    """返回 S/M/L,未知返回空串。"""
    if not scale_text and not revenue_text:
        return ""
    s = (scale_text or "") + " " + (revenue_text or "")
    for key, bucket in _SCALE_BUCKETS.items():
        if key in s:
            return bucket
    # 再按营收数字粗粒度判断
    m = re.search(r"(\d+(?:\.\d+)?)\s*(万|亿)", s)
    if m:
        val = float(m.group(1)) * (10000.0 if m.group(2) == "亿" else 1.0)
        if val < 5000:
            return "S"
        if val < 50000:
            return "M"
        return "L"
    return ""


def _extract_qualifications(text: str) -> list[str]:
    found: list[str] = []
    for tok in _QUAL_TOKENS:
        if tok in text and tok not in found:
            found.append(tok)
    # 抓"专利 X 项"数字资质
    patent_m = re.search(r"专利\s*\d+\s*项", text)
    if patent_m and patent_m.group(0) not in found:
        found.append(patent_m.group(0))
    return found


# -----------------------------------------------------------------------------
# Parsers
# -----------------------------------------------------------------------------

def _parse_md(path: Path) -> HistoricalClient:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return HistoricalClient(source_doc=str(path))
    return _parse_text_flat(text, path)


def _parse_docx(path: Path) -> HistoricalClient:
    try:
        import docx
    except ImportError:
        return HistoricalClient(source_doc=str(path))
    try:
        doc = docx.Document(str(path))
    except (OSError, ValueError, KeyError):
        return HistoricalClient(source_doc=str(path))
    text = "\n".join(p.text for p in doc.paragraphs if p.text and p.text.strip())
    return _parse_text_flat(text, path)


def _parse_text_flat(text: str, path: Path) -> HistoricalClient:
    """从扁平化文本里抽字段。兼容 md bullet 和 docx 段落。"""
    # 行业 / 区域 / 规模 / 营收:容忍 "- 行业：制造业" / "行业: xxx" / "行业 xxx"
    def _pick(label: str) -> str:
        # 兼容:
        #   行业：xxx
        #   - 行业：xxx
        #   - **行业**：xxx
        #   * 行业: xxx
        pattern = (
            r"[-*•·]?\s*\**\s*" + re.escape(label) + r"\s*\**\s*[:：]\s*([^\n]+)"
        )
        m = re.search(pattern, text)
        if m:
            return m.group(1).strip().strip("*").strip()
        return ""

    industry = _pick("行业")
    region = _pick("区域") or _pick("地区")
    scale = _pick("规模")
    revenue = _pick("营收") or _pick("营业额")
    # 从文件名兜底 company_name
    name_raw = path.stem
    name = name_raw.replace("_", "").strip()

    scale_bucket = _scale_bucket(scale, revenue)
    quals = _extract_qualifications(text)

    # tags:松散抓 "业务特征" 段或"客户经理备注"段里的关键词
    tags: list[str] = []
    feat_m = re.search(r"(业务特征|业务特点|经营特点)[\s\S]{0,400}", text)
    if feat_m:
        for line in feat_m.group(0).split("\n"):
            line = line.strip("- *•\t 　")
            if 3 <= len(line) <= 20:
                tags.append(line)
            if len(tags) >= 6:
                break

    return HistoricalClient(
        source_doc=str(path),
        company_name=name,
        industry=industry,
        region=region,
        scale=scale_bucket,
        qualifications=quals,
        tags=tags,
    )


def load_historical_clients(kb_dir: str | Path) -> list[HistoricalClient]:
    """装载 data/mock/channel-kb/historical-clients/ 下所有 .md/.docx 为锚。

    解析失败的文件被跳过(不抛)。
    """
    base = Path(kb_dir)
    if not base.is_dir():
        return []
    out: list[HistoricalClient] = []
    for fname in sorted(os.listdir(base)):
        lname = fname.lower()
        fpath = base / fname
        if lname.endswith(".md"):
            out.append(_parse_md(fpath))
        elif lname.endswith(".docx"):
            out.append(_parse_docx(fpath))
    return [c for c in out if c.company_name or c.industry]


# -----------------------------------------------------------------------------
# Scorer
# -----------------------------------------------------------------------------

def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


class LookAlikeKBMatcher:
    """对外部 candidate 逐家算三维 Jaccard + 加权 → match_score ∈ [0, 1]。

    权重默认 industry=0.5 / scale=0.2 / qualifications=0.3。
    """

    def __init__(
        self,
        clients: list[HistoricalClient],
        weights: dict[str, float] | None = None,
    ):
        self.clients = clients
        default_w = {"industry": 0.5, "scale": 0.2, "qualifications": 0.3}
        self.weights = {**default_w, **(weights or {})}
        # 预计算每家 client 的三维集合,省重复 tokenize
        self._client_tokens = [
            {
                "industry": _canon_industry_tokens(c.industry),
                "scale": {c.scale} if c.scale else set(),
                "qualifications": set(c.qualifications),
            }
            for c in clients
        ]

    def score(
        self, candidate: dict,
    ) -> tuple[float, dict[str, float], list[HistoricalClient]]:
        """
        candidate dict 字段(和 CompanyProfile.model_dump() 一致):
            industry, scale, revenue_latest, qualifications
        返回 (match_score, breakdown, top3_anchors)。
        """
        if not self.clients:
            return 0.0, {"industry": 0.0, "scale": 0.0, "qualifications": 0.0}, []

        cand_ind = _canon_industry_tokens(candidate.get("industry", ""))
        cand_scale = {
            _scale_bucket(candidate.get("scale", ""), candidate.get("revenue_latest", ""))
        } - {""}
        cand_quals = set(candidate.get("qualifications") or [])
        # 补:从 tags 抓资质关键词
        for t in (candidate.get("tags") or []):
            for qt in _QUAL_TOKENS:
                if qt in t:
                    cand_quals.add(qt)

        per_dim = {"industry": 0.0, "scale": 0.0, "qualifications": 0.0}
        per_client_scores: list[tuple[HistoricalClient, float]] = []
        for client, tok in zip(self.clients, self._client_tokens):
            s_ind = _jaccard(cand_ind, tok["industry"])
            s_scale = _jaccard(cand_scale, tok["scale"])
            s_qual = _jaccard(cand_quals, tok["qualifications"])
            # 每维取 max(across clients)
            per_dim["industry"] = max(per_dim["industry"], s_ind)
            per_dim["scale"] = max(per_dim["scale"], s_scale)
            per_dim["qualifications"] = max(per_dim["qualifications"], s_qual)
            # 单家合成分(用于 top-k anchor)
            combined = (
                self.weights["industry"] * s_ind
                + self.weights["scale"] * s_scale
                + self.weights["qualifications"] * s_qual
            )
            per_client_scores.append((client, combined))

        match_score = round(
            self.weights["industry"] * per_dim["industry"]
            + self.weights["scale"] * per_dim["scale"]
            + self.weights["qualifications"] * per_dim["qualifications"],
            4,
        )
        match_score = max(0.0, min(match_score, 1.0))

        per_client_scores.sort(key=lambda x: x[1], reverse=True)
        top3 = [c for c, s in per_client_scores[:3] if s > 0]

        breakdown = {k: round(v, 4) for k, v in per_dim.items()}
        return match_score, breakdown, top3
