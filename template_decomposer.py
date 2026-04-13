"""
模板拆解层 (Template Decomposition Layer)

将模板的每个段落分类为两种角色：
  SKELETON — 章节标题、字段标签、结构性元素 → 原样保留
  CONTENT  — 范例文本、写作指导 → 用真实内容替换

核心原则：宁可多重写，不可漏重写。
任何不确定的段落都归为 CONTENT（会被重写），因为：
- 误重写骨架 → LLM 大概率会复现标题（低风险）
- 漏重写范例 → 模板泄漏（高风险，这正是我们要根治的问题）
"""

import re
from dataclasses import dataclass, field as dc_field
from difflib import SequenceMatcher
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════

class TemplateRole(Enum):
    SKELETON = "skeleton"   # 标题、标签、结构 → 保留
    CONTENT = "content"     # 范例、指导 → 重写
    # 细粒度角色（向下兼容：PRESERVE/DATA_SLOT 等同于 SKELETON，EXAMPLE/INSTRUCTION 等同于 CONTENT）
    PRESERVE = "preserve"       # 保留原样的结构标题、编号、表头
    EXAMPLE = "example"         # 需要完全替换的示例文本
    DATA_SLOT = "data_slot"     # 仅包含 XX/下划线 的占位行
    INSTRUCTION = "instruction" # 模板中的指导说明文字（请、简述、列明等）


@dataclass
class ParaInfo:
    """一个段落的分类结果"""
    para_idx: int
    text: str
    role: TemplateRole
    is_heading: bool = False
    heading_level: int = 0      # 1=一、 2=（一） 3=1. 4=①/※
    section_id: str = ""
    # 从段落中提取的写作指令（括号内的"请..."等）
    embedded_instructions: list = dc_field(default_factory=list)


@dataclass
class SectionInfo:
    """一个逻辑章节"""
    section_id: str
    title: str
    level: int
    paragraphs: list[ParaInfo] = dc_field(default_factory=list)

    @property
    def skeleton_lines(self) -> list[str]:
        """本节的结构性文本（标题+标签行）"""
        _skeleton_roles = {TemplateRole.SKELETON, TemplateRole.PRESERVE, TemplateRole.DATA_SLOT}
        return [p.text for p in self.paragraphs
                if p.role in _skeleton_roles and p.text.strip()]

    @property
    def content_lines(self) -> list[str]:
        """本节的范例文本（将被重写）"""
        _content_roles = {TemplateRole.CONTENT, TemplateRole.EXAMPLE, TemplateRole.INSTRUCTION}
        return [p.text for p in self.paragraphs
                if p.role in _content_roles and p.text.strip()]

    @property
    def all_instructions(self) -> list[str]:
        """本节所有写作指令（从骨架行括号中提取 + CONTENT 中的指导句）"""
        result = []
        for p in self.paragraphs:
            result.extend(p.embedded_instructions)
        return result

    @property
    def content_para_indices(self) -> list[int]:
        """需要重写的段落索引"""
        _content_roles = {TemplateRole.CONTENT, TemplateRole.EXAMPLE, TemplateRole.INSTRUCTION}
        return [p.para_idx for p in self.paragraphs
                if p.role in _content_roles and p.text.strip()]

    @property
    def has_content_to_rewrite(self) -> bool:
        return len(self.content_lines) > 0


# ═══════════════════════════════════════════
# 分类规则
# ═══════════════════════════════════════════

_HEADING_PATTERNS = [
    (re.compile(r'^[一二三四五六七八九十]+、'), 1),
    (re.compile(r'^[（(][一二三四五六七八九十]+[)）]'), 2),
    (re.compile(r'^\d+[.．、]'), 3),
    (re.compile(r'^[①②③④⑤⑥⑦⑧⑨⑩]'), 4),
    (re.compile(r'^※\s*\d*[.．、]?'), 4),
]

# 签名行关键词 — 这些行属于 SKELETON（银行内部签名，保留不动）
_SIGNATURE_KEYWORDS = [
    '客户经理：', '共同调查人:', '共同调查人：',
    '管理经理/', '分管行长：', '行长：',
    '审查员：', '审批人：',
    '尽职调查：经营单位对上述材料真实性负责',
]


def _detect_heading(text: str) -> tuple[bool, int]:
    """检测标题。返回 (是否标题, 层级)"""
    stripped = text.strip()
    for pat, level in _HEADING_PATTERNS:
        if pat.match(stripped):
            return True, level
    return False, 0


def _extract_instructions(text: str) -> list[str]:
    """从骨架行中提取括号内的写作指令"""
    instructions = []
    # 匹配包含指导性动词的括号内容
    for m in re.finditer(
        r'[（(]([^)）]{4,80}(?:请|如|须|应|若|包括但不限于|可另附|可附)[^)）]{0,80})[）)]',
        text
    ):
        instructions.append(m.group(1).strip())
    return instructions


def _classify_paragraph(text: str) -> tuple[TemplateRole, bool, int]:
    """
    分类单个段落。

    返回: (角色, 是否标题, 标题层级)

    分类逻辑（按优先级）：
    1. 空行 → SKELETON
    2. 标题行 → SKELETON
    3. 签名行 → SKELETON
    4. 短标签行（<80字，以冒号结尾，无大段文字） → SKELETON
    5. 纯占位符行（主要是下划线/空格 + 标签） → SKELETON
    6. 表格注释行（"单位：万元"） → SKELETON
    7. 复选框行（主要由 □/☑ 选项构成） → SKELETON
    8. 其他一切 → CONTENT（安全默认，宁多重写）
    """
    stripped = text.strip()

    # 1. 空行
    if not stripped:
        return TemplateRole.SKELETON, False, 0

    is_h, level = _detect_heading(stripped)

    # 2. 标题行 — 但如果包含范例内容，归为 CONTENT
    #    判断标准：
    #    a) 太长（>=150字）→ 含范例内容
    #    b) 含 XX 占位符且长度>40 → 需要填写的范例
    #    c) 含冒号后接大段文字（标题：范例内容）且总长>100
    #    d) 含冒号后有范例特征（……/、/等连接多描述）且总长>40
    if is_h:
        has_xx = bool(re.search(r'X{2,}', stripped))
        # 冒号后有多少内容？
        colon_pos = max(stripped.find('：'), stripped.find(':'))
        after_colon_len = len(stripped) - colon_pos - 1 if colon_pos > 0 else 0
        # 冒号后的文本
        after_colon_text = stripped[colon_pos + 1:] if colon_pos > 0 else ""
        # 范例特征：省略号、泛指描述、斜杠分支、"如：" 示例引导等
        has_example_markers = bool(re.search(
            r'[\u2026\u00b7]|\.{2,}|/{1}[\u4e00-\u9fff]|'
            r'\u5982[\uff1a:]|'   # "如："
            r'\d{3,}[\u4e07\u5143\u540d\u4eba]',   # 具体数字+单位 (500万, 240名)
            after_colon_text))

        if len(stripped) >= 150:
            return TemplateRole.CONTENT, True, level
        if has_xx and len(stripped) > 40:
            return TemplateRole.CONTENT, True, level
        if after_colon_len > 80 and len(stripped) > 100:
            # 标题后跟了大段范例文字
            return TemplateRole.CONTENT, True, level
        if after_colon_len > 30 and len(stripped) > 50:
            # 冒号后有大量内容（纯标签行不会这么长）
            return TemplateRole.CONTENT, True, level
        if has_example_markers and after_colon_len > 20 and len(stripped) > 40:
            # 标题后跟了含范例特征的描述文字
            return TemplateRole.CONTENT, True, level
        return TemplateRole.SKELETON, True, level

    # 3. 签名/日期行
    for kw in _SIGNATURE_KEYWORDS:
        if kw in stripped:
            return TemplateRole.SKELETON, False, 0
    if re.match(r'^日期[：:]\s', stripped):
        return TemplateRole.SKELETON, False, 0

    # 4. 短标签行（以冒号结尾，且没有大段描述文字）
    #    比如 "关联企业关系：可附图"  "最近三年现金流量表分析："
    if len(stripped) < 80 and re.search(r'[：:]\s*$', stripped):
        return TemplateRole.SKELETON, False, 0

    # 5. 纯占位符/标签行
    #    比如 "上年度末社保人数     人；注册资本：         万元"
    #    特征：短，有大片空白或下划线
    blank_ratio = (stripped.count(' ') + stripped.count('　') +
                   stripped.count('_') + stripped.count('\t'))
    if len(stripped) < 120 and blank_ratio > len(stripped) * 0.3:
        return TemplateRole.SKELETON, False, 0

    # 6. 表格注释
    if re.match(r'^单位[：:]|^备注[：:]', stripped) and len(stripped) < 60:
        return TemplateRole.SKELETON, False, 0

    # 7. 复选框密集行（>= 2 个复选框，且行较短）
    cb_count = len(re.findall(r'[□☐☑✓]', stripped))
    if cb_count >= 2 and len(stripped) < 200:
        return TemplateRole.SKELETON, False, 0
    # 单个复选框但行很短
    if cb_count >= 1 and len(stripped) < 60:
        return TemplateRole.SKELETON, False, 0

    # 8. 兜底 → CONTENT
    return TemplateRole.CONTENT, False, 0


# ═══════════════════════════════════════════
# 细粒度段落角色分类
# ═══════════════════════════════════════════

# 模板示例行业关键词（宁多勿漏）
_TEMPLATE_SAMPLE_KEYWORDS = [
    "注塑", "模具", "塑胶", "某某", "XX公司", "XX有限", "XX集团",
    "XX银行", "XX事务所", "张XX", "李XX", "王XX", "陈XX", "刘XX",
]

# 指导性动词短语（必须是明确的指导结构，避免单字误匹配）
_INSTRUCTION_PHRASES = [
    "简述", "列明", "填写", "阐述", "标注",
]

# XX 占位符模式（宽松匹配）
_XX_PLACEHOLDER_RE = re.compile(r'X{2,}')

# 纯占位符行模式：仅包含 XX、下划线、空格、冒号、标签文字（<30字非占位内容）
_PURE_SLOT_RE = re.compile(r'^[\s_X：:．.、\u3000]*$')


def classify_paragraph_role(
    text: str,
    context_before: str = "",
    context_after: str = "",
) -> TemplateRole:
    """
    细粒度判断段落角色。

    分类优先级：
    1. PRESERVE — 编号格式开头的短标题；表头行；固定标题；签名行
    2. DATA_SLOT — 仅包含 XX 或下划线，无其他叙述内容
    3. INSTRUCTION — 包含指导性动词
    4. EXAMPLE — 包含 XX 占位符 + 叙述性文本；包含模板样例关键词
    5. 兜底 → EXAMPLE（宁可多标记也不要漏标记）

    Args:
        text: 段落文本
        context_before: 前一个段落的文本（可选，用于上下文辅助判断）
        context_after: 后一个段落的文本（可选）

    Returns:
        TemplateRole 枚举值
    """
    stripped = text.strip()

    # 空行 → PRESERVE
    if not stripped:
        return TemplateRole.PRESERVE

    is_h, level = _detect_heading(stripped)

    # ---- PRESERVE 判断 ----
    # 签名行
    for kw in _SIGNATURE_KEYWORDS:
        if kw in stripped:
            return TemplateRole.PRESERVE

    # 日期行
    if re.match(r'^日期[：:]\s', stripped):
        return TemplateRole.PRESERVE

    # 编号格式开头的短标题（无 XX，较短）
    if is_h and len(stripped) < 80:
        has_xx = bool(_XX_PLACEHOLDER_RE.search(stripped))
        if not has_xx:
            return TemplateRole.PRESERVE

    # 表头行
    if re.match(r'^单位[：:]|^备注[：:]', stripped) and len(stripped) < 60:
        return TemplateRole.PRESERVE

    # 复选框密集行
    cb_count = len(re.findall(r'[□☐☑✓]', stripped))
    if cb_count >= 2 and len(stripped) < 200:
        return TemplateRole.PRESERVE
    if cb_count >= 1 and len(stripped) < 60:
        return TemplateRole.PRESERVE

    # 短标签行（以冒号结尾，且没有大段描述文字）
    if len(stripped) < 80 and re.search(r'[：:]\s*$', stripped):
        return TemplateRole.PRESERVE

    # 审查意见等固定标题
    _fixed_titles = ["审查意见", "审批意见", "尽职调查", "意见表"]
    if any(kw in stripped for kw in _fixed_titles) and len(stripped) < 60:
        return TemplateRole.PRESERVE

    # ---- DATA_SLOT 判断 ----
    # 纯占位符行：仅包含 XX 或下划线
    has_xx = bool(_XX_PLACEHOLDER_RE.search(stripped))
    # 去掉 XX 和下划线后剩余的纯文字
    cleaned = re.sub(r'X{2,}|_{2,}|[\s：:．.、\u3000]', '', stripped)
    if has_xx and len(cleaned) < 15:
        return TemplateRole.DATA_SLOT

    # 纯占位符/标签行（大片空白或下划线）
    blank_ratio = (stripped.count(' ') + stripped.count('\u3000') +
                   stripped.count('_') + stripped.count('\t'))
    if len(stripped) < 120 and blank_ratio > len(stripped) * 0.3:
        return TemplateRole.DATA_SLOT

    # ---- INSTRUCTION 判断 ----
    # 包含指导性短语且较短（指导说明通常不长）
    if len(stripped) < 200:
        # "请+动词" 组合（明确的指导结构）
        if re.search(r'请(?:简述|描述|列明|填写|说明|分析|阐述|注明|标注|勿)', stripped):
            return TemplateRole.INSTRUCTION
        # 独立的指导性短语（不容易误匹配的多字词）
        for phrase in _INSTRUCTION_PHRASES:
            if phrase in stripped:
                return TemplateRole.INSTRUCTION

    # ---- EXAMPLE 判断（宽松，宁可多标记也不要漏标记） ----
    # 包含模板样例关键词
    for kw in _TEMPLATE_SAMPLE_KEYWORDS:
        if kw in stripped:
            return TemplateRole.EXAMPLE

    # 包含 XX 占位符 + 叙述性文本（不管数量多少）
    if has_xx and len(stripped) > 20:
        return TemplateRole.EXAMPLE

    # 包含常见模板示例模式
    if re.search(r'XX万元|XX年|XX%|XX人|XX公司|XX银行', stripped):
        return TemplateRole.EXAMPLE

    # 含有范例特征的较长段落
    if len(stripped) > 60:
        has_example_markers = bool(re.search(
            r'[\u2026\u00b7]|\.{2,}|/{1}[\u4e00-\u9fff]|'
            r'\u5982[\uff1a:]|'
            r'\d{3,}[\u4e07\u5143\u540d\u4eba]',
            stripped))
        if has_example_markers:
            return TemplateRole.EXAMPLE

    # 兜底：长段落都当作 EXAMPLE（宁多勿漏）
    if len(stripped) > 60:
        return TemplateRole.EXAMPLE

    # 短且不含任何标记的段落 → PRESERVE
    return TemplateRole.PRESERVE


def extract_template_fingerprints(doc_path: str) -> dict[str, str]:
    """
    提取模板中所有 EXAMPLE 段落的文本指纹。

    遍历模板文档中的所有表格单元格段落，对标记为 EXAMPLE 的段落：
    去掉 XX 标记后作为"指纹"文本，用于后续相似度比对。

    Args:
        doc_path: 模板 .docx 文件路径

    Returns:
        dict[paragraph_location → cleaned_text]
        其中 paragraph_location 格式为 "t{table_idx}_r{row_idx}_c{cell_idx}_p{para_idx}"
    """
    from docx import Document as _Document

    doc = _Document(doc_path)
    fingerprints: dict[str, str] = {}

    for t_idx, table in enumerate(doc.tables):
        for r_idx, row in enumerate(table.rows):
            for c_idx, cell in enumerate(row.cells):
                paras = cell.paragraphs
                for p_idx, para in enumerate(paras):
                    text = (para.text or "").strip()
                    if not text or len(text) < 15:
                        continue

                    # 获取上下文
                    ctx_before = paras[p_idx - 1].text.strip() if p_idx > 0 else ""
                    ctx_after = paras[p_idx + 1].text.strip() if p_idx < len(paras) - 1 else ""

                    role = classify_paragraph_role(text, ctx_before, ctx_after)
                    if role == TemplateRole.EXAMPLE:
                        # 去掉 XX 标记，生成指纹
                        cleaned = re.sub(r'X{2,}', '', text)
                        cleaned = re.sub(r'_{2,}', '', cleaned)
                        cleaned = re.sub(r'\s+', '', cleaned)
                        if len(cleaned) >= 10:
                            loc = f"t{t_idx}_r{r_idx}_c{c_idx}_p{p_idx}"
                            fingerprints[loc] = cleaned

    return fingerprints


# ═══════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════

def classify_cell_paragraphs(cell) -> list[ParaInfo]:
    """对一个单元格中的所有直属段落进行分类"""
    results = []
    for i, para in enumerate(cell.paragraphs):
        text = para.text
        role, is_h, level = _classify_paragraph(text)
        instructions = _extract_instructions(text) if role == TemplateRole.SKELETON else []

        results.append(ParaInfo(
            para_idx=i,
            text=text,
            role=role,
            is_heading=is_h,
            heading_level=level,
            embedded_instructions=instructions,
        ))
    return results


def group_into_sections(paragraphs: list[ParaInfo]) -> list[SectionInfo]:
    """
    将分类后的段落按标题层级分组为章节。

    分割规则：遇到 level <= 3 的标题就开新节。
    level 4 (①/※) 不开新节，视为子项。
    """
    if not paragraphs:
        return []

    sections: list[SectionInfo] = []
    current: SectionInfo | None = None
    counter = 0

    for para in paragraphs:
        if para.is_heading and para.heading_level <= 3:
            counter += 1
            sid = f"sec_{counter:02d}"
            para.section_id = sid
            current = SectionInfo(
                section_id=sid,
                title=para.text.strip(),
                level=para.heading_level,
                paragraphs=[para],
            )
            sections.append(current)
        elif current is not None:
            para.section_id = current.section_id
            current.paragraphs.append(para)
        else:
            # 标题前的段落 → 前言节
            if not sections or sections[0].section_id != "sec_00":
                current = SectionInfo(
                    section_id="sec_00", title="（前言）", level=0
                )
                sections.insert(0, current)
            para.section_id = "sec_00"
            current.paragraphs.append(para)

    return sections


def decompose_template(doc) -> dict[str, Any]:
    """
    主入口：拆解整个模板文档。

    返回:
        {
            "body_sections": list[SectionInfo],  # R3 主体的章节列表
            "body_paragraphs": list[ParaInfo],    # R3 所有段落分类
            "header_paragraphs": list[ParaInfo],  # R1 头部段落分类
            "stats": {
                "total_paras": int,
                "skeleton_count": int,
                "content_count": int,
                "section_count": int,
            }
        }
    """
    main_table = doc.tables[0]

    # R3 = 主体
    body_cell = main_table.rows[3].cells[0]
    body_paras = classify_cell_paragraphs(body_cell)
    body_sections = group_into_sections(body_paras)

    # R1 = 头部（包含客户名称、授信方案等标签字段和复选框）
    header_paras = []
    if len(main_table.rows) > 1:
        header_cell = main_table.rows[1].cells[0]
        header_paras = classify_cell_paragraphs(header_cell)

    skel_count = sum(1 for p in body_paras if p.role == TemplateRole.SKELETON)
    cont_count = sum(1 for p in body_paras if p.role == TemplateRole.CONTENT)

    return {
        "body_sections": body_sections,
        "body_paragraphs": body_paras,
        "header_paragraphs": header_paras,
        "stats": {
            "total_paras": len(body_paras),
            "skeleton_count": skel_count,
            "content_count": cont_count,
            "section_count": len(body_sections),
        },
    }


# ═══════════════════════════════════════════
# 模板泄漏检测（通用性方法）
# ═══════════════════════════════════════════

def compute_similarity(text1: str, text2: str) -> float:
    """计算两段文本的相似度 (0~1)"""
    if not text1 or not text2:
        return 0.0
    # 去空白后比较，避免格式差异干扰
    a = re.sub(r'\s+', '', text1)
    b = re.sub(r'\s+', '', text2)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def detect_leakage(
    generated_paragraphs: dict[int, str],
    template_paragraphs: list[ParaInfo],
    threshold: float = 0.5,
) -> list[dict]:
    """
    检测生成内容是否泄漏了模板原文。

    Args:
        generated_paragraphs: {para_idx: generated_text}
        template_paragraphs: 模板原始段落分类列表
        threshold: 相似度阈值，超过则判定为泄漏

    Returns:
        [{para_idx, similarity, template_text, generated_text}, ...]
    """
    leaks = []
    tpl_map = {p.para_idx: p for p in template_paragraphs}

    for idx, gen_text in generated_paragraphs.items():
        tpl_para = tpl_map.get(idx)
        if not tpl_para:
            continue
        # 检查所有内容角色（CONTENT/EXAMPLE/INSTRUCTION）
        _content_roles = {TemplateRole.CONTENT, TemplateRole.EXAMPLE, TemplateRole.INSTRUCTION}
        if tpl_para.role not in _content_roles:
            continue

        tpl_text = tpl_para.text
        # 短文本不检测
        if len(re.sub(r'\s+', '', tpl_text)) < 20:
            continue
        if len(re.sub(r'\s+', '', gen_text)) < 20:
            continue

        sim = compute_similarity(gen_text, tpl_text)
        if sim > threshold:
            leaks.append({
                "para_idx": idx,
                "similarity": round(sim, 3),
                "template_snippet": tpl_text[:100],
                "generated_snippet": gen_text[:100],
            })

    return leaks


# ═══════════════════════════════════════════
# 章节→KB维度映射
# ═══════════════════════════════════════════

# 通过章节标题关键词推断需要的 KB 维度
_SECTION_DIMENSION_MAP = {
    # 关键词 → 维度列表
    "借款人简介": ["basic_info", "controller", "shareholders", "credit_history", "risk"],
    "借款人概况": ["basic_info", "business"],
    "面访": ["controller"],
    "走访": ["business"],
    "股权融资": ["financing", "shareholders"],
    "历史授信": ["credit_history"],
    "授后": ["credit_history"],
    "风险信号": ["risk", "credit_history"],
    "负面信息": ["risk"],
    "PD评级": ["credit_history", "risk"],
    "法定代表人": ["controller", "basic_info"],
    "实控人": ["controller"],
    "资产情况": ["assets"],
    "关联企业": ["affiliates"],
    "经营": ["business", "supply_chain", "orders"],
    "财务": ["basic_info", "financing"],
    "产品": ["business"],
    "上下游": ["supply_chain"],
    "订单": ["orders"],
    "融资": ["financing", "credit_history"],
    "对外担保": ["financing", "risk"],
    "征信": ["credit_history", "risk"],
    "科技": ["r_and_d", "patents"],
    "研发": ["r_and_d"],
    "专利": ["patents"],
    "综合效益": ["business", "customer_manager", "bank_flows"],
    "借款原因": ["financing", "business", "orders"],
    "还款": ["financing", "business"],
    "担保分析": ["assets", "financing", "controller"],
    "抵押": ["assets"],
    "保证": ["financing"],
    "授信申报结论": ["basic_info", "business", "financing", "risk",
                      "assets", "credit_history", "bank_flows"],
    "六要素": ["financing", "business", "bank_flows", "assets"],
}


def infer_section_dimensions(section: SectionInfo) -> list[str]:
    """根据章节标题和骨架内容推断需要的 KB 维度"""
    text = section.title + " " + " ".join(section.skeleton_lines)
    dims = set()

    for keyword, dim_list in _SECTION_DIMENSION_MAP.items():
        if keyword in text:
            dims.update(dim_list)

    # 兜底：至少给 basic_info
    if not dims:
        dims.add("basic_info")

    return sorted(dims)
