# -*- coding: utf-8 -*-
"""V16 Classifier 自一致性检查.

策略:
  从 192 个已分类样本里分层抽 30 条(每个 label 5 条),重跑一次.
  关键:与首次使用不同 batch 分组(不同 user_msg hash),绕过 cache.
  如果同元素两次输出 op/label 一致 → 分类器稳定(temperature=0 有效)

输出: outputs/v16_self_consistency.md
"""
from __future__ import annotations

import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from v16_classifier import (
    SYSTEM_PROMPT, build_batch_user_message, extract_elements,
    build_section_index, SAMPLES_DIR,
)
from llm import LLMClient
from config import CLASSIFIER_PROVIDER, CLASSIFIER_TEMPERATURE

SAMPLES_JSON = Path(__file__).parent / "outputs" / "v16_labeled_elements.json"
LLM_JSON = Path(__file__).parent / "outputs" / "v16_llm_classified.json"
OUT = Path(__file__).parent / "outputs" / "v16_self_consistency.md"

random.seed(17)


def main():
    samples = json.loads(SAMPLES_JSON.read_text(encoding="utf-8"))["elements"]
    first_run = json.loads(LLM_JSON.read_text(encoding="utf-8"))["classifications_by_location"]

    # 1) 按 label 分层抽 5 个
    by_label: dict[str, list[dict]] = defaultdict(list)
    for s in samples:
        by_label[s["label"]].append(s)
    picked: list[dict] = []
    for lab, lst in by_label.items():
        random.shuffle(lst)
        picked.extend(lst[:5])
    print(f"[consistency] picked {len(picked)} samples (stratified)")

    # 2) 重建 section index
    section_by_loc: dict[tuple[str, str], list[str]] = {}
    for src_name in sorted(set(s["source"] for s in picked)):
        all_elems = extract_elements(SAMPLES_DIR / src_name)
        for loc, sec in build_section_index(all_elems).items():
            section_by_loc[(src_name, loc)] = sec

    # 3) 用 cache_enabled=False + 不同 batch 分组 → 绕过 cache
    llm = LLMClient(provider=CLASSIFIER_PROVIDER, cache_enabled=False)
    BATCH = 10  # 首次是 15,这次用 10 → batch 内组成不同 → user_msg hash 不同

    # 按 source 分组并组成新 batch
    by_src: dict[str, list[tuple[dict, list[str]]]] = defaultdict(list)
    for s in picked:
        sec = section_by_loc.get((s["source"], s["location"]), [])
        by_src[s["source"]].append((s, sec))

    second_run: dict[str, dict] = {}
    t0 = time.time()
    for src, items in by_src.items():
        for start in range(0, len(items), BATCH):
            batch = items[start:start + BATCH]
            user_msg = build_batch_user_message(src, batch)
            print(f"  [{src}] batch {start//BATCH+1} size={len(batch)}...", end=" ", flush=True)
            resp = llm.chat_json(SYSTEM_PROMPT, user_msg,
                                 temperature=CLASSIFIER_TEMPERATURE, max_retries=2)
            for c in resp.get("classifications", []):
                if "location" in c:
                    second_run[c["location"]] = c
            print(f"ok ({len(resp.get('classifications', []))})")

    # 4) 对比
    op_match = 0
    lab_match = 0
    total = 0
    detail_rows = []
    for s in picked:
        first = first_run.get(s["location"], {})
        second = second_run.get(s["location"], {})
        if not first or not second:
            continue
        total += 1
        f_op = first.get("op", "")
        f_lab = first.get("label", "")
        s_op = second.get("op", "")
        s_lab = second.get("label", "")
        op_ok = (f_op == s_op)
        lab_ok = (f_lab == s_lab)
        if op_ok:
            op_match += 1
        if lab_ok:
            lab_match += 1
        text = (s["text"] or "")[:30].replace("|", "丨").replace("\n", " ")
        mark_op = "✓" if op_ok else "✗"
        mark_lab = "✓" if lab_ok else "✗"
        detail_rows.append(
            (op_ok, lab_ok, s['location'], text, f_op, f_lab, s_op, s_lab, mark_op, mark_lab)
        )

    op_rate = (op_match / total * 100) if total else 0
    lab_rate = (lab_match / total * 100) if total else 0

    report_lines = [
        f"# V16 Classifier 自一致性报告",
        "",
        f"- provider: `{llm.provider}` / model: `{llm.model}`",
        f"- temperature: {CLASSIFIER_TEMPERATURE}",
        f"- 抽样: 每 label 5 条,共 {len(picked)} 条",
        f"- 首次分类来自 `v16_llm_classified.json`,本次重跑绕过 cache",
        "",
        f"## 核心指标",
        "",
        f"- **op 级自一致率: {op_match}/{total} = {op_rate:.1f}%** (决定下游执行路由)",
        f"- **label 级自一致率: {lab_match}/{total} = {lab_rate:.1f}%** (决定 UI 细粒度显示)",
        "",
        f"## 结论",
        "",
        ("✅ op 级 ≥95% → 下游执行层稳定,可以进入 generator 开发" if op_rate >= 95
         else f"⚠️ op 级 {op_rate:.1f}% <95% → 需加强 prompt 在歧义场景的决策"),
        "",
        "label 级低于 op 级是正常的 — 因为 SCAFFOLD/PRESERVE、FILL/SLOT 等是精细子分类,op 一致时 label 轻微漂移不影响执行。",
        "",
        "## 对比明细",
        "",
        "| 位置 | 文本 | 首次 op/label | 二次 op/label | op一致 | label一致 |",
        "|---|---|---|---|---|---|",
    ]
    # 先列 op 不一致的(严重),再列 label 不一致 op 一致的(轻),最后一致的
    detail_rows.sort(key=lambda r: (r[0], r[1]))
    for op_ok, lab_ok, loc, text, fo, fl, so, sl, mo, ml in detail_rows:
        report_lines.append(f"| {loc} | {text} | {fo}/{fl} | {so}/{sl} | {mo} | {ml} |")
    OUT.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\n[done] {OUT}")
    print(f"  op 级自一致率: {op_match}/{total} = {op_rate:.1f}%")
    print(f"  label 级自一致率: {lab_match}/{total} = {lab_rate:.1f}%")
    print(f"  耗时: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
