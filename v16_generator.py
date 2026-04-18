# -*- coding: utf-8 -*-
"""V16 Generator — element-level docx 产出器.

输入:
  - classifier 产物: `outputs/v16_llm_classified.json`
    (每个 location → {op, label, confidence, justification})
  - 模板 docx: `samples/*.docx`
  - 材料目录: 一组客户资料(docx/xlsx/pdf/txt)
输出:
  - 填充后的 docx
  - pending_tags.json (未能自动填写的字段清单,供前端展示)

架构参见 plans/dapper-cuddling-cupcake.md。Step 1 范围:骨架 + dry-run round-trip。
"""
from __future__ import annotations

import glob
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from docx import Document

# 复用 v16 classifier 的 Element / section 索引
sys.path.insert(0, str(Path(__file__).parent))
from v16_classifier import build_section_index
from v16_step1_extract import Element, extract_elements

OUTPUT_DIR = Path(__file__).parent / "outputs"
DEFAULT_CLASSIFIED_JSON = OUTPUT_DIR / "v16_llm_classified.json"


# ────────────────────────────────────────────────────────────
# 数据结构
# ────────────────────────────────────────────────────────────

@dataclass
class Classification:
    """单个 element 的分类结果."""
    location: str
    op: str           # PRESERVE / FILL / REWRITE
    label: str        # SCAFFOLD / PRESERVE / FILL / CLEAR / SLOT / CHECKBOX / REWRITE
    confidence: float
    justification: str = ""


@dataclass
class Materials:
    """材料层 facade — 给 handler 统一消费接口.

    Step 1 仅作为占位;KB / financial / anchors 的实际加载在 Step 2+ 接入.
    """
    file_contents: dict[str, str] = field(default_factory=dict)
    kb: dict[str, Any] = field(default_factory=dict)
    financial: Any = None
    anchors: dict[str, Any] = field(default_factory=dict)
    index: Any = None

    @property
    def facts(self) -> dict[str, Any]:
        return self.kb.get("facts", {}) if self.kb else {}

    @property
    def tables(self) -> dict[str, Any]:
        return self.kb.get("tables", {}) if self.kb else {}


@dataclass
class GenResult:
    """单个 element 的处理结果.

    action:
      - keep  : 保留原文,不改 docx
      - fill  : 用 new_text 替换 element 的文本
      - clear : 清空为 空字符串 / pending 标签
    pending_tag: 若非 None,会写入 pending_tags.json
    """
    location: str
    action: str
    new_text: str | None = None
    pending_tag: dict[str, Any] | None = None
    debug: str = ""


# ────────────────────────────────────────────────────────────
# I/O
# ────────────────────────────────────────────────────────────

def load_classifier_output(json_path: Path) -> dict[str, Classification]:
    """读 classifier 产出的 JSON,返回 location → Classification."""
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    out: dict[str, Classification] = {}
    for loc, rec in data.get("classifications_by_location", {}).items():
        out[loc] = Classification(
            location=loc,
            op=rec.get("op", ""),
            label=rec.get("label", ""),
            confidence=float(rec.get("confidence", 0.0) or 0.0),
            justification=rec.get("justification", ""),
        )
    return out


def load_template(docx_path: Path) -> tuple[Any, list[Element], dict[str, list[str]]]:
    """读模板 docx,返回 (doc, elements, section_by_loc).

    - doc:  python-docx Document 对象(可直接修改)
    - elements: 按出现顺序的 Element 列表
    - section_by_loc: location → 最近 3 层 section 标题栈
    """
    doc = Document(str(docx_path))
    elements = extract_elements(Path(docx_path))
    section_by_loc = build_section_index(elements)
    return doc, elements, section_by_loc


def load_materials(material_dir: Path | None) -> Materials:
    """读材料目录.

    Step 1: 仅加载 file_contents(文件名 → 纯文本),不做 KB 构建.
    Step 2+: 在此基础上延迟构建 kb / financial / anchors.
    """
    if material_dir is None or not Path(material_dir).exists():
        return Materials()

    # 延迟 import 避免 Step 1 强依赖 tools 整个模块
    from tools import _read_single_file

    exts = {".txt", ".docx", ".doc", ".pdf", ".xlsx", ".xls"}
    file_contents: dict[str, str] = {}
    for fp in glob.glob(os.path.join(str(material_dir), "*")):
        ext = os.path.splitext(fp)[1].lower()
        if ext not in exts:
            continue
        try:
            content = _read_single_file(fp)
            if content:
                file_contents[os.path.basename(fp)] = content
        except Exception as e:
            print(f"  [skip] {os.path.basename(fp)}: {e}")

    return Materials(file_contents=file_contents)


# ────────────────────────────────────────────────────────────
# 预处理:section 分组 / body-gap 检测(Step 5 实装,此处仅留钩子)
# ────────────────────────────────────────────────────────────

def _index_elements_by_location(elements: list[Element]) -> dict[str, Element]:
    return {e.location: e for e in elements}


def _group_rewrite_by_section(
    elements: list[Element],
    classifications: dict[str, Classification],
    section_by_loc: dict[str, list[str]],
) -> dict[tuple[str, ...], list[Element]]:
    """将 op==REWRITE 的 element 按 section heading 栈分组,准备合批处理."""
    groups: dict[tuple[str, ...], list[Element]] = {}
    for e in elements:
        cls = classifications.get(e.location)
        if not cls or cls.op != "REWRITE":
            continue
        sec_key = tuple(section_by_loc.get(e.location, []))
        groups.setdefault(sec_key, []).append(e)
    return groups


# ────────────────────────────────────────────────────────────
# Dry-run:验证 classifier 输出与 docx element round-trip
# ────────────────────────────────────────────────────────────

def dry_run(
    classified_json: Path,
    template_docx: Path,
    material_dir: Path | None = None,
    max_print: int = 40,
) -> dict[str, Any]:
    """把 classifier 输出与 docx element 对齐一次,打印前 N 条.

    返回统计:命中率、op/label 分布、section 分组数.
    """
    print(f"[v16_generator.dry_run] classified_json={classified_json.name}")
    print(f"                        template_docx ={template_docx.name}")
    classifications = load_classifier_output(classified_json)
    doc, elements, section_by_loc = load_template(template_docx)
    mats = load_materials(material_dir)
    print(f"  classifications: {len(classifications)}")
    print(f"  template elements: {len(elements)}")
    print(f"  material files loaded: {len(mats.file_contents)}")

    # 命中统计
    el_by_loc = _index_elements_by_location(elements)
    cls_locs = set(classifications.keys())
    elem_locs = set(el_by_loc.keys())
    hit = cls_locs & elem_locs
    only_cls = cls_locs - elem_locs
    only_elem = elem_locs - cls_locs
    print(f"  ├ loc 命中:  {len(hit)} / {len(cls_locs)} = "
          f"{(len(hit) / max(len(cls_locs), 1)) * 100:.1f}%")
    print(f"  ├ 只在 classifier 出现: {len(only_cls)} (跨文档的 element)")
    print(f"  └ 只在 template 出现:   {len(only_elem)} (classifier 未覆盖)")

    # op / label 分布
    op_dist: dict[str, int] = {}
    lab_dist: dict[str, int] = {}
    for loc in hit:
        c = classifications[loc]
        op_dist[c.op] = op_dist.get(c.op, 0) + 1
        lab_dist[c.label] = lab_dist.get(c.label, 0) + 1
    print(f"  op 分布:    {dict(sorted(op_dist.items()))}")
    print(f"  label 分布: {dict(sorted(lab_dist.items()))}")

    # REWRITE 分组
    rw_groups = _group_rewrite_by_section(elements, classifications, section_by_loc)
    print(f"  REWRITE 分组: {len(rw_groups)} 个 section")
    for i, (sec, items) in enumerate(list(rw_groups.items())[:5]):
        head = sec[-1] if sec else "<root>"
        print(f"    └ [{i+1}] {head[:30]}  ({len(items)} elems)")

    # 逐条打印前 N
    print(f"\n  [sample] 前 {max_print} 条 (location, op, label, text):")
    print("  " + "-" * 100)
    count = 0
    for e in elements:
        if e.location not in classifications:
            continue
        c = classifications[e.location]
        text_preview = (e.text or "").replace("\n", " ")[:50]
        print(f"    {e.location:20}  {c.op:8}/{c.label:9}  {text_preview}")
        count += 1
        if count >= max_print:
            break

    return {
        "classifications": len(classifications),
        "elements": len(elements),
        "hit": len(hit),
        "only_cls": len(only_cls),
        "only_elem": len(only_elem),
        "op_dist": op_dist,
        "label_dist": lab_dist,
        "rewrite_groups": len(rw_groups),
    }


# ────────────────────────────────────────────────────────────
# Entry
# ────────────────────────────────────────────────────────────

def _pick_template_for(docx_name: str, samples_dir: Path) -> Path:
    return samples_dir / docx_name


def main():
    """Dry-run 入口:逐个 sample docx 验证 round-trip.

    用法:
        py -u v16_generator.py                    # 跑 3 个 sample 全部
        py -u v16_generator.py 经纬测绘_对公成稿A   # 只跑一个
    """
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    samples_dir = Path(__file__).parent / "samples"
    if not DEFAULT_CLASSIFIED_JSON.exists():
        print(f"[err] classifier 输出不存在: {DEFAULT_CLASSIFIED_JSON}")
        sys.exit(1)

    candidates = sorted(samples_dir.glob("*.docx"))
    if len(sys.argv) > 1:
        key = sys.argv[1]
        candidates = [p for p in candidates if key in p.stem]

    for docx in candidates:
        print("\n" + "=" * 80)
        print(f"Template: {docx.name}")
        print("=" * 80)
        dry_run(
            classified_json=DEFAULT_CLASSIFIED_JSON,
            template_docx=docx,
            material_dir=None,
            max_print=30,
        )


if __name__ == "__main__":
    main()
