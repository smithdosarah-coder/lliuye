from __future__ import annotations

import re
from dataclasses import dataclass, field


_CANONICAL_PERIOD_RE = re.compile(r"^20\d{2}(?:\.\d{1,2})?$")


@dataclass
class PeriodAlignmentPlan:
    matched: list[tuple[int, str]] = field(default_factory=list)
    to_insert: list[tuple[int, str, str]] = field(default_factory=list)


def normalize_period(s: str) -> str:
    """Normalize common period strings to canonical 'YYYY' or 'YYYY.M'."""
    text = "" if s is None else str(s).strip()
    if not text:
        return ""

    text = text.replace("\uff08", "(").replace("\uff09", ")")
    text = text.replace("\uff0f", "/").replace("-", ".").replace("/", ".")
    text = re.sub(r"\(\u65b0\u589e\)$", "", text).strip()

    range_match = re.search(
        r"(20\d{2})\u5e74\s*\d{1,2}\s*[.\-~\u81f3]\s*(0?[1-9]|1[0-2])\u6708",
        text,
    )
    if range_match:
        year = range_match.group(1)
        month = int(range_match.group(2))
        return year if month >= 12 else f"{year}.{month}"

    month_match = re.search(r"(20\d{2})\s*[.]\s*(0?[1-9]|1[0-2])(?:\D|$)", text)
    if not month_match:
        month_match = re.search(r"(20\d{2})\u5e74\s*(0?[1-9]|1[0-2])\u6708", text)
    if not month_match:
        month_match = re.search(
            r"(20\d{2})\u5e74\s*(0?[1-9]|1[0-2])\u6708(?:\u672b|\u5e95|\u6b62|\u62a5\u8868)?",
            text,
        )
    if month_match:
        year = month_match.group(1)
        month = int(month_match.group(2))
        return year if month >= 12 else f"{year}.{month}"

    year_match = re.search(
        r"(20\d{2})\u5e74?(?:\u672b|\u5e95|\u5ea6|\u5e74\u5ea6|\u5e74\u62a5|12\u670831\u65e5)?(?:\D|$)",
        text,
    )
    if year_match:
        return year_match.group(1)

    direct_month_match = re.fullmatch(r"(20\d{2})\.(0?[1-9]|1[0-2])", text)
    if direct_month_match:
        year = direct_month_match.group(1)
        month = int(direct_month_match.group(2))
        return year if month >= 12 else f"{year}.{month}"

    direct_year_match = re.fullmatch(r"(20\d{2})", text)
    if direct_year_match:
        return direct_year_match.group(1)

    return text


def period_sort_key(p: str) -> tuple[int, int, int]:
    """Sort interim periods before same-year annual periods."""
    normalized = normalize_period(p)
    month_match = re.fullmatch(r"(20\d{2})\.(\d{1,2})", normalized)
    if month_match:
        return int(month_match.group(1)), int(month_match.group(2)), 0
    year_match = re.fullmatch(r"(20\d{2})", normalized)
    if year_match:
        return int(year_match.group(1)), 12, 1
    return 9999, 99, 99


def build_alignment_plan(
    template_periods: list[str],
    material_periods: list[str],
) -> PeriodAlignmentPlan:
    """Build a reusable alignment plan between template and material periods."""
    normalized_template = []
    for period in template_periods or []:
        normalized = normalize_period(period)
        if _CANONICAL_PERIOD_RE.fullmatch(normalized):
            normalized_template.append(normalized)

    normalized_material = []
    seen_material = set()
    for period in material_periods or []:
        normalized = normalize_period(period)
        if _CANONICAL_PERIOD_RE.fullmatch(normalized) and normalized not in seen_material:
            normalized_material.append(normalized)
            seen_material.add(normalized)

    template_set = set(normalized_template)
    matched = [
        (idx, period)
        for idx, period in enumerate(normalized_template)
        if period in seen_material
    ]

    ordered_missing = sorted(
        (period for period in normalized_material if period not in template_set),
        key=period_sort_key,
    )

    plan = PeriodAlignmentPlan(matched=matched)
    if not ordered_missing:
        return plan

    template_order = list(normalized_template)
    template_order_set = set(template_order)

    for period in ordered_missing:
        insert_side = "right"
        anchor_idx = len(template_order) - 1 if template_order else 0

        same_year_interim_idx = None
        same_year_annual_idx = None
        period_match = re.fullmatch(r"(20\d{2})(?:\.(\d{1,2}))?", period)
        year = period_match.group(1) if period_match else None
        is_interim = bool(period_match and period_match.group(2))

        if year:
            for idx, existing in enumerate(template_order):
                if existing == year:
                    same_year_annual_idx = idx
                elif existing.startswith(f"{year}."):
                    same_year_interim_idx = idx

        if is_interim and same_year_annual_idx is not None:
            anchor_idx = same_year_annual_idx
            insert_side = "left"
        elif (not is_interim) and same_year_interim_idx is not None:
            anchor_idx = same_year_interim_idx
            insert_side = "right"
        else:
            combined = sorted(set(template_order) | {period}, key=period_sort_key)
            position = combined.index(period)
            left_anchor = None
            right_anchor = None
            for left in reversed(combined[:position]):
                if left in template_order_set:
                    left_anchor = left
                    break
            for right in combined[position + 1:]:
                if right in template_order_set:
                    right_anchor = right
                    break

            if right_anchor is not None:
                anchor_idx = template_order.index(right_anchor)
                insert_side = "left"
            elif left_anchor is not None:
                anchor_idx = template_order.index(left_anchor)
                insert_side = "right"
            else:
                anchor_idx = 0
                insert_side = "right"

        plan.to_insert.append((anchor_idx, period, insert_side))

        # Keep evolving order in sync so later inserts use updated coordinates.
        insert_pos = anchor_idx + (1 if insert_side == "right" else 0)
        if insert_pos < 0:
            insert_pos = 0
        if insert_pos > len(template_order):
            insert_pos = len(template_order)
        template_order.insert(insert_pos, period)
        template_order_set.add(period)

    return plan
