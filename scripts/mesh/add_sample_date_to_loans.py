#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""一次性脚本: 给 data/mock/agent2-samples/loans.csv 加 sample_date 列.

per RFC freshness-claim-loan-sample.md §3 R3 难度分层 (反 5 原则 #2):
- 80% 近 12 月 (2025-05-09 → 2026-05-09 · LOAN_SAMPLE 365d 内 · fresh/recent)
- 20% 12-36 月 (2023-05-09 → 2025-05-09 · 部分 stale · 部分 BACKTEST_FIXTURE 仍 fresh)

deterministic seed=42 · 任何人重跑结果一致.

用法: py scripts/mesh/add_sample_date_to_loans.py
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "mock" / "agent2-samples" / "loans.csv"
SEED = 42
TODAY = date(2026, 5, 9)


def gen_sample_date(rng: random.Random) -> str:
    """80/20 分层: 80% 近 12 月 · 20% 12-36 月."""
    if rng.random() < 0.8:
        # 近 12 月 · 0-365 days ago
        days_ago = rng.randint(0, 365)
    else:
        # 12-36 月 · 365-1095 days ago
        days_ago = rng.randint(366, 1095)
    return (TODAY - timedelta(days=days_ago)).isoformat()


def main() -> int:
    rng = random.Random(SEED)

    rows: list[list[str]] = []
    with CSV_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        if "sample_date" in header:
            print(f"[add-sample-date] sample_date 已存在 · skip (path={CSV_PATH})")
            return 0
        new_header = header + ["sample_date"]
        rows.append(new_header)
        for row in reader:
            sample_date = gen_sample_date(rng)
            rows.append(row + [sample_date])

    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    # 统计分布
    fresh = sum(
        1 for r in rows[1:]
        if (TODAY - date.fromisoformat(r[-1])).days <= 365
    )
    aged = len(rows) - 1 - fresh
    print(f"[add-sample-date] 写入 {len(rows) - 1} 行 · header +1 col")
    print(f"[add-sample-date]   近 12 月 (≤ 365d): {fresh} ({fresh / (len(rows) - 1):.1%})")
    print(f"[add-sample-date]   12-36 月 (366-1095d): {aged} ({aged / (len(rows) - 1):.1%})")
    print(f"[add-sample-date] target 80/20 · seed={SEED} · today={TODAY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
