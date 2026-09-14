"""
Phase 4 — Exploratory analysis on the cleaned star schema.
Replicates the DAX measure logic in pandas to surface real patterns:
trends, segment/district/dealer/plan comparisons, budget vs actual, churn.
"""
import pandas as pd
import numpy as np

pd.set_option("display.max_columns", 30)
pd.set_option("display.width", 160)
pd.set_option("display.max_rows", 60)

C = "data/clean"
dim_customer = pd.read_csv(f"{C}/dim_customer.csv")
dim_dealer = pd.read_csv(f"{C}/dim_dealer.csv")
dim_plan = pd.read_csv(f"{C}/dim_plan.csv")
dim_subscriber = pd.read_csv(f"{C}/dim_subscriber.csv", parse_dates=["join_date", "churn_date"])
dim_district = pd.read_csv(f"{C}/dim_district.csv")
fact_billing = pd.read_csv(f"{C}/fact_billing.csv", parse_dates=["date"])
fact_budget = pd.read_csv(f"{C}/fact_budget.csv", parse_dates=["date"])

def hr(t):
    print("\n" + "=" * 95 + f"\n{t}\n" + "=" * 95)

# enrich subscriber with customer/dealer/plan attributes
sub_enriched = (dim_subscriber
    .merge(dim_customer, on="customer_id", how="left", suffixes=("", "_cust"))
    .merge(dim_dealer[["dealer_code", "dealer_name", "dealer_type", "district"]].rename(
        columns={"district": "dealer_district"}), on="dealer_code", how="left")
    .merge(dim_plan, on="plan_code", how="left"))

bill_enriched = fact_billing.merge(
    sub_enriched[["subscriber_id", "customer_id", "segment", "district", "district_detail",
                  "dealer_code", "dealer_name", "dealer_type", "plan_code", "plan_family",
                  "is_legacy_plan"]],
    on="subscriber_id", how="left")

# ---------------------------------------------------------------------------
hr("1. MONTHLY REVENUE TREND")
monthly = bill_enriched.groupby("date").agg(
    revenue=("billed_amount", "sum"),
    active_subs=("subscriber_id", "nunique"),
).reset_index()
monthly["arpu"] = monthly.revenue / monthly.active_subs
monthly["revenue_mom_pct"] = monthly.revenue.pct_change() * 100
monthly["revenue_yoy_pct"] = monthly.revenue.pct_change(12) * 100
monthly["subs_mom"] = monthly.active_subs.diff()
print(monthly.to_string(index=False))

# ---------------------------------------------------------------------------
hr("2. NEW / CHURNED / NET ADDS BY MONTH")
all_months = pd.date_range("2023-07-01", "2025-12-01", freq="MS")
adds = dim_subscriber.groupby(dim_subscriber.join_date.values.astype("datetime64[M]")).size()
adds = adds.reindex(all_months, fill_value=0).rename("gross_adds")
churns = dim_subscriber.dropna(subset=["churn_date"]).groupby(
    dim_subscriber.dropna(subset=["churn_date"]).churn_date.values.astype("datetime64[M]")).size()
churns = churns.reindex(all_months, fill_value=0).rename("churned")
flow = pd.concat([adds, churns], axis=1)
flow["net_adds"] = flow.gross_adds - flow.churned
# active BOP = active EOP of prior month
active_eop = monthly.set_index("date").active_subs.reindex(all_months)
flow["active_bop"] = active_eop.shift(1)
flow["churn_rate_pct"] = (flow.churned / flow.active_bop) * 100
print(flow.to_string())

hr("2b. CHURN RATE TRAILING 3-MONTH AVERAGE (last 6 rows)")
flow["churn_rate_trail3"] = flow.churn_rate_pct.rolling(3).mean()
print(flow[["churned", "active_bop", "churn_rate_pct", "churn_rate_trail3"]].tail(12))

# ---------------------------------------------------------------------------
hr("3. REVENUE & ARPU BY SEGMENT (full period + last 6 months)")
by_segment = bill_enriched.groupby("segment").agg(revenue=("billed_amount", "sum"),
                                                     active_subs=("subscriber_id", "nunique")).reset_index()
by_segment["arpu"] = by_segment.revenue / by_segment.active_subs
print(by_segment)

last6 = bill_enriched[bill_enriched.date >= "2025-07-01"]
by_segment_recent = last6.groupby(["date", "segment"]).agg(
    revenue=("billed_amount", "sum"), subs=("subscriber_id", "nunique")).reset_index()
by_segment_recent["arpu"] = by_segment_recent.revenue / by_segment_recent.subs
pivot_arpu_seg = by_segment_recent.pivot(index="date", columns="segment", values="arpu")
print("\nARPU by segment, last 6 months:")
print(pivot_arpu_seg)

# ---------------------------------------------------------------------------
hr("4. REVENUE & ARPU BY DISTRICT (detail, 5-way)")
by_district = bill_enriched.groupby("district_detail").agg(
    revenue=("billed_amount", "sum"), active_subs=("subscriber_id", "nunique")).reset_index()
by_district["arpu"] = by_district.revenue / by_district.active_subs
print(by_district.sort_values("revenue", ascending=False))

# ---------------------------------------------------------------------------
hr("5. BUDGET VS ACTUAL BY (budget) DISTRICT, 2025 monthly")
actual_2025 = bill_enriched[bill_enriched.date >= "2025-01-01"].groupby(
    ["district", "date"]).billed_amount.sum().reset_index().rename(columns={"billed_amount": "actual"})
budget_2025 = fact_budget[["district", "date", "budget_amount"]].rename(columns={"budget_amount": "budget"})
bva = actual_2025.merge(budget_2025, on=["district", "date"], how="outer")
bva["variance"] = bva.actual - bva.budget
bva["variance_pct"] = bva.variance / bva.budget * 100
print(bva.sort_values(["district", "date"]).to_string(index=False))

hr("5b. BUDGET VS ACTUAL — YTD TOTALS BY DISTRICT (Jan-Dec 2025)")
bva_ytd = bva.groupby("district").agg(actual=("actual", "sum"), budget=("budget", "sum")).reset_index()
bva_ytd["variance"] = bva_ytd.actual - bva_ytd.budget
bva_ytd["variance_pct"] = bva_ytd.variance / bva_ytd.budget * 100
print(bva_ytd)

hr("5c. BUDGET VS ACTUAL — COMPANY-WIDE MONTHLY (2025), cumulative variance")
company_bva = bva.groupby("date").agg(actual=("actual", "sum"), budget=("budget", "sum")).reset_index()
company_bva["variance"] = company_bva.actual - company_bva.budget
company_bva["variance_pct"] = company_bva.variance / company_bva.budget * 100
company_bva["cum_actual"] = company_bva.actual.cumsum()
company_bva["cum_budget"] = company_bva.budget.cumsum()
company_bva["cum_variance"] = company_bva.cum_actual - company_bva.cum_budget
print(company_bva.to_string(index=False))

# ---------------------------------------------------------------------------
hr("6. PLAN MIX — REVENUE & SUBSCRIBER SHARE BY PLAN FAMILY, AND LEGACY SHARE OVER TIME")
by_family = bill_enriched.groupby("plan_family").agg(
    revenue=("billed_amount", "sum"), subs=("subscriber_id", "nunique")).reset_index()
by_family["revenue_share_pct"] = by_family.revenue / by_family.revenue.sum() * 100
print(by_family.sort_values("revenue", ascending=False))

legacy_trend = bill_enriched.groupby(["date", "is_legacy_plan"]).subscriber_id.nunique().unstack()
legacy_trend["pct_legacy"] = legacy_trend[True] / (legacy_trend[True] + legacy_trend[False]) * 100
print("\nLegacy plan share of active subscribers over time (every 3rd month):")
print(legacy_trend.iloc[::3][["pct_legacy"]])

# ---------------------------------------------------------------------------
hr("7. NEW SUBSCRIBER PLAN CHOICE — are NEW joiners going legacy or core plans?")
sub_enriched["join_month"] = sub_enriched.join_date.values.astype("datetime64[M]")
new_by_month_legacy = sub_enriched.groupby(["join_month", "is_legacy_plan"]).size().unstack(fill_value=0)
new_by_month_legacy["pct_legacy_of_new"] = new_by_month_legacy[True] / (new_by_month_legacy[True] + new_by_month_legacy[False]) * 100
print(new_by_month_legacy.tail(12))

# ---------------------------------------------------------------------------
hr("8. DEALER PERFORMANCE — gross adds, churn among their acquired subs, revenue")
dealer_adds = sub_enriched.groupby("dealer_name").size().rename("total_subs_acquired")
dealer_churn = sub_enriched.groupby("dealer_name").churn_date.apply(lambda s: s.notna().sum()).rename("churned_subs")
dealer_stats = pd.concat([dealer_adds, dealer_churn], axis=1)
dealer_stats["churn_rate_of_book_pct"] = dealer_stats.churned_subs / dealer_stats.total_subs_acquired * 100
dealer_rev = bill_enriched.groupby("dealer_name").billed_amount.sum().rename("lifetime_revenue")
dealer_stats = dealer_stats.join(dealer_rev)
print(dealer_stats.sort_values("total_subs_acquired", ascending=False))

hr("8b. DEALER new-subscriber trend, last 6 months (gross adds per month per dealer)")
recent_adds = sub_enriched[sub_enriched.join_month >= "2025-07-01"]
print(recent_adds.groupby(["join_month", "dealer_name"]).size().unstack(fill_value=0))

# ---------------------------------------------------------------------------
hr("9. CHURN RATE BY SEGMENT AND BY DISTRICT (of subscribers ever active in-window)")
in_window = sub_enriched[sub_enriched.in_billing_window]
churn_by_segment = in_window.groupby("segment").agg(
    total=("subscriber_id", "count"),
    churned=("churn_date", lambda s: s.notna().sum())
)
churn_by_segment["churn_rate_pct"] = churn_by_segment.churned / churn_by_segment.total * 100
print(churn_by_segment)

churn_by_district = in_window.groupby("district_detail").agg(
    total=("subscriber_id", "count"),
    churned=("churn_date", lambda s: s.notna().sum())
)
churn_by_district["churn_rate_pct"] = churn_by_district.churned / churn_by_district.total * 100
print(churn_by_district)

churn_by_family = in_window.groupby("plan_family").agg(
    total=("subscriber_id", "count"),
    churned=("churn_date", lambda s: s.notna().sum())
)
churn_by_family["churn_rate_pct"] = churn_by_family.churned / churn_by_family.total * 100
print(churn_by_family.sort_values("churn_rate_pct", ascending=False))

hr("9b. CHURN RATE: legacy vs core plans")
churn_by_legacy = in_window.groupby("is_legacy_plan").agg(
    total=("subscriber_id", "count"),
    churned=("churn_date", lambda s: s.notna().sum())
)
churn_by_legacy["churn_rate_pct"] = churn_by_legacy.churned / churn_by_legacy.total * 100
print(churn_by_legacy)

# ---------------------------------------------------------------------------
hr("10. TENURE AT CHURN — are churners leaving early (onboarding problem) or late?")
churned_subs = dim_subscriber.dropna(subset=["churn_date"])
print(churned_subs.tenure_days.describe())
print("\nChurn tenure buckets:")
bins = [0, 30, 90, 180, 365, 730, 10000]
labels = ["0-30d", "31-90d", "91-180d", "181-365d", "1-2yr", "2yr+"]
print(pd.cut(churned_subs.tenure_days, bins=bins, labels=labels).value_counts().sort_index())

print("\nDONE")
