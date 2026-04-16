"""
QualityScorer — 信贷报告质量评分器 v2

9 个评分维度 + 1 个罚分项，总分 100。
规则层覆盖 ~60% 锚点，LLM 层可选（llm_caller）覆盖其余 ~40%。

用法:
    scorer = QualityScorer()
    report = scorer.score(text, source_file="path/to/report.txt")
    print(report.to_markdown())

合格线: 总分 >= 75 且无一票否决。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional, Any


# -------------------------------------------------------------------
# 数据契约
# -------------------------------------------------------------------
@dataclass
class DimensionScore:
    name: str
    weight: float
    raw_score: float  # 0-10
    weighted_score: float  # raw * weight / 10
    hit_items: list[str] = field(default_factory=list)
    missed_items: list[str] = field(default_factory=list)
    evidence_snippets: list[str] = field(default_factory=list)
    llm_comment: str = ""


@dataclass
class Hallucination:
    text: str
    reason: str
    location: str


@dataclass
class QualityReport:
    generated_text_file: str
    total_score: float
    total_score_before_penalty: float
    fatal_fail: bool
    fatal_reasons: list[str]
    dimensions: list[DimensionScore]
    hallucinations: list[Hallucination]
    pass_threshold: float = 75.0
    passed: bool = False

    def to_json(self) -> dict:
        return {
            "generated_text_file": self.generated_text_file,
            "total_score": round(self.total_score, 2),
            "total_score_before_penalty": round(self.total_score_before_penalty, 2),
            "fatal_fail": self.fatal_fail,
            "fatal_reasons": self.fatal_reasons,
            "pass_threshold": self.pass_threshold,
            "passed": self.passed,
            "dimensions": [
                {
                    "name": d.name,
                    "weight": d.weight,
                    "raw_score": round(d.raw_score, 2),
                    "weighted_score": round(d.weighted_score, 2),
                    "hit_items": d.hit_items,
                    "missed_items": d.missed_items,
                    "evidence_snippets": d.evidence_snippets,
                    "llm_comment": d.llm_comment,
                }
                for d in self.dimensions
            ],
            "hallucinations": [asdict(h) for h in self.hallucinations],
        }

    def to_markdown(self) -> str:
        lines: list[str] = []
        lines.append(f"# 质量评分报告")
        lines.append("")
        lines.append(f"- 报告文件: `{self.generated_text_file}`")
        lines.append(f"- 合格线: {self.pass_threshold}")
        lines.append(
            f"- 总分(扣罚前): **{self.total_score_before_penalty:.2f}** / 100"
        )
        lines.append(f"- 总分(扣罚后): **{self.total_score:.2f}** / 100")
        if self.fatal_fail:
            lines.append(f"- 一票否决: **是**")
            for r in self.fatal_reasons:
                lines.append(f"    - {r}")
        else:
            lines.append(f"- 一票否决: 否")
        lines.append(
            f"- 最终判定: **{'合格' if self.passed else '不合格'}**"
        )
        lines.append("")
        lines.append("## 维度明细")
        lines.append("")
        lines.append(
            "| # | 维度 | 权重 | 原始分 | 加权分 | 命中 | 缺失 |"
        )
        lines.append("|---|---|---|---|---|---|---|")
        for i, d in enumerate(self.dimensions, 1):
            hit = f"{len(d.hit_items)}"
            missed = f"{len(d.missed_items)}"
            lines.append(
                f"| {i} | {d.name} | {d.weight} | {d.raw_score:.1f}/10 | "
                f"{d.weighted_score:.2f} | {hit} | {missed} |"
            )
        lines.append("")
        for i, d in enumerate(self.dimensions, 1):
            lines.append(f"### 维度 {i}: {d.name}  (加权 {d.weighted_score:.2f} / {d.weight})")
            if d.hit_items:
                lines.append(f"- 命中({len(d.hit_items)}): " + " / ".join(d.hit_items))
            if d.missed_items:
                lines.append(f"- 缺失({len(d.missed_items)}): " + " / ".join(d.missed_items))
            if d.evidence_snippets:
                lines.append(f"- 证据片段:")
                for s in d.evidence_snippets[:3]:
                    snippet = s.replace("\n", " ")
                    if len(snippet) > 150:
                        snippet = snippet[:150] + "…"
                    lines.append(f"    - {snippet}")
            if d.llm_comment:
                lines.append(f"- LLM评语: {d.llm_comment}")
            lines.append("")
        if self.hallucinations:
            lines.append("## 疑似幻觉")
            lines.append("")
            for h in self.hallucinations:
                lines.append(f"- [{h.location}] {h.text} — {h.reason}")
            lines.append("")
        return "\n".join(lines)


# -------------------------------------------------------------------
# 工具: 章节切分
# -------------------------------------------------------------------
_CN_NUM = "一二三四五六七八九十"

_SECTION_HEAD_RE = re.compile(
    rf"(?m)^\s*(?:[（(]?[{_CN_NUM}]+[)）、.]|{'|'.join(f'（{c}）' for c in _CN_NUM)}|\d+[、.])\s*([^\n]{{1,40}})"
)


def split_sections(text: str) -> dict[str, str]:
    """
    按 "一、" / "（一）" / "1." 等切分章节，返回 {标题: 正文}。
    若切不开则返回 {"全文": text}。
    """
    heads: list[tuple[int, str]] = []
    for m in re.finditer(
        r"(?m)^\s*([一二三四五六七八九十]+[、.][^\n]{0,40})",
        text,
    ):
        heads.append((m.start(), m.group(1).strip()))
    if len(heads) < 2:
        return {"全文": text}
    sections: dict[str, str] = {}
    for i, (pos, title) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        sections[title] = text[pos:end]
    # 附加全文引用方便需要整体扫的维度
    sections["__ALL__"] = text
    return sections


def pick_section(sections: dict[str, str], keywords: list[str]) -> str:
    """从章节字典中挑选第一个标题含任一关键字的章节；找不到返回全文。"""
    for title, body in sections.items():
        if title == "__ALL__":
            continue
        for kw in keywords:
            if kw in title:
                return body
    return sections.get("__ALL__", "")


def snippet(text: str, pattern: str, width: int = 80) -> str:
    """摘取 pattern 命中附近一段文本用于证据展示。"""
    m = re.search(pattern, text)
    if not m:
        return ""
    s = max(0, m.start() - 20)
    e = min(len(text), m.end() + width)
    out = text[s:e].replace("\n", " ").strip()
    return out[:150]


# -------------------------------------------------------------------
# QualityScorer 主类
# -------------------------------------------------------------------
class QualityScorer:
    def __init__(
        self,
        llm_caller: Optional[Callable[[str, str], str]] = None,
        financial_indicators: Optional[Any] = None,
        borrower_name: Optional[str] = None,
    ):
        self.llm_caller = llm_caller
        self.financial_indicators = financial_indicators
        # 借款人主体名,用于检测概念幻觉(母公司/合并/保证人错标)
        if borrower_name is None and financial_indicators is not None:
            try:
                stmts = getattr(financial_indicators, "raw_statements", None)
                if stmts is not None:
                    borrower_name = getattr(stmts, "reporting_entity", None)
            except Exception:
                pass
        self.borrower_name = borrower_name or ""

    # ---------------------------------------------------------------
    # 主入口
    # ---------------------------------------------------------------
    def score(self, generated_text: str, source_file: str = "") -> QualityReport:
        sections = split_sections(generated_text)
        dims: list[DimensionScore] = []

        dims.append(self._dim1_hard_fields(generated_text, sections))
        dims.append(self._dim2_basic_info(generated_text, sections))
        dims.append(self._dim3_operation(generated_text, sections))
        dims.append(self._dim4_financial(generated_text, sections))
        dims.append(self._dim5_credit(generated_text, sections))
        dims.append(self._dim6_guarantee(generated_text, sections))
        dims.append(self._dim7_repayment(generated_text, sections))
        dims.append(self._dim8_advice(generated_text, sections))
        dims.append(self._dim9_format(generated_text, sections))

        hallucinations = self._detect_hallucinations(generated_text, sections)

        before_penalty = sum(d.weighted_score for d in dims)
        penalty = min(20.0, 5.0 * len(hallucinations))
        fatal_fail = len(hallucinations) >= 3
        fatal_reasons: list[str] = []
        if fatal_fail:
            fatal_reasons.append(
                f"检测到 {len(hallucinations)} 处疑似幻觉（>=3 触发一票否决）"
            )
        total = 0.0 if fatal_fail else max(0.0, before_penalty - penalty)
        passed = (not fatal_fail) and total >= 75.0

        return QualityReport(
            generated_text_file=source_file,
            total_score=total,
            total_score_before_penalty=before_penalty,
            fatal_fail=fatal_fail,
            fatal_reasons=fatal_reasons,
            dimensions=dims,
            hallucinations=hallucinations,
            passed=passed,
        )

    # ---------------------------------------------------------------
    # 维度 1: 申报方案硬字段位置完整性 (权重 2)
    # 说明:这些字段(申报额度/业务品种/期限/担保方式/PD评级/上期评级等)
    # 属于银行审批人视角的数据,客户材料里本就没有,应由客户经理人工填写。
    # 本维度不评LLM是否填入实值(它填不了也不该填),只评是否保留字段位置锚点,
    # 便于客户经理后续补齐。
    # ---------------------------------------------------------------
    def _dim1_hard_fields(self, text: str, sections: dict[str, str]) -> DimensionScore:
        anchors = [
            ("申报额度", r"申报额度"),
            ("申报敞口", r"申报敞口"),
            ("业务品种", r"业务品种"),
            ("业务期限", r"业务期限"),
            ("授信期限", r"授信期限"),
            ("担保方式", r"担保方式"),
            ("PD评级", r"PD评级"),
            ("上期评级", r"上一期授信评级"),
            ("上期敞口", r"上一期授信敞口"),
            ("上期担保", r"上一期授信担保方式"),
            ("批复日期", r"批复日期"),
            ("国标行业", r"国标行业"),
            ("绿通标识", r"绿通标识"),
        ]

        hits: list[str] = []
        missed: list[str] = []
        for name, pat in anchors:
            if re.search(pat, text):
                hits.append(name)
            else:
                missed.append(name)

        # 位置保留率: 13 项满分 10 分
        raw = 10.0 * (len(hits) / len(anchors))
        weight = 2.0
        return DimensionScore(
            name="申报方案硬字段",
            weight=weight,
            raw_score=raw,
            weighted_score=raw * weight / 10.0,
            hit_items=hits,
            missed_items=missed,
            evidence_snippets=[],
        )

    # ---------------------------------------------------------------
    # 维度 2: 企业基本情况 (权重 4)
    # ---------------------------------------------------------------
    def _dim2_basic_info(self, text: str, sections: dict[str, str]) -> DimensionScore:
        body = pick_section(sections, ["基本情况", "借款人简介", "借款人概况", "经营单位"])
        if not body:
            body = text

        items = [
            ("客户名称", r"客户名称[：:\s]*([^\s|]{2,})"),
            (
                "统一社会信用代码",
                r"(?:统一社会信用代码|社会信用代码)[：:\s]*([0-9A-Z]{15,18})",
            ),
            ("注册资本", r"注册资本[：:\s]*([\d.]+)\s*万?元?"),
            ("实收资本", r"实收资本[：:\s]*([\d.]+)\s*万?元?"),
            (
                "成立日期",
                r"成立(?:于|日期)?[：:]?\s*(\d{4}年\d{1,2}月|\d{4}[/-]\d{1,2})",
            ),
            (
                "法定代表人",
                r"(?:法定代表人|法人代表|法人)[：:\s]*([^\s，,；;。|]{2,6})",
            ),
            ("实际控制人", r"(?:实际控制人|实控人)[：:\s]*([^\s，,；;。|]{2,10})"),
            ("经营地址", r"(?:经营地址|坐落地点|注册地址|地址)[^。\n]{0,30}?([省市区县镇][^。\n]{4,60})"),
            ("员工/社保人数", r"(?:员工人数|社保人数|员工或社保人数)[^\d]{0,10}([\d]+)\s*人?"),
            ("主营业务", r"(?:主营业务|实际主营业务|主营业务范围|经营范围)[：:\s]*([^。\n]{10,})"),
        ]

        hits: list[str] = []
        missed: list[str] = []
        evidences: list[str] = []

        def good(v: str) -> bool:
            if not v:
                return False
            v = v.strip()
            if any(tok in v for tok in ("[待补充]", "[待确认]", "[TBD]")):
                return False
            if v.startswith("[") or v.startswith("【"):
                return False
            return True

        for name, pat in items:
            m = re.search(pat, body)
            if m and good(m.group(1)):
                hits.append(name)
                if len(evidences) < 3:
                    evidences.append(snippet(body, pat))
            else:
                missed.append(name)

        raw = len(hits)  # 每项 1 分, 10 项
        weight = 4.0
        return DimensionScore(
            name="企业基本情况",
            weight=weight,
            raw_score=raw,
            weighted_score=raw * weight / 10.0,
            hit_items=hits,
            missed_items=missed,
            evidence_snippets=evidences,
        )

    # ---------------------------------------------------------------
    # 维度 3: 经营情况分析 (权重 12)
    # ---------------------------------------------------------------
    def _dim3_operation(self, text: str, sections: dict[str, str]) -> DimensionScore:
        body = pick_section(
            sections, ["经营情况", "主要经营", "产品", "借款人主要经营"]
        )
        if not body or len(body) < 50:
            body = text

        checks = [
            (
                "主营产品/服务具体",
                [r"主营", r"产品", r"业务"],
                r"(主营|产品|方案|服务)[^。\n]{20,}",
            ),
            (
                "主要客户(≥3家具名)",
                [r"客户", r"下游"],
                None,
            ),
            (
                "主要供应商",
                [r"供应商", r"上游", r"采购"],
                r"(供应商|上游)[^。\n]{10,}",
            ),
            (
                "经营模式",
                [r"模式", r"销售", r"结算", r"账期"],
                r"(经营模式|销售模式|结算|账期)[^。\n]{8,}",
            ),
            (
                "在手订单",
                [r"在手订单", r"合同", r"订单"],
                r"(在手订单|合同金额|订单)[^。\n]{5,}",
            ),
            (
                "行业地位",
                [r"行业地位", r"市场地位", r"竞争力", r"领先", r"龙头", r"优势"],
                r"(行业地位|核心竞争力|竞争优势|市场)[^。\n]{10,}",
            ),
        ]

        # 具名客户: 粗略: "XX大学/XX公司/XX学院/政府/部门" 等 >=3
        # 排除: 借款人自身、关联公司、非客户的行业描述词
        exclude_tokens = (
            "借款人",
            "我行",
            "中锐",
            "福建中锐",
            "子公司",
            "母公司",
            "关联企业",
            "会计师事务所",
            "律师事务所",
            "下游客户",
            "主要客户",
        )
        raw_named = re.findall(
            r"([\u4e00-\u9fa5]{2,20}(?:大学|学院|学校|[^市区]公司|集团|局|水利局|研究所|管理中心|事业单位))",
            body,
        )
        named_customers: list[str] = []
        for c in raw_named:
            # 去掉自身 / 停用词
            if any(tok in c for tok in exclude_tokens):
                continue
            # 动词碎片
            if re.match(r"^(?:包括|提升|覆盖|涵盖|服务|带动|形成|构建|面向|聚焦)", c):
                continue
            named_customers.append(c)
        named_set = set(named_customers)

        hits: list[str] = []
        missed: list[str] = []
        scores: list[float] = []  # 每项 0 / 0.5 / 1
        evidences: list[str] = []

        for name, kws, ptn in checks:
            if name == "主要客户(≥3家具名)":
                if len(named_set) >= 3:
                    scores.append(1.0)
                    hits.append(name)
                    evidences.append("具名客户: " + "、".join(list(named_set)[:5]))
                elif len(named_set) >= 1 or any(k in body for k in kws):
                    scores.append(0.5)
                    missed.append(name + "(仅部分)")
                else:
                    scores.append(0.0)
                    missed.append(name)
                continue

            # 其它: 有 keyword 才算触碰, 有长描述才算具体
            has_kw = any(k in body for k in kws)
            specific = False
            if ptn:
                m = re.search(ptn, body)
                if m and len(m.group(0)) >= 20:
                    specific = True
            if specific:
                scores.append(1.0)
                hits.append(name)
                if len(evidences) < 5:
                    evidences.append(snippet(body, ptn))
            elif has_kw:
                scores.append(0.5)
                missed.append(name + "(仅提及)")
            else:
                scores.append(0.0)
                missed.append(name)

        # 6 项，每项 1 分 → 满分 6 映射到 0-10
        raw = (sum(scores) / 6.0) * 10.0
        weight = 14.0
        return DimensionScore(
            name="经营情况分析",
            weight=weight,
            raw_score=raw,
            weighted_score=raw * weight / 10.0,
            hit_items=hits,
            missed_items=missed,
            evidence_snippets=evidences,
        )

    # ---------------------------------------------------------------
    # 维度 4: 财务分析深度 (权重 26)
    # ---------------------------------------------------------------
    def _dim4_financial(self, text: str, sections: dict[str, str]) -> DimensionScore:
        body = pick_section(
            sections, ["财务情况", "财务", "财务分析", "主要财务"]
        )
        if not body or len(body) < 80:
            body = text

        hits: list[str] = []
        missed: list[str] = []
        evidences: list[str] = []

        # ① 三年关键科目完整性: 看是否同时出现多个科目 + "近三年" / "2023" / "2024" / "2025"
        key_subj = ["营业收入", "净利润", "应收账款", "存货", "应付账款", "资产总额", "负债"]
        subj_hits = sum(1 for s in key_subj if s in body)
        year_hits = sum(1 for y in ("2023", "2024", "2025", "近三年") if y in body)
        if subj_hits >= 4 and year_hits >= 2:
            hits.append("①三年关键科目完整")
            evidences.append(f"命中科目 {subj_hits} 个, 年度标识 {year_hits} 个")
        else:
            missed.append(f"①三年关键科目(科目{subj_hits},年度{year_hits})")

        # ② ≥5 个关键比率
        ratios = re.findall(
            r"(毛利率|净利率|资产负债率|流动比率|速动比率|总资产周转率|应收账款周转|存货周转|ROE|ROA|现金比率|EBITDA|利息保障倍数|营业利润率|净资产收益率)",
            body,
        )
        ratio_set = set(ratios)
        if len(ratio_set) >= 5:
            hits.append(f"②≥5 个关键比率(共{len(ratio_set)}种)")
        else:
            missed.append(f"②关键比率不足(仅{len(ratio_set)}种: {','.join(ratio_set)})")

        # ③ ≥4 个同比
        yoy = re.findall(
            r"(同比[+\-]?[\d.]+%?|较[^。\n]{0,8}(?:增加|减少|下降|增长|上升|降低)[^。\n]{0,15}?[\d.]+\s*%?|增幅[\d.]+\s*%|降幅[\d.]+\s*%|较上年[^。\n]{0,10}[\d.]+)",
            body,
        )
        if len(yoy) >= 4:
            hits.append(f"③≥4 个同比(共{len(yoy)}处)")
        else:
            missed.append(f"③同比不足(仅{len(yoy)}处)")

        # ④ 趋势归因: "主要由于|主要因为|原因是|受...影响"
        cause = re.findall(
            r"(主要由于|主要因为|原因是|受[^。\n]{1,15}影响|归因于|系因)", body
        )
        if len(cause) >= 2:
            hits.append(f"④趋势归因(共{len(cause)}处)")
            evidences.append(snippet(body, r"主要由于[^。\n]{5,}"))
        else:
            missed.append(f"④趋势归因不足(仅{len(cause)}处)")

        # ⑤ 三大活动现金流
        if "经营活动" in body and "投资活动" in body and "筹资活动" in body:
            hits.append("⑤三大活动现金流")
        else:
            missed.append("⑤三大活动现金流(未齐)")

        # ⑥ 真实性验证: 税务 / 银行流水
        if ("税务" in body or "税收" in body) and ("流水" in body or "银行流水" in body):
            hits.append("⑥真实性验证(税务+流水)")
        elif "税务" in body or "流水" in body:
            hits.append("⑥真实性验证(部分)")
        else:
            missed.append("⑥真实性验证")

        # ⑦ 行业对比
        if re.search(r"行业[^。\n]{0,15}(平均|均值|水平|对比|一般|区间|特性)", body):
            hits.append("⑦行业对比")
        else:
            missed.append("⑦行业对比")

        # ⑧ 财务与还款量化挂钩
        m_link = re.search(
            r"(覆盖|偿付|支撑|保障|偿还)[^。\n]{0,30}?[\d.]+\s*(?:万|亿|%|倍)",
            body,
        )
        if m_link:
            hits.append("⑧财务与还款量化挂钩")
            evidences.append(snippet(body, r"(覆盖|偿付|支撑|保障|偿还)[^。\n]{0,40}"))
        else:
            missed.append("⑧财务与还款量化挂钩")

        # ⑨ 对经营状况独立判断: "总体|整体|综合" + "良好|可控|稳定|承压|改善|下滑"
        if re.search(r"(总体|整体|综合看|综合判断)[^。\n]{0,30}?(良好|可控|稳定|承压|改善|下滑|修复|较好|一般)", body):
            hits.append("⑨独立判断")
        else:
            missed.append("⑨独立判断")

        # ⑩ 异常项识别
        if re.search(r"(异常|波动较大|大幅|急剧|骤|骤升|骤降|陡增|陡减|突降|突增|显著)", body):
            hits.append("⑩异常项识别")
        else:
            missed.append("⑩异常项识别")

        raw = float(len(hits))  # 10 项, 每项 1 分
        weight = 30.0
        return DimensionScore(
            name="财务分析深度",
            weight=weight,
            raw_score=raw,
            weighted_score=raw * weight / 10.0,
            hit_items=hits,
            missed_items=missed,
            evidence_snippets=evidences,
        )

    # ---------------------------------------------------------------
    # 维度 5: 征信分析 (权重 18)
    # ---------------------------------------------------------------
    def _dim5_credit(self, text: str, sections: dict[str, str]) -> DimensionScore:
        body = pick_section(sections, ["征信", "融资", "对外担保", "实控人征信"])
        if not body or len(body) < 80:
            body = text

        hits: list[str] = []
        missed: list[str] = []
        evidences: list[str] = []

        items = [
            ("①对公贷款", r"(?:公司|企业|借款人)?[^。\n]{0,30}?(?:贷款余额|融资余额|授信余额)[^。\n]{0,20}?[\d.]+\s*万"),
            ("②对公逾期", r"(?:公司|企业|借款人|五级分类)[^。\n]{0,60}?(?:逾期|不良|欠息|垫款|正常)"),
            ("③对公担保", r"对外担保|被担保|担保余额|无对外担保|材料未提供对外担保"),
            ("④对公查询", r"(?:机构|银行|金融机构|人行)(?:查询|信用报告)|查询次数|硬查询|征信查询"),
            ("⑤实控人贷款", r"(?:实控人|黄祖海|法人代表|法定代表人|个人)[^。\n]{0,80}?(?:贷款|信用卡|未结清|贷记卡|经营贷)"),
            ("⑥实控人逾期", r"(?:实控人|黄祖海|个人|法定代表人)[^。\n]{0,80}?(?:逾期|不良|欠息|已结清)|(?:实控人|个人)征信(?:未|无)(?:触发|不良|逾期)"),
            ("⑦实控人担保查询", r"(?:实控人|黄祖海|个人)[^。\n]{0,80}?(?:担保责任|共同还款|担保余额|征信查询|查询次数|信用报告)"),
            ("⑧瑕疵定性判断", r"(?:瑕疵|临时性|非恶意|未对[^。\n]{0,10}实质性?风险|实质性风险|已(?:结清|归还|缴清)|不构成重大|遗忘导致)"),
            ("⑨对本次授信影响", r"(?:本次授信|本次申报|对本次)[^。\n]{0,30}?(?:影响|风险|可控|综合评判)|综合评[判估][^。\n]{0,30}?(?:可控|未(?:造成|产生)实质性|准入)|未对借款人造成实质性"),
        ]

        for name, pat in items:
            m = re.search(pat, body)
            if m:
                hits.append(name)
                if len(evidences) < 4:
                    evidences.append(snippet(body, pat))
            else:
                missed.append(name)

        # 9 项, 每项 1.1 分 → 满分 9.9, 映射到 10
        raw = (len(hits) / 9.0) * 10.0
        weight = 14.0
        return DimensionScore(
            name="征信分析",
            weight=weight,
            raw_score=raw,
            weighted_score=raw * weight / 10.0,
            hit_items=hits,
            missed_items=missed,
            evidence_snippets=evidences,
        )

    # ---------------------------------------------------------------
    # 维度 6: 担保评估 (权重 8)
    # ---------------------------------------------------------------
    def _dim6_guarantee(self, text: str, sections: dict[str, str]) -> DimensionScore:
        body = pick_section(sections, ["担保分析", "担保"])
        if not body or len(body) < 50:
            body = text

        hits: list[str] = []
        missed: list[str] = []
        evidences: list[str] = []

        # 为担保专节才算的正文. 先尝试用 "（十）担保" / "担保分析" 子节
        guarantee_section = ""
        for title, s in sections.items():
            if title == "__ALL__":
                continue
            if "担保" in title and ("分析" in title or "（十）" in title or "十、" in title):
                guarantee_section = s
                break
        if not guarantee_section:
            # fallback: 找 "担保分析" / "个人担保" / "抵押" 上下文片段
            m = re.search(r"(担保分析|个人担保|抵押担保)[\s\S]{0,600}", body)
            guarantee_section = m.group(0) if m else ""

        checks = [
            (
                "担保方式说明(具体值)",
                r"担保方式[：:\s]*([\u4e00-\u9fa5]{2,10})",
                lambda v: v
                and v.strip()
                and not any(tok in v for tok in ("[待", "【", "|")),
            ),
            (
                "保证人/抵押物具体情况",
                r"(担保人|保证人|抵押物)[：:\s]*([^\n]{8,})|(身份证号|持股比例|抵押面积|抵押价值|评估价值|登记在我行名下)",
                None,
            ),
            (
                "担保能力与覆盖度",
                r"(覆盖|覆盖率|担保能力|足值|充足保障|偿债保障|连带责任|共担|共同偿债)",
                None,
            ),
            (
                "方式合理性判断",
                r"(合理|适当|强化[^。\n]{0,15}机制|风险共担|缓释|追加[^。\n]{0,10}担保|本次[^。\n]{0,10}担保[^。\n]{0,20}适宜)",
                None,
            ),
        ]

        for item in checks:
            if len(item) == 3:
                name, pat, val_check = item
            else:
                name, pat = item
                val_check = None
            # 担保方式说明优先在全文里找并校验具体值
            search_body = body if name == "担保方式说明(具体值)" else (guarantee_section or body)
            m = re.search(pat, search_body)
            if m:
                matched_val = next((g for g in m.groups() if g), "") if m.groups() else m.group(0)
                if val_check is not None:
                    if val_check(matched_val):
                        hits.append(name)
                        if len(evidences) < 3:
                            evidences.append(snippet(search_body, pat))
                    else:
                        missed.append(name + "(仅占位符)")
                else:
                    hits.append(name)
                    if len(evidences) < 3:
                        evidences.append(snippet(search_body, pat))
            else:
                missed.append(name)

        raw = (len(hits) / 4.0) * 10.0  # 每项 2.5
        weight = 10.0
        return DimensionScore(
            name="担保评估",
            weight=weight,
            raw_score=raw,
            weighted_score=raw * weight / 10.0,
            hit_items=hits,
            missed_items=missed,
            evidence_snippets=evidences,
        )

    # ---------------------------------------------------------------
    # 维度 7: 还款能力论证 (权重 14)
    # ---------------------------------------------------------------
    def _dim7_repayment(self, text: str, sections: dict[str, str]) -> DimensionScore:
        body = pick_section(sections, ["还款能力", "借款原因", "借款原因及还款"])
        if not body or len(body) < 80:
            # 还款论证可能散落, fallback 到全文
            body = text

        hits: list[str] = []
        missed: list[str] = []
        evidences: list[str] = []

        # ① 定量挂钩
        if re.search(
            r"(现金流|应收账款|应收款|在手订单|合同金额)[^。\n]{0,60}?[\d.]+\s*万[^。\n]{0,30}?(覆盖|偿还|偿付|归还|支撑|足以)",
            body,
        ) or re.search(
            r"(覆盖|偿还|偿付|归还|支撑|足以)[^。\n]{0,40}?[\d.]+\s*万",
            body,
        ):
            hits.append("①定量挂钩")
            evidences.append(snippet(body, r"(覆盖|偿还|偿付|支撑|足以)[^。\n]{0,50}"))
        else:
            missed.append("①定量挂钩")

        # ② 还款来源识别: 第一还款来源 / 第二还款来源 / 经营性现金流 / 政府补贴 / 股东
        src_hits = re.findall(
            r"(第一还款来源|第二还款来源|经营性现金流|应收账款回笼|政府补贴|股东支持|融资渠道|抵质押物)",
            body,
        )
        if len(set(src_hits)) >= 2:
            hits.append(f"②还款来源识别(共{len(set(src_hits))})")
        elif len(src_hits) >= 1:
            missed.append("②还款来源仅1项")
        else:
            missed.append("②还款来源识别")

        # ③ 期限匹配
        if re.search(r"(期限错配|期限匹配|账期[^。\n]{0,20}?(?:对应|匹配|覆盖)|贷款(?:到期|期限)[^。\n]{0,30}?(?:对应|匹配|覆盖))", body):
            hits.append("③期限匹配")
        else:
            missed.append("③期限匹配")

        # ④ 压力 / 最坏情况
        if re.search(r"(压力测试|最坏情况|极端情况|压力情景|抽贷|断贷|流动性压力|紧张|链断)", body):
            hits.append("④压力/最坏情况讨论")
        else:
            missed.append("④压力/最坏情况")

        # ⑤ 优先级排序
        if re.search(r"(第一还款来源|第二还款来源|主要还款来源|次要还款来源|优先|首要)", body):
            hits.append("⑤优先级排序")
        else:
            missed.append("⑤优先级排序")

        # ⑥ 论证链完整: 需要同时满足 "现金流" + "覆盖/偿还" + 有数字
        chain_ok = (
            re.search(r"现金流", body)
            and re.search(r"(覆盖|偿还|偿付|归还)", body)
            and re.search(r"\d+\s*万", body)
        )
        if chain_ok:
            hits.append("⑥论证链完整")
        else:
            missed.append("⑥论证链完整")

        raw = (len(hits) / 6.0) * 10.0
        weight = 14.0
        return DimensionScore(
            name="还款能力论证",
            weight=weight,
            raw_score=raw,
            weighted_score=raw * weight / 10.0,
            hit_items=hits,
            missed_items=missed,
            evidence_snippets=evidences,
        )

    # ---------------------------------------------------------------
    # 维度 8: 授信建议与风险判断 (权重 10)
    # ---------------------------------------------------------------
    def _dim8_advice(self, text: str, sections: dict[str, str]) -> DimensionScore:
        body = pick_section(
            sections,
            ["授信申报结论", "授信建议", "申报方案", "综合评价"],
        )
        if not body or len(body) < 50:
            body = text

        hits: list[str] = []
        missed: list[str] = []
        evidences: list[str] = []

        # ① 明确授信建议: 必须有清晰的 "建议准入 / 拟申请给予 + 数字额度" 等
        rec_match = re.search(
            r"(建议予以准入|建议准入|同意[^。\n]{0,10}?授信|拟申请给予[^。\n]{0,30}?[\d.]+\s*万|申报授信方案[：:][^。\n]{0,80}?[\d.]+\s*万)",
            body,
        )
        if rec_match:
            hits.append("①明确授信建议")
            evidences.append(snippet(body, r"(建议予以准入|建议准入|拟申请给予)[^。\n]{0,80}"))
        else:
            missed.append("①明确授信建议(缺具体额度或结论词)")

        # ② ≥3 个具体风险点
        risk_terms = re.findall(
            r"(信用瑕疵|流动性(?:紧张|压力)|应收账款(?:回款|延期)|欠税|逾期|集中度|行业(?:下行|波动)|账期(?:过长|延长)|现金流(?:紧张|压力)|市场风险|政策风险|供应链风险|期限错配|经营风险)",
            body,
        )
        if len(set(risk_terms)) >= 3:
            hits.append(f"②≥3 具体风险点(共{len(set(risk_terms))})")
        elif len(set(risk_terms)) >= 1:
            missed.append(f"②风险点不足(仅{len(set(risk_terms))})")
        else:
            missed.append("②具体风险点")

        # ③ 缓释措施: 每个风险点都要有对应措施 — 粗略判定: 出现 "缓释 / 追加担保 / 贷后监控 / 结构化" 至少 2 种且须附上下文
        mit = set()
        for kw in (
            "缓释",
            "追加[^。\n]{0,8}担保",
            "贷后[^。\n]{0,8}(监控|管控|跟踪)",
            "动态[^。\n]{0,6}(监测|跟踪)",
            "结构化授信",
            "压降",
            "保全[^。\n]{0,8}资产",
            "风险共担",
        ):
            if re.search(kw, body):
                mit.add(kw)
        if len(mit) >= 2:
            hits.append(f"③缓释措施(共{len(mit)})")
        elif len(mit) == 1:
            missed.append("③缓释措施(仅1项)")
        else:
            missed.append("③缓释措施")

        # ④ 合规判断
        comp_hits = []
        for token in ("反洗钱", "关联交易", "股权变动", "ESG"):
            if token in body:
                comp_hits.append(token)
        if len(comp_hits) >= 2:
            hits.append(f"④合规判断({'/'.join(comp_hits)})")
        elif comp_hits:
            missed.append(f"④合规判断仅{comp_hits}")
        else:
            missed.append("④合规判断")

        raw = (len(hits) / 4.0) * 10.0
        weight = 10.0
        return DimensionScore(
            name="授信建议与风险判断",
            weight=weight,
            raw_score=raw,
            weighted_score=raw * weight / 10.0,
            hit_items=hits,
            missed_items=missed,
            evidence_snippets=evidences,
        )

    # ---------------------------------------------------------------
    # 维度 9: 格式规范 (权重 2) — 扣分制
    # ---------------------------------------------------------------
    def _dim9_format(self, text: str, sections: dict[str, str]) -> DimensionScore:
        hits: list[str] = []
        missed: list[str] = []
        evidences: list[str] = []

        raw = 10.0

        # 1. markdown 表格符号: 一行中 "|" 出现 >=2 次, 且非表单原始字段分隔
        md_rows = 0
        for line in text.splitlines():
            # 排除 TABLE 标记行
            if "=== TABLE" in line:
                continue
            if line.count("|") >= 2 and "---" in line:
                md_rows += 1
            elif line.strip().startswith("|") and line.count("|") >= 3:
                md_rows += 1
        if md_rows >= 1:
            raw -= 2.5
            missed.append(f"markdown表格符号残留({md_rows}行)")
        else:
            hits.append("无 markdown 表格残留")

        # 2. prompt 标记泄露
        prompt_leaks = re.findall(
            r"(【章节标题】|【本节标题】|【证据清单】|【写作提示】|【注意事项】|```|<instruction>|<output>|System:|Assistant:)",
            text,
        )
        if prompt_leaks:
            raw -= 2.5
            missed.append(f"prompt标记泄露({len(prompt_leaks)}处)")
            if prompt_leaks:
                evidences.append("样例: " + prompt_leaks[0])
        else:
            hits.append("无 prompt 标记")

        # 3. 占位符 [待补充] / [待确认] / [TBD]
        placeholders = re.findall(r"(\[待补充\]|\[待确认\]|\[TBD\]|\{\{[^}]+\}\})", text)
        if placeholders:
            raw -= 2.5
            missed.append(f"占位符残留({len(placeholders)}处)")
        else:
            hits.append("无占位符残留")

        # 4. 语言流畅 (启发式): 连续重复词 / 机翻感词 / 过多英文
        clumsy = 0
        # "的的" "了了" 连续重复
        clumsy += len(re.findall(r"的的|了了|是是|和和", text))
        # 中英文间无空格的生硬翻译感很难规则判，跳过; 由 LLM 层补
        if clumsy >= 3:
            raw -= 2.5
            missed.append(f"语言不流畅({clumsy}处)")
        else:
            hits.append("语言基本流畅")

        raw = max(0.0, min(10.0, raw))
        weight = 2.0
        return DimensionScore(
            name="格式规范",
            weight=weight,
            raw_score=raw,
            weighted_score=raw * weight / 10.0,
            hit_items=hits,
            missed_items=missed,
            evidence_snippets=evidences,
        )

    # ---------------------------------------------------------------
    # 维度 10 / 数据真实性罚分 — 幻觉检测
    # ---------------------------------------------------------------
    def _detect_hallucinations(
        self, text: str, sections: dict[str, str]
    ) -> list[Hallucination]:
        halls: list[Hallucination] = []

        # 策略 1: financial_indicators 数字交叉
        if self.financial_indicators is not None:
            try:
                known_numbers = self._extract_known_numbers(self.financial_indicators)
                for m in re.finditer(r"([\u4e00-\u9fa5]{2,6})[：:\s]*([\d]+(?:\.\d+)?)\s*万", text):
                    label = m.group(1)
                    val = float(m.group(2))
                    for kname, kval in known_numbers.items():
                        if label in kname or kname in label:
                            if kval > 0 and abs(val - kval) / kval > 0.05:
                                halls.append(
                                    Hallucination(
                                        text=f"{label} {val}万",
                                        reason=f"与已知 {kname}={kval}万 差异 >5%",
                                        location=f"offset {m.start()}",
                                    )
                                )
                                break
            except Exception:
                pass

        # 策略 2: 主体身份错配(概念幻觉)
        # "母公司(X)/合并(X)/控股公司(X)/集团(X)/X母公司" 当 X 是借款人本身时
        if self.borrower_name:
            bn = self.borrower_name
            # 取借款人名主干(去掉"股份有限公司/有限公司"后缀方便匹配简称)
            bn_core = re.sub(r"(股份有限公司|有限责任公司|有限公司|股份公司)$", "", bn)
            bn_short = bn_core[-4:] if len(bn_core) >= 4 else bn_core
            role_labels = ["母公司", "合并报表", "合并口径", "集团合并", "控股公司", "集团公司"]
            for role in role_labels:
                # 形式A: 母公司(福建中锐网络股份有限公司)
                pat_a = re.compile(
                    rf"{role}\s*[\(（]\s*([^)）]{{2,40}})\s*[\)）]"
                )
                for m in pat_a.finditer(text):
                    inside = m.group(1)
                    if bn in inside or bn_core in inside or (bn_short and bn_short in inside):
                        halls.append(Hallucination(
                            text=m.group(0),
                            reason=f"主体身份错配:{bn}是借款人单体,不是{role}",
                            location=f"offset {m.start()}",
                        ))
                # 形式B: 福建中锐...母公司
                pat_b = re.compile(
                    rf"{bn_core[:8] if len(bn_core) >= 8 else bn_core}[^\n。,，]{{0,15}}{role}"
                )
                for m in pat_b.finditer(text):
                    halls.append(Hallucination(
                        text=m.group(0)[:60],
                        reason=f"主体身份错配:借款人{bn}被贴上{role}标签",
                        location=f"offset {m.start()}",
                    ))

        # 策略 3: BS 科目口径错标(较年初被写成同比)
        # 借款人财务中 BS 类存量科目配"同比"是口径错误
        bs_subjects = [
            "总资产", "资产总计", "总负债", "负债合计",
            "所有者权益", "股东权益",
            "资产负债率", "流动比率", "速动比率",
            "货币资金", "应收账款", "存货", "短期借款",
            "长期借款", "应付账款", "预收账款", "预付账款",
            "其他应收款", "其他应付款",
        ]
        for subj in bs_subjects:
            # "总资产...同比减少/增长/下降/上升/提升/增加"
            # 负前瞻 (?!周转) 排除流量口径 "应收账款周转天数同比+49天"
            pat = re.compile(
                rf"{subj}(?!周转)[^\n。]{{0,15}}?同比(?:减少|增长|下降|上升|提升|增加|下滑|扩张|[+-]\d)"
            )
            for m in pat.finditer(text):
                halls.append(Hallucination(
                    text=m.group(0)[:50],
                    reason=f"口径错标:{subj}是BS存量科目,应用『较年初』而非『同比』",
                    location=f"offset {m.start()}",
                ))

        # 策略 4: 角色-数据错配(保证人/抵押人段落用借款人财务数据)
        # 限定在保证人/抵押人相关章节里出现"营业收入同比增长X%""净利率X%""毛利率X%"等借款人特征短语
        role_sections = ["保证人", "抵押人", "担保人"]
        # 从全文中粗定位这些角色段落
        borrower_fin_markers = [
            r"营收.{0,5}同比[^\n。]{0,20}增长",
            r"净利率.{0,5}(?:提升|同比)",
            r"毛利率.{0,5}(?:下降|同比|稳定)",
            r"营业收入同比增长\d",
            r"净利润同比.{0,5}增长\d",
        ]
        for role in role_sections:
            # 找到角色段的位置(从"X.保证人"或"保证人主要财务"出发,取后续 800 字)
            for m_role in re.finditer(rf"[（(]?{role}(?:主要财务|财务分析|财务数据|情况|简介)", text):
                start = m_role.start()
                segment = text[start:start + 800]
                for pat in borrower_fin_markers:
                    m2 = re.search(pat, segment)
                    if m2:
                        halls.append(Hallucination(
                            text=m2.group(0)[:50],
                            reason=f"角色错配:{role}段落中出现疑似借款人财务特征句式",
                            location=f"offset {start + m2.start()}",
                        ))
                        break  # 每段只报一次,避免爆量

        # 去重(按 location+reason 前 40 字)
        seen = set()
        dedup: list[Hallucination] = []
        for h in halls:
            key = (h.location, h.reason[:40])
            if key in seen:
                continue
            seen.add(key)
            dedup.append(h)

        return dedup

    def _extract_known_numbers(self, ind: Any) -> dict[str, float]:
        """尽量从 FinancialIndicators 对象里取出 {字段名: 万元数值}."""
        out: dict[str, float] = {}
        try:
            as_dict = None
            if hasattr(ind, "to_dict"):
                as_dict = ind.to_dict()
            elif isinstance(ind, dict):
                as_dict = ind
            if as_dict:
                for k, v in as_dict.items():
                    try:
                        out[str(k)] = float(v)
                    except Exception:
                        continue
        except Exception:
            pass
        return out


# -------------------------------------------------------------------
# 自测
# -------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import io

    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", line_buffering=True
    )

    gen_file = r"D:\claude code\credit_report_agent_work\_tmp_gen_1776076894.txt"
    with open(gen_file, encoding="utf-8") as f:
        gen_text = f.read()

    scorer = QualityScorer()
    report = scorer.score(gen_text, source_file=gen_file)

    print("=" * 60)
    print("AI 版规则层基线分")
    print("=" * 60)
    print(report.to_markdown())
    print()

    manual_file = r"D:\claude code\credit_report_agent_work\_tmp_manual_full.txt"
    with open(manual_file, encoding="utf-8") as f:
        manual_text = f.read()

    report2 = scorer.score(manual_text, source_file=manual_file)
    print("=" * 60)
    print("人工版规则层基线分")
    print("=" * 60)
    print(report2.to_markdown())

    print()
    print("=" * 60)
    print("对比")
    print("=" * 60)
    gap = report2.total_score - report.total_score
    print(f"AI 版总分: {report.total_score:.2f}")
    print(f"人工版总分: {report2.total_score:.2f}")
    print(f"差距: {gap:+.2f}")
    if gap < 20:
        print("⚠ 警告: 差距 < 20, 打分器可能需要调校")
    else:
        print("√ 差距 >= 20, 分辨率基本 OK")
