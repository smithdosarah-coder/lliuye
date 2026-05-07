# -*- coding: utf-8 -*-
"""agent_channel.signal_density — Q-054 第 5 维度 candidate metadata.

候选企业近 90 天动态信号密度 0-1 分 · per Q-054 R3 v2 P0 mesh + CLAUDE.md §3.1 / §3.5.1 #6.

3 层算法:
  L1 freshness (确定性 · Python): signal_type → ClaimType → recency_weight
  L2 salience  (概率性 · LLM 可选): 走 shared.llm_caller · LLM 仅打 0-1 分
  L3 aggregate (确定性 · Python): clamp01(sum(L1 * L2) / SIGNAL_DENSITY_NORMALIZATION_DIVISOR)

硬线:
  - LLM 仅打 0-1 显著性 · 不算频次 (per §3.1)
  - LLM 越界 → 单 signal salience=0 + reason="llm_out_of_range"
                + 冻结 prompt 版本写 evidence/llm_out_of_range_<date>.md (Q-054 risk)
  - LLM 不可达 → static prior fallback + reason="llm_unavailable" · 不阻整流
  - 不破 Q-041 4 字段 · 仅 additive 加 signal_density / signal_density_reason

字段填不了 → signal_density=0.0 + signal_density_reason="未能自动填写: <cause>"

使用:
    from agent_channel.signal_density import compute_signal_density

    result = compute_signal_density(item, llm=llm_caller_or_none)
    # → {"signal_density": 0.42, "signal_density_reason": ""}
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from shared.evidence_freshness import (
    ClaimType,
    compute_freshness_days,
    compute_recency_weight,
)

logger = logging.getLogger(__name__)

# LLM prompt 版本 · 越界 evidence 记录用 · 任何 prompt 改动必 bump
SIGNAL_SALIENCE_PROMPT_VERSION: str = "v1.0-2026-05-07"

# 项目根 (用于 evidence/ 文件 path)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 每候选最多送 LLM 的 signal 数 · 控 token + Q-053 PB#2 守则 (短 prompt)
_LLM_BATCH_TOP_N: int = 10

# LLM salience prompt (≤ 60 行 · per Q-053 PB#2 220 行硬线 · Q-043 short + low)
_SIGNAL_SALIENCE_SYSTEM_PROMPT: str = """\
你是 Agent1 信贷客户经理 AI 助手 · 候选企业信号显著性评分器.

[安全]
- 输出严格 JSON · 不得编造内容 · 不得引用未提供信息.
- salience ∈ [0.0, 1.0] · 越界视为非法 · 系统会 fallback 静态 prior.

[evidence-first]
- 仅基于输入 signal 文本评分 · 缺失字段不可凭空补.

[评分锚点 · 业务依据"现在该打哪通电话"]
- 股权变更 / 法人变更 / 注资 / 实控人变更 → 0.7-0.95 (决策含金量最高)
- 中标公告 / 大额订单 / 政府采购 → 0.5-0.8
- 融资 / 扩产 / 新厂 / IPO / 并购 → 0.45-0.75
- 司法 / 税务 / 行政处罚 → 0.4-0.65
- 技术突破 / 专利 / 资质荣誉 → 0.35-0.6
- 一般新闻 / 招聘动态 → 0.2-0.45
- 社交舆情噪声 → 0.1-0.3

[输出 schema]
返回 JSON: {"per_signal": [{"idx": int, "salience": float}], "reason": str}
- per_signal[i].idx 对应输入 signals[i] 的索引 (从 0 起)
- per_signal[i].salience ∈ [0.0, 1.0]
- reason: 一句话说明你的整体判断逻辑

[自检]
返回前确认: (1) 所有 idx ∈ [0, len(signals)) (2) 所有 salience ∈ [0.0, 1.0]
"""

_SIGNAL_SALIENCE_SCHEMA_HINT: str = (
    '{"per_signal": [{"idx": 0, "salience": 0.85}], "reason": "<逻辑>"}'
)


# ============================================================================
# 模块级常量
# ============================================================================

# 归一化分母 · 3 个满分信号 (recency_w=1.0 × salience=1.0) 即 signal_density=1.0
# 业务依据: 1 条满分信号 ≈ 0.33 (远未到首抓阈值) · 3 条满分 = 客户经理首抓信号
SIGNAL_DENSITY_NORMALIZATION_DIVISOR: float = 3.0

# 90 天硬窗口 (per Q-054 · align freshness SLA · 窗口外 recency_weight 极低)
WINDOW_DAYS: int = 90

# signal_type → ClaimType (per shared.evidence_freshness.FRESHNESS_SLA_DAYS)
# 10 种 signal_type 来自 agent_channel.realtime_stream._SIGNAL_TYPE_TO_KEY
SIGNAL_TYPE_TO_CLAIM: dict[str, ClaimType] = {
    "biz":         ClaimType.BUSINESS_CHANGE,  # 工商变更 730d
    "bidding":     ClaimType.BID,              # 招投标 90d
    "growth":      ClaimType.FUNDING,          # 扩产 / 融资 365d
    "legal":       ClaimType.LEGAL,            # 司法 365d
    "tax":         ClaimType.FINANCIAL,        # 税务 120d
    "recruit":     ClaimType.RECRUIT,          # 招聘 60d
    "news":        ClaimType.NEWS,             # 新闻 180d
    "recognition": ClaimType.NEWS,             # 专精特新名单 → 资讯 180d
    "award":       ClaimType.NEWS,             # 获奖 180d
    "tech":        ClaimType.NEWS,             # 技术突破 180d
    "social":      ClaimType.NEWS,             # 社交舆情 180d
}

# 静态 salience prior 表 · LLM 不可达时 fallback (per §3.1 确定性兜底)
# 业务依据: 客户经理"现在该打哪通电话"优先级 ·
#   biz 股权 / 法人 / 注资 = 决策含金量最高 · social 噪声多
STATIC_SALIENCE_PRIOR: dict[str, float] = {
    "biz":         0.85,
    "bidding":     0.70,
    "growth":      0.65,
    "legal":       0.55,
    "tax":         0.50,
    "tech":        0.45,
    "recognition": 0.45,
    "award":       0.40,
    "recruit":     0.35,
    "news":        0.30,
    "social":      0.20,
}

# 未识别 signal_type 的兜底 salience
UNKNOWN_SALIENCE: float = 0.30


# ============================================================================
# 公开 API
# ============================================================================

def signal_type_to_claim_type(signal_type: str) -> ClaimType:
    """signal_type → ClaimType · 未识别返 GENERIC (180d SLA · per shared.evidence_freshness)."""
    return SIGNAL_TYPE_TO_CLAIM.get((signal_type or "").strip(), ClaimType.GENERIC)


def compute_signal_salience(signal: dict) -> tuple[float, str]:
    """单 signal 的 static prior salience · 0-1.

    单 signal API 只走 static prior · LLM 路径仅在 batch (compute_signal_density 内部)
    使用 · 避免 N 次 LLM 调用浪费 token.

    Returns:
        (salience ∈ [0, 1], reason="" 总为空)
    """
    return _static_salience(signal), ""


def _static_salience(signal: dict) -> float:
    """静态 prior 表 · 按 signal_type 返 prior 值 · 越界 clamp 到 [0, 1]."""
    stype = (signal.get("signal_type") or "").strip()
    val = STATIC_SALIENCE_PRIOR.get(stype, UNKNOWN_SALIENCE)
    return _clamp01(val)


def _clamp01(x: float) -> float:
    """clamp [0, 1] · 防 prior 表 / LLM 误差越界."""
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


# ============================================================================
# LLM batch salience 路径 (per Q-054 § L2 概率性层 · Q-053 PB#2 短 prompt)
# ============================================================================

def _compute_saliences_batch(
    signals: list[dict],
    *,
    llm: Optional[Any] = None,
) -> tuple[list[float], str]:
    """批量计算 N signal 的 salience · 1 次 LLM call · fallback static prior.

    Args:
        signals: list of signal dict (顺序保留)
        llm:     LLMCaller 实例 or None

    Returns:
        (saliences list 长度 == len(signals), reason)
        reason 非空 = LLM 路径降级 (llm_unavailable / llm_out_of_range / llm_invalid_response)
    """
    static_list = [_static_salience(s) for s in signals]

    if llm is None or not signals:
        return static_list, ""

    try:
        llm_list = _llm_salience_batch(signals, llm=llm)
    except Exception as e:  # noqa: BLE001 — LLM call 任何异常都 fallback static
        logger.warning(
            "signal_density LLM batch call failed: %s · fallback static prior",
            e, exc_info=False,
        )
        return static_list, "llm_unavailable"

    if llm_list is None:
        return static_list, "llm_unavailable"

    # 越界 guard · 任何 1 个越界即整批 fallback static + 写 evidence (PM 修正 #3)
    out_of_range = [
        (i, s) for i, s in enumerate(llm_list) if not (0.0 <= s <= 1.0)
    ]
    if out_of_range:
        _record_out_of_range_evidence(signals, llm_list, out_of_range)
        return static_list, "llm_out_of_range"

    return llm_list, ""


def _llm_salience_batch(
    signals: list[dict],
    *,
    llm: Any,
) -> Optional[list[float]]:
    """1 次 LLM JSON call · 评 top-N signal salience · 长度对齐 signals (超出 top-N 用 static).

    Returns:
        list[float] 长度 == len(signals) · 缺失 idx 用 static prior 兜底
        None 表示 LLM 返回不可用 (空 / 非预期 schema)
    """
    top_signals = signals[:_LLM_BATCH_TOP_N]

    user_payload = json.dumps(
        [
            {
                "idx": i,
                "type": s.get("signal_type", ""),
                "title": (s.get("signal_title") or "")[:120],
                "detail": (s.get("signal_detail") or "")[:240],
            }
            for i, s in enumerate(top_signals)
        ],
        ensure_ascii=False,
    )

    result = llm.chat_json(
        _SIGNAL_SALIENCE_SYSTEM_PROMPT,
        user_payload,
        schema_hint=_SIGNAL_SALIENCE_SCHEMA_HINT,
        temperature=0.1,
    )

    payload = getattr(result, "json_payload", None)
    if not isinstance(payload, dict):
        return None
    per_signal = payload.get("per_signal")
    if not isinstance(per_signal, list):
        return None

    salience_map: dict[int, float] = {}
    for entry in per_signal:
        if not isinstance(entry, dict):
            continue
        idx = entry.get("idx")
        sal = entry.get("salience")
        if isinstance(idx, int) and isinstance(sal, (int, float)):
            salience_map[idx] = float(sal)

    if not salience_map:
        return None

    out: list[float] = []
    for i, sig in enumerate(signals):
        if i in salience_map:
            out.append(salience_map[i])
        else:
            # LLM 未返该 idx (超出 top-N 或 LLM 漏) → static prior 兜底
            out.append(_static_salience(sig))
    return out


def _record_out_of_range_evidence(
    signals: list[dict],
    llm_scores: list[float],
    out_of_range_pairs: list[tuple[int, float]],
) -> None:
    """LLM 越界 → 冻结 prompt 版本 + signals + raw scores 到 evidence/llm_out_of_range_<date>.md.

    每天单文件 append · 不去重 · 越多 evidence 越好排查.
    silent-fail · evidence 写不进不阻断主流.
    """
    try:
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        evidence_dir = _PROJECT_ROOT / "evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        path = evidence_dir / f"llm_out_of_range_{date_str}.md"

        block = [
            f"\n## {now.isoformat(timespec='seconds')} · prompt={SIGNAL_SALIENCE_PROMPT_VERSION}",
            "",
            f"- 越界 idx + value: `{out_of_range_pairs}`",
            f"- 全 LLM 评分: `{llm_scores}`",
            "- 输入 signals:",
            "```json",
            json.dumps(
                [
                    {
                        "idx": i,
                        "type": s.get("signal_type", ""),
                        "title": (s.get("signal_title") or "")[:120],
                    }
                    for i, s in enumerate(signals)
                ],
                ensure_ascii=False,
                indent=2,
            ),
            "```",
            "",
            "**Action**: prompt freeze · 单候选 fallback static prior · 不阻整流 (per Q-054 PM 修正 #3).",
            "",
        ]
        with path.open("a", encoding="utf-8") as f:
            if path.stat().st_size == 0:
                f.write(
                    f"# LLM out-of-range evidence · {date_str}\n\n"
                    f"Q-054 B1 signal_density LLM salience 越界 fallback evidence.\n"
                    f"Prompt version frozen at: `{SIGNAL_SALIENCE_PROMPT_VERSION}`\n"
                )
            f.write("\n".join(block))
    except OSError as e:
        logger.warning("evidence write failed (silent): %s", e)


def compute_signal_density(
    item: dict,
    *,
    llm: Optional[Any] = None,
    reference_date: Optional[datetime] = None,
) -> dict:
    """主入口 · 单候选企业 signal_density 0-1.

    Args:
        item: enriched candidate dict · item["signals"] = list of signal dict
              每 signal 含 signal_type / signal_date (YYYY-MM-DD) / signal_title / signal_detail
        llm:  LLMCaller 实例 or None · None → 静态 prior fallback
        reference_date: datetime · 测试可注入固定时间 · 默认 now

    Returns:
        {
            "signal_density": float ∈ [0, 1],  (4 位精度)
            "signal_density_reason": str (空 = 正常 · 非空 = 降级原因合并),
        }

    设计:
      L1: per-signal recency_weight (Python · per shared.evidence_freshness)
      L2: per-signal salience (LLM or static prior · step 2 接 LLM)
      L3: clamp01(sum(L1 × L2) / SIGNAL_DENSITY_NORMALIZATION_DIVISOR)

    Edge cases:
      - signals 空 → 0.0 + reason="未能自动填写: no_signals"
      - 全 signal 缺 signal_date → recency_w=0 → density=0 + reason="missing_dates"
      - LLM 不可达 / 越界 / 异常 → 单 signal fallback static + reason 合并
    """
    signals = item.get("signals") or []
    if not signals:
        return {
            "signal_density": 0.0,
            "signal_density_reason": "未能自动填写: no_signals",
        }

    reasons: list[str] = []

    # L2: salience batch (概率性 · LLM 1 次 call 全 candidate · fallback static)
    saliences, salience_reason = _compute_saliences_batch(signals, llm=llm)
    if salience_reason:
        reasons.append(salience_reason)

    total_weight: float = 0.0
    valid_dates = 0

    for sig, sal in zip(signals, saliences):
        # L1: freshness recency_weight (确定性 · Python)
        evidence_date = sig.get("signal_date") or sig.get("evidence_date") or ""
        fd = compute_freshness_days(evidence_date, reference_date=reference_date)
        if fd is not None:
            valid_dates += 1
        recency_w = compute_recency_weight(fd)

        total_weight += recency_w * sal

    density = min(1.0, total_weight / SIGNAL_DENSITY_NORMALIZATION_DIVISOR)
    density = round(_clamp01(density), 4)

    if valid_dates == 0:
        # 所有 signal 缺 signal_date · density 不可信 · 标降级
        return {
            "signal_density": 0.0,
            "signal_density_reason": "未能自动填写: missing_dates",
        }

    # reason 合并 · 保留 evidence (不去重 · 多 LLM 失败 = 多 evidence)
    reason_str = ", ".join(reasons) if reasons else ""
    return {
        "signal_density": density,
        "signal_density_reason": reason_str,
    }


__all__ = [
    "SIGNAL_DENSITY_NORMALIZATION_DIVISOR",
    "WINDOW_DAYS",
    "SIGNAL_TYPE_TO_CLAIM",
    "STATIC_SALIENCE_PRIOR",
    "UNKNOWN_SALIENCE",
    "signal_type_to_claim_type",
    "compute_signal_salience",
    "compute_signal_density",
]
