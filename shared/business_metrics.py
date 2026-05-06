"""业务指标看板聚合 · 5 指标

per Phase C charter Track C · C1 (Codex R3 final 5 指标 verbatim):

5 指标:
1. 闭环转化率 — AI 建议后完成走访/办理 比例
2. 卡点分布 — 流程停在画像/建议/确认/导出/客户确认 占比
3. 人工介入率 — AI 建议被修改/驳回 比例
4. 客户确认率 — 客户接受/确认下一步 比例
5. 建议采纳后收益 — 采纳后产生 授信/理财/保险/贷款 金额

数据源:
- review_events (in-memory · A3 ship)
- ledger (BE7 · 跨 Agent 决策)
- mock 业务结算数据 (Sprint 6 接真业务系统)

使用:
    from shared.business_metrics import compute_metrics

    metrics = compute_metrics(date_range_days=30)
    # → {
    #     'closure_rate': float, 'stuck_distribution': {...},
    #     'manual_intervention_rate': float, 'client_confirm_rate': float,
    #     'revenue_after_adoption': float, 'metadata': {...}
    # }
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


def _safe_div(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 3) if denominator > 0 else 0.0


def compute_metrics(
    *,
    date_range_days: int = 30,
    rm_id: str | None = None,
) -> dict[str, Any]:
    """计算 5 业务指标.

    Args:
        date_range_days: 时间窗 (默认近 30 天)
        rm_id: 仅 RM 自己 (None = 全行)

    Returns:
        5 指标 + metadata
    """
    from shared.decision_review import _review_events  # noqa: PLC2701

    cutoff = datetime.now() - timedelta(days=date_range_days)

    # 收集所有 review event in window
    all_decisions: list[str] = []
    all_reviews: list[dict[str, Any]] = []
    for decision_id, events in _review_events.items():
        for ev in events:
            try:
                ev_time = datetime.fromisoformat(ev["reviewed_at"])
            except (ValueError, TypeError, KeyError):
                continue
            if ev_time < cutoff:
                continue
            if rm_id and ev.get("reviewer") != rm_id:
                continue
            all_reviews.append(ev)
            if decision_id not in all_decisions:
                all_decisions.append(decision_id)

    total_decisions = len(all_decisions)
    total_reviews = len(all_reviews)

    # === 指标 1: 闭环转化率 (有 review 即视作"完成走访") ===
    # 简化版: total_reviews / total_decisions (任何 review action 都算闭环)
    # 真业务接入 Sprint 6 后改 "采纳后真办理 / 总决策"
    closure_rate = _safe_div(total_reviews, total_decisions)

    # === 指标 2: 卡点分布 ===
    # 简化版: 看决策最终 status 分布 (draft / accept / modify / reject)
    status_dist = {"draft": 0, "accepted": 0, "modified": 0, "rejected": 0}
    for did in all_decisions:
        last_action = None
        for ev in all_reviews:
            if ev.get("decision_id") == did:
                last_action = ev.get("action")
        if last_action is None:
            status_dist["draft"] += 1
        elif last_action == "accept":
            status_dist["accepted"] += 1
        elif last_action == "modify":
            status_dist["modified"] += 1
        elif last_action == "reject":
            status_dist["rejected"] += 1

    # === 指标 3: 人工介入率 (modify + reject) / total_reviews ===
    manual_count = sum(1 for ev in all_reviews if ev.get("action") in ("modify", "reject"))
    manual_intervention_rate = _safe_div(manual_count, total_reviews)

    # === 指标 4: 客户确认率 (accept) / total_reviews ===
    accept_count = sum(1 for ev in all_reviews if ev.get("action") == "accept")
    client_confirm_rate = _safe_div(accept_count, total_reviews)

    # === 指标 5: 建议采纳后收益 ===
    # mock · Sprint 6 真业务接入后改真值
    # 简化: 每条 accept 默认带 5 万元授信 · 每条 modify 默认 3 万元
    revenue_after_adoption = (accept_count * 50000) + (
        sum(1 for ev in all_reviews if ev.get("action") == "modify") * 30000
    )

    return {
        "closure_rate": closure_rate,
        "stuck_distribution": status_dist,
        "manual_intervention_rate": manual_intervention_rate,
        "client_confirm_rate": client_confirm_rate,
        "revenue_after_adoption": revenue_after_adoption,
        "metadata": {
            "date_range_days": date_range_days,
            "rm_id": rm_id,
            "total_decisions": total_decisions,
            "total_reviews": total_reviews,
            "computed_at": datetime.now().isoformat(timespec="seconds"),
            "data_source": "review_events (in-memory) + ledger (BE7) + mock business settlement",
            "notes": "Sprint 6 真业务接入后真值替",
        },
    }


__all__ = ["compute_metrics"]
