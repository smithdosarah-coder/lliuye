# -*- coding: utf-8 -*-
"""MatrixMatcher: 规则集 × 事件集 的矩阵比对（Agent5 核心）。

两阶段策略：
  1. 硬规则（HARD_CHECKERS）：基于字段的确定性判定 —— 每个 RuleItem.dsl.check
     指向一个 Python 函数，函数返回 MatrixCell(status/severity/evidence/reason)。
     绝大多数组合在这里被过滤为 not_applicable 或直接判定 violate。
  2. LLM 判定（可选）：对"适用 & 未被硬规则决定"的单元格，调 compliance_checker.LLMJudge
     做语义判定。Demo 场景默认关闭 LLM（`use_llm=False`）保证稳定性。

聚合阶段：同一条 rule 命中多个 event 时合并为 ViolationRecord，调 defect_classifier 分级。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Any

from shared.kb_scan.models import RuleItem, RiskLevel


# ======================================================================
# 数据结构
# ======================================================================

@dataclass
class MatrixCell:
    rule_id: str
    event_id: str
    status: str = "not_applicable"     # violate / comply / not_applicable
    severity: str = "none"             # critical / major / minor / none
    evidence: str = ""
    match_reason: str = ""


@dataclass
class ViolationRecord:
    violation_id: str
    rule: RuleItem
    events: list[dict] = field(default_factory=list)
    severity: str = "minor"                 # critical / major / minor
    match_reason: str = ""
    evidence_chain: list[dict] = field(default_factory=list)
    recommendation: str = ""
    responsible_depts: list[str] = field(default_factory=list)
    deadline: str = ""


@dataclass
class ComplianceLedger:
    severe: list[ViolationRecord] = field(default_factory=list)   # critical
    normal: list[ViolationRecord] = field(default_factory=list)   # major
    observation: list[ViolationRecord] = field(default_factory=list)  # minor
    rule_count: int = 0
    event_count: int = 0
    cell_count: int = 0
    hit_count: int = 0
    duration_seconds: float = 0.0

    @property
    def stats(self) -> dict:
        return {
            "rules": self.rule_count, "events": self.event_count,
            "cells": self.cell_count, "hits": self.hit_count,
            "severe": len(self.severe), "normal": len(self.normal),
            "observation": len(self.observation),
            "duration": round(self.duration_seconds, 2),
        }


# ======================================================================
# 硬规则检查器注册
# 返回值：
#   None                    → 适用但不违规（comply）
#   MatrixCell(violate)     → 违规
#   (忽略，视为 not_applicable)
# ======================================================================

HARD_CHECKERS: dict[str, Callable[[RuleItem, dict, dict], MatrixCell | None]] = {}


def register_check(name: str):
    def deco(fn):
        HARD_CHECKERS[name] = fn
        return fn
    return deco


@register_check("loan_duration_limit")
def _loan_duration(rule: RuleItem, event: dict, params: dict) -> MatrixCell | None:
    if event.get("event_type") != "loan":
        return _NA(rule, event, "规则仅适用于放款事件")
    f = event["fields"]
    purpose = str(f.get("purpose") or "")
    prefix = params.get("purpose_prefix", "")
    if prefix and prefix not in purpose:
        return _NA(rule, event, f"用途非'{prefix}'，规则不适用")
    dur = f.get("duration_months")
    if dur is None:
        return _NA(rule, event, "期限字段缺失")
    limit = int(params.get("max_months", 12))
    if dur > limit:
        return MatrixCell(
            rule_id=rule.rule_id, event_id=event["event_id"],
            status="violate", severity="critical",
            evidence=f"期限={dur}月，超出阈值{limit}月",
            match_reason=f"{event['event_id']} 贷款用途={purpose}，期限{dur}月 > 上限{limit}月",
        )
    return _comply(rule, event, f"期限={dur}≤{limit}月")


@register_check("loan_amount_limit")
def _loan_amount(rule: RuleItem, event: dict, params: dict) -> MatrixCell | None:
    if event.get("event_type") != "loan":
        return _NA(rule, event, "规则仅适用于放款事件")
    f = event["fields"]
    purpose = str(f.get("purpose") or "")
    prefix = params.get("purpose_prefix", "")
    if prefix and prefix not in purpose:
        return _NA(rule, event, f"用途非'{prefix}'，规则不适用")
    amt = f.get("amount")
    if amt is None:
        return _NA(rule, event, "金额字段缺失")
    limit = float(params.get("max_amount", 200000))
    if amt > limit:
        return MatrixCell(
            rule_id=rule.rule_id, event_id=event["event_id"],
            status="violate", severity="critical",
            evidence=f"金额={amt:.0f}元，超出阈值{limit:.0f}元",
            match_reason=f"{event['event_id']} 用途={purpose}，金额{amt:.0f} > 上限{limit:.0f}",
        )
    return _comply(rule, event, f"金额={amt:.0f}≤{limit:.0f}元")


@register_check("loan_purpose_blacklist")
def _loan_purpose(rule: RuleItem, event: dict, params: dict) -> MatrixCell | None:
    if event.get("event_type") != "loan":
        return _NA(rule, event, "规则仅适用于放款事件")
    f = event["fields"]
    purpose = str(f.get("purpose") or "")
    banned = params.get("banned", [])
    hit = next((b for b in banned if b in purpose), None)
    if hit:
        return MatrixCell(
            rule_id=rule.rule_id, event_id=event["event_id"],
            status="violate", severity="minor",
            evidence=f"贷款用途='{purpose}' 含禁用词 '{hit}'",
            match_reason=f"{event['event_id']} 用途疑似投资性：{purpose}",
        )
    return _comply(rule, event, "用途无禁用词")


@register_check("model_independent_verified")
def _model_verified(rule: RuleItem, event: dict, params: dict) -> MatrixCell | None:
    if event.get("event_type") != "model":
        return _NA(rule, event, "规则仅适用于模型上线事件")
    status = str(event["fields"].get("verified_status") or "").strip()
    if "未" in status or status in ("否", "no", "false"):
        return MatrixCell(
            rule_id=rule.rule_id, event_id=event["event_id"],
            status="violate", severity="critical",
            evidence=f"独立验证状态='{status}'",
            match_reason=f"{event['event_id']} 模型未完成独立验证",
        )
    return _comply(rule, event, f"验证状态='{status}'")


@register_check("model_monitor_frequency")
def _model_freq(rule: RuleItem, event: dict, params: dict) -> MatrixCell | None:
    if event.get("event_type") != "model":
        return _NA(rule, event, "规则仅适用于模型上线事件")
    freq = str(event["fields"].get("monitor_frequency") or "").strip()
    if not freq:
        return _NA(rule, event, "监测频率字段缺失")
    if "季度" in freq or "月" in freq or "周" in freq or "每天" in freq or "日" in freq:
        return _comply(rule, event, f"监测频率={freq}")
    # 年度/其他 → 违规
    return MatrixCell(
        rule_id=rule.rule_id, event_id=event["event_id"],
        status="violate", severity="major",
        evidence=f"监测频率='{freq}'，低于季度要求",
        match_reason=f"{event['event_id']} 监测频率={freq} 不达季度要求",
    )


@register_check("model_report_sla")
def _model_sla(rule: RuleItem, event: dict, params: dict) -> MatrixCell | None:
    if event.get("event_type") != "model":
        return _NA(rule, event, "规则仅适用于模型上线事件")
    wd = event["fields"].get("workdays_to_report")
    if wd is None:
        return _NA(rule, event, "上线/报送日期缺失")
    max_wd = int(params.get("max_workdays", 5))
    if wd > max_wd:
        return MatrixCell(
            rule_id=rule.rule_id, event_id=event["event_id"],
            status="violate", severity="critical",
            evidence=f"上线到报送{wd}个工作日，超 {max_wd} 日",
            match_reason=f"{event['event_id']} 模型上线后{wd}个工作日才报送（应≤{max_wd}）",
        )
    return _comply(rule, event, f"报送间隔={wd}≤{max_wd} 工作日")


@register_check("coop_funding_ratio")
def _coop_ratio(rule: RuleItem, event: dict, params: dict) -> MatrixCell | None:
    if event.get("event_type") != "cooperation":
        return _NA(rule, event, "规则仅适用于联合贷款事件")
    ratio = event["fields"].get("funding_ratio")
    if ratio is None:
        return _NA(rule, event, "出资比例字段缺失")
    min_r = float(params.get("min_ratio", 30.0))
    if ratio < min_r:
        return MatrixCell(
            rule_id=rule.rule_id, event_id=event["event_id"],
            status="violate", severity="critical",
            evidence=f"本行出资比例={ratio}%，低于阈值{min_r}%",
            match_reason=f"{event['event_id']} 合作方={event['fields'].get('cooperator')}，"
                         f"本行出资{ratio}% < 下限{min_r}%",
        )
    return _comply(rule, event, f"出资比例={ratio}≥{min_r}%")


@register_check("coop_contract_exists")
def _coop_contract(rule: RuleItem, event: dict, params: dict) -> MatrixCell | None:
    if event.get("event_type") != "cooperation":
        return _NA(rule, event, "规则仅适用于联合贷款事件")
    status = str(event["fields"].get("contract_status") or "").strip()
    if status == "文档缺失" or "缺" in status or "无" in status:
        return MatrixCell(
            rule_id=rule.rule_id, event_id=event["event_id"],
            status="violate", severity="major",
            evidence=f"合同状态='{status}'",
            match_reason=f"{event['event_id']} 合作协议文档不全",
        )
    return _comply(rule, event, f"合同状态='{status}'")


# ---- 默认的适用性判定（用于无 dsl.check 的规则）----

CATEGORY_TO_EVENT = {
    "期限限制": {"loan"},
    "额度限制": {"loan"},
    "联合贷款": {"cooperation"},
    "风险模型": {"model"},
    "报送时效": {"model"},
    "合作准入": {"cooperation"},
    "集中度": {"cooperation"},
    "用途管理": {"loan"},
    "催收规范": {"loan"},
    "信息披露": {"loan"},
    "贷后管理": {"loan"},
    "贷前管理": {"loan"},
    "合同管理": {"loan"},
    "风险数据": {"model", "loan"},
    "风险管理体系": set(),
    "地域限制": {"loan"},
    "附则": set(),
    "其他": set(),
}


def _NA(rule: RuleItem, event: dict, reason: str) -> MatrixCell:
    return MatrixCell(
        rule_id=rule.rule_id, event_id=event["event_id"],
        status="not_applicable", severity="none",
        evidence="", match_reason=reason,
    )


def _comply(rule: RuleItem, event: dict, reason: str) -> MatrixCell:
    return MatrixCell(
        rule_id=rule.rule_id, event_id=event["event_id"],
        status="comply", severity="none", evidence="",
        match_reason=reason,
    )


# ======================================================================
# 矩阵比对引擎
# ======================================================================

SEVERITY_ORDER = {"critical": 0, "major": 1, "minor": 2, "none": 3}
DEADLINE_MAP = {
    "critical": "15 个工作日内完成",
    "major": "30 个工作日内完成",
    "minor": "下一季度内完成优化",
}


class MatrixMatcher:
    """规则集 × 事件集 → ComplianceLedger。"""

    def __init__(self, use_llm: bool = False, llm_judge=None):
        self.use_llm = use_llm
        self.llm_judge = llm_judge  # 可选 compliance_checker.LLMJudge 注入

    # ------------------------------------------------------------------

    def match(self, rules: list, events: list[dict],
              progress_cb=None) -> ComplianceLedger:
        t0 = time.time()
        cells: list[MatrixCell] = []
        ledger = ComplianceLedger(
            rule_count=len(rules), event_count=len(events),
            cell_count=len(rules) * len(events),
        )
        total = ledger.cell_count
        done = 0
        # 按 rule 外层 / event 内层
        for ri, rule in enumerate(rules):
            for ei, event in enumerate(events):
                cell = self._judge_cell(rule, event)
                cells.append(cell)
                done += 1
                if progress_cb and done % max(1, total // 40) == 0:
                    progress_cb(done, total)
        if progress_cb:
            progress_cb(total, total)

        # 聚合：同规则多事件 → 1 条 ViolationRecord
        violations = self._aggregate_violations(cells, rules, events)
        for v in violations:
            ranked = SEVERITY_ORDER.get(v.severity, 3)
            if ranked == 0:
                ledger.severe.append(v)
            elif ranked == 1:
                ledger.normal.append(v)
            elif ranked == 2:
                ledger.observation.append(v)
        ledger.hit_count = len(ledger.severe) + len(ledger.normal) + len(ledger.observation)
        ledger.duration_seconds = time.time() - t0
        return ledger

    # ------------------------------------------------------------------

    def _judge_cell(self, rule, event: dict) -> MatrixCell:
        dsl = getattr(rule, "dsl", {}) or {}
        check = dsl.get("check")
        if check and check in HARD_CHECKERS:
            try:
                cell = HARD_CHECKERS[check](rule, event, dsl.get("params") or {})
                if cell is not None:
                    return cell
            except (RuntimeError, ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                return _NA(rule, event, f"硬规则执行异常：{e}")
        # 无硬规则 → 按 category → event_type 判断适用性
        applicable = CATEGORY_TO_EVENT.get(getattr(rule, "category", "其他"), set())
        if applicable and event.get("event_type") in applicable:
            # 适用但无确定性判定 — Demo 模式：comply（避免引入噪音）
            if self.use_llm and self.llm_judge is not None:
                try:
                    return self.llm_judge(rule, event)
                except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError):
                    pass
            return _comply(rule, event, f"类别={rule.category}，适用但无确定性命中")
        return _NA(rule, event, f"类别={rule.category} 与事件类型不匹配")

    # ------------------------------------------------------------------

    def _aggregate_violations(self, cells: list[MatrixCell],
                               rules: list, events: list[dict]) -> list[ViolationRecord]:
        """按 rule 聚合所有 violate cell；再下沉到 defect_classifier 分级。"""
        from .defect_classifier import (
            DEADLINE_MAP as LEGACY_DL,  # noqa: F401 (保留映射兼容)
        )
        rule_by_id = {r.rule_id: r for r in rules}
        event_by_id = {e["event_id"]: e for e in events}

        by_rule: dict[str, list[MatrixCell]] = {}
        for c in cells:
            if c.status != "violate":
                continue
            by_rule.setdefault(c.rule_id, []).append(c)

        # 去重：多个 rule 引用同一 check（如政策+本行制度同时禁止期限>12月），
        # 保留 source 更"强"的（POLICY 优于 INTERNAL 优于 AUTO）。
        def _rule_priority(rid: str) -> int:
            if rid.startswith("POLICY"):
                return 0
            if rid.startswith("INTERNAL"):
                return 1
            return 2

        def _check_sig(rule) -> str | None:
            dsl = getattr(rule, "dsl", {}) or {}
            chk = dsl.get("check")
            if not chk:
                return None
            # 以 check + params 作为签名
            return chk + "|" + str(sorted((dsl.get("params") or {}).items()))

        # 按 check 签名分组，只保留优先级最高的 rule_id
        sig_groups: dict[str, list[str]] = {}
        for rid in by_rule.keys():
            r = rule_by_id.get(rid)
            if r is None:
                continue
            sig = _check_sig(r)
            if sig is None:
                sig_groups.setdefault(f"_nosig::{rid}", []).append(rid)
            else:
                sig_groups.setdefault(sig, []).append(rid)

        kept_rids: list[str] = []
        for sig, rids in sig_groups.items():
            rids_sorted = sorted(rids, key=_rule_priority)
            kept_rids.append(rids_sorted[0])
        # 过滤 by_rule
        by_rule = {rid: by_rule[rid] for rid in kept_rids}

        violations: list[ViolationRecord] = []
        vi = 0
        # 按严重度排序：先 critical，再 major，再 minor
        sorted_rule_ids = sorted(by_rule.keys(), key=lambda rid: SEVERITY_ORDER.get(
            max((c.severity for c in by_rule[rid]),
                key=lambda s: -SEVERITY_ORDER.get(s, 9)), 3))
        for rid in sorted_rule_ids:
            rule = rule_by_id.get(rid)
            if rule is None:
                continue
            cs = by_rule[rid]
            # 规则级严重度 = max
            rule_sev = min((c.severity for c in cs),
                           key=lambda s: SEVERITY_ORDER.get(s, 9))
            vi += 1
            v = ViolationRecord(
                violation_id=f"VIO-{vi:03d}",
                rule=rule,
                events=[event_by_id[c.event_id]
                        for c in cs if c.event_id in event_by_id],
                severity=rule_sev,
                match_reason=cs[0].match_reason,
                evidence_chain=[{
                    "event_id": c.event_id,
                    "evidence": c.evidence,
                    "reason": c.match_reason,
                } for c in cs],
                recommendation=_default_recommendation(rule, rule_sev, cs),
                responsible_depts=_default_depts(rule),
                deadline=DEADLINE_MAP.get(rule_sev, "60 个工作日内完成"),
            )
            violations.append(v)
        return violations


# ======================================================================
# 默认整改建议（模板化，不依赖 LLM — Demo 稳定）
# ======================================================================

def _default_recommendation(rule, severity: str, cells: list[MatrixCell]) -> str:
    eids = ", ".join(c.event_id for c in cells[:5])
    if severity == "critical":
        return (
            f"[立即] 暂停涉及业务 {eids} 的后续操作。\n"
            f"[立即] 组织业务、合规、风险三方联合复核原始记录。\n"
            f"[7 天内] 对同类业务开展专项自查，形成整改报告。"
        )
    if severity == "major":
        return (
            f"[10 天内] 针对 {rule.title} 补充制度/流程。\n"
            f"[30 天内] 对相关业务({eids})补做合规评估并留痕。"
        )
    return (
        f"[下一季度] 优化 {rule.title} 相关执行细节，完善文档与复核流程。"
    )


def _default_depts(rule) -> list[str]:
    cat = getattr(rule, "category", "")
    mapping = {
        "期限限制": ["零售信贷部", "合规部"],
        "额度限制": ["零售信贷部", "风险管理部"],
        "联合贷款": ["零售信贷部", "法律合规部"],
        "风险模型": ["风险管理部", "科技部"],
        "报送时效": ["风险管理部", "合规部"],
        "贷后管理": ["零售信贷部", "运营部"],
        "贷前管理": ["零售信贷部"],
        "催收规范": ["资产管理部", "合规部"],
        "信息披露": ["合规部", "运营部"],
        "用途管理": ["零售信贷部"],
        "合作准入": ["零售信贷部", "合规部"],
        "集中度": ["风险管理部"],
        "地域限制": ["合规部"],
    }
    return mapping.get(cat, ["合规部"])
