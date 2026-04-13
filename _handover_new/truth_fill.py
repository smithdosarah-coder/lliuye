# -*- coding: utf-8 -*-
"""truth_fill.py

Truth-first deterministic fillers that bypass the LLM.

These functions are intentionally conservative: if KB or parsed statements
lack evidence, the target cells stay blank rather than guessed.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Callable

from period_matcher import normalize_period, period_sort_key


def _norm(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", "", s)
    s = s.replace("\u3000", "")
    s = s.replace("\uff08", "(").replace("\uff09", ")")
    s = s.replace("\uff1a", ":")
    return s


def _contains(text: str, needles: list[str]) -> bool:
    t = _norm(text)
    return any(_norm(nd) in t for nd in needles if nd)


def _find_col(headers: list[str], needles: list[str]) -> int | None:
    hn = [_norm(h) for h in headers]
    normalized_needles = [_norm(nd) for nd in needles if _norm(nd)]

    for n in normalized_needles:
        for i, h in enumerate(hn):
            if h and h == n:
                return i

    for n in normalized_needles:
        for i, h in enumerate(hn):
            if not h:
                continue
            if n in h:
                return i
    return None


def _write_cell_text(cell, text: str) -> None:
    if cell is None:
        return
    try:
        text = "" if text is None else str(text)
        if cell.paragraphs:
            p = cell.paragraphs[0]
            if p.runs:
                p.runs[0].text = text
                for r in p.runs[1:]:
                    r.text = ""
            else:
                new_run = p.add_run(text)
                template_rpr = None
                for other_p in cell.paragraphs:
                    for other_run in other_p.runs:
                        rpr = other_run._r.rPr
                        if rpr is not None:
                            template_rpr = deepcopy(rpr)
                            break
                    if template_rpr is not None:
                        break
                if template_rpr is not None:
                    new_run._r.insert(0, template_rpr)
        else:
            cell.text = text
    except Exception:
        try:
            cell.text = str(text)
        except Exception:
            pass


def _infer_data_start_row(nt) -> int:
    data_start = 1
    try:
        if len(nt.rows) >= 2:
            row1_texts = [c.text.strip() for c in nt.rows[1].cells]
            row1_filled = sum(1 for t in row1_texts if t.strip())
            row1_numeric = sum(
                1 for t in row1_texts if t and re.match(r"^[\d,.\-%]+$", t.replace(" ", ""))
            )
            if (
                row1_numeric == 0
                and row1_filled > len(row1_texts) * 0.5
                and all(len(t) < 30 for t in row1_texts if t)
            ):
                data_start = 2
    except Exception:
        data_start = 1
    return data_start


def _first_nonempty(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _value_by_key_contains(item: dict[str, Any], key_needles: list[str]) -> str:
    normalized_needles = [_norm(nd) for nd in key_needles if _norm(nd)]

    for n in normalized_needles:
        for k, v in (item or {}).items():
            if v is None:
                continue
            if _norm(str(k)) == n:
                text = str(v).strip()
                if text:
                    return text

    for k, v in (item or {}).items():
        if v is None:
            continue
        if _contains(str(k), key_needles):
            text = str(v).strip()
            if text:
                return text
    return ""


def _drop_filled_from_empty(ts) -> None:
    try:
        filled_pos = set(ts.existing_data.keys())
        ts.empty_cells = [(r, c) for (r, c) in ts.empty_cells if (r, c) not in filled_pos]
    except Exception:
        pass


def prefill_supply_chain_tables(
    doc,
    nested_tables: list[Any],
    kb: dict[str, Any],
    log: Callable[[str], None] | None = None,
) -> int:
    """Fill upstream/downstream Top5 tables using KB facts."""
    facts = (kb or {}).get("facts", {}) or {}
    upstream = facts.get("upstream_top5")
    downstream = facts.get("downstream_top5")

    if not isinstance(upstream, list) and not isinstance(downstream, list):
        return 0

    filled = 0

    def _extract_header_period_columns(headers: list[str], metric_keyword: str) -> dict[tuple[str, str], int]:
        period_cols: dict[tuple[str, str], int] = {}
        for ci, header in enumerate(headers):
            hs = str(header or "").strip()
            period = normalize_period(hs)
            if not re.fullmatch(r"20\d{2}(?:\.\d{1,2})?", period):
                continue
            if metric_keyword not in hs:
                continue
            metric = "pct" if "占比" in hs else "amt"
            period_cols[(metric, period)] = ci
        return period_cols

    def _resolve_relative_periods(periods: list[str]) -> tuple[str | None, str | None]:
        annuals = sorted(
            [p for p in periods if re.fullmatch(r"20\d{2}", p)],
            key=period_sort_key,
        )
        interim = sorted(
            [p for p in periods if re.fullmatch(r"20\d{2}\.\d{1,2}", p)],
            key=period_sort_key,
        )
        annual_period = annuals[-1] if annuals else None
        interim_period = interim[-1] if interim else None
        return annual_period, interim_period

    def _log(msg: str):
        if log:
            try:
                log(msg)
            except Exception:
                pass

    up_markers = ["\u4e3b\u8981\u4e0a\u6e38\u4f9b\u5e94\u5546", "\u4e0a\u6e38\u4f9b\u5e94\u5546"]
    dn_markers = ["\u4e3b\u8981\u4e0b\u6e38\u9500\u552e\u5ba2\u6237", "\u4e0b\u6e38\u9500\u552e\u5ba2\u6237"]

    for ts in nested_tables or []:
        try:
            headers = [h or "" for h in (ts.header_row or [])]
            header_text = " ".join(h for h in headers if h)
        except Exception:
            continue

        is_up = isinstance(upstream, list) and upstream and _contains(header_text, up_markers)
        is_dn = isinstance(downstream, list) and downstream and _contains(header_text, dn_markers)
        if not is_up and not is_dn:
            continue

        try:
            parent_cell = doc.tables[ts.cell_path[0]].rows[ts.cell_path[1]].cells[ts.cell_path[2]]
            nt = parent_cell.tables[ts.nested_table_idx]
        except Exception:
            continue

        data_start = _infer_data_start_row(nt)
        items = upstream if is_up else downstream
        if not isinstance(items, list) or not items:
            continue

        if is_up:
            col_name = _find_col(headers, ["\u4e3b\u8981\u4e0a\u6e38\u4f9b\u5e94\u5546", "\u4e0a\u6e38\u4f9b\u5e94\u5546", "\u4f9b\u5e94\u5546"])
            col_product = _find_col(headers, ["\u91c7\u8d2d\u5546\u54c1", "\u91c7\u8d2d\u5185\u5bb9", "\u5546\u54c1"])
            period_cols = _extract_header_period_columns(headers, "\u91c7\u8d2d")
        else:
            col_name = _find_col(headers, ["\u4e3b\u8981\u4e0b\u6e38\u9500\u552e\u5ba2\u6237", "\u4e0b\u6e38\u9500\u552e\u5ba2\u6237", "\u5ba2\u6237"])
            col_product = _find_col(headers, ["\u9500\u552e\u4ea7\u54c1", "\u9500\u552e\u5546\u54c1", "\u9500\u552e\u5185\u5bb9", "\u5546\u54c1"])
            period_cols = _extract_header_period_columns(headers, "\u9500\u552e")

        annual_period, interim_period = _resolve_relative_periods(
            [period for _, period in period_cols.keys()]
        )
        col_amt = period_cols.get(("amt", annual_period)) if annual_period else None
        col_pct = period_cols.get(("pct", annual_period)) if annual_period else None
        col_amt_ytd = period_cols.get(("amt", interim_period)) if interim_period else None
        col_pct_ytd = period_cols.get(("pct", interim_period)) if interim_period else None

        col_settle = _find_col(headers, ["\u7ed3\u7b97\u65b9\u5f0f"])
        col_term = _find_col(headers, ["\u8d26\u671f"])
        col_years = _find_col(headers, ["\u5408\u4f5c\u5e74\u9650"])

        max_rows = min(5, len(items), max(0, len(nt.rows) - data_start))
        for i in range(max_rows):
            ri = data_start + i
            row = nt.rows[ri]
            item = items[i]
            if not isinstance(item, dict):
                continue

            values = {
                col_name: _value_by_key_contains(item, ["\u4e0a\u6e38\u4f9b\u5e94\u5546", "\u4e0b\u6e38\u9500\u552e\u5ba2\u6237", "\u5ba2\u6237", "\u4f9b\u5e94\u5546"]),
                col_product: _value_by_key_contains(item, ["\u91c7\u8d2d\u5546\u54c1", "\u9500\u552e\u4ea7\u54c1", "\u9500\u552e\u5546\u54c1", "\u5546\u54c1", "\u5185\u5bb9"]),
                col_amt: _value_by_key_contains(item, ["\u4e0a\u5e74\u91c7\u8d2d\u989d", "\u4e0a\u5e74\u9500\u552e\u989d", "\u4e0a\u5e74\u91d1\u989d"]),
                col_pct: _value_by_key_contains(item, ["\u4e0a\u5e74\u91c7\u8d2d\u989d\u5360\u6bd4", "\u4e0a\u5e74\u9500\u552e\u989d\u5360\u6bd4", "\u5360\u6bd4"]),
                col_amt_ytd: _value_by_key_contains(item, ["\u4eca\u5e741-9\u6708\u91c7\u8d2d\u989d", "\u4eca\u5e741-9\u6708\u9500\u552e\u989d", "1-9\u6708\u91d1\u989d"]),
                col_pct_ytd: _value_by_key_contains(item, ["\u4eca\u5e741-9\u6708\u91c7\u8d2d\u989d\u5360\u6bd4", "\u4eca\u5e741-9\u6708\u9500\u552e\u989d\u5360\u6bd4"]),
                col_settle: _value_by_key_contains(item, ["\u7ed3\u7b97\u65b9\u5f0f"]),
                col_term: _value_by_key_contains(item, ["\u8d26\u671f"]),
                col_years: _value_by_key_contains(item, ["\u5408\u4f5c\u5e74\u9650"]),
            }

            for ci, value in values.items():
                if ci is None or ci >= len(row.cells) or not value:
                    continue
                if row.cells[ci].text.strip():
                    continue
                _write_cell_text(row.cells[ci], value)
                filled += 1
                ts.existing_data[(ri, ci)] = value

        for ri in range(data_start + max_rows, len(nt.rows)):
            row = nt.rows[ri]
            row_text = " ".join((c.text or "").strip() for c in row.cells)
            if any(marker in row_text for marker in ["已核实", "银行账户流水", "账户流水"]):
                for ci in range(len(row.cells)):
                    _write_cell_text(row.cells[ci], "")
                    ts.existing_data.pop((ri, ci), None)

        _drop_filled_from_empty(ts)
        if max_rows:
            _log(f"KB prefill {ts.table_id}: {'upstream' if is_up else 'downstream'} {max_rows} rows")

    return filled


def prefill_kb_structured_tables(
    doc,
    nested_tables: list[Any],
    kb: dict[str, Any],
    log: Callable[[str], None] | None = None,
) -> int:
    """Fill other objective KB-driven tables (affiliates/financing/R&D)."""
    facts = (kb or {}).get("facts", {}) or {}
    filled = 0

    def _log(msg: str):
        if log:
            try:
                log(msg)
            except Exception:
                pass

    for ts in nested_tables or []:
        headers = [h or "" for h in (ts.header_row or [])]
        header_text = " ".join(headers)

        try:
            parent_cell = doc.tables[ts.cell_path[0]].rows[ts.cell_path[1]].cells[ts.cell_path[2]]
            nt = parent_cell.tables[ts.nested_table_idx]
        except Exception:
            continue

        # Affiliates
        if (
            isinstance(facts.get("affiliates"), list)
            and facts.get("affiliates")
            and _contains(header_text, ["\u5173\u8054", "\u6301\u80a1", "\u5f80\u6765", "\u4f01\u4e1a"])
        ):
            items = facts.get("affiliates") or []
            data_start = _infer_data_start_row(nt)
            max_rows = max(0, len(nt.rows) - data_start)
            if nt.rows and nt.rows[-1].cells and _contains(nt.rows[-1].cells[0].text or "", ["\u6ce8", "\u8bf4\u660e"]):
                max_rows -= 1
            max_rows = min(max_rows, len(items))

            col_specs = {
                _find_col(headers, ["\u4f01\u4e1a\u540d\u79f0", "\u5173\u8054\u4f01\u4e1a\u540d\u79f0", "\u540d\u79f0"]): ["\u4f01\u4e1a\u540d\u79f0", "\u5173\u8054\u4f01\u4e1a\u540d\u79f0", "\u540d\u79f0"],
                _find_col(headers, ["\u6210\u7acb\u65f6\u95f4"]): ["\u6210\u7acb\u65f6\u95f4"],
                _find_col(headers, ["\u80a1\u6743\u7ed3\u6784"]): ["\u80a1\u6743\u7ed3\u6784"],
                _find_col(headers, ["\u4e3b\u8425\u4e1a\u52a1\u53ca\u4ea7\u54c1", "\u4e3b\u8425\u4e1a\u52a1"]): ["\u4e3b\u8425\u4e1a\u52a1\u53ca\u4ea7\u54c1", "\u4e3b\u8425\u4e1a\u52a1"],
                _find_col(headers, ["\u6ce8\u518c\u8d44\u672c", "\u5b9e\u6536\u8d44\u672c"]): ["\u6ce8\u518c\u8d44\u672c/\u5b9e\u6536\u8d44\u672c", "\u6ce8\u518c\u8d44\u672c", "\u5b9e\u6536\u8d44\u672c"],
                _find_col(headers, ["\u4e0a\u5e74\u4e3b\u8425\u4e1a\u52a1\u6536\u5165", "\u8425\u4e1a\u6536\u5165"]): ["\u4e0a\u5e74\u4e3b\u8425\u4e1a\u52a1\u6536\u5165", "\u4e0a\u5e74\u8425\u4e1a\u6536\u5165", "\u8425\u4e1a\u6536\u5165"],
                _find_col(headers, ["\u4e0a\u5e74\u51c0\u5229\u6da6", "\u51c0\u5229\u6da6"]): ["\u4e0a\u5e74 \u51c0\u5229\u6da6", "\u4e0a\u5e74\u51c0\u5229\u6da6", "\u51c0\u5229\u6da6"],
                _find_col(headers, ["\u6700\u65b0\u878d\u8d44", "\u878d\u8d44"]): ["\u6700\u65b0\u878d\u8d44\u91d1\u989d", "\u6700\u65b0\u878d\u8d44"],
                _find_col(headers, ["\u5173\u8054\u4ea4\u6613", "\u8d44\u91d1\u5f80\u6765", "\u4e1a\u52a1\u5f80\u6765"]): ["\u4e1a\u52a1\u5f80\u6765", "\u4e1a\u52a1\u5f80\u6765\u60c5\u51b5"],
                _find_col(headers, ["\u6d89\u8bc9", "\u8bc9\u8bbc"]): ["\u6d89\u8bc9\u60c5\u51b5", "\u5907\u6ce8"],
            }

            for i in range(max_rows):
                ri = data_start + i
                row = nt.rows[ri]
                item = items[i]
                if not isinstance(item, dict):
                    continue
                for ci, keys in col_specs.items():
                    if ci is None or ci >= len(row.cells):
                        continue
                    value = _value_by_key_contains(item, keys)
                    if value and not row.cells[ci].text.strip():
                        _write_cell_text(row.cells[ci], value)
                        filled += 1
                        ts.existing_data[(ri, ci)] = value

            _drop_filled_from_empty(ts)
            if max_rows:
                _log(f"KB prefill {ts.table_id}: affiliates {max_rows} rows")
            continue

        # Financing
        if (
            isinstance(facts.get("financing"), list)
            and facts.get("financing")
            and _contains(header_text, ["\u878d\u8d44\u673a\u6784", "\u6388\u4fe1\u91d1\u989d", "\u62c5\u4fdd\u65b9\u5f0f"])
        ):
            items = facts.get("financing") or []
            data_start = _infer_data_start_row(nt)
            max_rows = max(0, len(nt.rows) - data_start)
            if nt.rows and nt.rows[-1].cells and _contains(nt.rows[-1].cells[0].text or "", ["\u6ce8", "\u8bf4\u660e"]):
                max_rows -= 1
            max_rows = min(max_rows, len(items))

            col_specs = {
                _find_col(headers, ["\u878d\u8d44\u673a\u6784"]): ["\u878d\u8d44\u673a\u6784"],
                _find_col(headers, ["\u54c1\u79cd"]): ["\u54c1\u79cd"],
                _find_col(headers, ["\u6388\u4fe1\u91d1\u989d", "\u6388\u4fe1"]): ["\u6388\u4fe1\u91d1\u989d", "\u6388\u4fe1"],
                _find_col(headers, ["\u5df2\u7528\u91d1\u989d", "\u5df2\u7528"]): ["\u5df2\u7528\u91d1\u989d", "\u5df2\u7528"],
                _find_col(headers, ["\u4e1a\u52a1\u8d77\u59cb\u65e5", "\u8d77\u59cb\u65e5"]): ["\u4e1a\u52a1\u8d77\u59cb\u65e5", "\u8d77\u59cb\u65e5"],
                _find_col(headers, ["\u4e1a\u52a1\u5230\u671f\u65e5", "\u5230\u671f\u65e5"]): ["\u4e1a\u52a1\u5230\u671f\u65e5", "\u5230\u671f\u65e5"],
                _find_col(headers, ["\u62c5\u4fdd\u65b9\u5f0f"]): ["\u62c5\u4fdd\u65b9\u5f0f"],
            }

            for i in range(max_rows):
                ri = data_start + i
                row = nt.rows[ri]
                item = items[i]
                if not isinstance(item, dict):
                    continue
                for ci, keys in col_specs.items():
                    if ci is None or ci >= len(row.cells):
                        continue
                    value = _value_by_key_contains(item, keys)
                    if value and not row.cells[ci].text.strip():
                        _write_cell_text(row.cells[ci], value)
                        filled += 1
                        ts.existing_data[(ri, ci)] = value

            _drop_filled_from_empty(ts)
            if max_rows:
                _log(f"KB prefill {ts.table_id}: financing {max_rows} rows")
            continue

        # R&D
        if (
            isinstance(facts.get("r_and_d"), list)
            and facts.get("r_and_d")
            and _contains(header_text, ["\u7814\u53d1\u8d39\u7528"])
            and _contains(header_text, ["\u5e74\u4efd"])
        ):
            by_year = {}
            for item in facts.get("r_and_d") or []:
                if not isinstance(item, dict):
                    continue
                year = _value_by_key_contains(item, ["\u5e74\u4efd"])
                if year:
                    by_year[_norm(year)] = item

            data_start = _infer_data_start_row(nt)
            col_specs = {
                _find_col(headers, ["\u5e74\u4efd"]): ["\u5e74\u4efd"],
                _find_col(headers, ["\u7814\u53d1\u8d39\u7528", "\u7814\u53d1\u6295\u5165"]): ["\u7814\u53d1\u8d39\u7528", "\u7814\u53d1\u6295\u5165"],
                _find_col(headers, ["\u7814\u53d1\u8d39\u7528\u5360\u6bd4", "\u7814\u53d1\u8d39\u7528/\u8425\u6536"]): ["\u7814\u53d1\u8d39\u7528\u5360\u6bd4", "\u7814\u53d1\u8d39\u7528/\u8425\u6536"],
                _find_col(headers, ["\u53d1\u660e\u4e13\u5229"]): ["\u53d1\u660e\u4e13\u5229", "\u53d1\u660e\u4e13\u5229\u9879\u6570"],
                _find_col(headers, ["\u5b9e\u7528\u65b0\u578b\u4e13\u5229"]): ["\u5b9e\u7528\u65b0\u578b\u4e13\u5229", "\u5b9e\u7528\u65b0\u578b\u4e13\u5229\u9879\u6570"],
            }

            for ri in range(data_start, len(nt.rows)):
                row = nt.rows[ri]
                if not row.cells:
                    continue
                year = _norm(row.cells[0].text)
                item = by_year.get(year)
                if not item:
                    continue
                for ci, keys in col_specs.items():
                    if ci is None or ci >= len(row.cells):
                        continue
                    value = _value_by_key_contains(item, keys)
                    if value and not row.cells[ci].text.strip():
                        _write_cell_text(row.cells[ci], value)
                        filled += 1
                        ts.existing_data[(ri, ci)] = value

            _drop_filled_from_empty(ts)
            _log(f"KB prefill {ts.table_id}: r_and_d")
            continue

    return filled


# ---------------------------------------------------------------------------
# New deterministic fillers (改造五)
# ---------------------------------------------------------------------------

def prefill_shareholder_table(
    doc,
    nested_tables: list[Any],
    kb: dict[str, Any],
    log: Callable[[str], None] | None = None,
) -> int:
    """Fill shareholder structure table using KB facts['shareholders'].

    Critically, this fills the *shareholder* table (股东名称/出资比例),
    NOT the affiliate table.  The semantic distinction prevents the previous
    bug where subsidiary names were inserted as shareholders.
    """
    facts = (kb or {}).get("facts", {}) or {}
    shareholders = facts.get("shareholders")
    if not isinstance(shareholders, list) or not shareholders:
        return 0

    filled = 0

    def _log(msg: str):
        if log:
            try:
                log(msg)
            except Exception:
                pass

    for ts in nested_tables or []:
        try:
            headers = [h or "" for h in (ts.header_row or [])]
            header_text = " ".join(h for h in headers if h)
        except Exception:
            continue

        # Must have shareholder-specific columns — NOT affiliate columns
        is_shareholder = (
            _contains(header_text, ["股东名称", "认缴出资", "出资比例"])
            and not _contains(header_text, ["成立时间", "净利润", "融资"])
        )
        if not is_shareholder:
            continue

        try:
            parent_cell = doc.tables[ts.cell_path[0]].rows[ts.cell_path[1]].cells[ts.cell_path[2]]
            nt = parent_cell.tables[ts.nested_table_idx]
        except Exception:
            continue

        data_start = _infer_data_start_row(nt)

        col_name = _find_col(headers, ["股东名称", "股东"])
        col_amount = _find_col(headers, ["认缴出资额", "认缴出资", "出资额", "持股数"])
        col_pct = _find_col(headers, ["出资比例%", "出资比例", "持股比例"])
        col_actual = _find_col(headers, ["实际出资额", "实际出资", "实缴出资"])
        col_form = _find_col(headers, ["出资形式", "出资方式"])

        # Find the "合计" row if it exists — we fill above it
        total_row_idx = None
        for ri in range(data_start, len(nt.rows)):
            row_text = " ".join((c.text or "").strip() for c in nt.rows[ri].cells)
            if "合计" in row_text:
                total_row_idx = ri
                break

        max_data_rows = (total_row_idx or len(nt.rows)) - data_start
        max_rows = min(max_data_rows, len(shareholders))

        for i in range(max_rows):
            ri = data_start + i
            if ri >= len(nt.rows):
                break
            row = nt.rows[ri]
            item = shareholders[i]
            if not isinstance(item, dict):
                continue

            values = {
                col_name: _value_by_key_contains(item, ["股东名称", "股东"]),
                col_amount: _value_by_key_contains(item, ["认缴出资额", "认缴出资", "出资额", "持股数"]),
                col_pct: _value_by_key_contains(item, ["出资比例%", "出资比例", "持股比例"]),
                col_actual: _value_by_key_contains(item, ["实际出资额", "实际出资", "实缴出资"]),
                col_form: _value_by_key_contains(item, ["出资形式", "出资方式"]),
            }

            for ci, value in values.items():
                if ci is None or ci >= len(row.cells) or not value:
                    continue
                if row.cells[ci].text.strip():
                    continue
                _write_cell_text(row.cells[ci], value)
                filled += 1
                ts.existing_data[(ri, ci)] = value

        _drop_filled_from_empty(ts)
        if max_rows:
            _log(f"KB prefill {ts.table_id}: shareholders {max_rows} rows")

    return filled


def prefill_asset_table(
    doc,
    nested_tables: list[Any],
    kb: dict[str, Any],
    log: Callable[[str], None] | None = None,
) -> int:
    """Fill asset tables (借款人资产 / 实控人家庭资产) using KB facts['assets']."""
    facts = (kb or {}).get("facts", {}) or {}
    assets = facts.get("assets")
    if not isinstance(assets, list) or not assets:
        return 0

    filled = 0

    def _log(msg: str):
        if log:
            try:
                log(msg)
            except Exception:
                pass

    for ts in nested_tables or []:
        try:
            headers = [h or "" for h in (ts.header_row or [])]
            header_text = " ".join(h for h in headers if h)
        except Exception:
            continue

        if not _contains(header_text, ["资产名称"]):
            continue
        if not _contains(header_text, ["所有权人", "权属", "资产类型"]):
            continue

        try:
            parent_cell = doc.tables[ts.cell_path[0]].rows[ts.cell_path[1]].cells[ts.cell_path[2]]
            nt = parent_cell.tables[ts.nested_table_idx]
        except Exception:
            continue

        data_start = _infer_data_start_row(nt)

        col_specs = {
            _find_col(headers, ["资产名称", "坐落位置"]): ["资产名称", "坐落位置"],
            _find_col(headers, ["所有权人"]): ["所有权人"],
            _find_col(headers, ["资产类型"]): ["资产类型"],
            _find_col(headers, ["权属", "权属证号"]): ["权属", "权属证号"],
            _find_col(headers, ["资产概况", "面积"]): ["资产概况", "面积"],
            _find_col(headers, ["账面", "购置价"]): ["账面", "购置价"],
            _find_col(headers, ["市场", "评估价"]): ["市场", "评估价"],
            _find_col(headers, ["自用", "出租"]): ["自用", "出租"],
            _find_col(headers, ["抵质押"]): ["抵质押"],
            _find_col(headers, ["融资金额"]): ["融资金额"],
        }

        max_rows = min(max(0, len(nt.rows) - data_start), len(assets))

        for i in range(max_rows):
            ri = data_start + i
            if ri >= len(nt.rows):
                break
            row = nt.rows[ri]
            item = assets[i]
            if not isinstance(item, dict):
                continue
            for ci, keys in col_specs.items():
                if ci is None or ci >= len(row.cells):
                    continue
                value = _value_by_key_contains(item, keys)
                if value and not row.cells[ci].text.strip():
                    _write_cell_text(row.cells[ci], value)
                    filled += 1
                    ts.existing_data[(ri, ci)] = value

        _drop_filled_from_empty(ts)
        if max_rows:
            _log(f"KB prefill {ts.table_id}: assets {max_rows} rows")

    return filled


def prefill_bank_flow_table(
    doc,
    nested_tables: list[Any],
    kb: dict[str, Any],
    log: Callable[[str], None] | None = None,
) -> int:
    """Fill bank flow verification table using KB facts['bank_flows']."""
    facts = (kb or {}).get("facts", {}) or {}
    flows = facts.get("bank_flows")
    if not isinstance(flows, list) or not flows:
        return 0

    filled = 0

    def _log(msg: str):
        if log:
            try:
                log(msg)
            except Exception:
                pass

    for ts in nested_tables or []:
        try:
            headers = [h or "" for h in (ts.header_row or [])]
            header_text = " ".join(h for h in headers if h)
        except Exception:
            continue

        if not _contains(header_text, ["开户行"]):
            continue
        if not _contains(header_text, ["流入量", "流入", "户名"]):
            continue

        try:
            parent_cell = doc.tables[ts.cell_path[0]].rows[ts.cell_path[1]].cells[ts.cell_path[2]]
            nt = parent_cell.tables[ts.nested_table_idx]
        except Exception:
            continue

        data_start = _infer_data_start_row(nt)

        col_specs = {
            _find_col(headers, ["开户行"]): ["开户行"],
            _find_col(headers, ["户名"]): ["户名"],
            _find_col(headers, ["账号"]): ["账号"],
            _find_col(headers, ["关系", "与借款人关系"]): ["关系", "与借款人关系"],
            _find_col(headers, ["时间段", "时间"]): ["时间段", "时间"],
            _find_col(headers, ["流入量", "流入"]): ["流入量", "流入"],
        }

        max_rows = min(max(0, len(nt.rows) - data_start), len(flows))

        for i in range(max_rows):
            ri = data_start + i
            if ri >= len(nt.rows):
                break
            row = nt.rows[ri]
            item = flows[i]
            if not isinstance(item, dict):
                continue
            for ci, keys in col_specs.items():
                if ci is None or ci >= len(row.cells):
                    continue
                value = _value_by_key_contains(item, keys)
                if value and not row.cells[ci].text.strip():
                    _write_cell_text(row.cells[ci], value)
                    filled += 1
                    ts.existing_data[(ri, ci)] = value

        _drop_filled_from_empty(ts)
        if max_rows:
            _log(f"KB prefill {ts.table_id}: bank_flows {max_rows} rows")

    return filled


def prefill_labeled_fields_from_kb(
    labeled_fields: list[Any],
    kb: dict[str, Any],
) -> dict[str, str]:
    """Pre-fill labeled fields (label:blank patterns) with KB facts.

    Returns a dict of {lf_id: value} for fields that can be filled
    deterministically from KB, so they don't need LLM processing.
    """
    facts = (kb or {}).get("facts", {}) or {}
    if not facts:
        return {}

    result: dict[str, str] = {}

    # Mapping: label keywords -> KB fact key
    label_to_fact = [
        (["客户经理"], "customer_manager_name"),
        (["联系电话"], "customer_manager_phone"),
        (["注册资本"], "registered_capital"),
        (["实收资本"], "paid_in_capital"),
        (["法定代表人", "法人代表"], "legal_representative"),
        (["社保人数", "上年度末社保"], "social_insurance_count"),
        (["员工人数", "上年度末员工"], lambda: facts.get("social_insurance_count") or facts.get("employee_count", "")),
        (["实际控制人持股", "股权穿透后"], "controller_share_pct"),
        (["反洗钱风险等级"], "aml_risk_level"),
        (["科技型企业评分"], None),  # can't determine from KB
    ]

    for lf in labeled_fields:
        lab = (getattr(lf, 'label', '') or '').strip()
        ctx = (getattr(lf, 'context_line', '') or '').strip()
        key_text = lab + ' ' + ctx

        for keywords, fact_key in label_to_fact:
            if not any(kw in key_text for kw in keywords):
                continue
            if fact_key is None:
                break
            if callable(fact_key):
                value = fact_key()
            else:
                value = str(facts.get(fact_key, "")).strip()
            if value:
                result[lf.lf_id] = value
            break

    return result
