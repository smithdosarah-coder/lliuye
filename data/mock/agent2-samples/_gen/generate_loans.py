"""
Agent2 historical loan samples generator (Phase 3-Final track 8a).

Anti-result-orientation 5 principles compliance (CLAUDE.md §3.5):
1. Blind testing  — difficulty tier maintained internally; no answer fields in output.
2. Difficulty stratification — A_clean 60% / B_marginal 20% / C_hard 15% / D_extreme 5%.
3. Real-source anchoring — field set per central bank credit report observable
   signals + retail bank credit SOP (current ratio / debt ratio / ROE / revenue
   yoy / net margin / credit score / overdue history / query frequency / cross-
   province debit etc.).
4. Desensitized recreation — synthesized loan_id only; no real entity data.
5. Environment boundary — Agent2 all internal modeling, external NOT mocked.

Output: data/mock/agent2-samples/loans.csv
- 7500 rows + 1 header row
- 29 columns including unique answer column `days_past_due`
- ~50/50 corp/retail mix (corp samples have company_age_years + 4 fin metrics)
- Random seed = 42 (reproducible)

Acceptance hard-line (DF-P3-1~10):
- 0 answer fields (no difficulty / label / is_bad_loan / risk_level / optimal_action)
- days_past_due distribution: 0=55-65% · 1-30=15-25% · 31-90=10-18% · 90+=3-8%
- collateral_type three-way 10-60% per bucket
- corp share 30-70% of total
- rate_pct 3-30, loan_amount_wan 10-2000, credit_score 350-900, no NaN

Usage: py data/mock/agent2-samples/_gen/generate_loans.py
"""
from __future__ import annotations

import csv
import random
from pathlib import Path

SEED = 42
N_ROWS = 7500
OUT_PATH = Path(__file__).resolve().parent.parent / "loans.csv"

# ---------------------------------------------------------------------------
# PM-side tier weights (internal · NOT in output)
# ---------------------------------------------------------------------------
TIER_WEIGHTS = [
    ("A_clean", 0.60),
    ("B_marginal", 0.20),
    ("C_hard", 0.15),
    ("D_extreme", 0.05),
]

# ---------------------------------------------------------------------------
# Reference enumerations (no answer-field leak)
# ---------------------------------------------------------------------------
INDUSTRIES_L1 = [
    ("制造业", 0.25),
    ("批发零售", 0.15),
    ("建筑业", 0.12),
    ("信息技术", 0.08),
    ("住宿餐饮", 0.06),
    ("租赁商服", 0.06),
    ("交通运输", 0.05),
    ("居民服务", 0.05),
    ("房地产", 0.05),
    ("科学研究", 0.03),
    ("金融业", 0.03),
    ("农林牧渔", 0.02),
    ("教育", 0.02),
    ("采矿业", 0.02),
    ("电力燃气", 0.01),
]

REGIONS = [
    ("华东", 0.25),
    ("华南", 0.18),
    ("华北", 0.15),
    ("华中", 0.12),
    ("西南", 0.12),
    ("东北", 0.10),
    ("西北", 0.08),
]

EDUCATIONS = [
    ("高中及以下", 0.35),
    ("大专", 0.30),
    ("本科", 0.30),
    ("硕士", 0.04),
    ("博士", 0.01),
]

MARRIAGES = [
    ("已婚", 0.50),
    ("未婚", 0.30),
    ("离异", 0.17),
    ("丧偶", 0.03),
]

SCALES = [
    ("小型", 0.60),
    ("中型", 0.30),
    ("大型", 0.10),
]

COLLATERALS = [
    ("抵押", 0.35),
    ("保证", 0.35),
    ("信用", 0.30),
]

PURPOSES_CORP = ["流动资金", "设备购置", "原材料采购", "技术改造", "经营周转", "应收账款融资"]
PURPOSES_RETAIL = ["消费", "装修", "经营周转", "流动资金"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def weighted_choice(items: list[tuple[str, float]]) -> str:
    r = random.random()
    cum = 0.0
    for label, w in items:
        cum += w
        if r < cum:
            return label
    return items[-1][0]


def pick_tier() -> str:
    return weighted_choice(TIER_WEIGHTS)


def round2(x: float) -> str:
    return f"{x:.2f}"


def round1(x: float) -> str:
    return f"{x:.1f}"


# ---------------------------------------------------------------------------
# Tier-conditioned credit profile (internal · drives signals + dpd)
# ---------------------------------------------------------------------------
def credit_profile(tier: str) -> dict:
    if tier == "A_clean":
        return dict(
            credit_score=random.randint(700, 900),
            past_overdue_1y=0 if random.random() < 0.92 else random.randint(0, 1),
            current_overdue=0,
            guarantee_times=random.randint(0, 1),
            query_3m=random.randint(0, 6),
            stddev=round(random.uniform(0.05, 0.20), 2),
            large_debit=random.randint(0, 3),
            cross_prov=random.randint(0, 2),
            rate_lo=3.5, rate_hi=7.5,
            cur_ratio_lo=1.5, cur_ratio_hi=3.5,
            debt_ratio_lo=0.20, debt_ratio_hi=0.55,
            roe_lo=8.0, roe_hi=25.0,
            yoy_lo=5.0, yoy_hi=30.0,
            margin_lo=8.0, margin_hi=25.0,
        )
    if tier == "B_marginal":
        return dict(
            credit_score=random.randint(600, 720),
            past_overdue_1y=random.randint(0, 2),
            current_overdue=random.choice([0, 0, 0, 1]),
            guarantee_times=random.randint(0, 3),
            query_3m=random.randint(2, 12),
            stddev=round(random.uniform(0.15, 0.40), 2),
            large_debit=random.randint(1, 8),
            cross_prov=random.randint(0, 5),
            rate_lo=6.0, rate_hi=12.0,
            cur_ratio_lo=0.95, cur_ratio_hi=1.60,
            debt_ratio_lo=0.45, debt_ratio_hi=0.78,
            roe_lo=0.0, roe_hi=12.0,
            yoy_lo=-10.0, yoy_hi=15.0,
            margin_lo=0.0, margin_hi=10.0,
        )
    if tier == "C_hard":
        return dict(
            credit_score=random.randint(500, 620),
            past_overdue_1y=random.randint(1, 6),
            current_overdue=random.randint(0, 2),
            guarantee_times=random.randint(1, 6),
            query_3m=random.randint(5, 18),
            stddev=round(random.uniform(0.30, 0.70), 2),
            large_debit=random.randint(4, 15),
            cross_prov=random.randint(2, 12),
            rate_lo=10.0, rate_hi=18.0,
            cur_ratio_lo=0.55, cur_ratio_hi=1.05,
            debt_ratio_lo=0.65, debt_ratio_hi=1.00,
            roe_lo=-15.0, roe_hi=5.0,
            yoy_lo=-30.0, yoy_hi=5.0,
            margin_lo=-10.0, margin_hi=5.0,
        )
    # D_extreme
    return dict(
        credit_score=random.randint(350, 540),
        past_overdue_1y=random.randint(3, 12),
        current_overdue=random.randint(1, 3),
        guarantee_times=random.randint(2, 10),
        query_3m=random.randint(10, 30),
        stddev=round(random.uniform(0.50, 1.20), 2),
        large_debit=random.randint(8, 30),
        cross_prov=random.randint(5, 25),
        rate_lo=14.0, rate_hi=28.0,
        cur_ratio_lo=0.30, cur_ratio_hi=0.80,
        debt_ratio_lo=0.85, debt_ratio_hi=1.50,
        roe_lo=-50.0, roe_hi=0.0,
        yoy_lo=-80.0, yoy_hi=0.0,
        margin_lo=-30.0, margin_hi=0.0,
    )


def days_past_due_for(tier: str) -> int:
    """Tier-conditioned dpd · with light noise so KS isn't 1.0."""
    r = random.random()
    if tier == "A_clean":
        if r < 0.95:
            return 0
        return random.randint(1, 7)
    if tier == "B_marginal":
        if r < 0.05:
            return 0
        if r < 0.95:
            return random.randint(1, 30)
        return random.randint(31, 50)
    if tier == "C_hard":
        if r < 0.05:
            return random.randint(1, 30)
        if r < 0.95:
            return random.randint(31, 90)
        return random.randint(91, 150)
    # D_extreme
    if r < 0.10:
        return random.randint(31, 90)
    if r < 0.70:
        return random.randint(91, 180)
    return random.randint(181, 270)


# ---------------------------------------------------------------------------
# Loan-structure sampler (corp/retail, tier-aware)
# ---------------------------------------------------------------------------
def loan_structure(is_corp: bool, tier: str, prof: dict) -> tuple[float, int, float, str, str]:
    if is_corp:
        if tier == "A_clean":
            amount = round(random.uniform(100, 2000), 2)
        elif tier == "D_extreme":
            amount = round(random.uniform(200, 1500), 2)
        else:
            amount = round(random.uniform(50, 1000), 2)
    else:
        if tier == "A_clean":
            amount = round(random.uniform(10, 200), 2)
        else:
            amount = round(random.uniform(15, 300), 2)

    term_bucket = random.random()
    if term_bucket < 0.30:
        term = random.choice([3, 6, 9, 12])
    elif term_bucket < 0.80:
        term = random.choice([12, 18, 24, 30, 36])
    else:
        term = random.choice([36, 48, 60])

    rate = round(random.uniform(prof["rate_lo"], prof["rate_hi"]), 2)
    rate = max(3.0, min(rate, 30.0))

    collateral = weighted_choice(COLLATERALS)
    purpose = random.choice(PURPOSES_CORP if is_corp else PURPOSES_RETAIL)
    return amount, term, rate, collateral, purpose


# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------
FIELDS = [
    "loan_id",
    "applicant_age", "marriage", "education", "job_tenure_months", "monthly_income_cny",
    "company_age_years", "industry_l1", "scale", "region",
    "current_ratio", "debt_ratio", "roe", "revenue_yoy", "net_margin",
    "loan_amount_wan", "term_months", "rate_pct", "collateral_type", "purpose",
    "credit_score", "past_overdue_count_1y", "current_overdue_count",
    "guarantee_times_1y", "query_times_3m",
    "bank_balance_stddev_3m", "large_debit_count_1m", "cross_province_count_1m",
    "days_past_due",
]


def build_row(idx: int) -> dict:
    tier = pick_tier()
    is_corp = random.random() < 0.50
    prof = credit_profile(tier)

    age = random.randint(22, 65)
    marriage = weighted_choice(MARRIAGES)
    education = weighted_choice(EDUCATIONS)
    tenure = max(0, int(random.gauss(60, 50)))
    tenure = min(tenure, 480)

    if tier == "A_clean":
        income = int(random.uniform(8000, 80000))
    elif tier == "B_marginal":
        income = int(random.uniform(5000, 30000))
    elif tier == "C_hard":
        income = int(random.uniform(3500, 20000))
    else:
        income = int(random.uniform(3000, 15000))

    region = weighted_choice(REGIONS)

    if is_corp:
        company_age = round(random.uniform(0.5, 30.0), 1)
        industry = weighted_choice(INDUSTRIES_L1)
        scale = weighted_choice(SCALES)
        current_ratio = round2(random.uniform(prof["cur_ratio_lo"], prof["cur_ratio_hi"]))
        debt_ratio = round2(random.uniform(prof["debt_ratio_lo"], prof["debt_ratio_hi"]))
        roe = round2(random.uniform(prof["roe_lo"], prof["roe_hi"]))
        yoy = round2(random.uniform(prof["yoy_lo"], prof["yoy_hi"]))
        margin = round2(random.uniform(prof["margin_lo"], prof["margin_hi"]))
    else:
        company_age = ""
        industry = ""
        scale = ""
        current_ratio = ""
        debt_ratio = ""
        roe = ""
        yoy = ""
        margin = ""

    amount, term, rate, collateral, purpose = loan_structure(is_corp, tier, prof)

    dpd = days_past_due_for(tier)

    return {
        "loan_id": f"L{idx:06d}",
        "applicant_age": age,
        "marriage": marriage,
        "education": education,
        "job_tenure_months": tenure,
        "monthly_income_cny": income,
        "company_age_years": company_age,
        "industry_l1": industry,
        "scale": scale,
        "region": region,
        "current_ratio": current_ratio,
        "debt_ratio": debt_ratio,
        "roe": roe,
        "revenue_yoy": yoy,
        "net_margin": margin,
        "loan_amount_wan": round2(amount),
        "term_months": term,
        "rate_pct": round2(rate),
        "collateral_type": collateral,
        "purpose": purpose,
        "credit_score": prof["credit_score"],
        "past_overdue_count_1y": prof["past_overdue_1y"],
        "current_overdue_count": prof["current_overdue"],
        "guarantee_times_1y": prof["guarantee_times"],
        "query_times_3m": prof["query_3m"],
        "bank_balance_stddev_3m": round2(prof["stddev"]),
        "large_debit_count_1m": prof["large_debit"],
        "cross_province_count_1m": prof["cross_prov"],
        "days_past_due": dpd,
    }


def main() -> None:
    random.seed(SEED)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for i in range(1, N_ROWS + 1):
            writer.writerow(build_row(i))
    print(f"wrote {N_ROWS} rows -> {OUT_PATH}")


if __name__ == "__main__":
    main()
