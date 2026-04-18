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
import re
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
    """读材料目录,构建 KB.

    Step 2: 加载 file_contents + build_material_kb。
    Step 4+: 延迟接入 financial / anchors / index。
    """
    if material_dir is None or not Path(material_dir).exists():
        return Materials()

    # 延迟 import 避免 Step 1 强依赖 tools 整个模块
    from tools import _read_single_file
    from material_kb import build_material_kb

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

    kb = build_material_kb(file_contents) if file_contents else {}
    return Materials(file_contents=file_contents, kb=kb)


# ────────────────────────────────────────────────────────────
# docx location → element 解析(写回 docx 时用)
# ────────────────────────────────────────────────────────────

def _resolve_docx_elements(doc, location: str) -> list:
    """把 location 字符串解析到 docx Paragraph 列表.

    支持:
      - P{n}           → [doc.paragraphs[n]]
      - T{t}R{r}C{c}P{p}            → [cell 内第 p 个 paragraph]
      - T{t}R{r}C{c}NTR{r2}C{c2}P{p} → 父 cell 下所有子表里对应 (r2,c2,p) 的
        paragraph 列表(extract_elements 对同 cell 多张子表共用相同 NT location,
        resolve 时对所有匹配子表都返回,由 apply 层统一处理)
    """
    # 简单段落
    m = re.match(r"^P(\d+)$", location)
    if m:
        pi = int(m.group(1))
        if 0 <= pi < len(doc.paragraphs):
            return [doc.paragraphs[pi]]
        return []

    m = re.match(r"^T(\d+)(.+)$", location)
    if not m:
        return []
    t_idx = int(m.group(1))
    rest = m.group(2)
    if t_idx >= len(doc.tables):
        return []

    # 候选 cell 集合(支持 NT 层多分支)
    current_cells = [None]  # 占位,第一步用 doc.tables[t_idx]
    current_tables = [doc.tables[t_idx]]

    cursor = 0
    while cursor < len(rest):
        mm = re.match(r"^(NT)?R(\d+)C(\d+)", rest[cursor:])
        if not mm:
            break
        is_nt, r_idx, c_idx = bool(mm.group(1)), int(mm.group(2)), int(mm.group(3))

        next_cells = []
        if is_nt:
            # 展开所有当前 cell 下的子表为新 tables
            next_tables = []
            for cell in current_cells:
                if cell is None:
                    continue
                for sub in cell.tables:
                    next_tables.append(sub)
            current_tables = next_tables
            current_cells = []

        for tbl in current_tables:
            if r_idx >= len(tbl.rows):
                continue
            row = tbl.rows[r_idx]
            if c_idx >= len(row.cells):
                continue
            next_cells.append(row.cells[c_idx])

        current_cells = next_cells
        # 下一轮的 tables 默认继承(若下一段又是 NT,再重新展开)
        current_tables = [] if not current_cells else [c for c in current_cells if c is not None]
        cursor += mm.end()

    mp = re.match(r"^P(\d+)$", rest[cursor:])
    if not mp:
        return []
    p_idx = int(mp.group(1))
    out = []
    for cell in current_cells:
        if cell is None or p_idx >= len(cell.paragraphs):
            continue
        out.append(cell.paragraphs[p_idx])
    return out


def _resolve_docx_element(doc, location: str):
    """兼容 API: 返回第一个匹配(无则 None)."""
    lst = _resolve_docx_elements(doc, location)
    return lst[0] if lst else None


def _set_paragraph_text(para, new_text: str) -> None:
    """在保留 run 格式的前提下,把 paragraph 文本替换为 new_text.

    策略:第一个 run 写全部文本,其余 run 清空。若 para 完全无 runs 则 add_run。
    """
    runs = para.runs
    if not runs:
        para.add_run(new_text)
        return
    runs[0].text = new_text
    for r in runs[1:]:
        r.text = ""
    # 若 add_run 在父结构存在 field/hyperlink 干扰,保险地用 _p 检查一次
    if not para.text:
        # runs 写入未成功(罕见 case),追加 run 兜底
        para.add_run(new_text)


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
# 核心:用 handler 跑完整流程
# ────────────────────────────────────────────────────────────

def apply_to_docx(doc, results: list["GenResult"]) -> dict[str, int]:
    """把 handler 产物写回 doc.

    每个 GenResult 的 location 可能对应多个 paragraph(NT 共用 location 的场景),
    此时对所有匹配 paragraph 都应用同一结果(语义等价的子表统一处理).
    Returns: {"fill": n, "keep": n, "clear": n, "miss": n} 统计
    """
    stats = {"fill": 0, "keep": 0, "clear": 0, "miss": 0}
    for r in results:
        if r.action == "keep":
            stats["keep"] += 1
            continue
        paras = _resolve_docx_elements(doc, r.location)
        if not paras:
            stats["miss"] += 1
            continue
        for para in paras:
            if r.action == "clear":
                _set_paragraph_text(para, "")
                stats["clear"] += 1
            elif r.action == "fill":
                _set_paragraph_text(para, r.new_text or "")
                stats["fill"] += 1
    return stats


def generate(
    classified_json: Path,
    template_docx: Path,
    material_dir: Path | None,
    output_docx: Path,
) -> dict[str, Any]:
    """V16 主入口:按 classifier 路由处理所有 element,写回 docx.

    Step 2 范围: PRESERVE/*、FILL/FILL、FILL/CLEAR、FILL/CHECKBOX 走确定性 handler;
                 FILL/SLOT、REWRITE/REWRITE 暂走 _not_impl(保留原状).
    """
    # 延迟 import handler(它依赖 v16_generator 的 GenResult)
    from v16_op_handlers import dispatch

    print(f"[v16_generator.generate] {template_docx.name}")
    classifications = load_classifier_output(classified_json)
    doc, elements, section_by_loc = load_template(template_docx)
    mats = load_materials(material_dir)
    print(f"  classifier: {len(classifications)} loc / template: {len(elements)} elems"
          f" / materials: {len(mats.file_contents)} files")
    if mats.kb:
        print(f"  KB facts: {len(mats.facts)}")

    # 对每个有分类的 element 调 dispatch
    results: list[GenResult] = []
    pending_tags: list[dict[str, Any]] = []
    handler_stats: dict[str, int] = {}

    for elem in elements:
        cls = classifications.get(elem.location)
        if cls is None:
            continue
        r = dispatch(elem, cls, mats)
        results.append(r)
        if r.pending_tag:
            pending_tags.append(r.pending_tag)
        key = f"{cls.op}/{cls.label}"
        handler_stats[key] = handler_stats.get(key, 0) + 1

    apply_stats = apply_to_docx(doc, results)
    doc.save(str(output_docx))

    # 导出 pending tags
    pending_path = output_docx.with_name(output_docx.stem + "_pending.json")
    pending_path.write_text(
        json.dumps({"pending_tags": pending_tags}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"  dispatch 分布: {dict(sorted(handler_stats.items()))}")
    print(f"  apply 统计: {apply_stats}")
    print(f"  pending tags: {len(pending_tags)}")
    print(f"  └ output: {output_docx}")
    print(f"  └ pending: {pending_path}")

    return {
        "handler_stats": handler_stats,
        "apply_stats": apply_stats,
        "pending_count": len(pending_tags),
        "output_docx": str(output_docx),
        "pending_json": str(pending_path),
    }


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
    """入口:

        py -u v16_generator.py                       # dry-run 3 samples
        py -u v16_generator.py 经纬测绘_对公成稿A      # dry-run 特定 sample
        py -u v16_generator.py --run                  # 生成 3 docx
        py -u v16_generator.py --run 普惠             # 生成特定 sample

    --run 下若提供 --material=DIR,会加载 KB;否则 KB 为空,FILL/FILL 全部 pending。
    """
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    samples_dir = Path(__file__).parent / "samples"
    if not DEFAULT_CLASSIFIED_JSON.exists():
        print(f"[err] classifier 输出不存在: {DEFAULT_CLASSIFIED_JSON}")
        sys.exit(1)

    do_run = "--run" in sys.argv
    material_dir = None
    for a in sys.argv:
        if a.startswith("--material="):
            material_dir = Path(a.split("=", 1)[1])

    key_args = [a for a in sys.argv[1:] if not a.startswith("--")]
    candidates = sorted(samples_dir.glob("*.docx"))
    if key_args:
        candidates = [p for p in candidates if any(k in p.stem for k in key_args)]

    for docx in candidates:
        print("\n" + "=" * 80)
        print(f"Template: {docx.name}")
        print("=" * 80)
        if do_run:
            out = OUTPUT_DIR / f"{docx.stem}_v16.docx"
            generate(
                classified_json=DEFAULT_CLASSIFIED_JSON,
                template_docx=docx,
                material_dir=material_dir,
                output_docx=out,
            )
        else:
            dry_run(
                classified_json=DEFAULT_CLASSIFIED_JSON,
                template_docx=docx,
                material_dir=material_dir,
                max_print=30,
            )


if __name__ == "__main__":
    main()
