# -*- coding: utf-8 -*-
"""
F4 Diagnostic: trace exactly why KB prefill matches/misses each labeled field and checkbox.
No LLM calls. Runs in seconds.
"""
import sys, io, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)

from docx import Document
from tools import _read_single_file
from material_kb import build_material_kb
from truth_fill import prefill_labeled_fields_from_kb, prefill_checkboxes_from_kb
from form_filler import (
    scan_labeled_fields, scan_cell_fields,
    scan_nested_tables, _get_cell,
)

TEMPLATE = r"templates_cache\福建普惠授信申报及审查审批意见表2025新版.docx"
MATERIAL_DIR = r"D:\刘野\众安\新建文件夹\2026.3.25续贷材料"


def load_materials(directory):
    exts = {'.txt', '.docx', '.doc', '.pdf', '.xlsx', '.xls'}
    result = {}
    for root, dirs, files in os.walk(directory):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in exts:
                fp = os.path.join(root, fname)
                try:
                    content = _read_single_file(fp)
                    if content:
                        result[os.path.basename(fp)] = content
                except Exception:
                    pass
    return result


def main():
    print("=" * 70)
    print("F4 DIAGNOSTIC")
    print("=" * 70)

    # 1. Load materials & build KB
    print("\n[1] Building KB...")
    file_contents = load_materials(MATERIAL_DIR)
    kb = build_material_kb(file_contents)
    facts = kb.get("facts", {})
    print(f"  KB facts ({len(facts)} keys):")
    for k, v in sorted(facts.items()):
        v_str = str(v)[:80]
        print(f"    {k}: {v_str}")

    # 2. Scan template
    print(f"\n[2] Scanning template: {TEMPLATE}")
    doc = Document(TEMPLATE)
    all_labeled_fields = []
    all_checkboxes = []
    global_lf = 0
    global_cb = 0

    for t_idx, table in enumerate(doc.tables):
        for r_idx, row in enumerate(table.rows):
            for c_idx, cell in enumerate(row.cells):
                lfs = scan_labeled_fields(cell, t_idx, r_idx, c_idx)
                for lf in lfs:
                    global_lf += 1
                    lf.lf_id = f"lf{global_lf:03d}"
                all_labeled_fields.extend(lfs)

                fields, cbs, examples = scan_cell_fields(cell, t_idx, r_idx, c_idx)
                for cb in cbs:
                    global_cb += 1
                    cb.cb_id = f"cb{global_cb:03d}"
                all_checkboxes.extend(cbs)

    print(f"  Found {len(all_labeled_fields)} labeled fields, {len(all_checkboxes)} checkboxes")

    # 3. Show all labeled fields
    print(f"\n[3] ALL LABELED FIELDS:")
    for lf in all_labeled_fields:
        print(f"  {lf.lf_id}: label='{lf.label}' | ctx='{lf.context_line[:60]}' | cell={lf.cell_path} | unit='{lf.unit}'")

    # 4. Run prefill and trace matching
    print(f"\n[4] PREFILL MATCHING (labeled fields):")
    result = prefill_labeled_fields_from_kb(all_labeled_fields, kb, financial_data=None)
    print(f"  Matched: {len(result)} fields")
    for lf_id, val in result.items():
        lf = next((f for f in all_labeled_fields if f.lf_id == lf_id), None)
        label = lf.label if lf else "?"
        print(f"    {lf_id} ({label}): '{val}'")

    # 5. Show which fields SHOULD have matched but didn't
    print(f"\n[5] UNMATCHED FIELDS (with KB fact analysis):")
    # Re-run the matching logic with verbose output
    label_to_fact = [
        (["客户名称"], "company_name"),
        (["申报单位"], "reporting_unit"),
        (["客户经理"], "customer_manager_name"),
        (["联系电话"], "customer_manager_phone"),
        (["申报额度"], "applied_credit_amount"),
        (["申报敞口"], "applied_exposure"),
        (["上一期授信敞口"], "prev_credit_exposure"),
        (["业务品种"], "business_product"),
        (["业务期限"], "business_term"),
        (["授信期限"], "credit_term"),
        (["担保方式"], "guarantee_method"),
        (["上一期授信担保方式"], "prev_guarantee_method"),
        (["PD评级"], "pd_rating"),
        (["上一期授信评级"], "prev_pd_rating"),
        (["国标行业"], "industry"),
        (["绿通标识"], "green_channel"),
        (["原有额度批复日期"], "prev_approval_date"),
        (["注册资本"], "registered_capital"),
        (["实收资本"], "paid_in_capital"),
        (["法定代表人", "法人代表"], "legal_representative"),
        (["实际控制人姓名", "实控人姓名"], "controller_name"),
        (["经营地址", "实际经营地址"], "operating_address"),
        (["社保人数", "上年度末社保"], "social_insurance_count"),
        (["员工人数", "上年度末员工"], "social_insurance_count"),
        (["实际控制人持股", "股权穿透后"], "controller_share_pct"),
        (["过往两年企业股权变动"], "equity_change"),
        (["反洗钱风险等级"], "aml_risk_level"),
        (["科技型企业评分"], "tech_score"),
        (["日均存款"], "avg_daily_deposit"),
        (["代发签约"], "payroll_signup"),
    ]
    for lf in all_labeled_fields:
        if lf.lf_id in result:
            continue  # already matched
        lab = (lf.label or '').strip()
        ctx = (lf.context_line or '').strip()
        key_text = lab + ' ' + ctx
        matched_rule = None
        for keywords, fact_key in label_to_fact:
            if any(kw in lab for kw in keywords):  # label only, matching actual prefill
                if callable(fact_key):
                    val = "(lambda)"
                else:
                    val = facts.get(fact_key, "<NOT IN KB>")
                matched_rule = f"rule={keywords[0]}→{fact_key}, KB val={str(val)[:60]}"
                break
        if matched_rule:
            print(f"  {lf.lf_id}: label='{lab[:40]}' → {matched_rule}")
        # Also show fields with no matching rule
        # (uncomment to see all unmatched)
        # else:
        #     print(f"  {lf.lf_id}: label='{lab[:40]}' → NO RULE")

    # 6. Checkbox prefill
    print(f"\n[6] CHECKBOX PREFILL:")
    cb_result = prefill_checkboxes_from_kb(all_checkboxes, kb)
    print(f"  Matched: {len(cb_result)} checkboxes")
    for cb_id, val in cb_result.items():
        cb = next((c for c in all_checkboxes if c.cb_id == cb_id), None)
        opt = getattr(cb, 'option_text', '') or getattr(cb, 'label', '') or '?' if cb else '?'
        grp = (getattr(cb, 'group_context', '') or getattr(cb, 'context_line', '') or '')[:40] if cb else '?'
        print(f"    {cb_id} ({opt} | {grp}): {val}")

    # 7. Show all checkboxes for reference
    print(f"\n[7] ALL CHECKBOXES:")
    for cb in all_checkboxes:
        grp = (getattr(cb, 'group_context', '') or getattr(cb, 'context_line', '') or '')[:50]
        opt = (getattr(cb, 'option_text', '') or getattr(cb, 'label', '') or '')[:20]
        print(f"  {cb.cb_id}: opt='{opt}' grp='{grp}'")


if __name__ == "__main__":
    main()
