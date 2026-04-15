# -*- coding: utf-8 -*-
"""
Section-by-Section Generation Engine v2.0

核心改造：从"单次投喂-单次生成"升级为三阶段协议：
  Phase 1 — 证据组装 (Evidence Assembly): LLM 逐项查找材料中的证据
  Phase 2 — 锚定撰写 (Grounded Generation): LLM 只用证据清单写正文
  Phase 3 — 自审门控 (Self-Audit Gate): 验证数字出处、检测重复/矛盾

设计原则：
  - 教LLM HOW TO THINK，而不是给它一堆规则
  - 每个数字必须有出处，没出处就不写
  - 缺失数据直接留空或一句话说明，不写影响分析段落
  - 风格锚定：注入真实人工报告样本，让LLM模仿长度和语气
"""

import os
import re
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from template_decomposer import (
    SectionInfo, ParaInfo, TemplateRole,
    detect_leakage, infer_section_dimensions,
)

logger = logging.getLogger(__name__)


# =============================================
# Phase 1: Evidence Assembly Prompt
# =============================================

_EVIDENCE_SYSTEM_PROMPT = (
    "你是一名资深银行信贷分析师的助手。\n"
    "你的任务是：在撰写报告之前，先做【证据组装】——\n"
    "从提供的全部材料中，逐一查找本节所需的每个数据点。\n\n"
    "【工作方法】\n"
    "1. 先理解本节在审批流程中要回答什么问题\n"
    "2. 列出本节需要的全部数据点（数字、事实、名称、日期等）\n"
    "3. 对每个数据点，在【全部材料来源】中逐一查找：\n"
    "   - 【财务数据锚点】（已验证的财务数字）\n"
    "   - 【企业画像锚点】（已确认的基本信息）\n"
    "   - 【客户材料摘要】（KB提取的结构化信息）\n"
    "   - 【补充材料原文】（原始文档检索结果）\n"
    "4. 对每个数据点输出一行结果\n\n"
    "【输出格式】严格按以下格式，每行一条：\n"
    "✓ 数据点名称: 值 [来源: 具体来源名称]\n"
    "✗ 数据点名称: 全部材料中未找到\n\n"
    "【关键规则】\n"
    "- 只有确认所有4个材料来源都查过之后，才能标记 ✗\n"
    "- 数值必须原样抄录，不做换算、不做估算\n"
    "- 不要推断、不要计算、不要补充任何材料中没有的信息\n"
    "- 如果同一数据在不同来源中有不同值，全部列出并标注来源\n"
)


# =============================================
# Phase 2: Grounded Generation Prompt
# =============================================

_GROUNDED_SYSTEM_PROMPT = (
    "你是一名资深商业银行信贷分析师,正在撰写普惠授信申报及审查审批意见表。\n\n"
    "【你的思考框架】\n"
    "面对每个子项,按以下顺序思考:\n"
    "1. 意图: 这个子项在审批中要支撑什么判断?\n"
    "2. 证据: 证据清单里有没有支撑这个判断的数据?\n"
    "3. 撰写: 有证据→用证据写结论;没证据→按【缺失数据三段式规则】具体列出所需材料\n"
    "4. 校验: 我写的每个数字,都能在证据清单中找到对应条目吗?\n\n"
    "【铁律】\n"
    "1. 证据清单标记 ✓ 的数据可以使用,标记 ✗ 的数据禁止编造\n"
    "2. 所有数字、公司名、人名、金额、日期必须来自证据清单,一字不改\n"
    "3. 缺失数据的处理【严禁泛泛】: 禁止只写\"材料不足\"/\"材料未提供\"/\n"
    "   \"(材料未提供) 万元\"/\"(具体原因需企业补充说明)\"/\"(具体数字需核实)\"\n"
    "   等空洞兜底短语。必须具体列出需要补充的材料名称,采用以下句式:\n"
    "     『需补充X项目的明细合同』\n"
    "     『需补充近三年分产品线毛利率表』\n"
    "     『需补充主要客户账期及回款明细』\n"
    "     『需补充{年度}{表名}/{凭证名}/{明细名}』\n"
    "   材料不足 → 句末必须追加 `,需补充{具体材料名}`,不得单独成句。\n"
    "   缺失内容分析,禁止写\"影响分析\"/\"建议补充\"兜底段落。\n"
    "4. 禁止从训练数据中补充任何看似合理的信息\n"
    "5. 禁止复制模板范例中的内容(范例数字已被屏蔽为____)\n"
    "6. 关联企业/担保人/子公司的数字绝对不得与借款人本身的数字相互挪用。\n"
    "   【已计算财务指标】中所有数字仅代表借款人单体;\n"
    "   关联企业/担保人的数字只能来自【证据清单】或【结构化材料锚点】中带明确主体前缀\n"
    "   (如『主体「XX有限公司」』)的条目,严格 1:1 对应到其所属主体名称,\n"
    "   禁止把任意一家关联企业的数字挪到另一家或借款人本身;\n"
    "   若锚点中标注『材料数据可疑』『请人工核实』,直接原文写『该关联企业财务数据存疑,\n"
    "   待人工核实』,禁止给出具体数字。\n"
    "7. 【已计算财务指标】中所有变动幅度短语(『较年初下降X个百分点』『同比增长X%』\n"
    "   『较年初提升X倍』『缩短X天』等)已由代码精确计算,你必须**原文复用**这些短语,\n"
    "   绝对不得自行重新计算、改写数值、或把当前值误当作变动值。\n"
    "   例: 财务指标给出『42.5% (较年初下降7.7个百分点 | 2024末:50.2% → 2025末:42.5%)』,\n"
    "   正文只能写『资产负债率较年初下降7.7个百分点至42.5%』,\n"
    "   绝不能写『下降42.5个百分点』(变动=当前值,数学荒谬)。\n"
    "   【严禁兜底话术】当某指标变动短语不在【已计算财务指标】块中时,\n"
    "   禁止输出『XX率较年初有所变化,具体幅度以财务附表为准』\n"
    "   『变动幅度待核』『具体数字参见附表』等所有形式的模糊兜底,\n"
    "   必须按铁律3写成『需补充 XX 近三年明细/同比数据』这类具体材料请求。\n"
    "8. 报告正文中数字一律按银行报告习惯保留至多2位小数(比率/倍数2位、百分比1位、\n"
    "   天数/人数整数),绝对禁止输出如 1.818974657571668 这类5位以上精度的浮点。\n"
    "9. 【降级兜底措辞硬规则】无论任何原因(材料缺失/证据不足/存疑),\n"
    "   降级兜底文案必须中性,严禁预判或提及任何下一步流程名,包括但不限于:\n"
    "   『审贷会』『贷审会』『贷委会』『上会』『待上会审议』『提交会议讨论』等。\n"
    "   统一使用『待人工核实』『待补充材料后复核』『待业务线补充』等中性措辞。\n"
    "10. 【财务分析三段式硬规则】撰写任何财务相关段落(盈利/偿债/营运/现金流/\n"
    "    科目变动原因分析等)时,必须严格按以下三段式组织,缺一不可:\n"
    "    (a) 数据罗列:逐年列出 2-3 个同比/环比数据并用趋势词串联\n"
    "        (如『连续增长/持续下降/由A走低至B/呈波动上升/趋于平稳』);\n"
    "    (b) 外因分析:从行业景气/政策变化/地区环境/上下游周期等外部维度分析\n"
    "        走势成因(证据充分时用行业基准或政策点支持;\n"
    "        证据不足时按铁律3具体列出『需补充行业XX报告/XX政策文件/地区XX数据』);\n"
    "    (c) 内因分析:结合材料中的业务动作/客户结构/供应结构/管理动作/研发投入\n"
    "        等内部维度,解读企业自身对走势的影响\n"
    "        (证据不足同样按铁律3列出所需材料清单)。\n"
    "    禁止只写『数据稳健』/『经营正常』/『盈利改善』等无证据结论。\n"
    "11. 【composite 段落硬规则】正文中出现 [COMPOSITE-SLOT] 标记的骨架行,\n"
    "    意味着该行正下方紧跟一张由系统独立填充的表格。\n"
    "    你只能对该骨架写 1-2 句总括/点评(例如『详见下表』或结合证据的一句话小结),\n"
    "    严禁重复列举表格会填的数据,更严禁写『材料未提供前五大XX』等兜底句\n"
    "    (表格有数据时会自动填充)。\n"
    "12. 【多年数据罗列铁律】撰写任何财务指标变动时,必须从【近三年财务指标罗列】块中\n"
    "    **原文引用**对应条目,格式必须是\n"
    "    『{指标} 2022/2023/2024/2025 年分别为 A/B/C/D,呈现 {走势}』。\n"
    "    严禁省略某年,严禁只写『同比增长 X%』而不展开多年数据;\n"
    "    若【近三年财务指标罗列】块中某指标缺失某年,原文保留『-』占位,\n"
    "    不得自行估算或填补。\n"
    "13. 【外因溯源铁律】外因分析(行业/政策/地区)必须引用\n"
    "    【行业/政策参考卡片】块中列出的具体条目名\n"
    "    (如『软件和信息技术服务业-典型账期 90-180 天』)。\n"
    "    若某维度没有对应卡片,必须明确写\n"
    "    『外因分析-{维度}待补充({具体调研名})』,\n"
    "    **严禁**编造未在卡片块中列出的行业数字、政策名称、地区标杆。\n"
    "14. 【内因溯源铁律】内因分析每一条结论必须标注材料来源,\n"
    "    格式 `(据材料:{来源描述})`,来源必须是\n"
    "    【企业画像锚点】/【财务数据锚点】/【结构化材料锚点】/【补充材料原文】\n"
    "    中已列出的条目。找不到对应来源 → 改写为\n"
    "    『需补充{具体材料名}』,\n"
    "    严禁用『公司管理层认为』『可能由于』『预计是因为』等泛化推测代替溯源。\n"
    "15. 【Composite 段禁重复罗列】composite 段(段落紧邻表格)中,\n"
    "    段落部分**禁止**逐条罗列表格内数据;段落只写总括 1-3 句\n"
    "    + 趋势 + 异常说明。若下方表格已列明现金流量四年明细,\n"
    "    段落绝不可再把每年数字列一遍——重复会触发审核退回。\n\n"
    "【禁止回显的结构块】(以下内容仅供你内部思考,绝对不得作为正文输出)\n"
    "- 任何以【...】开头的提示块标题(如【本节结构要求】【模板范例】"
    "【已计算财务指标】【证据清单】【撰写硬规则】【企业画像锚点】"
    "【财务主体归属硬规则】【结构化材料锚点】【本节必写字段锚点】等)\n"
    "- 任何以 ✓ 或 ✗ 开头、且含 [来源:...] 标记的证据条目行\n"
    "- 任何以 [规模]/[盈利能力]/[偿债能力]/[营运效率]/[现金流]/"
    "[关键科目原始期末值]/[代码识别的异常项]/[趋势定性] 开头的数据小节标题\n"
    "- 『口径说明:』『数据来源:』『报告日:』开头的说明行\n"
    "违反任何一条将被视为生成失败。\n\n"
    "【输出格式】\n"
    "- 中文专业表述,银行信贷报告文风\n"
    "- 简洁有力,结论明确,不写废话\n"
    "- 金额统一用万元口径\n"
    "- 禁止Markdown符号\n"
    "- 直接输出正文,不输出标题行\n"
)


# ---- 模板示例数字屏蔽 ----
# 目的: 把模板范例/骨架行内的数字(连同其单位)替换成 ______,
#       防止 LLM 把模板里的示例数字当作真实客户数字写入正文。
_TEMPLATE_NUM_WITH_UNIT_RE = re.compile(
    r"-?\d[\d,]*(?:\.\d+)?\s*(?:万元|亿元|%|个百分点|pct|倍|天|年|人|岁|元)"
)
# 独立日期 (2023年, 2023-01-02, 2023/01/02 等) 保留, 其他裸数字也屏蔽 (>=3 位)
_TEMPLATE_BARE_NUM_RE = re.compile(r"(?<!\d)\d{3,}(?:\.\d+)?(?!\d)")


def _mask_template_numbers(text: str) -> str:
    """把模板范例/骨架行中的数字(带单位/裸数)替换为 ______。"""
    if not text:
        return text
    text = _TEMPLATE_NUM_WITH_UNIT_RE.sub("______", text)
    text = _TEMPLATE_BARE_NUM_RE.sub("______", text)
    return text

# Style reference: injected as part of grounded generation prompt
# This teaches the LLM the expected conciseness and tone
_STYLE_REFERENCE = (
    "【风格参考（请模仿此长度和语气）】\n"
    "以下是同类报告中人工撰写的优秀段落样本，请严格模仿其：\n"
    "- 信息密度：每句话都包含具体数据或明确判断\n"
    "- 简洁程度：一个子项通常1-3句话，不超过100字\n"
    "- 缺失处理：直接跳过或留空，不写解释\n"
    "- 语气：肯定、专业、有判断力\n\n"
    "样本1（借款人概况）：\n"
    "  企业成立于2012年1月，经营地址位于福州大学国家大学科技园8号楼5层。"
    "经营地为租用办公楼，租用总面积2523平，年租金115万。"
    "上年度末社保人数69人；注册资本：4100万元、实收资本：4100万元；"
    "法定代表人：黄祖海。\n\n"
    "样本2（531预警）：\n"
    "  蓝色预警提示（1）疑似该查询客户贷款转至敏感标签客户；"
    "（2）监测企业存在未结案的民事类非合同案件。"
    "经核实，该企业贷后均提供合理发票；企业名下案件均已结案。"
    "综合评判，未对借款人造成实质性风险。\n\n"
    "样本3（缺失数据处理）：\n"
    "  [直接留空或跳过该子项，不写任何文字]\n"
)


# =============================================
# Phase 3: Self-Audit Prompt
# =============================================

_AUDIT_SYSTEM_PROMPT = (
    "你是银行信贷报告的质量审核员。请审核以下报告章节。\n\n"
    "【审核清单】\n"
    "1. 财务数字反查(最优先)：正文中所有财务相关数字(金额/比率/同比/周转天数/"
    "现金流净额等),必须在【已计算财务指标】块中精确存在。\n"
    "   - 指标块中找不到 → 标记为【幻觉】\n"
    "   - 数值被改写 → 标记为【错误】\n"
    "2. 其他数字核验：报告中非财务数字(日期/金额/人数等)是否都能在证据清单中找到？\n"
    "   - 找不到出处的数字 → 标记为【幻觉】\n"
    "3. 事实核验：报告中提到的公司名、人名、地址是否与证据一致？\n"
    "   - 不一致 → 标记为【错误】\n"
    "4. 财务分析完整性：财务段落是否至少含3个同比+3个比率+2段归因+还款能力挂钩？\n"
    "   - 缺失 → 标记为【分析缺失】(必须补齐而不是留空)\n"
    "5. 冗余检测：是否有超过50字的\"影响分析\"或\"建议补充\"段落,但无具体数据支撑？\n"
    "   - 有 → 标记为【冗余】\n"
    "6. 矛盾检测：报告内部是否有自相矛盾的判断？\n"
    "   - 有 → 标记为【矛盾】\n\n"
    "【输出格式】\n"
    "如果发现问题，逐条输出：\n"
    "  【问题类型】具体描述 → 修正建议\n"
    "如果无问题，输出：审核通过\n\n"
    "然后输出修正后的完整正文（即使无问题也输出一遍）。\n"
    "用 === 分隔审核意见和修正正文。\n"
)


# =============================================
# Prompt building
# =============================================

def build_section_prompt(
    section,
    kb=None,
    company_profile="",
    build_dimension_text_fn=None,
    truth_financial_data=None,
    material_index=None,
):
    """Build LLM prompt for generating a complete section.

    Returns: (system_prompt, user_prompt)
    NOTE: This is kept for backward compatibility. The new protocol uses
    build_evidence_prompt() + build_grounded_prompt() instead.
    """
    # Delegate to the grounded prompt builder (single-pass fallback)
    return _build_grounded_prompt_internal(
        section=section,
        kb=kb,
        company_profile=company_profile,
        build_dimension_text_fn=build_dimension_text_fn,
        truth_financial_data=truth_financial_data,
        material_index=material_index,
        evidence_text=None,  # No evidence available in single-pass mode
    )


def build_evidence_prompt(
    section,
    kb=None,
    company_profile="",
    build_dimension_text_fn=None,
    truth_financial_data=None,
    material_index=None,
    financial_indicators=None,
    material_anchor=None,
):
    """Phase 1: Build evidence assembly prompt.

    Returns: (system_prompt, user_prompt)

    financial_indicators: FinancialIndicators 对象(来自 FinancialAnalyzer)。
      若提供,注入"已计算财务指标"区块作为最高权威数据源,LLM 不得重新计算。
    """
    # Section structure
    structure_lines = []
    structure_lines.append("【本节标题】" + section.title)
    structure_lines.append("")
    structure_lines.append("【本节需要回答的问题】")
    structure_lines.append("请根据以下结构，列出本节需要查找的全部数据点：")
    structure_lines.append("")

    composite_idx = set(
        getattr(section, "composite_paragraph_indices", None) or []
    )

    for p in section.paragraphs:
        if not p.text.strip():
            continue
        is_composite = p.para_idx in composite_idx
        text = p.text.strip()
        text = re.sub(r'_{3,}', '______', text)
        text = re.sub(r'[ \u3000]{4,}', '______', text)
        text = _mask_template_numbers(text)
        if p.role == TemplateRole.SKELETON:
            if is_composite:
                structure_lines.append(
                    "  [COMPOSITE 跳过-表格独立填充] " + text
                )
            else:
                structure_lines.append("  " + text)
        elif is_composite:
            # CONTENT 但结构上是 composite:证据组装只需关注"写总括"所需的
            # 业务级证据(如上下游整体策略),不必搜具体数值
            structure_lines.append(
                "  [COMPOSITE 跳过-表格独立填充] " + text
            )

    instructions = section.all_instructions
    if instructions:
        structure_lines.append("")
        structure_lines.append("【写作提示】")
        for inst in instructions:
            structure_lines.append("  - " + inst)

    if composite_idx:
        structure_lines.append("")
        structure_lines.append(
            "【复合段落提示】标有 [COMPOSITE 跳过-表格独立填充] 的骨架行,"
            "其数据由表格填充路径独立处理,Phase1 无需为其查找数据点。"
        )

    structure_block = "\n".join(structure_lines)

    # Assemble all material sources
    user_parts = [structure_block]
    user_parts.append("\n以下是全部可用材料来源，请逐一检查：")

    # Financial indicators (最高权威: 代码从xlsx直接抽取+计算)
    if financial_indicators is not None:
        try:
            from financial_analyzer import FinancialAnalyzer
            fi_block = FinancialAnalyzer().format_for_prompt(
                financial_indicators, multi_year_data=truth_financial_data)
            user_parts.append("\n" + fi_block)
        except Exception:
            pass

    # Financial anchor (旧版兜底)
    if truth_financial_data:
        financial_block = _build_financial_anchor(truth_financial_data)
        if financial_block:
            user_parts.append(financial_block)

    # V14-v3: material_anchor 产出的【结构化材料锚点】 + 【行业/政策参考卡片】
    if material_anchor is not None:
        try:
            anchor_block = material_anchor.format_for_prompt()
            if anchor_block:
                user_parts.append("\n" + anchor_block)
        except Exception:
            pass

    # Company profile
    if company_profile:
        user_parts.append(
            "\n【企业画像锚点（已确认的事实）】\n" + company_profile)

    # KB materials
    materials_block = ""
    if kb and build_dimension_text_fn:
        dimensions = infer_section_dimensions(section)
        materials_block = build_dimension_text_fn(
            kb, dimensions, max_chars=10000, include_raw_tables=True
        )
    if materials_block:
        user_parts.append("\n【客户材料摘要】\n" + materials_block)

    # Full-text search
    material_supplement = ""
    if material_index is not None:
        hints = list(instructions) if instructions else []
        content_lines = section.content_lines
        if content_lines:
            for cl in content_lines[:5]:
                if len(cl) < 200:
                    hints.append(cl)
        material_supplement = material_index.search_for_section(
            section.title, hints
        )
    if material_supplement:
        user_parts.append(
            "\n【补充材料原文（从客户提供材料中检索）】\n"
            + material_supplement)

    if not materials_block and not material_supplement:
        user_parts.append(
            "\n【客户材料摘要】\n"
            "（未检索到与本节直接匹配的材料段落，"
            "请结合【企业画像锚点】、【财务数据锚点】等已提供信息）")

    user_parts.append(
        "\n请现在执行证据组装。"
        "逐一列出本节需要的数据点及其查找结果。")

    return _EVIDENCE_SYSTEM_PROMPT, "\n".join(user_parts)


def build_grounded_prompt(
    section,
    evidence_text,
    kb=None,
    company_profile="",
    build_dimension_text_fn=None,
    truth_financial_data=None,
    material_index=None,
    style_reference=True,
    financial_indicators=None,
    material_anchor=None,
):
    """Phase 2: Build grounded generation prompt using evidence.

    Returns: (system_prompt, user_prompt)
    """
    return _build_grounded_prompt_internal(
        section=section,
        kb=kb,
        company_profile=company_profile,
        build_dimension_text_fn=build_dimension_text_fn,
        truth_financial_data=truth_financial_data,
        material_index=material_index,
        evidence_text=evidence_text,
        style_reference=style_reference,
        financial_indicators=financial_indicators,
        material_anchor=material_anchor,
    )


def build_audit_prompt(section_title, generated_text, evidence_text,
                       financial_indicators=None):
    """Phase 3: Build self-audit prompt.

    Returns: (system_prompt, user_prompt)
    """
    user_parts = [
        "【章节标题】" + section_title,
        "",
    ]

    if financial_indicators is not None:
        try:
            from financial_analyzer import FinancialAnalyzer
            fi_block = FinancialAnalyzer().format_for_prompt(financial_indicators)
            user_parts.append(fi_block)
            user_parts.append("")
        except Exception:
            pass

    user_parts.extend([
        "【证据清单】",
        evidence_text or "(无证据清单)",
        "",
        "【待审核的报告正文】",
        generated_text,
        "",
        "请按审核清单逐项检查(财务数字反查最优先),然后输出修正后的完整正文。",
    ])
    return _AUDIT_SYSTEM_PROMPT, "\n".join(user_parts)


def _build_grounded_prompt_internal(
    section,
    kb=None,
    company_profile="",
    build_dimension_text_fn=None,
    truth_financial_data=None,
    material_index=None,
    evidence_text=None,
    style_reference=True,
    financial_indicators=None,
    material_anchor=None,
):
    """Internal: build the grounded generation prompt."""
    structure_lines = []
    structure_lines.append("【本节标题】" + section.title)
    structure_lines.append("")
    structure_lines.append("【本节结构要求(仅供你理解章节骨架,禁止回显本区块)】")
    structure_lines.append(
        "按以下骨架顺序撰写正文(有数据写,无数据留空或一句话说明\"材料未提供XX\"):")
    structure_lines.append(
        "注:下列骨架行仅用于提示结构顺序,系统已自动保留模板原文;"
        "你不得复述/重写骨架行本身,不得输出『【本节结构要求】』『【模板范例】』"
        "『【已计算财务指标】』『【证据清单】』等任何方括号/中括号头。"
        "骨架中的示例数字/下划线一律视为占位符,绝对不要把它们当作真实数据写入正文。")
    structure_lines.append("")

    # composite 段落集合(SKELETON 段 + 其下紧跟嵌套表格):
    #   这些骨架行对应的真实数据由 form_filler 的表格路径独立填充,
    #   LLM 只能写 1-2 句总括,不能重复列表格数据、不能写"材料未提供前五大XX"兜底
    composite_idx = set(
        getattr(section, "composite_paragraph_indices", None) or []
    )

    # composite 段落以结构顺序嵌入骨架提示(包括 CONTENT 角色的 composite 段)
    # 这样 LLM 在读到"①主要上游(前五大):"时,明确知道下面紧跟的表格由系统填
    for p in section.paragraphs:
        if not p.text.strip():
            continue
        is_composite = p.para_idx in composite_idx
        text = p.text.strip()
        text = re.sub(r'_{3,}', '______', text)
        text = re.sub(r'[ \u3000]{4,}', '______', text)
        text = _mask_template_numbers(text)
        if p.role == TemplateRole.SKELETON:
            if is_composite:
                structure_lines.append(
                    "  · [COMPOSITE-SLOT 下方紧跟表格由系统独立填充,"
                    "你只需 1-2 句总括] " + text
                )
            else:
                structure_lines.append("  · " + text)
        elif is_composite:
            # CONTENT 角色但结构上是 composite(后紧跟表格)—
            # 仍需 LLM 写,但按 composite 规则(只 1-2 句总括)
            structure_lines.append(
                "  · [COMPOSITE-SLOT 下方紧跟表格由系统独立填充,"
                "你只需 1-2 句总括,禁止写『材料未提供前五大XX』兜底句] "
                + text
            )

    instructions = section.all_instructions
    if instructions:
        structure_lines.append("")
        structure_lines.append("【写作提示】")
        for inst in instructions:
            structure_lines.append("  - " + inst)

    if composite_idx:
        structure_lines.append("")
        structure_lines.append(
            "【复合段落提示(composite)】本节含 "
            + str(len(composite_idx))
            + " 个『段落+紧邻表格』复合结构(已用 [COMPOSITE-SLOT] 标记)。\n"
            "【下方紧邻表格将独立填写,本段只写总括/趋势/异常,禁重复列数据】\n"
            "对 [COMPOSITE-SLOT] 骨架行:只写 1-3 句总括 + 趋势 + 异常说明,\n"
            "严禁重复列举该表格会填的数据(例如下方是现金流量四年明细表,\n"
            "你绝不可再把经营/投资/筹资每年数字逐条列一遍;\n"
            "下方是前五大客户表,你绝不可再列客户名+金额);\n"
            "严禁写『材料未提供前五大XX采购/销售金额』这类兜底句\n"
            "(表格由系统独立填充,LLM 不负责填表)。"
        )

    # V14-v3: 循环表 schema 提示
    loop_schema = getattr(section, "loop_table_schema", None) or {}
    if loop_schema:
        structure_lines.append("")
        structure_lines.append(
            "【循环子表结构提示(loop_table)】本节识别到『综述段 + 循环子表』结构:\n"
            "  - 综述 cell(para_idx=" + str(loop_schema.get("overview_para_idx"))
            + ")只写 1-2 句简洁说明(最多 100 字),\n"
            "    严禁在综述段塞流水明细/逐条列 row 数据。\n"
            "  - 下方循环子表列头: "
            + " / ".join(loop_schema.get("header_cols", []))
            + "\n"
            "  - 示例/占位 row 由系统独立清理(LLM 不写),\n"
            "    你绝不可输出『如未落实请说明原因』『请说明』等通用模板占位短语。"
        )

    content_lines = section.content_lines
    if content_lines:
        structure_lines.append("")
        structure_lines.append(
            "【模板范例(仅供理解格式/句式,数字已屏蔽为____,"
            "真实数字一律从【证据清单】和【已计算财务指标】取)】")
        example_text = "\n".join(content_lines)
        if len(example_text) > 2000:
            example_text = example_text[:2000] + "\n...(范例截断)"
        # 屏蔽示例内的全部数字,避免被当作客户数据回填
        example_text = _mask_template_numbers(example_text)
        structure_lines.append(example_text)

    structure_block = "\n".join(structure_lines)

    # Build user prompt
    user_parts = [structure_block]

    # Section-specific mandatory anchor fields
    _section_title = (section.title or "")
    if any(k in _section_title for k in ("借款人概况", "借款人简介", "基本情况", "企业基本")):
        user_parts.append(
            "\n【本节必写字段锚点(逐项从证据清单/企业画像取值写入,无证据则写『材料未提供XX』)】\n"
            "本节属于『借款人基本情况』,必须逐项覆盖以下10个核心字段,"
            "不得跳过或用资质类信息(排污许可证/环评等)替代:\n"
            "  1) 客户名称(企业全称)\n"
            "  2) 统一社会信用代码\n"
            "  3) 注册资本 / 实收资本(两者都要,单位万元)\n"
            "  4) 成立日期\n"
            "  5) 法定代表人(姓名+简要背景,如出生年/学历/从业经历)\n"
            "  6) 实际控制人 / 股权结构(谁控股多少)\n"
            "  7) 经营地址 / 注册地址\n"
            "  8) 员工人数 / 社保缴纳人数\n"
            "  9) 主营业务(从经营范围+实际业务)\n"
            " 10) 所属行业 / 行业地位(如有)\n"
            "以上字段若证据清单或企业画像中有明确值,必须原样写入;"
            "不要用『材料未提供排污/环评/资质』等无关内容占位。")

    # Financial indicators (最高权威: 代码从xlsx直接抽取+计算)
    fi_block_text = ""
    if financial_indicators is not None:
        try:
            from financial_analyzer import FinancialAnalyzer
            fa = FinancialAnalyzer()
            fi_block_text = fa.format_for_prompt(
                financial_indicators, multi_year_data=truth_financial_data)
            user_parts.append("\n" + fi_block_text)
            user_parts.append("\n" + fa.get_subject_anchor_rules(financial_indicators))
            user_parts.append(
                "\n【撰写硬规则】\n"
                "1. 所有财务比率/同比/周转天数/金额,必须从上面【已计算财务指标】块取值,"
                "不得自行计算或估算。\n"
                "2. 异常项必须逐条解读(为什么异常、对授信的影响)。指标块里标了"
                "[代码识别的异常项]的,撰写财务段时必须引用,并用『异常/显著/波动较大』"
                "等定性词明确标注。\n"
                "3. 涉及财务分析的段落,必须包含以下全部要素:\n"
                "   a) 至少3个同比增长率、至少3个比率\n"
                "   b) 至少2段归因解读,句式必须含『主要由于XX』『原因是XX』『受XX影响』其一\n"
                "   c) 与行业基准的对比句,句式如『高于/低于软件信息业XX-XX%典型区间』\n"
                "   d) 真实性交叉核对,至少提及『税务申报』『银行流水』二者之一\n"
                "   e) 与还款能力的定性或定量挂钩(覆盖/保障/偿付+数字)\n"
                "4. 没有出现在指标块中的财务数字,一律禁止写入正文。\n"
                "5. 涉及融资/担保/对外担保段落,优先引用【结构化材料锚点】中的融资清单、"
                "关联企业、资产清单等精确数据,不要写『材料未提供』当锚点里有时。")
        except Exception:
            pass

    # V14-v3: material_anchor 产出的【结构化材料锚点】 + 【行业/政策参考卡片】
    if material_anchor is not None:
        try:
            anchor_block = material_anchor.format_for_prompt()
            if anchor_block:
                user_parts.append("\n" + anchor_block)
        except Exception:
            pass

    # Inject evidence (Phase 2 mode) — this is the key difference
    if evidence_text:
        user_parts.append(
            "\n【证据清单（基于全部材料的逐项查找结果）】\n"
            "以下是预先从材料中查找到的证据。撰写时：\n"
            "- ✓ 标记的数据必须使用，数值原样引用\n"
            "- ✗ 标记的数据禁止编造，留空或写\"材料未提供\"\n"
            "- 不在清单中的数据禁止出现在正文中\n\n"
            + evidence_text)
    else:
        # Fallback: single-pass mode, inject raw materials
        if company_profile:
            user_parts.append(
                "\n【企业画像锚点（这些是已确认的事实，务必使用）】\n"
                + company_profile)

        if truth_financial_data:
            financial_block = _build_financial_anchor(truth_financial_data)
            if financial_block:
                user_parts.append(financial_block)

        materials_block = ""
        if kb and build_dimension_text_fn:
            dimensions = infer_section_dimensions(section)
            materials_block = build_dimension_text_fn(
                kb, dimensions, max_chars=10000, include_raw_tables=True
            )
        if materials_block:
            user_parts.append("\n【客户材料摘要】\n" + materials_block)

        material_supplement = ""
        if material_index is not None:
            hints = list(instructions) if instructions else []
            if content_lines:
                for cl in content_lines[:5]:
                    if len(cl) < 200:
                        hints.append(cl)
            material_supplement = material_index.search_for_section(
                section.title, hints
            )
        if material_supplement:
            user_parts.append(
                "\n【补充材料原文（从客户提供材料中检索）】\n"
                + material_supplement)

        if not materials_block and not material_supplement:
            user_parts.append(
                "\n【客户材料摘要】\n"
                "（未检索到与本节直接匹配的材料段落，"
                "请结合【企业画像锚点】、【财务数据锚点】等已提供信息撰写）")

    user_parts.append(
        "\n请现在撰写本节内容。"
        "直接输出正文，不要输出标题行（标题已由模板保留）。")

    # Build system prompt with style reference
    system_prompt = _GROUNDED_SYSTEM_PROMPT
    if style_reference:
        system_prompt += "\n" + _STYLE_REFERENCE

    return system_prompt, "\n".join(user_parts)


def _build_financial_anchor(truth_data):
    """Build financial data anchor block from truth data."""
    if not truth_data:
        return ""

    lines = ["\n【财务数据锚点（已验证，务必使用这些数字）】"]

    periods = sorted(truth_data.keys())
    for period in periods[-3:]:
        data = truth_data[period]
        if not data:
            continue
        lines.append("\n" + str(period) + "：")
        key_items = [
            ("营业收入", "revenue", "operating_revenue"),
            ("净利润", "net_profit"),
            ("资产总计", "total_assets"),
            ("负债合计", "total_liabilities"),
            ("所有者权益", "total_equity", "owners_equity"),
            ("应收账款", "accounts_receivable"),
            ("存货", "inventory"),
            ("货币资金", "cash_and_equivalents", "monetary_funds"),
            ("短期借款", "short_term_borrowings"),
            ("其他应收款", "other_receivables"),
            ("其他应付款", "other_payables"),
            ("应付账款", "accounts_payable"),
            ("长期投资", "long_term_investments", "long_term_equity_investments"),
            ("经营活动现金流量净额",
             "operating_cash_flow_net"),
            ("销售商品提供劳务收到的现金",
             "cash_received_from_sales"),
        ]
        for item_names in key_items:
            for name in item_names:
                if name in data:
                    val = data[name]
                    if isinstance(val, (int, float)):
                        lines.append(
                            "  " + item_names[0] + "："
                            + str(val) + "万元")
                    break

    return "\n".join(lines) if len(lines) > 1 else ""


# =============================================
# Three-phase section generation
# =============================================

def generate_all_sections(
    sections,
    kb=None,
    company_profile="",
    llm_fn=None,
    build_dimension_text_fn=None,
    truth_financial_data=None,
    template_paragraphs=None,
    progress_cb=None,
    max_retries=1,
    material_index=None,
    use_evidence_protocol=True,
    use_audit=True,
    financial_indicators=None,
    material_anchor=None,
    pending_questions_sink=None,
):
    """Generate content for all sections using the three-phase protocol.

    Phase 1 (Evidence Assembly): For each section, LLM extracts evidence
    Phase 2 (Grounded Generation): LLM writes using only the evidence
    Phase 3 (Self-Audit): LLM verifies its own output against evidence

    pending_questions_sink: 可选 list。若提供,每当发现某 section 正文留有
      "外因待补充" / "需补充XX" 等缺材料标签时,调用 LLM 生成 1-3 个给
      客户经理的具体问题,以 dict 形式追加到该 list。
      字段: {id, section_id, section_title, question, hint, input_type}
      前端 V14-B 可渲染为问卷,后端 V14-A 可作为 done 事件的 data。

    Returns: {para_idx: generated_text}
    """
    all_results = {}
    results_lock = threading.Lock()
    progress_lock = threading.Lock()
    pending = [s for s in sections if s.has_content_to_rewrite]
    total = len(pending)
    done_counter = {"n": 0}

    def _log(msg):
        if progress_cb:
            with progress_lock:
                progress_cb(msg)

    # 构建数字白名单(整个 run 共用一份)
    _numeric_whitelist = None
    if financial_indicators is not None:
        try:
            from numeric_validator import build_whitelist
            _numeric_whitelist = build_whitelist(financial_indicators)
        except Exception as e:
            logger.warning("Failed to build numeric whitelist: %s", e)

    def _process_section(section):
        with progress_lock:
            done_counter["n"] += 1
            idx = done_counter["n"]
        _log("[逐节生成] (" + str(idx) + "/" + str(total) + ") "
             + section.title[:30] + "...")

        evidence_text = None

        # ── Phase 1: Evidence Assembly ──
        if use_evidence_protocol:
            try:
                _log("  [Phase1-证据组装] " + section.title[:20])
                evi_sys, evi_usr = build_evidence_prompt(
                    section=section,
                    kb=kb,
                    company_profile=company_profile,
                    build_dimension_text_fn=build_dimension_text_fn,
                    truth_financial_data=truth_financial_data,
                    material_index=material_index,
                    financial_indicators=financial_indicators,
                    material_anchor=material_anchor,
                )
                evidence_text = llm_fn(evi_sys, evi_usr)
                if evidence_text:
                    evidence_text = evidence_text.strip()
                    found = evidence_text.count("✓")
                    missing = evidence_text.count("✗")
                    _log(f"  [证据] ✓{found}项 ✗{missing}项")
            except Exception as e:
                logger.warning("Evidence assembly failed for %s: %s",
                               section.section_id, e)
                evidence_text = None

        # ── Phase 2: Grounded Generation ──
        mode = "锚定撰写" if evidence_text else "直接撰写"
        _log(f"  [Phase2-{mode}] " + section.title[:20])

        if evidence_text:
            sys_p, usr_p = build_grounded_prompt(
                section=section,
                evidence_text=evidence_text,
                kb=kb,
                company_profile=company_profile,
                build_dimension_text_fn=build_dimension_text_fn,
                truth_financial_data=truth_financial_data,
                material_index=material_index,
                financial_indicators=financial_indicators,
                material_anchor=material_anchor,
            )
        else:
            sys_p, usr_p = build_section_prompt(
                section=section,
                kb=kb,
                company_profile=company_profile,
                build_dimension_text_fn=build_dimension_text_fn,
                truth_financial_data=truth_financial_data,
                material_index=material_index,
            )

        response = llm_fn(sys_p, usr_p)
        if not response:
            return None

        response = _clean_response(response)

        # ── Phase 3: Self-Audit ──
        if use_audit and evidence_text and len(response) > 200:
            try:
                _log("  [Phase3-自审] " + section.title[:20])
                audit_sys, audit_usr = build_audit_prompt(
                    section.title, response, evidence_text,
                    financial_indicators=financial_indicators)
                audit_response = llm_fn(audit_sys, audit_usr)
                if audit_response:
                    corrected = _extract_corrected_text(audit_response)
                    if corrected and len(corrected) > 100:
                        audit_part = audit_response.split("===")[0] if "===" in audit_response else ""
                        issues = []
                        for marker in ["【幻觉】", "【错误】", "【冗余】", "【矛盾】"]:
                            if marker in audit_part:
                                issues.append(marker)
                        if issues:
                            _log(f"  [自审发现] {' '.join(issues)} → 已修正")
                            response = corrected
                        elif "审核通过" in audit_part:
                            _log("  [自审] 审核通过")
                            if len(corrected) > len(response) * 0.5:
                                response = corrected
            except Exception as e:
                logger.warning("Self-audit failed for %s: %s",
                               section.section_id, e)

        # ── Phase 3.5: 数字白名单兜底 ──
        if _numeric_whitelist and response and len(response) > 80:
            try:
                from numeric_validator import find_inconsistencies
                errs = find_inconsistencies(response, _numeric_whitelist)
                if errs:
                    _log(f"  [数字守卫] 发现 {len(errs)} 处不一致,触发小范围重写")
                    fix_sys, fix_usr = _build_numeric_fix_prompt(response, errs)
                    fixed = llm_fn(fix_sys, fix_usr)
                    if fixed:
                        fixed = _clean_response(fixed)
                        errs2 = find_inconsistencies(fixed, _numeric_whitelist)
                        if len(errs2) < len(errs) and len(fixed) > len(response) * 0.5:
                            response = fixed
                            _log(f"  [数字守卫] 修复 {len(errs)-len(errs2)} 处,"
                                 f"剩余 {len(errs2)} 处")
            except Exception as e:
                logger.warning("Numeric guard failed for %s: %s",
                               section.section_id, e)

        # ── Phase 3.55: 变动短语守卫 ──
        if response and len(response) > 80:
            try:
                var_errs = _validate_variation_phrase(response)
                if var_errs:
                    _log(f"  [变动守卫] 发现 {len(var_errs)} 处算术异常,触发重写")
                    fix_sys, fix_usr = _build_variation_fix_prompt(response, var_errs)
                    fixed = llm_fn(fix_sys, fix_usr)
                    if fixed:
                        fixed = _clean_response(fixed)
                        errs2 = _validate_variation_phrase(fixed)
                        if len(errs2) < len(var_errs) and len(fixed) > len(response) * 0.5:
                            response = fixed
                            _log(f"  [变动守卫] 修复 {len(var_errs)-len(errs2)} 处,"
                                 f"剩余 {len(errs2)} 处")
            except Exception as e:
                logger.warning("Variation guard failed for %s: %s",
                               section.section_id, e)

        # ── Phase 3.57: 关联企业数字守卫(V12 改为代码确定性替换) ──
        if response and material_anchor is not None and len(response) > 80:
            try:
                fixed, n_fixes = _fix_affiliates_deterministic(response, material_anchor)
                if n_fixes > 0:
                    response = fixed
                    _log(f"  [关联企业守卫] 代码层替换 {n_fixes} 处错误数字")
            except Exception as e:
                logger.warning("Affiliate guard failed for %s: %s",
                               section.section_id, e)

        # ── Phase 3.58: 变动短语确定性兜底(V14v2) ──
        # (a) 变动值≈末值(如"微降38个百分点至38%"这种数学荒谬)
        # (b) 模糊兜底话术("具体幅度以财务附表为准")
        # 全部从 FinancialIndicators 取标准短语替换,无数据则降级为具体"待补充 XX"
        if response and len(response) > 80:
            try:
                fixed, n_var = _fix_variation_phrases(response, financial_indicators)
                if n_var > 0:
                    response = fixed
                    _log(f"  [变动短语兜底] 代码层修复 {n_var} 处(荒谬/兜底话术)")
            except Exception as e:
                logger.warning("Variation phrase fix failed for %s: %s",
                               section.section_id, e)

        # ── Phase 3.6: 子标题去重 ──
        if response:
            before_len = len(response)
            response = _dedupe_subheads(response)
            if len(response) < before_len:
                _log(f"  [去重] 子标题级合并: {before_len}→{len(response)}字")

        content_indices = section.content_para_indices
        para_texts = _distribute_to_paragraphs(response, content_indices, section)

        # Leakage detection + retry
        if template_paragraphs and max_retries > 0:
            leaks = detect_leakage(para_texts, template_paragraphs, threshold=0.5)
            if leaks:
                logger.warning("Template leakage in %s: %d paragraphs",
                               section.section_id, len(leaks))
                retry_usr = (usr_p + "\n\n【重要警告】上一次生成的内容"
                             "与模板范例过于相似，被判定为模板泄露。"
                             "请确保完全使用客户真实数据撰写。")
                response2 = llm_fn(sys_p, retry_usr)
                if response2:
                    response2 = _clean_response(response2)
                    para_texts2 = _distribute_to_paragraphs(
                        response2, content_indices, section)
                    leaks2 = detect_leakage(
                        para_texts2, template_paragraphs, threshold=0.5)
                    if len(leaks2) < len(leaks):
                        para_texts = para_texts2

        # ── Phase 4: pending_questions 外因问卷生成 ──
        # 扫描正文中"需补充XX"/"待补充"等具体材料请求标签,
        # 由 LLM 将其转换成给客户经理的具体问题(1-3 个)。
        if pending_questions_sink is not None and response:
            try:
                missing_aspects = _extract_missing_aspects(response)
                if missing_aspects:
                    questions = _generate_pending_questions(
                        section_id=section.section_id,
                        section_title=section.title,
                        missing_aspects=missing_aspects,
                        llm_fn=llm_fn,
                    )
                    if questions:
                        with results_lock:
                            pending_questions_sink.extend(questions)
                        _log(f"  [问卷] 产生 {len(questions)} 个待补充问题")
            except Exception as e:
                logger.warning("Pending questions generation failed for %s: %s",
                               section.section_id, e)

        return para_texts

    # V13: 并发执行 170 节(默认 10 路)
    try:
        max_workers = int(os.environ.get("SECTION_GEN_WORKERS", "10"))
    except Exception:
        max_workers = 10
    max_workers = max(1, min(max_workers, len(pending) or 1))

    _log(f"[并发生成] 共 {total} 节, 并发度 {max_workers}")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_section, s): s for s in pending}
        for fut in as_completed(futures):
            try:
                para_texts = fut.result()
            except Exception as e:
                logger.warning("Section worker failed: %s", e)
                continue
            if para_texts:
                with results_lock:
                    all_results.update(para_texts)

    return all_results


_NUMERIC_FIX_SYSTEM = (
    "你是银行信贷报告的数字修正员。\n"
    "任务:修正正文中与权威值不符的数字,保留其余全部内容不动。\n\n"
    "【硬规则】\n"
    "1. 只改数字,不改句式、不改段落结构、不改标题\n"
    "2. 错误清单以外的数字、文字一字不得改动\n"
    "3. 直接输出修正后的完整正文,不要输出解释或前言\n"
    "4. 不要输出 Markdown 标记,不要输出 === 分隔符\n"
)


# ---- 子标题级去重 ----

# 子标题识别:① ② (1) （1） 1. 1、 (一) （二）
_SUBHEAD_PREFIX_RE = re.compile(
    r"^\s*("
    r"[\u2460-\u2473]"                                   # ①-⑳
    r"|[\(（]\s*\d+\s*[\)）]"                              # (1) (2)
    r"|[\(（]\s*[一二三四五六七八九十]+\s*[\)）]"              # (一) (二)
    r"|\d+\s*[\.、．]"                                    # 1. 1、
    r")"
)


def _extract_subhead_label(line: str) -> str:
    """抽取行首子标题 label(统一格式);无子标题返回空串。"""
    m = _SUBHEAD_PREFIX_RE.match(line)
    if not m:
        return ""
    raw = m.group(1).strip()
    # 规范化:去空白、全角→半角
    s = raw.replace("（", "(").replace("）", ")").replace(" ", "")
    return s


def _dedupe_subheads(text: str) -> str:
    """同一 section 内同一子标题 label 出现多次时,保留信息量最大的一份。

    信息量 = 字数 + 数字出现次数 * 5(数字多的视为更有价值)。
    """
    if not text:
        return text
    lines = text.split("\n")

    # 切段: [(label, [line1, line2, ...]), ...]
    segments: list[tuple[str, list[str]]] = []
    current_label = ""
    current_lines: list[str] = []
    for line in lines:
        lab = _extract_subhead_label(line)
        if lab:
            if current_lines:
                segments.append((current_label, current_lines))
            current_label = lab
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_lines:
        segments.append((current_label, current_lines))

    # 统计 label 出现次数
    counts: dict[str, int] = {}
    for lab, _ in segments:
        if lab:
            counts[lab] = counts.get(lab, 0) + 1

    dup_labels = {lab for lab, c in counts.items() if c >= 2}
    if not dup_labels:
        return text

    # 对每个重复 label,只保留信息量最大的一段
    def _info_score(lines_):
        body = "\n".join(lines_)
        nums = len(re.findall(r"\d", body))
        return len(body) + nums * 5

    kept_idx: dict[str, int] = {}
    for i, (lab, lns) in enumerate(segments):
        if lab not in dup_labels:
            continue
        if lab not in kept_idx or _info_score(lns) > _info_score(segments[kept_idx[lab]][1]):
            kept_idx[lab] = i

    out_lines: list[str] = []
    for i, (lab, lns) in enumerate(segments):
        if lab in dup_labels and kept_idx.get(lab) != i:
            continue  # 丢弃重复段
        out_lines.extend(lns)

    return "\n".join(out_lines)


def _build_numeric_fix_prompt(text, errors):
    """构造"小范围数字修正"prompt(由数字白名单守卫触发)。"""
    lines = ["【错误清单(只修这些)】"]
    for i, e in enumerate(errors[:20], 1):
        lines.append(
            f"{i}. 上下文『{e.context}』:"
            f"该处 {e.tag} 写作 {e.actual}{e.unit},"
            f"权威值应为 {e.expected}{e.unit}"
        )
    lines.append("")
    lines.append("【待修正正文】")
    lines.append(text)
    lines.append("")
    lines.append("请直接输出修正后的完整正文。")
    return _NUMERIC_FIX_SYSTEM, "\n".join(lines)


# =============================================
# V11 Post-Validators
# =============================================

# 变动短语 "较年初/同比/环比 + 动词 + 变动值 + 单位 + 至 + 当前值"
_VARIATION_RE = re.compile(
    r"(较年初|较期初|较上年末|同比|环比)"
    r"(下降|下滑|降低|上升|上涨|提升|提高|增长|增加|减少|缩短|延长)"
    r"([\d.]+)"
    r"(个百分点|pct|倍|天|%)"
    r"至"
    r"([\d.]+)"
    r"(%|个百分点|pct|倍|天)?"
)


def _validate_variation_phrase(text):
    """检测 '变动值=当前值' 的典型 LLM 错误。

    例: '较年初下降42.5个百分点至42.5%' → delta=42.5 与 current=42.5 几乎相等,
         判定 LLM 把当前值误当作变动值。
    """
    if not text:
        return []
    errors = []
    seen = set()
    for m in _VARIATION_RE.finditer(text):
        matched = m.group(0)
        if matched in seen:
            continue
        seen.add(matched)
        try:
            delta = float(m.group(3))
            current = float(m.group(5))
        except Exception:
            continue
        if delta <= 1.0 and current <= 1.0:
            continue
        if abs(delta - current) < 0.05:
            errors.append((
                matched,
                f"变动值{delta}与当前值{current}几乎相等,"
                f"疑似把当前值误当作变动值"
            ))
    return errors


# 关联企业财务数字 "公司名 + (净利润/净亏损/营收类) + 金额"
# V12: 放宽 regex,允许无 "有限公司" 后缀的简称(如 "中锐海沃" / "汉鼎信息")
_AFFILIATE_METRIC_RE = re.compile(
    r"([\u4e00-\u9fa5A-Za-z()（）]{3,30}?"
    r"(?:有限公司|股份公司|集团|科技|信息|技术|软件|网络)?)"
    r"[^。;；]{0,60}?"
    r"(净利润|净亏损|营业收入|上年收入|上年营收|主营业务收入|上年营业收入)"
    r"\s*([\d,]+(?:\.\d+)?)\s*万"
)


def _validate_affiliate_profit(text, material_anchor):
    """扫关联企业财务数字,对照 MaterialAnchor.related_companies 验证。"""
    if not text or material_anchor is None:
        return []
    related = getattr(material_anchor, "related_companies", None) or []
    if not related:
        return []

    errors = []
    for m in _AFFILIATE_METRIC_RE.finditer(text):
        company_name = m.group(1).strip()
        metric = m.group(2)
        raw_val = m.group(3).replace(",", "")
        try:
            val = float(raw_val)
        except Exception:
            continue

        rc = None
        for c in related:
            cn = (c.name or "").strip()
            if not cn:
                continue
            tail_c = cn[-6:] if len(cn) >= 6 else cn
            tail_m = company_name[-6:] if len(company_name) >= 6 else company_name
            if cn in company_name or company_name in cn or tail_c in company_name or tail_m in cn:
                rc = c
                break
        if rc is None:
            continue

        # 净利润类 vs 营收类
        if metric in ("净利润", "净亏损"):
            try:
                expected = float((rc.net_profit or "0").replace(",", "") or "0")
            except Exception:
                continue
            actual = -abs(val) if metric == "净亏损" else val
            metric_label = "净利润"
            if rc.profit_suspect:
                errors.append((
                    m.group(0),
                    f"关联企业「{rc.name}」{metric_label}在锚点中标注为可疑"
                    f"[{rc.suspect_reason}],正文不得给出具体数字,"
                    f"改写为『该关联企业财务数据存疑,待人工核实』",
                ))
                continue
        else:
            try:
                expected = float((rc.revenue or "0").replace(",", "") or "0")
            except Exception:
                continue
            actual = val
            metric_label = "营业收入"
            if rc.revenue_suspect:
                errors.append((
                    m.group(0),
                    f"关联企业「{rc.name}」{metric_label}在锚点中标注为可疑"
                    f"[{rc.suspect_reason}],正文不得给出具体数字,"
                    f"改写为『该关联企业财务数据存疑,待人工核实』",
                ))
                continue

        tol = max(abs(expected) * 0.5, 50.0)
        if abs(actual - expected) > tol:
            errors.append((
                m.group(0),
                f"关联企业「{rc.name}」{metric_label}锚点值为{expected:.2f}万,"
                f"正文写作{raw_val}万偏差过大,必须改为{expected:.2f}万",
            ))
    return errors


_VARIATION_FIX_SYSTEM = (
    "你是银行信贷报告的句级修正员。\n"
    "任务:只改错误清单列出的短语,保留其余全部内容不动。\n\n"
    "【硬规则】\n"
    "1. 每条错误对应一个短语,改写要点:变动值不能等于当前值,\n"
    "   必须用『较年初下降X个百分点至Y%』/『同比缩短X天至Y天』/"
    "『较年初提升X倍至Y倍』形式,且 X≠Y\n"
    "2. 如果无法从上下文推断正确变动值,改写为『(待补充 <指标名> 近三年同比明细)』,\n"
    "   严禁输出『具体幅度以财务附表为准』『变动幅度待核』等模糊兜底话术\n"
    "3. 错误清单以外的数字、文字一字不得改动\n"
    "4. 直接输出修正后的完整正文,不要输出解释、前言或 === 分隔符\n"
)


def _build_variation_fix_prompt(text, errors):
    lines = ["【错误清单(只修这些变动短语)】"]
    for i, (matched, reason) in enumerate(errors, 1):
        lines.append(f"{i}. 『{matched}』 → {reason}")
    lines.append("")
    lines.append("【待修正正文】")
    lines.append(text)
    lines.append("")
    lines.append("请直接输出修正后的完整正文。")
    return _VARIATION_FIX_SYSTEM, "\n".join(lines)


def _build_affiliate_fix_prompt(text, errors):
    lines = ["【错误清单(只修这些关联企业数字)】"]
    for i, (matched, guidance) in enumerate(errors, 1):
        lines.append(f"{i}. 『{matched}』 → {guidance}")
    lines.append("")
    lines.append("【待修正正文】")
    lines.append(text)
    lines.append("")
    lines.append("请直接输出修正后的完整正文,只修错误清单列出的数字/短语,"
                 "其余一字不改。")
    return _NUMERIC_FIX_SYSTEM, "\n".join(lines)


# ---- V14v2: 确定性变动短语修复 ----

# metric 中文名 → FinancialIndicators 属性名 的映射
# 覆盖正文里常见的兜底/错误变动短语主语
_METRIC_ALIAS_TO_FIELD = {
    "毛利率": "gross_margin",
    "净利率": "net_margin",
    "营业利润率": "operating_margin",
    "资产负债率": "debt_to_asset_ratio",
    "流动比率": "current_ratio",
    "速动比率": "quick_ratio",
    "应收账款周转天数": "ar_turnover_days",
    "应收周转天数": "ar_turnover_days",
    "存货周转天数": "inventory_turnover_days",
}

# 变动值≈末值的荒谬短语:匹配 "...毛利率微降38.0个百分点至38.0%..."
# 允许 metric 名与动词之间插入"同比/较年初/大幅/显著/略/明显"等修饰词
_ABSURD_VARIATION_RE = re.compile(
    r"(毛利率|净利率|营业利润率|资产负债率|流动比率|速动比率|"
    r"应收账款周转天数|应收周转天数|存货周转天数)"
    r"(?:同比|较年初|大幅|显著|略|明显|小幅|继续|进一步|\s){0,6}"
    r"(微降|微升|下降|上升|缩短|延长|提升)"
    r"([\d.]+)\s*(个百分点|pct|倍|天|%)?"
    r"至"
    r"([\d.]+)\s*(%|个百分点|pct|倍|天)?"
)

# 模糊兜底短语:匹配 "XX率较年初有所变化,具体幅度以财务附表为准"
# 也覆盖"具体数字参见附表""变动幅度待核"等变体
_FUZZY_FALLBACK_RE = re.compile(
    r"(毛利率|净利率|营业利润率|资产负债率|流动比率|速动比率|"
    r"应收账款周转天数|应收周转天数|存货周转天数)"
    r"(?:同比|较年初)?有所变化[,，]"
    r"(?:具体幅度|具体数字|变动幅度)"
    r"(?:以财务附表为准|参见附表|待核|待补充)"
)


def _get_standard_variation_phrase(fi, metric_cn: str):
    """从 FinancialIndicators 取该 metric 的标准变动短语。

    返回 "较年初下降7.7个百分点至42.5%" 形式的一句话;
    若 fi 无该 metric 或无变动数据,返回 None。
    """
    if fi is None:
        return None
    field = _METRIC_ALIAS_TO_FIELD.get(metric_cn)
    if not field:
        return None
    pv = getattr(fi, field, None)
    if pv is None or pv.current is None or pv.previous is None:
        return None
    # 借用 PeriodValue.format() 内部逻辑生成变动短语
    cap = pv.compare_caption
    cur = pv.current
    unit = pv.unit
    if pv.yoy_abs is None and pv.yoy_pct is None:
        return None
    if unit == "%":
        if pv.yoy_abs is None or abs(pv.yoy_abs) < 0.05:
            return f"{metric_cn}{cap}持平(维持在{cur:.1f}%)"
        verb = "下降" if pv.yoy_abs < 0 else "上升"
        return f"{metric_cn}{cap}{verb}{abs(pv.yoy_abs):.1f}个百分点至{cur:.1f}%"
    if unit == "倍":
        if pv.yoy_abs is None or abs(pv.yoy_abs) < 0.005:
            return f"{metric_cn}{cap}持平(维持在{cur:.2f}倍)"
        verb = "下降" if pv.yoy_abs < 0 else "提升"
        return f"{metric_cn}{cap}{verb}{abs(pv.yoy_abs):.2f}倍至{cur:.2f}倍"
    if unit == "天":
        if pv.yoy_abs is None or abs(pv.yoy_abs) < 0.5:
            return f"{metric_cn}{cap}持平(维持在{cur:.0f}天)"
        verb = "缩短" if pv.yoy_abs < 0 else "延长"
        return f"{metric_cn}{cap}{verb}{abs(pv.yoy_abs):.0f}天至{cur:.0f}天"
    return None


def _fix_variation_phrases(text: str, financial_indicators) -> tuple[str, int]:
    """V14v2: 代码层兜底修复两类变动短语错误:

    (a) 变动值≈末值(数学荒谬,如"微降38.0个百分点至38.0%")
        |delta - current| / max(|delta|, |current|) < 0.02
        → 用 FinancialIndicators 标准短语替换,或 fallback 到"(待补充 XX 近三年明细)"
    (b) 模糊兜底话术("XX率较年初有所变化,具体幅度以财务附表为准")
        → 同上

    返回 (fixed_text, num_fixes)
    """
    if not text:
        return text, 0

    replacements = []  # (start, end, new_text, kind)

    # (a) 荒谬短语
    for m in _ABSURD_VARIATION_RE.finditer(text):
        metric_cn = m.group(1)
        try:
            delta = float(m.group(3))
            current = float(m.group(5))
        except Exception:
            continue
        # 双 0/极小 不算错
        if delta <= 1.0 and current <= 1.0:
            continue
        denom = max(abs(delta), abs(current), 1.0)
        if abs(delta - current) / denom >= 0.02:
            continue
        # 命中: delta≈current
        std = _get_standard_variation_phrase(financial_indicators, metric_cn)
        if std:
            new_text = std
        else:
            new_text = f"{metric_cn}变动幅度(待补充{metric_cn}近三年同比明细)"
        replacements.append((m.start(), m.end(), new_text, "absurd"))

    # (b) 模糊兜底
    for m in _FUZZY_FALLBACK_RE.finditer(text):
        metric_cn = m.group(1)
        std = _get_standard_variation_phrase(financial_indicators, metric_cn)
        if std:
            new_text = std
        else:
            new_text = f"{metric_cn}变动幅度(待补充{metric_cn}近三年同比明细)"
        replacements.append((m.start(), m.end(), new_text, "fuzzy"))

    if not replacements:
        return text, 0

    # 去重 + 从右往左替换(避免 offset 漂移)
    dedup = {}
    for s, e, n, k in replacements:
        dedup[(s, e)] = (s, e, n, k)
    reps = sorted(dedup.values(), key=lambda r: r[0], reverse=True)
    result = text
    for s, e, n, _k in reps:
        result = result[:s] + n + result[e:]
    return result, len(reps)


# ---- V12: 确定性关联企业修复 ----

def _match_related_company(company_name_in_text, related):
    """在 MaterialAnchor.related_companies 中找与正文公司名最匹配的记录。"""
    if not company_name_in_text or not related:
        return None
    name = company_name_in_text.strip()
    best = None
    best_score = 0
    for c in related:
        cn = (c.name or "").strip()
        if not cn:
            continue
        # 精确包含优先
        if cn == name:
            return c
        score = 0
        if cn in name or name in cn:
            score = max(len(cn), len(name))
        else:
            # 取尾部(通常为特征词如"汉鼎"/"海沃"/"青云")做匹配
            tail_c = cn[-6:] if len(cn) >= 6 else cn
            tail_n = name[-6:] if len(name) >= 6 else name
            if tail_c in name:
                score = len(tail_c)
            elif tail_n in cn:
                score = len(tail_n)
            else:
                # 最短公共前缀,需>=3 个字符
                shorter = min(len(cn), len(name))
                prefix_len = 0
                for i in range(shorter):
                    if cn[i] == name[i]:
                        prefix_len = i + 1
                    else:
                        break
                if prefix_len >= 3:
                    score = prefix_len
        if score > best_score:
            best_score = score
            best = c
    return best if best_score >= 3 else None


# metric + value (不含公司名)
_METRIC_VALUE_RE = re.compile(
    r"(净利润|净亏损|营业收入|上年收入|上年营收|主营业务收入|上年营业收入)"
    r"\s*([\d,]+(?:\.\d+)?)\s*万元?"
)

# 子句内的公司名(要求后缀字样)
_COMPANY_NAME_RE = re.compile(
    r"[\u4e00-\u9fa5A-Za-z()（）]{3,30}?"
    r"(?:有限公司|股份公司|股份有限公司|集团)"
)

# 普通中文词黑名单:即便被识别为核心词也跳过(歧义风险过大)
_ALIAS_BANNED = frozenset({
    "教育", "软件", "技术", "科技", "信息", "网络", "服务", "水利", "能源",
    "咨询", "工程", "投资", "发展", "集团", "控股", "工业", "贸易", "销售",
})


def _build_company_aliases(related):
    """从 RelatedCompany 列表动态构建核心词别名映射。

    目的:V14-v3b 发现 LLM 有时把"北京中锐青云科技有限公司"简写为"青云",
    F 的 _COMPANY_NAME_RE 要求后缀字样,漏匹配简称导致张冠李戴回归。
    本函数动态从关联企业全名剥离后缀+地理前缀+借款人共同前缀,抽核心词。
    通用词(教育/软件等)进黑名单,避免普通文本误杀。

    返回 [(alias_str, rc), ...] 按长度降序。无唯一核心词的公司跳过(冲撞)。
    """
    if not related:
        return []
    suffix_words = [
        "股份有限公司", "有限责任公司", "有限公司", "股份公司",
        "集团", "控股", "投资", "股份", "公司",
        "科技", "信息", "技术", "软件", "网络", "服务", "咨询",
        "工程", "贸易", "销售", "运营", "发展", "产业", "实业",
    ]
    geo_prefix = [
        "福建省", "北京市", "上海市", "广州市", "深圳市", "厦门市",
        "福建", "北京", "上海", "广州", "深圳", "厦门", "杭州", "南京",
        "天津", "重庆", "成都", "武汉", "江苏", "浙江", "山东", "广东",
        "陕西", "河南", "河北", "安徽", "四川", "湖北", "湖南", "江西",
    ]
    def _strip_geo(s: str) -> str:
        for pre in geo_prefix:
            if s.startswith(pre):
                return s[len(pre):]
        return s

    raw_names = [(c.name or "").strip() for c in related if (c.name or "").strip()]
    # 先剥地理前缀,再在剥离后的名字上算借款人共同前缀(如"中锐")
    # 这样 "福建中锐X/北京中锐Y/..." 在去掉地理后能识别出"中锐"为共同品牌
    geo_stripped = [_strip_geo(n) for n in raw_names]
    common_prefix = ""
    if len(geo_stripped) >= 2:
        shortest = min(len(n) for n in geo_stripped)
        for i in range(shortest):
            ch = geo_stripped[0][i]
            if all(n[i] == ch for n in geo_stripped):
                common_prefix += ch
            else:
                break
        if len(common_prefix) < 2:
            common_prefix = ""

    raw_cores = []
    for rc in related:
        name = (rc.name or "").strip()
        if not name:
            continue
        # 先剥地理前缀,再剥借款人共同前缀
        core = _strip_geo(name)
        if common_prefix and core.startswith(common_prefix):
            core = core[len(common_prefix):]
        # 去掉括号(如"(福建)")
        core = re.sub(r"[(（][^)）]*[)）]", "", core).strip()
        # 循环剥离尾部通用词
        changed = True
        while changed and core:
            changed = False
            for suf in suffix_words:
                if core.endswith(suf) and len(core) > len(suf):
                    core = core[: -len(suf)]
                    changed = True
                    break
        core = core.strip()
        if len(core) < 2 or core in _ALIAS_BANNED:
            continue
        raw_cores.append((core, rc))

    # 冲撞剔除:两家公司同核心词 → 都跳过(避免误归属)
    from collections import Counter
    counts = Counter(c for c, _ in raw_cores)
    final = [(c, r) for c, r in raw_cores if counts[c] == 1]
    final.sort(key=lambda x: -len(x[0]))
    return final


def _fix_affiliates_deterministic(text, material_anchor):
    """V14v2: 代码层直接替换关联企业财务数字,不经 LLM。

    子句级扫描(以 ;；。 分句),每个子句内按**左→右 token 位置**扫描:
      - 公司名 token → 更新 current_rc
      - metric+值 token → 归属到最近一次出现的 current_rc
    这样"A公司(收入X,净利Y)、B公司(收入P,净利Q)"这类单子句多家公司格式
    也能 1:1 对齐源材料。

    返回 (fixed_text, num_fixes)
    """
    if not text or material_anchor is None:
        return text, 0
    related = getattr(material_anchor, "related_companies", None) or []
    if not related:
        return text, 0

    aliases = _build_company_aliases(related)

    replacements = []  # (start, end, new_text)
    # 以 ;；。 作为子句分隔符,保留每个子句在原文中的 offset
    clause_bounds = []
    start = 0
    for i, ch in enumerate(text):
        if ch in "。;；":
            clause_bounds.append((start, i))
            start = i + 1
    if start < len(text):
        clause_bounds.append((start, len(text)))

    for cs, ce in clause_bounds:
        clause = text[cs:ce]

        # 1) 收集子句内全部 tokens: (pos, kind, payload)
        tokens = []
        for cm in _COMPANY_NAME_RE.finditer(clause):
            tokens.append((cm.start(), "company_full", cm))
        for mm in _METRIC_VALUE_RE.finditer(clause):
            tokens.append((mm.start(), "metric", mm))
        # alias 扫描:简称(如"青云"/"汉鼎"/"海沃")若独立出现也算公司 token
        alias_spans: list[tuple[int, int]] = []
        for alias_str, rc in aliases:
            for am in re.finditer(re.escape(alias_str), clause):
                s, e = am.start(), am.end()
                # 避免与已有 company_full span 重叠(LLM 写全名时也会命中 alias)
                if any(not (e <= fs or s >= fe)
                       for (fs, fe) in [(x[2].start(), x[2].end())
                                        for x in tokens if x[1] == "company_full"]):
                    continue
                alias_spans.append((s, e))
                tokens.append((s, "company_alias", rc))
        if not tokens:
            continue
        tokens.sort(key=lambda t: t[0])

        # 2) 左→右扫: 每遇公司名更新 current_rc, metric 归最近 current_rc
        current_rc = None
        for _pos, kind, m in tokens:
            if kind == "company_full":
                company_name = m.group(0).strip()
                rc = _match_related_company(company_name, related)
                if rc is not None:
                    current_rc = rc
                # 公司名未匹配到 anchor 记录时保留上一 current_rc(可能是简称)
                continue
            if kind == "company_alias":
                current_rc = m  # m 就是 rc 本身
                continue

            # metric
            if current_rc is None:
                continue
            rc = current_rc
            metric = m.group(1)
            raw_val = m.group(2).replace(",", "")
            try:
                val = float(raw_val)
            except Exception:
                continue

            is_profit_metric = metric in ("净利润", "净亏损")

            # 可疑数据 → 替换为"待人工核实"
            if is_profit_metric and rc.profit_suspect:
                new_tail = "财务数据存疑待人工核实"
            elif (not is_profit_metric) and rc.revenue_suspect:
                new_tail = "财务数据存疑待人工核实"
            else:
                try:
                    if is_profit_metric:
                        expected = float((rc.net_profit or "0").replace(",", "") or "0")
                    else:
                        expected = float((rc.revenue or "0").replace(",", "") or "0")
                except Exception:
                    continue

                actual = -abs(val) if metric == "净亏损" else val
                tol = max(abs(expected) * 0.5, 50.0)
                if abs(actual - expected) <= tol:
                    continue  # 在容差内,不改

                if is_profit_metric:
                    if abs(expected) < 1:
                        new_tail = "净利润规模极小(不足1万元)"
                    elif expected < 0:
                        new_tail = f"净亏损{abs(expected):.0f}万元"
                    else:
                        new_tail = f"净利润{expected:.0f}万元"
                else:
                    if abs(expected) < 1:
                        new_tail = "上年无主营业务收入"
                    else:
                        new_tail = f"营业收入{expected:.0f}万元"

            abs_start = cs + m.start()
            abs_end = cs + m.end()
            replacements.append((abs_start, abs_end, new_tail))

    if not replacements:
        return text, 0

    # 去重 (同一 span 可能被多个子句匹配) 并从右往左替换
    replacements = list({(s, e): (s, e, n) for s, e, n in replacements}.values())
    replacements.sort(key=lambda r: r[0], reverse=True)
    result = text
    for s, e, n in replacements:
        result = result[:s] + n + result[e:]
    return result, len(replacements)


def _extract_corrected_text(audit_response):
    """Extract the corrected text from audit response.

    The audit response format is:
      审核意见...
      ===
      修正后的正文...
    """
    if "===" in audit_response:
        parts = audit_response.split("===", 1)
        if len(parts) >= 2:
            return _clean_response(parts[1])

    # Fallback: if no separator, try to find the main text block
    # (audit output after the last issue marker)
    lines = audit_response.strip().split("\n")
    text_start = 0
    for i, line in enumerate(lines):
        if any(m in line for m in ["【幻觉】", "【错误】", "【冗余】", "【矛盾】", "审核通过"]):
            text_start = i + 1

    if text_start > 0 and text_start < len(lines):
        return _clean_response("\n".join(lines[text_start:]))

    return None


# =============================================
# Pending Questions (外因问卷生成)
# =============================================

# 扫描正文中"需补充XX"这类具体材料请求标签。
#   【严格】只匹配系统规范的缺材料句式,不匹配泛泛"材料不足"。
_MISSING_ASPECT_PATTERNS = [
    # "需补充X材料" / "需近三年XX表" / "需主要XX明细"
    re.compile(r'需(?:补充|提供|查看)?[^。;；\n]{3,60}?(?:表|清单|合同|明细|报告|凭证|数据|文件|资料|证明|附表)'),
    # "缺失XX/XX材料" (不要吞整段)
    re.compile(r'缺失[^。;；\n]{3,40}?(?:表|清单|合同|明细|报告|凭证|数据|文件|资料)'),
    # "待补充XX" / "待提供XX"
    re.compile(r'待(?:补充|提供)[^。;；\n]{3,40}?(?:表|清单|合同|明细|报告|凭证|数据|文件|资料)'),
]


def _extract_missing_aspects(text: str) -> list[str]:
    """从生成的正文中抽取"需补充XX"这类具体材料请求短语(最多 5 个)。"""
    if not text:
        return []
    aspects = []
    seen = set()
    for pat in _MISSING_ASPECT_PATTERNS:
        for m in pat.finditer(text):
            s = m.group(0).strip()
            # 去掉开头"需"/"待补充"等动词,保留核心名词短语
            key = re.sub(r'^(需|待补充|待提供|缺失)', '', s).strip()
            if key and key not in seen and 5 <= len(key) <= 80:
                seen.add(key)
                aspects.append(s)
            if len(aspects) >= 5:
                return aspects
    return aspects


_PENDING_Q_SYSTEM = (
    "你是银行信贷报告的'缺失材料问卷生成员'。\n"
    "任务:把报告某章节中标注的『需补充XX材料』转成给客户经理/客户的具体问题。\n\n"
    "【硬规则】\n"
    "1. 每个材料请求转成 1 个具体问题,问题要落到:要补充什么文件/数据 + 时间范围(如有)\n"
    "2. question 字段用中文问句(以?或？结尾),不要用陈述句\n"
    "3. hint 字段写 1 句提示,说明为什么需要(用于哪段分析)\n"
    "4. input_type 从下列选一个:'file'(需上传文件)/'text'(需填写文本说明)/"
    "'table'(需填写表格)/'number'(需填写数字)\n"
    "5. 严格 JSON 数组,每元素字段 {question, hint, input_type}\n"
    "6. 输出≤3个最重要的问题,宁少勿多\n"
    "7. 禁止出现『审贷会』『贷审会』『上会』等下一步流程名"
)


def _generate_pending_questions(
    section_id: str,
    section_title: str,
    missing_aspects: list,
    llm_fn=None,
) -> list:
    """基于被生成段落里标记的'需补充 XX'点,调用 LLM 生成 1-3 个待补充问题。

    Args:
        section_id: SectionInfo.section_id
        section_title: SectionInfo.title
        missing_aspects: list[str],如 ['需近三年分产品线毛利率表', ...]
        llm_fn: (system_prompt, user_prompt) -> str
    Returns:
        list of dict: {id, section_id, section_title, question, hint, input_type}
    """
    if not missing_aspects or llm_fn is None:
        return []

    import json as _json
    user_prompt = (
        "【章节】" + (section_title or "") + "\n"
        "【章节 ID】" + (section_id or "") + "\n"
        "【本章节被标注为缺失的具体材料】\n"
        + "\n".join("  - " + a for a in missing_aspects[:5])
        + "\n\n请按 system 规则输出一个 JSON 数组,每元素含 "
        "{question, hint, input_type} 三字段,≤3 条。"
        "只输出 JSON,不要解释。"
    )
    try:
        resp = llm_fn(_PENDING_Q_SYSTEM, user_prompt)
    except Exception:
        return []
    if not resp:
        return []

    # 提取 JSON 数组
    resp = resp.strip()
    # 去代码块围栏
    resp = re.sub(r'^```[a-z]*\n?', '', resp, flags=re.MULTILINE)
    resp = re.sub(r'^```\s*$', '', resp, flags=re.MULTILINE)
    start = resp.find('[')
    end = resp.rfind(']')
    if start < 0 or end <= start:
        return []
    payload = resp[start:end + 1]
    try:
        arr = _json.loads(payload)
    except Exception:
        return []
    if not isinstance(arr, list):
        return []

    out = []
    for i, item in enumerate(arr[:3]):
        if not isinstance(item, dict):
            continue
        q = (item.get("question") or "").strip()
        h = (item.get("hint") or "").strip()
        itp = (item.get("input_type") or "text").strip()
        if not q:
            continue
        if itp not in ("file", "text", "table", "number"):
            itp = "text"
        out.append({
            "id": f"{section_id}_q{i + 1:02d}",
            "section_id": section_id,
            "section_title": section_title,
            "question": q,
            "hint": h,
            "input_type": itp,
        })
    return out


def _clean_response(text):
    """Clean LLM response."""
    text = re.sub(r'^```[a-z]*\n?', '', text, flags=re.MULTILINE)
    text = re.sub(r'^```\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    text = _sanitize_output(text)
    return text.strip()


# Prompt 格式标记,若 LLM 把它们回显到正文里需清除
_LEAKED_MARKER_LABELS = (
    "章节标题", "本节标题",
    "本节需要回答的问题", "本节结构要求",
    "写作提示", "证据清单",
    "待审核的报告正文", "待修正正文",
    "模板范例",
    "企业画像锚点", "财务数据锚点",
    "客户材料摘要", "补充材料原文",
    "关键规则", "铁律", "输出格式",
    "你的思考框架", "审核清单",
    # 新增: Phase2 注入块 (V6 观察到全块回显)
    "已计算财务指标", "本节必写字段锚点",
    "撰写硬规则", "财务主体归属硬规则",
    "行业基准参照", "结构化材料锚点",
    "错误清单",
    # 审核阶段格式标记
    "审核意见", "修正后的完整正文", "修正后的正文",
    "幻觉", "冗余", "矛盾", "分析缺失",
    # 禁止回显的结构块
    "禁止回显的结构块",
)

# 块内子标题前缀(单独成行的)
_LEAKED_LINE_PREFIXES = (
    "口径说明:", "口径说明：",
    "数据来源:", "数据来源：",
    "报告日:", "报告日：",
    "[规模]", "[盈利能力]", "[偿债能力]", "[营运效率]", "[现金流]",
    "[关键科目原始期末值]", "[关键科目原始期末值(万元,供引用)]",
    "[代码识别的异常项]", "[代码识别的异常项 / 需重点关注]",
    "[趋势定性]",
)

# 证据清单条目行: ✓xxx / ✗xxx — LLM 把证据列表直接当正文回显时用
_EVIDENCE_LINE_RE = re.compile(r"^[ \t]*[✓✗][\s\S]{0,300}?\[来源[:：][^\]]*\][ \t]*$",
                               flags=re.MULTILINE)
# 保守版: 行首是 ✓/✗ 且行末含 [来源:...]
_SOURCE_TAG_RE = re.compile(r"\[来源[:：][^\]]*\]")


def _sanitize_output(text):
    """Strip leaked prompt markers, placeholders, and stray table formatting.

    Handles:
      - 【章节标题】xxx / 【本节标题】xxx 等 prompt 格式头被 LLM 回显
      - [待补充] / 【待补充】 / （待补充） 占位符残留
      - Markdown 表格残留行 (| --- | --- |) 以及行首/行尾孤立竖线
    """
    if not text:
        return text

    # 1) 逐行过滤泄漏的 prompt / 证据 / 数据块内容。
    #    策略:
    #    - 【marker(任意附加)】 头一律删除, 并进入 in_data_block 模式
    #    - [规模]/[盈利能力]/... 等子块标题同理
    #    - in_data_block 中: 数据行(短字段:值)、(来源:...)/├/└/  ...等样式一律删
    #    - 空行结束 block 模式
    #    - 行首 ✓/✗ 一律视为证据条目
    #    - "1. 【幻觉】..." / "2. 【分析缺失】..." 等审核条目一律删
    #    - "===" 分隔符删除

    _DATA_ROW_RE = re.compile(
        r"^\s*[\u4e00-\u9fa5A-Za-z0-9（）()/%·\-+.\s]{1,20}[:：]\s*[^\s].*$"
    )
    # 模板 marker 的组合正则 (一次匹配任一 marker)
    _MARKER_UNION_RE = re.compile(
        r"^[ \t]*【\s*(" +
        "|".join(re.escape(m) for m in _LEAKED_MARKER_LABELS) +
        r")[^】]*】[^\n]*$"
    )
    # block 内部常见前缀: (来源:  ├  └  数字纯表格行等
    _BLOCK_CONTINUATION_RE = re.compile(
        r"^[ \t]*(\(来源[:：]|├|└|[\u2500-\u257F]|来源[:：]|•|·)"
    )

    lines_filtered = []
    in_data_block = False
    for line in text.split("\n"):
        stripped = line.strip()

        # 空行: 结束 block 模式, 保留空行
        if not stripped:
            in_data_block = False
            lines_filtered.append(line)
            continue

        # 【marker(任意)】 头
        if _MARKER_UNION_RE.match(line):
            in_data_block = True
            continue

        # [子块标题] 头
        if any(stripped.startswith(p) for p in _LEAKED_LINE_PREFIXES):
            in_data_block = True
            continue

        # 在 data block 中: 数据行 / 续行样式全部跳过
        if in_data_block:
            if (_DATA_ROW_RE.match(stripped)
                    or _BLOCK_CONTINUATION_RE.match(line)):
                continue
            # 遇到真正的 prose 行 → 退出 block 模式, 保留本行
            in_data_block = False

        # 行首 ✓/✗ 证据条目
        if stripped.startswith(("✓", "✗")):
            continue

        # 审核条目: "N. 【幻觉】..." / "- 【错误】..." / "【幻觉】..."
        if re.match(
                r"^\s*(?:\d+[.)、]|[-*•])?\s*[\[【]\s*"
                r"(幻觉|错误|冗余|矛盾|分析缺失)\s*[\]】]",
                stripped):
            continue

        # "===" 分隔符
        if re.match(r"^={2,}$", stripped):
            continue

        lines_filtered.append(line)
    text = "\n".join(lines_filtered)

    # 2) 清理占位符 [待补充] 【待补充】 （待补充） (待补充) 待确认 待核实
    text = re.sub(
        r'[\[【（(]\s*(?:待补充|待确认|待核实|待填|TBD|TODO)\s*[\]】）)]',
        '', text, flags=re.IGNORECASE)

    # 3) 清理 markdown 表格分隔行  | --- | :-- |
    text = re.sub(
        r'^[ \t]*\|[\s\-:|]+\|?[ \t]*$',
        '', text, flags=re.MULTILINE)

    # 4) 去掉行首/行尾孤立的 | (markdown 表格行残留)
    text = re.sub(r'^[ \t]*\|', '', text, flags=re.MULTILINE)
    text = re.sub(r'\|[ \t]*$', '', text, flags=re.MULTILINE)

    # 4.1) 裁掉 5+ 位精度浮点 (1.818974657571668 → 1.82)
    #      只保留 2 位小数。不影响整数/1-2 位小数/年份。
    text = re.sub(r'(\d+\.\d{2})\d{2,}', r'\1', text)

    # 4.2) 过滤表格 cell 残影行: 独占一行的"数字+中文姓名"组合
    #      (正常 prose 中数字带单位/句号,不会是这种裸数+姓名模式)
    #      例: "39 4100 4100 黄祖海" → 整行删除
    _TABLE_RESIDUE_RE = re.compile(
        r'^\s*(?:\d+[\s\u3000]+){2,}[\u4e00-\u9fa5]{2,5}\s*$'
    )
    text = "\n".join(
        l for l in text.split("\n") if not _TABLE_RESIDUE_RE.match(l)
    )

    # 4.3) V14-v3 text 层 sanitize 增强

    # (a) "(材料未提供) 万元" / "(材料未提供)万元" → "(待补充金额,单位:万元)"
    text = re.sub(
        r'[（(]\s*材料未提供\s*[)）]\s*万?元',
        '(待补充金额,单位:万元)', text
    )
    text = re.sub(
        r'[（(]\s*材料未提供\s*[)）]',
        '(待补充相关材料)', text
    )

    # (b) "(具体原因需企业补充说明)" / "(具体数字需核实)" 嵌套括号兜底
    #     → 去掉括号,转为句末追加 ",需补充具体原因/具体数字说明"
    def _convert_nested_placeholder(m):
        content = m.group(1)
        return f",需补充{content}"

    text = re.sub(
        r'[（(]\s*(具体原因[^)）]{0,30}需[^)）]{0,20}补充[^)）]{0,20})\s*[)）]',
        _convert_nested_placeholder, text
    )
    text = re.sub(
        r'[（(]\s*(具体数字[^)）]{0,30}需[^)）]{0,20}核实[^)）]{0,20})\s*[)）]',
        _convert_nested_placeholder, text
    )
    text = re.sub(
        r'[（(]\s*(具体[^)）]{0,20}待[^)）]{0,20}补充[^)）]{0,20})\s*[)）]',
        _convert_nested_placeholder, text
    )

    # (c) "例: 『...』" / "例: 「...」" prompt 示例包裹残留 → 整体删除
    text = re.sub(
        r'例\s*[：:]\s*[『「][^』」]{0,200}[』」]',
        '', text
    )

    # (d) LLM 自加的黑体 **...** → 去掉包裹符(内容保留)
    text = re.sub(r'\*\*([^*\n]+)\*\*', r'\1', text)

    # (e) 孤立"材料不足"句 → 句末追加"需补充具体明细"
    #     只匹配未已经追加过的情况(后 30 字内无 "具体"/"需补充"/",需补充")
    def _augment_bare_insufficient(m):
        return m.group(0) + ",需补充具体明细"

    text = re.sub(
        r'材料不足(?![^\n]{0,30}(?:具体|需补充|,需补充))',
        _augment_bare_insufficient, text
    )

    # 5) 折叠多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 6) BS 科目口径兜底: 存量科目后紧邻"同比"→"较年初"
    #    (LLM 即便被锚点提醒,仍可能按训练语料习惯写"同比";这里做确定性修正)
    text = _fix_bs_caption(text)

    return text


_BS_STOCK_SUBJECTS = [
    "总资产", "资产总计", "总负债", "负债合计",
    "所有者权益", "股东权益", "净资产",
    "资产负债率", "流动比率", "速动比率",
    "货币资金", "应收账款", "存货", "短期借款",
    "长期借款", "应付账款", "预付账款", "预收账款",
    "其他应收款", "其他应付款",
]


def _fix_bs_caption(text: str) -> str:
    """将 <BS 存量科目>...同比  →  <BS 存量科目>...较年初
    排除"应收账款周转天数"这类流量口径。
    """
    if not text:
        return text
    for subj in _BS_STOCK_SUBJECTS:
        # subj 后紧跟"周转"/"周转天数"的视为流量,不改
        pat = re.compile(
            rf"({re.escape(subj)}(?!周转)[^\n。;；]{{0,25}}?)同比"
        )
        text = pat.sub(r"\1较年初", text)
    return text


def _distribute_to_paragraphs(generated_text, content_indices, section):
    """Distribute generated text to CONTENT paragraph slots."""
    if not content_indices:
        return {}

    blocks = [b.strip() for b in generated_text.split('\n') if b.strip()]

    merged = []
    for b in blocks:
        if merged and len(b) < 30 and not _looks_like_new_paragraph(b):
            merged[-1] += b
        else:
            merged.append(b)
    blocks = merged if merged else [generated_text.strip()]

    result = {}

    if len(content_indices) == 1:
        result[content_indices[0]] = generated_text.strip()
    elif len(blocks) <= len(content_indices):
        for i, idx in enumerate(content_indices):
            if i < len(blocks):
                result[idx] = blocks[i]
            else:
                result[idx] = ""
    else:
        for i in range(len(content_indices) - 1):
            result[content_indices[i]] = blocks[i]
        remaining = "\n".join(blocks[len(content_indices) - 1:])
        result[content_indices[-1]] = remaining

    return result


def _looks_like_new_paragraph(text):
    """Check if text looks like a new paragraph start."""
    pat = (r'^[(\uff08][\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341]'
           r'|^\d+[.\uff0e\u3001]'
           r'|^[\u2460\u2461\u2462\u2463\u2464\u2465\u2466\u2467\u2468\u2469]'
           r'|^[\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341]+\u3001'
           r'|^\u203b')
    return bool(re.match(pat, text.strip()))


# =============================================
# Apply to Word document
# =============================================

def apply_section_results(doc, results, body_cell_path=(0, 3, 0)):
    """Write generated content back to Word document.

    Returns: number of paragraphs applied
    """
    table_idx, row_idx, col_idx = body_cell_path
    cell = doc.tables[table_idx].rows[row_idx].cells[col_idx]
    paragraphs = cell.paragraphs
    applied = 0

    for para_idx, new_text in results.items():
        if para_idx >= len(paragraphs):
            continue

        para = paragraphs[para_idx]
        if not new_text:
            _clear_paragraph(para)
            applied += 1
            continue

        _distribute_text_to_runs(para, new_text)
        applied += 1

    return applied


def _clear_paragraph(para):
    """Clear paragraph text, preserving the paragraph element."""
    for run in para.runs:
        run.text = ""


def _distribute_text_to_runs(para, new_text):
    """Distribute new text to runs, preserving formatting."""
    runs = para.runs
    if not runs:
        para.add_run(new_text)
        return

    if len(runs) == 1:
        runs[0].text = new_text
    else:
        runs[0].text = new_text
        for run in runs[1:]:
            run.text = ""


# =============================================
# Output validation gate
# =============================================

def validate_output(doc, template_paragraphs, body_cell_path=(0, 3, 0),
                    threshold=0.5):
    """Final output validation: detect template leakage."""
    table_idx, row_idx, col_idx = body_cell_path
    cell = doc.tables[table_idx].rows[row_idx].cells[col_idx]
    paragraphs = cell.paragraphs

    generated = {}
    for p in template_paragraphs:
        if p.role == TemplateRole.CONTENT and p.para_idx < len(paragraphs):
            generated[p.para_idx] = paragraphs[p.para_idx].text

    return detect_leakage(generated, template_paragraphs, threshold=threshold)
