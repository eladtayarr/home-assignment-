"""Phase 4 follow-up: find WHERE the H2-2025 churn acceleration is concentrated."""
import pandas as pd
pd.set_option("display.max_columns", 30)
pd.set_option("display.width", 160)
pd.set_option("display.max_rows", 200)

C = "data/clean"
dim_customer = pd.read_csv(f"{C}/dim_customer.csv")
dim_dealer = pd.read_csv(f"{C}/dim_dealer.csv")
dim_plan = pd.read_csv(f"{C}/dim_plan.csv")
dim_subscriber = pd.read_csv(f"{C}/dim_subscriber.csv", parse_dates=["join_date", "churn_date"])
fact_billing = pd.read_csv(f"{C}/fact_billing.csv", parse_dates=["date"])

sub = (dim_subscriber
    .merge(dim_customer, on="customer_id", how="left")
    .merge(dim_dealer[["dealer_code", "dealer_name", "dealer_type", "district"]].rename(
        columns={"district": "dealer_district"}), on="dealer_code", how="left")
    .merge(dim_plan, on="plan_code", how="left"))

all_months = pd.date_range("2023-07-01", "2025-12-01", freq="MS")

def hr(t):
    print("\n" + "=" * 95 + f"\n{t}\n" + "=" * 95)

def monthly_churn_rate_by(group_col):
    """Monthly churn rate = churned-in-month / active-at-start-of-month, split by group_col."""
    active_eop = fact_billing.merge(sub[["subscriber_id", group_col]], on="subscriber_id", how="left") \
        .groupby(["date", group_col]).subscriber_id.nunique().unstack(fill_value=0)
    active_bop = active_eop.shift(1)
    churned = sub.dropna(subset=["churn_date"]).copy()
    churned["churn_month"] = churned.churn_date.values.astype("datetime64[M]")
    churned_by = churned.groupby(["churn_month", group_col]).size().unstack(fill_value=0)
    churned_by = churned_by.reindex(all_months, fill_value=0)
    rate = (churned_by / active_bop) * 100
    return rate

hr("MONTHLY CHURN RATE BY SEGMENT (last 12 months)")
r = monthly_churn_rate_by("segment")
print(r.tail(12).round(2))

hr("MONTHLY CHURN RATE BY DISTRICT_DETAIL (last 12 months)")
r = monthly_churn_rate_by("district_detail")
print(r.tail(12).round(2))

hr("MONTHLY CHURN RATE BY DEALER (last 12 months)")
r = monthly_churn_rate_by("dealer_name")
print(r.tail(12).round(2))

hr("MONTHLY CHURN RATE BY DEALER_TYPE (last 12 months)")
r = monthly_churn_rate_by("dealer_type")
print(r.tail(12).round(2))

hr("MONTHLY CHURN RATE BY PLAN_FAMILY (last 12 months)")
r = monthly_churn_rate_by("plan_family")
print(r.tail(12).round(2))

hr("MONTHLY CHURN RATE BY is_legacy_plan (last 12 months)")
r = monthly_churn_rate_by("is_legacy_plan")
print(r.tail(12).round(2))

hr("MONTHLY CHURN RATE BY SEGMENT x overall level check (H1 2025 avg vs H2 2025 avg)")
r = monthly_churn_rate_by("segment")
h1 = r.loc["2025-01-01":"2025-06-01"].mean()
h2 = r.loc["2025-07-01":"2025-12-01"].mean()
print(pd.DataFrame({"H1_2025_avg": h1, "H2_2025_avg": h2, "delta_pp": h2 - h1, "rel_change_pct": (h2-h1)/h1*100}))

hr("Same for district_detail")
r = monthly_churn_rate_by("district_detail")
h1 = r.loc["2025-01-01":"2025-06-01"].mean()
h2 = r.loc["2025-07-01":"2025-12-01"].mean()
print(pd.DataFrame({"H1_2025_avg": h1, "H2_2025_avg": h2, "delta_pp": h2 - h1, "rel_change_pct": (h2-h1)/h1*100}))

hr("Same for dealer_name")
r = monthly_churn_rate_by("dealer_name")
h1 = r.loc["2025-01-01":"2025-06-01"].mean()
h2 = r.loc["2025-07-01":"2025-12-01"].mean()
print(pd.DataFrame({"H1_2025_avg": h1, "H2_2025_avg": h2, "delta_pp": h2 - h1, "rel_change_pct": (h2-h1)/h1*100}).sort_values("delta_pp", ascending=False))

hr("Same for plan_family")
r = monthly_churn_rate_by("plan_family")
h1 = r.loc["2025-01-01":"2025-06-01"].mean()
h2 = r.loc["2025-07-01":"2025-12-01"].mean()
print(pd.DataFrame({"H1_2025_avg": h1, "H2_2025_avg": h2, "delta_pp": h2 - h1, "rel_change_pct": (h2-h1)/h1*100}).sort_values("delta_pp", ascending=False))

hr("Same for is_legacy_plan")
r = monthly_churn_rate_by("is_legacy_plan")
h1 = r.loc["2025-01-01":"2025-06-01"].mean()
h2 = r.loc["2025-07-01":"2025-12-01"].mean()
print(pd.DataFrame({"H1_2025_avg": h1, "H2_2025_avg": h2, "delta_pp": h2 - h1, "rel_change_pct": (h2-h1)/h1*100}))

hr("Overall company churn rate: full trend for context (all months)")
overall = monthly_churn_rate_by("segment").sum(axis=1)  # not meaningful directly; recompute properly
active_eop_total = fact_billing.groupby("date").subscriber_id.nunique()
active_bop_total = active_eop_total.reindex(all_months).shift(1)
churned_total = sub.dropna(subset=["churn_date"]).copy()
churned_total["churn_month"] = churned_total.churn_date.values.astype("datetime64[M]")
churned_total = churned_total.groupby("churn_month").size().reindex(all_months, fill_value=0)
overall_rate = (churned_total / active_bop_total) * 100
print(overall_rate.round(3))

hr("Dealer acquisition SHARE shift -- is a high-churn dealer growing share of NEW adds recently?")
sub["join_month"] = sub.join_date.values.astype("datetime64[M]")
share = sub.groupby(["join_month", "dealer_name"]).size().unstack(fill_value=0)
share_pct = share.div(share.sum(axis=1), axis=0) * 100
print(share_pct.tail(12).round(1))

print("\nDONE")
