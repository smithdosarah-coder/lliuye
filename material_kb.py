# -*- coding: utf-8 -*-
"""material_kb.py

Build a structured, multi-dimensional knowledge base (KB) from ALL uploaded
materials — not just one file.

Design goals:
- Scan ALL files (not just one "授信补充" doc) to maximise coverage.
- Deterministic regex/table parsing where possible, to reduce hallucination.
- Keep provenance: every fact records its source file.
- Structured output: facts are organised into semantic dimensions so
  downstream consumers can retrieve exactly what they need.

Dimensions:
  basic_info      — 企业名称/成立时间/注册资本/实收资本/社保人数/法人/行业
  shareholders    — 股东名称/持股比例/出资额/出资形式
  controller      — 实控人/配偶 姓名/身份证/简历
  business        — 主营业务描述/收入结构/核心竞争力/经营账期
  upstream_top5   — 前五大供应商
  downstream_top5 — 前五大客户
  affiliates      — 关联企业
  financing       — 融资机构/品种/额度/余额/起止日/担保
  credit_history  — 历史授信合作/上期方案/贷款提用/贷后要求
  risk_info       — 预警信号/诉讼/征信/ESG/反洗钱
  r_and_d         — 研发费用/专利
  orders          — 在手订单汇总
  bank_flows      — 银行流水汇总
  tax_data        — 纳税申报表对比
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _split_lines(text: str) -> list[str]:
    if not text:
        return []
    return [ln.strip() for ln in re.split(r"[\r\n]+", text) if ln and ln.strip()]


def _extract_block(lines: list[str], start_pat: str, end_pat: str | None = None) -> str:
    start_re = re.compile(start_pat)
    end_re = re.compile(end_pat) if end_pat else None
    start_i = None
    for i, ln in enumerate(lines):
        if start_re.search(ln):
            start_i = i + 1
            break
    if start_i is None:
        return ""
    out: list[str] = []
    for j in range(start_i, len(lines)):
        ln = lines[j]
        if end_re and end_re.search(ln):
            break
        out.append(ln)
    return "\n".join(out).strip()


def _parse_docx_export_tables(lines: list[str]) -> dict[str, list[list[str]]]:
    """Parse tables exported by tools._read_single_file for docx.

    The exporter emits:
      [表格N]
      col1\\tcol2\\t...
      ...

    Returns: {"表格1": [[...], ...], ...}
    """
    tables: dict[str, list[list[str]]] = {}
    current: list[list[str]] | None = None
    current_name: str | None = None
    for ln in lines:
        m = re.match(r"^\[表格(\d+)\]$", ln)
        if m:
            current_name = f"表格{m.group(1)}"
            current = []
            tables[current_name] = current
            continue
        if current is None:
            continue
        row = [c.strip() for c in ln.split("\t")]
        if any(c for c in row):
            current.append(row)
    return tables


# ---------------------------------------------------------------------------
# Semantic table identification (replaces hard-coded table numbers)
# ---------------------------------------------------------------------------

def _norm_header(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip())


def _header_contains(header_text: str, keywords: list[str]) -> bool:
    h = _norm_header(header_text)
    return any(_norm_header(kw) in h for kw in keywords)


def _identify_table_type(header_row: list[str]) -> str | None:
    """Identify a table's semantic type from its header row."""
    ht = " ".join(header_row)

    # Shareholder table: has 股东/出资 columns
    if _header_contains(ht, ["股东名称", "认缴出资", "出资比例"]):
        return "shareholders"

    # Upstream supplier table
    if _header_contains(ht, ["上游供应商", "供应商"]) and _header_contains(ht, ["采购"]):
        return "upstream"

    # Downstream customer table
    if _header_contains(ht, ["下游销售客户", "销售客户", "客户"]) and _header_contains(ht, ["销售"]):
        return "downstream"

    # Financing table
    if _header_contains(ht, ["融资机构"]) and _header_contains(ht, ["敞口", "额度", "担保"]):
        return "financing"

    # Affiliates table
    if _header_contains(ht, ["关联", "企业名称"]) and _header_contains(ht, ["成立时间", "股权结构", "净利润"]):
        return "affiliates"

    # R&D table
    if _header_contains(ht, ["研发费用"]) and _header_contains(ht, ["年份"]):
        return "r_and_d"

    # Bank flow table
    if _header_contains(ht, ["开户行"]) and _header_contains(ht, ["流入量", "流入"]):
        return "bank_flows"

    # Orders / contracts table
    if _header_contains(ht, ["合同"]) and _header_contains(ht, ["金额", "签署", "回款"]):
        return "orders"

    # Tax comparison table
    if _header_contains(ht, ["纳税", "财报"]) and _header_contains(ht, ["收入", "占比"]):
        return "tax_data"

    # Receivables detail table
    if _header_contains(ht, ["应收账款"]) and _header_contains(ht, ["金额"]):
        return "receivables_top5"

    # Other receivables detail table
    if _header_contains(ht, ["其他应收款"]) and _header_contains(ht, ["金额", "性质"]):
        return "other_receivables_top5"

    # Payables detail table
    if _header_contains(ht, ["应付账款"]) and _header_contains(ht, ["金额"]):
        return "payables_top5"

    # Asset table (实控人/企业资产)
    if _header_contains(ht, ["资产名称"]) and _header_contains(ht, ["所有权人", "权属"]):
        return "assets"

    # Patent table
    if _header_contains(ht, ["专利名称"]) and _header_contains(ht, ["证号"]):
        return "patents"

    return None


def _table_to_dicts(table_data: list[list[str]]) -> list[dict[str, str]]:
    """Convert header+rows to list of dicts."""
    if len(table_data) < 2:
        return []
    hdr = table_data[0]
    rows = []
    for r in table_data[1:]:
        if not any(c.strip() for c in r):
            continue
        item = {}
        for i, col in enumerate(hdr):
            if i < len(r) and col.strip():
                item[col.strip()] = r[i].strip()
        if item:
            rows.append(item)
    return rows


# ---------------------------------------------------------------------------
# Regex extractors (work across ALL files)
# ---------------------------------------------------------------------------

def _extract_basic_info(all_text: str, facts: dict):
    """Extract enterprise basic registration info via regex from all materials."""

    # Company name
    for pat in [
        r"(?:企业名称|公司名称|借款人|申请人|客户名称)[：:]\s*([\u4e00-\u9fff\w（）()]+(?:有限公司|股份有限公司))",
        r"([\u4e00-\u9fff]{2,}(?:有限公司|股份有限公司))",
    ]:
        m = re.search(pat, all_text)
        if m and len(m.group(1)) >= 6:
            facts.setdefault("company_name", m.group(1).strip())
            break

    # Establishment date
    for pat in [
        r"(?:成立于|注册日期|成立时间|成立日期)[：:]*\s*(\d{4}年\d{1,2}月(?:\d{1,2}日)?)",
        r"(?:成立于|注册日期)[：:]*\s*(\d{4}-\d{1,2}(?:-\d{1,2})?)",
    ]:
        m = re.search(pat, all_text)
        if m:
            facts["establishment_date"] = m.group(1).strip()
            break

    # Registered capital — handle OCR errors (方→万) and Chinese numerals
    for pat in [
        r"注册资本[：:]\s*([\d,.]+)\s*[万方]",   # "方" is common OCR error for "万"
        r"注册资本金[：:]\s*([\d,.]+)\s*[万方]",
    ]:
        m = re.search(pat, all_text)
        if m:
            facts["registered_capital"] = m.group(1).replace(",", "") + "万元"
            break

    # Paid-in capital — also check financial statement format ("实收资本（或股本）")
    for pat in [
        r"实收资本[：:]\s*([\d,.]+)\s*[万方]",
        r"实缴资本[：:]\s*([\d,.]+)\s*[万方]",
    ]:
        m = re.search(pat, all_text)
        if m:
            facts["paid_in_capital"] = m.group(1).replace(",", "") + "万元"
            break
    if "paid_in_capital" not in facts:
        # Financial statement xlsx format: "实收资本（或股本）  <row>  <number>"
        m = re.search(r"实收资本[（(]或股本[）)]\s+\d+\s+([\d,.]+)", all_text)
        if m:
            raw = float(m.group(1).replace(",", ""))
            if raw >= 10000:
                facts["paid_in_capital"] = f"{raw / 10000:.0f}万元"
            else:
                facts["paid_in_capital"] = f"{raw:.0f}元"

    # Social insurance count
    for pat in [
        r"(?:社保人数|参保人数|上年度末员工人数|社保缴纳人数)[：:]*\s*(\d+)\s*人",
        r"(\d+)\s*(?:人|名)\s*员工.*社保",
        r"社保.*?(\d+)\s*人",
    ]:
        m = re.search(pat, all_text)
        if m:
            facts["social_insurance_count"] = m.group(1).strip()
            break

    # Employee count (may differ from social insurance)
    for pat in [
        r"(?:员工人数|职工人数|在职人数)[：:]*\s*(\d+)\s*人",
        r"现有\s*(\d+)\s*(?:多)?名员工",
    ]:
        m = re.search(pat, all_text)
        if m:
            facts.setdefault("employee_count", m.group(1).strip())
            break

    # Legal representative
    _TITLE_BLACKLIST = {'主管会计', '总经理', '董事长', '经理', '会计', '出纳',
                        '财务', '审计', '监事', '秘书', '主任', '副总'}
    for pat in [
        r"法定代表人[：:\s]\s*([\u4e00-\u9fff]{2,4})",
        r"法人代表[：:\s]\s*([\u4e00-\u9fff]{2,4})",
    ]:
        for m in re.finditer(pat, all_text):
            candidate = m.group(1).strip()
            if candidate not in _TITLE_BLACKLIST:
                facts["legal_representative"] = candidate
                break
        if "legal_representative" in facts:
            break

    # Industry
    for pat in [
        r"国标行业[^：:]*[：:]\s*(.+?)(?:\n|$)",
        r"所属行业[：:]\s*(.+?)(?:\n|$)",
    ]:
        m = re.search(pat, all_text)
        if m:
            facts["industry"] = _clean_ws(m.group(1))[:120]
            break

    # Operating address
    for pat in [
        r"(?:经营地址|注册地址|办公地址|坐落地点)[^：:]*[：:]\s*(.+?)(?:[。，\n]|$)",
    ]:
        m = re.search(pat, all_text)
        if m and len(m.group(1).strip()) > 5:
            facts["operating_address"] = _clean_ws(m.group(1))[:150]
            break


def _extract_controller_info(all_text: str, facts: dict):
    """Extract controller / legal representative detailed info."""

    # Controller name
    for pat in [
        r"实际控制人[：:]\s*([\u4e00-\u9fff]{2,4})",
        r"实控人[：:]*\s*([\u4e00-\u9fff]{2,4})",
    ]:
        m = re.search(pat, all_text)
        if m:
            facts["controller_name"] = m.group(1).strip()
            break

    # Controller ID
    m = re.search(r"(?:实控人|实际控制人|法定代表人).*?(?:身份证号码?|身份证)[：:]\s*(\d{17}[\dXx])", all_text)
    if m:
        facts["controller_id"] = m.group(1).strip()

    # Controller shareholding ratio
    m = re.search(r"(?:实控人|实际控制人).*?(?:持股比例|合计持股)[：:]*\s*([\d.]+)\s*%", all_text)
    if m:
        facts["controller_share_pct"] = m.group(1).strip() + "%"

    # Spouse
    for pat in [
        r"(?:其)?配偶[为是：:]*\s*([\u4e00-\u9fff]{2,4})",
    ]:
        m = re.search(pat, all_text)
        if m:
            facts["spouse_name"] = m.group(1).strip()
            break

    m = re.search(r"配偶.*?(?:身份证号码?|身份证)[：:]\s*(\d{17}[\dXx])", all_text)
    if m:
        facts["spouse_id"] = m.group(1).strip()

    # Controller resume block (longer text)
    ctrl_block = _extract_block(
        _split_lines(all_text),
        r"(?:实际控制人|实控人).*(?:个人简介|简历|经历)[：:]",
        r"(?:^配偶|^（[三四五]）|^\d+\.\s*实控人)"
    )
    if ctrl_block:
        facts["controller_resume"] = ctrl_block[:500]


def _extract_credit_history(all_text: str, facts: dict):
    """Extract credit/authorisation history info."""

    # Historical cooperation with our bank
    for pat in [
        r"(?:与我行|我行与借款人|历史授信合作)[^。]*。",
        r"(?:历史授信合作|授信合作关系)[^。]*[。]",
    ]:
        m = re.search(pat, all_text)
        if m:
            facts["credit_cooperation_history"] = _clean_ws(m.group(0))[:300]
            break

    # Previous credit approval date
    m = re.search(r"(?:原有额度批复日期|上期批复日期|上一期授信)[：:]*\s*(\d{4}年\d{1,2}月\d{1,2}日)", all_text)
    if m:
        facts["prev_approval_date"] = m.group(1).strip()
        facts["is_existing_customer"] = True

    # Check existing customer signal
    if not facts.get("is_existing_customer"):
        if re.search(r"(?:存量客户|续授信|续贷|再融资|原有额度|上一期授信|授信补充)", all_text):
            facts["is_existing_customer"] = True
        elif re.search(r"新客户", all_text) and not re.search(r"存量客户", all_text):
            facts["is_existing_customer"] = False

    # Previous credit amount
    m = re.search(r"上一期授信敞口[^：:]*[：:]*\s*([\d,.]+)\s*万", all_text)
    if m:
        facts["prev_credit_exposure"] = m.group(1).replace(",", "") + "万元"

    # Previous guarantee method
    m = re.search(r"上一期授信担保方式[^：:]*[：:]*\s*(.+?)(?:[；\n]|$)", all_text)
    if m:
        facts["prev_guarantee_method"] = _clean_ws(m.group(1))[:80]

    # Previous PD rating
    m = re.search(r"上一期授信评级[^：:]*[：:]*\s*(\d+)\s*级", all_text)
    if m:
        facts["prev_pd_rating"] = m.group(1) + "级"

    # Loan drawdown info
    loan_block = _extract_block(
        _split_lines(all_text),
        r"贷款提用情况",
        r"(?:上一期授信条件|授信及风险信号)"
    )
    if loan_block:
        facts["loan_drawdown_info"] = loan_block[:500]


def _extract_risk_info(all_text: str, facts: dict):
    """Extract risk signals, litigation, ESG, AML info."""

    # Risk signal block
    risk_block = _extract_block(
        _split_lines(all_text),
        r"授信及风险信号提示",
        r"(?:其他负面信息|^（[二三]）|^\d+\.(?:其他|PD评级))"
    )
    if risk_block:
        facts["risk_signals"] = risk_block[:800]

    # Negative info block
    neg_block = _extract_block(
        _split_lines(all_text),
        r"其他负面信息",
        r"(?:^（[二三]）|^PD评级|^\d+\.)"
    )
    if neg_block:
        facts["negative_info"] = neg_block[:500]

    # ESG
    m = re.search(r"ESG[^：:]*[：:]*\s*[□☐☑■]?\s*([ABC])", all_text)
    if m:
        facts["esg_rating"] = m.group(1)

    # AML
    m = re.search(r"反洗钱风险等级[^：:]*[：:]*\s*[□☐☑■]?\s*(低|一般|较高|高)", all_text)
    if m:
        facts["aml_risk_level"] = m.group(1)


def _extract_order_info(all_text: str, facts: dict):
    """Extract in-hand orders summary."""
    for pat in [
        r"在手(?:项目)?订单.*?(\d+)\s*笔.*?合同总金额\s*([\d,.]+)\s*万.*?未回款.*?([\d,.]+)\s*万",
        r"在手订单.*?(\d+)\s*笔.*?总金额\s*([\d,.]+)\s*万",
    ]:
        m = re.search(pat, all_text)
        if m:
            facts["orders_count"] = m.group(1)
            facts["orders_total_amount"] = m.group(2).replace(",", "") + "万元"
            if m.lastindex >= 3:
                facts["orders_uncollected"] = m.group(3).replace(",", "") + "万元"
            break


def _extract_credit_application(all_text: str, facts: dict):
    """Extract credit application details (申报额度/品种/期限/担保)."""

    # 申报额度
    m = re.search(r"申报额度[^：:]*[：:]*\s*([\d,.]+)\s*万", all_text)
    if m:
        facts["applied_credit_amount"] = m.group(1).replace(",", "") + "万元"

    # 申报敞口
    m = re.search(r"(?:申报敞口|敞口)[^：:]*[：:]*\s*([\d,.]+)\s*万", all_text)
    if m:
        facts["applied_exposure"] = m.group(1).replace(",", "") + "万元"

    # 业务品种
    m = re.search(r"业务品种[：:]\s*(.+?)(?:[；;。\n]|$)", all_text)
    if m:
        facts["business_product"] = _clean_ws(m.group(1))[:80]

    # 业务期限
    m = re.search(r"业务期限[：:]\s*(.+?)(?:[；;。\n]|$)", all_text)
    if m:
        facts["business_term"] = _clean_ws(m.group(1))[:40]

    # 授信期限
    m = re.search(r"授信期限[：:]\s*(.+?)(?:[；;。\n]|$)", all_text)
    if m:
        facts["credit_term"] = _clean_ws(m.group(1))[:40]

    # 担保方式
    m = re.search(r"(?:^|[；;])担保方式[：:]\s*(.+?)(?:[；;。\n]|$)", all_text)
    if m:
        facts["guarantee_method"] = _clean_ws(m.group(1))[:80]

    # PD评级
    m = re.search(r"PD评级[^：:]*[：:]*\s*(\d+)\s*级", all_text)
    if m:
        facts["pd_rating"] = m.group(1) + "级"

    # 申报单位
    m = re.search(r"申报单位[：:]\s*([\u4e00-\u9fff\w]+?)(?:\s|$)", all_text)
    if m:
        facts["reporting_unit"] = m.group(1).strip()

    # 绿通标识
    m = re.search(r"绿通标识[：:]\s*(.+?)(?:\s{2,}|\n|$)", all_text)
    if m and m.group(1).strip():
        facts["green_channel"] = _clean_ws(m.group(1))[:30]

    # Credit change direction (增/减/维持)
    if re.search(r"☑\s*减少", all_text):
        facts["credit_change_direction"] = "decrease"
    elif re.search(r"☑\s*增加", all_text):
        facts["credit_change_direction"] = "increase"
    elif re.search(r"☑\s*维持", all_text):
        facts["credit_change_direction"] = "maintain"

    # Guarantee changed (担保方式变更)
    prev_guarantee = facts.get("prev_guarantee_method", "")
    curr_guarantee = facts.get("guarantee_method", "")
    if prev_guarantee and curr_guarantee and prev_guarantee != curr_guarantee:
        facts["guarantee_changed"] = True


def _extract_tech_info(all_text: str, facts: dict):
    """Extract technology enterprise info (科技型企业类型/评分)."""

    # Tech enterprise types — scan for checked items
    tech_types = []
    for ttype in ["科技型中小企业", "高新技术企业", "创新型中小企业",
                   "专精特新", "小巨人", "制造业单项冠军", "国家技术创新示范企业"]:
        if re.search(r"[☑■√✓]\s*" + re.escape(ttype), all_text):
            tech_types.append(ttype)
    # Also check from supplementary materials (e.g., 高新技术企业认定公告)
    if not tech_types:
        if re.search(r"高新技术企业(?:认定|证书|公告)", all_text):
            tech_types.append("高新技术企业")
        if re.search(r"专精特新.*(?:认定|证书|公告)", all_text):
            tech_types.append("专精特新")
        if re.search(r"科技型中小企业.*(?:认定|入库)", all_text):
            tech_types.append("科技型中小企业")

    if tech_types:
        facts["tech_enterprise_types"] = "、".join(tech_types)

    # Tech score
    m = re.search(r"科技型企业评分[：:]*\s*(\d+)\s*分", all_text)
    if m:
        facts["tech_score"] = m.group(1) + "分"

    # Enterprise scale classification
    m = re.search(r"规模划型[^：:]*[：:]*\s*[□☐☑■]?\s*(微型|小型|中型)", all_text)
    if m:
        facts["enterprise_scale"] = m.group(1)
    else:
        if re.search(r"☑\s*小型", all_text):
            facts["enterprise_scale"] = "小型"
        elif re.search(r"☑\s*微型", all_text):
            facts["enterprise_scale"] = "微型"
        elif re.search(r"☑\s*中型", all_text):
            facts["enterprise_scale"] = "中型"

    # Customer group
    if re.search(r"☑\s*支持类", all_text):
        facts["customer_group"] = "支持类"
    elif re.search(r"☑\s*审慎类", all_text):
        facts["customer_group"] = "审慎类"

    # Equity change
    m = re.search(r"(?:股权变动|股权变更).*?[：:]\s*(.+?)(?:\n|$)", all_text)
    if m:
        val = _clean_ws(m.group(1))[:100]
        if val:
            facts["equity_change"] = val

    # R&D personnel stock incentive
    if re.search(r"[☑■√✓]\s*是.*股权激励", all_text) or re.search(r"股权激励.*[☑■√✓]\s*是", all_text):
        facts["stock_incentive"] = "是"
    elif re.search(r"[☑■√✓]\s*否.*股权激励", all_text) or re.search(r"股权激励.*[☑■√✓]\s*否", all_text):
        facts["stock_incentive"] = "否"


def _extract_comprehensive_benefit(all_text: str, facts: dict):
    """Extract comprehensive benefit info (综合效益)."""
    # 日均存款
    m = re.search(r"日均存款\s*([\d,.]+)\s*万", all_text)
    if m:
        facts["avg_daily_deposit"] = m.group(1).replace(",", "") + "万元"

    # 代发签约
    m = re.search(r"(\d+)\s*(?:名|人)?员工.*签约代发", all_text)
    if m:
        facts["payroll_signup"] = m.group(1) + "人"

    # 发薪量
    m = re.search(r"发薪量\s*([\d,.]+)\s*万", all_text)
    if m:
        facts["payroll_amount"] = m.group(1).replace(",", "") + "万元"

    # PD评级下滑原因
    pd_block = _extract_block(
        _split_lines(all_text),
        r"PD评级较上期下滑",
        r"(?:^（[二三]）|^\d+\.)"
    )
    if pd_block:
        facts["pd_decline_reason"] = pd_block[:300]

    # 面访记录
    visit_block = _extract_block(
        _split_lines(all_text),
        r"实控人面访评价",
        r"(?:^3\.\s*实地走访|^\d+\.)"
    )
    if visit_block:
        facts["controller_interview"] = visit_block[:500]

    # 实地走访
    site_block = _extract_block(
        _split_lines(all_text),
        r"实地走访情况",
        r"(?:^4\.\s*与我行|^\d+\.)"
    )
    if site_block:
        facts["site_visit"] = site_block[:300]

    # 经营地址（从租赁合同中优先提取，区分注册地址和实际经营地址）
    for pat in [
        r"租[赁用].*?(?:位于|地址[为是：:])\s*(.+?)(?:[，。,\n]|$)",
        r"经营地.*?(?:位于)\s*(.+?)(?:[。\n]|$)",
        r"办公.*?(?:位于|地址[为是：:])\s*(.+?)(?:[，。,\n]|$)",
    ]:
        m = re.search(pat, all_text)
        if m and len(m.group(1).strip()) > 10:
            facts["actual_operating_address"] = _clean_ws(m.group(1))[:150]
            break


def _extract_customer_manager(all_text: str, facts: dict):
    """Extract customer manager info."""
    # Pattern: 客户经理：XXX  联系电话：XXX
    m = re.search(r"客户经理[：:]\s*([\u4e00-\u9fff]{2,4})", all_text)
    if m:
        facts["customer_manager_name"] = m.group(1).strip()
    m = re.search(r"联系电话[：:]\s*(1\d{10})", all_text)
    if m:
        facts["customer_manager_phone"] = m.group(1).strip()

    # Fallback: 姓名+手机号+收
    if not facts.get("customer_manager_name"):
        m = re.search(r"(?P<name>[\u4e00-\u9fff]{2,4})(?P<phone>1\d{10})收", all_text)
        if m:
            facts.setdefault("customer_manager_name", m.group("name"))
            facts.setdefault("customer_manager_phone", m.group("phone"))


def _extract_business_info(lines: list[str], all_text: str, facts: dict):
    """Extract business description, revenue structure, etc."""
    water = _extract_block(lines, r"^主营业务[—\-－]+智慧水利$", r"^主营业务[—\-－]+智慧教育$")
    edu = _extract_block(lines, r"^主营业务[—\-－]+智慧教育$", r"^公司产品优势")
    if water:
        facts["business_water"] = water
    if edu:
        facts["business_education"] = edu

    comp = _extract_block(lines, r"^公司产品优势以及企业的核心竞争力[：:]?$", r"^公司水利和教育的销售收入")
    if comp:
        facts["core_competence"] = comp

    rev = _extract_block(lines, r"^公司水利和教育的销售收入以及结构占比情况[：:]?$", r"^公司经营账期")
    if rev:
        facts["revenue_split"] = _clean_ws(rev)

    ap = _extract_block(lines, r"^公司经营账期情况描述[：:]?$", r"^实际控制人")
    if ap:
        facts["account_period"] = ap

    # Fallback: try generic patterns if structured headings weren't found
    if not facts.get("business_water") and not facts.get("business_education"):
        m = re.search(r"(?:实际主营业务|主营业务)[：:]\s*(.+?)(?:\n\n|\n[一-鿿])", all_text, re.DOTALL)
        if m and len(m.group(1).strip()) > 20:
            facts["main_business"] = _clean_ws(m.group(1))[:300]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def build_material_kb(file_contents: dict[str, str]) -> dict[str, Any]:
    """Build KB from ALL extracted file_contents.

    Unlike the previous version which only picked one file, this scans ALL
    uploaded materials to maximise coverage.  Tables are identified by header
    content (semantic matching), not by hard-coded table numbers.

    Returns a dict with keys:
    - source_files: list of files that contributed facts
    - facts: dict[str, Any]  (flat dimensions merged)
    - tables: dict[str, list[dict]]  (typed table data)
    """
    kb: dict[str, Any] = {
        "source_files": [],
        "source_file": "",  # backward compat
        "facts": {},
        "tables": {},
    }
    if not file_contents:
        return kb

    facts: dict[str, Any] = {}
    typed_tables: dict[str, list[dict]] = {}

    # Concatenate ALL materials for regex extraction
    all_text_parts = []
    for fname, content in file_contents.items():
        if content:
            all_text_parts.append(content)
    all_text = "\n\n".join(all_text_parts)

    # --- Regex extraction across all materials ---
    _extract_basic_info(all_text, facts)
    _extract_controller_info(all_text, facts)
    _extract_credit_history(all_text, facts)
    _extract_risk_info(all_text, facts)
    _extract_order_info(all_text, facts)
    _extract_customer_manager(all_text, facts)
    _extract_credit_application(all_text, facts)
    _extract_tech_info(all_text, facts)
    _extract_comprehensive_benefit(all_text, facts)

    # --- Per-file structured extraction ---
    for fname, content in file_contents.items():
        if not content:
            continue
        lines = _split_lines(content)

        # Business info (uses structured section headings)
        _extract_business_info(lines, content, facts)

        # Parse tables and identify by header content
        tables = _parse_docx_export_tables(lines)
        for tname, tdata in tables.items():
            if len(tdata) < 2:
                continue
            ttype = _identify_table_type(tdata[0])
            if ttype and ttype not in typed_tables:
                rows = _table_to_dicts(tdata)
                if rows:
                    typed_tables[ttype] = rows
                    kb["source_files"].append(fname)

    # --- Map typed tables into facts (backward compatible keys) ---
    if "upstream" in typed_tables:
        facts["upstream_top5"] = typed_tables["upstream"]
    if "downstream" in typed_tables:
        facts["downstream_top5"] = typed_tables["downstream"]
    if "financing" in typed_tables:
        facts["financing"] = typed_tables["financing"]
    if "affiliates" in typed_tables:
        facts["affiliates"] = typed_tables["affiliates"]
    if "r_and_d" in typed_tables:
        facts["r_and_d"] = typed_tables["r_and_d"]
    if "shareholders" in typed_tables:
        facts["shareholders"] = typed_tables["shareholders"]
    if "bank_flows" in typed_tables:
        facts["bank_flows"] = typed_tables["bank_flows"]
    if "orders" in typed_tables:
        facts["orders"] = typed_tables["orders"]
    if "tax_data" in typed_tables:
        facts["tax_data"] = typed_tables["tax_data"]
    if "assets" in typed_tables:
        facts["assets"] = typed_tables["assets"]
    if "patents" in typed_tables:
        facts["patents"] = typed_tables["patents"]
    if "receivables_top5" in typed_tables:
        facts["receivables_top5"] = typed_tables["receivables_top5"]
    if "other_receivables_top5" in typed_tables:
        facts["other_receivables_top5"] = typed_tables["other_receivables_top5"]
    if "payables_top5" in typed_tables:
        facts["payables_top5"] = typed_tables["payables_top5"]

    kb["facts"] = facts
    kb["tables"] = typed_tables
    if kb["source_files"]:
        kb["source_file"] = kb["source_files"][0]  # backward compat

    return kb


# ---------------------------------------------------------------------------
# Dimension-based retrieval (改造二: 按需检索)
# ---------------------------------------------------------------------------

# 维度定义：每个维度对应 KB facts 中的字段
DIMENSION_FIELDS = {
    "basic_info": [
        "company_name", "establishment_date", "registered_capital",
        "paid_in_capital", "social_insurance_count", "employee_count",
        "legal_representative", "industry", "operating_address",
    ],
    "controller": [
        "controller_name", "controller_id", "controller_share_pct",
        "controller_resume", "spouse_name", "spouse_id",
    ],
    "shareholders": ["shareholders"],
    "business": [
        "business_water", "business_education", "main_business",
        "core_competence", "revenue_split", "account_period",
    ],
    "supply_chain": ["upstream_top5", "downstream_top5"],
    "affiliates": ["affiliates"],
    "financing": ["financing"],
    "credit_history": [
        "credit_cooperation_history", "prev_approval_date",
        "is_existing_customer", "prev_credit_exposure",
        "prev_guarantee_method", "prev_pd_rating", "loan_drawdown_info",
    ],
    "risk": ["risk_signals", "negative_info", "esg_rating", "aml_risk_level"],
    "orders": ["orders_count", "orders_total_amount", "orders_uncollected"],
    "assets": ["assets"],
    "bank_flows": ["bank_flows"],
    "r_and_d": ["r_and_d"],
    "tax_data": ["tax_data"],
    "customer_manager": ["customer_manager_name", "customer_manager_phone"],
    "patents": ["patents"],
    "receivables": ["receivables_top5", "other_receivables_top5", "payables_top5"],
}

# 字段类型与相关维度的映射（用于 Phase 3 XX字段提取）
FIELD_TYPE_DIMENSIONS = {
    # 企业基本信息
    "company_name": ["basic_info"],
    "企业名称": ["basic_info"],
    "公司名称": ["basic_info"],
    "成立": ["basic_info"],
    "注册": ["basic_info"],
    "实收": ["basic_info"],
    "社保": ["basic_info"],
    "员工": ["basic_info"],
    "法人": ["basic_info"],
    "行业": ["basic_info"],
    "地址": ["basic_info"],

    # 实控人
    "实控人": ["controller", "basic_info"],
    "控制人": ["controller", "basic_info"],
    "配偶": ["controller"],
    "持股": ["controller", "shareholders"],

    # 股东
    "股东": ["shareholders"],
    "股权": ["shareholders"],

    # 业务相关
    "主营业务": ["business"],
    "业务": ["business"],
    "竞争力": ["business"],
    "收入": ["business", "supply_chain"],
    "账期": ["business"],

    # 上下游
    "上游": ["supply_chain"],
    "供应商": ["supply_chain"],
    "下游": ["supply_chain"],
    "客户": ["supply_chain", "orders"],
    "销售": ["supply_chain", "business"],

    # 关联企业
    "关联": ["affiliates"],
    "子公司": ["affiliates"],
    "参股": ["affiliates"],

    # 融资
    "融资": ["financing", "credit_history"],
    "授信": ["credit_history", "financing"],
    "贷款": ["financing", "credit_history"],
    "银行": ["financing", "bank_flows"],

    # 风险
    "风险": ["risk"],
    "负面": ["risk"],
    "诉讼": ["risk"],
    "ESG": ["risk"],
    "反洗钱": ["risk"],

    # 订单
    "订单": ["orders"],
    "合同": ["orders"],
    "项目": ["orders", "business"],

    # 资产
    "资产": ["assets"],
    "房产": ["assets"],
    "土地": ["assets"],
    "车辆": ["assets"],

    # 银行流水
    "流水": ["bank_flows"],
    "账户": ["bank_flows"],

    # 研发
    "研发": ["r_and_d"],
    "专利": ["r_and_d", "patents"],

    # 税务
    "纳税": ["tax_data"],
    "税": ["tax_data"],

    # 客户经理
    "客户经理": ["customer_manager"],
    "联系": ["customer_manager"],

    # 应收应付
    "应收": ["receivables"],
    "应付": ["receivables"],
}


def build_dimension_text(
    kb: dict[str, Any],
    dimensions: list[str],
    max_chars: int = 8000,
    include_raw_tables: bool = False,
) -> str:
    """Build KB text for specific dimensions only.

    This is the core of 改造二: instead of truncating all materials,
    each phase receives only the relevant KB dimensions.

    Args:
        kb: Knowledge base from build_material_kb()
        dimensions: List of dimension names to include (e.g., ["basic_info", "controller"])
        max_chars: Maximum characters for the output
        include_raw_tables: If True, include raw table data (for table-filling phases)

    Returns:
        Compact text containing only the requested dimensions.
    """
    facts = (kb or {}).get("facts", {}) or {}
    tables = (kb or {}).get("tables", {}) or {}
    parts: list[str] = []

    def add(title: str, body: str):
        b = (body or "").strip()
        if not b:
            return
        parts.append(f"[{title}]\n{b}")

    for dim in dimensions:
        fields = DIMENSION_FIELDS.get(dim, [])
        if not fields:
            continue

        if dim == "basic_info":
            lines = []
            for label, key in [
                ("企业名称", "company_name"),
                ("成立时间", "establishment_date"),
                ("注册资本", "registered_capital"),
                ("实收资本", "paid_in_capital"),
                ("社保人数", "social_insurance_count"),
                ("员工人数", "employee_count"),
                ("法定代表人", "legal_representative"),
                ("所属行业", "industry"),
                ("经营地址", "operating_address"),
            ]:
                v = facts.get(key, "")
                if v:
                    lines.append(f"{label}：{v}")
            if lines:
                add("企业基本信息", "\n".join(lines))

        elif dim == "controller":
            lines = []
            for label, key in [
                ("实控人", "controller_name"),
                ("实控人持股", "controller_share_pct"),
                ("实控人身份证", "controller_id"),
                ("配偶", "spouse_name"),
            ]:
                v = facts.get(key, "")
                if v:
                    lines.append(f"{label}：{v}")
            if facts.get("controller_resume"):
                lines.append(f"简历：{facts['controller_resume'][:200]}")
            if lines:
                add("实控人信息", "\n".join(lines))

        elif dim == "shareholders":
            sh = facts.get("shareholders") or []
            if isinstance(sh, list) and sh:
                lines = []
                for it in sh[:10]:
                    if isinstance(it, dict):
                        name = it.get("股东名称", "") or it.get("股东", "")
                        pct = it.get("出资比例%", "") or it.get("出资比例", "") or it.get("持股比例", "")
                        amt = it.get("认缴出资额", "") or it.get("认缴出资", "")
                        if name:
                            line = name
                            if pct:
                                line += f" {pct}"
                            if amt:
                                line += f" (认缴{amt})"
                            lines.append(line)
                if lines:
                    add("股东结构", "\n".join(lines))
                if include_raw_tables:
                    add("股东明细", _format_table_data(sh[:15], "股东"))

        elif dim == "business":
            bw = (facts.get("business_water") or "").strip()
            be = (facts.get("business_education") or "").strip()
            if bw:
                add("主营业务-智慧水利", bw)
            if be:
                add("主营业务-智慧教育", be)
            if not bw and not be:
                mb = (facts.get("main_business") or "").strip()
                if mb:
                    add("主营业务", mb)
            cc = (facts.get("core_competence") or "").strip()
            if cc:
                add("核心竞争力", cc)
            rs = (facts.get("revenue_split") or "").strip()
            if rs:
                add("收入结构", rs)
            ap = (facts.get("account_period") or "").strip()
            if ap:
                add("经营账期", ap)

        elif dim == "supply_chain":
            up = facts.get("upstream_top5") or []
            if isinstance(up, list) and up:
                names = []
                for it in up[:5]:
                    if isinstance(it, dict):
                        n = (it.get("主要上游供应商", "") or
                             it.get("上游供应商", "") or
                             it.get("供应商", ""))
                        if n:
                            names.append(n)
                if names:
                    add("主要上游供应商", "、".join(names))
                if include_raw_tables:
                    add("上游明细", _format_table_data(up[:5], "供应商"))

            dn = facts.get("downstream_top5") or []
            if isinstance(dn, list) and dn:
                names = []
                for it in dn[:5]:
                    if isinstance(it, dict):
                        n = (it.get("主要下游销售客户", "") or
                             it.get("下游销售客户", "") or
                             it.get("客户", ""))
                        if n:
                            names.append(n)
                if names:
                    add("主要下游客户", "、".join(names))
                if include_raw_tables:
                    add("下游明细", _format_table_data(dn[:5], "客户"))

        elif dim == "affiliates":
            af = facts.get("affiliates") or []
            if isinstance(af, list) and af:
                names = []
                for it in af[:5]:
                    if isinstance(it, dict):
                        n = it.get("企业名称", "") or it.get("关联企业名称", "")
                        if n:
                            names.append(n)
                if names:
                    add("关联企业", "、".join(names))
                if include_raw_tables:
                    add("关联企业明细", _format_table_data(af[:10], "企业"))

        elif dim == "financing":
            fn = facts.get("financing") or []
            if isinstance(fn, list) and fn:
                lines = []
                for it in fn[:5]:
                    if isinstance(it, dict):
                        inst = it.get("融资机构", "")
                        amt = it.get("授信金额", "") or it.get("授信额度", "")
                        used = it.get("已用金额", "") or it.get("已用额度", "")
                        if inst:
                            line = inst
                            if amt:
                                line += f" 授信{amt}"
                            if used:
                                line += f" 已用{used}"
                            lines.append(line)
                if lines:
                    add("融资情况", "\n".join(lines))
                if include_raw_tables:
                    add("融资明细", _format_table_data(fn[:10], "融资"))

        elif dim == "credit_history":
            lines = []
            for label, key in [
                ("历史合作", "credit_cooperation_history"),
                ("上期批复日期", "prev_approval_date"),
                ("上期敞口", "prev_credit_exposure"),
                ("上期担保", "prev_guarantee_method"),
                ("上期评级", "prev_pd_rating"),
            ]:
                v = facts.get(key, "")
                if v:
                    lines.append(f"{label}：{v}")
            if facts.get("is_existing_customer") is True:
                lines.append("客户类型：存量客户")
            elif facts.get("is_existing_customer") is False:
                lines.append("客户类型：新客户")
            if lines:
                add("授信历史", "\n".join(lines))
            ldi = (facts.get("loan_drawdown_info") or "").strip()
            if ldi:
                add("贷款提用情况", ldi[:300])

        elif dim == "risk":
            rs = (facts.get("risk_signals") or "").strip()
            if rs:
                add("风险信号", rs[:400])
            ni = (facts.get("negative_info") or "").strip()
            if ni:
                add("负面信息", ni[:300])
            esg = facts.get("esg_rating", "")
            if esg:
                add("ESG评级", esg)
            aml = facts.get("aml_risk_level", "")
            if aml:
                add("反洗钱风险等级", aml)

        elif dim == "orders":
            lines = []
            if facts.get("orders_count"):
                lines.append(f"在手订单：{facts['orders_count']}笔")
            if facts.get("orders_total_amount"):
                lines.append(f"合同总金额：{facts['orders_total_amount']}")
            if facts.get("orders_uncollected"):
                lines.append(f"未回款：{facts['orders_uncollected']}")
            if lines:
                add("在手订单", "\n".join(lines))

        elif dim == "assets":
            ast = facts.get("assets") or []
            if isinstance(ast, list) and ast:
                names = []
                for it in ast[:5]:
                    if isinstance(it, dict):
                        n = it.get("资产名称", "") or it.get("坐落位置", "")
                        owner = it.get("所有权人", "")
                        if n:
                            line = n
                            if owner:
                                line += f"({owner})"
                            names.append(line)
                if names:
                    add("资产情况", "、".join(names))
                if include_raw_tables:
                    add("资产明细", _format_table_data(ast[:10], "资产"))

        elif dim == "bank_flows":
            bf = facts.get("bank_flows") or []
            if isinstance(bf, list) and bf:
                lines = []
                for it in bf[:5]:
                    if isinstance(it, dict):
                        bank = it.get("开户行", "")
                        inflow = it.get("流入量", "") or it.get("流入", "")
                        if bank:
                            line = bank
                            if inflow:
                                line += f" 流入{inflow}"
                            lines.append(line)
                if lines:
                    add("银行流水", "\n".join(lines))
                if include_raw_tables:
                    add("银行流水明细", _format_table_data(bf[:10], "流水"))

        elif dim == "r_and_d":
            rd = facts.get("r_and_d") or []
            if isinstance(rd, list) and rd:
                lines = []
                for it in rd[:3]:
                    if isinstance(it, dict):
                        year = it.get("年份", "")
                        expense = it.get("研发费用", "") or it.get("研发投入", "")
                        if year and expense:
                            lines.append(f"{year}年：{expense}")
                if lines:
                    add("研发投入", "\n".join(lines))
                if include_raw_tables:
                    add("研发明细", _format_table_data(rd[:5], "研发"))

        elif dim == "tax_data":
            td = facts.get("tax_data") or []
            if isinstance(td, list) and td and include_raw_tables:
                add("纳税申报对比", _format_table_data(td[:5], "纳税"))

        elif dim == "customer_manager":
            cm_name = (facts.get("customer_manager_name") or "").strip()
            cm_phone = (facts.get("customer_manager_phone") or "").strip()
            if cm_name or cm_phone:
                add("客户经理", f"{cm_name} {cm_phone}".strip())

        elif dim == "patents":
            pt = facts.get("patents") or []
            if isinstance(pt, list) and pt:
                names = []
                for it in pt[:5]:
                    if isinstance(it, dict):
                        n = it.get("专利名称", "")
                        if n:
                            names.append(n)
                if names:
                    add("专利情况", "、".join(names))

        elif dim == "receivables":
            for key, title in [
                ("receivables_top5", "应收账款前五"),
                ("other_receivables_top5", "其他应收款前五"),
                ("payables_top5", "应付账款前五"),
            ]:
                items = facts.get(key) or []
                if isinstance(items, list) and items and include_raw_tables:
                    add(title, _format_table_data(items[:5], "明细"))

    text = "\n\n".join(parts)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[KB维度截断]"


def _format_table_data(items: list, label: str) -> str:
    """Format table data items as readable text."""
    if not items:
        return ""
    lines = []
    for i, it in enumerate(items, 1):
        if isinstance(it, dict):
            pairs = [f"{k}: {v}" for k, v in it.items() if v and str(v).strip()]
            if pairs:
                lines.append(f"{i}. " + " | ".join(pairs[:6]))
    return "\n".join(lines)


def infer_dimensions_for_field(field: "FieldSlot") -> list[str]:
    """Infer relevant KB dimensions from a field's context.

    Used by Phase 3 to select relevant materials for each batch of fields.
    """
    text = f"{field.context_before} {field.context_after} {field.xx_text}"
    dimensions = set()

    for keyword, dims in FIELD_TYPE_DIMENSIONS.items():
        if keyword in text:
            dimensions.update(dims)

    # Default: include basic_info if no specific dimension detected
    if not dimensions:
        dimensions.add("basic_info")

    return list(dimensions)


def infer_dimensions_for_batch(fields: list) -> list[str]:
    """Infer relevant KB dimensions for a batch of fields."""
    dimensions = set()
    for f in fields:
        dimensions.update(infer_dimensions_for_field(f))
    return list(dimensions)


def infer_dimensions_for_label(label: str, context: str = "") -> list[str]:
    """Infer relevant KB dimensions from a labeled field's label/context."""
    text = f"{label} {context}"
    dimensions = set()

    for keyword, dims in FIELD_TYPE_DIMENSIONS.items():
        if keyword in text:
            dimensions.update(dims)

    if not dimensions:
        dimensions.add("basic_info")

    return list(dimensions)


def infer_dimensions_for_example(example_text: str) -> list[str]:
    """Infer relevant KB dimensions from an example paragraph's content."""
    dimensions = set()

    for keyword, dims in FIELD_TYPE_DIMENSIONS.items():
        if keyword in example_text:
            dimensions.update(dims)

    # For example paragraphs, always include business dimension
    dimensions.add("business")

    return list(dimensions)


def kb_to_prompt_text(kb: dict[str, Any], max_chars: int = 6000) -> str:
    """Build a compact KB text for LLM prompts.

    Expanded to cover all new dimensions.
    """
    facts = (kb or {}).get("facts", {}) or {}
    parts: list[str] = []

    def add(title: str, body: str):
        b = (body or "").strip()
        if not b:
            return
        parts.append(f"[{title}]\n{b}")

    # Basic info
    basic_fields = [
        ("企业名称", "company_name"),
        ("成立时间", "establishment_date"),
        ("注册资本", "registered_capital"),
        ("实收资本", "paid_in_capital"),
        ("社保人数", "social_insurance_count"),
        ("员工人数", "employee_count"),
        ("法定代表人", "legal_representative"),
        ("所属行业", "industry"),
        ("经营地址", "operating_address"),
    ]
    basic_lines = []
    for label, key in basic_fields:
        v = facts.get(key, "")
        if v:
            basic_lines.append(f"{label}：{v}")
    if basic_lines:
        add("企业基本信息", "\n".join(basic_lines))

    # Controller
    ctrl_fields = [
        ("实控人", "controller_name"),
        ("实控人持股", "controller_share_pct"),
        ("实控人身份证", "controller_id"),
        ("配偶", "spouse_name"),
    ]
    ctrl_lines = []
    for label, key in ctrl_fields:
        v = facts.get(key, "")
        if v:
            ctrl_lines.append(f"{label}：{v}")
    if facts.get("controller_resume"):
        ctrl_lines.append(f"简历：{facts['controller_resume'][:200]}")
    if ctrl_lines:
        add("实控人信息", "\n".join(ctrl_lines))

    # Customer manager
    cm = f"{facts.get('customer_manager_name', '')} {facts.get('customer_manager_phone', '')}".strip()
    add("客户经理", cm)

    # Business
    add("主营业务-智慧水利", facts.get("business_water", ""))
    add("主营业务-智慧教育", facts.get("business_education", ""))
    if not facts.get("business_water") and not facts.get("business_education"):
        add("主营业务", facts.get("main_business", ""))
    add("核心竞争力", facts.get("core_competence", ""))
    add("收入结构", facts.get("revenue_split", ""))
    add("经营账期", facts.get("account_period", ""))

    # Credit history
    credit_lines = []
    for label, key in [
        ("历史合作", "credit_cooperation_history"),
        ("上期批复日期", "prev_approval_date"),
        ("上期敞口", "prev_credit_exposure"),
        ("上期担保", "prev_guarantee_method"),
        ("上期评级", "prev_pd_rating"),
        ("客户类型", None),
    ]:
        if key:
            v = facts.get(key, "")
            if v:
                credit_lines.append(f"{label}：{v}")
    if facts.get("is_existing_customer") is True:
        credit_lines.append("客户类型：存量客户")
    elif facts.get("is_existing_customer") is False:
        credit_lines.append("客户类型：新客户")
    if credit_lines:
        add("授信历史", "\n".join(credit_lines))

    # Risk info
    if facts.get("risk_signals"):
        add("风险信号", facts["risk_signals"][:300])
    if facts.get("negative_info"):
        add("负面信息", facts["negative_info"][:200])

    # Orders
    order_lines = []
    if facts.get("orders_count"):
        order_lines.append(f"在手订单{facts['orders_count']}笔")
    if facts.get("orders_total_amount"):
        order_lines.append(f"合同总金额{facts['orders_total_amount']}")
    if facts.get("orders_uncollected"):
        order_lines.append(f"未回款{facts['orders_uncollected']}")
    if order_lines:
        add("在手订单", "，".join(order_lines))

    # Supply chain summaries
    up = facts.get("upstream_top5") or []
    if isinstance(up, list) and up:
        names = [it.get("主要上游供应商", "") or it.get("上游供应商", "") or it.get("供应商", "")
                 for it in up if isinstance(it, dict)]
        names = [n for n in names if n]
        if names:
            add("主要上游(前五)", "、".join(names))

    dn = facts.get("downstream_top5") or []
    if isinstance(dn, list) and dn:
        names = [it.get("主要下游销售客户", "") or it.get("下游销售客户", "") or it.get("客户", "")
                 for it in dn if isinstance(it, dict)]
        names = [n for n in names if n]
        if names:
            add("主要下游(前五)", "、".join(names))

    # Shareholders summary
    sh = facts.get("shareholders") or []
    if isinstance(sh, list) and sh:
        sh_lines = []
        for it in sh[:15]:
            name = it.get("股东名称", "") or it.get("股东", "")
            pct = it.get("出资比例%", "") or it.get("出资比例", "") or it.get("持股比例", "")
            if name:
                sh_lines.append(f"{name} {pct}".strip())
        if sh_lines:
            add("股东结构", "\n".join(sh_lines))

    text = "\n\n".join(parts)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[KB截断]"
