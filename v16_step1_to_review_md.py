# -*- coding: utf-8 -*-
"""V16 Step 1: labeled json → review-friendly markdown."""
import json
from pathlib import Path
from collections import defaultdict

SRC = Path(__file__).parent / "outputs" / "v16_labeled_elements.json"
OUT = Path(__file__).parent / "outputs" / "v16_REVIEW_ME.md"

data = json.load(SRC.open(encoding="utf-8"))
elems = data["elements"]

by_label = defaultdict(list)
for e in elems:
    by_label[e["label"]].append(e)

LABEL_DESC = {
    "SCAFFOLD": "骨架 保留原文",
    "FILL":     "有客户数据 代码填",
    "CLEAR":    "示例无数据 清空+pending",
    "REWRITE":  "正文 LLM 整段重写",
    "SLOT":     "占位槽位",
    "PRESERVE": "指引保留",
}
ORDER = ["SCAFFOLD", "FILL", "CLEAR", "REWRITE", "SLOT", "PRESERVE"]

lines = []
lines.append("# V16 Step 1 — 200 条 element 标注,请 review\n")
lines.append("**假想当前客户**:福建中锐网络股份有限公司(黄祖海实控,智慧水利+智慧教育,注册资本 4100 万)\n")
lines.append("## 标签说明\n")
for lab in ORDER:
    lines.append(f"- **`{lab}`** — {LABEL_DESC[lab]}")
lines.append("\n## Review 说明\n")
lines.append("- 每条 element 如果**标对了** → 跳过\n")
lines.append("- 如果**标错了** → 在该行末尾用 `→ 应该是 {正确标签}` 写原因,或直接划掉\n")
lines.append("- 重点 review **置信度 <0.7 的(标 ⚠)**,高置信的快扫即可\n")
lines.append("- 如果样本**根本不该抽进来**(坏样本),标 `SKIP`\n")
lines.append("\n---\n")

for lab in ORDER:
    items = by_label.get(lab, [])
    lines.append(f"\n## `{lab}` ({len(items)} 条)\n")
    lines.append("| # | confidence | source | location | text | justification |")
    lines.append("|---|---|---|---|---|---|")
    for i, e in enumerate(items, 1):
        conf_mark = "⚠" if e["confidence"] < 0.7 else ""
        src_short = e["source"].replace("_对公成稿", "").replace("_骨架型", "")[:12]
        text = (e["text"] or "").replace("|", "丨").replace("\n", " ")[:100]
        just = (e["justification"] or "").replace("|", "丨")[:80]
        lines.append(f"| {i} | {conf_mark}{e['confidence']:.2f} | {src_short} | {e['location']} | {text} | {just} |")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"[done] {OUT}")
print(f"  总样本: {len(elems)}")
print(f"  低置信(⚠): {sum(1 for e in elems if e['confidence'] < 0.7)}")
print(f"  文件大小: {OUT.stat().st_size} bytes")
