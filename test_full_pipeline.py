# -*- coding: utf-8 -*-
"""
Full pipeline test: run FormFillAgent with section generation mode
on the real template + real materials, output filled docx.
"""
import sys
import io
import os
import glob
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from openai import OpenAI
from form_filler import FormFillAgent
from tools import _read_single_file

TEMPLATE = r"templates_cache\福建普惠授信申报及审查审批意见表2025新版.docx"
MATERIAL_DIR = r"D:\刘野\众安\新建文件夹\2026.3.25续贷材料"
OUTPUT_DIR = r"outputs"


def load_materials(directory):
    """Load all supported files from directory (recursive).
    Returns (file_contents, file_path_map).
    """
    exts = {'.txt', '.docx', '.doc', '.pdf', '.xlsx', '.xls'}
    result = {}
    path_map = {}
    for root, dirs, files in os.walk(directory):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in exts:
                fp = os.path.join(root, fname)
                try:
                    content = _read_single_file(fp)
                    if content:
                        key = os.path.basename(fp)
                        result[key] = content
                        path_map[key] = fp
                except Exception as e:
                    print(f"  Skip {fname}: {e}")
    return result, path_map


def make_llm_caller():
    """Create LLM caller using DeepSeek API."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("Set DEEPSEEK_API_KEY environment variable")
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    call_count = [0]

    def caller(system_prompt: str, user_prompt: str) -> str:
        call_count[0] += 1
        print(f"    [LLM call #{call_count[0]}] sys={len(system_prompt)}c usr={len(user_prompt)}c")
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=8192,
                    temperature=0.3,
                    timeout=120,
                )
                return resp.choices[0].message.content or ""
            except Exception as e:
                print(f"    [LLM retry {attempt+1}/3] {e}")
                if attempt == 2:
                    return ""

    return caller


def progress(msg):
    print(f"  [{time.strftime('%H:%M:%S')}] {msg}")


def main():
    print("=" * 60)
    print("Full Pipeline Test: Section Generation Mode")
    print("=" * 60)

    # 1. Load materials
    print("\n[1] Loading materials...")
    file_contents, file_path_map = load_materials(MATERIAL_DIR)
    print(f"    Loaded {len(file_contents)} files:")
    for fname in sorted(file_contents.keys()):
        print(f"      {fname} ({len(file_contents[fname])} chars)")

    # 2. Create LLM caller
    print("\n[2] Creating LLM caller (DeepSeek)...")
    llm_caller = make_llm_caller()

    # 3. Create FormFillAgent
    print("\n[3] Creating FormFillAgent...")
    agent = FormFillAgent(llm_caller, file_contents, file_path_map=file_path_map)

    # 4. Run pipeline
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"section_gen_test_{int(time.time())}.docx")

    print(f"\n[4] Running pipeline...")
    print(f"    Template: {TEMPLATE}")
    print(f"    Output:   {output_path}")
    print("-" * 60)

    try:
        result_path = agent.run(TEMPLATE, output_path, progress)
        print("-" * 60)
        print(f"\n[5] Pipeline complete!")
        print(f"    Output: {result_path}")
        print(f"    Stats: {agent.stats}")
        if agent.pending_tags:
            print(f"    Pending tags: {len(agent.pending_tags)}")
            for tag in agent.pending_tags[:10]:
                print(f"      - {tag.get('label', '?')}: {tag.get('context', '?')[:60]}")
    except Exception as e:
        print(f"\n[!] Pipeline failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Done")
    print("=" * 60)


if __name__ == "__main__":
    main()
