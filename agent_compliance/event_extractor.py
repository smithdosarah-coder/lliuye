# -*- coding: utf-8 -*-
"""EventExtractor: 从业务 Excel 行 → 统一 BusinessEvent 字典。

策略：
  - 根据表头自动识别 event_type（放款 / 联合贷款 / 风控模型）
  - 抽取 event_id / event_date / 主体字段（金额/期限/比例）
  - 保留 raw_record 用于追溯原始记录
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from .knowledge_base import ComplianceKnowledgeBase


# ----------------------------------------------------------------------
# 字段规范：每个 event_type 的字段映射规则
# ----------------------------------------------------------------------

LOAN_FIELD_MAP = {
    "event_id": ["放款单号", "loan_id"],
    "event_date": ["放款日期"],
    "amount": ["放款金额(元)", "金额"],
    "duration_months": ["期限(月)"],
    "purpose": ["贷款用途", "用途"],
    "cooperator": ["合作方"],
    "status": ["还款状态"],
    "customer_id": ["客户ID", "客户号"],
}

COOP_FIELD_MAP = {
    "event_id": ["合作单号"],
    "event_date": ["合作日期"],
    "cooperator": ["合作方名称"],
    "total_amount": ["放款总额(元)"],
    "bank_amount": ["本行出资(元)"],
    "funding_ratio": ["出资比例(%)"],
    "contract_status": ["合同状态"],
}

MODEL_FIELD_MAP = {
    "event_id": ["模型单号"],
    "event_date": ["上线日期"],
    "model_name": ["模型名称"],
    "verified_status": ["独立验证状态"],
    "report_date": ["上线报送日期"],
    "approver": ["审批人"],
    "model_type": ["模型类型"],
    "monitor_frequency": ["监测频率"],
}


def _pick(row: dict, keys: list[str]) -> Any:
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
    return None


def _detect_event_type(headers: set[str]) -> str:
    if "放款单号" in headers:
        return "loan"
    if "合作单号" in headers:
        return "cooperation"
    if "模型单号" in headers:
        return "model"
    return "unknown"


class EventExtractor:
    """将 KB 中的业务表行 → BusinessEvent 列表。"""

    def extract(self, kb: ComplianceKnowledgeBase) -> list[dict]:
        events: list[dict] = []
        for sheet_name, rows in kb.business_tables.items():
            if not rows:
                continue
            headers = {k for k in rows[0].keys() if k and not k.startswith("_")}
            et = _detect_event_type(headers)
            for r in rows:
                ev = self._row_to_event(r, et, sheet_name)
                if ev:
                    events.append(ev)
        return events

    def _row_to_event(self, row: dict, event_type: str, sheet: str) -> dict | None:
        if event_type == "loan":
            fm = LOAN_FIELD_MAP
        elif event_type == "cooperation":
            fm = COOP_FIELD_MAP
        elif event_type == "model":
            fm = MODEL_FIELD_MAP
        else:
            return None

        fields: dict[str, Any] = {}
        for logical, keys in fm.items():
            v = _pick(row, keys)
            if v is not None:
                fields[logical] = v

        event_id = str(fields.get("event_id") or "").strip()
        if not event_id:
            return None

        # 类型兜底
        if event_type == "loan":
            fields["amount"] = _to_float(fields.get("amount"))
            fields["duration_months"] = _to_int(fields.get("duration_months"))
        elif event_type == "cooperation":
            fields["total_amount"] = _to_float(fields.get("total_amount"))
            fields["bank_amount"] = _to_float(fields.get("bank_amount"))
            fields["funding_ratio"] = _to_float(fields.get("funding_ratio"))
        elif event_type == "model":
            fields["workdays_to_report"] = _workdays_between(
                fields.get("event_date"), fields.get("report_date"),
            )

        return {
            "event_id": event_id,
            "event_type": event_type,
            "event_date": str(fields.get("event_date") or ""),
            "fields": fields,
            "raw_record": {k: v for k, v in row.items() if not str(k).startswith("_")},
            "source_file": row.get("_source_file", ""),
            "sheet": sheet,
        }

    # ------------------------------------------------------------------

    def stats(self, events: list[dict]) -> dict:
        from collections import Counter
        c = Counter(e["event_type"] for e in events)
        return {"total": len(events), "by_type": dict(c)}


# ----------------------------------------------------------------------
# 工具函数
# ----------------------------------------------------------------------

def _to_float(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        m = re.search(r"-?\d+(\.\d+)?", str(v))
        return float(m.group()) if m else None


def _to_int(v) -> int | None:
    f = _to_float(v)
    return int(f) if f is not None else None


def _parse_date(v) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, date):
        return v
    s = str(v).strip()
    m = re.match(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except (ValueError, TypeError):
            return None
    return None


def _workdays_between(d1, d2) -> int | None:
    a = _parse_date(d1)
    b = _parse_date(d2)
    if not a or not b:
        return None
    if b < a:
        return -1
    # 粗略按自然日 - 周末
    days = 0
    cur = a
    while cur < b:
        cur = date.fromordinal(cur.toordinal() + 1)
        if cur.weekday() < 5:
            days += 1
    return days
