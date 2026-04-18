# -*- coding: utf-8 -*-
"""V16 Element Classifier — LLM-based zero-shot classifier.

输入:  outputs/v16_labeled_elements.json  (192 个采样 element)
       samples/*.docx                       (3 份源文档,用于建 section 上下文)
输出:  outputs/v16_llm_classified.json     (LLM 分类结果)

流程:
1. 对 3 份源 docx 做全量 element 抽取 + section 关联(nearest preceding heading)
2. 把 192 个采样 element 定位到全量 list,带上 section context
3. 按(source × section)分组批量送 LLM
4. LLM 返回 {op, label, confidence, justification}
5. 汇总保存

运行:
  py -u v16_classifier.py
环境变量:
  DEEPSEEK_API_KEY=sk-xxxx   (默认 provider)
  CLASSIFIER_PROVIDER=qwen_cloud / glm_cloud / local_vllm  (可切换)
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

# 复用现有抽取器
sys.path.insert(0, str(Path(__file__).parent))
from v16_step1_extract import (
    CURRENT_CLIENT, Element, SAMPLES_DIR, SECTION_NUM_RES, extract_elements,
)
from llm import LLMClient
from config import CLASSIFIER_PROVIDER, CLASSIFIER_TEMPERATURE

SRC = Path(__file__).parent / "outputs" / "v16_labeled_elements.json"
OUT = Path(__file__).parent / "outputs" / "v16_llm_classified.json"

# ────────────────────────────────────────────────────────────
# Section context 构建 — 给每个 element 找"最近的章节标题"
# ────────────────────────────────────────────────────────────
HEADING_STYLE_PAT = re.compile(r"^(Heading\s*\d|标题\s*\d|Title)", re.I)


def _is_heading_like(e: Element) -> bool:
    """判断是否为"章节性"元素:
    - 段落样式是 Heading/标题
    - 或文本短(<30)且匹配章节号正则
    """
    if not e or e.kind != "para":
        return False
    if HEADING_STYLE_PAT.match(e.style or ""):
        return True
    t = e.text or ""
    if len(t) >= 30:
        return False
    for _, pat in SECTION_NUM_RES:
        if pat.match(t):
            return True
    # 纯数字标题: "1 经营概况"
    if re.match(r"^\s*\d+\s+[\u4e00-\u9fa5]{2,15}$", t):
        return True
    return False


def build_section_index(all_elements: list[Element]) -> dict[str, list[str]]:
    """
    返回 location → [nearest_heading_texts(最近3层)] 的映射
    only 对 para 建立直接 section tree;cell 的 section 就用其所属 table 的前置标题
    """
    idx: dict[str, list[str]] = {}
    heading_stack: list[tuple[int, str]] = []  # (level, text)

    for e in all_elements:
        if e.kind == "para":
            # 尝试识别章节层级
            if _is_heading_like(e):
                level = 0
                for lvl, pat in SECTION_NUM_RES:
                    if pat.match(e.text):
                        level = lvl
                        break
                if level == 0 and HEADING_STYLE_PAT.match(e.style or ""):
                    m = re.search(r"(\d)", e.style or "")
                    level = int(m.group(1)) if m else 1
                # 弹栈同级或更深
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, e.text.strip()[:60]))

        idx[e.location] = [t for _, t in heading_stack[-3:]]

    return idx


# ────────────────────────────────────────────────────────────
# Prompt 构建
# ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """你是银行信贷报告"模板元素分类器"。
给定一批 element(段落或表格 cell),每个元素来自某份银行对公/普惠授信报告模板或历史成稿。
你要为每个 element 判断它在报告生成流水线中应归属的操作类型。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【3 种操作 op — 必须从下面三者中二选一或三选一】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• PRESERVE — 逐字保留原文不动。
  - 章节标题 / 章节编号 / 字段名标签 / 表头 / 单位说明 / 指引文字
  - 例: "一、授信客户基本情况"、"注册资本:"、"客户名称"、"单位:万元"、"如未落实请说明"

• FILL — 用当前客户的具体数值/短语替换,或按判定勾/叉复选框。有值就填;无值就留空并标 pending。
  - 字段取值部分:数字、日期、专有名词、短语
  - 复选框:根据客户档案判定是/否,勾选对应项
  - 纯占位符:下划线 / 空格 / "XX年XX月"

• REWRITE — 基于当前客户材料重写整段叙述性文字。
  - 正文段落、分析段、评价段、趋势描述、业务论述
  - 例: "公司主营智慧水利系统集成...该领域行业景气度持续提升"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【7 类细分 label — 用于下游路由决策】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• SCAFFOLD  (op=PRESERVE) — 骨架性保留:章节号/标题/字段标签/表头
• PRESERVE  (op=PRESERVE) — 说明性指引:"如涉及...""注:""备注:"
• FILL      (op=FILL)     — 有明确对应客户数据的字段取值(无对应材料时值为空)
• CLEAR     (op=FILL)     — 示例性但客户无对应数据(PD评级/申报单位/绿色信贷/银行方字段),清空+pending
• SLOT      (op=FILL)     — 纯占位符(下划线/连续空格/"(面积等)")
• CHECKBOX  (op=FILL)     — 复选框字段 "□XX;□YY" 结构,执行是勾/叉而非填值或清空
• REWRITE   (op=REWRITE)  — 叙述段落重写

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【判别规则 — 按优先级应用】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 独立行是"(一)1.①※"等章节编号/标题 → SCAFFOLD
2. 样式是 Heading/标题 N → SCAFFOLD
3. 文本**含 □ 或 ☐ 字符**(哪怕只有一个)→ CHECKBOX(执行逻辑:勾选符合客户的,其余打叉;不是清空)
4. 文本是"冒号结尾的短字段名"(注册资本:/法定代表人:) → 看紧邻右侧或下一 cell 来决定是 FILL 还是 CLEAR
5. 表格首行(header_row=true)多个短标题 → SCAFFOLD
6. 文本含纯占位符(≥4 连续下划线 / "____" / 连续空白 / "XX年XX月") → SLOT
7. 含具体数字 + 单位("4100 万元""2025年")且对应客户实际数据 → FILL
8. 含具体数字但字段属于"客户通常无"或"银行方"的类别 → CLEAR
9. 长度 >50 字、含自然语言叙述 → REWRITE
10. "如涉及/如未落实/请说明/可附图/注:/备注:/说明:" → PRESERVE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【字段归属区分 — 银行方 vs 客户方(极其重要)】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
有些字段的**主体是填报这份报告的银行/支行内部信息**,不是授信客户信息。
在没有"申报员档案"输入的情况下,这类字段一律判 CLEAR(清空+pending,等人工填)
绝对不可以用"当前客户档案"的公司名/地址/联系方式去填这类字段。

银行方字段(主体=银行,必须 CLEAR):
  - 申报单位、申报行、申报支行、经办行
  - 客户经理、联系电话(客户经理的)、客户经理所属部门
  - 授信审批岗、评议人、评议会、审批岗
  - 上一期授信敞口、上期批复意见、我行投向政策
  - 内部评级、白名单类型(由银行打标,不是客户)、PD 评级(由银行评,除非客户档案显式含评级)

识别线索:如文本含"我行""本行""支行""分行""客户经理""申报""评议""授信审批"等银行内部术语,
或字段名是"所属部门/联系电话/批复意见",即便 LLM 能从"当前客户档案"拼出像样的值,也必须 CLEAR。

客户方字段(主体=客户,正常 FILL):
  - 客户名称、注册资本、法人、实控人、主营、所属行业、经营地址
  - 营收、净利润、总资产、负债率(客户自身财务)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【当前假想客户档案】(用于判断 FILL 还是 CLEAR — 只对"客户方字段"适用)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
%CLIENT_PROFILE%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【输出格式 — 严格 JSON,不要 markdown,不要解释】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "classifications": [
    {
      "location": "T2R1C1P0",
      "op": "FILL",
      "label": "FILL",
      "confidence": 0.92,
      "justification": "字段取值=注册资本金额,客户档案有4100万对应"
    }
  ]
}

confidence 取值说明:
  0.95+ : 规则清晰,无歧义
  0.8+  : 规则适用,但有轻微噪声
  0.6+  : 存在歧义,凭 section 上下文判断
  <0.6  : 很不确定,标记 review
""".replace("%CLIENT_PROFILE%", json.dumps(CURRENT_CLIENT, ensure_ascii=False, indent=2))


def _fmt_element_for_prompt(i: int, e: dict, section: list[str]) -> str:
    """单元素格式化"""
    sec_line = " > ".join(section) if section else "(无上层章节)"
    flags = []
    if e.get("in_table"):
        flags.append("表格内")
    if e.get("is_header_row"):
        flags.append("表头行")
    if e.get("kind") == "cell":
        flags.append(f"row={e.get('row_idx', -1)}")
    style = e.get("style") or ""
    if style and style != "Normal":
        flags.append(f"style={style}")
    flag_str = " | ".join(flags) if flags else "-"
    text = e.get("text", "")
    if len(text) > 200:
        text = text[:200] + "...(截断)"
    return (
        f"{i}. location={e['location']}\n"
        f"   section={sec_line}\n"
        f"   flags={flag_str}\n"
        f"   text=「{text}」"
    )


def build_batch_user_message(source: str, batch_items: list[tuple[dict, list[str]]]) -> str:
    """batch_items: [(element_dict, section_chain)]"""
    lines = [
        f"【源文档】{source}",
        f"【批量大小】{len(batch_items)} 个元素",
        "",
        "【待分类元素】",
    ]
    for i, (e, sec) in enumerate(batch_items, 1):
        lines.append(_fmt_element_for_prompt(i, e, sec))
        lines.append("")
    lines.append("请为以上全部元素输出 classifications,数量与输入一致,顺序与输入一致。")
    return "\n".join(lines)


# ────────────────────────────────────────────────────────────
# 主流程
# ────────────────────────────────────────────────────────────
def main():
    print(f"[classifier] provider={CLASSIFIER_PROVIDER} temperature={CLASSIFIER_TEMPERATURE}")

    # 1) 加载 192 采样
    sampled = json.loads(SRC.read_text(encoding="utf-8"))
    samples: list[dict] = sampled["elements"]
    print(f"[classifier] loaded {len(samples)} sampled elements")

    # 2) 对每份源 docx 做全量抽取 + 建 section index
    section_by_loc: dict[tuple[str, str], list[str]] = {}
    sources_used = sorted(set(s["source"] for s in samples))
    for src_name in sources_used:
        src_path = SAMPLES_DIR / src_name
        if not src_path.exists():
            print(f"[WARN] source file missing: {src_path}", file=sys.stderr)
            continue
        all_elems = extract_elements(src_path)
        loc_to_section = build_section_index(all_elems)
        for loc, sec in loc_to_section.items():
            section_by_loc[(src_name, loc)] = sec
        print(f"[classifier] {src_name}: {len(all_elems)} total elements, sections built")

    # 3) 给每个采样挂上 section
    enriched: list[tuple[dict, list[str]]] = []
    for s in samples:
        sec = section_by_loc.get((s["source"], s["location"]), [])
        enriched.append((s, sec))

    # 4) 按 source 分组 batch
    BATCH_SIZE = 15
    grouped: dict[str, list[tuple[dict, list[str]]]] = defaultdict(list)
    for item in enriched:
        grouped[item[0]["source"]].append(item)

    # 5) 初始化 LLM
    llm = LLMClient(provider=CLASSIFIER_PROVIDER, cache_enabled=True)
    if not llm.api_key:
        print(f"[ERROR] 没找到 {CLASSIFIER_PROVIDER} 的 API key,无法分类", file=sys.stderr)
        sys.exit(1)
    print(f"[classifier] LLM ready: {llm.model}")

    # 6) 批量分类
    all_results: dict[str, dict] = {}  # location → classification
    errors: list[dict] = []
    t0 = time.time()

    for src, items in grouped.items():
        print(f"\n[classifier] === processing {src}: {len(items)} elements ===")
        for start in range(0, len(items), BATCH_SIZE):
            batch = items[start:start + BATCH_SIZE]
            batch_no = start // BATCH_SIZE + 1
            total_batches = (len(items) + BATCH_SIZE - 1) // BATCH_SIZE
            user_msg = build_batch_user_message(src, batch)
            print(f"  batch {batch_no}/{total_batches} (size={len(batch)})...", end=" ", flush=True)
            try:
                resp = llm.chat_json(
                    SYSTEM_PROMPT, user_msg,
                    temperature=CLASSIFIER_TEMPERATURE,
                    max_retries=2,
                )
                classifications = resp.get("classifications", []) if isinstance(resp, dict) else []
                if len(classifications) != len(batch):
                    print(f"mismatch: got {len(classifications)} vs expected {len(batch)}")
                    errors.append({
                        "source": src, "batch_no": batch_no,
                        "expected": len(batch), "got": len(classifications),
                    })
                # 按 location 对齐
                loc_to_cls = {c["location"]: c for c in classifications if isinstance(c, dict) and "location" in c}
                hit = 0
                for e, _sec in batch:
                    c = loc_to_cls.get(e["location"])
                    if c:
                        all_results[e["location"]] = c
                        hit += 1
                print(f"ok {hit}/{len(batch)} (cache={resp if isinstance(resp, dict) and resp.get('from_cache') else 'no'})")
            except Exception as ex:
                print(f"FAIL: {ex}")
                errors.append({
                    "source": src, "batch_no": batch_no,
                    "error": str(ex)[:200],
                })

    # 7) 保存
    out_payload = {
        "meta": {
            "provider": llm.provider,
            "model": llm.model,
            "temperature": CLASSIFIER_TEMPERATURE,
            "total_samples": len(samples),
            "total_classified": len(all_results),
            "elapsed_seconds": round(time.time() - t0, 1),
            "llm_stats": llm.get_stats(),
            "errors": errors,
        },
        "classifications_by_location": all_results,
    }
    OUT.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2),
                   encoding="utf-8")

    print(f"\n[done] {OUT}")
    print(f"  classified: {len(all_results)}/{len(samples)}")
    print(f"  elapsed: {out_payload['meta']['elapsed_seconds']}s")
    print(f"  llm stats: {llm.get_stats()}")
    if errors:
        print(f"  errors: {len(errors)} (见 out file)")


if __name__ == "__main__":
    main()
