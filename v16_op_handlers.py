# -*- coding: utf-8 -*-
"""V16 Op Handlers — 按 (op, label) 路由的元素处理器.

路由表 OP_LABEL_HANDLERS 硬编码,每个 handler 签名:
    handler(elem: Element, cls: Classification, mats: Materials) -> GenResult

Step 2 范围:4 个确定性 handler(不触发 LLM):
  - keep_as_is                (PRESERVE/*)
  - kb_lookup_fill            (FILL/FILL)
  - clear_with_pending_marker (FILL/CLEAR)
  - checkbox_tick             (FILL/CHECKBOX,基础版)

Step 3 追加 multi_slot_decompose (FILL/SLOT)。
Step 4 追加 section_batch_rewrite (REWRITE/REWRITE)。
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from v16_generator import Classification, GenResult, Materials
    from v16_step1_extract import Element

# 运行期导入(避免循环)
from v16_generator import GenResult


# ────────────────────────────────────────────────────────────
# 字段标签 → KB facts key 映射
# 覆盖 material_kb._extract_basic_info / _controller_info 写入的主要 key
# ────────────────────────────────────────────────────────────

FIELD_TO_KB_KEY: dict[str, str] = {
    # 基础信息
    "客户名称": "company_name",
    "授信客户全称": "company_name",
    "客户全称": "company_name",
    "企业名称": "company_name",
    "企业全称": "company_name",
    "统一社会信用代码": "uscc",
    "成立时间": "establishment_date",
    "成立日期": "establishment_date",
    "注册资本": "registered_capital",
    "实收资本": "paid_in_capital",
    "上年度末社保人数": "social_insurance_count",
    "社保人数": "social_insurance_count",
    "员工人数": "employee_count",
    "法定代表人": "legal_representative",
    "法人代表": "legal_representative",
    # 实际控制人
    "实际控制人": "controller_name",
    "实控人": "controller_name",
    "持股比例": "controller_share_pct",
    "实控人持股": "controller_share_pct",
    "股权比例": "controller_share_pct",
    # 经营
    "所属行业": "industry",
    "主营业务": "business_description",
    "主营产品": "business_description",
    "经营地址": "operating_address",
    "注册地址": "registered_address",
    "经营地点": "operating_address",
    "坐落地点": "operating_address",
    # 财务划型
    "上年度资产总额": "total_assets_last_year",
    "上年度销售额": "revenue_last_year",
    "上年度末员工人数": "employee_count",
    "上年度末社保": "social_insurance_count",
    # P1 硬字段 — 来自 hard_fields.py 格式正则抽取
    "身份证号码": "controller_id",
    "身份证号": "controller_id",
    "身份证": "controller_id",
    "公民身份号码": "controller_id",
    "出生日期": "controller_birth",
    "出生年月": "controller_birth",
    "电话": "phone",
    "联系电话": "phone",
    "手机": "phone",
    "手机号": "phone",
    "手机号码": "phone",
    "邮编": "post_code",
    "邮政编码": "post_code",
    "银行账号": "bank_account",
    "基本账户": "bank_account",
    "结算账号": "bank_account",
    "账号": "bank_account",
    # 审计 / 租赁 / 住址
    "审计机构": "auditor",
    "会计师事务所": "auditor",
    "审计师": "auditor",
    "审计单位": "auditor",
    "场地面积": "lease_area",
    "租赁面积": "lease_area",
    "房屋面积": "lease_area",
    "经营场所": "lease_location",
    "租赁地点": "lease_location",
    "厂房地址": "lease_location",
    "住址": "controller_home_address",
    "户籍地址": "controller_home_address",
    "家庭住址": "controller_home_address",
}


def _parse_field_label(text: str) -> tuple[str, str] | None:
    """从 'XXX: YYY' 或 'XXX：YYY' 抽 (label, current_value)."""
    m = re.match(r"^\s*(.{2,30}?)\s*[:：]\s*(.*)$", text)
    if not m:
        return None
    label = m.group(1).strip()
    value = m.group(2).strip()
    return label, value


def _lookup_in_kb(label: str, facts: dict) -> str | None:
    """字段标签 → KB 值(未命中返回 None)."""
    key = FIELD_TO_KB_KEY.get(label)
    if not key:
        return None
    v = facts.get(key)
    if v is None:
        return None
    return str(v).strip() or None


# ────────────────────────────────────────────────────────────
# Handler 1: keep_as_is  (PRESERVE/*)
# ────────────────────────────────────────────────────────────

def keep_as_is(elem, cls, mats) -> "GenResult":
    # Step 5: body-gap 场景 — SCAFFOLD header 后无 body,追加补录提示
    gap = getattr(mats, "body_gaps", {}).get(elem.location) if mats else None
    if gap and cls.op == "PRESERVE" and cls.label == "SCAFFOLD":
        original = (elem.text or "").rstrip()
        annotated = f"{original} 【待根据客户材料补充】"
        return GenResult(
            location=elem.location,
            action="fill",
            new_text=annotated,
            pending_tag={
                "location": elem.location,
                "reason": gap.get("reason", "SCAFFOLD body 缺失"),
                "text": original[:80],
                "suggested_action": "客户经理补写该小节正文",
            },
            debug=f"keep_as_is: body-gap annotated ({gap.get('next_loc')})",
        )
    return GenResult(
        location=elem.location,
        action="keep",
        new_text=None,
        debug=f"{cls.op}/{cls.label} preserved",
    )


# ────────────────────────────────────────────────────────────
# Handler 2: kb_lookup_fill  (FILL/FILL)
#   - 识别 'XXX: YYY' 或裸字段
#   - 若 label 在 FIELD_TO_KB_KEY 且 KB 有值 → 重写为 "XXX: 新值"
#   - 若 label 未知或 KB 无值 → 清空值部分 + pending_tag
# ────────────────────────────────────────────────────────────

def kb_lookup_fill(elem, cls, mats) -> "GenResult":
    text = elem.text or ""
    parsed = _parse_field_label(text)
    facts = mats.facts

    if parsed is None:
        # 不是 'label:value' 形态,作为 raw FILL 处理(原文保留,标 pending)
        return GenResult(
            location=elem.location,
            action="keep",
            pending_tag={
                "location": elem.location,
                "reason": "FILL 目标无可识别字段标签",
                "text": text[:80],
                "suggested_action": "需客户经理补充",
            },
            debug="kb_lookup_fill: no field label pattern",
        )

    label, cur_value = parsed
    new_value = _lookup_in_kb(label, facts)

    if new_value:
        return GenResult(
            location=elem.location,
            action="fill",
            new_text=f"{label}：{new_value}",
            debug=f"kb_lookup_fill: {label} ← KB[{FIELD_TO_KB_KEY[label]}]",
        )

    # KB 无值 / 字段不在映射表 → 清空现值 + pending
    return GenResult(
        location=elem.location,
        action="fill",
        new_text=f"{label}：【未能自动填写】",
        pending_tag={
            "location": elem.location,
            "reason": f"字段「{label}」KB 未命中",
            "text": text[:80],
            "suggested_action": "请客户经理从客户材料补录",
        },
        debug=f"kb_lookup_fill: {label} miss",
    )


# ────────────────────────────────────────────────────────────
# Handler 3: clear_with_pending_marker  (FILL/CLEAR)
#   银行侧字段(申报单位/客户经理/PD评级/白名单类型/绿通标识等)
# ────────────────────────────────────────────────────────────

def clear_with_pending_marker(elem, cls, mats) -> "GenResult":
    text = elem.text or ""
    parsed = _parse_field_label(text)
    if parsed:
        label, _ = parsed
        new_text = f"{label}：【待客户经理填写】"
        reason = f"银行侧字段「{label}」需人工填"
    else:
        new_text = "【待客户经理填写】"
        reason = "银行侧字段需人工填"

    return GenResult(
        location=elem.location,
        action="fill",
        new_text=new_text,
        pending_tag={
            "location": elem.location,
            "reason": reason,
            "text": text[:80],
            "suggested_action": "客户经理填写(银行内部字段)",
        },
        debug="clear_with_pending_marker",
    )


# ────────────────────────────────────────────────────────────
# Handler 4: checkbox_tick  (FILL/CHECKBOX)
#   - 基础版:若能从 KB 判定勾选,直接勾;否则保留原状并 pending
#   - 复杂规则(科技企业类型/规模划型/客群等)延后到 dedicated checkbox kb
# ────────────────────────────────────────────────────────────

CHECKBOX_RULES: list[tuple[re.Pattern, Callable]] = []


def _register_checkbox_rule(pattern: str):
    """装饰器:注册 checkbox 匹配规则."""
    def deco(fn):
        CHECKBOX_RULES.append((re.compile(pattern), fn))
        return fn
    return deco


@_register_checkbox_rule(r"(新客户|存量客户)")
def _tick_customer_status(text: str, facts: dict) -> str | None:
    is_existing = facts.get("is_existing_customer")
    if is_existing is True:
        return _tick_option(text, "存量客户")
    if is_existing is False:
        return _tick_option(text, "新客户")
    return None


def _tick_option(text: str, keyword: str) -> str:
    """把 text 里 '□{keyword}' 换成 '☑{keyword}',其余 □ 保留未勾."""
    return re.sub(r"[□☐]\s*(?=" + re.escape(keyword) + ")", "☑", text, count=1)


def checkbox_tick(elem, cls, mats) -> "GenResult":
    text = elem.text or ""
    facts = mats.facts

    for pat, fn in CHECKBOX_RULES:
        if pat.search(text):
            new_text = fn(text, facts)
            if new_text and new_text != text:
                return GenResult(
                    location=elem.location,
                    action="fill",
                    new_text=new_text,
                    debug=f"checkbox_tick: matched {pat.pattern}",
                )

    # 无规则命中 → 保留原状 + pending
    return GenResult(
        location=elem.location,
        action="keep",
        pending_tag={
            "location": elem.location,
            "reason": "复选框需根据客户材料判定",
            "text": text[:80],
            "suggested_action": "客户经理按实际情况勾选",
        },
        debug="checkbox_tick: no rule matched, pending",
    )


# ────────────────────────────────────────────────────────────
# Handler 5: multi_slot_decompose  (FILL/SLOT)
#   - 识别空白占位(≥3 连续空格 / 全角空格)或 XXX 占位
#   - 对每个占位:左侧最近 delimiter 后的词 = label,右侧紧跟的单位为 unit
#   - KB 命中 → 填值;未命中 → 写【未能自动填写】+ pending
# ────────────────────────────────────────────────────────────

_PLACEHOLDER_RE = re.compile(r"([ \u3000]{3,}|[Xx]{2,})")
_UNIT_RE = re.compile(r"^(万元|亿元|%|人|家|户|年|月|平方米|㎡|元)")
_SEGMENT_DELIMS = "；、，。;,\n"


def _extract_sub_label(left_ctx: str) -> str:
    """抽占位符左侧最近的字段标签.

    规则:
    1. 先按"列表分隔符"(；、，。;,)切段,取最后一段
    2. 段内若有「：/:」:
         - 冒号后到占位符之间非空(有子标签)→ 取冒号后(形如 'main：sub<placeholder>')
         - 冒号后到占位符之间为空 → 取冒号前(形如 'field：<placeholder>')
    3. 段内无冒号 → 整段即 label
    """
    seg_start = -1
    for c in _SEGMENT_DELIMS:
        seg_start = max(seg_start, left_ctx.rfind(c))
    segment = left_ctx[seg_start + 1:] if seg_start >= 0 else left_ctx

    colon_pos = max(segment.rfind("："), segment.rfind(":"))
    if colon_pos >= 0:
        after_colon = segment[colon_pos + 1:].strip(" \u3000")
        if after_colon:
            return after_colon
        return segment[:colon_pos].strip(" \u3000")
    return segment.strip(" \u3000")


def multi_slot_decompose(elem, cls, mats) -> "GenResult":
    text = elem.text or ""
    facts = mats.facts

    matches = list(_PLACEHOLDER_RE.finditer(text))
    if not matches:
        return GenResult(
            location=elem.location,
            action="keep",
            pending_tag={
                "location": elem.location,
                "reason": "SLOT 元素未识别到占位符模式",
                "text": text[:80],
                "suggested_action": "需客户经理检视",
            },
            debug="multi_slot_decompose: no placeholder",
        )

    new_text = text
    offset = 0
    filled_count = 0
    miss_labels: list[str] = []

    for m in matches:
        start = m.start() + offset
        end = m.end() + offset

        left_ctx = new_text[:start]
        label = _extract_sub_label(left_ctx)

        right_ctx = new_text[end:]
        unit_m = _UNIT_RE.match(right_ctx)
        unit = unit_m.group(1) if unit_m else ""

        value = _lookup_in_kb(label, facts) if label else None

        if value:
            # 值已含该单位且文本后紧跟相同单位 → 去掉值尾部单位避免重复
            if unit and value.endswith(unit):
                replacement = value[:-len(unit)].rstrip() or value
            else:
                replacement = value
            new_text = new_text[:start] + replacement + new_text[end:]
            offset += len(replacement) - (end - start)
            filled_count += 1
        else:
            marker = "【未能自动填写】"
            new_text = new_text[:start] + marker + new_text[end:]
            offset += len(marker) - (end - start)
            miss_labels.append(label or "(未识别字段)")

    if filled_count == 0:
        return GenResult(
            location=elem.location,
            action="fill",
            new_text=new_text,
            pending_tag={
                "location": elem.location,
                "reason": f"SLOT 全部子槽 KB 未命中: {', '.join(miss_labels[:6])}",
                "text": text[:80],
                "suggested_action": "请客户经理补录各子字段",
            },
            debug=f"multi_slot_decompose: {len(matches)} slots all miss",
        )

    pending_tag = None
    if miss_labels:
        pending_tag = {
            "location": elem.location,
            "reason": f"SLOT 部分子槽未命中: {', '.join(miss_labels[:6])}",
            "text": text[:80],
            "suggested_action": f"请客户经理补录 {len(miss_labels)} 个子字段",
        }

    return GenResult(
        location=elem.location,
        action="fill",
        new_text=new_text,
        pending_tag=pending_tag,
        debug=f"multi_slot_decompose: {filled_count}/{len(matches)} filled",
    )


# ────────────────────────────────────────────────────────────
# Handler 6: section_batch_rewrite  (REWRITE/REWRITE)
#   - 把同一 section 的 REWRITE element 合批送 LLM
#   - 单阶段 evidence-grounded prompt:系统提示强约束证据优先
#   - 证据不足的段落,要求 LLM 输出 "【未能自动填写:字段名】"
# ────────────────────────────────────────────────────────────

_REWRITE_SYSTEM_PROMPT = """你是信贷报告专业写作助手,为银行审贷员重写报告段落。

核心约束:
1. 【证据优先】每个数字/结论都要来自客户材料,禁止凭空编造或估算
2. 【无证据标注】材料无法支撑的段落,输出 "【未能自动填写:该段所需字段】"
3. 【粒度守恒】新段落长度量级应与原段落相当,不要过度扩写/压缩
4. 【口吻中立】使用第三人称正式书面语,不要评价、煽情、推销
5. 【数字原样】数字引用材料原文表述,不要改写小数位数、不要换算货币单位
6. 【禁止泄漏】不要输出 "证据清单" "审核意见" "✓" "✗" 等 prompt 术语
7. 【模板示例识别】"需要重写的段落"显示的是银行模板的示例/占位文本,仅用于
   理解字段结构(要写什么类型信息、包含哪些要素),禁止套用其中的具体数值、
   公司名、行业、地名、人名、日期等实质内容。示例中的"XX/XXX"、"张XX"、
   "2010年5月"、"芯片设计"等都是模板虚构,不代表客户实际情况。
8. 【事实强制引用】如果【企业事实】中列出了 company_name / uscc / controller_id /
   phone / post_code / bank_account / registered_capital / legal_representative /
   industry / business_description / operating_address 等字段,且正在写的段落
   需要这些信息,必须原样引用事实值,不得改写或省略。
9. 【履历严禁虚构】涉及法定代表人/实际控制人/实控人的简介段,如需写"行业工作经历
   /从业经历/教育背景/学校/专业/职务/任职年份/曾任职公司"等,每一条必须能在
   【客户材料】原文中找到对应文字。材料未提供教育/工作经历的,该子项直接写
   "【未能自动填写:教育背景(材料未记载)】""【未能自动填写:行业工作经历(材料
   未记载)】",严禁根据常识/行业推测/训练语料编造任何公司名、学校名、年份区间、
   职务头衔。
10. 【关联企业严禁虚构】涉及关联方/关联企业/集团的段落,企业名、持股比例、
    经营业务必须逐字来自【客户材料】;材料未明确的,写"【未能自动填写:关联企业
    详情(材料未记载)】",严禁编造关联企业名称或经营内容。"""


def _build_material_summary_for_rewrite(mats, max_chars: int = 6000) -> str:
    """给 REWRITE 用的材料摘要块 — facts + 原文片段."""
    parts: list[str] = []
    facts = mats.facts
    if facts:
        parts.append("【企业事实(来自 KB 解析)】")
        for k, v in sorted(facts.items()):
            s = str(v).strip() if v is not None else ""
            if s and len(s) < 300:
                parts.append(f"  - {k}: {s}")

    raw = mats.kb.get("raw_statements", []) if mats.kb else []
    if raw:
        parts.append("")
        parts.append("【材料原文片段】")
        budget = max_chars - sum(len(p) for p in parts)
        for stmt in raw:
            if budget <= 200:
                break
            t = str(stmt).strip()
            if len(t) < 20:
                continue
            chunk = t[:600]
            parts.append(chunk)
            budget -= len(chunk)
    text = "\n".join(parts)
    return text[:max_chars]


def section_batch_rewrite(
    section_elems,
    section_heading: list,
    mats,
) -> dict:
    """同一 section 的 REWRITE elements 合批调用 LLM.

    返回: {location: GenResult}
    异常时对所有 element 产出 pending(不抛错,不阻断 pipeline)。
    """
    if not section_elems:
        return {}

    heading_path = " > ".join(section_heading) if section_heading else "(根节)"
    section_title = section_heading[-1] if section_heading else "(未命名)"

    _RISK_MARKERS = (
        "法定代表人", "实际控制人", "实控人", "行业工作经历", "从业经历",
        "教育背景", "任职情况", "关联企业", "关联方",
    )
    elem_lines = []
    for e in section_elems:
        t = (e.text or "").replace("\n", " ")
        tags = []
        low = t[:200]
        if any(kw in low for kw in _RISK_MARKERS):
            tags.append("【高风险段·禁止虚构履历/关联方】")
        prefix = f'[{e.location}] ' + "".join(tags)
        elem_lines.append(prefix + t[:400])
    elem_block = "\n".join(elem_lines)

    material_block = _build_material_summary_for_rewrite(mats, max_chars=6000)

    schema_hint = (
        '输出严格 JSON 对象,key = 段落 location 字符串,value = 重写后的段落正文。\n'
        '示例: {"P26": "新正文...", "P43": "新正文..."}\n'
        '务必只返回 JSON,不要 markdown 围栏,不要任何说明文字。\n'
        f'必须包含全部 {len(section_elems)} 个 location 作为 key。'
    )

    user_content = (
        f"【所在章节】\n{heading_path}\n\n"
        f"【模板示例段落】(共 {len(section_elems)} 条,下列文本是银行模板的占位/示例,\n"
        f"仅用于理解字段结构和写作要点,禁止直接引用其中的公司名/行业/数字/日期等内容)\n"
        f"{elem_block}\n\n"
        f"【客户材料】(这里的企业事实和材料原文是唯一可引用的内容源)\n{material_block}\n\n"
        "请根据【客户材料】为每个 location 重写正文:\n"
        "- 参考【模板示例段落】理解每条要写什么字段,但内容全部来自【客户材料】\n"
        "- 【企业事实】中已明确的值必须原样嵌入相关段落\n"
        '- 若【客户材料】无法支撑该段所需信息,输出 "【未能自动填写:<缺失字段>】"\n'
        "- 输出 JSON 映射 {location: 新正文}"
    )

    try:
        from llm import LLMClient
        from config import GENERATOR_PROVIDER
        provider = GENERATOR_PROVIDER if GENERATOR_PROVIDER else "deepseek"
    except Exception:
        provider = "deepseek"
        from llm import LLMClient  # noqa

    out: dict = {}
    try:
        client = LLMClient(provider=provider)
        result = client.chat_json(
            _REWRITE_SYSTEM_PROMPT,
            user_content,
            schema_hint=schema_hint,
            temperature=0.2,
        )
    except Exception as exc:
        for e in section_elems:
            out[e.location] = GenResult(
                location=e.location,
                action="keep",
                pending_tag={
                    "location": e.location,
                    "reason": f"LLM 重写失败: {type(exc).__name__}",
                    "text": (e.text or "")[:80],
                    "suggested_action": "人工撰写或重试",
                },
                debug=f"section_batch_rewrite: llm error {exc}",
            )
        return out

    if not isinstance(result, dict):
        for e in section_elems:
            out[e.location] = GenResult(
                location=e.location,
                action="keep",
                pending_tag={
                    "location": e.location,
                    "reason": "LLM 返回非 JSON 对象",
                    "text": (e.text or "")[:80],
                    "suggested_action": "人工撰写",
                },
                debug="section_batch_rewrite: result not dict",
            )
        return out

    # 全材料文本串用于 proper-noun 归位校验(履历段/关联方段 幻觉拦截)
    all_material_text = ""
    if mats and getattr(mats, "file_contents", None):
        all_material_text = " ".join(mats.file_contents.values())

    for e in section_elems:
        new_text = result.get(e.location)
        if isinstance(new_text, str) and new_text.strip():
            new_text = new_text.strip()
            pending = None
            elem_text_head = (e.text or "")[:200]
            is_risk = any(kw in elem_text_head for kw in _RISK_MARKERS)
            # 履历/关联方段的 proper-noun 归位:
            # 校验文本中出现的 大学/学院/科技有限公司/网络有限公司/股份有限公司 等
            # 专有名词是否能在 材料原文 中找到,找不到即判定幻觉,整段退回 pending。
            if is_risk and all_material_text:
                _SUFFIXES = ("大学", "学院", "科技有限公司", "网络有限公司", "股份有限公司", "有限公司", "集团")
                pat = re.compile(
                    r"[\u4e00-\u9fffA-Za-z0-9]{2,12}"
                    r"(?:大学|学院|科技有限公司|网络有限公司|股份有限公司|有限公司|集团)"
                )
                nouns = pat.findall(new_text)
                # 贪婪匹配易把普通动宾短语连到"大学/学院"后缀上造成假阳性
                # (例: "租赁地址为福州大学" 被整体视为专名)
                # 对每个 match, 尝试 3~12 字的"后缀切片"是否命中材料; 任一命中即视为已支撑。
                def _supported(noun: str) -> bool:
                    # 去掉前缀虚词后再判: 保留末尾带后缀的专名实体
                    for suf in _SUFFIXES:
                        if noun.endswith(suf):
                            core_len = len(noun)
                            # 从最长到最短的"后缀切片"滑窗 — 只要有一段出现在原文,就算未虚构
                            for cut in range(0, core_len - len(suf)):
                                cand = noun[cut:]
                                if len(cand) >= 4 and cand in all_material_text:
                                    return True
                            # 后缀本身在原文独立出现且专名后缀的最短 "2字+后缀" 也找不到 → 判虚构
                            return False
                    return True
                fabricated = sorted({n for n in nouns if not _supported(n)})
                if fabricated:
                    preview = "、".join(fabricated[:3])
                    new_text = (
                        f"【未能自动填写:本段涉及履历/关联方,材料未记载模型引用的主体 "
                        f"({preview}),已拦截虚构内容,待客户经理补充原始信息】"
                    )
                    pending = {
                        "location": e.location,
                        "reason": f"履历/关联方幻觉拦截: {preview}",
                        "text": elem_text_head[:80],
                        "suggested_action": "客户经理补充履历/关联方原始文字后重写",
                    }
            if pending is None and "【未能自动填写" in new_text:
                pending = {
                    "location": e.location,
                    "reason": "LLM 判定材料证据不足",
                    "text": elem_text_head[:80],
                    "suggested_action": "客户经理补充材料后重写",
                }
            out[e.location] = GenResult(
                location=e.location,
                action="fill",
                new_text=new_text,
                pending_tag=pending,
                debug=f"section_batch_rewrite: section={section_title[:20]}",
            )
        else:
            out[e.location] = GenResult(
                location=e.location,
                action="keep",
                pending_tag={
                    "location": e.location,
                    "reason": "LLM 未覆盖该 location",
                    "text": (e.text or "")[:80],
                    "suggested_action": "人工撰写",
                },
                debug="section_batch_rewrite: missing in response",
            )
    return out


# ────────────────────────────────────────────────────────────
# 路由表(唯一真源)
# (op, label) → handler
# Step 2 先覆盖确定性路径;REWRITE 和 SLOT 用 _not_impl 占位
# ────────────────────────────────────────────────────────────

def _not_impl(elem, cls, mats) -> "GenResult":
    return GenResult(
        location=elem.location,
        action="keep",
        debug=f"[not-impl] {cls.op}/{cls.label}",
    )


OP_LABEL_HANDLERS: dict[tuple[str, str], Callable] = {
    # PRESERVE
    ("PRESERVE", "SCAFFOLD"): keep_as_is,
    ("PRESERVE", "PRESERVE"): keep_as_is,
    # FILL
    ("FILL", "FILL"): kb_lookup_fill,
    ("FILL", "CLEAR"): clear_with_pending_marker,
    ("FILL", "CHECKBOX"): checkbox_tick,
    ("FILL", "SLOT"): multi_slot_decompose,
    # REWRITE
    ("REWRITE", "REWRITE"): _not_impl,  # Step 4
}


def dispatch(elem, cls, mats) -> "GenResult":
    """按 (op, label) 找 handler 执行;未注册组合返回 keep + debug."""
    key = (cls.op, cls.label)
    handler = OP_LABEL_HANDLERS.get(key)
    if handler is None:
        return GenResult(
            location=elem.location,
            action="keep",
            debug=f"[no-handler] {cls.op}/{cls.label}",
        )
    return handler(elem, cls, mats)
