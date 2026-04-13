# -*- coding: utf-8 -*-
"""CLI test script to run form fill pipeline directly."""
import os, sys, time

sys.stdout.reconfigure(encoding='utf-8')

MATERIAL_DIR = r"D:\刘野\众安\新建文件夹\2026.3.25续贷材料"
TEMPLATE = os.path.join(os.path.dirname(__file__), "templates_cache",
                        "福建普惠授信申报及审查审批意见表2025新版.docx")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")

def main():
    from tools import tool_read_files, _expand_paths
    from form_filler import FormFillAgent
    from llm import LLMClient
    import re

    import sys as _sys
    provider = _sys.argv[1] if len(_sys.argv) > 1 else "deepseek"
    api_keys = {
        "deepseek": "sk-175ec8d4075a4de695c25177cbac83db",
        "minimax": "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",
        "kimi-k2.5": "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",
    }
    api_key = api_keys.get(provider, "")
    llm_client = LLMClient(provider=provider, api_key=api_key)
    print(f"使用模型: {provider} ({llm_client.model})")

    # 1. Read materials
    print("=== 读取材料 ===")
    expanded = _expand_paths([MATERIAL_DIR])
    print(f"找到 {len(expanded)} 个文件")

    file_contents = {}
    raw = tool_read_files([MATERIAL_DIR])
    for section in raw.split("===== "):
        if section.strip():
            parts = section.split(" =====\n", 1)
            if len(parts) == 2:
                k = parts[0].strip()
                k = re.sub(r"\s*\(\d+字\)\s*$", "", k)
                file_contents[k] = parts[1]
    print(f"已解析 {len(file_contents)} 个文件内容")

    # 2. Build file_path_map
    file_path_map = {}
    for fp in expanded:
        fname = os.path.basename(fp)
        parent = os.path.basename(os.path.dirname(fp))
        display_name = f"{parent}/{fname}" if parent else fname
        file_path_map[display_name] = fp

    # 3. LLM caller
    def llm_caller(system_prompt, user_prompt):
        return llm_client.simple_chat(system_prompt, user_prompt)

    # 4. Run
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR,
        f"福建普惠授信申报及审查审批意见表2025新版_filled_{int(time.time())}.docx")

    def progress(msg):
        print(f"[进度] {msg}")

    print(f"\n=== 开始填写 ===")
    print(f"模板: {TEMPLATE}")
    print(f"输出: {output_path}")

    agent = FormFillAgent(llm_caller, file_contents, file_path_map=file_path_map)
    result = agent.run(TEMPLATE, output_path, progress)

    print(f"\n=== 完成 ===")
    print(f"输出文件: {result}")
    print(f"统计: filled={agent.stats['filled']}, total={agent.stats['total_sections']}")
    if agent.stats['errors']:
        print(f"错误 ({len(agent.stats['errors'])}):")
        for e in agent.stats['errors']:
            print(f"  - {e}")
    if hasattr(agent, '_validation_blockers') and agent._validation_blockers:
        print(f"Blockers ({len(agent._validation_blockers)}):")
        for b in agent._validation_blockers:
            print(f"  - {b}")

if __name__ == "__main__":
    main()
