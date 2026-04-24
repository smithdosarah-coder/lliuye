"""
Task A · 在贷客户池 clients.csv 生成器。

产物：data/mock/alert-pool/clients.csv · 180 行薄画像 + 授信结构。
零答案硬线：见 onboarding §2 "零答案字段红线" —— CSV 列只含 onboarding 字段表里
列出的 13 个，不添加任何反 5 原则 §1 盲测法禁止的标注列。档位/倾向仅在
profiles.py 内流转，不输出。

对照 onboarding §2 Task A 字段清单：
  client_id, company_name, industry_l1, industry_l2, region, scale,
  credit_line_wan, balance_wan, interest_rate, term_months, product,
  first_draw_date, last_review_date
其中 region = 省-市-区 三级拼接。
"""

from __future__ import annotations

import csv
from pathlib import Path

from profiles import generate_profiles


def main() -> None:
    profiles = generate_profiles()
    out_path = Path(__file__).resolve().parent.parent / "clients.csv"

    columns = [
        "client_id",
        "company_name",
        "industry_l1",
        "industry_l2",
        "region",
        "scale",
        "credit_line_wan",
        "balance_wan",
        "interest_rate",
        "term_months",
        "product",
        "first_draw_date",
        "last_review_date",
    ]

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(columns)
        for p in profiles:
            region = f"{p.province}{p.city}{p.district}"
            writer.writerow([
                p.client_id,
                p.company_name,
                p.industry_l1,
                p.industry_l2,
                region,
                p.scale,
                p.credit_line_wan,
                p.balance_wan,
                f"{p.interest_rate:.2f}",
                p.term_months,
                p.product,
                p.first_draw_date,
                p.last_review_date,
            ])

    print(f"wrote {out_path} · rows={len(profiles)}")


if __name__ == "__main__":
    main()
