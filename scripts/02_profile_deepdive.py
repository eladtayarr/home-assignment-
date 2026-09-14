"""Phase 1 deep-dive follow-ups on flagged issues."""
import pandas as pd
import numpy as np

RAW = "data/raw"

customers = pd.read_csv(f"{RAW}/customers.csv", dtype=str)
subscribers = pd.read_csv(f"{RAW}/subscribers.csv", dtype=str)
billing = pd.read_csv(f"{RAW}/monthly_billing.csv", dtype=str)
dealers = pd.read_csv(f"{RAW}/dealers.csv", dtype=str)
plans = pd.read_csv(f"{RAW}/price_plans.csv", dtype=str)
budget = pd.read_csv(f"{RAW}/budget.csv", dtype=str)

billing["billed_amount_f"] = pd.to_numeric(billing.billed_amount, errors="coerce")
billing["billing_month_dt"] = pd.to_datetime(billing.billing_month, format="%Y-%m")
subscribers["join_date_dt"] = pd.to_datetime(subscribers.join_date, format="%m/%d/%Y")
subscribers["churn_date_dt"] = pd.to_datetime(subscribers.churn_date, format="%m/%d/%Y", errors="coerce")
subscribers["join_month"] = subscribers.join_date_dt.values.astype("datetime64[M]")
subscribers["churn_month"] = subscribers.churn_date_dt.values.astype("datetime64[M]")

def hr(t):
    print("\n" + "=" * 90 + f"\n{t}\n" + "=" * 90)

merged = billing.merge(subscribers[["subscriber_id", "churn_month", "join_month", "churn_date_dt"]],
                        on="subscriber_id", how="left")

hr("Billing STRICTLY AFTER churn MONTH (not just same-month partial bill)")
strictly_after = merged[merged.churn_month.notna() & (merged.billing_month_dt > merged.churn_month)]
print("Rows strictly after churn month:", len(strictly_after))
print("Distinct subscribers:", strictly_after.subscriber_id.nunique())
print(strictly_after[["subscriber_id", "billing_month", "churn_date_dt"]].head(15))

hr("Billing IN churn month but after churn_date (partial month) -- expected/benign")
same_month_after = merged[merged.churn_month.notna() & (merged.billing_month_dt == merged.churn_month)]
print("Rows:", len(same_month_after))

hr("Zero-billing subscribers: are they early/short-lived or outside billing window?")
subs_with_billing = set(billing.subscriber_id.unique())
zero_bill = subscribers[~subscribers.subscriber_id.isin(subs_with_billing)].copy()
print("Count:", len(zero_bill))
print("join_date range for zero-billing subs:", zero_bill.join_date_dt.min(), "to", zero_bill.join_date_dt.max())
print("churn populated among zero-billing subs:", zero_bill.churn_date_dt.notna().sum(), "/", len(zero_bill))
# how many joined AND churned within same month, before any invoice would generate?
zero_bill["same_month_churn"] = (zero_bill.join_month == zero_bill.churn_month)
print("Joined and churned within the same calendar month:", zero_bill.same_month_churn.sum())
print("\njoin_month distribution of zero-billing subs (top 10):")
print(zero_bill.join_month.value_counts().sort_index().tail(10))
print("\nHow many zero-billing subs joined in Dec-2025 (last month, no invoice run yet)?")
print((zero_bill.join_month == pd.Timestamp("2025-12-01")).sum())
print("\nHow many zero-billing subs have churn_date populated at all (i.e. not just 'too new')?")
print(zero_bill.churn_date_dt.notna().sum())
print("\nOf those with churn populated, tenure in days (join to churn):")
tenure = (zero_bill.loc[zero_bill.churn_date_dt.notna(), "churn_date_dt"] - zero_bill.loc[zero_bill.churn_date_dt.notna(), "join_date_dt"]).dt.days
print(tenure.describe())

hr("Overall join_date / churn_date range vs billing range")
print("subscribers join_date range:", subscribers.join_date_dt.min(), subscribers.join_date_dt.max())
print("subscribers churn_date range:", subscribers.churn_date_dt.min(), subscribers.churn_date_dt.max())
print("billing_month range:", billing.billing_month_dt.min(), billing.billing_month_dt.max())
print("Subscribers who joined BEFORE billing data starts (2023-07):", (subscribers.join_date_dt < pd.Timestamp("2023-07-01")).sum())

hr("Legacy/duplicate-style plan codes (T01-T25) vs base plans -- plan sprawl check")
plans_dedup = plans.drop_duplicates(subset=["plan_code"]).copy()
print("Total distinct plan_code:", plans_dedup.plan_code.nunique())
plans_dedup["is_legacy_style"] = plans_dedup.plan_code.str.startswith("PLN-T")
print(plans_dedup.groupby("is_legacy_style").size())
print("\nplan_family list_price spread (base vs T-series) - do T-series duplicate a family/price combo already covered?")
fam_price = plans_dedup.groupby(["plan_family"]).agg(
    n_plans=("plan_code", "nunique"),
    min_price=("monthly_list_price", lambda s: pd.to_numeric(s).min()),
    max_price=("monthly_list_price", lambda s: pd.to_numeric(s).max()),
)
print(fam_price)

hr("Subscriber adoption of T-series (legacy) vs core plan codes")
plan_usage = subscribers.plan_code.value_counts()
core_codes = ["PLN-S100", "PLN-S200", "PLN-S300", "PLN-UMAX", "PLN-U69", "PLN-B60", "PLN-B40",
              "PLN-YTH", "PLN-FAM", "PLN-SNR"]
t_series_usage = plan_usage[plan_usage.index.str.startswith("PLN-T")].sum()
core_usage = plan_usage[plan_usage.index.isin(core_codes)].sum()
print("Subscribers on core (current) plan codes:", core_usage)
print("Subscribers on T-series (legacy-named) plan codes:", t_series_usage)
print("Total:", plan_usage.sum())

hr("billed_amount vs plan monthly_list_price -- discount / dispersion check")
sub_plan = subscribers.merge(plans_dedup[["plan_code", "monthly_list_price", "plan_family"]], on="plan_code", how="left")
sub_plan["monthly_list_price"] = pd.to_numeric(sub_plan.monthly_list_price)
bill_plan = billing.merge(sub_plan[["subscriber_id", "monthly_list_price", "plan_family"]], on="subscriber_id", how="left")
bill_plan["ratio"] = bill_plan.billed_amount_f / bill_plan.monthly_list_price
print(bill_plan.ratio.describe())
print("\n% of billing rows within 5% of list price:", (bill_plan.ratio.between(0.95, 1.05)).mean() * 100)
print("% of billing rows below 50% of list price (heavy discount / partial month):", (bill_plan.ratio < 0.5).mean() * 100)
print("% of billing rows above 105% of list price (overage/add-ons):", (bill_plan.ratio > 1.05).mean() * 100)

hr("Dealer city null check + dealer_type breakdown")
print(dealers[dealers.city.isna()])
print(dealers.dealer_type.value_counts())

hr("Customer segment x district cross-tab (sanity)")
print(pd.crosstab(customers.segment, customers.district))

hr("Duplicate full-row check across all tables")
for name, df in [("customers", customers), ("subscribers", subscribers), ("dealers", dealers),
                  ("price_plans", plans), ("budget", budget), ("monthly_billing", billing)]:
    print(name, "full duplicate rows:", df.duplicated().sum())

print("\nDONE")
