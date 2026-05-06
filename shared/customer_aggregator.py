"""客户画像聚合 · 跨 Agent 视图

per Phase C charter Track A · A1 客户画像聚合 (PM 拍板 2026-05-06):

设计:
- 输入 customer_id → 聚合返:
  - 基础画像 (CRM contract 15 字段)
  - 跨 Agent 历史 (Agent1 推荐 → Agent6 报告 → Agent3 决策 → Agent5 合规校验 → Agent4 预警)
  - 持有产品列表
  - 最近 RM 互动
- 用 CRM contract 严格校验 schema
- ledger 查询取跨 Agent 决策时间线
- failures silent · 不阻 main flow (per CLAUDE.md §3.7.5 BE7 wrapper)

使用:
    from shared.customer_aggregator import aggregate_customer_profile

    profile = aggregate_customer_profile("C-001")
    # → { customer: CrmCustomerProfile, history: [...], holdings: [...], rm_interactions: [...] }
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from shared.crm_contract import CrmCustomerProfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MOCK_DIR = PROJECT_ROOT / "data" / "mock"
MOCK_PROFILES_PATH = MOCK_DIR / "customer_profiles.jsonl"


def _load_mock_profiles() -> dict[str, dict[str, Any]]:
    """加载 mock 个人客户 jsonl · 返 dict by customer_id."""
    if not MOCK_PROFILES_PATH.exists():
        return {}
    profiles: dict[str, dict[str, Any]] = {}
    with MOCK_PROFILES_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                rec = json.loads(line)
                cid = rec.get("customer_id")
                if cid:
                    profiles[cid] = rec
            except json.JSONDecodeError:
                continue
    return profiles


def _query_ledger_history(customer_id: str) -> list[dict[str, Any]]:
    """跨 Agent 决策时间线 · ledger 查询.

    silent fail · 返空 list 不破 main flow.
    """
    try:
        from shared.decision_ledger import default_ledger
        # 注: ledger 用 subject_id_hash 而不是 customer_id 直接 · 这里仅 best-effort
        # production 需要先 hash customer_id (PII) 后查
        from shared.decision_ledger import hash_subject_id
        subject_hash = hash_subject_id(customer_id)
        return default_ledger().query_subject(subject_hash) or []
    except (ImportError, AttributeError, RuntimeError, ValueError, TypeError, OSError):
        return []


def aggregate_customer_profile(customer_id: str) -> Optional[dict[str, Any]]:
    """聚合客户画像 · 返 None if not found.

    Args:
        customer_id: 客户唯一 ID

    Returns:
        {
            'customer': CrmCustomerProfile dict (15 字段),
            'history': list[dict] · 跨 Agent 决策时间线,
            'holdings': list[dict] · 现持产品 (从 customer.existing_products 展开),
            'rm_interactions': list[dict] · 最近 RM 互动 (mock),
            'metadata': { aggregated_at, source_count, ... }
        }
        or None if customer_id not found.
    """
    profiles = _load_mock_profiles()
    raw = profiles.get(customer_id)
    if not raw:
        return None

    # Validate via CRM contract (strict)
    try:
        customer = CrmCustomerProfile(**raw)
    except (ValueError, TypeError) as exc:
        # Failed validation · still return raw with error
        return {
            "customer_id": customer_id,
            "error": f"CRM contract 校验失败: {exc}",
            "raw": raw,
        }

    # 跨 Agent ledger 历史 (silent fail)
    history = _query_ledger_history(customer_id)

    # 现持产品展开 (mock · 真 production 接客户 CRM 现持表)
    holdings: list[dict[str, Any]] = []
    for product_name in customer.existing_products:
        holdings.append({
            "product_name": product_name,
            "status": "active",
            "since": "—",  # 真接 CRM 后填
        })

    # RM 最近互动 (mock · 真 production 接 CRM 互动表)
    rm_interactions: list[dict[str, Any]] = [
        {
            "rm_id": customer.relationship_manager_id,
            "type": "phone_call",
            "at": customer.last_contact_at.isoformat() if customer.last_contact_at else None,
            "notes": "客户上次接触 · 详细记录见 CRM",
        }
    ] if customer.last_contact_at else []

    return {
        "customer": customer.model_dump(mode="json"),
        "history": history,
        "holdings": holdings,
        "rm_interactions": rm_interactions,
        "metadata": {
            "aggregated_at": datetime.now().isoformat(timespec="seconds"),
            "source_count": 1 + (1 if history else 0) + (1 if holdings else 0),
            "consent_status": customer.consent_status.value,
            "schema_version": "1.0",
        },
    }


def list_customers(rm_id: Optional[str] = None) -> list[dict[str, Any]]:
    """列出客户 · 可选 RM 过滤 (用于 RM 客户列表页).

    Args:
        rm_id: 仅返该 RM 的客户 (None = 全部)

    Returns:
        list of {customer_id, name, age, risk_level, ...} (subset 字段)
    """
    profiles = _load_mock_profiles()
    items: list[dict[str, Any]] = []
    for cid, raw in profiles.items():
        if rm_id and raw.get("relationship_manager_id") != rm_id:
            continue
        items.append({
            "customer_id": cid,
            "name": raw.get("name", ""),
            "age": raw.get("age"),
            "city": raw.get("city", ""),
            "risk_level": raw.get("risk_level"),
            "credit_score": raw.get("credit_score"),
            "relationship_manager_id": raw.get("relationship_manager_id"),
            "last_contact_at": raw.get("last_contact_at"),
            "consent_status": raw.get("consent_status"),
        })
    return items


__all__ = [
    "aggregate_customer_profile",
    "list_customers",
]
