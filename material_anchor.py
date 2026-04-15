"""
MaterialAnchor — 从客户提供的 docx/xlsx 材料中抽取结构化锚点块。

解决的问题:
  Phase1 证据组装依赖 LLM 自己在全文本中搜索,容易漏掉表格信息
  (如融资清单/上下游客户/关联企业/资产明细)。
  本模块把这些表格直接解析成结构化锚点,注入到 company_profile,
  让 LLM 在写征信/还款/担保/经营段时能看到现成的真实数据。

目前针对:
  交行-xxx授信补充问题及材料1.docx (8 个标准表格)
  可扩展:在 parse_docx_tables 里增加 detector。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import os

try:
    from docx import Document
except ImportError:
    Document = None


# ------------------------------------------------------------------
# 数据结构
# ------------------------------------------------------------------
@dataclass
class FinancingRecord:
    lender: str
    product: str
    credit_amount: str  # 授信金额 万元
    used_amount: str
    start_date: str
    end_date: str
    guarantee: str


@dataclass
class PartnerRecord:
    """上游供应商 / 下游客户."""
    name: str
    goods_or_product: str
    amount: str  # 万元
    share_pct: str
    settlement: str = ""
    term: str = ""


@dataclass
class RelatedCompany:
    name: str
    established: str
    ownership: str
    business: str
    registered_capital: str
    revenue: str
    net_profit: str
    revenue_suspect: bool = False          # 数据层自检:revenue 列对齐疑点
    profit_suspect: bool = False           # 数据层自检:net_profit 列对齐疑点
    suspect_reason: str = ""               # 具体疑点说明


@dataclass
class AssetRecord:
    name: str
    owner: str
    asset_type: str
    ownership_cert: str
    size_info: str
    book_value: str
    market_value: str
    pledge_status: str


@dataclass
class RDRecord:
    year: str
    rd_expense: str
    rd_ratio: str
    rd_headcount: str
    rd_headcount_ratio: str


@dataclass
class MaterialAnchor:
    upstream: list[PartnerRecord] = field(default_factory=list)
    downstream: list[PartnerRecord] = field(default_factory=list)
    financing: list[FinancingRecord] = field(default_factory=list)
    related_companies: list[RelatedCompany] = field(default_factory=list)
    assets: list[AssetRecord] = field(default_factory=list)
    rd_records: list[RDRecord] = field(default_factory=list)
    industry_cards: list[dict] = field(default_factory=list)  # V14 G1:自动匹配的行业/政策参考卡片

    def is_empty(self) -> bool:
        return not any([
            self.upstream, self.downstream, self.financing,
            self.related_companies, self.assets, self.rd_records,
            self.industry_cards,
        ])

    def format_for_prompt(self) -> str:
        """格式化为 prompt anchor block,用于注入 company_profile。"""
        if self.is_empty():
            return ""
        lines = []
        lines.append("【结构化材料锚点(从客户补充材料表格精确抽取,撰写时优先引用)】")

        if self.financing:
            total_credit = sum(_to_float(r.credit_amount) for r in self.financing)
            total_used = sum(_to_float(r.used_amount) for r in self.financing)
            lines.append(f"[融资清单 共{len(self.financing)}笔,授信合计{total_credit:.0f}万元,"
                         f"已用{total_used:.0f}万元]")
            for r in self.financing:
                lines.append(f"  · {r.lender} / {r.product} / 授信{r.credit_amount}万元 / "
                             f"已用{r.used_amount}万元 / {r.start_date}~{r.end_date} / 担保:{r.guarantee}")

        if self.downstream:
            total_ds = sum(_to_float(r.amount) for r in self.downstream)
            lines.append(f"[主要下游客户(上年前{len(self.downstream)}大,合计{total_ds:.0f}万元)]")
            for r in self.downstream:
                lines.append(f"  · {r.name} / {r.goods_or_product} / {r.amount}万 / 占比{r.share_pct}")

        if self.upstream:
            total_us = sum(_to_float(r.amount) for r in self.upstream)
            lines.append(f"[主要上游供应商(上年前{len(self.upstream)}大,合计{total_us:.0f}万元)]")
            for r in self.upstream:
                lines.append(f"  · {r.name} / {r.goods_or_product} / {r.amount}万 / 占比{r.share_pct}")

        if self.related_companies:
            lines.append(f"[关联企业/子公司({len(self.related_companies)}家,多为本借款人100%控股,常担任保证人)]")
            lines.append("  ⚠ 以下每个数字均标注所属主体,写作时禁止把任一关联企业的数字挪到另一家或借款人本身。")
            for c in self.related_companies:
                lines.append(f"  · 关联企业「{c.name}」: 成立{c.established} | 股权{c.ownership} | "
                             f"主营{c.business} | 注册资本{c.registered_capital}万")
                # V12: 营收遮蔽策略
                rev_f = _to_float(c.revenue)
                if c.revenue_suspect:
                    lines.append(f"      · 上年营收(主体「{c.name}」):材料数据可疑[{c.suspect_reason}],请人工核实")
                elif abs(rev_f) < 1:
                    lines.append(f"      · 上年营收(主体「{c.name}」):上年无主营业务收入")
                else:
                    lines.append(f"      · 上年营收(主体「{c.name}」):{c.revenue}万")
                # V12: 净利润遮蔽策略
                prof_f = _to_float(c.net_profit)
                if c.profit_suspect:
                    lines.append(f"      · 上年净利润(主体「{c.name}」):材料数据可疑[{c.suspect_reason}],请人工核实")
                elif abs(prof_f) < 1:
                    lines.append(f"      · 上年净利润(主体「{c.name}」):净利润规模极小(不足1万元),可忽略")
                elif prof_f < 0:
                    lines.append(f"      · 上年净利润(主体「{c.name}」):净亏损{abs(prof_f):.0f}万(即负{abs(prof_f):.0f}万)")
                else:
                    lines.append(f"      · 上年净利润(主体「{c.name}」):{c.net_profit}万")

        if self.assets:
            lines.append(f"[可抵押资产清单({len(self.assets)}项)]")
            for a in self.assets:
                lines.append(f"  · {a.name} / 所有权人:{a.owner} / 类型:{a.asset_type} / "
                             f"权属证:{a.ownership_cert} / 规模:{a.size_info} / "
                             f"账面价:{a.book_value}万 / 评估价:{a.market_value}万 / 抵押:{a.pledge_status}")

        if self.rd_records:
            lines.append(f"[研发投入(近{len(self.rd_records)}年)]")
            for r in self.rd_records:
                lines.append(f"  · {r.year}年 研发费用{r.rd_expense}万 / 占比{r.rd_ratio} / "
                             f"研发人员{r.rd_headcount}人(占比{r.rd_headcount_ratio})")

        # V14 G1:行业/政策参考卡片(LLM 外因分析可直接引用;编号之外的禁编)
        if self.industry_cards:
            lines.append("")
            lines.append("【行业/政策参考卡片】(自动匹配,供外因分析引用。严禁编造未在此块列出的行业数字/政策)")
            for card in self.industry_cards:
                head = f"  ▸ 卡片: {card.get('industry', '')}"
                code = card.get("industry_code") or ""
                if code:
                    head += f" ({code})"
                lines.append(head)
                bench = card.get("benchmarks") or {}
                for m, rng in bench.items():
                    lines.append(f"      - {m}: {rng}")
                for pol in (card.get("key_policies") or []):
                    lines.append(f"      - 政策: {pol}")
                trend = card.get("industry_trends") or ""
                if trend:
                    lines.append(f"      - 趋势: {trend}")
                peer = card.get("peer_benchmark") or ""
                if peer:
                    lines.append(f"      - 同业中位数: {peer}")
                src = card.get("source") or ""
                if src:
                    lines.append(f"      - 来源: {src}")

        return "\n".join(lines)


def _to_float(s: str) -> float:
    if not s:
        return 0.0
    try:
        return float(str(s).replace(",", "").strip())
    except Exception:
        return 0.0


def _validate_related_company_row(rc: "RelatedCompany") -> "RelatedCompany":
    """对关联企业行做合理性自检,避免把错位/张冠李戴的数字喂给 LLM。
    触发条件:
      1. 营收 0 且净利润显著非零(>100 万) → 数学不自洽,两列都标可疑
      2. 净利润 > 营收 * 1.5 (且净利润 > 50 万) → 超反常,净利润列可疑
      3. 净利润为负且绝对值 > 营收(且营收 > 0)→ 净利润列可疑
    """
    rev = _to_float(rc.revenue)
    prof = _to_float(rc.net_profit)
    reasons: list[str] = []
    if rev == 0 and abs(prof) > 100:
        rc.revenue_suspect = True
        rc.profit_suspect = True
        reasons.append(f"0收入但净利润{prof:.0f}万,数学不自洽")
    elif rev > 0 and prof > 0 and prof > rev * 1.5 and prof > 50:
        rc.profit_suspect = True
        reasons.append(f"净利润({prof:.0f}万)>1.5倍营收({rev:.0f}万),列对齐可疑")
    elif rev > 0 and prof < 0 and abs(prof) > rev:
        rc.profit_suspect = True
        reasons.append(f"亏损额({abs(prof):.0f}万)超过营收({rev:.0f}万),列对齐可疑")
    rc.suspect_reason = ";".join(reasons)
    return rc


def _cell(row, idx: int) -> str:
    cells = list(row.cells)
    if idx >= len(cells):
        return ""
    return (cells[idx].text or "").replace("\n", " ").strip()


# ------------------------------------------------------------------
# docx 表格解析
# ------------------------------------------------------------------
def parse_docx_tables(docx_path: str) -> MaterialAnchor:
    """从 docx 中识别并抽取 8 种标准表格。按首行表头判别类型。"""
    if Document is None:
        return MaterialAnchor()
    try:
        doc = Document(docx_path)
    except Exception:
        return MaterialAnchor()

    anchor = MaterialAnchor()

    for tbl in doc.tables:
        if not tbl.rows:
            continue
        header = [(_cell(tbl.rows[0], i)) for i in range(len(tbl.rows[0].cells))]
        header_joined = " ".join(header)

        # 融资清单
        if "融资机构" in header_joined and "授信金额" in header_joined:
            for row in tbl.rows[1:]:
                lender = _cell(row, 0)
                if not lender or lender == "合计":
                    continue
                anchor.financing.append(FinancingRecord(
                    lender=lender,
                    product=_cell(row, 1),
                    credit_amount=_cell(row, 2),
                    used_amount=_cell(row, 3),
                    start_date=_cell(row, 4),
                    end_date=_cell(row, 5),
                    guarantee=_cell(row, 6),
                ))
            continue

        # 下游客户
        if "下游" in header_joined or "销售客户" in header_joined:
            for row in tbl.rows[1:]:
                name = _cell(row, 0)
                if not name or name == "合计":
                    continue
                anchor.downstream.append(PartnerRecord(
                    name=name,
                    goods_or_product=_cell(row, 1),
                    amount=_cell(row, 2),
                    share_pct=_cell(row, 3),
                    settlement=_cell(row, 4),
                    term=_cell(row, 5),
                ))
            continue

        # 上游供应商
        if "上游" in header_joined or "供应商" in header_joined:
            for row in tbl.rows[1:]:
                name = _cell(row, 0)
                if not name or name == "合计":
                    continue
                anchor.upstream.append(PartnerRecord(
                    name=name,
                    goods_or_product=_cell(row, 1),
                    amount=_cell(row, 2),
                    share_pct=_cell(row, 3),
                    settlement=_cell(row, 4),
                    term=_cell(row, 5),
                ))
            continue

        # 关联企业
        if "企业名称" in header_joined and "股权结构" in header_joined:
            for row in tbl.rows[1:]:
                name = _cell(row, 0)
                if not name:
                    continue
                rc = RelatedCompany(
                    name=name,
                    established=_cell(row, 1),
                    ownership=_cell(row, 2),
                    business=_cell(row, 3),
                    registered_capital=_cell(row, 4),
                    revenue=_cell(row, 5),
                    net_profit=_cell(row, 6),
                )
                anchor.related_companies.append(_validate_related_company_row(rc))
            continue

        # 资产/房产
        if "资产名称" in header_joined and ("账面" in header_joined or "评估" in header_joined):
            for row in tbl.rows[1:]:
                name = _cell(row, 0)
                if not name:
                    continue
                anchor.assets.append(AssetRecord(
                    name=name,
                    owner=_cell(row, 1),
                    asset_type=_cell(row, 2),
                    ownership_cert=_cell(row, 3),
                    size_info=_cell(row, 4),
                    book_value=_cell(row, 5),
                    market_value=_cell(row, 6),
                    pledge_status=_cell(row, 8),
                ))
            continue

        # 研发投入
        if ("研发费用" in header_joined or "研发投入" in header_joined):
            for row in tbl.rows[1:]:
                year = _cell(row, 0)
                if not year:
                    continue
                anchor.rd_records.append(RDRecord(
                    year=year,
                    rd_expense=_cell(row, 1),
                    rd_ratio=_cell(row, 2),
                    rd_headcount=_cell(row, 3),
                    rd_headcount_ratio=_cell(row, 4),
                ))
            continue

    return anchor


# ------------------------------------------------------------------
# 对外 API
# ------------------------------------------------------------------
def build_material_anchor(
    file_path_map: dict[str, str],
    company_profile: str | None = None,
    extra_keywords: list[str] | None = None,
    top_k: int = 3,
) -> MaterialAnchor:
    """遍历 file_path_map,识别补充材料 docx 并抽取 anchor。

    V14 G1 扩展:
      - 基于 company_profile 文本 + material_anchor 的上下游商品类型 +
        额外 keywords,调 industry_cards.find_cards() 自动匹配 top_k 张行业卡,
        挂到 anchor.industry_cards。
    """
    anchor = MaterialAnchor()
    if not file_path_map:
        # 仍允许通过 extra_keywords / company_profile 匹配卡片
        pass
    else:
        for fname, fpath in file_path_map.items():
            if not fpath.lower().endswith(".docx"):
                continue
            # 识别补充材料 docx(包含"补充"或"授信补充"字样)
            base = os.path.basename(fpath)
            if "补充" in base or "授信" in base:
                part = parse_docx_tables(fpath)
                anchor.upstream.extend(part.upstream)
                anchor.downstream.extend(part.downstream)
                anchor.financing.extend(part.financing)
                anchor.related_companies.extend(part.related_companies)
                anchor.assets.extend(part.assets)
                anchor.rd_records.extend(part.rd_records)

    # V14 G1:匹配行业卡片
    try:
        from industry_cards import find_cards
        kws: list[str] = []
        if company_profile:
            kws.append(str(company_profile))
        # 从上下游商品类型抽关键词
        for r in list(anchor.upstream) + list(anchor.downstream):
            if r.goods_or_product:
                kws.append(r.goods_or_product)
        # 从关联企业主营业务抽关键词
        for rc in anchor.related_companies:
            if rc.business:
                kws.append(rc.business)
        if extra_keywords:
            kws.extend([str(k) for k in extra_keywords if k])
        cards = find_cards(kws, top_k=top_k) if kws else []
        if cards:
            anchor.industry_cards = [c.to_dict() for c in cards]
    except Exception:
        pass

    return anchor


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    test_path = r"D:\刘野\众安\新建文件夹\2026.3.25续贷材料\交行-中锐网络授信补充问题及材料1.docx"
    anc = parse_docx_tables(test_path)
    print(anc.format_for_prompt())
