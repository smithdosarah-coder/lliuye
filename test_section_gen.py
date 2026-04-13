# -*- coding: utf-8 -*-
"""
Minimal test: verify section generation mode works end-to-end.
"""
import sys
import io
import os
import glob

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from docx import Document
from template_decomposer import decompose_template, TemplateRole, infer_section_dimensions, compute_similarity
from section_generator import build_section_prompt, _clean_response
from material_kb import build_material_kb, build_dimension_text
from tools import _read_single_file

TEMPLATE = r"templates_cache\福建普惠授信申报及审查审批意见表2025新版.docx"
MATERIAL_DIR = r"D:\刘野\众安\新建文件夹\2026.3.25续贷材料"


def load_materials(directory):
    """Load all supported files from directory."""
    exts = {'.txt', '.docx', '.doc', '.pdf', '.xlsx', '.xls'}
    result = {}
    for fp in glob.glob(os.path.join(directory, '*')):
        ext = os.path.splitext(fp)[1].lower()
        if ext in exts:
            try:
                content = _read_single_file(fp)
                if content:
                    result[os.path.basename(fp)] = content
            except Exception as e:
                print(f"  Skip {os.path.basename(fp)}: {e}")
    return result


def main():
    print("=" * 60)
    print("Test: Section Generation Mode")
    print("=" * 60)

    # 1. Load template
    print("\n[1] Loading template...")
    doc = Document(TEMPLATE)
    decomp = decompose_template(doc)
    stats = decomp["stats"]
    print(f"    Skeleton: {stats['skeleton_count']}, Content: {stats['content_count']}")
    sections_to_rewrite = [s for s in decomp["body_sections"] if s.has_content_to_rewrite]
    print(f"    Sections to rewrite: {len(sections_to_rewrite)}")

    # 2. Load materials and build KB
    print("\n[2] Loading materials...")
    file_contents = load_materials(MATERIAL_DIR)
    print(f"    Loaded {len(file_contents)} files")

    print("\n[3] Building KB...")
    kb = build_material_kb(file_contents)
    facts = kb.get("facts", {})
    print(f"    KB facts: {len(facts)} fields")
    for k, v in list(facts.items())[:8]:
        val_str = str(v)[:60] if v else "(empty)"
        print(f"      {k}: {val_str}")

    # 3. Pick test section: sec_45 (six elements) - the worst case from quality analysis
    test_section = None
    for s in sections_to_rewrite:
        if s.section_id == "sec_45":
            test_section = s
            break
    if not test_section:
        test_section = sections_to_rewrite[0]

    print(f"\n[4] Testing section: {test_section.section_id} - {test_section.title[:50]}")
    print(f"    Content paras to rewrite: {len(test_section.content_para_indices)}")
    dims = infer_section_dimensions(test_section)
    print(f"    KB dimensions: {dims}")

    # 4. Build prompt
    sys_p, usr_p = build_section_prompt(
        section=test_section,
        kb=kb,
        company_profile="",
        build_dimension_text_fn=build_dimension_text,
    )
    print(f"    System prompt: {len(sys_p)} chars")
    print(f"    User prompt: {len(usr_p)} chars")
    print(f"\n    User prompt preview:")
    print("-" * 40)
    print(usr_p[:2000])
    print("-" * 40)

    # 5. Call LLM
    print(f"\n[5] Calling DeepSeek LLM...")
    from openai import OpenAI
    client = OpenAI(
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com"
    )
    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": sys_p},
                {"role": "user", "content": usr_p},
            ],
            max_tokens=4096,
            temperature=0.3,
        )
        response = resp.choices[0].message.content
        response = _clean_response(response)
        print(f"    Response: {len(response)} chars")
        print(f"\n    Generated content (first 1200 chars):")
        print("-" * 40)
        print(response[:1200])
        print("-" * 40)
    except Exception as e:
        print(f"    LLM call failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # 6. Leakage check
    print(f"\n[6] Leakage check against template:")
    any_leak = False
    for p in test_section.paragraphs:
        if p.role == TemplateRole.CONTENT and p.text.strip():
            # Compare first 200 chars of response against each template paragraph
            sim = compute_similarity(response, p.text)
            status = "LEAK!" if sim > 0.5 else "ok"
            if sim > 0.3:
                print(f"    para[{p.para_idx}] sim={sim:.3f} [{status}] {p.text[:50]}...")
            if sim > 0.5:
                any_leak = True

    if any_leak:
        print("    WARNING: Template leakage detected!")
    else:
        print("    No leakage detected.")

    print("\n" + "=" * 60)
    print("Test PASSED" if not any_leak else "Test FAILED (leakage)")
    print("=" * 60)


if __name__ == "__main__":
    main()
