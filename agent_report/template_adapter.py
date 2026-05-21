# -*- coding: utf-8 -*-
"""Agent6 · Template Adapter(Phase 2 Task C)

职责:把不同来源/不同形态的模板归一为 TemplateProfile,供下游 truth_fill /
section_generator / quality_blocker 按模板特性走差异化路径。

支持的模板形态(2026-04-19):
  - 普惠申报书_骨架型.docx        scenario=inclusive_skeleton (基线 v7.23)
  - 兴业资管_对公成稿B.docx        scenario=corporate_long_form
  - 经纬测绘_对公成稿A.docx        scenario=corporate_long_form
  - 科创贷申报书_模板.docx         scenario=tech_credit (Phase 2 新增)
  - 小微对私授信申报书_模板.docx    scenario=micro_personal (Phase 2 新增)

CLAUDE.md §3.2:新增工具必须归入业务子域 → 本模块属 Agent6.材料解析域;
                按 scenario 路由,不在域内直接调其他域的内部实现。

不修改:evaluation/runner/adapters/agent6_report.py(红区);
       本 adapter 仅负责"识别 + 元信息归一",不替代 runner adapter。

DoD: L3-12(模板覆盖度,≥2 银行模板)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ============================================================================
# 数据结构
# ============================================================================


@dataclass
class TemplateProfile:
    """模板元信息归一对象,供下游一致性消费。"""

    scenario: str                 # tech_credit | micro_personal | corporate_long_form | inclusive_skeleton | unknown
    business_line: str            # corporate | inclusive | reserved | personal
    template_path: str            # 原 docx 路径
    template_name: str            # 原 docx 文件名
    field_density: str            # skeleton(骨架型≥300字段) | narrative(长文型≤30字段)
    expected_qc_floor: float      # 该模板预期 QC 下限(用于回归基线设定)
    feature_flags: dict[str, bool] = field(default_factory=dict)
    routing_hints: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "business_line": self.business_line,
            "template_path": self.template_path,
            "template_name": self.template_name,
            "field_density": self.field_density,
            "expected_qc_floor": self.expected_qc_floor,
            "feature_flags": dict(self.feature_flags),
            "routing_hints": dict(self.routing_hints),
        }


# ============================================================================
# 识别规则(治本式:用文件名 + 内容关键词,不写硬编 if-else 黑名单)
# ============================================================================


_SCENARIO_RULES: list[tuple[str, str, list[re.Pattern]]] = [
    # 文件名强信号优先(corporate_long_form / inclusive_skeleton)
    (
        "corporate_long_form",
        "corporate",
        [
            re.compile(r"对公成稿|成稿"),
            re.compile(r"经纬测绘|兴业资管"),
        ],
    ),
    (
        "inclusive_skeleton",
        "inclusive",
        [
            re.compile(r"普惠.*骨架|骨架.*普惠|普惠申报书"),
        ],
    ),
    # 内容专属信号(科创贷 / 小微对私)
    (
        "tech_credit",
        "corporate",
        [
            re.compile(r"科创|科技创新|高新认定|研发投入强度|发明专利"),
        ],
    ),
    (
        "micro_personal",
        "personal",
        [
            re.compile(r"小微.*对私|对私.*小微|个人授信|消费贷"),
            re.compile(r"DSR|身份证号|月均收入|家庭年收入"),
        ],
    ),
]


_DEFAULT_QC_FLOOR = {
    "tech_credit": 86.0,
    "micro_personal": 82.0,
    "corporate_long_form": 88.0,
    "inclusive_skeleton": 88.5,
    "unknown": 75.0,
}


def _read_docx_text(path: Path, max_chars: int = 4000) -> str:
    try:
        from docx import Document
    except Exception:
        return ""
    try:
        doc = Document(str(path))
    except Exception:
        return ""
    parts: list[str] = []
    total = 0
    for p in doc.paragraphs:
        t = (p.text or "").strip()
        if not t:
            continue
        parts.append(t)
        total += len(t)
        if total >= max_chars:
            break
    return "\n".join(parts)


def _count_field_markers(text: str) -> int:
    """粗略计数模板字段标记(下划线 / 中括号 / 复选框)。"""
    n = 0
    n += len(re.findall(r"_{4,}", text))
    n += len(re.findall(r"\[\s*\]", text))
    n += len(re.findall(r"\(\s*\)", text))
    return n


def _classify_scenario(name: str, text: str) -> tuple[str, str]:
    haystack = f"{name}\n{text}"
    for scenario, biz_line, patterns in _SCENARIO_RULES:
        if any(p.search(haystack) for p in patterns):
            return scenario, biz_line
    return "unknown", "reserved"


def detect_template(path: str | Path) -> TemplateProfile:
    """主入口:读 docx → 识别 scenario → 归一 TemplateProfile。"""
    p = Path(path)
    name = p.name
    text = _read_docx_text(p) if p.suffix.lower() == ".docx" else ""
    scenario, biz_line = _classify_scenario(name, text)
    field_count = _count_field_markers(text)
    density = "skeleton" if field_count >= 30 else "narrative"
    qc_floor = _DEFAULT_QC_FLOOR.get(scenario, _DEFAULT_QC_FLOOR["unknown"])
    flags: dict[str, bool] = {
        "needs_financial_anchor": scenario in {
            "tech_credit", "corporate_long_form", "inclusive_skeleton"
        },
        "needs_credit_query_breakdown": scenario == "micro_personal",
        "needs_rd_intensity_check": scenario == "tech_credit",
        "personal_data_grade_core": scenario == "micro_personal",
    }
    routing_hints: dict[str, Any] = {
        "field_density": density,
        "field_marker_count": field_count,
        "preferred_pipeline": (
            "v15_narrative" if density == "narrative" else "v14_skeleton"
        ),
    }
    return TemplateProfile(
        scenario=scenario,
        business_line=biz_line,
        template_path=str(p),
        template_name=name,
        field_density=density,
        expected_qc_floor=qc_floor,
        feature_flags=flags,
        routing_hints=routing_hints,
    )


# ============================================================================
# 2026-05-21 治本 Phase 1: client_metadata 解析 · placeholder 化路径专用
# ============================================================================


def _load_json_if_exists(path: Path) -> dict | None:
    """读 path 的 JSON 文件 (失败/不存在返 None)."""
    try:
        if not path or not Path(path).is_file():
            return None
        import json
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        return data
    except (OSError, ValueError, TypeError):
        return None


def _normalize_metadata_keys(raw: dict) -> dict:
    """归一 metadata key 命名 (sidecar 用 lower-case · placeholder schema 用 UPPER_CASE).

    输入可能是 original_client {name, name_core, legal_rep, registered_capital, ...}
    或 client_metadata {CLIENT_FULL_NAME, CLIENT_CORE_NAME, ...}
    · 返回 hybrid dict 同时含两种 key (上层 placeholder_replace 用 alias_map 兜底).
    """
    if not isinstance(raw, dict):
        return {}
    out = dict(raw)  # 保留原 key
    # 反向 alias map: lower-case → UPPER_CASE (与 placeholder_replace alias_map 同源 inverse)
    inverse_alias = {
        "name": "CLIENT_FULL_NAME",
        "name_core": "CLIENT_CORE_NAME",
        "legal_rep": "CLIENT_LEGAL_REP",
        "industry": "CLIENT_INDUSTRY_CATEGORY",
        "business": "CLIENT_BUSINESS_DESC",
        "registered_capital": "CLIENT_REGISTERED_CAPITAL",
        "location": "CLIENT_LOCATION_CITY",
    }
    for lk, uk in inverse_alias.items():
        if lk in raw and uk not in out:
            out[uk] = raw[lk]
    return out


def resolve_client_metadata(
    *,
    source_docx: Path | None = None,
    material_dir: Path | None = None,
    sample_id: str | None = None,
    credit_handoff_payload: dict | None = None,
) -> dict | None:
    """解析 client_metadata · placeholder 替换值的多源合并.

    优先级 (高 → 低):
      1. credit_handoff_payload (channel → credit → report 跨 agent handoff 主链)
      2. material_dir 内 client_metadata.json (Phase 4 · DP00X sample 每个 sample 配一份)
      3. source_docx 的 .metadata.json sidecar 的 original_client 字段
         (Phase 2 模板 placeholder 化时配 · 同时作 docx 真实客户档案兜底)

    返回:
      dict (含 UPPER_CASE placeholder key + lower-case alias key) 或 None (全无源)

    设计:
      - 老路径 / 老 docx 未 placeholder 化 → 返 None · generator 走旧逻辑不 break
      - placeholder 化 docx 无 handoff 时 → 拿 docx sidecar original_client 兜底
        (报告生成的还是"经纬测绘"自己的客户,与原 docx 字面一致 · 不产生 mismatch)
    """
    # 1. credit_handoff_payload
    if credit_handoff_payload and isinstance(credit_handoff_payload, dict):
        cm = credit_handoff_payload.get("client_metadata")
        if isinstance(cm, dict) and cm:
            return _normalize_metadata_keys(cm)

    # 2. material_dir / sample_id 的 client_metadata.json
    if material_dir:
        m_path = Path(material_dir) / "client_metadata.json"
        data = _load_json_if_exists(m_path)
        if isinstance(data, dict):
            cm = data.get("client_metadata") if "client_metadata" in data else data
            if isinstance(cm, dict) and cm:
                return _normalize_metadata_keys(cm)

    # 3. source_docx sidecar
    if source_docx:
        sidecar = Path(source_docx).with_suffix(".metadata.json")
        data = _load_json_if_exists(sidecar)
        if isinstance(data, dict):
            cm = data.get("client_metadata")
            if isinstance(cm, dict) and cm:
                return _normalize_metadata_keys(cm)
            # 兜底: original_client (Phase 2 sidecar 主字段 · docx 真实客户档案)
            oc = data.get("original_client")
            if isinstance(oc, dict) and oc:
                return _normalize_metadata_keys(oc)

    return None


# ============================================================================
# 批量扫描(用于回归 baseline 报告)
# ============================================================================


def scan_directory(samples_dir: str | Path) -> list[TemplateProfile]:
    """扫 samples/ 下所有 docx,返回 TemplateProfile 列表。"""
    base = Path(samples_dir)
    if not base.is_dir():
        return []
    out: list[TemplateProfile] = []
    for p in sorted(base.glob("*.docx")):
        out.append(detect_template(p))
    return out


def coverage_summary(profiles: list[TemplateProfile]) -> dict[str, Any]:
    """生成 coverage_by_template 汇总(供 evaluation yaml 配套报告)。"""
    by_scenario: dict[str, int] = {}
    by_business: dict[str, int] = {}
    qc_floors: dict[str, float] = {}
    for prof in profiles:
        by_scenario[prof.scenario] = by_scenario.get(prof.scenario, 0) + 1
        by_business[prof.business_line] = by_business.get(prof.business_line, 0) + 1
        qc_floors[prof.scenario] = prof.expected_qc_floor
    return {
        "total_templates": len(profiles),
        "by_scenario": by_scenario,
        "by_business_line": by_business,
        "qc_floor_by_scenario": qc_floors,
        "templates": [p.template_name for p in profiles],
    }
