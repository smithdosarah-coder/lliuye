# -*- coding: utf-8 -*-
"""Agent6 (报告生成) ↔ Agent3 (授信决策) 的数据契约与串联工具。

数据流：
  Agent6 写完 docx → dump_report_json() 同时产出 ReportJSON
    → Agent3 消费 ReportJSON 做决策
    → Agent3 调 apply_decision_writeback() 回填审批意见到 Word
"""

from __future__ import annotations
import json
import os
import re
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"


# ========== ReportJSON 结构 ==========

REPORT_JSON_SCHEMA_VERSION = "1.0"


def _safe_name(name: str) -> str:
    return "".join(c for c in (name or "report") if c.isalnum() or c in "_-")[:24]


def dump_report_json(
    client_name: str,
    sections: dict,
    docx_path: str | Path = "",
    template_path: str | Path = "",
    extras: dict | None = None,
) -> str:
    """在 outputs/ 目录产出 Agent3 可消费的 ReportJSON。

    返回 JSON 路径（字符串）。Agent3 用 `from_json()` 读。
    """
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = _safe_name(client_name)
    path = OUTPUTS_DIR / f"{safe}_{ts}_report.json"

    payload = {
        "schema_version": REPORT_JSON_SCHEMA_VERSION,
        "client_name": client_name or "",
        "generated_at": datetime.now().isoformat(),
        "source_docx": str(docx_path) if docx_path else "",
        "source_template": str(template_path) if template_path else "",
        "sections": {
            "ch1": sections.get("ch1", "") or "",
            "ch2": sections.get("ch2", "") or "",
            "ch3": sections.get("ch3", "") or "",
            "ch4": sections.get("ch4", "") or "",
        },
        # 从章节正文提取的轻量结构化摘要，给 Agent3 FeatureExtractor 当快速入口
        "facts": _extract_facts_from_sections(sections),
        "extras": extras or {},
    }

    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(path)


def _extract_facts_from_sections(sections: dict) -> dict:
    """从 4 章正文正则抽取关键事实（轻量，不替代 Agent3 的 FeatureExtractor）。"""
    text = "\n".join(sections.get(f"ch{i}", "") or "" for i in range(1, 5))
    facts = {}

    def _grab(pattern: str, group: int = 1) -> str:
        m = re.search(pattern, text)
        return m.group(group).strip() if m else ""

    facts["industry"] = _grab(r"行业[：:]\s*([^\n，,。]+)")
    facts["establishment_date"] = _grab(r"(?:成立日期|注册日期)[：:]\s*([0-9年月日/\- ]+)")
    facts["registered_capital"] = _grab(r"注册资本[：:]\s*([^\n，,。]+)")
    facts["legal_representative"] = _grab(r"法定代表人[：:]\s*([^\s\n，,。]+)")
    facts["credit_amount_requested"] = _grab(r"(?:本次?申请授信额度|申请授信额度|申请额度)[：:]?\s*([0-9,.]+\s*[万亿元]+)")
    facts["term_requested"] = _grab(r"(?:期限|授信期限)[：:]\s*([0-9]+\s*年)")
    facts["revenue_latest"] = _grab(r"营业收入[：:]\s*([0-9,.]+\s*[万亿元]+)")
    facts["profit_latest"] = _grab(r"(?:净利润|利润)[：:]\s*([0-9,.\-]+\s*[万亿元]+)")
    return {k: v for k, v in facts.items() if v}


def load_report_json(json_path: str | Path) -> dict:
    p = Path(json_path)
    return json.loads(p.read_text(encoding="utf-8"))


# ========== 决策回写：Agent3 → Agent6 ==========

def apply_decision_writeback(
    report_json_path: str | Path,
    decision_text: str,
    decision_meta: dict | None = None,
) -> str:
    """用 Agent3 产出的决策意见回写 Word 报告。

    流程：
      1. 读 ReportJSON 拿到 sections 和 template_path
      2. 把 decision_text 追加到 ch4（审批意见章节）
      3. 调 word_export.make_word_from_template 生成 `{original}_decided.docx`
      4. 返回新 docx 路径
    """
    payload = load_report_json(report_json_path)
    sections = payload.get("sections", {}).copy()
    template_path = payload.get("source_template") or ""
    client_name = payload.get("client_name", "")

    decision_meta = decision_meta or {}

    # 组装审批意见块
    appendix = ["", "", "—" * 20, "【授信决策意见（Agent3 辅助生成）】"]
    if decision_meta:
        for k, v in decision_meta.items():
            appendix.append(f"- {k}: {v}")
    appendix.append("")
    appendix.append(decision_text.strip())

    existing_ch4 = sections.get("ch4", "") or ""
    sections["ch4"] = existing_ch4 + "\n" + "\n".join(appendix)

    # 调 word_export
    import sys
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    if template_path and Path(template_path).exists():
        from word_export import make_word_from_template
        docx_path = make_word_from_template(template_path, sections, client_name=client_name)
    else:
        from word_export import make_word_report
        docx_path = make_word_report(client_name, "", "", "", "", "", sections)

    # 重命名为 _decided.docx 放到 outputs/
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = OUTPUTS_DIR / f"{_safe_name(client_name)}_{ts}_decided.docx"
    try:
        import shutil
        shutil.copy2(docx_path, str(target))
        return str(target)
    except Exception:
        return docx_path


def list_available_reports() -> list[dict]:
    """列出 outputs/ 下所有可供 Agent3 消费的 ReportJSON。"""
    if not OUTPUTS_DIR.exists():
        return []
    out = []
    for p in sorted(OUTPUTS_DIR.glob("*_report.json"), key=os.path.getmtime, reverse=True):
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
            out.append({
                "path": str(p),
                "client_name": payload.get("client_name", ""),
                "generated_at": payload.get("generated_at", ""),
                "filename": p.name,
            })
        except Exception:
            continue
    return out
